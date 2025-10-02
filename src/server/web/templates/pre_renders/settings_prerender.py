from markupsafe import Markup

def render_dashboard_settings():
    """Render the dashboard settings HTML content."""
    html = """
    <div class="setting-group">
        <div class="card-toggle-grid">
            <ul class="settings-list">
                <li class="card-toggle-item">
                    <span> Recent Activity </span>
                    <label class="switch">
                        <input type="checkbox">
                        <span class="slider"></span>
                    </label>
                </li>
                <li class="card-toggle-item">
                    <span> System Health </span>
                    <label class="switch">
                        <input type="checkbox">
                        <span class="slider"></span>
                    </label>
                </li>
                <li class="card-toggle-item">
                    <span> Quick Stats </span>
                    <label class="switch">
                        <input type="checkbox">
                        <span class="slider"></span>
                    </label>
                </li>
                <li class="card-toggle-item">
                    <span> Network Status </span>
                    <label class="switch">
                        <input type="checkbox">
                        <span class="slider"></span>
                    </label>
                </li>
                <li class="card-toggle-item">
                    <span> Alerts </span>
                    <label class="switch">
                        <input type="checkbox">
                        <span class="slider"></span>
                    </label>
                </li>
            </ul>
        </div>
    </div>
    """
    return Markup(html)

def render_appearance_settings():
    """Render the appearance settings HTML content."""
    html = """
    <div class="setting-group">
        <div class="setting-item">
            <div class="setting-info">
                <div class="setting-label">Dark Mode</div>
                <div class="setting-description">Switch between light and dark themes.</div>
            </div>
            <div class="card-toggle-item">
                <label class="switch">
                    <input type="checkbox">
                    <span class="slider"></span>
                </label>
            </div>
        </div>

        <div class="setting-item">
            <div class="setting-info">
                <div class="setting-label">Color Theme</div>
                <div class="setting-description">Choose your preferred color theme.</div>
            </div>
            <div class="card-toggle-item">
                <div class="theme-picker">
                    <div class="theme-option theme-blue active" data-theme="blue"></div>
                    <div class="theme-option theme-green" data-theme="green"></div>
                    <div class="theme-option theme-purple" data-theme="purple"></div>
                    <div class="theme-option theme-orange" data-theme="orange"></div>
                </div>
            </div>
        </div>
    </div>
    """
    return Markup(html)