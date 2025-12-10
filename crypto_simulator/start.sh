#!/bin/bash

# 加密货币蒙特卡洛模拟器启动脚本

echo "=================================================="
echo "  加密货币蒙特卡洛模拟器"
echo "=================================================="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3，请先安装 Python 3.7+"
    exit 1
fi

echo "✓ Python 版本:"
python3 --version
echo ""

# 检查依赖
echo "📦 检查依赖..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  未安装依赖，正在安装..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
else
    echo "✓ 依赖已安装"
fi
echo ""

# 启动服务器
echo "🚀 启动服务器..."
echo "访问地址: http://localhost:5000"
echo "按 Ctrl+C 退出"
echo ""

python3 app.py
