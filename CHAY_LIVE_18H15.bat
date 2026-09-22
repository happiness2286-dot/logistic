@echo off
title XSMB AI - RADAR REAL-TIME (18H15 - 18H35)
chcp 65001 >nul
color 0b

echo ==============================================================================
echo        XSMB AI - HE THONG GIAM SAT QUAY TRUC TIEP G1 -^> G5.6
echo ==============================================================================
echo [*] Dang khoi dong Mini App tren trinh duyet...
start http://localhost:8080/soi_cau_g1_g5_app.html

echo [*] Dang chay Radar tu dong bat giai truc tiep (moi 10 giay)...
echo [*] Quay xong G5.6 (~18h27): Tu dong xuat Top 1, Top 4, Dan Lot va To Mau Cau!
echo ==============================================================================
python soi_cau_g1_g5.py --live --interval 10

pause
