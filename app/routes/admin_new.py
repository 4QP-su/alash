from flask import Blueprint, render_template, session, redirect, request, jsonify
from datetime import datetime
from app.models import (
    get_db, add_reward, get_all_users, reset_user_progress, ban_user, 
    get_user_profile, get_level_completion_stats, get_dropoff_analysis, 
    get_activity_by_date, create_announcement, get_active_announcements, 
    get_all_announcements, deactivate_announcement, get_setting, set_setting, 
    log_activity, get_activity_logs, get_user_by_id, get_rank
)
from .utils import login_required, current_user


admin_bp = Blueprint('admin', __name__)


_ADMIN_URL = '/internal/system/console/v2'


_TEXTS = {
 'ru': {
   'title':  'ПАНЕЛЬ_УПРАВЛЕНИЯ_СИСТЕМОЙ',
   'users_list': 'ИДЕНТИФИЦИРОВАННЫЕ_ПОЛЬЗОВАТЕЛИ',
   'stats':  'АНАЛИЗ_АКТИВНОСТИ_УРОВНЕЙ',
   'feed':  'ЖИВОЙ_ЛОГ_АТАК',
   'content': 'УПРАВЛЕНИЕ_КОНТЕНТОМ',
   'analytics': 'АНАЛИТИКА',
   'system': 'СИСТЕМНЫЕ_НАСТРОЙКИ',
 },
 'kz': {
   'title':  'ЖҮЙЕНІ_БАСҚАРУ_ПАНЕЛІ',
   'users_list': 'АНЫҚТАЛҒАН_ПАЙДАЛАНУШЫЛАР',
   'stats':  'ДЕҢГЕЙЛЕРДІҢ_СТАТИСТИКАСЫ',
   'feed':  'ЖАНДЫ_ШАБУЫЛ_ТАСПАСЫ',
   'content': 'МАЗМҰНДЫ_БАСҚАРУ',
   'analytics': 'АНАЛИТИКА',
   'system': 'ЖҮЙЕЛІК_ПАРАМЕТРЛЕР',
 },
 'en': {
   'title':  'SYSTEM_CONTROL_PANEL',
   'users_list': 'IDENTIFIED_USERS',
   'stats':  'LEVEL_ACTIVITY_ANALYSIS',
   'feed':  'LIVE_ATTACK_FEED',
   'content': 'CONTENT_MANAGEMENT',
   'analytics': 'ANALYTICS',
   'system': 'SYSTEM_SETTINGS',
 },
}


def _admin_check():
 user = current_user()
 if not user or not user['is_admin']:
  return None
 return user


@admin_bp.route(_ADMIN_URL)
@login_required
def admin_panel():
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 lang = session.get('lang', 'ru')
 t = _TEXTS.get(lang, _TEXTS['en'])
 conn = get_db()

 users = conn.execute(
  "SELECT id, username, email, xp, balance, created_at, last_login, is_admin "
  "FROM users ORDER BY xp DESC"
 ).fetchall()

 stats = conn.execute(
  """SELECT category, level_id,
     COUNT(*) as total_attempts,
     SUM(success) as successes,
     ROUND(100.0 * SUM(success) / COUNT(*), 1) as success_rate
   FROM attempts
   GROUP BY category, level_id
   ORDER BY category, level_id"""
 ).fetchall()

 recent_attempts = conn.execute(
  """SELECT a.*, u.username
   FROM attempts a JOIN users u ON a.user_id = u.id
   ORDER BY a.created_at DESC LIMIT 15"""
 ).fetchall()

 announcements = conn.execute(
  "SELECT * FROM announcements WHERE is_active = 1 ORDER BY created_at DESC LIMIT 5"
 ).fetchall()

 conn.close()

 return render_template(
  'admin.html',
  users=users, stats=stats, recent_attempts=recent_attempts,
  announcements=announcements, t=t, curr_lang=lang,
 )


# ────────────────────────────────────────────────────────────────────
# Users Management
# ────────────────────────────────────────────────────────────────────

@admin_bp.route('/admin/users/list')
@login_required
def admin_users_list():
 """List all users with full details."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 users = get_all_users(sort_by='xp')
 for u in users:
  u['rank'] = get_rank(u['xp'])

 return jsonify([dict(u) for u in users])


@admin_bp.route('/admin/users/<int:user_id>/profile')
@login_required
def admin_user_profile(user_id):
 """Get full user profile."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 profile = get_user_profile(user_id)
 if not profile:
  return "User not found", 404

 return jsonify(profile)


@admin_bp.route('/admin/users/<int:user_id>/reset-progress', methods=['POST'])
@login_required
def admin_reset_progress(user_id):
 """Reset user progress."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 if user['id'] == user_id:
  return jsonify({'error': 'Cannot reset your own progress'}), 400

 reset_user_progress(user_id)
 log_activity(user['id'], 'RESET_USER_PROGRESS', f'Reset progress for user {user_id}')
 return jsonify({'ok': True, 'message': 'Progress reset'})


@admin_bp.route('/admin/users/<int:user_id>/ban', methods=['POST'])
@login_required
def admin_ban_user(user_id):
 """Ban a user."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 if user['id'] == user_id:
  return jsonify({'error': 'Cannot ban yourself'}), 400

 ban_user(user_id)
 log_activity(user['id'], 'BAN_USER', f'Banned user {user_id}')
 return jsonify({'ok': True, 'message': 'User banned'})


@admin_bp.route('/admin/users/<int:user_id>/reward', methods=['POST'])
@login_required
def admin_give_reward(user_id):
 """Give XP and balance reward to user."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 data = request.get_json()
 xp = int(data.get('xp', 0))
 balance = int(data.get('balance', 0))

 add_reward(user_id, xp, balance)
 log_activity(user['id'], 'GIVE_REWARD', f'Gave {xp}XP and {balance}balance to user {user_id}')
 return jsonify({'ok': True, 'message': 'Reward given'})


# ────────────────────────────────────────────────────────────────────
# Analytics
# ────────────────────────────────────────────────────────────────────

@admin_bp.route('/admin/analytics/completion')
@login_required
def admin_analytics_completion():
 """Get level completion statistics."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 stats = get_level_completion_stats()
 return jsonify(stats)


@admin_bp.route('/admin/analytics/dropoff')
@login_required
def admin_analytics_dropoff():
 """Get dropoff analysis (where users get stuck)."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 dropoff = get_dropoff_analysis()
 return jsonify(dropoff)


@admin_bp.route('/admin/analytics/activity')
@login_required
def admin_analytics_activity():
 """Get activity by date."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 days = request.args.get('days', 30, type=int)
 activity = get_activity_by_date(days)
 return jsonify(activity)


# ────────────────────────────────────────────────────────────────────
# Announcements (System Messages)
# ────────────────────────────────────────────────────────────────────

@admin_bp.route('/admin/announcements/create', methods=['POST'])
@login_required
def admin_create_announcement():
 """Create a new announcement."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 data = request.get_json()
 title = data.get('title', '').strip()
 message = data.get('message', '').strip()
 expires_at = data.get('expires_at')

 if not title or not message:
  return jsonify({'error': 'Title and message are required'}), 400

 create_announcement(title, message, user['id'], expires_at)
 log_activity(user['id'], 'CREATE_ANNOUNCEMENT', f'Created announcement: {title}')
 return jsonify({'ok': True, 'message': 'Announcement created'})


@admin_bp.route('/admin/announcements/all')
@login_required
def admin_get_announcements():
 """Get all announcements."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 announcements = get_all_announcements()
 return jsonify([dict(a) for a in announcements])


@admin_bp.route('/admin/announcements/<int:announcement_id>/deactivate', methods=['POST'])
@login_required
def admin_deactivate_announcement(announcement_id):
 """Deactivate an announcement."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 deactivate_announcement(announcement_id)
 log_activity(user['id'], 'DEACTIVATE_ANNOUNCEMENT', f'Deactivated announcement {announcement_id}')
 return jsonify({'ok': True, 'message': 'Announcement deactivated'})


# ────────────────────────────────────────────────────────────────────
# System Settings
# ────────────────────────────────────────────────────────────────────

@admin_bp.route('/admin/settings/get/<key>')
@login_required
def admin_get_setting(key):
 """Get a system setting."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 value = get_setting(key)
 return jsonify({'key': key, 'value': value})


@admin_bp.route('/admin/settings/set', methods=['POST'])
@login_required
def admin_set_setting():
 """Set a system setting."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 data = request.get_json()
 key = data.get('key', '').strip()
 value = data.get('value')

 if not key:
  return jsonify({'error': 'Key is required'}), 400

 set_setting(key, value)
 log_activity(user['id'], 'SET_SETTING', f'Set {key} = {value}')
 return jsonify({'ok': True, 'message': 'Setting updated'})


# ────────────────────────────────────────────────────────────────────
# Activity Logs
# ────────────────────────────────────────────────────────────────────

@admin_bp.route('/admin/logs/activity')
@login_required
def admin_get_logs():
 """Get activity logs."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 limit = request.args.get('limit', 100, type=int)
 logs = get_activity_logs(limit)
 return jsonify([dict(l) for l in logs])


# ────────────────────────────────────────────────────────────────────
# Legacy Routes (backward compatibility)
# ────────────────────────────────────────────────────────────────────

@admin_bp.route('/admin/ban/<int:user_id>', methods=['POST'])
@login_required
def admin_ban(user_id):
 """Legacy ban endpoint."""
 user = _admin_check()
 if not user:
  return "404 Not Found", 404

 if user['id'] == user_id:
  return "Cannot ban yourself", 400

 ban_user(user_id)
 log_activity(user['id'], 'BAN_USER', f'Banned user {user_id}')
 return redirect(_ADMIN_URL)


@admin_bp.route('/admin/give_money/<int:user_id>', methods=['POST'])
@login_required
def admin_give_money(user_id):
 """Legacy give money endpoint."""
 if not _admin_check():
  return "404 Not Found", 404

 add_reward(user_id, xp=0, balance=100)
 return redirect(_ADMIN_URL)
