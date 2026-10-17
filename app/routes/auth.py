import time
from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from app.models import (
    create_user, get_user_by_username, check_password,
    update_last_login, check_and_give_daily_bonus,
)
from app.utils.email_check import is_valid_email_format, email_domain_exists
from app.utils.email_sender import generate_code, send_verification_email
from app.utils.phone_sender import (
    generate_code as generate_phone_code,
    send_verification_sms,
    is_valid_phone,
    normalize_phone,
    is_valid_telegram,
    normalize_telegram,
    send_verification_telegram
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect("/")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm  = request.form.get("confirm", "").strip()
        phone     = request.form.get("phone", "").strip()
        telegram  = request.form.get("telegram", "").strip()
        method    = request.form.get("method", "email")  # email, phone или telegram

        # Валидация
        has_error = False
        
        if not username or not password:
            flash("Заполните имя пользователя и пароль", "error")
            has_error = True
        elif len(username) < 3:
            flash("Имя пользователя должно быть минимум 3 символа", "error")
            has_error = True
        elif len(password) < 6:
            flash("Пароль минимум 6 символов", "error")
            has_error = True
        elif password != confirm:
            flash("Пароли не совпадают", "error")
            has_error = True
        
        # Проверяем что заполнен хотя бы один контакт (email, phone или telegram)
        if not has_error and not email and not phone and not telegram:
            flash("Укажите email, номер телефона или Telegram", "error")
            has_error = True
        
        # Проверка email если выбран метод email или email указан
        if not has_error and email:
            if not is_valid_email_format(email):
                flash("Некорректный формат email", "error")
                has_error = True
            elif not email_domain_exists(email):
                flash("Email-адрес не существует (домен не найден)", "error")
                has_error = True
        
        # Проверка телефона если выбран метод phone
        phone_normalized = normalize_phone(phone) if phone else ''
        if not has_error and method == 'phone':
            if not phone:
                flash("Укажите номер телефона для SMS верификации", "error")
                has_error = True
            elif not is_valid_phone(phone):
                flash("Некорректный формат номера телефона", "error")
                has_error = True
        
        # Проверка Telegram если выбран метод telegram
        telegram_normalized = normalize_telegram(telegram) if telegram else ''
        if not has_error and method == 'telegram':
            if not telegram:
                flash("Укажите Telegram username", "error")
                has_error = True
            elif not is_valid_telegram(telegram):
                flash("Некорректный формат Telegram username", "error")
                has_error = True
        
        if not has_error:    # Сохраняем данные во временную сессию
            code = generate_code()
            session['pending_register'] = {
                'username': username,
                'email':    email,
                'password': password,
                'phone':    phone_normalized,
                'telegram': telegram_normalized,
                'method':   method,
                'code':     code,
                'expires':  time.time() + 600,  # 10 минут
            }

            # Выбираем метод верификации
            if method == 'telegram' and telegram_normalized:
                if send_verification_telegram(telegram_normalized, code):
                    flash(f"Код отправлен в Telegram @{telegram_normalized}", "success")
                    return redirect(url_for("auth.verify_telegram"))
                else:
                    flash("Не удалось отправить код в Telegram. Проверь username и нажми START в боте @hckr_sbot", "error")
            elif method == 'phone' and phone_normalized:
                if send_verification_sms(phone_normalized, code):
                    flash(f"Код отправлен на {phone_normalized}", "success")
                    return redirect(url_for("auth.verify_phone"))
                else:
                    flash("Не удалось отправить SMS. Проверь номер или выбери email.", "error")
            else:
                # Email верификация (по умолчанию)
                if not email:
                    flash("Email обязателен для email-верификации", "error")
                elif send_verification_email(email, code):
                    flash(f"Код отправлен на {email}", "success")
                    return redirect(url_for("auth.verify_email"))
                else:
                    flash("Не удалось отправить письмо. Проверь email.", "error")

    return render_template("register.html")


@auth_bp.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    pending = session.get('pending_register')

    # Если нет ожидающей регистрации — на страницу регистрации
    if not pending:
        return redirect(url_for("auth.register"))

    # Проверяем не истёк ли код
    if time.time() > pending.get('expires', 0):
        session.pop('pending_register', None)
        flash("Код истёк. Зарегистрируйся заново.", "error")
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        entered = request.form.get("code", "").strip()

        if entered == pending['code']:
            # Код верный — создаём аккаунт
            phone = pending.get('phone', '')
            result = create_user(pending['username'], pending['email'], pending['password'], phone)
            session.pop('pending_register', None)

            if result.get("ok"):
                flash("Аккаунт создан! Войдите в систему.", "success")
                return redirect(url_for("auth.login"))
            else:
                flash(result.get("error", "Ошибка регистрации"), "error")
                return redirect(url_for("auth.register"))
        else:
            flash("Неверный код. Попробуй ещё раз.", "error")

    return render_template("verify_email.html", email=pending.get('email', ''), phone=pending.get('phone', ''))


@auth_bp.route("/register/resend", methods=["POST"])
def resend_code():
    pending = session.get('pending_register')
    if not pending:
        return redirect(url_for("auth.register"))

    code = generate_code()
    pending['code']    = code
    pending['expires'] = time.time() + 600
    session['pending_register'] = pending  # обновляем сессию

    # Определяем метод верификации
    method = pending.get('method', 'email')
    
    if method == 'telegram' and pending.get('telegram'):
        if send_verification_telegram(pending['telegram'], code):
            flash("Новый код отправлен в Telegram.", "success")
            return redirect(url_for("auth.verify_telegram"))
        else:
            flash("Ошибка отправки в Telegram. Проверь username и нажми START в боте.", "error")
            return redirect(url_for("auth.verify_telegram"))
    elif method == 'phone' and pending.get('phone'):
        if send_verification_sms(pending['phone'], code):
            flash("Новый код отправлен.", "success")
            return redirect(url_for("auth.verify_phone"))
        else:
            flash("Ошибка отправки SMS. Попробуй позже.", "error")
            return redirect(url_for("auth.verify_phone"))
    else:
        if send_verification_email(pending['email'], code):
            flash("Новый код отправлен.", "success")
        else:
            flash("Ошибка отправки. Попробуй позже.", "error")

    return redirect(url_for("auth.verify_email"))


@auth_bp.route("/verify-phone", methods=["GET", "POST"])
def verify_phone():
    pending = session.get('pending_register')

    # Если нет ожидающей регистрации — на страницу регистрации
    if not pending:
        return redirect(url_for("auth.register"))

    # Проверяем не истёк ли код
    if time.time() > pending.get('expires', 0):
        session.pop('pending_register', None)
        flash("Код истёк. Зарегистрируйся заново.", "error")
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        entered = request.form.get("code", "").strip()

        if entered == pending['code']:
            # Код верный — создаём аккаунт
            phone = pending.get('phone', '')
            result = create_user(pending['username'], pending['email'], pending['password'], phone)
            session.pop('pending_register', None)

            if result.get("ok"):
                flash("Аккаунт создан! Войдите в систему.", "success")
                return redirect(url_for("auth.login"))
            else:
                flash(result.get("error", "Ошибка регистрации"), "error")
                return redirect(url_for("auth.register"))
        else:
            flash("Неверный код. Попробуй ещё раз.", "error")

    return render_template("verify_phone.html", phone=pending.get('phone', ''))


@auth_bp.route("/verify-telegram", methods=["GET", "POST"])
def verify_telegram():
    pending = session.get('pending_register')

    # Если нет ожидающей регистрации — на страницу регистрации
    if not pending:
        return redirect(url_for("auth.register"))

    # Проверяем не истёк ли код
    if time.time() > pending.get('expires', 0):
        session.pop('pending_register', None)
        flash("Код истёк. Зарегистрируйся заново.", "error")
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        entered = request.form.get("code", "").strip()

        if entered == pending['code']:
            # Код верный — создаём аккаунт
            phone = pending.get('phone', '')
            telegram = pending.get('telegram', '')
            result = create_user(pending['username'], pending['email'], pending['password'], phone, telegram)
            session.pop('pending_register', None)

            if result.get("ok"):
                flash("Аккаунт создан! Войдите в систему.", "success")
                return redirect(url_for("auth.login"))
            else:
                flash(result.get("error", "Ошибка регистрации"), "error")
                return redirect(url_for("auth.register"))
        else:
            flash("Неверный код. Попробуй ещё раз.", "error")

    return render_template("verify_telegram.html", telegram=pending.get('telegram', ''))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect("/")

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = get_user_by_username(username)

        if user and check_password(password, user["password"]):
            session.clear()
            session["user_id"] = user["id"]
            session["lang"] = session.get("lang", "ru")
            update_last_login(user["id"])
            check_and_give_daily_bonus(user["id"])
            return redirect("/")
        else:
            flash("Неверный логин или пароль", "error")

    return render_template("Login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")