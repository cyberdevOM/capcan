from markupsafe import Markup

def render_account_settings():
    """Render the change-password section. Profile fields are rendered in Jinja."""
    html = """
    <div class="setting-item">
        <div class="setting-info">
            <div class="setting-label">Change Password</div>
            <div class="setting-description">Update your account password regularly to enhance security.</div>
        </div>
    </div>
    <div class="password-change-form">
        <div class="input-group">
            <svg stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" class="icon">
                <path d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" stroke-linejoin="round" stroke-linecap="round"></path>
            </svg>
            <input class="input" type="password" id="oldPassword" placeholder="Current password">
            <button type="button" class="toggle-password" data-target="oldPassword" title="Show/Hide Password">
                <i class="fas fa-eye"></i>
            </button>
        </div>
        <div class="input-group">
            <svg stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" class="icon">
                <path d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" stroke-linejoin="round" stroke-linecap="round"></path>
            </svg>
            <input class="input" type="password" id="newPassword" placeholder="New password">
            <button type="button" class="toggle-password" data-target="newPassword" title="Show/Hide Password">
                <i class="fas fa-eye"></i>
            </button>
        </div>
        <div class="input-group">
            <svg stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" class="icon">
                <path d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" stroke-linejoin="round" stroke-linecap="round"></path>
            </svg>
            <input class="input" type="password" id="confirmPassword" placeholder="Confirm password">
        </div>
        <button class="settings-btn settings-btn-primary" onclick="changePassword()">Update Password</button>
        <span class="settings-feedback" id="passwordFeedback"></span>
    </div>
    """
    return Markup(html)


def render_client_settings():
    """Render client configuration settings."""
    html = """
    <div class="setting-item">
        <div class="setting-info">
            <div class="setting-label">Telemetry Report Interval (minutes)</div>
            <div class="setting-description">How often clients collect and send telemetry data to the server. Default is 5 minutes.</div>
        </div>
        <div class="setting-control" style="gap: 0.5rem; display: flex; align-items: center;">
            <input type="number" class="settings-number-input" value="5" min="1" max="60" id="heartbeatInterval">
            <button class="settings-btn settings-btn-primary" onclick="pushIntervalToAllClients()">Push to All Clients</button>
        </div>
    </div>
    <span class="settings-feedback" id="intervalFeedback"></span>
    <div class="setting-item">
        <div class="setting-info">
            <div class="setting-label">Connection Timeout</div>
            <div class="setting-description">Mark a client offline after this many missed telemetry reports.</div>
        </div>
        <div class="setting-control">
            <input type="number" class="settings-number-input" value="3" min="1" max="10" id="connectionTimeout">
        </div>
    </div>
    <div class="setting-item">
        <div class="setting-info">
            <div class="setting-label">Auto-approve Registrations</div>
            <div class="setting-description">Automatically approve new client registration requests.</div>
        </div>
        <div class="setting-control">
            <label class="switch">
                <input type="checkbox" id="autoApprove">
                <span class="slider"></span>
            </label>
        </div>
    </div>
    """
    return Markup(html)


def render_configs_settings():
    """Render config management settings."""
    html = """
    <div class="settings-placeholder">
        <i class="fas fa-file-code settings-placeholder-icon"></i>
        <p class="settings-placeholder-text">Config management coming soon.</p>
        <p class="settings-placeholder-sub">You will be able to create, edit, and push configurations to client groups from here.</p>
    </div>
    """
    return Markup(html)


def render_demo_settings():
    """Render the demo mode settings panel."""
    html = """
    <div class="settings-section">
        <h3 class="settings-section-title">Demo Mode</h3>
        <div class="setting-item">
            <div class="setting-info">
                <div class="setting-label">Enable Demo Mode on Clients</div>
                <div class="setting-description">
                    Push demo mode to all active clients. When enabled, clients send
                    synthetic telemetry data instead of real system metrics. Useful for
                    presentations and UI demonstrations.
                </div>
            </div>
            <div class="setting-control">
                <label class="switch">
                    <input type="checkbox" id="demoModeToggle">
                    <span class="slider"></span>
                </label>
            </div>
        </div>
        <div class="setting-item">
            <div class="setting-info">
                <div class="setting-label">Demo Alert Rate</div>
                <div class="setting-description">
                    Number of synthetic alerts submitted per hour while demo mode is active.
                </div>
            </div>
            <div class="setting-control" style="gap: 0.5rem; display: flex; align-items: center;">
                <input type="number" id="demoAlertRate" class="settings-number-input"
                       min="1" max="120" value="20">
                <span class="setting-description">/ hr</span>
                <button class="settings-btn settings-btn-secondary" onclick="pushDemoAlertRate()">Apply Rate</button>
            </div>
        </div>
        <div class="setting-item">
            <div class="setting-info">
                <div class="setting-label">Client Status</div>
                <div class="setting-description" id="demoStatusText">Loading…</div>
            </div>
            <div class="setting-control">
                <button class="settings-btn settings-btn-secondary" onclick="refreshDemoStatus()">
                    <i class="fas fa-sync-alt"></i> Refresh
                </button>
            </div>
        </div>
        <span class="settings-feedback" id="demoFeedback"></span>
    </div>

    <div class="settings-section">
        <h3 class="settings-section-title">About Demo Mode</h3>
        <p class="settings-placeholder-sub" style="padding: 0 0.25rem;">
            Demo mode replaces live telemetry with realistic synthetic data, allowing
            you to showcase the dashboard without exposing real infrastructure metrics.
            Toggling demo mode queues a settings update that each client applies on its
            next telemetry cycle. Clients that are currently offline will receive the
            update when they next check in.
        </p>
    </div>
    """
    return Markup(html)


def render_web_settings():
    """Render web/appearance settings."""
    html = """
    <div class="settings-section">
        <h3 class="settings-section-title">Appearance</h3>
        <div class="setting-item">
            <div class="setting-info">
                <div class="setting-label">Dark Mode</div>
                <div class="setting-description">Switch between light and dark themes.</div>
            </div>
            <div class="setting-control">
                <label class="switch">
                    <input type="checkbox" id="darkModeToggle">
                    <span class="slider"></span>
                </label>
            </div>
        </div>
        <div class="setting-item">
            <div class="setting-info">
                <div class="setting-label">Colour Theme</div>
                <div class="setting-description">Choose your preferred accent colour.</div>
            </div>
            <div class="setting-control">
                <div class="theme-picker">
                    <div class="theme-option theme-blue active" data-theme="blue" title="Blue"></div>
                    <div class="theme-option theme-green" data-theme="green" title="Green"></div>
                    <div class="theme-option theme-purple" data-theme="purple" title="Purple"></div>
                    <div class="theme-option theme-orange" data-theme="orange" title="Orange"></div>
                </div>
            </div>
        </div>
    </div>

    <div class="settings-section">
        <h3 class="settings-section-title">Dashboard Cards</h3>
        <div class="card-toggle-grid">
            <div class="card-toggle-item">
                <span>Recent Activity</span>
                <label class="switch">
                    <input type="checkbox" data-card="recent_activity" checked>
                    <span class="slider"></span>
                </label>
            </div>
            <div class="card-toggle-item">
                <span>System Health</span>
                <label class="switch">
                    <input type="checkbox" data-card="system_health" checked>
                    <span class="slider"></span>
                </label>
            </div>
            <div class="card-toggle-item">
                <span>Quick Stats</span>
                <label class="switch">
                    <input type="checkbox" data-card="quick_stats" checked>
                    <span class="slider"></span>
                </label>
            </div>
            <div class="card-toggle-item">
                <span>Network Status</span>
                <label class="switch">
                    <input type="checkbox" data-card="network_status" checked>
                    <span class="slider"></span>
                </label>
            </div>
            <div class="card-toggle-item">
                <span>Alerts</span>
                <label class="switch">
                    <input type="checkbox" data-card="alerts" checked>
                    <span class="slider"></span>
                </label>
            </div>
        </div>
    </div>

    <div class="settings-section">
        <h3 class="settings-section-title">Notifications</h3>
        <div class="setting-item">
            <div class="setting-info">
                <div class="setting-label">Email Notifications</div>
                <div class="setting-description">Receive email alerts for critical events.</div>
            </div>
            <div class="setting-control">
                <label class="switch">
                    <input type="checkbox" id="emailNotifications">
                    <span class="slider"></span>
                </label>
            </div>
        </div>
    </div>
    """
    return Markup(html)
 