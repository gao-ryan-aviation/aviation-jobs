# GitHub 新手指南（纯网页操作，不用敲任何命令）

## 先回答你的问题

**我不会去操作你的 GitHub。** 我这边已经把全部文件做好了（就在 `D:\航空招聘` 这个文件夹里），  
接下来只需要你**把文件夹里的东西传上去**，就像往网盘上传文件一样。

我唯一做不了的两件事：**注册账号**（需要你的邮箱）、**登录上传**（需要你的密码）。  
这两步任何人都代不了，但加起来大概 10 分钟，做完之后就全自动了。

> 打个比方：我做的是"网站文件"，GitHub 是"免费网站空间"。  
> 你只需要把文件放进空间，它会每天自动帮你刷新内容。

---

## 三种方案，你选一个

| 方案                     | 你要做的事                | 优点                    | 缺点               |
| ---------------------- | -------------------- | --------------------- | ---------------- |
| **A. GitHub 网页上传**（推荐） | 注册账号 + 拖一次文件 + 点两下开关 | 每天自动更新、不用开电脑、换任何设备都能看 | 第一次要注册账号         |
| **B. 每天叫我来跑**          | 每天对我说一句"更新招聘"        | 零操作、零学习成本             | 你不开对话就不更新        |
| **C. 本机一键脚本**          | 双击 `一键更新.bat`        | 不用注册任何账号              | 要装 Python，且电脑得开机 |

**建议选 A**，一次搞定永久省心；如果今天不想折腾，先用 B，随时可以再切 A。

---

# 方案 A：详细步骤（跟着做就行）

## 第 1 步：注册 GitHub 账号（约 3 分钟）

1. 浏览器打开 **<https://github.com/>**
2. 右上角点 **Sign up**（注册）
3. 填邮箱 → 密码 → 用户名（**用户名很重要，会变成网址的一部分，建议用拼音小写，比如 `zhangsan-aviation`**）
4. 完成邮箱验证（去邮箱点一下验证链接）
5. 登录成功后，右上角头像在就说明好了

> 免费账号完全够用，不需要付费，也不需要填信用卡。

---

## 第 2 步：新建一个仓库（约 1 分钟）

仓库 = 存放网站文件的文件夹。

1. 登录后打开 \*\*<https://github.com/new\*\*（或点头像旁边的> **+** → **New repository**）
2. 按下面填：

| 项目                    | 填什么                            |
| --------------------- | ------------------------------ |
| **Repository name**   | `aviation-jobs`（随便起，建议英文小写加横杠） |
| **Description**       | 航空招聘追踪看板（可不填）                  |
| **Public / Private**  | 一定要选 **Public**（公开，这样才能免费发布网页） |
| **Add a README file** | **不要勾**（我们要传自己的文件）             |
| 其他选项                  | 都不要动，保持默认                      |

1. 点绿色按钮 **Create repository**

**⚠️ 安全说明**：公开的是"招聘信息汇总"和代码，不含你的任何个人资料。  
唯一会公开出现的是你的 GitHub 用户名（在网址里）。

---

## 第 3 步：上传文件（约 2 分钟，就是拖一下）

建好仓库后，页面中间会有几个链接，其中一个是  
**uploading an existing file**（上传已有文件）——**点它**。

然后上传这些东西。打开 `D:\航空招聘` 文件夹，**把下面这些一次性全部选中，拖到网页上**：

```
✅ .github          ← 注意前面有个点，定时任务全靠它
✅ config
✅ src
✅ docs
✅ sources.csv
✅ run.py
✅ requirements.txt
✅ manual_feed.json
✅ README.md
✅ .gitignore
```

**不用传的**：`.workbuddy`、`.git`、`data`（data 会自动重新生成）、`.venv`

拖上去后，网页下方会出现文件列表，等小圆圈转完（全部变绿色对勾）。

然后：

1. 页面往下拉，找到 **Commit changes** 区域
2. 第一个输入框随便填一句，比如 `首次上传`
3. 点绿色按钮 **Commit changes**

> 💡 如果一次拖太多失败，就分开拖：先拖 `src` 文件夹 → Commit → 再拖 `config` → Commit → 以此类推。

**❗ 如果 `.github` 这个文件夹拖不上去**（它比较特殊），用这个办法补：

1. 在仓库页面点 **Add file** → **Create new file**
2. 文件名框里**完整输入**（GitHub 会自动建好文件夹）：
   ```
   .github/workflows/daily.yml
   ```
3. 内容框里粘贴下面这段代码：

```yaml
name: 航空招聘每日更新

on:
  schedule:
    # 北京时间每天 07:00（GitHub Actions 使用 UTC，即前一日 23:00）
    - cron: '0 23 * * *'
  workflow_dispatch:
  push:
    branches: [ main ]
    paths:
      - 'sources.csv'
      - 'config/rules.json'
      - 'src/**'
      - 'run.py'

permissions:
  contents: write
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: 检出仓库
        uses: actions/checkout@v4

      - name: 准备 Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: pip

      - name: 安装依赖
        run: pip install -r requirements.txt

      - name: 运行抓取与增量比对
        run: python run.py

      - name: 上传看板产物
        uses: actions/upload-pages-artifact@v3
        with:
          path: docs

      - name: 提交更新的数据
        continue-on-error: true
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data docs
          git diff --quiet --cached || git commit -m "chore: 更新招聘数据 $(date +'%Y-%m-%d')"
          git push

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: 发布到 GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

1. 拉到底点 **Commit changes**

---

## 第 4 步：打开网页托管开关（约 30 秒）

1. 打开你刚建的仓库页面
2. 点上方一排标签里最后一个 **Settings**（设置，齿轮图标）
3. 左边菜单找 **Pages**（在 Code and automation 分类下）
4. 找到 **Source**（来源 / Build and deployment）
5. 点下拉框，选 **GitHub Actions**（**别选 Deploy from a branch**）
6. 不用保存，选完自动生效

---

## 第 5 步：立刻跑一次，别等到明天（约 1 分钟）

这样你能马上验证是不是成功了：

1. 仓库页面点上方 **Actions** 标签
2. 左边列表点 **航空招聘每日更新**
3. 右边有个 **Run workflow** 下拉按钮 → 点它 → 再点绿色 **Run workflow**
4. 等 2-3 分钟，刷新页面，会出现一条运行记录
   - 🟡 黄色转圈 = 正在跑
   - ✅ 绿色对勾 = 成功
   - ❌ 红色叉 = 失败（点进去看红字报错，截图发我）

---

## 第 6 步：打开看板

成功后，看板地址就是：

```
https://你的用户名.github.io/你的仓库名/
```

比如用户名 `zhangsan-aviation`、仓库名 `aviation-jobs`，那就是：  
`https://zhangsan-aviation.github.io/aviation-jobs/`

**建议把这个网址存成浏览器书签，手机上也存一个。**  
以后每天打开这个网址就是最新的，换任何电脑、手机都一样。

> ⏰ 时间说明：定时任务设在**北京时间早上 7 点**，但 GitHub 免费版会有延迟，  
> 实际可能在 7:05 - 7:40 之间完成。想立刻看最新，随时去 Actions 点一次 Run workflow。

---

# 日常使用

## 加一家新航空公司 / 机场

1. 打开你的仓库，点 `sources.csv`
2. 右上角点**铅笔图标**（Edit this file）
3. 滚到最下面，另起一行，按格式填：

```csv
厦门航空,airport_cn,中国,https://www.xiamenair.com/zh-cn/about/careers.html,static,high,1,官网招聘页
```

字段顺序（用英文逗号隔开）：  
`主体名 | 类型 | 国家 | 招聘页网址 | 抓取方式 | 中国籍友好度 | 启用(1/0) | 备注`

- **类型**：`airline_cn` 国内航司 / `airline_intl` 外航 / `cargo` 货运 / `airport_cn` 国内机场 / `airport_intl` 境外机场 / `ground` 地服商
- **抓取方式**：拿不准就填 `auto`，系统会自动试；一直抓不到就填 `manual`（靠搜索补漏）
- **友好度**：`high` 明确招中国籍 / `mid` 有机会 / `low` 基本要本地身份 / `na` 不确定

1. 拉到底点 **Commit changes**
2. 第二天自动生效；想立刻看，去 Actions 点 Run workflow

## 改过滤规则（比如想加新的排除词）

编辑 `config/rules.json`，同样 Commit 即可。

---

# 常见问题

**Q：上传后 Actions 页面是空的？**  
A：说明 `.github/workflows/daily.yml` 没传上去。按第 3 步的"❗"部分手动建一次。

**Q：Actions 运行失败，报 `Permission denied`？**  
A：Settings → Actions → General → 页面最下面 **Workflow permissions** → 选 **Read and write permissions** → Save。

**Q：看板打开是 404？**  
A：三件事检查一遍：① 仓库是不是 Public；② Pages 的 Source 是不是选的 GitHub Actions；③ 工作流是不是已经成功跑过一次（绿色对勾）。首次发布可能要等 5-10 分钟。

**Q：看板里岗位很少（只有十几条）？**  
A：正常。目前 88 个主体里有 56 个能自动抓到，且经过"去飞行员 / 去派遣 / 只留面向中国籍"三层过滤，剩下 20 多条真实岗位。加主体、或把抓不到的主体改成 `manual` 让系统走搜索补漏，数量会上升。

**Q：能改成一天更新两次吗？**  
A：能。编辑 `.github/workflows/daily.yml`，把 `- cron: '0 23 * * *'` 改成两行：

```yaml
    - cron: '0 23 * * *'    # 北京时间 07:00
    - cron: '0 11 * * *'    # 北京时间 19:00
```

**Q：我想删掉某个不想看的主体？**  
A：`sources.csv` 里把那行的 `enabled` 改成 `0` 就行，不用删行，以后想看再改回 `1`。

---

# 方案 C：不想用 GitHub，本机跑

1. 先装一次 Python 3.12（<https://www.python.org/downloads/，安装时勾选> **Add Python to PATH**）
2. 双击 `一键更新.bat`
   - 第一次会自动建环境、装依赖，等 2 分钟
   - 以后每次双击只跑 1-2 分钟，跑完自动打开看板
3. 想跨设备用：把整个文件夹放进 OneDrive / 坚果云，另一台电脑同步后同样双击即可  
   （虚拟环境 `.venv` 不用同步，换电脑后会自动重建）

**关于双击后看到的是 PowerShell 蓝窗口**：这是故意这样设计的。  
`一键更新.bat` 只是个"启动器"，真正的中文交互界面由 `update.ps1` 提供。  
原因是不同电脑的 Windows 命令行编码设置不一样，中文在黑窗口里容易变乱码，  
而 PowerShell 处理中文不会出现这个问题。**只要这两个文件在同一个文件夹里就没事。**

如果只是想看看已有内容、不想重新抓取，双击 `打开看板.bat` 即可（秒开）。

---

# 需要帮忙时

直接把报错截图发我，或者告诉我"看板打不开"就行，我来查。
