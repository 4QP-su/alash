import os
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Настройки Gmail из .env ────────────────────────────────────
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', 'default@gmail.com')
SMTP_PASS = os.getenv('SMTP_PASS', 'xxxx')


def generate_code(length: int = 6) -> str:
    """Генерирует случайный цифровой код."""
    return ''.join(random.choices(string.digits, k=length))


def send_verification_email(to_email: str, code: str) -> bool:
    """
    Отправляет письмо с кодом подтверждения.
    Возвращает True если успешно, False при ошибке.
    """
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'HACKLAB // КОД ПОДТВЕРЖДЕНИЯ: {code}'
    msg['From']    = f'HackLab <{SMTP_USER}>'
    msg['To']      = to_email

    # Plain text версия
    text = f"""
HACKLAB_OS v2.6 // VERIFICATION REQUIRED

Твой код подтверждения: {code}

Введи его на странице регистрации.
Код действителен 10 минут.

Если ты не регистрировался — просто проигнорируй письмо.
"""

    # HTML версия (в стиле терминала)
    html = f"""
<!DOCTYPE html>
<html>
<body style="background:#0a0a0a; color:#00ff88; font-family:'Courier New',monospace; padding:40px;">
  <div style="max-width:420px; margin:0 auto; border:1px solid #00ff88; padding:32px;">
    <div style="font-size:11px; color:#444; margin-bottom:20px;">
      HACKLAB_OS v2.6 // VERIFICATION_REQUIRED
    </div>
    <h2 style="color:#00ff88; letter-spacing:3px; margin-bottom:24px;">EMAIL VERIFY</h2>
    <p style="color:#888; margin-bottom:16px;">Твой код подтверждения:</p>
    <div style="font-size:36px; letter-spacing:12px; color:#00ff88; 
                border:1px solid #333; padding:20px; text-align:center;
                background:#111; margin-bottom:24px;">
      {code}
    </div>
    <p style="color:#555; font-size:12px;">// Код действителен 10 минут</p>
    <p style="color:#333; font-size:11px; margin-top:20px;">
      Если ты не регистрировался в HackLab — просто проигнорируй письмо.
    </p>
  </div>
</body>
</html>
"""

    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f'[email_sender] Ошибка отправки: {e}')
        return False