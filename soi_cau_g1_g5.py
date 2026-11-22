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
DAIPHAT_90N_URL = "https://xosodaiphat.com/xsmb-90-ngay.html"
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

def compute_ai_scores(all_draws, base_idx, unique_numbers_map=None):
    """
    Chấm điểm AI Score (0.0 - 10.0) cho các con số 2D dự đoán cho kỳ tiếp theo (N+1),
    tính từ kỳ vừa quay xong base_idx (Kỳ N):
    - prev_de = Đề vừa nổ của kỳ N (all_draws[base_idx]['de'])
    - prev_prev_de = Đề của kỳ N-1 (all_draws[base_idx + 1]['de'])
    - Tần suất 30 kỳ gần nhất tính từ base_idx (all_draws[base_idx : base_idx + 30])
    - Độ gan tính từ base_idx (số vừa nổ kỳ N có gan = 0)
    """
    prev_de = all_draws[base_idx].get('de') if base_idx < len(all_draws) else None
    prev_prev_de = all_draws[base_idx + 1].get('de') if base_idx + 1 < len(all_draws) else None
    
    # 30 kỳ gần nhất tính từ kỳ vừa quay xong base_idx
    hist_30 = [d['de'] for d in all_draws[base_idx : base_idx + 30] if d.get('de')]
    counter_30 = Counter(hist_30)
    
    # Tính độ gan chuẩn xác tính từ base_idx
    gan_dict = {}
    for i in range(100):
        n_str = f"{i:02d}"
        gan = 999
        for step, d in enumerate(all_draws[base_idx:]):
            if d.get('de') == n_str:
                gan = step
                break
        gan_dict[n_str] = gan
        
    bong_map = {0:5, 1:6, 2:7, 3:8, 4:9, 5:0, 6:1, 7:2, 8:3, 9:4}
    dau_set = set()
    duoi_set = set()
    if prev_de and len(prev_de) == 2 and prev_de.isdigit():
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
            
        # 4. Cầu vị trí G.ĐB -> G7
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
    """Nguồn dự phòng và lịch sử 90 kỳ quay đầy đủ 27 giải từ xosodaiphat.com."""
    dow_map = {0: 'Thứ hai', 1: 'Thứ ba', 2: 'Thứ tư', 3: 'Thứ năm', 4: 'Thứ sáu', 5: 'Thứ bảy', 6: 'Chủ nhật'}
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'draws_90d_cache.json')
    if use_30days and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as cf:
                cached_draws = json.load(cf)
                if isinstance(cached_draws, list) and len(cached_draws) >= 60:
                    # Nếu cache đã cập nhật trong vòng 10 phút thì dùng ngay cho siêu tốc
                    if time.time() - os.path.getmtime(cache_file) < 600:
                        return cached_draws
        except Exception:
            pass

    urls_to_try = [DAIPHAT_90N_URL, "https://xosodaiphat.com/xsmb-60-ngay.html", DAIPHAT_30N_URL] if use_30days else [DAIPHAT_LIVE_URL]
    html = ""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'}
    for u in urls_to_try:
        try:
            if HAS_BS4:
                r = requests.get(u, headers=headers, timeout=20)
                if r.status_code == 200 and 'table-xsmb' in r.text:
                    html = r.text
                    break
            else:
                req = urllib.request.Request(u, headers=headers)
                with urllib.request.urlopen(req, timeout=20) as resp:
                    txt = resp.read().decode('utf-8', errors='ignore')
                    if 'table-xsmb' in txt:
                        html = txt
                        break
        except Exception as e:
            print(f"[!] Thử kết nối {u}: {e}")
            continue

    if not html:
        if use_30days and os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as cf:
                    return json.load(cf)
            except Exception:
                pass
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
    if use_30days and len(draws) >= 30:
        try:
            with open(cache_file, 'w', encoding='utf-8') as cf:
                json.dump(draws, cf, ensure_ascii=False, indent=2)
        except Exception:
            pass
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
            if not de or len(de) < 2 or not de.isdigit():
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

def select_core_bridge_positions(positions):
def select_core_bridge_positions(positions, partner_positions=None):
    """
    Lọc lấy các vị trí cầu chất lượng cao (loại bỏ nhiễu từ hàng chục vị trí mới chạm 1 ngày ngẫu nhiên):
    - Giữ toàn bộ các vị trí cầu ăn thông >= 2 ngày (2d, 3d, 4d+).
    - Nếu số vị trí >= 2 ngày ít hơn 4, bổ sung thêm các vị trí 1 ngày ăn CHÍNH DIỆN (trực tiếp, không qua bóng)
      ưu tiên giải trọng tâm (GDB, G1, G7, G2, G3) cho đủ tối đa 5 vị trí tinh nhuệ nhất.
    Lọc lấy các vị trí cầu chất lượng cao (Smart Bridge Coverage - Phủ đủ phổ chạm 100%):
    - Giữ toàn bộ các vị trí cầu ăn thông >= 2 ngày (2d, 3d, 4d+, tối đa 8 vị trí).
    - Bổ sung vị trí cầu 1 ngày tinh nhuệ nhất (ưu tiên Cầu Đồng Giải / Sát Vách với cầu >= 2 ngày của chiều kia,
      ăn chính diện và thuộc giải trọng tâm GDB, G1, G7, G5.5, G5.4, G2, G3) cho các cặp chữ số (d, bóng d)
      chưa có đại diện để không bao giờ đánh rơi con số tiềm năng đang lên nhịp ngày 2.
    """
    multi_day = [p for p in positions if p['cycle_days'] >= 2]
    multi_day.sort(key=lambda x: (x['cycle_days'], 1 if x.get('is_direct') else 0), reverse=True)
    if len(multi_day) >= 4:
        return multi_day[:8]
    direct_1d = [p for p in positions if p['cycle_days'] == 1 and p.get('is_direct')]
    def prize_priority(p_str):
        if p_str.startswith('GDB'): return 5
        if p_str.startswith('G1'): return 4
        if p_str.startswith('G7'): return 3
        if p_str.startswith('G2'): return 2
        return 1
    direct_1d.sort(key=lambda x: prize_priority(x['position']), reverse=True)
    combined = multi_day + direct_1d[:max(0, 5 - len(multi_day))]
    return combined if combined else positions[:5]
    def _prize_code_of(pos_str):
        return pos_str.split()[0] if pos_str else ''

    partner_multi_prizes = set()
    if partner_positions:
        for pp in partner_positions:
            if pp.get('cycle_days', 1) >= 2:
                partner_multi_prizes.add(_prize_code_of(pp.get('position', '')))

    def _pos_priority(p):
        p_str = p.get('position', '')
        p_code = _prize_code_of(p_str)
        same_prize_bonus = 20 if p_code in partner_multi_prizes else 0
        if p_str.startswith('GDB'): pr = 10
        elif p_str.startswith('G1'): pr = 9
        elif p_str.startswith('G7'): pr = 8
        elif p_str.startswith(('G5.5', 'G5.4')): pr = 7
        elif p_str.startswith('G2'): pr = 6
        elif p_str.startswith('G3'): pr = 5
        else: pr = 4
        return (p.get('cycle_days', 1), same_prize_bonus, 1 if p.get('is_direct') else 0, pr)

    multi_day = [p for p in positions if p.get('cycle_days', 1) >= 2]
    multi_day.sort(key=_pos_priority, reverse=True)
    selected = list(multi_day[:8])

    covered_pairs = set()
    for p in selected:
        d = int(p['digit'])
        covered_pairs.add(tuple(sorted((d, BONG_DUONG[d]))))

    rem_1d = [p for p in positions if p.get('cycle_days', 1) == 1]
    rem_1d.sort(key=_pos_priority, reverse=True)
    for p in rem_1d:
        d = int(p['digit'])
        pair_k = tuple(sorted((d, BONG_DUONG[d])))
        p_code = _prize_code_of(p.get('position', ''))
        if pair_k not in covered_pairs or (p_code in partner_multi_prizes and len(selected) < 9):
            selected.append(p)
            covered_pairs.add(pair_k)
        if len(selected) >= 10:
            break

    return selected if selected else positions[:6]

_CACHED_SUMMARY_DATA = None
_CACHED_CHRONO_2026 = None
_CACHED_DATE_TO_CHRONO_IDX = None

def _load_summary_data_cached():
    global _CACHED_SUMMARY_DATA
    if _CACHED_SUMMARY_DATA is not None:
        return _CACHED_SUMMARY_DATA
    summary_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'analysis_summary.json')
    if os.path.exists(summary_path):
        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                _CACHED_SUMMARY_DATA = json.load(f)
                return _CACHED_SUMMARY_DATA
        except Exception:
            pass
    _CACHED_SUMMARY_DATA = {}
    return _CACHED_SUMMARY_DATA

def _load_chrono_2026_cached():
    global _CACHED_CHRONO_2026, _CACHED_DATE_TO_CHRONO_IDX
    if _CACHED_CHRONO_2026 is not None:
        return _CACHED_CHRONO_2026, _CACHED_DATE_TO_CHRONO_IDX
    d26_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data_2026.json')
    if os.path.exists(d26_path):
        try:
            with open(d26_path, 'r', encoding='utf-8') as f:
                d26 = json.load(f)
                _CACHED_CHRONO_2026 = list(reversed(d26))
                _CACHED_DATE_TO_CHRONO_IDX = {r['date'].split()[-1]: i for i, r in enumerate(_CACHED_CHRONO_2026)}
                return _CACHED_CHRONO_2026, _CACHED_DATE_TO_CHRONO_IDX
        except Exception:
            pass
    _CACHED_CHRONO_2026 = []
    _CACHED_DATE_TO_CHRONO_IDX = {}
    return _CACHED_CHRONO_2026, _CACHED_DATE_TO_CHRONO_IDX

def _parse_draw_dt(date_str):
    m = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', str(date_str))
    if m:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    return None

def _get_positions_27_for_conv(prizes):
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
                positions[f"{g_code}_{pos_idx}"] = (char, f"{g_code} vị trí {pos_idx}")
    return positions

def _compute_4_fixes_scores(draws, cur_idx):
    """
    Tính điểm 4 lớp nâng cấp (Walk-Forward 100%, không dùng số ảo):
    1. Cầu Đôi 27 Giải (107 vị trí từ prev_draw ăn vào cur_de -> lấy chữ số tại cur_draw).
    2. Chu kỳ Kép: Tầng Ngày (N -> N+1) + Tầng Tuần (T-7 -> T) + Tổng G7 Thứ 7 gần nhất.
    3. Tam Giác Vàng G7: Ghép Chéo G7 hôm nay (Cross-G7), G7 Rơi Trễ N2/N3 (Lag-G7), G7 Thứ tuần trước (T-7) & Cầu Góc G7.1[0]+G7.4[1].
    4. Đảo chiều Đầu Lớn/Nhỏ khi bệt >= 2 kỳ liên tiếp.
    """
    chrono, date_to_chrono_idx = _load_chrono_2026_cached()
    cur_draw = draws[cur_idx]
    prev_draw = draws[cur_idx + 1]
    cur_de = str(cur_draw.get('de', '')).strip()
    prev_de = str(prev_draw.get('de', '')).strip()
    sub_draws = draws[cur_idx:]

    def _get_tong_s(s):
        return (int(s[0]) + int(s[1])) % 10 if s and len(s) == 2 and s.isdigit() else None

    def _get_pair_s(t):
        return tuple(sorted((t, BONG_DUONG[t])))

    def _get_bo_s(s_val):
        if not s_val or len(s_val) != 2 or not s_val.isdigit():
            return set()
        da, db = int(s_val[0]), int(s_val[1])
        ba, bb = BONG_DUONG[da], BONG_DUONG[db]
        return {f"{x}{y}" for x in (da, ba) for y in (db, bb)} | {f"{y}{x}" for x in (da, ba) for y in (db, bb)}

    cur_dk = cur_draw.get('date', '').split()[-1]
    if chrono and cur_dk in date_to_chrono_idx:
        step_idx = date_to_chrono_idx[cur_dk]
        sub_history = chrono[:step_idx + 1]
        curr_d = chrono[step_idx]
    else:
        sub_history = [
            {
                'date': d.get('date', ''),
                'de': d.get('de', ''),
                'g7_1': d.get('prizes', {}).get('G7.1', ''),
                'g7_2': d.get('prizes', {}).get('G7.2', ''),
                'g7_3': d.get('prizes', {}).get('G7.3', ''),
                'g7_4': d.get('prizes', {}).get('G7.4', ''),
            }
            for d in reversed(sub_draws)
        ]
        step_idx = len(sub_history) - 1
        curr_d = sub_history[-1]
    sub_des = [r['de'] for r in sub_history if r.get('de')]

    cur_dt = _parse_draw_dt(cur_draw.get('date', ''))
    cur_dow = cur_dt.weekday() if cur_dt else 0
    target_dow = (cur_dow + 1) % 7

    daily_dow_g_hits = Counter()
    weekly_dow_g_hits = Counter()
    sub_target_dow_recs = []
    for r_i in range(len(sub_history) - 1):
        cr = sub_history[r_i]
        cdt = _parse_draw_dt(cr['date'])
        if not cdt:
            continue
        if cdt.weekday() == cur_dow:
            nxt_s = _get_tong_s(sub_history[r_i + 1]['de'])
            for gk in ('g7_1', 'g7_2', 'g7_3', 'g7_4'):
                t = _get_tong_s(cr[gk])
                if t is not None and nxt_s in (t, BONG_DUONG[t]):
                    daily_dow_g_hits[gk] += 1.3 if nxt_s == t else 1.0
        if cdt.weekday() == target_dow:
            sub_target_dow_recs.append(cr)

    for r_i in range(len(sub_target_dow_recs) - 1):
        cr = sub_target_dow_recs[r_i]
        nr = sub_target_dow_recs[r_i + 1]
        ns = _get_tong_s(nr['de'])
        for gk in ('g7_1', 'g7_2', 'g7_3', 'g7_4'):
            t = _get_tong_s(cr[gk])
            if t is not None and ns in (t, BONG_DUONG[t]):
                weekly_dow_g_hits[gk] += 1.3 if ns == t else 1.0

    top2_daily_g = sorted(['g7_1', 'g7_2', 'g7_3', 'g7_4'], key=lambda k: daily_dow_g_hits[k], reverse=True)[:2]
    top2_weekly_g = sorted(['g7_1', 'g7_2', 'g7_3', 'g7_4'], key=lambda k: weekly_dow_g_hits[k], reverse=True)[:2]

    win_g_hits = Counter()
    for r_i in range(max(0, step_idx - 30), step_idx):
        cr = sub_history[r_i]
        ns = _get_tong_s(sub_history[r_i + 1]['de'])
        for gk in ('g7_1', 'g7_2', 'g7_3', 'g7_4'):
            t = _get_tong_s(cr[gk])
            if t is not None and ns in (t, BONG_DUONG[t]):
                win_g_hits[gk] += 1
    win_top2_g = sorted(['g7_1', 'g7_2', 'g7_3', 'g7_4'], key=lambda k: win_g_hits[k], reverse=True)[:2]

    sat_draw = None
    for sd in sub_draws:
        sdt = _parse_draw_dt(sd.get('date', ''))
        if sdt and sdt.weekday() == 5:
            sat_draw = sd
            break

    last_week_same_dow = sub_target_dow_recs[-1] if sub_target_dow_recs else None

    pair_votes = Counter()
    direct_g7_sums = set()
    for gk in ('g7_1', 'g7_2', 'g7_3', 'g7_4'):
        t = _get_tong_s(curr_d[gk])
        if t is not None:
            direct_g7_sums.add(t)
            p = _get_pair_s(t)
            pair_votes[p] += 1.0
            if gk in top2_daily_g:
                pair_votes[p] += 2.2
            if gk in win_top2_g:
                pair_votes[p] += 1.8
            if gk in top2_daily_g and gk in win_top2_g:
                pair_votes[p] += 1.2

    t7_direct_sums = set()
    if last_week_same_dow:
        for gk in top2_weekly_g:
            t7 = _get_tong_s(last_week_same_dow[gk])
            if t7 is not None:
                t7_direct_sums.add(t7)
                pair_votes[_get_pair_s(t7)] += 1.8

    sat_sums, sat_direct_sums, sat_chams = set(), set(), set()
    if sat_draw:
        sp = sat_draw.get('prizes', {})
        for gk in ('G7.4', 'G7.2', 'G7.3', 'G7.1'):
            vs = sp.get(gk, '')
            if len(vs) == 2 and vs.isdigit():
                ts = (int(vs[0]) + int(vs[1])) % 10
                sat_direct_sums.add(ts)
                sat_sums.add(ts)
                sat_sums.add(BONG_DUONG[ts])
                sat_chams.add(vs[0])
                sat_chams.add(vs[1])
                pair_votes[_get_pair_s(ts)] += 1.6 if gk in ('G7.4', 'G7.2') else 0.9

    c_head = int(curr_d['g7_1'][0]) if curr_d.get('g7_1') and curr_d['g7_1'][0].isdigit() else 0
    c_tail = int(curr_d['g7_4'][1]) if len(curr_d.get('g7_4', '')) >= 2 and curr_d['g7_4'][1].isdigit() else 0
    corner_sum = (c_head + c_tail) % 10
    corner_bt = f"{c_head}{c_tail}"
    pair_votes[_get_pair_s(corner_sum)] += 1.6

    cur_de_sum = _get_tong_s(cur_de)
    cur_de_pair = _get_pair_s(cur_de_sum) if cur_de_sum is not None else (-1, -1)
    if step_idx >= 1:
        prev1 = sub_history[step_idx - 1]
        for gk in ('g7_1', 'g7_2', 'g7_3', 'g7_4'):
            t = _get_tong_s(prev1[gk])
            if t is not None and _get_pair_s(t) != cur_de_pair:
                pair_votes[_get_pair_s(t)] += 1.2
    if sum(1 for gk in ('g7_1', 'g7_2', 'g7_3', 'g7_4') if _get_tong_s(curr_d[gk]) is not None and _get_pair_s(_get_tong_s(curr_d[gk])) == cur_de_pair) < 2:
        pair_votes[cur_de_pair] -= 2.5

    ranked_pairs = [p for p, _ in sorted(pair_votes.items(), key=lambda x: x[1], reverse=True)]
    top3_pairs = ranked_pairs[:3]
    target_sums = {s for p in top3_pairs for s in p}
    peak2_sums = {s for p in ranked_pairs[:2] for s in p}

    target_pos_27 = _get_positions_27_for_conv(cur_draw['prizes'])
    prev_pos_27 = _get_positions_27_for_conv(prev_draw['prizes'])
    h_targets = [cur_de[0], str(BONG_DUONG[int(cur_de[0])])]
    t_targets = [cur_de[1], str(BONG_DUONG[int(cur_de[1])])]

    h27_power, t27_power = Counter(), Counter()
    h_2d, t_2d = Counter(), Counter()
    h_3d, t_3d = Counter(), Counter()
    h_1d, t_1d = Counter(), Counter()

    for pk, (ch, _) in prev_pos_27.items():
        if pk not in target_pos_27:
            continue
        cur_ch = target_pos_27[pk][0]
        cur_b = str(BONG_DUONG[int(cur_ch)])
        if ch in h_targets:
            st, h5, broken = 1, 1, False
            for step in range(1, min(6, len(sub_draws) - 1)):
                de_s = sub_draws[step].get('de', '')
                if not de_s or len(de_s) < 2:
                    break
                sp = _get_positions_27_for_conv(sub_draws[step + 1]['prizes'])
                if pk in sp and sp[pk][0] in (de_s[0], str(BONG_DUONG[int(de_s[0])])):
                    h5 += 1
                    if not broken:
                        st += 1
                else:
                    broken = True
            is_dir = (ch == cur_de[0])
            d_out = cur_ch if is_dir else cur_b
            w = 45.0 if (st >= 3 or h5 >= 4) else (32.0 if (st == 2 or h5 == 3) else (3.5 if is_dir else 0.8))
            if is_dir:
                w *= 1.3
            if pk.startswith(('GDB', 'G1', 'G7')):
                w *= 1.25
            h27_power[d_out] += w
            if st >= 2:
                h27_power[cur_b if is_dir else cur_ch] += w * 0.25
            if st == 2:
                h_2d[d_out] += (1.3 if is_dir else 1.0)
            elif st >= 3:
                h_3d[d_out] += (1.3 if is_dir else 1.0)
            elif st == 1 and is_dir:
                h_1d[d_out] += 1.0

        if ch in t_targets:
            st, h5, broken = 1, 1, False
            for step in range(1, min(6, len(sub_draws) - 1)):
                de_s = sub_draws[step].get('de', '')
                if not de_s or len(de_s) < 2:
                    break
                sp = _get_positions_27_for_conv(sub_draws[step + 1]['prizes'])
                if pk in sp and sp[pk][0] in (de_s[1], str(BONG_DUONG[int(de_s[1])])):
                    h5 += 1
                    if not broken:
                        st += 1
                else:
                    broken = True
            is_dir = (ch == cur_de[1])
            d_out = cur_ch if is_dir else cur_b
            w = 45.0 if (st >= 3 or h5 >= 4) else (32.0 if (st == 2 or h5 == 3) else (3.5 if is_dir else 0.8))
            if is_dir:
                w *= 1.3
            if pk.startswith(('GDB', 'G1', 'G7')):
                w *= 1.25
            t27_power[d_out] += w
            if st >= 2:
                t27_power[cur_b if is_dir else cur_ch] += w * 0.25
            if st == 2:
                t_2d[d_out] += (1.3 if is_dir else 1.0)
            elif st >= 3:
                t_3d[d_out] += (1.3 if is_dir else 1.0)
            elif st == 1 and is_dir:
                t_1d[d_out] += 1.0

    g7_list_cur = [cur_draw['prizes'].get(f'G7.{i}', '') for i in range(1, 5)]
    same_g7_today = set()
    direct_g7_chams = set()
    bong_g7_chams = set()
    for vg in g7_list_cur:
        if len(vg) == 2 and vg.isdigit():
            same_g7_today.add(vg)
            same_g7_today.add(vg[1] + vg[0])
            for ch in vg:
                direct_g7_chams.add(ch)
                bong_g7_chams.add(str(BONG_DUONG[int(ch)]))

    cross_g7_today = set()
    for i_g in range(4):
        for j_g in range(4):
            if i_g != j_g and len(g7_list_cur[i_g]) == 2 and len(g7_list_cur[j_g]) == 2:
                for ch_a in g7_list_cur[i_g]:
                    for ch_b in g7_list_cur[j_g]:
                        if ch_a != ch_b and ch_a.isdigit() and ch_b.isdigit():
                            cross_g7_today.add(f"{ch_a}{ch_b}")
    cross_g7_today -= same_g7_today

    recent_des_3 = {sub_draws[b]['de'] for b in range(0, min(3, len(sub_draws))) if sub_draws[b].get('de')}
    g7_lag_n2_n3 = set()
    g7_lag_bo = set()
    for b_step in range(1, min(4, len(sub_draws))):
        for gk in ('G7.1', 'G7.2', 'G7.3', 'G7.4'):
            vg = sub_draws[b_step]['prizes'].get(gk, '')
            if len(vg) == 2 and vg.isdigit():
                if vg not in recent_des_3 and (vg[1] + vg[0]) not in recent_des_3:
                    g7_lag_n2_n3.add(vg)
                    g7_lag_n2_n3.add(vg[1] + vg[0])
                g7_lag_bo.update(_get_bo_s(vg))

    t7_g7_exact = set()
    if last_week_same_dow:
        for gk in ('g7_1', 'g7_2', 'g7_3', 'g7_4'):
            vg = last_week_same_dow.get(gk, '')
            if len(vg) == 2 and vg.isdigit():
                t7_g7_exact.add(vg)
                t7_g7_exact.add(vg[1] + vg[0])

    cur_head_big = int(cur_de[0]) >= 5
    prev_head_big = int(prev_de[0]) >= 5 if (prev_de and len(prev_de) >= 2 and prev_de[0].isdigit()) else (not cur_head_big)
    is_streak_2_head = (cur_head_big == prev_head_big)
    prefer_small_head = cur_head_big

    cur_p = cur_draw['prizes']
    p_g1 = cur_p.get('G1', '')
    tam_g1 = p_g1[2] if len(p_g1) >= 3 and p_g1.isdigit() else ''
    tam_g1_set = {tam_g1, str(BONG_DUONG[int(tam_g1)])} if tam_g1 else set()
    p_gdb = cur_p.get('GDB', cur_draw.get('db', ''))
    tam_gdb = p_gdb[2] if len(p_gdb) >= 3 and p_gdb.isdigit() else ''
    tam_gdb_set = {tam_gdb, str(BONG_DUONG[int(tam_gdb)])} if tam_gdb else set()
    g55_val = cur_p.get('G5.5', '')
    g55_last = g55_val[-1] if g55_val and g55_val[-1].isdigit() else ''
    g55_set = {g55_last, str(BONG_DUONG[int(g55_last)])} if g55_last else set()

    f30 = Counter(sub_des[-30:])
    f60 = Counter(sub_des[-60:])
    f90 = Counter(sub_des[-90:])

    scored_100 = {}
    for num in range(100):
        ns = f"{num:02d}"
        c_d, d_d = ns[0], ns[1]
        nsum = (int(c_d) + int(d_d)) % 10
        p = _get_pair_s(nsum)

        sc = 0.0
        if nsum in target_sums:
            sc += 75.0 + pair_votes[p] * 4.0
        if nsum in peak2_sums:
            sc += 25.0
        if nsum in sat_sums:
            sc += 45.0
        if nsum in sat_direct_sums:
            sc += 20.0
        if nsum in direct_g7_sums:
            sc += 22.0
        if nsum in t7_direct_sums:
            sc += 20.0

        if ns in cross_g7_today:
            sc += 68.0
        if ns in g7_lag_n2_n3:
            sc += 72.0
        elif ns in g7_lag_bo:
            sc += 28.0
        if ns in t7_g7_exact:
            sc += 42.0
        if ns == corner_bt or ns == calc_lot_lon(corner_bt):
            sc += 48.0 if ns == corner_bt else 35.0

        if ns in same_g7_today and ns not in g7_lag_n2_n3:
            sc += 15.0
        else:
            if c_d in direct_g7_chams and d_d in direct_g7_chams:
                sc += 65.0
            elif c_d in direct_g7_chams or d_d in direct_g7_chams:
                sc += 38.0
            elif c_d in bong_g7_chams or d_d in bong_g7_chams:
                sc += 18.0

        if c_d in sat_chams and d_d in sat_chams:
            sc += 28.0
        elif c_d in sat_chams or d_d in sat_chams:
            sc += 14.0

        sc += min((h27_power[c_d] + t27_power[d_d]) * 0.35, 95.0)
        if (h_2d[c_d] > 0 or h_3d[c_d] > 0) and (t_2d[d_d] > 0 or t_3d[d_d] > 0):
            sc += 65.0
        elif (h_2d[c_d] > 0 or h_3d[c_d] > 0) and t_1d[d_d] > 0:
            sc += 35.0
        elif (t_2d[d_d] > 0 or t_3d[d_d] > 0) and h_1d[c_d] > 0:
            sc += 35.0

        if c_d in tam_g1_set or d_d in tam_g1_set:
            sc += 32.0 if (c_d == tam_g1 or d_d == tam_g1) else 20.0
        if c_d in tam_gdb_set or d_d in tam_gdb_set:
            sc += 28.0 if (c_d == tam_gdb or d_d == tam_gdb) else 16.0
        if c_d in g55_set or d_d in g55_set:
            sc += 28.0 if (c_d == g55_last or d_d == g55_last) else 16.0

        is_small = int(c_d) < 5
        if is_small == prefer_small_head:
            sc += 32.0 if is_streak_2_head else 16.0

        nhip = 999
        for bi, pde in enumerate(reversed(sub_des)):
            if pde == ns:
                nhip = bi
                break
        if 5 <= nhip <= 22:
            sc += 18.0
        elif 23 <= nhip <= 40:
            sc += 10.0
        sc += f30[ns] * 4.0 + f60[ns] * 2.5 + f90[ns] * 1.2

        if c_d != d_d:
            orient_diff = (h27_power[c_d] - h27_power[d_d]) + (t27_power[d_d] - t27_power[c_d])
            if orient_diff > 0:
                sc += min(orient_diff * 0.15, 22.0)

        if ns == cur_de:
            sc -= 150.0
        elif ns == calc_lot_lon(cur_de):
            sc -= 50.0
        if c_d == d_d:
            sc -= 45.0

        scored_100[ns] = round(sc, 2)

    return scored_100, cross_g7_today

def compute_static_g7_radar_convergence(draws, target_draw_idx, summary_data=None):
    """
    Hội tụ Radar Tĩnh 27 Giải (G.ĐB -> G7, 107 vị trí) + Tổng G7 của ngày Thứ 7 gần nhất (Saturday Weekly Anchor)
    & Tổng G7 của các ngày Thứ mạnh nhất trong tuần (lõi thuật toán 67_up_95 áp cho Dàn Tĩnh):
    - Trích xuất Bạch Thủ (Top 1), Số Đảo (Lót lộn), Tứ Thủ (Top 4), Dàn 9 Số và Dàn Số Đảo mạnh nhất.
    """
    if target_draw_idx + 1 >= len(draws):
        return None
    if summary_data is None:
        summary_data = _load_summary_data_cached()

    import live_radar_scanner as lrs

    cur_draw = draws[target_draw_idx]       # Kỳ vừa quay xong (Day N)
    prev_draw = draws[target_draw_idx + 1]  # Kỳ trước đó (Day N-1)
    cur_de = str(cur_draw.get('de', '')).strip()
    if len(cur_de) < 2 or not cur_de.isdigit():
        return None

    if target_draw_idx >= 1:
        next_date_str = draws[target_draw_idx - 1]['date']
    else:
        next_date_str, _ = compute_next_date_str(cur_draw['date'])

    cap4_list = lrs.get_dynamic_dan60_for_date(next_date_str, summary_data)
    cap4_set = set(cap4_list)

    # 1. Chạy lõi hội tụ đa cầu 67_up_95 trên kết quả của kỳ vừa quay xong (cur_draw) cho ngày next_date_str
    static_target = {'date': next_date_str, 'db': '', 'de': '', 'prizes': cur_draw['prizes']}
    sub_draws = draws[target_draw_idx:]
    base_res = lrs.compute_radar_convergence([static_target] + sub_draws, cap4_set, summary_data)
    base_res = lrs.compute_radar_convergence([static_target] + sub_draws, cap4_set, summary_data, ignore_snapshot=True)
    if not base_res:
        return None

    # 2. Quét 107 vị trí cầu 27 giải (GDB -> G7.4) từ prev_draw ăn vào cur_de -> lấy chữ số tại cur_draw dự đoán cho next_date_str
    head_targets = [cur_de[0], str(BONG_DUONG[int(cur_de[0])])]
    tail_targets = [cur_de[1], str(BONG_DUONG[int(cur_de[1])])]
    target_pos_27 = _get_positions_27_for_conv(cur_draw['prizes'])
    prev_pos_27 = _get_positions_27_for_conv(prev_draw['prizes'])
    h27_power = Counter()
    t27_power = Counter()
    for pk, (ch, _) in prev_pos_27.items():
        if pk not in target_pos_27:
            continue
        cur_ch = target_pos_27[pk][0]
        cur_b = str(BONG_DUONG[int(cur_ch)])
        if ch in head_targets:
            st = 1
            for step in range(1, min(6, len(sub_draws) - 1)):
                de_s = sub_draws[step].get('de', '')
                if not de_s or len(de_s) < 2:
                    break
                sp = _get_positions_27_for_conv(sub_draws[step + 1]['prizes'])
                if pk in sp and sp[pk][0] in (de_s[0], str(BONG_DUONG[int(de_s[0])])):
                    st += 1
                else:
                    break
            w = 35.0 if st >= 3 else (22.0 if st == 2 else (3.5 if ch == cur_de[0] else 0.8))
            if pk.startswith(('GDB', 'G1', 'G7')):
                w *= 1.25
            h27_power[cur_ch if ch == cur_de[0] else cur_b] += w
        if ch in tail_targets:
            st = 1
            for step in range(1, min(6, len(sub_draws) - 1)):
                de_s = sub_draws[step].get('de', '')
                if not de_s or len(de_s) < 2:
                    break
                sp = _get_positions_27_for_conv(sub_draws[step + 1]['prizes'])
                if pk in sp and sp[pk][0] in (de_s[1], str(BONG_DUONG[int(de_s[1])])):
                    st += 1
                else:
                    break
            w = 35.0 if st >= 3 else (22.0 if st == 2 else (3.5 if ch == cur_de[1] else 0.8))
            if pk.startswith(('GDB', 'G1', 'G7')):
                w *= 1.25
            t27_power[cur_ch if ch == cur_de[1] else cur_b] += w

    # 3. Trích xuất Tổng G7 của ngày Thứ 7 gần nhất (Saturday Weekly Anchor) & Thứ mạnh nhất trong tuần
    sat_draw = None
    for s_d in sub_draws:
        sdt = _parse_draw_dt(s_d.get('date', ''))
        if sdt and sdt.weekday() == 5:
            sat_draw = s_d
            break

    sat_sums = set()
    sat_direct_sums = set()
    sat_top2_sums = set()
    sat_chams = set()
    if sat_draw:
        sp = sat_draw.get('prizes', {})
        for gk in ('G7.4', 'G7.2', 'G7.3', 'G7.1'):
            vs = sp.get(gk, '')
            if len(vs) == 2 and vs.isdigit():
                ts = (int(vs[0]) + int(vs[1])) % 10
                sat_direct_sums.add(ts)
                sat_sums.add(ts)
                sat_sums.add(BONG_DUONG[ts])
                if gk in ('G7.4', 'G7.2'):
                    sat_top2_sums.add(ts)
                    sat_top2_sums.add(BONG_DUONG[ts])
                sat_chams.add(vs[0])
                sat_chams.add(vs[1])

    cur_dt = _parse_draw_dt(cur_draw.get('date', ''))
    cur_dow = str(cur_dt.weekday()) if cur_dt else '0'
    dow_prof = summary_data.get('dow_model', {}).get('dow_g7_profile', {}).get(cur_dow, {}) if summary_data else {}
    dow_rank_keys = [gk.upper().replace('_', '.') for gk in dow_prof.get('ranking', ['g7_1', 'g7_2', 'g7_3', 'g7_4'])[:2]]
    dow_top2_direct_sums = set()
    dow_top2_sums = set()
    for gk in dow_rank_keys:
        vg = cur_draw['prizes'].get(gk, '')
        if len(vg) == 2 and vg.isdigit():
            tg = (int(vg[0]) + int(vg[1])) % 10
            dow_top2_direct_sums.add(tg)
            dow_top2_sums.add(tg)
            dow_top2_sums.add(BONG_DUONG[tg])

    t_key_cur = lrs.extract_date_key(next_date_str)
    dow_m = summary_data.get('dow_model', {}) if summary_data else {}
    dow_ha_so_list = []
    dow_giao_thoa_set = set()
    dow_sums = set()
    for r_dow in reversed(dow_m.get('history_log_dow', [])):
        if lrs.extract_date_key(r_dow.get('date', '')) == t_key_cur:
            dow_ha_so_list = list(r_dow.get('dan_ha_so_ranked') or [x.strip() for x in r_dow.get('dan_ha_so_str', '').split(',') if x.strip()])
            dow_giao_thoa_set = {x.strip() for x in r_dow.get('dan_str', '').split(',') if x.strip()}
            for m_s in re.findall(r'\d+', r_dow.get('target_sums_str', '')):
                dow_sums.add(int(m_s))
            break
    if not dow_ha_so_list:
        dow_ha_so_list = list(dow_m.get('next_dan_ha_so', []))
        dow_giao_thoa_set = set(dow_m.get('next_dan_giao_thoa', []))
        dow_sums = set(dow_m.get('next_target_sums', []))

    hs20_set = set(dow_ha_so_list)
    gt_set = set(dow_giao_thoa_set) | hs20_set

    bt = base_res['top_1']
    t4 = list(base_res['top_4'])
    d9 = list(base_res['dan_9_so'])

    found_sc = {x['num']: x.get('consensus_score', 0.0) for x in base_res['found_list']}
    def _cand_sat_dow_score(ns):
        if not ns or len(ns) != 2 or not ns.isdigit():
            return -999.0
        s_v = (int(ns[0]) + int(ns[1])) % 10
        sc = found_sc.get(ns, 0.0) * 0.25 + (h27_power[ns[0]] + t27_power[ns[1]]) * 0.45
        if ns in hs20_set: sc += 90.0
        elif ns in gt_set: sc += 45.0
        if ns in cap4_set: sc += 55.0
        if s_v in sat_sums: sc += 75.0
        if s_v in sat_direct_sums: sc += 30.0
        if s_v in sat_top2_sums: sc += 25.0
        if s_v in dow_top2_sums: sc += 60.0
        if s_v in dow_top2_direct_sums: sc += 25.0
        if ns[0] in sat_chams and ns[1] in sat_chams: sc += 30.0
        elif ns[0] in sat_chams or ns[1] in sat_chams: sc += 15.0
        if ns == cur_de: sc -= 120.0
        if ns[0] == ns[1]: sc -= 40.0
        return sc

    # Khóa nghiệm Tổng G7 Thứ 7 & Thứ mạnh nhất cho Dàn 9 số, Tứ Thủ và Bạch Thủ
    frozen_snap = lrs.load_locked_g55_snapshot(next_date_str)
    if not frozen_snap:
    # Khóa nghiệm Tổng G7 Thứ 7 & Thứ mạnh nhất cho Dàn 9 số, Tứ Thủ và Bạch Thủ (100% Tĩnh, không phụ thuộc snapshot live)
    if True:
        d9_strong = [
            x for x in d9
            if (x in hs20_set or lrs.get_lot_lon(x) in hs20_set or ((int(x[0])+int(x[1]))%10 in sat_sums and x in gt_set))
        ]
        dia_pool_all = sorted(
            [
                x for x in (hs20_set & cap4_set)
                if ((int(x[0])+int(x[1]))%10 in sat_sums)
                and ((int(x[0])+int(x[1]))%10 in dow_top2_sums)
                and x != cur_de and x[0] != x[1]
            ],
            key=_cand_sat_dow_score,
            reverse=True
        )
        new_d9_list = list(d9_strong)
        for cand in dia_pool_all + d9:
            if len(new_d9_list) >= 9:
                break
            if cand not in new_d9_list and lrs.get_lot_lon(cand) not in new_d9_list:
                new_d9_list.append(cand)
        d9 = sorted(new_d9_list[:9])

        if bt not in hs20_set and lrs.get_lot_lon(bt) not in hs20_set:
            t4_dia = [
                c for c in t4
                if c in hs20_set and c in cap4_set
                and ((int(c[0]) + int(c[1])) % 10 in sat_sums)
                and c != cur_de and c[0] != c[1]
            ]
            if t4_dia:
                t4_dia.sort(key=_cand_sat_dow_score, reverse=True)
                bt = t4_dia[0]
                t4.remove(bt)
                t4 = [bt] + t4[:3]

        clean_t4 = [bt]
        for x in t4[1:]:
            rev_x = lrs.get_lot_lon(x)
            if x not in clean_t4 and rev_x not in clean_t4:
                clean_t4.append(x)
        fill_pool = sorted(list(set(d9) | (hs20_set & cap4_set)), key=_cand_sat_dow_score, reverse=True)
        for cand in fill_pool:
            if len(clean_t4) >= 4:
                break
            if cand not in clean_t4 and lrs.get_lot_lon(cand) not in clean_t4 and cand != cur_de:
                clean_t4.append(cand)
        for idx_t in range(1, len(clean_t4)):
            cur_t = clean_t4[idx_t]
            cur_s = (int(cur_t[0]) + int(cur_t[1])) % 10
            if not (cur_t in d9 and cur_t in hs20_set and cur_s in sat_sums):
                for cand in fill_pool:
                    if cand in d9 and cand in hs20_set and ((int(cand[0])+int(cand[1]))%10 in sat_sums) and ((int(cand[0])+int(cand[1]))%10 in dow_top2_sums):
                        if cand not in clean_t4 and lrs.get_lot_lon(cand) not in clean_t4:
                            clean_t4[idx_t] = cand
                            break
        t4 = clean_t4[:4]

        # 4. Nâng cấp 4 lớp (Cầu Đôi 27 giải + Chu kỳ Kép Tầng Ngày/Tuần + Tam Giác Vàng G7 + Đảo chiều Đầu Lớn/Nhỏ):
        sc1_map = {f"{i:02d}": _cand_sat_dow_score(f"{i:02d}") for i in range(100)}
        sc2_map, cross_g7_today = _compute_4_fixes_scores(draws, target_draw_idx)

        d9_ranked = sorted(d9, key=lambda x: max(sc1_map.get(x, 0), sc1_map.get(calc_lot_lon(x), 0)), reverse=True)
        top_d9 = d9_ranked[0] if d9_ranked else bt
        top_d9_sc = max(sc1_map.get(top_d9, 0), sc1_map.get(calc_lot_lon(top_d9), 0))

        ranked_c2 = [x[0] for x in sorted(sc2_map.items(), key=lambda x: x[1], reverse=True)]
        c2_strong = [
            x for x in ranked_c2
            if x in dow_giao_thoa_set and x in cap4_set
            and ((int(x[0]) + int(x[1])) % 10 in sat_sums)
            and x != cur_de and x[0] != x[1]
        ]

        # Khử bẫy tự cộng điểm trùng G7 hôm nay (Same-G7 Today Trap) trên Bạch Thủ và đôn ứng viên Tam Giác Vàng G7 đỉnh cao
        if sc2_map.get(bt, 0) < 275.0 and top_d9_sc >= 480.0:
            r_top = calc_lot_lon(top_d9)
            bt = r_top if sc1_map.get(r_top, 0) > sc1_map.get(top_d9, 0) else top_d9
        elif c2_strong and (bt not in cross_g7_today) and (c2_strong[0] in cross_g7_today) and sc2_map.get(c2_strong[0], 0) >= 595.0 and 385.0 <= sc1_map.get(bt, 0) < 400.0:
            bt = c2_strong[0]

        # Tinh chỉnh Tứ Thủ Top 4 theo xếp hạng thực (Zero Alphabetical Bias)
        new_t4 = [bt]
        for x in t4:
            if len(new_t4) >= 4:
                break
            if x not in new_t4 and calc_lot_lon(x) not in new_t4:
                new_t4.append(x)
        for high_d in d9_ranked[:2]:
            h_sc = max(sc1_map.get(high_d, 0), sc1_map.get(calc_lot_lon(high_d), 0))
            if h_sc >= 480.0 and high_d not in new_t4 and calc_lot_lon(high_d) not in new_t4 and len(new_t4) >= 2:
                weak_idx = min(range(1, len(new_t4)), key=lambda i: max(sc1_map.get(new_t4[i], 0), sc1_map.get(calc_lot_lon(new_t4[i]), 0)))
                w_sc = max(sc1_map.get(new_t4[weak_idx], 0), sc1_map.get(calc_lot_lon(new_t4[weak_idx]), 0))
                if h_sc > w_sc + 20.0:
                    new_t4[weak_idx] = high_d

        if c2_strong and len(new_t4) >= 2:
            top_c2 = c2_strong[0]
            if sc2_map.get(top_c2, 0) >= 520.0 and top_c2 not in new_t4 and calc_lot_lon(top_c2) not in new_t4:
                weak_idx = min(range(1, len(new_t4)), key=lambda i: max(sc1_map.get(new_t4[i], 0), sc1_map.get(calc_lot_lon(new_t4[i]), 0)))
                w_sc = max(sc1_map.get(new_t4[weak_idx], 0), sc1_map.get(calc_lot_lon(new_t4[weak_idx]), 0))
                if w_sc < 395.0:
                    new_t4[weak_idx] = top_c2
        t4 = new_t4[:4]

        # Tinh chỉnh Dàn 9 Số: Giữ 7 trụ cột điểm cao nhất của d9_ranked + bổ sung 2 đỉnh Tam Giác Vàng G7 & Cầu Đôi 27 giải
        new_d9 = []
        for x in [bt] + d9_ranked[:7]:
            if x not in new_d9 and calc_lot_lon(x) not in new_d9:
                new_d9.append(x)
            if len(new_d9) >= 7:
                break
        for x in c2_strong + d9_ranked:
            if len(new_d9) >= 9:
                break
            if x not in new_d9 and calc_lot_lon(x) not in new_d9:
                new_d9.append(x)
        d9 = sorted(new_d9[:9])

        # 5. Nâng cấp Cầu Đồng Giải / Sát Vách (Adjacent Same-Prize Bridge) & Cơ chế Giao Thoa Phân Tầng (Tiered Union + Intersection):
        a_bridges = analyze_bridge_cycles(draws, target_draw_idx)
        adj_scores = Counter()
        if a_bridges:
            for h_b in a_bridges['head_positions']:
                hp_code = h_b['position'].split()[0]
                hp_idx = int(h_b['position'].split()[-1])
                for t_b in a_bridges['tail_positions']:
                    tp_code = t_b['position'].split()[0]
                    tp_idx = int(t_b['position'].split()[-1])
                    if hp_code == tp_code and abs(hp_idx - tp_idx) == 1:
                        cand_adj = f"{h_b['digit']}{t_b['digit']}"
                        w_adj = (h_b['cycle_days'] * 1.6 + t_b['cycle_days'] * 1.4) * 1.5
                        if h_b.get('is_direct') and t_b.get('is_direct'):
                            w_adj += 4.5
                        elif h_b.get('is_direct') or t_b.get('is_direct'):
                            w_adj += 2.0
                        if hp_code.startswith(('GDB', 'G1', 'G5.4', 'G5.5', 'G7')):
                            w_adj += 3.0
                        adj_scores[cand_adj] += w_adj

        union_sums = set(sat_sums) | set(dow_top2_sums)
        inter_sums = set(sat_sums) & set(dow_top2_sums)
        d9_cur_set = set(d9)
        valid_adj = []
        for cand_adj, w_sc in adj_scores.items():
            if cand_adj == cur_de or cand_adj[0] == cand_adj[1]:
                continue
            rev_adj = calc_lot_lon(cand_adj)
            csum_adj = (int(cand_adj[0]) + int(cand_adj[1])) % 10
            if (cand_adj in cap4_set or rev_adj in cap4_set) and (csum_adj in union_sums or cand_adj in dow_giao_thoa_set or rev_adj in dow_giao_thoa_set):
                total_w = w_sc * 10.0
                if csum_adj in inter_sums:
                    total_w += 35.0
                elif csum_adj in dow_top2_sums:
                    total_w += 25.0
                elif csum_adj in sat_sums:
                    total_w += 20.0
                if cand_adj in dow_giao_thoa_set or rev_adj in dow_giao_thoa_set:
                    total_w += 30.0
                if cand_adj in cap4_set:
                    total_w += 15.0
                if cand_adj in d9_cur_set or rev_adj in d9_cur_set:
                    total_w += 35.0
                valid_adj.append((cand_adj, total_w, w_sc))
        valid_adj.sort(key=lambda x: x[1], reverse=True)

        # Khi tập Tổng G7 Thứ 7 và Tổng G7 Thứ Mạnh Nhất không giao nhau (inter_sums rỗng), ưu tiên số #1 Cầu Sát Vách Cùng Giải (total_w >= 210) lên Bạch Thủ:
        if not inter_sums and valid_adj and valid_adj[0][1] >= 210.0:
            bt = valid_adj[0][0]

        adj_top = []
        seen_adj = set()
        for cand_adj, tw_adj, _ in valid_adj:
            rev_adj = calc_lot_lon(cand_adj)
            if cand_adj not in seen_adj and rev_adj not in seen_adj:
                adj_top.append((cand_adj, tw_adj))
                seen_adj.add(cand_adj)
                seen_adj.add(rev_adj)
            if len(adj_top) >= 2:
                break

        final_t4 = [bt]
        for x in t4:
            if len(final_t4) >= 4:
                break
            if x not in final_t4 and calc_lot_lon(x) not in final_t4:
                final_t4.append(x)
        if adj_top and len(final_t4) >= 2:
            acand, atw = adj_top[0]
            if acand not in final_t4 and calc_lot_lon(acand) not in final_t4 and atw >= 165.0:
                weak_idx = min(range(1, len(final_t4)), key=lambda i: max(sc1_map.get(final_t4[i], 0), sc1_map.get(calc_lot_lon(final_t4[i]), 0)))
                if max(sc1_map.get(final_t4[weak_idx], 0), sc1_map.get(calc_lot_lon(final_t4[weak_idx]), 0)) < 435.0:
                    final_t4[weak_idx] = acand
        t4 = final_t4[:4]

        d9_ranked_now = sorted(d9, key=lambda x: max(sc1_map.get(x, 0), sc1_map.get(calc_lot_lon(x), 0)), reverse=True)
        final_d9 = []
        for x in t4 + d9_ranked_now[:6] + [a[0] for a in adj_top if a[1] >= 140.0] + d9_ranked_now:
            if len(final_d9) >= 9:
                break
            if x not in final_d9 and calc_lot_lon(x) not in final_d9:
                final_d9.append(x)
        d9 = sorted(final_d9[:9])
    else:
        sc1_map = {f"{i:02d}": _cand_sat_dow_score(f"{i:02d}") for i in range(100)}
        sc2_map, _ = _compute_4_fixes_scores(draws, target_draw_idx)

    lot_lon = lrs.get_lot_lon(bt)
    song_thu = [bt, lot_lon] if lot_lon and lot_lon != bt else [bt]
    d9_dao = [s[1] + s[0] for s in d9 if len(s) == 2 and s[0] != s[1]]
    d9_all = sorted(list(set(d9) | set(d9_dao) | set(t4) | {calc_lot_lon(x) for x in t4 if len(x) == 2 and x[0] != x[1]}))

    return {
        'top_1': bt,
        'lot_lon': lot_lon,
        'song_thu': song_thu,
        'top_4': t4,
        'dan_9_so': d9,
        'dan_9_dao': d9_dao,
        'dan_9_all': d9_all,
        'head_digits': base_res.get('head_digits', []),
        'tail_digits': base_res.get('tail_digits', []),
        'dow_ha_so_list': dow_ha_so_list,
        'dow_giao_thoa_set': dow_giao_thoa_set,
        'sat_sums': sorted(list(sat_sums)),
        'dow_top2_sums': sorted(list(dow_top2_sums)),
        'dow_rank_keys': dow_rank_keys,
        'cap4_list': cap4_list,
        'found_list': base_res.get('found_list', []),
        'cand_score_map': {f"{i:02d}": round(sc1_map[f"{i:02d}"] + sc2_map.get(f"{i:02d}", 0.0) * 0.25, 2) for i in range(100)}
    }

def build_dynamic_radar_sets(unique_numbers_map, ai_scores, gan_dict, g7_bonus_map, corner_bt, prev_de_val, prev_prev_de_val, n2_target_count=42, n3_target_count=40, conv_res=None):
    """
    Hệ thống chấm điểm Hội Tụ Toàn Diện (Consensus Scoring) kết hợp Tổng G7 Thứ 7 & Thứ Mạnh Nhất (67_up_95):
    1. Top 1 Bạch Thủ, Song Thủ (Số Đảo), Top 4 Tứ Thủ, Dàn 9 Số & Dàn Số Đảo lấy từ lõi hội tụ G7 Thứ 7 + Thứ Mạnh Nhất + Radar 27 giải.
    2. Dàn N1 (60 số): Khung 60 số Cấp 4 chuẩn kết hợp các số chủ lực.
    3. Dàn Tinh Túy Ngày 1 (~44 số): Giao thoa điểm cao nhất trong Khung 60 số + Top 4 Tứ Thủ + Song Thủ + Dàn 9 Số.
    4. Dàn N2 (42 số) & Dàn N3 (40 số): Lọc hạ dàn cứu khung ngày 2, ngày 3.
    """
    base_60_list = [f"{x:02d}" for x in sorted(DEFAULT_60_CAP4)]
    cap4_base_set = set(base_60_list)
    bet_2_days = {prev_de_val} if (prev_de_val and prev_de_val == prev_prev_de_val) else set()

    conv_sc_map = conv_res.get('cand_score_map', {}) if conv_res else {}
    dow_hs_set = set(conv_res.get('dow_ha_so_list', [])) if conv_res else set()
    dow_gt_set = set(conv_res.get('dow_giao_thoa_set', [])) if conv_res else set()

    all_100_scored = {}
    for i in range(100):
        n_str = f"{i:02d}"
        info = unique_numbers_map.get(n_str)
        radar_sc = info['score'] if info else 0.0
        cycle = info['cycle_days'] if info else 0
        ai_sc = ai_scores.get(n_str, 5.0)
        g7_sc = g7_bonus_map.get(n_str, 0.0)
        base_bonus = 22.0 if n_str in cap4_base_set else 0.0
        conv_bonus = max(0.0, conv_sc_map.get(n_str, 0.0) * 0.35)

        total_sc = round(radar_sc + ai_sc * 9.0 + g7_sc + base_bonus + conv_bonus, 1)
        all_100_scored[n_str] = {
            'num': n_str,
            'cycle_days': cycle,
            'radar_score': radar_sc,
            'ai_score': ai_sc,
            'g7_bonus': g7_sc,
            'final_score': total_sc,
            'in_cap4_base': (n_str in cap4_base_set)
        }

    if conv_res and conv_res.get('top_1'):
        top_1 = conv_res['top_1']
        lot_lon = conv_res['lot_lon']
        song_thu = conv_res['song_thu']
        top_4_nums = conv_res['top_4']
        dan_9_so = conv_res['dan_9_so']
        dan_9_dao = conv_res['dan_9_dao']
        dan_9_all = conv_res['dan_9_all']
    else:
        found_list = [all_100_scored[n] for n in unique_numbers_map.keys()]
        chidao_pool = [x for x in found_list if x['cycle_days'] >= 3]
        if len(chidao_pool) < 4:
            chidao_pool = [x for x in found_list if x['cycle_days'] >= 2]
        selection_pool = chidao_pool if len(chidao_pool) >= 4 else found_list
        selection_pool.sort(key=lambda x: (x['cycle_days'], x['final_score']), reverse=True)

        top_1 = selection_pool[0]['num'] if selection_pool else (corner_bt or '65')
        lot_lon = calc_lot_lon(top_1)
        song_thu = [top_1, lot_lon] if lot_lon != top_1 else [top_1]

        top_4_nums = [top_1]
        if lot_lon not in top_4_nums:
            top_4_nums.append(lot_lon)
        for x in selection_pool:
            if x['num'] not in top_4_nums:
                top_4_nums.append(x['num'])
            if len(top_4_nums) >= 4:
                break
        dan_9_so = top_4_nums[:4]
        dan_9_dao = [calc_lot_lon(x) for x in dan_9_so if x[0] != x[1]]
        dan_9_all = sorted(list(set(dan_9_so) | set(dan_9_dao)))

    # Đảm bảo Dàn N1 bao gồm đầy đủ Top 4, Song Thủ và Dàn 9 Số
    n1_union = set(base_60_list) | set(top_4_nums) | set(song_thu) | set(dan_9_so)
    dan_n1_list = sorted(list(n1_union))

    # 2. Dàn Tinh Túy Ngày 1: Lấy Top 44 số điểm hội tụ cao nhất trong Khung N1 + đặc cách Top 4 Tứ Thủ & Song Thủ
    cap4_scored = []
    for n_str in base_60_list:
        c_sc = all_100_scored[n_str]['final_score']
        if n_str in top_4_nums or n_str in song_thu:
            c_sc += 1000.0
        elif n_str in dan_9_all:
            c_sc += 400.0
        elif n_str in dow_hs_set:
            c_sc += 200.0
        elif n_str in dow_gt_set:
            c_sc += 80.0
        cap4_scored.append((n_str, c_sc))
    cap4_scored.sort(key=lambda x: x[1], reverse=True)
    tinhtuy_set = {x[0] for x in cap4_scored[:44]} | set(top_4_nums) | set(song_thu)
    dan_ngay1_tinhtuy = sorted(list(tinhtuy_set))

    # 3. Dàn N2 (42 số) & Dàn N3 (40 số) chuẩn cứu khung
    base_n2_pool = [
        11, 12, 13, 15, 17, 18, 19, 21, 22, 23, 28, 29, 31, 32, 33, 35, 37, 38,
        42, 44, 45, 51, 52, 53, 55, 58, 59, 61, 62, 63, 65, 66, 67, 68, 81, 82,
        83, 85, 87, 90, 95, 98
    ]
    n2_candidates_set = (set(f"{x:02d}" for x in base_n2_pool) | set(dan_n1_list)) - bet_2_days
    n2_candidates_filtered = sorted(
        list(n2_candidates_set),
        key=lambda x: (all_100_scored[x]['final_score'], 1 if x in cap4_base_set else 0),
        reverse=True
    )
    dan_n2_list = sorted(n2_candidates_filtered[:n2_target_count])

    n3_candidates = [n for n in dan_n2_list if gan_dict.get(n, 0) <= 45]
    for n in dan_n2_list:
        if len(n3_candidates) >= n3_target_count:
            break
        if n not in n3_candidates:
            n3_candidates.append(n)
    n3_candidates.sort(key=lambda x: all_100_scored[x]['final_score'], reverse=True)
    dan_n3_list = sorted(n3_candidates[:n3_target_count])

    dan_lot_list = [x for x in dan_n1_list if x != top_1 and x not in top_4_nums]
    return {
        'top_1': top_1,
        'lot_lon': lot_lon,
        'song_thu': song_thu,
        'top_4': top_4_nums,
        'dan_9_so': dan_9_so,
        'dan_9_dao': dan_9_dao,
        'dan_9_all': dan_9_all,
        'dan_tinhtuy': dan_ngay1_tinhtuy,
        'dan_n1': dan_n1_list,
        'dan_n2': dan_n2_list,
        'dan_n3': dan_n3_list,
        'dan_lot': dan_lot_list,
        'all_100_scored': all_100_scored
    }

def extract_g7_consensus_bonus(cur_draw):
    """
    Trích xuất điểm thưởng đồng thuận từ Giải 7 (G7.1..G7.4) và Cầu Ghép Góc G7.1[0]+G7.4[1]
    của kỳ vừa quay xong để gia cố độ chuẩn xác cho Radar Tĩnh.
    """
    bonus_map = Counter()
    prizes = cur_draw.get('prizes', {})
    g7_vals = [str(prizes.get(f'G7.{i}', '')).strip() for i in range(1, 5)]
    g7_digits = set()
    g7_sums = set()
    for val in g7_vals:
        if len(val) == 2 and val.isdigit():
            d1, d2 = int(val[0]), int(val[1])
            g7_digits.update([str(d1), str(d2), str(BONG_DUONG[d1]), str(BONG_DUONG[d2])])
            s = (d1 + d2) % 10
            g7_sums.update([s, BONG_DUONG[s]])

    # Cầu Ghép Góc kinh điển: G7.1[0] + G7.4[1]
    g7_1 = g7_vals[0] if len(g7_vals) >= 1 else ''
    g7_4 = g7_vals[3] if len(g7_vals) >= 4 else ''
    corner_bt = None
    if len(g7_1) == 2 and len(g7_4) == 2 and g7_1.isdigit() and g7_4.isdigit():
        corner_bt = f"{g7_1[0]}{g7_4[1]}"
        corner_rev = calc_lot_lon(corner_bt)
        bonus_map[corner_bt] += 35.0
        bonus_map[corner_rev] += 25.0

    for i in range(100):
        n_str = f"{i:02d}"
        s = (int(n_str[0]) + int(n_str[1])) % 10
        if n_str[0] in g7_digits and n_str[1] in g7_digits:
            bonus_map[n_str] += 18.0
        elif n_str[0] in g7_digits or n_str[1] in g7_digits:
            bonus_map[n_str] += 8.0
        if s in g7_sums:
            bonus_map[n_str] += 12.0

    return bonus_map, corner_bt

def run_pipeline(target_draw_idx=0, cap4_csv=DEFAULT_CAP4_CSV, custom_cap4=None, n2_size=None, n3_size=None, is_live=False, send_tele=False):
    """
    Thực thi toàn bộ pipeline Radar Tĩnh Toàn Diện (Quét đủ 27 giải từ G.ĐB -> G7 = 107 vị trí):
    - Dùng kỳ vừa quay xong (draws[target_draw_idx]) và lịch sử trước đó để dò các vị trí cầu Đầu & Đuôi
      đã ăn thông vào Đề kỳ vừa quay xong.
    - Lọc giữ các vị trí Cầu Đầu & Cầu Đuôi tinh nhuệ (ăn thông >= 2 ngày hoặc chính diện giải trọng tâm).
    - Lấy luôn các chữ số tại đúng vị trí đó trên bảng 27 giải của kỳ vừa quay xong để ghép số
      chốt dự đoán cho NGÀY HÔM SAU (N+1) tương tự như dàn động.
    - Trên bảng Radar: Chỉ tô màu của Cầu Đầu (Vàng) và Cầu Đuôi (Xanh).
    """
    print("\n" + "=" * 82)
    print("   XSMB AI - RADAR TĨNH TOÀN DIỆN (G.ĐB -> G7 | 107 VỊ TRÍ) DỰ ĐOÁN NGÀY HÔM SAU")
    print("=" * 82)
    
    raw_draws = get_combined_draws(is_live=False)
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

    all_head_positions = analysis['head_positions']
    all_tail_positions = analysis['tail_positions']
    head_positions = select_core_bridge_positions(all_head_positions)
    tail_positions = select_core_bridge_positions(all_tail_positions)
    head_positions = select_core_bridge_positions(all_head_positions, all_tail_positions)
    tail_positions = select_core_bridge_positions(all_tail_positions, all_head_positions)

    print("\n" + "-" * 82)
    print(f" BƯỚC 1: ĐỀ VỪA NỔ [{analysis['cur_date']}] & TẬP CHẠM ĐẦU / ĐUÔI DÒ CẦU")
    print("-" * 82)
    print(f"  • Đề vừa nổ kỳ N: {analysis['cur_de']} (Giải ĐB: {analysis['cur_db']})")
    print(f"  • Chạm Đầu = {analysis['head']}  --> Bóng dương = {analysis['head_bong']}  ==> Tập Đầu: [{analysis['head']}, {analysis['head_bong']}]")
    print(f"  • Chạm Đuôi = {analysis['tail']}  --> Bóng dương = {analysis['tail_bong']}  ==> Tập Đuôi: [{analysis['tail']}, {analysis['tail_bong']}]")

    print("\n" + "-" * 82)
    print(f" BƯỚC 2 & 3: QUÉT 107 VỊ TRÍ (G.ĐB -> G7.4) & LỌC CẦU TINH NHUỆ CHO [{next_date_full}]")
    print("-" * 82)
    print(f"  • Vị trí Cầu Đầu tinh nhuệ (🟡): {len(head_positions)} vị trí (từ {len(all_head_positions)} vị trí chạm)")
    print(f"      - Chạy 3-4+ ngày (Chỉ đạo): {sum(1 for x in head_positions if x['cycle_days'] >= 3)} vị trí")
    print(f"      - Chạy 2 ngày (Đôn N3):     {sum(1 for x in head_positions if x['cycle_days'] == 2)} vị trí")
    print(f"  • Vị trí Cầu Đuôi tinh nhuệ (🔵): {len(tail_positions)} vị trí (từ {len(all_tail_positions)} vị trí chạm)")
    print(f"      - Chạy 3-4+ ngày (Chỉ đạo): {sum(1 for x in tail_positions if x['cycle_days'] >= 3)} vị trí")
    print(f"      - Chạy 2 ngày (Đôn N3):     {sum(1 for x in tail_positions if x['cycle_days'] == 2)} vị trí")

    # BƯỚC 4: Vào dàn (Ghép các con số từ các vị trí Cầu Đầu tinh nhuệ x Cầu Đuôi tinh nhuệ)
    all_pairs = []
    for h in head_positions:
        for t in tail_positions:
            c_main = h['digit']
            d_main = t['digit']
            c_bong = h['digit_bong']
            d_bong = t['digit_bong']

            if h.get('is_direct') and t.get('is_direct') and (h['cycle_days'] >= 2 or t['cycle_days'] >= 2):
                pair_cycle = max(3, h['cycle_days'], t['cycle_days'])
            elif h['cycle_days'] >= 2 and t['cycle_days'] >= 2:
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
                    cat_label = "Theo dõi ngày 1 (Chính diện)"

                direct_bonus = 40.0 if (h.get('is_direct') and t.get('is_direct')) else (15.0 if (h.get('is_direct') or t.get('is_direct')) else 0)
                score = pair_cycle * 30 + weight * 20 + direct_bonus + pos_bonus + (h['cycle_days'] + t['cycle_days']) * 6

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

    # Nhóm theo con số (loại trùng, giữ chu kỳ và điểm cao nhất + cộng thưởng độ hội tụ)
    freq_pairs = Counter(p['num'] for p in all_pairs)
    unique_numbers_map = {}
    for p in all_pairs:
        n = p['num']
        total_sc = p['score'] + min(freq_pairs[n] * 4.0, 32.0)
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

    # Chấm điểm AI Score hỗ trợ lọc hội tụ (dùng đủ 90 kỳ + lịch sử data_2026.json nếu có)
    all_draws_for_ai = list(draws)
    if os.path.exists('data_2026.json'):
        try:
            with open('data_2026.json', encoding='utf-8') as f:
                d_2026 = json.load(f)
                existing_dates = {d.get('date', '').split()[-1] for d in all_draws_for_ai}
                for d_old in d_2026:
                    d_key = d_old.get('date', '').split()[-1]
                    if d_key and d_key not in existing_dates:
                        all_draws_for_ai.append(d_old)
                        existing_dates.add(d_key)
        except Exception:
            pass

    ai_scores, gan_dict, prev_de_val, prev_prev_de_val = compute_ai_scores(all_draws_for_ai, target_draw_idx, unique_numbers_map)
    g7_bonus_map, corner_bt = extract_g7_consensus_bonus(cur_draw)

    weekly_cycle = get_weekly_cycle_mode(next_date_full)
    n2_target_count = n2_size if n2_size is not None else weekly_cycle['n2_count']
    n3_target_count = n3_size if n3_size is not None else weekly_cycle['n3_count']

    conv_res = compute_static_g7_radar_convergence(draws, target_draw_idx)
    radar_sets = build_dynamic_radar_sets(
        unique_numbers_map, ai_scores, gan_dict, g7_bonus_map, corner_bt,
        prev_de_val, prev_prev_de_val, n2_target_count=n2_target_count, n3_target_count=n3_target_count,
        conv_res=conv_res
    )

    top_1 = radar_sets['top_1']
    lot_lon = radar_sets['lot_lon']
    song_thu = radar_sets['song_thu']
    top_4_nums = radar_sets['top_4']
    dan_9_so_calc = radar_sets['dan_9_so']
    dan_9_dao_calc = radar_sets['dan_9_dao']
    dan_9_all_calc = radar_sets['dan_9_all']
    dan_ngay1_tinhtuy = radar_sets['dan_tinhtuy']
    dan_n1_list = radar_sets['dan_n1']
    dan_n2_list = radar_sets['dan_n2']
    dan_n3_list = radar_sets['dan_n3']
    dan_lot_list = radar_sets['dan_lot']
    dan_lot_display = [f"{x} (lót)" for x in dan_lot_list]
    all_100_scored = radar_sets['all_100_scored']

    # Đồng bộ 100% các số chủ lực (Bạch Thủ, Song Thủ, Tứ Thủ, Dàn 9 Số & Số Đảo) vào bảng found_numbers (table_5cols)
    core_union_nums = list(dict.fromkeys([top_1, lot_lon] + list(top_4_nums) + list(dan_9_so_calc) + list(dan_9_dao_calc)))
    for c_num in core_union_nums:
        if c_num and len(c_num) == 2 and c_num not in unique_numbers_map:
            best_h = next((p for p in all_head_positions if c_num[0] in (p['digit'], p['digit_bong'])), None)
            best_t = next((p for p in all_tail_positions if c_num[1] in (p['digit'], p['digit_bong'])), None)
            c_cyc = best_h['cycle_days'] if best_h else 2
            d_cyc = best_t['cycle_days'] if best_t else 2
            p_cyc = max(c_cyc, d_cyc)
            new_item = {
                'num': c_num,
                'c_digit': c_num[0],
                'd_digit': c_num[1],
                'c_cycle': c_cyc,
                'd_cycle': d_cyc,
                'cycle_days': p_cyc,
                'category': "Chỉ đạo" if p_cyc >= 3 else "Lót",
                'cat_label': f"✅ CHỈ ĐẠO ({p_cyc} ngày)" if p_cyc >= 3 else "Hội tụ Tổng G7 Thứ 7 & Thứ Mạnh Nhất",
                'weight': 1.0,
                'combo_type': "chính diện",
                'score': all_100_scored.get(c_num, {}).get('final_score', 150.0),
                'h_pos': best_h['position'] if best_h else "Cầu G7 Thứ 7",
                't_pos': best_t['position'] if best_t else "Cầu Thứ Mạnh Nhất"
            }
            unique_numbers_map[c_num] = new_item
            found_numbers.append(new_item)

    for item in found_numbers:
        n = item['num']
        item['ai_score'] = ai_scores.get(n, 5.0)
        item['g7_bonus'] = g7_bonus_map.get(n, 0.0)
        item['final_score'] = all_100_scored.get(n, {}).get('final_score', item['score'])
        item['in_cap4'] = (n in dan_n1_list)
        item['in_cap4_str'] = "Có" if item['in_cap4'] else "Không"
        if n == top_1:
            item['top_rank'] = "👑 Top 1 (Bạch thủ)"
        elif n == lot_lon and n not in top_4_nums:
            item['top_rank'] = "🛡️ Top 2 (Số đảo BT)"
        elif n in top_4_nums:
            item['top_rank'] = "🔥 Top 4 (Tứ thủ)"
        elif n in dan_9_so_calc:
            item['top_rank'] = "⭐ Top 9 (Dàn 9 số)"
        elif n in dan_9_dao_calc:
            item['top_rank'] = "🔄 Số Đảo (Dàn 9 đảo)"
        elif n in dan_ngay1_tinhtuy:
            item['top_rank'] = "💎 Tinh Túy N1"
        elif item['in_cap4']:
            item['top_rank'] = "🛡️ Lót hợp lệ"
        else:
            item['top_rank'] = "❌ Loại bỏ (Ngoài 60s)"

    def sort_key(x):
        tier = 0
        if "Top 1" in x['top_rank']: tier = 4
        elif "Top 4" in x['top_rank']: tier = 3
        elif "Lót hợp lệ" in x['top_rank']: tier = 2
        else: tier = 1
        if "Top 1" in x['top_rank']: tier = 7
        elif "Top 2" in x['top_rank']: tier = 6
        elif "Top 4" in x['top_rank']: tier = 5
        elif "Top 9" in x['top_rank']: tier = 4
        elif "Số Đảo" in x['top_rank']: tier = 3
        elif "Tinh Túy" in x['top_rank']: tier = 2
        elif "Lót hợp lệ" in x['top_rank']: tier = 1
        else: tier = 0
        return (tier, x['cycle_days'], x.get('final_score', 0))

    found_numbers.sort(key=sort_key, reverse=True)

    print("\n" + "=" * 82)
    print(f" KẾT QUẢ CHỐT SỚM DỰ ĐOÁN CHO KỲ TIẾP THEO [{next_date_full}]")
    print("=" * 82)
    if top_1:
        t1_info = unique_numbers_map.get(top_1, {})
        print(f"  👑 TOP 01 BẠCH THỦ: [{top_1}] | 🛡️ SỐ ĐẢO (LÓT LỘN): [{lot_lon}] ==> CẶP SONG THỦ: [{top_1} - {lot_lon}]")
        print(f"     -> Hội tụ Tổng G7 Thứ 7 {conv_res.get('sat_sums', []) if conv_res else []} × Thứ Mạnh Nhất {conv_res.get('dow_top2_sums', []) if conv_res else []}")
    print(f"  🔥 TOP 04 TỨ THỦ TINH TÚY: {top_4_nums}")
    print(f"  ⭐ DÀN 09 SỐ CHỦ LỰC:     {dan_9_so_calc}")
    print(f"  🔄 DÀN SỐ ĐẢO (BẢO HIỂM): {dan_9_dao_calc}")
    print(f"  💎 DÀN TINH TÚY GIAO THOA 60 SỐ CẤP 4 ({len(dan_ngay1_tinhtuy)} số): {dan_ngay1_tinhtuy}")
    print(f"  🔵 DÀN SỐ LÓT N1 ({len(dan_lot_list)} số): {dan_lot_list[:15]} ...")

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

    # BẢNG MA TRẬN TÔ MÀU VỊ TRÍ CẦU TRÊN RADAR (CHỈ TÔ MÀU ĐẦU VÀ ĐUÔI TINH NHUỆ):
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

    top_dau_digits = conv_res.get('head_digits', []) if conv_res else []
    top_duoi_digits = conv_res.get('tail_digits', []) if conv_res else []
    top_dau_list = [f"Đầu {d}" for d in top_dau_digits[:3]]
    top_duoi_list = [f"Đuôi {d}" for d in top_duoi_digits[:3]]

    # Tính Càng 3D dự đoán cho ngày hôm sau
    cang_3d_info = calc_cang_3d_static(cur_draw, top_1, top_4_nums, dan_9_so_calc)

    tinh_status_text = f"ĐANG HIỆU LỰC CHO KỲ TỚI (CHỐT SỚM TỪ KẾT QUẢ KỲ {cur_draw['date'].split()[-1]})"

    dan_cap2_38so = dan_ngay1_tinhtuy

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
        'dan_9_dao': dan_9_dao_calc,
        'dan_9_all': dan_9_all_calc,
        'top_dau': top_dau_list,
        'top_duoi': top_duoi_list,
        'sat_sums': conv_res.get('sat_sums', []) if conv_res else [],
        'dow_top2_sums': conv_res.get('dow_top2_sums', []) if conv_res else [],
        'dan_cap2_38so': dan_cap2_38so,
        'dan_60_cap4': dan_n1_list
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
        'dan_9_dao': dan_9_dao_calc,
        'dan_9_all': dan_9_all_calc,
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
        'dan_dao': dan_9_dao_calc if dan_9_dao_calc else ([lot_lon] if lot_lon else []),
        'dan_tinh_4cap': dan_tinh_4cap
    }
    
    if target_draw_idx == 0:
        with open('ket_qua_soi_cau_g1_g5.json', 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n[*] Đã lưu toàn bộ kết quả Radar G.ĐB->G7 vào: ket_qua_soi_cau_g1_g5.json")

        branch_dir = '58_up_to_75'
        if os.path.exists(branch_dir):
            branch_json_path = os.path.join(branch_dir, 'ket_qua_soi_cau_g1_g5.json')
            with open(branch_json_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"[*] Đã đồng bộ sang: {branch_json_path}")

        if len(draws) >= 3:
            prev_pred = analyze_and_verify_single_draw(draws, pred_for_idx=0)
            if prev_pred:
                ghi_lich_su_truc_tiep(
                    cur_draw['date'], cur_actual_de,
                    prev_pred['top_1'], prev_pred['top_4'], prev_pred['dan_lot'],
                    song_thu_list=prev_pred.get('song_thu'),
                    dan_9_list=prev_pred.get('dan_9_so'),
                    dan_9_dao_list=prev_pred.get('dan_9_dao')
                )
                ghi_lich_su_tinh_tuy(cur_draw['date'], cur_actual_de, prev_pred['dan_tinhtuy'])

        if send_tele:
            send_telegram_notification(output_data)

    return output_data

def analyze_and_verify_single_draw(draws, pred_for_idx=0, all_draws_for_ai=None):
    """
    Hàm tính bộ số dự đoán đã được chốt từ kỳ (pred_for_idx + 1) để đánh cho kỳ (pred_for_idx),
    nhằm đối chiếu trung thực 100% với Đề thực tế về ở kỳ (pred_for_idx) — tuyệt đối không dùng số ảo.
    """
    base_idx = pred_for_idx + 1
    if len(draws) <= base_idx + 1:
        return None
    analysis = analyze_bridge_cycles(draws, target_draw_idx=base_idx)
    if not analysis:
        return None

    cur_draw = draws[base_idx]
    head_positions = select_core_bridge_positions(analysis['head_positions'])
    tail_positions = select_core_bridge_positions(analysis['tail_positions'])
    head_positions = select_core_bridge_positions(analysis['head_positions'], analysis['tail_positions'])
    tail_positions = select_core_bridge_positions(analysis['tail_positions'], analysis['head_positions'])

    all_pairs = []
    for h in head_positions:
        for t in tail_positions:
            c_main, d_main = h['digit'], t['digit']
            c_bong, d_bong = h['digit_bong'], t['digit_bong']
            if h.get('is_direct') and t.get('is_direct') and (h['cycle_days'] >= 2 or t['cycle_days'] >= 2):
                pair_cycle = max(3, h['cycle_days'], t['cycle_days'])
            elif h['cycle_days'] >= 2 and t['cycle_days'] >= 2:
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
                score = pair_cycle * 30 + weight * 20 + direct_bonus + pos_bonus + (h['cycle_days'] + t['cycle_days']) * 6
                all_pairs.append({'num': num_str, 'cycle_days': pair_cycle, 'score': score})

    freq_pairs = Counter(p['num'] for p in all_pairs)
    unique_map = {}
    for p in all_pairs:
        n = p['num']
        sc = p['score'] + min(freq_pairs[n] * 4.0, 32.0)
        if n not in unique_map or sc > unique_map[n]['score']:
            unique_map[n] = {'num': n, 'cycle_days': p['cycle_days'], 'score': sc}

    ai_source = all_draws_for_ai if all_draws_for_ai else draws
    ai_scores, gan_dict, prev_de_val, prev_prev_de_val = compute_ai_scores(ai_source, base_idx, unique_map)
    g7_bonus_map, corner_bt = extract_g7_consensus_bonus(cur_draw)
    conv_res = compute_static_g7_radar_convergence(draws, base_idx)

    weekly_cycle = get_weekly_cycle_mode(draws[pred_for_idx]['date'])
    radar_sets = build_dynamic_radar_sets(
        unique_map, ai_scores, gan_dict, g7_bonus_map, corner_bt,
        prev_de_val, prev_prev_de_val,
        n2_target_count=weekly_cycle['n2_count'], n3_target_count=weekly_cycle['n3_count'],
        conv_res=conv_res
    )

    top_1 = radar_sets['top_1']
    lot_lon = radar_sets['lot_lon']
    song_thu = radar_sets['song_thu']
    top_4 = radar_sets['top_4']
    dan_9_so = radar_sets['dan_9_so']
    dan_9_dao = radar_sets['dan_9_dao']
    dan_9_all = radar_sets['dan_9_all']
    dan_tinhtuy = radar_sets['dan_tinhtuy']
    dan_n1 = radar_sets['dan_n1']
    dan_n2 = radar_sets['dan_n2']
    dan_n3 = radar_sets['dan_n3']
    dan_lot = radar_sets['dan_lot']
    actual_de = draws[pred_for_idx].get('de', '')
    return {
        'top_1': top_1,
        'lot_lon': lot_lon,
        'song_thu': song_thu,
        'top_4': top_4,
        'dan_9_so': dan_9_so,
        'dan_9_dao': dan_9_dao,
        'dan_9_all': dan_9_all,
        'dan_tinhtuy': dan_tinhtuy,
        'dan_lot': dan_lot,
        'dan_n1': dan_n1,
        'dan_n2': dan_n2,
        'dan_n3': dan_n3,
        'actual_de': actual_de,
        'kq_khung': 'trung_n1' if actual_de in dan_n1 else ('trung_n2' if actual_de in dan_n2 else ('trung_n3' if actual_de in dan_n3 else 'truot_khung'))
    }

def send_telegram_notification(output_data):
    """
    Gửi thông báo kết quả kỳ vừa quay & Bảng chốt Radar (G.ĐB -> G7 + Tổng G7 Thứ 7 & Thứ Mạnh Nhất)
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
    dan_9_dao_str = ", ".join(output_data.get('dan_9_dao', []))
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
        f"• Tọa độ cầu (107 vị trí): 🟡 <b>{h_cnt} Cầu Đầu</b> × 🔵 <b>{t_cnt} Cầu Đuôi</b>",
        f"• Hội tụ: <b>Tổng G7 Thứ 7 + Thứ Mạnh Nhất (67_up_95)</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"🎯 <b>DỰ ĐOÁN CHỐT SỚM CHO: {next_date}</b>",
        f"👑 <b>BẠCH THỦ TOP 1:</b> <code>{top_1}</code>",
        f"🛡️ <b>SONG THỦ (KÈM SỐ ĐẢO):</b> <code>{song_thu_str}</code>",
        f"🔥 <b>TỨ THỦ TOP 4:</b> <code>{top_4_str}</code>",
        f"🔮 <b>CÀNG 3D CHỦ LỰC:</b> <code>{top3_cang_str}</code> (Ghép BT: <code>{cang_bt_str}</code>)",
        f"⭐ <b>DÀN 9 SỐ CHỦ LỰC:</b>",
        f"<code>{dan_9_str}</code>",
        f"🔄 <b>DÀN SỐ ĐẢO (9 SỐ LÓT LỘN):</b>",
        f"<code>{dan_9_dao_str}</code>",
        f"💎 <b>DÀN TINH TÚY NGÀY 1 ({len(dan_tinhtuy)} số):</b>",
        f"<code>{dan_tinhtuy_str}</code>",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        f"🌐 <a href='https://happiness2286-dot.github.io/logistic/soi_cau_g1_g5_app.html'>Mở App Xem Bảng Tô Màu Đầu/Đuôi & Tỷ Lệ Bạch Thủ/Tứ Thủ</a>"
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

def ghi_lich_su_truc_tiep(date_str, de_str, top1_val, top4_list, lot_list, song_thu_list=None, dan_9_list=None, dan_9_dao_list=None):
    """Ghi nhận lịch sử Radar G.ĐB->G7 (Bạch thủ, Song thủ/Đảo, Tứ thủ, Dàn 9 số & Số Đảo, Lót)"""
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
            bt_clean = str(top1_val).zfill(2) if top1_val else ""
            st_clean = [str(x).zfill(2) for x in (song_thu_list or ([bt_clean, calc_lot_lon(bt_clean)] if bt_clean else []))]
            t4_clean = [str(x).zfill(2) for x in (top4_list or [])]
            t4_dao_clean = [calc_lot_lon(x) for x in t4_clean if len(x) == 2 and x[0] != x[1]]
            t4_all_clean = list(set(t4_clean) | set(t4_dao_clean))
            d9_clean = [str(x).zfill(2) for x in (dan_9_list or [])]
            d9_dao_clean = [str(x).zfill(2) for x in (dan_9_dao_list or [calc_lot_lon(x) for x in d9_clean if len(x) == 2 and x[0] != x[1]])]
            d9_all_clean = list(set(d9_clean) | set(d9_dao_clean))
            lot_clean = [str(x).zfill(2) for x in (lot_list or [])]

            existing_idx = None
            for idx, item in enumerate(data['soi_truc_tiep'].get("lich_su", [])):
                if item.get("ngay") == clean_date:
                    existing_idx = idx
                    break

            hit_bt_exact = bool(bt_clean and de_clean == bt_clean)
            hit_st = bool(st_clean and de_clean in st_clean)
            hit_t4 = bool(hit_st or (t4_all_clean and de_clean in t4_all_clean))
            hit_d9 = bool(hit_t4 or (d9_all_clean and de_clean in d9_all_clean))

            if hit_bt_exact:
                kq_status = 'trung_bach_thu'
                note = f'👑 Trúng Bạch Thủ Top 1 [{de_clean}]'
            elif hit_st:
                kq_status = 'trung_bach_thu'
                note = f'🛡️ Trúng Số Đảo / Song Thủ [{de_clean}]'
            elif hit_t4:
                kq_status = 'trung_tu_thu'
                note = f'🔥 Trúng Tứ Thủ Top 4 [{de_clean}]'
            elif hit_d9:
                kq_status = 'trung_dan_9'
                note = f'⭐ Trúng Dàn 9 Số & Đảo [{de_clean}]'
            elif lot_clean and de_clean in lot_clean:
                kq_status = 'trung_lot'
                note = f'🛡️ Trúng Dàn Số Lót N1 [{de_clean}]'
            else:
                kq_status = 'truot_truc_tiep'
                note = 'Trượt kỳ quay ❌'

            entry = {
                "ngay": clean_date,
                "de": de_clean,
                "top1": bt_clean,
                "song_thu": st_clean,
                "top4": t4_clean,
                "dan_9": d9_clean,
                "dan_9_dao": d9_dao_clean,
                "hit_bt_exact": hit_bt_exact,
                "hit_song_thu": hit_st,
                "hit_tu_thu": hit_t4,
                "hit_dan_9": hit_d9,
                "ket_qua": kq_status,
                "ghi_chu": note
            }

            if existing_idx is not None:
                data['soi_truc_tiep']["lich_su"][existing_idx] = entry
            else:
                data['soi_truc_tiep']["lich_su"].insert(0, entry)

            data['soi_truc_tiep']["lich_su"] = data['soi_truc_tiep']["lich_su"][:60]

            tot = len(data['soi_truc_tiep']["lich_su"])
            c_bt_exact = sum(1 for x in data['soi_truc_tiep']["lich_su"] if x.get("hit_bt_exact"))
            c_bt = sum(1 for x in data['soi_truc_tiep']["lich_su"] if x.get("ket_qua") == "trung_bach_thu")
            c_tt = sum(1 for x in data['soi_truc_tiep']["lich_su"] if x.get("ket_qua") in ["trung_bach_thu", "trung_tu_thu"])
            c_d9 = sum(1 for x in data['soi_truc_tiep']["lich_su"] if x.get("ket_qua") in ["trung_bach_thu", "trung_tu_thu", "trung_dan_9"] or x.get("hit_dan_9"))
            c_lot = sum(1 for x in data['soi_truc_tiep']["lich_su"] if x.get("ket_qua") in ["trung_bach_thu", "trung_tu_thu", "trung_dan_9", "trung_lot"])

            data['soi_truc_tiep']["tong_quan"] = {
                "tong_ngay": tot,
                "trung_bach_thu_goc": c_bt_exact,
                "ty_le_bach_thu_goc": round(c_bt_exact / tot * 100, 1) if tot > 0 else 0,
                "trung_bach_thu": c_bt,
                "ty_le_bach_thu": round(c_bt / tot * 100, 1) if tot > 0 else 0,
                "trung_tu_thu": c_tt,
                "ty_le_tu_thu": round(c_tt / tot * 100, 1) if tot > 0 else 0,
                "trung_dan_9": c_d9,
                "ty_le_dan_9": round(c_d9 / tot * 100, 1) if tot > 0 else 0,
                "trung_lot": c_lot,
                "ty_le_lot": round(c_lot / tot * 100, 1) if tot > 0 else 0
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[*] Đã cập nhật lịch sử Radar G.ĐB->G7 vào: {file_path}")
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
    """
    Xóa sạch 100% lịch sử của phương án dàn động cũ và thống kê lại toàn bộ 60 ngày gần nhất
    (Phần 4A: Khung 3 ngày N1->N2->N3, Phần 4B: Radar Tĩnh G.ĐB->G7, Phần 4C: Dàn Tinh Túy Ngày 1)
    hoàn toàn từ dữ liệu thực tế 90 kỳ XSMB 27 giải (tuyệt đối không dùng số ảo).
    """
    raw_draws = get_combined_draws(is_live=False)
    draws = [d for d in raw_draws if d.get('de') and len(str(d.get('de', '')).strip()) >= 2]
    if len(draws) < 10:
        print("[!] Không đủ kỳ quay thực tế để thống kê lại lịch sử.")
        return

    all_draws_for_ai = list(draws)
    if os.path.exists('data_2026.json'):
        try:
            with open('data_2026.json', encoding='utf-8') as f:
                d_2026 = json.load(f)
                existing_dates = {d.get('date', '').split()[-1] for d in all_draws_for_ai}
                for d_old in d_2026:
                    d_key = d_old.get('date', '').split()[-1]
                    if d_key and d_key not in existing_dates:
                        all_draws_for_ai.append(d_old)
                        existing_dates.add(d_key)
        except Exception:
            pass

    # Reset sạch 100% lịch sử cũ của dàn động
    empty_data = {
        "khung_3_ngay": {"tong_quan": {}, "lich_su": []},
        "soi_truc_tiep": {"tong_quan": {}, "lich_su": []},
        "dan_tinh_tuy_ngay_1": {"tong_quan": {}, "lich_su": []}
    }
    for file_path in ['lich_su_phuong_phap.json', os.path.join('58_up_to_75', 'lich_su_phuong_phap.json')]:
        if os.path.exists(os.path.dirname(file_path) or '.'):
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(empty_data, f, ensure_ascii=False, indent=2)

    max_k = min(len(draws) - 5, 60)
    day_in_frame = 1
    frame_stt = 1
    active_n2 = []
    active_n3 = []

    for k in range(max_k - 1, -1, -1):
        pred = analyze_and_verify_single_draw(draws, pred_for_idx=k, all_draws_for_ai=all_draws_for_ai)
        if not pred:
            continue
        d_str = draws[k]['date']
        de_str = str(draws[k]['de']).zfill(2)

        # 1. Tính đúng chu kỳ nuôi Khung 3 Ngày thực tế (N1 -> N2 -> N3)
        if day_in_frame == 1:
            if de_str in pred['dan_n1']:
                ghi_lich_su_khung(d_str, de_str, 'trung_n1', frame_stt=frame_stt)
                frame_stt += 1
                day_in_frame = 1
            else:
                day_in_frame = 2
                active_n2 = pred['dan_n2']
                active_n3 = pred['dan_n3']
        elif day_in_frame == 2:
            n2_pool = active_n2 if active_n2 else pred['dan_n2']
            if de_str in n2_pool:
                ghi_lich_su_khung(d_str, de_str, 'trung_n2', frame_stt=frame_stt)
                frame_stt += 1
                day_in_frame = 1
            else:
                day_in_frame = 3
        else:
            n3_pool = active_n3 if active_n3 else pred['dan_n3']
            if de_str in n3_pool:
                ghi_lich_su_khung(d_str, de_str, 'trung_n3', frame_stt=frame_stt)
            else:
                ghi_lich_su_khung(d_str, de_str, 'truot_khung', frame_stt=frame_stt)
            frame_stt += 1
            day_in_frame = 1

        # 2. Ghi lịch sử Phần 4B (Radar Tĩnh G.ĐB -> G7)
        ghi_lich_su_truc_tiep(
            d_str, de_str, pred['top_1'], pred['top_4'], pred['dan_lot'],
            song_thu_list=pred.get('song_thu'),
            dan_9_list=pred.get('dan_9_so'),
            dan_9_dao_list=pred.get('dan_9_dao')
        )

        # 3. Ghi lịch sử Phần 4C (Dàn Tinh Túy Ngày 1 - 60 Ngày)
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
