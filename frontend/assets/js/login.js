// Login form logic for EmpowerHR.

import { loginUser } from './api.js';
import { saveCurrentUser } from './auth.js';

const form = document.getElementById('loginForm');

if (form) {
    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;

        const credentials = {
            email,
            password
        };

        try {
            const user = await loginUser(credentials);
            saveCurrentUser(user);
            alert('تم تسجيل الدخول بنجاح');
            window.location.href = 'index.html';
        } catch (error) {
            alert(error.message);
        }
    });
}