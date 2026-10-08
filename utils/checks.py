"""Permission checks."""
import discord
from discord import app_commands

from utils.config import load_config


class NotAdmin(app_commands.CheckFailure):
    """Raised by the admin_only() check; the tree error handler reports it to the user."""


def get_home_guild_id(config: dict | None = None) -> int | None:
    """The server this bot manages (config `guild_id`), if configured."""
    return (config or load_config()).get("guild_id")


def is_home_guild(guild_id: int | None, config: dict | None = None) -> bool:
    """
    True if guild_id is the managed server. With no guild_id configured every
    server counts, which keeps older configs working.
    """
    home = get_home_guild_id(config)
    return home is None or guild_id == home


def is_admin(user: discord.abc.User) -> bool:
    """
    Check if a user is a bot admin.

    Admin rights only apply inside the managed server (config `guild_id`).
    The bot's settings are global, so without this anyone could invite the
    bot to a server of their own and make themselves an admin everywhere.

    Inside that server, administrators always count (so a fresh install can
    be configured from Discord), as do users in admin_ids and members with
    one of the admin_role_ids roles.
    """
    # Outside a guild there are no roles or permissions to check
    if not isinstance(user, discord.Member):
        return False

    config = load_config()
    home = get_home_guild_id(config)
    if home is not None and user.guild.id != home:
        return False

    # The Administrator shortcut is only safe when the bot is pinned to one server
    if home is not None and user.guild_permissions.administrator:
        return True

    if user.id in config["admin_ids"]:
        return True

    return any(role.id in config["admin_role_ids"] for role in user.roles)


def admin_only():
    """App-command check that only lets bot admins run the command."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not is_admin(interaction.user):
            raise NotAdmin("❌ Only admins can use this command.")
        return True

    return app_commands.check(predicate)
