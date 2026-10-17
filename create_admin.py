#!/usr/bin/env python3
"""Создаем админ аккаунт"""
import sqlite3
import os
import hashlib
import secrets

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'users.db')

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def create_admin():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    username = input("Admin username: ").strip()
    password = input("Admin password: ").strip()
    email = input("Admin email: ").strip()
    
    try:
        c.execute(
            "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
            (username, email.lower(), hash_password(password), 1)
        )
        conn.commit()
        print(f"✅ Admin '{username}' создан!")
    except sqlite3.IntegrityError as e:
        print(f"❌ Ошибка: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    create_admin()
