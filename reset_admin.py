#!/usr/bin/env python3
"""Удаляем старого admin и создаем нового"""
import sqlite3
import os
import hashlib
import secrets

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'users.db')

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"

def reset_admin():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Удаляем старого admin если есть
    c.execute("DELETE FROM users WHERE username = 'admin'")
    
    # Новые данные
    username = "admin"
    password = "aaaaaa"  # Твой новый пароль
    email = "admin@hacklab.local"
    
    # Создаем нового
    c.execute(
        "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, ?)",
        (username, email.lower(), hash_password(password), 1)
    )
    conn.commit()
    print(f"✅ Admin пересоздан!")
    print(f"   Username: {username}")
    print(f"   Password: {password}")
    
    conn.close()

if __name__ == '__main__':
    reset_admin()
