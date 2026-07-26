#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Fix the f-string backslash issue in ac.py
import re
with open(__file__.replace('_fix.py', 'ac.py'), 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the problematic line
# From: f'本周盘点\n{"━" * 30}\n连续打卡：{streak} 天\n活跃天数：{days_active}/7 天\n'
# To: sep = '━' * 30  then  f'本周盘点\n{sep}\n连续打卡：{streak} 天\n活跃天数：{days_active}/7 天\n'

old_line = '''display = (f'本周盘点\\n{"━" * 30}\\n连续打卡：{streak} 天\\n活跃天数：{days_active}/7 天\\n'''
new_line = '''sep = '━' * 30\ndisplay = (f'本周盘点\\n{sep}\\n连续打卡：{streak} 天\\n活跃天数：{days_active}/7 天\\n'''

if old_line in content:
    content = content.replace(old_line, new_line)
    with open(__file__.replace('_fix.py', 'ac.py'), 'w', encoding='utf-8') as f:
        f.write(content)
    print('fixed')
else:
    print('line not found, checking file...')
    lines = content.split('\\n')
    for i, line in enumerate(lines):
        if 'f-string expression' in line or 'display' in line and '本周盘点' in line:
            print(f'Line {i+1}: {repr(line)}')
    print('done checking')
