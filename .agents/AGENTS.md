# Rules & Customizations for XSMB AI Project

## Registered Skills
- **[xsmb-g7-prediction](file:///.agents/skills/xsmb-g7-prediction/SKILL.md)**: Hệ thống cào dữ liệu xổ số tự động, chấm điểm Super-Score đồng thuận đa khung thời gian (30-60-90 ngày), phân tích Đầu/Đuôi, thống kê kiểm chứng Top 3 Đầu / Top 3 Đuôi (Sheet `Thong_Ke_Top3_Dau_Duoi`), kiểm chứng nuôi khung 3 ngày (87.50% trúng khung), và xuất Excel chuẩn openpyxl.
- **[xsmb-lucky26-g7-filter](file:///.agents/skills/xsmb-lucky26-g7-filter/SKILL.md)**: Hệ thống kết hợp phân tích Giải Bảy XSMB và ma trận Lọc 2D/3D/4D Lucky_26_VIP, tích hợp Sheet LOC_COPY, mô hình Nhịp Vàng Gaussian, Tứ Thủ/Song Thủ Đề, mở rộng Top 20 3D/4D, Thống kê tỷ lệ trúng Top 3 Đầu & Đuôi và Nhật ký lịch sử kiểm chứng 3D/4D vào 1 file Excel thống nhất.
- **[xsmb-soi-cau-g1-g5](file:///.agents/skills/xsmb-soi-cau-g1-g5/SKILL.md)**: Hệ thống tự động soi vị trí G1->G5 XSMB, chu kỳ lặp 2-3-4 ngày, lót ngày 2, ưu tiên ngày 3-4, vị trí ngày 2 nổ trở thành chủ lực ngày 3, ghép dàn Chục x Đơn vị (từ Chạm đầu & Đuôi cùng bóng dương), lọc giao thoa 60 số Cấp 4 và trích xuất Top 1, Top 4 Tinh Túy theo thời gian thực (Real-time).

## Key Project Modules & Workflows

### 1. Cập Nhật Dữ Liệu Hàng Ngày & Báo Cáo Master:
```bash
python crawl_and_analyze.py
```
Lệnh trên sẽ tự động:
1. Cào kết quả mới nhất năm 2026 từ `https://mketqua.net/so-ket-qua`.
2. Phân tích xếp hạng G7, ma trận Lucky26, Tứ Thủ/Song Thủ Đề, dự đoán Top 3 Đầu / Top 3 Đuôi & thống kê kiểm chứng tỷ lệ trúng, Top 20 3D/4D & kiểm chứng lịch sử.
3. Xuất file Excel thống nhất: `Thong_Ke_G7_Va_Top20_XSMB_2026.xlsx`.
4. Cập nhật dữ liệu cho Web Dashboard Localhost `http://localhost:8080`.

### 2. Soi Vị Trí G1->G5 & Lọc 60 Số Cấp 4 (Module Mới):
- **Chạy phân tích kỳ mới nhất**:
  ```bash
  python soi_cau_g1_g5.py
  ```
- **Chạy chế độ Real-time trong lúc quay thưởng (18h15 - 18h35)**:
  ```bash
  python soi_cau_g1_g5.py --live
  ```
- **Tùy chỉnh file CSV 60 số Cấp 4**:
  ```bash
  python soi_cau_g1_g5.py --csv dan_60_cap_4.csv
  ```
- Kết quả được xuất ra console và lưu thành file `ket_qua_soi_cau_g1_g5.json`.

### 3. Nhánh Dự Án Độc Lập `58_up_to_75`:
- Thư mục: `58_up_to_75/`
- Chứa Mini App Tối Ưu Dàn 58 lên 75 số, chuyển cầu N1/N2/N3, kịch bản `update_daily.py`, dashboard `index.html` và file dữ liệu `data.json`.




