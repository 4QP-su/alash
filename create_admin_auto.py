#!/usr/bin/env python3
"""Создаем админ аккаунт автоматически"""
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
    
    # Дефолтные значения
    username = "admin"
    password = "aaaaaa"
    email = "admin@hacklab.local"
    
    try:
        c.execute(
            "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
            (username, email.lower(), hash_password(password), 1)
        )
        conn.commit()
        print(f"✅ Admin создан!")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Email: {email}")
    except sqlite3.IntegrityError:
        print(f"⚠️ Admin '{username}' уже существует")
    finally:
        conn.close()

if __name__ == '__main__':
    create_admin()
