// API helper functions for communicating with the EmpowerHR backend.

async function getJobs() {
    const response = await fetch('http://127.0.0.1:8000/jobs');

    if (!response.ok) {
        throw new Error('Failed to fetch jobs');
    }

    return await response.json();
}

export { getJobs };
