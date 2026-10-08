# -*- coding: utf-8 -*-
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $scriptDir

$logFile = Join-Path $scriptDir "cron_history.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

"=======================================================" | Out-File -FilePath $logFile -Append -Encoding utf8
"[$timestamp] BẮT ĐẦU CHẠY TỰ ĐỘNG LIVE XSMB TỪ 18H14..." | Out-File -FilePath $logFile -Append -Encoding utf8

try {
    # 1. Quét Radar Live trực tiếp (18h14 - 18h32)
    # Tự động chốt khóa và push GitHub ngay khi hoàn tất G5 (khoảng 18h24)
    "[$timestamp] Đang chạy Live Radar Scanner G1->G5 (tự khóa khi hết G5)..." | Out-File -FilePath $logFile -Append -Encoding utf8
    python live_radar_scanner.py --live --interval 5 --duration 1200 --auto_push 2>&1 | Out-File -FilePath $logFile -Append -Encoding utf8

    # 2. Sau khi có Giải Đặc Biệt (sau 18h31), chạy crawl và phân tích toàn diện Khung 3 Ngày
    $time2 = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$time2] Bắt đầu phân tích Khung 3 Ngày & xuất Excel Master..." | Out-File -FilePath $logFile -Append -Encoding utf8
    python crawl_and_analyze.py 2>&1 | Out-File -FilePath $logFile -Append -Encoding utf8

    # 3. Quét chốt và cập nhật lại Radar lần cuối
    python live_radar_scanner.py 2>&1 | Out-File -FilePath $logFile -Append -Encoding utf8

    # 4. Đẩy lại lần cuối toàn bộ dữ liệu lên GitHub
    git add . 2>&1 | Out-File -FilePath $logFile -Append -Encoding utf8
    git commit -m "Daily live cron sync $(Get-Date -Format 'yyyy-MM-dd HH:mm')" 2>&1 | Out-File -FilePath $logFile -Append -Encoding utf8
    git push origin main 2>&1 | Out-File -FilePath $logFile -Append -Encoding utf8

    $timeEnd = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$timeEnd] HOÀN TẤT ĐỒNG BỘ TOÀN BỘ DỮ LIỆU LÊN GITHUB THÀNH CÔNG!" | Out-File -FilePath $logFile -Append -Encoding utf8
} catch {
    "[$timestamp] LỖI: $_" | Out-File -FilePath $logFile -Append -Encoding utf8
}

"=======================================================" | Out-File -FilePath $logFile -Append -Encoding utf8
