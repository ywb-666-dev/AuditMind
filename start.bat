@echo off
chcp 65001 >nul
title 财务舞弊识别 SaaS 平台 - 启动器

echo ========================================
echo   财务舞弊识别 SaaS 平台 - 启动器
echo ========================================
echo.
echo 提示: 使用本机 Python 环境运行
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未检测到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python 已安装
echo.

REM 选择启动模式
echo 请选择启动模式:
echo 1. 启动后端 (FastAPI) - http://localhost:8000
echo 2. 启动前端 (Streamlit) - http://localhost:8501
echo 3. 启动前后端 (同时启动两个服务)
echo 4. 初始化数据库
echo 5. 退出
echo.

set /p choice="请输入选项 (1-5): "

if "%choice%"=="1" goto start_backend
if "%choice%"=="2" goto start_frontend
if "%choice%"=="3" goto start_both
if "%choice%"=="4" goto init_db
if "%choice%"=="5" goto end

echo 无效选项
goto end

:start_backend
echo.
echo [INFO] 启动后端服务...
echo [INFO] API文档: http://localhost:8000/docs
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
goto end

:start_frontend
echo.
echo [INFO] 启动前端服务...
echo [INFO] 访问地址: http://localhost:8501
cd frontend
streamlit run app.py
goto end

:start_both
echo.
echo [INFO] 启动后端服务...
start cmd /k "cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul
echo [INFO] 启动前端服务...
start cmd /k "cd frontend && streamlit run app.py"
echo.
echo [OK] 服务已启动:
echo   - 后端: http://localhost:8000
echo   - 前端: http://localhost:8501
goto end

:init_db
echo.
echo [INFO] 初始化数据库...
cd backend
python utils/init_cases.py
echo.
echo [OK] 数据库初始化完成
goto end

:end
echo.
pause
