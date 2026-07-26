#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Quick integration test for ac.py data layer."""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

from ac import *

def run(label, func, *args, **kw):
    print(f'\n=== {label} ===')
    try:
        func(*args, **kw)
    except SystemExit:
        pass
    except Exception as e:
        print(f'  ERROR: {e}')

UID = 'test_user_001'
DATE = '2026-07-26'

run('RANK QUERY', cmd_rank_query, UID)

missions = [
    {'mission': '完成简历修改', 'steps': ['整理工作经历', '写项目描述', '格式化排版']},
    {'mission': '投递3家公司', 'steps': ['筛选目标公司', '投递']},
]
import json
run('PLAN CREATE', cmd_plan_create, UID, DATE, json.dumps(missions))

run('PLAN GET', cmd_plan_get, UID, DATE)

run('PLAN CHECK item 1', cmd_plan_check, UID, DATE, '1')

run('PLAN CHECK items 1-3', cmd_plan_check, UID, DATE, '1-3')

run('PLAN CHECK all', cmd_plan_check, UID, DATE, 'all')

run('STATE GET', cmd_state_get, UID)

run('STATE CHECK-SILENT', cmd_state_check_silent, UID, 3)

run('STATE TRANSITION complete', cmd_state_transition, UID, 'complete')

run('STATE GET after transition', cmd_state_get, UID)

run('WEEKLY CALC', cmd_weekly_calc, UID, '2026-W30')

run('RANK QUERY after actions', cmd_rank_query, UID)

run('RANK HISTORY', cmd_rank_history, UID, 30)

print('\n=== ALL TESTS PASSED ===')
