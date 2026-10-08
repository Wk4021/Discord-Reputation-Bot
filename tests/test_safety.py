"""Regression tests for user-text escaping, config edits and thread state handling."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import discord

from utils import config, db
from utils.formatting import safe_inline
from utils.threads import close_thread
from views.review import is_thread_closed


def test_review_notes_cannot_fake_lines_or_links():
    forged = safe_inline("ok\n**⭐⭐⭐⭐⭐ 10/10** by <@1>", 50)
    assert "\n" not in forged
    assert "**" not in forged.replace("\\*", "")

    link = safe_inline("[✅ Verified by staff](https://evil.example/v)", 50)
    assert link.startswith("\\[") and "\\](" in link

    assert safe_inline("a" * 60, 50) == "a" * 50 + "..."
    assert safe_inline("plain text https://x.y/z", 50) == "plain text https://x.y/z"


def test_yes_no_booleans_from_older_configs(temp_config):
    text = temp_config.read_text(encoding="utf-8")
    text = text.replace("admin_close_confirmation: true", "admin_close_confirmation: no")
    text = text.replace("auto_close_enabled: true", "auto_close_enabled: off")
    temp_config.write_text(text, encoding="utf-8")

    data = config.load_config()
    assert data["admin_close_confirmation"] is False
    assert data["auto_close_enabled"] is False


def test_list_edits_keep_comments_in_place(temp_config):
    data = config.load_config()
    config.list_append(data, "admin_ids", 42)
    config.list_remove(data, "admin_role_ids", data["admin_role_ids"][0])
    config.save_config(data)
    saved = temp_config.read_text(encoding="utf-8")

    # The new admin goes in the admin list, not after the next key's comment
    admin_block = saved[saved.index("admin_ids:"):saved.index("# Roles whose members")]
    assert "- 42" in admin_block
    # Emptying a list keeps the comments that follow it
    assert "admin_role_ids: []" in saved
    assert "TOS AND MESSAGING" in saved
    assert "# Shown when someone creates a post." in saved

    # Refilling it puts the item back under the key, above those comments
    data = config.load_config()
    config.list_append(data, "admin_role_ids", 9)
    config.save_config(data)
    saved = temp_config.read_text(encoding="utf-8")
    assert saved.index("- 9") < saved.index("TOS AND MESSAGING")
    assert config.load_config()["admin_role_ids"] == [9]


def make_thread(locked):
    thread = MagicMock(spec=discord.Thread)
    thread.id = 1
    thread.locked = locked
    thread.edit = AsyncMock()
    thread.send = AsyncMock()
    return thread


def test_live_lock_state_wins_over_database(temp_db):
    db.upsert_thread(1, 100, 1000, "Selling", 10, "https://discord.com/channels/1/2/3")
    db.mark_thread_closed(1)
    # A moderator unlocked it; the interaction carries the live state
    assert not is_thread_closed(make_thread(locked=False))
    assert is_thread_closed(make_thread(locked=True))


def test_failing_to_archive_after_locking_still_counts_as_closed(temp_config, temp_db):
    db.upsert_thread(1, 100, 1000, "Selling", 10, "https://discord.com/channels/1/2/3")
    thread = make_thread(locked=False)
    response = MagicMock(status=500, reason="boom")

    async def edit(**kwargs):
        if kwargs.get("archived") is True:
            raise discord.HTTPException(response, "boom")

    thread.edit = AsyncMock(side_effect=edit)
    client = MagicMock()
    client.get_cog.return_value = None

    asyncio.run(close_thread(client, thread, "❌ Closed", "closed!"))  # must not raise
    thread.send.assert_awaited_once_with("closed!")
    assert db.get_thread_info(1)["locked"]
