# -*- coding: utf-8 -*-
"""
HỆ THỐNG AUTO-CRON TỰ ĐỘNG CHẠY HÀNG NGÀY LÚC 18H35
- Cào kết quả XSMB mới nhất
- Chạy thuật toán phân tích G7, ma trận Lucky26, Top Đầu/Đuôi, Dàn 9 số Cội Nguồn, Dàn 60 số
- Cập nhật PHẦN 0 Bảng Chốt Dàn Tĩnh 4 Cấp cho ngày tiếp theo
- Xuất file Excel Master 18 Sheet
- Tự động Commit & Push lên GitHub Pages (logistic & 57_up_to_75)
- Ghi nhật ký thực thi vào cron_update.log
"""

import os
import sys
import time
import shutil
import subprocess
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PYTHON_EXE = sys.executable or r"C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe"
BASE_LOGIC_DIR = r"E:\DONG BO\New Ha GCCK\Năm 2026\Dự Án AI_ Antigravity\Logic"
NEW_FOLDER_LOGIC_DIR = r"E:\DONG BO\New Ha GCCK\Năm 2026\Dự Án AI_ Antigravity\New folder\Logic"
DIR_58_UP_75 = r"E:\DONG BO\New Ha GCCK\Năm 2026\Dự Án AI_ Antigravity\58_up_to_75"
LOG_FILE = os.path.join(BASE_LOGIC_DIR, "cron_update.log")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"Log error: {e}")

def run_step(step_name, cmd, cwd, timeout=120):
    log(f"-> Đang chạy: {step_name} (Thư mục: {cwd})...")
    try:
        res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, shell=True)
        if res.returncode == 0:
            log(f"   [Thành công] {step_name}")
            return True, res.stdout
        else:
            log(f"   [Cảnh báo] {step_name} kết thúc với mã {res.returncode}")
            if res.stderr:
                log(f"   Stderr: {res.stderr.strip()[:200]}")
            return False, res.stderr
    except Exception as e:
        log(f"   [Lỗi] Ngoại lệ khi chạy {step_name}: {e}")
        return False, str(e)

def main():
    log("="*65)
    log("BẮT ĐẦU CHU TRÌNH AUTO-UPDATE XSMB 18H35 HÀNG NGÀY")
    log("="*65)

    # BƯỚC 1: Chạy crawl_and_analyze.py
    step1_cmd = f'"{PYTHON_EXE}" crawl_and_analyze.py'
    ok1, out1 = run_step("Cào dữ liệu & Phân tích G7 Master", step1_cmd, BASE_LOGIC_DIR, timeout=180)

    # BƯỚC 2: Chạy soi_cau_g1_g5.py (cập nhật radar & Dàn Tĩnh 4 Cấp ngày mới)
    step2_cmd = f'"{PYTHON_EXE}" soi_cau_g1_g5.py'
    ok2, out2 = run_step("Soi cầu G1-G5 & Chốt Dàn Tĩnh mới", step2_cmd, NEW_FOLDER_LOGIC_DIR, timeout=120)

    # BƯỚC 3: Đồng bộ các file sang 58_up_to_75
    log("-> Đồng bộ các file sang repo 58_up_to_75...")
    sync_files = ['soi_cau_g1_g5_app.html', 'ket_qua_soi_cau_g1_g5.json', 'lich_su_phuong_phap.json', 'soi_cau_g1_g5.py']
    for sf in sync_files:
        src = os.path.join(NEW_FOLDER_LOGIC_DIR, sf)
        dst = os.path.join(DIR_58_UP_75, sf)
        if os.path.exists(src):
            try:
                shutil.copy2(src, dst)
            except Exception as e:
                log(f"   [Lỗi copy {sf}]: {e}")

    # BƯỚC 4: Chạy update_daily.py trong 58_up_to_75 (nếu có)
    update_daily_script = os.path.join(DIR_58_UP_75, "update_daily.py")
    if os.path.exists(update_daily_script):
        run_step("Update Daily 58_up_to_75", f'"{PYTHON_EXE}" update_daily.py', DIR_58_UP_75, timeout=120)

    # BƯỚC 5: Tự động Push Git lên GitHub Cloud
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # 5.1 Push repo New folder/Logic
    git_cmd_nf = f'git add . && git commit -m "auto: Cap nhat ket qua ngay {date_str} [skip ci]" && git push origin main'
    run_step("Git Push repo New folder/Logic", git_cmd_nf, NEW_FOLDER_LOGIC_DIR, timeout=60)

    # 5.2 Push repo 58_up_to_75
    git_cmd_58 = f'git add . && git commit -m "auto: Cap nhat ket qua ngay {date_str} [skip ci]" && git push origin main'
    run_step("Git Push repo 58_up_to_75", git_cmd_58, DIR_58_UP_75, timeout=60)

    # 5.3 Push repo Logic gốc
    git_cmd_lg = f'git add . && git commit -m "auto: Cap nhat Excel Master va Tong Hop ngay {date_str} [skip ci]" && git push origin main'
    run_step("Git Push repo Logic goc", git_cmd_lg, BASE_LOGIC_DIR, timeout=60)

    log("="*65)
    log("HOÀN TẤT CHU TRÌNH TỰ ĐỘNG CẬP NHẬT XSMB HÀNG NGÀY!")
    log("="*65 + "\n")

if __name__ == '__main__':
    main()
