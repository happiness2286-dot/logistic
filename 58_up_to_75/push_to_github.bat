@echo off
echo ===================================================
echo   PUSH MINI APP XSMB 2026 UP TO GITHUB REPOSITORY
echo ===================================================
echo.
set /p REPO_URL="Nhap GitHub Repository URL (vi du: https://github.com/username/xsmb-2026-optimizer.git): "

if "%REPO_URL%"=="" (
    echo Error: GitHub URL khong duoc de trong!
    pause
    exit /b 1
)

git branch -M main
git remote add origin %REPO_URL%
git push -u origin main

echo.
echo ===================================================
echo   DA DAY DU LIEU LEN GITHUB THANH CONG!
echo ===================================================
pause
