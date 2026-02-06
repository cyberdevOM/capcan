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
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        // Load saved preference - future impl
        darkModeToggle.addEventListener('change', function () {
            document.body.classList.toggle('dark-mode', this.checked)
            localStorage.setItem('darkMode', this.checked);
        });

        const savedPreference = localStorage.getItem('darkMode') === 'true';
        darkModeToggle.checked = savedPreference;
        document.body.classList.toggle('dark-mode', savedPreference);
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

function selectClient(clientId) {
    document.querySelectorAll('.client-item').forEach(item => {
        item.classList.remove('selected');
    });

    // Add selected class to the clicked client
    const selectedItem = document.querySelector(`[data-client-id="${clientId}"]`);
    if (selectedItem) {
        selectedItem.classList.add('selected');
    }

    // load client Details - future impl
}

function connectClient(clientId) {
    console.log(`Connecting to client ${clientId}`);
    // Future implementation
}

function openFileManager(clientId) {
    console.log(`Opening file manager for client ${clientId}`);
    // Future implementation
}

function openTerminal(clientId) {
    console.log(`Opening terminal for client ${clientId}`);
    // Future implementation
}

function showLogs(clientId) {
    console.log(`Showing logs for client ${clientId}`);
    // Future implementation
}

function disconnectClient(clientId) {
    console.log(`Disconnecting client ${clientId}`);
    // Future implementation
}

function toggleFilter() {
    console.log('Toggling filter options');
    // Future implementation
}

function initializeClientSearch() {
    const clientSearch = document.getElementById('clientSearch');
    if (clientSearch) {
        clientSearch.addEventListener('input', function (e) {
            const searchTerm = e.target.value.toLowerCase();
            const clientItems = document.querySelectorAll('.client-item');

            clientItems.forEach(item => {
                const clientId = item.querySelector('.client-id')?.textContent.toLowerCase() || '';
                const platform = item.querySelector('.client-platform')?.textContent.toLowerCase() || '';

                if (clientId.includes(searchTerm) || platform.includes(searchTerm)) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
}

// Initialize the profile icon when the page loads
document.addEventListener('DOMContentLoaded', function () {
    initializeProfileIcon(); // Profile icon functionality
    initializeHamburgerMenu(); // Hamburger menu functionality
    initializeMasonryLayout(); // Masonry layout for dashboard
    initializeSettings(); // Settings page functionality
    initializeClientSearch(); // Client search functionality
    initializeDebugGrid(); // Debugging helpers
});

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