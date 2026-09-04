// My Applications page logic for EmpowerHR.

import { getCurrentUser, isLoggedIn, logout } from './auth.js';
import { getApplications } from './api.js';

const container = document.getElementById('applicationsContainer');

// Readable Arabic labels for the application statuses already defined by
// the backend/CSS (models.py default "Pending"; applications.css already
// styles status-pending/reviewed/interview/accepted/rejected). This only
// changes the displayed text -- the stored status value and the CSS class
// (still derived from the raw status) are unchanged.
const STATUS_LABELS = {
    Pending: 'قيد الانتظار',
    Reviewed: 'تمت المراجعة',
    Interview: 'مقابلة شخصية',
    Accepted: 'مقبول',
    Rejected: 'مرفوض'
};

function getStatusLabel(status) {
    return STATUS_LABELS[status] || status;
}

function renderEmptyState() {
    const emptyState = document.createElement('div');
    emptyState.className = 'empty-state';

    const message = document.createElement('p');
    message.textContent = 'لا توجد طلبات تقديم حتى الآن.';

    const browseLink = document.createElement('a');
    browseLink.href = 'index.html';
    browseLink.className = 'btn btn-primary';
    browseLink.textContent = 'تصفح الوظائف';

    emptyState.appendChild(message);
    emptyState.appendChild(browseLink);
    container.appendChild(emptyState);
}

function renderApplications(applications) {
    applications.forEach(application => {
        const card = document.createElement('div');
        card.className = 'job-card';

        const title = document.createElement('div');
        title.className = 'job-title';
        title.textContent = application.job_title;
        card.appendChild(title);

        const statusBadge = document.createElement('span');
        statusBadge.className = `status-badge status-${application.status.toLowerCase()}`;
        statusBadge.textContent = getStatusLabel(application.status);
        card.appendChild(statusBadge);

        const details = document.createElement('div');
        details.className = 'job-details';

        const dateApplied = new Date(application.date_applied).toLocaleDateString('ar-EG');

        const fields = [
            { label: 'الشركة', value: application.company },
            { label: 'الموقع', value: application.location },
            { label: 'الراتب', value: application.salary },
            { label: 'نوع التوظيف', value: application.employment_type },
            { label: 'تاريخ التقديم', value: dateApplied }
        ];

        fields.forEach(field => {
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
        container.appendChild(card);
    });
}

async function loadApplications() {
    if (!isLoggedIn()) {
        window.location.href = 'login.html';
        return;
    }

    const currentUser = getCurrentUser();

    container.innerHTML = '<p>جارٍ تحميل الطلبات...</p>';

    try {
        const applications = await getApplications();

        container.innerHTML = '';

        if (applications.length === 0) {
            renderEmptyState();
            return;
        }

        renderApplications(applications);
    } catch (error) {
        if (error.status === 401) {
            logout();
            window.location.href = 'login.html';
            return;
        }
        container.innerHTML = '<p>تعذر تحميل الطلبات.</p>';
        const retryBtn = document.createElement('button');
        retryBtn.className = 'btn btn-primary';
        retryBtn.textContent = 'إعادة المحاولة';
        retryBtn.addEventListener('click', function() {
            loadApplications();
        });
        container.appendChild(retryBtn);
    }
}

loadApplications();