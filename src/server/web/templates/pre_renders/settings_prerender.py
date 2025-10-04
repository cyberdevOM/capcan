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

def render_client_settings():
    """Render client settings HTML content. """
    html = """
    <div class="setting-group">
        <div class="setting-item">
            <div class="setting-info">
                <div class="setting-label">client settings 1</div>
                <div class="setting-description">Description for client setting 1.</div>
            </div>
            <div class="card-toggle-item">
                <label class="switch">
                    <input type="checkbox">
                    <span class="slider"></span>
                </label>
            </div>
        </div>
    </div>
    """
    return Markup(html)

def render_notification_settings():
    """Render notification settings HTML content."""
    html = """
    <div class="setting-group">
        <div class="setting-item">
            <div class="setting-info">
                <div class="setting-label">Email Notifications</div>
                <div class="setting-description">Enable or disable email notifications.</div>
            </div>
            <div class="card-toggle-item">
                <label class="switch">
                    <input type="checkbox">
                    <span class="slider"></span>
                </label>
            </div>
        </div>
    </div>
    """
    return Markup(html)

def render_security_settings():
    """Render security settings HTML content."""
    html = """
    <div class="setting-group">
        <div class="setting-item">
            <div class="setting-info">
                <div class="setting-label">Change Password</div>
                <div class="setting-description">Update your account password regularly to enhance security.</div>
            </div>
            <ul>
                <div class="card-toggle-item">
                    <div class="input-group">
                        <svg stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" class="icon">
                        <path d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" stroke-linejoin="round" stroke-linecap="round"></path>
                        </svg>
                        <input class="input" type="password" placeholder="Old Password">
                    </div>
                </div>
                <div class="card-toggle-item">
                    <div class="input-group">
                        <svg stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" class="icon">
                        <path d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" stroke-linejoin="round" stroke-linecap="round"></path>
                        </svg>
                        <input class="input" type="password" placeholder="New Password">
                    </div>
                </div>
                <div class="card-toggle-item">
                    <div class="input-group">
                        <svg stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" class="icon">
                        <path d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" stroke-linejoin="round" stroke-linecap="round"></path>
                        </svg>
                        <input class="input" type="password" placeholder="Confirm Password">
                    </div>
                </div>
            </ul>
        </div>
    </div>
    """
    return Markup(html) 