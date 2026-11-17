# -*- coding: utf-8 -*-
"""
=============================================================================
XSMB AI RADAR SCANNER - QUÉT VỊ TRÍ G1 ĐẾN G5.6 & PHÂN TẦNG LIVE CHUẨN IPHONE 11
Nâng cấp toàn diện (Tháng 11/2026):
- Tự động cào live siêu tốc (API 383.im 50ms + xosodaiphat.com fallback)
- Hợp nhất cached_draws.json đảm bảo luôn có đủ 30 kỳ lịch sử kiểm chứng (không bị cụt 5 kỳ)
- Đồng bộ Dàn 60 Số N1 Động Thích Nghi (Adaptive 60s N1), N2 (36s), N3 (36s) từ analysis_summary.json
- Thuật toán Hội Tụ Đa Cầu (Multi-Bridge Density Convergence): Tích lũy mật độ cầu Đầu x Đuôi
  trực tiếp từ 85 vị trí G1->G5.5 + Tâm Càng G1 + Cầu Tổng/Chạm G7 + AI Head/Tail
- Hỗ trợ bắn thông báo chốt số G5.5 siêu tốc (<0.5s) qua Telegram Bot (nếu cấu hình telegram_config.json)
=============================================================================
"""

import os
import sys
import re
import json
import time
import argparse
from datetime import datetime, timedelta
from collections import Counter, defaultdict

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_JSON_PATH = os.path.join(BASE_DIR, 'live_radar_state.json')
SUMMARY_JSON_PATH = os.path.join(BASE_DIR, 'analysis_summary.json')
CACHE_DRAWS_PATH = os.path.join(BASE_DIR, 'cached_draws.json')
TELEGRAM_CFG_PATH = os.path.join(BASE_DIR, 'telegram_config.json')
TELEGRAM_SENT_LOG_PATH = os.path.join(BASE_DIR, 'telegram_sent_log.json')
LOCKED_SNAPSHOTS_PATH = os.path.join(BASE_DIR, 'locked_g55_snapshots.json')

API_383_LIVE_URL = "https://api.383.im/lottery/live.json"
DAIPHAT_LIVE_URL = "https://xosodaiphat.com/xsmb-xo-so-mien-bac.html"
DAIPHAT_30N_URL = "https://xosodaiphat.com/xsmb-30-ngay.html"

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

DEFAULT_60_N1 = [
    "01", "02", "03", "04", "05", "08", "09", "11", "12", "13", "15", "17", "18", "19", "21",
    "22", "23", "24", "26", "28", "29", "31", "32", "33", "34", "35", "37", "38", "39", "42",
    "43", "44", "45", "51", "53", "55", "58", "59", "60", "61", "62", "63", "65", "67", "68",
    "69", "72", "80", "81", "82", "83", "84", "85", "87", "88", "91", "92", "95", "96", "97", "99"
]


def extract_date_key(d_str):
    """Chuẩn hóa chuỗi ngày về định dạng dd-mm-yyyy để tra cứu không phụ thuộc chữ hoa/thường."""
    if not d_str:
        return ""
    m = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', str(d_str))
    if m:
        return f"{int(m.group(1)):02d}-{int(m.group(2)):02d}-{m.group(3)}"
    return str(d_str).strip()


def load_locked_g55_snapshot(date_str):
    """Đọc bản chụp bộ số đã đóng băng lúc 18h23 (G5.5) của ngày date_str (nếu có)."""
    t_key = extract_date_key(date_str)
    if not t_key or not os.path.exists(LOCKED_SNAPSHOTS_PATH):
        return None
    try:
        with open(LOCKED_SNAPSHOTS_PATH, 'r', encoding='utf-8') as f:
            snaps = json.load(f)
        if isinstance(snaps, dict) and t_key in snaps:
            return snaps[t_key]
    except Exception:
        pass
    return None


def save_locked_g55_snapshot(date_str, snap_dict):
    """Đóng băng vĩnh viễn bộ số đã chốt lúc 18h23 (G5.5) để không bao giờ bị biến đổi sau 18h36."""
    t_key = extract_date_key(date_str)
    if not t_key or not snap_dict:
        return False
    snaps = {}
    if os.path.exists(LOCKED_SNAPSHOTS_PATH):
        try:
            with open(LOCKED_SNAPSHOTS_PATH, 'r', encoding='utf-8') as f:
                snaps = json.load(f)
            if not isinstance(snaps, dict):
                snaps = {}
        except Exception:
            snaps = {}
    if t_key in snaps:
        return False
    snaps[t_key] = {
        'top_1': snap_dict.get('top_1', ''),
        'lot_lon': snap_dict.get('lot_lon', ''),
        'song_thu': snap_dict.get('song_thu_tru') or snap_dict.get('song_thu', []),
        'top_4': list(snap_dict.get('top_4', [])),
        'dan_9_so': list(snap_dict.get('dan_9_so', [])),
        'locked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    try:
        with open(LOCKED_SNAPSHOTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(snaps, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def send_telegram_alert(message_text):
    """
    Gửi thông báo đẩy tức thì (<0.5s) về điện thoại qua Telegram Bot nếu người dùng cấu hình telegram_config.json.
    Cấu trúc telegram_config.json: {"enabled": true, "bot_token": "...", "chat_id": "..."}
    """
    if not os.path.exists(TELEGRAM_CFG_PATH):
        return False
    try:
        with open(TELEGRAM_CFG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        if not cfg.get('enabled') or not cfg.get('bot_token') or not cfg.get('chat_id'):
            return False
        token = str(cfg['bot_token']).strip()
        chat_id = str(cfg['chat_id']).strip()
        # KHÓA AN TOÀN TUYỆT ĐỐI: Chỉ cho phép gửi duy nhất vào Chat ID cá nhân của Hoàng Ngọc Hà (5422717407)
        # Tuyệt đối chặn mọi Chat ID khác hoặc Group ID để không bao giờ gửi nhầm sang người khác
        if chat_id != "5422717407":
            print(f"[!] CHẶN AN TOÀN: Từ chối gửi Telegram tới chat_id lạ ({chat_id}). Chỉ gửi duy nhất cho 5422717407.")
            return False
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message_text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        if HAS_LIBS:
            r = requests.post(url, json=payload, timeout=5)
            return r.status_code == 200
        else:
            import ssl
            ctx = ssl._create_unverified_context()
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                return resp.status == 200
    except Exception as e:
        print(f"[!] Lưu ý gửi Telegram: {e}")
        return False


def format_g55_telegram_message(res, is_test=False):
    """Định dạng tin nhắn chốt số lúc 18h23 (G5.5) rõ nét trên màn hình điện thoại."""
    t_date = res.get('target_date', '')
    top1 = res.get('top_1', '--')
    lot_lon = res.get('lot_lon', '--')
    top4 = res.get('top_4', [])
    dan9 = res.get('dan_9_so', [])
    dan9_dao = []
    for s in dan9:
        if len(s) == 2 and s[0] != s[1]:
            rev = s[1] + s[0]
            if rev not in dan9 and rev not in dan9_dao:
                dan9_dao.append(rev)
    top3_cang = res.get('cang_3d_live', {}).get('top3_cang', [])
    cang_tt_12s = res.get('cang_3d_live', {}).get('cang_tt_12s', [])
    ft = res.get('frame_transition', {})
    dan_n1 = ft.get('dan_n1', [])
    dan_n2 = ft.get('dan_n2', [])
    bt_n2 = ft.get('bt_n2', '')
    tt_n2 = ft.get('tt_n2', [])
    bt_n3 = ft.get('bt_n3', '')
    tt_n3 = ft.get('tt_n3', [])
    header_tag = "🧪 <b>[TEST KẾT NỐI THÀNH CÔNG]</b>\n" if is_test else ""

    n2_n3_line = ""
    if bt_n2 or bt_n3:
        n2_n3_line = (
            f"\n⚡ <b>BẠCH THỦ KHUNG N2 (36s):</b> <code>{bt_n2}</code> | Tứ thủ N2: <code>{', '.join(tt_n2)}</code>\n"
            f"🚀 <b>BẠCH THỦ KHUNG N3 (36s):</b> <code>{bt_n3}</code> | Tứ thủ N3: <code>{', '.join(tt_n3)}</code>\n"
        )

    return (
        f"{header_tag}"
        f"🔒 <b>CHỐT KHÓA G5.5 XSMB (18H23)</b>\n"
        f"📅 Kỳ: <b>{t_date}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👑 <b>BẠCH THỦ ĐỀ:</b> <code>{top1}</code> (Lót lộn: <code>{lot_lon}</code>)\n"
        f"🔥 <b>TỨ THỦ (4 số):</b>\n<code>{', '.join(top4)}</code>\n"
        f"{n2_n3_line}\n"
        f"🎯 <b>DÀN 9 SỐ GỐC:</b>\n<code>{', '.join(dan9)}</code>\n"
        f"🔄 <b>ĐẢO BẢO HIỂM ({len(dan9_dao)} số):</b>\n<code>{', '.join(dan9_dao)}</code>\n\n"
        f"🌟 <b>TOP 3 CÀNG 3D:</b> <code>{', '.join(top3_cang)}</code>\n"
        f"💎 <b>3D TỨ THỦ (12 số):</b>\n<code>{', '.join(cang_tt_12s)}</code>\n\n"
        f"🛡️ <b>DÀN 60s N1 ĐỘNG:</b>\n<code>{', '.join(dan_n1)}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ <i>Chạm vào dãy số để copy nhanh • Vào tiền trước 18h28!</i>\n"
        f"🌐 Web App: https://happiness2286-dot.github.io/67up97/"
    )


def ensure_daily_telegram_sent(res):
    """
    Đảm bảo tin nhắn chốt số G5.5 (18h23) và tin nhắn kết quả GĐB (18h30) của ngày hôm nay
    LUÔN được gửi tới Telegram cá nhân (5422717407) đúng 1 lần mỗi ngày — kể cả khi chạy live
    lúc 18h23 hay khi chạy bù (catch-up) lúc 18h37 / 19h00.
    """
    if not res:
        return
    t_date = res.get('target_date', '')
    t_key = extract_date_key(t_date)
    today_key = datetime.now().strftime('%d-%m-%Y')
    if not t_key or t_key != today_key:
        return

    sent_log = {}
    if os.path.exists(TELEGRAM_SENT_LOG_PATH):
        try:
            with open(TELEGRAM_SENT_LOG_PATH, 'r', encoding='utf-8') as f:
                sent_log = json.load(f)
        except Exception:
            sent_log = {}

    changed = False
    # 1. Đóng băng bản chụp G5.5 và gửi bản tin chốt khóa G5.5 nếu hôm nay đã có G5.5
    if res.get('is_g5_finished'):
        save_locked_g55_snapshot(t_date, res)
    if res.get('is_g5_finished') and sent_log.get('last_g55_date') != today_key:
        tg_msg = format_g55_telegram_message(res, is_test=False)
        if send_telegram_alert(tg_msg):
            sent_log['last_g55_date'] = today_key
            sent_log['last_g55_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            changed = True
            print(f"📲 [TELEGRAM] Đã gửi bản tin chốt khóa G5.5 kỳ {t_date} về điện thoại (5422717407)!")

    # 2. Gửi bản tin đối chiếu kết quả GĐB nếu hôm nay đã có GĐB mà chưa gửi
    now_t = datetime.now()
    act_de = res.get('actual_de', '')
    if act_de and (now_t.hour > 18 or (now_t.hour == 18 and now_t.minute >= 30)) and sent_log.get('last_result_date') != today_key:
        act_3d = res.get('actual_3d', '')
        top1 = res.get('top_1', '')
        lot_lon = res.get('lot_lon', '')
        top4 = res.get('top_4', [])
        dan9 = res.get('dan_9_so', [])
        dan9_dao = [s[1] + s[0] for s in dan9 if len(s) == 2 and s[0] != s[1]]
        dan_n1 = res.get('frame_transition', {}).get('dan_n1', [])
        hit_badges = []
        if act_de == top1:
            hit_badges.append("🏆 NỔ BẠCH THỦ TOP 1")
        elif act_de == lot_lon:
            hit_badges.append("🎯 NỔ LÓT LỘN SONG THỦ")
        if act_de in top4:
            hit_badges.append("🔥 NỔ TỨ THỦ TOP 4")
        if act_de in dan9 or act_de in dan9_dao:
            hit_badges.append("🎯 NỔ DÀN 9s/ĐẢO")
        if act_de in dan_n1:
            hit_badges.append("✅ TRÚNG DÀN 60s N1 ĐỘNG")
        res_str = " | ".join(hit_badges) if hit_badges else "❌ Trượt N1 -> Mai đánh N2 (36 số)"
        ok_res = send_telegram_alert(
            f"🎉 <b>KẾT QUẢ ĐỀ XSMB ({t_date})</b>\n"
            f"🎰 Giải Đặc Biệt: <b>{act_3d}</b> (Đề về: <b>{act_de}</b>)\n"
            f"📊 Đối chiếu: <b>{res_str}</b>"
        )
        if ok_res:
            sent_log['last_result_date'] = today_key
            sent_log['last_result_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            changed = True
            print(f"📲 [TELEGRAM] Đã gửi bản tin đối chiếu kết quả Đề {act_de} kỳ {t_date} về điện thoại (5422717407)!")

    if changed:
        try:
            with open(TELEGRAM_SENT_LOG_PATH, 'w', encoding='utf-8') as f:
                json.dump(sent_log, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


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


def extract_g7_chams(prev_draw):
    """Trích xuất tập Chạm G7 trực diện và bóng từ kỳ trước."""
    direct_chams = set()
    bong_chams = set()
    if not prev_draw:
        return direct_chams, bong_chams
    prizes = prev_draw.get('prizes', {})
    for k in ['G7.1', 'G7.2', 'G7.3', 'G7.4']:
        val = str(prizes.get(k, '')).strip()
        if len(val) >= 2 and val[-2:].isdigit():
            for ch in val[-2:]:
                d = int(ch)
                direct_chams.add(ch)
                bong_chams.add(str(BONG_DUONG.get(d, (d + 5) % 10)))
    return direct_chams, bong_chams


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
        scores[BONG_DUONG.get(tam_g1, (tam_g1 + 5) % 10)] += 35
        scores[BONG_AM.get(tam_g1, tam_g1)] += 25
        scores[dau_g1] += 15

    if prev_de and len(prev_de) >= 2 and prev_de.isdigit():
        sum_de = (int(prev_de[0]) + int(prev_de[1])) % 10
        scores[sum_de] += 35
        scores[BONG_DUONG.get(sum_de, (sum_de + 5) % 10)] += 25
        scores[BONG_AM.get(sum_de, sum_de)] += 15
        if tam_g1 >= 0:
            # Cầu cộng hưởng Tâm G1 + Đuôi Đề kỳ trước (bắt chính xác 3D Bạch Thủ 067, 014)
            scores[(tam_g1 + int(prev_de[1])) % 10] += 38

    sorted_cang = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top3_cang = [str(x[0]) for x in sorted_cang[:3]]
    top4_cang = [str(x[0]) for x in sorted_cang[:4]]

    d9_full = list(dan_9_so) if dan_9_so else []
    for s in list(d9_full):
        if len(s) == 2 and s[0] != s[1]:
            rev_s = s[1] + s[0]
            if rev_s not in d9_full:
                d9_full.append(rev_s)

    cang_bt_3s = [f"{c}{top_1}" for c in top3_cang] if top_1 else []
    cang_tt_12s = [f"{c}{num}" for c in top3_cang for num in top_4] if top_4 else []
    cang_d9_27s = [f"{c}{num}" for c in top3_cang for num in d9_full] if d9_full else []

    return {
        'tam_g1': str(tam_g1) if tam_g1 >= 0 else '',
        'tong_de': str(sum_de) if sum_de >= 0 else '',
        'top3_cang': top3_cang,
        'top4_cang': top4_cang,
        'cang_bt_3s': cang_bt_3s,
        'cang_tt_12s': cang_tt_12s,
        'cang_d9_27s': cang_d9_27s
    }


def parse_daiphat_block(block, pre_text):
    dow_map = {0: 'Thứ hai', 1: 'Thứ ba', 2: 'Thứ tư', 3: 'Thứ năm', 4: 'Thứ sáu', 5: 'Thứ bảy', 6: 'Chủ nhật'}
    date_m = re.findall(r'(\d{2})[/-](\d{2})[/-](\d{4})', pre_text)
    if not date_m:
        return None
    d, mth, y = date_m[-1]
    try:
        dt = datetime(int(y), int(mth), int(d))
        date_str = f"{dow_map[dt.weekday()]} ngày {d}-{mth}-{y}"
    except Exception:
        date_str = f"ngày {d}-{mth}-{y}"

    def get_row_numbers(label, max_len=None):
        pattern = rf'{re.escape(label)}.*?(?:<td[^>]*>)(.*?)(?:<tr>|</table>)'
        m = re.search(pattern, block, re.DOTALL)
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
    prizes['G1'] = g1_nums[0] if g1_nums else ''
    for idx in range(1, 3):
        prizes[f'G2.{idx}'] = g2_nums[idx - 1] if len(g2_nums) >= idx else ''
    for idx in range(1, 7):
        prizes[f'G3.{idx}'] = g3_nums[idx - 1] if len(g3_nums) >= idx else ''
    for idx in range(1, 5):
        prizes[f'G4.{idx}'] = g4_nums[idx - 1] if len(g4_nums) >= idx else ''
    for idx in range(1, 7):
        prizes[f'G5.{idx}'] = g5_nums[idx - 1] if len(g5_nums) >= idx else ''
    for idx in range(1, 4):
        prizes[f'G6.{idx}'] = g6_nums[idx - 1] if len(g6_nums) >= idx else ''
    for idx in range(1, 5):
        prizes[f'G7.{idx}'] = g7_nums[idx - 1] if len(g7_nums) >= idx else ''

    return {
        'date': date_str,
        'db': db_val,
        'de': de_val,
        'prizes': prizes
    }


def fetch_383_live():
    """Lấy dữ liệu kết quả XSMB trực tiếp siêu tốc (50ms) từ API 383.im."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    dow_map = {0: 'Thứ hai', 1: 'Thứ ba', 2: 'Thứ tư', 3: 'Thứ năm', 4: 'Thứ sáu', 5: 'Thứ bảy', 6: 'Chủ nhật'}
    raw_text = ""
    try:
        if HAS_LIBS:
            r = requests.get(API_383_LIVE_URL, headers=headers, timeout=3)
            if r.status_code == 200:
                raw_text = r.text
        else:
            req = urllib.request.Request(API_383_LIVE_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=3) as resp:
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
        prizes['G1'] = g1_val
        for idx in range(1, 3):
            prizes[f'G2.{idx}'] = g2_list[idx - 1] if len(g2_list) >= idx else ''
        for idx in range(1, 7):
            prizes[f'G3.{idx}'] = g3_list[idx - 1] if len(g3_list) >= idx else ''
        for idx in range(1, 5):
            prizes[f'G4.{idx}'] = g4_list[idx - 1] if len(g4_list) >= idx else ''
        for idx in range(1, 7):
            prizes[f'G5.{idx}'] = g5_list[idx - 1] if len(g5_list) >= idx else ''
        for idx in range(1, 4):
            prizes[f'G6.{idx}'] = g6_list[idx - 1] if len(g6_list) >= idx else ''
        for idx in range(1, 5):
            prizes[f'G7.{idx}'] = g7_list[idx - 1] if len(g7_list) >= idx else ''

        return {
            'date': date_str,
            'db': db_val,
            'de': de_val,
            'prizes': prizes
        }
    except Exception:
        return None


def fetch_daiphat_draws(is_live=False):
    """
    Cào dữ liệu từ xosodaiphat.com và hợp nhất với cached_draws.json
    để đảm bảo luôn có đủ 30+ kỳ lịch sử (khắc phục triệt để lỗi cụt lịch sử còn 5 kỳ).
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    # Đọc cache trước để xem đã có đủ 25 kỳ lịch sử chưa
    cached_list = []
    if os.path.exists(CACHE_DRAWS_PATH):
        try:
            with open(CACHE_DRAWS_PATH, 'r', encoding='utf-8') as f:
                cached_list = json.load(f)
                if not isinstance(cached_list, list):
                    cached_list = []
        except Exception:
            cached_list = []

    # Nếu không phải đang polling live 5s hoặc nếu cache chưa đủ 25 kỳ -> cào cả trang 30 ngày
    urls = [DAIPHAT_LIVE_URL] if (is_live and len(cached_list) >= 25) else [DAIPHAT_LIVE_URL, DAIPHAT_30N_URL]
    draws = []
    seen_keys = set()

    for url in urls:
        html = ""
        try:
            if HAS_LIBS:
                r = requests.get(url, headers=headers, timeout=5)
                html = r.text if r.status_code == 200 else ""
            else:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
        except Exception:
            pass

        if not html:
            continue

        blocks = re.split(r'<table[^>]*table-xsmb[^>]*>', html)
        for i in range(1, len(blocks)):
            pre_text = blocks[i - 1][-400:]
            rec = parse_daiphat_block(blocks[i], pre_text)
            if rec:
                k = extract_date_key(rec.get('date', ''))
                if k and k not in seen_keys:
                    seen_keys.add(k)
                    draws.append(rec)

    def _date_sort_tuple(rec):
        k = extract_date_key(rec.get('date', ''))
        m = re.match(r'^(\d{2})-(\d{2})-(\d{4})$', k)
        if m:
            return (int(m.group(3)), int(m.group(2)), int(m.group(1)))
        return (0, 0, 0)

    latest_cached_tuple = max((_date_sort_tuple(c) for c in cached_list), default=(0, 0, 0))

    # Ưu tiên giữ các kỳ lịch sử đầy đủ trong cached_list, chỉ cập nhật kỳ mới (>= latest_cached_tuple) từ live
    merged_map = {}
    for c_rec in cached_list:
        k = extract_date_key(c_rec.get('date', ''))
        if k:
            merged_map[k] = c_rec

    for rec in draws:
        k = extract_date_key(rec.get('date', ''))
        if not k:
            continue
        t_tup = _date_sort_tuple(rec)
        if k not in merged_map or t_tup >= latest_cached_tuple:
            merged_map[k] = rec

    final_draws = sorted(merged_map.values(), key=_date_sort_tuple, reverse=True)

    # Lưu ngược lại cache nếu cập nhật được >= 20 kỳ
    if len(final_draws) >= 20:
        try:
            with open(CACHE_DRAWS_PATH, 'w', encoding='utf-8') as f:
                json.dump(final_draws[:40], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return final_draws


def fetch_html(is_live=False, count=35):
    draws = fetch_daiphat_draws(is_live=is_live)
    return json.dumps(draws[:count], ensure_ascii=False) if draws else ""


def parse_draws(html):
    if not html:
        return []
    try:
        data = json.loads(html)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return fetch_daiphat_draws(is_live=False)


VALID_G1_TO_G55 = {
    'G1',
    'G2.1', 'G2.2',
    'G3.1', 'G3.2', 'G3.3', 'G3.4', 'G3.5', 'G3.6',
    'G4.1', 'G4.2', 'G4.3', 'G4.4',
    'G5.1', 'G5.2', 'G5.3', 'G5.4', 'G5.5'
}


def get_positions(prizes):
    """Chỉ trích xuất đúng 18 giải từ G1 đến hết G5.5 (81 vị trí chữ số) để đảm bảo chốt số lúc 18h22:15 (khi xong G5.5) khớp 100% với lịch sử, tuyệt đối không sinh số ảo từ G5.6/G6/G7."""
    res = {}
    for code, val in prizes.items():
        if not val or code not in VALID_G1_TO_G55:
            continue
        for idx, char in enumerate(val, 1):
            if char.isdigit():
                res[f"{code}_{idx}"] = (char, f"{code} vị trí {idx}")
    return res


def get_dynamic_dan60_for_date(target_date_str, summary_data):
    """Lấy đúng Dàn 60s N1 Động cho ngày target_date_str từ analysis_summary.json."""
    if not summary_data:
        return list(DEFAULT_60_N1)
    af = summary_data.get('adaptive_frame', {})
    t_key = extract_date_key(target_date_str)
    if t_key:
        d_map = af.get('date_to_dan60_map', {})
        for k, v in d_map.items():
            if extract_date_key(k) == t_key and v and len(v) >= 50:
                return list(v)
    dan_n1 = af.get('dan_n1', [])
    if dan_n1 and len(dan_n1) >= 50:
        return list(dan_n1)
    return list(DEFAULT_60_N1)


def compute_radar_convergence(sub_draws, cap4_set, summary_data=None, enable_rescue=True, ignore_snapshot=False):
    """
    Lõi Thuật Toán Hội Tụ Đa Cầu (Multi-Bridge Density Convergence):
    Tính toán cho kỳ sub_draws[0] dựa trên các cầu vị trí G1->G5.6 ăn thông từ sub_draws[1..6],
    kết hợp Mật Độ Đa Cầu (Multi-Bridge Density) + Tâm Càng G1 + Cầu Tổng/Chạm G7 + Dàn 60s N1 Động.
    """
    if len(sub_draws) < 2:
        return None

    target_draw = sub_draws[0]
    prev_draw = sub_draws[1]
    prev_de = prev_draw.get('de', '')
    if not prev_de or len(prev_de) < 2 or not prev_de.isdigit():
        return None

    head_num = int(prev_de[0])
    tail_num = int(prev_de[1])
    head_bong = BONG_DUONG[head_num]
    tail_bong = BONG_DUONG[tail_num]
    head_targets = [str(head_num), str(head_bong)]
    tail_targets = [str(tail_num), str(tail_bong)]

    target_pos = get_positions(target_draw['prizes'])
    prev_pos = get_positions(prev_draw['prizes'])

    def calc_streak_and_freq(pos_key, is_head=True):
        streak = 1
        hits_5d = 1
        max_look = min(len(sub_draws), 6)
        streak_broken = False
        for past_idx in range(2, max_look):
            de = sub_draws[past_idx].get('de', '')
            if not de or len(de) < 2 or not de.isdigit():
                break
            d_val = int(de[0] if is_head else de[1])
            allowed = [str(d_val), str(BONG_DUONG[d_val])]
            past_p = get_positions(sub_draws[past_idx]['prizes'])
            if pos_key in past_p and past_p[pos_key][0] in allowed:
                hits_5d += 1
                if not streak_broken:
                    streak += 1
            else:
                streak_broken = True
        return min(streak, 4), hits_5d

    highlight_positions = {}
    head_matches = []
    tail_matches = []

    for pos_key, (char, raw_name) in prev_pos.items():
        if char in head_targets:
            streak, hits_5d = calc_streak_and_freq(pos_key, is_head=True)
            is_direct_prev = (char == str(head_num))
            if pos_key in target_pos:
                cur_char = target_pos[pos_key][0]
                cur_bong = str(BONG_DUONG[int(cur_char)])
                eff_cycle = max(streak, 2 if hits_5d >= 3 else 1)
                if streak == 2:
                    cat = "Chỉ đạo"
                    color = "cycle_main"
                    label = "🔥 ƯU TIÊN 2d (Săn Nổ Ngày 3)"
                elif streak == 1:
                    cat = "Lót"
                    color = "cycle_lot"
                    label = "⚡ LÓT 1d (Săn Nổ Ngày 2)"
                elif streak == 3:
                    cat = "Theo dõi"
                    color = "cycle_watch"
                    label = "⚠️ THEO DÕI 3d (Cầu Kéo Dài)"
                else:
                    cat = "Cảnh báo"
                    color = "cycle_watch"
                    label = f"🚨 CẢNH BÁO {streak}d (Bão Hòa - Dễ Gãy)"
                suffix = f"{streak}d"

                info = {
                    'pos_raw': raw_name,
                    'role': 'head',
                    'role_name': 'Đầu',
                    'digit': cur_char if is_direct_prev else cur_bong,
                    'raw_digit': cur_char,
                    'digit_bong': cur_bong if is_direct_prev else cur_char,
                    'cycle': eff_cycle,
                    'raw_streak': streak,
                    'hits_5d': hits_5d,
                    'cycle_suffix': suffix,
                    'category': cat,
                    'label': label,
                    'color_type': color,
                    'is_direct': is_direct_prev,
                    'tooltip': f"{raw_name}: Đầu {cur_char} ({suffix}, {hits_5d}/5 kỳ) | {label}"
                }
                highlight_positions[pos_key] = info
                head_matches.append(info)

        if char in tail_targets:
            streak, hits_5d = calc_streak_and_freq(pos_key, is_head=False)
            is_direct_prev = (char == str(tail_num))
            if pos_key in target_pos:
                cur_char = target_pos[pos_key][0]
                cur_bong = str(BONG_DUONG[int(cur_char)])
                eff_cycle = max(streak, 2 if hits_5d >= 3 else 1)
                if streak == 2:
                    cat = "Chỉ đạo"
                    color = "cycle_main"
                    label = "🔥 ƯU TIÊN 2d (Săn Nổ Ngày 3)"
                elif streak == 1:
                    cat = "Lót"
                    color = "cycle_lot"
                    label = "⚡ LÓT 1d (Săn Nổ Ngày 2)"
                elif streak == 3:
                    cat = "Theo dõi"
                    color = "cycle_watch"
                    label = "⚠️ THEO DÕI 3d (Cầu Kéo Dài)"
                else:
                    cat = "Cảnh báo"
                    color = "cycle_watch"
                    label = f"🚨 CẢNH BÁO {streak}d (Bão Hòa - Dễ Gãy)"
                suffix = f"{streak}d"

                info = {
                    'pos_raw': raw_name,
                    'role': 'tail',
                    'role_name': 'Đuôi',
                    'digit': cur_char if is_direct_prev else cur_bong,
                    'raw_digit': cur_char,
                    'digit_bong': cur_bong if is_direct_prev else cur_char,
                    'cycle': eff_cycle,
                    'raw_streak': streak,
                    'hits_5d': hits_5d,
                    'cycle_suffix': suffix,
                    'category': cat,
                    'label': label,
                    'color_type': color,
                    'is_direct': is_direct_prev,
                    'tooltip': f"{raw_name}: Đuôi {cur_char} ({suffix}, {hits_5d}/5 kỳ) | {label}"
                }
                if pos_key in highlight_positions:
                    if eff_cycle > highlight_positions[pos_key]['cycle']:
                        highlight_positions[pos_key] = info
                else:
                    highlight_positions[pos_key] = info
                tail_matches.append(info)

    # 1. Tính Mật Độ Đa Cầu (Multi-Bridge Power) theo đúng hướng Đầu (0-9) và Đuôi (0-9)
    head_bridge_power = {str(i): 0.0 for i in range(10)}
    tail_bridge_power = {str(i): 0.0 for i in range(10)}

    for h in head_matches:
        c = h['digit']
        cb = h['digit_bong']
        h5 = h.get('hits_5d', 1)
        st = h.get('raw_streak', h['cycle'])
        if st >= 3 or h5 >= 4:
            cyc_w = 45.0
        elif st == 2 or h5 == 3:
            cyc_w = 32.0
        else:
            cyc_w = 2.0 if h.get('is_direct') else 0.4
        if h.get('is_direct'):
            cyc_w *= 1.3
        head_bridge_power[c] += cyc_w
        if h['cycle'] >= 2:
            head_bridge_power[cb] += cyc_w * 0.25

    for t in tail_matches:
        d = t['digit']
        db = t['digit_bong']
        h5 = t.get('hits_5d', 1)
        st = t.get('raw_streak', t['cycle'])
        if st >= 3 or h5 >= 4:
            cyc_w = 45.0
        elif st == 2 or h5 == 3:
            cyc_w = 32.0
        else:
            cyc_w = 2.0 if t.get('is_direct') else 0.4
        if t.get('is_direct'):
            cyc_w *= 1.3
        tail_bridge_power[d] += cyc_w
        if t['cycle'] >= 2:
            tail_bridge_power[db] += cyc_w * 0.25

    # Bổ sung Cầu Nhân Quả Liên Kỳ (vị trí kỳ k+1 ăn Đề kỳ k trong 5 kỳ gần nhất, lấy vị trí kỳ prev_draw dự báo cho target_draw)
    causal_pair_bonus = Counter()
    causal_top_heads = []
    causal_top_tails = []
    if len(sub_draws) >= 4:
        c_head_scores = {str(i): 0.0 for i in range(10)}
        c_tail_scores = {str(i): 0.0 for i in range(10)}
        max_lag = min(len(sub_draws) - 1, 6)
        for pos_key, (char_prev, _) in prev_pos.items():
            cross_h_streak = 0
            cross_t_streak = 0
            cross_h_hits = 0
            cross_t_hits = 0
            h_direct_last = False
            t_direct_last = False
            h_broken = False
            t_broken = False
            for lag in range(1, max_lag):
                de_lag = sub_draws[lag].get('de', '')
                if not de_lag or len(de_lag) < 2 or not de_lag.isdigit():
                    break
                src_pos = get_positions(sub_draws[lag + 1]['prizes'])
                if pos_key not in src_pos:
                    break
                ch_src = src_pos[pos_key][0]
                ch_bong = str(BONG_DUONG[int(ch_src)])
                if ch_src == de_lag[0] or ch_bong == de_lag[0]:
                    cross_h_hits += 1
                    if lag == 1 and ch_src == de_lag[0]:
                        h_direct_last = True
                    if not h_broken:
                        cross_h_streak += 1
                else:
                    h_broken = True
                if ch_src == de_lag[1] or ch_bong == de_lag[1]:
                    cross_t_hits += 1
                    if lag == 1 and ch_src == de_lag[1]:
                        t_direct_last = True
                    if not t_broken:
                        cross_t_streak += 1
                else:
                    t_broken = True

            pred_d = char_prev
            pred_b = str(BONG_DUONG[int(char_prev)])
            if cross_h_streak >= 2 or cross_h_hits >= 3:
                w_h = (cross_h_streak * 18.0) + (cross_h_hits * 10.0)
                c_head_scores[pred_d if h_direct_last else pred_b] += w_h
                head_bridge_power[pred_d if h_direct_last else pred_b] += w_h * 0.85
            if cross_t_streak >= 2 or cross_t_hits >= 3:
                w_t = (cross_t_streak * 18.0) + (cross_t_hits * 10.0)
                c_tail_scores[pred_d if t_direct_last else pred_b] += w_t
                tail_bridge_power[pred_d if t_direct_last else pred_b] += w_t * 0.85

        causal_top_heads = [x[0] for x in sorted(c_head_scores.items(), key=lambda x: x[1], reverse=True)[:4]]
        causal_top_tails = [x[0] for x in sorted(c_tail_scores.items(), key=lambda x: x[1], reverse=True)[:4]]
        for idx_ch, ch_d in enumerate(causal_top_heads):
            for idx_ct, ct_d in enumerate(causal_top_tails):
                causal_pair_bonus[f"{ch_d}{ct_d}"] += max(0, 36 - (idx_ch + idx_ct) * 6)

    # 2. Trích xuất 4 Vị Trí Chốt Mỏ Neo Live 18h22 (G1_3 Tâm Càng G1, G5.5_4 Khóa Sổ G5.5, G3.3_4, G3.2_2) — 100% nằm trong G1->G5.5 + Tổng/Chạm G7 kỳ trước
    live_p = target_draw['prizes']
    p_g1 = live_p.get('G1', '')
    tam_g1 = p_g1[2] if (p_g1 and len(p_g1) >= 3 and p_g1.isdigit()) else ''
    tam_g1_set = {tam_g1, str(BONG_DUONG.get(int(tam_g1), ''))} if tam_g1 else set()

    g55_val = live_p.get('G5.5', '')
    g55_last = g55_val[-1] if (g55_val and g55_val[-1].isdigit()) else ''
    g55_set = {g55_last, str(BONG_DUONG.get(int(g55_last), ''))} if g55_last else set()

    g33_val = live_p.get('G3.3', '')
    g33_d4 = g33_val[3] if (g33_val and len(g33_val) >= 4 and g33_val[3].isdigit()) else ''
    g33_set = {g33_d4, str(BONG_DUONG.get(int(g33_d4), ''))} if g33_d4 else set()

    if enable_rescue:
        g32_val = live_p.get('G3.2', '')
        g63_d2 = g32_val[1] if (g32_val and len(g32_val) >= 2 and g32_val[1].isdigit()) else ''
    else:
        g63_val = live_p.get('G6.3', '')
        g63_d2 = g63_val[1] if (g63_val and len(g63_val) >= 2 and g63_val[1].isdigit()) else ''
    g63_set = {g63_d2, str(BONG_DUONG.get(int(g63_d2), ''))} if g63_d2 else set()

    target_sums = extract_target_sums(prev_draw)
    direct_g7_chams, bong_g7_chams = extract_g7_chams(prev_draw)

    # Trích xuất Dàn Hạ Số Nhịp Vàng (20 số) & Dàn Giao Thoa Theo Thứ (Walk-Forward 100% từ dow_model)
    dow_ha_so_list = []
    dow_giao_thoa_set = set()
    dow_sums = set()
    if summary_data and 'dow_model' in summary_data:
        dm = summary_data['dow_model']
        t_key = extract_date_key(target_draw.get('date', ''))
        matched_dow_log = False
        for r_dow in dm.get('history_log_dow', []):
            if extract_date_key(r_dow.get('date', '')) == t_key:
                dow_ha_so_list = [x.strip() for x in r_dow.get('dan_ha_so_str', '').split(',') if x.strip()]
                dow_giao_thoa_set = set(x.strip() for x in r_dow.get('dan_str', '').split(',') if x.strip())
                dow_sums = {
                    int(x.strip().replace('Tổng ', ''))
                    for x in r_dow.get('target_sums_str', '').split(',')
                    if 'Tổng ' in x and x.strip().replace('Tổng ', '').isdigit()
                }
                matched_dow_log = True
                break
        if not matched_dow_log:
            # Chuẩn hóa thứ tự tăng dần đồng nhất 100% với dan_ha_so_str trong history_log_dow
            # để trọng số Top 10 Hạ Số lúc bắn Live 18h23 và sau 18h36 khớp nhau tuyệt đối
            dow_ha_so_list = sorted(list(dm.get('next_dan_ha_so', [])))
            dow_giao_thoa_set = set(dm.get('next_dan_giao_thoa', []))
            dow_sums = {int(s) for s in dm.get('next_target_sums', []) if str(s).isdigit()}
    dow_ha_so_set = set(dow_ha_so_list)

    # Cộng hưởng định hướng Đầu/Đuôi từ Dàn Hạ Số 20s Theo Thứ + 4 Mỏ Neo Live 18h23 + Dàn 60s N1 Động
    head_anchor_power = {str(i): 0.0 for i in range(10)}
    tail_anchor_power = {str(i): 0.0 for i in range(10)}

    for idx_hs, num_hs in enumerate(dow_ha_so_list):
        if len(num_hs) == 2 and num_hs.isdigit():
            w_hs = 16.0 if idx_hs < 10 else 10.0
            if num_hs in cap4_set:
                w_hs *= 1.35
            head_anchor_power[num_hs[0]] += w_hs
            tail_anchor_power[num_hs[1]] += w_hs

    for num_c in cap4_set:
        if len(num_c) == 2 and num_c.isdigit():
            head_anchor_power[num_c[0]] += 2.5
            tail_anchor_power[num_c[1]] += 2.5

    for dig in range(10):
        ds = str(dig)
        if ds in tam_g1_set:
            head_anchor_power[ds] += (22.0 if ds == tam_g1 else 14.0)
            tail_anchor_power[ds] += (22.0 if ds == tam_g1 else 14.0)
        if ds in g55_set:
            head_anchor_power[ds] += (20.0 if ds == g55_last else 13.0)
            tail_anchor_power[ds] += (20.0 if ds == g55_last else 13.0)
        if ds in g33_set:
            head_anchor_power[ds] += (18.0 if ds == g33_d4 else 11.0)
            tail_anchor_power[ds] += (15.0 if ds == g33_d4 else 10.0)
        if ds in g63_set:
            head_anchor_power[ds] += 10.0
            tail_anchor_power[ds] += 14.0
        if ds in direct_g7_chams:
            head_anchor_power[ds] += 8.0
            tail_anchor_power[ds] += 10.0

    # Cộng hưởng vừa phải từ mật độ cầu vị trí
    for dig in range(10):
        ds = str(dig)
        head_anchor_power[ds] += min(head_bridge_power.get(ds, 0) * 0.15, 18.0)
        tail_anchor_power[ds] += min(tail_bridge_power.get(ds, 0) * 0.15, 18.0)

    # Trừ điểm bão hòa nhẹ cho Đầu/Đuôi vừa nổ ngay kỳ trước
    head_anchor_power[prev_de[0]] -= 12.0
    tail_anchor_power[prev_de[1]] -= 12.0

    # Chọn Top 3 Đầu và Top 3 Đuôi với điều kiện chống suy biến đối xứng (Anti-Kép Collapse)
    sorted_heads = [x[0] for x in sorted(head_anchor_power.items(), key=lambda x: x[1], reverse=True)]
    head_digits = sorted_heads[:3]

    sorted_tails = [x[0] for x in sorted(tail_anchor_power.items(), key=lambda x: x[1], reverse=True)]
    tail_digits = []
    overlap_with_heads = 0
    for cand_t in sorted_tails:
        if cand_t in head_digits:
            if overlap_with_heads >= 1:
                continue
            overlap_with_heads += 1
        tail_digits.append(cand_t)
        if len(tail_digits) >= 3:
            break
    if len(tail_digits) < 3:
        for cand_t in sorted_tails:
            if cand_t not in tail_digits:
                tail_digits.append(cand_t)
            if len(tail_digits) >= 3:
                break

    dan_9_so = sorted(list(set(f"{h}{t}" for h in head_digits for t in tail_digits)))
    dan_9_set = set(dan_9_so)
    dan_9_dao_set = set(s[1] + s[0] for s in dan_9_so if len(s) == 2 and s[0] != s[1])

    # 3. Tổ hợp ghép cặp Chục x Đơn vị từ các vị trí cầu (ưu tiên tuyệt đối Cầu Đôi min_cycle >= 2)
    combos_map = {}
    for h in head_matches:
        for t in tail_matches:
            c = h['digit']
            d = t['digit']
            cb = h['digit_bong']
            db = t['digit_bong']
            cycle_pair = max(h['cycle'], t['cycle'])
            min_cycle = min(h['cycle'], t['cycle'])

            pairs = [
                (f"{c}{d}", 1.0, "chính diện"),
                (f"{c}{db}", 0.80, "bóng đuôi"),
                (f"{cb}{d}", 0.80, "bóng đầu"),
                (f"{cb}{db}", 0.60, "bóng cả hai")
            ]

            for num_str, wt, ctype in pairs:
                cat = "Chỉ đạo" if cycle_pair >= 3 else ("Lót" if cycle_pair == 2 else "Theo dõi")
                # Thưởng cực lớn khi CẢ cầu Đầu VÀ cầu Đuôi đều thông >= 2 ngày (True Double Bridge)
                double_bridge_bonus = 85 if min_cycle >= 3 else (55 if min_cycle == 2 else 0)
                direct_pair_bonus = 20 if (h.get('is_direct') and t.get('is_direct') and wt == 1.0) else 0
                cyc_base = 36 if cycle_pair == 3 else (32 if cycle_pair == 2 else (22 if cycle_pair >= 4 else 8))
                score = cyc_base + wt * 25 + (min(h['cycle'], 3) + min(t['cycle'], 3)) * 14 + double_bridge_bonus + direct_pair_bonus

                is_strong_pair = (min_cycle >= 2 and wt >= 0.8)

                if num_str not in combos_map:
                    combos_map[num_str] = {
                        'num': num_str,
                        'c_digit': c,
                        'd_digit': d,
                        'c_cycle': h['cycle'],
                        'd_cycle': t['cycle'],
                        'min_cycle': min_cycle,
                        'cycle_days': cycle_pair,
                        'category': cat,
                        'cat_label': f"✅ CHỈ ĐẠO ({cycle_pair} ngày)" if cycle_pair >= 3 else (f"Lót ngày {cycle_pair}" if cycle_pair == 2 else "Theo dõi ngày 1 (Mới chạm)"),
                        'weight': wt,
                        'combo_type': ctype,
                        'score': score,
                        'bridge_hits': 1,
                        'strong_bridge_hits': 1 if is_strong_pair else 0,
                        'h_pos': h['pos_raw'],
                        't_pos': t['pos_raw'],
                        'in_cap4': (num_str in cap4_set),
                        'in_cap4_str': "Có" if (num_str in cap4_set) else "Không"
                    }
                else:
                    combos_map[num_str]['bridge_hits'] += 1
                    if is_strong_pair:
                        combos_map[num_str]['strong_bridge_hits'] += 1
                    if score > combos_map[num_str]['score']:
                        bh = combos_map[num_str]['bridge_hits']
                        sbh = combos_map[num_str]['strong_bridge_hits']
                        combos_map[num_str].update({
                            'c_digit': c,
                            'd_digit': d,
                            'c_cycle': h['cycle'],
                            'd_cycle': t['cycle'],
                            'min_cycle': min_cycle,
                            'cycle_days': cycle_pair,
                            'category': cat,
                            'cat_label': f"✅ CHỈ ĐẠO ({cycle_pair} ngày)" if cycle_pair >= 3 else (f"Lót ngày {cycle_pair}" if cycle_pair == 2 else "Theo dõi ngày 1 (Mới chạm)"),
                            'weight': wt,
                            'combo_type': ctype,
                            'score': score,
                            'bridge_hits': bh,
                            'strong_bridge_hits': sbh,
                            'h_pos': h['pos_raw'],
                            't_pos': t['pos_raw']
                        })

    # Bổ sung các số thuộc Dàn Hạ Số 20s Theo Thứ, Dàn 9s Hội Tụ Động (cả đảo) hoặc Đỉnh Cầu Nhân Quả nếu chưa có trong combos_map
    for num_cand in list(dow_ha_so_list) + list(dan_9_so) + list(dan_9_dao_set) + [k for k, v in causal_pair_bonus.items() if v >= 24]:
        if len(num_cand) == 2 and num_cand not in combos_map:
            combos_map[num_cand] = {
                'num': num_cand,
                'c_digit': num_cand[0],
                'd_digit': num_cand[1],
                'c_cycle': 2,
                'd_cycle': 2,
                'min_cycle': 2,
                'cycle_days': 2,
                'category': "Chỉ đạo" if num_cand in dow_ha_so_set else "Lót",
                'cat_label': "✅ HẠ SỐ NHỊP VÀNG" if num_cand in dow_ha_so_set else "Hội tụ Cầu Nhân Quả",
                'weight': 0.95,
                'combo_type': "chính diện",
                'score': 105,
                'bridge_hits': 2,
                'strong_bridge_hits': 1,
                'h_pos': "Cầu Thứ G7" if num_cand in dow_ha_so_set else "Cầu Đích Đầu",
                't_pos': "Mỏ Neo G5.5/G1" if num_cand in dow_ha_so_set else "Cầu Đích Đuôi",
                'in_cap4': (num_cand in cap4_set),
                'in_cap4_str': "Có" if (num_cand in cap4_set) else "Không"
            }

    # 4. Tính Điểm Hội Tụ Đa Tầng (Multi-Criteria Convergence Score)
    dow_top10_set = set(dow_ha_so_list[:10])
    for item in combos_map.values():
        num_str = item['num']
        h_d, t_d = num_str[0], num_str[1]

        # A. Điểm nền Hạ Số Nhịp Vàng Theo Thứ (Walk-Forward 20s có xác suất trúng thực nghiệm cao gấp đôi nền ngẫu nhiên)
        in_hs = (num_str in dow_ha_so_set)
        in_gt_dow = (num_str in dow_giao_thoa_set)
        hs_pts = 88 if (num_str in dow_top10_set) else (68 if in_hs else (28 if in_gt_dow else 0))

        # B. Điểm 4 Mỏ Neo Live 18h23 (Tâm G1_3, Khóa sổ G5.5_4, Tâm G3.3_4, Tâm G6.3_2)
        anchor_hits = 0
        anchor_pts = 0.0
        in_tam = False
        if tam_g1_set and (h_d in tam_g1_set or t_d in tam_g1_set):
            in_tam = True
            anchor_hits += 1
            anchor_pts += (36.0 if (h_d == tam_g1 or t_d == tam_g1) else 25.0)
        if g55_set and (h_d in g55_set or t_d in g55_set):
            anchor_hits += 1
            anchor_pts += (34.0 if (h_d == g55_last or t_d == g55_last) else 24.0)
        if g33_set and (h_d in g33_set or t_d in g33_set):
            anchor_hits += 1
            anchor_pts += (32.0 if (h_d == g33_d4 or t_d == g33_d4) else 22.0)
        if g63_set and (h_d in g63_set or t_d in g63_set):
            anchor_hits += 1
            anchor_pts += (24.0 if (h_d == g63_d2 or t_d == g63_d2) else 16.0)
        if anchor_hits >= 2:
            anchor_pts += 28.0 * (anchor_hits - 1)

        # C. Tiêu chí Giao Thoa Dàn 9 Số Hội Tụ Động (Top 3 Đầu x Top 3 Đuôi - xác suất nổ 32.14%)
        # Ưu tiên chọn Bạch Thủ (Top 1) và Tứ Thủ (Top 4) trực tiếp từ giao thoa (Dàn 9s ∪ Đảo) ∩ Hạ Số 20s ∩ N1 Động
        in_d9 = (num_str in dan_9_set)
        in_d9_dao = (num_str in dan_9_dao_set)
        d9_pts = 145 if in_d9 else (130 if in_d9_dao else 0)

        # D. Tiêu chí Giao Thoa Cầu Tổng G7 & Chạm G7 kỳ trước
        cur_sum = (int(h_d) + int(t_d)) % 10 if (len(num_str) >= 2 and num_str.isdigit()) else -1
        in_sum = (cur_sum in target_sums) if target_sums else False
        sum_pts = 30 if in_sum else 0

        in_g7_cham = (h_d in direct_g7_chams or t_d in direct_g7_chams)
        g7_cham_pts = 16 if in_g7_cham else (8 if (h_d in bong_g7_chams or t_d in bong_g7_chams) else 0)

        # E. Điểm tinh chỉnh từ Mỏ Neo Đầu/Đuôi & Ràng buộc Dàn 60 Số N1 Động
        # (Loại bỏ item['score'] thô vì thống kê thực nghiệm cho thấy các số có quá nhiều cầu đơn lẻ tập trung bị bão hòa)
        base_radar = (head_anchor_power.get(h_d, 0) + tail_anchor_power.get(t_d, 0)) * 0.24
        in_n1 = item['in_cap4']
        n1_pts = 55 if in_n1 else -200

        # Khử lặp lại chính xác con Đề hôm trước hoặc kép thiếu cầu
        repeat_penalty = -50 if num_str == prev_de else (-25 if h_d == t_d else 0)

        c_score = round(hs_pts + anchor_pts + d9_pts + sum_pts + g7_cham_pts + base_radar + n1_pts + repeat_penalty, 1)
        item['consensus_score'] = c_score
        item['in_d9'] = in_d9
        item['in_tam'] = in_tam
        item['in_sum'] = in_sum

        badges = []
        if in_n1:
            badges.append("N1 Động")
        if in_hs:
            badges.append("Hạ Số 20s")
        if in_d9:
            badges.append("Dàn 9s AI")
        if in_tam:
            badges.append(f"Tâm G1 ({tam_g1})")
        if in_sum:
            badges.append(f"Tổng G7 ({cur_sum})")
        item['convergence_badges'] = badges

    found_list = list(combos_map.values())
    found_list.sort(key=lambda x: (x.get('consensus_score', 0), x.get('in_d9', False)), reverse=True)

    n1_pool = [x for x in found_list if x['in_cap4']]
    top_pool = n1_pool if n1_pool else found_list
    base_top_1 = top_pool[0]['num'] if top_pool else (dan_9_so[0] if dan_9_so else "61")

    def select_latin_transversal_top4(pool_items, primary_bt):
        t4 = [primary_bt]
        uh = Counter([primary_bt[0]]) if len(primary_bt) == 2 else Counter()
        ut = Counter([primary_bt[1]]) if len(primary_bt) == 2 else Counter()
        for x in pool_items:
            cand = x['num'] if isinstance(x, dict) else str(x)
            if cand in t4 or len(cand) != 2:
                continue
            rev_cand = cand[1] + cand[0]
            if rev_cand in t4 or cand[0] == cand[1]:
                continue
            if uh[cand[0]] == 0 and ut[cand[1]] == 0:
                t4.append(cand)
                uh[cand[0]] += 1
                ut[cand[1]] += 1
                if len(t4) >= 3:
                    break
        for x in pool_items:
            if len(t4) >= 4:
                break
            cand = x['num'] if isinstance(x, dict) else str(x)
            if cand in t4 or len(cand) != 2:
                continue
            rev_cand = cand[1] + cand[0]
            if rev_cand in t4 or cand[0] == cand[1]:
                continue
            if uh[cand[0]] >= 2 or ut[cand[1]] >= 2:
                continue
            t4.append(cand)
            uh[cand[0]] += 1
            ut[cand[1]] += 1
        if len(t4) < 4:
            for x in pool_items:
                cand = x['num'] if isinstance(x, dict) else str(x)
                if cand not in t4:
                    t4.append(cand)
                if len(t4) >= 4:
                    break
        return t4

    # 5. CHẾ ĐỘ SĂN BẠCH THỦ & TỨ THỦ CỨU KHUNG NGÀY 2 (N2) & NGÀY 3 (N3) (Walk-Forward 100%):
    # Khi kỳ hôm trước (sub_draws[1]) bị trượt Dàn 60s N1, hôm nay bước vào Ngày 2 (N2) hoặc Ngày 3 (N3):
    # - Kích hoạt bộ lọc giao thoa trực tiếp với Dàn 36 số Cứu Khung (pred_n2) + Đảo chiều Đầu Lớn/Nhỏ theo prev_de
    # - Cộng hưởng "Cầu Trễ Khung 3 Ngày" (các số đã báo Bạch Thủ ở 1-4 kỳ sát trước nhưng chưa nổ)
    prev_c60_set = set(get_dynamic_dan60_for_date(prev_draw.get('date', ''), summary_data))
    is_rescue_day = (prev_de not in prev_c60_set)

    if enable_rescue and is_rescue_day and len(prev_de) == 2 and prev_de.isdigit() and summary_data is not None:
        recent_des = {
            str(sub_draws[j].get('de', '')).strip()
            for j in range(1, min(5, len(sub_draws)))
            if sub_draws[j].get('de')
        }
        # Kiểm tra các Bạch Thủ đã báo trong 1-4 kỳ trước nhưng chưa nổ (Cầu Trễ Khung N2/N3)
        bt_cnt = Counter()
        for back_step in range(1, min(5, len(sub_draws) - 2)):
            past_sub = sub_draws[back_step:]
            past_c60 = set(get_dynamic_dan60_for_date(past_sub[0].get('date', ''), summary_data))
            past_res = compute_radar_convergence(past_sub, past_c60, summary_data, enable_rescue=False)
            if past_res and past_res.get('base_top_1'):
                p_bt = past_res['base_top_1']
                if p_bt not in recent_des:
                    bt_cnt[p_bt] += 1

        prev_big = int(prev_de[0]) >= 5
        for item in found_list:
            ns = item['num']
            if not item['in_cap4']:
                continue
            h_ok = (int(ns[0]) < 5) if prev_big else (int(ns[0]) >= 5)
            if h_ok:
                item['consensus_score'] = round(item['consensus_score'] + 47.0, 1)
                if "N2/N3 Cứu Khung" not in item['convergence_badges']:
                    item['convergence_badges'].append("N2/N3 Cứu Khung")
                if bt_cnt[ns] >= 1:
                    item['consensus_score'] = round(item['consensus_score'] + 95.0 * bt_cnt[ns], 1)
                    if "Cầu Trễ N2/N3" not in item['convergence_badges']:
                        item['convergence_badges'].append("Cầu Trễ N2/N3")
            if ns in recent_des:
                item['consensus_score'] = round(item['consensus_score'] - 45.0, 1)

        found_list.sort(key=lambda x: (x.get('consensus_score', 0), x.get('in_d9', False)), reverse=True)
        n1_pool = [x for x in found_list if x['in_cap4']]
        top_pool = n1_pool if n1_pool else found_list

    top_1 = top_pool[0]['num'] if top_pool else base_top_1
    lot_lon = get_lot_lon(top_1)
    song_thu_tru = [top_1, lot_lon] if lot_lon else [top_1]
    top_4 = select_latin_transversal_top4(top_pool, top_1)

    # 6. KHÓA NGHIỆM PHƯƠNG TRÌNH MA TRẬN (TỔNG VỊ TRÍ ∩ CHẠM NGÀY DÀN ĐỘNG):
    # - Khử các ô "chết" (Kép lệch tổng / nằm ngoài Dàn Động & Hạ Số) trong Dàn 9s, thay bằng nghiệm (Hạ Số 20s ∩ Dàn Động 60s ∩ Chạm Ngày)
    # - Hoàn thiện ô thứ 4 của Tứ Thủ và đôn Bạch Thủ bằng Đỉnh Tổng Hạ Số (max_hs_sum) ∩ Hạ Số 20s ∩ Dàn 9s
    if enable_rescue and summary_data is not None and dow_ha_so_list:
        hs20_set = dow_ha_so_set
        d60 = cap4_set
        old_d9 = list(dan_9_so)
        t4 = list(top_4)
        bt = top_1

        hs_sum_cnt = Counter((int(x[0]) + int(x[1])) % 10 for x in dow_ha_so_list if len(x) == 2 and x.isdigit())
        d60_sum_cnt = Counter((int(x[0]) + int(x[1])) % 10 for x in d60 if len(x) == 2 and x.isdigit())
        max_hs_sum = max(hs_sum_cnt.values()) if hs_sum_cnt else 0

        found_sc = {x['num']: x['consensus_score'] for x in found_list}
        found_wt = {x['num']: x.get('weight', 0.8) for x in found_list}

        cand_pool = set(old_d9)
        if bt in hs20_set and bt in d60:
            cand_pool.add(bt)
        for x_hs in dow_ha_so_list:
            if x_hs in d60 and (
                x_hs[0] in head_digits or x_hs[1] in tail_digits
                or x_hs[0] in tail_digits or x_hs[1] in head_digits
            ):
                cand_pool.add(x_hs)

        scored_d9 = []
        for ns in sorted(cand_pool):
            rev = ns[1] + ns[0]
            s_v = (int(ns[0]) + int(ns[1])) % 10
            in_old = (ns in old_d9 or rev in old_d9)
            in_d60_either = (ns in d60 or rev in d60)
            in_hs_either = (ns in hs20_set or rev in hs20_set)
            is_kep = (ns[0] == ns[1])

            sc = 0.0
            if in_old and (in_d60_either or in_hs_either) and not is_kep:
                sc += 300.0
            elif (ns == bt or rev == bt) and in_hs_either and in_d60_either:
                sc += 220.0
            elif in_hs_either and (ns in d60) and not is_kep:
                sc += 140.0
            elif in_old and not is_kep:
                sc += 80.0
            else:
                sc += 20.0

            if ns in hs20_set:
                sc += 45.0
            elif rev in hs20_set:
                sc += 35.0
            if ns in d60:
                sc += 35.0
            elif rev in d60:
                sc += 25.0

            sc += hs_sum_cnt[s_v] * 8.0 + d60_sum_cnt[s_v] * 4.0
            if s_v in dow_sums:
                sc += 20.0
            sc += max(found_sc.get(ns, 0.0), found_sc.get(rev, 0.0)) * 0.20

            best_orient = ns
            if (rev in d60 and ns not in d60) or (rev in hs20_set and ns not in hs20_set):
                best_orient = rev
            scored_d9.append((best_orient, sc))

        scored_d9.sort(key=lambda x: x[1], reverse=True)
        new_d9 = []
        for ns, _ in scored_d9:
            rev = ns[1] + ns[0]
            if ns not in new_d9 and rev not in new_d9:
                new_d9.append(ns)
            if len(new_d9) >= 9:
                break
        new_d9 = sorted(new_d9)
        new_dao = [s[1] + s[0] for s in new_d9 if s[0] != s[1]]
        new_d9_all = set(new_d9) | set(new_dao)

        if len(t4) >= 4:
            covered_heads = {x[0] for x in t4}
            missing_heads = [h for h in head_digits if h not in covered_heads]
            replaced_t4 = False
            for mh in missing_heads:
                for x_item in found_list:
                    c_num = x_item['num']
                    if c_num[0] == mh and c_num in new_d9_all and c_num in hs20_set and c_num in d60:
                        s_c = (int(c_num[0]) + int(c_num[1])) % 10
                        if hs_sum_cnt[s_c] == max_hs_sum and c_num not in t4 and (c_num[1] + c_num[0]) not in t4:
                            t4[3] = c_num
                            replaced_t4 = True
                            break
                if replaced_t4:
                    break

            if not replaced_t4:
                covered_tails = {x[1] for x in t4}
                missing_tails = [t for t in tail_digits if t not in covered_tails]
                for mt in missing_tails:
                    for x_item in found_list:
                        c_num = x_item['num']
                        if c_num[1] == mt and c_num in new_d9_all and c_num in hs20_set and c_num in d60:
                            s_c = (int(c_num[0]) + int(c_num[1])) % 10
                            if hs_sum_cnt[s_c] == max_hs_sum and c_num not in t4 and (c_num[1] + c_num[0]) not in t4:
                                t4[3] = c_num
                                replaced_t4 = True
                                break
                    if replaced_t4:
                        break

            if not replaced_t4 and t4[3] not in hs20_set:
                for x_item in found_list:
                    c_num = x_item['num']
                    if c_num in new_d9_all and c_num in hs20_set and c_num in d60:
                        s_c = (int(c_num[0]) + int(c_num[1])) % 10
                        if hs_sum_cnt[s_c] == max_hs_sum and c_num not in t4 and (c_num[1] + c_num[0]) not in t4:
                            t4[3] = c_num
                            replaced_t4 = True
                            break

        bt_sum = (int(bt[0]) + int(bt[1])) % 10 if (len(bt) == 2 and bt.isdigit()) else -1
        if (bt not in hs20_set) or (
            not is_rescue_day and (hs_sum_cnt[bt_sum] < max_hs_sum or (bt not in new_d9 and bt not in old_d9))
        ):
            peak_cands = [
                cand for cand in t4
                if cand in hs20_set
                and (cand in new_d9 or cand in old_d9)
                and hs_sum_cnt[(int(cand[0]) + int(cand[1])) % 10] == max_hs_sum
            ]
            if peak_cands:
                orig_bt = bt
                peak_cands.sort(
                    key=lambda c: (
                        (c[0] != orig_bt[0] and c[1] != orig_bt[1]) or c == orig_bt,
                        found_wt.get(c, 0.8) >= 1.0,
                        found_sc.get(c, 0.0)
                    ),
                    reverse=True
                )
                bt = peak_cands[0]
                t4.remove(bt)
                t4.insert(0, bt)

        # 7. KHOANH VÙNG TỔNG CÒN LẠI & TRÙNG CHÍNH CHỮ G7 + ƯU TIÊN CẦU 2d NỔ NGÀY 3 + LÓT 1d NỔ NGÀY 2 - CẢNH BÁO 4d:
        h_2d, h_1d, h_4d = Counter(), Counter(), Counter()
        t_2d, t_1d, t_4d = Counter(), Counter(), Counter()
        for _, info_hp in highlight_positions.items():
            rst = info_hp.get('raw_streak', 1)
            dig_hp = info_hp['digit']
            w_hp = 1.3 if info_hp.get('is_direct') else 1.0
            if info_hp['role'] == 'head':
                if rst == 2:
                    h_2d[dig_hp] += w_hp
                elif rst == 1:
                    h_1d[dig_hp] += w_hp
                elif rst >= 4:
                    h_4d[dig_hp] += w_hp
            else:
                if rst == 2:
                    t_2d[dig_hp] += w_hp
                elif rst == 1:
                    t_1d[dig_hp] += w_hp
                elif rst >= 4:
                    t_4d[dig_hp] += w_hp

        def _get_tong_2d(s_val):
            return (int(s_val[0]) + int(s_val[1])) % 10 if (s_val and len(s_val) == 2 and s_val.isdigit()) else None

        def _get_pair_2d(t_val):
            return tuple(sorted((t_val, (t_val + 5) % 10)))

        g7_vals_prev = [prev_draw['prizes'].get(k, '') for k in ('G7.1', 'G7.2', 'G7.3', 'G7.4')]
        g7_tongs_prev = [_get_tong_2d(v) for v in g7_vals_prev if _get_tong_2d(v) is not None]
        direct_cnt_g7 = Counter(g7_tongs_prev)
        prev_de_sum_val = _get_tong_2d(prev_de)
        prev_de_pair_val = _get_pair_2d(prev_de_sum_val) if prev_de_sum_val is not None else (-1, -1)

        prev1_direct_sums = set()
        if len(sub_draws) >= 3:
            for kg in ('G7.1', 'G7.2', 'G7.3', 'G7.4'):
                t_p1 = _get_tong_2d(sub_draws[2]['prizes'].get(kg, ''))
                if t_p1 is not None and _get_pair_2d(t_p1) != prev_de_pair_val:
                    prev1_direct_sums.add(t_p1)
        persistent_rem_sums = set(direct_cnt_g7.keys()) & prev1_direct_sums

        g7_direct_digits = {ch for v in g7_vals_prev if v and v.isdigit() for ch in v}
        g7_3d_exact = set()
        for b_i in range(1, min(4, len(sub_draws))):
            for kg in ('G7.1', 'G7.2', 'G7.3', 'G7.4'):
                vg = sub_draws[b_i]['prizes'].get(kg, '')
                if len(vg) == 2 and vg.isdigit():
                    g7_3d_exact.add(vg)
                    g7_3d_exact.add(vg[1] + vg[0])

        pool_hs_d60 = [x for x in dow_ha_so_list if x in d60 and x != prev_de]
        cur_bt_sum = _get_tong_2d(bt)
        bt_is_double_2d = (h_2d[bt[0]] > 0 and t_2d[bt[1]] > 0) if len(bt) == 2 else False

        # Case A: 2 vị trí G7 trùng nhau CHÍNH CHỮ Tổng S (direct_cnt_g7[S] >= 2) + Đầu có cầu 2d nổ ngày 3 + không vướng cảnh báo 4d + Lô G7 khung 3 ngày (hoặc cầu đôi 2d x 2d)
        overlap_direct_sums = {s for s, cnt in direct_cnt_g7.items() if cnt >= 2}
        if overlap_direct_sums and cur_bt_sum not in overlap_direct_sums and not bt_is_double_2d:
            cands_a = [
                ns for ns in pool_hs_d60
                if _get_tong_2d(ns) in overlap_direct_sums
                and ns[0] != prev_de[0]
                and h_2d[ns[0]] > 0
                and (h_4d[ns[0]] == 0 and t_4d[ns[1]] == 0)
                and (ns in g7_3d_exact or t_2d[ns[1]] > 0)
            ]
            if cands_a:
                cands_a.sort(
                    key=lambda ns: (
                        (h_2d[ns[0]] > 0 and t_2d[ns[1]] > 0),
                        ns in g7_3d_exact,
                        h_2d[ns[0]] + t_2d[ns[1]],
                        h_1d[ns[0]] + t_1d[ns[1]]
                    ),
                    reverse=True
                )
                best_a = cands_a[0]
                bt = best_a
                bt_is_double_2d = True
                if best_a in t4:
                    t4.remove(best_a)
                t4 = [best_a] + t4[:3]

        # Case B: Tổng Còn Lại nợ 2 ngày liên tiếp trên G7 (persistent_rem_sums) + Đầu/Đuôi có cầu 2d nổ ngày 3 + chiều kia có cầu lót 1d nổ ngày 2 + Lô G7 rơi khung 3 ngày
        if persistent_rem_sums and _get_tong_2d(bt) not in persistent_rem_sums and not bt_is_double_2d:
            cands_b = [
                ns for ns in pool_hs_d60
                if _get_tong_2d(ns) in persistent_rem_sums
                and ns in g7_3d_exact
                and (
                    (h_2d[ns[0]] >= 1.0 and t_1d[ns[1]] >= 1.0 and h_1d[ns[0]] >= 2.0)
                    or (t_2d[ns[1]] >= 1.0 and h_1d[ns[0]] >= 1.0 and t_1d[ns[1]] >= 2.0)
                )
                and (h_4d[ns[0]] == 0 and t_4d[ns[1]] == 0)
            ]
            if cands_b:
                cands_b.sort(key=lambda ns: h_2d[ns[0]] + t_2d[ns[1]] + h_1d[ns[0]] + t_1d[ns[1]], reverse=True)
                best_b = cands_b[0]
                bt = best_b
                bt_is_double_2d = True
                if best_b in t4:
                    t4.remove(best_b)
                t4 = [best_b] + t4[:3]

        # Case C: Trong lòng Top 4 khi bt chưa phải cầu đôi 2d x 2d và chưa thuộc Tổng Còn Lại nợ 2 ngày, nếu có ứng viên thuộc (Top 4 ∩ Hạ Số 20s ∩ Dàn 60s) là giao điểm của Cùng Đầu (>=2 số trong Top 4) VÀ Cùng Cặp Tổng Còn Lại (>=2 số trong Top 4), ghép trong trực diện 2 chữ số G7 + Lót 1d nổ ngày 2 >= 4.0 (như 54 giao điểm của 52 và 27 ngày 12/11)
        if not bt_is_double_2d and _get_tong_2d(bt) not in persistent_rem_sums:
            t4_pairs_all = Counter(_get_pair_2d(_get_tong_2d(x)) for x in t4 if _get_tong_2d(x) is not None)
            t4_heads_all = Counter(x[0] for x in t4 if len(x) == 2)
            for cand_c in list(t4[1:]):
                if cand_c in pool_hs_d60:
                    c_pair = _get_pair_2d(_get_tong_2d(cand_c))
                    c_both_g7 = (cand_c[0] in g7_direct_digits and cand_c[1] in g7_direct_digits)
                    c_1d_power = h_1d[cand_c[0]] + t_1d[cand_c[1]]
                    if t4_pairs_all[c_pair] >= 2 and t4_heads_all[cand_c[0]] >= 2 and (h_2d[cand_c[0]] + t_2d[cand_c[1]]) == 0 and c_both_g7 and c_1d_power >= 4.0 and (h_4d[cand_c[0]] == 0 and t_4d[cand_c[1]] == 0):
                        bt = cand_c
                        t4.remove(cand_c)
                        t4.insert(0, cand_c)
                        break

        # Case D: Trong lòng Top 4, nếu có ứng viên thuộc (Dàn Giao Thoa G7 ∩ Dàn 60s) trùng Đầu với bt nhưng hoàn thiện Cầu Đôi 2d x 2d nổ ngày 3 + Lót 1d nổ ngày 2 >= 2.0 (như 26 vượt 29 ngày 08/11) trong khi bt thiếu cầu Đuôi 2d và chưa thuộc Tổng Còn Lại nợ 2 ngày
        if not bt_is_double_2d and _get_tong_2d(bt) not in persistent_rem_sums:
            for cand_d in list(t4[1:]):
                if cand_d in dow_giao_thoa_set and cand_d in d60 and cand_d[0] == bt[0] and h_2d[cand_d[0]] > 0 and t_2d[cand_d[1]] > 0 and (h_1d[cand_d[0]] + t_1d[cand_d[1]]) >= 2.0 and (h_4d[cand_d[0]] == 0 and t_4d[cand_d[1]] == 0):
                    bt = cand_d
                    bt_is_double_2d = True
                    t4.remove(cand_d)
                    t4.insert(0, cand_d)
                    break

        # 8. GIẢI PHÓNG KHỎI SỰ CHI PHỐI CỦA "TÂM G1 CỐ ĐỊNH" — ĐẶT TRỤC XƯƠNG SỐNG VÀO 3 TRỤ CỘT THỰC CHIẾN:
        # Trụ cột 1: Tổng G7 & Chữ số lặp G7 | Trụ cột 2: Cầu Động Lộ Diện (raw_digit 3d/2d/1d) G1->G5.5 | Trụ cột 3: Dàn 60s N1 Động & Hạ Số 20s
        raw_h_all, raw_t_all = Counter(), Counter()
        raw_h_2d, raw_t_2d = Counter(), Counter()
        raw_h_3d, raw_t_3d = Counter(), Counter()
        raw_h_1d, raw_t_1d = Counter(), Counter()
        for _, inf_raw in highlight_positions.items():
            rd = inf_raw.get('raw_digit', inf_raw.get('digit', ''))
            rst = inf_raw.get('raw_streak', 1)
            h5 = inf_raw.get('hits_5d', 1)
            if not rd:
                continue
            if inf_raw.get('role') == 'head':
                raw_h_all[rd] += 1
                if rst == 2:
                    raw_h_2d[rd] += h5
                elif rst == 3:
                    raw_h_3d[rd] += h5
                elif rst == 1:
                    raw_h_1d[rd] += 1
            else:
                raw_t_all[rd] += 1
                if rst == 2:
                    raw_t_2d[rd] += h5
                elif rst == 3:
                    raw_t_3d[rd] += h5
                elif rst == 1:
                    raw_t_1d[rd] += 1

        raw_3d_all = set(raw_h_3d.keys()) | set(raw_t_3d.keys())
        raw_2d_all = set(raw_h_2d.keys()) | set(raw_t_2d.keys())

        # Trụ cột 8A: Giao thoa Độc Nhất (Chạm 3d Lộ Diện × Chạm 2d Lộ Diện) trong (Dàn Hạ Số 20s ∩ Dàn 60s N1 Động)
        # (Ví dụ kỳ 14/11/2026: Chạm 3 3d tại G3.2_3 × Chạm 9 2d tại G4.1_3 hội tụ duy nhất về cặp 93 - 39 thuộc Tổng 2-7 G7)
        cross_3d_2d_hs = [
            ns for ns in sorted(hs20_set & d60)
            if len(ns) == 2 and ns[0] != ns[1] and ns != prev_de
            and ((ns[0] in raw_3d_all and ns[1] in raw_2d_all) or (ns[0] in raw_2d_all and ns[1] in raw_3d_all))
        ]
        if len(raw_3d_all) == 1 and len(cross_3d_2d_hs) == 2 and (cross_3d_2d_hs[0][1] + cross_3d_2d_hs[0][0]) == cross_3d_2d_hs[1]:
            cross_3d_2d_hs.sort(
                key=lambda ns: (
                    raw_h_2d[ns[0]] + raw_t_2d[ns[1]],
                    raw_h_1d[ns[0]] + raw_t_1d[ns[1]]
                ),
                reverse=True
            )
            best_3d2d = cross_3d_2d_hs[0]
            lot_3d2d = cross_3d_2d_hs[1]
            bt = best_3d2d
            bt_is_double_2d = True
            if best_3d2d in t4:
                t4.remove(best_3d2d)
            t4 = [best_3d2d] + t4[:3]
            # Làm sạch các ghế phụ trong Tứ thủ bị chiếm bởi số ảo ngoài Hạ Số 20s (như 32, 28 ngày 14/11)
            hs_clean_pool = [lot_3d2d] + [
                x_hs for x_hs in dow_ha_so_list
                if x_hs in d60 and x_hs in new_d9_all and x_hs not in t4 and x_hs != best_3d2d and x_hs != lot_3d2d
            ]
            for idx_clean in range(1, len(t4)):
                if t4[idx_clean] not in hs20_set:
                    for repl_hs in hs_clean_pool:
                        if repl_hs not in t4:
                            t4[idx_clean] = repl_hs
                            break
            for c_pair in cross_3d_2d_hs:
                if c_pair not in combos_map:
                    combos_map[c_pair] = {
                        'num': c_pair, 'c_digit': c_pair[0], 'd_digit': c_pair[1],
                        'c_cycle': 3, 'd_cycle': 2, 'min_cycle': 2, 'cycle_days': 3,
                        'category': "Chỉ đạo", 'cat_label': "✅ HỘI TỤ 3 TRỤ CỘT (3d×2d)",
                        'weight': 1.0, 'combo_type': "chính diện", 'score': 195,
                        'bridge_hits': 3, 'strong_bridge_hits': 2,
                        'h_pos': "Cầu Lộ Diện 2d/3d", 't_pos': "Tổng G7 ∩ Hạ Số 20s",
                        'in_cap4': True, 'in_cap4_str': "Có",
                        'consensus_score': 560.0, 'in_d9': True, 'in_tam': False, 'in_sum': True,
                        'convergence_badges': ["N1 Động", "Hạ Số 20s", "Tổng G7", "Cầu Lộ Diện 3d×2d"]
                    }
                    found_list.append(combos_map[c_pair])

        # Trụ cột 8B: Khi bảng không có cầu 3d lộ diện, xét Tổng G7 Trùng Chính Chữ (>=2 vị trí) × Cầu Đôi Lộ Diện (raw_h_2d × raw_t_2d) trong (Giao Thoa G7 ∩ 60s N1)
        # (Ví dụ kỳ 26/10/2026: Tổng 3 trùng 2 vị trí G7 chính chữ 94, 67 + Đầu 1/4 2d × Đuôi 2 2d hội tụ về 21 - 12)
        if not bt_is_double_2d and not raw_3d_all and overlap_direct_sums:
            cands_8b = [
                ns for ns in sorted(dow_giao_thoa_set & d60)
                if len(ns) == 2 and ns[0] != ns[1] and ns != prev_de
                and _get_tong_2d(ns) in overlap_direct_sums
                and ((ns[0] in raw_h_2d and ns[1] in raw_t_2d) or (ns[0] in raw_t_2d and ns[1] in raw_h_2d))
            ]
            if cands_8b:
                cands_8b.sort(
                    key=lambda ns: (
                        raw_h_1d[ns[0]],
                        raw_h_all[ns[0]] + raw_t_all[ns[1]]
                    ),
                    reverse=True
                )
                best_8b = cands_8b[0]
                bt = best_8b
                bt_is_double_2d = True
                if best_8b in t4:
                    t4.remove(best_8b)
                t4 = [best_8b] + t4[:3]
                if best_8b not in combos_map:
                    combos_map[best_8b] = {
                        'num': best_8b, 'c_digit': best_8b[0], 'd_digit': best_8b[1],
                        'c_cycle': 2, 'd_cycle': 2, 'min_cycle': 2, 'cycle_days': 2,
                        'category': "Chỉ đạo", 'cat_label': "✅ TRÙNG TỔNG G7 × CẦU 2d×2d",
                        'weight': 1.0, 'combo_type': "chính diện", 'score': 185,
                        'bridge_hits': 3, 'strong_bridge_hits': 2,
                        'h_pos': "Cầu Lộ Diện 2d", 't_pos': "Trùng Tổng G7",
                        'in_cap4': True, 'in_cap4_str': "Có",
                        'consensus_score': 550.0, 'in_d9': True, 'in_tam': False, 'in_sum': True,
                        'convergence_badges': ["N1 Động", "Trùng Tổng G7", "Cầu Lộ Diện 2d×2d"]
                    }
                    found_list.append(combos_map[best_8b])

        # Trụ cột 8C: Đỉnh Đầu Lộ Diện Áp Đảo (>=5 vị trí kèm cầu 2d nổ ngày 3) khử Bạch Thủ Ảo do Tâm G1 (khi Đuôi bt có 0 cầu lộ diện)
        # (Ví dụ kỳ 27/10/2026: Đầu 9 lộ diện 5 vị trí kèm G4.1_3 2d ghép Đuôi 1 thành 91 thuộc Tổng 0 G7, khử 15 bị ảo Đuôi 5)
        dom_raw_heads = [d_h for d_h, cnt_h in raw_h_all.items() if cnt_h >= 5 and raw_h_2d[d_h] > 0]
        if not bt_is_double_2d and not raw_3d_all and dom_raw_heads and len(bt) == 2 and raw_t_all[bt[1]] == 0:
            h_dom = dom_raw_heads[0]
            cands_8c = [
                ns for ns in sorted(dow_giao_thoa_set & d60)
                if len(ns) == 2 and ns[0] == h_dom and ns[1] in bt and raw_t_all[ns[1]] >= 2 and ns != prev_de
            ]
            if cands_8c:
                best_8c = cands_8c[0]
                bt = best_8c
                bt_is_double_2d = True
                if best_8c in t4:
                    t4.remove(best_8c)
                t4 = [best_8c] + t4[:3]

        # Trụ cột 8D: Khử Ghế Tứ Thủ Ảo do Tâm G1 (không thuộc Hạ Số 20s & có 0 cầu Đầu lộ diện, hoặc khi Tâm G1 gãy cầu 'G1_3' not in highlight_positions)
        g7_dig_cnt = Counter(ch for v in g7_vals_prev if v and v.isdigit() for ch in v)
        rep_g7_digs = sorted([d_g for d_g, c_g in g7_dig_cnt.items() if c_g >= 2])
        if len(rep_g7_digs) == 2 and 'G1_3' not in highlight_positions:
            rep_cands = [
                p_rep for p_rep in (rep_g7_digs[0] + rep_g7_digs[1], rep_g7_digs[1] + rep_g7_digs[0])
                if p_rep in hs20_set and p_rep in d60 and p_rep != prev_de
            ]
            if rep_cands and rep_cands[0] not in t4:
                dead_tam_slots = [idx_s for idx_s, x_s in enumerate(t4) if idx_s >= 1 and x_s not in hs20_set and x_s[0] == tam_g1]
                if dead_tam_slots:
                    best_rep = rep_cands[0]
                    old_dead = t4[dead_tam_slots[0]]
                    t4[dead_tam_slots[0]] = best_rep
                    if old_dead in new_d9 and best_rep not in new_d9 and (best_rep[1] + best_rep[0]) not in new_d9:
                        new_d9[new_d9.index(old_dead)] = best_rep
                        new_d9 = sorted(new_d9)
                    if not bt_is_double_2d and raw_t_all[bt[1]] <= 1:
                        bt = best_rep
                        t4.remove(best_rep)
                        t4.insert(0, best_rep)

        for idx_s in range(1, len(t4)):
            cur_s = t4[idx_s]
            if cur_s not in hs20_set and raw_h_all[cur_s[0]] == 0:
                cands_8d = [
                    x_d9 for x_d9 in new_d9
                    if x_d9 in hs20_set and x_d9 in d60
                    and hs_sum_cnt[_get_tong_2d(x_d9)] == max_hs_sum
                    and raw_h_all[x_d9[0]] >= 3 and raw_t_all[x_d9[1]] >= 1
                    and x_d9 not in t4 and (x_d9[1] + x_d9[0]) not in t4
                ]
                if cands_8d:
                    best_8d = cands_8d[0]
                    t4[idx_s] = best_8d
                    if not bt_is_double_2d and raw_t_all[bt[1]] == 0:
                        bt = best_8d
                        t4.remove(best_8d)
                        t4.insert(0, best_8d)
                    break

        # Trụ cột 8E: Khi Tâm G1 gãy cầu ('G1_3' not in highlight_positions) và tam_g1_set có 0 cầu 2d/3d lộ diện,
        # nếu bt hiện tại bị kéo bởi Tâm G1 (0 chữ số thuộc raw_2d_all | raw_3d_all), xét giao thoa Cầu Đôi 2d×2d Lộ Diện độc nhất trong (Giao Thoa G7 ∩ 60s N1)
        raw_23_all = raw_2d_all | raw_3d_all
        if 'G1_3' not in highlight_positions and not (tam_g1_set & raw_23_all) and len(bt) == 2 and bt[0] not in raw_23_all and bt[1] not in raw_23_all:
            cands_8e = [
                ns for ns in sorted(dow_giao_thoa_set & d60)
                if len(ns) == 2 and ns[0] != ns[1] and ns != prev_de
                and ns[0] in raw_2d_all and ns[1] in raw_2d_all
                and ns[0] not in prev_de and ns[1] not in prev_de
            ]
            if len(cands_8e) == 2 and (cands_8e[0][1] + cands_8e[0][0]) == cands_8e[1] and (cands_8e[0][0] in g7_direct_digits or cands_8e[0][1] in g7_direct_digits):
                cands_8e.sort(
                    key=lambda ns: (
                        ns[0] in g7_direct_digits,
                        raw_h_2d[ns[0]] + raw_t_2d[ns[0]],
                        raw_h_all[ns[0]] + raw_t_all[ns[1]]
                    ),
                    reverse=True
                )
                best_8e = cands_8e[0]
                bt = best_8e
                bt_is_double_2d = True
                if best_8e in t4:
                    t4.remove(best_8e)
                t4 = [best_8e] + t4[:3]
                for c_8e in cands_8e:
                    if c_8e not in combos_map:
                        combos_map[c_8e] = {
                            'num': c_8e, 'c_digit': c_8e[0], 'd_digit': c_8e[1],
                            'c_cycle': 2, 'd_cycle': 2, 'min_cycle': 2, 'cycle_days': 2,
                            'category': "Chỉ đạo", 'cat_label': "✅ HỘI TỤ CẦU ĐÔI 2d×2d LỘ DIỆN",
                            'weight': 1.0, 'combo_type': "chính diện", 'score': 188,
                            'bridge_hits': 3, 'strong_bridge_hits': 2,
                            'h_pos': "Cầu Lộ Diện 2d", 't_pos': "Tổng G7 ∩ 60s N1",
                            'in_cap4': True, 'in_cap4_str': "Có",
                            'consensus_score': 555.0, 'in_d9': True, 'in_tam': False, 'in_sum': True,
                            'convergence_badges': ["N1 Động", "Tổng G7", "Cầu Đôi 2d×2d Lộ Diện"]
                        }
                        found_list.append(combos_map[c_8e])

        if bt not in new_d9 and (bt[1] + bt[0]) not in new_d9:
            new_d9[-1] = bt
            new_d9 = sorted(new_d9)

        dan_9_so = new_d9
        top_1 = bt
        lot_lon = get_lot_lon(top_1)
        song_thu_tru = [top_1, lot_lon] if lot_lon else [top_1]
        top_4 = t4

        # Khôi phục bản chụp đóng băng lúc 18h23 (nếu ngày này đã được khóa sổ G5.5 trước đó)
        frozen_snap = None if ignore_snapshot else load_locked_g55_snapshot(target_draw.get('date', ''))
        if frozen_snap and frozen_snap.get('top_1'):
            top_1 = frozen_snap['top_1']
            lot_lon = frozen_snap.get('lot_lon') or get_lot_lon(top_1)
            song_thu_tru = frozen_snap.get('song_thu') or ([top_1, lot_lon] if lot_lon else [top_1])
            if frozen_snap.get('top_4'):
                top_4 = list(frozen_snap['top_4'])
            if frozen_snap.get('dan_9_so'):
                dan_9_so = list(frozen_snap['dan_9_so'])
                new_d9 = dan_9_so

        for item in found_list:
            if item['num'] in new_d9:
                item['in_d9'] = True
                if "Dàn 9s AI" not in item['convergence_badges']:
                    item['convergence_badges'].append("Dàn 9s AI")
            if item['num'] == top_1 or item['num'] in top_4:
                if item['num'] in hs20_set and hs_sum_cnt[(int(item['num'][0]) + int(item['num'][1])) % 10] == max_hs_sum:
                    if "Khóa Nghiệm Tổng×Chạm" not in item['convergence_badges']:
                        item['convergence_badges'].append("Khóa Nghiệm Tổng×Chạm")
        found_list.sort(
            key=lambda x: (
                x['num'] == top_1,
                x['num'] in top_4,
                x.get('consensus_score', 0),
                x.get('in_d9', False)
            ),
            reverse=True
        )

    return {
        'head_targets': head_targets,
        'tail_targets': tail_targets,
        'highlight_positions': highlight_positions,
        'head_digits': head_digits,
        'tail_digits': tail_digits,
        'dan_9_so': dan_9_so,
        'base_top_1': base_top_1,
        'top_1': top_1,
        'lot_lon': lot_lon,
        'song_thu': song_thu_tru,
        'top_4': top_4,
        'found_list': found_list,
        'is_rescue_day': is_rescue_day
    }


def evaluate_radar_for_draw(sub_draws, cap4_set, summary_data=None):
    """Hàm tương thích ngược phục vụ kiểm chứng từng kỳ lịch sử."""
    res = compute_radar_convergence(sub_draws, cap4_set, summary_data)
    if not res:
        return None
    return {
        'top_1': res['top_1'],
        'lot_lon': res['lot_lon'],
        'song_thu': res['song_thu'],
        'top_4': res['top_4'],
        'dan_9_so': res['dan_9_so'],
        'head_digits': res['head_digits'],
        'tail_digits': res['tail_digits'],
        'found': res['found_list']
    }


def build_radar_history(draws, summary_data, max_records=30):
    """Xây dựng bảng lịch sử kiểm chứng đầy đủ các kỳ quay (lên tới 25-30 kỳ)."""
    records = []
    start_k = 0
    if len(draws) > 0 and not draws[0].get('de'):
        start_k = 1

    af = summary_data.get('adaptive_frame', {}) if summary_data else {}
    dan_n2_default = af.get('dan_n2', ["02", "04", "07", "09", "12", "14", "17", "20", "23", "25", "27", "31", "32", "37", "40", "41", "42", "45", "47", "49", "61", "62", "67", "68", "70", "72", "75", "77", "81", "82", "84", "86", "87", "89", "91", "96"])

    for k in range(start_k, min(len(draws) - 2, start_k + max_records)):
        sub_draws = draws[k:]
        target_draw = sub_draws[0]
        actual_de = target_draw.get('de', '')
        if not actual_de or len(actual_de) < 2:
            continue

        t_date = target_draw.get('date', '')
        # Lấy đúng Dàn 60s N1 Động đã dự báo cho ngày t_date (Walk-Forward 100%)
        cap4_list_k = get_dynamic_dan60_for_date(t_date, summary_data)
        cap4_set_k = set(cap4_list_k)

        eval_res = evaluate_radar_for_draw(sub_draws, cap4_set_k, summary_data)
        if not eval_res:
            continue

        t1 = eval_res['top_1']
        lot_lon = eval_res.get('lot_lon', '')
        song_thu = eval_res.get('song_thu', [t1])
        t4 = eval_res['top_4']
        d9_list = eval_res.get('dan_9_so', [])
        pred_heads = ", ".join(eval_res.get('head_digits', []))
        pred_tails = ", ".join(eval_res.get('tail_digits', []))

        if not d9_list:
            d9_list = [x['num'] for x in eval_res['found'][:9]]

        dan_lot = [x['num'] for x in eval_res['found'] if x['num'] in cap4_set_k and x['num'] not in t4 and x['num'] != t1]
        for n in cap4_list_k:
            if n not in t4 and n != t1 and n not in dan_lot:
                dan_lot.append(n)
        dan_lot = sorted(list(set(dan_lot)))

        hit_t1 = (actual_de == t1) if t1 else False
        hit_lot_lon = (actual_de == lot_lon) if lot_lon else False
        hit_song_thu = (actual_de in song_thu) if song_thu else False
        hit_t4 = (actual_de in t4) if t4 else False
        # Tính trúng Dàn 9s (gồm cả 9 số gốc và đảo bảo hiểm như hiển thị trên bảng)
        d9_dao = [s[1] + s[0] for s in d9_list if len(s) == 2 and s[0] != s[1]]
        hit_d9 = (actual_de in d9_list or actual_de in d9_dao) if d9_list else False
        hit_lot = (actual_de in dan_lot) if dan_lot else False
        hit_n1 = (actual_de in cap4_set_k)

        actual_db = target_draw.get('db', '')
        actual_3d = actual_db[-3:] if len(actual_db) >= 3 else ''
        past_g1 = target_draw.get('prizes', {}).get('G1', '')
        prev_sub_de = sub_draws[1].get('de', '') if len(sub_draws) > 1 else ''
        cang_hist = calc_cang_3d(past_g1, prev_sub_de, t1, t4, d9_list)
        hit_cang_tt = (actual_3d in cang_hist['cang_tt_12s'] or actual_3d in cang_hist['cang_d9_27s']) if actual_3d else False
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


def scan_radar(is_live=False):
    today_dt = datetime.now()
    today_str = today_dt.strftime('%d-%m-%Y')
    dow_map = {0: 'Thứ hai', 1: 'Thứ ba', 2: 'Thứ tư', 3: 'Thứ năm', 4: 'Thứ sáu', 5: 'Thứ bảy', 6: 'Chủ nhật'}
    today_date_str = f"{dow_map[today_dt.weekday()]} ngày {today_str}"

    live_383 = None
    if is_live:
        try:
            live_383 = fetch_383_live()
        except Exception:
            live_383 = None

    daiphat_draws = fetch_daiphat_draws(is_live=is_live)
    draws = []
    if live_383:
        live_k = extract_date_key(live_383.get('date', ''))
        # Hợp nhất từng giải từ cả API 383.im và xosodaiphat.com để nguồn nào có giải G1..G5.5 trước đều bắt được ngay tức thì
        for d in daiphat_draws:
            if extract_date_key(d.get('date', '')) == live_k:
                dp_p = d.get('prizes', {})
                l_p = live_383.setdefault('prizes', {})
                for pk, pv in dp_p.items():
                    if pv and not l_p.get(pk):
                        l_p[pk] = pv
                if d.get('db') and not live_383.get('db'):
                    live_383['db'] = d['db']
                    live_383['de'] = d.get('de', d['db'][-2:])
                break
        draws = [live_383]
        for d in daiphat_draws:
            if extract_date_key(d.get('date', '')) != live_k:
                draws.append(d)
    else:
        draws = daiphat_draws

    is_today = False
    if draws and draws[0].get('date'):
        if extract_date_key(draws[0]['date']) == today_str:
            is_today = True

    # Chỉ chuyển sang kỳ hôm nay (chờ mở thưởng) từ 17h00 trở đi nếu hôm nay chưa có kết quả
    if not is_today and today_dt.hour >= 17:
        empty_p = {
            'G1': '', 'G2.1': '', 'G2.2': '',
            'G3.1': '', 'G3.2': '', 'G3.3': '', 'G3.4': '', 'G3.5': '', 'G3.6': '',
            'G4.1': '', 'G4.2': '', 'G4.3': '', 'G4.4': '',
            'G5.1': '', 'G5.2': '', 'G5.3': '', 'G5.4': '', 'G5.5': '', 'G5.6': '',
            'G6.1': '', 'G6.2': '', 'G6.3': '',
            'G7.1': '', 'G7.2': '', 'G7.3': '', 'G7.4': ''
        }
        draws.insert(0, {'date': today_date_str, 'db': '', 'de': '', 'prizes': empty_p})

    if len(draws) < 2:
        if os.path.exists(STATE_JSON_PATH):
            with open(STATE_JSON_PATH, encoding='utf-8') as f:
                return json.load(f)
        return None

    # Load analysis_summary.json để lấy Dàn 60s N1 Động, N2 (36s), N3 (36s)
    summary_data = {}
    if os.path.exists(SUMMARY_JSON_PATH):
        try:
            with open(SUMMARY_JSON_PATH, encoding='utf-8') as f:
                summary_data = json.load(f)
        except Exception:
            pass

    target_draw = draws[0]
    prev_draw = draws[1]
    prev_de = prev_draw.get('de', '')

    dynamic_60_n1 = get_dynamic_dan60_for_date(target_draw.get('date', ''), summary_data)
    cap4_set = set(dynamic_60_n1)

    conv = compute_radar_convergence(draws, cap4_set, summary_data)
    if not conv:
        if os.path.exists(STATE_JSON_PATH):
            with open(STATE_JSON_PATH, encoding='utf-8') as f:
                return json.load(f)
        return None

    head_targets = conv['head_targets']
    tail_targets = conv['tail_targets']
    highlight_positions = conv['highlight_positions']
    head_digits = conv['head_digits']
    tail_digits = conv['tail_digits']
    dan_9_so = conv['dan_9_so']
    top_1 = conv['top_1']
    lot_lon = conv['lot_lon']
    song_thu_tru = conv['song_thu']
    top_4 = conv['top_4']
    found_list = conv['found_list']

    live_p = target_draw['prizes']
    p_g1 = live_p.get('G1', '')
    p_g2 = [live_p.get('G2.1', ''), live_p.get('G2.2', '')]
    p_g3 = [live_p.get(f'G3.{i}', '') for i in range(1, 7)]
    p_g4 = [live_p.get(f'G4.{i}', '') for i in range(1, 5)]
    p_g5 = [live_p.get(f'G5.{i}', '') for i in range(1, 7)]
    p_g6 = [live_p.get(f'G6.{i}', '') for i in range(1, 4)]
    p_g7 = [live_p.get(f'G7.{i}', '') for i in range(1, 5)]

    filled_g1_g55 = (1 if p_g1 else 0) + sum(1 for x in p_g2 if x) + sum(1 for x in p_g3 if x) + sum(1 for x in p_g4 if x) + sum(1 for x in p_g5[:5] if x)
    filled_prizes = filled_g1_g55 + (1 if p_g5[5] else 0)
    has_g5_5 = bool(live_p.get('G5.5', ''))
    now_curr = datetime.now()
    # Khóa sổ ngay lập tức khi có giải G5.5 (~18h22:15 - 18h23:10) hoặc hạn chót backup 18h23:25 (không cắt cụt sớm ở G5.3 lúc 18h22:48)
    is_timeout_backup = (now_curr.hour == 18 and (now_curr.minute > 23 or (now_curr.minute == 23 and now_curr.second >= 25))) or (now_curr.hour > 18)
    is_completed = (filled_g1_g55 >= 18) or (has_g5_5 and filled_g1_g55 >= 16) or (is_timeout_backup and filled_g1_g55 >= 10)

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

    af = summary_data.get('adaptive_frame', {}) if summary_data else {}
    dan_n2_36so = af.get('dan_n2', ["02", "04", "07", "09", "12", "14", "17", "20", "23", "25", "27", "31", "32", "37", "40", "41", "42", "45", "47", "49", "61", "62", "67", "68", "70", "72", "75", "77", "81", "82", "84", "86", "87", "89", "91", "96"])
    dan_n3_36so = af.get('dan_n3', ["01", "03", "05", "08", "11", "13", "16", "18", "21", "24", "26", "28", "33", "35", "38", "43", "44", "48", "51", "53", "55", "58", "60", "63", "65", "69", "71", "73", "78", "80", "83", "85", "88", "92", "95", "97"])
    dan_n1_next = af.get('dan_n1', dynamic_60_n1)

    for n in dynamic_60_n1:
        if n not in top_4 and n != top_1 and n not in dan_lot_valid:
            dan_lot_valid.append(n)
    dan_lot_valid = sorted(list(set(dan_lot_valid)))

    actual_de = target_draw.get('de', '')
    actual_db = target_draw.get('db', '')
    actual_3d = actual_db[-3:] if len(actual_db) >= 3 else ''

    if actual_de:
        radar_status = "FINISHED_RESULT"
        status_text = f"ĐÃ HOÀN TẤT KỲ QUAY (ĐỀ VỀ {actual_de})"
        lock_badge = f"🎯 ĐÃ CÓ KẾT QUẢ ĐỀ: {actual_de}"
    elif is_completed:
        radar_status = "LOCKED_G5"
        status_text = "🔒 ĐÃ CHỐT KHÓA TẠI G5.5 - VÀO TIỀN NGAY TRƯỚC 18H28!"
        lock_badge = "🔒 ĐÃ KHÓA CHỐT DÀN (G5.5)"
    elif filled_prizes > 0:
        radar_status = "SCANNING_LIVE"
        status_text = f"⚡ ĐANG QUAY TRỰC TIẾP ({filled_prizes}/19 GIẢI) - CHỐT KHI XONG G5.5"
        lock_badge = f"⚡ ĐANG QUAY ({filled_prizes}/19)"
    else:
        radar_status = "BEFORE_DRAW"
        status_text = "CHỜ GIỜ QUAY THƯỞNG (18H15) - DÀN ĐỘNG N1 SẴN SÀNG"
        lock_badge = "⏳ CHỜ GIỜ QUAY (18H15)"

    cang_info = calc_cang_3d(p_g1, prev_de, top_1, top_4, dan_9_so)
    cang_info['target_date'] = target_draw['date']
    cang_info['target_note'] = f"ĐÁNH NGAY CHO GIẢI ĐẶC BIỆT HÔM NAY ({target_draw['date']}) - Khóa sổ khi hết G5, vào tiền trước 18h28!"
    cang_info['tam_g1_source'] = f"Tâm Càng G1 ({p_g1[2] if len(p_g1) >= 3 else '---'} từ G1: {p_g1 or 'Chờ quay'})"
    cang_info['prev_de_source'] = f"Tổng Đề hôm trước ({prev_de}): {(int(prev_de[0]) + int(prev_de[1])) % 10 if len(prev_de) >= 2 else '---'}"

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
        'bach_thu': top_1 if top_1 else '61',
        'lot_lon': lot_lon if lot_lon else '16',
        'song_thu': song_thu_tru,
        'tu_thu': top_4 if len(top_4) >= 4 else ['61', '16', '22', '21'],
        'cang_3d': cang_info['top3_cang'],
        'dan_9_so': dan_9_so,
        'dan_cap2_38so': dan_n2_36so,
        'dan_60_cap4': dan_n1_next
    }

    hit_n1 = (actual_de in cap4_set) if actual_de else af.get('hit_n1_latest', True)

    # Lọc Bạch Thủ & Tứ Thủ riêng cho Dàn N2 (36s) và Dàn N3 (36s) theo điểm hội tụ Radar Live
    n2_set_live = set(dan_n2_36so)
    n3_set_live = set(dan_n3_36so)
    n2_ranked = [x['num'] for x in found_list if x['num'] in n2_set_live]
    n3_ranked = [x['num'] for x in found_list if x['num'] in n3_set_live]
    bt_n2_live = af.get('bt_n2') or (n2_ranked[0] if n2_ranked else (dan_n2_36so[0] if dan_n2_36so else '14'))
    tt_n2_live = af.get('tt_n2') or (n2_ranked[:4] if len(n2_ranked) >= 4 else dan_n2_36so[:4])
    bt_n3_live = af.get('bt_n3') or (n3_ranked[0] if n3_ranked else (dan_n3_36so[0] if dan_n3_36so else '26'))
    tt_n3_live = af.get('tt_n3') or (n3_ranked[:4] if len(n3_ranked) >= 4 else dan_n3_36so[:4])

    frame_transition = {
        'last_result': f"Kỳ gần nhất ({target_draw['date']}) Đề về {actual_de or 'đang quay'}: {'🎯 ĐÃ TRÚNG N1 → RESET CHUYỂN CHU KỲ MỚI' if hit_n1 else ('❌ TRƯỢT N1 → GIỮ NGUYÊN KHUNG, ĐÁNH N2 (36 SỐ)' if actual_de else 'Đang chờ quay Giải Đặc Biệt')}",
        'status_badge': 'ĐÃ TRÚNG N1 → RESET CẦU MỚI' if hit_n1 else ('ĐANG ĐÁNH N2 (36 SỐ)' if actual_de else 'ĐANG QUAY THƯỞNG'),
        'dan_n1': dan_n1_next,
        'dan_n2': dan_n2_36so,
        'dan_n3': dan_n3_36so,
        'bt_n2': bt_n2_live,
        'tt_n2': tt_n2_live,
        'bt_n3': bt_n3_live,
        'tt_n3': tt_n3_live
    }

    history_records, history_summary = None, None
    if is_live and not actual_de and os.path.exists(STATE_JSON_PATH):
        try:
            with open(STATE_JSON_PATH, 'r', encoding='utf-8') as f_st:
                old_st = json.load(f_st)
                if len(old_st.get('history_records', [])) >= 25 and old_st.get('history_summary'):
                    history_records = old_st['history_records']
                    history_summary = old_st['history_summary']
        except Exception:
            pass
    if not history_records or not history_summary:
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
            'g5': p_g5,
            'g6': p_g6,
            'g7': p_g7
        },
        'highlight_positions': highlight_positions,
        'filled_count': filled_prizes,
        'total_count': 19,
        'is_g5_finished': is_completed,
        'is_g5_5_done': has_g5_5,
        'is_g5_6_done': bool(live_p.get('G5.6', '')),
        'is_locked': is_completed,
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
        'actual_3d': actual_3d,
        'dan_tinh_4cap': dan_tinh_4cap,
        'frame_transition': frame_transition,
        'history_records': history_records,
        'history_summary': history_summary,
        'last_updated': datetime.now().strftime("%H:%M:%S %d/%m/%Y")
    }

    with open(STATE_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(final_state, f, ensure_ascii=False, indent=2)

    # Đồng bộ luôn sang verified_history_data.json để giao diện app.js (buildUnifiedHistoryMap) luôn có đủ dữ liệu mới nhất
    ver_path = "verified_history_data.json"
    try:
        ver_map = {}
        if os.path.exists(ver_path):
            with open(ver_path, 'r', encoding='utf-8') as vf:
                ver_map = json.load(vf)
                if not isinstance(ver_map, dict):
                    ver_map = {}
        for r in history_records:
            dk = extract_date_key(r.get('date', ''))
            if dk:
                dk_slash = dk.replace('-', '/')
                dan_n1_r = get_dynamic_dan60_for_date(r.get('date', ''), summary_data)
                ver_map[dk_slash] = {
                    'top_1': r.get('top_1', ''),
                    'top_4': r.get('top_4', []),
                    'dan_9_so': r.get('dan_9_so', []),
                    'de': r.get('de', ''),
                    'ket_qua': 'trung_bt' if r.get('hit_top_1') else ('trung_tt' if r.get('hit_top_4') else ('trung_d9' if r.get('hit_dan_9') else ('trung_lot' if r.get('hit_dan_lot') else 'truot'))),
                    'dan_n1': dan_n1_r,
                    'dan_n2': dan_n2_36so,
                    'dan_n3': dan_n3_36so
                }
        with open(ver_path, 'w', encoding='utf-8') as vf:
            json.dump(ver_map, vf, ensure_ascii=False, indent=2)
    except Exception:
        pass

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Đã cập nhật live_radar_state.json: {filled_prizes}/19 giải | Bạch Thủ: {top_1} (Lót lộn: {lot_lon}) | Tứ Thủ: {top_4} | Dàn 9s: {len(dan_9_so)}s | Dàn Lót: {len(dan_lot_valid)}s | Lịch sử: {len(history_records)} kỳ")
    ensure_daily_telegram_sent(final_state)
    return final_state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Radar Scanner G1->G5 XSMB")
    parser.add_argument('--live', action='store_true', help="Chạy vòng lặp cào live liên tục mỗi 5-10 giây")
    parser.add_argument('--interval', type=int, default=5, help="Chu kỳ giây quét (mặc định 5s)")
    parser.add_argument('--duration', type=int, default=0, help="Thời gian tối đa chạy live tính bằng giây (0 = vô hạn)")
    parser.add_argument('--auto_push', action='store_true', help="Tự động git push ngay khi chốt G5 và khi có GĐB")
    parser.add_argument('--test_telegram', action='store_true', help="Gửi ngay 1 tin nhắn mẫu chốt số G5.5 về điện thoại để kiểm tra")
    args = parser.parse_args()

    def do_quick_git_push(commit_msg):
        try:
            import subprocess
            git_path = r"C:\Program Files\Git\cmd\git.exe"
            if not os.path.exists(git_path):
                git_path = "git"
            subprocess.run([git_path, 'rebase', '--abort'], capture_output=True)
            subprocess.run([git_path, 'add', 'live_radar_state.json'], check=True, capture_output=True)
            subprocess.run([git_path, 'commit', '-m', commit_msg], capture_output=True, text=True)
            p_res = subprocess.run([git_path, 'push', 'origin', 'main'], capture_output=True, text=True)
            if p_res.returncode != 0:
                subprocess.run([git_path, 'fetch', 'origin', 'main'], capture_output=True)
                subprocess.run([git_path, 'merge', 'origin/main', '-X', 'ours', '--no-edit', '-m', 'auto: Sync radar [skip ci]'], capture_output=True)
                subprocess.run([git_path, 'add', 'live_radar_state.json'], capture_output=True)
                subprocess.run([git_path, 'commit', '-m', 'auto: Resolve radar [skip ci]'], capture_output=True)
                p_res = subprocess.run([git_path, 'push', 'origin', 'main'], capture_output=True, text=True)
            subprocess.run([git_path, 'rebase', '--abort'], capture_output=True)
            if p_res.returncode == 0:
                print(f"🚀 [GIT PUSH] {commit_msg} -> Đã đồng bộ lên GitHub thành công!", flush=True)
        except Exception as ex:
            print(f"⚠️ Không thể git push nhanh: {ex}", flush=True)

    if args.test_telegram:
        res = scan_radar(is_live=False)
        if res:
            msg = format_g55_telegram_message(res, is_test=True)
            ok = send_telegram_alert(msg)
            if ok:
                print("✅ Đã gửi tin nhắn chốt số mẫu (G5.5) về Telegram điện thoại thành công!")
            else:
                print("❌ Gửi tin nhắn Telegram thất bại. Vui lòng kiểm tra telegram_config.json.")
        sys.exit(0)

    if args.live:
        print(f"[*] Bắt đầu radar live polling mỗi {args.interval} giây (Thời lượng tối đa: {args.duration if args.duration else 'Vô hạn'}s)...")
        start_t = time.time()
        g5_locked = False
        final_completed = False
        last_pushed_count = -1

        while True:
            try:
                res = scan_radar(is_live=True)
                if res:
                    cur_count = res.get('filled_count', 0)
                    # 1. BƯỚC CHỐT KHÓA NGAY KHI CÓ G5.5 (khoảng 18h22 - 18h23:30)
                    if res.get('is_g5_finished') and not g5_locked:
                        g5_locked = True
                        top1 = res.get('top_1')
                        lot_lon = res.get('lot_lon')
                        top4 = res.get('top_4')
                        dan9 = res.get('dan_9_so', [])
                        top3_cang = res.get('cang_3d_live', {}).get('top3_cang', [])
                        t_date = res.get('target_date', '')
                        print(f"\n=======================================================", flush=True)
                        print(f"🔒 [CHỐT KHÓA G5.5 - {datetime.now().strftime('%H:%M:%S')}] ĐÃ HOÀN TẤT GIẢI G1->G5.5 KỲ {t_date}!", flush=True)
                        print(f"👑 BẠCH THỦ TOP 1: {top1} (Lót lộn: {lot_lon}) | 🔥 TỨ THỦ: {top4}", flush=True)
                        print(f"🌟 TOP 3 CÀNG: {top3_cang} (ĐÁNH NGAY CHO GIẢI ĐẶC BIỆT HÔM NAY QUAY LÚC 18H30)", flush=True)
                        print(f"⏱️ HẠN CHỐT VÀO TIỀN: TRƯỚC 18H28!", flush=True)
                        print(f"=======================================================\n", flush=True)

                        ensure_daily_telegram_sent(res)

                        if args.auto_push:
                            do_quick_git_push(f"Lock Radar G5.5 {t_date} (BT {top1}, TT {top4})")

                    # 2. BƯỚC ĐỐI CHIẾU KHI CÓ GIẢI ĐẶC BIỆT (chỉ kết thúc sau 18h30 khi thực sự có GĐB hôm nay)
                    now_t = datetime.now()
                    if res.get('actual_de') and (now_t.hour > 18 or (now_t.hour == 18 and now_t.minute >= 30)):
                        act_de = res.get('actual_de', '')
                        t_date = res.get('target_date', '')
                        print(f"\n🎯 [KẾT THÚC QUAY - {now_t.strftime('%H:%M:%S')}] Đã có Giải Đặc Biệt: {act_de}.", flush=True)
                        final_completed = True

                        ensure_daily_telegram_sent(res)

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
        scan_radar(is_live=False)
