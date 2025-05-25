<!-- PROJECT BADGES -->
<p align="center">
  <a href="https://github.com/Wk4021/Marketplace-Discord-Rep-Bot/actions"><img src="https://img.shields.io/github/actions/workflow/status/Wk4021/Marketplace-Discord-Rep-Bot/ci.yml?style=for-the-badge" alt="CI Status"/></a>
  <a href="https://github.com/Wk4021/Marketplace-Discord-Rep-Bot/stargazers"><img src="https://img.shields.io/github/stars/Wk4021/Marketplace-Discord-Rep-Bot?style=for-the-badge" alt="GitHub Stars"/></a>
  <a href="https://github.com/Wk4021/Marketplace-Discord-Rep-Bot/issues"><img src="https://img.shields.io/github/issues/Wk4021/Marketplace-Discord-Rep-Bot?style=for-the-badge" alt="GitHub Issues"/></a>
  <a href="https://discord.com/servers/marketplace-and-student-stores-765205625524584458"><img src="https://img.shields.io/discord/765205625524584458?style=for-the-badge" alt="Discord Server"/></a>
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge" alt="Python Version"/>
  <a href="https://github.com/Wk4021/Marketplace-Discord-Rep-Bot/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Wk4021/Marketplace-Discord-Rep-Bot?style=for-the-badge" alt="License"/></a>
</p>

# 📌 Marketplace Discord Rep Bot

A **Discord** bot that transforms your forum channels into a trusted, reputation-driven marketplace.  
Threads are gated behind a Terms of Service prompt, early messages are auto-deleted until TOS is handled, and buyers can leave **+rep / −rep** ratings on sellers’ posts. All data persists in **SQLite**, configurable via **slash commands**, and displayed through **rich embeds**.

---

## 🚀 Features

- 🔒 **TOS Gating**  
  - New threads in tracked forums prompt OP to accept or decline Terms of Service.  
  - Live countdown with Discord’s `<t:TIMESTAMP:R>` format.  
  - Non-bot messages before acceptance/decline are auto-deleted.  
  - Threads auto-close on timeout if unattended.

- ⭐ **Reputation System**  
  - OP’s reputation shown as a ⭐ star rating or cheeky “no rep” message.  
  - Buyers click **+ Rep** / **− Rep** buttons (one per user per thread).  
  - OP cannot rate themselves and must receive ≥1 rep before closing.  
  - Admins can override close logic with **Manage Threads** permission.

- 📊 **Lookup & Leaderboard**  
  - `/rep @user` — View a user’s total 👍 and 👎 rep and star gauge.  
  - `/repleaderboard` — Display the **Top 10** sellers by positive rep.

- 🛠️ **Slash-Command Configuration**  
  - `/channel_set <forum>` — Activate a forum channel for marketplace gating.  
  - `/log set <channel>` — Send rep-action embeds to a designated log channel.

- 💾 **Persistence & Reliability**  
  - Uses **SQLite** (`data/rep.db`) for all reputation data.  
  - **Persistent Views**: Buttons survive bot restarts.  
  - Easy config via `data/config.yaml` & `assets/rep_messages.txt`.  
  - All bot messages are **Discord embeds** for best readability.

---

## 📁 Project Structure

```bash
discord_forum_rep_bot/
├── bot.py                  # Entry point: loads cogs, registers views, handles sync
├── cogs/
│   └── rep.py              # Core cog: TOS gating, rep UI, commands, listeners
├── data/
│   ├── config.yaml         # Settings: tracked forums, messages, log channel
│   └── rep.db              # SQLite DB (auto-created)
├── utils/
│   └── db.py               # SQLite helper: schema init, add/get rep, leaderboard
├── assets/
│   └── rep_messages.txt    # “No rep” message pool
├── .env                    # ⚠️ DISCORD_TOKEN (in .gitignore)
├── requirements.txt        # Dependencies
└── .gitignore              # ignore `.env`, `__pycache__/`, `data/rep.db`, `.venv/`
````

---

## ⚙️ Installation & Setup

1. **Clone & install dependencies**

   ```bash
   git clone https://github.com/Wk4021/Marketplace-Discord-Rep-Bot.git
   cd Marketplace-Discord-Rep-Bot
   pip install -r requirements.txt
   ```

2. **Create `.env`**

   ```env
   DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
   ```

3. **Configure `data/config.yaml`**

   ```yaml
   forums:
     - 123456789012345678   # Forum channel IDs
   tos_message: |
     Please review our Terms of Service in <#123456789012345678>,
     then click ✅ or ❌. This post will auto-close {timeout} if no action.
   tos_decline_response: |
     You declined the Terms. This thread is now closed.
   no_rep_messages:
     - "Damn, get your rep up! 📈"
     - "Zero rep? 🚨 Proceed with caution!"
     # …add more!
   log_channel: 123456789012345678  # Optional: ID for logging
   ```

4. **Run the bot**

   ```bash
   python bot.py
   ```

5. **Invite & Sync**

   * Invite with `applications.commands` scope:

     ```
     https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot%20applications.commands&permissions=8
     ```
   * Use `!sync` to register slash commands globally (may take up to 1 hour).

---

## 📊 Star-Rating Guide

| Pos ➗ Total | Score (0–10) | Stars (out of 5) |
| :---------: | :----------: | :--------------: |
|    0 / 0    |       —      |       ☆☆☆☆☆      |
|    1 / 1    |      10      |       ⭐⭐⭐⭐⭐      |
|    3 / 4    |       8      |       ⭐⭐⭐⭐☆      |
|    2 / 5    |       4      |       ⭐⭐☆☆☆      |
|    0 / 5    |       0      |       ☆☆☆☆☆      |

---

## ❓ Troubleshooting & FAQ

**Q: How do I report bugs or ask questions?**
Please [open an issue](https://github.com/Wk4021/Marketplace-Discord-Rep-Bot/issues) on the repo.

**Q: Can I contribute or request new features?**
Absolutely! Fork the repo, submit a PR, and don’t forget to ⭐ the project if you find it helpful.

**Q: Why are slash commands delayed?**
Global sync can take up to **1 hour**. Use `!sync` to manually trigger registration.

---

<p align="center">
  ⭐ If you find this bot useful, please give it a star! ⭐  
  <br/>
  <em>Join our community on Discord:</em> <a href="https://discord.com/servers/marketplace-and-student-stores-765205625524584458">Marketplace & Student Stores</a>
</p>
