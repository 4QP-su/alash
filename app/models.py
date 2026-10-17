import sqlite3

import os

from datetime import datetime

import hashlib

import secrets



BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, '../data', 'users.db')





def get_db():

 conn = sqlite3.connect(DB_PATH)

 conn.row_factory = sqlite3.Row

 return conn





def init_db():

 """Создаёт все таблицы при первом запуске."""

 os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

 conn = get_db()

 c = conn.cursor()



 # --- Пользователи ---

 c.execute('''

  CREATE TABLE IF NOT EXISTS users (

   id   INTEGER PRIMARY KEY AUTOINCREMENT,

   username TEXT UNIQUE NOT NULL,

   email  TEXT UNIQUE,

   phone  TEXT UNIQUE,

   telegram TEXT UNIQUE,

   password TEXT NOT NULL,

   is_admin INTEGER DEFAULT 0,

   balance  INTEGER DEFAULT 500,

   xp   INTEGER DEFAULT 0,

   created_at TEXT DEFAULT (datetime('now')),

   last_login TEXT,

   last_bonus_date TEXT,

   csrf_theory_passed INTEGER DEFAULT 0,

   xss_theory_passed INTEGER DEFAULT 0,

   path_theory_passed INTEGER DEFAULT 0,

   auth_theory_passed INTEGER DEFAULT 0,

   sql_theory_passed INTEGER DEFAULT 0

  )

 ''')



 # --- Прогресс по уровням ---

 c.execute('''

  CREATE TABLE IF NOT EXISTS progress (

   id   INTEGER PRIMARY KEY AUTOINCREMENT,

   user_id  INTEGER NOT NULL,

   category TEXT NOT NULL, -- 'sql' / 'xss' / 'csrf'

   level_id INTEGER NOT NULL,

   completed INTEGER DEFAULT 0,

   unlocked INTEGER DEFAULT 0,

   hint_bought INTEGER DEFAULT 0,

   attempts INTEGER DEFAULT 0,

   completed_at TEXT,

   UNIQUE(user_id, category, level_id),

   FOREIGN KEY(user_id) REFERENCES users(id)

  )

 ''')



 # --- Лог каждой попытки ---

 c.execute('''

  CREATE TABLE IF NOT EXISTS attempts (

   id   INTEGER PRIMARY KEY AUTOINCREMENT,

   user_id  INTEGER NOT NULL,

   category TEXT NOT NULL,

   level_id INTEGER NOT NULL,

   success  INTEGER NOT NULL,

   payload  TEXT,

   ip_address TEXT,

   created_at TEXT DEFAULT (datetime('now')),

   FOREIGN KEY(user_id) REFERENCES users(id)

  )

 ''')



 conn.commit()

 conn.close()

 # --- Системные настройки для админов ---
 conn = get_db()
 c = conn.cursor()
 c.execute('''

  CREATE TABLE IF NOT EXISTS system_settings (

   key TEXT PRIMARY KEY,

   value TEXT NOT NULL,

   updated_at TEXT DEFAULT (datetime('now'))

  )

 ''')

 # --- Журнал админских действий и банов ---
 c.execute('''

  CREATE TABLE IF NOT EXISTS activity_logs (

   id   INTEGER PRIMARY KEY AUTOINCREMENT,

   user_id INTEGER,

   action TEXT NOT NULL,

   details TEXT,

   ip_address TEXT,

   user_agent TEXT,

   created_at TEXT DEFAULT (datetime('now')),

   FOREIGN KEY(user_id) REFERENCES users(id)

  )

''')

 conn.commit()
 conn.close()

 # Ensure legacy DB schemas are updated with new columns
 _ensure_attempts_columns()
 _ensure_activity_log_columns()


def get_system_setting(key: str, default=None):
 conn = get_db()
 row = conn.execute(
  "SELECT value FROM system_settings WHERE key = ?",
  (key,),
 ).fetchone()
 conn.close()
 return row['value'] if row else default


def set_system_setting(key: str, value: str):
 conn = get_db()
 conn.execute(
  "INSERT INTO system_settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')",
  (key, value),
 )
 conn.commit()
 conn.close()


 _ensure_user_columns()


def log_activity(user_id: int, action: str, details: str = None, ip_address: str = None, user_agent: str = None):
 conn = get_db()
 conn.execute(
  "INSERT INTO activity_logs(user_id, action, details, ip_address, user_agent) VALUES (?, ?, ?, ?, ?)",
  (user_id, action, details, ip_address, user_agent),
 )
 conn.commit()
 conn.close()


 _ensure_user_columns()





# ──────────────────────────────────────────────

# Пароли

# ──────────────────────────────────────────────



def _ensure_user_columns():

 conn = get_db()

 cols = [row['name'] for row in conn.execute("PRAGMA table_info(users)").fetchall()]

 alters = []

 if 'csrf_theory_passed' not in cols:

  alters.append("ALTER TABLE users ADD COLUMN csrf_theory_passed INTEGER DEFAULT 0")

 if 'xss_theory_passed' not in cols:

  alters.append("ALTER TABLE users ADD COLUMN xss_theory_passed INTEGER DEFAULT 0")

 if 'path_theory_passed' not in cols:

  alters.append("ALTER TABLE users ADD COLUMN path_theory_passed INTEGER DEFAULT 0")

 if 'auth_theory_passed' not in cols:

  alters.append("ALTER TABLE users ADD COLUMN auth_theory_passed INTEGER DEFAULT 0")

 if 'sql_theory_passed' not in cols:

  alters.append("ALTER TABLE users ADD COLUMN sql_theory_passed INTEGER DEFAULT 0")

 if 'telegram' not in cols:

  alters.append("ALTER TABLE users ADD COLUMN telegram TEXT")

 for sql in alters:

  conn.execute(sql)

  # Create unique index for telegram (NULL-safe)
  try:
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_telegram_unique ON users(telegram) WHERE telegram IS NOT NULL")
  except:
    pass

 if alters:

  conn.commit()

 conn.close()





def hash_password(password: str) -> str:

 salt = secrets.token_hex(16)

 hashed = hashlib.sha256((salt + password).encode()).hexdigest()

 return f"{salt}:{hashed}"





def check_password(password: str, stored: str) -> bool:

 try:

  salt, hashed = stored.split(":")

  return hashlib.sha256((salt + password).encode()).hexdigest() == hashed

 except Exception:

  return False





# ──────────────────────────────────────────────

# Пользователи

# ──────────────────────────────────────────────



def create_user(username: str, email: str, password: str, phone: str = '', telegram: str = '') -> dict:

 """Регистрирует нового пользователя. Возвращает {'ok': True} или {'error': '...'}"""

 conn = get_db()

 c = conn.cursor()

 # Нормализуем данные — пустые строки в None
 email_clean = email.strip().lower() if email and email.strip() else None
 phone_clean = phone.strip() if phone and phone.strip() else None
 telegram_clean = telegram.strip().lower() if telegram and telegram.strip() else None

 try:

  c.execute(

   "INSERT INTO users (username, email, phone, telegram, password) VALUES (?, ?, ?, ?, ?)",

   (username.strip(), email_clean, phone_clean, telegram_clean, hash_password(password))

  )

  conn.commit()

  return {"ok": True, "user_id": c.lastrowid}

 except sqlite3.IntegrityError as e:

  if "username" in str(e):

   return {"error": "Имя пользователя уже занято"}

  if "email" in str(e):

   return {"error": "Email уже зарегистрирован"}

  if "phone" in str(e):

   return {"error": "Номер телефона уже зарегистрирован"}

  return {"error": str(e)}

 finally:

  conn.close()





def get_user_by_username(username: str):

 conn = get_db()

 user = conn.execute(

  "SELECT * FROM users WHERE username = ?", (username,)

 ).fetchone()

 conn.close()

 return user





def get_user_by_id(user_id: int):

 conn = get_db()

 user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

 conn.close()

 return user





def update_last_login(user_id: int):

 conn = get_db()

 conn.execute(

  "UPDATE users SET last_login = ? WHERE id = ?",

  (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id)

 )

 conn.commit()

 conn.close()





# ──────────────────────────────────────────────

# Баланс / XP

# ──────────────────────────────────────────────



def add_reward(user_id: int, xp: int = 0, balance: int = 0):

 conn = get_db()

 conn.execute(

  "UPDATE users SET xp = xp + ?, balance = balance + ? WHERE id = ?",

  (xp, balance, user_id)

 )

 conn.commit()

 conn.close()





def deduct_balance(user_id: int, amount: int) -> bool:

 conn = get_db()

 user = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,)).fetchone()

 if not user or user["balance"] < amount:

  conn.close()

  return False

 conn.execute(

  "UPDATE users SET balance = balance - ? WHERE id = ?",

  (amount, user_id)

 )

 conn.commit()

 conn.close()

 return True





def check_and_give_daily_bonus(user_id: int):

 today = datetime.now().strftime('%Y-%m-%d')

 conn = get_db()

 user = conn.execute(

  "SELECT last_bonus_date FROM users WHERE id = ?", (user_id,)

 ).fetchone()

 if user and user["last_bonus_date"] != today:

  conn.execute(

   "UPDATE users SET balance = balance + 100, last_bonus_date = ? WHERE id = ?",

   (today, user_id)

  )

  conn.commit()

 conn.close()





# ──────────────────────────────────────────────

# Прогресс

# ──────────────────────────────────────────────



def _ensure_progress(c, user_id, category, level_id):

 c.execute(

  "INSERT OR IGNORE INTO progress (user_id, category, level_id) VALUES (?, ?, ?)",

  (user_id, category, level_id)

 )





def is_completed(user_id: int, category: str, level_id: int) -> bool:

 conn = get_db()

 row = conn.execute(

  "SELECT completed FROM progress WHERE user_id=? AND category=? AND level_id=?",

  (user_id, category, level_id)

 ).fetchone()

 conn.close()

 return bool(row and row["completed"])





def is_unlocked(user_id: int, category: str, level_id: int) -> bool:

 if level_id == 1:

  return True

 conn = get_db()

 # разблокирован если предыдущий пройден ИЛИ куплен

 prev = conn.execute(

  "SELECT completed FROM progress WHERE user_id=? AND category=? AND level_id=?",

  (user_id, category, level_id - 1)

 ).fetchone()

 bought = conn.execute(

  "SELECT unlocked FROM progress WHERE user_id=? AND category=? AND level_id=?",

  (user_id, category, level_id)

 ).fetchone()

 conn.close()

 return bool((prev and prev["completed"]) or (bought and bought["unlocked"]))





def mark_completed(user_id: int, category: str, level_id: int):

 conn = get_db()

 c = conn.cursor()

 _ensure_progress(c, user_id, category, level_id)

 c.execute(

  "UPDATE progress SET completed=1, completed_at=? WHERE user_id=? AND category=? AND level_id=?",

  (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id, category, level_id)

 )

 conn.commit()

 conn.close()





def mark_unlocked(user_id: int, category: str, level_id: int):

 conn = get_db()

 c = conn.cursor()

 _ensure_progress(c, user_id, category, level_id)

 c.execute(

  "UPDATE progress SET unlocked=1 WHERE user_id=? AND category=? AND level_id=?",

  (user_id, category, level_id)

 )

 conn.commit()

 conn.close()





def has_hint(user_id: int, category: str, level_id: int) -> bool:

 conn = get_db()

 row = conn.execute(

  "SELECT hint_bought FROM progress WHERE user_id=? AND category=? AND level_id=?",

  (user_id, category, level_id)

 ).fetchone()

 conn.close()

 return bool(row and row["hint_bought"])





def mark_hint_bought(user_id: int, category: str, level_id: int):

 conn = get_db()

 c = conn.cursor()

 _ensure_progress(c, user_id, category, level_id)

 c.execute(

  "UPDATE progress SET hint_bought=1 WHERE user_id=? AND category=? AND level_id=?",

  (user_id, category, level_id)

 )

 conn.commit()

 conn.close()





def mark_theory_passed(user_id: int, category: str):

 column = _theory_column(category)

 if not column:

  return

 conn = get_db()

 conn.execute(

  f"UPDATE users SET {column} = 1 WHERE id = ?",

  (user_id,)

 )

 conn.commit()

 conn.close()





def has_passed_theory(user_id: int, category: str) -> bool:

 column = _theory_column(category)

 if not column:

  return False

 conn = get_db()

 row = conn.execute(

  f"SELECT {column} FROM users WHERE id = ?",

  (user_id,)

 ).fetchone()

 conn.close()

 return bool(row and row[column])





def _theory_column(category: str) -> str:

 return {

  'csrf': 'csrf_theory_passed',

  'xss': 'xss_theory_passed',

  'path': 'path_theory_passed',

  'auth': 'auth_theory_passed',

  'sql': 'sql_theory_passed',

 }.get(category)





def log_attempt(user_id: int, category: str, level_id: int, success: bool, payload: str = "", ip_address: str = None):

 conn = get_db()

 c = conn.cursor()

 # увеличиваем счётчик попыток

 _ensure_progress(c, user_id, category, level_id)

 c.execute(

  "UPDATE progress SET attempts = attempts + 1 WHERE user_id=? AND category=? AND level_id=?",

  (user_id, category, level_id)

 )

 c.execute(

  "INSERT INTO attempts (user_id, category, level_id, success, payload, ip_address) VALUES (?, ?, ?, ?, ?, ?)",

  (user_id, category, level_id, int(success), payload[:500], ip_address)

 )

 conn.commit()

 conn.close()





# ──────────────────────────────────────────────

# Ранги

# ──────────────────────────────────────────────



RANKS = [

 (0, "Newbie",  "⬜"),

 (150, "Script Kiddie",""),

 (500, "White Hat", ""),

 (1000, "Elite Hacker", ""),

 (2000, "Zero Day",  ""),

]



def get_rank(xp: int) -> dict:

 rank_name, rank_icon = RANKS[0][1], RANKS[0][2]

 next_xp = RANKS[1][0]

 for i, (threshold, name, icon) in enumerate(RANKS):

  if xp >= threshold:

   rank_name, rank_icon = name, icon

   next_xp = RANKS[i + 1][0] if i + 1 < len(RANKS) else None

 progress_pct = 0

 if next_xp:

  # найдём порог текущего ранга

  curr_threshold = 0

  for threshold, name, _ in RANKS:

   if name == rank_name:

    curr_threshold = threshold

  span = next_xp - curr_threshold

  progress_pct = min(100, int((xp - curr_threshold) / span * 100))

 return {

  "name": rank_name,

  "icon": rank_icon,

  "next_xp": next_xp,

  "progress_pct": progress_pct,

 }





# ──────────────────────────────────────────────

# Лидерборд

# ──────────────────────────────────────────────

LEADERBOARD_TOP_N = 10



def get_leaderboard(limit: int = LEADERBOARD_TOP_N) -> list:

 conn = get_db()

 rows = conn.execute(

  "SELECT id, username, xp, balance FROM users ORDER BY xp DESC LIMIT ?", (limit,)

 ).fetchall()

 conn.close()

 return [dict(r) for r in rows]





def get_user_leaderboard_position(user_id: int) -> int:

 conn = get_db()

 row = conn.execute(

  """

  SELECT 1 + COUNT(*) AS pos

  FROM users

  WHERE xp > (SELECT xp FROM users WHERE id = ?)

  """,

  (user_id,),

 ).fetchone()

 conn.close()

 return int(row["pos"]) if row else 0





# ──────────────────────────────────────────────

# Статистика (для профиля)

# ──────────────────────────────────────────────



def get_user_stats(user_id: int) -> dict:

 conn = get_db()

 total_completed = conn.execute(

  "SELECT COUNT(*) as cnt FROM progress WHERE user_id=? AND completed=1", (user_id,)

 ).fetchone()["cnt"]



 total_attempts = conn.execute(

  "SELECT SUM(attempts) as s FROM progress WHERE user_id=?", (user_id,)

 ).fetchone()["s"] or 0



 last_activity = conn.execute(

  "SELECT MAX(created_at) as la FROM attempts WHERE user_id=?", (user_id,)

 ).fetchone()["la"]



 conn.close()

 return {

  "total_completed": total_completed,

  "total_attempts": total_attempts,

  "last_activity": last_activity,

 }




# ──────────────────────────────────────────────

# Admin Functions

# ──────────────────────────────────────────────


def _ensure_admin_tables():

  """Создаёт таблицы для админ-функционала если их нет."""

  conn = get_db()

  c = conn.cursor()


  # Таблица объявлений

  c.execute('''

   CREATE TABLE IF NOT EXISTS announcements (

    id   INTEGER PRIMARY KEY AUTOINCREMENT,

    title TEXT NOT NULL,

    message TEXT NOT NULL,

    is_active INTEGER DEFAULT 1,

    created_by INTEGER NOT NULL,

    created_at TEXT DEFAULT (datetime('now')),

    expires_at TEXT,

    FOREIGN KEY(created_by) REFERENCES users(id)

   )

  ''')


  # Таблица настроек системы

  c.execute('''

   CREATE TABLE IF NOT EXISTS system_settings (

    key TEXT PRIMARY KEY,

    value TEXT NOT NULL,

    updated_at TEXT DEFAULT (datetime('now'))

   )

  ''')


  # Таблица логов активности

  c.execute('''

   CREATE TABLE IF NOT EXISTS activity_logs (

    id   INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER,

    action TEXT NOT NULL,

    details TEXT,

    ip_address TEXT,

    user_agent TEXT,

    created_at TEXT DEFAULT (datetime('now')),

    FOREIGN KEY(user_id) REFERENCES users(id)

   )

  ''')

  conn.commit()

  conn.close()


def _ensure_attempts_columns():
  conn = get_db()
  cols = [row['name'] for row in conn.execute("PRAGMA table_info(attempts)").fetchall()]
  alters = []
  if 'ip_address' not in cols:
    alters.append("ALTER TABLE attempts ADD COLUMN ip_address TEXT")
  if 'created_at' not in cols:
    alters.append("ALTER TABLE attempts ADD COLUMN created_at TEXT DEFAULT (datetime('now'))")
  for stmt in alters:
    conn.execute(stmt)
  conn.commit()
  conn.close()


def _ensure_activity_log_columns():
  conn = get_db()
  cols = [row['name'] for row in conn.execute("PRAGMA table_info(activity_logs)").fetchall()]
  alters = []
  if 'ip_address' not in cols:
    alters.append("ALTER TABLE activity_logs ADD COLUMN ip_address TEXT")
  if 'user_agent' not in cols:
    alters.append("ALTER TABLE activity_logs ADD COLUMN user_agent TEXT")
  for stmt in alters:
    conn.execute(stmt)
  conn.commit()
  conn.close()


# ──── Users Management ────

def get_all_users(sort_by='xp', limit=None):

  """Получить список всех пользователей с их статистикой."""

  conn = get_db()

  query = """

    SELECT id, username, email, xp, balance, created_at, last_login, is_admin

    FROM users

    ORDER BY {} DESC

  """.format(sort_by)

  if limit:

   query += f" LIMIT {limit}"

  rows = conn.execute(query).fetchall()

  conn.close()

  return [dict(r) for r in rows]


def reset_user_progress(user_id: int):

  """Сбросить весь прогресс пользователя."""

  conn = get_db()

  conn.execute("DELETE FROM progress WHERE user_id = ?", (user_id,))

  conn.execute("DELETE FROM attempts WHERE user_id = ?", (user_id,))

  conn.execute("UPDATE users SET xp = 0 WHERE id = ?", (user_id,))

  conn.commit()

  conn.close()


def ban_user(user_id: int):

  """Забанить пользователя (удалить)."""

  conn = get_db()

  conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

  conn.commit()

  conn.close()


def get_user_profile(user_id: int):

  """Получить полный профиль пользователя для админа."""

  conn = get_db()

  user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

  if not user:

    conn.close()

    return None

  progress = conn.execute(

   "SELECT category, level_id, completed, attempts FROM progress WHERE user_id = ? ORDER BY category, level_id",

   (user_id,)

  ).fetchall()

  stats = get_user_stats(user_id)

  conn.close()

  return {

   'user': dict(user),

   'progress': [dict(p) for p in progress],

   'stats': stats,

  }


# ──── Analytics ────

def get_level_completion_stats():

  """Получить статистику прохождения по каждому уровню."""

  conn = get_db()

  rows = conn.execute("""

    SELECT

     category,

     level_id,

     COUNT(*) as total_users,

     SUM(completed) as users_completed,

     ROUND(100.0 * SUM(completed) / COUNT(*), 1) as completion_rate

    FROM progress

    GROUP BY category, level_id

    ORDER BY category, level_id

  """).fetchall()

  conn.close()

  return [dict(r) for r in rows]


def get_dropoff_analysis():

  """Найти уровни где чаще всего застревают/бросают."""

  conn = get_db()

  rows = conn.execute("""

    SELECT

     category,

     level_id,

     COUNT(*) as total_attempts,

     SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,

     ROUND(100.0 * SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) / COUNT(*), 1) as success_rate

    FROM attempts

    GROUP BY category, level_id

    ORDER BY success_rate ASC, total_attempts DESC

  """).fetchall()

  conn.close()

  return [dict(r) for r in rows]


def get_activity_by_date(days=30):

  """Получить активность по дням (регистрации, решённые задачи)."""

  conn = get_db()

  rows = conn.execute("""

    SELECT

     DATE(created_at) as date,

     (SELECT COUNT(*) FROM users WHERE DATE(created_at) = DATE(attempts.created_at)) as new_users,

     COUNT(*) as total_attempts,

     SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_attempts

    FROM attempts

    WHERE created_at >= datetime('now', '-' || ? || ' days')

    GROUP BY DATE(created_at)

    ORDER BY date DESC

  """, (days,)).fetchall()

  conn.close()

  return [dict(r) for r in rows]


# ──── Announcements ────

def create_announcement(title: str, message: str, created_by: int, expires_at=None):

  """Создать новое объявление."""

  conn = get_db()

  conn.execute(

   "INSERT INTO announcements (title, message, created_by, expires_at) VALUES (?, ?, ?, ?)",

   (title, message, created_by, expires_at)

  )

  conn.commit()

  conn.close()


def get_active_announcements():

  """Получить активные объявления."""

  conn = get_db()

  rows = conn.execute("""

    SELECT * FROM announcements

    WHERE is_active = 1 AND (expires_at IS NULL OR expires_at > datetime('now'))

    ORDER BY created_at DESC

  """).fetchall()

  conn.close()

  return [dict(r) for r in rows]


def get_all_announcements():

  """Получить все объявления (для админа)."""

  conn = get_db()

  rows = conn.execute("SELECT * FROM announcements ORDER BY created_at DESC").fetchall()

  conn.close()

  return [dict(r) for r in rows]


def deactivate_announcement(announcement_id: int):

  """Деактивировать объявление."""

  conn = get_db()

  conn.execute("UPDATE announcements SET is_active = 0 WHERE id = ?", (announcement_id,))

  conn.commit()

  conn.close()


# ──── System Settings ────

def get_setting(key: str, default=None):

  """Получить значение системной настройки."""

  conn = get_db()

  row = conn.execute("SELECT value FROM system_settings WHERE key = ?", (key,)).fetchone()

  conn.close()

  if row:

    try:

      return int(row['value'])

    except ValueError:

      return row['value']

  return default


def set_setting(key: str, value):

  """Установить значение системной настройки."""

  conn = get_db()

  conn.execute(

   "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",

   (key, str(value), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

  )

  conn.commit()

  conn.close()


# ──── Activity Logs ────

def log_activity(user_id, action: str, details=None, ip_address=None, user_agent=None):

  """Залогировать действие администратора или системы."""

  conn = get_db()

  conn.execute(

   "INSERT INTO activity_logs (user_id, action, details, ip_address, user_agent) VALUES (?, ?, ?, ?, ?)",

   (user_id, action, details, ip_address, user_agent)

  )

  conn.commit()

  conn.close()


def get_activity_logs(limit=100):

  """Получить логи активности."""

  conn = get_db()

  rows = conn.execute("""

    SELECT al.*, u.username

    FROM activity_logs al

    LEFT JOIN users u ON al.user_id = u.id

    ORDER BY al.created_at DESC

    LIMIT ?

  """, (limit,)).fetchall()

  conn.close()

  return [dict(r) for r in rows]

