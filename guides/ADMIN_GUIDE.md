# Admin System Guide

## Overview

The bot now includes an admin system that allows designated users to have additional privileges, particularly for moderating posts.

## Admin Configuration

### Config File Setup

Admins are configured in `data/config.yaml`:

```yaml
admin_ids:
- 123456789012345678  # Replace with actual admin user IDs
- 987654321098765432  # Add more admin IDs as needed
```

### Getting User IDs

To get a user's Discord ID:
1. Enable Developer Mode in Discord (User Settings → Advanced → Developer Mode)
2. Right-click the user → Copy User ID
3. Add the ID to the `admin_ids` list in config.yaml

## Admin Privileges

### Force Close Posts

**Normal Users**: Can only close their own posts after receiving at least one review
**Admins**: Can force close ANY post without review requirements

When an admin closes a post:
- Message: "🔒 This thread has been closed by admin @AdminName."
- Log: "❌ Force closed by admin @AdminName at [timestamp]"

### Admin Management Commands

| Command | Description | Permission |
|---------|-------------|------------|
| `/admin_add @user` | Add a user as admin | Admin only |
| `/admin_remove @user` | Remove admin privileges | Admin only |
| `/admin_list` | View all admins | Admin only |

## Admin Command Examples

### Adding an Admin
```
/admin_add @NewAdmin
```
Response: "✅ @NewAdmin has been added as an admin."

### Removing an Admin
```
/admin_remove @FormerAdmin
```
Response: "✅ @FormerAdmin has been removed from admin."

### Listing Admins
```
/admin_list
```
Shows all current admins with their display names.

## Safety Features

- **Self-Protection**: Cannot remove yourself as admin if you're the last admin
- **Admin-Only**: Only existing admins can add/remove other admins
- **Duplicate Prevention**: Cannot add someone who's already an admin
- **Graceful Handling**: Shows friendly error messages for invalid operations

## Usage Examples

### Normal Post Closure (by OP)
- User clicks "Close Post" 
- System checks: Is this the thread owner? ✓
- System checks: Does thread have reviews? ✓
- Result: Post closes normally

### Admin Force Closure
- Admin clicks "Close Post" on any thread
- System checks: Is this an admin? ✓
- System skips: Review requirement check (admin override)
- Result: Post closes immediately with admin attribution

## Configuration Tips

1. **Start Small**: Begin with 1-2 trusted admins
2. **Document IDs**: Keep a record of who each ID belongs to
3. **Regular Review**: Periodically review the admin list with `/admin_list`
4. **Backup Config**: Keep backups of your config.yaml file

## Security Notes

- Admin privileges are powerful - choose admins carefully
- IDs in config are persistent until manually removed
- Bot restart not required when updating admin list via commands
- Config file changes require bot restart to take effect