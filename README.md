# 全球航空 / 机场招聘追踪看板

自动追踪全球较大规模航空公司（含货运航司）、机场与地服公司**面向中国籍/中国人**的招聘信息，  
每天自动生成增量看板网页。整个系统运行在 GitHub 云端，**换任何一台电脑都能用**。

## 三条核心过滤规则

对应需求设定，改规则不用改代码，编辑 `config/rules.json` 即可：

1. **不含飞行员岗位** —— 命中飞行员/机长/副驾驶/Pilot 等词即剔除
   - 例外保护：命中"招聘专员/人力资源/Recruiter"等词时保留  
     （例如"负责外籍飞行员招聘的人力资源岗"不该被误杀）
2. **不接受派遣制** —— 命中派遣/劳务派遣/劳务外包/第三方用工/中介等即剔除
   - 注意：英文不判裸词 `dispatch`，因其在民航语境指运行签派；中文"外派"（驻外）也不判
3. **面向中国籍招聘** —— 分三档判定，避免一刀切：
   - 中国内地主体：默认招中国人，非飞行员/非派遣即可
   - 境外主体且标注 `china_friendly=high`：允许无显式"中国籍"字样  
     （官网列表页常不重复写，专场信息在详情页）
   - 其余境外主体：须有明确中国籍正向信号
   - 任一明确要求当地工作权（`Only permanent residents` 等）一律剔除

## 上线：两种模式任选

### 模式 A｜GitHub 云端（推荐：全自动，不用开电脑）

**没用过 GitHub 也不用怕 —— 全程网页操作，不用敲任何命令。**  
完整图文步骤见 👉 [`GitHub新手指南.md`](GitHub新手指南.md)

核心四步：注册账号 → 新建 **Public** 仓库 → 网页拖拽上传文件 → Settings / Pages 选 **GitHub Actions**。

- 看板地址：`https://你的用户名.github.io/你的仓库名/`
- 每天 **北京时间 07:00** 自动更新
- 想立刻刷新：仓库 → **Actions** → `航空招聘每日更新` → **Run workflow**

熟悉 git 的话也可以直接推送：

```bash
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```

### 模式 B｜本机运行（不想用 GitHub 时）

- Windows：双击 **`一键更新.bat`**
- macOS / Linux：双击 **`一键更新(Mac_Linux).command`**

首次运行会自动创建独立环境并安装依赖（约 2 分钟），之后每次 1-2 分钟，跑完自动打开看板。  
跨电脑使用：把整个文件夹放进网盘同步，换台电脑后同样双击（`.venv` 无需同步，会自动重建）。

> 前置条件：本机需装有 Python 3.11+。若没装，Windows 脚本会给出安装指引。

## 手动新增航空公司 / 机场

编辑 `sources.csv`（可直接在 GitHub 网页上点开编辑），加一行即可：

| 字段               | 必填 | 说明                                                                            |
| ---------------- | -- | ----------------------------------------------------------------------------- |
| `name`           | ✅  | 主体名，如「卡塔尔航空」                                                                  |
| `type`           | ✅  | `airline_pax` / `airline_cargo` / `airport` / `ground_handler` / `aggregator` |
| `country`        | ✅  | 国家地区，**写「中国内地」会按国内主体放宽中国籍判定**                                                 |
| `category`       |    | 便于筛选的备注，如「国内三大航」                                                              |
| `url`            | ✅  | 官方招聘页地址                                                                       |
| `method`         |    | `static` 静态 / `js` 需渲染 / `ats` / `manual` 只人工维护                               |
| `china_friendly` |    | `high` / `medium` / `low` / `na`，影响过滤宽严                                       |
| `enabled`        |    | `1` 启用，`0` 停用                                                                 |
| `notes`          |    | 备注                                                                            |

> 加完存盘，第二天自动抓取；想立即生效就手动 Run workflow。

## 查证后手工录入岗位

有些岗位（如外航在华专场）藏在公众号/第三方报名页，脚本抓不到。  
查证后写入 `manual_feed.json`，每天会自动合并：

```json
[
  {
    "source": "阿联酋航空",
    "type": "airline_pax",
    "country": "阿联酋",
    "china_friendly": "high",
    "title": "中国籍客舱乘务员招聘（上海站）",
    "url": "https://官方报名页",
    "snippet": "要求与截止时间摘要…"
  }
]
```

## 目录结构

```
sources.csv                   主体库（手动扩展入口）
config/rules.json             过滤规则、抓取参数
src/                          抓取 / 过滤 / 增量 / 看板 四个模块
run.py                        每日流水线入口
manual_feed.json              人工核实录入的岗位
data/jobs_latest.json         当前全量快照（增量比对基准）
data/daily/*.json             每日快照，保留 30 天
data/source_health.json       各源抓取健康度，用于排查失效源
docs/index.html               生成的看板（发布到 Pages）

一键更新.bat                  Windows 一键更新入口（本机模式）
update.ps1                    上述 bat 调用的中文化脚本
一键更新(Mac_Linux).command   macOS / Linux 一键更新入口
打开看板.bat                  只看不抓，直接打开已有看板
GitHub新手指南.md             零基础上线图文步骤
```

## 命令行运行（可选）

一键脚本内部调用的就是这条命令，需要手动指定参数时可直接使用：

```bash
pip install -r requirements.txt
python run.py                # 全量抓取
python run.py --limit 10     # 只跑前 10 个主体（调试）
python run.py --no-network   # 不联网，仅用 manual_feed 重建看板
```

## 已知局限

- **境外站点多为 JS 渲染**：脚本会自动走阅读代理兜底；若仍抓不到，请在  
  `docs/index.html` 底部「数据源抓取健康度」里查看哪些源失败，再用手动录入补齐。
- **聚合站（航空英才网、职友集）为非官方源**，看板中已标注，投递前务必回官网复核。
- 岗位截止时间、薪资等以官方页面为准，本看板仅供参考。
- 本项目只做公开信息聚合，不构成招聘要约，也不收取任何费用。
