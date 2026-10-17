#!/usr/bin/env python3
"""Update init_db to call _ensure_admin_tables."""

import re

with open('app/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find _ensure_user_columns() call in init_db and add _ensure_admin_tables() after it
pattern = r'(_ensure_user_columns\(\))'
replacement = r'\1\n  _ensure_admin_tables()'

if pattern in content:
    print("Pattern found")
    content = re.sub(pattern, replacement, content, count=1)
    with open('app/models.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Updated init_db to call _ensure_admin_tables()")
else:
    # Try a different search
    if '_ensure_user_columns()' in content:
        content = content.replace('  _ensure_user_columns()', '  _ensure_user_columns()\n  _ensure_admin_tables()', 1)
        with open('app/models.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✓ Updated init_db to call _ensure_admin_tables()")
    else:
        print("Could not find _ensure_user_columns() call")
