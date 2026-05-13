@echo off
chcp 65001 >nul
echo ========================================
echo   拱坝动态排仓系统 - 启动脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)
echo [✓] Python 环境正常

echo.
echo [2/3] 检查并安装后端依赖...
if not exist "backend\venv" (
    echo 创建虚拟环境...
    python -m venv backend\venv
)
call backend\venv\Scripts\activate.bat

pip install -r backend\requirements.txt -q
echo [✓] 后端依赖安装完成

echo.
echo [3/3] 启动服务...
echo.
echo ┌─────────────────────────────────────┐
echo │  后端 API: http://localhost:8000      │
echo │  前端界面: http://localhost:3000      │
echo │  API 文档: http://localhost:8000/docs  │
echo └─────────────────────────────────────┘
echo.

start "Backend API Server" cmd /k "cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

start "Frontend Dev Server" cmd /k "cd frontend && npm run dev"

echo.
echo [系统已启动] 请在浏览器中打开 http://localhost:3000
echo.
pause
