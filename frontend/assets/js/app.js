// Toggle dropdown modal
function toggleDropdown() {
    const modal = document.getElementById('dropdownModal');
    modal.classList.toggle('active');
}

// Populate and open the existing Job Details panel for a specific job
function openJobDetails(job) {
    const modal = document.getElementById('dropdownModal');

    modal.querySelector('.company-logo').textContent = job.company;
    modal.querySelector('.company-info h3').textContent = job.company;
    modal.querySelector('.job-title').textContent = job.title;

    const detailValues = modal.querySelectorAll('.detail-value');
    detailValues[0].textContent = job.salary;
    detailValues[1].textContent = job.location;

    modal.querySelector('.apply-btn').onclick = async function() {
        const { getCurrentUser, isLoggedIn } = await import('./auth.js');

        if (!isLoggedIn()) {
            window.location.href = 'login.html';
            return;
        }

        try {
            const { applyToJob } = await import('./api.js');
            await applyToJob(job.id, getCurrentUser().id);
            alert('تم تقديم طلبك بنجاح.');
        } catch (error) {
            alert(error.message);
        }
    };

    modal.classList.add('active');
}

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
                const text = stat.textContent;
                const number = parseInt(text.replace(/[^0-9]/g, ''));
                if (!isNaN(number)) {
                    let current = 0;
                    const increment = number / 50;
                    const suffix = text.replace(/[0-9,]/g, '');
                    const timer = setInterval(() => {
                        current += increment;
                        if (current >= number) {
                            stat.textContent = text;
                            clearInterval(timer);
                        } else {
                            stat.textContent = Math.floor(current).toLocaleString() + suffix;
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

// Fetch jobs from the API and render them inside #jobsContainer
async function renderJobs() {
    const container = document.getElementById('jobsContainer');

    try {
        const { getJobs } = await import('./api.js');
        const jobs = await getJobs();

        jobs.forEach(job => {
            const card = document.createElement('div');
            card.className = 'job-card';
            card.addEventListener('click', function(event) {
                if (event.target.closest('.apply-btn')) {
                    return;
                }
                event.stopPropagation();
                openJobDetails(job);
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
            applyBtn.addEventListener('click', async function() {
                const { getCurrentUser, isLoggedIn } = await import('./auth.js');

                if (!isLoggedIn()) {
                    window.location.href = 'login.html';
                    return;
                }

                try {
                    const { applyToJob } = await import('./api.js');
                    await applyToJob(job.id, getCurrentUser().id);
                    alert('تم تقديم طلبك بنجاح.');
                } catch (error) {
                    alert(error.message);
                }
            });
            card.appendChild(applyBtn);

            container.appendChild(card);
        });
    } catch (error) {
        container.innerHTML = '<p>تعذر تحميل الوظائف.</p>';
    }
}

renderJobs();

// Update the header based on the current login state
async function updateAuthUI() {
    const { getCurrentUser, isLoggedIn } = await import('./auth.js');

    if (!isLoggedIn()) {
        return;
    }

    const guestActions = document.getElementById('guestActions');
    const userName = document.getElementById('userName');
    const dropdownArrow = document.getElementById('dropdownArrow');

    if (!guestActions || !userName || !dropdownArrow) {
        return;
    }

    guestActions.classList.add('hidden');

    const currentUser = getCurrentUser();
    userName.textContent = currentUser?.full_name ?? 'User';
    userName.hidden = false;
    dropdownArrow.hidden = false;

    if (currentUser?.profile_image) {
        const { API_BASE_URL } = await import('./api.js');
        const profileIcon = document.getElementById('profileIcon');
        if (profileIcon) {
            profileIcon.style.backgroundImage = `url(${API_BASE_URL}${currentUser.profile_image})`;
            profileIcon.style.backgroundSize = 'cover';
            profileIcon.style.backgroundPosition = 'center';
            profileIcon.textContent = '';
        }
    }
}

updateAuthUI();

// Toggle the user menu
function toggleUserMenu() {
    const menu = document.getElementById('userMenu');
    menu.classList.toggle('active');
}

document.getElementById('profileCluster').addEventListener('click', toggleUserMenu);

// Close the user menu when clicking outside
document.addEventListener('click', function(event) {
    const menu = document.getElementById('userMenu');
    const profileCluster = document.getElementById('profileCluster');

    if (!profileCluster.contains(event.target)) {
        menu.classList.remove('active');
    }
});

// Handle logout
const logoutButton = document.getElementById('logoutButton');

if (logoutButton) {
    logoutButton.addEventListener('click', async function() {
        const { logout } = await import('./auth.js');
        logout();

        document.getElementById('userMenu').classList.remove('active');
        document.getElementById('userName').hidden = true;
        document.getElementById('dropdownArrow').hidden = true;
        document.getElementById('guestActions').classList.remove('hidden');

        window.location.href = 'index.html';
    });
}