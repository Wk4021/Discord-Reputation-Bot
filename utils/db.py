import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional

DB_PATH = 'data/rep.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # New reviews table to replace the old rep system
    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            giver_id    INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            thread_id   INTEGER NOT NULL,
            rating      INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 10),
            notes       TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(giver_id, receiver_id, thread_id)
        )
    """)
    
    # Users table to store all server members
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT NOT NULL,
            display_name TEXT,
            avatar_url  TEXT,
            banner_url  TEXT,
            accent_color INTEGER,
            public_flags INTEGER,
            joined_at   TIMESTAMP,
            left_at     TIMESTAMP NULL,
            is_in_server BOOLEAN DEFAULT TRUE,
            roles       TEXT,  -- JSON string of role data
            badges      TEXT,  -- JSON string of badge data
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Keep rep and rep_totals for backward compatibility, but they'll be deprecated
    c.execute("""
        CREATE TABLE IF NOT EXISTS rep (
            giver_id    INTEGER,
            receiver_id INTEGER,
            thread_id   INTEGER,
            rep_type    TEXT  CHECK(rep_type IN ('+', '-')),
            UNIQUE(giver_id, receiver_id, thread_id)
        )
    """)
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS rep_totals (
            user_id  INTEGER PRIMARY KEY,
            positive INTEGER DEFAULT 0,
            negative INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()

def add_rep(giver_id: int, receiver_id: int, thread_id: int, rep_type: str) -> bool:
    """
    Records a rep from giver_id to receiver_id in a given thread.
    Returns False if the same giver already rated this receiver in this thread.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # insert the individual rep
        c.execute(
            "INSERT INTO rep (giver_id, receiver_id, thread_id, rep_type) VALUES (?, ?, ?, ?)",
            (giver_id, receiver_id, thread_id, rep_type)
        )
        # bump the receiver’s total
        if rep_type == '+':
            c.execute(
                "INSERT INTO rep_totals (user_id, positive, negative) VALUES (?, 1, 0) "
                "ON CONFLICT(user_id) DO UPDATE SET positive = positive + 1",
                (receiver_id,)
            )
        else:
            c.execute(
                "INSERT INTO rep_totals (user_id, positive, negative) VALUES (?, 0, 1) "
                "ON CONFLICT(user_id) DO UPDATE SET negative = negative + 1",
                (receiver_id,)
            )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_rep(user_id: int) -> tuple[int,int]:
    """
    Fetch the total positive and negative rep for a given user (the receiver).
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT positive, negative FROM rep_totals WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return (row[0], row[1]) if row else (0, 0)

def get_top_positive_rep(limit: int = 10) -> list[tuple[int,int]]:
    """
    Returns a list of (user_id, positive_count) sorted descending.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, positive FROM rep_totals ORDER BY positive DESC LIMIT ?", (limit,))
    results = c.fetchall()
    conn.close()
    return results

# New review system functions

def add_review(giver_id: int, receiver_id: int, thread_id: int, rating: int, notes: Optional[str] = None) -> bool:
    """
    Records a review from giver_id to receiver_id in a given thread.
    Returns False if the same giver already reviewed this receiver in this thread.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO reviews (giver_id, receiver_id, thread_id, rating, notes) VALUES (?, ?, ?, ?, ?)",
            (giver_id, receiver_id, thread_id, rating, notes)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_reviews(user_id: int) -> Tuple[float, int, List[dict]]:
    """
    Get user's review statistics and latest reviews.
    Returns: (average_rating, total_reviews, latest_3_reviews)
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get average rating and total count
    c.execute("""
        SELECT AVG(rating), COUNT(*) 
        FROM reviews 
        WHERE receiver_id = ?
    """, (user_id,))
    result = c.fetchone()
    avg_rating = result[0] if result[0] else 0.0
    total_reviews = result[1]
    
    # Get latest 3 reviews
    c.execute("""
        SELECT giver_id, rating, notes, created_at 
        FROM reviews 
        WHERE receiver_id = ? 
        ORDER BY created_at DESC 
        LIMIT 3
    """, (user_id,))
    
    latest_reviews = []
    for row in c.fetchall():
        latest_reviews.append({
            'giver_id': row[0],
            'rating': row[1],
            'notes': row[2],
            'created_at': row[3]
        })
    
    conn.close()
    return (avg_rating, total_reviews, latest_reviews)

def get_top_rated_users(limit: int = 10) -> List[Tuple[int, float, int]]:
    """
    Returns top rated users by average rating.
    Returns: [(user_id, avg_rating, total_reviews), ...]
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT receiver_id, AVG(rating), COUNT(*) 
        FROM reviews 
        GROUP BY receiver_id 
        HAVING COUNT(*) >= 1
        ORDER BY AVG(rating) DESC, COUNT(*) DESC 
        LIMIT ?
    """, (limit,))
    results = c.fetchall()
    conn.close()
    return results

def has_user_reviewed(giver_id: int, receiver_id: int, thread_id: int) -> bool:
    """
    Check if a user has already reviewed another user in a specific thread.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT 1 FROM reviews 
        WHERE giver_id = ? AND receiver_id = ? AND thread_id = ?
    """, (giver_id, receiver_id, thread_id))
    result = c.fetchone()
    conn.close()
    return result is not None

# User management functions

def upsert_user(user_id: int, username: str, display_name: str = None, avatar_url: str = None, 
                banner_url: str = None, accent_color: int = None, public_flags: int = None,
                joined_at: str = None, is_in_server: bool = True, roles: str = None, badges: str = None) -> None:
    """
    Insert or update a user in the users table.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO users (user_id, username, display_name, avatar_url, banner_url, accent_color, 
                          public_flags, joined_at, is_in_server, roles, badges, last_updated) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            username = ?,
            display_name = ?,
            avatar_url = ?,
            banner_url = ?,
            accent_color = ?,
            public_flags = ?,
            is_in_server = ?,
            roles = ?,
            badges = ?,
            last_updated = CURRENT_TIMESTAMP
    """, (user_id, username, display_name, avatar_url, banner_url, accent_color, public_flags,
          joined_at, is_in_server, roles, badges, username, display_name, avatar_url, 
          banner_url, accent_color, public_flags, is_in_server, roles, badges))
    conn.commit()
    conn.close()

def mark_user_left(user_id: int) -> None:
    """
    Mark a user as having left the server.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE users 
        SET is_in_server = FALSE, left_at = CURRENT_TIMESTAMP, last_updated = CURRENT_TIMESTAMP
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()

def get_all_users() -> List[dict]:
    """
    Get all users from the database, including those who left the server.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT user_id, username, display_name, avatar_url, banner_url, accent_color, 
               public_flags, joined_at, left_at, is_in_server, roles, badges
        FROM users 
        ORDER BY is_in_server DESC, username ASC
    """)
    users = []
    for row in c.fetchall():
        users.append({
            'user_id': row[0],
            'username': row[1],
            'display_name': row[2],
            'avatar_url': row[3],
            'banner_url': row[4],
            'accent_color': row[5],
            'public_flags': row[6],
            'joined_at': row[7],
            'left_at': row[8],
            'is_in_server': bool(row[9]),
            'roles': row[10],
            'badges': row[11]
        })
    conn.close()
    return users
