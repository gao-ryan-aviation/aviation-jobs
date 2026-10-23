# -*- coding: utf-8 -*-
"""航空/机场招聘追踪 —— 每日增量流水线入口。

用法：
    python run.py                 # 全量抓取 + 过滤 + 增量比对 + 生成看板
    python run.py --limit 10      # 只跑前 10 个主体（调试用）
    python run.py --no-network    # 不联网，仅用 manual_feed.json 重建看板
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import fetchers                                    # noqa: E402
import filters                                     # noqa: E402
import diff                                        # noqa: E402
import dashboard                                   # noqa: E402
from sources import load_sources                   # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
MANUAL_FEED = os.path.join(BASE, "manual_feed.json")
MAX_WORKERS = 12


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_manual_feed():
    """读取人工/AI 补充的岗位（我或你在查证后手工录入）。"""
    if not os.path.exists(MANUAL_FEED):
        return []
    try:
        with open(MANUAL_FEED, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"manual_feed 解析失败: {e}")
        return []


def crawl_source(src, rules, session):
    """抓取单个主体，返回 (records, health_entry)。"""
    cfg = rules.get("fetch", {})
    name, url, method = src["name"], src["url"], src["method"]
    health = {"name": name, "url": url, "method": method,
              "ok": False, "status": None, "note": "", "candidates": 0}

    if method == "manual":
        health["note"] = "标记为人工维护，跳过自动抓取"
        return [], health

    delay = cfg.get("delay_between_requests", 1.0)
    html, err = fetchers.fetch_static(
        url, timeout=cfg.get("timeout", 25),
        retries=cfg.get("retries", 2), session=session)
    health["status"] = 200 if html else None

    # L2：静态内容过短，疑似 JS 渲染，走阅读代理
    used_jina = False
    if html and len(html) < 4000 and cfg.get("jina_enabled", True):
        jtext, jerr = fetchers.fetch_jina(url, cfg=cfg)
        if jtext and len(jtext) > len(html):
            html = jtext
            used_jina = True
            health["note"] = "经阅读代理渲染"

    if not html:
        health["ok"] = False
        health["note"] = err or "抓取失败"
        return [], health

    cands = (fetchers.extract_from_text(html, url)
             if used_jina
             else fetchers.extract_candidates(html, url, rules["job_keywords"]))
    time.sleep(delay)

    # L3：搜索引擎补漏（仅对高/中友好度主体）
    if cfg.get("ddg_enabled") and src["china_friendly"] in ("high", "medium"):
        extra = fetchers.fetch_ddg(f"{name} 招聘 2026",
                                   timeout=cfg.get("timeout", 25), cfg=cfg)
        seen = {c["url"] for c in cands}
        for title, href in extra:
            if href not in seen:
                cands.append({"title": title, "url": href, "snippet": ""})
                seen.add(href)

    health["candidates"] = len(cands)
    health["ok"] = True
    if not health["note"]:
        health["note"] = "静态抓取成功" if method == "static" else "抓取成功"

    records = [filters.build_record(src, c, TODAY, rules) for c in cands]
    return records, health


TODAY = datetime.now().strftime("%Y-%m-%d")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 个主体")
    ap.add_argument("--no-network", action="store_true", help="跳过联网抓取")
    ap.add_argument("--sources", default="sources.csv")
    args = ap.parse_args()

    log("载入主体库与规则")
    rules = filters.load_rules()
    sources, errs = load_sources(os.path.join(BASE, args.sources))
    for e in errs:
        log("  ! " + e)
    log(f"已启用 {len(sources)} 家主体")

    all_records, health = [], []

    if not args.no_network:
        items = sources[:args.limit] if args.limit else sources
        log(f"开始并发抓取 {len(items)} 个主体（并发 {MAX_WORKERS}）")
        from concurrent.futures import ThreadPoolExecutor
        import threading
        local = threading.local()

        def get_session():
            if not hasattr(local, "s"):
                local.s = requests.Session()
            return local.s

        def wrapped(src):
            try:
                return crawl_source(src, rules, get_session())
            except Exception as e:
                return [], {"name": src["name"], "url": src["url"],
                            "method": src.get("method"), "ok": False,
                            "status": None,
                            "note": f"异常 {type(e).__name__}: {str(e)[:40]}",
                            "candidates": 0}

        done = 0
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            for recs, h in ex.map(wrapped, items):
                done += 1
                all_records.extend(recs)
                health.append(h)
                if done % 10 == 0 or done == len(items):
                    log(f"  进度 {done}/{len(items)} | 累计候选 {len(all_records)} 条")
    else:
        log("跳过联网抓取（--no-network）")

    # 合并人工/AI 补充数据
    for item in load_manual_feed():
        pseudo = {
            "name": item.get("source", "人工补充"),
            "type": item.get("type", "airline_pax"),
            "country": item.get("country", ""),
            "category": "",
            "url": item.get("url", ""),
            "method": "manual",
            "china_friendly": item.get("china_friendly", "high"),
            "notes": "人工核实",
        }
        cand = {"title": item.get("title", ""), "url": item.get("url", ""),
                "snippet": item.get("snippet", "")}
        all_records.append(filters.build_record(pseudo, cand, TODAY, rules))
        if not any(h["name"] == pseudo["name"] for h in health):
            health.append({"name": pseudo["name"], "url": pseudo["url"],
                           "method": "manual", "ok": True, "status": None,
                           "note": "人工核实录入", "candidates": 1})

    all_records = filters.dedupe(all_records)

    ok_sources = sum(1 for h in health if h["ok"])
    stats = diff.diff_and_save(all_records, TODAY)
    stats["ok_sources"] = ok_sources
    stats["all_sources"] = len(sources)

    with open(os.path.join(BASE, "data", "source_health.json"),
              "w", encoding="utf-8") as f:
        json.dump(health, f, ensure_ascii=False, indent=2)

    out = dashboard.render(all_records, health, stats)
    log(f"看板已生成: {out}")
    log(f"统计: 抓取成功 {ok_sources}/{len(sources)} 源 | "
        f"候选项 {stats['total_seen']} 条 | 保留 {stats['kept']} 条 | "
        f"新增 {stats['new']} | 变化 {stats['updated']} | "
        f"排除 {stats['rejected']}")


def _has_requests():
    try:
        import requests  # noqa: F401
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    import requests  # noqa: E402  (顶层依赖，缺失则直接报错更清晰)
    main()
