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
        res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, shell=True)
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

def cleanup_git_state(cwd):
    """Dọn sạch mọi trạng thái rebase / merge dở dang và khóa file index.lock."""
    if not os.path.exists(os.path.join(cwd, ".git")):
        return
    subprocess.run("git rebase --abort", cwd=cwd, shell=True, capture_output=True)
    subprocess.run("git merge --abort", cwd=cwd, shell=True, capture_output=True)
    for p in [".git/rebase-merge", ".git/rebase-apply", ".git/index.lock"]:
        full_p = os.path.join(cwd, p)
        if os.path.isdir(full_p):
            shutil.rmtree(full_p, ignore_errors=True)
        elif os.path.isfile(full_p):
            try:
                os.remove(full_p)
            except Exception:
                pass

def safe_git_push(repo_dir, commit_msg):
    """Đẩy Git an toàn tuyệt đối - Local là nguồn dữ liệu chuẩn, không bao giờ kẹt rebase."""
    log(f"-> Đang đồng bộ Git Cloud an toàn (Thư mục: {repo_dir})...")
    cleanup_git_state(repo_dir)
    subprocess.run("git add -A", cwd=repo_dir, shell=True, capture_output=True)
    subprocess.run(f'git commit -m "{commit_msg}"', cwd=repo_dir, shell=True, capture_output=True)
    
    # 1. Thử push trực tiếp
    p = subprocess.run("git push origin main", cwd=repo_dir, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if p.returncode == 0:
        log(f"   [Thành công] Git Push: {repo_dir}")
        return True

    # 2. Nếu remote có commit mới, fetch và auto-merge ưu tiên local (-X ours)
    subprocess.run("git fetch origin main", cwd=repo_dir, shell=True, capture_output=True)
    subprocess.run('git merge origin/main -X ours --no-edit -m "auto: Merge sync [skip ci]"', cwd=repo_dir, shell=True, capture_output=True)
    subprocess.run("git add -A", cwd=repo_dir, shell=True, capture_output=True)
    subprocess.run('git commit -m "auto: Resolve conflict with local [skip ci]"', cwd=repo_dir, shell=True, capture_output=True)

    # 3. Push lại
    p2 = subprocess.run("git push origin main", cwd=repo_dir, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if p2.returncode == 0:
        log(f"   [Thành công] Git Push sau khi Auto-Merge: {repo_dir}")
        return True

    # 4. Dự phòng tối hậu: Force-with-lease vì Local là Single Source of Truth
    p3 = subprocess.run("git push origin main --force-with-lease", cwd=repo_dir, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if p3.returncode == 0:
        log(f"   [Thành công] Git Push (force-with-lease): {repo_dir}")
        return True

    cleanup_git_state(repo_dir)
    log(f"   [Cảnh báo] Git Push thất bại: {p2.stderr[:150] if p2.stderr else p.stderr[:150]}")
    return False

def main():
    log("="*65)
    log("BẮT ĐẦU CHU TRÌNH AUTO-UPDATE XSMB 18H35 HÀNG NGÀY")
    log("="*65)

    # Tự động dọn dẹp môi trường trước khi chạy
    cleanup_git_state(BASE_LOGIC_DIR)
    cleanup_git_state(DIR_58_UP_75)

    # BƯỚC 1: Chạy crawl_and_analyze.py
    step1_cmd = f'"{PYTHON_EXE}" crawl_and_analyze.py'
    ok1, out1 = run_step("Cào dữ liệu & Phân tích G7 Master", step1_cmd, BASE_LOGIC_DIR, timeout=180)

    # BƯỚC 2: Chạy soi_cau_g1_g5.py (cập nhật radar & Dàn Tĩnh 4 Cấp ngày mới)
    step2_cmd = f'"{PYTHON_EXE}" soi_cau_g1_g5.py'
    ok2, out2 = run_step("Soi cầu G1-G5 & Chốt Dàn Tĩnh mới", step2_cmd, BASE_LOGIC_DIR, timeout=120)

    # BƯỚC 2.5: Chạy live_radar_scanner.py (làm mới live_radar_state.json)
    step25_cmd = f'"{PYTHON_EXE}" live_radar_scanner.py'
    ok25, out25 = run_step("Làm mới Live Radar Scanner State", step25_cmd, BASE_LOGIC_DIR, timeout=90)

    # BƯỚC 3: Đồng bộ các file sang 58_up_to_75 và New folder/Logic
    log("-> Đồng bộ các file sang repo 58_up_to_75 & New folder/Logic...")
    sync_files = ['soi_cau_g1_g5_app.html', 'ket_qua_soi_cau_g1_g5.json', 'lich_su_phuong_phap.json', 'soi_cau_g1_g5.py', 'live_radar_state.json']
    for sf in sync_files:
        src = os.path.join(BASE_LOGIC_DIR, sf)
        dst_58 = os.path.join(DIR_58_UP_75, sf)
        if os.path.exists(src):
            try:
                shutil.copy2(src, dst_58)
            except Exception as e:
                log(f"   [Lỗi copy sang 58_up_to_75 {sf}]: {e}")
            if os.path.exists(NEW_FOLDER_LOGIC_DIR):
                try:
                    dst_nf = os.path.join(NEW_FOLDER_LOGIC_DIR, sf)
                    shutil.copy2(src, dst_nf)
                except Exception as e:
                    log(f"   [Lỗi copy sang New folder {sf}]: {e}")

    # BƯỚC 4: Chạy update_daily.py trong 58_up_to_75 (nếu có)
    update_daily_script = os.path.join(DIR_58_UP_75, "update_daily.py")
    if os.path.exists(update_daily_script):
        run_step("Update Daily 58_up_to_75", f'"{PYTHON_EXE}" update_daily.py', DIR_58_UP_75, timeout=120)

    # BƯỚC 5: Tự động Push Git lên GitHub Cloud an toàn
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # 5.1 Push repo Logic gốc (chính)
    safe_git_push(BASE_LOGIC_DIR, f"auto: Cap nhat Excel Master va Tong Hop ngay {date_str} [skip ci]")

    # 5.2 Push repo 58_up_to_75
    safe_git_push(DIR_58_UP_75, f"auto: Cap nhat ket qua ngay {date_str} [skip ci]")

    # 5.3 Push repo New folder/Logic
    if os.path.exists(NEW_FOLDER_LOGIC_DIR):
        safe_git_push(NEW_FOLDER_LOGIC_DIR, f"auto: Dong bo ket qua ngay {date_str} [skip ci]")

    log("="*65)
    log("HOÀN TẤT CHU TRÌNH TỰ ĐỘNG CẬP NHẬT XSMB HÀNG NGÀY!")
    log("="*65 + "\n")

if __name__ == '__main__':
    main()
