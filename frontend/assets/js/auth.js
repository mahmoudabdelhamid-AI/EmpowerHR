// Authentication state management for EmpowerHR.
// Single source of truth for the current logged-in user on the frontend.

const CURRENT_USER_KEY = 'currentUser';

function saveCurrentUser(user) {
    localStorage.setItem(CURRENT_USER_KEY, JSON.stringify(user));
}

function getCurrentUser() {
    const stored = localStorage.getItem(CURRENT_USER_KEY);
    return stored ? JSON.parse(stored) : null;
}

function isLoggedIn() {
    return getCurrentUser() !== null;
}

function logout() {
    localStorage.removeItem(CURRENT_USER_KEY);
}

export { saveCurrentUser, getCurrentUser, isLoggedIn, logout };