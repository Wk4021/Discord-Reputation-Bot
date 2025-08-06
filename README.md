<!-- PROJECT BADGES -->
<p align="center">
  <a href="https://github.com/Wk4021/Marketplace-Discord-Rep-Bot/releases"><img src="https://img.shields.io/github/v/release/Wk4021/Marketplace-Discord-Rep-Bot?style=for-the-badge" alt="Release"/></a>
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

- 📝 **Thread Log & Persistence**  
  - **Persistent Views**: +Rep, −Rep, and Close buttons survive bot restarts.  
  - **Single‐Embed Thread Logs** in your `/log set` channel:  
    - **TOS Status**: ⏳ Pending → ✅ Accepted / ❌ Declined / ⌛ Timed‐out  
    - **Rep Events**: Appends each +/− rep with timestamps  
    - **Thread Status**: ✅ Open → ❌ Closed (with time)

- 📊 **Lookup & Leaderboard**  
  - `/rep @user` — View a user’s total 👍 and 👎 rep and star gauge.  
  - `/repleaderboard` — Display the **Top 10** sellers by positive rep.

- 🔧 **Slash-Command Configuration**  
  - `/channel_set <forum>` — Activate a forum channel for marketplace gating.  
  - `/log set <channel>` — Send rep-action embeds to a designated log channel.

- 💾 **Persistence & Reliability**  
  - Uses **SQLite** (`data/rep.db`) for all reputation data.  
  - Easy config via `data/config.yaml` & `assets/rep_messages.txt`.  
  - All bot messages are **Discord embeds** for best readability.

  ### 🔒 Moderation & Trust System

  - **Strike & Warning Tracking** – Users who let posts auto‑close receive warnings; after a threshold of warnings, a strike is issued. View counts via `/strikeinfo @user`.
  - **Strike Appeals** – Users can submit an appeal explaining why a strike should be removed with `/appealstrike <reason>`.
  - **Trust Score** – Mods can view an aggregate trust score based on positive/negative rep and strikes using `/trustscore @user`.
  - **Fraud Checks** – Flag suspicious patterns (e.g. multiple reps from the same giver) with `/fraudcheck`.

  ### 🌐 Web Integration (Planned)

  These features require an accompanying web service. The bot includes scaffolding to integrate:
  - **OAuth Discord Linking** – Connect a Discord account to a web profile for private stats.
  - **Item Sales System** – Mark items as “Sold” and tie them to buyers.
  - **Rep Analytics Dashboard** – Charts and analytics on rep history and marketplace activity.
  - **Custom Profile Pages** – User bios, pinned threads, badges, and top sales.

  ### 🤖 Bot Enhancements

  - **Reminders & Pings** – Warn users 24 hours before their thread will be auto‑closed for inactivity.
  - **Feedback & Tags** – After giving rep, optionally add a descriptive tag with `/addtag` or leave free‑form feedback with `/feedback`.
  - **Rate Limiting** – Prevent rep spamming: you can only rep the same user once every 24 hours.
  - **Silent Post Mode** – Placeholder command `/silentmode` to bypass TOS gating for trusted sellers (not yet implemented).

  ### 🧠 Intelligence / Automation

  - **Seller Suggestions** – `/suggestsellers` recommends top sellers based on positive rep totals.
  - **Title Validation** – Automatically closes threads with banned words (e.g. “scam”, “fraud”) upon creation.
  - **Inactivity Detection by Message Quality** – Planned: ignore low‑effort “bump” messages when tracking last activity.

  ### 📦 Sales Integration

  - **Sale Confirmation** – Sellers can confirm a sale with `/confirm_sale @buyer [item]`, which logs the transaction and notifies the buyer.
  - **Transaction Logging** – All sales are recorded in the `transactions` table for future analytics and profile displays.
  - **Escrow & Multi‑Item Threads** – Planned: moderate payment release and handle multiple items within a single thread.

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
│   └── rep_messages.txt    # “No-rep” & GIF URLs
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
   log_channel: 123456789012345678  # Optional: ID for logging
   ```

4. **Run the bot**

   ```bash
   python bot.py
   ```

   Or on Windows, double-click `run_bot.bat`.

5. **Invite & Sync**

   Invite with both `bot` and `applications.commands` scopes:

   ```
   https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID
     &scope=bot%20applications.commands&permissions=8
   ```

   Use `!sync` to register slash commands globally (may take up to 1 hour).

---

## 📊 Star‐Rating Guide

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
Please [open an issue](https://github.com/Wk4021/Marketplace-Discord-Rep-Bot/issues).

**Q: Can I contribute or request features?**
Absolutely—fork the repo, submit a PR, and ⭐ the project!

**Q: Why do my slash commands take a while?**
Global registration can take up to **1 hour**. Use `!sync` for an immediate update.

---

<p align="center">
  ⭐ If you find this bot useful, please give it a star! ⭐  
  <br/>
  <em>Join our community on Discord:</em> <a href="https://discord.com/servers/marketplace-and-student-stores-765205625524584458">Marketplace & Student Stores</a>
</p>

