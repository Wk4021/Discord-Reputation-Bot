<!-- PROJECT BADGES -->
<p align="center">
  <a href="https://github.com/Wk4021/Discord-Reputation-Bot/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Wk4021/Discord-Reputation-Bot/ci.yml?branch=main&style=for-the-badge&label=CI" alt="CI Status"/></a>
  <a href="https://github.com/Wk4021/Discord-Reputation-Bot/stargazers"><img src="https://img.shields.io/github/stars/Wk4021/Discord-Reputation-Bot?style=for-the-badge" alt="GitHub Stars"/></a>
  <a href="https://github.com/Wk4021/Discord-Reputation-Bot/issues"><img src="https://img.shields.io/github/issues/Wk4021/Discord-Reputation-Bot?style=for-the-badge" alt="GitHub Issues"/></a>
  <a href="https://discord.com/servers/marketplace-and-student-stores-765205625524584458"><img src="https://img.shields.io/discord/765205625524584458?style=for-the-badge" alt="Discord Server"/></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge" alt="Python Version"/>
  <a href="https://github.com/Wk4021/Discord-Reputation-Bot/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Wk4021/Discord-Reputation-Bot?style=for-the-badge" alt="License"/></a>
</p>

# 🌟 Discord Reputation Bot V3.2

A reputation system for Discord marketplace communities. Members review each other with **1–10 star ratings and notes** inside forum posts, the bot gates new posts behind your **Terms of Service**, and finished listings are **closed automatically** to keep the marketplace tidy.

## 🆕 What's New in V3.2

- 🔒 **Security fixes**: every admin command is permission-checked, admin rights are limited to your own server, `!sync` is owner-only, and closed posts can no longer receive reviews
- ⏰ **Reliable auto-close**: correct timing in every time zone, and archived posts are still closed
- 🔁 **Restart-safe**: TOS prompts, buttons and log embeds keep working after the bot restarts
- 🧹 **Cleaner threads**: the review panel updates in place instead of reposting after every review
- 🗑️ **Web dashboard removed**: the bot is now Discord-only
- 🧪 **Tests and CI**: a pytest suite runs on Python 3.11–3.14 for every pull request

## 🚀 Features

### 🔒 TOS gating
- New posts in tracked forums get a Terms of Service prompt with a live countdown
- The post owner must agree before anyone can chat; declining or ignoring it closes the post
- Messages sent while the prompt is pending are removed

### ⭐ Reviews
- **⭐ Leave a Review** opens a form with a 1–10 rating and optional notes
- Reviewers must have posted in the thread, can't review themselves, and can review each post once
- The panel shows the owner's average rating, star bar and three latest reviews
- `/reviews @user` and `/leaderboard` let anyone look up reputations

### ⏰ Auto-close
- A post's first review starts a configurable timer (default 24 hours)
- The owner can cancel it with one click (useful for multi-item listings)
- Owners can close their own posts; closing a post with no reviews asks for confirmation

### 👑 Administration
- Server administrators, listed users and listed roles are bot admins (only in the server set by `guild_id`)
- `/settings` opens an interactive panel for auto-close, TOS text and bot status
- Every action is logged to a staff channel, with one live-updating embed per post

## 📁 Project Structure

```
Discord-Reputation-Bot/
├── bot.py                  # Entry point
├── RunMe.bat               # Windows launcher (start bot / install requirements)
├── cogs/
│   ├── reviews.py          # Post lifecycle, /reviews, /leaderboard, auto-close task
│   ├── admin.py            # Configuration and admin-management commands
│   └── logging_system.py   # Per-post log embeds in the log channel
├── views/
│   ├── tos.py              # TOS prompt
│   ├── review.py           # Review panel, review form, close flow
│   └── settings.py         # /settings panel
├── utils/
│   ├── db.py               # SQLite storage and migrations
│   ├── config.py           # config.yaml loading/saving
│   ├── checks.py           # Admin permission checks
│   ├── threads.py          # Shared close/log helpers
│   ├── presence.py         # Bot status
│   ├── formatting.py       # Star rendering, safe display of user text
│   ├── interactions.py     # Safe interaction replies and error reporting
│   └── messages.py         # Review-panel flavour text
├── assets/rep_messages.txt # Flavour text by rating (good / neutral / bad)
├── data/
│   ├── config.yaml.example # Copy to config.yaml
│   └── rep.db              # Created on first run
├── docs/                   # Guides
└── tests/                  # pytest suite
```

## 🚀 Quick Start

Full instructions, including Discord Developer Portal setup, are in **[docs/SETUP.md](docs/SETUP.md)**.

1. **Install Python 3.11+** and clone this repository.
2. **Create the bot** in the [Discord Developer Portal](https://discord.com/developers/applications), enable the **Server Members** and **Message Content** intents, and invite it with the permissions listed in [docs/SETUP.md](docs/SETUP.md#2-invite-the-bot).
3. **Configure it:**
   ```bash
   cp .env.example .env                              # add your bot token
   cp data/config.yaml.example data/config.yaml      # add your server, forum and log channel IDs
   ```
4. **Install and run:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   python bot.py
   ```
   On Windows you can instead double-click `RunMe.bat`: **[2]** creates the virtual environment and installs everything, **[1]** starts the bot.
5. **Register slash commands:** as the bot's owner, type `!sync` in your server. They appear immediately.

## 💬 Commands

| Command | Who | Description |
|---------|-----|-------------|
| `/reviews @user` | Everyone | A user's rating and latest reviews |
| `/leaderboard` | Everyone | Top 10 users by rating |
| `/settings` | Admins | Interactive settings panel |
| `/channel_set #forum` | Admins | Track another forum |
| `/log #channel` | Admins | Set the log channel |
| `/auto_close_toggle [true/false]` | Admins | Show or change auto-close |
| `/auto_close_hours <1-168>` | Admins | Set the auto-close timer |
| `/send_review_ui` | Admins | Post the review panel in the current thread |
| `/admin_add`, `/admin_remove`, `/admin_list` | Admins | Manage admin users |
| `/admin_role_add`, `/admin_role_remove` | Admins | Manage admin roles |
| `!sync [global]` | Bot owner | Register slash commands |

Details and examples: **[docs/COMMANDS.md](docs/COMMANDS.md)**.

## 📚 Documentation

- **[SETUP.md](docs/SETUP.md)**: installation, permissions and upgrading
- **[COMMANDS.md](docs/COMMANDS.md)**: every command in detail
- **[ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md)**: who counts as an admin and what admins can do
- **[CLOSE_POST_FLOW.md](docs/CLOSE_POST_FLOW.md)**: how posts are closed, manually and automatically
- **[LOGGING_GUIDE.md](docs/LOGGING_GUIDE.md)**: the log channel, and logging from your own cogs
- **[REVIEW_SYSTEM_MIGRATION.md](docs/REVIEW_SYSTEM_MIGRATION.md)**: history of the move from +/- rep to star reviews

## ❓ Troubleshooting

**Slash commands don't appear.** Run `!sync` in your server as the bot owner.

**"Only admins can use this command."** Check that `guild_id` in `data/config.yaml` is your server's ID, then add your user ID to `admin_ids` (or have a server administrator run `/admin_add` for you).

**The bot doesn't respond to new posts.** Check that the forum's ID is in `forums` (or add it with `/channel_set`) and that the bot can view the forum and send messages in threads.

**Messages aren't removed during the TOS prompt, or posts don't lock.** The bot needs **Manage Messages** and **Manage Threads**.

**"DISCORD_TOKEN is not set."** Copy `.env.example` to `.env` and paste your bot token.

## 🧪 Development

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
flake8 .
```

CI runs the same checks on Python 3.11–3.14 for pull requests and pushes to `main`.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for your change and make sure `pytest` passes
4. Open a pull request

---

<p align="center">
  <strong>⭐ If you find this bot useful, please give it a star! ⭐</strong><br/>
  <em>Join our community:</em> <a href="https://discord.com/servers/marketplace-and-student-stores-765205625524584458">Marketplace & Student Stores</a>
</p>
