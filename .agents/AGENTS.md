# Rules & Customizations for XSMB AI Project

## 1. QUY TẮC BẮT BUỘC KHI LÀM VIỆC VỚI NGƯỜI DÙNG
- **"Trao đổi trước tiên - Người dùng đồng ý mới tiến hành sửa"**: Mọi ý tưởng, thay đổi thuật toán, sửa code, thêm giao diện đều phải trao đổi giải thích phương án trước. Chỉ khi người dùng nhắn "đồng ý" mới can thiệp vào mã nguồn hoặc file dữ liệu.
- **Nguyên tắc phân lập thư mục độc lập**: Tuyệt đối không tự ý sao chép, đè lẫn cấu trúc dữ liệu giữa các thư mục dự án riêng biệt (`67_up_95`, `Logic`, `SANLUONG2026`).

---

## 2. QUY CHUẨN TUYỆT ĐỐI VỀ ĐÀI QUAY & DÒNG DỮ LIỆU (100% CÙNG ĐÀI XSMB)
- **Đồng nhất nguồn cào**: Toàn bộ hệ thống (`crawl_and_analyze.py`, `live_radar_scanner.py`, `soi_cau_g1_g5.py`) được khóa cố định theo mã định danh `code=mb` (Xổ số kiến thiết Miền Bắc truyền thống, 27 giải mở thưởng lúc 18h15). Tuyệt đối không kết nối với XSMT, XSMN hay Vietlott.
- **Nguồn cấp dữ liệu chuẩn hóa (Tuyệt đối không dùng mketqua.net/ketqua.net)**:
  - ❌ **CẤM HOÀN TOÀN**: `mketqua.net` và `ketqua.net` (bị ISP sinkhole chặn cổng 443 làm treo tiến trình quét và mất giờ chốt số).
  - ⚡ **Ưu tiên 1 (Live Real-time ~50ms)**: `https://api.383.im/lottery/live.json` — quét trực tiếp từng giải trong giờ quay (18h14 - 18h35).
  - 🛡️ **Ưu tiên 2 (Lịch sử & Dự phòng Tức thì)**: `https://xosodaiphat.com/xsmb-xo-so-mien-bac.html` và `xsmb-30-ngay.html`. Tự động fallback sang Đại Phát ngay lập tức nếu API 383.im gặp lỗi mạng hoặc timeout.
- **Bản chất đài quay XSMB**: Cả 7 ngày trong tuần đều mở thưởng tại chung 1 trường quay (**Số 1 Tăng Bạt Hổ, Hà Nội • Đài PT-TH Hà Nội / VTC9, 18h15 - 18h35**), dùng chung 1 hệ thống lồng quay và 1 Hội đồng giám sát.
- **Phân lập 2 tầng chu kỳ**:
  1. *Tầng 1 (Hàng ngày)*: Radar Live G1-G5, Dàn Tĩnh 4 Cấp và Khung 3N chạy theo nhịp rơi liên tục hàng ngày ($N-1 \rightarrow N \rightarrow N+1$).
  2. *Tầng 2 (Theo Thứ - DOW Model)*: Phân tích phong độ riêng theo từng thứ (chu kỳ 7 ngày) trong Excel Master 18 Sheet để bắt đúng quy luật riêng của từng đài thành viên.

---

## 3. KIẾN TRÚC 2 TRƯỜNG PHÁI KẾT HỢP: TĨNH (ĐẦU NGÀY) & ĐỘNG (GIỜ QUAY)

### A. PHẦN 0: DÀN TĨNH 4 CẤP (Tự Động Nhảy Ngày & Số Động 100%)
- **Cơ chế nhảy ngày thông minh**:
  - *Trước 18h15*: Giữ ngày hiện tại, trạng thái: `ĐANG CÓ HIỆU LỰC (VÀO TIỀN TRƯỚC 18H15)`.
  - *Sau 18h31 (khi đã có GĐB hôm nay)*: **Tự động `+1 ngày` và chuyển thứ tiếng Việt** sang ngày mai, trạng thái: `ĐANG HIỆU LỰC CHO KỲ TỚI (VÀO TIỀN TRƯỚC 18H15 NGÀY MAI)`.
  - Tuyệt đối không gán cứng chuỗi ngày hay số trong code/HTML.
- **4 Cấp Độ Phân Tầng Động**:
  1. **Cấp 4 (Hỏa lực tối thượng)**: 
     - 👑 **Bạch Thủ Đề**: Tọa độ hội tụ Cầu Ghép Góc $G7.1[0] + G7.4[1]$ từ kỳ hôm trước (ví dụ ngày 26/09 G7 là `66` và `45` $\rightarrow$ ra con **`65`** cho ngày 27/09).
     - 🔥 **Song Thủ Đề**: Cặp đảo chiều tự động (ví dụ: **`65 - 56`**).
     - ⭐ **Tứ Thủ Đề**: Ghép thêm 2 số cao điểm nhất của Dàn 9 số Cội Nguồn (ví dụ: **`65 - 56 - 22 - 21`**).
     - 🔮 **Càng 3D**: `0, 2, 4, 5, 7`.
  2. **Cấp 3 (Dàn 9 số Cội Nguồn)**: Tự động ghép ma trận **Top 3 Đầu $\times$ Top 3 Đuôi** phục hồi.
  3. **Cấp 2 (Dàn Giao Thoa 38 số)**: Ép Chạm G7 $\times$ Tổng G7 & Nhịp Vàng Gaussian.
  4. **Cấp 1 (Dàn Gốc 60 số N1)**: Khung N1 chuẩn độ phủ an toàn 87.5% - 97%.
- **Giao diện**: Nút 1-Click Copy tại Phần 0 liên kết sự kiện động, tự hiển thị text theo con số mới và sao chép chính xác.

---

### B. RADAR SOI LIVE G1-G5 & KHÓA CHỐT G5 TỨC THÌ (GIỜ QUAY)
1. **Khung Giờ Quét Live & Cơ Chế Date Guard**:
   - Tự động kích hoạt lúc **18:14:00**.
   - **Date Guard chống dừng sớm**: Trước 18h15 nếu API còn lưu kết quả ngày hôm qua, hệ thống tự động khởi tạo trạng thái "Chờ mở thưởng kỳ hôm nay" (0/19 giải), tuyệt đối không nhận nhầm giải ĐB cũ để dừng sớm. Tiến trình chạy xuyên suốt từ 18h14 đến 18h32.
2. **Cơ Chế Khóa Chốt G5 Tức Thì (`LOCKED_G5`)**:
   - Khi nổ đủ **19/19 giải (xong G5.6 lúc ~18h23 - 18h24)** $\rightarrow$ Hệ thống tự động chuyển trạng thái `LOCKED_G5`.
   - Lập tức tính toán và xuất toàn bộ dàn chốt ở Phần 2: Bạch Thủ Top 1 👑, Tứ Thủ Top 4 🔥, Càng 3D 🔮, Dàn Tinh Túy Ngày 1 ⭐, Số Lót N1 🛡️.
   - Tự động đẩy Git commit & push lên GitHub Pages ngay trước **18h28** để người dùng vào tiền an toàn trước khi quay Giải Đặc Biệt.
   - Phiên live chỉ kết thúc sau **18h30** khi đã thực sự có Giải Đặc Biệt của ngày hôm nay.
3. **Tâm 3 Càng 3D Live**:
   - Lấy số giữa (tâm) của Giải Nhất G1 (nổ lúc **18h16**) làm càng 3D.
   - Kết hợp trực tiếp với các dàn số để đánh trực diện cho **Giải Đặc Biệt (GĐB) của chính ngày hôm đó lúc 18h30**.
4. **Bộ Lọc Giao Thoa 3 Chiều (Consensus Scoring - Không Làm Mất Gốc)**:
   - **Nguyên tắc**: Giữ nguyên 100% logic thống kê chu kỳ của Radar gốc, không ghi đè làm mất cốt lõi.
   - **Công thức Điểm Hội Tụ Đồng Thuận**:
     $$\text{Điểm Giao Thoa} = \text{Radar G1-G5} + \text{Dàn 9s AI} + \text{Chạm Tâm G1} + \text{Ép Cầu Tổng G7} + \text{Khung 60s N1}$$
5. **Cặp Lót Lộn Song Thủ Trụ (Bảo Vệ 100%)**:
   - Triệt tiêu hoàn toàn rủi ro nổ lộn vị trí đầu/đuôi (bắt 42 về 24, hoặc bắt 23 về 32).
   - **Giao diện Thẻ Đôi Cân Xứng (Tab 2)**:
     - Thẻ trái: 👑 **Bạch Thủ Trụ** (Top 1) kèm nút Copy BT.
     - Thẻ phải: 🛡️ **Lót Lộn Trụ** kèm hiển thị `Cặp Song Thủ: [BT - Lót]` và nút Copy Cặp ST.
   - **Nút "Copy Gói Chốt Gấp" (1 Chạm)**: Gom tức thì đầy đủ: Bạch Thủ, Lót Lộn, Tứ Thủ, 3 Càng, Dàn 9s và Dàn Lót để gửi tin nhắn/vào tiền chớp nhoáng trước 18h28.

---

### C. PHẦN 3: DÀN SỐ N1 (60 SỐ) - PHÂN CẤP MÀU SẮC SỐ MẠNH (CHUẨN GIAO DIỆN)
- **Thanh Chú Thích Phân Loại (Legend Chips)**:
  - 👑 **Bạch thủ**: Nền vàng viền gold rực rỡ + glow (`.tag-bach-thu`).
  - 🔥 **Tứ thủ**: Nền cam viền orange + glow (`.tag-tu-thu`).
  - ⭐ **Dàn 9**: Nền xanh dương viền cyan + glow (`.tag-dan-9`).
  - 🔄 **Dàn đảo**: Nền xanh ngọc viền emerald + glow (`.tag-dan-dao`).
  - 📦 **Dàn lót**: Nền slate tối viền mờ tinh tế (`.tag-dan-lot`).
- **Lưới Ma Trận 60 Số N1**: Tự động phân cấp và khoác lên màu sắc, icon tương ứng giúp người dùng nhận diện ngay số mạnh để phân bổ tỷ trọng vốn.
- **Tính Năng 1-Click Copy Thông Minh**: Khi bấm vào từng số hoặc nút Copy Dàn N1, hệ thống tự động bóc tách sạch sẽ các icon và chỉ sao chép dãy số 2D chuẩn (`01, 02...`), không bị dính icon hay ký tự lạ.

---

### D. HỆ THỐNG KIỂM CHỨNG & THEO DÕI LỊCH SỬ 3 TRỤ CỘT (PHẦN 4A, 4B, 4C)
1. **Phần 4A (Khung 3 Ngày - 58_up_to_75)**: Theo dõi độc lập chu kỳ nuôi N1, N2, N3.
2. **Phần 4B (Soi Trực Tiếp G1-G5)**: Đánh giá hiệu suất Bạch Thủ Top 1, Tứ Thủ Top 4 và Dàn Lót.
3. **Phần 4C (Dàn Tinh Túy Ngày 1 - 60 Ngày)**:
   - Theo dõi độc lập 60 kỳ gần nhất của Dàn Tinh Túy Ngày 1 (Giao thoa 60 số Cấp 4).
   - Tự động cập nhật liên tục khi chốt dàn và khi có kết quả Đề qua hàm `ghi_lich_su_tinh_tuy()` trong `soi_cau_g1_g5.py`.
   - Kết quả kiểm chứng 60 kỳ thực tế: Ăn **52/60 ngày (86.7%)**, Trượt 8/60 ngày (13.3%), Quy mô dàn trung bình ~34 số/kỳ, Chuỗi ăn thông 6 ngày.
   - Giao diện đồng bộ: Badge phong độ 60N tại Phần 2 và Bảng 5 thẻ thống kê + danh sách 60 dòng cuộn dọc tại Phần 4C Web App.

---

## 4. CHIẾN LƯỢC QUẢN TRỊ RỦI RO 4 TẦNG (GIẢI PHÓNG TÂM LÝ & THỜI GIAN)
- **Mục tiêu**: Loại bỏ hoàn toàn áp lực tâm lý và tình trạng mất hàng giờ kiểm định thủ công mỗi ngày.
- **Phân bổ tỷ trọng vốn**:
  1. 🛡️ **Tầng 1 (Dàn 60 số N1 - Khung 3N ăn 97%)**: **TẤM KHIÊN BẢO VỆ VỐN**. Đảm bảo giữ vững an toàn tài khoản, ngày nào cũng giữ nhịp hòa hoặc lãi nhẹ.
  2. ⚖️ **Tầng 2 & 3 (Dàn 38s / Siêu Lọc 28s / Dàn 9s)**: **ĐÒN BẨY SINH LỜI**.
  3. 🎯 **Tầng 4 (Bạch Thủ 👑, Song Thủ 🔥, Tứ Thủ ⭐, Càng 3D 🔮)**: **ĐIỂM THƯỞNG MAY MẮN**. Chỉ vào tiền nhỏ (5% - 10% vốn). Trúng thì thắng đậm, trượt thì Tầng 1 đã bù đắp, tâm lý luôn thư thái, an nhiên.

---

## 5. HỆ THỐNG LẬP LỊCH TỰ ĐỘNG KÉP (WINDOWS TASK SCHEDULER)
- **Đường dẫn thực thi an toàn**: Dùng Windows 8.3 Short Path (`E:\DONGBO~1\NEWHAG~1\NM2026~1\DNAI_A~1\Logic\...`) để loại bỏ hoàn toàn lỗi mã hóa tiếng Việt có dấu (`Năm 2026` / `Dự Án`).
- **Quy chuẩn Git Push**: Luôn thực hiện `git pull --rebase origin main` trước khi `git push origin main` trong mọi file Python/batch để chống xung đột/từ chối đẩy mã.

### A. Tác Vụ Quét Live Giờ Vàng: `XSMB_AI_AutoLive_18h14`
- **Thời gian chạy**: Kích hoạt đúng **18:14:00** hàng ngày (`DAILY`).
- **Lệnh thực thi**: `cmd.exe /c E:\DONGBO~1\NEWHAG~1\NM2026~1\DNAI_A~1\Logic\auto_live_18h14.bat`.
- **Quy trình**:
  1. Quét Live liên tục mỗi 5s - 30s qua API `383.im` (Primary) và `xosodaiphat.com` (Fallback).
  2. Bắt đủ 19 giải (xong G5.6 ~18h23 - 18h24) $\rightarrow$ Khóa chốt `LOCKED_G5`, tự động commit & push GitHub Pages ngay trước 18h28.
  3. Đợi có GĐB (sau 18h31) $\rightarrow$ Phân tích và ghi nhận kết quả thực tế vào `lich_su_phuong_phap.json`.

### B. Tác Vụ Cập Nhật Tổng Hợp Tối: `XSMB_AI_AutoDaily_18h35`
- **Thời gian chạy**: Đúng **18:35:00** hàng ngày (`DAILY`).
- **Lệnh thực thi**: `cmd.exe /c E:\DONGBO~1\NEWHAG~1\NM2026~1\DNAI_A~1\Logic\auto_daily_18h35.bat`.
- **Quy trình tự động**:
  1. Cào kết quả XSMB 27 giải đầy đủ hôm nay qua `xosodaiphat.com` & `383.im`.
  2. Chạy phân tích G7, ma trận Lucky26, xuất Excel Master 18 Sheet và cập nhật `analysis_summary.json`.
  3. Chạy `soi_cau_g1_g5.py`, tính Dàn Tĩnh 4 Cấp mới cho ngày mai, nạp vào `ket_qua_soi_cau_g1_g5.json`.
  4. Đồng bộ file sang thư mục `58_up_to_75`.
  5. Tự động `git pull --rebase` và `git push` lên GitHub Pages (`logistic.git`).
  6. Ghi log kiểm tra vào `cron_update.log`.

---

## 6. ĐỒNG BỘ ĐÁM MÂY (GITHUB PAGES & MINI APP)
- Mini App & PC Web truy cập qua link Cloud:
  - Model 67UP97 (Live Radar & 97%): `https://happiness2286-dot.github.io/67up97/`
  - Model G1-G5 Logistic: `https://happiness2286-dot.github.io/logistic/soi_cau_g1_g5_app.html`
- Bất kỳ cập nhật nào về giao diện hay số liệu bắt buộc phải `git push origin main` thì người dùng trên điện thoại và PC mới nhận được bản mới.

---

## 7. CÁC SKILLS ĐÃ ĐĂNG KÝ
- **[xsmb-g7-prediction](file:///.agents/skills/xsmb-g7-prediction/SKILL.md)**: Phân tích G7 XSMB, Super-Score đa khung, Top 3 Đầu/Đuôi, kiểm chứng nuôi khung 3 ngày, xuất Excel chuẩn openpyxl.
- **[xsmb-lucky26-g7-filter](file:///.agents/skills/xsmb-lucky26-g7-filter/SKILL.md)**: Ma trận Lucky26, Nhịp Vàng Gaussian, Tứ Thủ/Song Thủ, Dàn Siêu Lọc N2/N3 (28 số), Top 20 3D/4D và Nhật ký 235+ ngày.
