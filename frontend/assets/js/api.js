// API helper functions for communicating with the EmpowerHR backend.

import { getToken } from './auth.js';

// Falls back to the existing local-development URL unchanged. A deployment
// can override this without a build step by setting
// `window.EMPOWERHR_API_BASE_URL` in a small inline <script> before this
// module loads -- no build system or bundler required.
const API_BASE_URL = (typeof window !== 'undefined' && window.EMPOWERHR_API_BASE_URL) || 'http://127.0.0.1:8000';

// Shared connection-error message used whenever the fetch itself fails
// (server unreachable, no network, CORS-blocked, DNS failure, etc.),
// so every caller sees one consistent, readable message instead of the
// raw browser TypeError.
const CONNECTION_ERROR_MESSAGE = 'Unable to connect to the server. Please check your connection and try again.';

// Parse a FastAPI-style error body into a single readable message.
// Handles both shapes the backend can return:
//   { "detail": "Email already registered" }
//   { "detail": [{ "msg": "...", ... }, ...] }   (Pydantic validation errors)
async function parseErrorMessage(response, fallbackMessage) {
    const errorData = await response.json().catch(() => null);

    if (errorData && errorData.detail) {
        if (typeof errorData.detail === 'string') {
            return errorData.detail;
        }

        if (Array.isArray(errorData.detail)) {
            return errorData.detail
                .map((entry) => entry && entry.msg ? entry.msg : 'Invalid input')
                .join(' ');
        }
    }

    return fallbackMessage;
}

// Shared fetch wrapper: performs the request, converts raw network/fetch
// failures into one consistent connection error, and converts non-2xx
// responses into a normal Error with a readable message and a `status`
// property (so callers can reliably branch on e.g. 401) without changing
// any request method/headers/body/endpoint/auth behavior.
async function apiFetch(url, options, fallbackMessage) {
    let response;

    try {
        response = await fetch(url, options);
    } catch (networkError) {
        throw new Error(CONNECTION_ERROR_MESSAGE);
    }

    if (!response.ok) {
        const message = await parseErrorMessage(response, fallbackMessage);
        const error = new Error(message);
        error.status = response.status;
        throw error;
    }

    return response;
}

async function getJobs() {
    const response = await apiFetch(`${API_BASE_URL}/jobs`, undefined, 'Failed to fetch jobs');
    return await response.json();
}

async function registerUser(userData) {
    const response = await apiFetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
    }, 'Failed to register user');

    return await response.json();
}

async function loginUser(credentials) {
    const response = await apiFetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(credentials)
    }, 'Failed to login');

    return await response.json();
}

async function applyToJob(jobId) {
    const response = await apiFetch(`${API_BASE_URL}/jobs/${jobId}/apply`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${getToken()}`
        }
    }, 'Failed to apply to job');

    return await response.json();
}

async function getApplications() {
    const response = await apiFetch(`${API_BASE_URL}/applications`, {
        headers: {
            'Authorization': `Bearer ${getToken()}`
        }
    }, 'Failed to fetch applications');

    return await response.json();
}

async function getProfile() {
    const response = await apiFetch(`${API_BASE_URL}/profile`, {
        headers: {
            'Authorization': `Bearer ${getToken()}`
        }
    }, 'Failed to fetch profile');

    return await response.json();
}

async function updateProfile(profileData) {
    const response = await apiFetch(`${API_BASE_URL}/profile`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify(profileData)
    }, 'Failed to update profile');

    return await response.json();
}

async function uploadProfilePhoto(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiFetch(`${API_BASE_URL}/profile/photo`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${getToken()}`
        },
        body: formData
    }, 'Failed to upload profile photo');

    return await response.json();
}

// --- Step 9: Employer System -------------------------------------------

async function registerEmployer(employerData) {
    const response = await apiFetch(`${API_BASE_URL}/employer/register`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(employerData)
    }, 'Failed to register employer');

    return await response.json();
}

async function getEmployerJobs() {
    const response = await apiFetch(`${API_BASE_URL}/employer/jobs`, {
        headers: {
            'Authorization': `Bearer ${getToken()}`
        }
    }, 'Failed to fetch employer jobs');

    return await response.json();
}

async function createJob(jobData) {
    const response = await apiFetch(`${API_BASE_URL}/employer/jobs`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify(jobData)
    }, 'Failed to create job');

    return await response.json();
}

async function updateJob(jobId, jobData) {
    const response = await apiFetch(`${API_BASE_URL}/employer/jobs/${jobId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify(jobData)
    }, 'Failed to update job');

    return await response.json();
}

async function deleteJob(jobId) {
    // 204 No Content -- no JSON body to parse.
    await apiFetch(`${API_BASE_URL}/employer/jobs/${jobId}`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${getToken()}`
        }
    }, 'Failed to delete job');
}

async function getApplicants(jobId) {
    const response = await apiFetch(`${API_BASE_URL}/employer/jobs/${jobId}/applicants`, {
        headers: {
            'Authorization': `Bearer ${getToken()}`
        }
    }, 'Failed to fetch applicants');

    return await response.json();
}

async function updateApplicationStatus(applicationId, status) {
    const response = await apiFetch(`${API_BASE_URL}/employer/applications/${applicationId}/status`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify({ status })
    }, 'Failed to update application status');

    return await response.json();
}

// --- Step 10: Candidate Profile & CV -------------------------------------

async function getCandidateProfile() {
    const response = await apiFetch(`${API_BASE_URL}/profile/candidate`, {
        headers: {
            'Authorization': `Bearer ${getToken()}`
        }
    }, 'Failed to fetch candidate profile');

    return await response.json();
}

async function updateCandidateProfile(profileData) {
    const response = await apiFetch(`${API_BASE_URL}/profile/candidate`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getToken()}`
        },
        body: JSON.stringify(profileData)
    }, 'Failed to update candidate profile');

    return await response.json();
}

async function uploadCv(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiFetch(`${API_BASE_URL}/profile/cv`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${getToken()}`
        },
        body: formData
    }, 'Failed to upload CV');

    return await response.json();
}

async function deleteCv() {
    const response = await apiFetch(`${API_BASE_URL}/profile/cv`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${getToken()}`
        }
    }, 'Failed to delete CV');

    return await response.json();
}

async function downloadApplicantCv(applicationId) {
    // Not JSON -- returns the CV file itself (blob) for the caller to
    // open/save, same auth pattern as every other authenticated call.
    const response = await apiFetch(`${API_BASE_URL}/employer/applications/${applicationId}/cv`, {
        headers: {
            'Authorization': `Bearer ${getToken()}`
        }
    }, 'Failed to download CV');

    return await response.blob();
}

export {
    API_BASE_URL,
    getJobs,
    registerUser,
    loginUser,
    applyToJob,
    getApplications,
    getProfile,
    updateProfile,
    uploadProfilePhoto,
    registerEmployer,
    getEmployerJobs,
    createJob,
    updateJob,
    deleteJob,
    getApplicants,
    updateApplicationStatus,
    getCandidateProfile,
    updateCandidateProfile,
    uploadCv,
    deleteCv,
    downloadApplicantCv
};