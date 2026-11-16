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
from datetime import datetime, timedelta
from collections import Counter
import subprocess
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

API_383_LIVE_URL = "https://api.383.im/lottery/live.json"
DAIPHAT_LIVE_URL = "https://xosodaiphat.com/xsmb-xo-so-mien-bac.html"
DAIPHAT_30N_URL = "https://xosodaiphat.com/xsmb-30-ngay.html"
DEFAULT_CAP4_CSV = "dan_60_cap_4.csv"

# Bảng bóng dương chính xác (0-5, 1-6, 2-7, 3-8, 4-9)
BONG_DUONG = {
    0: 5, 1: 6, 2: 7, 3: 8, 4: 9,
    5: 0, 6: 1, 7: 2, 8: 3, 9: 4
}

# 60 số Cấp 4 mặc định tối ưu (nếu chưa có file CSV)
DEFAULT_60_CAP4 = [
    1, 2, 3, 4, 5, 8, 9, 11, 12, 13, 15, 17, 18, 19, 21,
    22, 23, 24, 26, 28, 29, 31, 32, 33, 34, 35, 37, 38, 39, 42,
    43, 44, 45, 51, 53, 55, 58, 59, 60, 61, 62, 63, 65, 67, 68,
    69, 72, 80, 81, 82, 83, 84, 85, 87, 88, 91, 92, 95, 96, 97, 99
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

def fetch_383_live():
    """Lấy dữ liệu kết quả XSMB trực tiếp siêu tốc (50ms) từ API 383.im."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    dow_map = {0: 'Thứ hai', 1: 'Thứ ba', 2: 'Thứ tư', 3: 'Thứ năm', 4: 'Thứ sáu', 5: 'Thứ bảy', 6: 'Chủ nhật'}
    raw_text = ""
    try:
        if HAS_BS4:
            r = requests.get(API_383_LIVE_URL, headers=headers, timeout=4)
            if r.status_code == 200:
                raw_text = r.text
        else:
            req = urllib.request.Request(API_383_LIVE_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=4) as resp:
                raw_text = resp.read().decode('utf-8', errors='ignore')
    except Exception:
        return None

    if not raw_text:
        return None

    try:
        data = json.loads(raw_text)
        mb = data.get('mb', {})
        if not mb:
            return None
        d_str = mb.get('d', '')
        if d_str:
            parts = d_str.split('-')
            if len(parts) == 3:
                y, mth, d = parts
                dt = datetime(int(y), int(mth), int(d))
                date_str = f"{dow_map[dt.weekday()]} ngày {d}-{mth}-{y}"
            else:
                date_str = d_str
        else:
            now = datetime.now()
            date_str = f"{dow_map[now.weekday()]} ngày {now.strftime('%d-%m-%Y')}"

        pr = mb.get('pr', {})
        db_list = pr.get('db', [])
        db_val = db_list[0].strip() if db_list else ''
        de_val = db_val[-2:] if len(db_val) >= 2 else ''

        g1_list = pr.get('g1', [])
        g1_val = g1_list[0].strip() if g1_list else ''
        g2_list = [str(x).strip() for x in pr.get('g2', [])]
        g3_list = [str(x).strip() for x in pr.get('g3', [])]
        g4_list = [str(x).strip() for x in pr.get('g4', [])]
        g5_list = [str(x).strip() for x in pr.get('g5', [])]
        g6_list = [str(x).strip() for x in pr.get('g6', [])]
        g7_list = [str(x).strip() for x in pr.get('g7', [])]

        prizes = {}
        prizes['GDB'] = db_val
        prizes['G1'] = g1_val
        for idx in range(1, 3):
            prizes[f'G2.{idx}'] = g2_list[idx-1] if len(g2_list) >= idx else ''
        for idx in range(1, 7):
            prizes[f'G3.{idx}'] = g3_list[idx-1] if len(g3_list) >= idx else ''
        for idx in range(1, 5):
            prizes[f'G4.{idx}'] = g4_list[idx-1] if len(g4_list) >= idx else ''
        for idx in range(1, 7):
            prizes[f'G5.{idx}'] = g5_list[idx-1] if len(g5_list) >= idx else ''
        for idx in range(1, 4):
            prizes[f'G6.{idx}'] = g6_list[idx-1] if len(g6_list) >= idx else ''
        for idx in range(1, 5):
            prizes[f'G7.{idx}'] = g7_list[idx-1] if len(g7_list) >= idx else ''

        return {
            'date': date_str,
            'db': db_val,
            'de': de_val,
            'prizes': prizes
        }
    except Exception:
        return None

def fetch_daiphat_draws(use_30days=True):
    """Nguồn dự phòng và lịch sử các kỳ quay từ xosodaiphat.com."""
    dow_map = {0: 'Thứ hai', 1: 'Thứ ba', 2: 'Thứ tư', 3: 'Thứ năm', 4: 'Thứ sáu', 5: 'Thứ bảy', 6: 'Chủ nhật'}
    url = DAIPHAT_30N_URL if use_30days else DAIPHAT_LIVE_URL
    html = ""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'}
        if HAS_BS4:
            r = requests.get(url, headers=headers, timeout=6)
            html = r.text if r.status_code == 200 else ""
        else:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"[!] Không thể kết nối xosodaiphat.com: {e}")
        return []

    if not html:
        return []

    blocks = re.split(r'<table[^>]*table-xsmb[^>]*>', html)
    draws = []
    for i, b in enumerate(blocks[1:]):
        pre_text = blocks[i]
        date_m = re.findall(r'(\d{2})[/-](\d{2})[/-](\d{4})', pre_text)
        if not date_m: continue
        d, mth, y = date_m[-1]
        try:
            dt = datetime(int(y), int(mth), int(d))
            date_str = f"{dow_map[dt.weekday()]} ngày {d}-{mth}-{y}"
        except Exception:
            date_str = f"ngày {d}-{mth}-{y}"

        def get_row_numbers(label, max_len=None):
            pattern = rf'{re.escape(label)}.*?(?:<td[^>]*>)(.*?)(?:<tr>|</table>)'
            m = re.search(pattern, b, re.DOTALL)
            if not m:
                return []
            raw_nums = re.findall(r'>\s*([0-9]{2,5})\s*<', m.group(1))
            if max_len:
                raw_nums = [n for n in raw_nums if len(n) == max_len]
            return raw_nums

        db_nums = get_row_numbers('G.ĐB', 5)
        db_val = db_nums[0] if db_nums else ''
        de_val = db_val[-2:] if len(db_val) >= 2 else ''

        g1_nums = get_row_numbers('G.1', 5)
        g2_nums = get_row_numbers('G.2', 5)
        g3_nums = get_row_numbers('G.3', 5)
        g4_nums = get_row_numbers('G.4', 4)
        g5_nums = get_row_numbers('G.5', 4)
        g6_nums = get_row_numbers('G.6', 3)
        g7_nums = get_row_numbers('G.7', 2)

        prizes = {}
        prizes['GDB'] = db_val
        prizes['G1'] = g1_nums[0] if g1_nums else ''
        for idx in range(1, 3):
            prizes[f'G2.{idx}'] = g2_nums[idx-1] if len(g2_nums) >= idx else ''
        for idx in range(1, 7):
            prizes[f'G3.{idx}'] = g3_nums[idx-1] if len(g3_nums) >= idx else ''
        for idx in range(1, 5):
            prizes[f'G4.{idx}'] = g4_nums[idx-1] if len(g4_nums) >= idx else ''
        for idx in range(1, 7):
            prizes[f'G5.{idx}'] = g5_nums[idx-1] if len(g5_nums) >= idx else ''
        for idx in range(1, 4):
            prizes[f'G6.{idx}'] = g6_nums[idx-1] if len(g6_nums) >= idx else ''
        for idx in range(1, 5):
            prizes[f'G7.{idx}'] = g7_nums[idx-1] if len(g7_nums) >= idx else ''

        draws.append({
            'date': date_str,
            'db': db_val,
            'de': de_val,
            'prizes': prizes
        })
    return draws

def get_combined_draws(is_live=False):
    """
    Hệ thống nguồn kép độc lập:
    - Trực tiếp: Ưu tiên số 1 API 383.im (~50ms)
    - Quá khứ & Dự phòng: xosodaiphat.com
    """
    past_draws = fetch_daiphat_draws(use_30days=True)
    today_dt = datetime.now()
    today_str = today_dt.strftime('%d-%m-%Y')
    dow_map = {0: 'Thứ hai', 1: 'Thứ ba', 2: 'Thứ tư', 3: 'Thứ năm', 4: 'Thứ sáu', 5: 'Thứ bảy', 6: 'Chủ nhật'}
    today_date_str = f"{dow_map[today_dt.weekday()]} ngày {today_str}"

    if is_live:
        # 1. ƯU TIÊN SỐ 1: API 383.im
        live_draw = None
        try:
            live_draw = fetch_383_live()
        except Exception as e:
            print(f"[!] Lỗi kết nối 383.im: {e}")
            live_draw = None

        # 2. DỰ PHÒNG TỨC THÌ: Nếu 383.im không phản hồi hoặc lỗi, chuyển sang xosodaiphat.com
        if not live_draw:
            print("[*] API 383.im không phản hồi -> Chuyển sang nguồn dự phòng xosodaiphat.com...", flush=True)
            daiphat_live = fetch_daiphat_draws(use_30days=False)
            if daiphat_live:
                live_draw = daiphat_live[0]

        # 3. DATE GUARD: Kiểm tra xem kết quả cào về có phải của ngày hôm nay không
        is_today_draw = False
        if live_draw and live_draw.get('date'):
            # Kiểm tra ngày trong chuỗi date
            m_date = re.search(r'(\d{2})[-/](\d{2})[-/](\d{4})', live_draw['date'])
            if m_date:
                draw_date_formatted = f"{m_date.group(1)}-{m_date.group(2)}-{m_date.group(3)}"
                if draw_date_formatted == today_str:
                    is_today_draw = True

        if is_today_draw and live_draw:
            if past_draws and live_draw['date'].split()[-1] == past_draws[0]['date'].split()[-1]:
                past_draws[0] = live_draw
            else:
                past_draws.insert(0, live_draw)
        else:
            # Đài chưa bắt đầu quay kỳ hôm nay (ví dụ lúc 18h14) -> Khởi tạo kỳ hôm nay chờ mở thưởng
            empty_prizes = {
                'G1': '', 'G2.1': '', 'G2.2': '',
                'G3.1': '', 'G3.2': '', 'G3.3': '', 'G3.4': '', 'G3.5': '', 'G3.6': '',
                'G4.1': '', 'G4.2': '', 'G4.3': '', 'G4.4': '',
                'G5.1': '', 'G5.2': '', 'G5.3': '', 'G5.4': '', 'G5.5': '', 'G5.6': '',
                'G6.1': '', 'G6.2': '', 'G6.3': '',
                'G7.1': '', 'G7.2': '', 'G7.3': '', 'G7.4': ''
            }
            live_pending = {
                'date': today_date_str,
                'db': '',
                'de': '',
                'prizes': empty_prizes
            }
            if not past_draws or past_draws[0]['date'].split()[-1] != today_str:
                past_draws.insert(0, live_pending)
    else:
        live_draw = None
        try:
            live_draw = fetch_383_live()
        except Exception:
            live_draw = None
        if not live_draw:
            daiphat_live = fetch_daiphat_draws(use_30days=False)
            if daiphat_live:
                live_draw = daiphat_live[0]

        if live_draw and past_draws:
            if live_draw['date'].split()[-1] == past_draws[0]['date'].split()[-1]:
                past_draws[0] = live_draw
            elif live_draw['date'].split()[-1] != past_draws[0]['date'].split()[-1]:
                past_draws.insert(0, live_draw)
        elif live_draw and not past_draws:
            past_draws = [live_draw]
            
    return past_draws

def get_physical_positions(prizes):
    """
    Trả về danh sách tất cả 107 vị trí vật lý từ Giải ĐB đến hết Giải 7 kèm chữ số:
    Format: {'GDB vị trí 1': '2', 'G1 vị trí 1': '1', ..., 'G7.4 vị trí 2': '8'} (107 vị trí chuẩn trong 27 giải)
    """
    positions = {}
    ordered_keys = (
        ['GDB', 'G1'] +
        [f'G2.{i}' for i in range(1, 3)] +
        [f'G3.{i}' for i in range(1, 7)] +
        [f'G4.{i}' for i in range(1, 5)] +
        [f'G5.{i}' for i in range(1, 7)] +
        [f'G6.{i}' for i in range(1, 4)] +
        [f'G7.{i}' for i in range(1, 5)]
    )
    for g_code in ordered_keys:
        val = prizes.get(g_code, '')
        if not val:
            continue
        for pos_idx, char in enumerate(str(val).strip(), 1):
            if char.isdigit():
                key = f"{g_code} vị trí {pos_idx}"
                positions[key] = char
    return positions

def analyze_bridge_cycles(draws, target_draw_idx=0):
    """
    Phân tích vị trí cầu toàn diện từ Giải ĐB -> Giải 7 (27 giải = 107 vị trí) theo Cách 1:
    1. Kỳ vừa quay xong là cur_draw (draws[target_draw_idx]), đã có Đề (cur_de).
    2. Dò trên 107 vị trí của kỳ trước đó prev_draw (draws[target_draw_idx + 1]) xem vị trí nào
       đã báo trúng Chạm Đầu / Bóng Đầu (Cầu Đầu) và Chạm Đuôi / Bóng Đuôi (Cầu Đuôi) của Đề kỳ vừa quay xong.
    3. Lùi tiếp về các kỳ trước nữa (draws[target_draw_idx + 1 + step] ăn vào Đề của draws[target_draw_idx + step])
       để tính chu kỳ ăn thông liên tiếp (streak 1d, 2d, 3d, 4d+). Loại bỏ hoàn toàn cầu gãy.
    4. Nhìn vào ĐÚNG các tọa độ vị trí đó trên bảng kết quả 27 giải của kỳ vừa quay xong (cur_draw)
       để lấy chữ số mới làm Đầu (Hàng Chục) và Đuôi (Hàng Đơn Vị) chốt cho NGÀY HÔM SAU (N+1)!
    """
    prev_idx = target_draw_idx + 1
    if len(draws) <= prev_idx:
        return None

    cur_draw = draws[target_draw_idx]
    prev_draw = draws[prev_idx]
    
    de_str = cur_draw.get('de', '')
    if not de_str or len(de_str) < 2:
        return None
        
    cur_head_num = int(de_str[0])
    cur_tail_num = int(de_str[1])
    
    cur_head_bong = BONG_DUONG[cur_head_num]
    cur_tail_bong = BONG_DUONG[cur_tail_num]
    
    head_targets = [str(cur_head_num), str(cur_head_bong)]
    tail_targets = [str(cur_tail_num), str(cur_tail_bong)]
    
    cur_pos_map = get_physical_positions(cur_draw['prizes'])
    prev_pos_map = get_physical_positions(prev_draw['prizes'])
    
    # Hàm tính chuỗi ngày ăn thông liên tiếp (Streak):
    # Đã ăn ngày 1 khi vị trí pos ở draws[target_draw_idx + 1] trúng vào Đề của draws[target_draw_idx]
    def calculate_consecutive_bridge_days(pos, is_head=True):
        streak = 1
        for step in range(1, 7):
            res_idx = target_draw_idx + step
            src_idx = target_draw_idx + 1 + step
            if src_idx >= len(draws):
                break
            de = draws[res_idx].get('de', '')
            if not de or len(de) < 2:
                break
            target_digit = int(de[0] if is_head else de[1])
            allowed = [str(target_digit), str(BONG_DUONG[target_digit])]
            src_pos_map = get_physical_positions(draws[src_idx]['prizes'])
            if src_pos_map.get(pos) in allowed:
                streak += 1
            else:
                break # Cầu gãy dừng ngay lập tức
        return streak

    # 1. Quét các vị trí CẦU ĐẦU (vị trí ở kỳ N-1 ăn vào Đầu Đề kỳ N -> lấy số ở kỳ N cho ngày N+1)
    head_positions = []
    for pos, prev_char in prev_pos_map.items():
        if prev_char in head_targets:
            streak = calculate_consecutive_bridge_days(pos, is_head=True)
            cur_digit = cur_pos_map.get(pos)
            if not cur_digit:
                continue
                
            cur_bong = str(BONG_DUONG[int(cur_digit)])
            is_direct = (prev_char == str(cur_head_num))

            if streak >= 4:
                cat = "Chỉ đạo"
                label = "✅ CHỈ ĐẠO (Ưu tiên ngày 4)"
            elif streak == 3:
                cat = "Chỉ đạo"
                label = "✅ CHỈ ĐẠO (Ưu tiên ngày 3)"
            elif streak == 2:
                cat = "Lót"
                label = "Lót ngày 2 (Đôn lên chủ lực N3)"
            else:
                cat = "Theo dõi"
                label = "Theo dõi ngày 1 (Mới chạm)"

            head_positions.append({
                'position': pos,
                'prev_digit': prev_char,
                'digit': cur_digit,
                'digit_bong': cur_bong,
                'role': 'Đầu',
                'cycle_days': streak,
                'category': cat,
                'label': label,
                'is_direct': is_direct
            })

    # 2. Quét các vị trí CẦU ĐUÔI (vị trí ở kỳ N-1 ăn vào Đuôi Đề kỳ N -> lấy số ở kỳ N cho ngày N+1)
    tail_positions = []
    for pos, prev_char in prev_pos_map.items():
        if prev_char in tail_targets:
            streak = calculate_consecutive_bridge_days(pos, is_head=False)
            cur_digit = cur_pos_map.get(pos)
            if not cur_digit:
                continue
                
            cur_bong = str(BONG_DUONG[int(cur_digit)])
            is_direct = (prev_char == str(cur_tail_num))

            if streak >= 4:
                cat = "Chỉ đạo"
                label = "✅ CHỈ ĐẠO (Ưu tiên ngày 4)"
            elif streak == 3:
                cat = "Chỉ đạo"
                label = "✅ CHỈ ĐẠO (Ưu tiên ngày 3)"
            elif streak == 2:
                cat = "Lót"
                label = "Lót ngày 2 (Đôn lên chủ lực N3)"
            else:
                cat = "Theo dõi"
                label = "Theo dõi ngày 1 (Mới chạm)"

            tail_positions.append({
                'position': pos,
                'prev_digit': prev_char,
                'digit': cur_digit,
                'digit_bong': cur_bong,
                'role': 'Đuôi',
                'cycle_days': streak,
                'category': cat,
                'label': label,
                'is_direct': is_direct
            })

    return {
        'cur_date': cur_draw['date'],
        'cur_db': cur_draw['db'],
        'cur_de': cur_draw['de'],
        'prev_date': prev_draw['date'],
        'prev_db': prev_draw['db'],
        'prev_de': prev_draw['de'],
        'head': cur_head_num,
        'head_bong': cur_head_bong,
        'tail': cur_tail_num,
        'tail_bong': cur_tail_bong,
        'head_positions': head_positions,
        'tail_positions': tail_positions,
        'target_pos_map': cur_pos_map
    }

def calc_lot_lon(n):
    """Tính con số lót lộn (đảo chiều) của Bạch thủ; nếu kép bằng thì lót bóng kép."""
    if not n or len(n) < 2:
        return n
    if n[0] != n[1]:
        return f"{n[1]}{n[0]}"
    d = int(n[0])
    b = BONG_DUONG.get(d, (d + 5) % 10)
    return f"{b}{b}"

def calc_cang_3d_static(cur_draw, top_1, top_4, dan_9_so):
    """Tính Top Càng 3D cho ngày hôm sau từ Tâm GĐB + Tâm G1 + Tổng Đề của kỳ vừa quay xong."""
    bong_am = {0: 7, 7: 0, 1: 4, 4: 1, 2: 9, 9: 2, 3: 6, 6: 3, 5: 8, 8: 5}
    scores = {i: 0 for i in range(10)}
    db_val = str(cur_draw.get('db', '')).strip()
    g1_val = str(cur_draw.get('prizes', {}).get('G1', '')).strip()
    de_val = str(cur_draw.get('de', '')).strip()

    tam_g1 = -1
    tam_db = -1
    sum_de = -1

    if g1_val and len(g1_val) >= 5 and g1_val.isdigit():
        tam_g1 = int(g1_val[2])
        scores[tam_g1] += 45
        scores[BONG_DUONG.get(tam_g1, (tam_g1 + 5) % 10)] += 35
        scores[bong_am.get(tam_g1, tam_g1)] += 20

    if db_val and len(db_val) >= 5 and db_val.isdigit():
        tam_db = int(db_val[2])
        scores[tam_db] += 40
        scores[BONG_DUONG.get(tam_db, (tam_db + 5) % 10)] += 30

    if de_val and len(de_val) >= 2 and de_val.isdigit():
        sum_de = (int(de_val[0]) + int(de_val[1])) % 10
        scores[sum_de] += 35
        scores[BONG_DUONG.get(sum_de, (sum_de + 5) % 10)] += 25
        scores[bong_am.get(sum_de, sum_de)] += 15

    sorted_cang = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top3_cang = [str(x[0]) for x in sorted_cang[:3]]
    top5_cang = [str(x[0]) for x in sorted_cang[:5]]

    cang_bt_3s = [f"{c}{top_1}" for c in top3_cang] if top_1 else []
    cang_tt_12s = [f"{c}{num}" for c in top3_cang for num in top_4] if top_4 else []
    cang_d9_27s = [f"{c}{num}" for c in top3_cang for num in dan_9_so] if dan_9_so else []

    return {
        'tam_g1': str(tam_g1) if tam_g1 >= 0 else '',
        'tam_db': str(tam_db) if tam_db >= 0 else '',
        'tong_de': str(sum_de) if sum_de >= 0 else '',
        'top3_cang': top3_cang,
        'top5_cang': top5_cang,
        'cang_bt_3s': cang_bt_3s,
        'cang_tt_12s': cang_tt_12s,
        'cang_d9_27s': cang_d9_27s
    }

def compute_next_date_str(draw_date_str):
    """Tự động tính ngày hôm sau (N+1) và chuyển thứ tiếng Việt từ ngày kỳ vừa quay xong (N)."""
    dow_vn = {
        0: "Thứ hai", 1: "Thứ ba", 2: "Thứ tư", 3: "Thứ năm",
        4: "Thứ sáu", 5: "Thứ bảy", 6: "Chủ nhật"
    }
    date_m = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', str(draw_date_str))
    if date_m:
        d_val, m_val, y_val = map(int, date_m.groups())
        cur_dt = datetime(y_val, m_val, d_val)
        next_dt = cur_dt + timedelta(days=1)
        return f"{dow_vn[next_dt.weekday()]} ngày {next_dt.strftime('%d-%m-%Y')}", next_dt.strftime('%d/%m/%Y')
    return draw_date_str, draw_date_str

def run_pipeline(target_draw_idx=0, cap4_csv=DEFAULT_CAP4_CSV, custom_cap4=None, n2_size=None, n3_size=None, is_live=False, send_tele=False):
    """
    Thực thi toàn bộ pipeline Radar Tĩnh Toàn Diện (Quét đủ 27 giải từ G.ĐB -> G7 = 107 vị trí):
    - Dùng kỳ vừa quay xong (draws[target_draw_idx]) và lịch sử trước đó để dò các vị trí cầu Đầu & Đuôi
      đã ăn thông vào Đề kỳ vừa quay xong.
    - Lấy luôn các chữ số tại đúng vị trí đó trên bảng 27 giải của kỳ vừa quay xong để ghép số
      chốt dự đoán cho NGÀY HÔM SAU (N+1) tương tự như dàn động.
    - Trên bảng Radar: Chỉ tô màu của Cầu Đầu (Vàng) và Cầu Đuôi (Xanh).
    """
    print("\n" + "=" * 82)
    print("   XSMB AI - RADAR TĨNH TOÀN DIỆN (G.ĐB -> G7 | 107 VỊ TRÍ) DỰ ĐOÁN NGÀY HÔM SAU")
    print("=" * 82)
    
    raw_draws = get_combined_draws(is_live=False)
    # Chỉ lấy các kỳ đã quay xong (có đầy đủ giải ĐB / Đề)
    draws = [d for d in raw_draws if d.get('de') and len(str(d.get('de', '')).strip()) >= 2]
    if len(draws) < target_draw_idx + 2:
        print("[!] Dữ liệu cào về không đủ số kỳ để phân tích (từ cả API 383.im và xosodaiphat.com).")
        return None

    cur_draw = draws[target_draw_idx]
    prev_draw_idx = target_draw_idx + 1
    next_date_full, next_date_short = compute_next_date_str(cur_draw['date'])
    
    print(f"[*] Kỳ vừa quay xong (N):   [{cur_draw['date']}] - G.ĐB: {cur_draw['db']} (Đề: {cur_draw['de']})")
    print(f"[*] Kỳ đối chiếu cầu (N-1): [{draws[prev_draw_idx]['date']}] - G.ĐB: {draws[prev_draw_idx]['db']} (Đề: {draws[prev_draw_idx]['de']})")
    print(f"[*] Kỳ dự đoán chốt (N+1):  [{next_date_full}]")
    
    analysis = analyze_bridge_cycles(draws, target_draw_idx=target_draw_idx)
    if not analysis:
        print("[!] Không thể phân tích chu kỳ từ kỳ vừa quay xong.")
        return None

    print("\n" + "-" * 82)
    print(f" BƯỚC 1: ĐỀ VỪA NỔ [{analysis['cur_date']}] & TẬP CHẠM ĐẦU / ĐUÔI DÒ CẦU")
    print("-" * 82)
    print(f"  • Đề vừa nổ kỳ N: {analysis['cur_de']} (Giải ĐB: {analysis['cur_db']})")
    print(f"  • Chạm Đầu = {analysis['head']}  --> Bóng dương = {analysis['head_bong']}  ==> Tập Đầu: [{analysis['head']}, {analysis['head_bong']}]")
    print(f"  • Chạm Đuôi = {analysis['tail']}  --> Bóng dương = {analysis['tail_bong']}  ==> Tập Đuôi: [{analysis['tail']}, {analysis['tail_bong']}]")

    head_positions = analysis['head_positions']
    tail_positions = analysis['tail_positions']

    print("\n" + "-" * 82)
    print(f" BƯỚC 2 & 3: QUÉT 107 VỊ TRÍ (G.ĐB -> G7.4) & LẤY SỐ CHỐT CHO [{next_date_full}]")
    print("-" * 82)
    print(f"  • Tổng vị trí Cầu Đầu (🟡): {len(head_positions)} vị trí")
    print(f"      - Chạy 3-4+ ngày (Chỉ đạo): {sum(1 for x in head_positions if x['cycle_days'] >= 3)} vị trí")
    print(f"      - Chạy 2 ngày (Đôn N3):     {sum(1 for x in head_positions if x['cycle_days'] == 2)} vị trí")
    print(f"      - Mới chạm 1 ngày:          {sum(1 for x in head_positions if x['cycle_days'] == 1)} vị trí")
    print(f"  • Tổng vị trí Cầu Đuôi (🔵): {len(tail_positions)} vị trí")
    print(f"      - Chạy 3-4+ ngày (Chỉ đạo): {sum(1 for x in tail_positions if x['cycle_days'] >= 3)} vị trí")
    print(f"      - Chạy 2 ngày (Đôn N3):     {sum(1 for x in tail_positions if x['cycle_days'] == 2)} vị trí")
    print(f"      - Mới chạm 1 ngày:          {sum(1 for x in tail_positions if x['cycle_days'] == 1)} vị trí")

    # BƯỚC 4: Vào dàn (Ghép các con số từ các vị trí: Chục từ Đầu, Đơn vị từ Đuôi)
    all_pairs = []
    for h in head_positions:
        for t in tail_positions:
            c_main = h['digit']
            d_main = t['digit']
            c_bong = h['digit_bong']
            d_bong = t['digit_bong']

            if h.get('is_direct') and t.get('is_direct') and (h['cycle_days'] >= 2 or t['cycle_days'] >= 2):
                pair_cycle = max(3, h['cycle_days'], t['cycle_days'])
            elif h['cycle_days'] >= 2 or t['cycle_days'] >= 2:
                pair_cycle = max(h['cycle_days'], t['cycle_days'])
            else:
                pair_cycle = 1

            combos = [
                (f"{c_main}{d_main}", 1.0, "chính diện"),
                (f"{c_main}{d_bong}", 0.85, "bóng đuôi"),
                (f"{c_bong}{d_main}", 0.85, "bóng đầu"),
                (f"{c_bong}{d_bong}", 0.7, "bóng cả hai")
            ]

            pos_bonus = 0.0
            if ('GDB' in h['position'] or 'G7' in h['position'] or 'G1' in h['position']):
                pos_bonus += 15.0
            if ('GDB' in t['position'] or 'G7' in t['position'] or 'G1' in t['position']):
                pos_bonus += 15.0

            for num_str, weight, combo_type in combos:
                if pair_cycle >= 4:
                    cat = "Chỉ đạo"
                    cat_label = "✅ CHỈ ĐẠO (4 ngày)"
                elif pair_cycle == 3:
                    cat = "Chỉ đạo"
                    cat_label = "✅ CHỈ ĐẠO (3 ngày)"
                elif pair_cycle == 2:
                    cat = "Lót"
                    cat_label = "Lót ngày 2 (Đôn chủ lực N3)"
                else:
                    cat = "Theo dõi"
                    cat_label = "Theo dõi ngày 1 (Mới chạm)"

                direct_bonus = 40.0 if (h.get('is_direct') and t.get('is_direct')) else (15.0 if (h.get('is_direct') or t.get('is_direct')) else 0)
                score = pair_cycle * 30 + weight * 20 + direct_bonus + pos_bonus + (h['cycle_days'] + t['cycle_days']) * 5

                all_pairs.append({
                    'num': num_str,
                    'c_digit': c_main,
                    'd_digit': d_main,
                    'c_cycle': h['cycle_days'],
                    'd_cycle': t['cycle_days'],
                    'cycle_days': pair_cycle,
                    'category': cat,
                    'cat_label': cat_label,
                    'weight': weight,
                    'combo_type': combo_type,
                    'score': score,
                    'h_pos': h['position'],
                    't_pos': t['position']
                })

    # Nhóm theo con số (loại trùng, giữ chu kỳ và điểm cao nhất + cộng thưởng độ hội tụ nhiều cầu báo)
    freq_pairs = Counter(p['num'] for p in all_pairs)
    unique_numbers_map = {}
    for p in all_pairs:
        n = p['num']
        total_sc = p['score'] + min(freq_pairs[n] * 2.5, 35.0)
        p_copy = dict(p)
        p_copy['score'] = round(total_sc, 1)
        if n not in unique_numbers_map or total_sc > unique_numbers_map[n].get('score', 0):
            unique_numbers_map[n] = p_copy

    found_numbers = list(unique_numbers_map.values())

    # BƯỚC 5: So với dàn 60 số Cấp 4
    if custom_cap4:
        cap4_numbers = set(custom_cap4)
    else:
        cap4_numbers = set(load_cap4_numbers(cap4_csv))

    for item in found_numbers:
        item['in_cap4'] = (item['num'] in cap4_numbers)
        item['in_cap4_str'] = "Có" if item['in_cap4'] else "Không"

    # Chấm điểm AI Score hỗ trợ lọc hội tụ
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

    # Cộng điểm AI hội tụ vào score để chọn Top 1, Top 4 chuẩn xác nhất
    for item in found_numbers:
        n = item['num']
        item['ai_score'] = ai_scores.get(n, 5.0)
        item['final_score'] = round(item['score'] + item['ai_score'] * 8.0 + (20.0 if item['in_cap4'] else 0.0), 1)

    chidao_pool = [x for x in found_numbers if x['cycle_days'] >= 3]
    if len(chidao_pool) < 4:
        chidao_pool = [x for x in found_numbers if x['cycle_days'] >= 2]
    selection_pool = chidao_pool if len(chidao_pool) >= 4 else found_numbers
    selection_pool.sort(key=lambda x: (x['cycle_days'], x.get('final_score', 0)), reverse=True)

    top_1 = selection_pool[0]['num'] if len(selection_pool) >= 1 else '65'
    lot_lon = calc_lot_lon(top_1)
    song_thu = [top_1, lot_lon] if lot_lon != top_1 else [top_1]

    top_4_nums = []
    for x in selection_pool:
        if x['num'] not in top_4_nums:
            top_4_nums.append(x['num'])
        if len(top_4_nums) >= 4:
            break

    # DÀN SỐ LÓT & DÀN TINH TÚY GIAO THOA 60 SỐ CẤP 4
    dan_lot_valid = []
    dan_lot_discarded = []

    for item in found_numbers:
        n = item['num']
        if n == top_1:
            item['top_rank'] = "👑 Top 1 (Bạch thủ)"
        elif n in top_4_nums:
            item['top_rank'] = "🔥 Top 4 (Tứ thủ)"
        elif item['in_cap4']:
            item['top_rank'] = "🛡️ Lót hợp lệ"
            dan_lot_valid.append(n)
        else:
            item['top_rank'] = "❌ Loại bỏ (Ngoài 60s)"
            dan_lot_discarded.append(n)

    def sort_key(x):
        tier = 0
        if "Top 1" in x['top_rank']: tier = 4
        elif "Top 4" in x['top_rank']: tier = 3
        elif "Lót hợp lệ" in x['top_rank']: tier = 2
        else: tier = 1
        return (tier, x['cycle_days'], x.get('final_score', 0))

    found_numbers.sort(key=sort_key, reverse=True)

    # Dàn Ngày 1 Tinh Túy: Các số giao thoa 60 số Cấp 4 (sắp xếp theo điểm hội tụ giảm dần, lấy tối ưu ~34-40 số mạnh nhất hoặc toàn bộ giao thoa)
    tinhtuy_candidates = [x for x in found_numbers if x['in_cap4']]
    tinhtuy_candidates.sort(key=lambda x: x.get('final_score', 0), reverse=True)
    # Giữ quy mô tinh túy tối ưu (tối đa 38 số mạnh nhất trong giao thoa 60s, luôn bao gồm các số trong Top 4 thuộc 60s)
    dan_ngay1_tinhtuy = sorted([x['num'] for x in tinhtuy_candidates[:38]])

    dan_n1_list = [f"{x:02d}" for x in sorted(DEFAULT_60_CAP4)]
    dan_lot_list = [x for x in dan_n1_list if x != top_1 and x not in top_4_nums]
    dan_lot_display = [f"{x} (lót)" for x in dan_lot_list]

    print("\n" + "=" * 82)
    print(f" KẾT QUẢ CHỐT SỚM DỰ ĐOÁN CHO KỲ TIẾP THEO [{next_date_full}]")
    print("=" * 82)
    if top_1:
        t1_info = unique_numbers_map.get(top_1, {})
        print(f"  👑 TOP 01 BẠCH THỦ: [{top_1}] | 🛡️ LÓT LỘN: [{lot_lon}] ==> CẶP SONG THỦ: [{top_1} - {lot_lon}]")
        print(f"     -> Cầu báo: {t1_info.get('h_pos', '')} (Đầu) x {t1_info.get('t_pos', '')} (Đuôi) - Chu kỳ {t1_info.get('cycle_days', 3)} ngày")
    print(f"  🔥 TOP 04 TỨ THỦ TINH TÚY: {top_4_nums}")
    print(f"  ⭐ DÀN TINH TÚY GIAO THOA 60 SỐ CẤP 4 ({len(dan_ngay1_tinhtuy)} số): {dan_ngay1_tinhtuy}")
    print(f"  🔵 DÀN SỐ LÓT N1 ({len(dan_lot_list)} số): {dan_lot_list[:15]} ...")

    # Kiểm chứng thực tế nếu đang backtest kỳ quá khứ (target_draw_idx >= 1, khi đó kỳ dự đoán là draws[target_draw_idx - 1])
    predicted_actual_de = draws[target_draw_idx - 1]['de'] if target_draw_idx >= 1 else None
    cur_actual_de = cur_draw['de']

    # Trích xuất đầy đủ bảng kết quả 27 giải (từ Giải ĐB đến hết Giải 7) của kỳ vừa quay xong
    live_prizes = {
        'gdb': cur_draw['prizes'].get('GDB', cur_draw.get('db', '')),
        'g1': cur_draw['prizes'].get('G1', ''),
        'g2': [cur_draw['prizes'].get('G2.1', ''), cur_draw['prizes'].get('G2.2', '')],
        'g3': [cur_draw['prizes'].get(f'G3.{i}', '') for i in range(1, 7)],
        'g4': [cur_draw['prizes'].get(f'G4.{i}', '') for i in range(1, 5)],
        'g5': [cur_draw['prizes'].get(f'G5.{i}', '') for i in range(1, 7)],
        'g6': [cur_draw['prizes'].get(f'G6.{i}', '') for i in range(1, 4)],
        'g7': [cur_draw['prizes'].get(f'G7.{i}', '') for i in range(1, 5)]
    }
    
    total_all_prizes = 27
    filled_all_prizes = (
        (1 if live_prizes['gdb'] else 0) +
        (1 if live_prizes['g1'] else 0) +
        sum(1 for x in live_prizes['g2'] if x) +
        sum(1 for x in live_prizes['g3'] if x) +
        sum(1 for x in live_prizes['g4'] if x) +
        sum(1 for x in live_prizes['g5'] if x) +
        sum(1 for x in live_prizes['g6'] if x) +
        sum(1 for x in live_prizes['g7'] if x)
    )
    is_draw_finished = (filled_all_prizes == total_all_prizes)

    # ÁP DỤNG CHU KỲ 7 NGÀY & TỐI ƯU HÓA MỞ RỘNG N2 (42 SỐ), N3 (40 SỐ)
    weekly_cycle = get_weekly_cycle_mode(next_date_full)
    n2_target_count = n2_size if n2_size is not None else weekly_cycle['n2_count']
    n3_target_count = n3_size if n3_size is not None else weekly_cycle['n3_count']

    bet_2_days = {prev_de_val} if (prev_de_val and prev_de_val == prev_prev_de_val) else set()
    base_n2_pool = [
        11, 12, 13, 15, 17, 18, 19, 21, 22, 23, 28, 29, 31, 32, 33, 35, 37, 38,
        42, 44, 45, 51, 52, 53, 55, 58, 59, 61, 62, 63, 65, 66, 67, 68, 81, 82,
        83, 85, 87, 90, 95, 98
    ]
    n2_candidates_set = set(f"{x:02d}" for x in base_n2_pool)
    for n in dan_n1_list:
        n2_candidates_set.add(n)
        
    n2_candidates_filtered = []
    for n in n2_candidates_set:
        if n in bet_2_days:
            continue
        if unique_numbers_map and n in unique_numbers_map:
            cycle = unique_numbers_map[n].get('cycle_days', 0)
            if cycle < 2 and ai_scores.get(n, 5.0) < 7.0:
                continue
        n2_candidates_filtered.append(n)
        
    n2_candidates_filtered.sort(key=lambda x: (ai_scores.get(x, 5.0), 1 if x in dan_n1_list else 0), reverse=True)
    dan_n2_list = sorted(n2_candidates_filtered[:n2_target_count])

    n3_candidates = [n for n in dan_n2_list if gan_dict.get(n, 0) <= 45]
    for n in dan_n2_list:
        if len(n3_candidates) >= n3_target_count:
            break
        if n not in n3_candidates:
            n3_candidates.append(n)
    n3_candidates.sort(key=lambda x: ai_scores.get(x, 5.0), reverse=True)
    dan_n3_list = sorted(n3_candidates[:n3_target_count])

    is_n1_hit = (cur_actual_de in dan_n1_list) if cur_actual_de else False
    is_n2_hit = (cur_actual_de in dan_n2_list) if cur_actual_de else False
    is_n3_hit = (cur_actual_de in dan_n3_list) if cur_actual_de else False

    status_badge = "ĐÃ TRÚNG N1 → RESET CẦU MỚI" if is_n1_hit else ("ĐÃ TRÚNG N2 → CỨU N1 THÀNH CÔNG" if is_n2_hit else ("ĐÃ TRÚNG N3 → CỨU KHUNG THÀNH CÔNG" if is_n3_hit else "ĐANG THEO DÕI KHUNG"))

    frame_transition = {
        'last_result': f"Kỳ vừa quay ({cur_draw['date']} - Đề {cur_actual_de}) đã {status_badge}",
        'status_badge': status_badge,
        'schedule_n1': f"Đánh chính N1: {next_date_full} ({len(dan_n1_list)} Số N1)",
        'schedule_n2': f"Dự phòng N2: Ngày thứ 2 ({len(dan_n2_list)} số - Mở rộng cứu N1)",
        'schedule_n3': f"Dự phòng N3: Ngày thứ 3 ({len(dan_n3_list)} số - Cơ hội cuối)",
        'weekly_cycle': weekly_cycle
    }

    # BẢNG MA TRẬN TÔ MÀU VỊ TRÍ CẦU TRÊN RADAR (CHỈ TÔ MÀU ĐẦU VÀ ĐUÔI THEO YÊU CẦU):
    # - 🟡 VÀNG (role_head): Vị trí Cầu Đầu (Hàng Chục)
    # - 🔵 XANH (role_tail): Vị trí Cầu Đuôi (Hàng Đơn Vị)
    # - 🟡🔵 VÀNG-XANH (role_both): Vị trí vừa là Cầu Đầu vừa là Cầu Đuôi
    head_pos_dict = {}
    for it in head_positions:
        norm_key = re.sub(r'\s+vị\s+trí\s+', '_', it['position'])
        if norm_key not in head_pos_dict or it['cycle_days'] > head_pos_dict[norm_key]['cycle_days']:
            head_pos_dict[norm_key] = it

    tail_pos_dict = {}
    for it in tail_positions:
        norm_key = re.sub(r'\s+vị\s+trí\s+', '_', it['position'])
        if norm_key not in tail_pos_dict or it['cycle_days'] > tail_pos_dict[norm_key]['cycle_days']:
            tail_pos_dict[norm_key] = it

    highlight_positions = {}
    all_norm_keys = set(head_pos_dict.keys()) | set(tail_pos_dict.keys())
    for norm_key in all_norm_keys:
        in_h = norm_key in head_pos_dict
        in_t = norm_key in tail_pos_dict
        if in_h and in_t:
            h_it = head_pos_dict[norm_key]
            t_it = tail_pos_dict[norm_key]
            cycle = max(h_it['cycle_days'], t_it['cycle_days'])
            highlight_positions[norm_key] = {
                'pos_raw': h_it['position'],
                'role': 'both',
                'role_name': 'Đầu + Đuôi',
                'tag_label': 'Đ+Đ',
                'digit': h_it['digit'],
                'cycle': cycle,
                'cycle_suffix': 'Đ+Đ',
                'category': h_it['category'],
                'label': f"Cầu Đầu & Đuôi ({cycle}d)",
                'color_type': 'role_both',
                'tooltip': f"{h_it['position']}: Chữ số {h_it['digit']} | Vừa báo Cầu Đầu ({h_it['cycle_days']}d) vừa báo Cầu Đuôi ({t_it['cycle_days']}d)"
            }
        elif in_h:
            h_it = head_pos_dict[norm_key]
            cycle = h_it['cycle_days']
            highlight_positions[norm_key] = {
                'pos_raw': h_it['position'],
                'role': 'head',
                'role_name': 'Đầu',
                'tag_label': 'Đầu',
                'digit': h_it['digit'],
                'cycle': cycle,
                'cycle_suffix': 'Đầu',
                'category': h_it['category'],
                'label': f"Cầu Đầu ({cycle}d)",
                'color_type': 'role_head',
                'tooltip': f"{h_it['position']}: Cầu Đầu {h_it['digit']} (Bóng {h_it['digit_bong']}) | Chu kỳ ăn {cycle} ngày"
            }
        else:
            t_it = tail_pos_dict[norm_key]
            cycle = t_it['cycle_days']
            highlight_positions[norm_key] = {
                'pos_raw': t_it['position'],
                'role': 'tail',
                'role_name': 'Đuôi',
                'tag_label': 'Đuôi',
                'digit': t_it['digit'],
                'cycle': cycle,
                'cycle_suffix': 'Đuôi',
                'category': t_it['category'],
                'label': f"Cầu Đuôi ({cycle}d)",
                'color_type': 'role_tail',
                'tooltip': f"{t_it['position']}: Cầu Đuôi {t_it['digit']} (Bóng {t_it['digit_bong']}) | Chu kỳ ăn {cycle} ngày"
            }

    top_1_cycle = unique_numbers_map[top_1]['cycle_days'] if top_1 and top_1 in unique_numbers_map else 3
    top_1_display = f"{top_1} ({top_1_cycle}d)" if top_1 else ""

    top_4_display = []
    for num in top_4_nums:
        c = unique_numbers_map[num]['cycle_days'] if num in unique_numbers_map else 3
        top_4_display.append(f"★ {num} ({c}d)")

    # Đọc kết quả phân tích thống kê từ analysis_summary.json nếu có
    summary_data = None
    for s_path in ['analysis_summary.json', os.path.join(os.path.dirname(__file__), 'analysis_summary.json')]:
        if os.path.exists(s_path):
            try:
                with open(s_path, 'r', encoding='utf-8') as sf:
                    summary_data = json.load(sf)
                    break
            except Exception:
                pass

    # Top 3 Đầu & Top 3 Đuôi từ tần suất cầu Đầu/Đuôi mạnh nhất
    head_digit_Counter = Counter()
    for h_it in head_positions:
        head_digit_Counter[h_it['digit']] += h_it['cycle_days'] * 2
    tail_digit_Counter = Counter()
    for t_it in tail_positions:
        tail_digit_Counter[t_it['digit']] += t_it['cycle_days'] * 2

    top_dau_digits = [d for d, _ in head_digit_Counter.most_common(3)]
    if len(top_dau_digits) < 3:
        for d in [str(analysis['head']), str(analysis['head_bong']), str((analysis['head'] + 2) % 10)]:
            if d not in top_dau_digits:
                top_dau_digits.append(d)
            if len(top_dau_digits) >= 3:
                break
    top_duoi_digits = [d for d, _ in tail_digit_Counter.most_common(3)]
    if len(top_duoi_digits) < 3:
        for d in [str(analysis['tail']), str(analysis['tail_bong']), str((analysis['tail'] + 2) % 10)]:
            if d not in top_duoi_digits:
                top_duoi_digits.append(d)
            if len(top_duoi_digits) >= 3:
                break

    top_dau_list = [f"Đầu {d}" for d in top_dau_digits[:3]]
    top_duoi_list = [f"Đuôi {d}" for d in top_duoi_digits[:3]]

    # Ghép Dàn 9 số Cội Nguồn (Top 3 Đầu x Top 3 Đuôi từ Radar)
    dan_9_so_calc = []
    for hd in top_dau_digits[:3]:
        for td in top_duoi_digits[:3]:
            num_str = f"{hd}{td}"
            if num_str not in dan_9_so_calc:
                dan_9_so_calc.append(num_str)

    # Tính Càng 3D dự đoán cho ngày hôm sau
    cang_3d_info = calc_cang_3d_static(cur_draw, top_1, top_4_nums, dan_9_so_calc)

    tinh_status_text = f"ĐANG HIỆU LỰC CHO KỲ TỚI (CHỐT SỚM TỪ KẾT QUẢ KỲ {cur_draw['date'].split()[-1]})"

    dan_cap2_38so = dan_ngay1_tinhtuy if len(dan_ngay1_tinhtuy) >= 20 else [
        '01', '02', '04', '07', '09', '11', '12', '14', '16', '17', 
        '20', '22', '23', '25', '27', '31', '32', '37', '40', '41', 
        '42', '45', '47', '49', '61', '62', '67', '68', '70', '72', 
        '75', '77', '81', '82', '84', '86', '87', '89'
    ]

    dan_tinh_4cap = {
        'target_date': next_date_full,
        'status_text': tinh_status_text,
        'bach_thu': top_1,
        'lot_lon': lot_lon,
        'song_thu': song_thu,
        'tu_thu': top_4_nums,
        'cang_3d': cang_3d_info['top5_cang'],
        'cang_3d_info': cang_3d_info,
        'dan_9_so': dan_9_so_calc,
        'top_dau': top_dau_list,
        'top_duoi': top_duoi_list,
        'dan_cap2_38so': dan_cap2_38so,
        'dan_60_cap4': [f"{x:02d}" for x in DEFAULT_60_CAP4]
    }

    output_data = {
        'radar_mode': 'STATIC_27_PRIZES_NEXT_DAY',
        'target_date': cur_draw['date'],
        'next_date': next_date_full,
        'next_date_short': next_date_short,
        'prev_date': draws[prev_draw_idx]['date'],
        'cur_db': cur_draw['db'],
        'cur_de': cur_draw['de'],
        'prev_de': draws[prev_draw_idx]['de'],
        'head_targets': [analysis['head'], analysis['head_bong']],
        'tail_targets': [analysis['tail'], analysis['tail_bong']],
        'head_count': len(head_positions),
        'tail_count': len(tail_positions),
        'live_prizes': live_prizes,
        'highlight_positions': highlight_positions,
        'filled_count': filled_all_prizes,
        'total_count': total_all_prizes,
        'is_g5_finished': True,
        'is_draw_finished': is_draw_finished,
        'dan_ghep': sorted(list(unique_numbers_map.keys())),
        'dan_ngay_1_tinhtuy': dan_ngay1_tinhtuy,
        'dan_giao_thoa': dan_ngay1_tinhtuy,
        'dan_tinh_tuy': dan_ngay1_tinhtuy,
        'top_1': top_1,
        'top1': top_1,
        'lot_lon': lot_lon,
        'song_thu': song_thu,
        'top_1_display': top_1_display,
        'top_4': top_4_nums,
        'top4': top_4_nums,
        'top_4_display': top_4_display,
        'cang_3d_info': cang_3d_info,
        'dan_9': dan_9_so_calc,
        'dan_lot': dan_lot_list,
        'dan_lot_display': dan_lot_display,
        'dan_n1': dan_n1_list,
        'dan_n2': dan_n2_list,
        'dan_n3': dan_n3_list,
        'weekly_cycle': weekly_cycle,
        'ai_scores': ai_scores,
        'frame_transition': frame_transition,
        'table_5cols': found_numbers,
        'actual_de': cur_actual_de,
        'predicted_actual_de': predicted_actual_de,
        'dan_dao': [lot_lon] if lot_lon else [],
        'dan_tinh_4cap': dan_tinh_4cap
    }
    
    if target_draw_idx == 0:
        with open('ket_qua_soi_cau_g1_g5.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n[*] Đã lưu toàn bộ kết quả Radar G.ĐB->G7 vào: ket_qua_soi_cau_g1_g5.json")

        # Đồng bộ sang thư mục 58_up_to_75 nếu tồn tại
        branch_dir = '58_up_to_75'
        if os.path.exists(branch_dir):
            branch_json_path = os.path.join(branch_dir, 'ket_qua_soi_cau_g1_g5.json')
            with open(branch_json_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"[*] Đã đồng bộ sang: {branch_json_path}")

        # Khi chạy ở kỳ mới nhất (target_draw_idx == 0), kiểm chứng lại dự đoán của kỳ trước (draws[1]) cho kỳ hôm nay (draws[0])
        if len(draws) >= 3:
            prev_pred = analyze_and_verify_single_draw(draws, pred_for_idx=0)
            if prev_pred:
                ghi_lich_su_khung(cur_draw['date'], cur_actual_de, prev_pred['kq_khung'])
                ghi_lich_su_truc_tiep(cur_draw['date'], cur_actual_de, prev_pred['top_1'], prev_pred['top_4'], prev_pred['dan_lot'])
                ghi_lich_su_tinh_tuy(cur_draw['date'], cur_actual_de, prev_pred['dan_tinhtuy'])

        if send_tele:
            send_telegram_notification(output_data)

    return output_data

def analyze_and_verify_single_draw(draws, pred_for_idx=0):
    """
    Hàm tính bộ số dự đoán đã được chốt từ kỳ (pred_for_idx + 1) để đánh cho kỳ (pred_for_idx),
    nhằm đối chiếu trung thực 100% với Đề thực tế về ở kỳ (pred_for_idx).
    """
    base_idx = pred_for_idx + 1
    if len(draws) <= base_idx + 1:
        return None
    analysis = analyze_bridge_cycles(draws, target_draw_idx=base_idx)
    if not analysis:
        return None

    head_positions = analysis['head_positions']
    tail_positions = analysis['tail_positions']
    all_pairs = []
    for h in head_positions:
        for t in tail_positions:
            c_main, d_main = h['digit'], t['digit']
            c_bong, d_bong = h['digit_bong'], t['digit_bong']
            if h.get('is_direct') and t.get('is_direct') and (h['cycle_days'] >= 2 or t['cycle_days'] >= 2):
                pair_cycle = max(3, h['cycle_days'], t['cycle_days'])
            elif h['cycle_days'] >= 2 or t['cycle_days'] >= 2:
                pair_cycle = max(h['cycle_days'], t['cycle_days'])
            else:
                pair_cycle = 1
            combos = [
                (f"{c_main}{d_main}", 1.0),
                (f"{c_main}{d_bong}", 0.85),
                (f"{c_bong}{d_main}", 0.85),
                (f"{c_bong}{d_bong}", 0.7)
            ]
            pos_bonus = 15.0 if ('GDB' in h['position'] or 'G7' in h['position'] or 'G1' in h['position']) else 0.0
            pos_bonus += 15.0 if ('GDB' in t['position'] or 'G7' in t['position'] or 'G1' in t['position']) else 0.0
            direct_bonus = 40.0 if (h.get('is_direct') and t.get('is_direct')) else (15.0 if (h.get('is_direct') or t.get('is_direct')) else 0)
            for num_str, weight in combos:
                score = pair_cycle * 30 + weight * 20 + direct_bonus + pos_bonus + (h['cycle_days'] + t['cycle_days']) * 5
                all_pairs.append({'num': num_str, 'cycle_days': pair_cycle, 'score': score})

    freq_pairs = Counter(p['num'] for p in all_pairs)
    unique_map = {}
    for p in all_pairs:
        n = p['num']
        sc = p['score'] + min(freq_pairs[n] * 2.5, 35.0)
        if n not in unique_map or sc > unique_map[n]['score']:
            unique_map[n] = {'num': n, 'cycle_days': p['cycle_days'], 'score': sc}

    cap4_set = set(f"{x:02d}" for x in DEFAULT_60_CAP4)
    ai_scores, _, _, _ = compute_ai_scores(draws, base_idx, unique_map)
    found = list(unique_map.values())
    for item in found:
        n = item['num']
        item['in_cap4'] = (n in cap4_set)
        item['final_score'] = round(item['score'] + ai_scores.get(n, 5.0) * 8.0 + (20.0 if item['in_cap4'] else 0.0), 1)

    pool = [x for x in found if x['cycle_days'] >= 3]
    if len(pool) < 4:
        pool = [x for x in found if x['cycle_days'] >= 2]
    if len(pool) < 4:
        pool = found
    pool.sort(key=lambda x: (x['cycle_days'], x['final_score']), reverse=True)

    top_1 = pool[0]['num'] if pool else '65'
    top_4 = [x['num'] for x in pool[:4]]
    tinhtuy_cands = [x for x in found if x['in_cap4']]
    tinhtuy_cands.sort(key=lambda x: x['final_score'], reverse=True)
    dan_tinhtuy = sorted([x['num'] for x in tinhtuy_cands[:38]])
    dan_n1 = [f"{x:02d}" for x in sorted(DEFAULT_60_CAP4)]
    dan_lot = [x for x in dan_n1 if x != top_1 and x not in top_4]

    actual_de = draws[pred_for_idx].get('de', '')
    kq_khung = 'trung_n1' if actual_de in dan_n1 else 'truot_khung'
    return {
        'top_1': top_1,
        'top_4': top_4,
        'dan_tinhtuy': dan_tinhtuy,
        'dan_lot': dan_lot,
        'kq_khung': kq_khung
    }

def send_telegram_notification(output_data):
    """
    Gửi thông báo kết quả kỳ vừa quay & Bảng chốt Radar (G.ĐB -> G7) dự đoán cho ngày hôm sau
    về Telegram cá nhân của Nguyễn Trung Đông (NV02) qua Bot Bảng Lương PX GCCK.
    """
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'telegram_config.json')
    if not os.path.exists(cfg_path):
        print("[!] Không tìm thấy file cấu hình telegram_config.json")
        return False
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"[!] Lỗi đọc telegram_config.json: {e}")
        return False

    if not cfg.get('enabled', True):
        print("[*] Thông báo Telegram đang tắt trong cấu hình.")
        return False

    bot_token = cfg.get('bot_token', '').strip()
    chat_id = str(cfg.get('chat_id', '')).strip()
    recipient = cfg.get('recipient_name', 'Nguyễn Trung Đông (NV02)')
    bot_name = cfg.get('bot_name', 'Bảng Lương PX GCCK')

    if not bot_token or not chat_id:
        print("[!] Thiếu bot_token hoặc chat_id trong telegram_config.json")
        return False

    cur_date = output_data.get('target_date', '')
    next_date = output_data.get('next_date', '')
    cur_db = output_data.get('cur_db', '')
    cur_de = output_data.get('cur_de', '')
    top_1 = output_data.get('top_1', '')
    lot_lon = output_data.get('lot_lon', '')
    song_thu_str = " - ".join(output_data.get('song_thu', [top_1, lot_lon]))
    top_4_str = ", ".join(output_data.get('top_4', []))
    cang_info = output_data.get('cang_3d_info', {})
    top3_cang_str = ", ".join(cang_info.get('top3_cang', []))
    cang_bt_str = ", ".join(cang_info.get('cang_bt_3s', []))
    dan_9_str = ", ".join(output_data.get('dan_9', []))
    dan_tinhtuy = output_data.get('dan_ngay_1_tinhtuy', [])
    dan_tinhtuy_str = ", ".join(dan_tinhtuy)
    h_cnt = output_data.get('head_count', 0)
    t_cnt = output_data.get('tail_count', 0)

    msg_lines = [
        f"📡 <b>BẢNG LƯƠNG PX GCCK - RADAR XSMB (G.ĐB → G7)</b>",
        f"👤 Người nhận: <b>{recipient}</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"✅ <b>KỲ VỪA QUAY XONG: {cur_date}</b>",
        f"• Giải ĐB: <code>{cur_db}</code>  |  Đề nổ: <b>{cur_de}</b>",
        f"• Tọa độ cầu phát hiện (107 vị trí): 🟡 <b>{h_cnt} Cầu Đầu</b> × 🔵 <b>{t_cnt} Cầu Đuôi</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"🎯 <b>DỰ ĐOÁN CHỐT SỚM CHO: {next_date}</b>",
        f"👑 <b>BẠCH THỦ TOP 1:</b> <code>{top_1}</code>",
        f"🛡️ <b>SONG THỦ (KÈM LÓT LỘN):</b> <code>{song_thu_str}</code>",
        f"🔥 <b>TỨ THỦ TOP 4:</b> <code>{top_4_str}</code>",
        f"🔮 <b>CÀNG 3D CHỦ LỰC:</b> <code>{top3_cang_str}</code> (Ghép BT: <code>{cang_bt_str}</code>)",
        f"🎲 <b>DÀN 9 SỐ CỘI NGUỒN:</b>",
        f"<code>{dan_9_str}</code>",
        f"💎 <b>DÀN TINH TÚY NGÀY 1 ({len(dan_tinhtuy)} số):</b>",
        f"<code>{dan_tinhtuy_str}</code>",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"🌐 <a href='https://happiness2286-dot.github.io/logistic/soi_cau_g1_g5_app.html'>Mở App Xem Bảng Tô Màu Đầu/Đuôi (G.ĐB → G7)</a>"
    ]
    text_payload = "\n".join(msg_lines)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text_payload,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        if HAS_BS4:
            resp = requests.post(url, json=payload, timeout=10)
            ok = (resp.status_code == 200 and resp.json().get('ok'))
        else:
            data_bytes = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_obj = json.loads(resp.read().decode('utf-8', errors='ignore'))
                ok = res_obj.get('ok', False)
        if ok:
            print(f"[✓ Telegram] Đã bắn thành công bản tin chốt số cho {recipient} qua {bot_name}!")
            return True
        else:
            print(f"[!] Telegram trả về lỗi khi gửi cho {recipient}.")
            return False
    except Exception as e:
        print(f"[!] Lỗi kết nối gửi Telegram: {e}")
        return False

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

def ghi_lich_su_tinh_tuy(date_str, de_str, dan_tinhtuy_list):
    """Ghi nhận lịch sử Dàn Tinh Túy Ngày 1 (Theo dõi khoảng 60 ngày)"""
    for file_path in ['lich_su_phuong_phap.json', os.path.join('58_up_to_75', 'lich_su_phuong_phap.json')]:
        if not os.path.exists(os.path.dirname(file_path) or '.'):
            continue
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {}
            if 'dan_tinh_tuy_ngay_1' not in data:
                data['dan_tinh_tuy_ngay_1'] = {"tong_quan": {}, "lich_su": []}

            clean_date = date_str.split()[-1].replace('-', '/') if date_str else datetime.now().strftime('%d/%m/%Y')
            de_clean = str(de_str).zfill(2)
            is_hit = (de_clean in dan_tinhtuy_list) if dan_tinhtuy_list else False
            count_nums = len(dan_tinhtuy_list) if dan_tinhtuy_list else 0

            existing_idx = None
            for idx, item in enumerate(data['dan_tinh_tuy_ngay_1'].get("lich_su", [])):
                if item.get("ngay") == clean_date:
                    existing_idx = idx
                    break

            entry = {
                "stt": 1,
                "ngay": clean_date,
                "de": de_clean,
                "so_luong": count_nums,
                "ket_qua": "trung" if is_hit else "truot",
                "ghi_chu": f"Trúng Đề {de_clean} ✅ (Dàn {count_nums} số)" if is_hit else f"Trượt Đề {de_clean} ❌ ({count_nums} số)"
            }

            if existing_idx is not None:
                data['dan_tinh_tuy_ngay_1']["lich_su"][existing_idx] = entry
            else:
                data['dan_tinh_tuy_ngay_1']["lich_su"].insert(0, entry)

            # Cập nhật số thứ tự STT chuẩn
            tot = len(data['dan_tinh_tuy_ngay_1']["lich_su"])
            for i, itm in enumerate(data['dan_tinh_tuy_ngay_1']["lich_su"]):
                itm["stt"] = tot - i

            # Giới hạn giữ 60 kỳ gần nhất
            data['dan_tinh_tuy_ngay_1']["lich_su"] = data['dan_tinh_tuy_ngay_1']["lich_su"][:60]
            tot = len(data['dan_tinh_tuy_ngay_1']["lich_su"])

            c_trung = sum(1 for x in data['dan_tinh_tuy_ngay_1']["lich_su"] if x.get("ket_qua") == "trung")
            c_truot = sum(1 for x in data['dan_tinh_tuy_ngay_1']["lich_su"] if x.get("ket_qua") == "truot")
            avg_sz = round(sum(x.get("so_luong", 0) for x in data['dan_tinh_tuy_ngay_1']["lich_su"]) / tot, 1) if tot > 0 else 0

            # Tính chuỗi thắng thông gần nhất
            streak = 0
            for item in data['dan_tinh_tuy_ngay_1']["lich_su"]:
                if item.get("ket_qua") == "trung":
                    streak += 1
                else:
                    break

            data['dan_tinh_tuy_ngay_1']["tong_quan"] = {
                "tong_ngay": tot,
                "trung": c_trung,
                "truot": c_truot,
                "ty_le_trung": round(c_trung / tot * 100, 1) if tot > 0 else 0,
                "ty_le_truot": round(c_truot / tot * 100, 1) if tot > 0 else 0,
                "dan_tb": avg_sz,
                "chuoi_thong": streak
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[*] Đã cập nhật lịch sử Dàn Tinh Túy Ngày 1 vào: {file_path}")
        except Exception as e:
            print(f"[!] Lỗi ghi lịch sử Dàn Tinh Túy vào {file_path}: {e}")

def push_live_update(filled, total, is_done=False, actual_de=None):
    """Đồng bộ nhanh kết quả giải mới nổ lên GitHub để mobile cập nhật"""
    try:
        targets = ['ket_qua_soi_cau_g1_g5.json', 'lich_su_phuong_phap.json']
        if os.path.exists('live_radar_state.json'):
            targets.append('live_radar_state.json')
        if os.path.exists('58_up_to_75/ket_qua_soi_cau_g1_g5.json'):
            targets.append('58_up_to_75/ket_qua_soi_cau_g1_g5.json')
        if os.path.exists('58_up_to_75/lich_su_phuong_phap.json'):
            targets.append('58_up_to_75/lich_su_phuong_phap.json')
        subprocess.run(['git', 'add'] + targets, timeout=10, check=False)
        if actual_de:
            status_txt = f"NO GDB [{actual_de}]"
        elif is_done:
            status_txt = "HOAN TAT G5.6 - KHOA CHOT"
        else:
            status_txt = f"Da quay {filled}/{total} giai"
        msg = f"auto: Live XSMB {status_txt} [skip ci]"
        subprocess.run(['git', 'commit', '-m', msg], timeout=10, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Thử push trực tiếp
        res = subprocess.run(['git', 'push', 'origin', 'main'], timeout=20, check=False, capture_output=True, text=True)
        if res.returncode != 0:
            # Nếu remote có commit khác, fetch và auto-merge ưu tiên local
            subprocess.run(['git', 'fetch', 'origin', 'main'], timeout=15, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['git', 'merge', 'origin/main', '-X', 'ours', '--no-edit', '-m', 'auto: Sync live [skip ci]'], timeout=15, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['git', 'add'] + targets, timeout=10, check=False)
            subprocess.run(['git', 'commit', '-m', f"auto: Resolve live [skip ci]"], timeout=10, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            res = subprocess.run(['git', 'push', 'origin', 'main'], timeout=20, check=False, capture_output=True, text=True)
        
        # Đảm bảo hủy mọi rebase kẹt (nếu có)
        subprocess.run(['git', 'rebase', '--abort'], timeout=5, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if res.returncode == 0:
            print(f"      [✓ Cloud Sync] Đã đẩy thành công {status_txt} lên GitHub Pages!")
        else:
            err_msg = res.stderr.strip()[:100] if res.stderr else "Timeout/Rejection"
            print(f"      [!] Git push error: {err_msg}")
    except Exception as e:
        print(f"      [!] Lỗi push cloud: {e}")

def sync_full_history_60days():
    """Đồng bộ lại lịch sử kiểm chứng (4A, 4B, 4C) theo đúng thuật toán Radar G.ĐB -> G7 (27 giải)."""
    raw_draws = get_combined_draws(is_live=False)
    draws = [d for d in raw_draws if d.get('de') and len(str(d.get('de', '')).strip()) >= 2]
    if len(draws) < 5:
        return
    # Duyệt từ cũ đến mới để ghi lịch sử chuẩn thứ tự
    max_k = min(len(draws) - 2, 30)
    for k in range(max_k - 1, -1, -1):
        pred = analyze_and_verify_single_draw(draws, pred_for_idx=k)
        if pred:
            d_str = draws[k]['date']
            de_str = draws[k]['de']
            ghi_lich_su_khung(d_str, de_str, pred['kq_khung'])
            ghi_lich_su_truc_tiep(d_str, de_str, pred['top_1'], pred['top_4'], pred['dan_lot'])
            ghi_lich_su_tinh_tuy(d_str, de_str, pred['dan_tinhtuy'])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="XSMB AI - Radar G.ĐB -> G7 (107 Vị Trí) Dự Đoán Ngày Hôm Sau")
    parser.add_argument('--live', action='store_true', help='Chờ quay xong đủ 27 giải (có G.ĐB) rồi tự động chốt số ngày hôm sau & bắn Telegram')
    parser.add_argument('--interval', type=int, default=15, help='Khoảng thời gian kiểm tra kết quả (giây)')
    parser.add_argument('--backtest', type=int, default=0, help='Chỉ số kỳ cần soi (0: mới nhất vừa quay xong, 1: kỳ trước)')
    parser.add_argument('--csv', type=str, default=DEFAULT_CAP4_CSV, help='Đường dẫn file CSV 60 số Cấp 4')
    parser.add_argument('--max-minutes', type=int, default=25, help='Thời gian tối đa chờ hoàn tất kết quả (phút)')
    parser.add_argument('--n2-size', type=int, default=None, help='Số lượng số trong Dàn N2 (mở rộng, ví dụ: 42)')
    parser.add_argument('--n3-size', type=int, default=None, help='Số lượng số trong Dàn N3 (ví dụ: 40)')
    parser.add_argument('--push', action='store_true', help='Tự động git push lên GitHub để đồng bộ với GitHub Pages')
    parser.add_argument('--telegram', action='store_true', help='Bắn kết quả chốt số về Telegram cho Nguyễn Trung Đông (NV02) qua Bảng Lương PX GCCK')
    parser.add_argument('--sync-history', action='store_true', help='Đồng bộ lại lịch sử kiểm chứng theo Radar 27 giải')
    args = parser.parse_args()

    if args.sync_history:
        sync_full_history_60days()

    if args.live:
        print("\n" + "=" * 82)
        print(f" [*] ĐANG CHỜ KẾT QUẢ QUAY XONG ĐỦ 27 GIẢI (G.ĐB -> G7) ĐỂ CHỐT SỐ NGÀY HÔM SAU")
        print(" [*] Ngay khi có Giải Đặc Biệt, Radar quét 107 vị trí, chốt dàn ngày mai & bắn Telegram!")
        print("=" * 82)
        start_time = time.time()
        max_duration = args.max_minutes * 60
        today_str = datetime.now().strftime('%d-%m-%Y')
        while True:
            if time.time() - start_time > max_duration:
                print(f"\n[*] Đã đạt giới hạn thời gian chờ ({args.max_minutes} phút). Chạy phân tích kỳ mới nhất hiện có.")
                res = run_pipeline(target_draw_idx=0, cap4_csv=args.csv, n2_size=args.n2_size, n3_size=args.n3_size, is_live=False, send_tele=True)
                if args.push and res:
                    push_live_update(27, 27, is_done=True, actual_de=res.get('actual_de'))
                break
            try:
                raw_draws = get_combined_draws(is_live=False)
                draws = [d for d in raw_draws if d.get('de') and len(str(d.get('de', '')).strip()) >= 2]
                if draws and today_str in draws[0].get('date', ''):
                    res = run_pipeline(target_draw_idx=0, cap4_csv=args.csv, n2_size=args.n2_size, n3_size=args.n3_size, is_live=False, send_tele=True)
                    if args.push and res:
                        push_live_update(27, 27, is_done=True, actual_de=res.get('actual_de'))
                    print("[*] Đã hoàn tất chốt số dự đoán ngày hôm sau & gửi Telegram cho Nguyễn Trung Đông (NV02).")
                    break
                time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\n[*] Đã dừng tiến trình.")
                break
            except Exception as e:
                print(f"[!] Thử lại sau {args.interval}s: {e}")
                time.sleep(args.interval)
    else:
        res = run_pipeline(target_draw_idx=args.backtest, cap4_csv=args.csv, n2_size=args.n2_size, n3_size=args.n3_size, is_live=False, send_tele=args.telegram)
        if args.push and res:
            push_live_update(27, 27, is_done=True, actual_de=res.get('actual_de'))
