from markupsafe import Markup
from .dashboard_prerender import export_client_list

def get_platform_icon(platform):
    """Get FontAwesome icon for platform."""
    icons = {
        'win': 'fab fa-windows',
        'mac': 'fab fa-apple',
        'deb': 'fab fa-debian',
        'rpm': 'fab fa-redhat',
        'linux': 'fas fa-linux',
    }
    return icons.get(platform, 'fas fa-desktop')

def render_client_list():
    """Render the complete client list"""
    clients = export_client_list()

    html = ""
    for client in clients:
        html += render_client_item(client)

    return Markup(html)

def render_client_item(client):
    """Render individual client item"""
    platform_icon = get_platform_icon(client['platform'])
    status_class = "online" if client['status'] == "online" else "offline"

    html = f"""
    <div class="client-item" data-client-id="{client['id']}" onclick="selectClient('{client['id']}')">
        <div class="client-status">
            <span class="status-dot {status_class}"></span>
        </div>
        <div class="client-icon">
            <i class="{platform_icon}"></i>
        </div>
        <div class="client-info">
            <div class="client-id">{client['id']}</div>
            <div class="client-platform">{client['platform'].title()}</div>
            <div class="client-last-seen">{client['last_seen']}</div>
        </div>
        <div class="client-actions">
            <i class="fas fa-chevron-right"></i>
        </div>
    </div>
    """
    return html

def render_client_details(client_id=None):
    """Render client details panel"""
    if not client_id:
        return Markup("""
        <div class="client-details-empty">
            <i class="fas fa-desktop-empty"></i>
            <h3>Select a Client</h3>
            <p>Choose a client from the list to view details and controls.</p>
        </div>
        """)
    
    # Find the specific client

    clients = export_client_list()
    client = next((c for c in clients if c['id'] == client_id), None)

    if not client:
        return Markup("""
        <div class-"client-details-error">
            <i class="fas fa-exclamation-triangle"></i>
            <h3>Client Not Found</h3>
            <p>The selected client could not be found.</p>
        </div>
        """)
    
    platform_icon = get_platform_icon(client['platform'])
    status_class = "online" if client['status'] == "online" else "offline"

    html = f"""
    <div class="client-details-content">
        <div class="client-header">
            <div class="client-header-main">
                <i class="{platform_icon}"></i>
                <div class="client-header-info">
                    <h2>{client['id']}</h2>
                    <span class="client-platform-detail">{client['platform'].title()}</span>
                </div>
            </div>

            <div class="client-info-grid">
                <div class="info-card">
                    <div class="info-label">Status</div>
                    <div class="info-value">{client['status'].title()}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Last Seen</div>
                    <div class="info-value">{client['last_seen']}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Platform</div>
                    <div class="info-value">{client['platform'].title()}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">IP Address</div>
                    <div class="info-value">192.168.1.{45 + hash(client['id']) % 50}</div>
                </div>
            </div>
        
            <div class="client-controls">
                <button class="control-btn primary" onclick="connectClient('{client['id']}')">
                    <i class="fas fa-plug"></i> 
                    Connect
                </button>
                <button class="control-btn secondary" onclick="openFileManager('{client['id']}')">
                    <i class="fas fa-folder-open"></i>
                    File Manager
                </button>
                <button class="control-btn secondary" onclick="openTerminal('{client['id']}')
                    <i class="fas fa-terminal"></i>
                    Terminal
                </button>
                <button class="control-btn secondary" onclick="showLogs('{client['id']}')">
                    <i class="fas fa-file-alt"></i>
                    Logs
                </button>
                <button class="control-btn danger" onclick="disconnectClient('{client['id']}')">
                    <i class="fas fa-unplug"></i>
                    Disconnect
                </button>
            </div>

            <div class="client-performance">
                <h4>Performance</h4>
                <div class="performance-metrics">
                    <div class="metric">
                        <div class="metric-label">CPU Usage</div>
                        <div class="metric-bar">
                            <div class="metric-fill" style="width: {25 + hash(client['id']) % 40}"></div>
                            <span class="metric-text">{25 + hash(client['id']) % 40}%</span>
                        </div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Memory</div>
                        <div class="metric-bar">
                            <div class="metric-fill" style="width: {30 + hash(client['id']) % 50}"></div>
                            <span class="metric-text">{30 + hash(client['id']) % 50}%</span>
                        </div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Disk Usage</div>
                        <div class="metric-bar">
                            <div class="metric-fill" style="width: {20 + hash(client['id']) % 60}"></div>
                            <span class="metric-text">{20 + hash(client['id']) % 60}%</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
    return Markup(html)

__all__ = [
    "render_client_list",
    "render_client_item",
    "render_client_details"
]