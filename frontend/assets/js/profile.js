// Profile page logic for EmpowerHR.
// Uses the existing localStorage-based current-user mechanism (auth.js) --
// no JWT / new authorization scheme.

import { API_BASE_URL, getProfile, uploadProfilePhoto } from './api.js';
import { getCurrentUser, isLoggedIn, saveCurrentUser } from './auth.js';

if (!isLoggedIn()) {
    window.location.href = 'login.html';
} else {
    init();
}

function renderProfile(user) {
    const fullNameEl = document.getElementById('profileFullName');
    const emailEl = document.getElementById('profileEmail');
    const placeholder = document.getElementById('profilePhotoPlaceholder');

    fullNameEl.textContent = user?.full_name ?? '—';
    emailEl.textContent = user?.email ?? '—';

    if (user?.profile_image) {
        placeholder.style.backgroundImage = `url(${API_BASE_URL}${user.profile_image})`;
        placeholder.style.backgroundSize = 'cover';
        placeholder.style.backgroundPosition = 'center';
        placeholder.innerHTML = '<div class="photo-overlay">اضغط لتغيير الصورة</div>';
    } else {
        placeholder.style.backgroundImage = '';
        placeholder.innerHTML = '📷<div class="photo-overlay">اضغط لتغيير الصورة</div>';
    }
}

async function init() {
    // Show what we already have in localStorage immediately, then refresh
    // from the backend in case the profile changed on another device/tab.
    const storedUser = getCurrentUser();
    renderProfile(storedUser);

    try {
        const freshUser = await getProfile(storedUser.id);
        saveCurrentUser(freshUser);
        renderProfile(freshUser);
    } catch (error) {
        console.error(error);
    }

    const placeholder = document.getElementById('profilePhotoPlaceholder');
    const input = document.getElementById('profilePhotoInput');

    placeholder.addEventListener('click', function () {
        input.click();
    });

    input.addEventListener('change', async function (e) {
        if (!e.target.files || !e.target.files[0]) {
            return;
        }

        try {
            const updatedUser = await uploadProfilePhoto(getCurrentUser().id, e.target.files[0]);
            saveCurrentUser(updatedUser);
            renderProfile(updatedUser);
        } catch (error) {
            alert(error.message);
        }
    });
}
