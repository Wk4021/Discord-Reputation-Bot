```markdown
# 📌 Discord Forum Rep Bot

A **Discord bot** that turns your forum channels into a moderated, reputation-driven marketplace. New threads are gated behind a Terms of Service prompt, user messages are auto-deleted until TOS is accepted or declined, and buyers can leave +rep/–rep ratings on sellers’ posts. All ratings, leaderboards, and logs are persisted in SQLite and configurable via slash commands.

---

## 🚀 Features

- 🛡 **TOS Gating**  
  - New threads in tracked forums prompt OP to accept or decline Terms of Service.  
  - Countdown timer shown with `<t:TIMESTAMP:R>` format.  
  - Any non-bot messages sent before acceptance/decline are auto-deleted.  
  - Threads auto-close after timeout if no response.

- ⭐ **Reputation System**  
  - OP’s rep displayed as star rating (out of 5) or a cheeky “no rep” message.  
  - Buyers click **+ Rep** / **– Rep** buttons (one per user per thread).  
  - OP cannot rate themselves; OP cannot close until they’ve received at least one rep.  
  - Admins (Manage Threads perm) can override and close immediately.

- 📊 **Lookup & Leaderboard**  
  - `/rep @user` — view that user’s total 👍 and 👎 rep and star rating.  
  - `/repleaderboard` — top 10 users by total positive rep.

- 📝 **Slash-Commands Configuration**  
  - `/channel_set <forum>` — activate a forum channel for rep/TOS gating.  
  - `/log set <channel>` — designate a channel to receive embed-style rep logs.

- 🔄 **Persistence & Reliability**  
  - Uses **SQLite** for all reputation data (`data/rep.db`).  
  - **Persistent Views**: buttons survive bot restarts.  
  - Configurable via **`data/config.yaml`**.  
  - All bot messages are rich embeds for clarity.

---

## 📁 File Structure

```

discord\_forum\_rep\_bot/
├── bot.py                  # Entry point: loads cogs, registers views, syncs commands
├── cogs/
│   └── rep.py              # Core cog: TOS gating, rep UI, slash commands, listeners
├── data/
│   ├── config.yaml         # Your settings: tracked forums, TOS text, funny messages, log channel
│   └── rep.db              # SQLite database (auto-created on first run)
├── utils/
│   └── db.py               # SQLite helper: schema init, add/get rep, leaderboard
├── assets/
│   └── rep\_messages.txt    # One-line “no rep” messages (randomized)
├── .env                    # ⚠️ add your `DISCORD_TOKEN` here (see .gitignore)
├── requirements.txt        # `discord.py`, `PyYAML`, `python-dotenv`
└── .gitignore              # ignore `.env`, `__pycache__/`, `data/rep.db`, `.venv/`

````

---

## ⚙️ Setup & Run

1. **Clone & install dependencies**  
   ```bash
   git clone https://github.com/yourusername/discord_forum_rep_bot.git
   cd discord_forum_rep_bot
   pip install -r requirements.txt
````

2. **Create `.env`**

   ```env
   DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
   ```

3. **Configure `data/config.yaml`**

   ```yaml
   forums:
     - 913970503562178580   # Forum channel IDs to track
   tos_message: |
     Please review our Terms of Service in <#913970503562178580>, then click ✅ or ❌.
     This post will auto-close {timeout} if no action is taken.
   tos_decline_response: |
     You declined the Terms of Service. This thread is now closed.
   no_rep_messages:
     - "Damn, get your rep up! 📈"
     - "Zero rep? 🚨 Proceed with caution!"
     - … (add as many lines as you like)
   log_channel:                  # optional: channel ID for logging
   ```

4. **Run the bot**

   ```bash
   python bot.py
   ```

5. **Authorize & sync**

   * Make sure your OAuth2 invite URL includes `applications.commands` scope.
   * On first run, the bot auto-syncs slash commands. You can also use `!sync` in any text channel.

---

## 🧠 How It Works

1. **Thread Creation**

   * Listens to `on_thread_create`.
   * If `thread.parent_id` is in `forums`, the bot:

     * Marks thread as pending TOS.
     * Joins thread (if private) to allow messaging.
     * Sends a TOS prompt with a `{timeout}` countdown.

2. **Gating Messages**

   * `on_message` deletes any non-bot messages in threads pending TOS whose timestamp > prompt time.
   * Once OP clicks ✅ or ❌ (or timeouts), the pending flag is removed and gating stops.

3. **TOS View**

   * **Agree (✅)**

     * Cancels timeout, unblocks thread, deletes prompt, then calls `post_rep_ui()`.
   * **Decline (❌)**

     * Cancels timeout, unblocks thread, edits prompt to `tos_decline_response`, then archives & locks.

4. **Rep UI**

   * Presents OP’s rep star rating or a random “no rep” message.
   * Buyers click **+ Rep** / **– Rep**: stored per giver→receiver in SQLite.
   * Confirmation embeds sent to user & optionally to `log_channel`.

5. **Closing Posts**

   * **Close Post** button available after rep UI.
   * Only OP (with at least one rep) or admins can close.
   * Archives & locks thread.

6. **Slash Commands**

   * `/channel_set <forum>` – add a forum to `config.yaml`.
   * `/rep @user` – show user’s total 👍/👎 and stars.
   * `/repleaderboard` – top 10 by 👍 rep.
   * `/log set <channel>` – set rep log channel.

---

## ❓ FAQ

**Q: How do I add more “no rep” messages?**

* Edit `assets/rep_messages.txt`, one message per line.

**Q: Can I change the TOS timeout length?**

* In `on_thread_create`, adjust `timeout_secs = 30`.

**Q: Why aren’t slash commands showing?**

* Ensure the bot is invited with `applications.commands` scope and run `!sync`.

**Q: How do I remove a forum channel?**

* Manually edit `data/config.yaml`, remove the ID from `forums:`, then restart.

---

Made with ❤️ for safe, fun, and fair Discord marketplaces!
Feel free to file issues or contribute enhancements via pull requests.

```
