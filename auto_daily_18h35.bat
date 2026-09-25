@echo off
chcp 65001 > nul
cd /d "E:\DONG BO\New Ha GCCK\Năm 2026\Dự Án AI_ Antigravity\Logic"

title XSMB AI - Auto Daily 18h35 Task
echo =================================================================
echo   HE THONG TU DONG CAP NHAT XSMB & DAY CLOUD HANG NGAY LUC 18H35
echo =================================================================
echo.

"C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe" "auto_daily_18h35.py"

echo.
echo =================================================================
echo   DA HOAN TAT TIEN TRINH TU DONG!
echo =================================================================
timeout /t 5 > nul
