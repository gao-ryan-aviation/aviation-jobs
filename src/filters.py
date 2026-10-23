# -*- coding: utf-8 -*-
"""过滤与打标层：把抓取到的原始条目变成可投递判断的岗位记录。

三条核心规则对应需求：
  1. 岗位类型不含飞行员
  2. 用工形式不接受派遣制/外包
  3. 只保留面向中国人（中国籍）招聘、可驻外的岗位
"""
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_PATH = os.path.join(BASE_DIR, "config", "rules.json")


def load_rules(path=RULES_PATH):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _hit(text, words):
    """返回命中的词列表，大小写不敏感。"""
    low = text.lower()
    return [w for w in words if w.lower() in low]


def _all_words(rule_block):
    return (rule_block.get("zh") or []) + (rule_block.get("en") or [])


def judge(text, rules):
    """对一条岗位文本做判定，返回结构化结果。"""
    pilot_hits = _hit(text, _all_words(rules["exclude_pilot"]))
    exc_hits = _hit(text, _all_words(rules["pilot_exception"]))
    disp_hits = _hit(text, _all_words(rules["exclude_dispatch"]))
    pos_hits = _hit(text, _all_words(rules["china_target_positive"]))
    neg_hits = _hit(text, _all_words(rules["china_target_negative"]))
    noise_hits = _hit(text, _all_words(rules.get("exclude_noise", {})))

    # 规则1：飞行员剔除，但命中例外词时保留（如"负责外籍飞行员招聘"的HR岗）
    is_pilot = bool(pilot_hits) and not exc_hits
    # 规则2：派遣/外包剔除
    is_dispatch = bool(disp_hits)
    # 规则3：中国籍友好度打分
    china_score = len(pos_hits) - len(neg_hits)

    category = classify_category(text, rules["categories"])

    return {
        "is_pilot": is_pilot,
        "is_dispatch": is_dispatch,
        "is_noise": bool(noise_hits),
        "china_score": max(-3, min(3, china_score)),
        "category": category,
        "hits": {
            "pilot": pilot_hits,
            "pilot_exception": exc_hits,
            "dispatch": disp_hits,
            "noise": noise_hits,
            "china_positive": pos_hits,
            "china_negative": neg_hits,
        },
    }


def classify_category(text, categories):
    """按 categories 定义顺序匹配岗位类别。"""
    for cat in ["乘务", "地面服务", "货运物流", "机务维修",
                "运行保障", "市场销售", "职能支持"]:
        words = categories.get(cat) or []
        if _hit(text, words):
            return cat
    return "其他"


def passes(judgement, source_friendly, source_country=""):
    """最终是否保留。

    分三档判定，避免"一刀切"造成的漏召或过召：
      · 中国内地主体：默认就在招中国人，只要不是飞行员/派遣即可
      · 境外主体且标注中国籍友好=high：允许 china_score=0
        （官网列表页常常不重复写"中国籍"，专场信息在详情页）
      · 其余境外主体：必须有明确的中国籍正向信号
    任一份明确要求当地工作权（china_score<0）则一律剔除。
    """
    if judgement["is_pilot"] or judgement["is_dispatch"]:
        return False
    if judgement.get("is_noise"):
        return False
    if judgement["china_score"] < 0:
        return False
    if source_country == "中国内地":
        return True
    if source_friendly == "high":
        return judgement["china_score"] >= 0
    return judgement["china_score"] >= 1


def build_record(source, candidate, date_str, rules):
    blob = f"{candidate.get('title','')} {candidate.get('snippet','')}"
    j = judge(blob, rules)
    rec = {
        "id": stable_id(source["name"], candidate["url"], candidate["title"]),
        "source": source["name"],
        "source_type": source["type"],
        "country": source["country"],
        "title": candidate["title"],
        "url": candidate["url"],
        "snippet": candidate.get("snippet", ""),
        "category": j["category"],
        "china_score": j["china_score"],
        "source_friendly": source.get("china_friendly", "na"),
        "kept": passes(j, source.get("china_friendly", "na"),
                       source.get("country", "")),
        "reject_reason": reject_reason(j),
        "first_seen": date_str,
        "last_seen": date_str,
        "status": "NEW",
    }
    return rec


def reject_reason(j):
    if j["is_pilot"]:
        return "飞行员岗位（按需求排除）"
    if j["is_dispatch"]:
        return "派遣/外包用工（按需求排除）"
    if j.get("is_noise"):
        return "非岗位信息（公告/声明/下载）"
    if j["china_score"] < 0:
        return f"疑似要求当地工作权（命中：{', '.join(j['hits']['china_negative'][:3])}）"
    return ""


def stable_id(source_name, url, title):
    import hashlib
    raw = f"{source_name}|{url}|{title[:60]}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def dedupe(records):
    """按 id 去重，保留信息更完整的一条。"""
    best = {}
    for r in records:
        cur = best.get(r["id"])
        if cur is None or len(r.get("snippet", "")) > len(cur.get("snippet", "")):
            best[r["id"]] = r
    return list(best.values())
