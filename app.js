document.addEventListener('DOMContentLoaded', () => {
    const scheduleGrid = document.getElementById('scheduleGrid');
    const loading = document.getElementById('loading');
    const emptyState = document.getElementById('emptyState');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const themeToggle = document.getElementById('themeToggle');
    const pastEventsToggle = document.getElementById('pastEventsToggle');

    let allEvents = [];
    let currentFilter = 'all';
    let showPast = false;

    // Theme Logic
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
    }

    themeToggle.addEventListener('click', () => {
        document.body.classList.toggle('light-theme');
        const theme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
        localStorage.setItem('theme', theme);
    });

    // Past Events Logic
    pastEventsToggle.addEventListener('change', (e) => {
        showPast = e.target.checked;
        applyFilters();
    });

    async function loadData() {
        try {
            const [pbaRes, pwbaRes, usbcRes] = await Promise.all([
                fetch('pba_tv_schedule.json').then(r => r.ok ? r.json() : []),
                fetch('pwba_tv_schedule.json').then(r => r.ok ? r.json() : []),
                fetch('usbc_tv_schedule.json').then(r => r.ok ? r.json() : [])
            ]);

            const pba = pbaRes.map(e => ({ ...e, tour: 'pba' }));
            const pwba = pwbaRes.map(e => ({ ...e, tour: 'pwba' }));
            const usbc = usbcRes.map(e => ({ ...e, tour: 'usbc' }));

            allEvents = mergeSchedules(pba, pwba, usbc);
            applyFilters();
        } catch (error) {
            console.error('Error loading schedule:', error);
            loading.innerHTML = '<p>Failed to load schedules. Please try again later.</p>';
        }
    }

    function mergeSchedules(pba, pwba, usbc) {
        const combined = [...pba, ...pwba, ...usbc];
        const merged = [];
        const seen = new Set();

        combined.sort((a, b) => {
            if (a.start_time && !b.start_time) return -1;
            if (!a.start_time && b.start_time) return 1;
            return 0;
        });

        for (const event of combined) {
            const normalizedName = event.tournament.toLowerCase().replace(/[^a-z0-9]/g, '');
            const datePrefix = event.date_label.split(' ')[0].replace(/[^a-z0-9]/g, '');
            const key = `${normalizedName}_${datePrefix}`;
            
            if (seen.has(key)) continue;
            
            const fuzzyMatch = merged.find(m => {
                const mDate = m.date_label.split(' ')[0].replace(/[^a-z0-9]/g, '');
                if (mDate !== datePrefix) return false;
                const mName = m.tournament.toLowerCase();
                const eName = event.tournament.toLowerCase();
                return mName.includes(eName) || eName.includes(mName);
            });

            if (fuzzyMatch) {
                if (!fuzzyMatch.channel_logo && event.channel_logo) {
                    fuzzyMatch.channel_logo = event.channel_logo;
                }
                continue;
            }

            seen.add(key);
            merged.push(event);
        }

        return merged.sort((a, b) => parseDate(a) - parseDate(b));
    }

    function parseDate(event) {
        if (event.start_time) {
            const year = event.start_time.substring(0, 4);
            const month = event.start_time.substring(4, 6);
            const day = event.start_time.substring(6, 8);
            const hour = event.start_time.substring(9, 11);
            const min = event.start_time.substring(11, 13);
            return new Date(`${year}-${month}-${day}T${hour}:${min}:00Z`);
        }

        const months = {
            'jan': 0, 'feb': 1, 'mar': 2, 'apr': 3, 'may': 4, 'jun': 5,
            'jul': 6, 'aug': 7, 'sep': 8, 'oct': 9, 'nov': 10, 'dec': 11
        };

        const parts = event.date_label.toLowerCase().split(/[ \/]/);
        let month = 4; // Default to May
        let day = 1;

        for (const part of parts) {
            const clean = part.replace(/[^a-z]/g, '');
            if (months[clean] !== undefined) month = months[clean];
            const num = part.replace(/[^0-9]/g, '');
            if (num && !isNaN(num)) day = parseInt(num);
        }

        const date = new Date();
        date.setFullYear(2026);
        date.setMonth(month);
        date.setDate(day);
        date.setHours(12, 0, 0, 0);
        return date;
    }

    function applyFilters() {
        let filtered = allEvents;
        
        // Tour Filter
        if (currentFilter !== 'all') {
            filtered = filtered.filter(e => e.tour === currentFilter);
        }

        // Upcoming Filter
        if (!showPast) {
            const now = new Date();
            // Move 'now' back by 4 hours to account for ongoing events
            now.setHours(now.getHours() - 4); 
            filtered = filtered.filter(e => parseDate(e) >= now);
        }

        renderSchedule(filtered);
    }

    function renderSchedule(events) {
        loading.classList.add('hidden');
        scheduleGrid.innerHTML = '';
        
        if (events.length === 0) {
            scheduleGrid.classList.add('hidden');
            emptyState.classList.remove('hidden');
            return;
        }

        scheduleGrid.classList.remove('hidden');
        emptyState.classList.add('hidden');

        events.forEach(event => {
            const card = document.createElement('div');
            card.className = `event-card tour-${event.tour}`;

            const tourName = event.tour.toUpperCase();
            const displayDate = event.date_label;
            const location = event.location || 'See Event Details';

            card.innerHTML = `
                <div class="card-header">
                    <span class="tour-tag tour-${event.tour}">${tourName}</span>
                    ${event.channel_logo ? `<img src="${event.channel_logo}" alt="${event.channel}" class="event-logo">` : ''}
                </div>
                <h3 class="event-title">${event.tournament}</h3>
                <div class="event-details">
                    <div class="detail-item">
                        <span>📅</span>
                        <span>${displayDate}</span>
                    </div>
                    <div class="detail-item">
                        <span>📍</span>
                        <span>${location}</span>
                    </div>
                </div>
                <div class="channel-info">
                    <span>📺</span>
                    <span>${event.channel}</span>
                </div>
            `;
            scheduleGrid.appendChild(card);
        });
    }

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.getAttribute('data-filter');
            applyFilters();
        });
    });

    loadData();
});
