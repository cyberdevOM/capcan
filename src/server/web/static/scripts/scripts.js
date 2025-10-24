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
    const grid = document.getElementById('TilesGrid') || document.querySelector('.masonry-grid')
    if (grid) {
        if (!grid.querySelector('.grid-sizer')) {
            const gridSizer = document.createElement('div');
            gridSizer.className = 'grid-sizer';
            grid.appendChild(gridSizer);
        }

        const masonry = new Masonry(grid, {
            itemSelector: '.modular-block',
            columnWidth: '.grid-sizer',
            percentPosition: true,
            gutter: 20,
            fitWidth: false, // Let CSS handle width
            resize: true,
            transitionDuration: '0.3s'
        });

        // Force correct width calc
        function adjustGridWidth() {
            const mainContent = grid.closest('.main-content');
            if (mainContent) {
                const mainContentStyles = getComputedStyle(mainContent);
                const paddingLeft = parseFloat(mainContentStyles.paddingLeft) || 0;
                const paddingRight = parseFloat(mainContentStyles.paddingRight) || 0;
                
                const availableWidth = mainContent.clientWidth - paddingLeft - paddingRight;
                
                grid.style.width = '100%';
                grid.style.maxWidth = `${availableWidth}px`;

                console.log(`Adjusted grid width to ${availableWidth}px`);
            }
        }

        // Apply width fix after Masonry layout Complete
        masonry.on('layoutComplete', () => {
            adjustGridWidth();
        });

        // Handle Window Resize
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                adjustGridWidth();
                masonry.layout();
            }, 250); // Debounce resize events
        });

        // Initial adjustment
        setTimeout(adjustGridWidth, 100);

        // Reload layout on window resize
        const observer = new MutationObserver(() => {
            masonry.reloadItems();
            masonry.layout();
            setTimeout(adjustGridWidth, 50); // Adjust width after layout
        });

        observer.observe(grid, {
            childList: true,
            subtree: true
        });


        window.masonryInstance = masonry; // Expose for debugging
    }
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
    initializeProfileIcon();
    initializeHamburgerMenu();
    initializeMasonryLayout();
    initializeSettings();
    initializeClientSearch();
});