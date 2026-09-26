# -*- coding: utf-8 -*-
"""
=============================================================================
XSMB 2026 DAILY AUTO-UPDATER & OPTIMIZER
Tự động cào kết quả từ https://ketqua16.net/, cập nhật Excel, JSON và tái tối ưu Dàn 60 Số N1
=============================================================================
"""

import urllib.request
import re
import json
import os
import sys
import pandas as pd
from datetime import datetime

# Reconfigure stdout for UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_JSON_PATH = 'data.json'
EXCEL_PATH = 'Thong_Ke_G7_Va_Top20_XSMB_2026.xlsx'
URL = 'https://ketqua16.net/'
SO_KQ_URL = 'https://ketqua16.net/so-ket-qua'

def parse_tds_to_result(clean_tds):
    date_str = None
    gdb_str = None
    g7_list = []

    # Find Date
    for item in clean_tds:
        if 'ngày' in item.lower() and ('thứ' in item.lower() or 'chủ nhật' in item.lower()):
            lines = [l.strip() for l in item.split('\n') if l.strip()]
            date_str = lines[-1]
            break

    # Find Special Prize (GĐB) & G7
    for idx, item in enumerate(clean_tds):
        if 'đặc biệt' in item.lower() and idx + 1 < len(clean_tds):
            val = clean_tds[idx + 1]
            if val.isdigit() and len(val) == 5:
                gdb_str = val
        if 'bảy' in item.lower() and idx + 1 < len(clean_tds):
            val = clean_tds[idx + 1]
            digits = re.findall(r'\d{2}', val)
            if len(digits) >= 4:
                g7_list = digits[:4]

    if not date_str or not gdb_str or len(g7_list) < 4:
        return None, date_str

    return {
        'date': date_str,
        'gdb': gdb_str,
        'de': gdb_str[-2:],
        'g7_1': g7_list[0],
        'g7_2': g7_list[1],
        'g7_3': g7_list[2],
        'g7_4': g7_list[3]
    }, date_str

def get_date_key(d_str):
    if not d_str:
        return datetime.min
    m = re.search(r'(\d{2})-(\d{2})-(\d{4})', d_str)
    if m:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return datetime.min

def fetch_all_recent_results():
    results = {}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # 1. Ket noi trang chu
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Đang kết nối tới trang chủ {URL}...")
    try:
        req = urllib.request.Request(URL, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8')
        tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
        if tables:
            matches = re.findall(r'<td[^>]*>(.*?)</td>', tables[0], re.DOTALL | re.IGNORECASE)
            clean_tds = [re.sub(r'<.*?>', '', m).strip() for m in matches if re.sub(r'<.*?>', '', m).strip()]
            res, d_str = parse_tds_to_result(clean_tds)
            if res:
                results[res['date']] = res
                print(f"✅ Tìm thấy kết quả ngày [{res['date']}]: GĐB={res['gdb']} (Đề={res['de']}), G7=[{', '.join([res['g7_1'], res['g7_2'], res['g7_3'], res['g7_4']])}]")
            elif d_str:
                print(f"⏳ Kỳ quay [{d_str}] trên trang chủ đang diễn ra trực tiếp hoặc chưa có đầy đủ kết quả.")
    except Exception as e:
        print(f"⚠️ Không thể tải dữ liệu từ trang chủ {URL}: {e}")

    # 2. Ket noi so ket qua
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Đang tra cứu sổ kết quả {SO_KQ_URL}...")
    try:
        req = urllib.request.Request(SO_KQ_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8')
        tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.DOTALL)
        count_so = 0
        for t in tables:
            matches = re.findall(r'<td[^>]*>(.*?)</td>', t, re.DOTALL | re.IGNORECASE)
            clean_tds = [re.sub(r'<.*?>', '', m).strip() for m in matches if re.sub(r'<.*?>', '', m).strip()]
            res, _ = parse_tds_to_result(clean_tds)
            if res and res['date'] not in results:
                results[res['date']] = res
                count_so += 1
        print(f"✅ Đã quét {count_so} kỳ quay đã hoàn tất từ sổ kết quả.")
    except Exception as e:
        print(f"⚠️ Không thể tải dữ liệu từ sổ kết quả {SO_KQ_URL}: {e}")

    sorted_results = sorted(results.values(), key=lambda x: get_date_key(x['date']))
    return sorted_results

def fetch_latest_result():
    results = fetch_all_recent_results()
    return results[-1] if results else None

def get_dan_60(history_slice):
    head_scores = {0: 7.5, 1: 10.5, 2: 13.0, 3: 11.0, 4: 5.5, 5: 9.5, 6: 8.5, 7: 6.0, 8: 9.0, 9: 8.5}
    tail_scores = {0: 6.5, 1: 10.0, 2: 7.0, 3: 11.5, 4: 6.0, 5: 8.5, 6: 6.5, 7: 9.0, 8: 7.5, 9: 8.0}
    gaussian_high_freq = [39, 43, 57, 25, 89, 70, 34, 93, 52, 84, 7, 75, 2, 20, 98, 48]
    
    recent_2_days = [int(x['de']) for x in history_slice[-2:] if str(x.get('de', '')).isdigit()]
    recent_30_hits = [int(x['de']) for x in history_slice[-30:] if str(x.get('de', '')).isdigit()]
    
    pool = []
    for i in range(100):
        h = i // 10
        t = i % 10
        h_score = head_scores.get(h, 5.0)
        t_score = tail_scores.get(t, 5.0)
        
        score = h_score * 2.0 + t_score * 1.5
        if i in gaussian_high_freq:
            score += 10.0
            
        count_30 = recent_30_hits.count(i)
        score += count_30 * 4.0
        
        # Soft filtering: Mềm hóa bộ lọc N1 bằng điểm phạt thay vì loại bỏ cứng
        if h == 4 or h == 7:
            score -= 12.0
        if i in recent_2_days:
            score -= 15.0
        if h_score < 7.0 or t_score < 7.0:
            score -= 8.0
            
        pool.append({'num': i, 'score': score, 'valid': True})
        
    valid_pool = sorted(pool, key=lambda x: x['score'], reverse=True)
    selected = [p['num'] for p in valid_pool[:60]]
        
    top_10 = selected[:10]
    for num in top_10:
        sh = ((num // 10 + 5) % 10) * 10 + ((num % 10 + 5) % 10)
        target = next((p for p in pool if p['num'] == sh), None)
        if target and sh not in selected and len(selected) < 60:
            selected.append(sh)
            
    if recent_30_hits:
        inactive_30 = [n for n in selected if n not in recent_30_hits]
        active_outside = [p['num'] for p in valid_pool if p['num'] not in selected and p['num'] in recent_30_hits]
        swap_count = min(len(inactive_30), len(active_outside))
        for k in range(swap_count):
            rem_idx = selected.index(inactive_30[k])
            selected[rem_idx] = active_outside[k]
            
    return sorted(selected)

def sync_frame_history(data):
    history = data.get('history', [])
    frame_history = data.get('frame_history', [])
    existing_frame_stts = {f['stt'] for f in frame_history}
    
    updated = False
    for idx, rec in enumerate(history):
        stt = rec['stt']
        if stt not in existing_frame_stts and idx > 0:
            hist_before = history[:idx]
            dan_60 = get_dan_60(hist_before)
            de_hit = int(rec['de']) if str(rec.get('de', '')).isdigit() else -1
            
            is_hit = de_hit in dan_60
            result_str = "TRÚNG N1 🎯" if is_hit else "TRƯỢT KHUNG ❌"
            dan_str = ", ".join(f"{n:02d}" for n in dan_60) + f" ({len(dan_60)} số)"
            
            frame_entry = {
                "stt": stt,
                "date_start": rec['date'],
                "result": result_str,
                "de_hit": rec['de'],
                "dan_n1": dan_str
            }
            frame_history.append(frame_entry)
            updated = True
            
    data['frame_history'] = frame_history
    return updated

def update_app_js_fallback(data):
    if not os.path.exists('app.js'):
        return
    
    history = data.get('history', [])
    frame_history = data.get('frame_history', [])
    if not history:
        return

    latest_hist = history[-5:][::-1]
    latest_frame = frame_history[-5:][::-1]
    
    recent_5_hist_json = json.dumps(latest_hist, ensure_ascii=False, indent=8)
    recent_5_frame_json = json.dumps(latest_frame, ensure_ascii=False, indent=8)
    
    with open('app.js', 'r', encoding='utf-8') as f:
        content = f.read()

    new_default_data = f"""const DEFAULT_DATA = {{
    history: {recent_5_hist_json},
    frame_history: {recent_5_frame_json},
    dan_nhip_vang: [
        {{ "Thứ Hạng Hỏa Lực": "Top 01", "Con Số 2D": 39, "Điểm Nhịp Vàng Gaussian": "16.5 điểm", "Khuyến Nghị Vốn": "Ưu tiên hỏa lực chính" }},
        {{ "Thứ Hạng Hỏa Lực": "Top 02", "Con Số 2D": 43, "Điểm Nhịp Vàng Gaussian": "12.5 điểm", "Khuyến Nghị Vốn": "Ưu tiên hỏa lực chính" }},
        {{ "Thứ Hạng Hỏa Lực": "Top 03", "Con Số 2D": 57, "Điểm Nhịp Vàng Gaussian": "7.5 điểm", "Khuyến Nghị Vốn": "Ưu tiên hỏa lực chính" }},
        {{ "Thứ Hạng Hỏa Lực": "Top 04", "Con Số 2D": 25, "Điểm Nhịp Vàng Gaussian": "7.5 điểm", "Khuyến Nghị Vốn": "Ưu tiên hỏa lực chính" }},
        {{ "Thứ Hạng Hỏa Lực": "Top 05", "Con Số 2D": 89, "Điểm Nhịp Vàng Gaussian": "5.0 điểm", "Khuyến Nghị Vốn": "Ưu tiên hỏa lực chính" }}
    ]
}};"""

    content_updated = re.sub(
        r'// Embedded Default Data Fallback\s*const DEFAULT_DATA = \{.*?\};',
        f'// Embedded Default Data Fallback\n{new_default_data}',
        content,
        flags=re.DOTALL
    )

    with open('app.js', 'w', encoding='utf-8') as f:
        f.write(content_updated)
        
    print("🎉 Đã tự động đồng bộ dữ liệu dự phòng DEFAULT_DATA vào app.js!")

def update_index_html_version():
    if not os.path.exists('index.html'):
        return
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        content_updated = re.sub(r'styles\.css\?v=[^\s"\'<>]+', f'styles.css?v={timestamp}', content)
        content_updated = re.sub(r'app\.js\?v=[^\s"\'<>]+', f'app.js?v={timestamp}', content_updated)
        
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content_updated)
        print(f"🎉 Đã làm mới mã cache-busting index.html (v={timestamp})!")
    except Exception as e:
        print(f"⚠️ Không thể cập nhật version index.html: {e}")

import subprocess

def push_to_github():
    print("\n" + "-" * 65)
    print("  ĐANG KIỂM TRA THAY ĐỔI VÀ TUẦN TỰ PUSH LÊN GITHUB...")
    print("-" * 65)
    try:
        subprocess.run(["git", "add", "."], check=True)
        diff_res = subprocess.run(["git", "diff", "--cached", "--quiet"])
        if diff_res.returncode != 0:
            commit_msg = f"auto: Cap nhat ket qua XSMB ngay {datetime.now().strftime('%d/%m/%Y %H:%M')} & cache-busting"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            print("✅ Đã tạo commit mới thành công!")
        else:
            print("ℹ️ Không có thay đổi file mới để commit.")

        print("🚀 Đang đẩy dữ liệu mới nhất lên GitHub (origin main)...")
        push_res = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
        if push_res.returncode == 0:
            print("=================================================================")
            print("  🎉 ĐÃ TỰ ĐỘNG CẬP NHẬT VÀ PUSH LÊN GITHUB THANH CONG!")
            print("=================================================================")
        else:
            print(f"⚠️ Git push output: {push_res.stdout.strip()} {push_res.stderr.strip()}")
    except Exception as e:
        print(f"❌ Lỗi trong quá trình Push Git: {e}")

def update_database():
    all_fetched = fetch_all_recent_results()
    if not all_fetched:
        print("❌ Không lấy được kết quả xổ số từ nguồn mạng.")
        return False

    # Load data.json
    if os.path.exists(DATA_JSON_PATH):
        with open(DATA_JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {'history': [], 'frame_history': []}

    history = data.get('history', [])
    last_record = history[-1] if history else None
    last_date_key = get_date_key(last_record['date']) if last_record else datetime.min

    # Find new records that are newer than the last recorded date
    new_results = [r for r in all_fetched if get_date_key(r['date']) > last_date_key]

    if not new_results:
        print(f"ℹ️ Dữ liệu đã là mới nhất (Kỳ gần nhất: STT {last_record['stt'] if last_record else 0} [{last_record['date'] if last_record else 'N/A'}] - GĐB: {last_record['full_db'] if last_record else 'N/A'}).")
        # Ensure fallback & cache-busting always up to date
        update_app_js_fallback(data)
        update_index_html_version()
        return False

    print(f"🎯 Phát hiện {len(new_results)} kỳ quay mới cần bổ sung vào hệ thống:")
    excel_new_rows = []

    for res in new_results:
        new_stt = (history[-1]['stt'] + 1) if (history and isinstance(history[-1]['stt'], int)) else len(history) + 1
        new_entry = {
            'stt': new_stt,
            'date': res['date'],
            'full_db': res['gdb'],
            'de': res['de'],
            'g7_1': res['g7_1'],
            'g7_2': res['g7_2'],
            'g7_3': res['g7_3'],
            'g7_4': res['g7_4']
        }
        history.append(new_entry)
        print(f"  ✨ Bổ sung STT {new_stt} [{res['date']}]: GĐB={res['gdb']} (Đề={res['de']}), G7=[{res['g7_1']}, {res['g7_2']}, {res['g7_3']}, {res['g7_4']}]")

        excel_new_rows.append({
            'STT': new_stt,
            'Ngày Quay': res['date'],
            'Giải Đặc Biệt (5 số)': res['gdb'],
            'Số Đề (2 số cuối)': res['de'],
            'G7.1': res['g7_1'],
            'G7.2': res['g7_2'],
            'G7.3': res['g7_3'],
            'G7.4': res['g7_4']
        })

    data['history'] = history

    # Synchronize frame history
    frame_updated = sync_frame_history(data)
    if frame_updated:
        print("🎯 Đã tái tính toán và đồng bộ toàn bộ lịch sử Khung Nuôi N1.")

    # Save data.json
    with open(DATA_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("💾 Đã lưu thành công file data.json!")

    # Synchronize app.js
    update_app_js_fallback(data)

    # Refresh cache-busting in index.html
    update_index_html_version()

    # Append to Excel file
    if excel_new_rows:
        try:
            xl = pd.ExcelFile(EXCEL_PATH)
            df_hist = xl.parse('Du_Lieu_2026')
            df_updated = pd.concat([df_hist, pd.DataFrame(excel_new_rows)], ignore_index=True)
            with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df_updated.to_excel(writer, sheet_name='Du_Lieu_2026', index=False)
            print(f"📊 Đã ghi bổ sung {len(excel_new_rows)} dòng mới vào file Excel ({EXCEL_PATH})!")
        except Exception as e:
            print(f"⚠️ Lưu ý: Không thể ghi đè file Excel ({e}), nhưng data.json và Web App đã được cập nhật hoàn hảo.")

    return True

def update_excel_and_json(result):
    return update_database()

if __name__ == '__main__':
    print("=" * 65)
    print("   HỆ THỐNG CẬP NHẬT TỰ ĐỘNG KẾT QUẢ XSMB & TÁI TỐI ƯU 4 BƯỚC")
    print("=" * 65)
    
    updated = update_database()
    
    if updated:
        print("✅ Hoàn tất cập nhật và đồng bộ dữ liệu mới!")
    else:
        print("⚡ Dữ liệu hệ thống đã sẵn sàng.")
        
    # Auto push to GitHub on execution
    push_to_github()


