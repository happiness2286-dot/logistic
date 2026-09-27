@echo off
chcp 65001 > nul
cd /d "%~dp0"

title XSMB AI - Live Monitor 18h14
echo =================================================================
echo   HE THONG TU DONG GIAM SAT LIVE XSMB & DONG BO CLOUD LUC 18H14
echo =================================================================
echo.

"C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" "auto_live_18h14.py"

echo.
echo =================================================================
echo   DA HOAN TAT PHIEN LIVE XSMB!
echo =================================================================
timeout /t 5 > nul
