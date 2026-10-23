#!/bin/bash
# 航空招聘看板 - 一键更新（macOS / Linux）
# 用法：把本文件和项目文件夹放一起，双击运行（macOS 需先右键→打开 一次）

cd "$(dirname "$0")" || exit 1

echo "=========================================="
echo "    航空招聘看板  -  一键更新"
echo "=========================================="
echo ""

# 1. 检测 Python
PY=""
if command -v python3 >/dev/null 2>&1; then PY="python3"
elif command -v python >/dev/null 2>&1; then PY="python"
fi

if [ -z "$PY" ]; then
  echo "[提示] 没有检测到 Python，无法运行抓取。"
  echo "请先安装 Python 3（https://www.python.org/downloads/），然后重新双击本文件。"
  read -r -p "按回车键退出..."
  exit 1
fi

# 2. 准备虚拟环境
echo "[1/3] 检查运行环境..."
if [ ! -x ".venv/bin/python" ]; then
  echo "      首次运行，正在创建独立环境（约 1 分钟，只做这一次）..."
  "$PY" -m venv .venv || { read -r -p "创建失败，按回车退出..."; exit 1; }
fi

# 3. 依赖
echo "[2/3] 检查依赖库..."
if ! ./.venv/bin/python -c "import requests,bs4,lxml" >/dev/null 2>&1; then
  echo "      正在安装依赖（约 1 分钟）..."
  ./.venv/bin/python -m pip install -q -r requirements.txt || {
    echo "      依赖安装失败，请检查网络。"; read -r -p "按回车退出..."; exit 1; }
fi

# 4. 抓取
echo "[3/3] 正在抓取最新招聘信息（约 1-2 分钟）..."
echo ""
./.venv/bin/python run.py || { echo "运行出错。"; read -r -p "按回车退出..."; exit 1; }

echo ""
echo "=========================================="
echo "  更新完成！正在打开看板..."
echo "=========================================="
if command -v open >/dev/null 2>&1; then open "docs/index.html"
elif command -v xdg-open >/dev/null 2>&1; then xdg-open "docs/index.html"
fi
echo "看板位置：$(pwd)/docs/index.html"
read -r -p "按回车键退出..."
