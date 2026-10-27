/**
 * CineGlow - My Bookings Lookup Script
 * Searches database for reservations and renders printable tickets
 */

document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('search-booking-form');
    const bookingIdInput = document.getElementById('lookup_booking_id');
    const emailInput = document.getElementById('lookup_email');
    const submitBtn = document.getElementById('search-submit-btn');
    const alertBox = document.getElementById('lookup-alert');
    const resultArea = document.getElementById('booking-result-area');

    if (!searchForm) return;

    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Reset UI alerts
        alertBox.style.display = 'none';
        alertBox.className = 'form-alert';
        resultArea.style.display = 'none';
        resultArea.innerHTML = '';

        const bookingId = bookingIdInput.value.trim().toUpperCase();
        const email = emailInput.value.trim().toLowerCase();

        if (!bookingId) {
            showAlert('Please enter your Booking ID (e.g. BK-XXXXXX).', 'error');
            bookingIdInput.focus();
            return;
        }

        if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            showAlert('Please enter a valid registered email address.', 'error');
            emailInput.focus();
            return;
        }

        // Loading state
        const btnText = submitBtn.querySelector('.btn-text');
        const btnSpinner = submitBtn.querySelector('.btn-spinner');
        submitBtn.disabled = true;
        btnText.style.display = 'none';
        btnSpinner.style.display = 'inline-flex';

        try {
            const response = await fetch('/api/my-bookings/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ booking_id: bookingId, email: email })
            });

            const data = await response.json();

            if (response.ok && data.success) {
                renderBookingTicket(data.booking);
                showToast('Booking details found!', 'success');
            } else {
                showAlert(data.error || 'No booking found with the provided details.', 'error');
                showToast(data.error || 'No booking found', 'error');
            }
        } catch (err) {
            console.error('Error searching booking:', err);
            showAlert('Network error while searching. Please try again.', 'error');
            showToast('Search failed due to network error', 'error');
        } finally {
            submitBtn.disabled = false;
            btnText.style.display = 'inline-flex';
            btnSpinner.style.display = 'none';
        }
    });

    function showAlert(msg, type = 'error') {
        alertBox.className = `form-alert alert-${type}`;
        alertBox.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> ${msg}`;
        alertBox.style.display = 'flex';
    }

    function renderBookingTicket(b) {
        const seatsList = b.seats.split(',').map(s => s.trim()).filter(Boolean);
        const seatBadges = seatsList.map(seat => `<span class="seat-pill">${seat}</span>`).join('');

        resultArea.innerHTML = `
            <div class="ticket-action-bar" style="margin-bottom: 20px;">
                <button type="button" class="btn btn-primary" onclick="window.print()">
                    <i class="fa-solid fa-print"></i> Print Ticket
                </button>
                <a href="/confirmation/${b.booking_id}" class="btn btn-outline">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i> Open Confirmation Page
                </a>
            </div>

            <div class="ticket-wrapper">
                <div class="cinema-ticket">
                    <!-- Left Stub -->
                    <div class="ticket-main-stub">
                        <div class="ticket-header">
                            <div class="ticket-logo">
                                <i class="fa-solid fa-film text-accent"></i> CINE<span class="text-accent">GLOW</span> CINEMAS
                            </div>
                            <div class="ticket-type-badge">CONFIRMED ADMISSION</div>
                        </div>

                        <div class="ticket-body">
                            <div class="ticket-poster-col">
                                <img src="${b.poster_url}" alt="${b.movie_title}" class="ticket-poster-img">
                            </div>

                            <div class="ticket-details-col">
                                <span class="ticket-genre">${b.genre} • ${b.duration}</span>
                                <h2 class="ticket-movie-title">${b.movie_title}</h2>

                                <div class="ticket-meta-grid">
                                    <div class="ticket-meta-cell">
                                        <span class="meta-label">DATE</span>
                                        <span class="meta-value">${b.booking_date}</span>
                                    </div>
                                    <div class="ticket-meta-cell">
                                        <span class="meta-label">SHOWTIME</span>
                                        <span class="meta-value text-accent">${b.showtime}</span>
                                    </div>
                                    <div class="ticket-meta-cell">
                                        <span class="meta-label">AUDITORIUM</span>
                                        <span class="meta-value">Audi 1 (4K Laser)</span>
                                    </div>
                                    <div class="ticket-meta-cell">
                                        <span class="meta-label">TICKETS</span>
                                        <span class="meta-value">${b.ticket_quantity} Seat(s)</span>
                                    </div>
                                </div>

                                <div class="ticket-seats-highlight">
                                    <span class="meta-label">RESERVED SEAT(S)</span>
                                    <div class="seats-badges-list">
                                        ${seatBadges}
                                    </div>
                                </div>

                                <div class="ticket-customer-info">
                                    <div><i class="fa-regular fa-user text-muted"></i> <strong>Name:</strong> ${b.customer_name}</div>
                                    <div><i class="fa-regular fa-envelope text-muted"></i> <strong>Email:</strong> ${b.email}</div>
                                    <div><i class="fa-solid fa-phone text-muted"></i> <strong>Phone:</strong> ${b.phone}</div>
                                </div>
                            </div>
                        </div>

                        <div class="ticket-footer-strip">
                            <span class="fine-print"><i class="fa-solid fa-shield-halved"></i> Verified SQLite Database Record</span>
                            <span class="timestamp">Booked on: ${b.created_at}</span>
                        </div>
                    </div>

                    <!-- Perforation -->
                    <div class="ticket-perforation">
                        <div class="perf-notch notch-top"></div>
                        <div class="perf-line"></div>
                        <div class="perf-notch notch-bottom"></div>
                    </div>

                    <!-- Right Stub -->
                    <div class="ticket-side-stub">
                        <div class="stub-cinema-tag">CINEGLOW PASS</div>
                        
                        <div class="stub-booking-id">
                            <span class="stub-label">BOOKING ID</span>
                            <span class="stub-code">${b.booking_id}</span>
                        </div>

                        <div class="stub-info-block">
                            <div class="stub-info-row">
                                <span>Seats:</span>
                                <strong>${b.seats}</strong>
                            </div>
                            <div class="stub-info-row">
                                <span>Time:</span>
                                <strong>${b.showtime}</strong>
                            </div>
                            <div class="stub-info-row">
                                <span>Date:</span>
                                <strong>${b.booking_date}</strong>
                            </div>
                        </div>

                        <div class="stub-total-block">
                            <span class="stub-label">TOTAL PAID</span>
                            <span class="stub-amount">₹${parseFloat(b.total_amount).toFixed(2)}</span>
                        </div>

                        <div class="barcode-container">
                            <div class="mockup-barcode">
                                <span></span><span></span><span></span><span></span><span></span>
                                <span></span><span></span><span></span><span></span><span></span>
                                <span></span><span></span><span></span><span></span><span></span>
                                <span></span><span></span><span></span><span></span><span></span>
                            </div>
                            <span class="barcode-number">${b.booking_id}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;

        resultArea.style.display = 'block';
        resultArea.scrollIntoView({ behavior: 'smooth' });
    }
});
