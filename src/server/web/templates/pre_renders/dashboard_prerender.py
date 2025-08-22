from flask import render_template
from markupsafe import Markup
import datetime

# shared client list data
# This would typically be fetched from a database or an API in a real application
client_list = [
    {"id": "deb_1985111", "platform": "deb", "status": "online", "last_seen": "2 minutes ago"},
    {"id": "win_1192511", "platform": "win", "status": "online", "last_seen": "5 minutes ago"},
    {"id": "rpm_1134611", "platform": "mac", "status": "offline", "last_seen": "10 minutes ago"},
    {"id": "mac_1985111", "platform": "mac", "status": "online", "last_seen": "1 minute ago"},
    {"id": "win_1985111", "platform": "win", "status": "offline", "last_seen": "15 minutes ago"},
]

def export_client_list():
    return client_list

def render_quickstats():
    """Render quick stats for the dashboard."""
    total = len(client_list)
    online = sum(1 for c in client_list if c['status'] == 'online')
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
    """Render recent client activity."""
    recent_clients = sorted(client_list, key=lambda x: x.get('last_seen', ''), reverse=False)[:5]

    html = """
    <div class="activity-list">
    """

    for client in recent_clients:
        status_class = "online" if client['status'] == 'online' else "offline"
        platform_icon = get_platform_icon(client['platform'])

        html += f"""
        <div class="activity-item">
            <div class="activity-icon">
                <i class="{platform_icon}"></i>
            </div>
            <div class="activity-details">
                <div class="activity-client">{client['id']}</div>
                <div class="activity-time">{client['last_seen']}</div>
            </div>
            <div class="activity-status">
                <span class="status-dot {status_class}"></span>
                {client['status'].title()}
            </div>
        </div>
        """

    html += """
    </div>
    """
    return Markup(html)

def render_system_health():
    """Render system health information."""
    # Placeholder values for system health metrics
    uptime = "5 days, 4 hours"
    cpu_usage = 23
    memory_usage = 68
    disk_usage = 45

    html = f"""
    <div class="health-metrics">
        <div class="metric-row">
            <span class="metric-label">Uptime:</span>
            <span class="metric-value">{uptime}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">CPU:</span>
            <div class="metric-bar">
                <div class="metric-fill" style="width: {cpu_usage}%"></div>
                <span class="metric-percentage">{cpu_usage}%</span>
            </div>
        </div>
        <div class="metric-row">
            <span class="metric-label">Memory:</span>
            <div class="metric-bar">
                <div class="metric-fill" style="width: {memory_usage}%"></div>
                <span class="metric-percentage">{memory_usage}%</span>
            </div>
        </div>
        <div class="metric-row">
            <span class="metric-label">Disk:</span>
            <div class="metric-bar">
                <div class="metric-fill" style="width: {disk_usage}%"></div>
                <span class="metric-percentage">{disk_usage}%</span>
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
            <span>192.168.1.100</span>
        </div>
    </div>
    """
    return Markup(html)

def render_alerts():
    """Render system alerts."""
    # Placeholder alerts
    alerts=[
        {"type": "warning", "message": "High Memory usage detected.", "time": "5 min ago"},
        {"type": "info", "message": "New client connected", "time": "10 min ago"},
    ]

    html = """
    <div class="alerts-list"> 
    """

    for alert in alerts:
        icon = "fas fa-exclamation-triangle" if alert['type'] == 'warning' else "fas fa-info-circle"
        html += f"""
        <div class="alert-item alert-{alert['type']}">
            <i class="{icon}"></i>
            <div class="alert-content">
                <div class="alert-message">{alert['message']}</div>
                <div class="alert-time">{alert['time']}</div>
            </div>
        </div>
        """

    html += """
    </div>
    """

    return Markup(html)

def get_platform_icon(platform):
    """Get FontAwesome icon class based on platform."""
    icons = {
        "win": "fab fa-windows",
        "mac": "fab fa-apple",
        "deb": "fab fa-linux",
        "ubuntu": "fab fa-linux",
        "linux": "fab fa-linux",
        "rpm": "fab fa-linux",
    }
    return icons.get(platform, "fas fa-desktop")

# Export all render functions for use in templates

__all__ = [
    "export_client_list",
    "render_quickstats",
    "render_recent_activity",
    "render_system_health",
    "render_network_status",
    "render_alerts",
]
