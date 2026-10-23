# =============================================
#  航空招聘看板 - 一键更新脚本
#  双击「一键更新.bat」即可，不需要懂命令行
# =============================================
$ErrorActionPreference = "Continue"

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

function Write-Title {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "    航空招聘看板  -  一键更新" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
}

Write-Title

# ---------- 1. 检测 Python ----------
Write-Host "[准备] 检查 Python 环境..." -ForegroundColor Gray

$pyCmd  = $null
$pyArgs = @()

foreach ($c in @("py", "python", "python3")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) {
        $pyCmd = $c
        if ($c -eq "py") { $pyArgs = @("-3") }
        break
    }
}

# 常见安装路径兜底（安装时没勾选 Add to PATH 的情况）
if (-not $pyCmd) {
    $candidates = @()
    $candidates += (Get-ChildItem "$env:LOCALAPPDATA\Programs\Python" -Directory -ErrorAction SilentlyContinue |
                    ForEach-Object { Join-Path $_.FullName "python.exe" })
    $candidates += (Get-ChildItem "C:\Python3*" -File -ErrorAction SilentlyContinue |
                    ForEach-Object { $_.FullName })
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p)) { $pyCmd = $p; break }
    }
}

if (-not $pyCmd) {
    Write-Host ""
    Write-Host "  [提示] 这台电脑上没有安装 Python，无法运行抓取。" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  请先安装一次 Python（免费，约 1 分钟），二选一：" -ForegroundColor White
    Write-Host ""
    Write-Host "    方式一：打开 Microsoft Store，搜索 Python，安装 3.12 版本"
    Write-Host "    方式二：访问  https://www.python.org/downloads/"
    Write-Host "            下载安装时务必勾选  Add Python to PATH"
    Write-Host ""
    Write-Host "  装好后重新双击「一键更新.bat」即可。" -ForegroundColor White
    Write-Host "  如果不想安装任何软件，请改用 GitHub 云端方案，"
    Write-Host "  参见同目录下的《GitHub新手指南.md》。"
    Write-Host ""
    Read-Host "按回车键退出" | Out-Null
    exit 1
}

Write-Host "       找到 Python：$pyCmd" -ForegroundColor Green

# ---------- 2. 独立运行环境 ----------
Write-Host "[1/3] 检查运行环境..." -ForegroundColor Gray
$venvPy = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPy)) {
    Write-Host "       首次运行，正在创建独立环境（约 1 分钟，仅此一次）..." -ForegroundColor Yellow
    & $pyCmd @pyArgs -m venv ".venv" 2>&1 | Out-Null
    if (-not (Test-Path $venvPy)) {
        Write-Host ""
        Write-Host "  [失败] 虚拟环境创建失败。" -ForegroundColor Red
        Write-Host "  常见原因是 Microsoft Store 版 Python 缺少组件，"
        Write-Host "  建议卸载后从 python.org 重装 3.12，并勾选 Add Python to PATH。"
        Write-Host ""
        Read-Host "按回车键退出" | Out-Null
        exit 1
    }
    Write-Host "       环境已就绪。" -ForegroundColor Green
} else {
    Write-Host "       环境已存在，跳过。" -ForegroundColor Green
}

# ---------- 3. 依赖库 ----------
Write-Host "[2/3] 检查依赖库..." -ForegroundColor Gray
& $venvPy -c "import requests,bs4,lxml" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "       正在安装依赖（国内镜像，约 1 分钟）..." -ForegroundColor Yellow
    & $venvPy -m pip install -q -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "       镜像不可用，改用官方源重试..." -ForegroundColor Yellow
        & $venvPy -m pip install -q -r requirements.txt
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "  [失败] 依赖安装失败，请检查网络连接后重试。" -ForegroundColor Red
        Write-Host ""
        Read-Host "按回车键退出" | Out-Null
        exit 1
    }
    Write-Host "       依赖安装完成。" -ForegroundColor Green
} else {
    Write-Host "       依赖已安装，跳过。" -ForegroundColor Green
}

# ---------- 4. 抓取 ----------
Write-Host "[3/3] 正在抓取最新招聘信息（约 1-2 分钟）..." -ForegroundColor Gray
Write-Host ""
& $venvPy (Join-Path $root "run.py")
$exit = $LASTEXITCODE

Write-Host ""
if ($exit -ne 0) {
    Write-Host "  [失败] 抓取过程出错，请截图上面的错误信息反馈。" -ForegroundColor Red
    Write-Host ""
    Read-Host "按回车键退出" | Out-Null
    exit 1
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  更新完成！正在打开看板..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$dash = Join-Path $root "docs\index.html"
if (Test-Path $dash) {
    Start-Process $dash
    Write-Host ""
    Write-Host "  看板文件：$dash" -ForegroundColor White
    Write-Host "  （把这个文件发给别人、或放进网盘，任何电脑都能打开查看）"
} else {
    Write-Host "  未找到看板文件，请确认是否抓取成功。" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "按回车键关闭窗口" | Out-Null
exit 0
