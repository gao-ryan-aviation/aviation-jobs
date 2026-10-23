# -*- coding: utf-8 -*-
"""看板层：生成单文件 HTML，数据内嵌，双击即可打开，也可直接发布到 GitHub Pages。"""
import json
import os
from datetime import datetime

from sources import FRIENDLY_LABELS, TYPE_LABELS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(BASE_DIR, "docs")
LATEST = os.path.join(BASE_DIR, "data", "jobs_latest.json")
HEALTH = os.path.join(BASE_DIR, "data", "source_health.json")

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>航空招聘追踪看板</title>
<style>
:root{
  --bg:#f6f7f9; --card:#fff; --border:#e3e6ea; --text:#1f2328;
  --muted:#6b7280; --accent:#1d4ed8; --ok:#15803d; --warn:#b45309;
  --bad:#b91c1c; --chip:#eef2ff;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);
 font-family:-apple-system,"PingFang SC","Microsoft YaHei",Segoe UI,sans-serif;font-size:14px}
header{background:var(--card);border-bottom:1px solid var(--border);padding:18px 24px}
h1{margin:0 0 4px;font-size:19px}
.sub{color:var(--muted);font-size:12px}
.wrap{max-width:1400px;margin:0 auto;padding:20px 24px 60px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:18px}
.card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.card .n{font-size:24px;font-weight:600;line-height:1.2}
.card .l{color:var(--muted);font-size:12px;margin-top:2px}
.filters{background:var(--card);border:1px solid var(--border);border-radius:10px;
 padding:14px 16px;margin-bottom:16px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.filters label{font-size:12px;color:var(--muted);margin-right:4px}
select,input[type=text]{border:1px solid var(--border);border-radius:6px;padding:6px 9px;
 font-size:13px;background:#fff;color:var(--text);font-family:inherit}
input[type=text]{min-width:220px}
.chk{display:flex;align-items:center;gap:5px;font-size:13px;color:var(--text)}
table{width:100%;border-collapse:collapse;background:var(--card);
 border:1px solid var(--border);border-radius:10px;overflow:hidden}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--border);vertical-align:top}
th{background:#fafbfc;font-size:12px;color:var(--muted);font-weight:600;white-space:nowrap}
tr:last-child td{border-bottom:none}
tbody tr:hover{background:#f9fafb}
.tag{display:inline-block;padding:2px 8px;border-radius:20px;font-size:11px;
 background:var(--chip);color:var(--accent);white-space:nowrap}
.tag.new{background:#dcfce7;color:var(--ok)}
.tag.upd{background:#fef3c7;color:var(--warn)}
.tag.off{background:#f1f2f4;color:var(--muted)}
.tag.bad{background:#fee2e2;color:var(--bad)}
.a{text-decoration:none;color:var(--accent)}
.a:hover{text-decoration:underline}
.snip{color:var(--muted);font-size:12px;max-width:420px}
.notice{background:#fffbeb;border:1px solid #fde68a;color:#92400e;
 padding:10px 14px;border-radius:8px;margin-bottom:16px;font-size:12.5px}
footer{color:var(--muted);font-size:12px;text-align:center;padding:20px}
.empty{padding:30px;text-align:center;color:var(--muted)}
details{background:var(--card);border:1px solid var(--border);border-radius:10px;
 padding:12px 16px;margin-top:18px}
summary{cursor:pointer;font-weight:600}
.hrow{display:grid;grid-template-columns:140px 90px 1fr;gap:8px;padding:6px 0;
 border-bottom:1px solid #f1f2f4;font-size:12.5px}
.hrow:last-child{border-bottom:none}
.ok{color:var(--ok)} .wj{color:var(--warn)} .wb{color:var(--bad)}
</style>
</head>
<body>
<header>
  <h1>全球航空 / 机场招聘追踪看板</h1>
  <div class="sub">数据更新：<b>__UPDATED__</b>　·
  覆盖 <b>__NCOUNT__</b> 个国家地区 · <b>__SCOUNT__</b> 家主体 ·
  规则：排除飞行员 / 排除派遣外包 / 仅保留面向中国籍招聘</div>
</header>

<div class="wrap">
  <div class="notice">
    ⚠️ 聚合站来源（航空英才网、职友集）标注为<b>非官方源</b>，可能夹带中介信息，投递前请回到航司/机场官网复核。
    本看板只做信息聚合，不构成任何招聘要约。
  </div>

  <div class="cards">
    <div class="card"><div class="n">__KEPT__</div><div class="l">在招岗位（过滤后）</div></div>
    <div class="card"><div class="n">__NEW__</div><div class="l">今日新增</div></div>
    <div class="card"><div class="n">__CHANGED__</div><div class="l">今日变化</div></div>
    <div class="card"><div class="n">__CLOSED__</div><div class="l">近期下架</div></div>
    <div class="card"><div class="n">__REJECT__</div><div class="l">按规则排除</div></div>
    <div class="card"><div class="n">__OKSRC__/__ALLSRC__</div><div class="l">数据源抓取成功</div></div>
  </div>

  <div class="filters">
    <div><label>主体类型</label><select id="fType"><option value="">全部</option></select></div>
    <div><label>国家/地区</label><select id="fCountry"><option value="">全部</option></select></div>
    <div><label>岗位类别</label><select id="fCat"><option value="">全部</option></select></div>
    <div><label>状态</label><select id="fStatus">
      <option value="">全部</option>
      <option value="NEW">仅新增</option>
      <option value="UPDATED">仅变化</option>
      <option value="ONGOING">在招</option>
      <option value="CLOSED">已下架</option>
    </select></div>
    <div><label>中国籍友好</label><select id="fFriendly">
      <option value="">全部</option>
      <option value="high">高</option>
      <option value="medium">中</option>
      <option value="low">需当地工作权</option>
    </select></div>
    <div><input type="text" id="fText" placeholder="搜索岗位/主体/关键词…"></div>
    <label class="chk"><input type="checkbox" id="fDiscard"> 显示被排除的</label>
    <span id="count" style="color:#6b7280;font-size:12px"></span>
  </div>

  <table id="tbl">
    <thead><tr>
      <th style="width:110px">主体</th>
      <th style="width:200px">岗位</th>
      <th style="width:90px">类别</th>
      <th style="width:100px">国家/地区</th>
      <th style="width:110px">中国籍友好</th>
      <th style="width:70px">状态</th>
      <th>摘要</th>
    </tr></thead>
    <tbody></tbody>
  </table>
  <div class="empty" id="empty" style="display:none">没有符合条件的岗位。</div>

  <details>
    <summary>数据源抓取健康度（用于排查哪些主体没抓到）</summary>
    <div id="health"></div>
  </details>
</div>

<footer>由 GitHub Actions 每日自动生成 · 新增/变化/下架 三态增量比对</footer>

<script>
const DATA = __DATA__;
const HEALTH = __HEALTH__;
const TL = __TL__, FL = __FL__;

const $ = s => document.querySelector(s);
const tbody = document.querySelector("#tbl tbody");

function fillSelect(el, values){
  values.forEach(v => {
    const o = document.createElement("option");
    o.value = v; o.textContent = v; el.appendChild(o);
  });
}
fillSelect($("#fType"), [...new Set(DATA.map(r=>TL[r.source_type]||r.source_type))].filter(Boolean).sort());
fillSelect($("#fCountry"), [...new Set(DATA.map(r=>r.country))].filter(Boolean).sort());
fillSelect($("#fCat"), [...new Set(DATA.map(r=>r.category))].filter(Boolean).sort());

function statusTag(s){
  const m = {NEW:["new","新增"], UPDATED:["upd","变化"], ONGOING:["","在招"], CLOSED:["off","下架"]};
  const [c,t] = m[s] || ["",""];
  return `<span class="tag ${c}">${t}</span>`;
}

function render(){
  const ft = $("#fType").value, fc = $("#fCountry").value, fcat = $("#fCat").value,
        fs = $("#fStatus").value, ff = $("#fFriendly").value,
        txt = $("#fText").value.trim().toLowerCase(),
        showDiscard = $("#fDiscard").checked;

  const rows = DATA.filter(r => {
    if(!showDiscard && !r.kept) return false;
    if(ft && (TL[r.source_type]||r.source_type) !== ft) return false;
    if(fc && r.country !== fc) return false;
    if(fcat && r.category !== fcat) return false;
    if(fs && r.status !== fs) return false;
    if(ff && r.source_friendly !== ff) return false;
    if(txt){
      const blob = `${r.source} ${r.title} ${r.snippet}`.toLowerCase();
      if(!blob.includes(txt)) return false;
    }
    return true;
  });

  // 新增优先，其次在招，再其次变化，最后下架
  const order = {NEW:0, ONGOING:1, UPDATED:2, CLOSED:3};
  rows.sort((a,b) => (order[a.status]??9) - (order[b.status]??9));

  tbody.innerHTML = rows.map(r => `<tr>
    <td>${r.source}</td>
    <td><a class="a" href="${r.url}" target="_blank" rel="noopener">${r.title}</a></td>
    <td><span class="tag">${r.category}</span></td>
    <td>${r.country}</td>
    <td>${FL[r.source_friendly]||r.source_friendly}</td>
    <td>${statusTag(r.status)}</td>
    <td class="snip">${r.snippet || (r.reject_reason ? `<span class="tag bad">${r.reject_reason}</span>` : "")}</td>
  </tr>`).join("");

  $("#count").textContent = `显示 ${rows.length} / ${DATA.length} 条`;
  $("#empty").style.display = rows.length ? "none" : "block";
}

["#fType","#fCountry","#fCat","#fStatus","#fFriendly","#fText","#fDiscard"]
  .forEach(s => $(s).addEventListener("input", render));

// 健康度
$("#health").innerHTML = HEALTH.length ? HEALTH.map(h => {
  const cls = h.ok ? "ok" : (h.status === 403 || h.status === 429 ? "wj" : "wb");
  return `<div class="hrow"><div>${h.name}</div>
    <div class="${cls}">${h.ok ? "成功" : ("失败 " + (h.status||"ERR"))}</div>
    <div style="color:#6b7280">${h.note||""} · ${h.candidates??0} 条候选</div></div>`;
}).join("") : "<div class='empty'>暂无数据</div>";

render();
</script>
</body>
</html>
"""


def render(records, health=None, stats=None, out_path=None):
    os.makedirs(DOCS, exist_ok=True)
    out_path = out_path or os.path.join(DOCS, "index.html")

    stats = stats or {}
    kept = [r for r in records if r.get("kept")]
    countries = {r["country"] for r in records if r.get("country")}

    def dump(o):
        return (json.dumps(o, ensure_ascii=False)
                .replace("</", "<\\/").replace("<!--", "<\\!--"))

    updated_at = stats.get("date") or datetime.now().strftime("%Y-%m-%d")
    nsrc = stats.get("all_sources", 0)

    html = (TEMPLATE
            .replace("__DATA__", dump(records))
            .replace("__HEALTH__", dump(health or []))
            .replace("__TL__", dump(TYPE_LABELS))
            .replace("__FL__", dump(FRIENDLY_LABELS))
            .replace("__UPDATED__", updated_at)
            .replace("__CHANGED__", str(stats.get("updated", 0)))
            .replace("__KEPT__", str(len(kept)))
            .replace("__NEW__", str(stats.get("new", 0)))
            .replace("__CLOSED__", str(stats.get("closed", 0)))
            .replace("__REJECT__", str(stats.get("rejected", 0)))
            .replace("__OKSRC__", str(stats.get("ok_sources", 0)))
            .replace("__ALLSRC__", str(nsrc))
            .replace("__NCOUNT__", str(len(countries)))
            .replace("__SCOUNT__", str(nsrc)))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path
