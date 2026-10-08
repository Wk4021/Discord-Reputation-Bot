# bot.py - Entry point for Discord Forum Rep Bot
import asyncio
import os
import sys

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from utils.checks import get_home_guild_id, is_home_guild
from utils.config import CONFIG_PATH, PROJECT_ROOT, load_config
from utils.db import init_db
from utils.interactions import reply_ephemeral
from utils.presence import presence_from_config

# Console output contains emoji; don't crash when it is redirected to a file
# or a console that can't encode them (common on Windows).
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(errors="replace")

# Load environment variables from .env next to this file
load_dotenv(PROJECT_ROOT / ".env")

EXTENSIONS = ("cogs.logging_system", "cogs.reviews", "cogs.admin")

# Configure bot intents
intents = discord.Intents.default()
intents.message_content = True  # needed for the !sync prefix command
intents.members = True          # member cache for admin lists and the leaderboard


class RepTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # The bot manages one server; ignore commands from any other server
        if interaction.guild_id is not None and not is_home_guild(interaction.guild_id):
            await reply_ephemeral(interaction, "❌ This bot isn't set up for this server.")
            return False
        return True


class RepBot(commands.Bot):
    async def setup_hook(self):
        init_db()
        for extension in EXTENSIONS:
            await self.load_extension(extension)

        config = load_config()
        if config["guild_id"] is None:
            print("⚠️  guild_id is not set in data/config.yaml. Set it to your server's ID: until then "
                  "server administrators are not automatically bot admins and commands work in every server.")
            if not config["admin_ids"] and not config["admin_role_ids"]:
                print("⚠️  No admins are configured either, so nobody can use admin commands. "
                      "Set guild_id (or admin_ids) in data/config.yaml and restart.")

        # Set the configured presence before connecting so it's sent on login
        activity, status = presence_from_config(config)
        if activity:
            self.activity = activity
            self.status = status


# Mentions are limited to users so text from config or user input can never
# ping @everyone/@here or roles.
bot = RepBot(
    command_prefix="!",
    intents=intents,
    tree_cls=RepTree,
    allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
)


@bot.event
async def on_ready():
    """Called when the bot is ready (and again after reconnects)."""
    print(f"✅ Logged in as {bot.user}")
    home = get_home_guild_id()
    for guild in bot.guilds:
        if home is not None and guild.id != home:
            print(f"⚠️  Also in another server: {guild.name} ({guild.id}). Commands there are ignored; "
                  "consider turning off 'Public Bot' in the Developer Portal.")
    print("✅ Ready. Use !sync to register slash commands in your server.")


@bot.command(name="sync")
@commands.is_owner()
async def sync_commands(ctx: commands.Context, scope: str = "guild"):
    """
    Register slash commands with Discord (bot owner only).

    !sync         - register in the configured server (or this one); appears instantly
    !sync global  - register in every server (can take up to an hour)

    Each mode removes the other's registrations so commands never show twice.
    """
    home = get_home_guild_id()
    guild = discord.Object(id=home) if home is not None else ctx.guild
    app_id = bot.application_id
    try:
        if scope == "global":
            synced = await bot.tree.sync()
            note = ""
            if guild is not None:
                await bot.http.bulk_upsert_guild_commands(app_id, guild.id, [])
            else:
                note = " Per-server copies were not removed; run this inside the server if commands show twice."
            await ctx.send(f"✅ Globally synced {len(synced)} slash commands. (May take up to 1 hour to appear){note}")
        else:
            if guild is None:
                return await ctx.send("❌ Use `!sync` inside your server, or set guild_id in the config.")
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            # Clearing global commands would also remove them from other
            # servers, which only makes sense when the bot is pinned to one
            if home is not None:
                await bot.http.bulk_upsert_global_commands(app_id, [])
            await ctx.send(f"✅ Synced {len(synced)} slash commands to the server.")
        print(f"✅ Synced {len(synced)} slash commands ({scope}).")
    except discord.HTTPException as e:
        print(f"[ERROR] Failed to sync commands: {e}")
        await ctx.send("❌ Failed to sync commands.")


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    # Silently ignore unknown prefix commands and non-owners trying !sync
    if isinstance(error, (commands.CommandNotFound, commands.NotOwner)):
        return
    print(f"[ERROR] Command {ctx.command} failed: {error}")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        message = str(error) if str(error) else "❌ You can't use this command here."
    else:
        print(f"[ERROR] /{interaction.command.name if interaction.command else '?'} failed: {error!r}")
        message = "❌ Something went wrong while running that command."
    await reply_ephemeral(interaction, message)


def check_setup() -> str | None:
    """Return the token, or None after explaining what's missing."""
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("❌ DISCORD_TOKEN is not set. Copy .env.example to .env and add your bot token.")
        return None
    if not CONFIG_PATH.exists():
        print(f"❌ {CONFIG_PATH} not found. Copy data/config.yaml.example to data/config.yaml and fill it in.")
        return None
    return token


async def main(token: str):
    # Route discord.py's own log messages (rate limits, gateway issues) to the console
    discord.utils.setup_logging()
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    token = check_setup()
    if token is None:
        sys.exit(1)
    try:
        asyncio.run(main(token))
    except KeyboardInterrupt:
        pass
