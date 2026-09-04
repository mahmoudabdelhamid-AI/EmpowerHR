// Employer Dashboard page logic for EmpowerHR (Step 9).
//
// Single page with three in-page views (My Jobs / Create-Edit Job /
// Applicants), toggled via the existing .hidden class convention (the
// same mechanism app.js/index.html already use for the dropdownModal).
//
// Follows profile.js's setFeedback/clearFeedback inline-feedback
// pattern for create/edit/delete/status-change outcomes, and the same
// loading/retry pattern already used in app.js/applications.js for the
// initial jobs/applicants fetch.

import {
    getEmployerJobs,
    createJob,
    updateJob,
    deleteJob,
    getApplicants,
    updateApplicationStatus,
    downloadApplicantCv
} from './api.js';
import { getCurrentUser, isLoggedIn, logout } from './auth.js';

const STATUS_LABELS = {
    Pending: 'قيد الانتظار',
    Reviewed: 'تمت المراجعة',
    Interview: 'مقابلة شخصية',
    Accepted: 'مقبول',
    Rejected: 'مرفوض'
};
const STATUS_VALUES = Object.keys(STATUS_LABELS);

// "Leave unchanged" sentinel for the employment-type select in the
// edit form -- the employer-jobs list endpoint doesn't return
// employment_type, so on edit we never know the job's current value
// and must avoid overwriting it unless the employer explicitly picks
// a new one.
const KEEP_CURRENT_VALUE = '';

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

// --- View switching -----------------------------------------------------

const views = {
    myJobs: document.getElementById('myJobsView'),
    jobForm: document.getElementById('jobFormView'),
    applicants: document.getElementById('applicantsView')
};

function showView(name) {
    Object.entries(views).forEach(([key, el]) => {
        if (!el) {
            return;
        }
        el.classList.toggle('hidden', key !== name);
    });
}

// --- My Jobs --------------------------------------------------------------

let cachedJobs = [];
let cachedJobsById = {};

async function loadMyJobs() {
    const container = document.getElementById('myJobsContainer');
    container.innerHTML = '<p>جارٍ تحميل الوظائف...</p>';

    try {
        cachedJobs = await getEmployerJobs();
        cachedJobsById = Object.fromEntries(cachedJobs.map(job => [job.id, job]));
        renderMyJobs(cachedJobs);
    } catch (error) {
        if (error.status === 401) {
            logout();
            window.location.href = 'login.html';
            return;
        }
        container.innerHTML = '<p>تعذر تحميل الوظائف.</p>';
        const retryBtn = document.createElement('button');
        retryBtn.className = 'btn btn-primary';
        retryBtn.textContent = 'إعادة المحاولة';
        retryBtn.addEventListener('click', loadMyJobs);
        container.appendChild(retryBtn);
    }
}

function renderMyJobs(jobs) {
    const container = document.getElementById('myJobsContainer');
    container.innerHTML = '';

    if (jobs.length === 0) {
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        const message = document.createElement('p');
        message.textContent = 'لا توجد وظائف بعد. أضف وظيفتك الأولى.';
        emptyState.appendChild(message);
        container.appendChild(emptyState);
        return;
    }

    const grid = document.createElement('div');
    grid.id = 'myJobsGrid';
    grid.style.display = 'grid';
    grid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(280px, 1fr))';
    grid.style.gap = '2rem';

    jobs.forEach(job => {
        grid.appendChild(createMyJobCard(job));
    });

    container.appendChild(grid);
}

function createMyJobCard(job) {
    const card = document.createElement('div');
    card.className = 'job-card';

    const title = document.createElement('div');
    title.className = 'job-title';
    title.textContent = job.title;
    card.appendChild(title);

    const statusBadge = document.createElement('span');
    statusBadge.className = `status-badge ${job.is_active ? 'status-accepted' : 'status-rejected'}`;
    statusBadge.textContent = job.is_active ? 'نشطة' : 'غير نشطة';
    card.appendChild(statusBadge);

    const details = document.createElement('div');
    details.className = 'job-details';
    [
        { label: 'الشركة', value: job.company },
        { label: 'الموقع', value: job.location },
        { label: 'الراتب', value: job.salary }
    ].forEach(field => {
        const item = document.createElement('div');
        item.className = 'detail-item';
        const content = document.createElement('div');
        content.className = 'detail-content';
        const label = document.createElement('div');
        label.className = 'detail-label';
        label.textContent = field.label;
        const value = document.createElement('div');
        value.className = 'detail-value';
        value.textContent = field.value;
        content.appendChild(label);
        content.appendChild(value);
        item.appendChild(content);
        details.appendChild(item);
    });
    card.appendChild(details);

    const feedback = document.createElement('div');
    feedback.className = 'hidden';
    feedback.setAttribute('role', 'alert');
    feedback.style.marginTop = '0.75rem';

    const actions = document.createElement('div');
    actions.style.display = 'flex';
    actions.style.flexWrap = 'wrap';
    actions.style.gap = '0.5rem';
    actions.style.marginTop = '1rem';

    const editBtn = document.createElement('button');
    editBtn.className = 'btn btn-primary';
    editBtn.textContent = 'تعديل';
    editBtn.addEventListener('click', () => openEditJobForm(job));

    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'btn btn-secondary';
    toggleBtn.style.color = '#2563eb';
    toggleBtn.style.borderColor = '#2563eb';
    toggleBtn.textContent = job.is_active ? 'إيقاف الوظيفة' : 'تفعيل الوظيفة';
    toggleBtn.addEventListener('click', async () => {
        clearFeedback(feedback);
        try {
            const updated = await updateJob(job.id, { is_active: !job.is_active });
            cachedJobsById[job.id] = updated;
            renderMyJobs(Object.values(cachedJobsById));
        } catch (error) {
            setFeedback(feedback, error.message, true);
        }
    });

    const applicantsBtn = document.createElement('button');
    applicantsBtn.className = 'btn btn-secondary';
    applicantsBtn.style.color = '#2563eb';
    applicantsBtn.style.borderColor = '#2563eb';
    applicantsBtn.textContent = 'عرض المتقدمين';
    applicantsBtn.addEventListener('click', () => openApplicantsView(job));

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'btn btn-secondary';
    deleteBtn.style.color = '#991b1b';
    deleteBtn.style.borderColor = '#991b1b';
    deleteBtn.textContent = 'حذف';
    deleteBtn.addEventListener('click', async () => {
        clearFeedback(feedback);
        if (!window.confirm('هل أنت متأكد من حذف هذه الوظيفة؟')) {
            return;
        }
        try {
            await deleteJob(job.id);
            delete cachedJobsById[job.id];
            renderMyJobs(Object.values(cachedJobsById));
        } catch (error) {
            setFeedback(feedback, error.message, true);
        }
    });

    actions.appendChild(editBtn);
    actions.appendChild(toggleBtn);
    actions.appendChild(applicantsBtn);
    actions.appendChild(deleteBtn);

    card.appendChild(actions);
    card.appendChild(feedback);

    return card;
}

// --- Create / Edit Job form -----------------------------------------------

const jobForm = document.getElementById('jobForm');
const jobFormTitle = document.getElementById('jobFormTitle');
const jobFormFeedback = document.getElementById('jobFormFeedback');
const jobFormJobId = document.getElementById('jobFormJobId');
const jobTitleInput = document.getElementById('jobTitleInput');
const jobLocationInput = document.getElementById('jobLocationInput');
const jobSalaryInput = document.getElementById('jobSalaryInput');
const jobEmploymentTypeInput = document.getElementById('jobEmploymentTypeInput');
const jobIsActiveGroup = document.getElementById('jobIsActiveGroup');
const jobIsActiveInput = document.getElementById('jobIsActiveInput');

function openCreateJobForm() {
    clearFeedback(jobFormFeedback);
    jobFormTitle.textContent = 'إضافة وظيفة جديدة';
    jobFormJobId.value = '';
    jobTitleInput.value = '';
    jobLocationInput.value = '';
    jobSalaryInput.value = '';

    // Creating: employment_type is required, no "keep current" option.
    removeKeepCurrentOption();
    jobEmploymentTypeInput.value = 'Full-time';
    jobIsActiveGroup.style.display = 'none'; // is_active isn't settable on create

    showView('jobForm');
}

function openEditJobForm(job) {
    clearFeedback(jobFormFeedback);
    jobFormTitle.textContent = `تعديل: ${job.title}`;
    jobFormJobId.value = job.id;
    jobTitleInput.value = job.title;
    jobLocationInput.value = job.location;
    jobSalaryInput.value = job.salary;

    // Editing: the employer-jobs list doesn't include employment_type,
    // so default to "leave unchanged" rather than guessing/overwriting it.
    addKeepCurrentOptionIfMissing();
    jobEmploymentTypeInput.value = KEEP_CURRENT_VALUE;

    jobIsActiveGroup.style.display = 'flex';
    jobIsActiveInput.checked = job.is_active;

    showView('jobForm');
}

function addKeepCurrentOptionIfMissing() {
    if (jobEmploymentTypeInput.querySelector('option[value=""]')) {
        return;
    }
    const keepOption = document.createElement('option');
    keepOption.value = KEEP_CURRENT_VALUE;
    keepOption.textContent = '-- اتركه كما هو --';
    jobEmploymentTypeInput.insertBefore(keepOption, jobEmploymentTypeInput.firstChild);
}

function removeKeepCurrentOption() {
    const keepOption = jobEmploymentTypeInput.querySelector('option[value=""]');
    if (keepOption) {
        keepOption.remove();
    }
}

document.getElementById('showCreateJobBtn').addEventListener('click', openCreateJobForm);
document.getElementById('jobFormCancelBtn').addEventListener('click', () => {
    showView('myJobs');
});

jobForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    clearFeedback(jobFormFeedback);

    const jobId = jobFormJobId.value;
    const isEditing = jobId !== '';

    try {
        if (isEditing) {
            const payload = {
                title: jobTitleInput.value.trim(),
                location: jobLocationInput.value.trim(),
                salary: jobSalaryInput.value.trim(),
                is_active: jobIsActiveInput.checked
            };
            if (jobEmploymentTypeInput.value !== KEEP_CURRENT_VALUE) {
                payload.employment_type = jobEmploymentTypeInput.value;
            }
            const updated = await updateJob(Number(jobId), payload);
            cachedJobsById[updated.id] = updated;
        } else {
            const payload = {
                title: jobTitleInput.value.trim(),
                location: jobLocationInput.value.trim(),
                salary: jobSalaryInput.value.trim(),
                employment_type: jobEmploymentTypeInput.value
            };
            const created = await createJob(payload);
            cachedJobsById[created.id] = created;
        }

        renderMyJobs(Object.values(cachedJobsById));
        showView('myJobs');
    } catch (error) {
        setFeedback(jobFormFeedback, error.message, true);
    }
});

// --- Applicants -------------------------------------------------------

async function openApplicantsView(job) {
    document.getElementById('applicantsForJobTitle').textContent = `المتقدمون على: ${job.title}`;
    showView('applicants');
    await loadApplicants(job);
}

async function loadApplicants(job) {
    const container = document.getElementById('applicantsContainer');
    container.innerHTML = '<p>جارٍ تحميل المتقدمين...</p>';

    try {
        const applicants = await getApplicants(job.id);
        renderApplicants(job, applicants);
    } catch (error) {
        if (error.status === 401) {
            logout();
            window.location.href = 'login.html';
            return;
        }
        container.innerHTML = '<p>تعذر تحميل المتقدمين.</p>';
        const retryBtn = document.createElement('button');
        retryBtn.className = 'btn btn-primary';
        retryBtn.textContent = 'إعادة المحاولة';
        retryBtn.addEventListener('click', () => loadApplicants(job));
        container.appendChild(retryBtn);
    }
}

function renderApplicants(job, applicants) {
    const container = document.getElementById('applicantsContainer');
    container.innerHTML = '';

    if (applicants.length === 0) {
        const emptyState = document.createElement('div');
        emptyState.className = 'empty-state';
        const message = document.createElement('p');
        message.textContent = 'لا يوجد متقدمون على هذه الوظيفة حتى الآن.';
        emptyState.appendChild(message);
        container.appendChild(emptyState);
        return;
    }

    const grid = document.createElement('div');
    grid.id = 'applicantsContainer_grid';
    grid.style.display = 'grid';
    grid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(280px, 1fr))';
    grid.style.gap = '2rem';

    applicants.forEach(applicant => {
        grid.appendChild(createApplicantCard(job, applicant));
    });

    container.appendChild(grid);
}

function createApplicantCard(job, applicant) {
    const card = document.createElement('div');
    card.className = 'job-card';

    const name = document.createElement('div');
    name.className = 'job-title';
    name.textContent = applicant.full_name;
    card.appendChild(name);

    const statusBadge = document.createElement('span');
    statusBadge.className = `status-badge status-${applicant.status.toLowerCase()}`;
    statusBadge.textContent = STATUS_LABELS[applicant.status] || applicant.status;
    card.appendChild(statusBadge);

    const details = document.createElement('div');
    details.className = 'job-details';

    const dateApplied = new Date(applicant.date_applied).toLocaleDateString('ar-EG');
    [
        { label: 'البريد الإلكتروني', value: applicant.email },
        { label: 'تاريخ التقديم', value: dateApplied }
    ].forEach(field => {
        const item = document.createElement('div');
        item.className = 'detail-item';
        const content = document.createElement('div');
        content.className = 'detail-content';
        const label = document.createElement('div');
        label.className = 'detail-label';
        label.textContent = field.label;
        const value = document.createElement('div');
        value.className = 'detail-value';
        value.textContent = field.value;
        content.appendChild(label);
        content.appendChild(value);
        item.appendChild(content);
        details.appendChild(item);
    });
    card.appendChild(details);

    const feedback = document.createElement('div');
    feedback.className = 'hidden';
    feedback.setAttribute('role', 'alert');
    feedback.style.marginTop = '0.75rem';

    // Step 10: CV affordance -- only shown when the applicant actually
    // has a CV. Downloads through the controlled, authenticated employer
    // endpoint (no static/public CV URL is ever referenced here).
    if (applicant.has_cv) {
        const cvBtn = document.createElement('button');
        cvBtn.className = 'btn btn-secondary';
        cvBtn.style.color = '#2563eb';
        cvBtn.style.borderColor = '#2563eb';
        cvBtn.style.marginTop = '1rem';
        cvBtn.textContent = 'عرض السيرة الذاتية';
        cvBtn.addEventListener('click', async () => {
            clearFeedback(feedback);
            try {
                const blob = await downloadApplicantCv(applicant.application_id);
                const objectUrl = URL.createObjectURL(blob);
                const tempLink = document.createElement('a');
                tempLink.href = objectUrl;
                tempLink.download = `cv_${applicant.full_name}`;
                document.body.appendChild(tempLink);
                tempLink.click();
                tempLink.remove();
                URL.revokeObjectURL(objectUrl);
            } catch (error) {
                setFeedback(feedback, error.message, true);
            }
        });
        card.appendChild(cvBtn);
    }

    const statusRow = document.createElement('div');
    statusRow.style.marginTop = '1rem';

    const statusLabel = document.createElement('label');
    statusLabel.textContent = 'تغيير الحالة';
    statusLabel.style.display = 'block';
    statusLabel.style.marginBottom = '0.5rem';
    statusLabel.style.fontWeight = '600';

    const statusSelect = document.createElement('select');
    STATUS_VALUES.forEach(value => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = STATUS_LABELS[value];
        if (value === applicant.status) {
            option.selected = true;
        }
        statusSelect.appendChild(option);
    });

    statusSelect.addEventListener('change', async function () {
        clearFeedback(feedback);
        const newStatus = statusSelect.value;
        try {
            const updated = await updateApplicationStatus(applicant.application_id, newStatus);
            applicant.status = updated.status;
            statusBadge.className = `status-badge status-${updated.status.toLowerCase()}`;
            statusBadge.textContent = STATUS_LABELS[updated.status] || updated.status;
            setFeedback(feedback, 'تم تحديث حالة الطلب بنجاح', false);
        } catch (error) {
            statusSelect.value = applicant.status;
            setFeedback(feedback, error.message, true);
        }
    });

    statusRow.appendChild(statusLabel);
    statusRow.appendChild(statusSelect);
    card.appendChild(statusRow);
    card.appendChild(feedback);

    return card;
}

document.getElementById('backToMyJobsBtn').addEventListener('click', () => {
    showView('myJobs');
});

document.getElementById('showMyJobsBtn').addEventListener('click', () => {
    showView('myJobs');
});

// --- Init -------------------------------------------------------------

function init() {
    showView('myJobs');
    loadMyJobs();
}

// --- Access guard -----------------------------------------------------
// Placed last, after every const/function it depends on (views, init,
// etc.) has been declared -- calling init() any earlier hits the
// temporal dead zone for `const views` and throws a ReferenceError.

if (!isLoggedIn()) {
    window.location.href = 'login.html';
} else if (getCurrentUser()?.role !== 'employer') {
    // A candidate account has no business on this page. This is a UX
    // guard only -- the backend independently rejects every employer
    // endpoint for non-employer tokens regardless of this check.
    window.location.href = 'index.html';
} else {
    init();
}
