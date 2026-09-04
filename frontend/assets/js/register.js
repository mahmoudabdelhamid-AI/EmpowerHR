// Registration form logic for EmpowerHR.
// Assumes the manually-added password fields use id="password" and
// id="confirmPassword" (matching the existing camelCase convention
// used by firstName, lastName, birthDate, etc.).

import { registerUser, uploadProfilePhoto, loginUser, updateCandidateProfile } from './api.js';
import { saveToken, logout } from './auth.js';

// Dedicated key for the one-time registration-success notification handed
// off to login.html via sessionStorage. Kept distinct from any
// authentication-related storage key (see auth.js) and never holds
// tokens, passwords, or user data -- just the existing success message.
const REGISTRATION_SUCCESS_KEY = 'registrationSuccessMessage';

const registerError = document.getElementById('registerError');

document.getElementById('registrationForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    if (registerError) {
        registerError.textContent = '';
        registerError.classList.add('hidden');
    }

    const firstName = document.getElementById('firstName').value.trim();
    const lastName = document.getElementById('lastName').value.trim();
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    if (password !== confirmPassword) {
        if (registerError) {
            registerError.textContent = 'كلمتا المرور غير متطابقتين';
            registerError.classList.remove('hidden');
        } else {
            alert('كلمتا المرور غير متطابقتين');
        }
        return;
    }

    const userData = {
        full_name: `${firstName} ${lastName}`.trim(),
        email: email,
        password: password
    };

    try {
        const newUser = await registerUser(userData);

        // specialization/skills are real, persisted CandidateProfile data
        // as of Step 10 -- but per the approved architecture, profile
        // editing (not registration) owns persisting them. Collected here
        // on the form for continuity with the existing UX, then sent
        // through the same authenticated post-registration session
        // already used below for the profile photo (temporary login ->
        // authenticated call -> logout). Registration already succeeded
        // at this point, so a failure here is logged but does not block
        // the rest of the flow -- the candidate can also set these later
        // from the profile page.
        const specializationSelect = document.getElementById('specialization');
        const skillsInput = document.getElementById('skills');
        const specialization = (specializationSelect && specializationSelect.value)
            ? specializationSelect.options[specializationSelect.selectedIndex].text
            : '';
        const skills = skillsInput ? skillsInput.value.trim() : '';

        const photoInput = document.getElementById('photoInput');
        const hasPhoto = photoInput && photoInput.files && photoInput.files[0];
        const hasCandidateProfileData = specialization || skills;

        if (hasPhoto || hasCandidateProfileData) {
            try {
                const { access_token } = await loginUser({ email, password });
               saveToken(access_token);

               try {
                   if (hasPhoto) {
                       await uploadProfilePhoto(photoInput.files[0]);
                   }
                   if (hasCandidateProfileData) {
                       await updateCandidateProfile({ specialization, skills });
                   }
               } finally {
                   logout();
               }
            } catch (photoError) {
                console.error(photoError);
            }
        }

        try {
            sessionStorage.setItem(REGISTRATION_SUCCESS_KEY, 'تم إنشاء حسابك بنجاح.');
        } catch (storageError) {
            // Success notification is optional UX -- if sessionStorage is
            // unavailable for any reason, the redirect below must still
            // happen normally.
        }

        // اخرج من الـ event الحالي تماما
        setTimeout(() => {
            window.location.href = './login.html';
        }, 0);

        return;

    } catch (error) {
        console.error(error);
        if (registerError) {
            registerError.textContent = error.message;
            registerError.classList.remove('hidden');
        } else {
            alert(error.message);
        }
    }
});
