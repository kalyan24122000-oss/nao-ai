"""
Database module for AI Chatbot
SQLite database for persistent storage
"""

import sqlite3
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "chatbot.db")


def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT DEFAULT 'New Chat',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model TEXT DEFAULT 'nvidia/nemotron-3-nano-30b-a3b:free',
            is_active INTEGER DEFAULT 1
        )
    """)
    
    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            reasoning TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    
    # Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Stats table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            total_messages INTEGER DEFAULT 0,
            total_sessions INTEGER DEFAULT 0,
            UNIQUE(date)
        )
    """)
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")


# =============================================================================
# User Functions
# =============================================================================

def create_user(email: str, password_hash: str, name: str = "User") -> Dict:
    """Create a new user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    user_id = str(uuid.uuid4())
    
    try:
        cursor.execute("""
            INSERT INTO users (id, email, password, name, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (user_id, email, password_hash, name))
        conn.commit()
        return {"id": user_id, "email": email, "name": name}
    except sqlite3.IntegrityError:
        return None  # Email exists
    finally:
        conn.close()

def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def verify_user(email: str, password_hash: str) -> Optional[Dict]:
    """Verify user credentials."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM users WHERE email = ? AND password = ?
    """, (email, password_hash))
    row = cursor.fetchone()
    
    if row:
        # Update last login
        cursor.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (row['id'],))
        conn.commit()
        conn.close()
        return dict(row)
    
    conn.close()
    return None

def get_all_users() -> List[Dict]:
    """Get all users for admin panel."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, created_at, last_login FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# =============================================================================
# Session Functions
# =============================================================================

def create_session(session_id: str, title: str = "New Chat") -> Dict:
    """Create a new chat session."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO sessions (id, title, created_at, updated_at)
        VALUES (?, ?, datetime('now'), datetime('now'))
    """, (session_id, title))
    
    conn.commit()
    conn.close()
    
    return {"id": session_id, "title": title}


def get_session(session_id: str) -> Optional[Dict]:
    """Get session by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_all_sessions(limit: int = 50) -> List[Dict]:
    """Get all sessions, ordered by most recent."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT s.*, 
               (SELECT COUNT(*) FROM messages WHERE session_id = s.id) as message_count,
               (SELECT content FROM messages WHERE session_id = s.id ORDER BY created_at LIMIT 1) as first_message
        FROM sessions s
        WHERE s.is_active = 1
        ORDER BY s.updated_at DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def update_session_title(session_id: str, title: str):
    """Update session title."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE sessions 
        SET title = ?, updated_at = datetime('now')
        WHERE id = ?
    """, (title, session_id))
    
    conn.commit()
    conn.close()


def delete_session(session_id: str):
    """Soft delete a session."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE sessions SET is_active = 0 WHERE id = ?
    """, (session_id,))
    
    conn.commit()
    conn.close()


def delete_all_sessions():
    """Delete all sessions."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE sessions SET is_active = 0")
    
    conn.commit()
    conn.close()


# =============================================================================
# Message Functions
# =============================================================================

def add_message(session_id: str, role: str, content: str, 
                reasoning: str = None, image_url: str = None) -> Dict:
    """Add a message to a session."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create session if it doesn't exist
    cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        create_session(session_id)
    
    cursor.execute("""
        INSERT INTO messages (session_id, role, content, reasoning, image_url)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, role, content, reasoning, image_url))
    
    message_id = cursor.lastrowid
    
    # Update session timestamp and title (use first user message as title)
    if role == "user":
        cursor.execute("""
            UPDATE sessions 
            SET updated_at = datetime('now'),
                title = CASE 
                    WHEN title = 'New Chat' THEN substr(?, 1, 50)
                    ELSE title
                END
            WHERE id = ?
        """, (content, session_id))
    else:
        cursor.execute("""
            UPDATE sessions SET updated_at = datetime('now') WHERE id = ?
        """, (session_id,))
    
    conn.commit()
    conn.close()
    
    return {"id": message_id, "session_id": session_id, "role": role, "content": content}


def get_messages(session_id: str, limit: int = 100) -> List[Dict]:
    """Get all messages for a session."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM messages 
        WHERE session_id = ?
        ORDER BY created_at ASC
        LIMIT ?
    """, (session_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_message_count(session_id: str = None) -> int:
    """Get total message count."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if session_id:
        cursor.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,))
    else:
        cursor.execute("SELECT COUNT(*) FROM messages")
    
    count = cursor.fetchone()[0]
    conn.close()
    
    return count


# =============================================================================
# Settings Functions
# =============================================================================

def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting value."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        try:
            return json.loads(row[0])
        except:
            return row[0]
    return default


def set_setting(key: str, value: Any):
    """Set a setting value."""
    conn = get_connection()
    cursor = conn.cursor()
    
    value_str = json.dumps(value) if not isinstance(value, str) else value
    
    cursor.execute("""
        INSERT OR REPLACE INTO settings (key, value, updated_at)
        VALUES (?, ?, datetime('now'))
    """, (key, value_str))
    
    conn.commit()
    conn.close()


# =============================================================================
# Stats Functions
# =============================================================================

def get_stats() -> Dict:
    """Get overall statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM sessions WHERE is_active = 1")
    total_sessions = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT date(created_at) as day, COUNT(*) as count 
        FROM messages 
        GROUP BY date(created_at)
        ORDER BY day DESC
        LIMIT 7
    """)
    daily_messages = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "daily_messages": daily_messages
    }


# Initialize database on import
init_database()
