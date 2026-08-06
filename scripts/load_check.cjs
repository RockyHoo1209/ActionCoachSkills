const fs = require("fs"), path = require("path");

// ── 1. Load all JSONL files ──
const DIR = "data/reviews";
const files = fs.readdirSync(DIR).filter(f => f.endsWith(".jsonl"));
console.log("Found files:", files.join(", "));

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
    } catch (e) { /* skip parse errors */ }
  }
  console.log(`  ${f}: ${lines.length} lines -> ${n} loaded`);
}
console.log("\nTotal comments: " + comments.length + ", contents: " + contents.length);

// ── Check a few sample fields ──
console.log("\n--- Sample comment fields ---");
if (comments.length > 0) console.log(Object.keys(comments[0]).join(", "));
if (comments.length > 0) console.log("Content sample:", JSON.stringify(comments[0].content || "", null, 0).slice(0, 200));

console.log("\n--- Sample content fields ---");
if (contents.length > 0) console.log(Object.keys(contents[0]).join(", "));
