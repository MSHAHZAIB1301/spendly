import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sqlite3

def is_postgres_available():
    """Check if a valid PostgreSQL DATABASE_URL is available"""
    database_url = os.environ.get('DATABASE_URL', '')
    return bool(database_url and database_url.startswith('postgres'))

def get_db():
    """Returns a connection with row_factory and foreign keys enabled"""
    if is_postgres_available():
        database_url = os.environ.get('DATABASE_URL')
        try:
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            conn.autocommit = True
            return conn
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}, falling back to SQLite")
            pass

    # SQLite fallback for local development
    conn = sqlite3.connect("expense_tracker.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_db_cursor():
    """Returns (connection, cursor) tuple for operations that need explicit commit"""
    if is_postgres_available():
        database_url = os.environ.get('DATABASE_URL')
        try:
            conn = psycopg2.connect(database_url)
            conn.autocommit = False
            return conn, conn.cursor()
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}, falling back to SQLite")
            pass

    conn = sqlite3.connect("expense_tracker.db")
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor()

def init_db():
    """Creates all tables using CREATE TABLE IF NOT EXISTS"""
    if is_postgres_available():
        database_url = os.environ.get('DATABASE_URL')
        try:
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    date TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)

            conn.commit()
            cursor.close()
            conn.close()
            return
        except Exception as e:
            print(f"PostgreSQL init failed: {e}, falling back to SQLite")

    # SQLite fallback for local development
    conn = sqlite3.connect("expense_tracker.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
