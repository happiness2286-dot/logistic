---
name: xsmb-soi-cau-g1-g5
description: Hệ thống tự động soi vị trí G1->G5 XSMB, chu kỳ lặp 2-3-4 ngày, lót ngày 2, ưu tiên ngày 3-4, vị trí ngày 2 nổ trở thành chủ lực ngày 3, ghép dàn Chục x Đơn vị (từ Chạm đầu & Đuôi cùng bóng dương), lọc giao thoa 60 số Cấp 4 và trích xuất Top 1, Top 4 Tinh Túy theo thời gian thực (Real-time).
---

# XSMB G1-G5 Position Bridge, Cycle Tracker & Cap 4 Filter Baseline

Kỹ năng này chuyên trách nghiệp vụ **Soi Vị Trí G1 $\rightarrow$ G5, Chu Kỳ Lặp & Lọc Dàn 60 Số Cấp 4**, được triển khai độc lập theo chuẩn 9 bước nghiêm ngặt:

---

## 1. Bản Đồ 85 Vị Trí Vật Lý Chuẩn (G1 $\rightarrow$ G5)
Hệ thống chỉ quét các giải từ G1 đến G5, loại bỏ hoàn toàn Giải Đặc Biệt, G6 và G7 khi lập bản đồ vị trí:
- **Giải 1**: 1 giải $\times$ 5 số = 5 vị trí (`G1 vị trí 1` .. `G1 vị trí 5`).
- **Giải 2**: 2 giải $\times$ 5 số = 10 vị trí (`G2.1 vị trí 1` .. `G2.2 vị trí 5`).
- **Giải 3**: 6 giải $\times$ 5 số = 30 vị trí (`G3.1 vị trí 1` .. `G3.6 vị trí 5`).
- **Giải 4**: 4 giải $\times$ 4 số = 16 vị trí (`G4.1 vị trí 1` .. `G4.4 vị trí 4`).
- **Giải 5**: 6 giải $\times$ 4 số = 24 vị trí (`G5.1 vị trí 1` .. `G5.6 vị trí 4`).
*(Tổng cộng: 85 vị trí vật lý chuẩn)*.

---

## 2. Quy Trình Cốt Lõi 9 Bước

### Bước 1: Xác định đề ngày hôm trước ($D_{N-1}$)
- Trích xuất 2 số cuối giải Đặc Biệt kỳ trước: Chạm đầu = $H$, Chạm đuôi = $T$.

### Bước 2: Lấy bóng dương chính
- Bảng ánh xạ: $0 \leftrightarrow 5, 1 \leftrightarrow 6, 2 \leftrightarrow 7, 3 \leftrightarrow 8, 4 \leftrightarrow 9$.
- Bóng đầu: $H_{bong} = Bong(H)$.
- Bóng đuôi: $T_{bong} = Bong(T)$.

### Bước 3: Tập hợp số cần soi vị trí
- Tập Hàng Chục: $\{H, H_{bong}\}$.
- Tập Hàng Đơn Vị: $\{T, T_{bong}\}$.

### Bước 4: Tìm tất cả vị trí xuất hiện trong 5 ngày gần nhất
- Quét 85 vị trí vật lý trên 5 kỳ gần nhất từ nguồn `mketqua.net` để ghi nhận tọa độ.

### Bước 5: Áp dụng quy tắc chu kỳ lặp & Phân loại
- **Lặp 2 ngày**: Gán nhãn `Lót ngày 2`.
- **Lặp 3 ngày**: Gán nhãn `Ưu tiên ngày 3`.
- **Lặp 4 ngày**: Gán nhãn `Ưu tiên ngày 4`.
- **Không thuộc khung 2-4 ngày**: Bỏ qua hoàn toàn.
- **Quy tắc đặc biệt**: Nếu vị trí ngày 2 đã nổ đề ở kỳ trước $\rightarrow$ nâng hạng thành **`★ Chủ lực ngày 3 (Nổ ngày 2)`**.

### Bước 6: Soi kết quả kỳ đang quay tại các vị trí đã ghi nhận
- Nhặt chữ số tại các vị trí thuộc nhóm Chạm Đầu $\rightarrow$ Tập ứng viên **Hàng Chục**.
- Nhặt chữ số tại các vị trí thuộc nhóm Đuôi $\rightarrow$ Tập ứng viên **Hàng Đơn Vị**.

### Bước 7: Ghép tổ hợp dàn mới
- Nhân Descartes: Hàng Chục $\times$ Hàng Đơn Vị $\rightarrow$ Dàn ghép 2D (đã loại trùng).

### Bước 8: So với 60 số Cấp 4 (Giao thoa là nguồn nguyên liệu)
- Đọc 60 số Cấp 4 từ file `dan_60_cap_4.csv` (hoặc từ bộ tối ưu Optimizer Dàn 60).
- Dàn 60 Cấp 4 **CHỈ LÀ NGUỒN NGUYÊN LIỆU / MÀNG LỌC ĐIỀU KIỆN CẦN**, không phải tiêu chí xếp hạng.
- Xác định trạng thái `Trong 60 số?`: Có / Không.

### Bước 9: QUY TẮC CHỌN TOP 1 / TOP 4 (ĐÃ SỬA CHUẨN)
- **TUYỆT ĐỐI KHÔNG** lấy con mạnh có điểm cao trong dàn giao thoa ra làm Top 1 / Top 4.
- **CHỈ ĐẠO DUY NHẤT**: CHỈ LẤY con có điểm nổ ngày 3, ngày 4 (vị trí lặp 3-4 ngày) làm CHỈ ĐẠO.
- **Top 1**: Con có vị trí lặp 3 ngày hoặc 4 ngày mạnh nhất (và nằm trong 60 số).
- **Top 4**: 4 con có vị trí lặp 3-4 ngày mạnh nhất (và nằm trong 60 số).
- **Lót ngày 2**: Con có vị trí lặp 2 ngày (Đánh lót; nếu nổ ngày 2 $\rightarrow$ Tổng lực ngày 3).
- **Theo dõi ngày 1**: Con có vị trí lặp 1 ngày.
- **Bảng hiển thị chuẩn 5 cột**: `Con số` | `Vị trí lặp` | `Phân loại` | `Trong 60 số?` | `Top`.

---

## 3. Lệnh Vận Hành & Khai Thác

### Chạy phân tích kỳ mới nhất / chỉ định:
```bash
python soi_cau_g1_g5.py
```

### Chạy chế độ giám sát Real-time trong lúc quay thưởng (18h15 - 18h35):
Tự động quét mỗi 15 giây từ `mketqua.net`, cập nhật ngay khi từng giải trong G1 $\rightarrow$ G5 xuất hiện:
```bash
python soi_cau_g1_g5.py --live
```

### Tùy chỉnh danh sách 60 số Cấp 4:
```bash
python soi_cau_g1_g5.py --csv <duong_dan_file.csv>
```
File CSV có cấu trúc: `STT,So_2D` (hoặc 1 cột chứa 60 số định dạng 2 chữ số `00` - `99`).
Output được tự động xuất ra console và lưu thành file JSON: `ket_qua_soi_cau_g1_g5.json`.
