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
    """Render the demo mode settings panel with a three-way mode selector."""
    html = """
    <div class="settings-section">
        <h3 class="settings-section-title">Demo Mode</h3>
        <div class="setting-item">
            <div class="setting-info">
                <div class="setting-label">Simulation Mode</div>
                <div class="setting-description">
                    Choose how demo mode operates across all active clients.
                    Changes are queued and applied on each client&rsquo;s next check-in.
                </div>
            </div>
            <div class="setting-control">
                <div class="demo-mode-selector" id="demoModeSelector">
                    <button class="demo-seg-btn active" data-mode="false">
                        <i class="fas fa-power-off"></i> Off
                    </button>
                    <button class="demo-seg-btn" data-mode="simulated">
                        <i class="fas fa-flask"></i> Simulated
                    </button>
                    <button class="demo-seg-btn" data-mode="script">
                        <i class="fas fa-terminal"></i> Script
                    </button>
                </div>
            </div>
        </div>
        <div class="setting-item">
            <div class="setting-info">
                <div class="setting-label">Demo Alert Rate</div>
                <div class="setting-description">
                    Synthetic alerts per hour (Simulated mode only).
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
                <div class="setting-description" id="demoStatusText">Loading&hellip;</div>
            </div>
            <div class="setting-control">
                <button class="settings-btn settings-btn-secondary" onclick="refreshDemoStatus()">
                    <i class="fas fa-sync-alt"></i> Refresh
                </button>
            </div>
        </div>
        <span class="settings-feedback" id="demoFeedback"></span>
    </div>

    <!-- Mode description panels — shown/hidden by JS based on selected mode -->

    <div class="settings-section" id="demoInfoSynthetic" style="display: none;">
        <h3 class="settings-section-title">About Simulated Mode</h3>
        <p class="settings-placeholder-sub" style="padding: 0 0.25rem;">
            Simulated mode replaces live telemetry with realistic synthetic data and
            generates random security alerts at the configured rate. No real system data
            is collected. Ideal for UI demonstrations without exposing real infrastructure.
            The setting is queued and applied on each client&rsquo;s next check-in.
        </p>
    </div>

    <div class="settings-section" id="demoInfoScript" style="display: none;">
        <h3 class="settings-section-title">Script Attack Simulation</h3>
        <p class="settings-placeholder-sub" style="padding: 0 0.25rem 0.4rem;">
            In script mode, clients collect <strong>real telemetry</strong> from the host
            OS &mdash; no synthetic data is generated. The <code>demo_attack_sim</code>
            binary must be running on each target client to produce live CPU spikes, disk
            writes, file-integrity events, suspicious process names, and rogue TCP
            listeners that the security watchers will detect and report as real alerts.
        </p>
        <p class="settings-placeholder-sub" style="padding: 0 0.25rem 0.4rem;">
            Run all scenarios for 60 seconds on the target host:
        </p>
        <pre class="demo-script-cmd">./demo_attack_sim --all --duration 60</pre>
        <p class="settings-placeholder-sub" style="padding: 0.4rem 0.25rem 0;">
            The binary is bundled inside demo client packages (built with
            <code>build_client.sh --demo</code>). Remote triggering from this dashboard
            is planned for a future release.
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
 