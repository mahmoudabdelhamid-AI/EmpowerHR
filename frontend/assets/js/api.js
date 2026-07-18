// API helper functions for communicating with the EmpowerHR backend.

async function getJobs() {
    const response = await fetch('http://127.0.0.1:8000/jobs');

    if (!response.ok) {
        throw new Error('Failed to fetch jobs');
    }

    return await response.json();
}

async function registerUser(userData) {
    const response = await fetch('http://127.0.0.1:8000/register', {
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
    const response = await fetch('http://127.0.0.1:8000/login', {
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

export { getJobs, registerUser, loginUser };