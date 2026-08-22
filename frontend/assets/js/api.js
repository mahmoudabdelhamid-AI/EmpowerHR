// API helper functions for communicating with the EmpowerHR backend.

const API_BASE_URL = 'http://127.0.0.1:8000';

async function getJobs() {
    const response = await fetch(`${API_BASE_URL}/jobs`);

    if (!response.ok) {
        throw new Error('Failed to fetch jobs');
    }

    return await response.json();
}

async function registerUser(userData) {
    const response = await fetch(`${API_BASE_URL}/register`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const message = (errorData && errorData.detail) || 'Failed to register user';
        throw new Error(message);
    }

    return await response.json();
}

async function loginUser(credentials) {
    const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(credentials)
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const message = (errorData && errorData.detail) || 'Failed to login';
        throw new Error(message);
    }

    return await response.json();
}

async function applyToJob(jobId, userId) {
    const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/apply`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ user_id: userId })
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const message = (errorData && errorData.detail) || 'Failed to apply to job';
        throw new Error(message);
    }

    return await response.json();
}

async function getApplications(userId) {
    const response = await fetch(`${API_BASE_URL}/applications?user_id=${userId}`);

    if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const message = (errorData && errorData.detail) || 'Failed to fetch applications';
        throw new Error(message);
    }

    return await response.json();
}

async function getProfile(userId) {
    const response = await fetch(`${API_BASE_URL}/profile?user_id=${userId}`);

    if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const message = (errorData && errorData.detail) || 'Failed to fetch profile';
        throw new Error(message);
    }

    return await response.json();
}

async function uploadProfilePhoto(userId, file) {
    const formData = new FormData();
    formData.append('user_id', userId);
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/profile/photo`, {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const message = (errorData && errorData.detail) || 'Failed to upload profile photo';
        throw new Error(message);
    }

    return await response.json();
}

export {
    API_BASE_URL,
    getJobs,
    registerUser,
    loginUser,
    applyToJob,
    getApplications,
    getProfile,
    uploadProfilePhoto
};