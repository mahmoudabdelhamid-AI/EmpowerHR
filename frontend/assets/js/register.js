// Registration form logic for EmpowerHR.
// Assumes the manually-added password fields use id="password" and
// id="confirmPassword" (matching the existing camelCase convention
// used by firstName, lastName, birthDate, etc.).

import { registerUser, uploadProfilePhoto } from './api.js';

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
        const newUser = await registerUser(userData);

        // If the user selected a profile photo (photoUpload.js only previews
        // it locally), send it through the existing Step 6 upload endpoint
        // now that we have the new user's id. Registration already succeeded
        // at this point, so a photo upload failure is logged but does not
        // block the rest of the flow.
        const photoInput = document.getElementById('photoInput');
        if (photoInput && photoInput.files && photoInput.files[0]) {
            try {
                await uploadProfilePhoto(newUser.id, photoInput.files[0]);
            } catch (photoError) {
                console.error(photoError);
            }
        }

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
