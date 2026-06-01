let active_client_id = null;
let active_client_name = null;
const chart_instances = {};
const _telemetry_polls = {};

// ── Client selection ──────────────────────────────────────────
function selectClient(clientId) {
    active_client_id = clientId;
    active_client_name = document.querySelector(`.client-item[data-client-id="${clientId}"] .client-id`)?.textContent || clientId;
    const deleteBtn = document.getElementById('deleteClientBtn');
    if (deleteBtn) deleteBtn.disabled = false;

    // Card click = exclusive single select; check only this client's checkbox
    document.querySelectorAll('.client-select').forEach(el => { el.checked = el.value === clientId; });
    onClientCheckboxChange();

    fetch(`/clients?client_id=${clientId}`, {headers: {'X-Requested-With': 'XMLHttpRequest'}})
        .then(r => r.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newDetails = doc.getElementById('clientDetails');
            if (newDetails) {
                document.getElementById('clientDetails').innerHTML = newDetails.innerHTML;
                loadClientPanel(clientId);
            }
        });
    document.querySelectorAll('.client-item').forEach(el =>
        el.classList.toggle('active', el.dataset.clientId === clientId));
}

function connectClient(clientId) {
    console.log(`Connecting to client ${clientId}`);
}

function openFileManager(clientId) {
    console.log(`Opening file manager for client ${clientId}`);
}

function openTerminal(clientId) {
    console.log(`Opening terminal for client ${clientId}`);
}

function showLogs(clientId) {
    console.log(`Showing logs for client ${clientId}`);
}

function disconnectClient(clientId) {
    console.log(`Disconnecting client ${clientId}`);
}

// ── Client Panel (charts + alerts) ───────────────────────────
function loadClientPanel(clientId) {
    // Clear all active telemetry polls before starting a new one
    Object.keys(_telemetry_polls).forEach(id => {
        clearInterval(_telemetry_polls[id]);
        delete _telemetry_polls[id];
    });

    // Destroy any Chart.js instances from the previous client
    Object.keys(chart_instances).forEach(k => {
        chart_instances[k].destroy();
        delete chart_instances[k];
    });
    fetch_telemetry_and_render_charts(clientId);
    load_panel_alerts(clientId, 'all');

    // Refresh charts, stat cards, and alerts every 30 seconds
    _telemetry_polls[clientId] = setInterval(() => {
        fetch_telemetry_and_render_charts(clientId);
        load_panel_alerts(clientId, 'all', true);
    }, 30000);
}

function fetch_telemetry_and_render_charts(clientId) {
    fetch(`/api/v1/telemetry/web/${clientId}/history?limit=50`)
        .then(r => r.json())
        .then(data => {
            // Destroy existing instances for this client before re-rendering
            [`cpu-${clientId}`, `mem-${clientId}`, `disk-${clientId}`, `net-${clientId}`].forEach(k => {
                if (chart_instances[k]) { chart_instances[k].destroy(); delete chart_instances[k]; }
            });
            render_charts(clientId, data.telemetry || []);
            update_stat_cards(clientId, data.telemetry || []);
        })
        .catch(() => {});
}

function render_charts(clientId, rows) {
    if (typeof Chart === 'undefined') return;

    const labels = rows.map(r => {
        const d = new Date(r.timestamp);
        return d.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    });

    const sharedOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
            legend: {display: false},
            tooltip: {
                backgroundColor: '#1a1a2e',
                titleColor: '#d6d6e6',
                bodyColor: '#a0a0b0',
                borderColor: '#2e2e3e',
                borderWidth: 1,
            },
        },
        scales: {
            x: {
                ticks: {color: '#7a7a9a', maxTicksLimit: 6, maxRotation: 0},
                grid:  {color: 'rgba(255,255,255,0.05)'},
            },
            y: {
                ticks: {color: '#7a7a9a'},
                grid:  {color: 'rgba(255,255,255,0.05)'},
                beginAtZero: true,
            },
        },
    };

    function makeLineChart(canvasId, data, color, yMax) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        const opts = JSON.parse(JSON.stringify(sharedOptions));
        if (yMax !== undefined) opts.scales.y.max = yMax;
        return new Chart(canvas, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    data,
                    borderColor: color,
                    backgroundColor: color + '22',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true,
                    tension: 0.3,
                }],
            },
            options: opts,
        });
    }

    const cpuData  = rows.map(r => r.telemetry?.cpu_percent     ?? null);
    const memData  = rows.map(r => r.telemetry?.memory_percent  ?? null);
    const diskData = rows.map(r => r.telemetry?.disk_usage      ?? null);
    const sentData = rows.map(r => r.telemetry?.network_sent_bytes != null
        ? Math.round(r.telemetry.network_sent_bytes / 1024) : null);
    const recvData = rows.map(r => r.telemetry?.network_recv_bytes != null
        ? Math.round(r.telemetry.network_recv_bytes / 1024) : null);

    const c1 = makeLineChart(`chart-cpu-${clientId}`,  cpuData,  '#4ade80', 100);
    const c2 = makeLineChart(`chart-mem-${clientId}`,  memData,  '#60a5fa', 100);
    const c3 = makeLineChart(`chart-disk-${clientId}`, diskData, '#f59e0b', 100);
    if (c1) chart_instances[`cpu-${clientId}`]  = c1;
    if (c2) chart_instances[`mem-${clientId}`]  = c2;
    if (c3) chart_instances[`disk-${clientId}`] = c3;

    // Network: two datasets (sent + received)
    const netCanvas = document.getElementById(`chart-net-${clientId}`);
    if (netCanvas) {
        const opts = JSON.parse(JSON.stringify(sharedOptions));
        opts.plugins.legend.display = true;
        opts.plugins.legend.labels = {color: '#a0a0b0', boxWidth: 10, font: {size: 10}};
        chart_instances[`net-${clientId}`] = new Chart(netCanvas, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {label: 'Sent',  data: sentData, borderColor: '#a78bfa', backgroundColor: '#a78bfa22', borderWidth: 2, pointRadius: 0, fill: true, tension: 0.3, spanGaps: true},
                    {label: 'Recv',  data: recvData, borderColor: '#34d399', backgroundColor: '#34d39922', borderWidth: 2, pointRadius: 0, fill: true, tension: 0.3, spanGaps: true},
                ],
            },
            options: opts,
        });
    }

    // Show "no data" placeholder when there are no telemetry rows
    if (rows.length === 0) {
        ['cpu', 'mem', 'disk', 'net'].forEach(k => {
            const wrap = document.getElementById(`chart-${k}-${clientId}`)?.closest('.chart-wrap');
            if (wrap) wrap.innerHTML = '<div class="chart-no-data"><i class="fas fa-chart-line"></i><span>No data yet</span></div>';
        });
    }
}

// ── Panel alerts ──────────────────────────────────────────────
function load_panel_alerts(clientId, filter, silent = false) {
    const container = document.getElementById(`panel-alerts-${clientId}`);
    if (!container) return;
    if (!silent) {
        container.innerHTML = '<div class="panel-alerts-loading"><i class="fas fa-spinner fa-spin"></i></div>';
    }

    let url = `/api/v1/web/alerts?client_id=${clientId}&limit=100`;
    if (filter === 'unresolved')   url += '&status=unresolved';
    if (filter === 'acknowledged') url += '&status=acknowledged';
    if (filter === 'critical')     url += '&severity=critical';

    fetch(url)
        .then(r => r.json())
        .then(data => {
            const alerts = data.alerts || [];
            if (alerts.length === 0) {
                container.innerHTML = '<div class="panel-alerts-empty"><i class="fas fa-check-circle"></i><span>No alerts found</span></div>';
                return;
            }
            container.innerHTML = alerts.map(a => render_panel_alert_item(a, clientId)).join('');
        })
        .catch(() => {
            if (container) container.innerHTML = '<div class="panel-alerts-empty">Failed to load alerts.</div>';
        });
}

function filterPanelAlerts(btn, clientId) {
    btn.closest('.alert-filter-pills').querySelectorAll('.alert-pill').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    load_panel_alerts(clientId, btn.dataset.filter);
}

function render_panel_alert_item(a, clientId) {
    const severityColors = {critical: '#f87171', high: '#fb923c', medium: '#fbbf24', low: '#60a5fa', info: '#a78bfa'};
    const color = severityColors[a.severity] || '#a0a0b0';
    const time  = panel_relative_time(a.created_at);
    const statusClass = a.status === 'unresolved' ? 'unresolved' : a.status === 'acknowledged' ? 'acknowledged' : 'resolved';
    const statusLabel = a.status === 'unresolved' ? 'Open' : a.status === 'acknowledged' ? 'Ack' : 'Done';

    // Parse a human-readable detail snippet from the details JSON blob
    let detailSnippet = '';
    if (a.details) {
        try {
            const d = typeof a.details === 'string' ? JSON.parse(a.details) : a.details;
            if (d.message)        detailSnippet = d.message;
            else if (d.value != null && d.threshold != null)
                detailSnippet = `Value ${d.value} exceeded threshold ${d.threshold}`;
            else if (d.process)   detailSnippet = `Process: ${d.process}`;
            else {
                const first = Object.entries(d)[0];
                if (first) detailSnippet = `${first[0]}: ${first[1]}`;
            }
        } catch(_) {}
    }

    const scoreHtml = a.score != null
        ? `<span class="panel-alert-score" title="Risk score">${Math.round(a.score)}</span>`
        : '';

    const role = window.CAPCAN_USER_ROLE || 'read-only';
    const can_act = role !== 'read-only';

    const ackBtn = (can_act && a.status === 'unresolved')
        ? `<button class="panel-alert-btn" title="Acknowledge" onclick="ackPanelAlert('${a.alert_id}','${clientId}')"><i class="fas fa-check"></i></button>`
        : '';
    const resBtn = (can_act && a.status === 'acknowledged')
        ? `<button class="panel-alert-btn resolve" title="Resolve" onclick="resolvePanelAlert('${a.alert_id}','${clientId}')"><i class="fas fa-times"></i></button>`
        : '';

    return `
    <div class="panel-alert-item" data-alert-id="${a.alert_id}">
        <div class="panel-alert-severity-bar" style="background:${color}"></div>
        <div class="panel-alert-content">
            <div class="panel-alert-top">
                <span class="panel-alert-type">${a.event_type || 'alert'}</span>
                <span class="panel-alert-sev-badge" style="color:${color};border-color:${color}20;background:${color}15">${a.severity || '?'}</span>
                ${scoreHtml}
                <span class="panel-alert-status ${statusClass}">${statusLabel}</span>
            </div>
            ${detailSnippet ? `<div class="panel-alert-detail">${esc_panel_html(detailSnippet)}</div>` : ''}
            <div class="panel-alert-time"><i class="fas fa-clock" style="opacity:.5;margin-right:3px"></i>${time}</div>
        </div>
        <div class="panel-alert-actions">${ackBtn}${resBtn}</div>
    </div>`;
}

function esc_panel_html(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function ackPanelAlert(alertId, clientId) {
    const el = document.querySelector(`[data-alert-id="${alertId}"]`);
    if (el) el.style.opacity = '0.4';
    fetch(`/api/v1/web/alerts/${alertId}/acknowledge`, {method: 'POST'})
        .then(() => reload_panel_alerts(clientId));
}

function resolvePanelAlert(alertId, clientId) {
    const el = document.querySelector(`[data-alert-id="${alertId}"]`);
    if (el) el.style.opacity = '0.4';
    fetch(`/api/v1/web/alerts/${alertId}/resolve`, {method: 'POST'})
        .then(() => reload_panel_alerts(clientId));
}

function reload_panel_alerts(clientId) {
    const activeFilter = document.querySelector(`#panel-alerts-${clientId}`)
        ?.closest('.panel-alerts-section')
        ?.querySelector('.alert-pill.active')
        ?.dataset.filter || 'all';
    load_panel_alerts(clientId, activeFilter, true); // silent = no loading flash
}

function panel_relative_time(isoStr) {
    if (!isoStr) return '—';
    const diffMs = Date.now() - new Date(isoStr).getTime();
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1)  return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24)  return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
}

function togglePanelConfig(clientId) {
    const body    = document.getElementById(`cfg-body-${clientId}`);
    const chevron = document.getElementById(`cfg-chevron-${clientId}`);
    if (!body) return;
    const opening = body.style.display === 'none' || body.style.display === '';
    body.style.display    = opening ? 'block' : 'none';
    if (chevron) chevron.style.transform = opening ? 'rotate(180deg)' : '';
}

// ── Multi-select ──────────────────────────────────────────────
function toggleSelectAll(cb) {
    document.querySelectorAll('.client-select').forEach(el => { el.checked = cb.checked; });
    onClientCheckboxChange();
}

function onClientCheckboxChange() {
    const selected = getSelectedClientIds();
    const masterCb = document.getElementById('select-all-clients');
    const all = document.querySelectorAll('.client-select');
    if (masterCb) masterCb.indeterminate = selected.length > 0 && selected.length < all.length;
    document.querySelectorAll('.btn-configure-selected').forEach(btn => {
        btn.style.opacity = selected.length > 0 ? '1' : '0.5';
    });
}

function getSelectedClientIds() {
    return Array.from(document.querySelectorAll('.client-select:checked')).map(el => el.value);
}

// ── Config push ───────────────────────────────────────────────
function read_config_form(clientId) {
    const intervalMinutes = parseInt(document.getElementById(`cfg-interval-${clientId}`)?.value || '5', 10);
    const interval = intervalMinutes * 60;
    const collectKeys = ['cpu', 'memory', 'disk', 'network', 'processes', 'temperatures', 'top_processes'];
    const collect = {};
    collectKeys.forEach(k => {
        const el = document.getElementById(`cfg-${k}-${clientId}`);
        collect[k] = el ? el.checked : true;
    });
    const watcherKeys = ['file_integrity', 'process', 'network', 'login', 'service'];
    const watchers = {};
    watcherKeys.forEach(k => {
        const el = document.getElementById(`cfg-w-${k}-${clientId}`);
        watchers[k] = el ? el.checked : true;
    });
    return { interval, collect, watchers };
}

function pushConfig(clientIds, formSourceId) {
    const settings = read_config_form(formSourceId);
    const statusEl = document.getElementById(`cfg-status-${formSourceId}`);
    if (statusEl) { statusEl.textContent = ''; statusEl.className = 'config-status'; }

    fetch('/api/v1/clients/config', {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ client_ids: clientIds, settings })
    })
    .then(r => r.json().then(data => ({ ok: r.ok, data })))
    .then(({ ok, data }) => {
        if (!statusEl) return;
        if (!ok || data.error) {
            statusEl.textContent = 'Error: ' + (data.error || 'Unknown error');
            statusEl.className = 'config-status error';
        } else {
            statusEl.textContent = (data.message || 'Settings queued') + ' — will apply on next client check-in.';
            statusEl.className = 'config-status success';
            setTimeout(() => { statusEl.textContent = ''; statusEl.className = 'config-status'; }, 7000);
        }
    })
    .catch(err => {
        if (statusEl) {
            statusEl.textContent = 'Error: ' + err.message;
            statusEl.className = 'config-status error';
        }
    });
}

function pushConfigToSelected(formSourceId) {
    const ids = getSelectedClientIds();
    if (ids.length === 0) { alert('No clients selected. Use the checkboxes in the list.'); return; }
    pushConfig(ids, formSourceId);
}

function openBulkConfig() {
    const ids = getSelectedClientIds();
    if (ids.length === 0) { alert('Select at least one client first.'); return; }
    const activeItem = document.querySelector('.client-item.active');
    if (activeItem) {
        pushConfigToSelected(activeItem.dataset.clientId);
    } else {
        alert(`${ids.length} client(s) selected. Open a client to configure, then click "Apply to all selected".`);
    }
}

function toggleFilter() {}

// ── Add Client Modal ──────────────────────────────────────────
function openAddClientModal() {
    document.getElementById('addUsername').value = '';
    document.getElementById('addIpAddress').value = '';
    document.getElementById('addPassword').value = '';
    document.getElementById('addClientError').textContent = '';
    set_add_loading(false);
    document.getElementById('addClientModal').classList.add('active');
    document.getElementById('addUsername').focus();
}

function closeAddClientModal() {
    if (document.getElementById('addSubmitBtn').disabled) return;
    document.getElementById('addClientModal').classList.remove('active');
}

function set_add_loading(loading) {
    document.getElementById('addSubmitBtn').disabled = loading;
    document.getElementById('addCancelBtn').disabled = loading;
    document.getElementById('addBtnLabel').style.display = loading ? 'none' : '';
    document.getElementById('addBtnSpinner').style.display = loading ? '' : 'none';
}

function submitAddClient() {
    const username = document.getElementById('addUsername').value.trim();
    const ip_address = document.getElementById('addIpAddress').value.trim();
    const password = document.getElementById('addPassword').value;
    const errorEl = document.getElementById('addClientError');

    if (!username) { errorEl.textContent = 'Username is required.'; return; }
    if (!ip_address) { errorEl.textContent = 'Client IP is required.'; return; }
    if (!password) { errorEl.textContent = 'Password is required.'; return; }
    errorEl.textContent = '';
    set_add_loading(true);

    fetch('/api/v1/clients/admin/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ username, ip_address, password })
    })
    .then(r => r.json())
    .then(data => {
        set_add_loading(false);
        if (data.error) { errorEl.textContent = data.error; return; }
        location.reload();
    })
    .catch(err => {
        set_add_loading(false);
        errorEl.textContent = 'Error: ' + err.message;
    });
}

// ── Delete Client Modal ───────────────────────────────────────
function openDeleteClientModal() {
    if (!active_client_id) return;
    document.getElementById('deleteClientMsg').textContent =
        `Are you sure you want to delete client "${active_client_name}"? This will SSH into the machine and uninstall the service.`;
    document.getElementById('deletePassword').value = '';
    document.getElementById('deleteClientError').textContent = '';
    set_delete_loading(false);
    document.getElementById('deleteClientModal').classList.add('active');
    document.getElementById('deletePassword').focus();
}

function closeDeleteClientModal() {
    if (document.getElementById('deleteSubmitBtn').disabled) return;
    document.getElementById('deleteClientModal').classList.remove('active');
}

function set_delete_loading(loading) {
    document.getElementById('deleteSubmitBtn').disabled = loading;
    document.getElementById('deleteCancelBtn').disabled = loading;
    document.getElementById('deleteBtnLabel').style.display = loading ? 'none' : '';
    document.getElementById('deleteBtnSpinner').style.display = loading ? '' : 'none';
}

function confirmDeleteClient() {
    if (!active_client_id) return;
    const password = document.getElementById('deletePassword').value;
    const errorEl = document.getElementById('deleteClientError');

    if (!password) { errorEl.textContent = 'Password is required.'; return; }
    errorEl.textContent = '';
    set_delete_loading(true);

    fetch(`/api/v1/clients/admin/${active_client_id}`, {
        method: 'DELETE',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ password })
    })
    .then(r => r.json())
    .then(data => {
        set_delete_loading(false);
        if (data.error) { errorEl.textContent = data.error; return; }
        closeDeleteClientModal();
        location.reload();
    })
    .catch(err => {
        set_delete_loading(false);
        errorEl.textContent = 'Delete failed: ' + err.message;
    });
}

// ── Real-time stat card + status badge updates ────────────────
function fmt_uptime(seconds) {
    if (seconds == null) return '—';
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (d > 0) return `${d}d ${h}h`;
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
}

function update_stat_cards(clientId, rows) {
    if (!rows || rows.length === 0) return;
    const latest = rows[rows.length - 1];
    const t = latest.telemetry || {};

    const setText = (id, val) => {
        const el = document.getElementById(id);
        if (el && val != null) el.textContent = val;
    };

    setText(`stat-cpu-${clientId}`,   t.cpu_percent    != null ? `${t.cpu_percent}%`    : null);
    setText(`stat-mem-${clientId}`,   t.memory_percent != null ? `${t.memory_percent}%` : null);
    setText(`stat-disk-${clientId}`,  t.disk_usage     != null ? `${t.disk_usage}%`     : null);
    setText(`stat-procs-${clientId}`, t.process_count  != null ? t.process_count        : null);
    setText(`stat-uptime-${clientId}`, t.uptime_seconds != null ? fmt_uptime(t.uptime_seconds) : null);

    // Update panel status badge based on how recent the latest telemetry is
    const ageMs = latest.timestamp ? Date.now() - new Date(latest.timestamp).getTime() : Infinity;
    const status = ageMs <= 600000 ? 'online' : 'offline';
    const badge = document.getElementById(`panel-status-badge-${clientId}`);
    const dot   = document.getElementById(`panel-status-dot-${clientId}`);
    const txt   = document.getElementById(`panel-status-text-${clientId}`);
    if (badge) badge.className = `panel-status-badge ${status}`;
    if (dot)   dot.className   = `status-dot ${status}`;
    if (txt)   txt.textContent = status.charAt(0).toUpperCase() + status.slice(1);
}

// ── Client list status poll (runs continuously) ───────────────
function poll_client_list_status() {
    fetch('/api/v1/web/dashboard/clients/status')
        .then(r => r.json())
        .then(data => {
            (data.clients || []).forEach(c => {
                const dot = document.getElementById(`list-dot-${c.client_id}`);
                if (dot) dot.className = `status-dot ${c.is_online ? 'online' : 'offline'}`;
                const ls = document.getElementById(`list-lastseen-${c.client_id}`);
                if (ls) ls.textContent = c.last_seen;
            });
        })
        .catch(() => {});
}

// ── Event listeners (deferred until DOM is ready) ─────────────
document.addEventListener('DOMContentLoaded', function () {
    // Start client list status poll immediately and repeat every 60 s
    poll_client_list_status();
    setInterval(poll_client_list_status, 60000);

    document.getElementById('clientSearch')?.addEventListener('input', function () {
        const q = this.value.toLowerCase();
        document.querySelectorAll('.client-item').forEach(el => {
            const text = el.querySelector('.client-id')?.textContent.toLowerCase() || '';
            el.style.display = text.includes(q) ? '' : 'none';
        });
    });

    document.getElementById('addClientModal')?.addEventListener('click', function (e) {
        if (e.target === this) closeAddClientModal();
    });

    document.getElementById('deleteClientModal')?.addEventListener('click', function (e) {
        if (e.target === this) closeDeleteClientModal();
    });
});
