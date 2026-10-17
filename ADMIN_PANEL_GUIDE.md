# Admin Panel Enhancement - Complete Guide

## Overview

Enhanced admin panel for HackLab platform with 4 major management sections:

### 1. **Users Management** 👥
- **List all users** with XP, balance, registration date, last login
- **View full user profiles** including progress, statistics, and activity
- **Reset user progress** - Clear all completed levels and XP (but retain account)
- **Ban users** - Remove user account (irreversible)
- **Give rewards** - Award XP and balance to users

### 2. **Analytics** 📊
- **Level completion statistics** - See how many users completed each level
- **Dropoff analysis** - Identify where users get stuck/abandon levels (sorted by lowest success rate)
- **Activity by date** - Track new user registrations and completed tasks over time (7/30/90 days)
- **Success rates** - Visual breakdown of attempt success rates per level

### 3. **Announcements** 📢
- **Create global announcements** - Show banner messages to all logged-in users
- **Set expiration dates** - Auto-deactivate old announcements
- **Manage active announcements** - View, edit, deactivate messages
- **Track creation** - See who created each announcement and when

### 4. **System Settings** ⚙️
- **XP rewards** - Customize XP given for level completion
- **Balance rewards** - Customize balance currency for level completion
- **Hint pricing** - Set cost of hints in balance currency
- **Daily bonuses** - Configure login bonus amounts
- **Key-value configuration** - Store arbitrary system settings

### 5. **Activity Logs** 📋
- **Admin action tracking** - See all admin operations (bans, resets, rewards)
- **System events** - Track important system activities
- **Audit trail** - Who did what, when, and details
- **Suspicious activity monitoring** - Monitor user behavior patterns

---

## Installation & Setup

### Step 1: Run Migration Script

```bash
cd d:\hckr-tr
python migration_admin_panel.py
```

This script will:
- ✓ Backup original files
- ✓ Update `app/models.py` to call `_ensure_admin_tables()`
- ✓ Replace `app/routes/admin.py` with enhanced version
- ✓ Replace `templates/admin.html` with new dashboard
- ✓ Create admin tables in database
- ✓ Clean up temporary files

### Step 2: Start Application

```bash
python run.py
```

On first run, the app will automatically create the new admin tables.

### Step 3: Access Admin Panel

Navigate to: `/internal/system/console/v2`

(Must be logged in as admin user)

---

## New Database Tables

### `announcements`
```sql
id                -- Primary key
title             -- Announcement title
message           -- Full message text
is_active         -- 1 = visible, 0 = hidden
created_by        -- Admin user ID
created_at        -- Creation timestamp
expires_at        -- Optional expiration time
```

### `system_settings`
```sql
key               -- Setting name (e.g., 'xp_reward_per_level')
value             -- Setting value
updated_at        -- Last update timestamp
```

### `activity_logs`
```sql
id                -- Primary key
user_id           -- Admin who performed action
action            -- Action type (e.g., 'BAN_USER', 'RESET_PROGRESS')
details           -- Additional info
ip_address        -- IP address of admin
user_agent        -- Browser info
created_at        -- Timestamp
```

---

## API Endpoints Reference

### Users Management
- `GET /admin/users/list` - List all users with stats
- `GET /admin/users/<id>/profile` - Get user profile & progress
- `POST /admin/users/<id>/reset-progress` - Reset user progress
- `POST /admin/users/<id>/ban` - Ban user
- `POST /admin/users/<id>/reward` - Give reward (JSON: {xp, balance})

### Analytics
- `GET /admin/analytics/completion` - Level completion stats
- `GET /admin/analytics/dropoff` - Where users get stuck
- `GET /admin/analytics/activity?days=30` - Daily activity trends

### Announcements
- `POST /admin/announcements/create` - Create announcement (JSON: {title, message, expires_at})
- `GET /admin/announcements/all` - Get all announcements
- `POST /admin/announcements/<id>/deactivate` - Hide announcement

### Settings
- `GET /admin/settings/get/<key>` - Get setting value
- `POST /admin/settings/set` - Set value (JSON: {key, value})

### Logs
- `GET /admin/logs/activity?limit=100` - Get activity logs

---

## New Functions in `app/models.py`

### User Management
```python
get_all_users(sort_by='xp', limit=None)      # List users
reset_user_progress(user_id)                  # Clear progress
ban_user(user_id)                             # Delete user
get_user_profile(user_id)                     # Full profile
```

### Analytics
```python
get_level_completion_stats()                  # Completion rates
get_dropoff_analysis()                        # Where users struggle
get_activity_by_date(days=30)                 # Activity trends
```

### Announcements
```python
create_announcement(title, message, created_by, expires_at=None)
get_active_announcements()
get_all_announcements()
deactivate_announcement(announcement_id)
```

### Settings
```python
get_setting(key, default=None)                # Retrieve setting
set_setting(key, value)                       # Store setting
```

### Logging
```python
log_activity(user_id, action, details=None, ip_address=None, user_agent=None)
get_activity_logs(limit=100)
```

---

## Admin Panel UI Features

### Multi-Tab Interface
- **Users Tab**: User list, profiles, rewards, reset, ban
- **Analytics Tab**: Completion stats, dropoff analysis, activity trends
- **Announcements Tab**: Create/manage announcements
- **Settings Tab**: Configure system parameters
- **Logs Tab**: View admin activity trail

### Design Highlights
- Cyber-themed UI with neon green/blue styling
- Responsive table displays
- Modal dialogs for detailed views
- Form inputs for bulk operations
- Real-time data loading via AJAX
- Confirmation dialogs for dangerous operations

---

## Security Considerations

✓ **Admin-only access** - All endpoints check `is_admin` flag
✓ **Audit logging** - All actions logged with admin ID and timestamp
✓ **Irreversible actions** - Ban cannot be undone (backup DB before destructive ops)
✓ **Self-protection** - Cannot ban/reset own account
✓ **Input validation** - All user inputs validated/sanitized
✓ **CSRF protection** - Forms use Flask's CSRF tokens (if configured)

---

## Troubleshooting

**Problem**: Admin endpoints return 404
- **Solution**: Ensure user has `is_admin = 1` in database
  ```sql
  UPDATE users SET is_admin = 1 WHERE username = 'admin_username';
  ```

**Problem**: Empty tables or "Loading..." stuck
- **Solution**: Check browser console for JS errors
- Clear browser cache and reload

**Problem**: Cannot find new tables after migration
- **Solution**: Delete `users.db` and restart app to reinit all tables
  ```bash
  rm data/users.db
  python run.py
  ```

---

## File Changes Summary

### Modified Files
- `app/models.py` - Added 20+ new functions for admin operations
- `app/routes/admin.py` - Complete rewrite with 15+ endpoints
- `templates/admin.html` - Replaced with comprehensive dashboard

### New/Temporary Files (auto-cleaned)
- `migration_admin_panel.py` - Main migration script
- `app/routes/admin_new.py` - Temp file (merged into admin.py)
- `templates/admin_enhanced.html` - Temp file (merged into admin.html)

### Backup Files Created
- `app/routes/admin.py.bak.*` - Original admin routes
- `templates/admin.html.bak.*` - Original admin template
- `app/models.py.bak.*` - Original models (if modified)

---

## Next Steps

1. ✓ Run migration script
2. ✓ Start application
3. ✓ Log in as admin user
4. ✓ Access `/internal/system/console/v2`
5. ✓ Test each section:
   - View users, reset/ban test account
   - Check analytics for level completion
   - Create test announcement
   - Modify a system setting
   - Review activity logs

---

## Version History

- **v1.0** (2026-05-24)
  - Complete admin panel enhancement
  - 4 major sections: Users, Analytics, Announcements, Settings
  - Activity logging
  - Full API endpoints

---

For questions or issues, review the admin.py routes or models.py for documentation.
