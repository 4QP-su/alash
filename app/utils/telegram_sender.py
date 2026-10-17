"""Telegram бот для отправки кодов верификации"""
import os
import requests
import random
import string

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def generate_code(length: int = 6) -> str:
    """Генерирует случайный цифровой код."""
    return ''.join(random.choices(string.digits, k=length))


def normalize_username(username: str) -> str:
    """Нормализует username (убирает @ если есть)"""
    username = username.strip()
    if username.startswith('@'):
        username = username[1:]
    return username.lower()


def is_valid_username(username: str) -> bool:
    """Проверяет формат username (5-32 символа, a-z, 0-9, _)"""
    username = normalize_username(username)
    if len(username) < 5 or len(username) > 32:
        return False
    return username.replace('_', '').isalnum()


def send_verification_code(username: str, code: str) -> bool:
    """
    Отправляет код подтверждения в Telegram.
    Возвращает True если успешно, False при ошибке.
    """
    if not TELEGRAM_BOT_TOKEN:
        print('[telegram_sender] TELEGRAM_BOT_TOKEN не настроен')
        return False
    
    username = normalize_username(username)
    message = f"🔐 *HACKLAB Verification*\n\nКод подтверждения: `{code}`\n\nДействителен 10 минут."
    
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        data = {
            'chat_id': f"@{username}",
            'text': message,
            'parse_mode': 'Markdown',
        }
        resp = requests.post(url, json=data, timeout=10)
        result = resp.json()
        
        if result.get('ok'):
            print(f'[telegram_sender] Код отправлен @{username}')
            return True
        else:
            error = result.get('description', 'Unknown error')
            print(f'[telegram_sender] Telegram error: {error}')
            return False
            
    except Exception as e:
        print(f'[telegram_sender] Request error: {e}')
        return False


def check_bot_working() -> bool:
    """Проверяет что бот работает и токен валиден"""
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        url = f"{TELEGRAM_API_URL}/getMe"
        resp = requests.get(url, timeout=5)
        return resp.json().get('ok', False)
    except:
        return False
