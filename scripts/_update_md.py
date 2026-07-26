#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Update SKILL.md: replace Points System with Rank/Tier System."""
import sys
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)

import re

P = r'D:\work\ActionCoachSkills\SKILL.md'
with open(P, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Simple line replacements
content = content.replace('今日预计积分：60 + 完成奖励', '今日预计：完成所有任务可升阶')
content = content.replace('完成进度：1/5 | 已得积分：10', '完成进度：1/5 | 今日可获：1 ⭐')
content = content.replace('积分减半', '星星减半')

# 2. Build the new section
NEW = (
    '## 段位系统（Rank System）\n\n'
    '段位系统取代了传统积分体系，灵感来自《王者荣耀》的排位机制。用户的持续行动转化为⭐⭐，⭐⭐积累推动段位晋升，让成长路径清晰可见。段位不是排行榜，而是你专属的成长轨迹。\n\n'
    '### 脚本化数据层\n'
    '所有段位、计划、状态、周报数据由 `scripts/ac.py` 管理，SKILL.md 只定义触发逻辑。详细脚本命令见 [脚本化分析.md](docs/脚本化分析.md)。\n\n'
    '### 段位与晋升规则\n\n'
    '| 段位 | 图标 | 子段位 | 每级所需⭐⭐ | 解锁能力 |\n'
    '|---|---|---|---|---|\n'
    '| 青铜 | 🥉 | 3 | 3 | 基础教练陪伴 |\n'
    '| 白银 | 🥈 | 3 | 4 | 教练开始了解你的习惯 |\n'
    '| 黄金 | 🥇 | 4 | 4 | 周报自动生成 |\n'
    '| 铂金 | 🏵️ | 4 | 5 | 可兑换深度复盘 |\n'
    '| 钻石 | 💎 | 5 | 5 | 教练分析你的行为模式 |\n'
    '| 星耀 | ⭐ | 5 | 5 | 可获得专属挑战周 |\n'
    '| 王者 | 👑 | 1 | ∞ | 教练为你写月度成长史诗 |\n\n'
    '### ⭐获取规则\n\n'
    '| 行动 | ⭐ | 说明 |\n'
    '|---|---|---|\n'
    '| 完成当日计划（至少做了一个 step） | 1 | 早安计划中有勾选即可 |\n'
    '| 完美日（所有 task 完成）额外 +1 | 1 | 今天的全部计划都打勾 |\n'
    '| 连续 7 天打卡 | 3 | 连续 7 天完成当日计划 |\n'
    '| 连续 30 天打卡 | 10 | 月度里程碑 |\n'
    '| 主动复盘写了感受 | 1 | 晚间复盘时写了内容 |\n\n'
    '### 特殊机制\n\n'
    '- **段位保护**：晋升到新段位后，有 3 天保护期，期间不会掉⭐\n'
    '- **沉默掉⭐**：连续 3-7 天无互动会触发掉⭐，保护期可抵消一次\n'
    '- **最高段位记录**：历史最高段位永久保留，即使掉段也不消失\n'
    '- **款式加成**：RPG 款式下⭐⭐获取翻倍（因为⭐⭐本身就是游戏经验值）\n\n'
    '### 段位查看\n\n'
    '用户随时说"我的段位"或"我的⭐⭐" → 教练显示当前段位和获取记录\n\n'
    '```\n'
    '+------------------------------------+\n'
    '| 你的段位                            |\n'
    '|                                    |\n'
    '| 当前段位：🥉 青铜 III              |\n'
    '| ⭐⭐总数：12                       |\n'
    '| 本周获得：4 ⭐                     |\n'
    '| 本月获得：12 ⭐                    |\n'
    '| 连续打卡：🔥 5 天                  |\n'
    '| 升段进度：还需 2/4 ⭐              |\n'
    '| 历史最高：🏵️ 铂金 II              |\n'
    '|                                    |\n'
    '| 段位特权已解锁：                    |\n'
    '| 🥇 周报自动生成                    |\n'
    '+------------------------------------+\n'
    '```\n\n'
    '后台操作（由执行 Agent 调用 `scripts/ac.py`）：\n'
    '- 查询段位：`python scripts/ac.py rank query --user {user_id}`\n'
    '- 加⭐⭐：`python scripts/ac.py rank add-star --user {user_id} --reason {reason}`\n'
    '- 扣⭐⭐：`python scripts/ac.py rank lose-star --user {user_id} --reason {reason}`\n'
    '- 检查沉默降⭐：`python scripts/ac.py rank check-demote --user {user_id}`\n'
    '- 更新连续打卡：`python scripts/ac.py rank update-streak --user {user_id}`\n'
    '- 查看历史：`python scripts/ac.py rank history --user {user_id}`\n\n'
    '### 段位系统的设计哲学\n\n'
    '段位在 ActionCoach 里的角色是**成长路径，不是排名**：\n\n'
    '1. **视觉化进步** — 从青铜到王者，用户看到自己的成长轨迹，而不是抽象的数字\n'
    '2. **段位保护解决"怕断"的焦虑** — 用户知道即使某天必须休息，也有保护期兜底\n'
    '3. **解锁机制解决"看不到进步"** — 每个新段位都解锁新的教练能力（周报、深度复盘、成长报告）\n'
    '4. **历史最高段位解决"挫败感"** — 即使某段时间状态不好掉段，历史最高段位永远保留\n'
    '5. **段位比积分更有叙事感** — "我是黄金"比"我有 500 分"更有身份认同和成就感\n\n'
    '段位系统确保了：**用户越坚持，教练关系越深，段位越高，而不是越坚持越无聊。**\n'
)

# 3. Replace the old section
idx = content.find('## 积分系统（Points System）')
if idx >= 0:
    end_idx = content.find('\n---\n', idx)
    if end_idx < 0:
        end_idx = len(content)
    content = content[:idx] + NEW + content[end_idx:]
    print('OK: section replaced')
else:
    print('FAIL: section not found')

with open(P, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done. 积分 count:', content.count('积分'))
