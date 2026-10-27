/**
 * CineGlow - Interactive Movie & Seat Booking Engine
 * Handles Date/Showtime selection, Seat Grid Rendering,
 * Real-time Price Calculation, and Transactional Booking Submission
 */

document.addEventListener('DOMContentLoaded', () => {
    if (typeof BOOKING_CONFIG === 'undefined') return;

    // State Variables
    let selectedDate = '';
    let selectedTime = '';
    let selectedSeats = new Set();
    let bookedSeats = new Set();
    const ticketPrice = BOOKING_CONFIG.ticketPrice || 200;

    // DOM Elements
    const dateButtons = document.querySelectorAll('.date-pill-btn');
    const timeButtons = document.querySelectorAll('.time-pill-btn');
    const seatRowsWrapper = document.getElementById('seat-rows-wrapper');
    const seatLoadingOverlay = document.getElementById('seat-loading-overlay');
    const pastTimeNotice = document.getElementById('past-time-notice');

    // Summary Elements
    const summaryDateEl = document.getElementById('summary-date');
    const summaryTimeEl = document.getElementById('summary-time');
    const summarySeatsEl = document.getElementById('summary-seats');
    const summaryQuantityEl = document.getElementById('summary-quantity');
    const summaryTotalEl = document.getElementById('summary-total');

    // Booking Form Elements
    const bookingForm = document.getElementById('booking-form');
    const nameInput = document.getElementById('customer_name');
    const emailInput = document.getElementById('customer_email');
    const phoneInput = document.getElementById('customer_phone');
    const confirmBtn = document.getElementById('confirm-booking-btn');
    const formAlert = document.getElementById('form-general-alert');

    // Error message spans
    const nameError = document.getElementById('name-error');
    const emailError = document.getElementById('email-error');
    const phoneError = document.getElementById('phone-error');

    // Cinema Layout Structure: Rows A-F, 8 seats per row (4-aisle-4)
    const ROWS = ['A', 'B', 'C', 'D', 'E', 'F'];
    const SEATS_PER_ROW = 8;

    /**
     * Helper to test if a time on a given date has passed compared to local browser time
     */
    function isShowtimePassed(dateStr, timeStr) {
        const now = new Date();
        const todayStr = now.toISOString().split('T')[0];

        if (dateStr < todayStr) return true;
        if (dateStr > todayStr) return false;

        // Same day: parse time "10:00 AM", "1:30 PM", "5:00 PM", "8:30 PM"
        const [timePart, modifier] = timeStr.split(' ');
        let [hours, minutes] = timePart.split(':').map(Number);

        if (modifier === 'PM' && hours < 12) hours += 12;
        if (modifier === 'AM' && hours === 12) hours = 0;

        const showDate = new Date();
        showDate.setHours(hours, minutes, 0, 0);

        return showDate < now;
    }

    /**
     * Updates showtime buttons availability for the selected date
     */
    function updateShowtimesForDate() {
        let hasActiveSlot = false;
        let pastCount = 0;

        timeButtons.forEach(btn => {
            const time = btn.getAttribute('data-time');
            const isPassed = isShowtimePassed(selectedDate, time);

            if (isPassed) {
                btn.disabled = true;
                btn.classList.remove('active');
                pastCount++;
            } else {
                btn.disabled = false;
                if (!hasActiveSlot) {
                    btn.classList.add('active');
                    selectedTime = time;
                    hasActiveSlot = true;
                }
            }
        });

        if (pastTimeNotice) {
            pastTimeNotice.style.display = (pastCount > 0) ? 'flex' : 'none';
        }

        // If no slot was available today (all passed)
        if (!hasActiveSlot) {
            selectedTime = '';
            showToast('All showtimes for today have passed. Please select a future date.', 'info');
        }

        updateSummary();
        fetchBookedSeats();
    }

    /**
     * Builds the interactive cinema seating plan
     */
    function renderSeatGrid() {
        seatRowsWrapper.innerHTML = '';

        ROWS.forEach(rowLetter => {
            const rowDiv = document.createElement('div');
            rowDiv.className = 'seat-row';

            // Left Row Label
            const leftLabel = document.createElement('span');
            leftLabel.className = 'row-label';
            leftLabel.textContent = rowLetter;
            rowDiv.appendChild(leftLabel);

            // Left Subgroup: Seats 1 to 4
            const leftGroup = document.createElement('div');
            leftGroup.className = 'seats-subgroup';
            for (let i = 1; i <= 4; i++) {
                leftGroup.appendChild(createSeatElement(rowLetter, i));
            }
            rowDiv.appendChild(leftGroup);

            // Central Aisle Gap
            const aisleGap = document.createElement('div');
            aisleGap.className = 'aisle-gap';
            rowDiv.appendChild(aisleGap);

            // Right Subgroup: Seats 5 to 8
            const rightGroup = document.createElement('div');
            rightGroup.className = 'seats-subgroup';
            for (let i = 5; i <= 8; i++) {
                rightGroup.appendChild(createSeatElement(rowLetter, i));
            }
            rowDiv.appendChild(rightGroup);

            // Right Row Label
            const rightLabel = document.createElement('span');
            rightLabel.className = 'row-label';
            rightLabel.textContent = rowLetter;
            rowDiv.appendChild(rightLabel);

            seatRowsWrapper.appendChild(rowDiv);
        });
    }

    /**
     * Creates an individual seat button element
     */
    function createSeatElement(rowLetter, seatNum) {
        const seatId = `${rowLetter}${seatNum}`;
        const seatBtn = document.createElement('button');
        seatBtn.type = 'button';
        seatBtn.className = 'seat-btn';
        seatBtn.id = `seat-${seatId}`;
        seatBtn.setAttribute('data-seat-id', seatId);
        seatBtn.textContent = seatId;

        // Apply state: booked, selected, or available
        if (bookedSeats.has(seatId)) {
            seatBtn.classList.add('seat-booked');
            seatBtn.disabled = true;
            seatBtn.title = `Seat ${seatId} is already booked`;
        } else if (selectedSeats.has(seatId)) {
            seatBtn.classList.add('seat-selected');
            seatBtn.title = `Seat ${seatId} selected`;
        } else {
            seatBtn.classList.add('seat-available');
            seatBtn.title = `Seat ${seatId} available - ₹${ticketPrice}`;
        }

        // Click handler to toggle selection
        seatBtn.addEventListener('click', () => {
            if (bookedSeats.has(seatId)) return;

            if (selectedSeats.has(seatId)) {
                selectedSeats.delete(seatId);
                seatBtn.classList.remove('seat-selected');
                seatBtn.classList.add('seat-available');
            } else {
                selectedSeats.add(seatId);
                seatBtn.classList.remove('seat-available');
                seatBtn.classList.add('seat-selected');
            }

            updateSummary();
            validateForm();
        });

        return seatBtn;
    }

    /**
     * Fetches live booked seats from SQLite database for the selected movie, date, and showtime
     */
    async function fetchBookedSeats() {
        if (!selectedDate || !selectedTime) {
            bookedSeats.clear();
            renderSeatGrid();
            return;
        }

        seatLoadingOverlay.style.display = 'flex';

        try {
            const url = `/api/seats?movie_id=${BOOKING_CONFIG.movieId}&date=${encodeURIComponent(selectedDate)}&showtime=${encodeURIComponent(selectedTime)}`;
            const response = await fetch(url);
            const data = await response.json();

            bookedSeats.clear();
            if (data.booked_seats && Array.isArray(data.booked_seats)) {
                data.booked_seats.forEach(s => bookedSeats.add(s));
            }

            // Remove any currently selected seats that are already booked
            selectedSeats.forEach(s => {
                if (bookedSeats.has(s)) {
                    selectedSeats.delete(s);
                }
            });

            renderSeatGrid();
            updateSummary();
            validateForm();

        } catch (err) {
            console.error('Failed to fetch seat availability:', err);
            showToast('Unable to check seat availability. Please check your network connection.', 'error');
        } finally {
            seatLoadingOverlay.style.display = 'none';
        }
    }

    /**
     * Updates the checkout summary card with live numbers
     */
    function updateSummary() {
        // Date display
        const activeDateBtn = document.querySelector('.date-pill-btn.active');
        if (activeDateBtn) {
            const day = activeDateBtn.querySelector('.date-day').textContent;
            const sub = activeDateBtn.querySelector('.date-sub').textContent;
            summaryDateEl.textContent = `${day}, ${sub}`;
        } else {
            summaryDateEl.textContent = selectedDate || '--';
        }

        // Showtime display
        summaryTimeEl.textContent = selectedTime || 'Select a time';

        // Seats & Quantity
        const seatArray = Array.from(selectedSeats).sort();
        if (seatArray.length > 0) {
            summarySeatsEl.textContent = seatArray.join(', ');
            summarySeatsEl.classList.add('highlight-seats');
        } else {
            summarySeatsEl.textContent = 'None selected';
            summarySeatsEl.classList.remove('highlight-seats');
        }

        const count = seatArray.length;
        summaryQuantityEl.textContent = count;

        // Total Amount: ₹200 * count
        const total = count * ticketPrice;
        summaryTotalEl.textContent = `₹${total.toLocaleString('en-IN')}`;

        // Confirm Button Text
        const btnText = confirmBtn.querySelector('.btn-text');
        if (count > 0) {
            btnText.innerHTML = `<i class="fa-solid fa-lock"></i> Confirm Booking (₹${total.toLocaleString('en-IN')})`;
        } else {
            btnText.innerHTML = `<i class="fa-solid fa-lock"></i> Select Seats to Book`;
        }
    }

    /**
     * Validates input fields and enables/disables the confirm button
     */
    function validateForm() {
        const nameVal = nameInput.value.trim();
        const emailVal = emailInput.value.trim();
        const phoneVal = phoneInput.value.trim();
        const hasSeats = selectedSeats.size > 0;
        const hasSlot = selectedDate && selectedTime;

        let isValid = true;

        if (nameVal.length < 2) isValid = false;
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailVal)) isValid = false;
        if (!/^\+?[0-9\s-]{7,15}$/.test(phoneVal)) isValid = false;
        if (!hasSeats || !hasSlot) isValid = false;

        confirmBtn.disabled = !isValid;
        return isValid;
    }

    // Input event listeners for real-time validation
    nameInput.addEventListener('input', () => {
        if (nameInput.value.trim().length >= 2) {
            nameError.textContent = '';
            nameInput.classList.remove('is-invalid');
        }
        validateForm();
    });

    emailInput.addEventListener('input', () => {
        if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailInput.value.trim())) {
            emailError.textContent = '';
            emailInput.classList.remove('is-invalid');
        }
        validateForm();
    });

    phoneInput.addEventListener('input', () => {
        if (/^\+?[0-9\s-]{7,15}$/.test(phoneInput.value.trim())) {
            phoneError.textContent = '';
            phoneInput.classList.remove('is-invalid');
        }
        validateForm();
    });

    // Date button clicks
    dateButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            dateButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedDate = btn.getAttribute('data-date');
            
            // Clear seat selections when date changes
            selectedSeats.clear();
            updateShowtimesForDate();
        });
    });

    // Time button clicks
    timeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.disabled) return;
            timeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedTime = btn.getAttribute('data-time');

            // Clear seat selections when showtime changes
            selectedSeats.clear();
            updateSummary();
            fetchBookedSeats();
        });
    });

    // Form Submission Handling
    bookingForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Hide previous alerts
        formAlert.style.display = 'none';
        formAlert.className = 'form-alert';

        const nameVal = nameInput.value.trim();
        const emailVal = emailInput.value.trim();
        const phoneVal = phoneInput.value.trim();

        // Detailed field checks
        let hasError = false;

        if (nameVal.length < 2) {
            nameError.textContent = 'Please enter your full name (at least 2 letters).';
            nameInput.classList.add('is-invalid');
            hasError = true;
        }

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailVal)) {
            emailError.textContent = 'Please enter a valid email address.';
            emailInput.classList.add('is-invalid');
            hasError = true;
        }

        if (!/^\+?[0-9\s-]{7,15}$/.test(phoneVal)) {
            phoneError.textContent = 'Please enter a valid phone number (min 7 digits).';
            phoneInput.classList.add('is-invalid');
            hasError = true;
        }

        if (selectedSeats.size === 0) {
            formAlert.className = 'form-alert alert-error';
            formAlert.textContent = 'Please select at least one seat on the cinema plan.';
            formAlert.style.display = 'flex';
            hasError = true;
        }

        if (!selectedDate || !selectedTime) {
            formAlert.className = 'form-alert alert-error';
            formAlert.textContent = 'Please choose a valid date and showtime.';
            formAlert.style.display = 'flex';
            hasError = true;
        }

        if (hasError) return;

        // Initiate Booking Request
        const btnText = confirmBtn.querySelector('.btn-text');
        const btnSpinner = confirmBtn.querySelector('.btn-spinner');

        confirmBtn.disabled = true;
        btnText.style.display = 'none';
        btnSpinner.style.display = 'inline-flex';

        const payload = {
            movie_id: BOOKING_CONFIG.movieId,
            booking_date: selectedDate,
            showtime: selectedTime,
            seats: Array.from(selectedSeats),
            customer_name: nameVal,
            email: emailVal,
            phone: phoneVal
        };

        try {
            const response = await fetch('/api/book', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                showToast('Booking successful! Redirecting to your ticket...', 'success');
                setTimeout(() => {
                    window.location.href = result.redirect_url;
                }, 700);
            } else {
                // Booking error or conflict (e.g. seat already booked)
                formAlert.className = 'form-alert alert-error';
                formAlert.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${result.error || 'Booking failed. Please try again.'}`;
                formAlert.style.display = 'flex';
                showToast(result.error || 'Booking error', 'error');

                // Refresh seat plan to reflect newest booked seats
                await fetchBookedSeats();

                confirmBtn.disabled = false;
                btnText.style.display = 'inline-flex';
                btnSpinner.style.display = 'none';
            }
        } catch (err) {
            console.error('Booking submission error:', err);
            formAlert.className = 'form-alert alert-error';
            formAlert.textContent = 'Network error while processing booking. Please try again.';
            formAlert.style.display = 'flex';
            showToast('Network error while processing booking', 'error');

            confirmBtn.disabled = false;
            btnText.style.display = 'inline-flex';
            btnSpinner.style.display = 'none';
        }
    });

    // Initialize Default State
    const activeDateBtn = document.querySelector('.date-pill-btn.active');
    if (activeDateBtn) {
        selectedDate = activeDateBtn.getAttribute('data-date');
    }
    updateShowtimesForDate();
});
