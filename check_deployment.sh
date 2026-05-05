#!/bin/bash
# 检查前后端部署方式的脚本
# 在服务器上运行此脚本

echo "=========================================="
echo "   部署方式检查脚本"
echo "=========================================="
echo ""

# 1. 检查 systemd 服务
echo "【1】检查 systemd 服务..."
if command -v systemctl &> /dev/null; then
    services=$(systemctl list-units --type=service --state=running | grep -iE "streamlit|uvicorn|fastapi|auditmind|fraud" | awk '{print $1}')
    if [ -n "$services" ]; then
        echo "✅ 发现 systemd 服务："
        echo "$services" | while read s; do
            echo "   - $s"
        done
    else
        echo "❌ 未找到相关 systemd 服务"
    fi
else
    echo "❌ systemctl 不可用"
fi
echo ""

# 2. 检查 supervisor
echo "【2】检查 supervisor..."
if command -v supervisorctl &> /dev/null; then
    svcs=$(supervisorctl status 2>/dev/null | grep -iE "streamlit|uvicorn|fastapi|auditmind|fraud")
    if [ -n "$svcs" ]; then
        echo "✅ 发现 supervisor 进程："
        echo "$svcs"
    else
        echo "❌ supervisor 中未找到相关进程"
    fi
else
    echo "❌ supervisorctl 不可用"
fi
echo ""

# 3. 检查 Docker
echo "【3】检查 Docker..."
if command -v docker &> /dev/null; then
    containers=$(docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}" | grep -iE "streamlit|uvicorn|fastapi|auditmind|fraud|8000|8501")
    if [ -n "$containers" ]; then
        echo "✅ 发现 Docker 容器："
        echo "$containers"
    else
        echo "❌ Docker 中未找到相关容器"
    fi
    
    # 检查 docker-compose
    if [ -f "docker-compose.yml" ] || [ -f "docker-compose.yaml" ]; then
        echo "📄 发现 docker-compose.yml 文件"
    fi
else
    echo "❌ Docker 不可用"
fi
echo ""

# 4. 检查 screen/tmux
echo "【4】检查 screen / tmux 会话..."
if command -v screen &> /dev/null; then
    screens=$(screen -ls 2>/dev/null | grep -iE "streamlit|uvicorn|fastapi|auditmind|fraud|\d+\.Socket")
    if [ -n "$screens" ]; then
        echo "✅ 发现 screen 会话："
        echo "$screens"
    else
        echo "❌ 未找到 screen 会话"
    fi
fi

if command -v tmux &> /dev/null; then
    tmux_sessions=$(tmux ls 2>/dev/null | grep -iE "streamlit|uvicorn|fastapi|auditmind|fraud")
    if [ -n "$tmux_sessions" ]; then
        echo "✅ 发现 tmux 会话："
        echo "$tmux_sessions"
    else
        echo "❌ 未找到 tmux 会话"
    fi
fi
echo ""

# 5. 检查运行中的进程
echo "【5】检查运行中的进程..."
echo "--- 端口 8000 (后端 FastAPI) ---"
port8000=$(ss -tlnp 2>/dev/null | grep ":8000" || netstat -tlnp 2>/dev/null | grep ":8000")
if [ -n "$port8000" ]; then
    echo "$port8000"
else
    echo "❌ 端口 8000 未监听"
fi

echo ""
echo "--- 端口 8501 (前端 Streamlit) ---"
port8501=$(ss -tlnp 2>/dev/null | grep ":8501" || netstat -tlnp 2>/dev/null | grep ":8501")
if [ -n "$port8501" ]; then
    echo "$port8501"
else
    echo "❌ 端口 8501 未监听"
fi
echo ""

# 6. 查找进程详情
echo "【6】查找 uvicorn / streamlit 进程..."
uvicorn_pids=$(pgrep -f "uvicorn" 2>/dev/null)
streamlit_pids=$(pgrep -f "streamlit" 2>/dev/null)

if [ -n "$uvicorn_pids" ]; then
    echo "✅ uvicorn 进程："
    for pid in $uvicorn_pids; do
        cmdline=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ')
        echo "   PID: $pid - $cmdline"
    done
else
    echo "❌ 未找到 uvicorn 进程"
fi

if [ -n "$streamlit_pids" ]; then
    echo "✅ streamlit 进程："
    for pid in $streamlit_pids; do
        cmdline=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ')
        echo "   PID: $pid - $cmdline"
    done
else
    echo "❌ 未找到 streamlit 进程"
fi
echo ""

# 7. 检查 nginx 反向代理
echo "【7】检查 nginx..."
if command -v nginx &> /dev/null; then
    nginx_conf=$(nginx -T 2>/dev/null | grep -iE "8000|8501|streamlit|uvicorn|auditmind|fraud" | head -10)
    if [ -n "$nginx_conf" ]; then
        echo "✅ nginx 配置中包含相关路由："
        echo "$nginx_conf"
    else
        echo "⚠️ nginx 已安装但未找到相关配置"
    fi
else
    echo "❌ nginx 未安装"
fi
echo ""

# 8. 检查项目路径
echo "【8】查找项目目录..."
project_paths=$(find / -type d -name "fraud_detection_saaS" 2>/dev/null | head -5)
if [ -n "$project_paths" ]; then
    echo "✅ 发现项目目录："
    echo "$project_paths"
else
    echo "⚠️ 未找到项目目录"
fi
echo ""

echo "=========================================="
echo "   检查完成"
echo "=========================================="
