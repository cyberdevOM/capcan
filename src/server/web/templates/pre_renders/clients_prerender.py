from markupsafe import Markup
import datetime

from ....core.database import Database
from .dashboard_prerender import get_platform_icon, _humanize_time, _is_online
from ....utils.timestamper import format_uptime


def _fetch_clients():
    db = Database()
    try:
        return db.get_all_clients_with_status()
    finally:
        db.close()


def _collect_toggle(client_id: str, key: str, label: str, effective: dict) -> str:
    """Render a single collect toggle checkbox."""
    collect = effective.get("collect", {})
    checked = "checked" if collect.get(key, True) else ""
    return (
        f'<label class="toggle-label">'
        f'<input type="checkbox" class="collect-toggle" '
        f'id="cfg-{key}-{client_id}" {checked}> {label}'
        f'</label>'
    )


def _watcher_toggle(client_id: str, key: str, label: str, effective: dict) -> str:
    """Render a single watcher toggle checkbox."""
    watchers = effective.get("watchers", {})
    checked = "checked" if watchers.get(key, True) else ""
    return (
        f'<label class="toggle-label">'
        f'<input type="checkbox" class="watcher-toggle" '
        f'id="cfg-w-{key}-{client_id}" {checked}> {label}'
        f'</label>'
    )


def render_client_list(user_role='read-only'):
    """Render the complete client list with multi-select checkboxes."""
    clients = _fetch_clients()
    can_manage = user_role in ('admin', 'super-admin')
    can_config = user_role in ('admin', 'super-admin', 'analyst')

    if not clients:
        return Markup("""
        <div class="client-list-empty">
            <i class="fas fa-desktop"></i>
            <p>No clients registered yet.</p>
        </div>
        """)

    if can_config:
        header = """
    <div class="client-list-header">
        <label class="select-all-label">
            <input type="checkbox" id="select-all-clients" onchange="toggleSelectAll(this)">
            <span>Select all</span>
        </label>
        <button class="btn-configure-selected" onclick="openBulkConfig()" title="Configure selected clients">
            <i class="fas fa-sliders-h"></i> Configure selected
        </button>
    </div>
    """
    else:
        header = ""

    html = header
    for c in clients:
        status = "online" if _is_online(c.get("last_seen")) else "offline"
        icon = get_platform_icon(c.get("client_os", ""))
        last_seen = _humanize_time(c.get("last_seen"))
        cid = c['client_id']
        os_label = (c.get('client_os') or 'Unknown').title()
        ip_label = c.get('ip_address') or ''
        platform_line = f"{os_label}" + (f" &bull; {ip_label}" if ip_label else "")
        checkbox_html = (
            f'<label class="client-checkbox" onclick="event.stopPropagation()">'
            f'<input type="checkbox" class="client-select" value="{cid}"'
            f' onchange="onClientCheckboxChange()"></label>'
        ) if can_config else ''
        html += f"""
        <div class="client-item" data-client-id="{cid}" onclick="selectClient('{cid}')">
            {checkbox_html}
            <div class="client-status">
                <span class="status-dot {status}" id="list-dot-{cid}"></span>
            </div>
            <div class="client-icon">
                <i class="{icon}"></i>
            </div>
            <div class="client-info">
                <div class="client-id">{c['hostname']}</div>
                <div class="client-platform">{platform_line}</div>
                <div class="client-last-seen" id="list-lastseen-{cid}">{last_seen}</div>
            </div>
            <div class="client-actions">
                <i class="fas fa-chevron-right"></i>
            </div>
        </div>
        """
    return Markup(html)


def render_client_details(client_id=None, user_role='read-only'):
    """Render client details panel, optionally with latest telemetry."""
    if not client_id:
        return Markup("""
        <div class="client-details-empty">
            <i class="fas fa-desktop"></i>
            <h3>Select a Client</h3>
            <p>Choose a client from the list to view details and metrics.</p>
        </div>
        """)

    db = Database()
    try:
        row = db.get_client_by_id(client_id)
        telemetry_row = db.get_latest_client_telemetry(client_id)
        effective_settings = db.get_effective_settings(client_id) or {}
        db.cursor.execute(
            "SELECT COUNT(*) FROM client_configs WHERE client_id = %s AND applied_at IS NULL",
            (client_id,),
        )
        pending_count = db.cursor.fetchone()[0]
    finally:
        db.close()

    if not row:
        return Markup("""
        <div class="client-details-error">
            <i class="fas fa-exclamation-triangle"></i>
            <h3>Client Not Found</h3>
            <p>The selected client could not be found.</p>
        </div>
        """)

    cols = ["client_id", "client_number", "hostname", "client_os",
            "description", "version", "client_secret", "registered_at", "revoked", "notes"]
    c = dict(zip(cols, row))
    cid = c['client_id']

    status = "offline"
    if telemetry_row:
        status = "online" if _is_online(telemetry_row.get("timestamp")) else "offline"

    icon = get_platform_icon(c.get("client_os", ""))
    os_label = (c.get('client_os') or 'Unknown').title()
    ip_label = c.get('ip_address', '') or ''
    subtitle = os_label + (f" &bull; {ip_label}" if ip_label else "")

    t = telemetry_row["telemetry"] if telemetry_row else {}
    cpu  = t.get("cpu_percent", "—")
    mem  = t.get("memory_percent", "—")
    disk = t.get("disk_usage", "—")
    uptime_s = t.get("uptime_seconds")
    uptime_disp = format_uptime(uptime_s) if uptime_s is not None else "—"
    procs = t.get("process_count", "—")

    pending_badge = (
        '<span class="pending-badge"><i class="fas fa-clock"></i> Pending</span>'
        if pending_count > 0 else ''
    )

    def stat_card(icon_cls, label, value, unit="", stat_id=""):
        val_str = f"{value}{unit}" if isinstance(value, (int, float)) else str(value)
        id_attr = f' id="{stat_id}"' if stat_id else ''
        return f"""
        <div class="stat-card">
            <div class="stat-icon"><i class="{icon_cls}"></i></div>
            <div class="stat-info">
                <div class="stat-label">{label}</div>
                <div class="stat-value"{id_attr}>{val_str}</div>
            </div>
        </div>"""

    stats_html = (
        stat_card("fas fa-microchip", "CPU", cpu, "%" if isinstance(cpu, (int, float)) else "", f"stat-cpu-{cid}") +
        stat_card("fas fa-memory", "Memory", mem, "%" if isinstance(mem, (int, float)) else "", f"stat-mem-{cid}") +
        stat_card("fas fa-hdd", "Disk", disk, "%" if isinstance(disk, (int, float)) else "", f"stat-disk-{cid}") +
        stat_card("fas fa-clock", "Uptime", uptime_disp, "", f"stat-uptime-{cid}") +
        stat_card("fas fa-tasks", "Processes", procs, "", f"stat-procs-{cid}")
    )

    can_config = user_role in ('admin', 'super-admin', 'analyst')
    can_act = user_role in ('admin', 'super-admin')

    if can_config: # match interval value with settings from client_main, deployer, and settings_prerender
        config_html = f"""
    <div class="config-form" id="config-form-{cid}">
        <div class="config-row">
            <label class="config-label">Report interval (minutes)</label>
            <input type="number" class="config-input" id="cfg-interval-{cid}"
                   min="1" max="60"
                   value="{round(effective_settings.get('interval', 120) / 60)}"> 
        </div>
        <div class="config-row">
            <label class="config-label">Collect</label>
            <div class="config-toggles">
                {_collect_toggle(cid, 'cpu',           'CPU',          effective_settings)}
                {_collect_toggle(cid, 'memory',        'Memory',       effective_settings)}
                {_collect_toggle(cid, 'disk',          'Disk',         effective_settings)}
                {_collect_toggle(cid, 'network',       'Network',      effective_settings)}
                {_collect_toggle(cid, 'processes',     'Processes',    effective_settings)}
                {_collect_toggle(cid, 'temperatures',  'Temperatures', effective_settings)}
                {_collect_toggle(cid, 'top_processes', 'Top Procs',    effective_settings)}
            </div>
        </div>
        <div class="config-row">
            <label class="config-label">Watchers</label>
            <div class="config-toggles">
                {_watcher_toggle(cid, 'file_integrity', 'File Integrity', effective_settings)}
                {_watcher_toggle(cid, 'process',        'Process',        effective_settings)}
                {_watcher_toggle(cid, 'network',        'Network',        effective_settings)}
                {_watcher_toggle(cid, 'login',          'Login',          effective_settings)}
                {_watcher_toggle(cid, 'service',        'Service',        effective_settings)}
            </div>
        </div>
        <div class="config-actions">
            <button class="control-btn primary"
                    onclick="pushConfig(['{cid}'], '{cid}')">
                <i class="fas fa-upload"></i> Apply to this client
            </button>
            <button class="control-btn secondary btn-configure-selected"
                    onclick="pushConfigToSelected('{cid}')">
                <i class="fas fa-layer-group"></i> Apply to all selected
            </button>
        </div>
        <div class="config-status" id="cfg-status-{cid}"></div>
    </div>"""
    else:
        config_html = ""

    action_buttons_html = ""
    if can_act:
        action_buttons_html = f"""
                <button class="control-btn secondary" onclick="showLogs('{cid}')">
                    <i class="fas fa-file-alt"></i> Logs
                </button>
                <button class="control-btn primary" onclick="connectClient('{cid}')">
                    <i class="fas fa-plug"></i> Connect
                </button>"""

    config_section_html = ""
    if can_config:
        config_section_html = f"""
                <div class="panel-config-section">
                    <button class="panel-config-toggle" onclick="togglePanelConfig('{cid}')">
                        <i class="fas fa-sliders-h"></i>
                        Remote Settings
                        {pending_badge}
                        <i class="fas fa-chevron-down panel-config-chevron" id="cfg-chevron-{cid}"></i>
                    </button>
                    <div class="panel-config-body" id="cfg-body-{cid}">
                        {config_html}
                    </div>
                </div>"""

    html = f"""
    <div class="client-panel" data-client-id="{cid}">

        <div class="panel-header">
            <div class="panel-header-left">
                <i class="{icon} panel-platform-icon"></i>
                <div class="panel-header-info">
                    <h2 class="panel-hostname">{c['hostname']}</h2>
                    <span class="panel-subtitle">{subtitle}</span>
                </div>
                <span class="panel-status-badge {status}" id="panel-status-badge-{cid}">
                    <span class="status-dot {status}" id="panel-status-dot-{cid}"></span>
                    <span id="panel-status-text-{cid}">{status.title()}</span>
                </span>
            </div>
            <div class="panel-header-actions">
                {action_buttons_html}
            </div>
        </div>

        <div class="panel-body">

            <div class="panel-data">

                <div class="panel-stats-row">
                    {stats_html}
                </div>

                <div class="panel-section-label">
                    <i class="fas fa-chart-line"></i> Telemetry History
                </div>
                <div class="charts-grid">
                    <div class="chart-card">
                        <div class="chart-card-header">
                            <span class="chart-title">CPU Usage</span>
                            <span class="chart-unit">%</span>
                        </div>
                        <div class="chart-wrap"><canvas id="chart-cpu-{cid}"></canvas></div>
                    </div>
                    <div class="chart-card">
                        <div class="chart-card-header">
                            <span class="chart-title">Memory Usage</span>
                            <span class="chart-unit">%</span>
                        </div>
                        <div class="chart-wrap"><canvas id="chart-mem-{cid}"></canvas></div>
                    </div>
                    <div class="chart-card">
                        <div class="chart-card-header">
                            <span class="chart-title">Disk Usage</span>
                            <span class="chart-unit">%</span>
                        </div>
                        <div class="chart-wrap"><canvas id="chart-disk-{cid}"></canvas></div>
                    </div>
                    <div class="chart-card">
                        <div class="chart-card-header">
                            <span class="chart-title">Network I/O</span>
                            <span class="chart-unit">KB</span>
                        </div>
                        <div class="chart-wrap"><canvas id="chart-net-{cid}"></canvas></div>
                    </div>
                </div>

                {config_section_html}

            </div>

            <div class="panel-alerts-section">
                <div class="panel-alerts-header">
                    <span class="panel-section-label">
                        <i class="fas fa-bell"></i> Alerts
                    </span>
                    <div class="alert-filter-pills">
                        <button class="alert-pill active" data-filter="all"
                                onclick="filterPanelAlerts(this, '{cid}')">All</button>
                        <button class="alert-pill" data-filter="unresolved"
                                onclick="filterPanelAlerts(this, '{cid}')">Open</button>
                        <button class="alert-pill" data-filter="acknowledged"
                                onclick="filterPanelAlerts(this, '{cid}')">Ack</button>
                        <button class="alert-pill" data-filter="critical"
                                onclick="filterPanelAlerts(this, '{cid}')">Critical</button>
                    </div>
                </div>
                <div class="panel-alerts-list" id="panel-alerts-{cid}">
                    <div class="panel-alerts-loading">
                        <i class="fas fa-spinner fa-spin"></i> Loading&hellip;
                    </div>
                </div>
            </div>

        </div>
    </div>
    """
    return Markup(html)


__all__ = [
    "render_client_list",
    "render_client_details",
]