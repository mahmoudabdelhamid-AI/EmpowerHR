// Authentication state management for EmpowerHR.
// Single source of truth for the current logged-in user on the frontend.

const CURRENT_USER_KEY = 'currentUser';
const ACCESS_TOKEN_KEY = 'accessToken';

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

// Step 7.1: the backend now issues a JWT on login. It is stored here so
// it is available for later steps (attaching it to protected requests).
// Nothing reads or requires this token yet.
function saveToken(token) {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

function getToken() {
    return localStorage.getItem(ACCESS_TOKEN_KEY);

}

function logout() {
    localStorage.removeItem(CURRENT_USER_KEY);
    localStorage.removeItem(ACCESS_TOKEN_KEY);
}

export { saveCurrentUser, getCurrentUser, isLoggedIn, logout, saveToken, getToken };