# -*- coding: utf-8 -*-
"""增量层：与昨日快照比对，标记 新增 / 变化 / 下架，避免每天看重复内容。"""
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DAILY_DIR = os.path.join(DATA_DIR, "daily")
LATEST = os.path.join(DATA_DIR, "jobs_latest.json")


def _load(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def diff_and_save(current_records, date_str=None, keep_days=30):
    """比对并落盘。返回统计字典。"""
    os.makedirs(DAILY_DIR, exist_ok=True)
    today = date_str or datetime.now().strftime("%Y-%m-%d")

    prev = {r["id"]: r for r in _load(LATEST)}
    cur = {r["id"]: r for r in current_records}

    new_ids, updated_ids, closed_ids = [], [], []

    for rid, rec in cur.items():
        if rid not in prev:
            rec["status"] = "NEW"
            rec["first_seen"] = today
            rec["last_seen"] = today
            new_ids.append(rid)
        else:
            old = prev[rid]
            rec["first_seen"] = old.get("first_seen", today)
            rec["last_seen"] = today
            changed = (old.get("title") != rec.get("title")
                       or old.get("url") != rec.get("url"))
            rec["status"] = "UPDATED" if changed else "ONGOING"
            if changed:
                updated_ids.append(rid)

    for rid, old in prev.items():
        if rid not in cur:
            # 已下架的岗位保留一条记录，便于追踪
            old = dict(old)
            old["status"] = "CLOSED"
            old["last_seen"] = old.get("last_seen", today)
            closed_ids.append(rid)
            current_records.append(old)

    _save(os.path.join(DAILY_DIR, f"{today}.json"), current_records)
    _save(LATEST, current_records)

    # 清理过期快照
    try:
        files = sorted(f for f in os.listdir(DAILY_DIR) if f.endswith(".json"))
        for f in files[:-keep_days]:
            os.remove(os.path.join(DAILY_DIR, f))
    except Exception:
        pass

    kept = [r for r in current_records if r.get("kept")]
    stats = {
        "date": today,
        "total_seen": len(cur),
        "kept": len(kept),
        "new": len(new_ids),
        "updated": len(updated_ids),
        "closed": len(closed_ids),
        "rejected": len(cur) - len(kept),
    }
    return stats
