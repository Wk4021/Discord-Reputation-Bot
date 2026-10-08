# Command Reference

All slash commands work only inside the server set by `guild_id` (elsewhere they reply "❌ This bot isn't set up for this server."). Admin commands reply with "❌ Only admins can use this command." to anyone else. See [ADMIN_GUIDE.md](ADMIN_GUIDE.md) for who counts as an admin.

## Public commands

### `/reviews <user>`
Shows a user's average rating, review count and three latest reviews (only you can see the reply). Works for people who have left the server.

```
⭐ Reviews for UserName
Rating: ⭐⭐⭐⭐☆ (8.2/10 from 5 reviews)

Latest Reviews
⭐⭐⭐⭐⭐ 10/10 by @Reviewer1
> Excellent service, very professional!
```

### `/leaderboard`
Posts the top 10 users by average rating (ties broken by number of reviews).

## Admin commands

### `/settings`
Opens a private settings panel:

| Button | What it changes |
|--------|-----------------|
| 🔧 Auto-Close Settings | Auto-close on/off, timer (1–168 hours), admin close confirmation |
| 📋 TOS Settings | TOS prompt text and decline message |
| 👑 Admin Settings | Shows current admin users and roles |
| 🤖 Bot Status | Activity type, status message and online status |
| 🔄 Refresh | Reloads the panel |

Changes are saved to `data/config.yaml` and logged to the log channel.

### `/channel_set <forum>`
Adds a forum to the tracked list. New posts there get the TOS prompt and review panel.

### `/log <channel>`
Sets the channel where the bot logs activity.

### `/auto_close_toggle [enabled]`
Without an argument, shows the current auto-close settings. With `true` or `false`, turns auto-close on or off. Posts that already have a timer keep it.

### `/auto_close_hours <hours>`
Sets how long after a post's first review it closes (1–168). Only affects timers started afterwards.

### `/send_review_ui`
Posts a review panel in the current thread. Useful for posts created before the bot was added, or if the panel was deleted.

### `/admin_add <user>` / `/admin_remove <user>`
Adds or removes a user in `admin_ids`. `/admin_remove` also accepts people who have left the server, and won't remove the last listed admin if that's you. It can't remove admin rights that come from a role or from the server Administrator permission, and says so if the user is still an admin that way.

### `/admin_role_add <role>` / `/admin_role_remove <role>`
Adds or removes a role in `admin_role_ids`. @everyone and bot-managed roles can't be added.

### `/admin_list`
Lists configured admin users and roles.

## Owner command

### `!sync [global]`
Registers slash commands with Discord. Only the bot's owner can use it; anyone else is ignored.

- `!sync`: your server (`guild_id`, or the current server if it isn't set), appears immediately
- `!sync global`: every server, can take up to an hour

Each form removes the other's registrations, so commands never appear twice.

## Buttons

| Button | Where | Who |
|--------|-------|-----|
| ✅ I Agree / ❌ I Do Not Agree | TOS prompt on a new post | Post owner |
| ⭐ Leave a Review | Review panel | Anyone who has posted in the thread, except the owner |
| Close Post | Review panel | Post owner or admins ([details](CLOSE_POST_FLOW.md)) |
| I have multiple items - Keep thread open | Auto-close notice | Post owner |

Buttons keep working after the bot restarts. In closed posts the review, close and keep-open buttons reply "🔒 This post is closed."; an answered or expired TOS prompt replies "⌛ This prompt has expired."
