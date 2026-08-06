#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ActionCoach 评论数据分析引擎
============================
从 JSONL 格式的社交媒体评论中提取用户需求洞察，
用于优化 ActionCoach SKILL.md 的教练能力。

用法：
    python scripts/analyze_reviews.py --input-dir ./data/reviews --output-dir ./output

依赖：numpy, pandas, jieba (标准库以外)
"""

import os
import re
import json
import math
import argparse
from datetime import datetime, timezone, timedelta
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import jieba
import jieba.analyse

# ============================================================
# 1. 中文情感词典（基于通用情感词汇 + 教练场景扩展）
# ============================================================

POSITIVE_WORDS = set([
    # 通用正面
    "好", "棒", "赞", "爱", "喜欢", "开心", "快乐", "幸福", "满意",
    "感谢", "谢谢", "感动", "温暖", "有用", "有效", "成功", "坚持",
    "进步", "成长", "改变", "突破", "自信", "勇气", "力量", "希望",
    "帮助", "收获", "值得", "推荐", "受益", "启发", "触动", "共鸣",
    "轻松", "舒服", "自由", "释放", "解压", "鼓励", "支持", "信任",
    "专业", "靠谱", "实用", "清晰", "简单", "方便", "精准", "深度",
    # 教练场景正面
    "自律", "行动", "打卡", "目标", "完成", "做到", "实现", "达成",
    "早起", "规律", "习惯", "动力", "能量", "积极", "向上", "治愈",
    "温柔", "坚定", "接纳", "允许", "看见", "懂得", "理解", "陪伴",
    "觉察", "觉醒", "悟了", "通了", "醒了", "新我", "蜕变", "重生",
])

NEGATIVE_WORDS = set([
    # 通用负面
    "差", "烂", "糟", "坏", "烦", "累", "痛", "苦", "哭", "丧",
    "讨厌", "恶心", "失望", "生气", "愤怒", "焦虑", "恐惧", "害怕",
    "紧张", "压力", "崩溃", "绝望", "无聊", "疲惫", "厌倦", "疲倦",
    "浪费", "骗人", "没用", "无效", "失败", "放弃", "挣扎", "煎熬",
    "恶心", "糟糕", "后悔", "上当", "不值", "垃圾", "无语", "无奈",
    # 教练/成长场景负面
    "拖延", "懒", "废", "颓", "丧", "躺平", "摆烂", "摆", "混",
    "自律失败", "破罐破摔", "自暴自弃", "内耗", "拧巴", "纠结",
    "迷茫", "困惑", "困惑", "混乱", "无力", "无助", "脆弱", "孤独",
    "空虚", "麻木", "机械", "重复", "停滞", "卡住", "瓶颈", "平台",
    "焦虑症", "抑郁", "emo", "破防", "压力大", "扛不住", "受不了",
    "做不到", "坚持不了", "半途而废", "三分钟热度", "三天打鱼",
])

INTENSIFIERS = set(["很", "太", "非常", "特别", "极其", "无比", "超级", "十分", "好", "真", "真的", "实在"])


def simple_sentiment_score(text):
    """基于词典的中文情感评分，返回 (score, pos_count, neg_count)"""
    words = jieba.lcut(text)
    pos_count = sum(1 for w in words if w in POSITIVE_WORDS)
    neg_count = sum(1 for w in words if w in NEGATIVE_WORDS)
    # 简单的强度词加权
    intensifier_count = sum(1 for w in words if w in INTENSIFIERS)
    score = (pos_count - neg_count) * (1 + 0.3 * intensifier_count)
    return score, pos_count, neg_count


def classify_sentiment(score):
    if score > 1.5:
        return "positive"
    elif score < -1.5:
        return "negative"
    else:
        return "neutral"


# ============================================================
# 2. 用户需求主题体系（教练场景）
# ============================================================

# 主题关键词映射 —— 将 jieba 分词结果归类到教练相关主题
TOPIC_KEYWORDS = {
    "拖延与行动障碍": [
        "拖延", "懒", "不想动", "行动", "启动", "开始", "执行力",
        "拖", "等等", "明天", "下次", "迟迟", "迈不出", "第一步",
        "三分钟热度", "半途而废", "坚持不了", "坚持不下去",
    ],
    "目标与计划": [
        "目标", "计划", "规划", "设定", "制定", "分解", "拆解",
        "todo", "待办", "清单", "日程", "安排", "优先级", "排期",
        "里程碑", "阶段", "步骤", "路径", "路线图", "方向",
    ],
    "自律与习惯": [
        "自律", "习惯", "打卡", "早起", "作息", "规律", "日常",
        "routine", "坚持", "连续", "每天", "每日", "习惯养成",
    ],
    "情绪与内耗": [
        "焦虑", "内耗", "拧巴", "纠结", "迷茫", "焦虑症", "emo",
        "压力", "疲惫", "无力", "空虚", "烦躁", "心烦", "不安",
        "恐惧", "害怕", "担心", "紧张", "崩溃", "抑郁", "低落",
    ],
    "自我接纳与成长": [
        "接纳", "允许", "看见", "觉察", "觉醒", "疗愈", "治愈",
        "成长", "改变", "蜕变", "突破", "进步", "重生", "新我",
        "和解", "放下", "释怀", "原谅", "爱自己", "自信", "勇气",
    ],
    "教练方法与关系": [
        "教练", "coach", "指导", "引导", "提问", "倾听", "反馈",
        "陪伴", "支持", "鼓励", "监督", " accountability", "问责",
        "镜子", "反映", "照见", "对话", "沟通", "信任", " rapport",
    ],
    "效率与工具": [
        "效率", "工具", "方法", "技巧", "模板", "框架", "系统",
        "app", "软件", "笔记", "记录", "追踪", "跟踪", "衡量",
        "复盘", "总结", "反思", "review", "回顾", "分析",
    ],
    "价值与价格": [
        "贵", "价格", "付费", "免费", "值", "不值", "性价比",
        "收费", "报名", "课程", "学费", "投资", "值得", "划算",
    ],
}


def detect_topics(words, topic_map=None):
    """对分词结果检测所属主题，返回 topic -> matched_keywords 映射"""
    if topic_map is None:
        topic_map = TOPIC_KEYWORDS
    topics = defaultdict(list)
    for w in words:
        w_lower = w.lower()
        for topic, keywords in topic_map.items():
            if w_lower in keywords or any(kw in w_lower for kw in keywords if len(kw) > 1):
                topics[topic].append(w)
    return dict(topics)


# ============================================================
# 3. 用户画像推断
# ============================================================

SEGMENT_SIGNALS = {
    "拖延挣扎型": {
        "keywords": ["拖延", "懒", "不想动", "拖", "等等", "明天再说",
                     "坚持不了", "半途而废", "三分钟热度", "启动困难"],
        "description": "知道该做什么但迟迟不开始，在拖延-自责循环中挣扎",
    },
    "习惯崩盘型": {
        "keywords": ["习惯", "打卡", "自律失败", "坚持不了", "三天打鱼",
                     "routine", "早起失败", "作息乱", "放弃", "又断了"],
        "description": "尝试过多次建立习惯但总是中断，需要外部监督和轻推",
    },
    "方向迷茫型": {
        "keywords": ["迷茫", "不知道", "方向", "困惑", "选择", "意义",
                     "目标", "找不到", "该做什么", "何去何从"],
        "description": "不是不想做，而是不知道做什么，需要厘清目标",
    },
    "情绪内耗型": {
        "keywords": ["焦虑", "内耗", "emo", "压力", "崩溃", "抑郁",
                     "拧巴", "纠结", "疲惫", "无力", "低能量"],
        "description": "被情绪消耗大量能量，需要先处理情绪再处理事情",
    },
    "积极成长型": {
        "keywords": ["成长", "改变", "进步", "突破", "蜕变", "觉醒",
                     "自律成功", "收获", "心得体会", "学到了"],
        "description": "已经在路上，需要更深度的陪伴和更高阶的指导",
    },
    "教练学习者": {
        "keywords": ["教练", "coach", "学教练", "教", "方法", "技术",
                     "培训", "认证", "督导", "教练技术"],
        "description": "想成为教练或学习教练方法，而非被教练",
    },
}


def infer_segments(words):
    """基于评论内容推断用户所属的潜在画像"""
    scores = {}
    for seg_name, seg_info in SEGMENT_SIGNALS.items():
        score = sum(1 for w in words if w in seg_info["keywords"])
        if score > 0:
            scores[seg_name] = score
    return scores


# ============================================================
# 4. 核心分析类
# ============================================================

class ReviewAnalyzer:
    def __init__(self, input_dir=".", output_dir="output"):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.df = None
        self.analysis = {}

    def load_data(self):
        """加载所有 JSONL 文件"""
        jsonl_files = list(self.input_dir.glob("*.jsonl"))
        if not jsonl_files:
            print(f"[!] 在 {self.input_dir} 中未找到 .jsonl 文件")
            # 也找子目录
            jsonl_files = list(self.input_dir.rglob("*.jsonl"))

        records = []
        for fpath in sorted(jsonl_files):
            print(f"  读取: {fpath.name} ({fpath.stat().st_size / 1024:.1f} KB)")
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

        self.df = pd.DataFrame(records)
        print(f"  共加载 {len(self.df)} 条评论，来自 {len(jsonl_files)} 个文件")
        return self

    def preprocess(self):
        """数据预处理"""
        df = self.df
        if df is None or df.empty:
            raise ValueError("无数据，请先调用 load_data()")

        # 时间戳处理
        if "create_time" in df.columns:
            df["create_dt"] = pd.to_datetime(df["create_time"], unit="ms", errors="coerce")
            df["create_date"] = df["create_dt"].dt.date
            df["create_hour"] = df["create_dt"].dt.hour
            df["create_month"] = df["create_dt"].dt.month

        # 缺失值填充
        df["content"] = df.get("content", "").fillna("")
        df["like_count"] = pd.to_numeric(df.get("like_count", 0), errors="coerce").fillna(0)
        df["sub_comment_count"] = pd.to_numeric(df.get("sub_comment_count", 0), errors="coerce").fillna(0)

        # 内容长度
        df["content_len"] = df["content"].apply(len)

        # 分词 + 分析
        print("  对评论进行中文分词...")
        df["words"] = df["content"].apply(lambda x: jieba.lcut(str(x)) if x else [])
        df["word_count"] = df["words"].apply(len)

        print("  计算情感得分...")
        sentiments = df["content"].apply(simple_sentiment_score)
        df["sentiment_score"] = sentiments.apply(lambda x: x[0])
        df["sentiment_pos"] = sentiments.apply(lambda x: x[1])
        df["sentiment_neg"] = sentiments.apply(lambda x: x[2])
        df["sentiment"] = df["sentiment_score"].apply(classify_sentiment)

        print("  检测主题分布...")
        df["topics"] = df["words"].apply(detect_topics)

        print("  推断用户画像...")
        df["segments"] = df["words"].apply(infer_segments)

        self.df = df
        return self

    def analyze(self):
        """执行多维度分析"""
        df = self.df
        analysis = {}

        # ---- 4.1 基本统计 ----
        analysis["basic_stats"] = {
            "total_comments": len(df),
            "unique_users": df["creator_hash"].nunique() if "creator_hash" in df.columns else 0,
            "unique_notes": df["note_id"].nunique() if "note_id" in df.columns else 0,
            "total_likes": int(df["like_count"].sum()),
            "avg_likes": float(df["like_count"].mean()),
            "avg_content_len": float(df["content_len"].mean()),
            "avg_word_count": float(df["word_count"].mean()),
            "date_range": (
                str(df["create_dt"].min()) if "create_dt" in df.columns else "N/A",
                str(df["create_dt"].max()) if "create_dt" in df.columns else "N/A",
            ),
        }

        # ---- 4.2 高频关键词 ----
        all_words = [w for words in df["words"] for w in words if len(w) > 1]
        word_freq = Counter(all_words)
        # 过滤停用词
        stop_words = set(["的", "了", "是", "在", "我", "有", "和", "就", "不", "人",
                          "都", "一", "一个", "也", "要", "可以", "这个", "那个",
                          "会", "很", "到", "去", "能", "做", "说", "没有", "吗",
                          "吧", "呢", "啊", "呀", "哦", "嗯", "哈", "嘛",
                          "什么", "怎么", "为什么", "因为", "所以", "但是", "如果",
                          "就是", "还是", "不是", "只是", "但是", "而且", "虽然",
                          "已经", "可能", "应该", "需要", "觉得", "感觉", "看到",
                          "知道", "真的", "有点", "一些", "这么", "那么", "这样",
                          "用", "被", "把", "对", "从", "以", "让", "这", "那"])
        top_words = [(w, c) for w, c in word_freq.most_common(100) if w not in stop_words][:50]
        analysis["top_keywords"] = top_words

        # ---- 4.3 主题分布 ----
        topic_counter = Counter()
        topic_word_map = defaultdict(list)
        for _, row in df.iterrows():
            for topic, matched in row["topics"].items():
                topic_counter[topic] += len(matched)
                topic_word_map[topic].extend(matched)

        analysis["topic_distribution"] = {
            topic: {
                "count": count,
                "pct": round(count / max(sum(topic_counter.values()), 1) * 100, 1),
                "top_words": [w for w, _ in Counter(topic_word_map[topic]).most_common(10)],
            }
            for topic, count in topic_counter.most_common()
        }

        # ---- 4.4 情感分布 ----
        sentiment_dist = df["sentiment"].value_counts()
        analysis["sentiment_distribution"] = {
            str(k): {"count": int(v), "pct": round(float(v) / len(df) * 100, 1)}
            for k, v in sentiment_dist.items()
        }
        analysis["avg_sentiment_score"] = float(df["sentiment_score"].mean())

        # ---- 4.5 情感 × 主题 交叉分析 ----
        topic_sentiment = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "total": 0})
        for _, row in df.iterrows():
            for topic in row["topics"]:
                topic_sentiment[topic][row["sentiment"]] += 1
                topic_sentiment[topic]["total"] += 1

        analysis["topic_sentiment_cross"] = {
            topic: {
                "positive_pct": round(s["positive"] / max(s["total"], 1) * 100, 1),
                "negative_pct": round(s["negative"] / max(s["total"], 1) * 100, 1),
                "neutral_pct": round(s["neutral"] / max(s["total"], 1) * 100, 1),
                "total": s["total"],
            }
            for topic, s in sorted(topic_sentiment.items(), key=lambda x: x[1]["total"], reverse=True)
        }

        # ---- 4.6 用户画像分布 ----
        segment_counter = Counter()
        for segs in df["segments"]:
            for seg in segs:
                segment_counter[seg] += 1

        analysis["user_segment_distribution"] = {
            seg: {
                "count": count,
                "pct": round(count / max(sum(segment_counter.values()), 1) * 100, 1),
                "description": SEGMENT_SIGNALS.get(seg, {}).get("description", ""),
            }
            for seg, count in segment_counter.most_common()
        }

        # ---- 4.7 高赞评论分析（最有价值的信号） ----
        high_likes = df.nlargest(30, "like_count")
        analysis["top_liked_comments"] = []
        for _, row in high_likes.iterrows():
            content = str(row["content"])[:200]
            analysis["top_liked_comments"].append({
                "content": content,
                "likes": int(row["like_count"]),
                "sentiment": row["sentiment"],
                "topics": list(row["topics"].keys()) if row["topics"] else [],
                "segments": list(row["segments"].keys()) if row["segments"] else [],
            })

        # ---- 4.8 时间趋势（按日） ----
        if "create_date" in df.columns:
            daily_stats = df.groupby("create_date").agg(
                count=("content", "count"),
                avg_sentiment=("sentiment_score", "mean"),
                total_likes=("like_count", "sum"),
            ).reset_index()
            daily_stats["create_date"] = daily_stats["create_date"].astype(str)
            analysis["daily_trend"] = daily_stats.to_dict("records")

        # ---- 4.9 热门讨论话题（基于高频词共现） ----
        # 找同时出现的多个关键词组合 (bigrams of keywords)
        key_words_set = set(w for w, _ in top_words[:30])
        bigram_counter = Counter()
        for words in df["words"]:
            kw_in_comment = [w for w in words if w in key_words_set and w not in stop_words]
            for i in range(len(kw_in_comment) - 1):
                for j in range(i + 1, min(i + 4, len(kw_in_comment))):
                    pair = tuple(sorted([kw_in_comment[i], kw_in_comment[j]]))
                    if pair[0] != pair[1]:
                        bigram_counter[pair] += 1

        analysis["keyword_cooccurrence"] = [
            {"pair": list(p), "count": c}
            for p, c in bigram_counter.most_common(30)
        ]

        self.analysis = analysis
        return self

    def generate_report(self):
        """生成结构化的分析报告"""
        a = self.analysis
        report = []

        report.append("=" * 60)
        report.append("ActionCoach 评论数据分析报告")
        report.append("=" * 60)

        # 基本统计
        bs = a["basic_stats"]
        report.append(f"\n## 一、数据概览")
        report.append(f"  总评论数:   {bs['total_comments']}")
        report.append(f"  独立用户:   {bs['unique_users']}")
        report.append(f"  独立笔记:   {bs['unique_notes']}")
        report.append(f"  总点赞数:   {bs['total_likes']:,}")
        report.append(f"  平均点赞:   {bs['avg_likes']:.1f}")
        report.append(f"  平均字数:   {bs['avg_content_len']:.0f}")
        report.append(f"  时间范围:   {bs['date_range'][0][:10]} ~ {bs['date_range'][1][:10]}")

        # 情感分布
        report.append(f"\n## 二、情感分布")
        for sent, info in a["sentiment_distribution"].items():
            bar = "█" * int(info["pct"] / 2) + "░" * (50 - int(info["pct"] / 2))
            report.append(f"  {sent:>8}: {bar} {info['pct']:.1f}% ({info['count']})")
        report.append(f"  平均情感得分: {a['avg_sentiment_score']:.2f} (-5~+5)")

        # 主题分布
        report.append(f"\n## 三、讨论主题分布")
        for topic, info in a["topic_distribution"].items():
            bar = "█" * int(info["pct"] / 2) + "░" * (50 - int(info["pct"] / 2))
            report.append(f"  {topic}: {bar} {info['pct']:.1f}%")
            top_kw = ", ".join(info["top_words"][:6])
            report.append(f"    └ 典型词: {top_kw}")

        # 主题 × 情感 交叉
        report.append(f"\n## 四、主题-情感交叉分析（发现风险与机会）")
        report.append(f"  {'主题':<16} {'正面':>8} {'负面':>8} {'中性':>8} {'总量':>6}")
        report.append(f"  {'-'*50}")
        for topic, info in a["topic_sentiment_cross"].items():
            report.append(f"  {topic:<16} {info['positive_pct']:>7.1f}% {info['negative_pct']:>7.1f}% "
                          f"{info['neutral_pct']:>7.1f}% {info['total']:>6}")

        # 用户画像分布
        report.append(f"\n## 五、用户画像倾向分布")
        for seg, info in a["user_segment_distribution"].items():
            bar = "█" * int(info["pct"] / 2) + "░" * (50 - int(info["pct"] / 2))
            report.append(f"  {seg:<12}: {bar} {info['pct']:.1f}%")
            report.append(f"    └ {info['description']}")

        # 热门关键词
        report.append(f"\n## 六、高频关键词 Top 30")
        for i, (w, c) in enumerate(a["top_keywords"][:30], 1):
            report.append(f"  {i:>2}. {w:<8} ({c})")

        # 关键词共现 Top 15
        report.append(f"\n## 七、关键词共现（发现需求关联）")
        for item in a["keyword_cooccurrence"][:15]:
            report.append(f"  {' + '.join(item['pair']):<20} → {item['count']} 次同时出现")

        # 高赞评论（最有价值的信号）
        report.append(f"\n## 八、高赞评论精选（潜在需求信号）")
        report.append(f"  {'='*60}")
        for i, c in enumerate(a["top_liked_comments"][:15], 1):
            content_short = c["content"][:120]
            report.append(f"\n  [{i}] ❤️ {c['likes']} | [{c['sentiment']}]")
            report.append(f"      {content_short}")
            if c["topics"]:
                report.append(f"      主题: {', '.join(c['topics'])}")
            if c["segments"]:
                report.append(f"      画像: {', '.join(c['segments'])}")

        # Actionable Insights
        report.append(f"\n## 九、对 ActionCoach 的需求洞察与建议")
        self._generate_insights(report, a)

        return "\n".join(report)

    def _generate_insights(self, report, a):
        """基于分析数据生成教练产品洞察"""
        report.append(f"  {'='*60}")

        # 1. 最强烈的需求信号
        top_topic = a["topic_distribution"]
        if top_topic:
            top_3 = list(top_topic.keys())[:3]
            report.append(f"\n  【需求热度 Top 3】")
            for i, t in enumerate(top_3, 1):
                info = top_topic[t]
                report.append(f"    {i}. {t} ({info['pct']:.1f}%)")
                report.append(f"      典型诉求: {', '.join(info['top_words'][:5])}")

        # 2. 负面情绪高发的主题（风险点）
        neg_topics = [
            (t, info) for t, info in a["topic_sentiment_cross"].items()
            if info["negative_pct"] > 20
        ]
        if neg_topics:
            report.append(f"\n  【风险警告 - 高负面情绪主题】")
            for t, info in sorted(neg_topics, key=lambda x: x[1]["negative_pct"], reverse=True):
                report.append(f"    ⚠️ {t}: {info['negative_pct']:.1f}% 负面")
                report.append(f"      这是用户痛点最集中的领域，教练技能应优先回应")

        # 3. 用户画像推荐优先级
        segs = a["user_segment_distribution"]
        if segs:
            top_seg = list(segs.keys())[0] if segs else "N/A"
            report.append(f"\n  【核心用户画像】")
            report.append(f"    占比最高: {top_seg}")
            report.append(f"    → ActionCoach 应优先优化对此类用户的回应策略")

        # 4. 关键词共现中的需求组合
        cooc = a["keyword_cooccurrence"]
        if cooc:
            top_pair = cooc[0]["pair"]
            report.append(f"\n  【需求关联发现】")
            report.append(f"    「{' + '.join(top_pair)}」是最常被同时提及的需求组合")
            report.append(f"    → 教练技能应设计覆盖这个需求组合的对话流程")

        # 5. 对比现有 Persona 的覆盖缺口
        report.append(f"\n  【画像覆盖检查】")
        existing_personas = ["拖延挣扎型", "习惯崩盘型", "方向迷茫型", "情绪内耗型", "积极成长型"]
        if segs:
            found = [s for s in existing_personas if s in segs]
            missing = [s for s in existing_personas if s not in segs]
            report.append(f"    数据中已确认: {', '.join(found) if found else '无'}")
            report.append(f"    数据中未发现: {'、'.join(missing) if missing else '无'}")
            extra = [s for s in segs if s not in existing_personas]
            if extra:
                report.append(f"    新发现的画像类型: {'、'.join(extra)}")
                report.append(f"    → 建议在 SKILL.md 中补充对这些用户类型的支持")

        # 6. 对 SKILL.md 的优化方向
        report.append(f"\n  【SKILL.md 优化建议】")
        report.append(f"    1. 在 Step 1 目标澄清阶段，增加对「{list(a['topic_distribution'].keys())[0] if a['topic_distribution'] else '核心需求'}」主题的引导提问")
        report.append(f"    2. 针对高频负面情绪主题，设计专门的「情绪接纳」对话分支")
        report.append(f"    3. 根据画像分布调整每日推送的 tone —— 对主力画像做个性化")

    def export_json(self, path=None):
        """导出分析结果为 JSON"""
        if path is None:
            path = self.output_dir / "analysis_result.json"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 转换不可序列化的类型
        def serialize(obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.ndarray,)):
                return obj.tolist()
            if isinstance(obj, pd.Timestamp):
                return str(obj)
            return obj

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.analysis, f, ensure_ascii=False, indent=2, default=serialize)
        print(f"\n分析结果已导出: {path}")
        return self

    def export_report(self, path=None):
        """导出可读报告为 txt"""
        if path is None:
            path = self.output_dir / "analysis_report.txt"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        report_text = self.generate_report()
        with open(path, "w", encoding="utf-8") as f:
            f.write(report_text)
        print(f"可读报告已导出: {path}")
        return self

    def export_data_with_tags(self, path=None):
        """导出带标签的增强数据为 CSV"""
        if path is None:
            path = self.output_dir / "comments_with_tags.csv"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        df_out = self.df[["content", "sentiment", "sentiment_score", "like_count",
                          "sub_comment_count", "content_len", "create_time"]].copy()
        df_out["topics"] = df_out.index.map(
            lambda i: ",".join(self.df.iloc[i]["topics"].keys()) if self.df.iloc[i]["topics"] else "")
        df_out["segments"] = df_out.index.map(
            lambda i: ",".join(self.df.iloc[i]["segments"].keys()) if self.df.iloc[i]["segments"] else "")

        # 限制内容长度以免 CSV 过大
        df_out["content"] = df_out["content"].apply(lambda x: str(x)[:500])
        df_out.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"带标签数据已导出: {path}")
        return self

    def run_all(self):
        """一键执行全流程"""
        print("=" * 50)
        print("ActionCoach 评论数据分析引擎")
        print("=" * 50)
        print("\n[1/5] 加载数据...")
        self.load_data()

        print("\n[2/5] 预处理 & 分词...")
        self.preprocess()

        print("\n[3/5] 多维分析...")
        self.analyze()

        print("\n[4/5] 生成报告...")
        self.export_report()
        self.export_json()
        self.export_data_with_tags()

        print("\n[5/5] 分析完成！")
        # 打印报告摘要
        report = self.generate_report()
        # 提取关键部分
        lines = report.split("\n")
        for line in lines:
            if any(kw in line for kw in ["需求热度 Top", "风险警告", "核心用户画像",
                                         "需求关联发现", "画像覆盖检查", "SKILL.md 优化",
                                         "一、数据概览", "二、情感分布", "三、讨论主题"]):
                print(line)
        print(f"\n完整报告: {self.output_dir / 'analysis_report.txt'}")


def main():
    parser = argparse.ArgumentParser(description="ActionCoach 评论数据分析引擎")
    parser.add_argument("--input-dir", default="./data/reviews",
                        help="存放 JSONL 评论文件的目录 (默认: ./data/reviews)")
    parser.add_argument("--output-dir", default="./output/analysis",
                        help="分析结果输出目录 (默认: ./output/analysis)")
    args = parser.parse_args()

    analyzer = ReviewAnalyzer(input_dir=args.input_dir, output_dir=args.output_dir)
    analyzer.run_all()


if __name__ == "__main__":
    main()
