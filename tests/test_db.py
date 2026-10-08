import sqlite3
import time
from datetime import datetime, timedelta, timezone

from utils import db


def add_thread(thread_id=1, owner_id=10):
    db.upsert_thread(thread_id, 100, 1000, "Selling stuff", owner_id, "https://discord.com/channels/1/2/3")


def test_review_is_unique_per_giver_receiver_thread(temp_db):
    assert db.add_review(1, 2, 3, 8, "great")
    assert not db.add_review(1, 2, 3, 9, "again")
    assert db.has_user_reviewed(1, 2, 3)
    avg, total, latest = db.get_user_reviews(2)
    assert (avg, total) == (8, 1)
    assert latest[0]["notes"] == "great"


def test_count_thread_reviews_can_exclude_a_giver(temp_db):
    db.add_review(1, 2, 3, 8)
    db.add_review(2, 2, 3, 6)
    assert db.count_thread_reviews(3) == 2
    assert db.count_thread_reviews(3, exclude_giver_id=2) == 1


def test_timestamps_use_sqlite_utc_format(temp_db):
    with sqlite3.connect(temp_db) as conn:
        sqlite_now = conn.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]
    ours = db._utc_text(time.time())
    delta = abs(datetime.fromisoformat(ours) - datetime.fromisoformat(sqlite_now))
    assert delta < timedelta(seconds=5)


def test_auto_close_due_only_after_scheduled_time(temp_db):
    add_thread(1)
    add_thread(2)
    assert db.schedule_thread_auto_close(1, time.time() - 60)
    assert db.schedule_thread_auto_close(2, time.time() + 3600)
    due = [t["thread_id"] for t in db.get_threads_to_auto_close()]
    assert due == [1]


def test_auto_close_schedules_only_once(temp_db):
    add_thread(1)
    assert db.schedule_thread_auto_close(1, time.time() + 100)
    assert not db.schedule_thread_auto_close(1, time.time() + 200)


def test_cancelled_auto_close_is_not_rescheduled(temp_db):
    add_thread(1)
    db.cancel_thread_auto_close(1)
    assert not db.schedule_thread_auto_close(1, time.time() - 60)
    assert db.get_threads_to_auto_close() == []


def test_closed_threads_are_not_auto_closed_again(temp_db):
    add_thread(1)
    db.schedule_thread_auto_close(1, time.time() - 60)
    db.mark_thread_closed(1)
    assert db.get_threads_to_auto_close() == []
    info = db.get_thread_info(1)
    assert info["archived"] and info["locked"]


def test_migration_converts_local_auto_close_times_to_utc(tmp_path, monkeypatch):
    path = tmp_path / "old.db"
    monkeypatch.setattr(db, "DB_PATH", str(path))
    db.init_db()
    add_thread(1)
    local = datetime(2026, 1, 1, 12, 0, 0)
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE threads SET auto_close_scheduled = ?", (local.isoformat(" "),))
        conn.execute("PRAGMA user_version = 0")

    db.init_db()

    with sqlite3.connect(path) as conn:
        stored = conn.execute("SELECT auto_close_scheduled FROM threads").fetchone()[0]
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    # The naive value was in the host's local time zone
    assert stored == local.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    assert version == db.SCHEMA_VERSION


def test_pending_tos_resolves_exactly_once(temp_db):
    db.add_pending_tos(5, 10, 100.0, 130.0)
    assert db.get_pending_tos() == [{"thread_id": 5, "owner_id": 10, "prompted_at": 100.0, "expires_at": 130.0}]
    assert db.resolve_pending_tos(5)
    assert not db.resolve_pending_tos(5)
    assert db.get_pending_tos() == []


def test_thread_participants(temp_db):
    assert not db.has_participated(1, 2)
    db.add_thread_participant(1, 2)
    db.add_thread_participant(1, 2)
    assert db.has_participated(1, 2)


def test_thread_log_message_is_persisted(temp_db):
    add_thread(1)
    db.set_thread_log_message(1, 999)
    assert db.get_thread_info(1)["log_message_id"] == 999
