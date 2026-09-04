// Profile page logic for EmpowerHR.
// Uses the existing localStorage-based current-user mechanism (auth.js) --
// no JWT / new authorization scheme.

import { API_BASE_URL, getProfile, updateProfile, uploadProfilePhoto, getCandidateProfile, updateCandidateProfile, uploadCv, deleteCv } from './api.js';
import { getCurrentUser, isLoggedIn, logout, saveCurrentUser } from './auth.js';

// Small local helpers for writing/clearing inline feedback text into a
// given container. Not a global notification system -- each container is
// looked up once and passed in explicitly by the calling code below.
function setFeedback(el, message, isError) {
    if (!el) {
        return;
    }
    el.textContent = message;
    el.setAttribute('role', isError ? 'alert' : 'status');
    el.classList.remove('hidden');
}

function clearFeedback(el) {
    if (!el) {
        return;
    }
    el.textContent = '';
    el.classList.add('hidden');
}

if (!isLoggedIn()) {
    window.location.href = 'login.html';
} else {
    init();
}

function renderProfile(user) {
    const fullNameInput = document.getElementById('profileFullNameInput');
    const emailEl = document.getElementById('profileEmail');
    const placeholder = document.getElementById('profilePhotoPlaceholder');

    if (fullNameInput) {
        fullNameInput.value = user?.full_name ?? '';
    }
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

// Step 10: render specialization/skills fields and the CV status line
// from a CandidateProfileResponse ({ specialization, skills, has_cv,
// cv_uploaded_at }).
function renderCandidateProfile(candidateProfile) {
    const specializationInput = document.getElementById('profileSpecializationInput');
    const skillsInput = document.getElementById('profileSkillsInput');
    const cvStatus = document.getElementById('cvStatus');
    const cvDeleteBtn = document.getElementById('cvDeleteBtn');

    if (specializationInput) {
        specializationInput.value = candidateProfile?.specialization ?? '';
    }
    if (skillsInput) {
        skillsInput.value = candidateProfile?.skills ?? '';
    }

    if (candidateProfile?.has_cv) {
        cvStatus.textContent = 'توجد سيرة ذاتية مرفوعة ✅';
        cvDeleteBtn.style.display = '';
    } else {
        cvStatus.textContent = 'لا توجد سيرة ذاتية مرفوعة';
        cvDeleteBtn.style.display = 'none';
    }
}

async function init() {
    // Show what we already have in localStorage immediately, then refresh
    // from the backend in case the profile changed on another device/tab.
    const storedUser = getCurrentUser();
    renderProfile(storedUser);

    try {
        const freshUser = await getProfile();
        saveCurrentUser(freshUser);
        renderProfile(freshUser);
    } catch (error) {
        if (error.status === 401) {
            logout();
            window.location.href = 'login.html';
            return;
        }
        console.error(error);
    }

    try {
        const candidateProfile = await getCandidateProfile();
        renderCandidateProfile(candidateProfile);
    } catch (error) {
        if (error.status === 401) {
            logout();
            window.location.href = 'login.html';
            return;
        }
        console.error(error);
    }

    const placeholder = document.getElementById('profilePhotoPlaceholder');
    const input = document.getElementById('profilePhotoInput');
    const photoError = document.getElementById('profilePhotoError');

    placeholder.addEventListener('click', function () {
        input.click();
    });

    placeholder.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ' || e.code === 'Space') {
            e.preventDefault();
            input.click();
        }
    });

    input.addEventListener('change', async function (e) {
        if (!e.target.files || !e.target.files[0]) {
            return;
        }

        clearFeedback(photoError);

        try {
            const updatedUser = await uploadProfilePhoto(e.target.files[0])
            saveCurrentUser(updatedUser);
            renderProfile(updatedUser);
        } catch (error) {
            setFeedback(photoError, error.message, true);
        }
    });

    // Step 10: CV upload / replace / delete.
    const cvInput = document.getElementById('cvInput');
    const cvUploadBtn = document.getElementById('cvUploadBtn');
    const cvDeleteBtn = document.getElementById('cvDeleteBtn');
    const cvFeedback = document.getElementById('cvFeedback');

    cvUploadBtn.addEventListener('click', function () {
        cvInput.click();
    });

    cvInput.addEventListener('change', async function (e) {
        if (!e.target.files || !e.target.files[0]) {
            return;
        }

        clearFeedback(cvFeedback);

        try {
            const candidateProfile = await uploadCv(e.target.files[0]);
            renderCandidateProfile(candidateProfile);
            setFeedback(cvFeedback, 'تم رفع السيرة الذاتية بنجاح', false);
        } catch (error) {
            setFeedback(cvFeedback, error.message, true);
        } finally {
            cvInput.value = '';
        }
    });

    cvDeleteBtn.addEventListener('click', async function () {
        clearFeedback(cvFeedback);

        try {
            const candidateProfile = await deleteCv();
            renderCandidateProfile(candidateProfile);
            setFeedback(cvFeedback, 'تم حذف السيرة الذاتية', false);
        } catch (error) {
            setFeedback(cvFeedback, error.message, true);
        }
    });

    const editForm = document.getElementById('profileEditForm');
    const formFeedback = document.getElementById('profileFormFeedback');

    if (editForm) {
        editForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            clearFeedback(formFeedback);

            const fullName = document.getElementById('profileFullNameInput').value.trim();
            const specialization = document.getElementById('profileSpecializationInput').value.trim();
            const skills = document.getElementById('profileSkillsInput').value.trim();
            const newPassword = document.getElementById('newPassword').value;
            const confirmNewPassword = document.getElementById('confirmNewPassword').value;

            if (newPassword || confirmNewPassword) {
                if (newPassword !== confirmNewPassword) {
                    setFeedback(formFeedback, 'كلمتا المرور غير متطابقتين', true);
                    return;
                }
            }

            const payload = { full_name: fullName };
            if (newPassword) {
                payload.password = newPassword;
            }

            try {
                const updatedUser = await updateProfile(payload);
                saveCurrentUser(updatedUser);
                renderProfile(updatedUser);

                const updatedCandidateProfile = await updateCandidateProfile({ specialization, skills });
                renderCandidateProfile(updatedCandidateProfile);

                document.getElementById('newPassword').value = '';
                document.getElementById('confirmNewPassword').value = '';
                setFeedback(formFeedback, 'تم تحديث الملف الشخصي بنجاح', false);
            } catch (error) {
                setFeedback(formFeedback, error.message, true);
            }
        });
    }
}