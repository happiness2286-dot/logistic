---
name: xsmb-lucky26-g7-filter
description: Hệ thống kết hợp phân tích Giải Bảy XSMB (xsmb-g7-prediction) và ma trận Lọc 2D/3D/4D Lucky_26_VIP, hỗ trợ hạ số theo Chạm - Tổng, Nhịp Vàng Gaussian, Tứ Thủ / Song Thủ Đề, Đảo Chiều Đầu Lớn/Nhỏ N1-N2-N3, Dàn Siêu Lọc N2/N3 (28 số), Song Thủ Lô Rơi, mở rộng Top 20 3D/4D và Nhật ký lịch sử kiểm chứng 3D/4D.
---

# XSMB Lucky26 Matrix & Dynamic Frame 3-Day Filter Baseline

Kỹ năng này mở rộng từ `xsmb-g7-prediction`, tích hợp thuật toán **Ma Trận Lọc 2D/3D/4D từ Lucky_26_VIP.xlsx**, mô hình **Nhịp Vàng Gaussian**, phân lớp **Tứ Thủ / Song Thủ Đề**, quy tắc **Đảo Chiều Đầu Lớn/Nhỏ (5-9 vs 0-4)**, **Cặp Song Thủ Lô Rơi**, thuật toán **Dàn Siêu Lọc N2/N3 (28 số - Trúng 44.53% khi N1 trượt)** và hệ thống trích xuất **Top 20 3D Ba Càng & Top 20 4D Bốn Càng Mạnh Nhất**, kèm **Nhật Ký Kiểm Chứng Lịch Sử 234+ Ngày**, tích hợp vào **1 file Excel 18 Sheet Master thống nhất**.

---

## 1. Thuật Toán Lọc Dàn Động Nuôi Khung 3 Ngày

### A. Quy Tắc Đảo Chiều Đầu Lớn (5-9) & Đầu Nhỏ (0-4)
- **N1 (Ngày 1)**: Đánh dàn gốc **60 số** ($S_1$) từ Top G7 / Top Consensus.
- **N2 (Ngày 2 - Khi N1 trượt)**:
  - Nếu Đề N1 về **Đầu Lớn ($\ge 5$)**: Đảo sang ưu tiên **Đầu Nhỏ ($< 5$)** $\rightarrow$ Cắt bớt 15–20 số, thu về dàn ~$40$ số.
  - Nếu Đề N1 về **Đầu Nhỏ ($< 5$)**: Đảo sang ưu tiên **Đầu Lớn ($\ge 5$)** $\rightarrow$ Thu về dàn ~$40$ số.
- **N3 (Ngày 3 - Khi N1 & N2 trượt)**:
  - Đảo chiều tiếp tục theo Đề N2 $\rightarrow$ Thu về dàn ~$35$ số.

### B. Thuật Toán Dàn Siêu Lọc N2 & N3 (28 Số - N1 Hit Matrix)
- Trích xuất **Trọng Số Chạm/Tổng/Vị Trí** từ tất cả các khung N1 trúng trong 234+ ngày qua (`N1 Hit Matrix`).
- Nhận dàn đã qua đảo chiều ($~40$ số), chấm điểm giao thoa với N1 Hit Matrix và nhịp Gaussian để tự động rút gọn dàn N2 & N3 về đúng **28 số**.
- **Hiệu suất kiểm chứng 2026**: Tỷ lệ trúng N2/N3 khi N1 trượt đạt tới **44.53%** với dàn cực mỏng (28 số).

### C. Thuật Toán Song Thủ Lô Rơi (N2/N3)
- Trích xuất 2 con số trùng nhịp lô rơi với 27 giải KQXS hôm trước từ dàn gốc 60 số.
- Theo dõi hiệu suất nổ độc lập qua 3 ngày (tỷ lệ trúng khung **~31.17%**).

---

## 2. Phân Lớp Hỏa Lực & Thuật Toán Ghép 3D / 4D (Top 20)

### 👑 Song Thủ & Tứ Thủ Đề Hỏa Lực
- **Song Thủ Đề (2 số VIP)**: 2 con số có điểm Đồng Thuận ma trận cao nhất.
- **Tứ Thủ Đề (4 số Siêu Cấp)**: 4 con số có điểm Đồng Thuận cao nhất.

### 🔮 Ghép Vị Trí Ba Càng (3D) & Bốn Càng (4D) Top 20
- **Tập Càng Đầu**: Trích xuất các vị trí càng nổ mạnh từ Giải Bảy & Giải Đặc Biệt tuần trước (Càng 3D: `0, 2, 4, 5, 7`; Càng 4D: `0, 2`).
- **Ghép 3D (Ba Càng Top 20)**: $\text{Càng 3D} + \text{Đề 2D Gốc}$.
- **Ghép 4D (Bốn Càng Top 20)**: $\text{Càng 4D} + \text{Ba Càng 3D}$.

---

## 3. Cấu Trúc Báo Cáo Excel Master 18 Sheets

1. `LOC_COPY`: Sheet Bảng Cấu Hình & Kết Quả Lọc Copy 2D.
2. `LIVE_LOC_THEO_THU`: Bộ lọc tự động theo Thứ (Live Formulas dropdown).
3. `Du_Lieu_2026`: Dữ liệu thô XSMB năm 2026 cào từ mketqua.net (234+ bản ghi).
4. `Thong_Ke_G7_MultiWindow`: Thống kê vị trí G7 theo Tuần và khung 30-60-90 ngày.
5. `Top20_Dong_Thuan`: Top 20 dự đoán đồng thuận Super-Score.
6. `Thong_Ke_Theo_Thu`: Phong độ 7 thứ trong tuần & xu hướng G7.
7. `Du_Doan_Tong_Theo_Thu`: Chi tiết dự đoán Chạm - Tổng theo từng Thứ.
8. `Thong_Ke_Phong_Do_G7_Thu`: Phong độ vị trí G7 theo từng Thứ.
9. `Nhat_Ky_Kiem_Chung_Thu`: Nhật ký lịch sử kiểm chứng dự đoán theo Thứ.
10. `Phan_Tich_Cau_Ghep_Goc`: Cầu ghép góc G7.1 & G7.4.
11. `Dan_Ha_So_Nhip_Vang`: Dàn hạ số nhịp vàng Gaussian.
12. `Thong_Ke_Nang_Cao_G7`: Phân tích 4 thuật toán nâng cao G7 & Nhật ký kiểm chứng thực tế.
13. `Lich_Su_Truc_Tiep_2026`: Lịch sử kiểm chứng 1 ngày.
14. `Thong_Ke_Dau_Duoi`: Tần suất Đầu/Đuôi & Top dự đoán ngày tới.
15. `Thong_Ke_Top3_Dau_Duoi`: Thống kê tỷ lệ trúng Top 3 Đầu, Top 3 Đuôi & Dàn 9 Số.
16. **`Lich_Su_Nuoi_Khung_3Ngay`**: Lịch sử kiểm chứng nuôi khung 3 ngày với **Dàn Siêu Lọc N2/N3 (28 số - Trúng 44.53% khi N1 trượt)** & Song Thủ Lô Rơi.
17. `Top_3D_4D_Manh_Nhat`: Danh sách Top 20 Ba Càng (3D) & Top 20 Bốn Càng (4D) Mạnh Nhất.
18. `Lich_Su_3D_4D_2026`: Nhật Ký Kiểm Chứng Lịch Sử Dự Đoán 3D & 4D 2026.

---

## 4. Quy Trình Cập Nhật Hàng Ngày

Chạy lệnh duy nhất để tự động cào dữ liệu mới, chấm điểm Ma trận Lucky26, phân tích Dàn Siêu Lọc N2/N3, kiểm chứng 3D/4D lịch sử, xuất Excel Master 18 Sheet thống nhất và cập nhật Web Dashboard:

```bash
python crawl_and_analyze.py
```

