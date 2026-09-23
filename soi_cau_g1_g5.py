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
from collections import Counter
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

def get_weekly_cycle_mode(draw_date_str=None):
    """
    Áp dụng chu kỳ 7 ngày (Cấp 4):
    Tuần 1 (1-7): Bảo hiểm mở rộng (N2: 42 số, N3: 40 số)
    Tuần 2 (8-14): Hard Filter (N2: 38 số, N3: 36 số)
    Tuần 3 (15-21): Bảo hiểm mở rộng (N2: 45 số, N3: 42 số)
    Tuần 4+ (22 trở đi): Hard Filter Mở rộng (N2: 42 số, N3: 40 số)
    """
    day = 23
    if draw_date_str:
        match = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', str(draw_date_str))
        if match:
            day = int(match.group(1))
    if 1 <= day <= 7:
        return {'week': 'Tuần 1', 'model': 'Bảo hiểm mở rộng', 'n2_count': 42, 'n3_count': 40, 'note': 'Cầu mở rộng'}
    elif 8 <= day <= 14:
        return {'week': 'Tuần 2', 'model': 'Hard Filter', 'n2_count': 38, 'n3_count': 36, 'note': 'Tiết kiệm vốn'}
    elif 15 <= day <= 21:
        return {'week': 'Tuần 3', 'model': 'Bảo hiểm mở rộng', 'n2_count': 45, 'n3_count': 42, 'note': 'Cầu bùng nổ'}
    else:
        return {'week': 'Tuần 4', 'model': 'Hard Filter Mở Rộng', 'n2_count': 42, 'n3_count': 40, 'note': 'Bảo toàn & Cứu khung'}

def compute_ai_scores(all_draws, target_idx, unique_numbers_map=None):
    """
    Chấm điểm AI Score (0.0 - 10.0) cho các con số 2D:
    - Tần suất 30 kỳ (Golden Frequency)
    - Nhịp gan lý tưởng (5 - 25 ngày)
    - Phạt số bệt 2 ngày liên tiếp
    - Phạt gan cực đại (> 45 ngày)
    - Thưởng điểm cầu vị trí G1->G5 đang chạy (Chỉ đạo: +2.5, Lót: +1.5, Theo dõi: +0.8)
    - Loại bỏ cầu gãy hoàn toàn
    """
    prev_de = all_draws[target_idx + 1]['de'] if target_idx + 1 < len(all_draws) else None
    prev_prev_de = all_draws[target_idx + 2]['de'] if target_idx + 2 < len(all_draws) else None
    
    # 30 kỳ gần nhất tính từ target_idx + 1
    hist_30 = [d['de'] for d in all_draws[target_idx + 1: target_idx + 31] if d.get('de')]
    counter_30 = Counter(hist_30)
    
    # Tính độ gan
    gan_dict = {}
    for i in range(100):
        n_str = f"{i:02d}"
        gan = 999
        for step, d in enumerate(all_draws[target_idx + 1:]):
            if d.get('de') == n_str:
                gan = step
                break
        gan_dict[n_str] = gan
        
    bong_map = {0:5, 1:6, 2:7, 3:8, 4:9, 5:0, 6:1, 7:2, 8:3, 9:4}
    dau_set = set()
    duoi_set = set()
    if prev_de and len(prev_de) == 2:
        c = int(prev_de[0])
        dv = int(prev_de[1])
        dau_set = {str(c), str(bong_map[c])}
        duoi_set = {str(dv), str(bong_map[dv])}
        
    scores = {}
    for i in range(100):
        n_str = f"{i:02d}"
        sc = 5.0
        
        # 1. Tần suất 30 kỳ
        freq = counter_30.get(n_str, 0)
        if freq == 1: sc += 1.5
        elif freq == 2: sc += 2.2
        elif freq >= 3: sc += 1.8
        else: sc -= 0.5
        
        # 2. Độ gan
        gan = gan_dict.get(n_str, 999)
        if 5 <= gan <= 25: sc += 1.5
        elif gan > 45: sc -= 3.0
        
        # Bệt 2 ngày liên tiếp -> phạt rất nặng để loại khỏi N2
        if prev_de == n_str and prev_prev_de == n_str:
            sc -= 6.0
        elif prev_de == n_str:
            sc -= 1.5
            
        # 3. Tương hợp Đầu/Đuôi & Bóng
        if n_str[0] in dau_set and n_str[1] in duoi_set:
            sc += 1.2
        elif n_str[0] in dau_set or n_str[1] in duoi_set:
            sc += 0.5
            
        # 4. Cầu vị trí G1->G5
        if unique_numbers_map and n_str in unique_numbers_map:
            info = unique_numbers_map[n_str]
            cat = info.get('category', '')
            cycle = info.get('cycle_days', 0)
            if cat == 'Chỉ đạo' or cycle >= 3:
                sc += 2.5
            elif cat == 'Lót' or cycle == 2:
                sc += 1.5
            elif cycle == 1:
                sc += 0.8
                
        scores[n_str] = round(min(max(sc, 1.0), 9.9), 1)
        
    return scores, gan_dict, prev_de, prev_prev_de

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

    # ÁP DỤNG CHU KỲ 7 NGÀY & TỐI ƯU HÓA MỞ RỘNG N2 (42 SỐ), N3 (40 SỐ)
    weekly_cycle = get_weekly_cycle_mode(target_draw['date'])
    n2_target_count = weekly_cycle['n2_count']
    n3_target_count = weekly_cycle['n3_count']

    # Chấm điểm AI Score cho tất cả 100 số
    all_draws_for_ai = draws
    if os.path.exists('data_2026.json'):
        try:
            with open('data_2026.json', encoding='utf-8') as f:
                d_2026 = json.load(f)
                if len(d_2026) > len(all_draws_for_ai):
                    all_draws_for_ai = d_2026
        except Exception:
            pass

    ai_scores, gan_dict, prev_de_val, prev_prev_de_val = compute_ai_scores(all_draws_for_ai, target_draw_idx, unique_numbers_map)

    # 1. DÀN N2 (42 số - Mở rộng cứu N1):
    # Tuyển chọn số từ N1 và các ứng viên tiềm năng có điểm AI cao
    # Loại bỏ số bệt 2 ngày liên tiếp (đề về 2 ngày liên tục)
    bet_2_days = {prev_de_val} if (prev_de_val and prev_de_val == prev_prev_de_val) else set()
    base_n2_pool = [
        11, 12, 13, 15, 17, 18, 19, 21, 22, 23, 28, 29, 31, 32, 33, 35, 37, 38,
        42, 44, 45, 51, 52, 53, 55, 58, 59, 61, 62, 63, 65, 66, 67, 68, 81, 82,
        83, 85, 87, 90, 95, 98
    ]
    n2_candidates_set = set(f"{x:02d}" for x in base_n2_pool)
    for n in dan_n1_list:
        n2_candidates_set.add(n)
        
    n2_candidates_filtered = [n for n in n2_candidates_set if n not in bet_2_days]
    n2_candidates_filtered.sort(key=lambda x: (ai_scores.get(x, 5.0), 1 if x in dan_n1_list else 0), reverse=True)
    dan_n2_list = sorted(n2_candidates_filtered[:n2_target_count])

    # 2. DÀN N3 (40 số - Cơ hội cuối cứu khung):
    # Tuyển chọn từ Dàn N2, ưu tiên số có điểm AI cao và không bị gan cực đại (> 45 ngày)
    n3_candidates = [n for n in dan_n2_list if gan_dict.get(n, 0) <= 45]
    for n in dan_n2_list:
        if len(n3_candidates) >= n3_target_count:
            break
        if n not in n3_candidates:
            n3_candidates.append(n)
    n3_candidates.sort(key=lambda x: ai_scores.get(x, 5.0), reverse=True)
    dan_n3_list = sorted(n3_candidates[:n3_target_count])

    # Trạng thái chuyển cầu ngày mới
    is_n1_hit = (actual_de in dan_n1_list) if actual_de else False
    is_n2_hit = (actual_de in dan_n2_list) if actual_de else False
    is_n3_hit = (actual_de in dan_n3_list) if actual_de else False

    status_badge = "ĐÃ TRÚNG N1 → RESET CẦU MỚI" if is_n1_hit else ("ĐÃ TRÚNG N2 → CỨU N1 THÀNH CÔNG" if is_n2_hit else ("ĐÃ TRÚNG N3 → CỨU KHUNG THÀNH CÔNG" if is_n3_hit else "ĐANG THEO DÕI KHUNG"))

    frame_transition = {
        'last_result': f"Kỳ gần nhất ({target_draw['date']}) đã {status_badge}",
        'status_badge': status_badge,
        'schedule_n1': f"Đánh chính N1: Kỳ tiếp theo ({len(dan_n1_list)} Số N1)",
        'schedule_n2': f"Dự phòng N2: Ngày thứ 2 ({len(dan_n2_list)} số - Mở rộng cứu N1)",
        'schedule_n3': f"Dự phòng N3: Ngày thứ 3 ({len(dan_n3_list)} số - Cơ hội cuối)",
        'weekly_cycle': weekly_cycle
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
        'dan_tinh_tuy': dan_ngay1_tinhtuy,
        'top_1': top_1,
        'top1': top_1,
        'top_1_display': top_1_display,
        'top_4': top_4_nums,
        'top4': top_4_nums,
        'top_4_display': top_4_display,
        'dan_lot': dan_lot_list,
        'dan_lot_display': dan_lot_display,
        'dan_n1': dan_n1_list,
        'dan_n2': dan_n2_list,
        'dan_n3': dan_n3_list,
        'weekly_cycle': weekly_cycle,
        'ai_scores': ai_scores,
        'frame_transition': frame_transition,
        'table_5cols': found_numbers,
        'actual_de': actual_de
    }
    
    with open('ket_qua_soi_cau_g1_g5.json', 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"\n[*] Đã lưu toàn bộ kết quả phân tầng 5 cột vào: ket_qua_soi_cau_g1_g5.json")

    # Đồng bộ sang thư mục 58_up_to_75 nếu tồn tại
    branch_dir = '58_up_to_75'
    if os.path.exists(branch_dir):
        branch_json_path = os.path.join(branch_dir, 'ket_qua_soi_cau_g1_g5.json')
        with open(branch_json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"[*] Đã đồng bộ sang: {branch_json_path}")

    # BƯỚC 5: TỰ ĐỘNG GHI LỊCH SỬ PHƯƠNG PHÁP HÀNG NGÀY CHO CẢ 2 CƠ CHẾ
    if actual_de:
        # Cơ chế 4A: Khung 3 ngày (58_up_to_75)
        if actual_de in dan_n1_list:
            kq_khung = 'trung_n1'
        elif actual_de in dan_n2_list:
            kq_khung = 'trung_n2'
        elif actual_de in dan_n3_list:
            kq_khung = 'trung_n3'
        else:
            kq_khung = 'truot_khung'
        ghi_lich_su_khung(target_draw['date'], actual_de, kq_khung)

        # Cơ chế 4B: Soi trực tiếp (Bạch thủ, Tứ thủ, Lót)
        ghi_lich_su_truc_tiep(target_draw['date'], actual_de, top_1, top_4_nums, dan_lot_list)

    return output_data

def ghi_lich_su_khung(date_str, de_str, kq_status, frame_stt=None):
    """Ghi nhận lịch sử khung 3 ngày (58_up_to_75)"""
    for file_path in ['lich_su_phuong_phap.json', os.path.join('58_up_to_75', 'lich_su_phuong_phap.json')]:
        if not os.path.exists(os.path.dirname(file_path) or '.'):
            continue
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
            if 'khung_3_ngay' not in data:
                data['khung_3_ngay'] = {"tong_quan": {}, "lich_su": []}

            clean_date = date_str.split()[-1].replace('-', '/') if date_str else datetime.now().strftime('%d/%m/%Y')

            existing_idx = None
            for idx, item in enumerate(data['khung_3_ngay'].get("lich_su", [])):
                if item.get("ngay") == clean_date:
                    existing_idx = idx
                    break

            note_map = {
                'trung_n1': 'Trúng N1 ngày 1 ✅ (Dàn 60s)',
                'trung_n2': 'Trúng N2 ngày 2 ✅ (Dàn 42s Mở rộng)',
                'trung_n3': 'Trúng N3 ngày 3 ✅ (Dàn 40s Cơ hội cuối)',
                'truot_khung': 'Trượt khung 3 ngày ❌'
            }

            entry = {
                "khung_stt": frame_stt or len(data['khung_3_ngay'].get("lich_su", [])) + 1,
                "ngay": clean_date,
                "de": str(de_str).zfill(2),
                "ket_qua": kq_status,
                "ghi_chu": note_map.get(kq_status, kq_status)
            }

            if existing_idx is not None:
                data['khung_3_ngay']["lich_su"][existing_idx] = entry
            else:
                data['khung_3_ngay']["lich_su"].insert(0, entry)

            data['khung_3_ngay']["lich_su"] = data['khung_3_ngay']["lich_su"][:50]

            tot = len(data['khung_3_ngay']["lich_su"])
            c_n1 = sum(1 for x in data['khung_3_ngay']["lich_su"] if x.get("ket_qua") == "trung_n1")
            c_n2 = sum(1 for x in data['khung_3_ngay']["lich_su"] if x.get("ket_qua") == "trung_n2")
            c_n3 = sum(1 for x in data['khung_3_ngay']["lich_su"] if x.get("ket_qua") == "trung_n3")
            c_truot = sum(1 for x in data['khung_3_ngay']["lich_su"] if x.get("ket_qua") == "truot_khung")

            data['khung_3_ngay']["tong_quan"] = {
                "tong_khung": tot,
                "trung_n1": c_n1,
                "trung_n2": c_n2,
                "trung_n3": c_n3,
                "truot_khung": c_truot,
                "ty_le_n1": round(c_n1 / tot * 100, 1) if tot > 0 else 0,
                "ty_le_n2": round(c_n2 / tot * 100, 1) if tot > 0 else 0,
                "ty_le_n3": round(c_n3 / tot * 100, 1) if tot > 0 else 0,
                "ty_le_truot": round(c_truot / tot * 100, 1) if tot > 0 else 0
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[*] Đã cập nhật lịch sử khung vào: {file_path}")
        except Exception as e:
            print(f"[!] Lỗi ghi lịch sử khung vào {file_path}: {e}")

def ghi_lich_su_truc_tiep(date_str, de_str, top1_val, top4_list, lot_list):
    """Ghi nhận lịch sử soi trực tiếp (Bạch thủ, Tứ thủ, Lót)"""
    for file_path in ['lich_su_phuong_phap.json', os.path.join('58_up_to_75', 'lich_su_phuong_phap.json')]:
        if not os.path.exists(os.path.dirname(file_path) or '.'):
            continue
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
            if 'soi_truc_tiep' not in data:
                data['soi_truc_tiep'] = {"tong_quan": {}, "lich_su": []}

            clean_date = date_str.split()[-1].replace('-', '/') if date_str else datetime.now().strftime('%d/%m/%Y')
            de_clean = str(de_str).zfill(2)

            existing_idx = None
            for idx, item in enumerate(data['soi_truc_tiep'].get("lich_su", [])):
                if item.get("ngay") == clean_date:
                    existing_idx = idx
                    break

            if top1_val and de_clean == str(top1_val).zfill(2):
                kq_status = 'trung_bach_thu'
                note = f'👑 Trúng Bạch Thủ Top 1 [{de_clean}]'
            elif top4_list and de_clean in [str(x).zfill(2) for x in top4_list]:
                kq_status = 'trung_tu_thu'
                note = f'⭐ Trúng Tứ Thủ Top 4 [{de_clean}]'
            elif lot_list and de_clean in [str(x).zfill(2) for x in lot_list]:
                kq_status = 'trung_lot'
                note = f'🛡️ Trúng Dàn Số Lót [{de_clean}]'
            else:
                kq_status = 'truot_truc_tiep'
                note = 'Trượt kỳ quay ❌'

            entry = {
                "ngay": clean_date,
                "de": de_clean,
                "top1": str(top1_val) if top1_val else "",
                "top4": top4_list if top4_list else [],
                "ket_qua": kq_status,
                "ghi_chu": note
            }

            if existing_idx is not None:
                data['soi_truc_tiep']["lich_su"][existing_idx] = entry
            else:
                data['soi_truc_tiep']["lich_su"].insert(0, entry)

            data['soi_truc_tiep']["lich_su"] = data['soi_truc_tiep']["lich_su"][:50]

            tot = len(data['soi_truc_tiep']["lich_su"])
            c_bt = sum(1 for x in data['soi_truc_tiep']["lich_su"] if x.get("ket_qua") == "trung_bach_thu")
            c_tt = sum(1 for x in data['soi_truc_tiep']["lich_su"] if x.get("ket_qua") in ["trung_bach_thu", "trung_tu_thu"])
            c_lot = sum(1 for x in data['soi_truc_tiep']["lich_su"] if x.get("ket_qua") in ["trung_bach_thu", "trung_tu_thu", "trung_lot"])

            data['soi_truc_tiep']["tong_quan"] = {
                "tong_ngay": tot,
                "trung_bach_thu": c_bt,
                "trung_tu_thu": c_tt,
                "trung_lot": c_lot,
                "ty_le_bach_thu": round(c_bt / tot * 100, 1) if tot > 0 else 0,
                "ty_le_tu_thu": round(c_tt / tot * 100, 1) if tot > 0 else 0,
                "ty_le_lot": round(c_lot / tot * 100, 1) if tot > 0 else 0
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[*] Đã cập nhật lịch sử soi trực tiếp vào: {file_path}")
        except Exception as e:
            print(f"[!] Lỗi ghi lịch sử trực tiếp vào {file_path}: {e}")

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
