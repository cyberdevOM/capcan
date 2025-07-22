const userData = {
    isLoggedIn: false, // change to true if user is logged in
    username: 'Guest', // change to the actual username if logged in
    profilePicture: null // change to the actual profile picture URL if available
};

function isTouchDevice() {
    return window.matchMedia('(hover: none)').matches ||
            window.matchMedia('(pointer: coarse)').matches ||
            'ontouchstart' in window;
}


function initializeProfileIcon() {
    const profileIcon = document.getElementById('profileIcon');
    const loginMenu = document.getElementById('loginMenu');

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

        loginMenu.style.display = 'none';

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


        if (isTouchDevice()) {
            profileIcon.ontouchstart = function(e) {
                e.stopPropagation();
                if (loginMenu) {
                    loginMenu.classList.toggle('show');
                }
            };

            document.addEventListener('click', function(e) {
                const loginMenu = document.getElementById('loginMenu');
                const profileIcon = document.getElementById('profileIcon');

                if (!profileIcon.contains(e.target) && !loginMenu.contains(e.target)) {
                    loginMenu.classList.remove('show');
                }
            });
        } else {

            profileIcon.onclick = null;

            let hoverTimeout;
            const profileContainer = document.querySelector('.profile-container');

            if (profileContainer) {
                profileContainer.addEventListener('mouseleave', function() {
                    hoverTimeout = setTimeout(() => {
                        if (loginMenu) {
                            loginMenu.classList.remove('show');
                        }
                    }, 100);
                });

                profileContainer.addEventListener('mouseenter', function() {
                    clearTimeout(hoverTimeout);
                });
            }
        }
        
    }
}

// Initialize the profile icon when the page loads
document.addEventListener('DOMContentLoaded', initializeProfileIcon);

// Re initialize if screen size changes (Desktop ~ Mobile)
window.addEventListener('resize', function() {
    this.clearTimeout(this.window.resizeTimeout);
    this.window.resizeTimeout = this.setTimeout(initializeProfileIcon, 250);
})