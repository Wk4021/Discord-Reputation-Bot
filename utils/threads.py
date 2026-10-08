"""Shared actions on marketplace threads and the log channel."""
import time

import discord

from utils import db
from utils.config import load_config
from utils.interactions import reply_ephemeral


async def send_log(client: discord.Client, embed: discord.Embed) -> None:
    """Send an embed to the configured log channel, if there is one. Never raises."""
    log_ch_id = load_config()["log_channel"]
    if not log_ch_id:
        return
    log_ch = client.get_channel(log_ch_id)
    if not log_ch:
        return
    if embed.timestamp is None:
        embed.timestamp = discord.utils.utcnow()
    try:
        await log_ch.send(embed=embed)
    except discord.HTTPException as e:
        print(f"[WARN] Could not send to log channel {log_ch_id}: {e}")


async def update_thread_log(client: discord.Client, thread: discord.Thread, **kwargs) -> None:
    """Update the per-thread log embed via the LoggingSystem cog, if loaded. Never raises."""
    logging_cog = client.get_cog("LoggingSystem")
    if logging_cog:
        await logging_cog.update_thread_log(thread, **kwargs)


async def close_thread(client: discord.Client, thread: discord.Thread, status: str,
                       notice: str | discord.Embed | None = None) -> None:
    """
    Lock and archive a thread, record it in the database and set its
    "Thread Status" in the thread log.

    `status` is the log text, e.g. "❌ Closed"; the time is appended.
    `notice` is posted in the thread once it is locked, so nobody is told a
    post is closed unless locking actually worked.

    Raises discord.HTTPException if the thread can't be locked (for example
    when the bot lacks Manage Threads).
    """
    # Locking first proves we have permission; the bot can still post in a
    # locked thread. Archived threads must be unarchived to be edited.
    await thread.edit(locked=True, archived=False)
    db.mark_thread_closed(thread.id)

    if notice is not None:
        try:
            if isinstance(notice, discord.Embed):
                await thread.send(embed=notice)
            else:
                await thread.send(notice)
        except discord.HTTPException as e:
            print(f"[WARN] Could not post close notice in {thread.id}: {e}")

    # The post is closed once it's locked; failing to archive it only means
    # it stays in the active list, so don't report the close as failed
    try:
        await thread.edit(archived=True)
    except discord.HTTPException as e:
        print(f"[WARN] Locked thread {thread.id} but could not archive it: {e}")

    await update_thread_log(
        client, thread,
        field_updates={"Thread Status": f"{status} at <t:{int(time.time())}:T>"}
    )


async def close_thread_for(interaction: discord.Interaction, thread: discord.Thread, status: str,
                           notice: str | discord.Embed | None) -> bool:
    """
    Close a thread in response to a button or modal. Acknowledges the
    interaction first (closing can take longer than Discord's 3 seconds) and
    tells the user privately if it failed. Returns True on success.
    """
    if not interaction.response.is_done():
        await interaction.response.defer()
    try:
        await close_thread(interaction.client, thread, status, notice)
        return True
    except discord.HTTPException as e:
        print(f"[ERROR] Could not close thread {thread.id}: {e}")
        await reply_ephemeral(
            interaction, "❌ I couldn't close this post. Ask an admin to check that I have **Manage Threads**."
        )
        return False
