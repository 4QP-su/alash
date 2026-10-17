from flask import Blueprint, render_template, session, redirect, request, url_for
import json
import os
import urllib.parse

from app.models import (
 get_db, add_reward, get_user_profile, reset_user_progress,
 ban_user, get_system_setting, set_system_setting, log_activity,
)
from app.config import BASE_DIR

from .utils import login_required, current_user



admin_bp = Blueprint('admin', __name__)



_ADMIN_URL = '/internal/system/console/v2'



_TEXTS = {

 'ru': {

  'title':  'ПАНЕЛЬ_УПРАВЛЕНИЯ_СИСТЕМОЙ',

  'users_list': 'ИДЕНТИФИЦИРОВАННЫЕ_ПОЛЬЗОВАТЕЛИ',

  'stats':  'АНАЛИЗ_АКТИВНОСТИ_УРОВНЕЙ',

  'feed':  'ЖИВОЙ_ЛОГ_АТАК',

 },

 'kz': {

  'title':  'ЖҮЙЕНІ_БАСҚАРУ_ПАНЕЛІ',

  'users_list': 'АНЫҚТАЛҒАН_ПАЙДАЛАНУШЫЛАР',

  'stats':  'ДЕҢГЕЙЛЕРДІҢ_СТАТИСТИКАСЫ',

  'feed':  'ЖАНДЫ_ШАБУЫЛ_ТАСПАСЫ',

 },

 'en': {

  'title':  'SYSTEM_CONTROL_PANEL',

  'users_list': 'IDENTIFIED_USERS',

  'stats':  'LEVEL_ACTIVITY_ANALYSIS',

  'feed':  'LIVE_ATTACK_FEED',

 },

}





def _admin_check():

 user = current_user()

 if not user or not user['is_admin']:

  return None

 return user


def _level_file(category: str) -> str:
    return os.path.join(BASE_DIR, f'levels_{category}.json')


def _load_levels(category: str) -> dict:
    path = _level_file(category)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'ru': {}}


def _save_levels(category: str, payload: dict):
    path = _level_file(category)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


@admin_bp.route(_ADMIN_URL)

@login_required

def admin_panel():

 user = _admin_check()

 if not user:

  return "404 Not Found", 404



 lang = session.get('lang', 'ru')

 t = _TEXTS.get(lang, _TEXTS['en'])
 operator_filter = request.args.get('operator', type=str)
 category_filter = request.args.get('category', type=str)
 decode_payload = request.args.get('decode', '0') == '1'

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

 user_ip_counts = {
  row['user_id']: row['distinct_ips']
  for row in conn.execute(
   "SELECT user_id, COUNT(DISTINCT ip_address) as distinct_ips FROM attempts GROUP BY user_id"
  ).fetchall()
 }

 where_clauses = []
 params = []
 if operator_filter:
  where_clauses.append("u.username = ?")
  params.append(operator_filter)
 if category_filter:
  where_clauses.append("a.category = ?")
  params.append(category_filter.lower())

 query = "SELECT a.*, u.username FROM attempts a JOIN users u ON a.user_id = u.id"
 if where_clauses:
  query += " WHERE " + " AND ".join(where_clauses)
 query += " ORDER BY a.created_at DESC LIMIT 25"

 recent_attempts = [dict(row) for row in conn.execute(query, params).fetchall()]

 conn.close()

 for attempt in recent_attempts:
  payload = attempt.get('payload') or ''
  attempt['payload_decoded'] = urllib.parse.unquote_plus(payload)
  attempt['payload_view'] = attempt['payload_decoded'] if decode_payload else payload
  attempt['suspicious_ips'] = user_ip_counts.get(attempt['user_id'], 0) >= 3
  attempt['category_label'] = attempt['category'].upper() if attempt.get('category') else 'UNKNOWN'

 return render_template(

  'admin.html',

  users=users, stats=stats, recent_attempts=recent_attempts,

  t=t, curr_lang=lang,

  operator_filter=operator_filter,
  category_filter=category_filter,
  decode_payload=decode_payload,
 )





@admin_bp.route(_ADMIN_URL + '/levels')

@login_required

def admin_levels():
    user = _admin_check()
    if not user:
        return "404 Not Found", 404

    lang = session.get('lang', 'ru')
    t = _TEXTS.get(lang, _TEXTS['en'])
    category = request.args.get('category', 'sql').lower()
    if category not in ['sql', 'xss', 'csrf', 'path']:
        category = 'sql'

    levels = _load_levels(category)

    return render_template(
        'admin_levels.html',
        categories=['sql', 'xss', 'csrf', 'path'],
        selected_category=category,
        levels_json=json.dumps(levels, ensure_ascii=False, indent=2),
        t=t,
        curr_lang=lang,
    )


@admin_bp.route(_ADMIN_URL + '/levels', methods=['POST'])

@login_required

def admin_levels_save():
    user = _admin_check()
    if not user:
        return "404 Not Found", 404

    lang = session.get('lang', 'ru')
    t = _TEXTS.get(lang, _TEXTS['en'])
    category = request.form.get('category', 'sql').lower()
    if category not in ['sql', 'xss', 'csrf', 'path']:
        category = 'sql'

    levels_json = request.form.get('levels_json', '')
    error = None
    try:
        levels = json.loads(levels_json)
        _save_levels(category, levels)
    except ValueError:
        error = 'Invalid JSON payload. Please correct the syntax and resubmit.'

    return render_template(
        'admin_levels.html',
        categories=['sql', 'xss', 'csrf', 'path'],
        selected_category=category,
        levels_json=levels_json,
        error=error,
        t=t,
        curr_lang=lang,
    )


@admin_bp.route('/admin/ban/<int:user_id>', methods=['POST'])

@login_required

def admin_ban(user_id):

 user = _admin_check()

 if not user:

  return "404 Not Found", 404

 if user['id'] == user_id:

  return "Cannot ban yourself", 400

 log_activity(user['id'], 'ban_user', f'Banned user {user_id}', request.remote_addr, request.headers.get('User-Agent'))
 ban_user(user_id)
 return redirect(_ADMIN_URL)


@admin_bp.route(_ADMIN_URL + '/user/<int:user_id>')

@login_required

def admin_user_detail(user_id):
 user = _admin_check()
 if not user:
  return "404 Not Found", 404
 profile = get_user_profile(user_id)
 if not profile:
  return "404 Not Found", 404
 conn = get_db()
 recent_attempts = conn.execute(
  "SELECT a.*, u.username FROM attempts a JOIN users u ON a.user_id = u.id "
  "WHERE a.user_id = ? ORDER BY a.created_at DESC LIMIT 30",
  (user_id,),
 ).fetchall()
 activity_log = conn.execute(
  "SELECT action, details, ip_address, user_agent, created_at FROM activity_logs "
  "WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
  (user_id,),
 ).fetchall()
 conn.close()
 return render_template(
  'admin_user.html',
  profile=profile,
  recent_attempts=recent_attempts,
  activity_log=activity_log,
  t=_TEXTS.get(session.get('lang', 'ru'), _TEXTS['en']),
  curr_lang=session.get('lang', 'ru'),
 )


@admin_bp.route(_ADMIN_URL + '/user/<int:user_id>/reset', methods=['POST'])

@login_required

def admin_user_reset(user_id):
 admin = _admin_check()
 if not admin:
  return "404 Not Found", 404
 reset_user_progress(user_id)
 log_activity(admin['id'], 'reset_progress', f'Reset progress for user {user_id}', request.remote_addr, request.headers.get('User-Agent'))
 return redirect(url_for('admin.admin_user_detail', user_id=user_id))


@admin_bp.route('/admin/give_money/<int:user_id>', methods=['POST'])

@login_required

def admin_give_money(user_id):

 if not _admin_check():

  return "404 Not Found", 404

 add_reward(user_id, xp=0, balance=100)

 return redirect(_ADMIN_URL)

