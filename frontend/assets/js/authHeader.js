// Shared header / authenticated-navigation behavior for EmpowerHR.
//
// Extracted from app.js (Step 7.5) so the same header logic (profile
// icon/photo, user menu, logout) can be reused on pages other than
// index.html without duplicating it. Behavior is unchanged from the
// original app.js implementation, with two small additions so it also
// works correctly on pages that have no #guestActions element (only
// index.html has one, inside the hero section):
//   - updateAuthUI() no longer requires #guestActions to exist before
//     populating the header.
//   - the logout handler only touches #guestActions if it's present.
// Everything else is identical to the original app.js code.

// Update the header based on the current login state
async function updateAuthUI() {
    const { getCurrentUser, isLoggedIn } = await import('./auth.js');

    if (!isLoggedIn()) {
        return;
    }

    const guestActions = document.getElementById('guestActions');
    const userName = document.getElementById('userName');
    const dropdownArrow = document.getElementById('dropdownArrow');

    if (!userName || !dropdownArrow) {
        return;
    }

    if (guestActions) {
        guestActions.classList.add('hidden');
    }

    const currentUser = getCurrentUser();
    userName.textContent = currentUser?.full_name ?? 'User';
    userName.hidden = false;
    dropdownArrow.hidden = false;

    const userEmail = document.getElementById('userEmail');
    if (userEmail) {
        userEmail.textContent = currentUser?.email ?? '';
    }

    // Step 9: employer accounts get a link to their dashboard in the
    // user menu. This is a UX convenience only -- not a security
    // boundary; every employer endpoint independently enforces its own
    // authorization server-side regardless of what the frontend shows.
    if (currentUser?.role === 'employer') {
        const userMenu = document.getElementById('userMenu');
        const logoutButton = document.getElementById('logoutButton');
        if (userMenu && logoutButton && !document.getElementById('employerDashboardLink')) {
            const dashboardLink = document.createElement('a');
            dashboardLink.id = 'employerDashboardLink';
            dashboardLink.href = 'employer-dashboard.html';
            dashboardLink.textContent = 'Employer Dashboard';
            userMenu.insertBefore(dashboardLink, logoutButton);
        }
    }

    if (currentUser?.profile_image) {
        const { API_BASE_URL } = await import('./api.js');
        const profileIcon = document.getElementById('profileIcon');
        if (profileIcon) {
            profileIcon.style.backgroundImage = `url(${API_BASE_URL}${currentUser.profile_image})`;
            profileIcon.style.backgroundSize = 'cover';
            profileIcon.style.backgroundPosition = 'center';
            profileIcon.textContent = '';
        }
    }
}

updateAuthUI();

// Toggle the user menu
function toggleUserMenu() {
    const menu = document.getElementById('userMenu');
    menu.classList.toggle('active');

    if (menu.classList.contains('active')) {
        const firstAction = menu.querySelector('a, button');
        if (firstAction) {
            firstAction.focus();
        }
    }
}

const profileClusterEl = document.getElementById('profileCluster');
profileClusterEl.tabIndex = 0;
profileClusterEl.setAttribute('role', 'button');
profileClusterEl.addEventListener('click', toggleUserMenu);
profileClusterEl.addEventListener('keydown', function(event) {
    if (event.key === 'Enter' || event.key === ' ' || event.code === 'Space') {
        event.preventDefault();
        toggleUserMenu();
    }
});

// Close the user menu when clicking outside
document.addEventListener('click', function(event) {
    const menu = document.getElementById('userMenu');
    const profileCluster = document.getElementById('profileCluster');

    if (!profileCluster.contains(event.target)) {
        menu.classList.remove('active');
    }
});

// Close the user menu on Escape and return focus to the profile cluster
document.addEventListener('keydown', function(event) {
    if (event.key !== 'Escape') {
        return;
    }
    const menu = document.getElementById('userMenu');
    if (menu.classList.contains('active')) {
        menu.classList.remove('active');
        document.getElementById('profileCluster').focus();
    }
});

// Handle logout
const logoutButton = document.getElementById('logoutButton');

if (logoutButton) {
    logoutButton.addEventListener('click', async function() {
        const { logout } = await import('./auth.js');
        logout();

        document.getElementById('userMenu').classList.remove('active');
        document.getElementById('userName').hidden = true;
        document.getElementById('dropdownArrow').hidden = true;

        const guestActions = document.getElementById('guestActions');
        if (guestActions) {
            guestActions.classList.remove('hidden');
        }

        window.location.href = 'index.html';
    });
}