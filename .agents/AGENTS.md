# Rules & Customizations for XSMB AI Project

## Registered Skills
- **[xsmb-g7-prediction](file:///.agents/skills/xsmb-g7-prediction/SKILL.md)**: Hệ thống cào dữ liệu xổ số tự động, chấm điểm Super-Score đồng thuận đa khung thời gian (30-60-90 ngày), phân tích Đầu/Đuôi, thống kê kiểm chứng Top 3 Đầu / Top 3 Đuôi (Sheet `Thong_Ke_Top3_Dau_Duoi`), kiểm chứng nuôi khung 3 ngày (87.50% trúng khung), và xuất Excel chuẩn openpyxl.
- **[xsmb-lucky26-g7-filter](file:///.agents/skills/xsmb-lucky26-g7-filter/SKILL.md)**: Hệ thống kết hợp phân tích Giải Bảy XSMB và ma trận Lọc 2D/3D/4D Lucky_26_VIP, tích hợp Sheet LOC_COPY, mô hình Nhịp Vàng Gaussian, Tứ Thủ/Song Thủ Đề, mở rộng Top 20 3D/4D, Thống kê tỷ lệ trúng Top 3 Đầu & Đuôi và Nhật ký lịch sử kiểm chứng 3D/4D vào 1 file Excel thống nhất.

## Command to Run Daily Update:
```bash
python crawl_and_analyze.py
```
Lệnh trên sẽ tự động:
1. Cào kết quả mới nhất năm 2026 từ `https://mketqua.net/so-ket-qua`.
2. Phân tích xếp hạng G7, ma trận Lucky26, Tứ Thủ/Song Thủ Đề, dự đoán Top 3 Đầu / Top 3 Đuôi & thống kê kiểm chứng tỷ lệ trúng, Top 20 3D/4D & kiểm chứng lịch sử.
3. Xuất file Excel thống nhất: `Thong_Ke_G7_Va_Top20_XSMB_2026.xlsx`.
4. Cập nhật dữ liệu cho Web Dashboard Localhost `http://localhost:8080`.



