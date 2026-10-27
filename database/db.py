import os
import sqlite3

# Try importing psycopg2 for Supabase / PostgreSQL
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

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

def is_postgres():
    """Returns True if DATABASE_URL is configured (Supabase/PostgreSQL)."""
    db_url = os.environ.get("DATABASE_URL", "").strip()
    return bool(db_url and PSYCOPG2_AVAILABLE)

class PostgresCursorWrapper:
    """Wraps psycopg2 cursor to translate '?' placeholders to '%s' for portability."""
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query, vars=None):
        query = query.replace("?", "%s")
        if vars is not None:
            return self._cursor.execute(query, tuple(vars))
        return self._cursor.execute(query)

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __getattr__(self, name):
        return getattr(self._cursor, name)

class PostgresConnectionWrapper:
    """Wraps psycopg2 connection to provide uniform execute/cursor API matching sqlite3."""
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return PostgresCursorWrapper(self._conn.cursor())

    def execute(self, query, vars=None):
        cur = self.cursor()
        cur.execute(query, vars)
        return cur

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()

def get_db_connection():
    """
    Returns a database connection:
    - If DATABASE_URL is set, connects to Supabase / PostgreSQL.
    - Otherwise, falls back to local SQLite (cinema.db).
    """
    db_url = os.environ.get("DATABASE_URL", "").strip()

    if db_url and PSYCOPG2_AVAILABLE:
        # Normalize postgres:// to postgresql:// if needed (standard for Render / Heroku)
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
        conn.autocommit = False
        return PostgresConnectionWrapper(conn)
    else:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

def init_db():
    """Initializes tables and seeds sample movies if table is empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if is_postgres():
        # PostgreSQL Schema for Supabase
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            genre VARCHAR(100) NOT NULL,
            duration VARCHAR(50) NOT NULL,
            rating NUMERIC(3, 1) NOT NULL,
            poster_url TEXT NOT NULL,
            description TEXT NOT NULL,
            language VARCHAR(50) DEFAULT 'English',
            release_year VARCHAR(10) DEFAULT '2026'
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            booking_id VARCHAR(50) UNIQUE NOT NULL,
            customer_name VARCHAR(150) NOT NULL,
            email VARCHAR(150) NOT NULL,
            phone VARCHAR(50) NOT NULL,
            movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
            booking_date VARCHAR(20) NOT NULL,
            showtime VARCHAR(20) NOT NULL,
            seats TEXT NOT NULL,
            ticket_quantity INTEGER NOT NULL,
            total_amount NUMERIC(10, 2) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS booked_seats (
            id SERIAL PRIMARY KEY,
            movie_id INTEGER NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
            show_date VARCHAR(20) NOT NULL,
            showtime VARCHAR(20) NOT NULL,
            seat_number VARCHAR(10) NOT NULL,
            booking_id VARCHAR(50) NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
            UNIQUE (movie_id, show_date, showtime, seat_number)
        );
        """)

        cursor.execute("SELECT COUNT(*) as count FROM movies;")
        row = cursor.fetchone()
        count = row["count"] if isinstance(row, dict) else row[0]

        if count == 0:
            for m in SAMPLE_MOVIES:
                cursor.execute("""
                INSERT INTO movies (title, genre, duration, rating, poster_url, description, language, release_year)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    m["title"], m["genre"], m["duration"], m["rating"],
                    m["poster_url"], m["description"], m["language"], m["release_year"]
                ))
            conn.commit()
            print(f"[Supabase] Initialized database and seeded {len(SAMPLE_MOVIES)} sample movies.")
        else:
            conn.commit()

    else:
        # SQLite Schema
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

        cursor.execute("SELECT COUNT(*) as count FROM movies;")
        count = cursor.fetchone()["count"]

        if count == 0:
            for m in SAMPLE_MOVIES:
                cursor.execute("""
                INSERT INTO movies (title, genre, duration, rating, poster_url, description, language, release_year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    m["title"], m["genre"], m["duration"], m["rating"],
                    m["poster_url"], m["description"], m["language"], m["release_year"]
                ))
            conn.commit()
            print(f"[SQLite] Initialized database and seeded {len(SAMPLE_MOVIES)} sample movies.")
        else:
            conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialization successful.")
