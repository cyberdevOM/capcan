from markupsafe import Markup
import datetime

from ....core.database import Database
from .dashboard_prerender import get_platform_icon, _humanize_time, _is_online


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


def render_client_list():
    """Render the complete client list with multi-select checkboxes."""
    clients = _fetch_clients()

    if not clients:
        return Markup("""
        <div class="client-list-empty">
            <i class="fas fa-desktop"></i>
            <p>No clients registered yet.</p>
        </div>
        """)

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

    html = header
    for c in clients:
        status = "online" if _is_online(c.get("last_seen")) else "offline"
        icon = get_platform_icon(c.get("client_os", ""))
        last_seen = _humanize_time(c.get("last_seen"))
        cid = c['client_id']
        html += f"""
        <div class="client-item" data-client-id="{cid}">
            <label class="client-checkbox" onclick="event.stopPropagation()">
                <input type="checkbox" class="client-select" value="{cid}"
                       onchange="onClientCheckboxChange()">
            </label>
            <div class="client-status" onclick="selectClient('{cid}')">
                <span class="status-dot {status}"></span>
            </div>
            <div class="client-icon" onclick="selectClient('{cid}')">
                <i class="{icon}"></i>
            </div>
            <div class="client-info" onclick="selectClient('{cid}')">
                <div class="client-id">{c['hostname']}</div>
                <div class="client-platform">{(c.get('client_os') or 'unknown').title()}</div>
                <div class="client-last-seen">{last_seen}</div>
            </div>
            <div class="client-actions" onclick="selectClient('{cid}')">
                <i class="fas fa-chevron-right"></i>
            </div>
        </div>
        """
    return Markup(html)


def render_client_details(client_id=None):
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

    # row columns: client_id, client_number, hostname, client_os,
    #              description, version, client_secret, registered_at, revoked, notes
    cols = ["client_id", "client_number", "hostname", "client_os",
            "description", "version", "client_secret", "registered_at", "revoked", "notes"]
    c = dict(zip(cols, row))

    status = "offline"
    if telemetry_row:
        status = "online" if _is_online(telemetry_row.get("timestamp")) else "offline"

    icon = get_platform_icon(c.get("client_os", ""))
    t = telemetry_row["telemetry"] if telemetry_row else {}
    cpu  = t.get("cpu_percent", "—")
    mem  = t.get("memory_percent", "—")
    disk = t.get("disk_usage", "—")

    cpu_w  = f"{cpu}%" if isinstance(cpu,  (int, float)) else "0%"
    mem_w  = f"{mem}%" if isinstance(mem,  (int, float)) else "0%"
    disk_w = f"{disk}%" if isinstance(disk, (int, float)) else "0%"

    html = f"""
    <div class="client-details-content">
        <div class="client-header">
            <div class="client-header-main">
                <i class="{icon}"></i>
                <div class="client-header-info">
                    <h2>{c['hostname']}</h2>
                    <span class="client-platform-detail">{(c.get('client_os') or 'unknown').title()}</span>
                </div>
            </div>

            <div class="client-info-grid">
                <div class="info-card">
                    <div class="info-label">Status</div>
                    <div class="info-value">{status.title()}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Last Seen</div>
                    <div class="info-value">{_humanize_time(telemetry_row['timestamp'] if telemetry_row else None)}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Platform</div>
                    <div class="info-value">{(c.get('client_os') or 'unknown').title()}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Version</div>
                    <div class="info-value">{c.get('version', 'N/A')}</div>
                </div>
            </div>

            <div class="client-controls">
                <button class="control-btn primary" onclick="connectClient('{c['client_id']}')">
                    <i class="fas fa-plug"></i> Connect
                </button>
                <button class="control-btn secondary" onclick="showLogs('{c['client_id']}')">
                    <i class="fas fa-file-alt"></i> Logs
                </button>
                <button class="control-btn danger" onclick="disconnectClient('{c['client_id']}')">
                    <i class="fas fa-unplug"></i> Disconnect
                </button>
            </div>

            <div class="client-performance">
                <h4>Latest Telemetry</h4>
                <div class="performance-metrics">
                    <div class="metric">
                        <div class="metric-label">CPU Usage</div>
                        <div class="metric-bar">
                            <div class="metric-fill" style="width:{cpu_w}"></div>
                            <span class="metric-text">{cpu}{"%" if isinstance(cpu, (int,float)) else ""}</span>
                        </div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Memory</div>
                        <div class="metric-bar">
                            <div class="metric-fill" style="width:{mem_w}"></div>
                            <span class="metric-text">{mem}{"%" if isinstance(mem, (int,float)) else ""}</span>
                        </div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Disk Usage</div>
                        <div class="metric-bar">
                            <div class="metric-fill" style="width:{disk_w}"></div>
                            <span class="metric-text">{disk}{"%" if isinstance(disk, (int,float)) else ""}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="client-remote-config">
                <h4>
                    Remote Settings
                    {('<span class="pending-badge"><i class="fas fa-clock"></i> Pending</span>') if pending_count > 0 else ''}
                </h4>
                <div class="config-form" id="config-form-{c['client_id']}">
                    <div class="config-row">
                        <label class="config-label">Report interval (seconds)</label>
                        <input type="number" class="config-input" id="cfg-interval-{c['client_id']}"
                               min="10" max="86400"
                               value="{effective_settings.get('interval', 300)}">
                    </div>
                    <div class="config-row">
                        <label class="config-label">Collect</label>
                        <div class="config-toggles">
                            {_collect_toggle(c['client_id'], 'cpu',       'CPU',       effective_settings)}
                            {_collect_toggle(c['client_id'], 'memory',    'Memory',    effective_settings)}
                            {_collect_toggle(c['client_id'], 'disk',      'Disk',      effective_settings)}
                            {_collect_toggle(c['client_id'], 'network',   'Network',   effective_settings)}
                            {_collect_toggle(c['client_id'], 'processes', 'Processes', effective_settings)}
                        </div>
                    </div>
                    <div class="config-actions">
                        <button class="control-btn primary"
                                onclick="pushConfig(['{c['client_id']}'], '{c['client_id']}')">
                            <i class="fas fa-upload"></i> Apply to this client
                        </button>
                        <button class="control-btn secondary"
                                onclick="pushConfigToSelected('{c['client_id']}')">
                            <i class="fas fa-layer-group"></i> Apply to all selected
                        </button>
                    </div>
                    <div class="config-status" id="cfg-status-{c['client_id']}"></div>
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