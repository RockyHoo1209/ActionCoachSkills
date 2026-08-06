const fs = require("fs"), path = require("path");

// ── Config ──────────────────────────────────────────────
const DIR = "data/reviews";
const OUT_DIR = path.join(DIR, "analysis_output");

// ── 1. Load Data ──
const files = fs.readdirSync(DIR).filter(f => f.endsWith(".jsonl"));
const comments = [], contents = [];
for (const f of files) {
  const raw = fs.readFileSync(path.join(DIR, f), "utf8").trim();
  const lines = raw.split("\n");
  let n = 0;
  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const obj = JSON.parse(line);
      if (obj.comment_id !== undefined) comments.push(obj);
      else if (obj.note_id !== undefined) contents.push(obj);
      n++;
    } catch (_) {}
  }
}

// ── 2. Keyword Category Dictionary ──
const CAT_DICT = {
  emotional_distress:  ["焦虑","抑郁","失眠","睡不着","崩溃","绝望","痛苦","迷茫","压力","恐惧","害怕","烦躁","无助","自卑","没信心","不自信","失落","空虚","煎熬","折磨","想死","受不了","想哭"],
  financial_pressure:  ["没钱","缺钱","负债","信用卡","花呗","月光","积蓄","存款","房贷","房租","吃饭","生存","补贴","失业保险","经济","收入","工资","裁员","赔偿","n+1"],
  job_search_frust:    ["找不到工作","投简历","面试","offer","已读不回","没有回复","石沉大海","海投","被拒","不合适","已读","没有结果","空窗期","gap","空白期","hr","boss直聘","智联","猎聘"],
  age_discrimination:  ["年龄","35岁","35","中年","年纪大","年轻人","应届生","毕业生","00后","90后","大龄","30岁","40岁","25岁"],
  skill_gap:           ["技能","学习","培训","考证","学历","证书","不会","不懂","转行","没经验","经验","能力","技术","知识","充电","转型","0基础","入门"],
  self_improvement:    ["提升","成长","改变","进步","行动","自律","努力","坚持","早起","读书","健身","减肥","打卡","day"],
  social_stigma:       ["丢人","没面子","看不起","嘲笑","废物","废人","啃老","家里蹲","宅","社交","朋友","家人","亲戚","结婚","对象","同学","聚会"],
  coaching_needs:      ["教练","指导","课程","训练营","陪跑","规划","咨询","建议","怎么办","方法","出路","方向","职业规划","转型","陪跑","1v1","一对一","带教"],
  job_type_reference:  ["公务员","考公","考研","考编","铁饭碗","国企","事业单位","大厂","互联网","外企","创业","自由职业","副业","自媒体","摆摊","送外卖","跑滴滴"],
};

// ── 3. Sentiment Dictionary ──
const POS_WORDS = ["加油","坚持","找到","上岸","offer","恭喜","好运","努力","希望","信心","好转","满意","不错","开心","高兴","感谢","有用","收获","成功","进步","突破","相信"];
const NEG_WORDS = ["太难","焦虑","崩溃","绝望","想死","受不了","痛苦","失败","找不到","被拒","难受","完蛋","没戏","放弃","不行","没希望","废了","煎熬","折磨","垃圾","恶心","烦死","迷茫","无助","睡不着","失眠"];

function safeStr(v) { return (v || "").toString().trim(); }

function getCategories(text) {
  const t = safeStr(text);
  const hits = {};
  for (const [cat, words] of Object.entries(CAT_DICT)) {
    for (const w of words) {
      if (t.includes(w)) { hits[cat] = (hits[cat] || 0) + 1; break; }
    }
  }
  return hits;
}

function getSentiment(text) {
  const t = safeStr(text);
  let pos = 0, neg = 0;
  for (const w of POS_WORDS) { const m = t.match(new RegExp(w, "g")); if (m) pos += m.length; }
  for (const w of NEG_WORDS) { const m = t.match(new RegExp(w, "g")); if (m) neg += m.length; }
  if (pos === 0 && neg === 0) return "neutral";
  // Check mixed first
  if (pos > 0 && neg > 0) return "mixed";
  if (pos > neg) return "positive";
  return "negative";
}

// ── 4. Compute Stats ──
const totalLikes = comments.reduce((s, r) => s + (parseInt(r.like_count) || 0), 0);
const totalSubCmt = comments.reduce((s, r) => s + (parseInt(r.sub_comment_count) || 0), 0);

// Category counts
const catCounts = {}, catLikes = {};
for (const r of comments) {
  const cats = getCategories(r.content);
  for (const [c] of Object.entries(cats)) {
    catCounts[c] = (catCounts[c] || 0) + 1;
    catLikes[c] = (catLikes[c] || 0) + (parseInt(r.like_count) || 0);
  }
}

// Sentiment counts
const sentCounts = { positive: 0, mixed: 0, neutral: 0, negative: 0 };
const sentLikes = { positive: 0, mixed: 0, neutral: 0, negative: 0 };
for (const r of comments) {
  const s = getSentiment(r.content);
  sentCounts[s]++;
  sentLikes[s] += (parseInt(r.like_count) || 0);
}

// Top liked
const topLiked = [...comments].sort((a, b) => (parseInt(b.like_count)||0) - (parseInt(a.like_count)||0)).slice(0, 20);

// Coaching-need comments
const coachingNeed = comments.filter(r => {
  const cats = getCategories(r.content);
  return cats.coaching_needs || cats.self_improvement;
}).sort((a, b) => (parseInt(b.like_count)||0) - (parseInt(a.like_count)||0)).slice(0, 15);

// Bigram analysis (Chinese 2-char phrases)
const bgCounts = {};
for (const r of comments) {
  const t = safeStr(r.content).replace(/[，。！？、；：""''（）【】《》\s\d\w]/g, "");
  for (let i = 0; i < t.length - 1; i++) {
    const bg = t.substring(i, i + 2);
    if (/[\u4e00-\u9fff]{2}/.test(bg)) bgCounts[bg] = (bgCounts[bg] || 0) + 1;
  }
}
const topBigrams = Object.entries(bgCounts).sort((a, b) => b[1] - a[1]).slice(0, 60);

// Length distribution
const lenBins = { "1-10字": 0, "11-30字": 0, "31-60字": 0, "61-100字": 0, "100+字": 0 };
for (const r of comments) {
  const len = safeStr(r.content).length;
  if (len <= 10) lenBins["1-10字"]++;
  else if (len <= 30) lenBins["11-30字"]++;
  else if (len <= 60) lenBins["31-60字"]++;
  else if (len <= 100) lenBins["61-100字"]++;
  else lenBins["100+字"]++;
}

// ── 5. Compose Report ──
const CAT_LABEL = {
  emotional_distress: "😰 情绪焦虑/心理压力",
  financial_pressure: "💰 经济压力/财务困境",
  job_search_frust:   "📋 求职挫败/简历面试",
  age_discrimination: "🔢 年龄歧视/代际压力",
  skill_gap:          "📚 技能不足/学习提升",
  self_improvement:   "🌱 自我成长/行动力",
  social_stigma:      "👥 社会压力/面子问题",
  coaching_needs:     "🧭 教练/指导需求",
  job_type_reference: "🏢 职业类型/行业参考",
};

const lines = [];
const L = (s) => lines.push(s);

L("=".repeat(76));
L("  失业·求职·就业 评论数据分析报告");
L("  ActionCoach 垂直教练产品调研");
L("=".repeat(76));
L("  分析时间: " + new Date().toISOString().replace("T", " ").slice(0, 19));
L("  评论总数: " + comments.length + " 条");
L("  视频/笔记: " + contents.length + " 条");
L("  总点赞: " + totalLikes.toLocaleString());
L("");
L("─".repeat(76));
L("  一、话题关键词分类分布");
L("─".repeat(76));
L("  (一条评论可能命中多个类别)");
L("");

const sortedCats = Object.entries(catCounts).sort((a, b) => b[1] - a[1]);
const maxCat = sortedCats.length > 0 ? sortedCats[0][1] : 1;
for (const [cat, cnt] of sortedCats) {
  const label = CAT_LABEL[cat] || cat;
  const bar = "█".repeat(Math.round((cnt / maxCat) * 30)).padEnd(30, "─");
  const pct = ((cnt / comments.length) * 100).toFixed(1);
  L("  " + label + "  " + bar + "  " + cnt + "条 (" + pct + "%)  [赞" + (catLikes[cat]||0).toLocaleString() + "]");
}
L("");

L("─".repeat(76));
L("  二、情感倾向分布");
L("─".repeat(76));
const sentLabel = { positive: "😊 积极/希望", mixed: "🤔 复杂/矛盾", neutral: "😐 中性/陈述", negative: "😞 消极/绝望" };
const maxSent = Math.max(...Object.values(sentCounts));
for (const [s, cnt] of Object.entries(sentCounts)) {
  const bar = "█".repeat(Math.round((cnt / maxSent) * 30)).padEnd(30, "─");
  const pct = ((cnt / comments.length) * 100).toFixed(1);
  L("  " + (sentLabel[s]||s) + "  " + bar + "  " + cnt + "条 (" + pct + "%)  [赞" + (sentLikes[s]||0).toLocaleString() + "]");
}
L("");

L("─".repeat(76));
L("  三、最高赞评论 TOP 20（洞察核心痛点/共鸣点）");
L("─".repeat(76));
for (let i = 0; i < topLiked.length; i++) {
  const r = topLiked[i];
  const cats = Object.keys(getCategories(r.content)).map(c => CAT_LABEL[c]||c).join(", ");
  L("  #" + (i+1).toString().padStart(2) + "  👍" + (r.like_count||"").padStart(6) + "  " + safeStr(r.nickname));
  L("      " + r.content);
  L("      → " + cats);
}
L("");

L("─".repeat(76));
L("  四、教练需求评论（含「怎么办」「教练」「出路」「方法」等）");
L("─".repeat(76));
if (coachingNeed.length === 0) {
  L("  （无直接命中，展示备选）");
  const fallback = comments.filter(r => /怎么办|方向|出路|建议|方法|规划/.test(r.content))
    .sort((a,b) => (parseInt(b.like_count)||0)-(parseInt(a.like_count)||0)).slice(0, 10);
  for (const r of fallback) {
    L("  👍" + (r.like_count||"").padStart(6) + "  " + r.content);
  }
} else {
  for (let i = 0; i < coachingNeed.length; i++) {
    const r = coachingNeed[i];
    L("  #" + (i+1).toString().padStart(2) + "  👍" + (r.like_count||"").padStart(6) + "  " + r.content);
  }
}
L("");

L("─".repeat(76));
L("  五、高频词组 TOP 60（2字组合，反映热议焦点）");
L("─".repeat(76));
for (let i = 0; i < topBigrams.length; i += 6) {
  const row = topBigrams.slice(i, i+6).map(([w, c]) => w + "(" + c + ")").join("  ");
  L("  " + row);
}
L("");

L("─".repeat(76));
L("  六、评论长度分布");
L("─".repeat(76));
const maxBin = Math.max(...Object.values(lenBins));
for (const [bin, cnt] of Object.entries(lenBins)) {
  const bar = "█".repeat(Math.round((cnt / maxBin) * 30)).padEnd(30, "─");
  const pct = ((cnt / comments.length) * 100).toFixed(1);
  L("  " + bin.padEnd(10) + bar + " " + cnt + "条 (" + pct + "%)");
}
L("");

// Contents analysis
if (contents.length > 0) {
  L("─".repeat(76));
  L("  七、关联笔记/视频分析");
  L("─".repeat(76));
  const totLike = contents.reduce((s, r) => s + (parseInt(r.liked_count)||0), 0);
  const totCollect = contents.reduce((s, r) => s + (parseInt(r.collected_count)||0), 0);
  const totCmt = contents.reduce((s, r) => s + (parseInt(r.comment_count)||0), 0);
  L("  总点赞: " + totLike.toLocaleString() + "  总收藏: " + totCollect.toLocaleString() + "  总评论: " + totCmt.toLocaleString());
  L("");

  // Tag analysis
  const tagCounts = {};
  for (const r of contents) {
    const tags = safeStr(r.tag_list).split(",");
    for (const t of tags) {
      const tt = t.trim().replace(/^#/, "");
      if (tt) tagCounts[tt] = (tagCounts[tt] || 0) + 1;
    }
  }
  const topTags = Object.entries(tagCounts).sort((a,b) => b[1]-a[1]).slice(0, 25);
  L("  热门话题标签 TOP 25:");
  for (const [tag, cnt] of topTags) {
    L("    #" + tag + " (" + cnt + "条)");
  }
  L("");

  L("  内容标题/描述摘录 (前10条):");
  for (const r of contents.slice(0, 10)) {
    const title = safeStr(r.title || r.desc || "").substring(0, 80);
    L("    " + (title || "(无标题)"));
  }
  L("");
}

L("=".repeat(76));
L("  八、用户需求洞察与产品建议");
L("=".repeat(76));
L("");

// Generate insights based on top categories
const topCats = sortedCats.map(([c]) => c);

const INSIGHTS = {
  emotional_distress: [
    "• 这是当前用户最大的痛点类别，远超其他维度",
    "• 长期失业已引发失眠、崩溃、绝望等心理健康问题",
    "• 用户需要的不仅是求职方法论，更是心理支持和信心重建",
    "• 产品应内置「心理疏导模块」而非纯技能培训",
  ],
  financial_pressure: [
    "• 经济压力紧随情绪问题，用户面临生存危机",
    "• 求职时间窗口紧迫，无法承受长期再培训",
    "• 建议设计「快速就业→稳定→转型」三阶段路径",
    "• 可针对急需收入用户推出「短期陪跑计划」",
  ],
  job_search_frust: [
    "• 简历石沉大海、已读不回、面试无反馈是日常",
    "• 用户需要的是「反馈」和「迭代指南」，而非泛泛建议",
    "• 教练核心服务应是：简历诊断→投递策略→面试模拟→拒信复盘",
  ],
  age_discrimination: [
    "• 年龄焦虑普遍存在，35岁/40岁是真实恐惧线",
    "• 用户需要看到「同龄人成功转型案例」和「非年龄敏感赛道」",
    "• 可设计「第二曲线/中年转型」专项产品线",
  ],
  skill_gap: [
    "• 用户知道缺技能但不知道学什么、怎么学",
    "• 建议提供「岗位技能诊断→学习路径规划→实战项目」闭环",
    "• 可与平台课程结合，打造教练+课程组合产品",
  ],
  self_improvement: [
    "• 用户有强烈的改变意愿（自律、打卡、坚持高频出现）",
    "• 缺的是可持续的行动计划和 accountability 机制",
    "• 教练核心价值在于「陪伴+督促+纠偏」",
  ],
  social_stigma: [
    "• 社会/家庭压力显著——「丢人」「啃老」「废物」是高频自嘲",
    "• 用户需要被理解、被接纳，教练要创造心理安全空间",
    "• 同伴社群是重要的产品设计要素",
  ],
  coaching_needs: [
    "• 用户明确表达了对「教练/指导/规划」的需求",
    "• 现有职业咨询太贵/太泛，缺乏「失业人群垂直教练」",
    "• 这是最大的机会窗口",
  ],
};

// Print insights for top 4 categories
let printed = 0;
for (const cat of topCats) {
  if (printed >= 4) break;
  const tip = INSIGHTS[cat];
  if (tip) {
    L("  📌 " + (CAT_LABEL[cat] || cat));
    for (const line of tip) L("  " + line);
    L("");
    printed++;
  }
}

L("  ─── 产品定位建议 ───");
L("  目标人群: 失业人群（含被裁、应届待业、空窗期长、中年转型）");
L("  核心价值: 不是另一个求职课程，而是「失业期的专属教练」");
L("  差异化: 心理支持 + 求职实战 + 同伴监督 三位一体");
L("  建议 MVP: 1v1 线上陪跑教练 + 同伴社群 + AI 辅助工具");
L("");

L("  ─── 建议产品模块 ───");
L("  模块1 — 心理重建: 认知行为练习 + 小胜利计划 + 同伴支持组");
L("  模块2 — 求职陪跑: 简历诊断/优化 + 面试模拟 + 投递策略 + 拒信复盘");
L("  模块3 — 技能诊断: 目标岗位技能缺口分析 + 学习路径 + 实战项目");
L("  模块4 — 经济应急: 快速过渡性工作推荐 + 副业启动 + 财务规划");
L("  模块5 — 社群运营: 同阶段失业者互助小组 + 校友网络 + 日常打卡监督");
L("");

L("  ─── 教练产品关键设计原则 ───");
L("  1. 短周期承诺（4-6周起），降低决策门槛");
L("  2. 结果导向而非过程导向（明确每周里程碑）");
L("  3. 价格可负担（针对经济压力人群设计梯度定价）");
L("  4. 强 accountability（教练每日/隔日 check-in，用户承诺行动）");
L("  5. 社群作为留存抓手（同路人效应）");
L("");

L("=".repeat(76));
L("  报告结束");
L("=".repeat(76));

// ── 6. Write Output ──
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

const reportTxt = lines.join("\n");
fs.writeFileSync(path.join(OUT_DIR, "analysis_report.txt"), reportTxt, "utf8");

const jsonOut = {
  meta: { total_comments: comments.length, total_contents: contents.length, total_likes: totalLikes },
  keyword_categories: sortedCats.map(([cat, cnt]) => ({
    category: cat, label: CAT_LABEL[cat] || cat, count: cnt,
    pct: ((cnt / comments.length) * 100).toFixed(1),
    likes: catLikes[cat] || 0,
  })),
  sentiment: Object.entries(sentCounts).map(([s, cnt]) => ({
    sentiment: s, count: cnt,
    pct: ((cnt / comments.length) * 100).toFixed(1),
    likes: sentLikes[s] || 0,
  })),
  top_liked: topLiked.map(r => ({ content: r.content, like_count: r.like_count, nickname: r.nickname })),
  coaching_potential: coachingNeed.map(r => ({ content: r.content, like_count: r.like_count })),
  top_bigrams: topBigrams.map(([w, c]) => ({ phrase: w, count: c })),
  length_distribution: lenBins,
  content_tags: (() => {
    const tc = {};
    for (const r of contents) {
      for (const t of safeStr(r.tag_list).split(",")) {
        const tt = t.trim().replace(/^#/,"");
        if (tt) tc[tt] = (tc[tt] || 0) + 1;
      }
    }
    return Object.entries(tc).sort((a,b) => b[1]-a[1]).slice(0, 25).map(([t, c]) => ({ tag: t, count: c }));
  })(),
};
fs.writeFileSync(path.join(OUT_DIR, "analysis_data.json"), JSON.stringify(jsonOut, null, 2), "utf8");

console.log("\n✅ Analysis complete!");
console.log("   Report: " + path.join(OUT_DIR, "analysis_report.txt"));
console.log("   JSON:   " + path.join(OUT_DIR, "analysis_data.json"));
console.log(reportTxt);
