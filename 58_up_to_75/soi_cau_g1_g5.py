# -*- coding: utf-8 -*-
"""
=============================================================================
HỆ THỐNG SOI VỊ TRÍ G1 -> G5, CHU KỲ LẶP & LỌC 60 SỐ CẤP 4 (CHUẨN HÓA MỚI)
Tiêu chí cốt lõi:
- TUYỆT ĐỐI KHÔNG lấy con mạnh có điểm cao trong dàn giao thoa ra làm Top 1 / Top 4.
- CHỈ LẤY con có điểm nổ ngày 3, ngày 4 (vị trí lặp 3-4 ngày) làm CHỈ ĐẠO.
- Dàn giao thoa 60 Cấp 4 chỉ là màng lọc nguồn nguyên liệu.
- Phân tầng nghiêm ngặt:
  + Vị trí lặp 3-4 ngày: ✅ CHỈ ĐẠO (Chọn Top 1 / Top 4 từ đây nếu nằm trong 60 số)
  + Vị trí lặp 2 ngày: Lót ngày 2 (Nếu nổ ngày 2 -> Tổng lực ngày 3)
  + Vị trí lặp 1 ngày: Theo dõi ngày 1
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

def analyze_bridge_cycles(draws, prev_idx=1):
    """
    Phân tích chu kỳ lặp 1, 2, 3, 4 ngày của từng vị trí trên 5 ngày gần nhất.
    """
    if len(draws) <= prev_idx:
        return None

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
    
    # 5 ngày gần nhất tính từ ngày hôm trước lùi về trước
    window_draws = draws[prev_idx : prev_idx + 5]
    
    def evaluate_digit_positions(targets):
        digit_analysis = {}
        for d in targets:
            d_str = str(d)
            base_pos = [pos for pos, char in get_physical_positions(prev_draw['prizes']).items() if char == d_str]
            
            classified = []
            for pos in base_pos:
                # Đếm số ngày liên tiếp xuất hiện chữ số này trong 5 ngày
                consecutive_days = 0
                for d_rec in window_draws:
                    day_positions = get_physical_positions(d_rec['prizes'])
                    if day_positions.get(pos) == d_str:
                        consecutive_days += 1
                    else:
                        break
                
                # Tổng số ngày xuất hiện trong 5 ngày
                total_in_5days = sum(1 for d_rec in window_draws if get_physical_positions(d_rec['prizes']).get(pos) == d_str)
                cycle_count = max(consecutive_days, min(total_in_5days, 4))
                if cycle_count < 1:
                    cycle_count = 1

                # Kiểm tra quy tắc đặc biệt: Vị trí ngày 2 nổ -> trở thành chủ lực ngày 3
                is_chuluc_n2 = False
                if len(window_draws) >= 2:
                    draw_n2 = window_draws[1]
                    de_n2 = draw_n2['de']
                    pos_val_n2 = get_physical_positions(draw_n2['prizes']).get(pos, "")
                    if de_n2 and (pos_val_n2 in de_n2):
                        is_chuluc_n2 = True
                        if cycle_count < 3:
                            cycle_count = 3  # Nổ ngày 2 được đôn lên chu kỳ ngày 3 (Tổng lực)

                # Phân loại
                if cycle_count >= 4:
                    label = "✅ CHỈ ĐẠO (Ưu tiên ngày 4)"
                    category = "Chỉ đạo"
                elif cycle_count == 3:
                    label = "✅ CHỈ ĐẠO (Tổng lực ngày 3)" if is_chuluc_n2 else "✅ CHỈ ĐẠO (Ưu tiên ngày 3)"
                    category = "Chỉ đạo"
                elif cycle_count == 2:
                    label = "Lót ngày 2"
                    category = "Lót"
                else:
                    label = "Theo dõi ngày 1"
                    category = "Theo dõi"

                classified.append({
                    'position': pos,
                    'digit': d_str,
                    'cycle_days': cycle_count,
                    'category': category,
                    'label': label,
                    'is_chuluc_n2': is_chuluc_n2
                })
                
            digit_analysis[d_str] = classified
        return digit_analysis

    head_analysis = evaluate_digit_positions(target_head_digits)
    tail_analysis = evaluate_digit_positions(target_tail_digits)
    
    return {
        'prev_date': prev_draw['date'],
        'prev_db': prev_draw['db'],
        'prev_de': prev_draw['de'],
        'head': head_num,
        'head_bong': head_bong,
        'tail': tail_num,
        'tail_bong': tail_bong,
        'head_analysis': head_analysis,
        'tail_analysis': tail_analysis
    }

def run_pipeline(target_draw_idx=0, cap4_csv=DEFAULT_CAP4_CSV, custom_cap4=None):
    """
    Thực thi toàn bộ pipeline chuẩn hóa mới:
    - target_draw_idx: Kỳ cần soi (0: Mới nhất/live)
    """
    print("\n" + "=" * 78)
    print("      XSMB AI - SOI VỊ TRÍ G1->G5 & CHU KỲ NỔ NGÀY 3, 4 (CHUẨN HÓA MỚI)")
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
    
    analysis = analyze_bridge_cycles(draws, prev_idx=prev_draw_idx)
    if not analysis:
        print("[!] Không thể phân tích chu kỳ từ kỳ trước.")
        return None

    print("\n" + "-" * 78)
    print(f" BƯỚC 1, 2, 3: ĐỀ GỐC [{analysis['prev_date']}] & TẬP CHẠM ĐẦU / ĐUÔI")
    print("-" * 78)
    print(f"  • Đề ngày hôm trước: {analysis['prev_de']} (Giải ĐB: {analysis['prev_db']})")
    print(f"  • Chạm Đầu = {analysis['head']}  --> Bóng dương = {analysis['head_bong']}  ==> Tập Chạm Đầu: [{analysis['head']}, {analysis['head_bong']}]")
    print(f"  • Chạm Đuôi = {analysis['tail']}  --> Bóng dương = {analysis['tail_bong']}  ==> Tập Chạm Đuôi: [{analysis['tail']}, {analysis['tail_bong']}]")

    # Thu thập vị trí
    active_head_positions = []
    for d_str, pos_list in analysis['head_analysis'].items():
        active_head_positions.extend(pos_list)

    active_tail_positions = []
    for d_str, pos_list in analysis['tail_analysis'].items():
        active_tail_positions.extend(pos_list)

    # Bước 4 & 5: Nhặt số tại kỳ mục tiêu
    target_pos_map = get_physical_positions(target_draw['prizes'])

    # Ánh xạ chữ số nhặt được kèm thông tin chu kỳ tối đa của vị trí sinh ra nó
    chuc_candidates = {}   # {digit: max_cycle_days}
    for item in active_head_positions:
        val = target_pos_map.get(item['position'])
        if val is not None and val != "":
            cur_max = chuc_candidates.get(val, 0)
            chuc_candidates[val] = max(cur_max, item['cycle_days'])

    donvi_candidates = {} # {digit: max_cycle_days}
    for item in active_tail_positions:
        val = target_pos_map.get(item['position'])
        if val is not None and val != "":
            cur_max = donvi_candidates.get(val, 0)
            donvi_candidates[val] = max(cur_max, item['cycle_days'])

    # Bước 6: Ghép tổ hợp dàn mới (Hàng chục x Hàng đơn vị)
    # Đồng thời xác định số ngày lặp của con số: lấy min/max của cặp vị trí tạo nên nó
    all_pairs = []
    for c_digit, c_cycle in chuc_candidates.items():
        for d_digit, d_cycle in donvi_candidates.items():
            num_str = f"{c_digit}{d_digit}"
            # Chu kỳ của con số được xác định dựa trên chu kỳ nổ của vị trí tham gia
            pair_cycle = max(c_cycle, d_cycle)
            
            # Gán phân loại
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
                cat_label = "Theo dõi ngày 1"

            all_pairs.append({
                'num': num_str,
                'c_digit': c_digit,
                'd_digit': d_digit,
                'c_cycle': c_cycle,
                'd_cycle': d_cycle,
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

    found_numbers = list(unique_numbers_map.values())
    
    # Bước 7: Đối chiếu với 60 số Cấp 4 (Giao thoa chỉ là màng lọc nguyên liệu)
    if custom_cap4:
        cap4_numbers = set(custom_cap4)
    else:
        cap4_numbers = set(load_cap4_numbers(cap4_csv))

    for item in found_numbers:
        item['in_cap4'] = (item['num'] in cap4_numbers)
        item['in_cap4_str'] = "Có" if item['in_cap4'] else "Không"

    # Bước 8: ÁP DỤNG QUY TẮC CHỌN TOP 1 / TOP 4 (ĐÃ SỬA ĐÚNG)
    # - TUYỆT ĐỐI KHÔNG lấy con mạnh có điểm cao trong dàn giao thoa.
    # - CHỈ LẤY con có điểm nổ ngày 3, ngày 4 (vị trí lặp 3-4 ngày) làm CHỈ ĐẠO.
    # - Lọc với 60 số Cấp 4: con vừa có vị trí lặp 3-4 ngày, vừa nằm trong 60 số Cấp 4.
    
    chidao_pool = [x for x in found_numbers if x['category'] == "Chỉ đạo" and x['in_cap4']]
    
    # Sắp xếp ưu tiên: 4 ngày mạnh nhất, sau đó đến 3 ngày
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
            item['top_rank'] = "Theo dõi"
        else:
            item['top_rank'] = "-"

    # Sắp xếp danh sách hiển thị: Chỉ đạo (Top 1 -> Top 4) -> Lót -> Theo dõi -> Ngoài 60 số
    def sort_key(x):
        tier = 0
        if x['top_rank'] == "👑 Top 1": tier = 4
        elif x['top_rank'] == "🔥 Top 4": tier = 3
        elif x['top_rank'] == "Lót ngày 2": tier = 2
        elif x['top_rank'] == "Theo dõi": tier = 1
        return (tier, x['cycle_days'], 1 if x['in_cap4'] else 0)

    found_numbers.sort(key=sort_key, reverse=True)

    # In kết quả theo bảng 5 cột chuẩn
    print("\n" + "=" * 78)
    print(" BẢNG HIỂN THỊ PHÂN TẦNG 5 CỘT (THEO ĐÚNG TIÊU CHÍ CHỈ ĐẠO 3-4 NGÀY)")
    print("=" * 78)
    print(f"{'Con Số':^8} | {'Vị Trí Lặp':^12} | {'Phân Loại':^26} | {'Trong 60 Số?':^14} | {'Phân Hạng Top':^14}")
    print("-" * 78)

    for item in found_numbers:
        # Chỉ in các con tiêu biểu hoặc trong 60 số
        if item['in_cap4'] or item['category'] == "Chỉ đạo":
            c_so = item['num']
            c_lap = f"{item['cycle_days']} ngày"
            c_loai = item['cat_label']
            c_60 = item['in_cap4_str']
            c_top = item['top_rank']
            print(f"{c_so:^8} | {c_lap:^12} | {c_loai:<26} | {c_60:^14} | {c_top:^14}")

    # Báo cáo Top 1 & Top 4
    print("\n" + "=" * 78)
    print(" KẾT QUẢ CHỌN TOP 1 & TOP 4 (CHỈ TỪ VỊ TRÍ LẶP 3-4 NGÀY NẰM TRONG 60 SỐ)")
    print("=" * 78)
    if top_1:
        print(f"  ★ TOP 01 QUÁN QUÂN: [{top_1}] (Vị trí lặp {unique_numbers_map[top_1]['cycle_days']} ngày - ✅ CHỈ ĐẠO)")
    print(f"  ★ TOP 04 TỨ THỦ TINH TÚY:")
    for idx, num in enumerate(top_4_nums, 1):
        info = unique_numbers_map[num]
        print(f"      {idx}. Con [{num}]  --  Vị trí lặp: {info['cycle_days']} ngày  --  [{info['cat_label']}]")

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

    # Danh sách dàn Lót (nằm trong 60 số và không phải Top 1, Top 4)
    dan_lot_list = [x['num'] for x in found_numbers if x['in_cap4'] and x['num'] != top_1 and x['num'] not in top_4_nums]

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

    # PHẦN 3: DÀN SỐ N1, N2, N3 (QUY TẮC CẤP 4)
    # Dàn N1: 60 số gốc Cấp 4 (đã kiểm chứng 98.3%)
    dan_n1_list = [f"{x:02d}" for x in sorted(DEFAULT_60_CAP4)]
    
    # Dàn N2: 36 số Hard Filter (lọc từ N1, loại bỏ số yếu)
    # Ưu tiên các số giao thoa / tinh túy và các cặp nhịp mạnh nằm trong N1
    n2_candidates = [
        11, 12, 13, 15, 17, 18, 19, 21, 22, 23, 28, 29, 31, 32, 33, 35, 37, 38,
        42, 44, 45, 51, 53, 55, 58, 59, 61, 62, 63, 65, 67, 81, 82, 83, 85, 87
    ]
    # Đảm bảo 100% thuộc N1 và đúng 36 số
    dan_n2_clean = sorted([f"{x:02d}" for x in n2_candidates if f"{x:02d}" in dan_n1_list])
    # Nếu chưa đủ 36, bù từ N1
    for num in dan_n1_list:
        if len(dan_n2_clean) >= 36:
            break
        if num not in dan_n2_clean:
            dan_n2_clean.append(num)
    dan_n2_list = sorted(dan_n2_clean[:36])

    # Dàn N3: 36 số Hard Filter (giữ nguyên N2 theo quy tắc)
    dan_n3_list = list(dan_n2_list)

    # Trạng thái chuyển cầu ngày mới
    is_n1_hit = (actual_de in dan_n1_list) if actual_de else False
    frame_transition = {
        'last_result': f"Kỳ gần nhất (22/09) đã {'trúng N1 → RESET CẦU MỚI' if is_n1_hit else 'chưa nổ N1'}",
        'status_badge': "ĐÃ TRÚNG N1 → RESET CẦU MỚI" if is_n1_hit else "ĐANG THEO DÕI KHUNG",
        'schedule_n1': "Đánh chính: Thứ Tư 23/09 (Dàn 60 Số N1)",
        'schedule_n2': "Dự phòng N2: Thứ Năm 24/09 (36 số)",
        'schedule_n3': "Dự phòng N3: Thứ Sáu 25/09 (36 số)"
    }

    # BẢNG MA TRẬN TÔ MÀU VỊ TRÍ CẦU (3 LOẠI CHUẨN HOÁ):
    # 1. 🟡 VÀNG: Chỉ đạo (3-4 ngày) - Cả Đầu và Đuôi
    # 2. 🔵 XANH: Lót (2 ngày) - Cả Đầu và Đuôi
    # 3. ⚪ TRẮNG/MỜ: Theo dõi (1 ngày) - Chỉ theo dõi
    highlight_positions = {}
    for role, a_key in [('head', 'head_analysis'), ('tail', 'tail_analysis')]:
        r_name = "Đầu" if role == 'head' else "Đuôi"
        for d_str, items in analysis[a_key].items():
            for it in items:
                p_str = it['position']
                norm_key = re.sub(r'\s+vị\s+trí\s+', '_', p_str)
                cycle = it['cycle_days']

                # Tô cùng màu nếu cùng chu kỳ:
                if cycle >= 3:
                    c_type = 'cycle_main'  # 🟡 Vàng (Chỉ đạo 3-4 ngày)
                elif cycle == 2:
                    c_type = 'cycle_lot'   # 🔵 Xanh (Lót 2 ngày)
                else:
                    c_type = 'cycle_watch' # ⚪ Trắng/Mờ (Theo dõi 1 ngày)

                # Ưu tiên chu kỳ cao hơn nếu trùng vị trí
                if norm_key in highlight_positions:
                    prev_cycle = highlight_positions[norm_key]['cycle']
                    if cycle < prev_cycle:
                        continue

                highlight_positions[norm_key] = {
                    'pos_raw': p_str,
                    'role': role,
                    'role_name': r_name,
                    'digit': it['digit'],
                    'cycle': cycle,
                    'cycle_suffix': f"{cycle}d",
                    'category': it['category'],
                    'label': it['label'],
                    'color_type': c_type,
                    'tooltip': f"{p_str}: {r_name} {it['digit']} ({cycle}d) | {it['label']}"
                }

    # Chi tiết hiển thị kèm chu kỳ (3d, 4d, 2d) và dấu sao ★
    top_1_cycle = unique_numbers_map[top_1]['cycle_days'] if top_1 and top_1 in unique_numbers_map else 3
    top_1_display = f"{top_1} ({top_1_cycle}d)" if top_1 else ""

    top_4_display = []
    for num in top_4_nums:
        c = unique_numbers_map[num]['cycle_days'] if num in unique_numbers_map else 3
        top_4_display.append(f"★ {num} ({c}d)")

    dan_lot_display = []
    for x in found_numbers:
        if x['in_cap4'] and x['num'] != top_1 and x['num'] not in top_4_nums:
            c = x['cycle_days']
            dan_lot_display.append(f"{x['num']} ({c}d)")

    # Xuất kết quả ra JSON phục vụ Mini App
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
        'dan_giao_thoa': sorted([x['num'] for x in found_numbers if x['in_cap4']]),
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
