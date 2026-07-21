// Registration form logic for EmpowerHR.
// Assumes the manually-added password fields use id="password" and
// id="confirmPassword" (matching the existing camelCase convention
// used by firstName, lastName, birthDate, etc.).

import { registerUser } from './api.js';

document.getElementById('registrationForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const firstName = document.getElementById('firstName').value.trim();
    const lastName = document.getElementById('lastName').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    if (password !== confirmPassword) {
        alert('كلمتا المرور غير متطابقتين');
        return;
    }

    const userData = {
        full_name: `${firstName} ${lastName}`.trim(),
        email: email,
        password: password
    };

    try {
        await registerUser(userData);

        alert('تم إنشاء حسابك بنجاح.');

        // اخرج من الـ event الحالي تماما
        setTimeout(() => {
            window.location.href = './login.html';
        }, 0);

        return;

    } catch (error) {
        console.error(error);
    }
});