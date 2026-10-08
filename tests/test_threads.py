"""Behaviour of the shared close/log helpers, using mocked Discord objects."""
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

from cogs.logging_system import LoggingSystem
from utils import db
from utils.formatting import capped_lines
from utils.messages import load_rep_messages
from utils.threads import close_thread


def http_error(cls=discord.Forbidden, status=403):
    response = MagicMock(status=status, reason="nope")
    return cls(response, "nope")


def make_thread(thread_id=1):
    thread = MagicMock(spec=discord.Thread)
    thread.id = thread_id
    thread.name = "Selling stuff"
    thread.owner_id = 10
    thread.jump_url = "https://discord.com/channels/1/2/3"
    thread.edit = AsyncMock()
    thread.send = AsyncMock()
    return thread


def make_client(log_channel=None):
    client = MagicMock(spec=commands.Bot)
    client.get_channel.return_value = log_channel
    cog = LoggingSystem(client)
    client.get_cog.return_value = cog
    return client


def track(thread_id=1):
    db.upsert_thread(thread_id, 100, 1000, "Selling stuff", 10, "https://discord.com/channels/1/2/3")


def test_close_still_works_when_log_channel_is_unwritable(temp_config, temp_db):
    track()
    log_channel = MagicMock(spec=discord.TextChannel)
    log_channel.send = AsyncMock(side_effect=http_error())
    thread = make_thread()

    asyncio.run(close_thread(make_client(log_channel), thread, "❌ Closed", "closed!"))

    thread.edit.assert_any_await(locked=True, archived=False)
    thread.edit.assert_any_await(archived=True)
    thread.send.assert_awaited_once_with("closed!")
    assert db.get_thread_info(1)["locked"]


def test_no_notice_is_posted_when_locking_fails(temp_config, temp_db):
    track()
    thread = make_thread()
    thread.edit.side_effect = http_error()

    with pytest.raises(discord.Forbidden):
        asyncio.run(close_thread(make_client(), thread, "🤖 Auto-closed", "closed!"))

    thread.send.assert_not_awaited()
    assert not db.get_thread_info(1)["locked"]


def test_closed_thread_is_no_longer_due_for_auto_close(temp_config, temp_db):
    import time
    track()
    db.schedule_thread_auto_close(1, time.time() - 60)
    assert db.is_auto_close_due(1)
    asyncio.run(close_thread(make_client(), make_thread(), "🤖 Auto-closed"))
    assert not db.is_auto_close_due(1)
    assert db.get_threads_to_auto_close() == []


def test_reopened_thread_is_usable_again(temp_config, temp_db):
    track()
    db.mark_thread_closed(1)
    db.set_thread_state(1, archived=False, locked=False)
    info = db.get_thread_info(1)
    assert not info["locked"] and not info["archived"]


def test_rep_messages_load_from_any_directory(tmp_path):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        messages = load_rep_messages()
    finally:
        os.chdir(cwd)
    assert messages["good"] and messages["bad"]


def test_capped_lines_respects_embed_field_limit():
    lines = [f"• <@{i:018d}> (ID: {i:018d})" for i in range(100)]
    text = capped_lines(lines)
    assert len(text) <= 1024
    assert text.endswith("more")
    assert capped_lines([]) == "None"
    assert capped_lines(["a", "b"]) == "a\nb"
