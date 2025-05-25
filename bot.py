# bot.py - Entry point for Discord Forum Rep Bot
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
from utils.db import init_db
from cogs.rep import RepTOSView, RepButtonView

# Load environment variables from .env
load_dotenv()

# Configure bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.messages = True

# Initialize bot
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    """
    Called when the bot is ready. Initializes the database,
    registers persistent views, and prints startup confirmation.
    """
    print(f"✅ Logged in as {bot.user}")
    init_db()

    # Register persistent views for button survival
    bot.add_view(RepButtonView())
    bot.add_view(RepTOSView())
    bot.add_view(RepButtonView(None, None))

    print("✅ Ready. Use !sync to globally sync slash commands.")

@bot.command(name="sync")
async def sync_commands(ctx: commands.Context):
    """
    Clears & re-syncs global slash commands (may take up to 1 hour to propagate).
    """
    try:
        # Optional: uncomment if you want to fully clear before syncing
        # bot.tree.clear_commands()

        synced = await bot.tree.sync()
        print(f"✅ Globally synced {len(synced)} slash commands.")
        await ctx.send(f"✅ Globally synced {len(synced)} slash commands. (May take up to 1 hour to appear)")
    except Exception as e:
        print(f"[ERROR] Failed to sync globally: {e}")
        await ctx.send("❌ Failed to sync commands.")

async def main():
    """
    Main entrypoint for loading cogs and starting the bot.
    """
    async with bot:
        await bot.load_extension("cogs.rep")
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())
