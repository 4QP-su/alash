import re
from flask import Blueprint, render_template, request, session, redirect, url_for
from app.models import (
 is_completed, is_unlocked, mark_completed,
 has_hint, log_attempt, add_reward,
 mark_theory_passed, has_passed_theory,
)
from app.config import load_levels
from .utils import login_required, current_user

xss_bp = Blueprint('xss', __name__)


def _get_levels():
 return load_levels('levels_xss.json', session.get('lang', 'ru'))


@xss_bp.route('/XSS/theory')
def xss_theory():
 show_quiz = request.args.get('quiz') == '1'
 return render_template('xss_theory.html', show_quiz=show_quiz)


@xss_bp.route('/verify-theory/xss', methods=['POST'])
@login_required
def verify_xss_theory():
 wrong = [str(i) for i in range(1, 7) if request.form.get(f'q{i}') != 'corr']
 if not wrong:
  user = current_user()
  mark_theory_passed(user['id'], 'xss')
  return redirect(url_for('xss.xss_labs'))
 
 # Quiz hints for wrong answers
 from app.config import t_for_lang
 t = t_for_lang(session.get('lang', 'ru'))
 quiz_hints = t.get('quiz_hints', {}).get('xss', {})
 
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
  'ru': f"{err} {wrong_questions_text}: {', '.join(wrong)}.\n\n" + "\n".join(hint_messages) + "\n\nnepemotpu teopuio no npo6yi eshe pa3.",
  'kz': f"{err} {wrong_questions_text}: {', '.join(wrong)}.\n\n" + "\n".join(hint_messages) + "\n\nTeophnyo kaira kapan, tarbai kaph koph.",
 }
 err_msg = details.get(lang, f"{err} {wrong_questions_text}: {', '.join(wrong)}.\n\n" + "\n".join(hint_messages) + "\n\nReview theory and try again.")
 return render_template('xss_theory.html', error=err_msg, show_quiz=True)


@xss_bp.route('/XSS')
@login_required
def xss_labs():
 levels = _get_levels()
 user = current_user()
 uid = user['id']
 for lvl in levels.values():
  lid    = lvl['id']
  lvl['completed'] = is_completed(uid, 'xss', lid)
  lvl['unlocked'] = lid == 1 or is_completed(uid, 'xss', lid-1) or is_unlocked(uid, 'xss', lid)
 return render_template('xss_levels.html', levels=levels.values())


@xss_bp.route('/XSS/<int:level_id>', methods=['GET', 'POST'])
@login_required
def xss_level(level_id):
 user = current_user()
 uid = user['id']
 if not has_passed_theory(uid, 'xss'):
  return redirect(url_for('xss.xss_theory'))

 levels  = _get_levels()
 level_data = levels.get(level_id)
 if not level_data:
  return redirect(url_for('xss.xss_labs'))

 user = current_user()
 uid  = user['id']
 unlocked = level_id == 1 or is_completed(uid,'xss',level_id-1) or is_unlocked(uid,'xss',level_id)
 if not unlocked:
  return render_template('access_denied.html', level_id=level_id, category='xss')

 already  = is_completed(uid, 'xss', level_id)
 hint_bought = has_hint(uid, 'xss', level_id)
 message  = ""
 is_won  = False

 if request.method == 'POST' and not already:
  val  = request.form.get('user_input', '')
  val_low = val.lower().strip()

  if level_id == 1:
   is_won = '<script>' in val_low and 'alert' in val_low

  elif level_id == 2:
   blocked = bool(re.search(r'<script>', val))
   has_spaces = bool(re.search(r'<\s+script\s*>', val, re.IGNORECASE))
   is_won = has_spaces and not blocked and 'alert' in val_low

  elif level_id == 3:
   no_script = not bool(re.search(r'<\s*script', val_low))
   has_event = bool(re.search(r'on(error|load|mouseover|click|focus)\s*=', val_low))
   is_won = has_event and no_script and 'alert' in val_low

  elif level_id == 4:
   direct = bool(re.search(r'\balert\b', val_low))
   encoded = any(x in val_low for x in
       ['\\u00','string.fromcharcode','eval(','atob(','confirm(','prompt('])
   is_won = encoded and not direct

  elif level_id == 5:
   has_js = bool(re.search(r'javascript\s*:', val_low))
   has_data = bool(re.search(r'data\s*:\s*text/html', val_low))
   is_won = (has_js or has_data) and 'alert' in val_low

  log_attempt(uid, 'xss', level_id, is_won, val[:300])

  if is_won:
   mark_completed(uid, 'xss', level_id)
   add_reward(uid, xp=100, balance=125)
   message = " XSS SUCCESS!"
  else:
   message = " Payload не сработал. Попробуй ещё раз."

 return render_template(
  'xss.html',
  level=level_id,
  level_data=level_data,
  description=level_data['desc'],
  level_hint=level_data['hint'],
  message=message,
  hint_bought=hint_bought,
  is_already_completed=already or is_won,
  is_won=is_won,
 )
