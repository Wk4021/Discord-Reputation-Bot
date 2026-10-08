import os
from unittest.mock import MagicMock

import discord
import yaml

from utils import config
from utils.checks import is_admin
from utils.formatting import generate_star_rating, review_stars, star_bar


HOME = 555


def make_member(user_id=1, administrator=False, role_ids=(), guild_id=HOME):
    member = MagicMock(spec=discord.Member)
    member.id = user_id
    member.guild.id = guild_id
    member.guild_permissions.administrator = administrator
    member.roles = [MagicMock(id=r) for r in role_ids]
    return member


def test_star_rendering():
    assert star_bar(10) == "⭐⭐⭐⭐⭐"
    assert star_bar(7) == "⭐⭐⭐✨☆"
    assert review_stars(7) == "⭐⭐⭐✨"
    assert generate_star_rating(0, 0) is None
    assert generate_star_rating(8, 1) == "Rating: ⭐⭐⭐⭐☆ (8.0/10 from 1 review)"


def test_config_save_keeps_order_comments_and_emoji(temp_config):
    keys = list(yaml.safe_load(temp_config.read_text(encoding="utf-8")))
    data = config.load_config()
    data["tos_decline_response"] = "Nope 🚫"
    config.save_config(data)

    raw = temp_config.read_text(encoding="utf-8")
    assert "Nope 🚫" in raw
    assert "# Example: Marketplace forum" in raw
    assert list(yaml.safe_load(raw)) == keys


def test_config_normalizes_hand_edited_values(temp_config):
    lines = [
        "guild_id: '55'",
        "forums:",
        "admin_ids:",
        "  - '42'",
        "  - not-a-number",
        "log_channel: '7'",
        "auto_close_hours: '999'",
        "auto_close_enabled: 'false'",
        "bot_status:",
    ]
    temp_config.write_text("\n".join(lines) + "\n", encoding="utf-8")
    data = config.load_config()
    assert data["guild_id"] == 55
    assert data["forums"] == []
    assert data["admin_ids"] == [42]
    assert data["log_channel"] == 7
    assert data["auto_close_hours"] == 168
    assert data["auto_close_enabled"] is False
    assert data["bot_status"]["activity_type"] == "watching"

    # Saving doesn't add keys that were only filled in with defaults
    config.save_config(data)
    assert "tos_timeout_seconds" not in temp_config.read_text(encoding="utf-8")


def test_config_reloads_after_external_edit(temp_config):
    assert config.load_config()["auto_close_hours"] == 24
    data = yaml.safe_load(temp_config.read_text(encoding="utf-8"))
    data["auto_close_hours"] = 5
    temp_config.write_text(yaml.safe_dump(data), encoding="utf-8")
    stat = temp_config.stat()
    os.utime(temp_config, (stat.st_atime, stat.st_mtime + 10))
    assert config.load_config()["auto_close_hours"] == 5


def test_load_config_returns_independent_copies(temp_config):
    config.load_config()["forums"].append(1)
    assert 1 not in config.load_config()["forums"]


def test_get_forum_ids_accepts_strings():
    assert config.get_forum_ids({"forums": ["123", 456, "bad"]}) == [123, 456]
    assert config.get_forum_ids({}) == []


def test_is_admin(temp_config):
    data = config.load_config()
    data["guild_id"] = HOME
    data["admin_ids"] = [42]
    data["admin_role_ids"] = [7]
    config.save_config(data)

    assert is_admin(make_member(42))
    assert is_admin(make_member(1, role_ids=[7]))
    assert is_admin(make_member(1, administrator=True))
    assert not is_admin(make_member(1, role_ids=[8]))
    # Users outside a guild (DMs) are never admins
    assert not is_admin(MagicMock(spec=discord.User, id=42))


def test_admin_rights_only_apply_in_home_server(temp_config):
    data = config.load_config()
    data["guild_id"] = HOME
    data["admin_ids"] = [42]
    config.save_config(data)

    # Being Administrator of some other server the bot was invited to grants nothing
    assert not is_admin(make_member(1, administrator=True, guild_id=999))
    assert not is_admin(make_member(42, guild_id=999))


def test_without_home_server_administrator_is_not_enough(temp_config):
    data = config.load_config()
    data["guild_id"] = None
    data["admin_ids"] = [42]
    config.save_config(data)

    assert not is_admin(make_member(1, administrator=True, guild_id=999))
    assert is_admin(make_member(42, guild_id=999))
