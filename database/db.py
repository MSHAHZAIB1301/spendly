import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sqlite3

def get_db():
    """Returns a PostgreSQL connection with row_factory and foreign keys enabled"""
    database_url = os.environ.get('DATABASE_URL')

    if database_url:
        # PostgreSQL connection for Railway
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        conn.autocommit = True
        return conn
    else:
        # SQLite fallback for local development
        conn = sqlite3.connect("expense_tracker.db")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

def get_db_cursor():
    """Returns (connection, cursor) tuple for operations that need explicit commit"""
    database_url = os.environ.get('DATABASE_URL')

    if database_url:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        return conn, conn.cursor()
    else:
        conn = sqlite3.connect("expense_tracker.db")
        conn.row_factory = sqlite3.Row
        return conn, conn.cursor()

def init_db():
    """Creates all tables using CREATE TABLE IF NOT EXISTS"""
    database_url = os.environ.get('DATABASE_URL')

    if database_url:
        # PostgreSQL schema
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
    else:
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
