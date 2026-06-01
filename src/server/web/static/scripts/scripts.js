const userData = {
    isLoggedIn: false, // change to true if user is logged in
    username: 'Guest', // change to the actual username if logged in
    profilePicture: null // change to the actual profile picture URL if available
};

function setupProfileIcon(iconId, menuId) {
    const profileIcon = document.getElementById(iconId);
    const loginMenu = document.getElementById(menuId);

    if (!profileIcon) {
        console.error('Profile icon element not found');
        return;
    }

    if (userData.isLoggedIn) {
        // User is logged in
        if (userData.profilePicture) {
            profileIcon.className = 'profile-icon';
            profileIcon.style.backgroundImage = `url('${userData.profilePicture}')`;
            profileIcon.innerHTML = '';
        } else {
            // No profile picture available
            const initials = userData.username.split(' ')
                .map(word => word[0])
                .join('')
                .substring(0, 2);

            profileIcon.className = 'profile-icon';
            profileIcon.style.backgroundColor = ''; // Default background color
            profileIcon.style.color = ''; // Default text color
            profileIcon.style.backgroundImage = '';
            profileIcon.innerHTML = initials;
        }
        if (loginMenu) {
            loginMenu.style.display = 'none';
        }

        profileIcon.onclick = function () {
            window.location.href = '/settings'; // Redirect to profile page (change settings to profile once added)
        };
    } else {
        // User is not logged in
        profileIcon.className = 'profile-icon guest';
        profileIcon.style.backgroundImage = '';
        profileIcon.innerHTML = '<i class="fas fa-user-circle"></i>'; // Font Awesome icon

        if (loginMenu) {
            loginMenu.classList.remove('show');
        }

        profileIcon.onclick = function (e) {
            e.stopPropagation(); // Prevent event bubbling
            if (loginMenu) {
                loginMenu.classList.toggle('show');
            } else {
                console.error('Login menu element not found');
            }
        };

        document.addEventListener('click', function (e) {
            const profileContainer = document.querySelector('.profile-container');
            if (loginMenu && !profileContainer.contains(e.target)) {
                loginMenu.classList.remove('show');
            }
        });
    }
}

function initializeProfileIcon() {
    // Set up the profile icon for the top bar
    setupProfileIcon('topbarProfileIcon', 'topbarLoginMenu');
}

function initializeHamburgerMenu() {
    const hamburgerToggle = document.querySelector('.hamburger input[type="checkbox"]');
    const collapsedOptions = document.getElementById('collapsedOptions');

    // Ensure the hamburger toggle and collapsed options are present
    if (!hamburgerToggle || !collapsedOptions) {
        console.error('Element Not Found');
        return;
    }

    // Initialize the hamburger menu toggle
    hamburgerToggle.addEventListener('change', function () {
        if (this.checked) {
            collapsedOptions.classList.add('show');
        } else {
            collapsedOptions.classList.remove('show');
        }
    });

    // Close the hamburger menu when clicking outside of it
    document.addEventListener('click', function (e) {
        const hamburgerContainer = document.getElementById('topBarOptionsCollapsed');
        if (!hamburgerContainer.contains(e.target) && !collapsedOptions.contains(e.target)) {
            hamburgerToggle.checked = false;
            collapsedOptions.classList.remove('show');
        }
    });

    // Close the hamburger menu when clicking on a link
    const navItems = collapsedOptions.querySelectorAll('.mobile-icon-link');
    navItems.forEach(item => {
        item.addEventListener('click', function () {
            hamburgerToggle.checked = false;
            collapsedOptions.classList.remove('show');
        });
    });
}

function initializeMasonryLayout() {
    const grid = document.getElementById('TilesGrid');
    
    if (!grid) {
        console.log('No TilesGrid found');
        return;
    }

    // Skip if the container uses CSS Grid (dashboard uses CSS Grid now)
    if (getComputedStyle(grid).display === 'grid') {
        console.log('TilesGrid uses CSS Grid, skipping Masonry');
        return;
    }

    // Clear any existing grid sizers
    const existingSizers = grid.querySelectorAll('.grid-sizer');
    existingSizers.forEach(sizer => sizer.remove());

    // Add grid sizer
    const gridSizer = document.createElement('div');
    gridSizer.className = 'grid-sizer';
    grid.appendChild(gridSizer);

    // Wait for CSS to load then initialize
    setTimeout(() => {
        const masonry = new Masonry(grid, {
            itemSelector: '.modular-block',
            columnWidth: '.grid-sizer',
            gutter: 16,
            percentPosition: true,
            fitWidth: false
        });

        // Force layout
        setTimeout(() => {
            masonry.layout();
            console.log('Masonry layout complete');
        }, 100);

        // Store for debugging
        window.masonryInstance = masonry;
    }, 200);
}

function initializeSettings() {
    // Apply dark mode on every page, not just when the toggle exists
    const savedPreference = localStorage.getItem('darkMode') !== 'false';
    document.body.classList.toggle('dark-mode', savedPreference);

    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.checked = savedPreference;
        darkModeToggle.addEventListener('change', function () {
            document.body.classList.toggle('dark-mode', this.checked);
            localStorage.setItem('darkMode', this.checked);
        });
    }

    const themeOptions = document.querySelectorAll('.theme-option');
    themeOptions.forEach(option => {
        option.addEventListener('click', function () {
            // Remove active class from all options
            themeOptions.forEach(opt => opt.classList.remove('active'));

            // Add active class to the selected option
            this.classList.add('active');

            // Save theme preference
            const selectedTheme = this.dataset.theme;
            localStorage.setItem('colorTheme', selectedTheme);

            // Apply the selected theme
            console.log(`Theme changed to: ${selectedTheme}`);
        });
    });

    // load saved theme
    const savedTheme = localStorage.getItem('colorTheme') || 'blue';
    const savedThemeOption = document.querySelector(`[data-theme="${savedTheme}"]`);
    if (savedThemeOption) {
        themeOptions.forEach(opt => opt.classList.remove('active'));
        savedThemeOption.classList.add('active');
    }

    // Dashboard card toggles
    const cardToggles = document.querySelectorAll('[data-card]');
    cardToggles.forEach(toggle => {
        const cardName = toggle.dataset.card;

        // load saved state
        const isEnabled = localStorage.getItem(`card_${cardName}`) !== 'false'; // default to true
        toggle.checked = isEnabled;

        //save sate on change
        toggle.addEventListener('change', function () {
            localStorage.setItem(`card_${cardName}`, this.checked);
            console.log(`Card ${cardName} ${this.checked ? 'enabled' : 'disabled'}`);
        });
    });

    // Other settings controls
}

function changePassword() {
    console.log('changePassword — not yet implemented');
}

function saveDisplayName() {
    console.log('saveDisplayName — not yet implemented');
}

function saveEmail() {
    console.log('saveEmail — not yet implemented');
}


function initializeSettingsNav() {
    const navItems = document.querySelectorAll('.settings-nav-item');
    if (!navItems.length) return;

    function activatePanel(panelName) {
        const panel = document.getElementById('panel-' + panelName);
        if (!panel) return;
        navItems.forEach(n => n.classList.remove('active'));
        document.querySelectorAll('.settings-panel').forEach(p => p.classList.remove('active'));
        const navItem = document.querySelector(`.settings-nav-item[data-panel="${panelName}"]`);
        if (navItem) navItem.classList.add('active');
        panel.classList.add('active');
    }

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const target = item.dataset.panel;
            activatePanel(target);
            history.replaceState(null, '', '#' + target);
        });
    });

    // Activate panel from URL hash on load
    const hash = window.location.hash.replace('#', '');
    if (hash && document.getElementById('panel-' + hash)) {
        activatePanel(hash);
    }

    // Activate panel when hash changes (e.g. nav links clicked while already on settings page)
    window.addEventListener('hashchange', function () {
        const newHash = window.location.hash.replace('#', '');
        if (newHash && document.getElementById('panel-' + newHash)) {
            activatePanel(newHash);
        }
    });
}

function initializePasswordToggles() {
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.toggle-password');
        if (!btn) return;
        const input = document.getElementById(btn.dataset.target);
        if (!input) return;
        const isHidden = input.type === 'password';
        input.type = isHidden ? 'text' : 'password';
        const icon = btn.querySelector('i');
        if (icon) icon.className = isHidden ? 'fas fa-eye-slash' : 'fas fa-eye';
    });
}

// Initialize the profile icon when the page loads
document.addEventListener('DOMContentLoaded', function () {
    initializeProfileIcon(); // Profile icon functionality
    initializeHamburgerMenu(); // Hamburger menu functionality
    initializeMasonryLayout(); // Masonry layout for dashboard
    initializeSettings(); // Settings page functionality
    initializeSettingsNav(); // Settings sidebar navigation
    initializeDebugGrid(); // Debugging helpers
    initializePasswordToggles(); // Show/hide password buttons
    initializeDemoSettings(); // Demo mode selector (only active when panel exists)
    pollAlertCount();       // Notification badge — runs on every page
    pollCriticalAlerts();   // Toast banners for critical alerts — runs on every page
    pollDashboardTiles();   // Live dashboard tile updates (no-op if not on dashboard)
});

/// === DEMO MODE === ///

function initializeDemoSettings() {
    const selector = document.getElementById('demoModeSelector');
    if (!selector) return; // demo panel not rendered (server not started with --demo)

    refreshDemoStatus();

    selector.querySelectorAll('.demo-seg-btn').forEach(btn => {
        btn.addEventListener('click', () => setDemoMode(btn.dataset.mode));
    });
}

/**
 * Push a simulation mode to all active clients.
 * mode: 'false' | 'simulated' | 'script'
 */
function setDemoMode(mode) {
    const feedback  = document.getElementById('demoFeedback');
    const rateInput = document.getElementById('demoAlertRate');
    const alertRate = rateInput ? parseInt(rateInput.value, 10) : 20;

    if (feedback) { feedback.textContent = 'Saving\u2026'; feedback.style.color = 'var(--text-secondary)'; }

    const payload = { demo_mode: mode };
    // Include alert rate only when enabling simulated mode
    if (mode === 'simulated' && !isNaN(alertRate) && alertRate > 0) {
        payload.demo_alerts_per_hour = alertRate;
    }

    fetch('/api/v1/demo/push', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'ok') {
                if (feedback) { feedback.textContent = data.message; feedback.style.color = 'var(--success-color, #27ae60)'; }
                _applyDemoModeUI(mode);     // optimistic UI update
                refreshDemoStatus();
            } else {
                if (feedback) { feedback.textContent = data.error || 'Failed to update mode.'; feedback.style.color = 'var(--error-color, #e74c3c)'; }
            }
            if (feedback) setTimeout(() => { feedback.textContent = ''; }, 4000);
        })
        .catch(() => {
            if (feedback) { feedback.textContent = 'Request failed.'; feedback.style.color = 'var(--error-color, #e74c3c)'; setTimeout(() => { feedback.textContent = ''; }, 4000); }
        });
}

/** Update the segment highlight and show the matching info panel. */
function _applyDemoModeUI(mode) {
    // Highlight active segment
    const selector = document.getElementById('demoModeSelector');
    if (selector) {
        selector.querySelectorAll('.demo-seg-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });
    }
    // Show the relevant info panel, hide the others
    const panels = { simulated: 'demoInfoSynthetic', script: 'demoInfoScript' };
    Object.entries(panels).forEach(([m, id]) => {
        const el = document.getElementById(id);
        if (el) el.style.display = (mode === m) ? '' : 'none';
    });
}

function pushIntervalToAllClients() {
    const input = document.getElementById('heartbeatInterval');
    const feedback = document.getElementById('intervalFeedback');
    const minutes = parseInt(input?.value, 10);

    if (isNaN(minutes) || minutes < 1 || minutes > 60) {
        if (feedback) { feedback.textContent = 'Invalid interval (1–60 minutes).'; feedback.style.color = 'var(--error-color, #e74c3c)'; }
        return;
    }

    if (feedback) { feedback.textContent = 'Pushing…'; feedback.style.color = 'var(--text-secondary)'; }

    fetch('/api/v1/clients/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_ids: 'all', settings: { interval: minutes * 60 } }),
    })
        .then(r => r.json().then(data => ({ ok: r.ok, data })))
        .then(({ ok, data }) => {
            if (feedback) {
                if (ok) {
                    feedback.textContent = data.message || `Interval queued for all clients.`;
                    feedback.style.color = 'var(--success-color, #27ae60)';
                } else {
                    feedback.textContent = data.error || 'Failed to push interval.';
                    feedback.style.color = 'var(--error-color, #e74c3c)';
                }
                setTimeout(() => { feedback.textContent = ''; }, 4000);
            }
        })
        .catch(() => {
            if (feedback) { feedback.textContent = 'Request failed.'; feedback.style.color = 'var(--error-color, #e74c3c)'; setTimeout(() => { feedback.textContent = ''; }, 4000); }
        });
}

function pushDemoAlertRate() {
    const rateInput = document.getElementById('demoAlertRate');
    const feedback = document.getElementById('demoFeedback');
    const rate = parseInt(rateInput?.value, 10);

    if (isNaN(rate) || rate < 1) {
        if (feedback) { feedback.textContent = 'Invalid rate.'; feedback.style.color = 'var(--error-color, #e74c3c)'; }
        return;
    }

    if (feedback) { feedback.textContent = 'Applying\u2026'; feedback.style.color = 'var(--text-secondary)'; }

    fetch('/api/v1/demo/push', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ demo_alerts_per_hour: rate }),
    })
        .then(r => r.json())
        .then(data => {
            if (feedback) {
                feedback.textContent = data.status === 'ok' ? `Alert rate set to ${rate}/hr for ${data.queued} client(s).` : (data.error || 'Failed.');
                feedback.style.color = data.status === 'ok' ? 'var(--success-color, #27ae60)' : 'var(--error-color, #e74c3c)';
                setTimeout(() => { feedback.textContent = ''; }, 4000);
            }
        })
        .catch(() => {
            if (feedback) { feedback.textContent = 'Request failed.'; feedback.style.color = 'var(--error-color, #e74c3c)'; }
        });
}


function refreshDemoStatus() {
    const statusText = document.getElementById('demoStatusText');
    if (!statusText) return;

    fetch('/api/v1/demo/status')
        .then(r => r.json())
        .then(data => {
            if (data.error) { statusText.textContent = 'Unable to load status.'; return; }

            const { total_active_clients, modes, pending_changes } = data;

            // Determine the dominant active mode for the segment highlight
            let activeMode = 'false';
            if ((modes.simulated || 0) > 0 && (modes.script || 0) === 0) activeMode = 'simulated';
            else if ((modes.script || 0) > 0 && (modes.simulated || 0) === 0) activeMode = 'script';
            // If both are non-zero, leave as 'false' (mixed state — no segment highlighted)
            _applyDemoModeUI(activeMode);

            // Build human-readable status line
            const parts = [];
            if (modes.simulated > 0) parts.push(`${modes.simulated} simulated`);
            if (modes.script    > 0) parts.push(`${modes.script} script-based`);
            const activeStr  = parts.length ? parts.join(', ') : 'none';
            const pendingStr = pending_changes > 0 ? ` \u2014 ${pending_changes} pending check-in` : '';
            statusText.textContent =
                `${total_active_clients} active client(s) \u2014 demo active: ${activeStr}${pendingStr}`;
        })
        .catch(() => { statusText.textContent = 'Unable to load status.'; });
}

/// === DEBUGGING HELPERS === ///

let debugMenuVisible = false;

function initializeDebugGrid() {
    // Only enable debug in development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        document.body.classList.add('debug-mode');
        createDebugControls();
        createViewportInfo();
        setupDebugToggle();
    }
}
function setupDebugToggle() {
    document.addEventListener('keydown', function(e) {
        // Press Ctrl+Shift+D to toggle debug menu
        if (e.ctrlKey && e.shiftKey && e.code === 'KeyD') {
            e.preventDefault();
            toggleDebugMenu();
        }
    });
}

function toggleDebugMenu() {
    const debugControls = document.querySelector('.debug-controls');
    const viewportInfo = document.querySelector('.viewport-info');
    
    debugMenuVisible = !debugMenuVisible;
    
    if (debugMenuVisible) {
        debugControls?.classList.add('visible');
        viewportInfo?.classList.add('visible');
        console.log('🔧 Debug menu enabled (Ctrl+Shift+D to toggle)');
    } else {
        debugControls?.classList.remove('visible');
        viewportInfo?.classList.remove('visible');
        // Also disable any active debug modes
        document.body.classList.remove('debug-grid');
        document.querySelectorAll('.debug-controls button.active').forEach(btn => {
            btn.classList.remove('active');
        });
        console.log('🔧 Debug menu disabled');
    }
}

function createDebugControls() {
    const debugControls = document.createElement('div');
    debugControls.className = 'debug-controls';
    
    // Get current page name
    const pageName = document.title.split(' - ')[0] || 'Unknown';
    
    debugControls.innerHTML = `
        <h4>DEBUG (${pageName})</h4>
        <button id="toggleGridDebug">Grid</button>
        <button id="toggleMasonryDebug">Order</button>
        <button id="showGridSizes">Sizes</button>
        <button id="highlightOverflow">Overflow</button>
        <button id="showBreakpoints">BP</button>
    `;
    
    document.body.appendChild(debugControls);

    // Event listeners
    document.getElementById('toggleGridDebug').addEventListener('click', toggleGridDebug);
    document.getElementById('toggleMasonryDebug').addEventListener('click', toggleMasonryDebug);
    document.getElementById('showGridSizes').addEventListener('click', logGridSizes);
    document.getElementById('highlightOverflow').addEventListener('click', highlightOverflow);
    document.getElementById('showBreakpoints').addEventListener('click', showBreakpoints);
}

function createViewportInfo() {
    const viewportInfo = document.createElement('div');
    viewportInfo.className = 'viewport-info';
    document.body.appendChild(viewportInfo);
    
    updateViewportInfo();
    window.addEventListener('resize', updateViewportInfo);
}

function updateViewportInfo() {
    const info = document.querySelector('.viewport-info');
    if (info) {
        const gridContainer = document.getElementById('TilesGrid') || 
                             document.querySelector('.dashboard-tiles') || 
                             document.querySelector('.settings-grid') ||
                             document.querySelector('.client-container');
        
        const blockCount = document.querySelectorAll('.modular-block').length;
        
        info.innerHTML = `
            ${window.innerWidth}×${window.innerHeight}<br>
            ${getCurrentBreakpoint()}<br>
            ${getGridColumns()}<br>
            ${blockCount} blocks<br>
            ${gridContainer ? 'Grid: ✓' : 'Grid: ✗'}
        `;
    }
}

function getCurrentBreakpoint() {
    const width = window.innerWidth;
    if (width <= 400) return 'XS (≤400px)';
    if (width <= 600) return 'SM (≤600px)';
    if (width <= 900) return 'MD (≤900px)';
    if (width <= 1200) return 'LG (≤1200px)';
    if (width <= 1440) return 'XL (≤1440px)';
    return 'XXL (>1440px)';
}

function getGridColumns() {
    const width = window.innerWidth;
    if (width <= 400) return '1 col';
    if (width <= 600) return '2 col';
    if (width <= 900) return '3 col';
    if (width <= 1200) return '4 col';
    return '5 col';
}

function toggleGridDebug() {
    const body = document.body;
    const button = document.getElementById('toggleGridDebug');
    
    if (body.classList.contains('debug-grid')) {
        body.classList.remove('debug-grid');
        button.classList.remove('active');
    } else {
        body.classList.add('debug-grid');
        button.classList.add('active');
    }
}

function toggleMasonryDebug() {
    // Find the actual grid container that exists on this page
    const container = document.getElementById('TilesGrid') || 
                     document.querySelector('.dashboard-tiles') || 
                     document.querySelector('.settings-grid');
    
    const button = document.getElementById('toggleMasonryDebug');
    
    if (!container) {
        console.log('No grid container found on this page');
        return;
    }
    
    const items = container.querySelectorAll('.modular-block');
    
    if (items.length === 0) {
        console.log('No modular blocks found');
        return;
    }
    
    items.forEach((item, index) => {
        if (item.dataset.debugIndex) {
            delete item.dataset.debugIndex;
        } else {
            item.dataset.debugIndex = index + 1;
        }
    });
    
    button.classList.toggle('active');
    console.log(`Masonry debug toggled for ${items.length} blocks`);
}

function logGridSizes() {
    const blocks = document.querySelectorAll('.modular-block');
    
    if (blocks.length === 0) {
        console.log('No modular blocks found on this page');
        return;
    }
    
    console.group('🔍 Grid Analysis');
    console.log(`Found ${blocks.length} blocks on current page`);
    
    blocks.forEach((block, index) => {
        const rect = block.getBoundingClientRect();
        const sizeClass = Array.from(block.classList)
            .find(cls => cls.startsWith('modular-block-')) || 'unknown';
        
        console.log(`Block ${index + 1}:`, {
            class: sizeClass,
            size: `${rect.width.toFixed(0)}×${rect.height.toFixed(0)}px`,
            percent: `${((rect.width / window.innerWidth) * 100).toFixed(1)}%`,
            title: block.querySelector('.modular-block-title')?.textContent || 'No title'
        });
    });
    
    console.groupEnd();
}

function highlightOverflow() {
    const button = document.getElementById('highlightOverflow');
    
    if (button.classList.contains('active')) {
        document.querySelectorAll('[data-overflow-debug]').forEach(el => {
            el.style.removeProperty('outline');
            delete el.dataset.overflowDebug;
        });
        button.classList.remove('active');
    } else {
        document.querySelectorAll('*').forEach(el => {
            if (el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight) {
                el.style.outline = '2px solid red';
                el.dataset.overflowDebug = 'true';
            }
        });
        button.classList.add('active');
    }
}

function showBreakpoints() {
    const breakpoints = [400, 600, 900, 1200, 1440];
    const button = document.getElementById('showBreakpoints');
    
    // Remove existing lines
    document.querySelectorAll('.breakpoint-line').forEach(line => line.remove());
    
    if (button.classList.contains('active')) {
        button.classList.remove('active');
        return;
    }
    
    breakpoints.forEach((bp, i) => {
        const line = document.createElement('div');
        line.className = 'breakpoint-line';
        line.style.cssText = `
            position: fixed;
            left: ${bp}px;
            top: 0;
            width: 1px;
            height: 100vh;
            background: rgba(255, ${i * 50}, 0, 0.6);
            z-index: 9999;
            pointer-events: none;
        `;
        
        const label = document.createElement('div');
        label.style.cssText = `
            position: absolute;
            top: 5px;
            left: 2px;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 1px 3px;
            font-size: 9px;
            border-radius: 2px;
            font-family: monospace;
        `;
        label.textContent = `${bp}`;
        line.appendChild(label);
        
        document.body.appendChild(line);
    });
    
    button.classList.add('active');
}

// ========================================================
// ALERT SYSTEM
// ========================================================

// ---- State ----
let all_alerts = [];
let selected_alert_id = null;

// ---- Nav badge polling ----
let last_alert_count = -1; // -1 = not yet known

function pollAlertCount() {
    function fetchCount() {
        fetch('/api/v1/web/alerts/count')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data) return;
                const n = data.unresolved > 0 ? data.unresolved : 0;

                // Update nav badge
                const badge = document.getElementById('alertBadge');
                if (badge) {
                    if (n > 0) {
                        badge.textContent = n > 99 ? '99+' : n;
                        badge.style.display = 'inline-block';
                    } else {
                        badge.style.display = 'none';
                    }
                }

                // If the count has risen since last check, immediately surface new alerts
                if (last_alert_count >= 0 && n > last_alert_count) {
                    // Trigger toast check and dashboard tile refresh right away
                    if (typeof fetch_critical_now === 'function') fetch_critical_now();
                    if (typeof refresh_dashboard_now === 'function') refresh_dashboard_now();
                }
                last_alert_count = n;
            })
            .catch(() => {});
    }
    fetchCount();
    setInterval(fetchCount, 5000); // 5s heartbeat — lightweight count only
}

// ---- Alerts page init ----
function initAlerts(preselectedId) {
    const list = document.getElementById('alertList');
    if (!list) return; // not on alerts page
    loadAlerts().then(() => {
        if (preselectedId) selectAlert(preselectedId);
    });
}

function loadAlerts() {
    return fetch('/api/v1/web/alerts?limit=500')
        .then(r => r.ok ? r.json() : { alerts: [] })
        .then(data => {
            all_alerts = data.alerts || [];
            filterAlerts(); // apply current filter state to fresh data
        })
        .catch(() => {
            all_alerts = [];
            renderAlertList([]);
        });
}

function filterAlerts() {
    const q        = (document.getElementById('alertSearch')?.value || '').toLowerCase();
    const severity = document.getElementById('alertSeverityFilter')?.value || '';
    const status   = document.getElementById('alertStatusFilter')?.value || '';

    const filtered = all_alerts.filter(a => {
        if (severity && a.severity !== severity) return false;
        if (status   && a.status   !== status)   return false;
        if (q) {
            const haystack = [a.event_type, a.hostname, a.client_id, a.severity, a.status]
                .filter(Boolean).join(' ').toLowerCase();
            if (!haystack.includes(q)) return false;
        }
        return true;
    });
    renderAlertList(filtered);
}

function renderAlertList(alerts) {
    const list = document.getElementById('alertList');
    if (!list) return;

    if (!alerts.length) {
        list.innerHTML = '<div class="alert-list-placeholder">No alerts found.</div>';
        return;
    }

    list.innerHTML = alerts.map(a => `
        <div class="alert-item sev-${a.severity || 'undefined'}${a.alert_id === selected_alert_id ? ' selected' : ''}"
             id="alert-item-${a.alert_id}"
             onclick="selectAlert('${a.alert_id}')">
            <div class="alert-item-header">
                <span class="alert-item-title">${escapeHtml(a.event_type || 'Unknown event')}</span>
                <span class="severity-badge severity-${a.severity || 'undefined'}">${a.severity || '?'}</span>
            </div>
            <div class="alert-item-meta">
                <span>${escapeHtml(a.hostname || a.client_id || '—')}</span>
                <span>·</span>
                <span class="status-badge status-${a.status || 'unresolved'}">${a.status || 'unresolved'}</span>
                <span>·</span>
                <span>${relativeTime(a.created_at)}</span>
            </div>
        </div>
    `).join('');
}

function selectAlert(alertId) {
    selected_alert_id = alertId;
    document.querySelectorAll('.alert-item').forEach(el => {
        el.classList.toggle('selected', el.id === 'alert-item-' + alertId);
    });

    const alert = all_alerts.find(a => a.alert_id === alertId);
    if (!alert) return;

    const panel = document.getElementById('alertDetailPanel');
    if (!panel) return;

    let detailsHtml = '';
    if (alert.details) {
        let parsed;
        try { parsed = typeof alert.details === 'string' ? JSON.parse(alert.details) : alert.details; }
        catch(e) { parsed = alert.details; }
        detailsHtml = `
            <div class="alert-details-section">
                <h4>Details</h4>
                <pre class="alert-details-pre">${escapeHtml(JSON.stringify(parsed, null, 2))}</pre>
            </div>`;
    }

    const role = window.CAPCAN_USER_ROLE || 'read-only';
    const can_act = role !== 'read-only';

    const can_ack  = can_act && alert.status === 'unresolved';
    const can_res  = can_act && alert.status === 'acknowledged'; // must acknowledge first

    panel.innerHTML = `
        <div class="alert-detail-header">
            <div class="alert-detail-header-main">
                <i class="fas fa-bell"></i>
                <div>
                    <h2 class="alert-detail-title">${escapeHtml(alert.event_type || 'Unknown event')}</h2>
                    <div class="alert-detail-badges">
                        <span class="severity-badge severity-${alert.severity || 'undefined'}">${alert.severity || 'undefined'}</span>
                        <span class="status-badge status-${alert.status || 'unresolved'}">${alert.status || 'unresolved'}</span>
                    </div>
                </div>
            </div>
            <div class="alert-detail-actions">
                <button class="alert-btn alert-btn-ack" ${can_ack ? '' : 'disabled'}
                        onclick="acknowledgeAlert('${alert.alert_id}')">
                    <i class="fas fa-check-circle"></i> Acknowledge
                </button>
                <button class="alert-btn alert-btn-resolve" ${can_res ? '' : 'disabled'}
                        onclick="resolveAlert('${alert.alert_id}')">
                    <i class="fas fa-check-double"></i> Resolve
                </button>
            </div>
        </div>
        <div class="alert-info-grid">
            <div class="alert-info-card">
                <div class="alert-info-label">Alert ID</div>
                <div class="alert-info-value" style="font-size:0.78rem">${escapeHtml(alert.alert_id)}</div>
            </div>
            <div class="alert-info-card">
                <div class="alert-info-label">Client</div>
                <div class="alert-info-value">${escapeHtml(alert.hostname || alert.client_id || '—')}</div>
            </div>
            <div class="alert-info-card">
                <div class="alert-info-label">Score</div>
                <div class="alert-info-value">${alert.score != null ? alert.score : '—'}</div>
            </div>
            <div class="alert-info-card">
                <div class="alert-info-label">Rule ID</div>
                <div class="alert-info-value">${escapeHtml(alert.rule_id || '—')}</div>
            </div>
            <div class="alert-info-card">
                <div class="alert-info-label">Created</div>
                <div class="alert-info-value">${alert.created_at ? new Date(alert.created_at).toLocaleString() : '—'}</div>
            </div>
            <div class="alert-info-card">
                <div class="alert-info-label">Acknowledged by</div>
                <div class="alert-info-value">${alert.acknowledged_by ? escapeHtml(alert.acknowledged_by) : '—'}</div>
            </div>
            ${alert.tags && alert.tags.length ? `
            <div class="alert-info-card">
                <div class="alert-info-label">Tags</div>
                <div class="alert-info-value">${(Array.isArray(alert.tags) ? alert.tags : [alert.tags]).map(t => escapeHtml(t)).join(', ')}</div>
            </div>` : ''}
        </div>
        ${detailsHtml}`;
}

function acknowledgeAlert(alertId) {
    fetch(`/api/v1/web/alerts/${alertId}/acknowledge`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.error) { alert('Error: ' + data.error); return; }
            loadAlerts().then(() => selectAlert(alertId));
            pollAlertCount();
        })
        .catch(e => alert('Request failed: ' + e));
}

function resolveAlert(alertId) {
    fetch(`/api/v1/web/alerts/${alertId}/resolve`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.error) { alert('Error: ' + data.error); return; }
            loadAlerts().then(() => selectAlert(alertId));
            pollAlertCount();
        })
        .catch(e => alert('Request failed: ' + e));
}

// ---- Helpers ----
function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function relativeTime(isoStr) {
    if (!isoStr) return '—';
    const diff = Math.floor((Date.now() - new Date(isoStr)) / 1000);
    if (diff < 60)   return diff + 's ago';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400)return Math.floor(diff / 3600) + 'h ago';
    return Math.floor(diff / 86400) + 'd ago';
}

// ── Critical Alert Toast Banners ────────────────────────────────────────────

// In-memory only — no sessionStorage, so new alerts always surface during a session.
const toast_seen = new Set();
// True until the first fetch completes; used to age-gate startup toasts.
let toast_first_fetch = true;

function toast_sev_class(sev) {
    const map = { critical:'', high:'toast-high', medium:'toast-medium',
                  low:'toast-low', info:'toast-info' };
    return map[sev] || '';
}

function showAlertToast(alert) {
    const container = document.getElementById('alertToastContainer');
    if (!container) return;

    const sev      = (alert.severity || 'critical').toLowerCase();
    const sev_class = toast_sev_class(sev);
    const event    = escapeHtml(alert.event_type || 'Unknown event');
    const host     = escapeHtml(alert.hostname || alert.client_id || '?');
    const id       = alert.alert_id;
    const status   = alert.status || 'unresolved';

    const toast = document.createElement('div');
    toast.className = `alert-toast ${sev_class}`;
    toast.dataset.alertId = id;

    const canAck = status === 'unresolved';
    const canRes = status === 'acknowledged';

    toast.innerHTML = `
        <div class="alert-toast-header">
            <span class="alert-toast-sev">${escapeHtml(sev)}</span>
            <button class="alert-toast-close" title="Dismiss"><i class="fas fa-times"></i></button>
        </div>
        <div class="alert-toast-event">${event}</div>
        <div class="alert-toast-host">${host}</div>
        <div class="alert-toast-actions">
            ${canAck ? `<button class="alert-toast-btn alert-toast-btn-ack" data-id="${id}"><i class="fas fa-check-circle"></i> Ack</button>` : ''}
            ${canRes ? `<button class="alert-toast-btn alert-toast-btn-resolve" data-id="${id}"><i class="fas fa-check-double"></i> Resolve</button>` : ''}
        </div>
        <div class="alert-toast-progress"></div>
    `;

    toast.querySelector('.alert-toast-close').addEventListener('click', () => {
        dismiss_toast(toast);
    });

    const ackBtn = toast.querySelector('.alert-toast-btn-ack');
    if (ackBtn) ackBtn.addEventListener('click', () => {
        fetch(`/api/v1/web/alerts/${id}/acknowledge`, { method: 'POST' })
            .then(r => r.ok ? r.json() : null)
            .then(() => dismiss_toast(toast))
            .catch(() => {});
    });

    const resBtn = toast.querySelector('.alert-toast-btn-resolve');
    if (resBtn) resBtn.addEventListener('click', () => {
        fetch(`/api/v1/web/alerts/${id}/resolve`, { method: 'POST' })
            .then(r => r.ok ? r.json() : null)
            .then(() => dismiss_toast(toast))
            .catch(() => {});
    });

    container.appendChild(toast);

    const timer = setTimeout(() => dismiss_toast(toast), 10000);
    toast.dismiss_timer = timer;
}

function dismiss_toast(toast) {
    clearTimeout(toast.dismiss_timer);
    toast.style.transition = 'opacity 0.3s, transform 0.3s';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(60px)';
    setTimeout(() => toast.remove(), 320);
}

function pollCriticalAlerts() {
    function fetchCritical() {
        fetch('/api/v1/web/alerts?severity=critical&status=unresolved&limit=20')
            .then(r => r.ok ? r.json() : { alerts: [] })
            .then(data => {
                const now = Date.now();
                const is_first = toast_first_fetch;
                toast_first_fetch = false;

                (data.alerts || []).forEach(a => {
                    const id = a.alert_id;
                    if (toast_seen.has(id)) return;

                    // On the very first fetch, only surface alerts created in the last 5 min
                    // to avoid spamming toasts for a backlog of old alerts on page load.
                    if (is_first && a.created_at) {
                        const ageSec = (now - new Date(a.created_at).getTime()) / 1000;
                        if (ageSec > 300) {
                            toast_seen.add(id); // silently mark seen
                            return;
                        }
                    }

                    toast_seen.add(id);
                    showAlertToast(a);
                });
            })
            .catch(() => {});
    }
    // Expose so pollAlertCount can trigger an immediate check on count rise
    window.fetch_critical_now = fetchCritical;
    fetchCritical();
    setInterval(fetchCritical, 15000); // poll every 15s as a fallback
}


// ── Live Dashboard Tile Polling ──────────────────────────────────────────────

function pollDashboardTiles() {
    const grid = document.getElementById('TilesGrid');
    if (!grid) return; // not on the dashboard page

    // Map tile API key → element ID (title with spaces replaced by hyphens)
    const TILE_MAP = {
        quickstats:      'Quick-Stats',
        recent_activity: 'Recent-Activity',
        system_health:   'System-Health',
        network_status:  'Network-Status',
        alerts:          'Alerts',
    };

    function updateTiles() {
        fetch('/api/v1/web/dashboard/tiles')
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (!data) return;
                Object.entries(TILE_MAP).forEach(([key, elId]) => {
                    const tile = document.getElementById(elId);
                    if (!tile || !data[key]) return;
                    const content = tile.querySelector('.modular-block-content');
                    if (content) content.innerHTML = data[key];
                });
            })
            .catch(() => {});
    }

    // Expose so pollAlertCount can trigger an immediate refresh on count rise
    window.refresh_dashboard_now = updateTiles;

    // First update after a short delay (let the page settle), then every 30s
    setTimeout(updateTiles, 5000);
    setInterval(updateTiles, 30000);
}
