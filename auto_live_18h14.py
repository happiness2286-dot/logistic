# -*- coding: utf-8 -*-
"""
=============================================================================
XSMB AI - MASTER LIVE CONTROLLER (18H14 - 18H33)
Tự động đồng bộ cùng lúc cả 2 hệ thống trực tiếp cùng đài quay XSMB:
1. Repo Logic (Mini App G1->G5): soi_cau_g1_g5.py --live --interval 8 --push
   -> Cập nhật tức thì: https://happiness2286-dot.github.io/logistic/soi_cau_g1_g5_app.html
2. Repo 67_up_95 (Dashboard Radar): live_radar_scanner.py --live --interval 8 --auto_push
   -> Cập nhật tức thì: https://happiness2286-dot.github.io/67up97/
=============================================================================
"""

import os
import sys
import time
import subprocess
import threading
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PYTHON_EXE = sys.executable or r"C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe"
BASE_LOGIC_DIR = r"E:\DONG BO\New Ha GCCK\Năm 2026\Dự Án AI_ Antigravity\Logic"
DIR_67_UP_95 = r"E:\DONG BO\New Ha GCCK\Năm 2026\Dự Án AI_ Antigravity\67_up_95"
LOG_FILE = os.path.join(BASE_LOGIC_DIR, "cron_live_18h14.log")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"Log error: {e}")

def run_process(name, cmd, cwd, timeout_sec=1500):
    log(f"-> KHỞI ĐỘNG TIẾN TRÌNH LIVE: {name} (Thư mục: {cwd})")
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )
        for line in iter(proc.stdout.readline, ''):
            clean_line = line.strip()
            if clean_line:
                log(f"[{name}] {clean_line}")
        proc.stdout.close()
        ret = proc.wait(timeout=timeout_sec)
        log(f"-> TIẾN TRÌNH {name} KẾT THÚC VỚI MÃ: {ret}")
    except Exception as e:
        log(f"[!] LỖI TIẾN TRÌNH {name}: {e}")

def main():
    log("=" * 70)
    log("BẮT ĐẦU CHU TRÌNH GIÁM SÁT LIVE TRỰC TIẾP XSMB (18H14)")
    log("=" * 70)

    # Tự động dọn dẹp cặn Git trước phiên live
    try:
        subprocess.run("git rebase --abort", cwd=BASE_LOGIC_DIR, shell=True, capture_output=True)
        subprocess.run("git merge --abort", cwd=BASE_LOGIC_DIR, shell=True, capture_output=True)
        lock_file = os.path.join(BASE_LOGIC_DIR, ".git", "index.lock")
        if os.path.exists(lock_file):
            os.remove(lock_file)
    except Exception:
        pass

    threads = []

    # 1. Tiến trình Logic G1->G5 (Đảm nhiệm vai trò Single-Writer độc quyền đẩy Cloud)
    cmd_logic = f'"{PYTHON_EXE}" soi_cau_g1_g5.py --live --interval 8 --push'
    t1 = threading.Thread(target=run_process, args=("Logic_G1_G5", cmd_logic, BASE_LOGIC_DIR), daemon=True)
    threads.append(t1)
    t1.start()

    # 2. Tiến trình Live Radar Scanner (Tính toán radar độc lập, không tranh chấp Git)
    cmd_radar = f'"{PYTHON_EXE}" live_radar_scanner.py --live --interval 8'
    t2 = threading.Thread(target=run_process, args=("Radar_Scanner", cmd_radar, BASE_LOGIC_DIR), daemon=True)
    threads.append(t2)
    t2.start()

    # Chờ các tiến trình hoàn thành (tối đa 25 phút đến ~18h39)
    for t in threads:
        t.join(timeout=1600)

    log("=" * 70)
    log("HOÀN TẤT PHIÊN GIÁM SÁT LIVE XSMB HÔM NAY!")
    log("=" * 70 + "\n")

if __name__ == '__main__':
    main()
