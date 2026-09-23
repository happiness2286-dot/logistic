# -*- coding: utf-8 -*-
"""
=============================================================================
HỆ THỐNG SOI VỊ TRÍ G1 -> G5, CHU KỲ LẶP & LỌC 60 SỐ CẤP 4 (CHUẨN HÓA MỚI)
1. QUY TẮC CẦU:
   - Cầu chạy ngày 3, 4: ✅ VẪN LẤY BÌNH THƯỜNG (ưu tiên Top 1, Top 4)
   - Cầu đã bỏ (gãy): ❌ KHÔNG LẤY NỮA — loại bỏ hoàn toàn (không cộng dồn ngày đứt đoạn)
   - Cầu mới chạm ngày 1: ⚠️ THEO DÕI — nếu nổ ngày 2 -> thành tổng lực ngày 3
   - Ngày 2 (nếu nổ): 🎯 THÀNH TỔNG LỰC NGÀY 3 (đôn lên chu kỳ 3 ngày)
   - Số lót: 🛡️ LẤY TỪ 60 SỐ N1

2. QUY TRÌNH 5 BƯỚC:
   - Bước 1: Xác định đề ngày hôm trước (Chạm đầu, Đuôi, Bóng dương -> Tập Đầu, Tập Đuôi)
   - Bước 2: Soi vị trí mới chạm & chu kỳ trên kỳ đang quay G1->G5
   - Bước 3: Ưu tiên theo quy tắc đầu đuôi bóng
   - Bước 4: Vào dàn (Ghép các con số từ các vị trí: Chục từ Đầu, Đơn vị từ Đuôi)
   - Bước 5: So với dàn 60 số Cấp 4 (Giao thoa là kết quả tinh túy; chọn Top 1, Top 4)
=============================================================================
"""

import os
import sys
import re
import json
import time
import argparse
from datetime import datetime
import pandas as pd

# Reconfigure stdout for UTF-8 on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Import requests & BeautifulSoup with fallback
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    import urllib.request
    import urllib.parse
    HAS_BS4 = False

MKETQUA_SO_KQ_URL = "https://mketqua.net/so-ket-qua"
MKETQUA_LIVE_URL = "https://mketqua.net/"
DEFAULT_CAP4_CSV = "dan_60_cap_4.csv"

# Bảng bóng dương chính xác (0-5, 1-6, 2-7, 3-8, 4-9)
BONG_DUONG = {
    0: 5, 1: 6, 2: 7, 3: 8, 4: 9,
    5: 0, 6: 1, 7: 2, 8: 3, 9: 4
}

# 60 số Cấp 4 mặc định tối ưu (nếu chưa có file CSV)
DEFAULT_60_CAP4 = [
    1, 2, 3, 4, 5, 8, 9, 11, 12, 13, 15, 17, 18, 19, 20,
    21, 22, 23, 24, 26, 28, 29, 31, 32, 33, 34, 35, 37, 38, 42,
    44, 45, 51, 53, 55, 58, 59, 60, 61, 62, 63, 65, 67, 68, 69,
    72, 80, 81, 82, 83, 84, 85, 87, 88, 91, 92, 95, 97, 98, 99
]

def ensure_cap4_csv(csv_path=DEFAULT_CAP4_CSV):
    """Tạo file CSV 60 số Cấp 4 nếu chưa tồn tại"""
    if not os.path.exists(csv_path):
        df = pd.DataFrame({
            'STT': list(range(1, len(DEFAULT_60_CAP4) + 1)),
            'So_2D': [f"{x:02d}" for x in sorted(DEFAULT_60_CAP4)]
        })
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"[*] Đã tự động khởi tạo file CSV 60 số Cấp 4: {csv_path}")

def load_cap4_numbers(csv_path=DEFAULT_CAP4_CSV):
    """Đọc 60 số Cấp 4 từ file CSV"""
    ensure_cap4_csv(csv_path)
    try:
        df = pd.read_csv(csv_path, dtype=str)
        col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        numbers = []
        for val in df[col].dropna():
            v_str = str(val).strip().zfill(2)
            if v_str.isdigit() and len(v_str) == 2:
                numbers.append(v_str)
        numbers = sorted(list(set(numbers)))
        return numbers
    except Exception as e:
        print(f"[!] Lỗi khi đọc file CSV {csv_path}: {e}. Dùng dàn Cấp 4 dự phòng.")
        return [f"{x:02d}" for x in sorted(DEFAULT_60_CAP4)]

def fetch_mketqua_html(count=10):
    """Lấy mã HTML các kỳ xổ số gần nhất từ mketqua.net"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    if HAS_BS4:
        try:
            resp = requests.post(MKETQUA_SO_KQ_URL, data={'code': 'mb', 'count': str(count), 'dow': '7'}, headers=headers, timeout=12)
            if resp.status_code == 200:
                return resp.text
        except Exception as e:
            print(f"[!] Requests failed: {e}, chuyển sang urllib...")
            
    try:
        import urllib.request
        import urllib.parse
        data = urllib.parse.urlencode({'code': 'mb', 'count': str(count), 'dow': '7'}).encode('utf-8')
        req = urllib.request.Request(MKETQUA_SO_KQ_URL, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"[!] Lỗi kết nối mketqua.net: {e}")
        return ""

def parse_lottery_blocks(html):
    """Phân tách từng kỳ quay và trích xuất đúng 85 vị trí vật lý trong G1 -> G5"""
    blocks = html.split('<table class="table table-condensed kqcenter kqvertimarginw table-kq-border table-kq-hover-div table-bordered kqbackground table-kq-bold-border tb-phoi-border watermark table-striped" id="result_tab_mb">')
    draws = []
    
    for b in blocks[1:]:
        date_m = re.search(r'id="result_date">([^<]+)</span>', b)
        date_str = date_m.group(1).strip() if date_m else ""
        
        # Đặc biệt
        db_m = re.search(r'id="rs_0_0"[^>]*>(\d{5})</div>', b)
        if not db_m:
            db_m = re.search(r'id="rs_0_0"[^>]*data-sofar="(\d{5})"', b)
        db_val = db_m.group(1).strip() if db_m else ""
        de_val = db_val[-2:] if len(db_val) >= 2 else ""

        # Trích xuất 85 vị trí vật lý trong G1 -> G5
        prizes = {}
        config = [(1, 1), (2, 2), (3, 6), (4, 4), (5, 6)]
        for g_num, total_subs in config:
            for sub_idx in range(total_subs):
                g_code = f"G{g_num}" if g_num == 1 else f"G{g_num}.{sub_idx+1}"
                elem_id = f"rs_{g_num}_{sub_idx}"
                v_m = re.search(rf'id="{elem_id}"[^>]*>([^<]*)</div>', b)
                if not v_m:
                    v_m = re.search(rf'id="{elem_id}"[^>]*data-sofar="([^"]*)"', b)
                val = v_m.group(1).strip() if v_m else ""
                prizes[g_code] = val

        draws.append({
            'date': date_str,
            'db': db_val,
            'de': de_val,
            'prizes': prizes
        })
        
    return draws

def get_physical_positions(prizes):
    """
    Trả về danh sách tất cả các vị trí vật lý kèm chữ số:
    Format: {'G2.1 vị trí 5': '2', 'G3.1 vị trí 1': '1', ...} (tối đa 85 vị trí chuẩn trong G1->G5)
    """
    positions = {}
    for g_code, val in prizes.items():
        if not val:
            continue
        for pos_idx, char in enumerate(val, 1):
            key = f"{g_code} vị trí {pos_idx}"
            positions[key] = char
    return positions

def analyze_bridge_cycles(draws, target_draw_idx=0):
    """
    Phân tích vị trí cầu G1->G5 XSMB theo chuẩn 5 bước và quy tắc mới:
    1. Cầu chạy ngày 3, 4: ✅ VẪN LẤY BÌNH THƯỜNG (ưu tiên Top 1, Top 4)
    2. Cầu đã bỏ (gãy): ❌ KHÔNG LẤY NỮA — loại bỏ hoàn toàn (không cộng dồn ngày đứt quãng)
    3. Cầu mới chạm ngày 1: ⚠️ THEO DÕI (ưu tiên theo quy tắc đầu đuôi bóng -> Dàn ngày 1 -> Giao thoa 60 số)
    4. Ngày 2 (nếu nổ): 🎯 THÀNH TỔNG LỰC NGÀY 3 (đôn lên chu kỳ 3 ngày)
    5. Số lót: 🛡️ LẤY TỪ 60 SỐ N1
    """
    prev_idx = target_draw_idx + 1
    if len(draws) <= prev_idx:
        return None

    target_draw = draws[target_draw_idx]
    prev_draw = draws[prev_idx]
    
    de_str = prev_draw['de']
    if len(de_str) < 2:
        return None
        
    head_num = int(de_str[0])
    tail_num = int(de_str[1])
    
    head_bong = BONG_DUONG[head_num]
    tail_bong = BONG_DUONG[tail_num]
    
    target_head_digits = [head_num, head_bong]
    target_tail_digits = [tail_num, tail_bong]
    
    target_pos_map = get_physical_positions(target_draw['prizes'])
    
    # Hàm tính chuỗi ngày xuất hiện liên tiếp (Streak) tính lùi từ kỳ hiện tại
    # Tuyệt đối loại bỏ cầu gãy: hễ đứt quãng là dừng ngay lập tức
    def calculate_consecutive_days(pos, digit_char):
        streak = 1
        for past_idx in range(target_draw_idx + 1, min(len(draws), target_draw_idx + 6)):
            past_pos_map = get_physical_positions(draws[past_idx]['prizes'])
            if past_pos_map.get(pos) == digit_char:
                streak += 1
            else:
                # CẦU ĐÃ BỎ (GÃY) -> DỪNG LẠI NGAY LẬP TỨC, LOẠI BỎ HOÀN TOÀN
                break
        return streak

    # Quét vị trí Chạm Đầu
    head_positions = []
    for pos, char in target_pos_map.items():
        if char in [str(x) for x in target_head_digits]:
            streak = calculate_consecutive_days(pos, char)
            
            # Quy tắc 4: Ngày 2 (nếu nổ ở đề hôm trước) -> Thành tổng lực ngày 3
            is_chuluc_n2 = False
            if streak == 2 and prev_idx < len(draws):
                prev_de_val = prev_draw['de']
                if char in prev_de_val:
                    is_chuluc_n2 = True
                    streak = 3  # Thăng hạng lên tổng lực ngày 3
            
            if streak >= 4:
                cat = "Chỉ đạo"
                label = "✅ CHỈ ĐẠO (Ưu tiên ngày 4)"
            elif streak == 3:
                cat = "Chỉ đạo"
                label = "✅ CHỈ ĐẠO (Tổng lực ngày 3)" if is_chuluc_n2 else "✅ CHỈ ĐẠO (Ưu tiên ngày 3)"
            elif streak == 2:
                cat = "Lót"
                label = "Lót ngày 2"
            else:
                cat = "Theo dõi"
                label = "Theo dõi ngày 1 (Mới chạm)"
                
            head_positions.append({
                'position': pos,
                'digit': char,
                'role': 'Đầu',
                'cycle_days': streak,
                'category': cat,
                'label': label,
                'is_chuluc_n2': is_chuluc_n2
            })

    # Quét vị trí Chạm Đuôi
    tail_positions = []
    for pos, char in target_pos_map.items():
        if char in [str(x) for x in target_tail_digits]:
            streak = calculate_consecutive_days(pos, char)
            
            # Quy tắc 4: Ngày 2 (nếu nổ ở đề hôm trước) -> Thành tổng lực ngày 3
            is_chuluc_n2 = False
            if streak == 2 and prev_idx < len(draws):
                prev_de_val = prev_draw['de']
                if char in prev_de_val:
                    is_chuluc_n2 = True
                    streak = 3  # Thăng hạng lên tổng lực ngày 3
            
            if streak >= 4:
                cat = "Chỉ đạo"
                label = "✅ CHỈ ĐẠO (Ưu tiên ngày 4)"
            elif streak == 3:
                cat = "Chỉ đạo"
                label = "✅ CHỈ ĐẠO (Tổng lực ngày 3)" if is_chuluc_n2 else "✅ CHỈ ĐẠO (Ưu tiên ngày 3)"
            elif streak == 2:
                cat = "Lót"
                label = "Lót ngày 2"
            else:
                cat = "Theo dõi"
                label = "Theo dõi ngày 1 (Mới chạm)"
                
            tail_positions.append({
                'position': pos,
                'digit': char,
                'role': 'Đuôi',
                'cycle_days': streak,
                'category': cat,
                'label': label,
                'is_chuluc_n2': is_chuluc_n2
            })

    return {
        'prev_date': prev_draw['date'],
        'prev_db': prev_draw['db'],
        'prev_de': prev_draw['de'],
        'head': head_num,
        'head_bong': head_bong,
        'tail': tail_num,
        'tail_bong': tail_bong,
        'head_positions': head_positions,
        'tail_positions': tail_positions,
        'target_pos_map': target_pos_map
    }

def run_pipeline(target_draw_idx=0, cap4_csv=DEFAULT_CAP4_CSV, custom_cap4=None):
    """
    Thực thi toàn bộ pipeline chuẩn hóa 5 bước theo yêu cầu:
    Bước 1: Xác định đề ngày hôm trước (Chạm đầu, Đuôi, Bóng dương)
    Bước 2: Soi vị trí mới chạm & chu kỳ trên kỳ đang quay G1->G5 (Loại bỏ hoàn toàn cầu gãy)
    Bước 3: Ưu tiên theo quy tắc đầu đuôi bóng
    Bước 4: Vào dàn (Ghép các con số từ các vị trí: Chục từ Đầu, Đơn vị từ Đuôi)
    Bước 5: So với dàn 60 số Cấp 4 (Giao thoa là kết quả tinh túy; chọn Top 1, Top 4)
    Quy tắc số lót: Lấy từ 60 số N1
    """
    print("\n" + "=" * 78)
    print("      XSMB AI - SOI VỊ TRÍ G1->G5 & CHU KỲ NỔ THEO 5 BƯỚC CHUẨN HÓA")
    print("=" * 78)
    
    html = fetch_mketqua_html(count=10)
    if not html:
        print("[!] Không thể lấy dữ liệu từ mketqua.net!")
        return None
        
    draws = parse_lottery_blocks(html)
    if len(draws) < 2:
        print("[!] Dữ liệu cào về không đủ số kỳ để phân tích.")
        return None

    target_draw = draws[target_draw_idx]
    prev_draw_idx = target_draw_idx + 1
    
    print(f"[*] Kỳ đang soi/quay:  [{target_draw['date']}] - GDB: {target_draw['db'] or '(Đang quay...)'} (Đề: {target_draw['de'] or '??'})")
    print(f"[*] Kỳ trước làm gốc: [{draws[prev_draw_idx]['date']}] - GDB: {draws[prev_draw_idx]['db']} (Đề: {draws[prev_draw_idx]['de']})")
    
    analysis = analyze_bridge_cycles(draws, target_draw_idx=target_draw_idx)
    if not analysis:
        print("[!] Không thể phân tích chu kỳ từ kỳ trước.")
        return None

    print("\n" + "-" * 78)
    print(f" BƯỚC 1: ĐỀ HÔM TRƯỚC [{analysis['prev_date']}] & TẬP CHẠM ĐẦU / ĐUÔI")
    print("-" * 78)
    print(f"  • Đề ngày hôm trước: {analysis['prev_de']} (Giải ĐB: {analysis['prev_db']})")
    print(f"  • Chạm Đầu = {analysis['head']}  --> Bóng dương = {analysis['head_bong']}  ==> Tập Đầu: [{analysis['head']}, {analysis['head_bong']}]")
    print(f"  • Chạm Đuôi = {analysis['tail']}  --> Bóng dương = {analysis['tail_bong']}  ==> Tập Đuôi: [{analysis['tail']}, {analysis['tail_bong']}]")

    head_positions = analysis['head_positions']
    tail_positions = analysis['tail_positions']

    print("\n" + "-" * 78)
    print(f" BƯỚC 2 & 3: VỊ TRÍ MỚI CHẠM & CHU KỲ (ƯU TIÊN QUY TẮC ĐẦU ĐUÔI BÓNG)")
    print("-" * 78)
    print(f"  • Tổng vị trí Chạm Đầu ({analysis['head']}, {analysis['head_bong']}): {len(head_positions)} vị trí")
    print(f"      - Chạy 3-4 ngày (Chỉ đạo): {sum(1 for x in head_positions if x['cycle_days'] >= 3)} vị trí")
    print(f"      - Chạy 2 ngày (Lót):      {sum(1 for x in head_positions if x['cycle_days'] == 2)} vị trí")
    print(f"      - Mới chạm 1 ngày:        {sum(1 for x in head_positions if x['cycle_days'] == 1)} vị trí")
    print(f"  • Tổng vị trí Chạm Đuôi ({analysis['tail']}, {analysis['tail_bong']}): {len(tail_positions)} vị trí")
    print(f"      - Chạy 3-4 ngày (Chỉ đạo): {sum(1 for x in tail_positions if x['cycle_days'] >= 3)} vị trí")
    print(f"      - Chạy 2 ngày (Lót):      {sum(1 for x in tail_positions if x['cycle_days'] == 2)} vị trí")
    print(f"      - Mới chạm 1 ngày:        {sum(1 for x in tail_positions if x['cycle_days'] == 1)} vị trí")

    # BƯỚC 4: Vào dàn (Ghép các con số từ các vị trí theo quy tắc đầu đuôi bóng)
    # Hàng Chục lấy từ các vị trí Đầu, Hàng Đơn Vị lấy từ các vị trí Đuôi
    all_pairs = []
    for h in head_positions:
        for t in tail_positions:
            num_str = f"{h['digit']}{t['digit']}"
            pair_cycle = max(h['cycle_days'], t['cycle_days'])
            
            if pair_cycle >= 4:
                cat = "Chỉ đạo"
                cat_label = "✅ CHỈ ĐẠO (4 ngày)"
            elif pair_cycle == 3:
                cat = "Chỉ đạo"
                cat_label = "✅ CHỈ ĐẠO (3 ngày)"
            elif pair_cycle == 2:
                cat = "Lót"
                cat_label = "Lót ngày 2"
            else:
                cat = "Theo dõi"
                cat_label = "Theo dõi ngày 1 (Mới chạm)"

            all_pairs.append({
                'num': num_str,
                'c_digit': h['digit'],
                'd_digit': t['digit'],
                'c_cycle': h['cycle_days'],
                'd_cycle': t['cycle_days'],
                'cycle_days': pair_cycle,
                'category': cat,
                'cat_label': cat_label
            })

    # Nhóm theo con số (loại trùng, giữ chu kỳ cao nhất)
    unique_numbers_map = {}
    for p in all_pairs:
        n = p['num']
        if n not in unique_numbers_map or p['cycle_days'] > unique_numbers_map[n]['cycle_days']:
            unique_numbers_map[n] = p
        elif p['cycle_days'] == unique_numbers_map[n]['cycle_days']:
            # Nếu bằng chu kỳ thì cộng dồn độ mạnh
            cur_sum = unique_numbers_map[n]['c_cycle'] + unique_numbers_map[n]['d_cycle']
            new_sum = p['c_cycle'] + p['d_cycle']
            if new_sum > cur_sum:
                unique_numbers_map[n] = p

    found_numbers = list(unique_numbers_map.values())

    # BƯỚC 5: So với dàn 60 số Cấp 4 (Giao thoa là kết quả tinh túy)
    if custom_cap4:
        cap4_numbers = set(custom_cap4)
    else:
        cap4_numbers = set(load_cap4_numbers(cap4_csv))

    for item in found_numbers:
        item['in_cap4'] = (item['num'] in cap4_numbers)
        item['in_cap4_str'] = "Có" if item['in_cap4'] else "Không"

    # CHỌN TOP 1 & TOP 4 (QUY TẮC CẦU CHẠY NGÀY 3, 4 ƯU TIÊN TOP 1, TOP 4)
    # Lấy các số có chu kỳ >= 3 ngày (Chỉ đạo) và nằm trong 60 số Cấp 4
    chidao_pool = [x for x in found_numbers if x['category'] == "Chỉ đạo" and x['in_cap4']]
    
    # Sắp xếp ưu tiên: 4 ngày trước, sau đó đến 3 ngày, tổng chu kỳ chục+đơn vị
    chidao_pool.sort(key=lambda x: (x['cycle_days'], x['c_cycle'] + x['d_cycle']), reverse=True)

    top_1 = chidao_pool[0]['num'] if len(chidao_pool) >= 1 else None
    top_4_nums = [x['num'] for x in chidao_pool[:4]]

    # Gán nhãn Top cho từng con số
    for item in found_numbers:
        n = item['num']
        if n == top_1:
            item['top_rank'] = "👑 Top 1"
        elif n in top_4_nums:
            item['top_rank'] = "🔥 Top 4"
        elif item['category'] == "Lót" and item['in_cap4']:
            item['top_rank'] = "Lót ngày 2"
        elif item['category'] == "Theo dõi" and item['in_cap4']:
            item['top_rank'] = "Ngày 1 (Mới chạm)"
        else:
            item['top_rank'] = "-"

    # Sắp xếp danh sách hiển thị bảng 5 cột
    def sort_key(x):
        tier = 0
        if x['top_rank'] == "👑 Top 1": tier = 4
        elif x['top_rank'] == "🔥 Top 4": tier = 3
        elif x['top_rank'] == "Lót ngày 2": tier = 2
        elif x['top_rank'] == "Ngày 1 (Mới chạm)": tier = 1
        return (tier, x['cycle_days'], 1 if x['in_cap4'] else 0)

    found_numbers.sort(key=sort_key, reverse=True)

    # In bảng 5 cột
    print("\n" + "=" * 78)
    print(" BẢNG PHÂN TẦNG 5 CỘT (QUY TẮC: CẦU CHẠY 3-4 NGÀY LẤY BÌNH THƯỜNG / GÃY THÌ LOẠI BỎ)")
    print("=" * 78)
    print(f"{'Con Số':^8} | {'Vị Trí Lặp':^12} | {'Phân Loại':^28} | {'Trong 60 Số?':^14} | {'Phân Hạng Top':^18}")
    print("-" * 78)

    for item in found_numbers:
        c_so = item['num']
        c_lap = f"{item['cycle_days']} ngày"
        c_loai = item['cat_label']
        c_60 = item['in_cap4_str']
        c_top = item['top_rank']
        print(f"{c_so:^8} | {c_lap:^12} | {c_loai:<28} | {c_60:^14} | {c_top:^18}")

    # Báo cáo Top 1 & Top 4
    print("\n" + "=" * 78)
    print(" KẾT QUẢ TOP 1 & TOP 4 (ƯU TIÊN CẦU CHẠY NGÀY 3, 4 NẰM TRONG 60 SỐ)")
    print("=" * 78)
    if top_1:
        t1_info = unique_numbers_map[top_1]
        print(f"  ★ TOP 01 QUÁN QUÂN: [{top_1}] (Vị trí lặp {t1_info['cycle_days']} ngày - {t1_info['cat_label']})")
    print(f"  ★ TOP 04 TỨ THỦ TINH TÚY:")
    for idx, num in enumerate(top_4_nums, 1):
        info = unique_numbers_map[num]
        print(f"      {idx}. Con [{num}]  --  Vị trí lặp: {info['cycle_days']} ngày  --  [{info['cat_label']}]")

    # Dàn Ngày 1 Tinh Túy: Các số giao thoa 60 số
    dan_ngay1_tinhtuy = sorted([x['num'] for x in found_numbers if x['in_cap4']])
    print(f"\n  ★ DÀN TINH TÚY GIAO THOA 60 SỐ CẤP 4 ({len(dan_ngay1_tinhtuy)} số):")
    print(f"      {dan_ngay1_tinhtuy}")

    # QUY TẮC 5: SỐ LÓT LẤY TỪ 60 SỐ N1
    dan_n1_list = [f"{x:02d}" for x in sorted(DEFAULT_60_CAP4)]
    dan_lot_list = [x for x in dan_n1_list if x != top_1 and x not in top_4_nums]
    dan_lot_display = [f"{x} (lót)" for x in dan_lot_list]

    print(f"\n  ★ QUY TẮC 5: DÀN SỐ LÓT (LẤY TỪ 60 SỐ N1 - {len(dan_lot_list)} số):")
    print(f"      {dan_lot_list}")

    # Kiểm chứng thực tế nếu đã có kết quả
    actual_de = target_draw['de']
    if actual_de:
        is_hit_top1 = (actual_de == top_1)
        is_hit_top4 = (actual_de in top_4_nums)
        actual_info = unique_numbers_map.get(actual_de)
        
        print("\n" + "-" * 78)
        print(f" KIỂM CHỨNG THỰC TẾ KỲ QUAY [{target_draw['date']}]: ĐỀ VỀ {actual_de}")
        print("-" * 78)
        if actual_info:
            print(f"  • Con {actual_de} thuộc nhóm: {actual_info['cat_label']} (Lặp {actual_info['cycle_days']} ngày)")
            print(f"  • Nằm trong 60 số Cấp 4: {actual_info['in_cap4_str']}")
            print(f"  • Trúng Top 1: {'✓ TRÚNG TOP 1' if is_hit_top1 else 'Không'}")
            print(f"  • Trúng Top 4: {'✓ TRÚNG TOP 4' if is_hit_top4 else 'Không'}")
            if actual_info['category'] == "Lót":
                print(f"  • 🎯 NỔ LÓT NGÀY 2 ({actual_de}) ==> SẼ TRỞ THÀNH TỔNG LỰC NGÀY 3 Ở KỲ TIẾP THEO!")
        else:
            in_n1 = actual_de in dan_n1_list
            print(f"  • Con {actual_de} nằm trong Dàn Lót 60 số N1: {'✓ TRÚNG SỐ LÓT N1' if in_n1 else 'Không'}")

    # Trích xuất bảng kết quả trực tiếp G1 -> G5.6
    live_prizes = {
        'g1': target_draw['prizes'].get('G1', ''),
        'g2': [target_draw['prizes'].get('G2.1', ''), target_draw['prizes'].get('G2.2', '')],
        'g3': [target_draw['prizes'].get(f'G3.{i}', '') for i in range(1, 7)],
        'g4': [target_draw['prizes'].get(f'G4.{i}', '') for i in range(1, 5)],
        'g5': [target_draw['prizes'].get(f'G5.{i}', '') for i in range(1, 7)]
    }
    
    total_g1_to_g5 = 1 + 2 + 6 + 4 + 6 # 19 giải
    filled_g1_to_g5 = (1 if live_prizes['g1'] else 0) + \
                      sum(1 for x in live_prizes['g2'] if x) + \
                      sum(1 for x in live_prizes['g3'] if x) + \
                      sum(1 for x in live_prizes['g4'] if x) + \
                      sum(1 for x in live_prizes['g5'] if x)

    is_g5_finished = (filled_g1_to_g5 == total_g1_to_g5)

    # Dàn N2, N3
    n2_candidates = [
        11, 12, 13, 15, 17, 18, 19, 21, 22, 23, 28, 29, 31, 32, 33, 35, 37, 38,
        42, 44, 45, 51, 53, 55, 58, 59, 61, 62, 63, 65, 67, 81, 82, 83, 85, 87
    ]
    dan_n2_clean = sorted([f"{x:02d}" for x in n2_candidates if f"{x:02d}" in dan_n1_list])
    for num in dan_n1_list:
        if len(dan_n2_clean) >= 36:
            break
        if num not in dan_n2_clean:
            dan_n2_clean.append(num)
    dan_n2_list = sorted(dan_n2_clean[:36])
    dan_n3_list = list(dan_n2_list)

    # Trạng thái chuyển cầu ngày mới
    is_n1_hit = (actual_de in dan_n1_list) if actual_de else False
    frame_transition = {
        'last_result': f"Kỳ gần nhất ({target_draw['date']}) đã {'trúng N1 → RESET CẦU MỚI' if is_n1_hit else 'chưa nổ N1'}",
        'status_badge': "ĐÃ TRÚNG N1 → RESET CẦU MỚI" if is_n1_hit else "ĐANG THEO DÕI KHUNG",
        'schedule_n1': "Đánh chính: Kỳ tiếp theo (Dàn 60 Số N1)",
        'schedule_n2': "Dự phòng N2: Ngày thứ 2 (36 số)",
        'schedule_n3': "Dự phòng N3: Ngày thứ 3 (36 số)"
    }

    # BẢNG MA TRẬN TÔ MÀU VỊ TRÍ CẦU (3 LOẠI CHUẨN HOÁ):
    # 1. 🟡 VÀNG: Chỉ đạo (3-4 ngày)
    # 2. 🔵 XANH: Lót (2 ngày)
    # 3. ⚪ TRẮNG/MỜ: Theo dõi (1 ngày)
    # Cầu gãy: Loại bỏ hoàn toàn
    highlight_positions = {}
    for role_name, pos_group in [('Đầu', head_positions), ('Đuôi', tail_positions)]:
        for it in pos_group:
            p_str = it['position']
            norm_key = re.sub(r'\s+vị\s+trí\s+', '_', p_str)
            cycle = it['cycle_days']

            if cycle >= 3:
                c_type = 'cycle_main'
            elif cycle == 2:
                c_type = 'cycle_lot'
            else:
                c_type = 'cycle_watch'

            if norm_key in highlight_positions:
                prev_cycle = highlight_positions[norm_key]['cycle']
                if cycle < prev_cycle:
                    continue

            highlight_positions[norm_key] = {
                'pos_raw': p_str,
                'role': 'head' if role_name == 'Đầu' else 'tail',
                'role_name': role_name,
                'digit': it['digit'],
                'cycle': cycle,
                'cycle_suffix': f"{cycle}d",
                'category': it['category'],
                'label': it['label'],
                'color_type': c_type,
                'tooltip': f"{p_str}: {role_name} {it['digit']} ({cycle}d) | {it['label']}"
            }

    top_1_cycle = unique_numbers_map[top_1]['cycle_days'] if top_1 and top_1 in unique_numbers_map else 3
    top_1_display = f"{top_1} ({top_1_cycle}d)" if top_1 else ""

    top_4_display = []
    for num in top_4_nums:
        c = unique_numbers_map[num]['cycle_days'] if num in unique_numbers_map else 3
        top_4_display.append(f"★ {num} ({c}d)")

    # Xuất kết quả JSON
    output_data = {
        'target_date': target_draw['date'],
        'prev_date': draws[prev_draw_idx]['date'],
        'prev_de': analysis['prev_de'],
        'head_targets': [analysis['head'], analysis['head_bong']],
        'tail_targets': [analysis['tail'], analysis['tail_bong']],
        'live_prizes': live_prizes,
        'highlight_positions': highlight_positions,
        'filled_count': filled_g1_to_g5,
        'total_count': total_g1_to_g5,
        'is_g5_finished': is_g5_finished,
        'dan_ghep': sorted(list(unique_numbers_map.keys())),
        'dan_ngay_1_tinhtuy': dan_ngay1_tinhtuy,
        'dan_giao_thoa': dan_ngay1_tinhtuy,
        'top_1': top_1,
        'top_1_display': top_1_display,
        'top_4': top_4_nums,
        'top_4_display': top_4_display,
        'dan_lot': dan_lot_list,
        'dan_lot_display': dan_lot_display,
        'dan_n1': dan_n1_list,
        'dan_n2': dan_n2_list,
        'dan_n3': dan_n3_list,
        'frame_transition': frame_transition,
        'table_5cols': found_numbers,
        'actual_de': actual_de
    }
    
    with open('ket_qua_soi_cau_g1_g5.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\n[*] Đã lưu toàn bộ kết quả phân tầng 5 cột vào: ket_qua_soi_cau_g1_g5.json")

    return output_data

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="XSMB AI - Soi Vị Trí G1->G5 & Chu Kỳ Nổ Ngày 3, 4")
    parser.add_argument('--live', action='store_true', help='Bật chế độ giám sát Real-time trong lúc quay thưởng')
    parser.add_argument('--interval', type=int, default=10, help='Khoảng thời gian thăm dò Real-time (giây)')
    parser.add_argument('--backtest', type=int, default=0, help='Chỉ số kỳ cần soi (0: mới nhất, 1: kỳ trước)')
    parser.add_argument('--csv', type=str, default=DEFAULT_CAP4_CSV, help='Đường dẫn file CSV 60 số Cấp 4')
    parser.add_argument('--max-minutes', type=int, default=25, help='Thời gian tối đa chạy live (phút)')
    args = parser.parse_args()

    if args.live:
        print("\n" + "=" * 78)
        print(f" [*] ĐANG CHẠY CHẾ ĐỘ GIÁM SÁT REAL-TIME (Tự động cập nhật mỗi {args.interval} giây)")
        print(" [*] Radar tự động lấy kết quả trực tiếp từ Giải 1 -> Giải 5.6 (bỏ qua G6, G7)")
        print(" [*] Ngay khi Giải 5.6 nổ xong, hệ thống sẽ tự động chốt Dàn Tinh Túy & Tô Màu Cầu")
        print("=" * 78)
        last_filled = -1
        start_time = time.time()
        max_duration = args.max_minutes * 60
        while True:
            if time.time() - start_time > max_duration:
                print(f"\n[*] Đã đạt giới hạn thời gian chạy ({args.max_minutes} phút). Dừng phiên live.")
                break
            try:
                res = run_pipeline(target_draw_idx=0, cap4_csv=args.csv)
                if res:
                    filled = res.get('filled_count', 0)
                    total = res.get('total_count', 19)
                    now_str = datetime.now().strftime('%H:%M:%S')
                    if filled != last_filled:
                        print(f"\n>>> [{now_str}] CẬP NHẬT MỚI: Đã quay {filled}/{total} giải.")
                        last_filled = filled
                    
                    if res.get('is_g5_finished'):
                        print(f"\n[★ {now_str}] ĐÃ HOÀN TẤT GIẢI 5.6! XUẤT THÀNH CÔNG DÀN TINH TÚY & TÔ MÀU VỊ TRÍ CẦU.")
                        print(f"      Top 1: {res.get('top_1')} | Top 4: {res.get('top_4')}")
                        break
                time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\n[*] Đã dừng chế độ giám sát Real-time.")
                break
            except Exception as e:
                print(f"[!] Thử lại sau {args.interval}s do lỗi kết nối: {e}")
                time.sleep(args.interval)
    else:
        run_pipeline(target_draw_idx=args.backtest, cap4_csv=args.csv)
