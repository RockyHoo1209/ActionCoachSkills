const fs = require("fs"), path = require("path");

// ─── Load analysis data ──────────────────────────
const DATA_FILE = "data/reviews/analysis_output/analysis_data.json";
const data = JSON.parse(fs.readFileSync(DATA_FILE, "utf8"));

function esc(s) { return (s??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

const L = [];
function emit(s="") { L.push(s); }

emit(`<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>失业·求职·就业 评论分析报告</title>
<style>
  body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; background:#f5f6fa; color:#1a1a2e; margin:0; padding:20px; line-height:1.7; }
  .container { max-width:960px; margin:0 auto; }
  h1 { text-align:center; font-size:28px; margin:30px 0 5px; }
  .subtitle { text-align:center; color:#666; font-size:14px; margin-bottom:30px; }
  .summary-cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:30px; }
  .card { background:white; border-radius:10px; padding:16px; text-align:center; box-shadow:0 1px 4px rgba(0,0,0,.08); }
  .card .num { font-size:32px; font-weight:700; color:#e94560; }
  .card .label { font-size:13px; color:#888; margin-top:4px; }
  section { background:white; border-radius:12px; padding:24px; margin-bottom:20px; box-shadow:0 1px 4px rgba(0,0,0,.08); }
  h2 { font-size:20px; margin:0 0 16px; padding-bottom:10px; border-bottom:2px solid #e94560; }
  .bar-chart { margin:10px 0; }
  .bar-row { display:flex; align-items:center; margin:6px 0; gap:8px; }
  .bar-label { width:220px; text-align:right; font-size:14px; flex-shrink:0; }
  .bar-track { flex:1; height:24px; background:#eef0f7; border-radius:12px; overflow:hidden; }
  .bar-fill { height:100%; border-radius:12px; transition:width .3s; display:flex; align-items:center; padding-left:8px; font-size:12px; color:white; font-weight:600; }
  .bar-count { width:100px; font-size:13px; color:#555; flex-shrink:0; }
  .comment-list { list-style:none; padding:0; margin:0; }
  .comment-list li { padding:12px 16px; border-bottom:1px solid #f0f0f0; border-radius:6px; margin:6px 0; background:#fafafa; }
  .comment-list li:last-child { border-bottom:none; }
  .comment-meta { font-size:12px; color:#999; margin-top:4px; }
  .like-badge { display:inline-block; background:#e94560; color:white; font-size:12px; padding:1px 8px; border-radius:10px; font-weight:600; }
  .tag { display:inline-block; background:#eef0f7; color:#555; font-size:12px; padding:2px 10px; border-radius:10px; margin:2px; }
  .bigrams { display:flex; flex-wrap:wrap; gap:6px; }
  .bigrams span { background:#eef0f7; padding:4px 12px; border-radius:16px; font-size:13px; }
  .bigrams .count { color:#e94560; font-weight:600; }
  .insight-box { background:#fff8f0; border-left:4px solid #e94560; padding:12px 16px; margin:12px 0; border-radius:0 8px 8px 0; }
  .module-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:14px; }
  .module-card { background:#fafafa; border-radius:10px; padding:16px; border:1px solid #eef0f7; }
  .module-card h4 { margin:0 0 8px; color:#e94560; }
  .module-card ul { margin:0; padding-left:18px; font-size:14px; }
  .module-card li { margin:4px 0; }
  footer { text-align:center; font-size:12px; color:#aaa; margin:40px 0 20px; }
  @media(max-width:640px){ .bar-label { width:120px; font-size:12px; } .bar-count { width:70px; } }
</style>
</head>
<body>
<div class="container">
<h1>📊 失业·求职·就业 评论数据分析报告</h1>
<p class="subtitle">面向「失业教练」垂直产品设计 · ActionCoach · ${new Date().toISOString().replace("T"," ").slice(0,19)}</p>

<div class="summary-cards">
  <div class="card"><div class="num">${data.meta.total_comments.toLocaleString()}</div><div class="label">评论总数</div></div>
  <div class="card"><div class="num">${data.meta.total_contents.toLocaleString()}</div><div class="label">笔记/视频</div></div>
  <div class="card"><div class="num">${data.meta.total_likes.toLocaleString()}</div><div class="label">总点赞</div></div>
  <div class="card"><div class="num">${data.meta.total_replies.toLocaleString()}</div><div class="label">总回复</div></div>
  <div class="card"><div class="num">${data.meta.dy_comments.toLocaleString()}</div><div class="label">抖音评论</div></div>
  <div class="card"><div class="num">${data.meta.xhs_comments.toLocaleString()}</div><div class="label">小红书评论</div></div>
</div>
`);

// ── Part 1: Category Distribution ──
emit(`<section><h2>📂 话题关键词分类分布</h2><p style="color:#888;font-size:13px;">一条评论可能命中多个类别，按命中条数降序</p>
<div class="bar-chart">`);

const maxCat = data.keyword_categories.length > 0 ? data.keyword_categories[0].count : 1;
for (const c of data.keyword_categories) {
  const pct = ((c.count / data.meta.total_comments)*100).toFixed(1);
  const pctBar = (c.count / maxCat * 100).toFixed(1);
  emit(`<div class="bar-row"><span class="bar-label">${esc(c.label)}</span><div class="bar-track"><div class="bar-fill" style="width:${pctBar}%;background:#${c.category==="coaching_needs"?"e94560":c.category==="self_improvement"?"0f3460":c.category==="emotional_distress"?"e94560":"533483"}">${c.count}</div></div><span class="bar-count">${c.count}条 (${pct}%)</span></div>`);
}
emit(`</div></section>`);

// ── Part 2: Sentiment ──
emit(`<section><h2>😊 情感倾向分布</h2><div class="bar-chart">`);
const maxSent = Math.max(...data.sentiment.map(s=>s.count));
for (const s of data.sentiment) {
  const emoji = {positive:"😊", mixed:"🤔", neutral:"😐", negative:"😞"}[s.sentiment]||"";
  const pctBar = (s.count / maxSent * 100).toFixed(1);
  const pct = ((s.count / data.meta.total_comments)*100).toFixed(1);
  const color = {positive:"#27ae60", mixed:"#f39c12", neutral:"#95a5a6", negative:"#e74c3c"}[s.sentiment]||"#95a5a6";
  emit(`<div class="bar-row"><span class="bar-label">${emoji} ${s.sentiment==="positive"?"积极/希望":s.sentiment==="mixed"?"复杂/矛盾":s.sentiment==="neutral"?"中性/陈述":"消极/绝望"}</span><div class="bar-track"><div class="bar-fill" style="width:${pctBar}%;background:${color}">${s.count}</div></div><span class="bar-count">${s.count}条 (${pct}%) · 赞${s.likes.toLocaleString()}</span></div>`);
}
emit(`</div></section>`);

// ── Part 3: Top Comments ──
emit(`<section><h2>🔥 最高赞评论 TOP 20</h2><ol class="comment-list">`);
for (const r of data.top_liked) {
  emit(`<li><strong>${esc(r.content)}</strong><div class="comment-meta"><span class="like-badge">👍${r.like_count}</span> ${esc(r.nickname)} · ${r.platform||""}</div></li>`);
}
emit(`</ol></section>`);

// ── Part 4: Coaching Potential ──
emit(`<section><h2>🧭 教练需求评论 TOP 15</h2><ol class="comment-list">`);
for (const r of data.coaching_potential) {
  emit(`<li><strong>${esc(r.content)}</strong><div class="comment-meta"><span class="like-badge">👍${r.like_count}</span></div></li>`);
}
emit(`</ol></section>`);

// ── Part 5: Bigrams ──
emit(`<section><h2>🔤 高频词组 TOP 60</h2><div class="bigrams">`);
for (const b of data.top_bigrams) {
  emit(`<span>${esc(b.phrase)} <span class="count">${b.count}</span></span>`);
}
emit(`</div></section>`);

// ── Part 6: Length ──
emit(`<section><h2>📏 评论长度分布</h2><div class="bar-chart">`);
const maxLen = Math.max(...Object.values(data.length_distribution));
for (const [bin, cnt] of Object.entries(data.length_distribution)) {
  const pctBar = (cnt / maxLen * 100).toFixed(1);
  const pct = ((cnt / data.meta.total_comments)*100).toFixed(1);
  emit(`<div class="bar-row"><span class="bar-label">${esc(bin)}</span><div class="bar-track"><div class="bar-fill" style="width:${pctBar}%;background:#533483">${cnt}</div></div><span class="bar-count">${cnt}条 (${pct}%)</span></div>`);
}
emit(`</div></section>`);

// ── Part 7: Content Tags ──
if (data.content_tags && data.content_tags.length > 0) {
  emit(`<section><h2>🏷️ 热门话题标签 TOP 30</h2>`);
  for (const t of data.content_tags) {
    emit(`<span class="tag">#${esc(t.tag)} (${t.count})</span>`);
  }
  emit(`</section>`);
}

// ── Part 8: Source Keywords ──
if (data.source_keywords && data.source_keywords.length > 0) {
  emit(`<section><h2>🔍 搜索关键词分布</h2><div class="bar-chart">`);
  const maxKw = data.source_keywords[0].count;
  for (const k of data.source_keywords) {
    const pctBar = (k.count / maxKw * 100).toFixed(1);
    emit(`<div class="bar-row"><span class="bar-label">"${esc(k.keyword)}"</span><div class="bar-track"><div class="bar-fill" style="width:${pctBar}%;background:#0f3460">${k.count}</div></div><span class="bar-count">${k.count}条</span></div>`);
  }
  emit(`</div></section>`);
}

// ── Part 9: Insights & Product Suggestions ──
const topCats = data.keyword_categories.slice(0, 5).map(c => c.category);

const INSIGHTS = {
  coaching_needs: "用户明确表达了对教练/指导/规划的需求，这是最大的产品机会窗口。现有的职业咨询太贵/太泛，缺乏「失业人群垂直教练」。用户希望有人带着走、陪着练、给反馈。",
  self_improvement: "用户有强烈的改变意愿（自律、打卡、坚持高频出现），缺的是可持续的行动计划和 accountability 机制。教练核心价值在于「陪伴+督促+纠偏」。「小胜利」策略是让用户坚持下去的关键。",
  emotional_distress: "这是最深层的痛点——长期失业引发失眠、崩溃、绝望、自我怀疑。用户需要的不仅是求职方法论，更是心理支持和信心重建。产品必须内置心理疏导模块，而非纯技能培训。「不是你不行，是市场不行」——认知重构是关键切入点。",
  skill_gap: "用户知道缺技能但不知道学什么、怎么学。建议提供「岗位技能诊断→学习路径→实战项目」闭环。可与在线课程结合，打造教练+课程组合产品。",
  job_search_frust: "简历石沉大海、已读不回、面试无反馈是日常。用户需要的是「反馈」和「迭代指南」，而非泛泛建议。教练核心服务：简历诊断→投递策略→面试模拟→拒信复盘。",
  age_discrimination: "年龄焦虑普遍，35岁/40岁是真实恐惧线。用户需要看到「同龄人成功转型案例」和「非年龄敏感赛道」。可设计「第二曲线/中年转型」专项产品线。",
  social_stigma: "社会/家庭压力显著——「丢人」「啃老」「废物」是高频自嘲词。用户需要被理解、被接纳，教练首先要创造心理安全空间。同伴社群是重要的产品设计要素，同路人效应极其重要。",
  financial_pressure: "经济压力紧迫，求职时间窗口窄。建议设计「快速就业→稳定→转型」三阶段路径。针对急需收入用户推出「短期陪跑计划」。",
};

const CAT_LABEL = {
  coaching_needs: "🧭 教练/指导需求", self_improvement: "🌱 自我成长/行动力",
  emotional_distress: "😰 情绪焦虑/心理压力", skill_gap: "📚 技能不足/学习提升",
  job_search_frust: "📋 求职挫败/简历面试", age_discrimination: "🔢 年龄歧视/代际压力",
  social_stigma: "👥 社会压力/面子问题", financial_pressure: "💰 经济压力/财务困境",
};

emit(`<section><h2>💡 用户需求洞察与产品方向</h2>`);
for (const cat of topCats) {
  const tip = INSIGHTS[cat];
  if (tip) {
    emit(`<div class="insight-box"><strong>${CAT_LABEL[cat]||cat}</strong><br>${esc(tip)}</div>`);
  }
}

emit(`
<div class="insight-box" style="border-left-color:#0f3460;background:#f0f4ff;">
<strong>🎯 产品定位总结</strong><br>
<b>目标人群:</b> 失业/求职中人群（被裁、应届待业、空窗期长、中年转型、裸辞）<br>
<b>核心价值:</b> 不是又一个求职课程，而是「失业期的专属教练 — 陪你走出来的那个人」<br>
<b>差异化定位:</b> 心理支持 + 求职实战 + 同伴监督 三位一体<br>
<b>建议 MVP:</b> 1v1 线上陪跑教练（短周期4-6周）+ 同阶段社群 + AI 辅助工具
</div>

<h3 style="margin-top:24px;">📦 建议产品模块设计</h3>
<div class="module-grid">
  <div class="module-card"><h4>🧠 模块1 — 心理重建</h4><ul><li>认知行为练习（认知重构）</li><li>小胜利计划（每周微目标）</li><li>同伴支持小组</li></ul></div>
  <div class="module-card"><h4>🔍 模块2 — 求职陪跑</h4><ul><li>简历诊断与优化</li><li>投递策略制定</li><li>面试模拟与复盘</li><li>Offer评估与谈判</li></ul></div>
  <div class="module-card"><h4>📚 模块3 — 技能诊断</h4><ul><li>岗位技能缺口分析</li><li>个性化学习路径</li><li>实战项目推送</li></ul></div>
  <div class="module-card"><h4>💰 模块4 — 经济应急</h4><ul><li>快速过渡性工作推荐</li><li>副业启动清单</li><li>财务压力疏导</li></ul></div>
  <div class="module-card"><h4>👥 模块5 — 社群运营</h4><ul><li>同阶段互助小组</li><li>每日打卡监督</li><li>校友网络</li></ul></div>
</div>

<h3 style="margin-top:24px;">⚙️ 产品设计原则</h3>
<ol style="font-size:14px;">
<li><b>短周期承诺</b>（4-6周起），降低决策门槛</li>
<li><b>结果导向</b>而非过程导向（明确每周可交付里程碑）</li>
<li><b>价格可负担</b>（针对经济压力人群设计梯度定价）</li>
<li><b>强 accountability</b>（教练每日/隔日 check-in，用户承诺行动）</li>
<li><b>社群作为留存抓手</b>（同路人效应 + 归属感）</li>
<li><b>内容+服务双引擎</b>（免费内容引流 → 付费教练转化）</li>
</ol>

<h3 style="margin-top:24px;">📢 内容营销方向（引流）</h3>
<ul style="font-size:14px;">
<li><b>方向A:</b> 真实失业日记 / 上岸故事 / 转型案例 → 建立信任</li>
<li><b>方向B:</b> 求职技巧硬干货（简历模板、面试题库、行业薪资）→ 吸引精准流量</li>
<li><b>方向C:</b> 心理/认知类内容（如何应对空窗期焦虑、自我价值重建）→ 引发共鸣传播</li>
<li><b>方向D:</b> 教练过程记录（真实陪跑 case study）→ 展示产品价值</li>
</ul>
</section>`);

emit(`<footer>ActionCoachSkills · 分析脚本 analyze_all.cjs · ${new Date().toISOString().replace("T"," ").slice(0,19)}</footer>
</div></body></html>`);

const outPath = "data/reviews/analysis_output/analysis_report.html";
fs.writeFileSync(outPath, L.join("\n"), "utf8");
console.log("✅ HTML report written to: " + outPath);
