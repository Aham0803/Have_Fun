import os
import re
import uuid
import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from database.db import get_db_connection, init_db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'cineglow-secret-key-cinema-ticket-booking-2026'

TICKET_PRICE = 200  # ₹200 per seat

# Initialize database on app startup
with app.app_context():
    init_db()

def is_past_slot(date_str, time_str):
    """
    Checks if a given date and showtime have already passed compared to now.
    date_str: 'YYYY-MM-DD'
    time_str: e.g. '10:00 AM', '1:30 PM', '5:00 PM', '8:30 PM'
    """
    try:
        now = datetime.datetime.now()
        slot_dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %I:%M %p")
        return slot_dt < now
    except Exception:
        return False

# ==================== WEB ROUTES ====================

@app.route('/')
def index():
    """Home page: displays hero banner, featured movies list, search/genre filters."""
    conn = get_db_connection()
    movies = conn.execute("SELECT * FROM movies ORDER BY rating DESC").fetchall()
    conn.close()
    return render_template('index.html', movies=movies)

@app.route('/book/<int:movie_id>')
def book_movie(movie_id):
    """Booking page: allows selecting date, showtime, seats, and entering user details."""
    conn = get_db_connection()
    movie = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    conn.close()

    if not movie:
        abort(404)

    # Generate dates for next 7 days starting from today
    today = datetime.date.today()
    available_dates = []
    for i in range(7):
        d = today + datetime.timedelta(days=i)
        available_dates.append({
            "iso": d.strftime("%Y-%m-%d"),
            "display": d.strftime("%a, %b %d"),
            "is_today": (i == 0)
        })

    showtimes = ["10:00 AM", "1:30 PM", "5:00 PM", "8:30 PM"]

    return render_template(
        'book.html',
        movie=movie,
        available_dates=available_dates,
        showtimes=showtimes,
        ticket_price=TICKET_PRICE
    )

@app.route('/confirmation/<booking_id>')
def confirmation(booking_id):
    """Displays booking confirmation details and ticket view."""
    conn = get_db_connection()
    booking = conn.execute("""
        SELECT b.*, m.title as movie_title, m.poster_url, m.duration, m.genre
        FROM bookings b
        JOIN movies m ON b.movie_id = m.id
        WHERE b.booking_id = ?
    """, (booking_id.strip().upper(),)).fetchone()
    conn.close()

    if not booking:
        return render_template('confirmation.html', not_found=True, booking_id=booking_id)

    # Format created_at if available
    seat_list = [s.strip() for s in booking['seats'].split(',') if s.strip()]

    return render_template('confirmation.html', booking=booking, seat_list=seat_list)

@app.route('/my-bookings', methods=['GET'])
def my_bookings():
    """Page to search and retrieve bookings by Booking ID and Email."""
    return render_template('my_bookings.html')

# ==================== API ENDPOINTS ====================

@app.route('/api/seats', methods=['GET'])
def get_booked_seats():
    """
    Returns a list of already booked seat identifiers for a specific movie, date, and showtime.
    Query params: movie_id, date, showtime
    """
    movie_id = request.args.get('movie_id')
    date_str = request.args.get('date')
    showtime = request.args.get('showtime')

    if not movie_id or not date_str or not showtime:
        return jsonify({"error": "Missing required query parameters"}), 400

    conn = get_db_connection()
    rows = conn.execute("""
        SELECT seat_number FROM booked_seats
        WHERE movie_id = ? AND show_date = ? AND showtime = ?
    """, (movie_id, date_str, showtime)).fetchall()
    conn.close()

    booked = [r['seat_number'] for r in rows]
    return jsonify({"booked_seats": booked})

@app.route('/api/book', methods=['POST'])
def process_booking():
    """
    Validates form data, checks seat conflicts inside an atomic SQLite transaction,
    saves booking details, records booked seats, and returns booking confirmation ID.
    """
    data = request.get_json() or {}

    movie_id = data.get('movie_id')
    booking_date = data.get('booking_date', '').strip()
    showtime = data.get('showtime', '').strip()
    seats = data.get('seats', [])
    customer_name = data.get('customer_name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()

    # 1. Validation
    if not movie_id:
        return jsonify({"success": False, "error": "Please select a valid movie."}), 400
    if not booking_date:
        return jsonify({"success": False, "error": "Please select a booking date."}), 400
    if not showtime:
        return jsonify({"success": False, "error": "Please select a showtime."}), 400
    if not seats or not isinstance(seats, list) or len(seats) == 0:
        return jsonify({"success": False, "error": "Please select at least one seat."}), 400
    if not customer_name or len(customer_name) < 2:
        return jsonify({"success": False, "error": "Please enter a valid customer name."}), 400
    
    # Email regex check
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_pattern, email):
        return jsonify({"success": False, "error": "Please provide a valid email address."}), 400

    # Phone validation (allow digits, spaces, plus, hyphens, min 7 digits)
    digits_only = re.sub(r'\D', '', phone)
    if len(digits_only) < 7 or len(digits_only) > 15:
        return jsonify({"success": False, "error": "Please provide a valid contact phone number."}), 400

    # Date and Showtime validation (no past bookings)
    today_iso = datetime.date.today().strftime("%Y-%m-%d")
    if booking_date < today_iso:
        return jsonify({"success": False, "error": "Cannot book tickets for past dates."}), 400

    if is_past_slot(booking_date, showtime):
        return jsonify({"success": False, "error": "This showtime has already passed for today. Please pick another slot."}), 400

    # Clean & normalize seat numbers
    clean_seats = sorted(list(set(str(s).strip().upper() for s in seats)))
    ticket_quantity = len(clean_seats)
    total_amount = ticket_quantity * TICKET_PRICE

    # 2. Database Transaction to prevent race conditions and double booking
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Verify movie exists
        cursor.execute("SELECT id, title FROM movies WHERE id = ?", (movie_id,))
        movie = cursor.fetchone()
        if not movie:
            conn.close()
            return jsonify({"success": False, "error": "Movie not found."}), 404

        # Begin immediate exclusive check
        # Check if ANY of the requested seats are already booked
        placeholders = ','.join(['?'] * len(clean_seats))
        query = f"""
            SELECT seat_number FROM booked_seats
            WHERE movie_id = ? AND show_date = ? AND showtime = ?
            AND seat_number IN ({placeholders})
        """
        cursor.execute(query, [movie_id, booking_date, showtime] + clean_seats)
        conflicts = [row['seat_number'] for row in cursor.fetchall()]

        if conflicts:
            conn.rollback()
            conn.close()
            conflict_str = ", ".join(conflicts)
            return jsonify({
                "success": False,
                "error": f"Seat(s) {conflict_str} were just booked by another user. Please choose different seats."
            }), 409

        # Generate unique booking ID: e.g. BK-7F9C21
        unique_token = uuid.uuid4().hex[:6].upper()
        booking_id = f"BK-{unique_token}"
        seats_comma_separated = ", ".join(clean_seats)

        # Insert booking record
        cursor.execute("""
            INSERT INTO bookings (
                booking_id, customer_name, email, phone, movie_id,
                booking_date, showtime, seats, ticket_quantity, total_amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            booking_id, customer_name, email, phone, movie_id,
            booking_date, showtime, seats_comma_separated, ticket_quantity, total_amount
        ))

        # Insert individual booked seats records
        for seat in clean_seats:
            cursor.execute("""
                INSERT INTO booked_seats (movie_id, show_date, showtime, seat_number, booking_id)
                VALUES (?, ?, ?, ?, ?)
            """, (movie_id, booking_date, showtime, seat, booking_id))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "booking_id": booking_id,
            "redirect_url": url_for('confirmation', booking_id=booking_id)
        })

    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "error": f"Booking failed due to a server error: {str(e)}"}), 500

@app.route('/api/my-bookings/search', methods=['POST'])
def search_booking():
    """
    Searches for a booking matching booking_id and email.
    """
    data = request.get_json() or {}
    booking_id = data.get('booking_id', '').strip().upper()
    email = data.get('email', '').strip().lower()

    if not booking_id or not email:
        return jsonify({"success": False, "error": "Please enter both Booking ID and Email."}), 400

    conn = get_db_connection()
    row = conn.execute("""
        SELECT b.*, m.title as movie_title, m.poster_url, m.duration, m.genre
        FROM bookings b
        JOIN movies m ON b.movie_id = m.id
        WHERE UPPER(b.booking_id) = ? AND LOWER(b.email) = ?
    """, (booking_id, email)).fetchone()
    conn.close()

    if not row:
        return jsonify({"success": False, "error": "No booking found matching the provided Booking ID and Email."}), 404

    return jsonify({
        "success": True,
        "booking": {
            "booking_id": row["booking_id"],
            "customer_name": row["customer_name"],
            "email": row["email"],
            "phone": row["phone"],
            "movie_title": row["movie_title"],
            "poster_url": row["poster_url"],
            "genre": row["genre"],
            "duration": row["duration"],
            "booking_date": row["booking_date"],
            "showtime": row["showtime"],
            "seats": row["seats"],
            "ticket_quantity": row["ticket_quantity"],
            "total_amount": row["total_amount"],
            "created_at": row["created_at"]
        }
    })

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    # Local & Cloud deployment runner
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
