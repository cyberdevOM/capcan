"""
Client deployment utilities.

Responsibilities:
  - Trigger build_client.sh at startup to produce dist/capcan-client-bundle/.
  - Deploy the bundle to a remote Linux host via SSH/SFTP (paramiko).
  - Uninstall the client service on a remote host via SSH.

The shared bundle on disk is never modified during deployment — the per-client
config.yaml is generated in memory and uploaded directly to the target host.
"""

import os
import threading
import subprocess
import yaml
import paramiko


REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..')
)
BUNDLE_DIR = os.path.join(REPO_ROOT, 'dist', 'capcan-client-bundle')
BUILD_SCRIPT = os.path.join(REPO_ROOT, 'scripts', 'build_client.sh')

_build_lock = threading.Lock()
_build_status: dict = {'state': 'idle', 'message': 'Not yet started'}

# Persisted across build threads so settings.yaml is written correctly after a build.
_bundle_demo_mode: bool = False
_bundle_demo_alerts_per_hour: int = 20


def write_bundle_settings(demo_mode: bool = False, demo_alerts_per_hour: int = 20) -> None:
    """
    Write settings.yaml into the bundle directory.

    Called at startup (after --demo flag is parsed) and after a successful
    background build so every copy of the bundle has consistent defaults.
    The deployer uploads all files in BUNDLE_DIR, so this file is included
    automatically whenever a client is deployed.
    """
    global _bundle_demo_mode, _bundle_demo_alerts_per_hour
    _bundle_demo_mode = demo_mode
    _bundle_demo_alerts_per_hour = demo_alerts_per_hour

    os.makedirs(BUNDLE_DIR, exist_ok=True)
    settings = {
        'demo_mode': demo_mode,
        'demo_alerts_per_hour': demo_alerts_per_hour,
        'interval': 300,
        'collect': {
            'cpu': True,
            'memory': True,
            'disk': True,
            'network': True,
            'processes': True,
        },
    }
    with open(os.path.join(BUNDLE_DIR, 'settings.yaml'), 'w') as fh:
        yaml.dump(settings, fh, default_flow_style=False, sort_keys=False)
    print(
        f'[deployer] settings.yaml written '
        f'(demo_mode={demo_mode}, demo_alerts_per_hour={demo_alerts_per_hour})'
    )


def get_build_status() -> dict:
    return _build_status.copy()


# ── Background build ──────────────────────────────────────────────────────────

def _do_build(server_ip: str, server_port: int) -> None:
    global _build_status
    with _build_lock:
        _build_status = {'state': 'building', 'message': 'Building client bundle…'}
        try:
            result = subprocess.run(
                ['bash', BUILD_SCRIPT, server_ip, str(server_port)],
                capture_output=True, text=True, timeout=300, cwd=REPO_ROOT,
            )
            if result.returncode == 0:
                _build_status = {'state': 'ready', 'message': 'Bundle ready'}
                _refresh_base_config(server_ip, server_port)
                write_bundle_settings(_bundle_demo_mode, _bundle_demo_alerts_per_hour)
            else:
                _build_status = {
                    'state': 'error',
                    'message': result.stderr.strip() or 'Build failed — check server logs.',
                }
        except subprocess.TimeoutExpired:
            _build_status = {'state': 'error', 'message': 'Build timed out after 300 s.'}
        except Exception as exc:
            _build_status = {'state': 'error', 'message': str(exc)}


def ensure_bundle(server_ip: str, server_port: int) -> None:
    """
    Called once at server startup.
    - If the binary already exists, refresh config.yaml with the current server URL.
    - Otherwise, kick off a background build thread.
    Guards against double-invocation (e.g. Flask debug reloader).
    """
    global _build_status

    with _build_lock:
        if _build_status['state'] == 'building':
            return  # already running, skip duplicate call

    bundle_binary = os.path.join(BUNDLE_DIR, 'capcan-client')
    if os.path.exists(bundle_binary):
        _refresh_base_config(server_ip, server_port)
        _build_status = {'state': 'ready', 'message': 'Bundle ready'}
        print(f'[deployer] Bundle found — config refreshed for http://{server_ip}:{server_port}')
    else:
        print(f'[deployer] Bundle not found — building in background for http://{server_ip}:{server_port}')
        t = threading.Thread(target=_do_build, args=(server_ip, server_port), daemon=True)
        t.start()


def _refresh_base_config(server_ip: str, server_port: int) -> None:
    """Write a fresh base config.yaml into the bundle (credentials left blank)."""
    os.makedirs(BUNDLE_DIR, exist_ok=True)
    with open(os.path.join(BUNDLE_DIR, 'config.yaml'), 'w') as fh:
        yaml.dump(
            {'server_url': f'http://{server_ip}:{server_port}',
             'platform': 'linux',
             'client_id': '',
             'secret_key': ''},
            fh,
        )


def _bundle_server_url() -> str:
    try:
        with open(os.path.join(BUNDLE_DIR, 'config.yaml')) as fh:
            return yaml.safe_load(fh).get('server_url', '')
    except Exception:
        return ''


# Deploy

def deploy_client(
    target_ip: str,
    ssh_user: str,
    ssh_password: str,
    client_id: str,
    secret_key: str,
) -> tuple[bool, str, str | None]:
    """
    SFTP the client bundle to target_ip and install it as a systemd service.

    config.yaml is generated in memory with the injected credentials —
    the shared bundle on disk is never modified.

    Returns (success: bool, message: str, real_hostname: str | None).
    """
    state = _build_status.get('state')
    if state == 'building':
        return False, 'Client bundle is still building — please wait and try again.', None
    if state != 'ready':
        return False, f'Client bundle not ready (state: {state}). Check server logs.', None

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(target_ip, username=ssh_user, password=ssh_password, timeout=30)
        sftp = ssh.open_sftp()

        # Grab the machine's real hostname before doing anything else
        real_hostname_raw, _ = _exec(ssh, 'hostname')
        real_hostname = real_hostname_raw.strip() or None

        _exec(ssh, 'mkdir -p /tmp/capcan-client-bundle')

        # Upload all bundle files (config.yaml overwritten below)
        for fname in sorted(os.listdir(BUNDLE_DIR)):
            local_path = os.path.join(BUNDLE_DIR, fname)
            if os.path.isfile(local_path):
                sftp.put(local_path, f'/tmp/capcan-client-bundle/{fname}')

        # Overwrite config.yaml with per-deployment credentials (never touch the disk copy)
        injected_config = yaml.dump({
            'server_url': _bundle_server_url(),
            'platform': 'linux',
            'client_id': client_id,
            'secret_key': secret_key,
        })
        with sftp.open('/tmp/capcan-client-bundle/config.yaml', 'w') as fh:
            fh.write(injected_config)

        sftp.close()

        _exec(ssh,
              'chmod +x /tmp/capcan-client-bundle/capcan-client '
              '/tmp/capcan-client-bundle/install-service.sh '
              '/tmp/capcan-client-bundle/uninstall-service.sh')

        # Run installer (install-service.sh copies uninstall-service.sh to /opt too)
        _sudo_exec(ssh, 'bash /tmp/capcan-client-bundle/install-service.sh', ssh_password)

        return True, 'Client deployed and service installed successfully.', real_hostname

    except paramiko.AuthenticationException:
        return False, 'SSH authentication failed — check the username and password.', None
    except (paramiko.SSHException, OSError) as exc:
        return False, f'SSH/network error: {exc}', None
    except Exception as exc:
        return False, f'Deployment failed: {exc}', None
    finally:
        ssh.close()


# Undeploy

def undeploy_client(
    target_ip: str,
    ssh_user: str,
    ssh_password: str,
) -> tuple[bool, str]:
    """
    Run the uninstall script on target_ip via SSH.
    Returns (success: bool, message: str).
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(target_ip, username=ssh_user, password=ssh_password, timeout=30)
        _sudo_exec(ssh, 'bash /opt/capcan-client/uninstall-service.sh', ssh_password)
        return True, 'Client uninstalled successfully.'
    except paramiko.AuthenticationException:
        return False, 'SSH authentication failed — check the username and password.'
    except (paramiko.SSHException, OSError) as exc:
        return False, f'SSH/network error: {exc}'
    except Exception as exc:
        return False, f'Uninstall failed: {exc}'
    finally:
        ssh.close()


# SSH helpers

def _exec(ssh: paramiko.SSHClient, cmd: str) -> tuple[str, str]:
    _, stdout, stderr = ssh.exec_command(cmd)
    stdout.channel.recv_exit_status()
    return stdout.read().decode(), stderr.read().decode()


def _sudo_exec(ssh: paramiko.SSHClient, cmd: str, password: str) -> str:
    """
    Run a privileged command via 'sudo -S' (password fed via stdin).

    Note: if the target sudoers policy sets 'requiretty', this will fail.
    Use NOPASSWD or SSH key auth with a sudo rule in that case.
    """
    stdin, stdout, stderr = ssh.exec_command(f'sudo -S {cmd}')
    stdin.write(password + '\n')
    stdin.flush()
    stdin.channel.shutdown_write()
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    err = stderr.read().decode()
    if exit_code != 0:
        raise RuntimeError(f'sudo command failed (exit {exit_code}): {err.strip()}')
    return out
