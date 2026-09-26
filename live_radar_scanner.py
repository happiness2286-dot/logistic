# -*- coding: utf-8 -*-
"""
=============================================================================
XSMB AI RADAR SCANNER - QUÉT VỊ TRÍ G1 ĐẾN G5.6 & PHÂN TẦNG LIVE CHUẨN IPHONE 11
Tích hợp vào Dashboard 67_UP_95:
- Tự động cào live mỗi 5s (18h15 - 18h35) từ mketqua.net / xosodaiphat.com
- Quét 85 vị trí vật lý (G1 -> G5.6), tính chu kỳ ăn thông 1d, 2d, 3d, 4d
- Lọc giao thoa với Dàn 60 Số N1 Đã Kiểm Định
- Xuất Bảng Phân Tầng 5 Cột: Con Số - Vị Trí - Chu Kỳ - Trong N1? - Phân Hạng
- Quản lý Khung nuôi 3 ngày (N1: 60s, N2: 36s, N3: 36s) & Auto-Shift
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

# UTF-8 stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_LIBS = True
except ImportError:
    import urllib.request
    import urllib.parse
    HAS_LIBS = False

STATE_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'live_radar_state.json')
SUMMARY_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'analysis_summary.json')
MKETQUA_SO_KQ_URL = "https://mketqua.net/so-ket-qua"
MKETQUA_LIVE_URL = "https://mketqua.net/"

BONG_DUONG = {
    0: 5, 1: 6, 2: 7, 3: 8, 4: 9,
    5: 0, 6: 1, 7: 2, 8: 3, 9: 4
}

BONG_AM = {
    0: 7, 7: 0,
    1: 4, 4: 1,
    2: 9, 9: 2,
    3: 6, 6: 3,
    5: 8, 8: 5
}

def get_lot_lon(num_str):
    """Tính con số đảo (lót lộn) của Bạch thủ, nếu kép thì lót bóng kép."""
    if not num_str or len(num_str) < 2:
        return ""
    if num_str[0] != num_str[1]:
        return f"{num_str[1]}{num_str[0]}"
    d = int(num_str[0])
    b = BONG_DUONG.get(d, (d + 5) % 10)
    return f"{b}{b}"

def extract_target_sums(prev_draw):
    """Trích xuất tập Cầu Tổng G7 và Tổng Đề kỳ trước."""
    target_sums = set()
    if not prev_draw:
        return target_sums
    prev_de = prev_draw.get('de', '')
    if prev_de and len(prev_de) >= 2 and prev_de.isdigit():
        s_de = (int(prev_de[0]) + int(prev_de[1])) % 10
        target_sums.add(s_de)
        target_sums.add(BONG_DUONG.get(s_de, (s_de + 5) % 10))
    prizes = prev_draw.get('prizes', {})
    for k in ['G7.1', 'G7.2', 'G7.3', 'G7.4']:
        val = prizes.get(k, '')
        if val and len(val) >= 2 and val[-2:].isdigit():
            t = (int(val[-2]) + int(val[-1])) % 10
            target_sums.add(t)
            target_sums.add(BONG_DUONG.get(t, (t + 5) % 10))
    return target_sums

def calc_cang_3d(g1_val, prev_de, top_1, top_4, dan_9_so):
    """Bắt Top 3 Càng 3D từ Tâm Càng Giải Nhất (G1) + Bóng Dương/Bóng Âm + Tổng Đề Kỳ Trước."""
    scores = {i: 0 for i in range(10)}
    tam_g1 = -1
    dau_g1 = -1
    sum_de = -1

    if g1_val and len(g1_val) >= 5 and g1_val.isdigit():
        tam_g1 = int(g1_val[2])
        dau_g1 = int(g1_val[0])
        scores[tam_g1] += 45
        scores[BONG_DUONG.get(tam_g1, (tam_g1+5)%10)] += 35
        scores[BONG_AM.get(tam_g1, tam_g1)] += 25
        scores[dau_g1] += 15

    if prev_de and len(prev_de) >= 2 and prev_de.isdigit():
        sum_de = (int(prev_de[0]) + int(prev_de[1])) % 10
        scores[sum_de] += 35
        scores[BONG_DUONG.get(sum_de, (sum_de+5)%10)] += 25
        scores[BONG_AM.get(sum_de, sum_de)] += 15

    sorted_cang = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top3_cang = [str(x[0]) for x in sorted_cang[:3]]
    top4_cang = [str(x[0]) for x in sorted_cang[:4]]

    cang_bt_3s = [f"{c}{top_1}" for c in top3_cang] if top_1 else []
    cang_tt_12s = [f"{c}{num}" for c in top3_cang for num in top_4] if top_4 else []
    cang_d9_27s = [f"{c}{num}" for c in top3_cang for num in dan_9_so] if dan_9_so else []

    return {
        'tam_g1': str(tam_g1) if tam_g1 >= 0 else '',
        'tong_de': str(sum_de) if sum_de >= 0 else '',
        'top3_cang': top3_cang,
        'top4_cang': top4_cang,
        'cang_bt_3s': cang_bt_3s,
        'cang_tt_12s': cang_tt_12s,
        'cang_d9_27s': cang_d9_27s
    }

DEFAULT_60_N1 = [
    "01", "02", "03", "04", "05", "08", "09", "11", "12", "13", "15", "17", "18", "19", "21",
    "22", "23", "24", "26", "28", "29", "31", "32", "33", "34", "35", "37", "38", "39", "42",
    "43", "44", "45", "51", "53", "55", "58", "59", "60", "61", "62", "63", "65", "67", "68",
    "69", "72", "80", "81", "82", "83", "84", "85", "87", "88", "91", "92", "95", "96", "97", "99"
]

def fetch_html(is_live=True, count=35):
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 Chrome/120.0.0.0 Safari/604.1',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    table_tag = '<table class="table table-condensed kqcenter kqvertimarginw table-kq-border table-kq-hover-div table-bordered kqbackground table-kq-bold-border tb-phoi-border watermark table-striped" id="result_tab_mb">'
    
    so_kq_html = ""
    if HAS_LIBS:
        try:
            resp = requests.post(MKETQUA_SO_KQ_URL, data={'code': 'mb', 'count': str(count), 'dow': '7'}, headers=headers, timeout=10)
            if resp.status_code == 200:
                so_kq_html = resp.text
        except Exception:
            pass

    if not so_kq_html:
        try:
            data = urllib.parse.urlencode({'code': 'mb', 'count': str(count), 'dow': '7'}).encode('utf-8')
            req = urllib.request.Request(MKETQUA_SO_KQ_URL, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                so_kq_html = response.read().decode('utf-8', errors='ignore')
        except Exception:
            pass

    if is_live:
        home_html = ""
        try:
            if HAS_LIBS:
                resp_h = requests.get(MKETQUA_LIVE_URL, headers=headers, timeout=7)
                if resp_h.status_code == 200 and table_tag in resp_h.text:
                    home_html = resp_h.text
        except Exception:
            pass

        if home_html and so_kq_html:
            h_b = home_html.split(table_tag)
            s_b = so_kq_html.split(table_tag)
            if len(h_b) > 1 and len(s_b) > 1:
                return s_b[0] + table_tag + h_b[1] + table_tag + table_tag.join(s_b[1:])
        elif home_html:
            return home_html

    return so_kq_html

def parse_draws(html):
    blocks = html.split('<table class="table table-condensed kqcenter kqvertimarginw table-kq-border table-kq-hover-div table-bordered kqbackground table-kq-bold-border tb-phoi-border watermark table-striped" id="result_tab_mb">')
    draws = []
    seen_dates = set()
    
    for b in blocks[1:]:
        date_m = re.search(r'id="result_date">([^<]+)</span>', b)
        date_str = date_m.group(1).strip() if date_m else ""
        if not date_str:
            continue
        norm_date = re.sub(r'\s+', ' ', date_str).strip()
        if norm_date in seen_dates:
            continue
        seen_dates.add(norm_date)
        
        db_m = re.search(r'id="rs_0_0"[^>]*>(\d{5})</div>', b)
        if not db_m:
            db_m = re.search(r'id="rs_0_0"[^>]*data-sofar="(\d{5})"', b)
        db_val = db_m.group(1).strip() if db_m else ""
        de_val = db_val[-2:] if len(db_val) >= 2 else ""

        prizes = {}
        config = [(1, 1), (2, 2), (3, 6), (4, 4), (5, 6), (7, 4)]
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

def get_positions(prizes):
    res = {}
    for code, val in prizes.items():
        if not val or code.startswith('G7'): continue
        for idx, char in enumerate(val, 1):
            res[f"{code}_{idx}"] = (char, f"{code} vị trí {idx}")
    return res

def scan_radar():
    html = fetch_html(is_live=True)
    if not html:
        if os.path.exists(STATE_JSON_PATH):
            with open(STATE_JSON_PATH, encoding='utf-8') as f:
                return json.load(f)
        return None

    draws = parse_draws(html)
    if len(draws) < 2:
        if os.path.exists(STATE_JSON_PATH):
            with open(STATE_JSON_PATH, encoding='utf-8') as f:
                return json.load(f)
        return None

    target_draw = draws[0]
    prev_draw = draws[1]

    prev_de = prev_draw['de']
    if not prev_de or len(prev_de) < 2:
        if os.path.exists(STATE_JSON_PATH):
            with open(STATE_JSON_PATH, encoding='utf-8') as f:
                return json.load(f)
        return None

    head_num = int(prev_de[0])
    tail_num = int(prev_de[1])
    head_bong = BONG_DUONG[head_num]
    tail_bong = BONG_DUONG[tail_num]
    head_targets = [str(head_num), str(head_bong)]
    tail_targets = [str(tail_num), str(tail_bong)]

    target_pos = get_positions(target_draw['prizes'])
    prev_pos = get_positions(prev_draw['prizes'])

    def calc_streak(pos_key, is_head=True):
        streak = 1
        for past_idx in range(2, min(len(draws), 7)):
            de = draws[past_idx]['de']
            if not de or len(de) < 2: break
            d_val = int(de[0] if is_head else de[1])
            allowed = [str(d_val), str(BONG_DUONG[d_val])]
            past_p = get_positions(draws[past_idx]['prizes'])
            if pos_key in past_p and past_p[pos_key][0] in allowed:
                streak += 1
            else:
                break
        return min(streak, 4)

    highlight_positions = {}
    head_matches = []
    tail_matches = []

    for pos_key, (char, raw_name) in prev_pos.items():
        if char in head_targets:
            streak = calc_streak(pos_key, is_head=True)
            if pos_key in target_pos:
                cur_char = target_pos[pos_key][0]
                cur_bong = str(BONG_DUONG[int(cur_char)])
                cat = "Chỉ đạo" if streak >= 3 else ("Lót" if streak == 2 else "Theo dõi")
                color = "cycle_main" if streak >= 3 else ("cycle_lot" if streak == 2 else "cycle_watch")
                suffix = f"{streak}d"
                label = f"✅ CHỈ ĐẠO ({streak} ngày)" if streak >= 3 else (f"Lót ngày {streak}" if streak == 2 else "Theo dõi ngày 1 (Mới chạm)")
                
                info = {
                    'pos_raw': raw_name,
                    'role': 'head',
                    'role_name': 'Đầu',
                    'digit': cur_char,
                    'digit_bong': cur_bong,
                    'cycle': streak,
                    'cycle_suffix': suffix,
                    'category': cat,
                    'label': label,
                    'color_type': color,
                    'tooltip': f"{raw_name}: Đầu {cur_char} ({suffix}) | {label}"
                }
                highlight_positions[pos_key] = info
                head_matches.append(info)

        if char in tail_targets:
            streak = calc_streak(pos_key, is_head=False)
            if pos_key in target_pos:
                cur_char = target_pos[pos_key][0]
                cur_bong = str(BONG_DUONG[int(cur_char)])
                cat = "Chỉ đạo" if streak >= 3 else ("Lót" if streak == 2 else "Theo dõi")
                color = "cycle_main" if streak >= 3 else ("cycle_lot" if streak == 2 else "cycle_watch")
                suffix = f"{streak}d"
                label = f"✅ CHỈ ĐẠO ({streak} ngày)" if streak >= 3 else (f"Lót ngày {streak}" if streak == 2 else "Theo dõi ngày 1 (Mới chạm)")
                
                info = {
                    'pos_raw': raw_name,
                    'role': 'tail',
                    'role_name': 'Đuôi',
                    'digit': cur_char,
                    'digit_bong': cur_bong,
                    'cycle': streak,
                    'cycle_suffix': suffix,
                    'category': cat,
                    'label': label,
                    'color_type': color,
                    'tooltip': f"{raw_name}: Đuôi {cur_char} ({suffix}) | {label}"
                }
                if pos_key in highlight_positions:
                    if streak > highlight_positions[pos_key]['cycle']:
                        highlight_positions[pos_key] = info
                else:
                    highlight_positions[pos_key] = info
                tail_matches.append(info)

    # Tổ hợp ghép cặp Chục x Đơn vị
    combos_map = {}
    cap4_set = set(DEFAULT_60_N1)

    for h in head_matches:
        for t in tail_matches:
            c = h['digit']
            d = t['digit']
            cb = h['digit_bong']
            db = t['digit_bong']
            cycle_pair = max(h['cycle'], t['cycle'])
            
            pairs = [
                (f"{c}{d}", 1.0, "chính diện"),
                (f"{c}{db}", 0.85, "bóng đuôi"),
                (f"{cb}{d}", 0.85, "bóng đầu"),
                (f"{cb}{db}", 0.7, "bóng cả hai")
            ]
            
            for num_str, wt, ctype in pairs:
                cat = "Chỉ đạo" if cycle_pair >= 3 else ("Lót" if cycle_pair == 2 else "Theo dõi")
                score = cycle_pair * 40 + wt * 25 + (h['cycle'] + t['cycle']) * 10
                
                if num_str not in combos_map or score > combos_map[num_str]['score']:
                    combos_map[num_str] = {
                        'num': num_str,
                        'c_digit': c,
                        'd_digit': d,
                        'c_cycle': h['cycle'],
                        'd_cycle': t['cycle'],
                        'cycle_days': cycle_pair,
                        'category': cat,
                        'cat_label': f"✅ CHỈ ĐẠO ({cycle_pair} ngày)" if cycle_pair >= 3 else (f"Lót ngày {cycle_pair}" if cycle_pair == 2 else "Theo dõi ngày 1 (Mới chạm)"),
                        'weight': wt,
                        'combo_type': ctype,
                        'score': score,
                        'h_pos': h['pos_raw'],
                        't_pos': t['pos_raw'],
                        'in_cap4': (num_str in cap4_set),
                        'in_cap4_str': "Có" if (num_str in cap4_set) else "Không"
                    }

    # 1. Trích xuất thông tin G1 & Tâm G1 trực tiếp
    live_p = target_draw['prizes']
    p_g1 = live_p.get('G1', '')
    p_g2 = [live_p.get('G2.1', ''), live_p.get('G2.2', '')]
    p_g3 = [live_p.get(f'G3.{i}', '') for i in range(1, 7)]
    p_g4 = [live_p.get(f'G4.{i}', '') for i in range(1, 5)]
    p_g5 = [live_p.get(f'G5.{i}', '') for i in range(1, 7)]
    filled_prizes = (1 if p_g1 else 0) + sum(1 for x in p_g2 if x) + sum(1 for x in p_g3 if x) + sum(1 for x in p_g4 if x) + sum(1 for x in p_g5 if x)
    is_completed = (filled_prizes >= 19)

    tam_g1 = p_g1[2] if (p_g1 and len(p_g1) >= 3 and p_g1.isdigit()) else ''
    tam_g1_set = {tam_g1, str(BONG_DUONG.get(int(tam_g1), ''))} if tam_g1 else set()

    # 2. Load analysis_summary.json để đồng bộ Top 3 Đầu x Top 3 Đuôi AI
    summary_data = {}
    if os.path.exists(SUMMARY_JSON_PATH):
        try:
            with open(SUMMARY_JSON_PATH, encoding='utf-8') as f:
                summary_data = json.load(f)
        except Exception:
            pass

    head_digits = []
    if summary_data.get('top_predicted_heads'):
        head_digits = [h['head'].replace('Đầu ', '').strip() for h in summary_data['top_predicted_heads'][:3]]
    if not head_digits:
        head_digits = ['3', '4', '2']

    tail_digits = []
    if summary_data.get('top_predicted_tails'):
        tail_digits = [t['tail'].replace('Đuôi ', '').strip() for t in summary_data['top_predicted_tails'][:3]]
    if not tail_digits:
        tail_digits = ['2', '7', '1']

    dan_9_so = sorted(list(set(f"{h}{t}" for h in head_digits for t in tail_digits)))

    # 3. Trích xuất Cầu Tổng G7 & Tổng Đề kỳ trước
    target_sums = extract_target_sums(prev_draw)

    # 4. Tính Điểm Hội Tụ Đa Tầng (Multi-Criteria Convergence Score) cho từng con số
    for item in combos_map.values():
        num_str = item['num']
        c_pair = item['cycle_days']
        wt = item['weight']
        
        # A. Điểm nền Radar Vị trí G1-G5: chu kỳ 2 ngày nhịp đẹp: 30đ, chu kỳ 3d: 25đ, 1d: 15đ
        cycle_pts = 30 if c_pair == 2 else (25 if c_pair >= 3 else 15)
        base_radar = cycle_pts + wt * 20
        
        # B. Tiêu chí Giao Thoa 1: Khớp Dàn 9 Số Cội Nguồn AI (Top 3 Đầu x Top 3 Đuôi)
        in_d9 = (num_str in dan_9_so)
        d9_pts = 55 if in_d9 else 0
        
        # C. Tiêu chí Giao Thoa 2: Đồng bộ Chữ Số Tâm Càng G1 (vừa quay lúc 18h16)
        in_tam = False
        tam_pts = 0
        if tam_g1_set and len(num_str) >= 2:
            if num_str[0] in tam_g1_set or num_str[1] in tam_g1_set:
                in_tam = True
                tam_pts = 35 if (num_str[0] == tam_g1 or num_str[1] == tam_g1) else 25
                
        # D. Tiêu chí Giao Thoa 3: Khớp Cầu Tổng G7 & Tổng Đề kỳ trước
        cur_sum = (int(num_str[0]) + int(num_str[1])) % 10 if (len(num_str) >= 2 and num_str.isdigit()) else -1
        in_sum = (cur_sum in target_sums) if target_sums else False
        sum_pts = 30 if in_sum else 0
        
        # E. Ràng buộc an toàn: Bắt buộc thuộc Dàn 60 Số N1 Đã Kiểm Định
        in_n1 = item['in_cap4']
        n1_pts = 35 if in_n1 else -200
        
        c_score = base_radar + d9_pts + tam_pts + sum_pts + n1_pts
        item['consensus_score'] = c_score
        item['in_d9'] = in_d9
        item['in_tam'] = in_tam
        item['in_sum'] = in_sum
        
        badges = []
        if in_n1: badges.append("N1")
        if in_d9: badges.append("Dàn 9s AI")
        if in_tam: badges.append(f"Tâm G1 ({tam_g1})")
        if in_sum: badges.append(f"Tổng G7 ({cur_sum})")
        item['convergence_badges'] = badges

    found_list = list(combos_map.values())
    found_list.sort(key=lambda x: (x.get('consensus_score', 0), x['score']), reverse=True)

    # 5. Xác định Bạch Thủ Top 1, Lót Lộn Song Thủ và Top 4 Tứ Thủ
    n1_pool = [x for x in found_list if x['in_cap4']]
    top_pool = n1_pool if n1_pool else found_list
    top_1 = top_pool[0]['num'] if top_pool else "41"
    lot_lon = get_lot_lon(top_1)
    song_thu_tru = [top_1, lot_lon]

    # Top 4 Tứ thủ tinh hoa: Bạch thủ + Lót lộn (nếu thuộc N1) + các con số có điểm hội tụ cao nhất kế tiếp
    top_4 = [top_1]
    if lot_lon in cap4_set and lot_lon not in top_4:
        top_4.append(lot_lon)
    for x in top_pool:
        if x['num'] not in top_4:
            top_4.append(x['num'])
        if len(top_4) >= 4:
            break

    dan_lot_valid = []
    table_5cols = []

    for item in found_list:
        n = item['num']
        if n == top_1:
            item['top_rank'] = "👑 Top 1 (Bạch thủ)"
        elif n == lot_lon:
            item['top_rank'] = "🛡️ Lót Lộn (Song thủ)"
            if n in cap4_set and n not in dan_lot_valid:
                dan_lot_valid.append(n)
        elif n in top_4:
            item['top_rank'] = "🔥 Top 4 (Tứ thủ)"
        elif item['in_cap4']:
            item['top_rank'] = "🛡️ Lót hợp lệ"
            if n not in dan_lot_valid:
                dan_lot_valid.append(n)
        else:
            item['top_rank'] = "❌ Loại bỏ (Ngoài N1)"
        table_5cols.append(item)

    # Đảm bảo Dàn Lót Hợp Lệ luôn đầy đủ (bổ sung từ Dàn 9 số & Dàn Cấp 2 / N1 loại trừ Top 1 & Top 4)
    dan_cap2_38so = ["01", "02", "04", "07", "09", "11", "12", "14", "16", "17", "20", "22", "23", "25", "27", "31", "32", "37", "40", "41", "42", "45", "47", "49", "61", "62", "67", "68", "70", "72", "75", "77", "81", "82", "84", "86", "87", "89"]
    backup_pool = [x for x in dan_9_so if x in cap4_set and x not in top_4 and x != top_1]
    backup_pool += [x for x in dan_cap2_38so if x in cap4_set and x not in top_4 and x != top_1]
    for n in backup_pool:
        if n not in dan_lot_valid:
            dan_lot_valid.append(n)
    dan_lot_valid = sorted(list(set(dan_lot_valid)))

    actual_de = target_draw.get('de', '')
    if actual_de:
        radar_status = "FINISHED_RESULT"
        status_text = f"ĐÃ HOÀN TẤT KỲ QUAY (ĐỀ VỀ {actual_de})"
        lock_badge = f"🎯 ĐÃ CÓ KẾT QUẢ ĐỀ: {actual_de}"
    elif is_completed:
        radar_status = "LOCKED_G5"
        status_text = "🔒 ĐÃ CHỐT KHÓA KHI HẾT G5 (19/19 GIẢI) - VÀO TIỀN NGAY TRƯỚC 18H28!"
        lock_badge = "🔒 ĐÃ KHÓA CHỐT DÀN (HẾT G5)"
    elif filled_prizes > 0:
        radar_status = "SCANNING_LIVE"
        status_text = f"⚡ ĐANG QUAY TRỰC TIẾP ({filled_prizes}/19 GIẢI) - CHỐT KHI XONG G5"
        lock_badge = f"⚡ ĐANG QUAY ({filled_prizes}/19)"
    else:
        radar_status = "BEFORE_DRAW"
        status_text = "CHỜ GIỜ QUAY THƯỞNG (18H15) - DÀN TĨNH SẴN SÀNG"
        lock_badge = "⏳ CHỜ GIỜ QUAY (18H15)"

    # Bắt Top 3 Càng 3D từ Tâm Càng G1 + Bóng Tổng Đề
    cang_info = calc_cang_3d(p_g1, prev_de, top_1, top_4, dan_9_so)
    cang_info['target_date'] = target_draw['date']
    cang_info['target_note'] = f"ĐÁNH NGAY CHO GIẢI ĐẶC BIỆT HÔM NAY ({target_draw['date']}) - Khóa sổ khi hết G5, vào tiền trước 18h28!"
    cang_info['tam_g1_source'] = f"Tâm Càng G1 ({p_g1[2] if len(p_g1)>=3 else '---'} từ G1: {p_g1 or 'Chờ quay'})"
    cang_info['prev_de_source'] = f"Tổng Đề hôm trước ({prev_de}): {(int(prev_de[0])+int(prev_de[1]))%10 if len(prev_de)>=2 else '---'}"

    # Dàn Tĩnh 4 Cấp trước 18h15 (Tự động nhảy ngày sang kỳ tiếp theo nếu đã có GĐB)
    dow_vn = {
        0: "Thứ hai", 1: "Thứ ba", 2: "Thứ tư", 3: "Thứ năm",
        4: "Thứ sáu", 5: "Thứ bảy", 6: "Chủ nhật"
    }
    date_m = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', target_draw['date'])
    if date_m and actual_de:
        d_val, m_val, y_val = map(int, date_m.groups())
        cur_dt = datetime(y_val, m_val, d_val)
        next_dt = cur_dt + timedelta(days=1)
        tinh_target_date = f"{dow_vn[next_dt.weekday()]} ngày {next_dt.strftime('%d-%m-%Y')}"
        tinh_status_text = f"ĐANG HIỆU LỰC CHO KỲ TỚI (VÀO TIỀN TRƯỚC 18H15 NGÀY {next_dt.strftime('%d/%m')})"
    else:
        tinh_target_date = target_draw['date']
        tinh_status_text = "ĐANG CÓ HIỆU LỰC (VÀO TIỀN TRƯỚC 18H15)"

    dan_tinh_4cap = {
        'target_date': tinh_target_date,
        'status_text': tinh_status_text,
        'bach_thu': top_1 if top_1 else '65',
        'lot_lon': lot_lon if lot_lon else '56',
        'song_thu': song_thu_tru,
        'tu_thu': top_4 if len(top_4) >= 4 else ['65', '56', '22', '21'],
        'cang_3d': cang_info['top3_cang'],
        'dan_9_so': dan_9_so,
        'dan_cap2_38so': dan_cap2_38so,
        'dan_60_cap4': DEFAULT_60_N1
    }

    # Auto-Shift Khung 3 ngày
    hit_n1 = (actual_de in DEFAULT_60_N1) if actual_de else False
    
    frame_transition = {
        'last_result': f"Kỳ gần nhất ({target_draw['date']}) Đề về {actual_de or 'đang quay'}: {'🎯 ĐÃ TRÚNG N1 → RESET CHUYỂN CHU KỲ MỚI' if hit_n1 else ('❌ TRƯỢT N1 → GIỮ NGUYÊN KHUNG, ĐÁNH N2 (36 SỐ)' if actual_de else 'Đang chờ quay Giải Đặc Biệt')}",
        'status_badge': 'ĐÃ TRÚNG N1 → RESET CẦU MỚI' if hit_n1 else ('ĐANG ĐÁNH N2 (36 SỐ)' if actual_de else 'ĐANG QUAY THƯỞNG'),
        'dan_n1': DEFAULT_60_N1,
        'dan_n2': ["02", "04", "07", "09", "12", "14", "17", "20", "23", "25", "27", "31", "32", "37", "40", "41", "42", "45", "47", "49", "61", "62", "67", "68", "70", "72", "75", "77", "81", "82", "84", "86", "87", "89", "91", "96"],
        'dan_n3': ["01", "03", "05", "08", "11", "13", "16", "18", "21", "24", "26", "28", "33", "35", "38", "43", "44", "48", "51", "53", "55", "58", "60", "63", "65", "69", "71", "73", "78", "80", "83", "85", "88", "92", "95", "97"]
    }

    # Đánh giá Lịch sử kiểm chứng các kỳ trước đó
    history_records, history_summary = build_radar_history(draws, summary_data, max_records=30)

    final_state = {
        'target_date': target_draw['date'],
        'prev_date': prev_draw['date'],
        'prev_de': prev_de,
        'head_targets': head_targets,
        'tail_targets': tail_targets,
        'live_prizes': {
            'g1': p_g1,
            'g2': p_g2,
            'g3': p_g3,
            'g4': p_g4,
            'g5': p_g5
        },
        'highlight_positions': highlight_positions,
        'filled_count': filled_prizes,
        'total_count': 19,
        'is_g5_finished': is_completed,
        'radar_status': radar_status,
        'status_text': status_text,
        'lock_badge': lock_badge,
        'top_1': top_1,
        'lot_lon': lot_lon,
        'song_thu_tru': song_thu_tru,
        'top_4': top_4,
        'cang_3d_live': cang_info,
        'dan_9_heads': head_digits,
        'dan_9_tails': tail_digits,
        'dan_9_so': dan_9_so,
        'dan_lot': dan_lot_valid,
        'table_5cols': table_5cols,
        'actual_de': actual_de,
        'dan_tinh_4cap': dan_tinh_4cap,
        'frame_transition': frame_transition,
        'history_records': history_records,
        'history_summary': history_summary,
        'last_updated': datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    }

    with open(STATE_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(final_state, f, ensure_ascii=False, indent=2)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Đã cập nhật live_radar_state.json: {filled_prizes}/19 giải | Bạch Thủ: {top_1} (Lót lộn: {lot_lon}) | Tứ Thủ: {top_4} | Dàn 9s: {len(dan_9_so)}s | Dàn Lót: {len(dan_lot_valid)}s | Lịch sử: {len(history_records)} kỳ")
    return final_state

def evaluate_radar_for_draw(sub_draws, cap4_set, summary_data=None):
    """Tính toán Bạch thủ Top 1, Lót lộn Song thủ, Tứ thủ Top 4 theo thuật toán Hội Tụ Đa Tầng."""
    if len(sub_draws) < 2:
        return None
    target_draw = sub_draws[0]
    prev_draw = sub_draws[1]
    prev_de = prev_draw.get('de', '')
    if not prev_de or len(prev_de) < 2:
        return None

    head_num = int(prev_de[0])
    tail_num = int(prev_de[1])
    head_targets = [str(head_num), str(BONG_DUONG[head_num])]
    tail_targets = [str(tail_num), str(BONG_DUONG[tail_num])]

    target_pos = get_positions(target_draw['prizes'])
    prev_pos = get_positions(prev_draw['prizes'])

    g1_val = target_draw.get('prizes', {}).get('G1', '')
    tam_g1 = g1_val[2] if (g1_val and len(g1_val) >= 3 and g1_val.isdigit()) else ''
    tam_g1_set = {tam_g1, str(BONG_DUONG.get(int(tam_g1), ''))} if tam_g1 else set()

    t_date = target_draw.get('date', '')
    top3_history_map = {r['date']: r for r in summary_data.get('history_top3_dau_duoi_records', [])} if summary_data else {}
    t3_info = top3_history_map.get(t_date, {})
    d9_str = t3_info.get('pred_9_nums', '')
    d9_set = set([x.strip() for x in d9_str.split(',') if x.strip()]) if d9_str else set()

    target_sums = extract_target_sums(prev_draw)

    def calc_streak_local(pos_key, is_head=True):
        streak = 1
        for past_idx in range(2, min(len(sub_draws), 7)):
            de = sub_draws[past_idx].get('de', '')
            if not de or len(de) < 2:
                break
            d_val = int(de[0] if is_head else de[1])
            allowed = [str(d_val), str(BONG_DUONG[d_val])]
            past_p = get_positions(sub_draws[past_idx]['prizes'])
            if pos_key in past_p and past_p[pos_key][0] in allowed:
                streak += 1
            else:
                break
        return min(streak, 4)

    head_matches = []
    tail_matches = []
    for pos_key, (char, raw_name) in prev_pos.items():
        if char in head_targets and pos_key in target_pos:
            st = calc_streak_local(pos_key, is_head=True)
            c = target_pos[pos_key][0]
            head_matches.append({'digit': c, 'digit_bong': str(BONG_DUONG[int(c)]), 'cycle': st, 'pos_raw': raw_name})
        if char in tail_targets and pos_key in target_pos:
            st = calc_streak_local(pos_key, is_head=False)
            c = target_pos[pos_key][0]
            tail_matches.append({'digit': c, 'digit_bong': str(BONG_DUONG[int(c)]), 'cycle': st, 'pos_raw': raw_name})

    combos_map = {}
    for h in head_matches:
        for t in tail_matches:
            c = h['digit']
            d = t['digit']
            cb = h['digit_bong']
            db = t['digit_bong']
            cycle_pair = max(h['cycle'], t['cycle'])
            pairs = [(f"{c}{d}", 1.0), (f"{c}{db}", 0.85), (f"{cb}{d}", 0.85), (f"{cb}{db}", 0.7)]
            for num_str, wt in pairs:
                cycle_pts = 30 if cycle_pair == 2 else (25 if cycle_pair >= 3 else 15)
                base_radar = cycle_pts + wt * 20

                in_d9 = (num_str in d9_set)
                d9_pts = 55 if in_d9 else 0

                in_tam = (tam_g1_set and (num_str[0] in tam_g1_set or num_str[1] in tam_g1_set))
                tam_pts = 35 if (tam_g1 and (num_str[0] == tam_g1 or num_str[1] == tam_g1)) else (25 if in_tam else 0)

                cur_sum = (int(num_str[0]) + int(num_str[1])) % 10 if (len(num_str) >= 2 and num_str.isdigit()) else -1
                in_sum = (cur_sum in target_sums) if target_sums else False
                sum_pts = 30 if in_sum else 0

                in_n1 = (num_str in cap4_set)
                n1_pts = 35 if in_n1 else -200

                c_score = base_radar + d9_pts + tam_pts + sum_pts + n1_pts
                if num_str not in combos_map or c_score > combos_map[num_str]['consensus_score']:
                    combos_map[num_str] = {
                        'num': num_str,
                        'consensus_score': c_score,
                        'cycle_days': cycle_pair,
                        'in_cap4': in_n1,
                        'score': cycle_pair * 40 + wt * 25
                    }

    found = list(combos_map.values())
    found.sort(key=lambda x: (x.get('consensus_score', 0), x['score']), reverse=True)

    n1_pool = [x for x in found if x['in_cap4']]
    top_pool = n1_pool if n1_pool else found
    t1 = top_pool[0]['num'] if top_pool else ""
    lot_lon = get_lot_lon(t1)
    song_thu = [t1, lot_lon] if lot_lon else [t1]

    t4 = [t1] if t1 else []
    if lot_lon and lot_lon in cap4_set and lot_lon not in t4:
        t4.append(lot_lon)
    for x in top_pool:
        if x['num'] not in t4:
            t4.append(x['num'])
        if len(t4) >= 4:
            break

    return {
        'top_1': t1,
        'lot_lon': lot_lon,
        'song_thu': song_thu,
        'top_4': t4,
        'found': found
    }

def build_radar_history(draws, summary_data, max_records=30):
    """Xây dựng bảng lịch sử kiểm chứng các kỳ quay (Top 1 Bạch Thủ, Lót Lộn Song Thủ, Top 4 Tứ Thủ, Dàn 9 Số, Dàn Lót)."""
    cap4_set = set(DEFAULT_60_N1)
    top3_history_map = {r['date']: r for r in summary_data.get('history_top3_dau_duoi_records', [])} if summary_data else {}
    records = []

    start_k = 0
    if len(draws) > 0 and not draws[0].get('de'):
        start_k = 1

    for k in range(start_k, min(len(draws) - 2, start_k + max_records)):
        sub_draws = draws[k:]
        target_draw = sub_draws[0]
        actual_de = target_draw.get('de', '')
        if not actual_de or len(actual_de) < 2:
            continue

        eval_res = evaluate_radar_for_draw(sub_draws, cap4_set, summary_data)
        if not eval_res:
            continue

        t1 = eval_res['top_1']
        lot_lon = eval_res.get('lot_lon', '')
        song_thu = eval_res.get('song_thu', [t1])
        t4 = eval_res['top_4']

        t_date = target_draw.get('date', '')
        t3_info = top3_history_map.get(t_date, {})
        d9_str = t3_info.get('pred_9_nums', '')
        d9_list = [x.strip() for x in d9_str.split(',') if x.strip()] if d9_str else []
        pred_heads = t3_info.get('pred_heads', '')
        pred_tails = t3_info.get('pred_tails', '')

        if not d9_list:
            d9_list = [x['num'] for x in eval_res['found'][:9]]

        dan_lot = [x['num'] for x in eval_res['found'] if x['num'] in cap4_set and x['num'] not in t4 and x['num'] != t1]
        dan_cap2_38so = ["01", "02", "04", "07", "09", "11", "12", "14", "16", "17", "20", "22", "23", "25", "27", "31", "32", "37", "40", "41", "42", "45", "47", "49", "61", "62", "67", "68", "70", "72", "75", "77", "81", "82", "84", "86", "87", "89"]
        backup_pool = [x for x in d9_list if x in cap4_set and x not in t4 and x != t1]
        backup_pool += [x for x in dan_cap2_38so if x in cap4_set and x not in t4 and x != t1]
        for n in backup_pool:
            if n not in dan_lot:
                dan_lot.append(n)
        dan_lot = sorted(list(set(dan_lot)))

        hit_t1 = (actual_de == t1) if t1 else False
        hit_lot_lon = (actual_de == lot_lon) if lot_lon else False
        hit_song_thu = (actual_de in song_thu) if song_thu else False
        hit_t4 = (actual_de in t4) if t4 else False
        hit_d9 = (actual_de in d9_list) if d9_list else False
        hit_lot = (actual_de in dan_lot) if dan_lot else False
        hit_n1 = (actual_de in cap4_set)

        actual_db = target_draw.get('db', '')
        actual_3d = actual_db[-3:] if len(actual_db) >= 3 else ''
        past_g1 = target_draw.get('prizes', {}).get('G1', '')
        prev_sub_de = sub_draws[1].get('de', '') if len(sub_draws) > 1 else ''
        cang_hist = calc_cang_3d(past_g1, prev_sub_de, t1, t4, d9_list)
        hit_cang_tt = (actual_3d in cang_hist['cang_tt_12s']) if (actual_3d and cang_hist['cang_tt_12s']) else False
        hit_cang_bt = (actual_3d in cang_hist['cang_bt_3s']) if (actual_3d and cang_hist['cang_bt_3s']) else False

        records.append({
            'stt': len(records) + 1,
            'date': t_date,
            'de': actual_de,
            'actual_3d': actual_3d,
            'top_1': t1,
            'lot_lon': lot_lon,
            'song_thu': song_thu,
            'hit_top_1': hit_t1,
            'hit_lot_lon': hit_lot_lon,
            'hit_song_thu': hit_song_thu,
            'top_4': t4,
            'hit_top_4': hit_t4,
            'dan_9_so': d9_list,
            'pred_heads': pred_heads,
            'pred_tails': pred_tails,
            'hit_dan_9': hit_d9,
            'dan_lot': dan_lot,
            'hit_dan_lot': hit_lot,
            'hit_n1': hit_n1,
            'top3_cang': cang_hist['top3_cang'],
            'hit_cang_tt': hit_cang_tt,
            'hit_cang_bt': hit_cang_bt
        })

    tot = len(records)
    t1_hits = sum(1 for r in records if r['hit_top_1'])
    song_thu_hits = sum(1 for r in records if r.get('hit_song_thu'))
    t4_hits = sum(1 for r in records if r['hit_top_4'])
    d9_hits = sum(1 for r in records if r['hit_dan_9'])
    lot_hits = sum(1 for r in records if r['hit_dan_lot'])
    n1_hits = sum(1 for r in records if r['hit_n1'])
    cang_tt_hits = sum(1 for r in records if r['hit_cang_tt'])
    cang_bt_hits = sum(1 for r in records if r['hit_cang_bt'])

    summary = {
        'total_evals': tot,
        'top1_hits': t1_hits,
        'top1_rate': round(t1_hits / tot * 100, 2) if tot else 0,
        'song_thu_hits': song_thu_hits,
        'song_thu_rate': round(song_thu_hits / tot * 100, 2) if tot else 0,
        'top4_hits': t4_hits,
        'top4_rate': round(t4_hits / tot * 100, 2) if tot else 0,
        'dan9_hits': d9_hits,
        'dan9_rate': round(d9_hits / tot * 100, 2) if tot else 0,
        'lot_hits': lot_hits,
        'lot_rate': round(lot_hits / tot * 100, 2) if tot else 0,
        'n1_hits': n1_hits,
        'n1_rate': round(n1_hits / tot * 100, 2) if tot else 0,
        'cang_tt_hits': cang_tt_hits,
        'cang_tt_rate': round(cang_tt_hits / tot * 100, 2) if tot else 0,
        'cang_bt_hits': cang_bt_hits,
        'cang_bt_rate': round(cang_bt_hits / tot * 100, 2) if tot else 0
    }
    return records, summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Radar Scanner G1->G5 XSMB")
    parser.add_argument('--live', action='store_true', help="Chạy vòng lặp cào live liên tục mỗi 5-10 giây")
    parser.add_argument('--interval', type=int, default=7, help="Chu kỳ giây quét (mặc định 7s)")
    parser.add_argument('--duration', type=int, default=0, help="Thời gian tối đa chạy live tính bằng giây (0 = vô hạn)")
    parser.add_argument('--auto_push', action='store_true', help="Tự động git push ngay khi chốt G5 và khi có GĐB")
    args = parser.parse_args()

    def do_quick_git_push(commit_msg):
        try:
            import subprocess
            git_path = r"C:\Program Files\Git\cmd\git.exe"
            subprocess.run([git_path, 'add', 'live_radar_state.json'], check=True, capture_output=True)
            subprocess.run([git_path, 'commit', '-m', commit_msg], capture_output=True, text=True)
            subprocess.run([git_path, 'push', 'origin', 'main'], capture_output=True, text=True)
            print(f"🚀 [GIT PUSH] {commit_msg} -> Đã đồng bộ lên GitHub thành công!", flush=True)
        except Exception as ex:
            print(f"⚠️ Không thể git push nhanh: {ex}", flush=True)

    if args.live:
        print(f"[*] Bắt đầu radar live polling mỗi {args.interval} giây (Thời lượng tối đa: {args.duration if args.duration else 'Vô hạn'}s)...")
        start_t = time.time()
        g5_locked = False
        final_completed = False

        while True:
            try:
                res = scan_radar()
                if res:
                    # 1. BƯỚC CHỐT KHÓA NGAY KHI HẾT G5 (18h24)
                    if res.get('is_g5_finished') and not g5_locked:
                        g5_locked = True
                        top1 = res.get('top_1')
                        top4 = res.get('top_4')
                        top3_cang = res.get('cang_3d_live', {}).get('top3_cang', [])
                        t_date = res.get('target_date', '')
                        print(f"\n=======================================================", flush=True)
                        print(f"🔒 [CHỐT KHÓA G5 - {datetime.now().strftime('%H:%M:%S')}] ĐÃ HOÀN TẤT 19/19 GIẢI G1->G5 KỲ {t_date}!", flush=True)
                        print(f"👑 BẠCH THỦ TOP 1: {top1} | 🔥 TỨ THỦ: {top4}", flush=True)
                        print(f"🌟 TOP 3 CÀNG: {top3_cang} (ĐÁNH NGAY CHO GIẢI ĐẶC BIỆT HÔM NAY QUAY LÚC 18H30)", flush=True)
                        print(f"⏱️ HẠN CHỐT VÀO TIỀN: TRƯỚC 18H28!", flush=True)
                        print(f"=======================================================\n", flush=True)
                        if args.auto_push:
                            do_quick_git_push(f"Lock Radar G5 {t_date} (BT {top1}, TT {top4})")

                    # 2. BƯỚC ĐỐI CHIẾU KHI CÓ GIẢI ĐẶC BIỆT (sau 18h30)
                    if res.get('actual_de'):
                        print(f"\n🎯 [KẾT THÚC QUAY - {datetime.now().strftime('%H:%M:%S')}] Đã có Giải Đặc Biệt: {res.get('actual_de')}.", flush=True)
                        final_completed = True
                        if args.auto_push:
                            do_quick_git_push(f"Finish XSMB {res.get('target_date')} (DB {res.get('actual_de')})")
                        break
            except Exception as e:
                print(f"[!] Lỗi khi quét radar: {e}", flush=True)

            if args.duration > 0 and (time.time() - start_t) >= args.duration:
                print(f"[*] Đã hết thời gian live {args.duration}s. Dừng quét!")
                break
            time.sleep(args.interval)
    else:
        scan_radar()
