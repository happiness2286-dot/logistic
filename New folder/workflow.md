# Quy Trình Vận Hành & Hướng Dẫn Cập Nhật Hàng Ngày

Tài liệu chốt lại toàn bộ Skill phân tích XSMB G7, các lệnh vận hành hàng ngày và cấu trúc tệp dữ liệu đã lưu trữ vào bộ nhớ hệ thống.

---

## ⚡ 1. Lệnh Cập Nhật Dữ Liệu Hàng Ngày

Để hệ thống tự động cào kết quả ngày mới nhất từ `mketqua.net`, chạy lại mô hình toán học và xuất lại toàn bộ **Excel 7 Sheet + Web Dashboard**, bạn mở Terminal (PowerShell/CMD) tại thư mục dự án và chạy duy nhất lệnh sau:

```bash
python crawl_and_analyze.py
```

### Kết Quả Tự Động Đầu Ra Sau Khi Chạy Lệnh:
1. 📄 **`data_2026.json`**: Dữ liệu thô XSMB năm 2026 tự động cập nhật đến ngày mới nhất.
2. 📄 **`analysis_summary.json`**: Kết quả phân tích xếp hạng G7, Top 20 Super-Score, Top Đầu/Đuôi, Lịch sử kiểm chứng 1 ngày & Khung 3 ngày (87.50%).
3. 📊 **`Thong_Ke_G7_Va_Top20_XSMB_2026.xlsx`**: **Tệp Excel 7 Sheet Chuyên Nghiệp** (Kẻ ô, màu sắc tiêu đề Navy, tô màu đỏ TRÚNG / xanh TRƯỢT).
4. 🌐 **Web Dashboard Localhost**: Truy cập `http://localhost:8080` để xem giao diện trực quan.

---

## 🧠 2. Kỹ Năng (Skill) Đã Lưu Vào Bộ Nhớ Hệ Thống

Tài liệu Kỹ Năng chi tiết đã được lưu trữ vĩnh viễn tại tệp:
👉 **[SKILL.md](file:///.agents/skills/xsmb-g7-prediction/SKILL.md)** và **[AGENTS.md](file:///.agents/AGENTS.md)**.

### Tóm Tắt Quy Trình Toán Học Trong Skill:
- **Bước 1**: Tính Mod 10 Tổng ($T$) & Bóng ($B$) của 4 vị trí G7 (tạo dàn 20 số/vị trí).
- **Bước 2**: Thống kê phong độ G7 tuần trước ISO, chọn Top 1, Top 2, Top 3 và loại bỏ Top 4.
- **Bước 3**: Chấm điểm Super-Score theo tần suất 30-60-90 ngày, nhịp đẹp (+10đ), và Chạm G7 (+5đ).
- **Bước 4**: Phân tích Đầu (Hàng chục) & Đuôi (Hàng đơn vị) tiềm năng nhất.
- **Bước 5**: Kiểm chứng Lịch sử 218 ngày: Khung 1 ngày (Trúng 44.04%) và Nuôi Khung 3 ngày (Trúng 87.50%).

---

## 📊 3. Danh Sách 7 Sheet Trong File Excel Hoàn Chỉnh

| Sheet | Tên Sheet | Nội Dung Báo Cáo |
| :---: | :--- | :--- |
| 1 | `Du_Lieu_2026` | Dữ liệu gốc 219 ngày 2026 |
| 2 | `Thong_Ke_G7_MultiWindow` | Thống kê G7 Tuần, 30-60-90 Ngày & Chiến thuật Khung 1-3 Ngày |
| 3 | `Top20_Dong_Thuan` | Top 20 dự đoán đồng thuận Super-Score (Kèm Cột Chạm G7) |
| 4 | `Thong_Ke_Theo_Thu` | Phong độ 7 Thứ trong tuần & Dự đoán Bộ Tổng |
| 5 | `Lich_Su_Truc_Tiep_2026` | Nhật ký dự đoán 1 ngày (Trúng 44.04%) tô màu TRÚNG (Đỏ) / TRƯỢT (Xanh) |
| 6 | `Thong_Ke_Dau_Duoi` | Tần suất Đầu/Đuôi & Top 3 Đầu / Top 3 Đuôi ngày tới |
| 7 | **`Lich_Su_Nuoi_Khung_3Ngay`** | **Lịch sử kiểm chứng nuôi khung 3 ngày 216 Khung (Tỷ Lệ Trúng Khung 87.50%)** |