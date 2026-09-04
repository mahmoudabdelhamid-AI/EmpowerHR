// Toggle dropdown modal
function toggleDropdown() {
    const modal = document.getElementById('dropdownModal');
    modal.classList.toggle('active');
}

// Small local helpers for writing/clearing inline Apply feedback into a
// given container element. Shared by both the Job Details modal and each
// job card's own feedback element so the two Apply flows stay consistent,
// without introducing a global notification system.
function setApplyFeedback(el, message, isError) {
    if (!el) {
        return;
    }
    el.textContent = message;
    el.setAttribute('role', isError ? 'alert' : 'status');
    el.classList.remove('hidden');
}

function clearApplyFeedback(el) {
    if (!el) {
        return;
    }
    el.textContent = '';
    el.classList.add('hidden');
}

// Tracks the element that had focus when the Job Details modal was opened,
// so focus can be restored to it when the modal closes via Escape.
let jobDetailsModalOpener = null;

// Populate and open the existing Job Details panel for a specific job
function openJobDetails(job) {
    jobDetailsModalOpener = document.activeElement;

    const modal = document.getElementById('dropdownModal');

    modal.querySelector('.company-logo').textContent = job.company;
    modal.querySelector('.company-info h3').textContent = job.company;
    modal.querySelector('.job-title').textContent = job.title;

    const detailValues = modal.querySelectorAll('.detail-value');
    detailValues[0].textContent = job.salary;
    detailValues[1].textContent = job.location;

    const modalApplyFeedback = modal.querySelector('#modalApplyFeedback');
    clearApplyFeedback(modalApplyFeedback);

    modal.querySelector('.apply-btn').onclick = async function() {
        const { isLoggedIn } = await import('./auth.js');

        if (!isLoggedIn()) {
            window.location.href = 'login.html';
            return;
        }

        clearApplyFeedback(modalApplyFeedback);

        try {
            const { applyToJob } = await import('./api.js');
            await applyToJob(job.id);
            setApplyFeedback(modalApplyFeedback, 'تم تقديم طلبك بنجاح.', false);
        } catch (error) {
            setApplyFeedback(modalApplyFeedback, error.message, true);
        }
    };
    modal.classList.add('active');
    modal.focus();
}

// Closes the Job Details modal via the existing 'active' class mechanism
// and restores focus to whatever opened it, if that element still exists.
function closeJobDetailsModal() {
    const modal = document.getElementById('dropdownModal');
    modal.classList.remove('active');

    if (jobDetailsModalOpener && document.body.contains(jobDetailsModalOpener)) {
        jobDetailsModalOpener.focus();
    }
    jobDetailsModalOpener = null;
}

// Close the Job Details modal on Escape
document.addEventListener('keydown', function(event) {
    if (event.key !== 'Escape') {
        return;
    }
    const modal = document.getElementById('dropdownModal');
    if (modal.classList.contains('active')) {
        closeJobDetailsModal();
    }
});

// Close dropdown when clicking outside
document.addEventListener('click', function(event) {
    const modal = document.getElementById('dropdownModal');
    const profileIcon = document.querySelector('.profile-icon');
    
    if (!modal.contains(event.target) && !profileIcon.contains(event.target)) {
        modal.classList.remove('active');
    }
});

// Animate numbers on scroll
const animateNumbers = (entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const statNumbers = entry.target.querySelectorAll('.stat-number');
            statNumbers.forEach(stat => {
                // Some stat numbers wrap their text in a child element (e.g.
                // the "5%" stat's <span class="highlight-5">) for special
                // styling. Animate that child in place so it isn't replaced
                // by a plain text node; otherwise its markup/class is lost
                // the moment the animation starts.
                const target = stat.querySelector('.highlight-5') || stat;
                const text = target.textContent;
                const number = parseInt(text.replace(/[^0-9]/g, ''));
                if (!isNaN(number)) {
                    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                        target.textContent = text;
                        return;
                    }
                    let current = 0;
                    const increment = number / 50;
                    const suffix = text.replace(/[0-9,]/g, '');
                    const timer = setInterval(() => {
                        current += increment;
                        if (current >= number) {
                            target.textContent = text;
                            clearInterval(timer);
                        } else {
                            target.textContent = Math.floor(current).toLocaleString() + suffix;
                        }
                    }, 30);
                }
            });
            observer.unobserve(entry.target);
        }
    });
};

const observer = new IntersectionObserver(animateNumbers, {
    threshold: 0.5
});

observer.observe(document.querySelector('.stats-section'));

// Step 7.8: jobs fetched from the API are cached here once so the
// homepage search can filter them client-side without issuing another
// request on every keystroke.
let allJobs = [];

// Build a single job card element. Extracted out of renderJobs() so the
// same card markup/behavior (click -> Job Details modal, Apply button ->
// auth check -> applyToJob) can be reused when rendering the full job
// list and when rendering filtered search results.
function createJobCard(job) {
    const card = document.createElement('div');
    card.className = 'job-card';
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.addEventListener('click', function(event) {
        if (event.target.closest('.apply-btn')) {
            return;
        }
        event.stopPropagation();
        openJobDetails(job);
    });
    card.addEventListener('keydown', function(event) {
        if (event.target.closest('.apply-btn')) {
            return;
        }
        if (event.key === 'Enter' || event.key === ' ' || event.code === 'Space') {
            event.preventDefault();
            openJobDetails(job);
        }
    });

    const title = document.createElement('div');
    title.className = 'job-title';
    title.textContent = job.title;
    card.appendChild(title);

    const details = document.createElement('div');
    details.className = 'job-details';

    const fields = [
        { label: 'الشركة', value: job.company },
        { label: 'الموقع', value: job.location },
        { label: 'الراتب', value: job.salary }
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

    const applyBtn = document.createElement('button');
    applyBtn.className = 'apply-btn';
    applyBtn.textContent = 'تقديم الآن';

    const cardApplyFeedback = document.createElement('div');
    cardApplyFeedback.className = 'hidden';
    cardApplyFeedback.setAttribute('role', 'alert');

    applyBtn.addEventListener('click', async function() {
        const { isLoggedIn } = await import('./auth.js');

        if (!isLoggedIn()) {
            window.location.href = 'login.html';
            return;
        }

        clearApplyFeedback(cardApplyFeedback);

        try {
            const { applyToJob } = await import('./api.js');
            await applyToJob(job.id);
            setApplyFeedback(cardApplyFeedback, 'تم تقديم طلبك بنجاح.', false);
        } catch (error) {
            setApplyFeedback(cardApplyFeedback, error.message, true);
        }
    });
    card.appendChild(applyBtn);
    card.appendChild(cardApplyFeedback);

    return card;
}

// Render a given list of jobs into #jobsContainer (used for both the
// full list and filtered search results). Shows a simple message when
// the list is empty (e.g. no search matches).
function renderJobList(jobsToRender) {
    const container = document.getElementById('jobsContainer');
    container.innerHTML = '';

    if (jobsToRender.length === 0) {
        container.innerHTML = '<p>لا توجد وظائف مطابقة.</p>';
        return;
    }

    jobsToRender.forEach(job => {
        container.appendChild(createJobCard(job));
    });
}

// Filter the already-loaded jobs in memory by title, company, or
// location. No additional API request is made here.
function filterJobs(query) {
    const normalizedQuery = query.trim().toLocaleLowerCase();

    if (!normalizedQuery) {
        renderJobList(allJobs);
        return;
    }

    const matches = allJobs.filter(job => {
        const haystack = [job.title, job.company, job.location]
            .filter(Boolean)
            .join(' ')
            .toLocaleLowerCase();
        return haystack.includes(normalizedQuery);
    });

    renderJobList(matches);
}

// Wire the existing homepage search input (inside .search-bar) to filter
// the in-memory job list as the user types.
function initJobSearch() {
    const searchInput = document.querySelector('.search-bar input');
    if (!searchInput) {
        return;
    }

    searchInput.addEventListener('input', function(event) {
        filterJobs(event.target.value);
    });
}

// Fetch jobs from the API, cache them in memory, and render them inside
// #jobsContainer.
async function renderJobs() {
    const container = document.getElementById('jobsContainer');
    container.innerHTML = '<p>جارٍ تحميل الوظائف...</p>';

    try {
        const { getJobs } = await import('./api.js');
        allJobs = await getJobs();
        renderJobList(allJobs);
    } catch (error) {
        container.innerHTML = '<p>تعذر تحميل الوظائف.</p>';
        const retryBtn = document.createElement('button');
        retryBtn.className = 'btn btn-primary';
        retryBtn.textContent = 'إعادة المحاولة';
        retryBtn.addEventListener('click', function() {
            renderJobs();
        });
        container.appendChild(retryBtn);
    }
}

initJobSearch();
initJobSearch();
renderJobs();