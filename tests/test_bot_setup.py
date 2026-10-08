"""Loads every extension the way the real bot does, without connecting to Discord."""
import asyncio

import bot as bot_module

ADMIN_COMMANDS = {
    "channel_set", "log", "admin_add", "admin_remove", "admin_list", "admin_role_add",
    "admin_role_remove", "auto_close_toggle", "auto_close_hours", "settings", "send_review_ui",
}
PUBLIC_COMMANDS = {"reviews", "leaderboard"}


def test_extensions_load_and_register_everything(temp_config, temp_db):
    bot = bot_module.RepBot(command_prefix="!", intents=bot_module.intents)

    async def run():
        async with bot:
            await bot.setup_hook()
            commands = {c.name: c for c in bot.tree.get_commands()}
            custom_ids = {
                item.custom_id
                for view in bot.persistent_views
                for item in view.children
            }
            return commands, custom_ids, bot.activity

    commands, custom_ids, activity = asyncio.run(run())

    assert set(commands) == ADMIN_COMMANDS | PUBLIC_COMMANDS
    admin_check = "admin_only.<locals>.predicate"
    for name, command in commands.items():
        assert command.guild_only, name
        has_admin_check = any(c.__qualname__ == admin_check for c in command.checks)
        assert has_admin_check == (name in ADMIN_COMMANDS), name

    # Every button that must survive restarts is registered as persistent
    assert {"leave_review", "close_post", "cancel_auto_close", "tos_agree", "tos_decline"} <= custom_ids

    # Configured status is applied before connecting
    assert activity is not None and activity.name == "marketplace reviews"
