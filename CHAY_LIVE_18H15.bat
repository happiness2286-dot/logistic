@echo off
title XSMB AI - RADAR REAL-TIME (18H15 - 18H35)
chcp 65001 >nul
color 0b

echo ==============================================================================
echo        XSMB AI - HE THONG GIAM SAT QUAY TRUC TIEP G1 -^> G5.6
echo ==============================================================================

:: Kiem tra va khoi dong web server Localhost 8080 neu chua chay
netstat -ano | findstr :8080 >nul
if errorlevel 1 (
    echo [*] Dang khoi dong Local Web Server (Port 8080)...
    start /b python -m http.server 8080 >nul 2>&1
    timeout /t 2 /nobreak >nul
) else (
    echo [*] Web Server Port 8080 da san sang.
)

echo [*] Dang mo Mini App tren trinh duyet...
start http://localhost:8080/soi_cau_g1_g5_app.html

echo [*] Dang chay Radar tu dong bat giai truc tiep (moi 8 giay)...
echo [*] Tu dong Cloud Sync len GitHub Pages cho Dien thoai (--push)
echo [*] Quay xong G5.6 (~18h27): Tu dong xuat Top 1, Top 4, Dan Lot va To Mau Cau!
echo ==============================================================================
python soi_cau_g1_g5.py --live --interval 8 --push

pause
