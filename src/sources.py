# -*- coding: utf-8 -*-
"""读取并校验主体库 sources.csv。

用户后期只需在 GitHub 网页上编辑 sources.csv 增加一行即可接入新主体，
无需改代码。字段缺失或填写非法时会给出可读错误而不是崩溃。
"""
import csv
import os

REQUIRED_FIELDS = ["name", "type", "country", "url"]
VALID_TYPES = {"airline_pax", "airline_cargo", "airport",
               "ground_handler", "aggregator"}
VALID_METHODS = {"static", "js", "ats", "manual", "search"}
VALID_FRIENDLY = {"high", "medium", "low", "na"}


def load_sources(path="sources.csv"):
    """返回 (sources, errors)。errors 为不影响主流程的提示信息列表。"""
    if not os.path.exists(path):
        return [], [f"主体库文件不存在: {path}"]

    sources, errors = [], []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # 表头占第1行
            row = {k: (v or "").strip() for k, v in row.items() if k}

            missing = [k for k in REQUIRED_FIELDS if not row.get(k)]
            if missing:
                errors.append(f"第{i}行缺少必填字段 {missing}，已跳过")
                continue

            if row.get("enabled", "1") not in ("1", "true", "True", "yes"):
                continue

            stype = row.get("type", "").lower()
            if stype not in VALID_TYPES:
                errors.append(f"第{i}行 type='{stype}' 非法，已跳过")
                continue

            method = row.get("method", "static").lower()
            if method not in VALID_METHODS:
                errors.append(f"第{i}行 method='{method}' 非法，已按 static 处理")
                method = "static"

            friendly = row.get("china_friendly", "na").lower()
            if friendly not in VALID_FRIENDLY:
                friendly = "na"

            sources.append({
                "name": row["name"],
                "type": stype,
                "country": row.get("country", ""),
                "category": row.get("category", ""),
                "url": row["url"],
                "method": method,
                "china_friendly": friendly,
                "notes": row.get("notes", ""),
            })
    return sources, errors


TYPE_LABELS = {
    "airline_pax": "客运航司",
    "airline_cargo": "货运航司",
    "airport": "机场",
    "ground_handler": "地服公司",
    "aggregator": "聚合/代理源",
}

FRIENDLY_LABELS = {
    "high": "中国籍友好·高",
    "medium": "中国籍友好·中",
    "low": "需当地工作权",
    "na": "未知",
}

if __name__ == "__main__":
    srcs, errs = load_sources()
    print(f"已启用主体 {len(srcs)} 家")
    for e in errs:
        print("  !", e)
    from collections import Counter
    print(Counter(s["type"] for s in srcs))
