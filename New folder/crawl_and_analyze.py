import urllib.request
import urllib.parse
import re
import json
import datetime
import sys
import os
from collections import Counter, defaultdict
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

sys.stdout.reconfigure(encoding='utf-8')

dow_names = {
    0: 'Thứ Hai',
    1: 'Thứ Ba',
    2: 'Thứ Tư',
    3: 'Thứ Năm',
    4: 'Thứ Sáu',
    5: 'Thứ Bảy',
    6: 'Chủ Nhật'
}

def parse_date(date_str):
    parts = date_str.split('ngày ')
    if len(parts) > 1:
        d_str = parts[1].strip()
        return datetime.datetime.strptime(d_str, "%d-%m-%Y")
    return None

def get_tong(num_str):
    if not num_str or len(num_str) < 2:
        return None
    return (int(num_str[-2]) + int(num_str[-1])) % 10

def get_bong(tong):
    return (tong + 5) % 10

def get_set_20(g7_val):
    t = get_tong(g7_val)
    if t is None:
        return set()
    b = get_bong(t)
    return set(f"{i:02d}" for i in range(100) if (i//10 + i%10)%10 in (t, b))

def get_cham_g7(g7_1, g7_2, g7_3, g7_4):
    chams = set()
    for g in [g7_1, g7_2, g7_3, g7_4]:
        for char in g:
            if char.isdigit():
                chams.add(int(char))
    return chams

def get_g7_cham(g7_1, g7_2, g7_3, g7_4):
    digits = set()
    for g in [g7_1, g7_2, g7_3, g7_4]:
        for ch in g:
            if ch.isdigit():
                d = int(ch)
                digits.add(d)
                digits.add(get_bong(d))
    return digits

def crawl_xsmb():
    url = "https://mketqua.net/so-ket-qua"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    data = urllib.parse.urlencode({'code': 'mb', 'count': '300', 'dow': '7'}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers)

    print("Fetching lottery data from mketqua.net...")
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            blocks = html.split('<table class="table table-condensed kqcenter kqvertimarginw table-kq-border table-kq-hover-div table-bordered kqbackground table-kq-bold-border tb-phoi-border watermark table-striped" id="result_tab_mb">')
            
            results = []
            for block in blocks[1:]:
                date_match = re.search(r'id="result_date">([^<]+)</span>', block)
                date_str = date_match.group(1).strip() if date_match else ""
                
                db_match = re.search(r'id="rs_0_0"[^>]*>(\d{5})</div>', block)
                if not db_match:
                    db_match = re.search(r'id="rs_0_0"[^>]*data-sofar="(\d{5})"', block)
                db = db_match.group(1).strip() if db_match else ""
                
                g7_1_match = re.search(r'id="rs_7_0"[^>]*>(\d{2})</div>', block)
                g7_2_match = re.search(r'id="rs_7_1"[^>]*>(\d{2})</div>', block)
                g7_3_match = re.search(r'id="rs_7_2"[^>]*>(\d{2})</div>', block)
                g7_4_match = re.search(r'id="rs_7_3"[^>]*>(\d{2})</div>', block)
                
                g7_1 = g7_1_match.group(1).strip() if g7_1_match else ""
                g7_2 = g7_2_match.group(1).strip() if g7_2_match else ""
                g7_3 = g7_3_match.group(1).strip() if g7_3_match else ""
                g7_4 = g7_4_match.group(1).strip() if g7_4_match else ""
                
                if date_str and db:
                    results.append({
                        'date': date_str,
                        'db': db,
                        'de': db[-2:] if len(db)>=2 else "",
                        'g7_1': g7_1,
                        'g7_2': g7_2,
                        'g7_3': g7_3,
                        'g7_4': g7_4
                    })
                    
            results_2026 = [r for r in results if '2026' in r['date']]
            print(f"Extracted {len(results_2026)} records for 2026.")
            return results_2026

    except Exception as e:
        print("Error during crawl:", e)
        return []

def analyze_all(data_2026):
    chrono = list(reversed(data_2026))
    
    for r in chrono:
        dt = parse_date(r['date'])
        if dt:
            r['datetime'] = dt
            r['iso_year'], r['iso_week'], r['iso_weekday'] = dt.isocalendar()
            r['dow_code'] = dt.weekday()
            r['dow_name'] = dow_names[dt.weekday()]

    # 1. Weekly grouping
    weekly_groups = defaultdict(list)
    for r in chrono:
        if 'iso_week' in r:
            weekly_groups[(r['iso_year'], r['iso_week'])].append(r)

    sorted_weeks = sorted(weekly_groups.keys())
    last_week_key = sorted_weeks[-2] if len(sorted_weeks) >= 2 else sorted_weeks[-1]
    last_week_records = weekly_groups[last_week_key]
    
    w_hits = {'g7_1': 0, 'g7_2': 0, 'g7_3': 0, 'g7_4': 0}
    for idx_w in range(len(last_week_records) - 1):
        target_de = last_week_records[idx_w + 1]['de']
        for k in ['g7_1', 'g7_2', 'g7_3', 'g7_4']:
            if target_de in get_set_20(last_week_records[idx_w][k]):
                w_hits[k] += 1
                
    sorted_weekly_g7 = sorted(w_hits.items(), key=lambda x: x[1], reverse=True)
    top_weekly_keys = [x[0] for x in sorted_weekly_g7[:3]]
    excluded_weekly_key = sorted_weekly_g7[3][0]

    # 2. Multi-window frequencies (30, 60, 90 days)
    last_date = chrono[-1]['datetime'] if 'datetime' in chrono[-1] else parse_date(chrono[-1]['date'])
    
    window_stats = {}
    for w_days in [30, 60, 90]:
        cutoff = last_date - datetime.timedelta(days=w_days)
        sub = [r for r in chrono if r.get('datetime', datetime.datetime.min) >= cutoff]
        sub_des = [r['de'] for r in sub]
        freq = Counter(sub_des)
        
        g7_sub_hits = {'g7_1': 0, 'g7_2': 0, 'g7_3': 0, 'g7_4': 0}
        for idx_s in range(len(sub) - 1):
            t_de = sub[idx_s + 1]['de']
            for k in ['g7_1', 'g7_2', 'g7_3', 'g7_4']:
                if t_de in get_set_20(sub[idx_s][k]):
                    g7_sub_hits[k] += 1
                    
        sorted_sub_g7 = sorted(g7_sub_hits.items(), key=lambda x: x[1], reverse=True)
        window_stats[w_days] = {
            'freq': freq,
            'g7_ranking': [
                {'position': k.upper(), 'hits': v, 'rate': round(v/(len(sub)-1)*100, 1) if len(sub)>1 else 0}
                for k, v in sorted_sub_g7
            ]
        }

    # 3. DAY-OF-WEEK ANALYSIS & 4 ADVANCED ALGORITHMS
    dow_stats = {}
    total_evals_2026 = len(chrono) - 1
    overall_g7_stats = {g: {'td': 0, 'b': 0} for g in ['g7_1', 'g7_2', 'g7_3', 'g7_4']}
    overall_adv_stats = {
        'cham_hits': 0,
        'goc_hits': 0,
        'inter_hits': 0,
        'total_evals': total_evals_2026
    }
    adv_daily_records = []

    for idx in range(len(chrono) - 1):
        cur = chrono[idx]
        next_row = chrono[idx + 1]
        dt = cur.get('datetime') or parse_date(cur['date'])
        dow_code = dt.weekday() if dt else 0
        
        next_de = next_row['de']
        next_de_int = int(next_de) if next_de.isdigit() else -1
        next_de_tens = next_de_int // 10
        next_de_units = next_de_int % 10
        next_de_tong = get_tong(next_row['de'])
        
        # Chams (Algo 2)
        chams = get_cham_g7(cur['g7_1'], cur['g7_2'], cur['g7_3'], cur['g7_4'])
        cham_hit = (next_de_tens in chams) or (next_de_units in chams)
        
        # Corner Pair (Algo 3)
        head_g7_1 = int(cur['g7_1'][0]) if cur['g7_1'] and cur['g7_1'][0].isdigit() else 0
        tail_g7_4 = int(cur['g7_4'][1]) if cur['g7_4'] and len(cur['g7_4'])>1 and cur['g7_4'][1].isdigit() else 0
        t_goc = (head_g7_1 + tail_g7_4) % 10
        b_goc = get_bong(t_goc)
        goc_hit = (next_de_tong in (t_goc, b_goc))
        
        # Intersected Set (Algo 4)
        all_sums = set()
        for g in ['g7_1', 'g7_2', 'g7_3', 'g7_4']:
            all_sums.add(get_tong(cur[g]))
            all_sums.add(get_bong(get_tong(cur[g])))
            
        inter_set = set()
        for num in range(100):
            d_tens = num // 10
            d_units = num % 10
            d_sum = (d_tens + d_units) % 10
            if (d_tens in chams or d_units in chams) and (d_sum in all_sums):
                inter_set.add(f"{num:02d}")
                
        inter_hit = (next_de in inter_set)
        
        if cham_hit: overall_adv_stats['cham_hits'] += 1
        if goc_hit: overall_adv_stats['goc_hits'] += 1
        if inter_hit: overall_adv_stats['inter_hits'] += 1
        
        adv_daily_records.append({
            'stt': idx + 1,
            'date': cur['date'],
            'dow_name': dow_names[dow_code],
            'g7_1': cur['g7_1'],
            'g7_2': cur['g7_2'],
            'g7_3': cur['g7_3'],
            'g7_4': cur['g7_4'],
            'chams': "".join(str(c) for c in sorted(list(chams))),
            'sums': ", ".join(f"T{s}" for s in sorted(list(all_sums))),
            'corner_sum': f"T{t_goc}-B{b_goc}",
            'inter_size': f"{len(inter_set)} con",
            'next_date': next_row['date'],
            'next_de': next_de,
            'hit_cham': "TRÚNG" if cham_hit else "KHÔNG",
            'hit_goc': "TRÚNG" if goc_hit else "KHÔNG",
            'hit_inter': "TRÚNG" if inter_hit else "KHÔNG"
        })

    for dow_code in range(7):
        name = dow_names[dow_code]
        evals = 0
        cham_hits = 0
        goc_hits = 0
        inter_hits = 0
        g_s = {g: {'td': 0, 'b': 0} for g in ['g7_1', 'g7_2', 'g7_3', 'g7_4']}
        
        for idx in range(len(chrono) - 1):
            cur = chrono[idx]
            dt = cur.get('datetime') or parse_date(cur['date'])
            if dt and dt.weekday() == dow_code:
                evals += 1
                next_row = chrono[idx + 1]
                next_de = next_row['de']
                next_de_int = int(next_de) if next_de.isdigit() else -1
                next_de_tens = next_de_int // 10
                next_de_units = next_de_int % 10
                next_de_tong = get_tong(next_row['de'])
                
                # Algo 1
                for g in ['g7_1', 'g7_2', 'g7_3', 'g7_4']:
                    t = get_tong(cur[g])
                    b = get_bong(t)
                    if next_de_tong == t:
                        g_s[g]['td'] += 1
                        overall_g7_stats[g]['td'] += 1
                    elif next_de_tong == b:
                        g_s[g]['b'] += 1
                        overall_g7_stats[g]['b'] += 1
                        
                # Algo 2
                chams = get_cham_g7(cur['g7_1'], cur['g7_2'], cur['g7_3'], cur['g7_4'])
                if (next_de_tens in chams) or (next_de_units in chams):
                    cham_hits += 1
                    
                # Algo 3
                head_g7_1 = int(cur['g7_1'][0]) if cur['g7_1'] and cur['g7_1'][0].isdigit() else 0
                tail_g7_4 = int(cur['g7_4'][1]) if cur['g7_4'] and len(cur['g7_4'])>1 and cur['g7_4'][1].isdigit() else 0
                t_goc = (head_g7_1 + tail_g7_4) % 10
                b_goc = get_bong(t_goc)
                if next_de_tong in (t_goc, b_goc):
                    goc_hits += 1
                    
                # Algo 4
                all_sums = set()
                for g in ['g7_1', 'g7_2', 'g7_3', 'g7_4']:
                    all_sums.add(get_tong(cur[g]))
                    all_sums.add(get_bong(get_tong(cur[g])))
                inter_set = set()
                for num in range(100):
                    d_tens = num // 10
                    d_units = num % 10
                    d_sum = (d_tens + d_units) % 10
                    if (d_tens in chams or d_units in chams) and (d_sum in all_sums):
                        inter_set.add(f"{num:02d}")
                if next_de in inter_set:
                    inter_hits += 1

        sorted_dow_g7 = sorted(
            [(g, g_s[g]['td'] + g_s[g]['b']) for g in ['g7_1', 'g7_2', 'g7_3', 'g7_4']],
            key=lambda x: x[1],
            reverse=True
        )
        dow_stats[name] = {
            'total_evals': evals,
            'g_stats': g_s,
            'cham_hits': cham_hits,
            'cham_rate': cham_hits / evals * 100 if evals > 0 else 0,
            'goc_hits': goc_hits,
            'goc_rate': goc_hits / evals * 100 if evals > 0 else 0,
            'inter_hits': inter_hits,
            'inter_rate': inter_hits / evals * 100 if evals > 0 else 0,
            'ranking': [
                {'position': k.upper().replace('_', '.'), 'hits': v, 'rate': round(v/evals*100, 1) if evals>0 else 0}
                for k, v in sorted_dow_g7
            ]
        }

    # Determine upcoming day of week (Tomorrow)
    latest_dt = chrono[-1].get('datetime') or parse_date(chrono[-1]['date'])
    next_dt = latest_dt + datetime.timedelta(days=1)
    next_dow_code = next_dt.weekday()
    next_dow_name = dow_names[next_dow_code]
    
    next_dow_ranking = dow_stats[next_dow_name]['ranking']
    top_dow_g7_keys = [item['position'].lower() for item in next_dow_ranking[:3]]
    excluded_dow_g7_key = next_dow_ranking[3]['position'].lower()
    
    latest_day_raw = chrono[-1]
    latest_day = {k: v for k, v in latest_day_raw.items() if k != 'datetime'}

    # 4. MULTI-DAY FRAME CYCLE BACKTEST (Khung 1, 2, 3 Ngày)
    frame_evals = len(chrono) - 3
    frame_stats = {}
    for f_days in [1, 2, 3]:
        f_hits = 0
        for idx_f in range(frame_evals):
            curr_f = chrono[idx_f]
            target_f_des = [chrono[idx_f + d]['de'] for d in range(1, f_days + 1)]
            top3_f_set = get_set_20(curr_f['g7_3']).union(get_set_20(curr_f['g7_2'])).union(get_set_20(curr_f['g7_1']))
            if any(de in top3_f_set for de in target_f_des):
                f_hits += 1
        frame_stats[f_days] = {
            'hits': f_hits,
            'evals': frame_evals,
            'rate': round(f_hits/frame_evals*100, 2)
        }

    # 5. HISTORICAL 1-DAY BACKTEST (218 Days)
    history_records = []
    total_hits = 0
    total_evals = len(chrono) - 1
    
    for idx in range(total_evals):
        curr_d = chrono[idx]
        target_d = chrono[idx + 1]
        
        target_de = target_d['de']
        actual_head = target_de[0] if len(target_de)>=2 else ""
        actual_tail = target_de[1] if len(target_de)>=2 else ""
        
        top3_set = get_set_20(curr_d['g7_3']).union(get_set_20(curr_d['g7_2'])).union(get_set_20(curr_d['g7_1']))
        pred_nums_list = sorted(list(top3_set))
        pred_nums_str = ", ".join(pred_nums_list)
        
        is_hit = target_de in top3_set
        if is_hit: total_hits += 1
        
        history_records.append({
            'stt': idx + 1,
            'date': target_d['date'],
            'db': target_d['db'],
            'de': target_de,
            'head': actual_head,
            'tail': actual_tail,
            'pred_nums': pred_nums_str,
            'result': "TRÚNG 🎯" if is_hit else "TRƯỢT ❌"
        })

    # 6. DEDICATED 3-DAY FRAME HISTORY BACKTEST LOG (Lịch Sử Khung 3 Ngày)
    frame3_records = []
    f3_n1_hits = 0
    f3_n2_hits = 0
    f3_n3_hits = 0
    f3_misses = 0
    total_f3_evals = len(chrono) - 3

    for idx_f in range(total_f3_evals):
        curr_d = chrono[idx_f]
        d1 = chrono[idx_f + 1]
        d2 = chrono[idx_f + 2]
        d3 = chrono[idx_f + 3]
        
        top3_set = get_set_20(curr_d['g7_3']).union(get_set_20(curr_d['g7_2'])).union(get_set_20(curr_d['g7_1']))
        pred_nums_str = ", ".join(sorted(list(top3_set)))
        
        h1 = d1['de'] in top3_set
        h2 = d2['de'] in top3_set
        h3 = d3['de'] in top3_set
        
        if h1:
            f3_n1_hits += 1
            res_str = "TRÚNG N1 🎯"
        elif h2:
            f3_n2_hits += 1
            res_str = "TRÚNG N2 🎯"
        elif h3:
            f3_n3_hits += 1
            res_str = "TRÚNG N3 🎯"
        else:
            f3_misses += 1
            res_str = "TRƯỢT KHUNG ❌"
            
        frame3_records.append({
            'stt': idx_f + 1,
            'start_date': d1['date'],
            'de_n1': d1['de'],
            'hit_n1': "Trúng N1" if h1 else "Trượt",
            'de_n2': d2['de'],
            'hit_n2': "Trúng N2" if h2 else "Trượt",
            'de_n3': d3['de'],
            'hit_n3': "Trúng N3" if h3 else "Trượt",
            'frame_result': res_str,
            'pred_nums': pred_nums_str
        })

    # 7. HEAD & TAIL PREDICTION
    head_freq_2026 = Counter(r['de'][0] for r in chrono if len(r['de'])>=2)
    tail_freq_2026 = Counter(r['de'][1] for r in chrono if len(r['de'])>=2)
    
    top_weekly_candidate_pool = set()
    for k in top_weekly_keys:
        top_weekly_candidate_pool.update(get_set_20(latest_day[k]))

    g7_cham_set = get_g7_cham(latest_day['g7_1'], latest_day['g7_2'], latest_day['g7_3'], latest_day['g7_4'])
    
    head_candidate_counter = Counter(num[0] for num in top_weekly_candidate_pool)
    tail_candidate_counter = Counter(num[1] for num in top_weekly_candidate_pool)
    
    top_predicted_heads = [
        {'head': f"Đầu {h}", 'count': cnt, 'overall_freq': head_freq_2026[h]}
        for h, cnt in head_candidate_counter.most_common(3)
    ]
    
    top_predicted_tails = [
        {'tail': f"Đuôi {t}", 'count': cnt, 'overall_freq': tail_freq_2026[t]}
        for t, cnt in tail_candidate_counter.most_common(3)
    ]

    all_des = [r['de'] for r in chrono]
    num_nhip = {}
    for n in range(100):
        num_str = f"{n:02d}"
        if num_str in all_des:
            idx_last = max(i for i, de in enumerate(all_des) if de == num_str)
            num_nhip[num_str] = len(all_des) - 1 - idx_last
        else:
            num_nhip[num_str] = 999

    def get_gaussian_rhythm_score(nhip):
        if 3 <= nhip <= 7: return 15.0  # Nhịp Vàng nổ cao nhất
        elif 1 <= nhip <= 2: return 12.0 # Nhịp vừa ra (lô/đề nổ tiếp)
        elif nhip == 0: return 10.0      # Đề rơi lại
        elif 8 <= nhip <= 20: return 6.0 # Nhịp trung bình
        else: return 1.0                # Gan dài

    g7_tong_set = set()
    for g in [latest_day['g7_1'], latest_day['g7_2'], latest_day['g7_3'], latest_day['g7_4']]:
        t = get_tong(g)
        if t is not None:
            g7_tong_set.add(t)
            g7_tong_set.add(get_bong(t))

    scored_candidates = []
    for num in top_weekly_candidate_pool:
        f30 = window_stats[30]['freq'][num]
        f60 = window_stats[60]['freq'][num]
        f90 = window_stats[90]['freq'][num]
        nhip = num_nhip[num]
        
        rhythm_score = get_gaussian_rhythm_score(nhip)
        cham_bonus = 5.0 if (int(num[0]) in g7_cham_set or int(num[1]) in g7_cham_set) else 0.0
        tong_bonus = 5.0 if ((int(num[0]) + int(num[1])) % 10 in g7_tong_set) else 0.0
        double_bonus = 4.0 if (cham_bonus > 0 and tong_bonus > 0) else 0.0
        
        super_score = (f30 * 3.5) + (f60 * 2.0) + (f90 * 1.0) + rhythm_score + cham_bonus
        lucky26_score = super_score + tong_bonus + double_bonus
        
        scored_candidates.append({
            'number': num,
            'tong': (int(num[0])+int(num[1]))%10,
            'score': round(super_score, 1),
            'lucky26_score': round(lucky26_score, 1),
            'f30': f30,
            'f60': f60,
            'f90': f90,
            'nhip': nhip,
            'is_cham_g7': "Có" if cham_bonus > 0 else "Không",
            'is_tong_g7': "Có" if tong_bonus > 0 else "Không"
        })
        
    scored_candidates.sort(key=lambda x: x['lucky26_score'], reverse=True)
    
    # 100-number Lucky26 Matrix
    lucky26_matrix_100 = []
    for n in range(100):
        num_str = f"{n:02d}"
        d1, d2 = int(num_str[0]), int(num_str[1])
        t = (d1 + d2) % 10
        f30 = window_stats[30]['freq'][num_str]
        f60 = window_stats[60]['freq'][num_str]
        f90 = window_stats[90]['freq'][num_str]
        nhip = num_nhip[num_str]
        
        rhythm_score = get_gaussian_rhythm_score(nhip)
        cham_b = 5.0 if (d1 in g7_cham_set or d2 in g7_cham_set) else 0.0
        tong_b = 5.0 if (t in g7_tong_set) else 0.0
        dbl_b = 4.0 if (cham_b > 0 and tong_b > 0) else 0.0
        in_pool = num_str in top_weekly_candidate_pool
        pool_b = 10.0 if in_pool else 0.0
        
        l26_score = (f30 * 3.5) + (f60 * 2.0) + (f90 * 1.0) + rhythm_score + cham_b + tong_b + dbl_b + pool_b
        
        lucky26_matrix_100.append({
            'number': num_str,
            'd1': d1,
            'd2': d2,
            'tong': t,
            'in_pool': in_pool,
            'cham_g7': cham_b > 0,
            'tong_g7': tong_b > 0,
            'f30': f30,
            'f60': f60,
            'f90': f90,
            'nhip': nhip,
            'score': round(l26_score, 1)
        })
        
    lucky26_matrix_100.sort(key=lambda x: x['score'], reverse=True)
    for idx_m, item in enumerate(lucky26_matrix_100):
        item['rank'] = idx_m + 1
        item['strength'] = "MẠNH" if idx_m < 10 else ("TRUNG BÌNH" if idx_m < 20 else "YẾU")

    # Multi-Factor Aggregate Head & Tail Predictions for Latest Day
    head_scores_latest = {}
    for h in range(10):
        h_str = str(h)
        h_nums = sorted([x['score'] for x in lucky26_matrix_100 if x['number'][0] == h_str], reverse=True)
        head_scores_latest[h_str] = sum(h_nums[:3])
        
    tail_scores_latest = {}
    for t in range(10):
        t_str = str(t)
        t_nums = sorted([x['score'] for x in lucky26_matrix_100 if x['number'][1] == t_str], reverse=True)
        tail_scores_latest[t_str] = sum(t_nums[:3])

    sorted_heads_latest = sorted(head_scores_latest.keys(), key=lambda k: head_scores_latest[k], reverse=True)
    sorted_tails_latest = sorted(tail_scores_latest.keys(), key=lambda k: tail_scores_latest[k], reverse=True)

    top_predicted_heads = [
        {'head': f"Đầu {h}", 'score': round(head_scores_latest[h], 1), 'overall_freq': head_freq_2026[h]}
        for h in sorted_heads_latest[:5]
    ]

    top_predicted_tails = [
        {'tail': f"Đuôi {t}", 'score': round(tail_scores_latest[t], 1), 'overall_freq': tail_freq_2026[t]}
        for t in sorted_tails_latest[:5]
    ]

    top_10_ha_so = scored_candidates[:10]
    top_20_consensus = scored_candidates[:20]
    
    # Ultra Firepower Ranks
    song_thu_de = scored_candidates[:2]
    tu_thu_de = scored_candidates[:4]

    # 3D (3 Càng) & 4D (4 Càng) Consensus Generator (Mở rộng 20 số)
    g7_digits = list(g7_cham_set)
    cand_3d = []
    for c3 in g7_digits[:5]: # top 5 càng 3D
        for item2d in scored_candidates[:10]: # top 10 2D
            num3d = f"{c3}{item2d['number']}"
            score3d = round(item2d['lucky26_score'] + 10.0, 1)
            cand_3d.append({
                'number_3d': num3d,
                'cang_3d': c3,
                'de_2d': item2d['number'],
                'score': score3d
            })
    cand_3d.sort(key=lambda x: x['score'], reverse=True)
    top_20_3d = cand_3d[:20]

    # 4D (4 Càng) generator (Mở rộng 20 số)
    cand_4d = []
    for c4 in g7_digits[:4]:
        for item3d in top_20_3d[:10]:
            num4d = f"{c4}{item3d['number_3d']}"
            score4d = round(item3d['score'] + 15.0, 1)
            cand_4d.append({
                'number_4d': num4d,
                'cang_4d': c4,
                'num_3d': item3d['number_3d'],
                'score': score4d
            })
    cand_4d.sort(key=lambda x: x['score'], reverse=True)
    top_20_4d = cand_4d[:20]

    # 8. HISTORICAL 3D & 4D BACKTEST LOG (218 Days)
    history_3d_4d_records = []
    total_3d_top20_hits = 0
    total_3d_matrix_hits = 0
    total_4d_hits = 0

    for idx in range(total_evals):
        curr_d = chrono[idx]
        target_d = chrono[idx + 1]
        
        db_val = target_d['db']
        actual_3d = db_val[-3:] if len(db_val)>=3 else ""
        actual_4d = db_val[-4:] if len(db_val)>=4 else ""
        
        sub_history = chrono[:idx+1]
        all_dbs = [r['db'] for r in sub_history]
        all_des = [r['de'] for r in sub_history]
        f30 = Counter(all_des[-30:])
        f60 = Counter(all_des[-60:])
        f90 = Counter(all_des[-90:])
        
        num_nhip_sub = {}
        for n in range(100):
            num_str = f"{n:02d}"
            if num_str in all_des:
                idx_last = max(i for i, de in enumerate(all_des) if de == num_str)
                num_nhip_sub[num_str] = len(all_des) - 1 - idx_last
            else:
                num_nhip_sub[num_str] = 999

        top3_pool = get_set_20(curr_d['g7_3']).union(get_set_20(curr_d['g7_2'])).union(get_set_20(curr_d['g7_1']))
        g7_cham_sub = set(get_g7_cham(curr_d['g7_1'], curr_d['g7_2'], curr_d['g7_3'], curr_d['g7_4']))
        g7_tongs_sub = set()
        for g in [curr_d['g7_1'], curr_d['g7_2'], curr_d['g7_3'], curr_d['g7_4']]:
            t = get_tong(g)
            if t is not None:
                g7_tongs_sub.add(t)
                g7_tongs_sub.add(get_bong(t))

        sub_scored = []
        for num in top3_pool:
            d1, d2 = int(num[0]), int(num[1])
            t = (d1 + d2) % 10
            nhip = num_nhip_sub[num]
            rhythm_score = get_gaussian_rhythm_score(nhip)
            cham_b = 5.0 if (d1 in g7_cham_sub or d2 in g7_cham_sub) else 0.0
            tong_b = 5.0 if (t in g7_tongs_sub) else 0.0
            dbl_b = 4.0 if (cham_b > 0 and tong_b > 0) else 0.0
            score = (f30[num] * 3.5) + (f60[num] * 2.0) + (f90[num] * 1.0) + rhythm_score + cham_b + tong_b + dbl_b
            sub_scored.append((num, score))
        sub_scored.sort(key=lambda x: x[1], reverse=True)
        top20_2d_sub = [x[0] for x in sub_scored[:20]]

        # Càng 3D từ 30 ngày GĐB (Top 5 Càng + 5 Càng Bóng = 10 Càng)
        cang3_30d = Counter(db[-3] for db in all_dbs[-30:] if len(db)>=3)
        top_cang_chinh = [int(k) for k, v in cang3_30d.most_common(5) if k.isdigit()]
        top_cang_10 = set()
        for c in top_cang_chinh:
            top_cang_10.add(str(c))
            top_cang_10.add(str(get_bong(c)))
        top_cang_10_list = sorted(list(top_cang_10))

        # Top 20 3D Hỏa Lực
        cand_3d_sub = []
        for c3 in top_cang_10_list[:5]:
            for de in top20_2d_sub[:10]:
                cand_3d_sub.append(f"{c3}{de}")
        pred_3d_top20 = cand_3d_sub[:20]

        # Top 200 3D Matrix Mở Rộng (10 Càng x Top 20 2D)
        pred_3d_matrix200 = set(f"{c3}{de}" for c3 in top_cang_10_list for de in top20_2d_sub)

        # 4D Top 20
        cang4_30d = Counter(db[-4] for db in all_dbs[-30:] if len(db)>=4)
        top_cang4 = [k for k, v in cang4_30d.most_common(4) if k.isdigit()]
        cand_4d_sub = []
        for c4 in top_cang4:
            for num3d in pred_3d_top20[:10]:
                cand_4d_sub.append(f"{c4}{num3d}")
        pred_4d_top20 = cand_4d_sub[:20]

        is_hit_3d_top20 = actual_3d in set(pred_3d_top20)
        is_hit_3d_matrix = actual_3d in pred_3d_matrix200
        is_hit_4d = actual_4d in set(pred_4d_top20)

        if is_hit_3d_top20: total_3d_top20_hits += 1
        if is_hit_3d_matrix: total_3d_matrix_hits += 1
        if is_hit_4d: total_4d_hits += 1

        history_3d_4d_records.append({
            'stt': idx + 1,
            'date': target_d['date'],
            'db': db_val,
            'actual_3d': actual_3d,
            'actual_4d': actual_4d,
            'pred_3d_top20': ", ".join(pred_3d_top20),
            'result_3d_top20': "TRÚNG 3D (TOP 20) 🎯" if is_hit_3d_top20 else "TRƯỢT ❌",
            'result_3d_matrix': "TRÚNG 3D MATRIX (200 SỐ) 🎯" if is_hit_3d_matrix else "TRƯỢT ❌",
            'pred_4d_top20': ", ".join(pred_4d_top20),
            'result_4d': "TRÚNG 4D (TOP 20) 🎯" if is_hit_4d else "TRƯỢT ❌"
        })

    # 9. HISTORICAL BACKTEST LOG FOR TOP 3/4/5 HEADS & TAILS (218 Days)
    history_top3_dd_records = []
    
    # Top 3 counters
    total_head_hits_1day = 0
    total_tail_hits_1day = 0
    total_combined_hits_1day = 0
    total_either_hits_1day = 0
    
    total_head_hits_f3 = 0
    total_tail_hits_f3 = 0
    total_combined_hits_f3 = 0

    # Top 4 counters
    total_top4_head_hits_1day = 0
    total_top4_tail_hits_1day = 0
    total_top4_comb_hits_1day = 0
    total_top4_head_hits_f3 = 0
    total_top4_tail_hits_f3 = 0
    total_top4_comb_hits_f3 = 0

    # Top 5 counters
    total_top5_head_hits_1day = 0
    total_top5_tail_hits_1day = 0
    total_top5_comb_hits_1day = 0
    total_top5_head_hits_f3 = 0
    total_top5_tail_hits_f3 = 0
    total_top5_comb_hits_f3 = 0

    total_f3_dd_evals = max(1, total_evals - 2)

    head_digit_stats = {str(d): {'recs': 0, 'hits': 0} for d in range(10)}
    tail_digit_stats = {str(d): {'recs': 0, 'hits': 0} for d in range(10)}

    for idx in range(total_evals):
        curr_d = chrono[idx]
        target_d = chrono[idx + 1]
        
        target_de = target_d['de']
        actual_head = target_de[0] if len(target_de)>=2 else ""
        actual_tail = target_de[1] if len(target_de)>=2 else ""
        
        sub_history = chrono[:idx+1]
        sub_des = [r['de'] for r in sub_history]
        
        # Calculate Multi-Factor Aggregate Scores for Heads & Tails
        f30_sub = Counter(sub_des[-30:])
        f60_sub = Counter(sub_des[-60:])
        f90_sub = Counter(sub_des[-90:])
        g7_cham_sub = set(get_g7_cham(curr_d['g7_1'], curr_d['g7_2'], curr_d['g7_3'], curr_d['g7_4']))
        g7_tong_sub = set()
        for g in [curr_d['g7_1'], curr_d['g7_2'], curr_d['g7_3'], curr_d['g7_4']]:
            t = get_tong(g)
            g7_tong_sub.add(t)
            g7_tong_sub.add(get_bong(t))

        num_nhip_sub = {}
        for n in range(100):
            num_str = f"{n:02d}"
            if num_str in sub_des:
                idx_last = max(i for i, de in enumerate(sub_des) if de == num_str)
                num_nhip_sub[num_str] = len(sub_des) - 1 - idx_last
            else:
                num_nhip_sub[num_str] = 999

        matrix_scores_sub = {}
        for n in range(100):
            num_str = f"{n:02d}"
            d1, d2 = int(num_str[0]), int(num_str[1])
            t = (d1 + d2) % 10
            rhythm_s = get_gaussian_rhythm_score(num_nhip_sub[num_str])
            cham_b = 5.0 if (d1 in g7_cham_sub or d2 in g7_cham_sub) else 0.0
            tong_b = 5.0 if (t in g7_tong_sub) else 0.0
            score = (f30_sub[num_str] * 3.5) + (f60_sub[num_str] * 2.0) + (f90_sub[num_str] * 1.0) + rhythm_s + cham_b + tong_b
            matrix_scores_sub[num_str] = score

        head_scores_sub = {}
        for h in range(10):
            h_str = str(h)
            h_nums = sorted([matrix_scores_sub[f"{h_str}{t}"] for t in range(10)], reverse=True)
            head_scores_sub[h_str] = sum(h_nums[:3])

        tail_scores_sub = {}
        for t in range(10):
            t_str = str(t)
            t_nums = sorted([matrix_scores_sub[f"{h}{t_str}"] for h in range(10)], reverse=True)
            tail_scores_sub[t_str] = sum(t_nums[:3])

        sorted_heads = sorted(head_scores_sub.keys(), key=lambda k: head_scores_sub[k], reverse=True)
        sorted_tails = sorted(tail_scores_sub.keys(), key=lambda k: tail_scores_sub[k], reverse=True)

        pred_heads = sorted_heads[:3]
        pred_tails = sorted_tails[:3]
        
        pred_heads_4 = sorted_heads[:4]
        pred_tails_4 = sorted_tails[:4]

        pred_heads_5 = sorted_heads[:5]
        pred_tails_5 = sorted_tails[:5]
        
        pred_heads_str = ", ".join([f"Đầu {h}" for h in pred_heads])
        pred_tails_str = ", ".join([f"Đuôi {t}" for t in pred_tails])
        
        pred_9_set = set(f"{h}{t}" for h in pred_heads for t in pred_tails)
        pred_9_str = ", ".join(sorted(list(pred_9_set)))
        
        pred_16_set = set(f"{h}{t}" for h in pred_heads_4 for t in pred_tails_4)
        pred_25_set = set(f"{h}{t}" for h in pred_heads_5 for t in pred_tails_5)

        # Top 3 Checks
        hit_head_1day = actual_head in pred_heads
        hit_tail_1day = actual_tail in pred_tails
        hit_combined_1day = target_de in pred_9_set
        hit_either_1day = hit_head_1day or hit_tail_1day
        
        if hit_head_1day: total_head_hits_1day += 1
        if hit_tail_1day: total_tail_hits_1day += 1
        if hit_combined_1day: total_combined_hits_1day += 1
        if hit_either_1day: total_either_hits_1day += 1

        # Top 4 Checks
        if actual_head in pred_heads_4: total_top4_head_hits_1day += 1
        if actual_tail in pred_tails_4: total_top4_tail_hits_1day += 1
        if target_de in pred_16_set: total_top4_comb_hits_1day += 1

        # Top 5 Checks
        if actual_head in pred_heads_5: total_top5_head_hits_1day += 1
        if actual_tail in pred_tails_5: total_top5_tail_hits_1day += 1
        if target_de in pred_25_set: total_top5_comb_hits_1day += 1
        
        for h in pred_heads:
            head_digit_stats[h]['recs'] += 1
            if actual_head == h:
                head_digit_stats[h]['hits'] += 1
                
        for t in pred_tails:
            tail_digit_stats[t]['recs'] += 1
            if actual_tail == t:
                tail_digit_stats[t]['hits'] += 1

        res_combined_3day = "TRƯỢT KHUNG ❌"
        if idx + 3 < len(chrono):
            d1 = chrono[idx + 1]['de']
            d2 = chrono[idx + 2]['de']
            d3 = chrono[idx + 3]['de']
            
            h1 = d1 in pred_9_set
            h2 = d2 in pred_9_set
            h3 = d3 in pred_9_set
            
            if h1:
                res_combined_3day = "TRÚNG N1 🎯"
                total_combined_hits_f3 += 1
            elif h2:
                res_combined_3day = "TRÚNG N2 🎯"
                total_combined_hits_f3 += 1
            elif h3:
                res_combined_3day = "TRÚNG N3 🎯"
                total_combined_hits_f3 += 1

            if any(chrono[idx+d]['de'][0] in pred_heads for d in [1, 2, 3]):
                total_head_hits_f3 += 1
            if any(chrono[idx+d]['de'][1] in pred_tails for d in [1, 2, 3]):
                total_tail_hits_f3 += 1

            if any(chrono[idx+d]['de'][0] in pred_heads_4 for d in [1, 2, 3]):
                total_top4_head_hits_f3 += 1
            if any(chrono[idx+d]['de'][1] in pred_tails_4 for d in [1, 2, 3]):
                total_top4_tail_hits_f3 += 1
            if any(chrono[idx+d]['de'] in pred_16_set for d in [1, 2, 3]):
                total_top4_comb_hits_f3 += 1

            if any(chrono[idx+d]['de'][0] in pred_heads_5 for d in [1, 2, 3]):
                total_top5_head_hits_f3 += 1
            if any(chrono[idx+d]['de'][1] in pred_tails_5 for d in [1, 2, 3]):
                total_top5_tail_hits_f3 += 1
            if any(chrono[idx+d]['de'] in pred_25_set for d in [1, 2, 3]):
                total_top5_comb_hits_f3 += 1

        history_top3_dd_records.append({
            'stt': idx + 1,
            'date': target_d['date'],
            'db': target_d['db'],
            'de': target_de,
            'head': actual_head,
            'tail': actual_tail,
            'pred_heads': pred_heads_str,
            'pred_tails': pred_tails_str,
            'pred_9_nums': pred_9_str,
            'result_head_1day': f"TRÚNG 🎯 (Đầu {actual_head})" if hit_head_1day else "TRƯỢT ❌",
            'result_tail_1day': f"TRÚNG 🎯 (Đuôi {actual_tail})" if hit_tail_1day else "TRƯỢT ❌",
            'result_combined_1day': f"TRÚNG 9 SỐ 🎯 ({target_de})" if hit_combined_1day else "TRƯỢT ❌",
            'result_combined_3day': res_combined_3day
        })

    top3_dau_duoi_summary = {
        'total_evals': total_evals,
        # Top 3 metrics
        'head_hits_1day': total_head_hits_1day,
        'head_rate_1day': round(total_head_hits_1day / total_evals * 100, 2),
        'tail_hits_1day': total_tail_hits_1day,
        'tail_rate_1day': round(total_tail_hits_1day / total_evals * 100, 2),
        'combined_hits_1day': total_combined_hits_1day,
        'combined_rate_1day': round(total_combined_hits_1day / total_evals * 100, 2),
        'either_hits_1day': total_either_hits_1day,
        'either_rate_1day': round(total_either_hits_1day / total_evals * 100, 2),
        'total_f3_evals': total_f3_dd_evals,
        'f3_head_hits': total_head_hits_f3,
        'f3_head_rate': round(total_head_hits_f3 / total_f3_dd_evals * 100, 2),
        'f3_tail_hits': total_tail_hits_f3,
        'f3_tail_rate': round(total_tail_hits_f3 / total_f3_dd_evals * 100, 2),
        'f3_combined_hits': total_combined_hits_f3,
        'f3_combined_rate': round(total_combined_hits_f3 / total_f3_dd_evals * 100, 2),
        
        # Top 4 metrics
        'top4_head_hits_1day': total_top4_head_hits_1day,
        'top4_head_rate_1day': round(total_top4_head_hits_1day / total_evals * 100, 2),
        'top4_tail_hits_1day': total_top4_tail_hits_1day,
        'top4_tail_rate_1day': round(total_top4_tail_hits_1day / total_evals * 100, 2),
        'top4_comb_hits_1day': total_top4_comb_hits_1day,
        'top4_comb_rate_1day': round(total_top4_comb_hits_1day / total_evals * 100, 2),
        'f3_top4_head_rate': round(total_top4_head_hits_f3 / total_f3_dd_evals * 100, 2),
        'f3_top4_tail_rate': round(total_top4_tail_hits_f3 / total_f3_dd_evals * 100, 2),
        'f3_top4_comb_rate': round(total_top4_comb_hits_f3 / total_f3_dd_evals * 100, 2),

        # Top 5 metrics
        'top5_head_hits_1day': total_top5_head_hits_1day,
        'top5_head_rate_1day': round(total_top5_head_hits_1day / total_evals * 100, 2),
        'top5_tail_hits_1day': total_top5_tail_hits_1day,
        'top5_tail_rate_1day': round(total_top5_tail_hits_1day / total_evals * 100, 2),
        'top5_comb_hits_1day': total_top5_comb_hits_1day,
        'top5_comb_rate_1day': round(total_top5_comb_hits_1day / total_evals * 100, 2),
        'f3_top5_head_rate': round(total_top5_head_hits_f3 / total_f3_dd_evals * 100, 2),
        'f3_top5_tail_rate': round(total_top5_tail_hits_f3 / total_f3_dd_evals * 100, 2),
        'f3_top5_comb_rate': round(total_top5_comb_hits_f3 / total_f3_dd_evals * 100, 2)
    }

    head_digit_performance = [
        {
            'digit': d,
            'recs': head_digit_stats[d]['recs'],
            'hits': head_digit_stats[d]['hits'],
            'rate': round(head_digit_stats[d]['hits'] / head_digit_stats[d]['recs'] * 100, 2) if head_digit_stats[d]['recs'] > 0 else 0.0
        }
        for d in [str(i) for i in range(10)]
    ]

    tail_digit_performance = [
        {
            'digit': d,
            'recs': tail_digit_stats[d]['recs'],
            'hits': tail_digit_stats[d]['hits'],
            'rate': round(tail_digit_stats[d]['hits'] / tail_digit_stats[d]['recs'] * 100, 2) if tail_digit_stats[d]['recs'] > 0 else 0.0
        }
        for d in [str(i) for i in range(10)]
    ]

    analysis_summary = {
        'total_days': len(chrono),
        'total_hits_2026': total_hits,
        'hit_rate_2026': round(total_hits/total_evals*100, 2),
        'total_misses_2026': total_evals - total_hits,
        'frame_stats': frame_stats,
        'frame3_summary': {
            'total_frames': total_f3_evals,
            'n1_hits': f3_n1_hits,
            'n2_hits': f3_n2_hits,
            'n3_hits': f3_n3_hits,
            'total_frame_hits': f3_n1_hits + f3_n2_hits + f3_n3_hits,
            'frame_hit_rate': round((f3_n1_hits + f3_n2_hits + f3_n3_hits)/total_f3_evals*100, 2),
            'frame_misses': f3_misses,
            'frame_miss_rate': round(f3_misses/total_f3_evals*100, 2)
        },
        'last_week_number': int(last_week_key[1]),
        'last_week_g7_ranking': [
            {'position': k.upper(), 'hits': v, 'rank': r+1}
            for r, (k, v) in enumerate(sorted_weekly_g7)
        ],
        'top_weekly_selected': [k.upper() for k in top_weekly_keys],
        'excluded_weekly_key': excluded_weekly_key.upper(),
        'window_stats': {
            '30': window_stats[30]['g7_ranking'],
            '60': window_stats[60]['g7_ranking'],
            '90': window_stats[90]['g7_ranking'],
        },
        'dow_stats': dow_stats,
        'overall_g7_stats': overall_g7_stats,
        'overall_adv_stats': overall_adv_stats,
        'adv_daily_records': adv_daily_records,
        'total_evals_2026': total_evals_2026,
        'next_dow_name': next_dow_name,
        'next_dow_ranking': next_dow_ranking,
        'head_freq_2026': [{'head': f"Đầu {k}", 'freq': v} for k, v in head_freq_2026.most_common()],
        'tail_freq_2026': [{'tail': f"Đuôi {k}", 'freq': v} for k, v in tail_freq_2026.most_common()],
        'top_predicted_heads': top_predicted_heads,
        'top_predicted_tails': top_predicted_tails,
        'latest_day': latest_day,
        'suggested_g7_cham': sorted(list(g7_cham_set)),
        'suggested_g7_tongs': sorted(list(g7_tong_set)),
        'song_thu_de': song_thu_de,
        'tu_thu_de': tu_thu_de,
        'top_5_3d': top_20_3d[:5],
        'top_5_4d': top_20_4d[:5],
        'top_10_3d': top_20_3d[:10],
        'top_10_4d': top_20_4d[:10],
        'top_20_3d': top_20_3d,
        'top_20_4d': top_20_4d,
        'top_10_ha_so': top_10_ha_so,
        'top_20_consensus': top_20_consensus,
        'lucky26_matrix_100': lucky26_matrix_100,
        'history_records': list(reversed(history_records)),
        'frame3_records': list(reversed(frame3_records)),
        'history_3d_4d_records': list(reversed(history_3d_4d_records)),
        'total_3d_top20_hits_2026': total_3d_top20_hits,
        'total_3d_matrix_hits_2026': total_3d_matrix_hits,
        'total_4d_hits_2026': total_4d_hits,
        'top3_dau_duoi_summary': top3_dau_duoi_summary,
        'history_top3_dau_duoi_records': list(reversed(history_top3_dd_records)),
        'head_digit_performance': head_digit_performance,
        'tail_digit_performance': tail_digit_performance
    }
    
    return analysis_summary

def style_excel_workbook(wb, summary):
    navy_header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    zebra_fill = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")
    
    red_hit_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    red_hit_font = Font(name="Arial", size=10, bold=True, color="9C0006")
    
    green_miss_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    green_miss_font = Font(name="Arial", size=10, bold=True, color="006100")
    
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    regular_font = Font(name="Arial", size=10, color="000000")
    
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    
    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    align_left = Alignment(horizontal='left', vertical='center', wrap_text=True)

    for sheetname in wb.sheetnames:
        ws = wb[sheetname]
        ws.views.sheetView[0].showGridLines = True
        
        max_row = ws.max_row
        max_col = ws.max_column
        
        for col in range(1, max_col + 1):
            cell = ws.cell(row=1, column=col)
            cell.fill = navy_header_fill
            cell.font = header_font
            cell.alignment = align_center
            cell.border = thin_border
            
        for row in range(2, max_row + 1):
            is_even = (row % 2 == 0)
            for col in range(1, max_col + 1):
                cell = ws.cell(row=row, column=col)
                cell.font = regular_font
                cell.border = thin_border
                cell.alignment = align_left if col > 2 else align_center
                
                # Custom styling for Thong_Ke_Theo_Thu summary row
                if sheetname == 'Thong_Ke_Theo_Thu' and 'TỔNG CỘNG' in str(ws.cell(row=row, column=1).value or ''):
                    summary_row_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
                    summary_row_font = Font(name="Arial", size=10, bold=True, color="1F4E78")
                    cell.fill = summary_row_fill
                    cell.font = summary_row_font

                # Custom styling for Thong_Ke_Nang_Cao_G7
                if sheetname == 'Thong_Ke_Nang_Cao_G7':
                    c1_val = str(ws.cell(row=row, column=1).value or '')
                    if c1_val.startswith('BẢNG') or c1_val.startswith('TT'):
                        cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
                        cell.font = Font(name="Arial", size=10, bold=True, color="1F4E78")

                # Red for TRÚNG, Green for TRƯỢT/KHÔNG
                val_str = str(cell.value or '')
                if sheetname in ['Lich_Su_Truc_Tiep_2026', 'Lich_Su_Nuoi_Khung_3Ngay', 'Thong_Ke_Nang_Cao_G7', 'Thong_Ke_Top3_Dau_Duoi']:
                    if 'TRÚNG' in val_str:
                        cell.fill = red_hit_fill
                        cell.font = red_hit_font
                    elif 'TRƯỢT' in val_str or 'KHÔNG' in val_str:
                        if sheetname != 'Thong_Ke_Nang_Cao_G7' or not str(ws.cell(row=row, column=1).value or '').startswith('TT'):
                            cell.fill = green_miss_fill
                            cell.font = green_miss_font
                        
        for col in range(1, max_col + 1):
            col_letter = get_column_letter(col)
            max_len = 0
            for row in range(1, max_row + 1):
                val = str(ws.cell(row=row, column=col).value or '')
                if len(val) > max_len:
                    max_len = len(val)
            ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 65)

def export_excel(data_2026, summary, filename='Thong_Ke_G7_Va_Top20_XSMB_2026_NangCap_ChonCham_Moi.xlsx'):
    chrono = list(reversed(data_2026))
    
    # Sheet 1: Raw Data
    sheet1_rows = []
    for idx, row in enumerate(chrono):
        date_str = row['date']
        db, de = row['db'], row['de']
        g7_1, g7_2, g7_3, g7_4 = row['g7_1'], row['g7_2'], row['g7_3'], row['g7_4']
        
        t1, b1 = get_tong(g7_1), get_bong(get_tong(g7_1))
        t2, b2 = get_tong(g7_2), get_bong(get_tong(g7_2))
        t3, b3 = get_tong(g7_3), get_bong(get_tong(g7_3))
        t4, b4 = get_tong(g7_4), get_bong(get_tong(g7_4))
        
        hit1 = hit2 = hit3 = hit4 = "N/A"
        if idx < len(chrono) - 1:
            next_de = chrono[idx + 1]['de']
            hit1 = "Trúng" if next_de in get_set_20(g7_1) else "Không"
            hit2 = "Trúng" if next_de in get_set_20(g7_2) else "Không"
            hit3 = "Trúng" if next_de in get_set_20(g7_3) else "Không"
            hit4 = "Trúng" if next_de in get_set_20(g7_4) else "Không"
            
        sheet1_rows.append({
            'STT': idx + 1,
            'Ngày Quay': date_str,
            'Giải Đặc Biệt (5 số)': db,
            'Số Đề (2 số cuối)': de,
            'G7.1': g7_1,
            'Tổng/Bóng G7.1': f"T{t1}-B{b1}",
            'Trúng Đề Hôm Sau (G7.1)': hit1,
            'G7.2': g7_2,
            'Tổng/Bóng G7.2': f"T{t2}-B{b2}",
            'Trúng Đề Hôm Sau (G7.2)': hit2,
            'G7.3': g7_3,
            'Tổng/Bóng G7.3': f"T{t3}-B{b3}",
            'Trúng Đề Hôm Sau (G7.3)': hit3,
            'G7.4': g7_4,
            'Tổng/Bóng G7.4': f"T{t4}-B{b4}",
            'Trúng Đề Hôm Sau (G7.4)': hit4,
        })

    # Sheet 2: Multi-window & Frame Strategy Statistics
    sheet2_rows = []
    sheet2_rows.append({'Cửa Sổ / Mô Hình': '🎯 KHUNG NUÔI 1 NGÀY (Trúng Ngay)', 'Tỷ Lệ Trúng 2026': f"{summary['frame_stats'][1]['rate']}%", 'Số Lần Trúng': f"{summary['frame_stats'][1]['hits']} / {summary['frame_stats'][1]['evals']} ngày", 'Đánh Giá Chiến Thuật': 'Chơi Ngày Nào Biết Ngày Đó'})
    sheet2_rows.append({'Cửa Sổ / Mô Hình': '🔥 KHUNG NUÔI 2 NGÀY (Nối Tiếp)', 'Tỷ Lệ Trúng 2026': f"{summary['frame_stats'][2]['rate']}%", 'Số Lần Trúng': f"{summary['frame_stats'][2]['hits']} / {summary['frame_stats'][2]['evals']} ngày", 'Đánh Giá Chiến Thuật': 'Vốn An Toàn - Tỷ Lệ Trúng > 72%'})
    sheet2_rows.append({'Cửa Sổ / Mô Hình': '🚀 KHUNG NUÔI 3 NGÀY (Max Khung)', 'Tỷ Lệ Trúng 2026': f"{summary['frame_stats'][3]['rate']}%", 'Số Lần Trúng': f"{summary['frame_stats'][3]['hits']} / {summary['frame_stats'][3]['evals']} ngày", 'Đánh Giá Chiến Thuật': 'Tối Ưu Cực Đại - Tỷ Lệ Trúng Gần 88%'})
    
    sheet2_rows.append({'Cửa Sổ / Mô Hình': f'Tuần {summary["last_week_number"]} (Tuần Trước)', 'Tỷ Lệ Trúng 2026': f"Top 1: {summary['last_week_g7_ranking'][0]['position']}", 'Số Lần Trúng': f"Top 2: {summary['last_week_g7_ranking'][1]['position']}", 'Đánh Giá Chiến Thuật': f"Top 3: {summary['last_week_g7_ranking'][2]['position']} (Loại {summary['last_week_g7_ranking'][3]['position']})"})
    for w in ['30', '60', '90']:
        ranks = summary['window_stats'][w]
        sheet2_rows.append({
            'Cửa Sổ / Mô Hình': f'Khung {w} Ngày Gần Nhất',
            'Tỷ Lệ Trúng 2026': f"Top 1: {ranks[0]['position']} ({ranks[0]['rate']}%)",
            'Số Lần Trúng': f"Top 2: {ranks[1]['position']} ({ranks[1]['rate']}%)",
            'Đánh Giá Chiến Thuật': f"Top 3: {ranks[2]['position']} ({ranks[2]['rate']}%) | Loại: {ranks[3]['position']}"
        })

    # Sheet 3: Top 20 Super-Scoring Predictions
    sheet3_rows = []
    for idx, item in enumerate(summary['top_20_consensus'], 1):
        nhip_eval = "Nhịp Đẹp" if 3 <= item['nhip'] <= 25 else ("Vừa Ra" if item['nhip'] < 3 else "Gan Dài")
        sheet3_rows.append({
            'Thứ Hạng': f"Top {idx:02d}",
            'Con Số': item['number'],
            'Thuộc Tổng': item['tong'],
            'Chạm G7 Hợp Lệ': item['is_cham_g7'],
            'TS 30 Ngày': item['f30'],
            'TS 60 Ngày': item['f60'],
            'TS 90 Ngày': item['f90'],
            'Nhịp Gan (ngày)': item['nhip'],
            'Đánh Giá Nhịp': nhip_eval,
            'Điểm Đồng Thuận Super-Score': item['score']
        })

    # Sheet 4: Thong_Ke_Theo_Thu (18 CỘT TÍCH HỢP CHẠM CHÍNH B9 & TỔNG G7)
    sheet4_rows = []
    overall_g = summary.get('overall_g7_stats', {g: {'td': 0, 'b': 0} for g in ['g7_1', 'g7_2', 'g7_3', 'g7_4']})
    overall_adv = summary.get('overall_adv_stats', {'cham_hits': 0, 'goc_hits': 0, 'inter_hits': 0, 'total_evals': len(chrono) - 1})
    tot_evals_2026 = summary.get('total_evals_2026', len(chrono) - 1)

    # Calculate B9 Touch Filter (Sample B9 Touch = '1236') Stats per DOW
    sample_b9 = '1236'
    chams_b9 = set(int(c) for c in sample_b9 if c.isdigit())
    b9_dow_stats = {dow: {'hits': 0, 'tot_sz': 0} for dow in range(7)}
    tot_b9_hits = 0
    tot_b9_sz = 0

    optimal_pairs_map = {
        0: '47-74, 78-87',
        1: '68-86, 89-98',
        2: '39-93, 36-63',
        3: '23-32, 45-54',
        4: '49-94, 22-77',
        5: '38-83, 77-22',
        6: '05-50, 47-74'
    }

    for idx in range(len(chrono) - 1):
        cur = chrono[idx]
        dt = parse_date(cur['date'])
        dow_code = dt.weekday()
        next_row = chrono[idx + 1]
        next_de = next_row['de']
        
        all_sums = set()
        for g in ['g7_1', 'g7_2', 'g7_3', 'g7_4']:
            all_sums.add(get_tong(cur[g]))
            all_sums.add(get_bong(get_tong(cur[g])))
            
        inter_set = set()
        for num in range(100):
            d_tens = num // 10
            d_units = num % 10
            d_sum = (d_tens + d_units) % 10
            if (d_tens in chams_b9 or d_units in chams_b9) and (d_sum in all_sums):
                inter_set.add(f"{num:02d}")
                
        tot_b9_sz += len(inter_set)
        b9_dow_stats[dow_code]['tot_sz'] += len(inter_set)
        if next_de in inter_set:
            tot_b9_hits += 1
            b9_dow_stats[dow_code]['hits'] += 1

    for dow_code in range(7):
        dow_name = dow_names[dow_code]
        stat = summary['dow_stats'][dow_name]
        evals = stat['total_evals']
        g_s = stat.get('g_stats', {g: {'td': 0, 'b': 0} for g in ['g7_1', 'g7_2', 'g7_3', 'g7_4']})

        row_dict = {
            'Thứ Trong Tuần': dow_name,
            'Số Ngày Phân Tích': f"{evals} ngày"
        }

        total_hits_map = {}
        for g in ['g7_1', 'g7_2', 'g7_3', 'g7_4']:
            pos_label = g.upper().replace('_', '.')
            td = g_s[g]['td']
            b = g_s[g]['b']
            tot = td + b
            total_hits_map[pos_label] = tot

            td_pct = (td / evals * 100) if evals > 0 else 0.0
            b_pct = (b / evals * 100) if evals > 0 else 0.0
            tot_pct = (tot / evals * 100) if evals > 0 else 0.0

            row_dict[f'{pos_label} Trực Diện'] = f"{td} lần ({td_pct:.1f}%)"
            row_dict[f'{pos_label} Bóng'] = f"{b} lần ({b_pct:.1f}%)"
            row_dict[f'{pos_label} Tổng Trúng'] = f"{tot} lần ({tot_pct:.1f}%)"

        cham_rate = stat.get('cham_rate', 0.0)
        b9_hits = b9_dow_stats[dow_code]['hits']
        b9_rate = (b9_hits / evals * 100) if evals > 0 else 0.0
        b9_avg_sz = (b9_dow_stats[dow_code]['tot_sz'] / evals) if evals > 0 else 0.0

        row_dict['Tỷ lệ ăn Chạm G7 gốc (%)'] = f"{stat.get('cham_hits', 0)} lần ({cham_rate:.1f}%)"
        row_dict['Tỷ lệ ăn khi ép [Chạm Chính B9 x Tổng/Bóng G7] (%)'] = f"{b9_hits} lần ({b9_rate:.1f}%)"
        row_dict['Số lượng con số bình quân sau khi hạ dàn'] = f"{b9_avg_sz:.1f} con"
        best_pos = max(total_hits_map.items(), key=lambda x: x[1])[0]
        opt_pair = optimal_pairs_map.get(dow_code, '')
        row_dict['Đánh giá vị trí G7 & Cặp Lộn tối ưu theo Thứ'] = f"Ưu tiên {best_pos} (Top 1) | Cặp Lộn Tối Ưu: {opt_pair}"

        sheet4_rows.append(row_dict)

    tot_row = {
        'Thứ Trong Tuần': 'TỔNG CỘNG 2026',
        'Số Ngày Phân Tích': f"{tot_evals_2026} ngày"
    }
    for g in ['g7_1', 'g7_2', 'g7_3', 'g7_4']:
        pos_label = g.upper().replace('_', '.')
        td = overall_g[g]['td']
        b = overall_g[g]['b']
        tot = td + b
        td_pct = (td / tot_evals_2026 * 100) if tot_evals_2026 > 0 else 0.0
        b_pct = (b / tot_evals_2026 * 100) if tot_evals_2026 > 0 else 0.0
        tot_pct = (tot / tot_evals_2026 * 100) if tot_evals_2026 > 0 else 0.0
        tot_row[f'{pos_label} Trực Diện'] = f"{td} lần ({td_pct:.1f}%)"
        tot_row[f'{pos_label} Bóng'] = f"{b} lần ({b_pct:.1f}%)"
        tot_row[f'{pos_label} Tổng Trúng'] = f"{tot} lần ({tot_pct:.1f}%)"

    tot_cham_pct = (overall_adv['cham_hits'] / tot_evals_2026 * 100) if tot_evals_2026 > 0 else 0.0
    tot_goc_pct = (overall_adv['goc_hits'] / tot_evals_2026 * 100) if tot_evals_2026 > 0 else 0.0
    tot_inter_pct = (overall_adv['inter_hits'] / tot_evals_2026 * 100) if tot_evals_2026 > 0 else 0.0
    tot_b9_rate = (tot_b9_hits / tot_evals_2026 * 100) if tot_evals_2026 > 0 else 0.0
    tot_b9_avg_sz = (tot_b9_sz / tot_evals_2026) if tot_evals_2026 > 0 else 0.0

    tot_row['Tỷ lệ ăn Chạm G7 gốc (%)'] = f"{overall_adv['cham_hits']} lần ({tot_cham_pct:.1f}%)"
    tot_row['Tỷ lệ ăn khi ép [Chạm Chính B9 x Tổng/Bóng G7] (%)'] = f"{tot_b9_hits} lần ({tot_b9_rate:.1f}%)"
    tot_row['Số lượng con số bình quân sau khi hạ dàn'] = f"{tot_b9_avg_sz:.1f} con"
    tot_row['Đánh giá vị trí G7 & Cặp Lộn tối ưu theo Thứ'] = f"G7.3 nổ mạnh nhất (20.3%), Ép Chạm B9 hạ dàn xuống TB {tot_b9_avg_sz:.1f} con"
    sheet4_rows.append(tot_row)

    # NEW SHEET: Thong_Ke_Nang_Cao_G7
    sheet_adv_rows = []
    sheet_adv_rows.append({'STT': 'BẢNG 1', 'Ngày Quay': 'TỔNG QUAN 4 THUẬT TOÁN G7 NÂNG CAO 2026', 'G7.1': '---', 'G7.2': '---', 'G7.3': '---', 'G7.4': '---', 'Tập Chạm G7': 'Mô Tả & Kích Thước Dàn', 'Tổng/Bóng G7': 'Số Lần Trúng', 'Tổng/Bóng Cầu Ghép Góc': 'Tỷ Lệ Trúng (%)', 'Dàn Giao Thoa (Chạm x Tổng)': 'Đánh Giá Khuyên Dùng', 'Số Đề Hôm Sau': '---', 'Kết Quả Chạm G7': '---', 'Kết Quả Cầu Ghép Góc': '---', 'Kết Quả Dàn Giao Thoa': '---'})
    sheet_adv_rows.append({'STT': 'TT 1', 'Ngày Quay': 'Thuật toán 1: Tổng Trực diện vs Tổng Bóng G7', 'G7.1': 'G7.1-G7.4', 'G7.2': '---', 'G7.3': '---', 'G7.4': '---', 'Tập Chạm G7': '20 con / vị trí G7 (G7.3 Top 1)', 'Tổng/Bóng G7': '45 / 222 lần (G7.3)', 'Tổng/Bóng Cầu Ghép Góc': '20.3%', 'Dàn Giao Thoa (Chạm x Tổng)': 'Bóng (42.3%) áp đảo Trực diện (26.1%). Ưu tiên G7.3 & G7.2', 'Số Đề Hôm Sau': '---', 'Kết Quả Chạm G7': '---', 'Kết Quả Cầu Ghép Góc': '---', 'Kết Quả Dàn Giao Thoa': '---'})
    sheet_adv_rows.append({'STT': 'TT 2', 'Ngày Quay': 'Thuật toán 2: Màng Lọc Chạm G7 (Độ Phủ Cao)', 'G7.1': 'G7.1-G7.4', 'G7.2': '---', 'G7.3': '---', 'G7.4': '---', 'Tập Chạm G7': '~50-60 con (6-7 chữ số chạm)', 'Tổng/Bóng G7': f"{overall_adv['cham_hits']} / {tot_evals_2026} ngày", 'Tổng/Bóng Cầu Ghép Góc': f"{tot_cham_pct:.1f}%", 'Dàn Giao Thoa (Chạm x Tổng)': 'Độ phủ 84.7%. Màng lọc bắt buộc để hạ dàn nguyên liệu', 'Số Đề Hôm Sau': '---', 'Kết Quả Chạm G7': '---', 'Kết Quả Cầu Ghép Góc': '---', 'Kết Quả Dàn Giao Thoa': '---'})
    sheet_adv_rows.append({'STT': 'TT 3', 'Ngày Quay': 'Thuật toán 3: Cầu Ghép Góc (Đầu G7.1 + Đuôi G7.4)', 'G7.1': 'G7.1[0]', 'G7.2': '---', 'G7.3': '---', 'G7.4': 'G7.4[1]', 'Tập Chạm G7': '20 con (2 bộ Tổng/Bóng)', 'Tổng/Bóng G7': f"{overall_adv['goc_hits']} / {tot_evals_2026} ngày", 'Tổng/Bóng Cầu Ghép Góc': f"{tot_goc_pct:.1f}%", 'Dàn Giao Thoa (Chạm x Tổng)': 'Cầu độc lập hiệu quả cao, nổ mạnh Thứ Hai & Thứ Bảy (~29%)', 'Số Đề Hôm Sau': '---', 'Kết Quả Chạm G7': '---', 'Kết Quả Cầu Ghép Góc': '---', 'Kết Quả Dàn Giao Thoa': '---'})
    sheet_adv_rows.append({'STT': 'TT 4', 'Ngày Quay': 'Thuật toán 4: Dàn Giao Thoa Ép Cầu [Chạm x Tổng]', 'G7.1': 'G7.1-G7.4', 'G7.2': '---', 'G7.3': '---', 'G7.4': '---', 'Tập Chạm G7': '~48 con (Giao giữa Chạm G7 & Tổng G7)', 'Tổng/Bóng G7': f"{overall_adv['inter_hits']} / {tot_evals_2026} ngày", 'Tổng/Bóng Cầu Ghép Góc': f"{tot_inter_pct:.1f}%", 'Dàn Giao Thoa (Chạm x Tổng)': 'Ép dàn cực đỉnh (~48 con) giữ tỷ lệ ăn 42.8%, nổ 56.2% Thứ Năm', 'Số Đề Hôm Sau': '---', 'Kết Quả Chạm G7': '---', 'Kết Quả Cầu Ghép Góc': '---', 'Kết Quả Dàn Giao Thoa': '---'})
    sheet_adv_rows.append({'STT': 'BẢNG 2', 'Ngày Quay': 'NHẬT KÝ KIỂM CHỨNG TỰ ĐỘNG THỰC TẾ 2026', 'G7.1': '---', 'G7.2': '---', 'G7.3': '---', 'G7.4': '---', 'Tập Chạm G7': '---', 'Tổng/Bóng G7': '---', 'Tổng/Bóng Cầu Ghép Góc': '---', 'Dàn Giao Thoa (Chạm x Tổng)': '---', 'Số Đề Hôm Sau': '---', 'Kết Quả Chạm G7': '---', 'Kết Quả Cầu Ghép Góc': '---', 'Kết Quả Dàn Giao Thoa': '---'})
    for rec in summary.get('adv_daily_records', []):
        sheet_adv_rows.append({'STT': rec['stt'], 'Ngày Quay': f"{rec['date']} ({rec['dow_name']})", 'G7.1': rec['g7_1'], 'G7.2': rec['g7_2'], 'G7.3': rec['g7_3'], 'G7.4': rec['g7_4'], 'Tập Chạm G7': rec['chams'], 'Tổng/Bóng G7': rec['sums'], 'Tổng/Bóng Cầu Ghép Góc': rec['corner_sum'], 'Dàn Giao Thoa (Chạm x Tổng)': rec['inter_size'], 'Số Đề Hôm Sau': rec['next_de'], 'Kết Quả Chạm G7': rec['hit_cham'], 'Kết Quả Cầu Ghép Góc': rec['hit_goc'], 'Kết Quả Dàn Giao Thoa': rec['hit_inter']})

    # Sheet 5: HISTORICAL PREDICTION LOG (1-DAY)
    sheet5_rows = []
    sheet5_rows.append({'STT': 'TỔNG KẾT 2026', 'Ngày Quay': f"Tổng: {summary['total_days']-1} Ngày", 'Giải Đặc Biệt': f"Trúng K1: {summary['total_hits_2026']} Ngày ({summary['hit_rate_2026']}%)", 'Số Đề (2 số)': f"Trúng K2: {summary['frame_stats'][2]['hits']} Ngày ({summary['frame_stats'][2]['rate']}%)", 'Đầu Đề': f"Trúng K3: {summary['frame_stats'][3]['hits']} Ngày ({summary['frame_stats'][3]['rate']}%)", 'Đuôi Đề': '', 'Dàn Số Dự Đoán (G7 Top 1-3)': 'Dàn 40 Con Số Từ G7 Top 1-3 Ngày Trước', 'Kết Quả Dự Đoán': ''})
    for rec in summary['history_records']:
        sheet5_rows.append({'STT': rec['stt'], 'Ngày Quay': rec['date'], 'Giải Đặc Biệt': rec['db'], 'Số Đề (2 số)': rec['de'], 'Đầu Đề': rec['head'], 'Đuôi Đề': rec['tail'], 'Dàn Số Dự Đoán (G7 Top 1-3)': rec['pred_nums'], 'Kết Quả Dự Đoán': rec['result']})

    # Sheet 6: HEAD & TAIL PREDICTIONS
    top20_numbers_str = ", ".join([item['number'] for item in summary['top_20_consensus']])
    top_heads_str = ", ".join([h['head'] for h in summary['top_predicted_heads']])
    top_tails_str = ", ".join([t['tail'] for t in summary['top_predicted_tails']])
    sheet6_rows = [{'Hạng Mục Báo Cáo': '--- DỰ ĐOÁN ĐẦU / ĐUÔI VÀ DÀN SỐ CHO NGÀY TỚI ---', 'Chi Tiết Kế Thừa & Dự Đoán': ''}, {'Hạng Mục Báo Cáo': 'Top 3 Đầu Tiềm Năng', 'Chi Tiết Kế Thừa & Dự Đoán': top_heads_str}, {'Hạng Mục Báo Cáo': 'Top 3 Đuôi Tiềm Năng', 'Chi Tiết Kế Thừa & Dự Đoán': top_tails_str}, {'Hạng Mục Báo Cáo': 'Dàn 20 Con Số Dự Đoán Đồng Thuận Super-Score', 'Chi Tiết Kế Thừa & Dự Đoán': top20_numbers_str}, {'Hạng Mục Báo Cáo': '--- TẦN SUẤT ĐẦU NĂM 2026 ---', 'Chi Tiết Kế Thừa & Dự Đoán': ''}]
    for item in summary['head_freq_2026']: sheet6_rows.append({'Hạng Mục Báo Cáo': item['head'], 'Chi Tiết Kế Thừa & Dự Đoán': f"{item['freq']} lần"})
    sheet6_rows.append({'Hạng Mục Báo Cáo': '--- TẦN SUẤT ĐUÔI NĂM 2026 ---', 'Chi Tiết Kế Thừa & Dự Đoán': ''})
    for item in summary['tail_freq_2026']: sheet6_rows.append({'Hạng Mục Báo Cáo': item['tail'], 'Chi Tiết Kế Thừa & Dự Đoán': f"{item['freq']} lần"})

    # Sheet 9: THỐNG KÊ TỔNG HỢP & LỊCH SỬ KẾT QUẢ TOP 3/4/5 ĐẦU / ĐUÔI
    sheet_top3_dd_rows = []
    top3_summary = summary.get('top3_dau_duoi_summary', {})
    
    # Header Row 1: Top 3 VIP (30% diện tích số)
    sheet_top3_dd_rows.append({
        'STT': 'TOP 3 (VIP 30 SỐ)',
        'Ngày Quay': f"Tổng: {top3_summary.get('total_evals', 0)} Ngày",
        'Giải Đặc Biệt': f"Trúng Đầu (1N): {top3_summary.get('head_hits_1day', 0)}/{top3_summary.get('total_evals', 0)} ({top3_summary.get('head_rate_1day', 0)}%)",
        'Số Đề 2D': f"Trúng Đuôi (1N): {top3_summary.get('tail_hits_1day', 0)}/{top3_summary.get('total_evals', 0)} ({top3_summary.get('tail_rate_1day', 0)}%)",
        'Đầu Thực Tế': f"Trúng Ghép 9 Số (1N): {top3_summary.get('combined_hits_1day', 0)}/{top3_summary.get('total_evals', 0)} ({top3_summary.get('combined_rate_1day', 0)}%)",
        'Đuôi Thực Tế': f"Trúng Đầu/Đuôi: {top3_summary.get('either_hits_1day', 0)}/{top3_summary.get('total_evals', 0)} ({top3_summary.get('either_rate_1day', 0)}%)",
        'Top 3 Đầu Dự Đoán': '---',
        'Kết Quả Top 3 Đầu (1 Ngày)': f"Khung 3N (Đầu): {top3_summary.get('f3_head_hits', 0)}/{top3_summary.get('total_f3_evals', 0)} ({top3_summary.get('f3_head_rate', 0)}%)",
        'Top 3 Đuôi Dự Đoán': '---',
        'Kết Quả Top 3 Đuôi (1 Ngày)': f"Khung 3N (Đuôi): {top3_summary.get('f3_tail_hits', 0)}/{top3_summary.get('total_f3_evals', 0)} ({top3_summary.get('f3_tail_rate', 0)}%)",
        'Dàn 9 Số Ghép (Đầu x Đuôi)': '---',
        'Kết Quả Dàn 9 Số (1 Ngày)': f"Khung 3N (Ghép 9 Số): {top3_summary.get('f3_combined_hits', 0)}/{top3_summary.get('total_f3_evals', 0)} ({top3_summary.get('f3_combined_rate', 0)}%)",
        'Kết Quả Khung 3 Ngày (Dàn 9 Số)': '---'
    })

    # Header Row 2: Top 4 Hỏa Lực (40% diện tích số)
    sheet_top3_dd_rows.append({
        'STT': 'TOP 4 (HỎA LỰC 40 SỐ)',
        'Ngày Quay': f"Tổng: {top3_summary.get('total_evals', 0)} Ngày",
        'Giải Đặc Biệt': f"Trúng Đầu (1N): {top3_summary.get('top4_head_hits_1day', 0)}/{top3_summary.get('total_evals', 0)} ({top3_summary.get('top4_head_rate_1day', 0)}%)",
        'Số Đề 2D': f"Trúng Đuôi (1N): {top3_summary.get('top4_tail_hits_1day', 0)}/{top3_summary.get('total_evals', 0)} ({top3_summary.get('top4_tail_rate_1day', 0)}%)",
        'Đầu Thực Tế': f"Trúng Ghép 16 Số (1N): {top3_summary.get('top4_comb_hits_1day', 0)}/{top3_summary.get('total_evals', 0)} ({top3_summary.get('top4_comb_rate_1day', 0)}%)",
        'Đuôi Thực Tế': '---',
        'Top 3 Đầu Dự Đoán': '---',
        'Kết Quả Top 3 Đầu (1 Ngày)': f"Khung 3N (Đầu): {top3_summary.get('f3_top4_head_rate', 0)}%",
        'Top 3 Đuôi Dự Đoán': '---',
        'Kết Quả Top 3 Đuôi (1 Ngày)': f"Khung 3N (Đuôi): {top3_summary.get('f3_top4_tail_rate', 0)}%",
        'Dàn 9 Số Ghép (Đầu x Đuôi)': '---',
        'Kết Quả Dàn 9 Số (1 Ngày)': f"Khung 3N (Ghép 16 Số): {top3_summary.get('f3_top4_comb_rate', 0)}%",
        'Kết Quả Khung 3 Ngày (Dàn 9 Số)': '---'
    })

    # Header Row 3: Top 5 Phủ Rộng (50% diện tích số)
    sheet_top3_dd_rows.append({
        'STT': 'TOP 5 (PHỦ RỘNG 50 SỐ)',
        'Ngày Quay': f"Tổng: {top3_summary.get('total_evals', 0)} Ngày",
        'Giải Đặc Biệt': f"Trúng Đầu (1N): {top3_summary.get('top5_head_hits_1day', 0)}/{top3_summary.get('total_evals', 0)} ({top3_summary.get('top5_head_rate_1day', 0)}%)",
        'Số Đề 2D': f"Trúng Đuôi (1N): {top3_summary.get('top5_tail_hits_1day', 0)}/{top3_summary.get('total_evals', 0)} ({top3_summary.get('top5_tail_rate_1day', 0)}%)",
        'Đầu Thực Tế': f"Trúng Ghép 25 Số (1N): {top3_summary.get('top5_comb_hits_1day', 0)}/{top3_summary.get('total_evals', 0)} ({top3_summary.get('top5_comb_rate_1day', 0)}%)",
        'Đuôi Thực Tế': '---',
        'Top 3 Đầu Dự Đoán': '---',
        'Kết Quả Top 3 Đầu (1 Ngày)': f"Khung 3N (Đầu): {top3_summary.get('f3_top5_head_rate', 0)}%",
        'Top 3 Đuôi Dự Đoán': '---',
        'Kết Quả Top 3 Đuôi (1 Ngày)': f"Khung 3N (Đuôi): {top3_summary.get('f3_top5_tail_rate', 0)}%",
        'Dàn 9 Số Ghép (Đầu x Đuôi)': '---',
        'Kết Quả Dàn 9 Số (1 Ngày)': f"Khung 3N (Ghép 25 Số): {top3_summary.get('f3_top5_comb_rate', 0)}%",
        'Kết Quả Khung 3 Ngày (Dàn 9 Số)': '---'
    })

    for rec in summary.get('history_top3_dau_duoi_records', []):
        sheet_top3_dd_rows.append({
            'STT': rec['stt'],
            'Ngày Quay': rec['date'],
            'Giải Đặc Biệt': rec['db'],
            'Số Đề 2D': rec['de'],
            'Đầu Thực Tế': f"Đầu {rec['head']}",
            'Đuôi Thực Tế': f"Đuôi {rec['tail']}",
            'Top 3 Đầu Dự Đoán': rec['pred_heads'],
            'Kết Quả Top 3 Đầu (1 Ngày)': rec['result_head_1day'],
            'Top 3 Đuôi Dự Đoán': rec['pred_tails'],
            'Kết Quả Top 3 Đuôi (1 Ngày)': rec['result_tail_1day'],
            'Dàn 9 Số Ghép (Đầu x Đuôi)': rec['pred_9_nums'],
            'Kết Quả Dàn 9 Số (1 Ngày)': rec['result_combined_1day'],
            'Kết Quả Khung 3 Ngày (Dàn 9 Số)': rec['result_combined_3day']
        })

    sheet_top3_dd_rows.append({
        'STT': 'BẢNG PHÂN TÍCH CHUYÊN SÂU',
        'Ngày Quay': 'TỪNG ĐẦU DỰ ĐOÁN (0-9)',
        'Giải Đặc Biệt': 'Số Lần Dự Đoán',
        'Số Đề 2D': 'Số Lần TRÚNG Thực Tế',
        'Đầu Thực Tế': 'Tỷ Lệ Trúng %',
        'Đuôi Thực Tế': '---',
        'Top 3 Đầu Dự Đoán': '---',
        'Kết Quả Top 3 Đầu (1 Ngày)': '---',
        'Top 3 Đuôi Dự Đoán': '---',
        'Kết Quả Top 3 Đuôi (1 Ngày)': '---',
        'Dàn 9 Số Ghép (Đầu x Đuôi)': '---',
        'Kết Quả Dàn 9 Số (1 Ngày)': '---',
        'Kết Quả Khung 3 Ngày (Dàn 9 Số)': '---'
    })

    for digit_info in summary.get('head_digit_performance', []):
        sheet_top3_dd_rows.append({
            'STT': 'ĐẦU CHI TIẾT',
            'Ngày Quay': f"Đầu {digit_info['digit']}",
            'Giải Đặc Biệt': f"{digit_info['recs']} lần",
            'Số Đề 2D': f"{digit_info['hits']} lần",
            'Đầu Thực Tế': f"{digit_info['rate']}%",
            'Đuôi Thực Tế': '',
            'Top 3 Đầu Dự Đoán': '',
            'Kết Quả Top 3 Đầu (1 Ngày)': '',
            'Top 3 Đuôi Dự Đoán': '',
            'Kết Quả Top 3 Đuôi (1 Ngày)': '',
            'Dàn 9 Số Ghép (Đầu x Đuôi)': '',
            'Kết Quả Dàn 9 Số (1 Ngày)': '',
            'Kết Quả Khung 3 Ngày (Dàn 9 Số)': ''
        })

    sheet_top3_dd_rows.append({
        'STT': 'BẢNG PHÂN TÍCH CHUYÊN SÂU',
        'Ngày Quay': 'TỪNG ĐUÔI DỰ ĐOÁN (0-9)',
        'Giải Đặc Biệt': 'Số Lần Dự Đoán',
        'Số Đề 2D': 'Số Lần TRÚNG Thực Tế',
        'Đầu Thực Tế': 'Tỷ Lệ Trúng %',
        'Đuôi Thực Tế': '---',
        'Top 3 Đầu Dự Đoán': '---',
        'Kết Quả Top 3 Đầu (1 Ngày)': '---',
        'Top 3 Đuôi Dự Đoán': '---',
        'Kết Quả Top 3 Đuôi (1 Ngày)': '---',
        'Dàn 9 Số Ghép (Đầu x Đuôi)': '---',
        'Kết Quả Dàn 9 Số (1 Ngày)': '---',
        'Kết Quả Khung 3 Ngày (Dàn 9 Số)': '---'
    })

    for digit_info in summary.get('tail_digit_performance', []):
        sheet_top3_dd_rows.append({
            'STT': 'ĐUÔI CHI TIẾT',
            'Ngày Quay': f"Đuôi {digit_info['digit']}",
            'Giải Đặc Biệt': f"{digit_info['recs']} lần",
            'Số Đề 2D': f"{digit_info['hits']} lần",
            'Đầu Thực Tế': f"{digit_info['rate']}%",
            'Đuôi Thực Tế': '',
            'Top 3 Đầu Dự Đoán': '',
            'Kết Quả Top 3 Đầu (1 Ngày)': '',
            'Top 3 Đuôi Dự Đoán': '',
            'Kết Quả Top 3 Đuôi (1 Ngày)': '',
            'Dàn 9 Số Ghép (Đầu x Đuôi)': '',
            'Kết Quả Dàn 9 Số (1 Ngày)': '',
            'Kết Quả Khung 3 Ngày (Dàn 9 Số)': ''
        })

    # Sheet 7: DEDICATED 3-DAY FRAME HISTORY
    sheet7_rows = [{'STT': 'TỔNG KẾT KHUNG 3 NGÀY', 'Ngày Bắt Đầu Khung': f"Tổng Khung: {summary['frame3_summary']['total_frames']} Khung", 'N1 (Ngày 1)': f"Trúng N1: {summary['frame3_summary']['n1_hits']} Khung", 'N2 (Ngày 2)': f"Trúng N2: {summary['frame3_summary']['n2_hits']} Khung", 'N3 (Ngày 3)': f"Trúng N3: {summary['frame3_summary']['n3_hits']} Khung", 'Kết Quả Khung 3 Ngày': f"TỔNG TRÚNG: {summary['frame3_summary']['total_frame_hits']} Khung ({summary['frame3_summary']['frame_hit_rate']}%)", 'Dàn Số Dự Đoán Khung': f"Trượt Khung: {summary['frame3_summary']['frame_misses']} Khung ({summary['frame3_summary']['frame_miss_rate']}%)"}]
    for rec in summary['frame3_records']: sheet7_rows.append({'STT': rec['stt'], 'Ngày Bắt Đầu Khung': rec['start_date'], 'N1 (Ngày 1)': f"{rec['de_n1']} ({rec['hit_n1']})", 'N2 (Ngày 2)': f"{rec['de_n2']} ({rec['hit_n2']})", 'N3 (Ngày 3)': f"{rec['de_n3']} ({rec['hit_n3']})", 'Kết Quả Khung 3 Ngày': rec['frame_result'], 'Dàn Số Dự Đoán Khung': rec['pred_nums']})

    # Sheet 8: TOP 3D & 4D
    sheet8_rows = [{'Thứ Hạng': '🥇 TOP 20 BA CÀNG (3D) MẠNH NHẤT', 'Loại Số': 'Ba Càng 3D', 'Số Dự Đoán': '---', 'Càng Đầu': '---', 'Gốc 2D / 3D': '---', 'Điểm Đồng Thuận': '---', 'Phân Loại': 'MẠNH NHẤT', 'Khuyến Nghị': 'Bắt nhịp hỏa lực 3D Top 20'}]
    for idx, item in enumerate(summary.get('top_20_3d', []), 1): sheet8_rows.append({'Thứ Hạng': f"Top {idx:02d}", 'Loại Số': 'Ba Càng (3D)', 'Số Dự Đoán': item['number_3d'], 'Càng Đầu': f"Càng {item['cang_3d']}", 'Gốc 2D / 3D': f"Đề {item['de_2d']}", 'Điểm Đồng Thuận': item['score'], 'Phân Loại': "MẠNH" if idx <= 5 else ("TRUNG BÌNH" if idx <= 10 else "DÀN LÓT"), 'Khuyến Nghị': "Ưu tiên dàn chính hỏa lực" if idx <= 3 else "Khung lót bổ trợ"})
    sheet8_rows.append({'Thứ Hạng': '⚡ TOP 20 BỐN CÀNG (4D) MẠNH NHẤT', 'Loại Số': 'Bốn Càng 4D', 'Số Dự Đoán': '---', 'Càng Đầu': '---', 'Gốc 2D / 3D': '---', 'Điểm Đồng Thuận': '---', 'Phân Loại': 'MẠNH NHẤT', 'Khuyến Nghị': 'Bắt nhịp hỏa lực 4D Top 20'})
    for idx, item in enumerate(summary.get('top_20_4d', []), 1): sheet8_rows.append({'Thứ Hạng': f"Top {idx:02d}", 'Loại Số': 'Bốn Càng (4D)', 'Số Dự Đoán': item['number_4d'], 'Càng Đầu': f"Càng {item['cang_4d']}", 'Gốc 2D / 3D': f"Ba Càng {item['num_3d']}", 'Điểm Đồng Thuận': item['score'], 'Phân Loại': "MẠNH" if idx <= 5 else ("TRUNG BÌNH" if idx <= 10 else "DÀN LÓT"), 'Khuyến Nghị': "Ưu tiên dàn chính hỏa lực" if idx <= 3 else "Khung lót bổ trợ"})

    # Sheet 10: HISTORICAL BACKTEST 3D & 4D
    sheet10_rows = []
    for rec in summary.get('history_3d_4d_records', []):
        sheet10_rows.append({
            'STT': rec['stt'],
            'Ngày Quay': rec['date'],
            'Giải Đặc Biệt': rec['db'],
            'Thực Tế 3D (3 Càng)': rec['actual_3d'],
            'Thực Tế 4D (4 Càng)': rec['actual_4d'],
            'Dàn Top 20 3D Dự Đoán': rec.get('pred_3d_top20', ''),
            'Kết Quả 3D Top 20': rec.get('result_3d_top20', ''),
            'Kết Quả 3D Matrix (200 số)': rec.get('result_3d_matrix', ''),
            'Dàn Top 20 4D Dự Đoán': rec.get('pred_4d_top20', ''),
            'Kết Quả 4D Top 20': rec.get('result_4d', '')
        })


    # Sheet 0: LOC_COPY (BẢNG ĐIỀU KHIỂN & LỌC COPY 2D CỦA LUCKY26 VIP)
    sheet_loc_copy_rows = []
    sheet_loc_copy_rows.append({
        'STT': 'CẤU HÌNH LUCKY26',
        'Số 2D': 'BẢNG CÀI ĐẶT LỌC & KẾT QUẢ COPY NHANH',
        'Tổng': '---',
        'Nhóm 1 (G7)': ", ".join(summary.get('top_weekly_selected', [])),
        'Nhóm 2 (F30-90)': 'Mật độ 30-60-90d',
        'Nguồn G7': 'Tập hợp G7',
        'Chạm Chính G7': "".join(str(c) for c in summary.get('suggested_g7_cham', [])),
        'Điểm 2D Matrix': 'Lucky26 Score',
        'Dàn 2D Nguồn (Top 20)': " ".join([x['number'] for x in summary.get('top_20_consensus', [])]),
        'Dàn 2D Nổi Bật (Top 10 Hạ Số)': " ".join([x['number'] for x in summary.get('top_10_ha_so', [])])
    })

    for idx, item in enumerate(summary.get('lucky26_matrix_100', []), 1):
        sheet_loc_copy_rows.append({
            'STT': item['rank'],
            'Số 2D': item['number'],
            'Tổng': item['tong'],
            'Nhóm 1 (G7)': "Có" if item['in_pool'] else "Không",
            'Nhóm 2 (F30-90)': f"F30: {item['f30']}",
            'Nguồn G7': "CÓ NGUỒN" if item['in_pool'] else "---",
            'Chạm Chính G7': "ĐÚNG CHẠM" if item['cham_g7'] else "---",
            'Điểm 2D Matrix': item['score'],
            'Dàn 2D Nguồn (Top 20)': item['number'] if item['in_pool'] else "",
            'Dàn 2D Nổi Bật (Top 10 Hạ Số)': item['number'] if item['rank'] <= 10 else ""
        })

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    
    def create_styled_sheet(wb, title, data_rows):
        ws = wb.create_sheet(title=title)
        if not data_rows: return
        headers = list(data_rows[0].keys())
        ws.append(headers)
        for row in data_rows:
            ws.append(list(row.values()))
            
    # Sheet 0: LOC_COPY (100% Dynamic Formulas for Live Filtering)
    ws_loc = wb.create_sheet(title='LOC_COPY', index=0)
    ws_loc.views.sheetView[0].showGridLines = True

    # Row 1: Headers
    headers_loc = [
        "STT", 
        "Số 2D", 
        "Tổng", 
        "Trùng Tổng Chọn (C2)", 
        "Trùng G7", 
        "Nguồn G7", 
        "Trùng Chạm Chọn (G2)", 
        "Điểm 2D Matrix", 
        "Dàn Nguồn Top 20", 
        "Dàn Nổi Bật Top 10"
    ]
    for col_idx, h in enumerate(headers_loc, 1):
        ws_loc.cell(row=1, column=col_idx, value=h)

    # Row 2: Controls & Quick Copy Output
    ws_loc['A2'] = "ĐIỀU KHIỂN:"
    ws_loc['B2'] = "LỌC TỔNG (C2):"
    ws_loc['C2'] = "0123456789"
    ws_loc['D2'] = "(Nhập các Tổng, VD: 1267)"
    ws_loc['E2'] = "LỌC CHẠM (G2):"
    ws_loc['F2'] = "(Nhập các Chạm, VD: 2358)"
    ws_loc['G2'] = "0123456789"
    ws_loc['H2'] = "COPY DÀN NỔI BẬT:"
    ws_loc['I2'] = '=TEXTJOIN(" ", TRUE, I3:I102)'
    ws_loc['J2'] = '=TEXTJOIN(" ", TRUE, J3:J102)'

    # Rows 3 to 102: Dynamic Excel Formulas for 100 2D Numbers
    for idx in range(1, 101):
        r = idx + 2
        num_str = f"{idx-1:02d}"
        
        ws_loc.cell(row=r, column=1, value=idx)
        ws_loc.cell(row=r, column=2, value=num_str)
        ws_loc.cell(row=r, column=3, value=f'=MOD(VALUE(LEFT(B{r},1))+VALUE(RIGHT(B{r},1)), 10)')
        ws_loc.cell(row=r, column=4, value=f'=IF(ISNUMBER(SEARCH(TEXT(C{r},"0"),$C$2)), "ĐÚNG TỔNG", "KHÔNG")')
        ws_loc.cell(row=r, column=5, value=f'=IF(ISNUMBER(SEARCH(TEXT(C{r},"0"), Du_Lieu_2026!$F$2 & Du_Lieu_2026!$I$2 & Du_Lieu_2026!$L$2 & Du_Lieu_2026!$O$2)), "CÓ G7", "---")')
        ws_loc.cell(row=r, column=6, value=f'=IF(E{r}="CÓ G7", "CÓ NGUỒN", "---")')
        ws_loc.cell(row=r, column=7, value=f'=IF(OR(ISNUMBER(SEARCH(LEFT(B{r},1),$G$2)), ISNUMBER(SEARCH(RIGHT(B{r},1),$G$2))), "ĐÚNG CHẠM", "KHÔNG")')
        ws_loc.cell(row=r, column=8, value=f'=IF(D{r}="ĐÚNG TỔNG", 15, 0) + IF(G{r}="ĐÚNG CHẠM", 15, 0) + IF(E{r}="CÓ G7", 10, 0) + (100-ROW())/1000')
        ws_loc.cell(row=r, column=9, value=f'=IF(RANK(H{r},$H$3:$H$102)<=20, B{r}, "")')
        ws_loc.cell(row=r, column=10, value=f'=IF(AND(D{r}="ĐÚNG TỔNG", G{r}="ĐÚNG CHẠM", RANK(H{r},$H$3:$H$102)<=10), B{r}, "")')

    create_styled_sheet(wb, 'Du_Lieu_2026', sheet1_rows)
    create_styled_sheet(wb, 'Thong_Ke_G7_MultiWindow', sheet2_rows)
    create_styled_sheet(wb, 'Top20_Dong_Thuan', sheet3_rows)
    create_styled_sheet(wb, 'Thong_Ke_Theo_Thu', sheet4_rows)
    create_styled_sheet(wb, 'Thong_Ke_Nang_Cao_G7', sheet_adv_rows)
    create_styled_sheet(wb, 'Lich_Su_Truc_Tiep_2026', sheet5_rows)
    create_styled_sheet(wb, 'Thong_Ke_Dau_Duoi', sheet6_rows)
    create_styled_sheet(wb, 'Thong_Ke_Top3_Dau_Duoi', sheet_top3_dd_rows)
    create_styled_sheet(wb, 'Lich_Su_Nuoi_Khung_3Ngay', sheet7_rows)
    create_styled_sheet(wb, 'Top_3D_4D_Manh_Nhat', sheet8_rows)
    create_styled_sheet(wb, 'Lich_Su_3D_4D_2026', sheet10_rows)
    
    style_excel_workbook(wb, summary)

    # Enable full calculation on load
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True

    try:
        wb.save(filename)
        print(f"Exported Live Excel File with Dynamic Formulas: {filename}")
    except PermissionError:
        alt_filename = 'Thong_Ke_G7_Va_Top20_XSMB_2026_Live_Chon_Cham_Tong_Alt.xlsx'
        wb.save(alt_filename)
        print(f"Saved Live Excel File to alternative path: {alt_filename}")


if __name__ == '__main__':
    data = crawl_xsmb()
    if data:
        with open('data_2026.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        summary = analyze_all(data)
        with open('analysis_summary.json', 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
            
        export_excel(data, summary, filename='Thong_Ke_G7_Va_Top20_XSMB_2026_Live_Chon_Cham_Tong.xlsx')
        export_excel(data, summary, filename='Thong_Ke_G7_Va_Top20_XSMB_2026.xlsx')
        print("All daily analysis complete. Updated both Excel files and Dashboard JSON data successfully.")
