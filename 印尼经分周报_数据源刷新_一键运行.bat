@echo off
chcp 936 >nul
title Indonesia Weekly Report Data Refresh
echo ============================================
echo   Indonesia Weekly Report - Auto Refresh
echo ============================================
echo.

cd /d "%~dp0"

set "PYEXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

echo [1/3] Python: %PYEXE%
"%PYEXE%" --version

echo [2/3] Query data sources and refresh excel (1-2 min)...
"%PYEXE%" "%~dp0印尼经分周报_数据源刷新.py"

echo.
echo [3/3] Done!
echo Output: 8月预估\印尼经分周报_时间戳_数据源刷新.xlsx
echo.
pause
