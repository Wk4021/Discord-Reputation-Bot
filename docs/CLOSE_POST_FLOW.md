# How Posts Are Closed

Closing a post locks the thread, posts the closing message, archives the thread, records it in the database and updates the post's log embed. The thread is locked first, so the closing message only appears if closing actually worked; if the bot lacks **Manage Threads**, the person who clicked gets a private error instead.

A post counts as closed when it is **locked**. Discord also archives quiet posts by itself; those stay usable. If a moderator unlocks a closed post, its buttons work again.

The review, close and keep-open buttons in a closed post reply "🔒 This post is closed." and do nothing else.

## Close Post button

```
Clicked by…
├── someone else                → "Only the thread creator or admins can close this post."
├── an admin (not the owner)
│   ├── admin_close_confirmation: true  → type "Yes" to confirm → closed
│   └── admin_close_confirmation: false → closed immediately
└── the post owner
    ├── post has reviews        → closed immediately
    └── post has no reviews     → type "Yes" to confirm → closed
```

The confirmation accepts "Yes" in any capitalisation; anything else cancels.

| Who closed it | Message in the thread | Log status |
|---------------|-----------------------|------------|
| Owner, with reviews | 🔒 This thread is now closed by its creator. | ❌ Closed |
| Owner, no reviews | 🔒 This thread is now closed by its creator (no reviews received). | ❌ Closed without reviews |
| Admin | 🔒 This thread has been closed by admin @Name. | ❌ Force closed by admin @Name |

## Automatic closing

### After the first review
When a post receives its first review (and `auto_close_enabled` is on), the bot schedules it to close after `auto_close_hours` and posts a notice with a countdown. The owner can click **I have multiple items - Keep thread open** to cancel. A cancelled post is never rescheduled.

The bot checks for due posts every 10 minutes, so a post can close up to 10 minutes after its timer ends. Posts that Discord has already archived are still closed and locked.

### TOS not answered
If the owner doesn't answer the TOS prompt within `tos_timeout_seconds` (default 30), the post is closed. Declining the TOS closes it straight away. Both survive restarts: a prompt that expired while the bot was offline is handled as soon as it comes back.
