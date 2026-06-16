@echo off
title FormatIQ - YouTube Research System
echo.
echo  =============================================
echo    FormatIQ -- YouTube Research and Strategy
echo  =============================================
echo.

set SCRIPT_DIR=%~dp0
set BACKEND_DIR=%SCRIPT_DIR%backend
set FRONTEND_DIR=%SCRIPT_DIR%frontend

:: Install backend dependencies
echo [1/4] Setting up Python environment...
cd /d "%BACKEND_DIR%"
if not exist venv (
  python -m venv venv
)
call venv\Scripts\activate.bat
pip install -q -r "%SCRIPT_DIR%requirements.txt"

:: Install frontend dependencies
echo [2/4] Installing Node dependencies...
cd /d "%FRONTEND_DIR%"
if not exist node_modules (
  npm install --silent
)

:: Start backend in new window
echo [3/4] Starting backend server (port 8000)...
cd /d "%BACKEND_DIR%"
start "FormatIQ Backend" cmd /k "call venv\Scripts\activate.bat && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait a moment
timeout /t 3 /nobreak >nul

:: Start frontend in new window
echo [4/4] Starting frontend (port 5173)...
cd /d "%FRONTEND_DIR%"
start "FormatIQ Frontend" cmd /k "npm run dev"

echo.
echo  FormatIQ is running!
echo  Frontend: http://localhost:5173
echo  Backend:  http://localhost:8000
echo  API docs: http://localhost:8000/docs
echo.
echo  Close the backend and frontend windows to stop.
pause
