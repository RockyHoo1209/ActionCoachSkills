#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ActionCoach Data Layer - CLI tool for rank, plan, state, weekly, config."""
import json, os, sys, datetime, re

# Fix stdout encoding for GBK terminals
if hasattr(sys.stdout, "buffer"):
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

# ── 段位定义 ──
TIER_DEFS = [
    {'key':'bronze','name':'青铜','subs':3,'stars':3,'unlock':'基础教练陪伴','icon':'🥉'},
    {'key':'silver','name':'白银','subs':3,'stars':4,'unlock':'教练开始了解你的习惯','icon':'🥈'},
    {'key':'gold','name':'黄金','subs':4,'stars':4,'unlock':'周报自动生成','icon':'🥇'},
    {'key':'platinum','name':'铂金','subs':4,'stars':5,'unlock':'可兑换深度复盘','icon':'💎'},
    {'key':'diamond','name':'钻石','subs':5,'stars':5,'unlock':'教练分析你的行为模式','icon':'💠'},
    {'key':'star','name':'星耀','subs':5,'stars':5,'unlock':'可获得专属挑战周','icon':'✨'},
    {'key':'king','name':'王者','subs':1,'stars':999,'unlock':'教练为你写月度成长叙事','icon':'👑'},
]
TIER_MAP = {t['key']:t for t in TIER_DEFS}

# ── 星星获取规则 ──
STAR_RULES = [
    {'reason':'daily_done','stars':1,'label':'完成当日计划（至少做了一个 step）'},
    {'reason':'perfect_day','stars':1,'label':'完美日（所有 task 完成）额外 +1'},
    {'reason':'streak_7','stars':3,'label':'连续 7 天打卡'},
    {'reason':'streak_30','stars':10,'label':'连续 30 天打卡'},
    {'reason':'active_review','stars':1,'label':'主动复盘写了感受'},
]
STAR_RULE_MAP = {r['reason']:r for r in STAR_RULES}

# ── 状态机 ──
STATE_MACHINE = {
    'states': ['onboard','active','silent','stuck','done','paused'],
    'initial': 'onboard',
    'transitions': {
        'onboard':{'complete':'active'},
        'active':{'silent_3d':'silent','stuck':'stuck','done':'done','pause':'paused'},
        'silent':{'silent_7d':'paused','return':'active','stuck':'stuck'},
        'stuck':{'unlock':'active','pause':'paused'},
        'done':{'new_goal':'active','pause':'paused'},
        'paused':{'return':'active','reset':'onboard'},
    },
    'labels': {
        'onboard':'引导阶段','active':'活跃（日循环）','silent':'沉默关怀',
        'stuck':'卡住处理','done':'目标完成','paused':'暂停/重来',
    },
}

# ══════════════════════ HELPERS ══════════════════════

def _path(user_id, kind):
    os.makedirs(DATA_DIR, exist_ok=True)
    sid = re.sub(r'[^a-zA-Z0-9_]', '_', str(user_id))
    return os.path.join(DATA_DIR, f'{kind}_{sid}.json')

def _read(path, default=None):
    if default is None: default = {}
    if not os.path.exists(path): return default
    try:
        with open(path,'r',encoding='utf-8') as f: return json.load(f)
    except: return default

def _write(path, data):
    with open(path,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)

def _ok(data=None, display=None):
    r = {'ok':True}
    if data: r['data'] = data
    if display: r['display'] = display
    print(json.dumps(r, ensure_ascii=False))
    sys.exit(0)

def _err(msg):
    print(json.dumps({'ok':False,'error':msg}, ensure_ascii=False))
    sys.exit(1)

def _today(): return datetime.date.today().isoformat()
def _curr_week(): return datetime.date.today().strftime('%Y-W%W')

def _parse_dt(s):
    """Parse ISO datetime string to datetime (Python 3.6 compat)."""
    try:
        return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')
    except ValueError:
        return datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S')

def _parse_week(s):
    m = re.match(r'(\d{4})-W(\d{2})', s)
    if not m: _err('Invalid week format, use YYYY-WNN')
    jan4 = datetime.date(int(m.group(1)),1,4)
    start = jan4 - datetime.timedelta(days=jan4.isoweekday()-1)
    return start + datetime.timedelta(weeks=int(m.group(2))-1)

def _calc_tier(total_stars):
    """从总星星数计算当前段位"""
    needed = []
    for t in TIER_DEFS:
        for sub in range(t['subs'],0,-1):
            needed.append((t['key'], sub, t['stars']))
    idx = 0
    while idx < len(needed) and total_stars >= needed[idx][2]:
        total_stars -= needed[idx][2]
        idx += 1
    if idx >= len(needed):
        return TIER_DEFS[-1]['key'], 0, TIER_DEFS[-1]['stars']
    tier_key, sub_tier, stars_for_this = needed[idx]
    return tier_key, sub_tier, stars_for_this - total_stars if total_stars < stars_for_this else 0
    # return tier_key, sub_tier, stars_needed_to_next

def _calc_tier_v2(total_stars):
    """返回 (tier_key, sub_tier, stars_in_this_sub, stars_needed_for_next)"""
    needed = []
    for t in TIER_DEFS:
        for sub in range(t['subs'],0,-1):
            needed.append((t['key'], sub, t['stars']))
    remaining = total_stars
    current_tier = TIER_DEFS[0]['key']
    current_sub = TIER_DEFS[0]['subs']
    stars_earned_here = 0
    stars_needed = TIER_DEFS[0]['stars']
    for nk, ns, nst in needed:
        if remaining >= nst:
            remaining -= nst
            current_tier, current_sub = nk, ns
            stars_earned_here = nst
            stars_needed = nst
        else:
            current_tier, current_sub = nk, ns
            stars_earned_here = remaining
            stars_needed = nst
            remaining = 0
            break
    if remaining > 0:
        return TIER_DEFS[-1]['key'], 0, remaining, None
    return current_tier, current_sub, stars_earned_here, stars_needed

def _tier_display(tier_key, sub_tier):
    t = TIER_MAP[tier_key]
    if tier_key == 'king':
        return f'{t["icon"]} {t["name"]}'
    sub_names = {3:'III',2:'II',1:'I',5:'V',4:'IV',0:'-',None:'-'}
    sn = sub_names.get(sub_tier, str(sub_tier))
    return f'{t["icon"]} {t["name"]} {sn}'

# ══════════════════════ RANK ══════════════════════

def cmd_rank_query(user_id):
    data = _read(_path(user_id,'rank'), {
        'total_stars':0, 'highest_tier':'bronze','highest_sub':3,
        'streak':0,'longest_streak':0,'last_active':None,
        'protection':0,'history':[],
    })
    ts = data['total_stars']
    tk, sub, earned, needed = _calc_tier_v2(ts)
    td = _tier_display(tk, sub)
    # 本周/本月获取
    today = datetime.date.today()
    ws = today - datetime.timedelta(days=today.weekday())
    ms = today.replace(day=1)
    wk = sum(1 for e in data['history']
             if e.get('type')=='earn' and _parse_dt(e['date']).date() >= ws)
    mo = sum(1 for e in data['history']
             if e.get('type')=='earn' and _parse_dt(e['date']).date() >= ms)
    # 升段所需
    next_info = ''
    if tk != 'king':
        tdef = TIER_MAP[tk]
        needs = needed if needed is not None else tdef['stars']
        next_info = f'还需 {earned}/{needs} 星'
    display_lines = [
        f'当前段位：{td}',
        f'星星总数：{ts}',
        f'本周获得：{wk} 星',
        f'本月获得：{mo} 星',
        f'连续打卡：{data["streak"]} 天',
    ]
    if next_info:
        display_lines.append(f'升段进度：{next_info}')
    if data['protection'] > 0:
        display_lines.append(f'段位保护剩余：{data["protection"]} 天')
    hi = data.get('highest_tier','bronze')
    hs = data.get('highest_sub',3)
    if hi != tk or hs != sub:
        display_lines.append(f'历史最高：{_tier_display(hi,hs)}')
    _ok({
        'tier':tk,'sub_tier':sub,'total_stars':ts,'streak':data['streak'],
        'week_earned':wk,'month_earned':mo,'highest_tier':hi,
        'highest_sub':hs,'protection':data['protection'],
    }, display='\n'.join(display_lines))

def cmd_rank_add_star(user_id, reason, note=None):
    if reason not in STAR_RULE_MAP:
        _err(f'Unknown reason: {reason}')
    rule = STAR_RULE_MAP[reason]
    stars = rule['stars']
    path = _path(user_id,'rank')
    data = _read(path, {
        'total_stars':0,'highest_tier':'bronze','highest_sub':3,
        'streak':0,'longest_streak':0,'last_active':None,
        'protection':0,'history':[],
    })
    old_tk, old_sub, _, _ = _calc_tier_v2(data['total_stars'])
    data['total_stars'] += stars
    data['last_active'] = datetime.datetime.now().isoformat()
    # 更新最高段位
    new_tk, new_sub, _, _ = _calc_tier_v2(data['total_stars'])
    ti_rank = {t['key']:i for i,t in enumerate(TIER_DEFS)}
    if ti_rank.get(new_tk,0) > ti_rank.get(data.get('highest_tier','bronze'),0):
        data['highest_tier'] = new_tk
        data['highest_sub'] = new_sub
        # 升段保护
        data['protection'] = 3
    # 历史记录
    entry = {'type':'earn','reason':reason,'stars':stars,'label':rule['label'],
             'date':datetime.datetime.now().isoformat()}
    if note: entry['note'] = note
    data['history'].append(entry)
    _write(path, data)
    old_disp = _tier_display(old_tk, old_sub)
    new_disp = _tier_display(new_tk, new_sub)
    msg = f'⭐ +{stars} 星 | {rule["label"]}'
    if old_tk != new_tk or old_sub != new_sub:
        msg += f'\n🎉 晋升！{old_disp} → {new_disp}'
    _ok({'added':stars,'total':data['total_stars'],'tier':new_tk,'sub_tier':new_sub}, display=msg)

def cmd_rank_lose_star(user_id, reason, note=None):
    path = _path(user_id,'rank')
    data = _read(path, {
        'total_stars':0,'highest_tier':'bronze','highest_sub':3,
        'streak':0,'longest_streak':0,'last_active':None,
        'protection':0,'history':[],
    })
    old_tk, old_sub, _, _ = _calc_tier_v2(data['total_stars'])
    # 段位保护
    if data['protection'] > 0:
        data['protection'] -= 1
        _write(path, data)
        _ok({'lost':0,'total':data['total_stars'],'protection_used':True},
            display='🛡️ 段位保护生效，本次不掉星')
    if data['total_stars'] <= 0:
        _ok({'lost':0,'total':0}, display='已在最低段位，无法掉星')
    data['total_stars'] -= 1
    entry = {'type':'lose','reason':reason,'stars':1,
             'date':datetime.datetime.now().isoformat()}
    if note: entry['note'] = note
    data['history'].append(entry)
    _write(path, data)
    new_tk, new_sub, _, _ = _calc_tier_v2(data['total_stars'])
    msg = f'💫 -1 星'
    if old_tk != new_tk or old_sub != new_sub:
        old_disp = _tier_display(old_tk, old_sub)
        new_disp = _tier_display(new_tk, new_sub)
        msg += f'\n⚠️ 掉段！{old_disp} → {new_disp}'
    _ok({'lost':1,'total':data['total_stars'],'tier':new_tk,'sub_tier':new_sub}, display=msg)

def cmd_rank_check_demote(user_id, silent_days=3):
    """检查是否应该掉星"""
    path = _path(user_id,'rank')
    data = _read(path, {
        'total_stars':0,'highest_tier':'bronze','highest_sub':3,
        'streak':0,'longest_streak':0,'last_active':None,
        'protection':0,'history':[],
    })
    if data['last_active'] is None:
        _ok({'should_demote':False,'silent_days':0})
    elapsed = (datetime.datetime.now() - _parse_dt(data['last_active'])).days
    should = False
    reason = ''
    if elapsed >= 7:
        should = True
        reason = '连续7天沉默，建议执行掉段'
    elif elapsed >= 3:
        should = True
        reason = f'连续{elapsed}天沉默，建议扣星'
    _ok({'should_demote':should,'silent_days':elapsed,'reason':reason}, display=reason or f'未沉默（{elapsed}天前活跃）')

def cmd_rank_history(user_id, days=30):
    data = _read(_path(user_id,'rank'), {})
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    recent = [e for e in data.get('history',[])
              if _parse_dt(e['date']) >= cutoff]
    _ok({'entries':recent[-50:],'total':len(recent)})

def cmd_rank_update_streak(user_id):
    path = _path(user_id,'rank')
    data = _read(path, {
        'total_stars':0,'highest_tier':'bronze','highest_sub':3,
        'streak':0,'longest_streak':0,'last_active':None,
        'protection':0,'history':[],
    })
    today = _today()
    if data['last_active'] and data['last_active'].startswith(today):
        return
    yesterday = (datetime.date.today()-datetime.timedelta(days=1)).isoformat()
    last = data.get('last_active','')[:10] if data.get('last_active') else None
    if last == today:
        return
    if last == yesterday:
        data['streak'] += 1
    else:
        data['streak'] = 1
    data['last_active'] = datetime.datetime.now().isoformat()
    if data['streak'] > data['longest_streak']:
        data['longest_streak'] = data['streak']
    _write(path, data)

# ══════════════════════ PLAN ══════════════════════

def cmd_plan_create(user_id, date_str, missions_json):
    try: missions = json.loads(missions_json)
    except json.JSONDecodeError as e: _err(f'Invalid JSON: {e}')
    if not isinstance(missions,list) or len(missions)==0: _err('missions must be non-empty array')
    for m in missions:
        if 'mission' not in m or 'steps' not in m: _err('Each mission needs mission+steps fields')
        if not isinstance(m['steps'],list): _err('steps must be array')
    plan = {'user':user_id,'date':date_str,'missions':missions,'completed':[],
            'created_at':datetime.datetime.now().isoformat()}
    _write(_path(user_id,f'plan_{date_str}'), plan)
    _ok({'date':date_str,'total_steps':sum(len(m['steps']) for m in missions),'missions':missions,'completed':[]},
        display=_fmt_plan(plan))

def cmd_plan_check(user_id, date_str, item_str):
    plan = _read(_path(user_id,f'plan_{date_str}'), None)
    if not plan: _err(f'No plan for {user_id} on {date_str}')
    items = _parse_items(item_str, plan)
    if not items: _err(f'Invalid item: {item_str}')
    plan['completed'] = sorted(set(plan['completed']+items))
    _write(_path(user_id,f'plan_{date_str}'), plan)
    just = []; idx=1
    for m in plan['missions']:
        for s in m['steps']:
            if idx in items: just.append(s)
            idx+=1
    total = sum(len(m['steps']) for m in plan['missions'])
    done = len(plan['completed'])
    _ok({'completed_items':items,'done':done,'total':total,'progress':f'{done}/{total}'},
        display=_fmt_plan(plan))

def cmd_plan_get(user_id, date_str):
    plan = _read(_path(user_id,f'plan_{date_str}'), None)
    if not plan: _err(f'No plan for {user_id} on {date_str}')
    total = sum(len(m['steps']) for m in plan['missions'])
    done = len(plan['completed'])
    mp = _mission_progress(plan)
    _ok({'date':date_str,'missions':plan['missions'],'completed':plan['completed'],
        'total_steps':total,'done_steps':done,'progress':f'{done}/{total}','mission_progress':mp},
        display=_fmt_plan(plan))

def _parse_items(s, plan):
    s = s.strip()
    total = sum(len(m['steps']) for m in plan['missions'])
    if s.lower()=='all': return list(range(1,total+1))
    res = []
    for p in re.split(r'[,，、\s]+', s):
        if not p: continue
        m = re.match(r'^(\d+)-(\d+)$', p)
        if m: res.extend(range(int(m.group(1)),int(m.group(2))+1))
        else:
            m = re.match(r'^(\d+)$', p)
            if m and 1<=int(m.group(1))<=total: res.append(int(m.group(1)))
    return sorted(set(res))

def _mission_progress(plan):
    cs = set(plan.get('completed',[])); idx=1; res=[]
    for m in plan['missions']:
        ms = len(m['steps'])
        md = sum(1 for i in range(ms) if (idx+i) in cs)
        res.append({'mission':m['mission'],'done':md,'total':ms,'complete':md==ms})
        idx+=ms
    return res

def _fmt_plan(plan):
    cs = set(plan.get('completed',[]))
    lines = ['\U0001f4cb 今日计划']
    lines.append('\u2501'*30)
    idx=1
    for m in plan['missions']:
        lines.append('')
        lines.append('**'+m['mission']+'**')
        for s in m['steps']:
            mk = '\u2611\ufe0f' if idx in cs else '\u2b1c'
            tx = '~~'+s+'~~\uff08\u5df2\u5b8c\u6210\uff09' if idx in cs else s
            lines.append('  '+mk+' '+str(idx)+'. '+tx)
            idx+=1
    total = sum(len(m['steps']) for m in plan['missions'])
    done = len(plan.get('completed',[]))
    lines.append('')
    lines.append('\u5b8c\u6210\u8fdb\u5ea6\uff1a'+str(done)+'/'+str(total))
    return '\n'.join(lines)

# ══════════════════════ STATE ══════════════════════

def cmd_state_get(user_id):
    data = _read(_path(user_id,'state'),
        {'state':'onboard','silent_days':0,'last_active':None})
    lb = STATE_MACHINE['labels'].get(data['state'], data['state'])
    _ok({'state':data['state'],'label':lb,'silent_days':data.get('silent_days',0),
        'last_active':data.get('last_active')}, display='\u5f53\u524d\u72b6\u6001\uff1a'+lb)

def cmd_state_transition(user_id, event):
    data = _read(_path(user_id,'state'),
        {'state':'onboard','silent_days':0,'last_active':None})
    trans = STATE_MACHINE['transitions'].get(data['state'], {})
    if event not in trans: _err('Cannot transition from '+data['state']+' with '+event)
    old_state = data['state']
    old_lb = STATE_MACHINE['labels'].get(data['state'], data['state'])
    new = trans[event]
    new_lb = STATE_MACHINE['labels'].get(new, new)
    data['state'] = new
    data['silent_days'] = 0
    if event in ('return','complete') or new in ('active',):
        data['last_active'] = datetime.datetime.now().isoformat()
    _write(_path(user_id,'state'), data)
    if new == 'active': cmd_rank_update_streak(user_id)
    _ok({'from':old_state,'to':new,'event':event},
        display='\u72b6\u6001\u5207\u6362\uff1a'+old_lb+'\u2192'+new_lb)

def cmd_state_check_silent(user_id, days=3):
    data = _read(_path(user_id,'state'),
        {'state':'onboard','silent_days':0,'last_active':None})
    if not data.get('last_active'):
        _ok({'silent':False,'silent_days':0}, display='\u7528\u6237\u521a\u521b\u5efa')
    elapsed = (datetime.datetime.now()-_parse_dt(data['last_active'])).days
    data['silent_days'] = elapsed
    _write(_path(user_id,'state'), data)
    msg = ''
    if elapsed>=7 and data['state'] in ('active','silent'):
        msg = '\u7528\u6237\u5df2\u6c89\u9ed8'+str(elapsed)+'\u5929\uff0c\u5efa\u8bae\u8f6c\u5165\u6682\u505c\u6a21\u5f0f'
    elif elapsed>=days and data['state']=='active':
        msg = '\u7528\u6237\u5df2\u6c89\u9ed8'+str(elapsed)+'\u5929\uff0c\u5efa\u8bae\u8f6c\u5165\u5173\u6000\u6a21\u5f0f'
    else:
        msg = '\u7528\u6237\u672a\u6c89\u9ed8\uff08\u4e0a\u6b21\u6d3b\u8dc3\uff1a'+str(elapsed)+'\u5929\u524d\uff09'
    _ok({'silent':elapsed>=days,'silent_days':elapsed,'state':data['state']}, display=msg)

# ══════════════════════ WEEKLY ══════════════════════

def cmd_weekly_calc(user_id, week_str):
    start = _parse_week(week_str)
    days = [(start+datetime.timedelta(days=i)).isoformat() for i in range(7)]
    plans = [_read(_path(user_id,f'plan_{d}'), None) for d in days]
    plans = [p for p in plans if p]
    if not plans: _err('\u672c\u5468\u6ca1\u6709\u8ba1\u5212\u6570\u636e')
    ts = ds = best_rate = days_active = 0
    best_day = None
    for plan in plans:
        t = sum(len(m['steps']) for m in plan['missions'])
        d = len(plan.get('completed',[]))
        ts+=t; ds+=d
        rate = d/t if t else 0
        if d>0: days_active+=1
        if rate>best_rate: best_rate,best_day=rate,plan['date']
    overall = round(ds/ts*100) if ts else 0
    rd = _read(_path(user_id,'rank'), {})
    streak = rd.get('streak',0)
    sep = '\u2501'*30
    lines = [
        '\u672c\u5468\u76d8\u70b9',
        sep,
        '\u8fde\u7eed\u6253\u5361\uff1a'+str(streak)+' \u5929',
        '\u6d3b\u8dc3\u5929\u6570\uff1a'+str(days_active)+'/7 \u5929',
        '\u5b8c\u6210\u7387\uff1a'+str(overall)+'%',
        '\u5b8c\u6210\u8fdb\u5ea6\uff1a'+str(ds)+'/'+str(ts),
        '\u6700\u4f73\u4e00\u5929\uff1a'+str(best_day or '\u65e0'),
        '',
        '\u4e0b\u5468\u60f3\u8c03\u6574\u4ec0\u4e48\uff1f',
        '[\u52a0\u70b9\u91cf] [\u51cf\u70b9\u91cf] [\u8c03\u6574\u65b9\u5f0f] [\u4e0d\u53d8]',
    ]
    _ok({'week':week_str,'days_active':days_active,'total_steps':ts,
        'done_steps':ds,'completion_rate':overall,'best_day':best_day,'streak':streak},
        display='\n'.join(lines))

# ══════════════════════ CONFIG ══════════════════════

def cmd_config_set(user_id, key, value):
    data = _read(_path(user_id,'config'), {})
    data[key] = value
    data['updated_at'] = datetime.datetime.now().isoformat()
    _write(_path(user_id,'config'), data)
    _ok({key:value}, display='\u914d\u7f6e\u5df2\u66f4\u65b0\uff1a'+key+' = '+value)

def cmd_config_get(user_id, key=None):
    data = _read(_path(user_id,'config'), {})
    if key:
        if key not in data: _err('Key not found: '+key)
        _ok({key:data[key]}, display=key+': '+str(data[key]))
    _ok(data, display=json.dumps(data,ensure_ascii=False,indent=2))

# ══════════════════════ CLI ══════════════════════

VERSION = "1.0.0"

def cmd_version():
    _ok({
        "script": "ac.py",
        "version": VERSION,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "data_dir": DATA_DIR,
    }, display=f"ActionCoach Data Layer v{VERSION}\nPython {sys.version.split()[0]} on {sys.platform}\nData: {DATA_DIR}")

def cmd_check():
    """Verify environment is ready for ActionCoach."""
    issues = []
    if sys.version_info < (3, 6):
        issues.append("Python 3.6+ required")
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        tf = os.path.join(DATA_DIR, ".write_test")
        with open(tf, "w") as f: f.write("ok")
        os.remove(tf)
    except Exception as e:
        issues.append(f"Cannot write to data dir: {e}")
    missing = []
    for mod in ["json", "os", "sys", "datetime", "re"]:
        try: __import__(mod)
        except: missing.append(mod)
    if missing: issues.append(f"Missing stdlib modules: {missing}")
    _ok({
        "ok": len(issues) == 0,
        "issues": issues,
        "version": VERSION,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "data_dir": DATA_DIR,
    }, display="\n".join(issues) if issues else f"ActionCoach v{VERSION} ready on {sys.platform}")

def main():
    if len(sys.argv)<2: _err(f"Usage: python {os.path.basename(__file__)} <command>")
    cmd = sys.argv[1]
    if cmd in ("--version", "version"): cmd_version()
    elif cmd in ("--check", "check"): cmd_check()
    args = sys.argv[2:]
    cmd = sys.argv[1]; args = sys.argv[2:]
    def parse(a):
        kw={}; i=0
        while i<len(a):
            if a[i].startswith('--'):
                k=a[i][2:]
                if i+1<len(a) and not a[i+1].startswith('--'): kw[k]=a[i+1]; i+=2
                else: kw[k]=True; i+=1
            else: i+=1
        return kw
    kw=parse(args); user=kw.get('user')

    if cmd=='rank' and len(args)>0:
        s=args[0]
        if not user: _err('--user required')
        if s=='query': cmd_rank_query(user)
        elif s=='add-star': cmd_rank_add_star(user, kw.get('reason'), kw.get('note'))
        elif s=='lose-star': cmd_rank_lose_star(user, kw.get('reason'), kw.get('note'))
        elif s=='check-demote': cmd_rank_check_demote(user, int(kw.get('days',3)))
        elif s=='history': cmd_rank_history(user, int(kw.get('days',30)))
        elif s=='update-streak': cmd_rank_update_streak(user)
        else: _err('Unknown rank sub: '+s)

    elif cmd=='plan' and len(args)>0:
        s=args[0]; dt=kw.get('date',_today())
        if not user: _err('--user required')
        if s=='create':
            if not kw.get('missions'): _err('--missions required')
            cmd_plan_create(user, dt, kw['missions'])
        elif s=='check':
            if not kw.get('item'): _err('--item required')
            cmd_plan_check(user, dt, kw['item'])
        elif s=='get': cmd_plan_get(user, dt)
        else: _err('Unknown plan sub: '+s)

    elif cmd=='state' and len(args)>0:
        s=args[0]
        if not user: _err('--user required')
        if s=='get': cmd_state_get(user)
        elif s=='transition':
            if not kw.get('event'): _err('--event required')
            cmd_state_transition(user, kw['event'])
        elif s=='check-silent': cmd_state_check_silent(user, int(kw.get('days',3)))
        else: _err('Unknown state sub: '+s)

    elif cmd=='weekly' and len(args)>0:
        s=args[0]
        if not user: _err('--user required')
        if s=='calc': cmd_weekly_calc(user, kw.get('week',_curr_week()))
        else: _err('Unknown weekly sub: '+s)

    elif cmd=='config' and len(args)>0:
        s=args[0]
        if not user: _err('--user required')
        if s=='set':
            if not kw.get('key') or kw.get('value') is None: _err('--key and --value required')
            cmd_config_set(user, kw['key'], kw['value'])
        elif s=='get': cmd_config_get(user, kw.get('key'))
        else: _err('Unknown config sub: '+s)

    else: print(__doc__)

if __name__=='__main__':
    main()
