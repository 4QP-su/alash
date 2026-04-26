import re
from flask import Blueprint, render_template, request, session, redirect, url_for
from app.models import (
 is_completed, is_unlocked, mark_completed,
 has_hint, log_attempt, add_reward,
 mark_theory_passed, has_passed_theory,
)
from app.config import load_levels
from .utils import login_required, current_user, get_db_for_level

sql_bp = Blueprint('sql', __name__)


def _get_levels():
 return load_levels('levels_sql.json', session.get('lang', 'ru'))


@sql_bp.route('/sql-injection/theory')
def sql_theory():
 show_quiz = request.args.get('quiz') == '1'
 return render_template('sql_theory.html', show_quiz=show_quiz)


@sql_bp.route('/verify-theory/sql', methods=['POST'])
@login_required
def verify_sql_theory():
 wrong = [str(i) for i in range(1, 7) if request.form.get(f'q{i}') != 'corr']
 if not wrong:
  user = current_user()
  mark_theory_passed(user['id'], 'sql')
  return redirect(url_for('sql.sql_labs'))
 
 # Quiz hints for wrong answers
 from app.config import t_for_lang
 t = t_for_lang(session.get('lang', 'ru'))
 quiz_hints = t.get('quiz_hints', {}).get('sql', {})
 
 lang = session.get('lang', 'ru')
 from app.config import t_for_lang
 err = t_for_lang(lang).get('theory_quiz_error', 'ACCESS_DENIED')
 
 # Build detailed error message with hints
 hint_messages = []
 for q_num in wrong:
  if q_num in quiz_hints:
   hint_messages.append(f"Q{q_num}: {quiz_hints[q_num]}")
 
 wrong_questions_text = t.get('wrong_questions', 'Wrong questions')
 details = {
  'ru': f"{err} {wrong_questions_text}: {', '.join(wrong)}.\n\n" + "\n".join(hint_messages) + "\n\nПересмотри теорию и попробуй снова.",
  'kz': f"{err} {wrong_questions_text}: {', '.join(wrong)}.\n\n" + "\n".join(hint_messages) + "\n\nТеорияны қайта қарап, тағы байқап көр.",
 }
 err_msg = details.get(lang, f"{err} {wrong_questions_text}: {', '.join(wrong)}.\n\n" + "\n".join(hint_messages) + "\n\nReview theory and try again.")
 return render_template('sql_theory.html', error=err_msg, show_quiz=True)


@sql_bp.route('/sql-injection')
@login_required
def sql_labs():
 levels = _get_levels()
 user = current_user()
 uid = user['id']
 for lvl in levels.values():
  lid    = lvl['id']
  lvl['completed'] = is_completed(uid, 'sql', lid)
  lvl['unlocked'] = lid == 1 or is_unlocked(uid, 'sql', lid)
 return render_template('sql_levels.html', levels=levels.values())


@sql_bp.route('/sql-injection/<int:level_id>', methods=['GET', 'POST'])
@login_required
def sql_level(level_id):
 user = current_user()
 uid = user['id']
 if not has_passed_theory(uid, 'sql'):
  return redirect(url_for('sql.sql_theory'))

 levels  = _get_levels()
 level_data = levels.get(level_id)
 if not level_data:
  return redirect(url_for('sql.sql_labs'))

 user = current_user()
 uid = user['id']

 if not is_unlocked(uid, 'sql', level_id):
  return render_template('access_denied.html', level_id=level_id)

 is_won    = False
 is_already_done = is_completed(uid, 'sql', level_id)
 hint_bought  = has_hint(uid, 'sql', level_id)
 message   = None
 rows    = None

 if request.method == 'POST':
  username = request.form.get('username', '').strip()
  password = request.form.get('password', '').strip()
  ulow  = username.lower()

  conn, table = get_db_for_level(level_id)
  c = conn.cursor()
  success = False

  try:
   if level_id == 1:
    c.execute(f"SELECT * FROM {table} WHERE username='{username}' AND password='{password}'")
    success = bool(c.fetchone())

   elif level_id == 2:
    fu = username.replace(" --", "--").replace("-- ", "--")
    fp = password.replace(" --", "--").replace("-- ", "--")
    c.execute(f"SELECT * FROM {table} WHERE username='{fu}' AND password='{fp}'")
    success = bool(c.fetchone())
    if not success:
     message = "ACCESS DENIED — попробуй admin'-- или admin'#"

   elif level_id == 3:
    c.execute(f"SELECT * FROM {table} WHERE username='{username}' AND password='{password}'")
    success = bool(c.fetchone()) or "order by" in ulow

   elif level_id == 4:
    if "union" in ulow:
     success = True
     rows = [("1", "8.0.35 - MySQL", "FLAG{SQL_LVL_4_DONE}")]
    else:
     message = "ACCESS DENIED — используй UNION SELECT"

   elif level_id == 5:
    if "information_schema" in ulow or "table_name" in ulow:
     success = True
     rows = [("secret_flags", "flag_column")]
    else:
     message = "ACCESS DENIED — ищи в information_schema.tables"

   elif level_id == 6:
    if any(k in ulow for k in ("flag", "secret_table", "secret_flags")):
     success = True
     rows = [("FLAG{SQL_LVL_6_DONE}", "Congratulations!")]
    else:
     message = "ACCESS DENIED — ищи FLAG или secret_table"

  except Exception as e:
   message = f"Database error: {e}"
  finally:
   conn.close()

  log_attempt(uid, 'sql', level_id, success, username)

  if success:
   is_won = True
   if not is_already_done:
    mark_completed(uid, 'sql', level_id)
    add_reward(uid, xp=50, balance=125)
    is_already_done = True
  elif not message:
   message = "ACCESS DENIED"

 return render_template(
  'sql_injection.html',
  level=level_data,
  is_won=is_won,
  is_already_completed=is_already_done,
  hint_bought=hint_bought,
  rows=rows,
  message=message,
 )
