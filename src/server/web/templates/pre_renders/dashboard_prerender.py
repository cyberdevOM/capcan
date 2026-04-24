from flask import render_template
from markupsafe import Markup
import datetime

from ....core.database import Database


# ─── helpers ────────────────────────────────────────────────────────────────

def _humanize_time(dt_obj):
    """Return a human-readable 'X ago' string from a datetime (or None)."""
    if dt_obj is None:
        return "Never"
    now = datetime.datetime.now()
    # strip timezone if present so subtraction works
    if hasattr(dt_obj, "tzinfo") and dt_obj.tzinfo is not None:
        dt_obj = dt_obj.replace(tzinfo=None)
    seconds = (now - dt_obj).total_seconds()
    if seconds < 60:
        return f"{int(seconds)}s ago"
    if seconds < 3600:
        return f"{int(seconds / 60)} min ago"
    if seconds < 86400:
        return f"{int(seconds / 3600)} hrs ago"
    return f"{int(seconds / 86400)} days ago"


def _is_online(last_seen, threshold_seconds=600):
    """A client is online if its last telemetry arrived within threshold_seconds."""
    if last_seen is None:
        return False
    now = datetime.datetime.now()
    if hasattr(last_seen, "tzinfo") and last_seen.tzinfo is not None:
        last_seen = last_seen.replace(tzinfo=None)
    return (now - last_seen).total_seconds() <= threshold_seconds


def get_platform_icon(platform):
    """Return FontAwesome icon class for a platform string."""
    icons = {
        "win":     "fab fa-windows",
        "windows": "fab fa-windows",
        "mac":     "fab fa-apple",
        "macos":   "fab fa-apple",
        "deb":     "fab fa-linux",
        "ubuntu":  "fab fa-linux",
        "linux":   "fab fa-linux",
        "rpm":     "fab fa-linux",
    }
    return icons.get(platform.lower() if platform else "", "fas fa-desktop")


def _fetch_clients():
    """Query all non-revoked clients with their online status. Returns list of dicts."""
    db = Database()
    try:
        return db.get_all_clients_with_status()
    finally:
        db.close()


# ─── render functions ────────────────────────────────────────────────────────

def render_quickstats():
    """Render quick stats tile: total / online / offline counts."""
    clients = _fetch_clients()
    total = len(clients)
    online = sum(1 for c in clients if _is_online(c.get("last_seen")))
    offline = total - online

    html = f"""
    <div class="quickstats-grid">
        <div class="stat-item">
            <div class="stat-number">{total}</div>
            <div class="stat-label">Total Clients</div>
        </div>
        <div class="stat-item">
            <div class="stat-number stat-online">{online}</div>
            <div class="stat-label">Online</div>
        </div>
        <div class="stat-item">
            <div class="stat-number stat-offline">{offline}</div>
            <div class="stat-label">Offline</div>
        </div>
    </div>
    """
    return Markup(html)


def render_recent_activity():
    """Render recent activity tile: last 5 clients sorted by last_seen."""
    clients = _fetch_clients()
    # already sorted newest-first by the DB query; take first 5
    recent = clients[:5]

    html = '<div class="activity-list">'
    for c in recent:
        status = "online" if _is_online(c.get("last_seen")) else "offline"
        icon = get_platform_icon(c.get("client_os", ""))
        html += f"""
        <div class="activity-item">
            <div class="activity-icon"><i class="{icon}"></i></div>
            <div class="activity-details">
                <div class="activity-client">{c['hostname']}</div>
                <div class="activity-time">{_humanize_time(c.get('last_seen'))}</div>
            </div>
            <div class="activity-status">
                <span class="status-dot {status}"></span>
                {status.title()}
            </div>
        </div>
        """
    html += "</div>"
    return Markup(html)


def render_system_health():
    """Render system health tile using the latest telemetry from the most active client."""
    clients = _fetch_clients()
    # find the most recently seen client that has telemetry
    active = next((c for c in clients if c.get("last_seen") is not None), None)

    if active is None:
        return Markup("""
        <div class="health-metrics">
            <p style="color:#888;text-align:center;padding:1rem;">
                No clients reporting yet
            </p>
        </div>
        """)

    db = Database()
    try:
        row = db.get_latest_client_telemetry(active["client_id"])
    finally:
        db.close()

    if row is None or not row.get("telemetry"):
        return Markup("""
        <div class="health-metrics">
            <p style="color:#888;text-align:center;padding:1rem;">
                Awaiting first telemetry report
            </p>
        </div>
        """)

    t = row["telemetry"]
    cpu    = t.get("cpu_percent", 0)
    mem    = t.get("memory_percent", 0)
    disk   = t.get("disk_usage", 0)
    uptime = t.get("uptime_seconds")
    if uptime is not None:
        days, rem = divmod(int(uptime), 86400)
        hours, _  = divmod(rem, 3600)
        uptime_str = f"{days}d {hours}h" if days else f"{hours}h"
    else:
        uptime_str = "N/A"

    html = f"""
    <div class="health-metrics">
        <div style="font-size:0.75rem;color:#888;margin-bottom:0.5rem;">
            {active['hostname']} &mdash; {_humanize_time(active.get('last_seen'))}
        </div>
        <div class="metric-row">
            <span class="metric-label">Uptime:</span>
            <span class="metric-value">{uptime_str}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">CPU:</span>
            <div class="metric-bar">
                <div class="metric-fill" style="width:{cpu}%"></div>
                <span class="metric-percentage">{cpu}%</span>
            </div>
        </div>
        <div class="metric-row">
            <span class="metric-label">Memory:</span>
            <div class="metric-bar">
                <div class="metric-fill" style="width:{mem}%"></div>
                <span class="metric-percentage">{mem}%</span>
            </div>
        </div>
        <div class="metric-row">
            <span class="metric-label">Disk:</span>
            <div class="metric-bar">
                <div class="metric-fill" style="width:{disk}%"></div>
                <span class="metric-percentage">{disk}%</span>
            </div>
        </div>
    </div>
    """
    return Markup(html)


def render_network_status():
    """Render network status widget."""
    html = """
    <div class="network-status">
        <div class="network-item">
            <i class="fas fa-wifi"></i>
            <span>Connected</span>
        </div>
        <div class="network-item">
            <i class="fas fa-globe"></i>
            <span>8.8.8.8</span>
        </div>
        <div class="network-item">
            <i class="fas fa-server"></i>
            <span>Server Online</span>
        </div>
    </div>
    """
    return Markup(html)


def render_alerts():
    """Render alerts tile (placeholder — alert pipeline not yet connected)."""
    html = """
    <div class="alerts-list">
        <div class="alert-item alert-info">
            <i class="fas fa-info-circle"></i>
            <div class="alert-content">
                <div class="alert-message">Alert pipeline coming soon</div>
                <div class="alert-time">—</div>
            </div>
        </div>
    </div>
    """
    return Markup(html)


# ─── exports ─────────────────────────────────────────────────────────────────

__all__ = [
    "render_quickstats",
    "render_recent_activity",
    "render_system_health",
    "render_network_status",
    "render_alerts",
]
