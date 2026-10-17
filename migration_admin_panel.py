#!/usr/bin/env python3
"""
Complete migration script for admin panel enhancement.
Handles all necessary file replacements and updates.
"""

import shutil
import os
import re
from datetime import datetime

def backup_file(filepath):
    """Create backup of file."""
    if os.path.exists(filepath):
        backup_path = f"{filepath}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(filepath, backup_path)
        print(f"✓ Backed up: {filepath} → {backup_path}")
        return True
    return False

def replace_admin_route():
    """Replace admin.py routes with enhanced version."""
    src = 'app/routes/admin_new.py'
    dst = 'app/routes/admin.py'
    
    if os.path.exists(src):
        backup_file(dst)
        shutil.move(src, dst)
        print(f"✓ Replaced admin routes: {dst}")
        return True
    return False

def replace_admin_template():
    """Replace admin.html template with enhanced version."""
    src = 'templates/admin_enhanced.html'
    dst = 'templates/admin.html'
    
    if os.path.exists(src):
        backup_file(dst)
        shutil.move(src, dst)
        print(f"✓ Replaced admin template: {dst}")
        return True
    return False

def update_models_init_db():
    """Update models.py to call _ensure_admin_tables."""
    filepath = 'app/models.py'
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already updated
    if '_ensure_admin_tables()' in content:
        print("✓ models.py already has _ensure_admin_tables() call")
        return True
    
    # Add call to _ensure_admin_tables
    backup_file(filepath)
    content = content.replace(
        '  _ensure_user_columns()',
        '  _ensure_user_columns()\n  _ensure_admin_tables()'
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✓ Updated models.py to call _ensure_admin_tables()")
    return True

def create_admin_tables():
    """Create admin tables in database."""
    import sqlite3
    
    db_path = os.path.join('data', 'users.db')
    
    if not os.path.exists(db_path):
        print("⚠ Database not found yet, will be created on first app run")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
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
        print(f"✓ Created admin tables in database")
        return True
    except Exception as e:
        print(f"✗ Error creating admin tables: {e}")
        return False

def cleanup_temp_files():
    """Remove temporary migration files."""
    temp_files = [
        'app/routes/admin_new.py',
        'templates/admin_enhanced.html',
        'migrate_admin_tables.py',
        'fix_models.py',
        'replace_admin.py',
    ]
    
    for filepath in temp_files:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"✓ Cleaned up: {filepath}")

def main():
    print("=" * 60)
    print("Admin Panel Enhancement Migration")
    print("=" * 60)
    
    steps = [
        ("Update models.py", update_models_init_db),
        ("Replace admin routes", replace_admin_route),
        ("Replace admin template", replace_admin_template),
        ("Create admin tables", create_admin_tables),
    ]
    
    success_count = 0
    for step_name, step_func in steps:
        try:
            print(f"\n▶ {step_name}...")
            if step_func():
                success_count += 1
            else:
                print(f"⚠ {step_name} - skipped or already done")
        except Exception as e:
            print(f"✗ {step_name} - Error: {e}")
    
    print(f"\n▶ Cleaning up temporary files...")
    cleanup_temp_files()
    
    print("\n" + "=" * 60)
    print(f"✓ Migration complete! ({success_count}/{len(steps)} steps)")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review changes in backed up files if needed")
    print("2. Run: python run.py")
    print("3. Access admin panel at: /internal/system/console/v2")
    print("=" * 60)

if __name__ == '__main__':
    main()
