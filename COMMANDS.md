# 📋 Discord Reputation Bot V3.1 - Command Reference

Complete documentation for all slash commands and interactive features in Discord Reputation Bot V3.1.

---

## 🆕 **New in V3.1**

### **Interactive Settings Management**
- **`/settings`**: Comprehensive dashboard with buttons and modal forms
- **Auto-Close Controls**: Toggle and configure automatic thread closure
- **User Notifications**: Mentions when users receive reviews
- **Enhanced Logging**: All actions logged to console and Discord

---

## 📊 **Public Commands**

### `/reviews <user>`
**Description**: View a user's review statistics and recent reviews  
**Usage**: `/reviews @username`  
**Permissions**: Everyone  
**Example Output**:
```
⭐ Reviews for Username
Rating: ⭐⭐⭐⭐✨ (8.5/10 from 12 reviews)

📝 Latest Reviews
⭐⭐⭐⭐⭐ 10/10 by @reviewer1
> Excellent seller, fast delivery!

⭐⭐⭐⭐☆ 8/10 by @reviewer2  
> Good communication, item as described
```

### `/leaderboard`
**Description**: Show the top 10 highest rated users  
**Usage**: `/leaderboard`  
**Permissions**: Everyone  
**Example Output**:
```
🏆 Top Rated Users

1. Username1 - ⭐⭐⭐⭐⭐ 9.8/10 (25 reviews)
2. Username2 - ⭐⭐⭐⭐✨ 9.2/10 (18 reviews)
3. Username3 - ⭐⭐⭐⭐☆ 8.9/10 (31 reviews)
...
```

---

## 👑 **Admin Commands**

### `/settings` *(NEW in V3.1)*
**Description**: Interactive settings dashboard with buttons and forms  
**Usage**: `/settings`  
**Permissions**: Admin only (user ID or role ID)  
**Features**:
- **🔧 Auto-Close Settings**: Enable/disable and set timer
- **📋 TOS Settings**: Edit TOS message and decline response
- **👑 Admin Settings**: View current admins (read-only)
- **🌐 Server Settings**: Configure server name and invite link
- **🔄 Refresh**: Update display with current values

**Dashboard Display**:
```
⚙️ Bot Settings Dashboard

🔧 Auto-Close Settings    📁 Forum Channels    📝 Log Channel
Status: ✅ Enabled        Tracking: 3 forums   Channel: #logs
Timer: 24 hours

👑 Admin Settings         🌐 Server Info       📋 TOS Settings
Users: 2                  Name: My Server      Message: Configured
Roles: 1                                       Decline: Configured
```

### `/auto_close_toggle [enabled]` *(NEW in V3.1)*
**Description**: Toggle auto-close feature on/off or view current status  
**Usage**: 
- `/auto_close_toggle` - Show current status
- `/auto_close_toggle true` - Enable auto-close
- `/auto_close_toggle false` - Disable auto-close
**Permissions**: Admin only  
**Example Output**:
```
⚙️ Auto-Close Setting Updated
Auto-close feature is now ✅ Enabled

Timer: Threads will auto-close 24 hours after first review
```

### `/auto_close_hours <hours>` *(NEW in V3.1)*
**Description**: Set the number of hours before auto-close (1-168 hours)  
**Usage**: `/auto_close_hours 48`  
**Permissions**: Admin only  
**Validation**: Hours must be between 1 and 168 (1 week maximum)  
**Example Output**:
```
⏰ Auto-Close Timer Updated
Auto-close timer set to 48 hours

Previous: 24 hours → New: 48 hours
Note: This only affects new auto-close schedules.
```

### `/send_review_ui` *(NEW in V3.1)*
**Description**: Manually send the review interface to current thread  
**Usage**: `/send_review_ui` (must be used in a thread)  
**Permissions**: Admin only  
**Use Case**: When review interface needs to be re-sent or manually triggered  
**Example**: Useful if the automatic interface was deleted or didn't appear

### `/channel_set <channel>`
**Description**: Add a forum channel for reputation tracking  
**Usage**: `/channel_set #marketplace-forum`  
**Permissions**: Admin only  
**Effect**: Bot will monitor new threads in this forum and apply TOS gating + review system

### `/log <channel>`
**Description**: Set the channel where review logs and admin actions are sent  
**Usage**: `/log #mod-logs`  
**Permissions**: Admin only  
**Effect**: All reviews, auto-close events, and admin actions will be logged here

### `/admin_add <user>`
**Description**: Add a user as admin  
**Usage**: `/admin_add @username`  
**Permissions**: Admin only  
**Effect**: User can use all admin commands and modify settings

### `/admin_remove <user>`
**Description**: Remove admin privileges from a user  
**Usage**: `/admin_remove @username`  
**Permissions**: Admin only  
**Safety**: Cannot remove yourself if you're the last admin

### `/admin_list`
**Description**: View all current admins (users and roles)  
**Usage**: `/admin_list`  
**Permissions**: Admin only  
**Example Output**:
```
👑 Admin List

Admin Users (2)
• @Admin1 (Administrator)
• @Admin2 (Owner)

Admin Roles (1)  
• @Staff (Staff Role)
```

### `/admin_role_add <role>` *(NEW in V3.1)*
**Description**: Add a role that grants admin permissions  
**Usage**: `/admin_role_add @Staff`  
**Permissions**: Admin only  
**Effect**: All users with this role can use admin commands

### `/admin_role_remove <role>` *(NEW in V3.1)*
**Description**: Remove admin permissions from a role  
**Usage**: `/admin_role_remove @Staff`  
**Permissions**: Admin only  
**Effect**: Users with this role lose admin access (unless they have individual admin status)

---

## 🎮 **Interactive Elements**

### **Review Interface**
**Triggers**: Appears after TOS acceptance or via `/send_review_ui`  
**Buttons**:
- **⭐ Leave a Review**: Opens rating modal (1-10 + optional notes)
- **Close Post**: Thread owner or admin can close the post

### **Review Modal** *(Enhanced in V3.1)*
**Fields**:
- **Rating (1-10)**: Required number input with validation
- **Review Notes**: Optional text area (500 character limit)
**Actions After Submission**:
1. **User gets mentioned**: "@user You received a **8/10** review!"
2. **First review triggers auto-close**: Warning embed with cancel button appears
3. **Review logged**: Sent to log channel with full details
4. **UI refreshes**: Updated rating display with new review

### **Auto-Close Warning** *(NEW in V3.1)*
**Trigger**: Appears after first review in a thread (if enabled)  
**Display**:
```
⏰ Auto-Close Scheduled
This thread will automatically close in 24 hours unless you cancel it below.

Why?
Threads auto-close after the first review to keep the marketplace clean. 
If you have multiple items in this listing, click the button below.

[I have multiple items - Keep thread open]
```
**Button**: Only thread owner can cancel auto-close

---

## 🔧 **Settings Interface Details**

### **Auto-Close Settings Modal**
**Fields**:
- **Enable Auto-Close**: `true` or `false`
- **Auto-Close Hours**: Number between 1-168
**Validation**: Prevents invalid inputs with error messages

### **TOS Settings Modal**
**Fields**:
- **TOS Message**: Multi-line text (1000 char limit) with `{timeout}` placeholder
- **TOS Decline Response**: Multi-line text (500 char limit)
**Pre-filled**: Shows current configuration values

### **Server Settings Modal**  
**Fields**:
- **Server Display Name**: Text shown on web dashboard (100 char limit)
- **Server Invite Link**: Optional Discord invite URL (200 char limit)
**Usage**: Enhances web dashboard branding and functionality

---

## 📝 **Logging & Notifications**

### **Console Logging**
All major actions are logged to console with timestamps:
```
[AUTO-CLOSE] Admin1 enabled auto-close feature
[AUTO-CLOSE] Scheduled thread 123456789 (Selling iPhone) to close in 24 hours
[AUTO-CLOSE] User123 cancelled auto-close for thread 123456789
[AUTO-CLOSE] Successfully closed thread 123456789 (Selling iPhone)
[SETTINGS] Admin1 accessed settings dashboard
```

### **Discord Log Channel**
Comprehensive embeds sent to configured log channel:
- **Review submissions** with rating and user info
- **Auto-close scheduling** with thread details and countdown
- **Auto-close cancellations** with user and reason
- **Auto-close executions** with thread info and action taken
- **Settings changes** with before/after values
- **Admin actions** with user and action details

### **User Notifications** *(NEW in V3.1)*
Thread owners are mentioned when they receive reviews:
```
@ThreadOwner You received a **9/10** review!
```
This appears alongside the auto-close warning (if applicable) or as a standalone message.

---

## ⚡ **Quick Reference**

### **Most Used Commands**
- `/settings` - One-stop shop for all configuration
- `/reviews @user` - Check someone's reputation
- `/leaderboard` - See top-rated users
- `/auto_close_toggle` - Quick enable/disable auto-close

### **Setup Commands** (One-time)
- `/channel_set #forum` - Add forum for tracking
- `/log #logs` - Set log channel
- `/admin_add @user` - Add initial admins

### **Maintenance Commands**
- `!sync` - Register slash commands (owner only)
- `/send_review_ui` - Manually trigger review interface

---

## 🔍 **Troubleshooting Commands**

**Commands not appearing?**
- Use `!sync` and wait up to 1 hour

**Auto-close not working?**
- Check `/settings` → Auto-Close Settings
- Use `/auto_close_toggle true` to enable

**User can't access admin commands?**
- Add with `/admin_add @user` or `/admin_role_add @role`
- Verify in `/admin_list`

**Settings interface not responding?**
- Ensure user has admin permissions
- Check for JavaScript errors in browser console (web dashboard)

---

## 🎯 **Best Practices**

1. **Use `/settings`** for most configuration changes - it's user-friendly and validates input
2. **Set up logging early** with `/log #channel` to track all bot activity
3. **Configure auto-close** based on your community needs (24 hours is good default)
4. **Add role-based admins** with `/admin_role_add` for easier permission management
5. **Check `/admin_list`** regularly to maintain proper admin access
6. **Use `/leaderboard`** to showcase top community members
7. **Monitor log channel** for any issues or unusual activity

---

*This documentation covers Discord Reputation Bot V3.1. For setup guides and additional information, see the main README.md and guides/ folder.*