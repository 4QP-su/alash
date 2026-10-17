from flask import Blueprint, render_template, request, session, redirect, url_for
import json
import os

from app.models import (
    get_rank,
    get_leaderboard,
    LEADERBOARD_TOP_N,
    get_user_stats,
    get_user_by_username,
    get_user_leaderboard_position,
    is_completed,
    check_and_give_daily_bonus,
    get_db,
)
from app.config import BASE_DIR, SUPPORTED_LANGS, t_for_lang
from .utils import login_required, current_user


main_bp = Blueprint('main', __name__)


def _load_ui_translations(lang: str) -> dict:
    t = t_for_lang(lang)
    translations_dir = os.path.join(BASE_DIR, 'translations')
    ach_path = os.path.join(translations_dir, f'achievements_{lang}.json')
    try:
        with open(ach_path, 'r', encoding='utf-8') as f:
            t.update(json.load(f))
    except FileNotFoundError:
        fallback_path = os.path.join(translations_dir, 'achievements_en.json')
        with open(fallback_path, 'r', encoding='utf-8') as f:
            t.update(json.load(f))
    return t


def _badge_slug(code: str) -> str:
    return code.lower().replace('/', '_')


def _build_badges(t: dict, badge_defs: list) -> list:
    badges = []
    for code, earned in badge_defs:
        slug = _badge_slug(code)
        badges.append({
            'code': code,
            'title': t.get(f'badge_{slug}_title', code),
            'desc': t.get(f'badge_{slug}_desc', ''),
            'earned': earned,
        })
    return badges


@main_bp.route('/')
def index():
    # Если пользователь залогинен, показываем dashboard
    if session.get('user_id'):
        user = current_user()
        if not user:
            session.clear()
            curr_lang = session.get('lang', 'ru')
            t = t_for_lang(curr_lang)
            return render_template('home.html', t=t, curr_lang=curr_lang)
        uid = user['id']

        check_and_give_daily_bonus(uid)

        # Guard against negative balance
        if user['balance'] < 0:
            conn = get_db()
            conn.execute("UPDATE users SET balance = 50 WHERE id = ? AND balance < 0", (uid,))
            conn.commit()
            conn.close()

        sql_done = sum(1 for i in range(1, 7) if is_completed(uid, 'sql', i))
        xss_done = sum(1 for i in range(1, 6) if is_completed(uid, 'xss', i))
        csrf_done = sum(1 for i in range(1, 4) if is_completed(uid, 'csrf', i))
        path_done = sum(1 for i in range(1, 4) if is_completed(uid, 'path', i))
        auth_done = sum(1 for i in range(1, 4) if is_completed(uid, 'auth', i))

        # Load translations
        curr_lang = session.get('lang', 'ru')
        t = t_for_lang(curr_lang)

        return render_template(
            'index.html',
            sql_done=sql_done,
            xss_done=xss_done,
            csrf_done=csrf_done,
            path_done=path_done,
            auth_done=auth_done,
            t=t,
            curr_lang=curr_lang,
        )
    else:
        # Если не залогинен, показываем home с переводами
        curr_lang = session.get('lang', 'ru')
        t = t_for_lang(curr_lang)
        return render_template('home.html', t=t, curr_lang=curr_lang)


@main_bp.route('/home')
def home():
    return redirect(url_for('main.index'))


@main_bp.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in SUPPORTED_LANGS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('main.index'))


@main_bp.route('/profile')
@login_required
def profile():
    user = current_user()
    uid = user['id']
    rank = get_rank(user['xp'])
    stats = get_user_stats(uid)
    
    # Get hints_bought and clean_completions
    conn = get_db()
    agg = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN hint_bought = 1 THEN 1 ELSE 0 END), 0) AS hints_bought,
            COALESCE(SUM(CASE WHEN completed = 1 AND hint_bought = 0 THEN 1 ELSE 0 END), 0) AS clean_completions
        FROM progress
        WHERE user_id = ?
        """,
        (uid,),
    ).fetchone()
    conn.close()
    
    stats['hints_bought'] = int(agg["hints_bought"])
    stats['clean_completions'] = int(agg["clean_completions"])
    
    # Get module progress
    levels_total = {'sql': 6, 'xss': 5, 'csrf': 3, 'path': 3, 'auth': 3}
    module_progress = {
        cat: sum(1 for i in range(1, total + 1) if is_completed(uid, cat, i))
        for cat, total in levels_total.items()
    }

    lang = session.get('lang', 'ru')
    t = t_for_lang(lang)

    return render_template(
        'profile.html',
        user=user,
        rank=rank,
        stats=stats,
        module_progress=module_progress,
        t=t,
        curr_lang=lang,
    )


@main_bp.route('/leaderboard')
@login_required
def leaderboard():
    user = current_user()
    board = get_leaderboard(LEADERBOARD_TOP_N)
    for row in board:
        row['is_me'] = row['username'] == user['username']
    lang = session.get('lang', 'ru')
    t = t_for_lang(lang)
    return render_template('leaderboard.html', board=board, current_user=user, t=t, curr_lang=lang)


def _public_profile_context(target_user: dict, viewer_id: int) -> dict:
    uid = target_user['id']
    rank = get_rank(target_user['xp'])
    stats = get_user_stats(uid)

    conn = get_db()
    agg = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN hint_bought = 1 THEN 1 ELSE 0 END), 0) AS hints_bought,
            COALESCE(SUM(CASE WHEN completed = 1 AND hint_bought = 0 THEN 1 ELSE 0 END), 0) AS clean_completions,
            COALESCE(SUM(CASE WHEN completed = 1 AND attempts = 1 THEN 1 ELSE 0 END), 0) AS first_try_completions
        FROM progress
        WHERE user_id = ?
        """,
        (uid,),
    ).fetchone()
    conn.close()

    stats['hints_bought'] = int(agg['hints_bought'])
    stats['clean_completions'] = int(agg['clean_completions'])
    stats['first_try_completions'] = int(agg['first_try_completions'])

    levels_total = {'sql': 6, 'xss': 5, 'csrf': 3, 'path': 3, 'auth': 3}
    module_progress = {
        cat: sum(1 for i in range(1, total + 1) if is_completed(uid, cat, i))
        for cat, total in levels_total.items()
    }
    theory_passed = sum(
        1 for cat in ('sql', 'xss', 'csrf', 'path', 'auth')
        if target_user.get(f'{cat}_theory_passed')
    )

    return {
        'user': target_user,
        'rank': rank,
        'stats': stats,
        'module_progress': module_progress,
        'levels_total': levels_total,
        'leaderboard_position': get_user_leaderboard_position(uid),
        'theory_passed': theory_passed,
        'is_own_profile': viewer_id == uid,
    }


@main_bp.route('/user/<username>')
@login_required
def user_profile(username):
    row = get_user_by_username(username)
    if not row:
        return redirect(url_for('main.leaderboard'))

    viewer = current_user()
    target_user = {
        'id': row['id'],
        'username': row['username'],
        'xp': row['xp'],
        'balance': row['balance'],
        'created_at': row['created_at'],
        'sql_theory_passed': row['sql_theory_passed'],
        'xss_theory_passed': row['xss_theory_passed'],
        'csrf_theory_passed': row['csrf_theory_passed'],
        'path_theory_passed': row['path_theory_passed'],
        'auth_theory_passed': row['auth_theory_passed'],
    }

    lang = session.get('lang', 'ru')
    t = t_for_lang(lang)

    ctx = _public_profile_context(target_user, viewer['id'])
    ctx['t'] = t
    ctx['curr_lang'] = lang
    return render_template('user_profile.html', **ctx)


@main_bp.route('/stats')
@login_required
def stats():
    # Redirect to profile since stats are now integrated there
    return redirect(url_for('main.profile'))

@main_bp.route('/achievements')
@login_required
def achievements():
    user = current_user()
    uid = user['id']

    levels_total = {'sql': 6, 'xss': 5, 'csrf': 3, 'path': 3, 'auth': 3}
    completed = {
        cat: sum(1 for i in range(1, total + 1) if is_completed(uid, cat, i))
        for cat, total in levels_total.items()
    }

    conn = get_db()
    agg = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END), 0) AS total_completed,
            COALESCE(SUM(attempts), 0) AS total_attempts,
            COALESCE(SUM(CASE WHEN hint_bought = 1 THEN 1 ELSE 0 END), 0) AS hints_bought,
            COALESCE(SUM(CASE WHEN completed = 1 AND hint_bought = 0 THEN 1 ELSE 0 END), 0) AS clean_completions,
            COALESCE(SUM(CASE WHEN completed = 1 AND attempts = 1 THEN 1 ELSE 0 END), 0) AS first_try_completions
        FROM progress
        WHERE user_id = ?
        """,
        (uid,),
    ).fetchone()
    conn.close()

    total_completed = int(agg["total_completed"])
    total_attempts = int(agg["total_attempts"])
    hints_bought = int(agg["hints_bought"])
    clean_completions = int(agg["clean_completions"])
    first_try_completions = int(agg["first_try_completions"])
    total_levels = sum(levels_total.values())
    all_theory_passed = all(
        bool(user[f"{cat}_theory_passed"]) for cat in ("sql", "xss", "csrf", "path", "auth")
    )

    badge_defs = [
        ("SQL/INIT/01", completed["sql"] >= 1),
        ("XSS/INIT/01", completed["xss"] >= 1),
        ("CSRF/INIT/01", completed["csrf"] >= 1),
        ("PATH/INIT/01", completed["path"] >= 1),
        ("AUTH/INIT/01", completed["auth"] >= 1),
        ("SQL/MASTER/ALL", completed["sql"] == levels_total["sql"]),
        ("XSS/MASTER/ALL", completed["xss"] == levels_total["xss"]),
        ("CSRF/MASTER/ALL", completed["csrf"] == levels_total["csrf"]),
        ("PATH/MASTER/ALL", completed["path"] == levels_total["path"]),
        ("AUTH/MASTER/ALL", completed["auth"] == levels_total["auth"]),
        ("THEORY/CORE/05", all_theory_passed),
        ("GLOBAL/100PCT", total_completed == total_levels),
        ("EXEC/FIRST/03", first_try_completions >= 3),
        ("EXEC/FIRST/10", first_try_completions >= 10),
        ("EXEC/CLEAN/08", clean_completions >= 8),
        ("EXEC/CLEAN/ALL", total_completed == total_levels and clean_completions == total_levels),
        ("ECON/BAL/1000", user["balance"] >= 1000),
        ("ECON/BAL/2500", user["balance"] >= 2500),
        ("ECON/SHOP/03", hints_bought >= 3),
        ("ECON/SHOP/08", hints_bought >= 8),
        ("OPS/GRIND/30", total_attempts >= 30),
        ("OPS/GRIND/75", total_attempts >= 75),
    ]

    lang = session.get('lang', 'ru')
    t = _load_ui_translations(lang)
    badges = _build_badges(t, badge_defs)
    unlocked_count = sum(1 for b in badges if b["earned"])

    return render_template(
        'achievements.html',
        badges=badges,
        unlocked_count=unlocked_count,
        total_badges=len(badges),
        t=t,
        curr_lang=lang,
    )


@main_bp.route('/reset')
def reset():
    session.clear()
    return redirect(url_for('auth.login'))
