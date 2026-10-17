import os
import random
import string
import requests

# ── Настройки SMS провайдера из .env ───────────────────────────
SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'smsc')  # smsc, twilio, smsru, telegram

# Telegram (бесплатно через бота)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# SMSC.ru (Россия/СНГ)
SMSC_LOGIN = os.getenv('SMSC_LOGIN', '')
SMSC_PASSWORD = os.getenv('SMSC_PASSWORD', '')

# Twilio (Международный)
TWILIO_SID = os.getenv('TWILIO_SID', '')
TWILIO_TOKEN = os.getenv('TWILIO_TOKEN', '')
TWILIO_FROM = os.getenv('TWILIO_FROM', '')  # номер в формате +1234567890

# SMS.ru (Россия)
SMSRU_API_ID = os.getenv('SMSRU_API_ID', '')


def generate_code(length: int = 6) -> str:
    """Генерирует случайный цифровой код."""
    return ''.join(random.choices(string.digits, k=length))


def _send_smsc(phone: str, message: str) -> bool:
    """Отправка через SMSC.kz (Казахстан)"""
    try:
        url = "https://smsc.kz/sys/send.php"
        params = {
            'login': SMSC_LOGIN,
            'psw': SMSC_PASSWORD,
            'phones': phone,
            'mes': message,
            'fmt': 3,  # JSON формат
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        print(f'[phone_sender] SMSC.kz response: {data}')
        return 'error' not in data and data.get('id', 0) > 0
    except Exception as e:
        print(f'[phone_sender] SMSC.kz error: {e}')
        return False


def _send_twilio(phone: str, message: str) -> bool:
    """Отправка через Twilio"""
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
        auth = (TWILIO_SID, TWILIO_TOKEN)
        data = {
            'From': TWILIO_FROM,
            'To': phone,
            'Body': message,
        }
        resp = requests.post(url, data=data, auth=auth, timeout=10)
        return resp.status_code == 201
    except Exception as e:
        print(f'[phone_sender] Twilio error: {e}')
        return False


def _send_smsru(phone: str, message: str) -> bool:
    """Отправка через SMS.ru"""
    try:
        url = "https://sms.ru/sms/send"
        params = {
            'api_id': SMSRU_API_ID,
            'to': phone,
            'msg': message,
            'json': 1,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        return data.get('status') == 'OK'
    except Exception as e:
        print(f'[phone_sender] SMS.ru error: {e}')
        return False


def send_verification_sms(phone: str, code: str) -> bool:
    """
    Отправляет SMS с кодом подтверждения.
    Возвращает True если успешно, False при ошибке.
    """
    message = f"HACKLAB: Код подтверждения: {code}. Действителен 10 минут."
    
    # Нормализуем номер (убираем лишние символы)
    phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    if SMS_PROVIDER == 'smsc':
        return _send_smsc(phone, message)
    elif SMS_PROVIDER == 'twilio':
        return _send_twilio(phone, message)
    elif SMS_PROVIDER == 'smsru':
        return _send_smsru(phone, message)
    else:
        print(f'[phone_sender] Неизвестный провайдер: {SMS_PROVIDER}')
        return False


def normalize_phone(phone: str) -> str:
    """Нормализует номер телефона к формату +7XXXXXXXXXX (РФ и Казахстан)"""
    digits = ''.join(c for c in phone if c.isdigit())
    
    # Если номер уже с +7 (11 цифр начинается с 7)
    if len(digits) == 11 and digits[0] == '7':
        return '+' + digits
    # Если номер начинается с 8 и 11 цифр — заменяем на +7
    if len(digits) == 11 and digits[0] == '8':
        return '+7' + digits[1:]
    # Если номер без кода страны (10 цифр) — добавляем +7
    elif len(digits) == 10:
        return '+7' + digits
    # Если уже с + — возвращаем как есть
    elif phone.startswith('+') and len(digits) >= 10:
        return phone
    
    return phone


def is_valid_phone(phone: str) -> bool:
    """Проверяет формат номера телефона"""
    digits = ''.join(c for c in phone if c.isdigit())
    # Минимум 10 цифр (без кода страны), максимум 15 (с кодом)
    return 10 <= len(digits) <= 15


# ── Telegram верификация (бесплатно) ───────────────────────────

def normalize_telegram(username: str) -> str:
    """Нормализует Telegram username (убирает @ если есть)"""
    username = username.strip()
    if username.startswith('@'):
        username = username[1:]
    return username.lower()


def is_valid_telegram(username: str) -> bool:
    """Проверяет формат Telegram username (5-32 символа, a-z, 0-9, _)"""
    username = normalize_telegram(username)
    if len(username) < 5 or len(username) > 32:
        return False
    return username.replace('_', '').replace('.', '').isalnum()


def _find_chat_id_by_username(username: str) -> int | None:
    """Ищет chat_id по username через getUpdates"""
    try:
        url = f"{TELEGRAM_API_URL}/getUpdates"
        resp = requests.get(url, timeout=10)
        updates = resp.json()
        
        if not updates.get('ok'):
            return None
            
        username_lower = username.lower()
        
        # Ищем в обновлениях
        for update in reversed(updates.get('result', [])):
            msg = update.get('message', {})
            chat = msg.get('chat', {})
            chat_username = chat.get('username', '').lower()
            
            if chat_username == username_lower:
                return chat.get('id')
                
        return None
    except Exception as e:
        print(f'[phone_sender] Error finding chat_id: {e}')
        return None


def send_verification_telegram(username: str, code: str) -> bool:
    """
    Отправляет код подтверждения в Telegram.
    Возвращает True если успешно, False при ошибке.
    """
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'your_bot_token_here':
        print('[phone_sender] TELEGRAM_BOT_TOKEN не настроен')
        return False
    
    username = normalize_telegram(username)
    message = f"🔐 *HACKLAB Verification*\n\nКод подтверждения: `{code}`\n\nДействителен 10 минут."
    
    try:
        # Сначала ищем chat_id по username
        chat_id = _find_chat_id_by_username(username)
        
        if not chat_id:
            print(f'[phone_sender] Не найден chat_id для @{username}')
            print('[phone_sender] Пользователь должен написать /start боту @hckr_sbot')
            return False
        
        url = f"{TELEGRAM_API_URL}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown',
        }
        resp = requests.post(url, json=data, timeout=10)
        result = resp.json()
        
        if result.get('ok'):
            print(f'[phone_sender] Код отправлен @{username} (ID: {chat_id})')
            return True
        else:
            error = result.get('description', 'Unknown error')
            print(f'[phone_sender] Telegram error: {error}')
            return False
            
    except Exception as e:
        print(f'[phone_sender] Telegram request error: {e}')
        return False
