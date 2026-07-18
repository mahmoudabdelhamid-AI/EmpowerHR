// Toggle dropdown modal
function toggleDropdown() {
    const modal = document.getElementById('dropdownModal');
    modal.classList.toggle('active');
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
            const numbers = entry.target.querySelectorAll('.stat-number');
            numbers.forEach(num => {
                const target = parseInt(num.textContent.replace(/[^0-9]/g, ''));
                if (target && !num.classList.contains('animated')) {
                    let current = 0;
                    const increment = target / 50;
                    const timer = setInterval(() => {
                        current += increment;
                        if (current >= target) {
                            num.innerHTML = num.innerHTML.replace(/[0-9,]+/, target.toLocaleString());
                            clearInterval(timer);
                            num.classList.add('animated');
                        } else {
                            num.innerHTML = num.innerHTML.replace(/[0-9,]+/, Math.floor(current).toLocaleString());
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
            card.appendChild(applyBtn);

            container.appendChild(card);
        });
    } catch (error) {
        container.innerHTML = '<p>تعذر تحميل الوظائف.</p>';
    }
}

renderJobs();
