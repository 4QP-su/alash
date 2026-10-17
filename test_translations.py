#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json

# Load and check files
with open('app/translations/ui_ru.json', 'r', encoding='utf-8') as f:
    ru_data = json.load(f)

with open('app/translations/ui_kz.json', 'r', encoding='utf-8') as f:
    kz_data = json.load(f)

print("✓ Файлы загружены успешно!")
print(f"  RU: {len(ru_data)} ключей")
print(f"  KZ: {len(kz_data)} ключей")

# Count by module
ru_modules = {
    'sql': sum(1 for k in ru_data.keys() if k.startswith('sql_')),
    'xss': sum(1 for k in ru_data.keys() if k.startswith('xss_')),
    'csrf': sum(1 for k in ru_data.keys() if k.startswith('csrf_')),
    'path': sum(1 for k in ru_data.keys() if k.startswith('path_')),
    'auth': sum(1 for k in ru_data.keys() if k.startswith('auth_')),
}

kz_modules = {
    'sql': sum(1 for k in kz_data.keys() if k.startswith('sql_')),
    'xss': sum(1 for k in kz_data.keys() if k.startswith('xss_')),
    'csrf': sum(1 for k in kz_data.keys() if k.startswith('csrf_')),
    'path': sum(1 for k in kz_data.keys() if k.startswith('path_')),
    'auth': sum(1 for k in kz_data.keys() if k.startswith('auth_')),
}

print("\nРусский:")
for mod, count in ru_modules.items():
    print(f"  {mod.upper()}: {count} ключей")

print("\nКазахский:")
for mod, count in kz_modules.items():
    print(f"  {mod.upper()}: {count} ключей")

# Sample check
print("\n[ Примеры переводов ]")
print(f"  ru['xss_theory_h1'] = {ru_data.get('xss_theory_h1', 'MISSING')}")
print(f"  ru['csrf_theory_h1'] = {ru_data.get('csrf_theory_h1', 'MISSING')}")
print(f"  ru['path_theory_h1'] = {ru_data.get('path_theory_h1', 'MISSING')}")
print(f"  ru['auth_theory_h1'] = {ru_data.get('auth_theory_h1', 'MISSING')}")
