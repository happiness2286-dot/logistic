# -*- coding: utf-8 -*-
"""
=============================================================================
XSMB AI - KỊCH BẢN BACKTEST ĐO LƯỜNG TỶ LỆ TRÚNG KHUNG 3 NGÀY (58_UP_TO_75)
Hỗ trợ kiểm thử độc lập:
  python backtest.py --n2-size 42
  python backtest.py --n2-size 36
  python backtest.py --count 32
=============================================================================
"""

import os
import sys
import json
import argparse
from collections import Counter

# Hỗ trợ UTF-8 console trên Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DEFAULT_60_CAP4 = [
    1, 2, 3, 4, 5, 8, 9, 11, 12, 13, 15, 17, 18, 19, 20,
    21, 22, 23, 24, 26, 28, 29, 31, 32, 33, 34, 35, 37, 38, 42,
    44, 45, 51, 53, 55, 58, 59, 60, 61, 62, 63, 65, 67, 68, 69,
    72, 80, 81, 82, 83, 84, 85, 87, 88, 91, 92, 95, 97, 98, 99
]

def compute_ai_scores(all_draws, target_idx):
    """Chấm điểm AI Score cho 100 số 2D tại một kỳ quay cụ thể"""
    prev_de = all_draws[target_idx - 1]['de'] if target_idx >= 1 else None
    prev_prev_de = all_draws[target_idx - 2]['de'] if target_idx >= 2 else None
    
    start_30 = max(0, target_idx - 30)
    hist_30 = [d['de'] for d in all_draws[start_30:target_idx] if d.get('de')]
    counter_30 = Counter(hist_30)
    
    gan_dict = {}
    for i in range(100):
        n_str = f"{i:02d}"
        gan = 999
        for step, d in enumerate(reversed(all_draws[:target_idx])):
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
        
        freq = counter_30.get(n_str, 0)
        if freq == 1: sc += 1.5
        elif freq == 2: sc += 2.2
        elif freq >= 3: sc += 1.8
        else: sc -= 0.5
        
        gan = gan_dict.get(n_str, 999)
        if 5 <= gan <= 25: sc += 1.5
        elif gan > 45: sc -= 3.0
        
        if prev_de == n_str and prev_prev_de == n_str:
            sc -= 6.0
        elif prev_de == n_str:
            sc -= 1.5
            
        if n_str[0] in dau_set and n_str[1] in duoi_set:
            sc += 1.2
        elif n_str[0] in dau_set or n_str[1] in duoi_set:
            sc += 0.5
            
        scores[n_str] = round(min(max(sc, 1.0), 9.9), 1)
        
    return scores, gan_dict, prev_de, prev_prev_de

def run_backtest(n2_size=42, n3_size=40, count=32):
    data_file = 'data_2026.json'
    if not os.path.exists(data_file):
        print(f"[!] Không tìm thấy file {data_file}")
        return
        
    with open(data_file, 'r', encoding='utf-8') as f:
        draws = json.load(f)
        
    # data_2026.json: index 0 là mới nhất, đảo ngược để chạy theo thứ tự thời gian
    chronological = list(reversed(draws))
    total_draws = len(chronological)
    test_count = min(count, total_draws)
    start_idx = total_draws - test_count
    
    print("\n" + "=" * 80)
    print(f"      XSMB AI - BACKTEST ĐO LƯỜNG TỶ LỆ TRÚNG KHUNG ({test_count} KỲ GẦN NHẤT)")
    print(f"      Cấu hình: N1 = 60 số | N2 = {n2_size} số (Mở rộng) | N3 = {n3_size} số")
    print("=" * 80)
    
    dan_n1_set = set(f"{x:02d}" for x in DEFAULT_60_CAP4)
    base_n2_pool = [
        11, 12, 13, 15, 17, 18, 19, 21, 22, 23, 28, 29, 31, 32, 33, 35, 37, 38,
        42, 44, 45, 51, 52, 53, 55, 58, 59, 61, 62, 63, 65, 66, 67, 68, 81, 82,
        83, 85, 87, 90, 95, 98
    ]
    
    khung_state = 1 # 1: Đang đánh N1, 2: Đang nuôi N2, 3: Đang nuôi N3
    c_n1 = 0
    c_n2 = 0
    c_n3 = 0
    c_truot = 0
    
    results = []
    
    for idx in range(start_idx, total_draws):
        curr = chronological[idx]
        de = curr.get('de')
        date_str = curr.get('date')
        
        scores, gan_dict, prev_de, prev_prev_de = compute_ai_scores(chronological, idx)
        
        # 1. Dàn N2
        bet_2_days = {prev_de} if (prev_de and prev_de == prev_prev_de) else set()
        n2_candidates_set = set(f"{x:02d}" for x in base_n2_pool)
        for n in dan_n1_set:
            n2_candidates_set.add(n)
            
        n2_filtered = [n for n in n2_candidates_set if n not in bet_2_days]
        n2_filtered.sort(key=lambda x: (scores.get(x, 5.0), 1 if x in dan_n1_set else 0), reverse=True)
        dan_n2_list = set(sorted(n2_filtered[:n2_size]))
        
        # 2. Dàn N3
        n3_candidates = [n for n in dan_n2_list if gan_dict.get(n, 0) <= 45]
        for n in dan_n2_list:
            if len(n3_candidates) >= n3_size:
                break
            if n not in n3_candidates:
                n3_candidates.append(n)
        n3_candidates.sort(key=lambda x: scores.get(x, 5.0), reverse=True)
        dan_n3_list = set(sorted(n3_candidates[:n3_size]))
        
        # Đánh giá kết quả theo chu kỳ nuôi khung 3 ngày
        if khung_state == 1:
            if de in dan_n1_set:
                c_n1 += 1
                status = "🎯 TRÚNG N1 (Ngày 1)"
                khung_state = 1
            else:
                status = "⚠️ Trượt N1 -> Chuyển sang nuôi N2"
                khung_state = 2
        elif khung_state == 2:
            if de in dan_n2_list:
                c_n2 += 1
                status = "🛡️ TRÚNG N2 (Cứu N1 thành công)"
                khung_state = 1
            else:
                status = "⚠️ Trượt N2 -> Chuyển sang nuôi N3"
                khung_state = 3
        elif khung_state == 3:
            if de in dan_n3_list:
                c_n3 += 1
                status = "🛡️ TRÚNG N3 (Cơ hội cuối thành công)"
                khung_state = 1
            else:
                c_truot += 1
                status = "❌ TRƯỢT KHUNG 3 NGÀY"
                khung_state = 1
                
        results.append({
            'date': date_str,
            'de': de,
            'status': status
        })
        
    # In bảng chi tiết từng kỳ
    print(f"\n{'STT':^4} | {'Ngày Quay':^28} | {'Đề':^6} | {'Kết Quả Đánh Giá':<35}")
    print("-" * 80)
    for i, r in enumerate(results, 1):
        print(f"{i:^4} | {r['date']:<28} | {r['de']:^6} | {r['status']:<35}")
        
    tot_resolved = c_n1 + c_n2 + c_n3 + c_truot
    rate_n1 = round(c_n1 / tot_resolved * 100, 1) if tot_resolved > 0 else 0
    rate_n2 = round(c_n2 / tot_resolved * 100, 1) if tot_resolved > 0 else 0
    rate_n3 = round(c_n3 / tot_resolved * 100, 1) if tot_resolved > 0 else 0
    rate_truot = round(c_truot / tot_resolved * 100, 1) if tot_resolved > 0 else 0
    rate_tong = round((c_n1 + c_n2 + c_n3) / tot_resolved * 100, 1) if tot_resolved > 0 else 0
    
    print("\n" + "=" * 80)
    print("                     BẢNG TỔNG HỢP CHỈ SỐ BACKTEST")
    print("=" * 80)
    print(f"  • Tổng số khung đã hoàn thành:   {tot_resolved} khung (từ {test_count} kỳ quay)")
    print(f"  • 🎯 Trúng N1 (Ăn ngay ngày 1):   {c_n1} khung ({rate_n1}%)")
    print(f"  • 🛡️ Trúng N2 (Cứu N1):           {c_n2} khung ({rate_n2}%)")
    print(f"  • 🛡️ Trúng N3 (Cứu ngày cuối):    {c_n3} khung ({rate_n3}%)")
    print(f"  • ❌ Trượt khung 3 ngày:          {c_truot} khung ({rate_truot}%)")
    print("-" * 80)
    print(f"  🏆 TỔNG TỶ LỆ TRÚNG KHUNG:        {c_n1 + c_n2 + c_n3}/{tot_resolved} = {rate_tong}%")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="XSMB AI - Backtest đo lường tỷ lệ trúng khung 3 ngày")
    parser.add_argument('--n2-size', type=int, default=42, help='Số lượng số trong Dàn N2 (mặc định: 42)')
    parser.add_argument('--n3-size', type=int, default=40, help='Số lượng số trong Dàn N3 (mặc định: 40)')
    parser.add_argument('--count', type=int, default=32, help='Số lượng kỳ cũ cần test (mặc định: 32)')
    args = parser.parse_args()
    
    run_backtest(n2_size=args.n2_size, n3_size=args.n3_size, count=args.count)
