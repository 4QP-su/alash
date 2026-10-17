#!/usr/bin/env python3
"""Migration script to create admin panel tables."""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join('data', 'users.db')

def migrate():
    """Create admin tables."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create announcements table
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

    # Create system_settings table
    c.execute('''
     CREATE TABLE IF NOT EXISTS system_settings (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TEXT DEFAULT (datetime('now'))
     )
    ''')

    # Create activity_logs table
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
    print('✓ Admin tables created successfully')

if __name__ == '__main__':
    migrate()
