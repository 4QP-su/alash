import os
from flask import Flask

from app.models import init_db
from app.config import BASE_DIR

def create_app():
 # ── Создаём приложение ──────────────────────────────────────────
 app = Flask(
  __name__,
  template_folder=os.path.join(BASE_DIR, '../templates'),
  static_folder=os.path.join(BASE_DIR, '../static'),
 )
 app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))

 # ── Инициализация БД ────────────────────────────────────────────
 with app.app_context():
  init_db()

 # ── Регистрация blueprints ──────────────────────────────────────
 from app.routes.auth import auth_bp
 from app.routes.main import main_bp
 from app.routes.sql  import sql_bp
 from app.routes.xss  import xss_bp 
 from app.routes.csrf import csrf_bp
 from app.routes.path_traversal import path_bp
 from app.routes.auth_bypass import authbypass_bp
 from app.routes.modules import modules_bp
 from app.routes.admin import admin_bp
 from app.routes.gemini_chat import gemini_bp

 app.register_blueprint(auth_bp)
 app.register_blueprint(main_bp)
 app.register_blueprint(sql_bp)
 app.register_blueprint(xss_bp)
 app.register_blueprint(csrf_bp)
 app.register_blueprint(path_bp)
 app.register_blueprint(authbypass_bp)
 app.register_blueprint(modules_bp)
 app.register_blueprint(admin_bp)
 app.register_blueprint(gemini_bp)

 # ── Context processor — current_user и переводы в шаблонах ─────
 from flask import session
 from app.models import get_user_by_id, get_rank
 from app.config import t_for_lang, HINT_PRICE, SURRENDER_PRICE, DAILY_BONUS

 @app.context_processor
 def inject_globals():
  lang = session.get('lang', 'ru')
  uid = session.get('user_id')
  user = get_user_by_id(uid) if uid else None
  rank = get_rank(user['xp']) if user else None
  return {
   'current_user': user,
   'current_rank': rank,
   't': t_for_lang(lang),
   'HINT_PRICE': HINT_PRICE,
   'SURRENDER_PRICE': SURRENDER_PRICE,
   'DAILY_BONUS': DAILY_BONUS,
   'hint_price': HINT_PRICE,
   'surrender_price': SURRENDER_PRICE,
   'daily_bonus': DAILY_BONUS,
  }

 @app.after_request
 def set_security_headers(response):
    # Basic recommended security headers; origin-level fallback when proxy/CDN isn't configured
    if 'X-Frame-Options' not in response.headers:
       response.headers['X-Frame-Options'] = 'DENY'
    if 'Strict-Transport-Security' not in response.headers:
       response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    # Start with Report-Only CSP to avoid breaking pages; move to enforce after validation
    if 'Content-Security-Policy' not in response.headers and 'Content-Security-Policy-Report-Only' not in response.headers:
       response.headers['Content-Security-Policy-Report-Only'] = "default-src 'self';"
    if 'X-Content-Type-Options' not in response.headers:
       response.headers['X-Content-Type-Options'] = 'nosniff'
    if 'Referrer-Policy' not in response.headers:
       response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if 'Permissions-Policy' not in response.headers:
       response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
    return response

 return app

