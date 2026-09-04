// Login form logic for EmpowerHR.

import { loginUser } from './api.js';
import { saveCurrentUser, saveToken } from './auth.js';

// Dedicated key used by register.js to hand off a one-time
// registration-success notification. Must match the key in register.js.
const REGISTRATION_SUCCESS_KEY = 'registrationSuccessMessage';

// Show the registration-success notification, if one is waiting, and
// immediately clear it so it never reappears on refresh or a later visit.
// Runs once on page load, independent of the login form itself. If
// sessionStorage is unavailable for any reason, this is skipped silently
// -- it must never block the normal login page from working.
(function showRegistrationSuccessMessage() {
    const successEl = document.getElementById('loginSuccessMessage');
    if (!successEl) {
        return;
    }

    let message = null;
    try {
        message = sessionStorage.getItem(REGISTRATION_SUCCESS_KEY);
        if (message) {
            sessionStorage.removeItem(REGISTRATION_SUCCESS_KEY);
        }
    } catch (storageError) {
        return;
    }

    if (message) {
        successEl.textContent = message;
        successEl.classList.remove('hidden');
    }
})();

const form = document.getElementById('loginForm');
const loginError = document.getElementById('loginError');

if (form) {
    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        if (loginError) {
            loginError.textContent = '';
            loginError.classList.add('hidden');
        }

        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        const credentials = {
            email,
            password
        };

        try {
            const { access_token, token_type, ...user } = await loginUser(credentials);
            saveCurrentUser(user);
            saveToken(access_token);
            alert('تم تسجيل الدخول بنجاح');
            window.location.href = 'index.html';
        } catch (error) {
            if (loginError) {
                loginError.textContent = error.message;
                loginError.classList.remove('hidden');
            } else {
                alert(error.message);
            }
        }
    });
}