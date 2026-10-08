"""SQLite storage for reviews, tracked threads and pending TOS prompts."""
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from utils.config import PROJECT_ROOT

DB_PATH = str(PROJECT_ROOT / 'data' / 'rep.db')

# Timestamps are stored as UTC text in the same format SQLite's
# CURRENT_TIMESTAMP produces, so they compare correctly in SQL.
_TS_FORMAT = '%Y-%m-%d %H:%M:%S'

# Bump when adding a migration to _migrate()
SCHEMA_VERSION = 1


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _utc_text(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime(_TS_FORMAT)


def init_db():
    with closing(_connect()) as conn, conn:
        # WAL lets readers and the writer work at the same time
        conn.execute("PRAGMA journal_mode=WAL")

        conn.execute("""
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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                thread_id   INTEGER PRIMARY KEY,
                channel_id  INTEGER NOT NULL,
                guild_id    INTEGER NOT NULL,
                name        TEXT NOT NULL,
                owner_id    INTEGER NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                archived    BOOLEAN DEFAULT FALSE,
                locked      BOOLEAN DEFAULT FALSE,
                jump_url    TEXT NOT NULL,
                auto_close_scheduled TIMESTAMP NULL,
                auto_close_cancelled BOOLEAN DEFAULT FALSE
            )
        """)

        # TOS prompts awaiting an answer; survives restarts
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_tos (
                thread_id   INTEGER PRIMARY KEY,
                owner_id    INTEGER NOT NULL,
                prompted_at REAL NOT NULL,
                expires_at  REAL NOT NULL
            )
        """)

        # Who has posted in each tracked thread (used to gate reviews)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS thread_participants (
                thread_id INTEGER NOT NULL,
                user_id   INTEGER NOT NULL,
                PRIMARY KEY (thread_id, user_id)
            )
        """)

        # Columns added after the threads table first shipped
        for column in ("auto_close_scheduled TIMESTAMP NULL",
                       "auto_close_cancelled BOOLEAN DEFAULT FALSE",
                       "log_message_id INTEGER NULL"):
            try:
                conn.execute(f"ALTER TABLE threads ADD COLUMN {column}")
            except sqlite3.OperationalError:
                pass  # Column already exists

        _migrate(conn)


def _migrate(conn: sqlite3.Connection):
    version = conn.execute("PRAGMA user_version").fetchone()[0]

    if version < 1:
        # Earlier versions stored auto-close times in the host's local time
        # while comparing them against UTC. Convert them to UTC.
        rows = conn.execute(
            "SELECT thread_id, auto_close_scheduled FROM threads WHERE auto_close_scheduled IS NOT NULL"
        ).fetchall()
        for row in rows:
            try:
                local = datetime.fromisoformat(str(row["auto_close_scheduled"]))
            except ValueError:
                continue
            utc = local.astimezone(timezone.utc).strftime(_TS_FORMAT)
            conn.execute("UPDATE threads SET auto_close_scheduled = ? WHERE thread_id = ?",
                         (utc, row["thread_id"]))

    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


# ─── Reviews ────────────────────────────────────────────────────────────────

def add_review(giver_id: int, receiver_id: int, thread_id: int, rating: int, notes: Optional[str] = None) -> bool:
    """
    Records a review from giver_id to receiver_id in a given thread.
    Returns False if the same giver already reviewed this receiver in this thread.
    """
    with closing(_connect()) as conn:
        try:
            with conn:
                conn.execute(
                    "INSERT INTO reviews (giver_id, receiver_id, thread_id, rating, notes) VALUES (?, ?, ?, ?, ?)",
                    (giver_id, receiver_id, thread_id, rating, notes)
                )
            return True
        except sqlite3.IntegrityError:
            return False


def get_user_reviews(user_id: int) -> Tuple[float, int, List[dict]]:
    """
    Get user's review statistics and latest reviews.
    Returns: (average_rating, total_reviews, latest_3_reviews)
    """
    with closing(_connect()) as conn:
        avg_rating, total_reviews = conn.execute(
            "SELECT AVG(rating), COUNT(*) FROM reviews WHERE receiver_id = ?", (user_id,)
        ).fetchone()
        latest = conn.execute("""
            SELECT giver_id, rating, notes, created_at
            FROM reviews
            WHERE receiver_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 3
        """, (user_id,)).fetchall()
    return (avg_rating or 0.0, total_reviews, [dict(row) for row in latest])


def get_top_rated_users(limit: int = 10) -> List[Tuple[int, float, int]]:
    """
    Returns top rated users by average rating.
    Returns: [(user_id, avg_rating, total_reviews), ...]
    """
    with closing(_connect()) as conn:
        rows = conn.execute("""
            SELECT receiver_id, AVG(rating), COUNT(*)
            FROM reviews
            GROUP BY receiver_id
            ORDER BY AVG(rating) DESC, COUNT(*) DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [tuple(row) for row in rows]


def has_user_reviewed(giver_id: int, receiver_id: int, thread_id: int) -> bool:
    """
    Check if a user has already reviewed another user in a specific thread.
    """
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT 1 FROM reviews WHERE giver_id = ? AND receiver_id = ? AND thread_id = ?",
            (giver_id, receiver_id, thread_id)
        ).fetchone()
    return row is not None


def count_thread_reviews(thread_id: int, exclude_giver_id: Optional[int] = None) -> int:
    """Number of reviews left in a thread, optionally ignoring one giver."""
    with closing(_connect()) as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM reviews WHERE thread_id = ? AND giver_id IS NOT ?",
            (thread_id, exclude_giver_id)
        ).fetchone()[0]


# ─── Threads ────────────────────────────────────────────────────────────────

def upsert_thread(thread_id: int, channel_id: int, guild_id: int, name: str,
                  owner_id: int, jump_url: str, archived: bool = False, locked: bool = False) -> None:
    """
    Insert or update a thread in the threads table.
    """
    with closing(_connect()) as conn, conn:
        conn.execute("""
            INSERT INTO threads (thread_id, channel_id, guild_id, name, owner_id, jump_url, archived, locked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(thread_id) DO UPDATE SET
                name = excluded.name,
                archived = excluded.archived,
                locked = excluded.locked,
                jump_url = excluded.jump_url
        """, (thread_id, channel_id, guild_id, name, owner_id, jump_url, archived, locked))


def mark_thread_closed(thread_id: int) -> None:
    """Record that a thread was archived and locked."""
    with closing(_connect()) as conn, conn:
        conn.execute("UPDATE threads SET archived = TRUE, locked = TRUE WHERE thread_id = ?", (thread_id,))


def set_thread_state(thread_id: int, archived: bool, locked: bool) -> None:
    """Mirror a tracked thread's archived/locked state from Discord (e.g. a moderator reopened it)."""
    with closing(_connect()) as conn, conn:
        conn.execute("UPDATE threads SET archived = ?, locked = ? WHERE thread_id = ?",
                     (archived, locked, thread_id))


def get_thread_info(thread_id: int) -> Optional[dict]:
    """
    Get thread information from the database.
    """
    with closing(_connect()) as conn:
        row = conn.execute("""
            SELECT thread_id, channel_id, guild_id, name, owner_id, created_at,
                   archived, locked, jump_url, log_message_id
            FROM threads
            WHERE thread_id = ?
        """, (thread_id,)).fetchone()
    if not row:
        return None
    info = dict(row)
    info['archived'] = bool(info['archived'])
    info['locked'] = bool(info['locked'])
    return info


def set_thread_log_message(thread_id: int, message_id: int) -> None:
    """Remember which log-channel message tracks this thread."""
    with closing(_connect()) as conn, conn:
        conn.execute("UPDATE threads SET log_message_id = ? WHERE thread_id = ?", (message_id, thread_id))


def schedule_thread_auto_close(thread_id: int, close_timestamp: float) -> bool:
    """
    Schedule a thread to auto-close at the given Unix timestamp.

    Only the first call per thread takes effect (and never after the owner
    cancelled), so concurrent first reviews can't both schedule. Returns True
    if this call scheduled it.
    """
    with closing(_connect()) as conn, conn:
        cursor = conn.execute("""
            UPDATE threads
            SET auto_close_scheduled = ?
            WHERE thread_id = ?
            AND auto_close_scheduled IS NULL
            AND auto_close_cancelled = FALSE
        """, (_utc_text(close_timestamp), thread_id))
        return cursor.rowcount == 1


def cancel_thread_auto_close(thread_id: int) -> None:
    """
    Cancel the auto-close for a thread.
    """
    with closing(_connect()) as conn, conn:
        conn.execute("UPDATE threads SET auto_close_cancelled = TRUE WHERE thread_id = ?", (thread_id,))


def get_threads_to_auto_close() -> List[dict]:
    """
    Get threads that should be auto-closed (scheduled time has passed and not cancelled).
    """
    with closing(_connect()) as conn:
        rows = conn.execute("""
            SELECT thread_id, channel_id, guild_id, name, owner_id, jump_url
            FROM threads
            WHERE auto_close_scheduled IS NOT NULL
            AND auto_close_scheduled <= CURRENT_TIMESTAMP
            AND auto_close_cancelled = FALSE
            AND locked = FALSE
        """).fetchall()
    return [dict(row) for row in rows]


def is_auto_close_due(thread_id: int) -> bool:
    """Re-check a single thread right before closing it (the owner may have just cancelled)."""
    with closing(_connect()) as conn:
        row = conn.execute("""
            SELECT 1 FROM threads
            WHERE thread_id = ?
            AND auto_close_scheduled IS NOT NULL
            AND auto_close_scheduled <= CURRENT_TIMESTAMP
            AND auto_close_cancelled = FALSE
            AND locked = FALSE
        """, (thread_id,)).fetchone()
    return row is not None


# ─── Thread participants ────────────────────────────────────────────────────

def add_thread_participant(thread_id: int, user_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("INSERT OR IGNORE INTO thread_participants (thread_id, user_id) VALUES (?, ?)",
                     (thread_id, user_id))


def has_participated(thread_id: int, user_id: int) -> bool:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT 1 FROM thread_participants WHERE thread_id = ? AND user_id = ?",
                           (thread_id, user_id)).fetchone()
    return row is not None


# ─── Pending TOS prompts ────────────────────────────────────────────────────

def add_pending_tos(thread_id: int, owner_id: int, prompted_at: float, expires_at: float) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("""
            INSERT OR REPLACE INTO pending_tos (thread_id, owner_id, prompted_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (thread_id, owner_id, prompted_at, expires_at))


def resolve_pending_tos(thread_id: int) -> bool:
    """
    Remove a pending TOS prompt. Returns True only for the caller that
    actually removed it, so agree/decline/timeout can't both act.
    """
    with closing(_connect()) as conn, conn:
        return conn.execute("DELETE FROM pending_tos WHERE thread_id = ?", (thread_id,)).rowcount == 1


def get_pending_tos() -> List[dict]:
    with closing(_connect()) as conn:
        rows = conn.execute("SELECT thread_id, owner_id, prompted_at, expires_at FROM pending_tos").fetchall()
    return [dict(row) for row in rows]
