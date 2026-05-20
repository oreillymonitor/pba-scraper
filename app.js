document.addEventListener('DOMContentLoaded', () => {
    const scheduleGrid = document.getElementById('scheduleGrid');
    const loading = document.getElementById('loading');
    const emptyState = document.getElementById('emptyState');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const themeToggle = document.getElementById('themeToggle');
    const pastEventsToggle = document.getElementById('pastEventsToggle');
    const broadcastOnlyToggle = document.getElementById('broadcastOnlyToggle');

    let allEvents = [];
    let currentFilter = 'all';
    let showPast = false;
    let broadcastOnly = false;

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

    // Broadcast Only Logic
    broadcastOnlyToggle.addEventListener('change', (e) => {
        broadcastOnly = e.target.checked;
        applyFilters();
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

        combined.sort((a, b) => {
            if (a.start_time && !b.start_time) return -1;
            if (!a.start_time && b.start_time) return 1;
            return 0;
        });

        for (const event of combined) {
            // Normalize for comparison
            let tournament = event.tournament.toLowerCase()
                .replace(/go bowling\s*/i, '')
                .replace(/[^a-z0-9]/g, '');
            
            // Special case for U.S. Open variants
            if (tournament.includes('uswomensopen')) tournament = 'uswomensopen';
            if (tournament.includes('usopen')) tournament = 'usopen';
            
            // Standardize Date Label (e.g., Jun -> June)
            const monthMap = {
                'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April',
                'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August',
                'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December'
            };
            
            let normalizedDate = event.date;
            for (const [short, full] of Object.entries(monthMap)) {
                if (normalizedDate.toLowerCase().startsWith(short) && !normalizedDate.toLowerCase().startsWith(full.toLowerCase())) {
                    normalizedDate = normalizedDate.replace(new RegExp(short, 'i'), full);
                }
            }
            
            // Handle ET in date vs time
            let time = event.time;
            if (normalizedDate.toUpperCase().includes(' ET')) {
                normalizedDate = normalizedDate.replace(/ ET/i, '').trim();
                if (!time.includes('ET')) time = `${time} ET`.trim();
            }

            const fuzzyMatch = merged.find(m => {
                const mDate = m.date.replace(/[^a-z0-9]/g, '').toLowerCase();
                const eDate = normalizedDate.replace(/[^a-z0-9]/g, '').toLowerCase();
                const dateMatch = (mDate === eDate || mDate.startsWith(eDate) || eDate.startsWith(mDate));
                if (!dateMatch) return false;

                const mName = m.tournament.toLowerCase().replace(/go bowling\s*/i, '').replace(/[^a-z0-9]/g, '');
                const eName = event.tournament.toLowerCase().replace(/go bowling\s*/i, '').replace(/[^a-z0-9]/g, '');
                const isUSOpen = (n) => n.includes('usopen') || n.includes('uswomensopen') || n.includes('womensopen');
                
                const nameMatch = (isUSOpen(mName) && isUSOpen(eName)) || mName.includes(eName) || eName.includes(mName);
                return nameMatch;
            });

            if (fuzzyMatch) {
                if (!fuzzyMatch.time && time) fuzzyMatch.time = time;
                if (!fuzzyMatch.start_time && event.start_time) fuzzyMatch.start_time = event.start_time;
                
                const isGeneric = (loc) => !loc || loc.includes('Details') || loc.includes('Online') || loc.includes('TV');
                if (isGeneric(fuzzyMatch.location) && !isGeneric(event.location)) {
                    fuzzyMatch.location = event.location;
                }
                continue;
            }

            // Update the event object with normalized data
            event.date = normalizedDate;
            event.time = time;
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
        console.log("Applying filters:", { currentFilter, showPast, broadcastOnly });
        let filtered = allEvents;
        
        // Tour Filter
        if (currentFilter !== 'all') {
            filtered = filtered.filter(e => e.tour === currentFilter);
        }

        // Broadcast Filter
        if (broadcastOnly) {
            filtered = filtered.filter(e => e.channel.toLowerCase() !== 'bowltv');
        }

        // Upcoming Filter
        if (!showPast) {
            const now = new Date();
            const bufferTime = 6 * 60 * 60 * 1000;
            filtered = filtered.filter(e => {
                const eventDate = parseDate(e);
                return (eventDate.getTime() + bufferTime) >= now.getTime();
            });
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
            
            // Format Date for display
            const dateObj = parseDate(event);
            const dateOptions = { weekday: 'long', month: 'long', day: 'numeric' };
            const dateText = dateObj.toLocaleDateString('en-US', dateOptions);
            
            // Format Time for display
            let timeText = event.time;
            if (timeText) {
                // Ensure ET is there
                if (!timeText.toUpperCase().includes('ET')) {
                    timeText = `${timeText} ET`;
                }
                // Standardize format (e.g., 7 PM ET)
                timeText = timeText.replace(/\s*ET/i, ' ET');
            }

            const location = event.location || 'Online / TV';

            card.innerHTML = `
                <div class="card-date-col">
                    <span class="date-text">${dateText}</span>
                    ${timeText ? `<span class="time-text">${timeText}</span>` : ''}
                    <span class="tour-tag tour-${event.tour}">${tourName}</span>
                </div>
                <div class="card-main-col">
                    <h3 class="event-title">${event.tournament}</h3>
                    <span class="event-location">📍 ${location}</span>
                </div>
                <div class="card-channel-col">
                    <span class="channel-name">${event.channel}</span>
                    ${event.channel_logo ? `<img src="${event.channel_logo}" alt="${event.channel}" class="event-logo">` : ''}
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
