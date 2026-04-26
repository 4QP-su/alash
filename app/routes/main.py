from flask import Blueprint, render_template, request, session, redirect, url_for

from app.models import (
    get_rank,
    get_leaderboard,
    get_user_stats,
    is_completed,
    check_and_give_daily_bonus,
    get_db,
)
from app.config import SUPPORTED_LANGS
from .utils import login_required, current_user


main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def index():
    user = current_user()
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

    return render_template(
        'index.html',
        sql_done=sql_done,
        xss_done=xss_done,
        csrf_done=csrf_done,
        path_done=path_done,
        auth_done=auth_done,
    )


@main_bp.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in SUPPORTED_LANGS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('main.index'))


@main_bp.route('/profile')
@login_required
def profile():
    user = current_user()
    rank = get_rank(user['xp'])
    stats = get_user_stats(user['id'])
    return render_template('profile.html', user=user, rank=rank, stats=stats)


@main_bp.route('/leaderboard')
@login_required
def leaderboard():
    user = current_user()
    board = get_leaderboard(10)
    for row in board:
        row['rank_info'] = get_rank(row['xp'])
        row['is_me'] = row['username'] == user['username']
    return render_template('leaderboard.html', board=board)


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

    badges = [
        {"code": "SQL/INIT/01", "title": "SQL ENTRY", "desc": "Complete SQL level 1.", "earned": completed["sql"] >= 1},
        {"code": "XSS/INIT/01", "title": "XSS ENTRY", "desc": "Complete XSS level 1.", "earned": completed["xss"] >= 1},
        {"code": "CSRF/INIT/01", "title": "CSRF ENTRY", "desc": "Complete CSRF level 1.", "earned": completed["csrf"] >= 1},
        {"code": "PATH/INIT/01", "title": "PATH ENTRY", "desc": "Complete Path Traversal level 1.", "earned": completed["path"] >= 1},
        {"code": "AUTH/INIT/01", "title": "AUTH ENTRY", "desc": "Complete Auth Bypass level 1.", "earned": completed["auth"] >= 1},

        {"code": "SQL/MASTER/ALL", "title": "SQL MASTER", "desc": "Finish all SQL levels.", "earned": completed["sql"] == levels_total["sql"]},
        {"code": "XSS/MASTER/ALL", "title": "XSS MASTER", "desc": "Finish all XSS levels.", "earned": completed["xss"] == levels_total["xss"]},
        {"code": "CSRF/MASTER/ALL", "title": "CSRF MASTER", "desc": "Finish all CSRF levels.", "earned": completed["csrf"] == levels_total["csrf"]},
        {"code": "PATH/MASTER/ALL", "title": "PATH MASTER", "desc": "Finish all Path levels.", "earned": completed["path"] == levels_total["path"]},
        {"code": "AUTH/MASTER/ALL", "title": "AUTH MASTER", "desc": "Finish all Auth levels.", "earned": completed["auth"] == levels_total["auth"]},

        {"code": "THEORY/CORE/05", "title": "THEORY CERTIFIED", "desc": "Pass theory quizzes in all 5 modules.", "earned": all_theory_passed},
        {"code": "GLOBAL/100PCT", "title": "FULL STACK THREAT", "desc": "Complete all module levels.", "earned": total_completed == total_levels},

        {"code": "EXEC/FIRST/03", "title": "COLD START", "desc": "Complete 3 levels on first try.", "earned": first_try_completions >= 3},
        {"code": "EXEC/FIRST/10", "title": "NO WARMUP", "desc": "Complete 10 levels on first try.", "earned": first_try_completions >= 10},
        {"code": "EXEC/CLEAN/08", "title": "CLEAN OPERATOR", "desc": "Complete 8 levels without buying hints.", "earned": clean_completions >= 8},
        {"code": "EXEC/CLEAN/ALL", "title": "NO-HINT HERO", "desc": "Complete all levels without hints.", "earned": total_completed == total_levels and clean_completions == total_levels},

        {"code": "ECON/BAL/1000", "title": "BLACK MARKET WHALE", "desc": "Reach $1000 balance.", "earned": user["balance"] >= 1000},
        {"code": "ECON/BAL/2500", "title": "SHADOW TREASURY", "desc": "Reach $2500 balance.", "earned": user["balance"] >= 2500},
        {"code": "ECON/SHOP/03", "title": "DATA ADDICT", "desc": "Buy 3 hints.", "earned": hints_bought >= 3},
        {"code": "ECON/SHOP/08", "title": "INTEL BROKER", "desc": "Buy 8 hints.", "earned": hints_bought >= 8},

        {"code": "OPS/GRIND/30", "title": "PERSISTENT", "desc": "Make 30 total attempts.", "earned": total_attempts >= 30},
        {"code": "OPS/GRIND/75", "title": "RELENTLESS", "desc": "Make 75 total attempts.", "earned": total_attempts >= 75},
    ]

    unlocked_count = sum(1 for b in badges if b["earned"])
    return render_template(
        'achievements.html',
        badges=badges,
        unlocked_count=unlocked_count,
        total_badges=len(badges),
    )


@main_bp.route('/reset')
def reset():
    session.clear()
    return redirect(url_for('auth.login'))
