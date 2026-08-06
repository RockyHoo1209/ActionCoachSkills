const fs = require("fs"), path = require("path");

// ─── Config ──────────────────────────────────────────
const ROOT = "./data/reviews";
const SUBDIRS = ["dy"];
const OUT_DIR = path.join(ROOT, "analysis_output");

// ─── Keyword Categories ──────────────────────────────
const CAT_DICT = {
  emotional_distress:  ["焦虑","抑郁","失眠","睡不着","崩溃","绝望","痛苦","迷茫","压力","恐惧","害怕","烦躁","无助","自卑","没信心","不自信","失落","空虚","煎熬","折磨","想死","受不了","想哭","内耗","心累","emo"],
  financial_pressure:  ["没钱","缺钱","负债","信用卡","花呗","月光","积蓄","存款","房贷","房租","吃饭","生存","补贴","失业保险","经济","收入","工资","裁员","赔偿","n+1","降薪","欠款"],
  job_search_frust:    ["找不到工作","投简历","面试","offer","已读不回","没有回复","石沉大海","海投","被拒","不合适","已读","没有结果","空窗期","gap","空白期","hr","boss直聘","智联","猎聘","求职","简历"],
  age_discrimination:  ["年龄","35岁","35","中年","年纪大","年轻人","应届生","毕业生","00后","90后","大龄","30岁","40岁","25岁","35+","年纪"],
  skill_gap:           ["技能","学习","培训","考证","学历","证书","不会","不懂","转行","没经验","经验","能力","技术","知识","充电","转型","0基础","入门","学什么","怎么学","提升自己"],
  self_improvement:    ["提升","成长","改变","进步","行动","自律","努力","坚持","早起","读书","健身","减肥","打卡","day","掌控","习惯","觉醒","突破","蜕变"],
  social_stigma:       ["丢人","没面子","看不起","嘲笑","废物","废人","啃老","家里蹲","宅","社交","朋友","家人","亲戚","结婚","对象","同学","聚会","比较","攀比"],
  coaching_needs:      ["教练","指导","课程","训练营","陪跑","规划","咨询","建议","怎么办","方法","出路","方向","职业规划","转型","1v1","一对一","带教","导师","mentor","求助","帮帮我"],
  job_type_reference:  ["公务员","考公","考研","考编","铁饭碗","国企","事业单位","大厂","互联网","外企","创业","自由职业","副业","自媒体","摆摊","送外卖","跑滴滴","开店","电商"],
};

const CAT_LABEL = {
  emotional_distress:  "😰 情绪焦虑/心理压力",
  financial_pressure:  "💰 经济压力/财务困境",
  job_search_frust:    "📋 求职挫败/简历面试",
  age_discrimination:  "🔢 年龄歧视/代际压力",
  skill_gap:           "📚 技能不足/学习提升",
  self_improvement:    "🌱 自我成长/行动力",
  social_stigma:       "👥 社会压力/面子问题",
  coaching_needs:      "🧭 教练/指导需求",
  job_type_reference:  "🏢 职业类型/行业参考",
};

const POS_WORDS  = ["加油","坚持","找到","上岸","offer","恭喜","好运","努力","希望","信心","好转","满意","不错","开心","高兴","感谢","有用","收获","成功","进步","突破","相信","可以的","会好的"];
const NEG_WORDS  = ["太难","焦虑","崩溃","绝望","想死","受不了","痛苦","失败","找不到","被拒","难受","完蛋","没戏","放弃","不行","没希望","废了","煎熬","折磨","垃圾","恶心","烦死","迷茫","无助","睡不着","失眠","活不下去"];

function safeStr(v) { return (v ?? "").toString().trim(); }
function pad(s, n) { s = String(s); while (s.length < n) s = " " + s; return s; }

function getCategories(text) {
  const t = safeStr(text); const hits = {};
  for (const [cat, words] of Object.entries(CAT_DICT))
    for (const w of words)
      if (t.includes(w)) { hits[cat] = (hits[cat]||0)+1; break; }
  return hits;
}

function getSentiment(text) {
  const t = safeStr(text);
  let pos = 0, neg = 0;
  for (const w of POS_WORDS) { const m = t.match(new RegExp(w,"g")); if(m) pos += m.length; }
  for (const w of NEG_WORDS) { const m = t.match(new RegExp(w,"g")); if(m) neg += m.length; }
  if (pos === 0 && neg === 0) return "neutral";
  if (pos > 0 && neg > 0) return "mixed";
  if (pos > neg) return "positive";
  return "negative";
}

// ─── Load Data ───────────────────────────────────────
const comments = [], contents = [];
for (const sub of SUBDIRS) {
  const dir = path.join(ROOT, sub);
  if (!fs.existsSync(dir)) continue;
  const files = fs.readdirSync(dir).filter(f => f.endsWith(".jsonl"));
  for (const f of files) {
    const raw = fs.readFileSync(path.join(dir, f), "utf8").trim();
    const lines = raw.split("\n");
    let n = 0;
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const obj = JSON.parse(line);
        // Detect comment vs content by fields
        if (obj.comment_id !== undefined) {
          // Normalize: unify field names
          if (obj.aweme_id && !obj.note_id) {
            obj.source_platform = "dy";
            obj.content_raw = obj.content;
          } else {
            obj.source_platform = "xhs";
          }
          comments.push(obj);
          n++;
        } else if (obj.note_id !== undefined) {
          contents.push(obj);
          n++;
        }
      } catch(_) {}
    }
    console.log(`  ${sub}/${f}: ${lines.length} lines -> ${n} parsed`);
  }
}
console.log(`\nTotal: comments=${comments.length}, contents=${contents.length}`);

// ─── Stats ───────────────────────────────────────────
const totalLikes = comments.reduce((s,r) => s + (parseInt(r.like_count)||0), 0);
const totalReplies = comments.reduce((s,r) => s + (parseInt(r.sub_comment_count)||0), 0);

// Category distribution
const catCounts = {}, catLikes = {};
for (const r of comments) {
  const cats = getCategories(r.content);
  for (const c of Object.keys(cats)) {
    catCounts[c] = (catCounts[c]||0) + 1;
    catLikes[c] = (catLikes[c]||0) + (parseInt(r.like_count)||0);
  }
}
const sortedCats = Object.entries(catCounts).sort((a,b) => b[1]-a[1]);

// Sentiment
const sentCounts = {positive:0, mixed:0, neutral:0, negative:0};
const sentLikes   = {positive:0, mixed:0, neutral:0, negative:0};
for (const r of comments) {
  const s = getSentiment(r.content);
  sentCounts[s]++; sentLikes[s] += (parseInt(r.like_count)||0);
}

// Top liked
const topLiked = [...comments].sort((a,b)=>(parseInt(b.like_count)||0)-(parseInt(a.like_count)||0)).slice(0,20);

// Coaching-need comments
const coachingNeed = comments.filter(r => {
  const cats = getCategories(r.content);
  return cats.coaching_needs || cats.self_improvement;
}).sort((a,b)=>(parseInt(b.like_count)||0)-(parseInt(a.like_count)||0)).slice(0,15);

// Bigrams (Chinese 2-char)
const bgCounts = {};
for (const r of comments) {
  const t = safeStr(r.content).replace(/[，。！？、；：""''（）【】《》\s\d\w]/g,"");
  for (let i=0; i<t.length-1; i++) {
    const bg = t.substring(i,i+2);
    if (/[\u4e00-\u9fff]{2}/.test(bg)) bgCounts[bg] = (bgCounts[bg]||0) + 1;
  }
}
const topBigrams = Object.entries(bgCounts).sort((a,b)=>b[1]-a[1]).slice(0,60);

// Length
const lenBins = {"1-10字":0, "11-30字":0, "31-60字":0, "61-100字":0, "100+字":0};
for (const r of comments) {
  const L = safeStr(r.content).length;
  if (L <= 10) lenBins["1-10字"]++;
  else if (L <= 30) lenBins["11-30字"]++;
  else if (L <= 60) lenBins["31-60字"]++;
  else if (L <= 100) lenBins["61-100字"]++;
  else lenBins["100+字"]++;
}

// Platform breakdown
const dyComments = comments.filter(r => r.source_platform === "dy");
const xhsComments = comments.filter(r => r.source_platform === "xhs");

// ─── Tag analysis (XHS contents) ─────────────────────
const tagCounts = {};
for (const r of contents) {
  const tags = safeStr(r.tag_list).split(",");
  for (const t of tags) {
    const tt = t.trim().replace(/^#/,"");
    if (tt) tagCounts[tt] = (tagCounts[tt]||0)+1;
  }
}
const topTags = Object.entries(tagCounts).sort((a,b)=>b[1]-a[1]).slice(0,30);

// Source keyword analysis
const kwCounts = {};
for (const r of contents) {
  const kw = safeStr(r.source_keyword).trim();
  if (kw) kwCounts[kw] = (kwCounts[kw]||0)+1;
}
const topSourceKw = Object.entries(kwCounts).sort((a,b)=>b[1]-a[1]).slice(0,20);

// ─── Build Report ────────────────────────────────────
const L = [];
const out = (s="") => L.push(s);

out("=".repeat(78));
out("  失业·求职·就业 评论数据分析报告");
out("  面向「失业教练」垂直产品设计");
out("=".repeat(78));
out("  分析时间: " + new Date().toISOString().replace("T"," ").slice(0,19));
out("  数据来源: 抖音(2条样例) + 小红书(1819条评论 + 100条笔记)");
out("  评论总数: " + comments.length + " 条");
out("  笔记/视频: " + contents.length + " 条");
out("  总点赞: " + totalLikes.toLocaleString());
out("  总回复: " + totalReplies.toLocaleString());
out("");

out("─".repeat(78));
out("  一、数据来源分布");
out("─".repeat(78));
out("  抖音(dy): " + dyComments.length + " 条评论 (仅样例)");
out("  小红书(xhs): " + xhsComments.length + " 条评论");
out("  小红书笔记/视频: " + contents.length + " 条");
out("");

out("─".repeat(78));
out("  二、话题关键词分类分布");
out("─".repeat(78));
out("  (一条评论可能命中多个类别，按命中条数降序)");
out("");
const maxCat = sortedCats.length > 0 ? sortedCats[0][1] : 1;
for (const [cat, cnt] of sortedCats) {
  const bar = "█".repeat(Math.round((cnt/maxCat)*30)).padEnd(30,"─");
  const pct = ((cnt/comments.length)*100).toFixed(1);
  out("  " + (CAT_LABEL[cat]||cat).padEnd(24) + " " + bar + "  " + pad(cnt,4) + "条 (" + pad(pct,5) + "%)  [赞" + (catLikes[cat]||0).toLocaleString() + "]");
}
out("");

out("─".repeat(78));
out("  三、情感倾向分布");
out("─".repeat(78));
const sentLabel = {positive:"😊 积极/希望", mixed:"🤔 复杂/矛盾", neutral:"😐 中性/陈述", negative:"😞 消极/绝望"};
const maxSent = Math.max(...Object.values(sentCounts));
for (const [s,cnt] of Object.entries(sentCounts)) {
  const bar = "█".repeat(Math.round((cnt/maxSent)*30)).padEnd(30,"─");
  const pct = ((cnt/comments.length)*100).toFixed(1);
  out("  " + (sentLabel[s]||s).padEnd(16) + bar + "  " + pad(cnt,4) + "条 (" + pad(pct,5) + "%)  [赞" + (sentLikes[s]||0).toLocaleString() + "]");
}
out("");

out("─".repeat(78));
out("  四、最高赞评论 TOP 20（洞察核心痛点与共鸣点）");
out("─".repeat(78));
for (let i=0; i<topLiked.length; i++) {
  const r = topLiked[i];
  const cats = Object.keys(getCategories(r.content));
  const catStr = cats.length ? cats.map(c=>CAT_LABEL[c]||c).join(", ") : "(未分类)";
  out("  #" + pad(i+1,2) + "  👍" + pad(r.like_count,6) + "  " + safeStr(r.nickname).padEnd(10) + " [" + (r.source_platform||"") + "]");
  out("      " + r.content);
  out("      → " + catStr);
}
out("");

out("─".repeat(78));
out("  五、教练需求评论 TOP 15（含「教练」「怎么办」「出路」「方向」「方法」等）");
out("─".repeat(78));
if (coachingNeed.length === 0) {
  out("  (未找到明确匹配)");
} else {
  for (let i=0; i<coachingNeed.length; i++) {
    const r = coachingNeed[i];
    out("  #" + pad(i+1,2) + "  👍" + pad(r.like_count,6) + "  " + r.content);
  }
}
out("");

out("─".repeat(78));
out("  六、高频词组 TOP 60（2字组合，反映热议焦点）");
out("─".repeat(78));
for (let i=0; i<topBigrams.length; i+=6) {
  const row = topBigrams.slice(i,i+6).map(([w,c])=>w+"("+c+")").join("  ");
  out("  " + row);
}
out("");

out("─".repeat(78));
out("  七、评论长度分布");
out("─".repeat(78));
const maxBin = Math.max(...Object.values(lenBins));
for (const [bin,cnt] of Object.entries(lenBins)) {
  const bar = "█".repeat(Math.round((cnt/maxBin)*30)).padEnd(30,"─");
  const pct = ((cnt/comments.length)*100).toFixed(1);
  out("  " + bin.padEnd(10) + bar + " " + pad(cnt,4) + "条 (" + pad(pct,5) + "%)");
}
out("");

// Content analysis
out("─".repeat(78));
out("  八、关联笔记/视频分析（小红书数据）");
out("─".repeat(78));
const totLike   = contents.reduce((s,r)=>s+(parseInt(r.liked_count)||0),0);
const totCollect= contents.reduce((s,r)=>s+(parseInt(r.collected_count)||0),0);
const totCmt    = contents.reduce((s,r)=>s+(parseInt(r.comment_count)||0),0);
out("  总点赞: " + totLike.toLocaleString() + "  总收藏: " + totCollect.toLocaleString() + "  总评论: " + totCmt.toLocaleString());
out("");

out("  搜索关键词分布:");
for (const [kw,cnt] of topSourceKw) {
  out("    \"" + kw + "\" → " + cnt + "条");
}
out("");

out("  热门话题标签 TOP 30:");
for (const [tag,cnt] of topTags) {
  out("    #" + tag + " (" + cnt + ")");
}
out("");

out("  笔记标题摘录 (前10):");
for (const r of contents.slice(0,10)) {
  const title = safeStr(r.title || r.desc || "").substring(0,80);
  out("    " + (title || "(无标题)"));
}
out("");

out("=".repeat(78));
out("  九、用户需求洞察与产品方向建议");
out("=".repeat(78));
out("");

const topCats = sortedCats.map(([c])=>c);
const INSIGHTS = {
  coaching_needs: [
    "用户明确表达了对教练/指导/规划的需求，这是最大的产品机会窗口",
    "现有的职业咨询太贵/太泛，缺乏「失业人群垂直教练」",
    "用户希望有人带着走、陪着练、给反馈",
  ],
  self_improvement: [
    "用户有强烈的改变意愿（自律、打卡、坚持高频出现）",
    "缺的是可持续的行动计划和 accountability 机制",
    "教练核心价值在于「陪伴+督促+纠偏」",
    "「小胜利」策略是让用户坚持下去的关键",
  ],
  emotional_distress: [
    "这是最深层的痛点——长期失业引发失眠、崩溃、绝望、自我怀疑",
    "用户需要的不仅是求职方法论，更是心理支持和信心重建",
    "产品必须内置心理疏导模块，而非纯技能培训",
    "「不是你不行，是市场不行」——认知重构是关键切入点",
  ],
  skill_gap: [
    "用户知道缺技能但不知道学什么、怎么学",
    "建议提供「岗位技能诊断→学习路径→实战项目」闭环",
    "可与在线课程结合，打造教练+课程组合产品",
  ],
  job_search_frust: [
    "简历石沉大海、已读不回、面试无反馈是日常",
    "用户需要的是「反馈」和「迭代指南」，而非泛泛建议",
    "教练核心服务：简历诊断→投递策略→面试模拟→拒信复盘",
  ],
  age_discrimination: [
    "年龄焦虑普遍，35岁/40岁是真实恐惧线",
    "用户需要看到「同龄人成功转型案例」和「非年龄敏感赛道」",
    "可设计「第二曲线/中年转型」专项产品线",
  ],
  social_stigma: [
    "社会/家庭压力显著——「丢人」「啃老」「废物」是高频自嘲词",
    "用户需要被理解、被接纳，教练首先要创造心理安全空间",
    "同伴社群是重要的产品设计要素，同路人效应极其重要",
  ],
  financial_pressure: [
    "经济压力紧迫，求职时间窗口窄",
    "建议设计「快速就业→稳定→转型」三阶段路径",
    "针对急需收入用户推出「短期陪跑计划」",
  ],
};

let printed = 0;
for (const cat of topCats) {
  if (printed >= 5) break;
  const tip = INSIGHTS[cat];
  if (tip) {
    out("  📌 " + (CAT_LABEL[cat]||cat));
    for (const line of tip) out("    " + line);
    out(""); printed++;
  }
}

out("  ─── 产品定位总结 ───");
out("");
out("  目标人群: 失业/求职中人群（被裁、应届待业、空窗期长、中年转型、裸辞）");
out("  核心价值: 不是又一个求职课程，而是「失业期的专属教练 — 陪你走出来的那个人」");
out("  差异化定位: 心理支持 + 求职实战 + 同伴监督 三位一体");
out("  建议 MVP: 1v1 线上陪跑教练（短周期4-6周）+ 同阶段社群 + AI 辅助工具");
out("");
out("  ─── 建议产品模块设计 ───");
out("");
out("  模块1 — 心理重建与信心恢复");
out("    • 认知行为练习（认知重构：不是你不行，是环境不对）");
out("    • 小胜利计划（每周一个可完成的微目标）");
out("    • 同伴支持小组（同阶段失业者互助圈）");
out("");
out("  模块2 — 求职陪跑");
out("    • 简历诊断与优化（每份简历逐字反馈）");
out("    • 投递策略制定（目标公司清单 + 每周投递计划）");
out("    • 面试模拟与复盘（mock + 拒信复盘）");
out("    • offer 评估与谈判指导");
out("");
out("  模块3 — 技能诊断与转型路径");
out("    • 目标岗位技能缺口诊断");
out("    • 个性化学习路径规划");
out("    • 实战项目推送（3天/7天/21天 mini 项目）");
out("");
out("  模块4 — 经济应急方案");
out("    • 快速过渡性工作推荐（兼职/外包/临时）");
out("    • 副业启动清单 + 最小启动方案");
out("    • 财务压力疏导与规划");
out("");
out("  模块5 — 社群运营");
out("    • 同阶段失业者互助小组（按失业时长/行业分）");
out("    • 每日打卡监督 + 成就墙");
out("    • 校友网络（找到工作的人回来分享）");
out("");

out("  ─── 教练产品关键设计原则 ───");
out("  1. 短周期承诺（4-6周起），降低决策门槛");
out("  2. 结果导向而非过程导向（明确每周可交付里程碑）");
out("  3. 价格可负担（针对经济压力人群设计梯度定价）");
out("  4. 强 accountability（教练每日/隔日 check-in，用户承诺行动）");
out("  5. 社群作为留存抓手（同路人效应 + 归属感）");
out("  6. 内容+服务双引擎（免费内容引流 → 付费教练转化）");
out("");

out("  ─── 内容营销方向(引流) ───");
out("  方向A: 真实失业日记 / 上岸故事 / 转型案例 → 建立信任");
out("  方向B: 求职技巧硬干货（简历模板、面试题库、行业薪资）→ 吸引精准流量");
out("  方向C: 心理/认知类内容（如何应对空窗期焦虑、自我价值重建）→ 引发共鸣传播");
out("  方向D: 教练过程记录（真实陪跑 case study）→ 展示产品价值");
out("");

out("=".repeat(78));
out("  报告结束");
out("=".repeat(78));

// ─── Write Outputs ───────────────────────────────────
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, {recursive:true});

const reportTxt = L.join("\n");
fs.writeFileSync(path.join(OUT_DIR, "full_analysis_report.txt"), reportTxt, "utf8");

fs.writeFileSync(path.join(OUT_DIR, "analysis_data.json"), JSON.stringify({
  meta: {
    total_comments: comments.length, total_contents: contents.length,
    total_likes: totalLikes, total_replies: totalReplies,
    dy_comments: dyComments.length, xhs_comments: xhsComments.length,
  },
  keyword_categories: sortedCats.map(([cat,cnt])=>({
    category: cat, label: CAT_LABEL[cat]||cat, count: cnt,
    pct: ((cnt/comments.length)*100).toFixed(1),
    likes: catLikes[cat]||0,
  })),
  sentiment: Object.entries(sentCounts).map(([s,cnt])=>({
    sentiment: s, count: cnt,
    pct: ((cnt/comments.length)*100).toFixed(1),
    likes: sentLikes[s]||0,
  })),
  top_liked: topLiked.map(r=>({
    content: r.content, like_count: r.like_count, nickname: r.nickname, platform: r.source_platform,
  })),
  coaching_potential: coachingNeed.map(r=>({
    content: r.content, like_count: r.like_count, platform: r.source_platform,
  })),
  top_bigrams: topBigrams.map(([w,c])=>({phrase:w, count:c})),
  length_distribution: lenBins,
  platform_breakdown: { dy: dyComments.length, xhs: xhsComments.length },
  content_tags: topTags.map(([t,c])=>({tag:t, count:c})),
  source_keywords: topSourceKw.map(([k,c])=>({keyword:k, count:c})),
}, null, 2), "utf8");

console.log("\n✅ Full analysis complete!");
console.log("   Report: " + path.join(OUT_DIR, "full_analysis_report.txt"));
console.log("   JSON:   " + path.join(OUT_DIR, "analysis_data.json"));
console.log("\n" + reportTxt);
