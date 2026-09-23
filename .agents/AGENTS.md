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
- **Chuẩn hóa 5 Quy Tắc**:
  1. Cầu chạy ngày 3, 4: Vẫn lấy bình thường (ưu tiên Top 1, Top 4).
  2. Cầu đã bỏ (gãy): Không lấy nữa — loại bỏ hoàn toàn (streak liên tục, không cộng dồn đứt quãng).
  3. Cầu mới chạm ngày 1: Theo dõi — nếu nổ ngày 2 -> trở thành tổng lực ngày 3.
  4. Quy trình 5 bước (ví dụ ngày 22/09 từ đề 21/09: 40432 -> Đầu [3, 8], Đuôi [2, 7] -> Soi vị trí -> Ưu tiên đầu đuôi bóng -> Ghép dàn Ngày 1 -> Giao thoa 60 số Cấp 4).
  5. Dàn số lót: Lấy từ 60 số N1.
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

### 4. Ứng Dụng Web UI Radar Soi Cầu G1-G5 (`soi_cau_g1_g5_app.html`):
- File được lưu và đồng bộ tại 2 vị trí:
  - Thư mục gốc: `soi_cau_g1_g5_app.html`
  - Thư mục nhánh: `58_up_to_75/soi_cau_g1_g5_app.html`
- **Link Online GitHub Pages**:
  - Gốc: `https://happiness2286-dot.github.io/logistic/soi_cau_g1_g5_app.html`
  - Nhánh 58: `https://happiness2286-dot.github.io/logistic/58_up_to_75/soi_cau_g1_g5_app.html`
- **Đặc tả UI & Mobile UX**:
  - Tối ưu chuẩn Mobile Responsive (đặc biệt iPhone 11: 414 × 896).
  - Có Action Sheet Bottom Menu sao chép nhanh: Top 1, Top 4, Dàn Tinh Túy, Dàn N1, N2, N3.
  - Phân loại cầu gộp: 🟡 Chỉ đạo (3-4 ngày: đánh chính) | 🔵 Lót (2 ngày) | ⚪ Theo dõi (1 ngày).
  - Thẻ `div` và HTML luôn cân bằng chuẩn, không lặp ID.
  - **Phần 4 Tách Biệt**: PHẦN 4A (Khung 3 ngày 58_up_to_75) và PHẦN 4B (Soi trực tiếp Bạch thủ/Tứ thủ).
  - **Tối Ưu N2/N3 & Chu Kỳ 7 Ngày**: N2 mở rộng (42 số - lọc bệt 2 ngày), N3 cơ hội cuối (40 số - lọc gan >45 ngày), chu kỳ 7 ngày tự động theo tuần.
