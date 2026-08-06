#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ActionCoach 评论分析结果可视化
==============================
读取 analyze_reviews.py 输出的 JSON，生成带图表的 HTML 报告。

用法:
    python scripts/visualize_analysis.py \
        --input output/analysis/analysis_result.json \
        --output output/analysis/report.html

依赖: matplotlib, numpy, json, base64, io
"""

import json
import base64
import io
import os
import argparse
from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# ---------- 中文字体 ----------
def _find_chinese_font():
    candidates = [
        "Microsoft YaHei", "SimHei",
        "Noto Sans CJK SC", "Source Han Sans CN",
        "PingFang SC", "Hiragino Sans GB",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            return name
    for f in fm.fontManager.ttflist:
        if any(kw in f.name.lower() for kw in ["yahei", "simhei", "noto", "cjk"]):
            return f.name
    return None

CN_FONT = _find_chinese_font()
if CN_FONT:
    plt.rcParams["font.sans-serif"] = [CN_FONT, "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


# ---------- 绘图辅助 ----------
def _fig_to_base64(fig, dpi=150):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor="white")
    buf.seek(0)
    data = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return data


def plot_sentiment_pie(data):
    sd = data.get("sentiment_distribution", {})
    labels_map = {"positive": "正面", "neutral": "中性", "negative": "负面"}
    colors_map = {"positive": "#4CAF50", "negative": "#F44336", "neutral": "#9E9E9E"}
    labels, sizes, colors = [], [], []
    for sent in ["positive", "neutral", "negative"]:
        if sent in sd:
            labels.append(labels_map[sent])
            sizes.append(sd[sent]["count"])
            colors.append(colors_map[sent])
    fig, ax = plt.subplots(figsize=(5, 4))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.1f%%",
        colors=colors, startangle=90,
        textprops={"fontsize": 11},
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontweight("bold")
    ax.set_title("评论情感分布", fontsize=14, fontweight="bold", pad=15)
    return _fig_to_base64(fig)


def plot_topic_bar(data):
    td = data.get("topic_distribution", {})
    items = sorted(td.items(), key=lambda x: x[1]["count"], reverse=True)
    topics = [t for t, _ in items]
    values = [v["count"] for _, v in items]
    pcts = [v["pct"] for _, v in items]
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(topics)))
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(range(len(topics)), values, color=colors[::-1])
    ax.set_yticks(range(len(topics)))
    ax.set_yticklabels(topics, fontsize=10)
    ax.set_xlabel("评论数", fontsize=11)
    ax.set_title("讨论主题分布", fontsize=14, fontweight="bold", pad=15)
    ax.invert_yaxis()
    mx = max(values) if values else 1
    for bar, val, pct in zip(bars, values, pcts):
        ax.text(bar.get_width() + mx*0.01,
                bar.get_y() + bar.get_height()/2,
                f"  {val} ({pct}%)", va="center", fontsize=9)
    return _fig_to_base64(fig)


def plot_segment_bar(data):
    sd = data.get("user_segment_distribution", {})
    items = sorted(sd.items(), key=lambda x: x[1]["count"], reverse=True)
    segs = [s for s, _ in items]
    counts = [v["count"] for _, v in items]
    colors = plt.cm.Oranges(np.linspace(0.3, 0.9, len(segs)))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(range(len(segs)), counts, color=colors[::-1])
    ax.set_yticks(range(len(segs)))
    ax.set_yticklabels(segs, fontsize=9)
    ax.set_xlabel("提及次数", fontsize=11)
    ax.set_title("用户画像倾向分布", fontsize=14, fontweight="bold", pad=15)
    ax.invert_yaxis()
    mx = max(counts) if counts else 1
    for bar, val in zip(bars, counts):
        ax.text(bar.get_width() + mx*0.01,
                bar.get_y() + bar.get_height()/2,
                f"  {val}", va="center", fontsize=9)
    return _fig_to_base64(fig)


def plot_topic_sentiment_heatmap(data):
    tsc = data.get("topic_sentiment_cross", {})
    if not tsc:
        return None
    topics = list(tsc.keys())
    metrics = ["positive_pct", "negative_pct", "neutral_pct"]
    labels = ["正面%", "负面%", "中性%"]
    matrix = np.array([[tsc[t][m] for m in metrics] for t in topics])
    fig, ax = plt.subplots(figsize=(7, max(4, len(topics)*0.4)))
    im = ax.imshow(matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=100)
    ax.set_xticks(range(3))
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_yticks(range(len(topics)))
    ax.set_yticklabels(topics, fontsize=9)
    ax.set_title("主题 x 情感交叉分析", fontsize=14, fontweight="bold", pad=15)
    for i in range(len(topics)):
        for j in range(3):
            val = matrix[i, j]
            color = "white" if 30 < val < 70 else "black"
            ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                    fontsize=8, color=color, fontweight="bold")
    fig.colorbar(im, ax=ax, shrink=0.6, label="百分比")
    return _fig_to_base64(fig)


def plot_keyword_bar(data):
    kws = data.get("top_keywords", [])
    if not kws:
        return None
    words = [w for w, _ in kws[:20]]
    counts = [c for _, c in kws[:20]]
    colors = plt.cm.Purples(np.linspace(0.3, 0.9, len(words)))
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.barh(range(len(words)), counts, color=colors[::-1])
    ax.set_yticks(range(len(words)))
    ax.set_yticklabels(words, fontsize=10)
    ax.set_xlabel("出现频次", fontsize=11)
    ax.set_title("高频关键词 Top 20", fontsize=14, fontweight="bold", pad=15)
    ax.invert_yaxis()
    mx = max(counts) if counts else 1
    for bar, val in zip(bars, counts):
        ax.text(bar.get_width() + mx*0.005,
                bar.get_y() + bar.get_height()/2,
                f"  {val}", va="center", fontsize=9)
    return _fig_to_base64(fig)


def plot_daily_trend(data):
    dt = data.get("daily_trend", [])
    if not dt:
        return None
    dates = [d["create_date"] for d in dt]
    counts = [d["count"] for d in dt]
    fig, ax = plt.subplots(figsize=(10, 3.5))
    ax.fill_between(range(len(dates)), counts, alpha=0.3, color="#2196F3")
    ax.plot(range(len(dates)), counts, color="#1565C0", linewidth=1.2)
    ax.set_xlabel("日期", fontsize=10)
    ax.set_ylabel("评论数", fontsize=10)
    ax.set_title("每日评论量趋势", fontsize=14, fontweight="bold", pad=15)
    step = max(1, len(dates)//10)
    ax.set_xticks(range(0, len(dates), step))
    ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=30, fontsize=7)
    return _fig_to_base64(fig)


# ---------- HTML 报告 ----------
CSS_STYLE = """
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,'Microsoft YaHei','PingFang SC',sans-serif;background:#f5f7fa;color:#1a1a2e;line-height:1.6;}
.container{max-width:960px;margin:0 auto;padding:20px;}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);color:#fff;padding:40px 30px;border-radius:12px;margin-bottom:24px;}
.header h1{font-size:28px;margin-bottom:6px;}
.header .subtitle{font-size:14px;opacity:0.8;}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:24px;}
.stat-card{background:#fff;border-radius:10px;padding:16px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.06);}
.stat-card .num{font-size:28px;font-weight:700;color:#0f3460;}
.stat-card .label{font-size:12px;color:#666;margin-top:4px;}
.section{background:#fff;border-radius:12px;padding:24px;margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06);}
.section h2{font-size:18px;margin-bottom:16px;padding-bottom:8px;border-bottom:2px solid #e8ecf1;display:flex;align-items:center;gap:8px;}
.chart-img{width:100%;max-width:800px;display:block;margin:0 auto;border-radius:8px;}
.insight-box{background:#e3f2fd;border-left:4px solid #1976d2;padding:14px 18px;border-radius:0 8px 8px 0;margin:12px 0;font-size:14px;}
.warn-box{background:#fce4ec;border-left:4px solid #c62828;padding:14px 18px;border-radius:0 8px 8px 0;margin:12px 0;font-size:14px;}
.success-box{background:#e8f5e9;border-left:4px solid #2e7d32;padding:14px 18px;border-radius:0 8px 8px 0;margin:12px 0;font-size:14px;}
.comment-card{background:#fafafa;border-radius:8px;padding:12px 16px;margin:8px 0;border:1px solid #eee;}
.comment-card .meta{font-size:12px;color:#888;margin-bottom:4px;}
.comment-card .text{font-size:14px;}
.tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;margin:2px;}
.tag-positive{background:#c8e6c9;color:#1b5e20;}
.tag-negative{background:#ffcdd2;color:#b71c1c;}
.tag-neutral{background:#e0e0e0;color:#424242;}
.tag-topic{background:#e3f2fd;color:#1565c0;}
.footer{text-align:center;font-size:12px;color:#999;padding:24px 0;}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
@media(max-width:640px){.two-col{grid-template-columns:1fr;}}
</style>
"""

def generate_html(data):
    bs = data.get("basic_stats", {})
    sentiment_img = plot_sentiment_pie(data)
    topic_img = plot_topic_bar(data)
    segment_img = plot_segment_bar(data)
    heatmap_img = plot_topic_sentiment_heatmap(data)
    keyword_img = plot_keyword_bar(data)
    trend_img = plot_daily_trend(data)

    parts = []
    parts.append('<!DOCTYPE html>')
    parts.append('<html lang="zh-CN">')
    parts.append('<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">')
    parts.append(f'<title>ActionCoach 评论数据分析报告</title>{CSS_STYLE}</head>')
    parts.append('<body><div class="container">')

    # Header
    parts.append('<div class="header">')
    parts.append('<h1>AI ActionCoach 评论数据分析报告</h1>')
    parts.append('<div class="subtitle">基于用户评论的需求洞察与产品优化方向</div>')
    parts.append('</div>')

    # Stats grid
    parts.append('<div class="stats-grid">')
    for label, key, fmt in [
        ("总评论数", "total_comments", "{}"),
        ("独立用户", "unique_users", "{}"),
        ("总点赞数", "total_likes", "{:,}"),
        ("平均点赞", "avg_likes", "{:.1f}"),
    ]:
        val = bs.get(key, 0)
        parts.append(f'<div class="stat-card"><div class="num">{fmt.format(val)}</div><div class="label">{label}</div></div>')
    dr = bs.get("date_range", ["", ""])
    parts.append(f'<div class="stat-card"><div class="num">{dr[0][:10] if dr[0] else "-"}</div><div class="label">开始日期</div></div>')
    parts.append(f'<div class="stat-card"><div class="num">{dr[1][:10] if dr[1] else "-"}</div><div class="label">结束日期</div></div>')
    parts.append('</div>')

    # Sentiment
    parts.append('<div class="section">')
    parts.append('<h2>情感分布</h2>')
    parts.append(f'<p style="color:#666;margin-bottom:12px;font-size:13px;">平均情感得分: {data.get("avg_sentiment_score", 0):.2f}（范围 -5 ~ +5）</p>')
    parts.append(f'<img class="chart-img" src="data:image/png;base64,{sentiment_img}" alt="情感分布">')
    parts.append('</div>')

    # Topic
    parts.append('<div class="section"><h2>讨论主题分布</h2>')
    parts.append(f'<img class="chart-img" src="data:image/png;base64,{topic_img}" alt="主题分布">')
    parts.append('<div style="margin-top:12px;">')
    tsc = data.get("topic_sentiment_cross", {})
    for topic, info in sorted(tsc.items(), key=lambda x: x[1]["total"], reverse=True):
        neg = info.get("negative_pct", 0)
        pos = info.get("positive_pct", 0)
        if neg > 20:
            parts.append(f'<div class="warn-box">\u26a0\ufe0f <strong>{topic}</strong>: 负面 {neg:.1f}% — 用户痛点集中领域，需优先回应</div>')
        elif pos > 50:
            parts.append(f'<div class="success-box">\u2705 <strong>{topic}</strong>: 正面 {pos:.1f}% — ActionCoach 的优势领域</div>')
    parts.append('</div></div>')

    # Two-column: segments + keywords
    parts.append('<div class="two-col">')
    parts.append(f'<div class="section"><h2>用户画像倾向</h2><img class="chart-img" src="data:image/png;base64,{segment_img}" alt="用户画像"></div>')
    parts.append(f'<div class="section"><h2>高频关键词</h2><img class="chart-img" src="data:image/png;base64,{keyword_img}" alt="关键词"></div>')
    parts.append('</div>')

    # Heatmap
    if heatmap_img:
        parts.append('<div class="section"><h2>主题 x 情感交叉分析</h2>')
        parts.append(f'<img class="chart-img" src="data:image/png;base64,{heatmap_img}" alt="交叉分析">')
        parts.append('<p style="color:#666;margin-top:8px;font-size:12px;">绿色 = 正面占比高，红色 = 负面占比高。负面 > 20% 需优先回应。</p>')
        parts.append('</div>')

    # Trend
    if trend_img:
        parts.append(f'<div class="section"><h2>时间趋势</h2><img class="chart-img" src="data:image/png;base64,{trend_img}" alt="趋势"></div>')

    # Top comments
    top_comments = data.get("top_liked_comments", [])
    if top_comments:
        parts.append('<div class="section"><h2>高赞评论精选</h2>')
        tag_cls = {"positive": "tag-positive", "negative": "tag-negative", "neutral": "tag-neutral"}
        for i, c in enumerate(top_comments[:12], 1):
            sent = c.get("sentiment", "neutral")
            topics = c.get("topics", [])
            topic_tags = "".join(f'<span class="tag tag-topic">{t}</span>' for t in topics)
            parts.append(f'<div class="comment-card">')
            parts.append(f'<div class="meta">\u2764\ufe0f {c.get("likes",0)} | <span class="tag {tag_cls.get(sent,"tag-neutral")}">{sent}</span> {topic_tags}</div>')
            parts.append(f'<div class="text">{c.get("content","")}</div>')
            parts.append('</div>')
        parts.append('</div>')

    # Insights
    parts.append('<div class="section"><h2>对 ActionCoach 的优化建议</h2>')
    td = data.get("topic_distribution", {})
    if td:
        top3 = list(td.keys())[:3]
        parts.append(f'<div class="insight-box"><strong>需求热度 Top 3:</strong> {"、".join(top3)}<br>教练技能应优先覆盖这三个主题的对话场景。</div>')
    sd = data.get("user_segment_distribution", {})
    if sd:
        top_seg = list(sd.keys())[0]
        desc = sd[top_seg].get("description", "")
        parts.append(f'<div class="insight-box"><strong>核心用户画像:</strong> {top_seg}<br>{desc}<br>每日推送和对话风格应优先适配此类用户。</div>')
    cooc = data.get("keyword_cooccurrence", [])
    if cooc:
        tp = " + ".join(cooc[0]["pair"])
        parts.append(f'<div class="insight-box"><strong>需求关联发现:</strong> 「{tp}」是最常被同时提及的需求组合，对话流程应覆盖此组合。</div>')
    parts.append('<div class="insight-box"><strong>SKILL.md 优化方向</strong><br>')
    parts.append('1. 在 Step 1 目标澄清阶段增加对高频主题的引导提问<br>')
    parts.append('2. 针对高负面情绪主题设计「情绪接纳」对话分支<br>')
    parts.append('3. 根据画像分布对每日推送 tone 做个性化适配<br>')
    parts.append('4. 补充「教练学习者」用户类型的支持路径')
    parts.append('</div></div>')

    parts.append(f'<div class="footer">由 ActionCoach 评论分析引擎生成 | {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>')
    parts.append('</div></body></html>')
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(description="ActionCoach 评论分析可视化")
    parser.add_argument("--input", default="output/analysis/analysis_result.json",
                        help="analysis_result.json 路径")
    parser.add_argument("--output", default="output/analysis/report.html",
                        help="输出的 HTML 报告路径")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[!] 输入文件不存在: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"  生成 HTML 报告...")
    html = generate_html(data)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  HTML 报告已导出: {output_path.resolve()}")
    print(f"  用浏览器打开即可查看")


if __name__ == "__main__":
    main()
