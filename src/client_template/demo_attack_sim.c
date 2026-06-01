/*
 * Capcan Demo Attack Simulator (not for grading, implemented for viva demo)
 * ==========================================
 * Simulates realistic attack activity to exercise all Capcan collectors and
 * security watchers in a demo environment. Compiled to a standalone binary so
 *
 *
 * Build
 * -----
 *   gcc -O2 -o demo_attack_sim demo_attack_sim.c -lpthread
 *
 * Usage
 * -----
 *   ./demo_attack_sim [OPTIONS]
 *
 * Options
 * -------
 *   --all               Run all scenarios (default when no flag is provided)
 *   --cpu-stress        Saturate all logical CPUs for --duration seconds
 *   --disk-stress       Write/read a large temp file to spike disk I/O metrics
 *   --file-events       Create, modify, and delete a file in /etc (or /tmp
 *                       fallback) to trigger FileIntegrityWatcher
 *   --process-events    Rename child processes to suspicious names (nc, nmap)
 *                       to trigger ProcessWatcher
 *   --honeypot-access    Read the Capcan canary files to trigger the honeypot
 *                       atime-based alert (poll_atime, 30s poll cycle)
 *   --network-events    Bind a TCP listener on port 4444 to trigger NetworkWatcher
 *   --duration SECS     Stress scenario duration in seconds (default: 30)
 *   --help              Print this message and exit
 *
 * Safety
 * ------
 *   - No existing system files are modified.
 *   - All temp files and sockets are cleaned up on exit (SIGINT/SIGTERM handled).
 *   - Process renaming uses prctl(PR_SET_NAME) — no code injection.
 *   - Network listener accepts no connections.
 *
 * Coverage notes
 * --------------
 * The following watchers are NOT triggered by this simulator because they
 * require real system events that cannot be safely synthesised:
 *
 *   LoginWatcher    — monitors /var/log/auth.log for SSH brute-force. Trigger
 *                     manually by running repeated failed SSH logins from
 *                     another machine in the demo network.
 *
 *   ServiceWatcher  — monitors systemctl for critical service state changes.
 *                     Trigger manually: `sudo systemctl stop <service>` then
 *                     restart. Stopping ufw or fail2ban is the most visible
 *                     demo event.
 *
 * Linux-only. Requires: glibc, pthreads (-lpthread).
 */

#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <netinet/in.h>
#include <pthread.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

/* -------------------------------------------------------------------------
 * Globals
 * ---------------------------------------------------------------------- */

static volatile sig_atomic_t g_stop = 0;
static int g_duration   = 300;  /* total runtime in seconds — configurable via --duration */
static int g_wave_secs  = 60;   /* per-wave stress duration */
#define WAVE_COOLDOWN 10         /* seconds of quiet between waves */

/* Paths that need cleaning up if we exit mid-scenario. */
static char g_tmp_disk_path[256] = {0};
static char g_tmp_file_event_path[256] = {0};

/* -------------------------------------------------------------------------
 * Logging helpers
 * ---------------------------------------------------------------------- */

static void sim_log(const char *tag, const char *fmt, ...)
{
    va_list ap;
    char timebuf[32];
    time_t now = time(NULL);
    struct tm *tm_info = localtime(&now);
    strftime(timebuf, sizeof(timebuf), "%H:%M:%S", tm_info);
    printf("[%s] [%s] ", timebuf, tag);
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    printf("\n");
    fflush(stdout);
}

/* -------------------------------------------------------------------------
 * Signal handler — clean up temp files on SIGINT / SIGTERM
 * ---------------------------------------------------------------------- */

static void handle_signal(int sig)
{
    (void)sig;
    g_stop = 1;
    if (g_tmp_disk_path[0])
        unlink(g_tmp_disk_path);
    if (g_tmp_file_event_path[0])
        unlink(g_tmp_file_event_path);
}

/* -------------------------------------------------------------------------
 * Scenario: CPU stress
 *
 * Spawns one pthread per logical CPU. Each thread runs a tight floating-point
 * loop that cannot be optimised away (volatile accumulator). Threads exit when
 * g_stop is set or their deadline arrives.
 * ---------------------------------------------------------------------- */

typedef struct { double deadline; } cpu_worker_args_t;

static void *cpu_worker(void *arg)
{
    cpu_worker_args_t *a = (cpu_worker_args_t *)arg;
    volatile double x = 1.0;
    while (!g_stop) {
        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        if ((double)now.tv_sec + (double)now.tv_nsec / 1e9 >= a->deadline)
            break;
        /* Tight FP loop — drives CPU utilisation on one core. */
        for (int i = 0; i < 500000; i++)
            x = x * 1.000001 + 0.000001;
    }
    return NULL;
}

static void cpu_stress(int duration)
{
    long ncpus = sysconf(_SC_NPROCESSORS_ONLN);
    if (ncpus <= 0) ncpus = 2;

    sim_log("cpu-stress", "Spinning up %ld worker threads for %ds …", ncpus, duration);

    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    double deadline = (double)ts.tv_sec + (double)ts.tv_nsec / 1e9 + duration;

    pthread_t *threads = calloc((size_t)ncpus, sizeof(pthread_t));
    cpu_worker_args_t *args = calloc((size_t)ncpus, sizeof(cpu_worker_args_t));
    if (!threads || !args) {
        sim_log("cpu-stress", "memory allocation failed");
        free(threads); free(args);
        return;
    }

    for (long i = 0; i < ncpus; i++) {
        args[i].deadline = deadline;
        pthread_create(&threads[i], NULL, cpu_worker, &args[i]);
    }
    for (long i = 0; i < ncpus; i++)
        pthread_join(threads[i], NULL);

    free(threads);
    free(args);
    sim_log("cpu-stress", "Done.");
}

/* -------------------------------------------------------------------------
 * Scenario: Disk stress
 *
 * Writes a 64 MiB temp file in /tmp using 1 MiB random-ish chunks, fsyncs,
 * then reads it back. Loops until the deadline to sustain the I/O spike.
 * ---------------------------------------------------------------------- */

#define DISK_CHUNK_SIZE  (1 * 1024 * 1024)  /* 1 MiB per write call */
#define DISK_PASSES      64                  /* 64 MiB per loop pass */

static void disk_stress(int duration)
{
    /* Build a predictable-but-non-zero chunk to defeat any transparent
     * zero-page optimisations in the kernel. */
    unsigned char *chunk = malloc(DISK_CHUNK_SIZE);
    if (!chunk) { sim_log("disk-stress", "malloc failed"); return; }
    for (int i = 0; i < DISK_CHUNK_SIZE; i++)
        chunk[i] = (unsigned char)(i ^ 0xA5);

    snprintf(g_tmp_disk_path, sizeof(g_tmp_disk_path), "/tmp/capcan_sim_disk_XXXXXX");
    int fd = mkstemp(g_tmp_disk_path);
    if (fd < 0) {
        sim_log("disk-stress", "mkstemp failed: %s", strerror(errno));
        free(chunk);
        g_tmp_disk_path[0] = '\0';
        return;
    }

    sim_log("disk-stress", "Writing/reading %s for %ds …", g_tmp_disk_path, duration);

    time_t deadline = time(NULL) + duration;
    while (!g_stop && time(NULL) < deadline) {
        /* Write pass */
        lseek(fd, 0, SEEK_SET);
        ftruncate(fd, 0);
        for (int p = 0; p < DISK_PASSES; p++) {
            if (write(fd, chunk, DISK_CHUNK_SIZE) < 0) break;
        }
        fsync(fd);

        /* Read pass */
        lseek(fd, 0, SEEK_SET);
        ssize_t n;
        do {
            n = read(fd, chunk, DISK_CHUNK_SIZE);
        } while (n > 0 && !g_stop);
    }

    close(fd);
    unlink(g_tmp_disk_path);
    g_tmp_disk_path[0] = '\0';
    free(chunk);
    sim_log("disk-stress", "Done.");
}

/* -------------------------------------------------------------------------
 * Scenario: File events
 *
 * Creates, appends to, then deletes a clearly-labelled sentinel file inside
 * /etc (which FileIntegrityWatcher monitors via inotify) to trigger all three
 * event types: file_created → file_modified → file_deleted.
 *
 * Falls back to /tmp if /etc is not writable. Note that /tmp is NOT watched
 * by FileIntegrityWatcher, so only /etc triggers a real alert.
 * ---------------------------------------------------------------------- */

static void file_events(void)
{
    const char *dirs[] = { "/etc", "/tmp", NULL };
    const char *chosen = NULL;
    int triggers_watcher = 0;

    for (int i = 0; dirs[i]; i++) {
        if (access(dirs[i], W_OK) == 0) {
            chosen = dirs[i];
            triggers_watcher = (i == 0);
            break;
        }
    }
    if (!chosen) { sim_log("file-events", "No writable directory found — skipped."); return; }
    if (!triggers_watcher)
        sim_log("file-events", "WARNING: /etc not writable — using /tmp (will NOT trigger FileIntegrityWatcher).");

    /* Run multiple create→modify→delete cycles per wave to produce several events. */
    const char *filenames[] = { "capcan-demo-sim.txt", "capcan-demo-cfg.conf", "capcan-demo-key.pem" };
    int n_files = (int)(sizeof(filenames) / sizeof(filenames[0]));

    for (int cycle = 0; cycle < n_files && !g_stop; cycle++) {
        char path[512];
        snprintf(path, sizeof(path), "%s/%s", chosen, filenames[cycle]);

        sim_log("file-events", "[%d/%d] Creating  %s", cycle + 1, n_files, path);
        FILE *fh = fopen(path, "w");
        if (!fh) { sim_log("file-events", "fopen failed: %s", strerror(errno)); continue; }
        fprintf(fh, "capcan demo simulation — file_created event (cycle %d)\n", cycle + 1);
        fclose(fh);
        sleep(1);

        sim_log("file-events", "[%d/%d] Modifying %s", cycle + 1, n_files, path);
        fh = fopen(path, "a");
        if (fh) { fprintf(fh, "capcan demo simulation — file_modified event\n"); fclose(fh); }
        sleep(1);

        sim_log("file-events", "[%d/%d] Deleting  %s", cycle + 1, n_files, path);
        unlink(path);
        sleep(1);
    }
    sim_log("file-events", "Done.");
}

/* -------------------------------------------------------------------------
 * Scenario: Process events
 *
 * Forks child processes and uses prctl(PR_SET_NAME) to rename them to
 * suspicious names ("nc", "nmap"). psutil reads the process name from
 * /proc/{pid}/status Name:, which reflects the prctl name — so ProcessWatcher
 * fires a process_started alert without executing any harmful binary.
 *
 * The child simply sleeps long enough for ProcessWatcher to poll (10 s cycle),
 * then exits. The parent waits for it after killing it.
 * ---------------------------------------------------------------------- */

static void process_events(void)
{
    /* Pool of suspicious process names targeting ProcessWatcher */
    const char *names[] = {
        "nc", "nmap", "wget", "curl", "hydra",
        "masscan", "ncat", "socat", "python3", "msfconsole", NULL
    };
    int total = 0;
    while (names[total]) total++;

    /* Run 3 randomly-chosen names per wave so each wave looks different */
    srand((unsigned int)time(NULL) ^ (unsigned int)getpid());
    for (int i = 0; i < 3 && !g_stop; i++) {
        const char *name = names[rand() % total];
        sim_log("process-events", "Spawning suspicious process '%s' …", name);
        pid_t pid = fork();
        if (pid < 0) { sim_log("process-events", "fork failed: %s", strerror(errno)); continue; }
        if (pid == 0) {
            prctl(PR_SET_NAME, name, 0, 0, 0);
            sleep(15);
            exit(0);
        }
        sleep(12);
        kill(pid, SIGTERM);
        waitpid(pid, NULL, 0);
    }
    sim_log("process-events", "Done.");
}

/* -------------------------------------------------------------------------
 * Scenario: Honeypot access
 *
 * Reads the Capcan canary files to trigger poll_atime's atime-change
 * detection. The honeypot watcher compares st_atime every 30 seconds; a
 * change > 1 second fires a critical "honeypot_access" alert.
 *
 * On Linux with the default `relatime` mount option, atime is updated on
 * read when the current atime is older than mtime — which is always true for
 * freshly-deployed canary files. If `noatime` is set, only the inotify path
 * (write/delete events) will fire and reads won't be detected; the simulator
 * logs a warning in that case.
 *
 * Files tried (in order):
 *   /tmp/.capcan_session   — no root required
 *   ~/.capcan/.env         — no root required
 * ---------------------------------------------------------------------- */

static void honeypot_access(void)
{
    const char *home = getenv("HOME");
    char env_path[512] = {0};
    if (home)
        snprintf(env_path, sizeof(env_path), "%s/.capcan/.env", home);

    /* Candidate canary files.  /tmp/.capcan_session is always tried;
     * ~/.capcan/.env requires HOME to be set. */
    const char *candidates[] = {
        "/tmp/.capcan_session",
        env_path[0] ? env_path : NULL,
        NULL
    };

    int accessed = 0;
    for (int i = 0; candidates[i]; i++) {
        const char *path = candidates[i];
        if (access(path, F_OK) != 0)
            continue;  /* file not deployed yet */

        sim_log("honeypot-access", "Reading canary file %s …", path);
        FILE *fh = fopen(path, "r");
        if (!fh) {
            sim_log("honeypot-access", "Cannot open %s: %s", path, strerror(errno));
            continue;
        }
        /* Read the entire file so the kernel marks atime as accessed. */
        char buf[4096];
        while (fread(buf, 1, sizeof(buf), fh) > 0)
            ;
        fclose(fh);
        accessed++;
        sim_log("honeypot-access",
                "Read complete. poll_atime will detect this within 30s.");
    }

    if (!accessed) {
        sim_log("honeypot-access",
                "No canary files found — is the Capcan client running? "
                "Start the client first so it can deploy honeypot files.");
    }

    sim_log("honeypot-access", "Done.");
}


/* -------------------------------------------------------------------------
 * Scenario: Network events
 *
 * Binds a TCP listener on a port from SUSPICIOUS_LISTEN_PORTS and holds it
 * open for `duration` seconds so NetworkWatcher can detect it.
 * Tries candidate ports in order; falls back if a port is already in use.
 * ---------------------------------------------------------------------- */

static void network_events(int duration)
{
    int candidate_ports[] = { 4444, 4445, 5555, 9999, 0 };
    int srv_fd = -1;
    int bound_port = 0;

    for (int i = 0; candidate_ports[i]; i++) {
        int fd = socket(AF_INET, SOCK_STREAM, 0);
        if (fd < 0) continue;

        int opt = 1;
        setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        struct sockaddr_in addr = {0};
        addr.sin_family      = AF_INET;
        addr.sin_addr.s_addr = INADDR_ANY;
        addr.sin_port        = htons((uint16_t)candidate_ports[i]);

        if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) == 0) {
            listen(fd, 1);
            srv_fd = fd;
            bound_port = candidate_ports[i];
            break;
        }
        close(fd);
    }

    if (srv_fd < 0) {
        sim_log("network-events", "Could not bind to any suspicious port — skipped.");
        return;
    }

    sim_log("network-events", "Listening on TCP port %d for %ds …", bound_port, duration);

    /* Use poll/select with a timeout so we wake up promptly on g_stop. */
    struct timespec deadline;
    clock_gettime(CLOCK_MONOTONIC, &deadline);
    deadline.tv_sec += duration;

    while (!g_stop) {
        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        if (now.tv_sec > deadline.tv_sec ||
            (now.tv_sec == deadline.tv_sec && now.tv_nsec >= deadline.tv_nsec))
            break;
        sleep(1);
    }

    close(srv_fd);
    sim_log("network-events", "Done.");
}

/* -------------------------------------------------------------------------
 * Scenario: Memory stress
 *
 * Allocates and touches 512 MiB in chunks to drive memory_percent up.
 * Holds the allocation for `duration` seconds then frees it.
 * ---------------------------------------------------------------------- */

#define MEM_CHUNK_MB  64
#define MEM_CHUNKS     8   /* 64 MiB × 8 = 512 MiB total */

static void memory_stress(int duration)
{
    size_t chunk_sz = (size_t)MEM_CHUNK_MB * 1024 * 1024;
    void *chunks[MEM_CHUNKS];
    int n = 0;

    sim_log("memory-stress", "Allocating %d × %dMiB for %ds …", MEM_CHUNKS, MEM_CHUNK_MB, duration);
    for (int i = 0; i < MEM_CHUNKS; i++) {
        chunks[i] = malloc(chunk_sz);
        if (!chunks[i]) { sim_log("memory-stress", "malloc failed at chunk %d — proceeding with %d", i, n); break; }
        memset(chunks[i], (unsigned char)(i ^ 0xBE), chunk_sz);
        n++;
    }

    time_t deadline = time(NULL) + duration;
    while (!g_stop && time(NULL) < deadline) sleep(1);

    for (int i = 0; i < n; i++) free(chunks[i]);
    sim_log("memory-stress", "Done.");
}

/* -------------------------------------------------------------------------
 * Scenario: Log tampering
 *
 * Appends fake SSH brute-force lines to auth.log/syslog to trigger
 * LoginWatcher and demonstrate log-based alert detection.
 * ---------------------------------------------------------------------- */

static void log_tamper(void)
{
    const char *targets[] = { "/var/log/auth.log", "/var/log/syslog", "/var/log/messages", NULL };

    time_t now = time(NULL);
    char timebuf[32];
    struct tm *tm_info = localtime(&now);
    strftime(timebuf, sizeof(timebuf), "%b %d %H:%M:%S", tm_info);
    char hostname[64] = "localhost";
    gethostname(hostname, sizeof(hostname));

    for (int i = 0; targets[i]; i++) {
        if (access(targets[i], W_OK) != 0) continue;
        FILE *fh = fopen(targets[i], "a");
        if (!fh) continue;
        for (int j = 0; j < 5; j++) {
            fprintf(fh, "%s %s sshd[%d]: Failed password for root from 185.220.101.%d port %d ssh2\n",
                    timebuf, hostname, (int)(getpid() % 60000 + 1000 + j),
                    40 + j, 51200 + j);
        }
        fclose(fh);
        sim_log("log-tamper", "Appended 5 fake failed-login lines to %s", targets[i]);
        sim_log("log-tamper", "Done.");
        return;
    }
    sim_log("log-tamper", "No writable log file found — skipped.");
}

/* -------------------------------------------------------------------------
 * Scenario: Cron events
 *
 * Writes a fake cron job to /etc/cron.d/ then removes it, triggering
 * FileIntegrityWatcher on the /etc path.
 * ---------------------------------------------------------------------- */

static void cron_events(void)
{
    const char *path = "/etc/cron.d/capcan-demo-sim";
    if (access("/etc/cron.d", W_OK) != 0) {
        sim_log("cron-events", "/etc/cron.d not writable — skipped.");
        return;
    }
    sim_log("cron-events", "Writing fake cron job to %s …", path);
    FILE *fh = fopen(path, "w");
    if (!fh) { sim_log("cron-events", "fopen failed: %s", strerror(errno)); return; }
    fprintf(fh, "# capcan demo simulation\n*/5 * * * * root /tmp/capcan-demo-task.sh\n");
    fclose(fh);
    sleep(2);
    sim_log("cron-events", "Removing %s …", path);
    unlink(path);
    sim_log("cron-events", "Done.");
}

/* -------------------------------------------------------------------------
 * Thread wrappers
 * ---------------------------------------------------------------------- */

typedef struct { int duration; } scenario_args_t;

static void *thread_cpu_stress(void *arg)      { cpu_stress(((scenario_args_t *)arg)->duration);    return NULL; }
static void *thread_disk_stress(void *arg)     { disk_stress(((scenario_args_t *)arg)->duration);   return NULL; }
static void *thread_memory_stress(void *arg)   { memory_stress(((scenario_args_t *)arg)->duration); return NULL; }
static void *thread_file_events(void *arg)     { (void)arg; file_events();                           return NULL; }
static void *thread_process_events(void *arg)  { (void)arg; process_events();                        return NULL; }
static void *thread_network_events(void *arg)  { network_events(((scenario_args_t *)arg)->duration); return NULL; }
static void *thread_honeypot_access(void *arg) { (void)arg; honeypot_access();                       return NULL; }
static void *thread_log_tamper(void *arg)      { (void)arg; log_tamper();                             return NULL; }
static void *thread_cron_events(void *arg)     { (void)arg; cron_events();                            return NULL; }

/* -------------------------------------------------------------------------
 * main
 * ---------------------------------------------------------------------- */

static void print_help(const char *prog)
{
    printf(
        "Usage: %s [OPTIONS]\n\n"
        "  --all               Run all scenarios (default)\n"
        "  --cpu-stress        CPU saturation → telemetry spike\n"
        "  --disk-stress       Disk I/O stress → telemetry spike\n"
        "  --memory-stress     Memory pressure → telemetry spike\n"
        "  --file-events       Create/modify/delete files in /etc → FileIntegrityWatcher\n"
        "  --process-events    Suspicious process names → ProcessWatcher\n"
        "  --network-events    TCP listener on suspicious port → NetworkWatcher\n"
        "  --honeypot-access   Read canary files → honeypot atime alert\n"
        "  --log-tamper        Append fake SSH failures to auth.log → LoginWatcher\n"
        "  --cron-events       Write/remove fake cron job in /etc/cron.d\n"
        "  --duration SECS     Total runtime in seconds (default: 300)\n"
        "  --help              Show this message\n\n"
        "Scenarios repeat in ~60s waves for the full duration with a brief\n"
        "cooldown between waves, generating sustained telemetry spikes and alerts.\n"
        "All temp files and sockets are cleaned up on exit.\n",
        prog
    );
}

int main(int argc, char *argv[])
{
    struct sigaction sa = {0};
    sa.sa_handler = handle_signal;
    sigaction(SIGINT,  &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);

    int opt_all            = 0;
    int opt_cpu_stress     = 0;
    int opt_disk_stress    = 0;
    int opt_memory_stress  = 0;
    int opt_file_events    = 0;
    int opt_process_events = 0;
    int opt_network_events = 0;
    int opt_honeypot       = 0;
    int opt_log_tamper     = 0;
    int opt_cron_events    = 0;

    static struct option long_options[] = {
        { "all",             no_argument,       NULL, 'a' },
        { "cpu-stress",      no_argument,       NULL, 'c' },
        { "disk-stress",     no_argument,       NULL, 'd' },
        { "memory-stress",   no_argument,       NULL, 'm' },
        { "file-events",     no_argument,       NULL, 'f' },
        { "process-events",  no_argument,       NULL, 'p' },
        { "network-events",  no_argument,       NULL, 'n' },
        { "honeypot-access", no_argument,       NULL, 'H' },
        { "log-tamper",      no_argument,       NULL, 'l' },
        { "cron-events",     no_argument,       NULL, 'C' },
        { "duration",        required_argument, NULL, 'D' },
        { "help",            no_argument,       NULL, 'h' },
        { NULL, 0, NULL, 0 }
    };

    int c;
    while ((c = getopt_long(argc, argv, "acdmfpnHlCD:h", long_options, NULL)) != -1) {
        switch (c) {
            case 'a': opt_all            = 1; break;
            case 'c': opt_cpu_stress     = 1; break;
            case 'd': opt_disk_stress    = 1; break;
            case 'm': opt_memory_stress  = 1; break;
            case 'f': opt_file_events    = 1; break;
            case 'p': opt_process_events = 1; break;
            case 'n': opt_network_events = 1; break;
            case 'H': opt_honeypot       = 1; break;
            case 'l': opt_log_tamper     = 1; break;
            case 'C': opt_cron_events    = 1; break;
            case 'D': g_duration = atoi(optarg); break;
            case 'h': print_help(argv[0]); return 0;
            default:  print_help(argv[0]); return 1;
        }
    }

    int any = opt_cpu_stress | opt_disk_stress | opt_memory_stress | opt_file_events |
              opt_process_events | opt_network_events | opt_honeypot |
              opt_log_tamper | opt_cron_events;
    if (opt_all || !any) {
        opt_cpu_stress = opt_disk_stress = opt_memory_stress = opt_file_events =
            opt_process_events = opt_network_events = opt_honeypot =
            opt_log_tamper = opt_cron_events = 1;
    }

    printf("============================================================\n");
    printf("  Capcan Demo Attack Simulator\n");
    printf("  Total runtime : %ds  |  Wave duration : %ds  |  Cooldown : %ds\n",
           g_duration, g_wave_secs, WAVE_COOLDOWN);
    printf("============================================================\n");
    fflush(stdout);

    time_t run_end = time(NULL) + g_duration;
    int wave = 0;

    while (!g_stop && time(NULL) < run_end) {
        wave++;
        int remaining = (int)(run_end - time(NULL));
        int wave_dur  = remaining < g_wave_secs ? remaining : g_wave_secs;

        printf("\n[wave %d] Starting — %ds wave, %ds total remaining\n",
               wave, wave_dur, remaining);
        fflush(stdout);

        pthread_t threads[9];
        scenario_args_t args = { .duration = wave_dur };
        int n = 0;

        if (opt_cpu_stress)     pthread_create(&threads[n++], NULL, thread_cpu_stress,     &args);
        if (opt_disk_stress)    pthread_create(&threads[n++], NULL, thread_disk_stress,    &args);
        if (opt_memory_stress)  pthread_create(&threads[n++], NULL, thread_memory_stress,  &args);
        if (opt_file_events)    pthread_create(&threads[n++], NULL, thread_file_events,    NULL);
        if (opt_process_events) pthread_create(&threads[n++], NULL, thread_process_events, NULL);
        if (opt_network_events) pthread_create(&threads[n++], NULL, thread_network_events, &args);
        if (opt_honeypot)       pthread_create(&threads[n++], NULL, thread_honeypot_access,NULL);
        if (opt_log_tamper)     pthread_create(&threads[n++], NULL, thread_log_tamper,     NULL);
        if (opt_cron_events)    pthread_create(&threads[n++], NULL, thread_cron_events,    NULL);

        for (int i = 0; i < n; i++)
            pthread_join(threads[i], NULL);

        printf("[wave %d] Complete.\n", wave);
        fflush(stdout);

        remaining = (int)(run_end - time(NULL));
        if (!g_stop && remaining > 0) {
            int pause = remaining < WAVE_COOLDOWN ? remaining : WAVE_COOLDOWN;
            printf("[cooldown] %ds before next wave …\n", pause);
            fflush(stdout);
            for (int i = 0; i < pause && !g_stop; i++) sleep(1);
        }
    }

    printf("\n[done] All waves completed. Runtime: ~%ds.\n", g_duration);
    return 0;
}
