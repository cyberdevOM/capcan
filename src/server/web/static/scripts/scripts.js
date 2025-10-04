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

        profileIcon.onclick = function() {
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

        profileIcon.onclick = function(e) {
            e.stopPropagation(); // Prevent event bubbling
            if (loginMenu) {
                loginMenu.classList.toggle('show');
            } else {
                console.error('Login menu element not found');
            }
        };

        document.addEventListener('click', function(e) {
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
    hamburgerToggle.addEventListener('change', function() {
        if (this.checked) {
            collapsedOptions.classList.add('show');
        } else {
            collapsedOptions.classList.remove('show');
        }        
    });

    // Close the hamburger menu when clicking outside of it
    document.addEventListener('click', function(e) {
        const hamburgerContainer = document.getElementById('topBarOptionsCollapsed');
        if (!hamburgerContainer.contains(e.target) && !collapsedOptions.contains(e.target)) {
            hamburgerToggle.checked = false;
            collapsedOptions.classList.remove('show');
        }
    });

    // Close the hamburger menu when clicking on a link
    const navItems = collapsedOptions.querySelectorAll('.mobile-icon-link');
    navItems.forEach(item => {
        item.addEventListener('click', function() {
            hamburgerToggle.checked = false;
            collapsedOptions.classList.remove('show');
        });
    });
}

function initializeMasonryLayout() {
    const grid = document.getElementById('TilesGrid')
    if (grid) {
        const masonry = new Masonry(grid, {
            itemSelector: '.modular-block',
            columnWidth: '.modular-block-xs', // Use the smallest block size as the column width
            gutter: 16,
            fitWidth: true,
            transitionDuration: '0.3s'
        });

        // Reload layout on window resize
        const observer = new MutationObserver(() => {
            masonry.reloadItems();
            masonry.layout();
        });

        observer.observe(grid, { 
            childList: true,
            subtree: true
        });
    }
}

// Initialize the profile icon when the page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeProfileIcon();
    initializeHamburgerMenu();
    initializeMasonryLayout();
});