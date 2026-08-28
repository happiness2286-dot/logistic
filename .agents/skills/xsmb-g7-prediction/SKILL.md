---
name: xsmb-g7-prediction
description: Quy trình thống kê Giải Bảy XSMB, phân tích đồng thuận 30-60-90 ngày, dự đoán Đầu - Đuôi Đề và xuất file Excel 7 Sheet chuẩn openpyxl.
---

# XSMB G7 Prediction & Multi-Window Consensus Methodology

Kỹ năng tự động cào dữ liệu xổ số miền Bắc từ `mketqua.net`, tính toán tổng số + bóng số của 4 Giải Bảy (G7.1, G7.2, G7.3, G7.4), xếp hạng vị trí G7 hiệu quả nhất tuần trước, đồng thuận đa khung thời gian (30, 60, 90 ngày), phân tích tần suất Đầu/Đuôi, kiểm chứng lịch sử 218 ngày (1 ngày & nuôi khung 3 ngày), và xuất báo cáo Excel 7 Sheet chuyên nghiệp.

## 1. Các Bước Chạy Cập Nhật Dữ Liệu Hàng Ngày

Để cập nhật dữ liệu ngày mới nhất và xuất lại toàn bộ báo cáo Excel 7 Sheet + Web Dashboard, sử dụng lệnh duy nhất:

```bash
python crawl_and_analyze.py
```

### Kết Quả Đầu Ra Tự Động:
1. `data_2026.json`: Dữ liệu thô XSMB năm 2026 cào trực tiếp từ mketqua.net.
2. `analysis_summary.json`: Kết quả phân tích xếp hạng G7, Top 20 đồng thuận Super-Score, Top Đầu/Đuôi, và lịch sử kiểm chứng 218 ngày.
3. `Thong_Ke_G7_Va_Top20_XSMB_2026.xlsx`: Tệp Excel 7 Sheet định dạng `openpyxl` chuyên nghiệp (kẻ ô, màu sắc tiêu đề Navy, tô màu đỏ TRÚNG / xanh TRƯỢT).

---

## 2. Quy Trình Phân Tích Kỹ Thuật

### Bước 1: Tính Tổng & Bóng Số Giải 7
- **Tổng chữ số (Mod 10)**: $T = (a + b) \pmod{10}$ (với $a, b$ là 2 chữ số Giải 7).
- **Bóng Dương (Mod 10)**: $B = (T + 5) \pmod{10}$.
- Mỗi vị trí G7 tạo ra dàn 20 con số (10 số thuộc Tổng $T$ và 10 số thuộc Bóng $B$).

### Bước 2: Xếp Hạng Vị Trí G7 Hiệu Quả Tuần Trước
- Thống kê tỷ lệ trúng Đề của 4 vị trí G7 trong tuần ISO trước đó (v dụ: Tuần 32 dự đoán cho Tuần 33).
- Chọn **Top 1, Top 2, Top 3** có phong độ cao nhất; **Loại bỏ Top 4** có tỷ lệ thấp nhất.

### Bước 3: Thuật Toán Chấm Điểm Super-Score (Đa Nhân Tố)
$$\text{Super\_Score} = (F_{30d} \times 3.0) + (F_{60d} \times 2.0) + (F_{90d} \times 1.0) + \text{Rhythm\_Bonus} + \text{Chạm\_Bonus}$$
- **Rhythm\_Bonus**: +10 điểm cho nhịp đẹp (gan 3-25 ngày).
- **Chạm\_Bonus**: +5 điểm cho con số thuộc tập Chạm G7 (chữ số G7 + bóng chạm).

### Bước 4: Lịch Sử Kiểm Chứng & Nuôi Khung 3 Ngày
- **Khung 1 Ngày (Trúng Ngay)**: Tỷ lệ trúng **44.04%** (96 / 218 ngày).
- **Khung Nuôi 3 Ngày (Max Khung)**: Tỷ lệ trúng **87.50%** (189 / 216 khung).

---

## 3. Cấu Trúc Báo Cáo Excel 11 Sheet Chuyên Nghiệp

1. `LOC_COPY`: Bảng điều khiển & bộ lọc 2D động cho người dùng.
2. `Du_Lieu_2026`: Dữ liệu thô 2026 cào từ mketqua.net.
3. `Thong_Ke_G7_MultiWindow`: Thống kê G7 theo Tuần & mốc 30-60-90 Ngày + Khung 1-3 ngày.
4. `Top20_Dong_Thuan`: Top 20 dự đoán đồng thuận Super-Score (Kèm Cột Chạm G7).
5. `Thong_Ke_Theo_Thu`: Phong độ 7 Thứ trong tuần & Dự đoán Bộ Tổng theo Thứ.
6. `Thong_Ke_Nang_Cao_G7`: Phân tích 4 thuật toán nâng cao G7 & Nhật ký kiểm chứng thực tế.
7. `Lich_Su_Truc_Tiep_2026`: Nhật ký dự đoán 1 ngày (Red TRÚNG / Green TRƯỢT).
8. `Thong_Ke_Dau_Duoi`: Tần suất Đầu/Đuôi & Top 3 Đầu / Top 3 Đuôi ngày tới.
9. **`Thong_Ke_Top3_Dau_Duoi`**: **Bảng Thống Kê Tỷ Lệ Trúng & Nhật Ký Kiểm Chứng Top 3 Đầu (29.02% 1N, 68.92% 3N), Top 3 Đuôi (24.55% 1N, 63.51% 3N) & Dàn 9 Số Ghép (7.14% 1N, 26.58% 3N)**.
10. `Lich_Su_Nuoi_Khung_3Ngay`: Lịch sử kiểm chứng nuôi khung 3 ngày (87.50% trúng khung).
11. `Top_3D_4D_Manh_Nhat`: Bảng Top 20 Ba Càng (3D) & Top 20 Bốn Càng (4D) Mạnh Nhất.
12. `Lich_Su_3D_4D_2026`: Nhật ký kiểm chứng lịch sử 3D & 4D năm 2026.
