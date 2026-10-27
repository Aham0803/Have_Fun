/**
 * CineGlow - Main Javascript File
 * Handles Global Navigation, Toast Notifications, and Movie Search/Filtering
 */

// Toast notification helper
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconClass = 'fa-circle-info';
    if (type === 'success') iconClass = 'fa-circle-check';
    if (type === 'error') iconClass = 'fa-triangle-exclamation';

    toast.innerHTML = `
        <i class="fa-solid ${iconClass}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Search and Genre Filter logic on Home Page
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('movie-search-input');
    const clearSearchBtn = document.getElementById('clear-search-btn');
    const genrePills = document.querySelectorAll('.genre-pill');
    const movieCards = document.querySelectorAll('.movie-card');
    const noResultsBox = document.getElementById('no-movies-found');
    const resetFiltersBtn = document.getElementById('reset-filters-btn');

    if (!movieCards.length) return; // Not on home page

    let currentGenre = 'all';
    let searchQuery = '';

    function filterMovies() {
        let visibleCount = 0;
        const q = searchQuery.toLowerCase().trim();

        movieCards.forEach(card => {
            const title = card.getAttribute('data-title') || '';
            const genre = card.getAttribute('data-genre') || '';

            const matchesQuery = !q || title.includes(q) || genre.toLowerCase().includes(q);
            const matchesGenre = (currentGenre === 'all') || genre.toLowerCase().includes(currentGenre.toLowerCase());

            if (matchesQuery && matchesGenre) {
                card.style.display = 'flex';
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });

        if (noResultsBox) {
            noResultsBox.style.display = (visibleCount === 0) ? 'block' : 'none';
        }

        if (clearSearchBtn) {
            clearSearchBtn.style.display = q ? 'block' : 'none';
        }
    }

    // Search input handler
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchQuery = e.target.value;
            filterMovies();
        });
    }

    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', () => {
            searchInput.value = '';
            searchQuery = '';
            filterMovies();
            searchInput.focus();
        });
    }

    // Genre pills handler
    genrePills.forEach(pill => {
        pill.addEventListener('click', () => {
            genrePills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            currentGenre = pill.getAttribute('data-genre');
            filterMovies();
        });
    });

    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            searchQuery = '';
            currentGenre = 'all';
            genrePills.forEach(p => {
                p.classList.toggle('active', p.getAttribute('data-genre') === 'all');
            });
            filterMovies();
        });
    }
});
