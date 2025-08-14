# Review System Migration Guide

## Overview

The bot has been upgraded from a simple +/- rep system to a comprehensive **star rating review system** with the following new features:

### ✨ New Features

1. **Star Rating (1-10)**: Users can now rate from 1-10 instead of just +/-
2. **Review Notes**: Optional text reviews to provide detailed feedback
3. **Review Modal**: Clean popup interface for submitting reviews
4. **Average Rating Display**: Shows average rating with star visualization
5. **Latest Reviews**: Display of the 3 most recent reviews with notes
6. **Enhanced Commands**: New `/reviews` and `/leaderboard` commands

---

## Database Changes

### New Table: `reviews`
```sql
CREATE TABLE reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    giver_id    INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    thread_id   INTEGER NOT NULL,
    rating      INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 10),
    notes       TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(giver_id, receiver_id, thread_id)
)
```

### Backward Compatibility
- Old `rep` and `rep_totals` tables are preserved but deprecated
- Existing data remains intact but new reviews use the new system

---

## UI Changes

### Button Changes
- **Before**: "✅ + Rep" and "❌ - Rep" buttons
- **After**: "⭐ Leave a Review" button that opens a modal

### Review Modal
- **Rating Field**: Enter number 1-10
- **Notes Field**: Optional detailed review (500 char limit)

### Display Changes
- **Star Rating**: Shows 1-5 stars based on average (e.g., ⭐⭐⭐✨☆ 7.5/10)
- **Latest Reviews**: Shows up to 3 recent reviews with ratings and notes
- **Better Visualization**: Star emojis instead of just numbers

---

## Command Changes

### Updated Commands

| Old Command | New Command | Description |
|-------------|-------------|-------------|
| `/rep @user` | `/reviews @user` | View user's reviews and rating |
| `/repleaderboard` | `/leaderboard` | Top rated users |
| `/log #channel` | `/log #channel` | Set review log channel |

### New Review Display
```
⭐ Reviews for UserName
Rating: ⭐⭐⭐⭐☆ (8.2/10 from 5 reviews)

Average Rating: 8.2/10
Total Reviews: 5

Latest Reviews:
⭐⭐⭐⭐⭐ 10/10 by @Reviewer1
> Excellent service, very professional!

⭐⭐⭐⭐ 8/10 by @Reviewer2
> Good communication, delivered on time.

⭐⭐⭐✨ 7/10 by @Reviewer3
> Decent work, could be better.
```

---

## Key Functions

### Database Functions (utils/db.py)
- `add_review(giver_id, receiver_id, thread_id, rating, notes)` - Add new review
- `get_user_reviews(user_id)` - Get avg rating, total, and latest 3 reviews
- `get_top_rated_users(limit)` - Get leaderboard by rating
- `has_user_reviewed(giver_id, receiver_id, thread_id)` - Check if already reviewed

### UI Functions (cogs/rep.py)
- `ReviewModal` - Modal popup for collecting ratings and notes
- `ReviewButtonView` - New button interface with review button
- `post_review_ui()` - Display review interface with stars and recent reviews
- `generate_star_rating()` - Convert numeric rating to star display

---

## Migration Notes

### For Users
- **No action required** - existing data is preserved
- Start using the new "⭐ Leave a Review" button
- Can provide detailed feedback with notes
- View others' detailed reviews with `/reviews @user`

### For Admins
- Run the bot - database will auto-upgrade with new tables
- Old rep data remains accessible but new reviews are preferred
- Update any documentation referencing old commands
- Consider informing users about the new review system

---

## Configuration

No configuration changes required. The system uses the existing:
- `log_channel` - Where review logs are sent
- `forums` - Which forums to track
- `tos_message` - Same TOS acceptance flow

---

## Example Usage Flow

1. **User creates thread** → TOS acceptance required
2. **After TOS accepted** → Review UI appears with star rating display
3. **Other users click "⭐ Leave a Review"** → Modal popup appears
4. **User fills rating (1-10) and optional notes** → Review saved
5. **UI updates** → Shows new average rating and latest reviews
6. **Commands available** → `/reviews @user` and `/leaderboard`

The new system provides much richer feedback while maintaining the same ease of use!