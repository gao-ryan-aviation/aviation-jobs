# -*- coding: utf-8 -*-
"""抓取层：多层降级 + 岗位级条目提取。

降级顺序：
  L1 static  —— requests 直接取 HTML
  L2 jina    —— 公共阅读代理渲染 JS 页面（云端可用，有限流）
  L3 ddg     —— DuckDuckGo HTML 端点做搜索引擎补漏

提取原则：只认「招聘公告级」条目（招聘简章/招聘公告/Vacancy/Now Hiring），
丢弃栏目入口、下载附件、导航链接——这是保证看板可读性的关键。
"""
import random
import re
import time
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# 栏目入口标题：这些不是具体岗位，直接丢弃
NAV_TITLES = {
    "校园招聘", "社会招聘", "飞行员招聘", "乘务安全员招聘", "其他招聘", "人才招聘",
    "招聘信息", "招聘", "招聘职位", "招聘岗位", "职位", "职位空缺", "职位搜索",
    "加入我们", "招贤纳士", "诚聘英才", "工作机会", "更多", "查看更多", "更多>>",
    "careers", "career", "jobs", "job", "job opportunities", "career opportunities",
    "search jobs", "all jobs", "all open positions", "view all jobs", "open positions",
    "open roles", "current vacancies", "vacancies", "work with us", "join us",
}

# 明显不是岗位的标题片段
BAD_TITLE_PAT = re.compile(
    r"(查看更多|更多\s*[›>»]|立即下载|点击下载|下载$|附件|常见问题|法律声明|隐私|"
    r"关于我们|关于.{0,6}公司|联系我们|网站地图|免责声明|使用条款|cookie|"
    r"privacy|terms|sitemap|contact us|about us|cookie policy|sign in|log ?in|"
    r"register|subscribe|newsletter|follow us)", re.I)

# 附件/静态资源路径
BAD_URL_PAT = re.compile(
    r"(/download/|/images?/|/static/|/assets?/|/upload/|/question/|/faq|"
    r"/privacy|/legal|/sitemap|\.(pdf|docx?|xlsx?|zip|rar|jpe?g|png|gif|mp4)(\?|$))", re.I)

# 强信号：出现即认为是招聘公告
STRONG_ZH = ["招聘简章", "招聘公告", "招聘启事", "招聘信息", "招聘岗位",
             "诚聘", "招募", "招录", "招聘计划", "人才引进", "校园招聘简章"]
STRONG_EN = ["job opening", "open position", "now hiring", "we are hiring",
             "apply now", "vacancy", "vacancies", "job description",
             "recruitment", "career opportunity", "join our team"]

# 弱信号：需配合长度判断，避免把栏目页当岗位
WEAK = ["招聘", "职位", "岗位", "job", "career", "position", "opening", "apply", "hiring"]

# 导航词表：若标题去掉标点后只剩这些词，说明是栏目入口而非具体岗位。
# 用分词法而非穷举黑名单，能自动覆盖 "Search for vacancies" 这类未见过的组合。
NAV_WORDS = {
    "招聘", "招聘信息", "人才招聘", "招聘公告", "校园招聘", "社会招聘", "职位", "岗位",
    "工作", "机会", "加入", "我们", "更多", "查看", "详情", "全部", "所有", "搜索",
    "job", "jobs", "career", "careers", "vacancy", "vacancies", "position", "positions",
    "opening", "openings", "opportunity", "opportunities", "role", "roles", "work",
    "with", "us", "our", "the", "for", "and", "at", "all", "view", "search", "go", "to",
    "explore", "apply", "now", "current", "available", "join", "team", "office", "head",
    "center", "centre", "contact", "help", "info", "home", "internship", "graduate",
    "global", "international", "candidate", "candidates", "vacature", "stellenangebote",
}

_WS = re.compile(r"\s+")


def _headers():
    return {
        "User-Agent": random.choice(UA_POOL),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }


def fetch_static(url, timeout=18, retries=1, session=None):
    """L1：直接取 HTML。返回 (html, err)。"""
    s = session or requests
    last = None
    for attempt in range(retries + 1):
        try:
            r = s.get(url, headers=_headers(), timeout=timeout)
            if r.status_code == 200:
                r.encoding = r.apparent_encoding or r.encoding
                return r.text, None
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:80]}"
        if attempt < retries:
            time.sleep(1.0 * (attempt + 1))
    return None, last


def fetch_jina(url, timeout=45, cfg=None):
    """L2：经公共阅读代理渲染 JS。返回 (text, err)。"""
    if not (cfg or {}).get("jina_enabled", True):
        return None, "jina 已关闭"
    endpoint = cfg.get("jina_prefix", "https://r.jina.ai/") + url
    try:
        r = requests.get(endpoint, headers=_headers(), timeout=timeout)
        if r.status_code == 200:
            return r.text, None
        return None, f"jina HTTP {r.status_code}"
    except Exception as e:
        return None, f"jina {type(e).__name__}: {str(e)[:60]}"


def fetch_ddg(query, timeout=20, cfg=None, limit=8):
    """L3：搜索引擎补漏，返回 [(title, url)]。"""
    if not (cfg or {}).get("ddg_enabled", False):
        return []
    endpoint = cfg.get("ddg_endpoint", "https://html.duckduckgo.com/html/")
    try:
        r = requests.post(endpoint, data={"q": query},
                          headers=_headers(), timeout=timeout)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.text, "html.parser")
        out = []
        for a in soup.select("a.result__a"):
            href = a.get("href", "")
            m = re.search(r"uddg=([^&]+)", href)
            if m:
                href = unquote(m.group(1))
            title = _clean(a.get_text(" "))
            if href.startswith("http") and title:
                out.append((title, href))
            if len(out) >= limit:
                break
        return out
    except Exception:
        return []


def _clean(s):
    return _WS.sub(" ", (s or "")).strip()


def _norm_title(t):
    return re.sub(r"[\s\-–—_·|:：]+", "", t).lower()


def _same_site(url, base_url):
    """是否与入口页同子域（避免跨站导航链接混入）。"""
    a, b = urlparse(url).netloc.lower(), urlparse(base_url).netloc.lower()
    if not a or not b:
        return True
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def _is_nav_only(title):
    """标题是否只由导航词构成（栏目入口，不是具体岗位）。"""
    low = title.lower()
    # 中文：去掉通用词后若无实质内容
    zh = re.findall(r"[\u4e00-\u9fff]+", title)
    en = re.findall(r"[a-zA-Z]+", low)
    if zh:
        if all(w in NAV_WORDS for w in zh):
            return True
    if en and not zh:
        if all(w in NAV_WORDS for w in en):
            return True
    return False


def _is_job_title(title):
    """标题是否像一条具体的招聘公告。"""
    low = title.lower()
    if len(title) < 6 or len(title) > 140:
        return False
    if _norm_title(title) in {_norm_title(x) for x in NAV_TITLES}:
        return False
    if _is_nav_only(title):
        return False
    if BAD_TITLE_PAT.search(title):
        return False
    if any(k in title for k in STRONG_ZH):
        return True
    if any(k in low for k in STRONG_EN):
        return True
    # 弱信号：中文标题需 >=10 字，英文 >=20 字符，避免"社会招聘"这类栏目
    if any(k in low for k in WEAK):
        enough = (len(title) >= 10 if re.search(r"[\u4e00-\u9fff]", title)
                  else len(title) >= 20)
        # 还须含具体岗位名词，否则多是"Explore Job Openings"之类栏目入口
        return enough and bool(_hit_role(title, low))
    return False


# 岗位名词：用来区分"具体岗位"与"招聘栏目入口"
ROLE_ZH = ["乘务", "安全员", "空乘", "专员", "主管", "经理", "助理", "工程师", "技术员",
          "技师", "调度", "签派", "地服", "值机", "行李", "货运", "物流", "销售", "市场",
          "客服", "行政", "财务", "法务", "合规", "采购", "运营", "运行", "维修", "机务",
          "学员", "实习生", "见习", "主任", "服务", "保障", "操作", "代表", "队长", "组长",
          "班长", "顾问", "秘书", "会计", "出纳", "翻译", "安检", "护卫", "监护", "装卸",
          "搬运", "分拣", "单证", "报关", "监装", "招聘", "招聘简章", "招聘公告"]
ROLE_EN = ["crew", "officer", "engineer", "technician", "manager", "specialist",
           "analyst", "agent", "supervisor", "coordinator", "assistant", "attendant",
           "handler", "controller", "dispatcher", "representative", "executive",
           "intern", "trainee", "graduate", "apprentice", "operator", "driver",
           "loader", "ramp", "cargo", "sales", "service", "security", "screener",
           "mechanic", "planner", "customs", "documentation"]


def _hit_role(title, low):
    if any(k in title for k in ROLE_ZH):
        return True
    return any(k in low for k in ROLE_EN)


def extract_candidates(html, base_url, job_keywords=None, cap=40):
    """从 HTML 中提取「招聘公告级」条目。

    返回 [{title, url, snippet}]，按标题去重，单源最多 cap 条。
    """
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    out, seen = [], set()

    for a in soup.find_all("a", href=True):
        try:
            url = urljoin(base_url, a["href"])
        except Exception:
            continue
        if urlparse(url).scheme not in ("http", "https"):
            continue
        if BAD_URL_PAT.search(url):
            continue
        if not _same_site(url, base_url):
            continue

        title = _clean(a.get_text(" "))
        if not _is_job_title(title):
            continue

        parent = a.find_parent(["li", "tr", "div", "article", "section", "td"])
        snippet = _clean(parent.get_text(" "))[:240] if parent else ""
        if snippet.startswith(title):
            snippet = snippet[len(title):].strip()

        key = _norm_title(title)[:50]
        if key in seen:
            continue
        seen.add(key)

        out.append({"title": title[:140], "url": url, "snippet": snippet})
        if len(out) >= cap:
            break
    return out


def extract_from_text(text, base_url, cap=40):
    """从阅读代理返回的 markdown/纯文本中提取条目（链接形如 [标题](URL)）。"""
    if not text:
        return []
    out, seen = [], set()
    for m in re.finditer(r"\[([^\]]{6,140})\]\((https?://[^\s\)]+)\)", text):
        title, url = _clean(m.group(1)), m.group(2)
        if BAD_URL_PAT.search(url) or not _is_job_title(title):
            continue
        key = _norm_title(title)[:50]
        if key in seen:
            continue
        seen.add(key)
        out.append({"title": title, "url": url, "snippet": ""})
        if len(out) >= cap:
            break
    return out
