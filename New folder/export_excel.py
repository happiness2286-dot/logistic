import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Try importing pandas/openpyxl or fallback to csv/openpyxl
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

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

# Load data
with open('data_2026.json', 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

with open('analysis_summary.json', 'r', encoding='utf-8') as f:
    summary = json.load(f)

# Oldest to newest
chrono = list(reversed(raw_data))

# Prepare Sheet 1 Data: Data 2026
sheet1_rows = []
for idx, row in enumerate(chrono):
    date_str = row['date']
    db = row['db']
    de = row['de']
    g7_1 = row['g7_1']
    g7_2 = row['g7_2']
    g7_3 = row['g7_3']
    g7_4 = row['g7_4']
    
    t1, b1 = get_tong(g7_1), get_bong(get_tong(g7_1))
    t2, b2 = get_tong(g7_2), get_bong(get_tong(g7_2))
    t3, b3 = get_tong(g7_3), get_bong(get_tong(g7_3))
    t4, b4 = get_tong(g7_4), get_bong(get_tong(g7_4))
    
    # Hit next day?
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

# Sheet 2: Thong ke G7
sheet2_rows = [
    {
        'Vị Trí G7': 'G7.3',
        'Xếp Hạng': '🥇 Top 1',
        'Trúng Khung 1 Ngày': '44 / 218',
        'Tỷ Lệ Trúng K1 (%)': '20.18%',
        'Trúng Khung 2 Ngày': '83 / 217',
        'Tỷ Lệ Trúng K2 (%)': '38.25%',
        'Trúng Khung 3 Ngày': '111 / 216',
        'Tỷ Lệ Trúng K3 (%)': '51.39%',
        'Trạng Thái Ap Dung': 'ÁP DỤNG (Top 1)'
    },
    {
        'Vị Trí G7': 'G7.2',
        'Xếp Hạng': '🥈 Top 2',
        'Trúng Khung 1 Ngày': '38 / 218',
        'Tỷ Lệ Trúng K1 (%)': '17.43%',
        'Trúng Khung 2 Ngày': '79 / 217',
        'Tỷ Lệ Trúng K2 (%)': '36.41%',
        'Trúng Khung 3 Ngày': '106 / 216',
        'Tỷ Lệ Trúng K3 (%)': '49.07%',
        'Trạng Thái Ap Dung': 'ÁP DỤNG (Top 2)'
    },
    {
        'Vị Trí G7': 'G7.1',
        'Xếp Hạng': '🥉 Top 3',
        'Trúng Khung 1 Ngày': '35 / 218',
        'Tỷ Lệ Trúng K1 (%)': '16.06%',
        'Trúng Khung 2 Ngày': '75 / 217',
        'Tỷ Lệ Trúng K2 (%)': '34.56%',
        'Trúng Khung 3 Ngày': '106 / 216',
        'Tỷ Lệ Trúng K3 (%)': '49.07%',
        'Trạng Thái Ap Dung': 'ÁP DỤNG (Top 3)'
    },
    {
        'Vị Trí G7': 'G7.4',
        'Xếp Hạng': '❌ Top 4',
        'Trúng Khung 1 Ngày': '32 / 218',
        'Tỷ Lệ Trúng K1 (%)': '14.68%',
        'Trúng Khung 2 Ngày': '64 / 217',
        'Tỷ Lệ Trúng K2 (%)': '29.49%',
        'Trúng Khung 3 Ngày': '102 / 216',
        'Tỷ Lệ Trúng K3 (%)': '47.22%',
        'Trạng Thái Ap Dung': 'LOẠI BỎ (Top 4)'
    }
]

# Sheet 3: Top 20 Predictions
sheet3_rows = []
for idx, item in enumerate(summary['top_20'], 1):
    nhip_eval = "Nhịp Đẹp" if 3 <= item['nhip'] <= 25 else ("Vừa Ra" if item['nhip'] < 3 else "Gan Dài")
    sheet3_rows.append({
        'Thứ Hạng': f"Top {idx:02d}",
        'Con Số': item['number'],
        'Thuộc Tổng': item['tong'],
        'Tần Suất 2026 (lần)': item['freq'],
        'Nhịp Gan (ngày)': item['nhip'],
        'Đánh Giá Nhịp': nhip_eval,
        'Điểm Số Tối Ưu': item['score']
    })

excel_filename = 'Thong_Ke_G7_Va_Top20_XSMB_2026.xlsx'

if HAS_PANDAS:
    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        pd.DataFrame(sheet1_rows).to_excel(writer, sheet_name='Du_Lieu_2026', index=False)
        pd.DataFrame(sheet2_rows).to_excel(writer, sheet_name='Thong_Ke_G7', index=False)
        pd.DataFrame(sheet3_rows).to_excel(writer, sheet_name='Top_20_Du_Doan', index=False)
    print(f"Successfully generated Excel file: {excel_filename}")
else:
    print("Pandas not found. Installing openpyxl/pandas or exporting CSV...")
