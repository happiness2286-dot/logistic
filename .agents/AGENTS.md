# Rules & Customizations for XSMB AI Project

## 1. QUY TẮC BẮT BUỘC KHI LÀM VIỆC VỚI NGƯỜI DÙNG
- **"Trao đổi trước tiên - Người dùng đồng ý mới tiến hành sửa"**: Mọi ý tưởng, thay đổi thuật toán, sửa code, thêm giao diện đều phải trao đổi giải thích phương án trước. Chỉ khi người dùng nhắn "đồng ý" mới can thiệp vào mã nguồn hoặc file dữ liệu.
- **Nguyên tắc phân lập thư mục độc lập**: Tuyệt đối không tự ý sao chép, đè lẫn cấu trúc dữ liệu giữa các thư mục dự án riêng biệt (`67_up_95`, `Logic`, `SANLUONG2026`).

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
  4. **Cấp 1 (Dàn Gốc 60 số N1)**: Khung N1 chuẩn độ phủ an toàn 87.5% - 97%.
- **Giao diện**: Hiển thị ở khối **PHẦN 0** trên Mini App & PC Web (`soi_cau_g1_g5_app.html`), có sẵn các nút 1-Click Copy từng cấp dàn.

---

### B. RADAR SOI LIVE G1-G5 & KHÓA CHỐT G5 TỨC THÌ (GIỜ QUAY)
1. **Khung Giờ Quét Live**: Tự động quét trong khung giờ vàng **18h14 – 18h35**.
2. **Cơ Chế Khóa Chốt G5 Tức Thì (`LOCKED_G5`)**:
   - Khi nổ đủ **19/19 giải (xong G5.6 lúc ~18h24)** $\rightarrow$ Hệ thống tự động chuyển trạng thái `LOCKED_G5`.
   - Lập tức tính toán và xuất toàn bộ dàn chốt để người dùng vào tiền an toàn **trước 18h28** (trước khi quay Giải Đặc Biệt GĐB).
3. **Tâm 3 Càng 3D Live**:
   - Lấy số giữa (tâm) của Giải Nhất G1 (nổ lúc **18h16**) làm càng 3D.
   - Kết hợp trực tiếp với các dàn số để đánh trực diện cho **Giải Đặc Biệt (GĐB) của chính ngày hôm đó lúc 18h30**.
4. **Bộ Lọc Giao Thoa 3 Chiều (Consensus Scoring - Không Làm Mất Gốc)**:
   - **Nguyên tắc**: Giữ nguyên 100% logic thống kê chu kỳ của Radar gốc, không ghi đè làm mất cốt lõi.
   - **Công thức Điểm Hội Tụ Đồng Thuận**:
     $$\text{Điểm Giao Thoa} = \text{Radar G1-G5} + \text{Dàn 9s AI} + \text{Chạm Tâm G1} + \text{Ép Cầu Tổng G7} + \text{Khung 60s N1}$$
   - **Kiểm chứng thực tế ngày 26/09/2026**: Đề về **32**, số 32 bứt phá hội tụ điểm cao vào thẳng **Tứ Thủ** (`42, 24, 32, 37`).
5. **Cặp Lót Lộn Song Thủ Trụ (Bảo Vệ 100%)**:
   - Triệt tiêu hoàn toàn rủi ro nổ lộn vị trí đầu/đuôi (bắt 42 về 24, hoặc bắt 23 về 32).
   - **Giao diện Thẻ Đôi Cân Xứng (Tab 2)**:
     - Thẻ trái: 👑 **Bạch Thủ Trụ** (Top 1) kèm nút Copy BT.
     - Thẻ phải: 🛡️ **Lót Lộn Trụ** kèm hiển thị `Cặp Song Thủ: [BT - Lót]` và nút Copy Cặp ST.
   - **Nút "Copy Gói Chốt Gấp" (1 Chạm)**: Gom tức thì đầy đủ: Bạch Thủ, Lót Lộn, Tứ Thủ, 3 Càng, Dàn 9s và Dàn Lót để gửi tin nhắn/vào tiền chớp nhoáng trước 18h28.

---

## 3. HỆ THỐNG LẬP LỊCH TỰ ĐỘNG KÉP (WINDOWS TASK SCHEDULER)

### A. Tác Vụ Quét Live Giờ Vàng: `XSMB_AI_AutoUpdate_18h15`
- **Thời gian chạy**: Kích hoạt lúc **18:14:00** hàng ngày (`DAILY`).
- **File thực thi**: `AUTO_CRON_18H15.ps1` (chạy ngầm qua PowerShell UTF-8).
- **Quy trình**:
  1. Quét Live liên tục mỗi 5s - 30s qua `live_radar_scanner.py`.
  2. Bắt đủ 19 giải (xong G5.6 ~18h24) $\rightarrow$ Khóa chốt `LOCKED_G5`, tự động commit & push GitHub Pages ngay trước 18h28.
  3. Đợi có GĐB (sau 18h31) $\rightarrow$ Phân tích và ghi nhận kết quả thực tế.

### B. Tác Vụ Cập Nhật Tổng Hợp Tối: `XSMB_Auto_Update_Daily_18h35`
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
  - Model 67UP97 (Live Radar & 97%): `https://happiness2286-dot.github.io/67up97/`
  - Model G1-G5 Logistic: `https://happiness2286-dot.github.io/logistic/soi_cau_g1_g5_app.html`
- Bất kỳ cập nhật nào về giao diện hay số liệu bắt buộc phải `git push origin main` thì người dùng trên điện thoại và PC mới nhận được bản mới.

---

## 5. CÁC SKILLS ĐÃ ĐĂNG KÝ
- **[xsmb-g7-prediction](file:///.agents/skills/xsmb-g7-prediction/SKILL.md)**: Phân tích G7 XSMB, Super-Score đa khung, Top 3 Đầu/Đuôi, kiểm chứng nuôi khung 3 ngày, xuất Excel chuẩn openpyxl.
- **[xsmb-lucky26-g7-filter](file:///.agents/skills/xsmb-lucky26-g7-filter/SKILL.md)**: Ma trận Lucky26, Nhịp Vàng Gaussian, Tứ Thủ/Song Thủ, Dàn Siêu Lọc N2/N3 (28 số), Top 20 3D/4D và Nhật ký 235+ ngày.
