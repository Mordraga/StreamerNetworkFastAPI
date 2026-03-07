import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

def initialize_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            data TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            onboarding_dismissed BOOLEAN NOT NULL DEFAULT FALSE
        )
    ''')
    # Migrations
    cursor.execute("ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS theme TEXT NOT NULL DEFAULT 'dark'")
    cursor.execute("ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS timezone TEXT")
    cursor.execute("ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS display_name_override TEXT")
    cursor.execute("ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS time_format TEXT NOT NULL DEFAULT '12'")
    conn.commit()
    conn.close()