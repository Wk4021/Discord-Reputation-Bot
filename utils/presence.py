"""Applies the configurable bot status (activity + online status)."""
import discord

STATUS_TYPES = {
    "online": discord.Status.online,
    "idle": discord.Status.idle,
    "dnd": discord.Status.dnd,
    "invisible": discord.Status.invisible,
}

ACTIVITY_TYPES = {
    "playing": discord.ActivityType.playing,
    "listening": discord.ActivityType.listening,
    "watching": discord.ActivityType.watching,
    "competing": discord.ActivityType.competing,
    "streaming": discord.ActivityType.streaming,
}


def build_presence(activity_type: str, message: str, status_type: str) -> tuple[discord.BaseActivity, discord.Status]:
    status = STATUS_TYPES.get(status_type, discord.Status.online)
    if activity_type == "streaming":
        # Streaming requires a URL (using a placeholder)
        activity = discord.Streaming(name=message, url="https://twitch.tv/placeholder")
    else:
        activity = discord.Activity(type=ACTIVITY_TYPES.get(activity_type, discord.ActivityType.watching), name=message)
    return activity, status


def presence_from_config(config: dict) -> tuple[discord.BaseActivity | None, discord.Status | None]:
    """Presence described by the config's bot_status section, or (None, None) if disabled."""
    bot_status = config.get("bot_status") or {}
    if not bot_status.get("enabled", True):
        return None, None
    return build_presence(
        bot_status.get("activity_type", "watching"),
        bot_status.get("message", "marketplace reviews"),
        bot_status.get("status_type", "online"),
    )


async def apply_bot_status(bot: discord.Client, activity_type: str, message: str, status_type: str):
    """Update the bot's Discord presence while it is connected."""
    try:
        activity, status = build_presence(activity_type, message, status_type)
        await bot.change_presence(status=status, activity=activity)
        print(f"[BOT-STATUS] Updated bot status: {activity_type} {message} ({status_type})")
    except Exception as e:
        print(f"[ERROR] Failed to update bot status: {e}")


async def clear_bot_status(bot: discord.Client):
    """Remove the custom activity while the bot is connected."""
    try:
        await bot.change_presence(activity=None, status=discord.Status.online)
        print("[BOT-STATUS] Custom status cleared")
    except Exception as e:
        print(f"[ERROR] Failed to clear bot status: {e}")
