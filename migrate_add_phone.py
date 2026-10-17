#!/usr/bin/env python3
"""Миграция: добавляем колонку phone в таблицу users"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Проверяем какие таблицы существуют
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in c.fetchall()]
    print(f"Найдены таблицы: {tables}")
    
    if 'users' not in tables:
        print("❌ Таблица users не существует! Нужно пересоздать базу.")
        conn.close()
        return False
    
    # Проверяем есть ли колонка phone
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    print(f"Колонки в users: {columns}")
    
    if 'phone' not in columns:
        print("Добавляю колонку phone...")
        c.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        conn.commit()
        print("✅ Колонка phone добавлена!")
    else:
        print("Колонка phone уже существует")
    
    conn.close()
    return True

if __name__ == '__main__':
    migrate()
    