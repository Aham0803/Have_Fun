import sqlite3
import os

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "cinema.db")

SAMPLE_MOVIES = [
    {
        "title": "Interstellar Drift",
        "genre": "Sci-Fi / Adventure",
        "duration": "2h 35m",
        "rating": 8.9,
        "poster_url": "/static/images/poster_interstellar_drift.jpg",
        "description": "An expedition beyond the known cosmos tests the limits of humanity when a lost starship discovers a gateway bridging alternate realities.",
        "language": "English",
        "release_year": "2026"
    },
    {
        "title": "Neon Riot",
        "genre": "Cyberpunk / Action",
        "duration": "2h 15m",
        "rating": 8.6,
        "poster_url": "/static/images/poster_neon_knight.jpg",
        "description": "In a rain-drenched megacity ruled by rogue artificial intelligence, a lone operative must navigate chaos to survive and expose a sinister plot.",
        "language": "English",
        "release_year": "2026"
    },
    {
        "title": "Realm of Titans",
        "genre": "Fantasy / Epic",
        "duration": "2h 48m",
        "rating": 9.1,
        "poster_url": "/static/images/poster_elysium.jpg",
        "description": "When the celestial spires fracture, legendary warriors embark on a treacherous mountain ascent to prevent an ancient cataclysm.",
        "language": "English",
        "release_year": "2026"
    },
    {
        "title": "Shadows of Blackwood Manor",
        "genre": "Horror / Mystery",
        "duration": "1h 58m",
        "rating": 8.1,
        "poster_url": "/static/images/poster_shadow_manor.jpg",
        "description": "A secluded Victorian estate harbors dark secrets that awaken only when night falls, confronting visitors with chilling manifestations.",
        "language": "English",
        "release_year": "2026"
    },
    {
        "title": "Apex Velocity",
        "genre": "Action / Crime",
        "duration": "2h 08m",
        "rating": 8.5,
        "poster_url": "/static/images/poster_apex_velocity.jpg",
        "description": "A high-stakes underground racing thriller where speed has no limits, and drivers push modified machines through midnight city streets.",
        "language": "English",
        "release_year": "2026"
    },
    {
        "title": "Echoes of Silence",
        "genre": "Drama / Romance",
        "duration": "2h 02m",
        "rating": 8.7,
        "poster_url": "/static/images/poster_echoes_silence.jpg",
        "description": "A heartfelt journey of unspoken words, music, and redemption between two souls reunited after years apart.",
        "language": "English",
        "release_year": "2026"
    }
]

def get_db_connection():
    """Returns a SQLite connection with Row row_factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes tables and populates sample movies if table is empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Movies table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        genre TEXT NOT NULL,
        duration TEXT NOT NULL,
        rating REAL NOT NULL,
        poster_url TEXT NOT NULL,
        description TEXT NOT NULL,
        language TEXT DEFAULT 'English',
        release_year TEXT DEFAULT '2026'
    );
    """)

    # 2. Bookings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id TEXT UNIQUE NOT NULL,
        customer_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        movie_id INTEGER NOT NULL,
        booking_date TEXT NOT NULL,
        showtime TEXT NOT NULL,
        seats TEXT NOT NULL,
        ticket_quantity INTEGER NOT NULL,
        total_amount REAL NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (movie_id) REFERENCES movies (id) ON DELETE CASCADE
    );
    """)

    # 3. Booked Seats table with UNIQUE constraint preventing double-booking
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS booked_seats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER NOT NULL,
        show_date TEXT NOT NULL,
        showtime TEXT NOT NULL,
        seat_number TEXT NOT NULL,
        booking_id TEXT NOT NULL,
        UNIQUE (movie_id, show_date, showtime, seat_number),
        FOREIGN KEY (booking_id) REFERENCES bookings (booking_id) ON DELETE CASCADE,
        FOREIGN KEY (movie_id) REFERENCES movies (id) ON DELETE CASCADE
    );
    """)

    # Check if movies exist, if not insert sample movies
    cursor.execute("SELECT COUNT(*) as count FROM movies;")
    count = cursor.fetchone()["count"]

    if count == 0:
        for m in SAMPLE_MOVIES:
            cursor.execute("""
            INSERT INTO movies (title, genre, duration, rating, poster_url, description, language, release_year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                m["title"],
                m["genre"],
                m["duration"],
                m["rating"],
                m["poster_url"],
                m["description"],
                m["language"],
                m["release_year"]
            ))
        conn.commit()
        print(f"[DB] Initialized database and seeded {len(SAMPLE_MOVIES)} sample movies.")
    else:
        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialization successful.")
