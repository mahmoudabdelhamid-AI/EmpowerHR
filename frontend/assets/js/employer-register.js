// Employer registration form logic for EmpowerHR.
// Mirrors register.js: same inline-error-feedback pattern, same
// success -> sessionStorage handoff -> redirect to login.html flow.

import { registerEmployer } from './api.js';

// Same key login.js already reads from sessionStorage on page load.
const REGISTRATION_SUCCESS_KEY = 'registrationSuccessMessage';

const employerRegisterError = document.getElementById('employerRegisterError');

document.getElementById('employerRegistrationForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    if (employerRegisterError) {
        employerRegisterError.textContent = '';
        employerRegisterError.classList.add('hidden');
    }

    const fullName = document.getElementById('fullName').value.trim();
    const companyName = document.getElementById('companyName').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    if (password !== confirmPassword) {
        if (employerRegisterError) {
            employerRegisterError.textContent = 'كلمتا المرور غير متطابقتين';
            employerRegisterError.classList.remove('hidden');
        } else {
            alert('كلمتا المرور غير متطابقتين');
        }
        return;
    }

    const employerData = {
        full_name: fullName,
        company_name: companyName,
        email: email,
        password: password
    };

    try {
        await registerEmployer(employerData);

        try {
            sessionStorage.setItem(REGISTRATION_SUCCESS_KEY, 'تم إنشاء حساب صاحب العمل بنجاح.');
        } catch (storageError) {
            // Success notification is optional UX -- if sessionStorage is
            // unavailable for any reason, the redirect below must still
            // happen normally.
        }

        window.location.href = './login.html';
    } catch (error) {
        console.error(error);
        if (employerRegisterError) {
            employerRegisterError.textContent = error.message;
            employerRegisterError.classList.remove('hidden');
        } else {
            alert(error.message);
        }
    }
});
