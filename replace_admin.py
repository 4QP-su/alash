#!/usr/bin/env python3
"""Replace admin.py with the new enhanced version."""

import shutil
import os

src = 'app/routes/admin_new.py'
dst = 'app/routes/admin.py'
backup = 'app/routes/admin.py.bak'

# Backup original
if os.path.exists(dst):
    shutil.copy(dst, backup)
    print(f"✓ Backed up original to {backup}")

# Replace with new
shutil.copy(src, dst)
print(f"✓ Replaced {dst} with enhanced version")

# Clean up temp file
os.remove(src)
print(f"✓ Cleaned up {src}")
