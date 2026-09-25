# Rules & Customizations for XSMB AI Project

## 1. QUY TẮC BẮT BUỘC KHI LÀM VIỆC VỚI NGƯỜI DÙNG
- **"Trao đổi trước tiên - Người dùng đồng ý mới tiến hành sửa"**: Mọi ý tưởng, thay đổi thuật toán, sửa code, thêm giao diện đều phải trao đổi giải thích phương án trước. Chỉ khi người dùng nhắn "đồng ý" mới can thiệp vào mã nguồn hoặc file dữ liệu.

---

## 2. KIẾN TRÚC 2 TRƯỜNG PHÁI KẾT HỢP: TĨNH (ĐẦU NGÀY) & ĐỘNG (GIỜ QUAY)

### A. PHẦN 0: DÀN TĨNH 4 CẤP (Đánh trước 18h15)
- **Thời điểm**: Có sẵn từ 18h35 tối hôm trước đến 18h15 chiều hôm sau.
- **Cơ sở dữ liệu**: Dựa trên kết quả kỳ trước (ngày hôm qua) và thống kê lịch sử 2026.
- **4 Cấp Độ Phân Tầng**:
  1. **Cấp 4 (Hỏa lực tối thượng)**: 
     - 👑 **Bạch Thủ Đề**: Tọa độ hội tụ Cầu Ghép Góc $G7.1[0] + G7.4[1]$ (Ví dụ: con 41).
     - 🔥 **Song Thủ Đề**: Cặp đảo chiều (Ví dụ: 41 - 14).
     - ⭐ **Tứ Thủ Đề**: Ghép thêm 2 số cao điểm nhất của Dàn 9 số (Ví dụ: 41 - 14 - 67 - 31).
     - 🔮 **Càng 3D**: `0, 2, 4, 5, 7`.
  2. **Cấp 3 (Dàn 9 số Cội Nguồn)**: Ghép trực tiếp **Top 3 Đầu $\times$ Top 3 Đuôi** phục hồi.
  3. **Cấp 2 (Dàn Giao Thoa 38 số)**: Ép Chạm G7 $\times$ Tổng G7 & Nhịp Vàng Gaussian.
  4. **Cấp 1 (Dàn Gốc 60 số N1)**: Khung N1 chuẩn độ phủ an toàn 87.5%.
- **Giao diện**: Hiển thị ở khối **PHẦN 0** trên Mini App & PC Web (`soi_cau_g1_g5_app.html`), có sẵn các nút 1-Click Copy từng cấp dàn.

### B. PHẦN 2: DÀN TINH TÚY LIVE (Bắt nước rút sau Giải 5.6)
- **Thời điểm**: Tự động kích hoạt ngay sau khi quay xong Giải 5.6 (khoảng 18h22 - 18h24).
- **Cơ sở dữ liệu**: Bắt các vị trí nổ thực tế từ 19 giải (G1 $\rightarrow$ G5.6), tính chu kỳ 3-4 ngày, giao thoa với Dàn 60 số Cấp 4.
- **Cấu trúc**:
  - 🟡 **Top 1 (Chỉ đạo 3-4d)**: Bạch thủ nước rút (viền vàng phát sáng).
  - 🟠 **Top 4 (Chỉ đạo 3-4d)**: Tứ thủ nước rút (gắn sao cam).
  - ⚪ **Dàn Tinh Túy Ngày 1**: Dàn rút gọn 25-35 số.
  - 🔵 **Dàn Số Lót N1**: Dàn bảo hiểm hòa vốn.
- **Chiến thuật kết hợp**: Nếu số của Phần 0 (như 41) trùng khớp với Top 1/Top 4 của Phần 2 $\rightarrow$ Điểm hội tụ vàng, tự tin đánh lớn.

---

## 3. HỆ THỐNG LẬP LỊCH TỰ ĐỘNG (WINDOWS TASK SCHEDULER)
- **Tên tác vụ Windows**: `XSMB_Auto_Update_Daily_18h35`
- **Thời gian chạy**: Đúng **18:35:00** hàng ngày (`DAILY`).
- **File thực thi**: `auto_daily_18h35.bat` $\rightarrow$ gọi `auto_daily_18h35.py`.
- **Quy trình tự động**:
  1. Cào kết quả XSMB mới nhất hôm nay (27 giải).
  2. Chạy phân tích G7, ma trận Lucky26, xuất Excel Master 18 Sheet và cập nhật `analysis_summary.json`.
  3. Chạy `soi_cau_g1_g5.py`, tính Dàn Tĩnh 4 Cấp mới cho ngày mai, nạp vào `ket_qua_soi_cau_g1_g5.json`.
  4. Đồng bộ file sang thư mục `58_up_to_75`.
  5. Tự động `git commit` và `git push` lên GitHub Pages (`logistic.git` & `57_up_to_75.git`).
  6. Ghi log kiểm tra vào `cron_update.log`.

---

## 4. ĐỒNG BỘ ĐÁM MÂY (GITHUB PAGES & MINI APP)
- Mini App & PC Web truy cập qua link Cloud:
  `https://happiness2286-dot.github.io/logistic/soi_cau_g1_g5_app.html`
- Bất kỳ cập nhật nào về giao diện hay số liệu bắt buộc phải `git push origin main` thì người dùng trên điện thoại và PC mới nhận được bản mới.

---

## 5. CÁC SKILLS ĐÃ ĐĂNG KÝ
- **[xsmb-g7-prediction](file:///.agents/skills/xsmb-g7-prediction/SKILL.md)**: Phân tích G7 XSMB, Super-Score đa khung, Top 3 Đầu/Đuôi, kiểm chứng nuôi khung 3 ngày, xuất Excel chuẩn openpyxl.
- **[xsmb-lucky26-g7-filter](file:///.agents/skills/xsmb-lucky26-g7-filter/SKILL.md)**: Ma trận Lucky26, Nhịp Vàng Gaussian, Tứ Thủ/Song Thủ, Dàn Siêu Lọc N2/N3 (28 số), Top 20 3D/4D và Nhật ký 235+ ngày.
