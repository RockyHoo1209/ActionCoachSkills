#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成示例评论数据，用于测试 analyze_reviews.py 分析管道。
运行: python scripts/generate_sample_data.py
输出: data/reviews/sample_comments.jsonl
"""

import json
import random
import time
from datetime import datetime, timedelta

random.seed(42)

# 模拟真实评论 —— 覆盖拖延、自律、教练、成长、内耗等主题
SAMPLE_COMMENTS = [
    # === 拖延与行动障碍 ===
    "每次想做正事就开始拖延，刷手机刷到半夜然后自责，第二天又重复，怎么打破这个循环",
    "拖延症晚期患者求拯救，明明知道该做什么就是不想动",
    "我也总是拖延，看了很多方法都没用，感觉需要有人盯着我才能动起来",
    "拖延不是懒，是完美主义在作祟，怕做不好所以不开始",
    "道理都懂就是做不到，说的就是我本人了",
    "做计划的时候激情满满，执行的时候各种理由推脱，我太难了",
    "拖延的背后是恐惧，害怕失败所以迟迟不开始",

    # === 自律与习惯 ===
    "坚持早起30天了，感觉整个人都不一样了，自律真的能改变人生",
    "自律打卡第100天，从一个摆烂的人变成现在的自己，感谢那个没放弃的我",
    "有没有人一起打卡互相监督，一个人真的坚持不下去",
    "习惯养成真的好难，前21天简直要命，但熬过去就好了",
    "每天进步一点点，三个月回头看真的被自己惊讶到",
    "找一个搭子一起自律真的很重要，互相监督比一个人坚持容易太多了",
    "自律不是靠意志力，是靠环境和习惯，把目标融入日常",

    # === 教练方法与关系 ===
    "好的教练真的像一面镜子，让你看清自己看不到的盲区",
    "教练不是在给你答案，而是在帮你问对的问题",
    "遇到了一个很好的教练，她总是不评判我，只是耐心地听我说然后问我问题",
    "教练和心理咨询师的区别是什么？感觉教练更注重行动和未来",
    "AI教练真的能替代真人教练吗？感觉少了那种被理解的感觉",
    "一个好的coach真的能改变你的人生轨迹，感恩",
    "找教练有用吗？价格不便宜但确实帮我突破了瓶颈",

    # === 情绪与内耗 ===
    "精神内耗太严重了，一天下来什么都没做却累得要死",
    "焦虑到失眠，感觉所有人都在前进只有我停在原地",
    "允许自己停下来也是一种能力，我花了很久才学会",
    "接纳自己的不完美才是治愈的开始",
    "每天被焦虑裹挟，明明很努力还是觉得不够好",
    "内耗的本质是自我攻击，学会对自己温柔一点",
    "抑郁情绪来的时候什么都不想做，这个时候不逼自己才是对的",

    # === 目标与计划 ===
    "目标定了很多次都半途而废，现在学会了把大目标拆成小步骤",
    "SMART原则真的有用，目标要具体可衡量才有执行力",
    "不会做计划怎么办，每次计划都做得太满然后完不成更挫败",
    "有没有好用的目标管理工具推荐，想要一个能每天提醒我的",
    "计划不用太完美，完成比完美更重要",
    "每天三个最重要的事，做完就收工，这个方法让我不再焦虑",
    "从年目标倒推到日计划，这个方法帮我实现了年度flag",

    # === 自我接纳与成长 ===
    "成长就是接纳自己的普通然后依然努力",
    "最近最大的成长是学会了对自己说没关系，慢慢来",
    "人的改变真的是从接纳开始的，越抗拒越痛苦",
    "不要等到准备好了再开始，先做了再说，路是走出来的",
    "人生没有白走的路，每一步都算数",
    "25岁之后开始觉醒，原来爱自己才是所有改变的基础",
    "允许自己做自己，允许别人做别人",

    # === 价值与价格 ===
    "教练课程太贵了，一个月几千块真的负担不起",
    "有没有性价比高的教练推荐，想要被监督又不想花太多钱",
    "免费的东西往往最贵，好的服务值得付费",
    "如果有一个AI教练每天在微信里提醒我打卡，我愿意付费",
    "花了钱才更珍惜，免费的课程根本不会听完",
]

def make_comment(content, base_ts, idx):
    like = random.choices(
        [0, 1, 3, 5, 10, 20, 50, 100, 500, 1000, 5000],
        weights=[30, 25, 15, 10, 7, 5, 3, 2, 1.5, 1, 0.5],
        k=1
    )[0]
    sub_count = random.choices([0, 1, 2, 3, 5, 10, 20], weights=[40, 25, 15, 10, 5, 3, 2], k=1)[0]
    ts = base_ts + random.randint(0, 86400000)  # 同一天内随机偏移

    return {
        "comment_id": f"sample_{idx:06d}",
        "create_time": ts,
        "note_id": f"note_{random.randint(100000, 999999)}",
        "content": content,
        "creator_hash": f"user_{random.randint(1, 200):04d}",
        "nickname": f"用户{random.randint(100, 999)}***",
        "sub_comment_count": str(sub_count),
        "pictures": "",
        "parent_comment_id": "" if random.random() > 0.3 else f"parent_{random.randint(1, 500):06d}",
        "last_modify_ts": ts + random.randint(0, 3600000),
        "like_count": str(like),
    }

def main():
    # 生成 3 个月跨度的数据
    start_date = datetime(2026, 5, 1)
    records = []

    for day_offset in range(90):
        day_ts = int((start_date + timedelta(days=day_offset)).timestamp() * 1000)
        # 每天生成 5-15 条评论
        daily_count = random.randint(5, 15)
        for i in range(daily_count):
            content = random.choice(SAMPLE_COMMENTS)
            # 偶尔加一些随机变化
            if random.random() < 0.2:
                content += " " + random.choice(["共勉", "加油", "说的太对了", "收藏了", "同感"])
            records.append(make_comment(content, day_ts, len(records)))

    # 追加一些高赞评论
    high_like_contents = [
        "拖延的根源不是懒，是恐惧。怕做不好、怕被评价、怕失败。教练帮我看到的这一点，改变了我的人生。",
        "一个好的教练就像一面镜子，不评判不指责，只是温柔地让你看见自己。遇见她之后我才真正开始改变。",
        "每天在群里打卡坚持了200天，从一个重度拖延症变成了行动派。不是因为我意志力变强了，而是因为我有了 accountability partner。",
        "自律不是苦行僧，而是对自己的人生有掌控感。当你开始行动，焦虑自然就消失了。",
        "内耗是可以停止的。第一步就是允许自己不完美，允许自己慢慢来。",
    ]
    for content in high_like_contents:
        for _ in range(3):
            ts = int((start_date + timedelta(days=random.randint(0, 89))).timestamp() * 1000)
            rec = make_comment(content, ts, len(records))
            rec["like_count"] = str(random.randint(500, 8000))
            records.append(rec)

    # 打乱顺序
    random.shuffle(records)

    import os
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reviews")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "sample_comments.jsonl")

    with open(out_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"生成 {len(records)} 条示例评论 → {out_path}")

if __name__ == "__main__":
    main()
