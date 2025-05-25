import sqlite3

DB_PATH = 'data/rep.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # track who gave rep, to whom, in which thread
    c.execute("""
        CREATE TABLE IF NOT EXISTS rep (
            giver_id    INTEGER,
            receiver_id INTEGER,
            thread_id   INTEGER,
            rep_type    TEXT  CHECK(rep_type IN ('+', '-')),
            UNIQUE(giver_id, receiver_id, thread_id)
        )
    """)
    # totals by *receiver* only
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
