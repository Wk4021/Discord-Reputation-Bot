# Logging Guide

The bot logs to the channel set by `log_channel` in `data/config.yaml` (or `/log`). If no log channel is set, or the bot can't post there, logging is skipped and everything else keeps working.

## What gets logged

**One live embed per post.** When a post is created in a tracked forum, the bot posts an embed and keeps editing it:

| Field | Example |
|-------|---------|
| TOS Status | ⏳ Pending → ✅ Accepted at 14:02 |
| Review Events | @Buyer gave 9/10 rating at 15:30 (one line per review, newest kept if it gets long) |
| Thread Status | ✅ Open → 🤖 Auto-closed at 15:30 |

The embed's message ID is stored in the database, so the same embed keeps updating after a restart.

**Separate entries** for each submitted review, auto-close scheduled or cancelled, admin force-closes, auto-closes, settings changes and opening `/settings`.

## Logging from your own cog

Use the helpers in `utils/threads.py`:

```python
import discord
from utils.threads import send_log, update_thread_log

# One-off log entry (timestamp added automatically)
embed = discord.Embed(title="📦 Item sold", description=f"{member.mention} sold an item")
await send_log(bot, embed)

# Update a post's live embed
await update_thread_log(
    bot, thread,
    field_updates={"Thread Status": "✅ Sold"},           # replace a field (added if missing)
    event_additions={"Review Events": "Buyer confirmed"},  # append a timestamped line
)
```

`update_thread_log` creates the post's embed if it doesn't exist yet. To create one with custom fields, call the cog directly:

```python
logging_cog = bot.get_cog("LoggingSystem")
if logging_cog:
    await logging_cog.create_thread_log(thread, fields={"Status": "Active", "Events": "*No events yet*"})
```

Load `cogs.logging_system` before cogs that use it (see `EXTENSIONS` in `bot.py`).
