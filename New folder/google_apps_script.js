// ==============================================================================
// CẤU HÌNH GOOGLE DRIVE, TELEGRAM BOT & MINI APP
// ==============================================================================
var PRODUCT_FOLDER_ID = ""; // Ví dụ: "1A2b3C4d5E6f7G..." (Để trống hệ thống tự tạo)
var SCRAP_FOLDER_ID = "";   // Ví dụ: "9Z8y7X6w5V4u3T..." (Để trống hệ thống tự tạo)

// 🤖 CẤU HÌNH TELEGRAM BOT TỰ ĐỘNG CẢNH BÁO
var TELEGRAM_BOT_TOKEN = "8871498341:AAFTzNNaCNXZlaTJlh8znudxrYFs69bu74s"; // Dán Token Bot lấy từ @BotFather vào đây (Ví dụ: "123456789:ABCdefGhIJKlmNo...")
var TELEGRAM_CHAT_ID = "-5457065729";   // Dán Chat ID Nhóm Telegram xưởng vào đây (Ví dụ: "-100123456789")

// 🌐 URL Mini App Sản Lượng của bạn (Netlify hoặc GitHub Pages)
var MINI_APP_URL = "https://happiness2286-dot.github.io/sanluonggcck/";       // Dán link GitHub Pages (ví dụ: "https://ten-ban.github.io/SANLUONG2026/") hoặc Netlify vào đây!

function doGet(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var masterSheet = ss.getSheetByName("Danh Mục Master");
    if (!masterSheet) {
      return ContentService.createTextOutput(JSON.stringify({
        "result": "empty",
        "message": "Chưa có Master Data trên Cloud"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    var cellVal = masterSheet.getRange("A2").getValue();
    if (!cellVal) {
      return ContentService.createTextOutput(JSON.stringify({
        "result": "empty"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    var masterData = JSON.parse(cellVal);
    return ContentService.createTextOutput(JSON.stringify({
      "result": "success",
      "masterData": masterData
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      "result": "error",
      "message": err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

function doPost(e) {
  try {
    // 1. Mở Sheet "Nhật Ký Sản Lượng" (Hoặc Sheet đầu tiên)
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Nhật Ký Sản Lượng");
    if (!sheet) {
      sheet = ss.getSheets()[0];
    }

    // 2. Đọc dữ liệu JSON gửi từ điện thoại công nhân
    var contents = (e && e.postData && e.postData.contents) ? e.postData.contents : "{}";
    var data = JSON.parse(contents);

    // XỬ LÝ LƯU DANH MỤC MASTER (SẢN PHẨM, NGUYÊN CÔNG & CÔNG NHÂN) TỪ ADMIN
    if (data.action === "saveMasterData" && data.masterData) {
      var masterSheet = ss.getSheetByName("Danh Mục Master");
      if (!masterSheet) {
        masterSheet = ss.insertSheet("Danh Mục Master");
        masterSheet.appendRow(["CƠ SỞ DỮ LIỆU DANH MỤC MASTER (JSON)"]);
      }
      masterSheet.getRange("A2").setValue(JSON.stringify(data.masterData));

      // Tự động đảm bảo Sheet "Đơn Hàng & Giao Hàng" được khởi tạo chuẩn mẫu
      try { createDonHangGiaoHangSheet(); } catch (eDh) { console.log(eDh); }

      // Đồng bộ tự động danh sách Công Nhân từ Master Data sang Sheet "Danh Sách Công Nhân"
      if (data.masterData.userAccounts && Array.isArray(data.masterData.userAccounts)) {
        var wSheet = ss.getSheetByName("Danh Sách Công Nhân") || ss.insertSheet("Danh Sách Công Nhân");
        var existingNames = new Set();
        var currentData = wSheet.getDataRange().getValues();

        if (currentData.length <= 1) {
          wSheet.clear();
          wSheet.appendRow(["Họ Và Tên Công Nhân", "Tài Khoản / Mã", "Trạng Thái"]);
        } else {
          for (var r = 1; r < currentData.length; r++) {
            if (currentData[r][0]) existingNames.add(String(currentData[r][0]).trim());
          }
        }

        data.masterData.userAccounts.forEach(function (acc) {
          var name = acc.fullName || acc.username;
          if (name && !existingNames.has(name.trim())) {
            wSheet.appendRow([name.trim(), acc.username || "", "Đang làm việc"]);
            existingNames.add(name.trim());
          }
        });
      }

      return ContentService.createTextOutput(JSON.stringify({
        "result": "success",
        "message": "Đã đồng bộ thành công Sản phẩm, Nguyên công & Công nhân mới lên Cloud!"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // XỬ LÝ LƯU HOẶC CẬP NHẬT ĐƠN HÀNG & GIAO HÀNG TỪ ADMIN
    if (data.action === "saveOrderData" && data.order) {
      var orderSheet = createDonHangGiaoHangSheet();
      var o = data.order;
      var oPo = String(o.po || "").trim();

      var oRows = orderSheet.getDataRange().getValues();
      var foundRow = -1;

      for (var r = 1; r < oRows.length; r++) {
        if (String(oRows[r][1]).trim().toLowerCase() === oPo.toLowerCase()) {
          foundRow = r + 1;
          break;
        }
      }

      var qtyPlan = Number(o.qty_plan || 0);
      var qtyDelivered = Number(o.qty_delivered || 0);
      var status = qtyDelivered >= qtyPlan ? "Đã giao đủ" : "Đang sản xuất";

      if (foundRow > 1) {
        // Cập nhật dòng PO hiện có
        orderSheet.getRange(foundRow, 5).setValue(qtyPlan);
        orderSheet.getRange(foundRow, 7).setValue(qtyDelivered);
        orderSheet.getRange(foundRow, 8).setFormula("=E" + foundRow + "-G" + foundRow);
        orderSheet.getRange(foundRow, 10).setValue(o.deadline || "");
        orderSheet.getRange(foundRow, 11).setValue(status);
        if (o.note) orderSheet.getRange(foundRow, 12).setValue(o.note);
      } else {
        // Thêm PO mới vào dòng cuối
        var nextSttOrder = oRows.length;
        var rowFormula = "=E" + (nextSttOrder + 1) + "-G" + (nextSttOrder + 1);
        orderSheet.appendRow([
          nextSttOrder,
          oPo,
          o.customer || "",
          o.product || "",
          qtyPlan,
          0,
          qtyDelivered,
          rowFormula,
          o.order_date || "",
          o.deadline || "",
          status,
          o.note || ""
        ]);
      }

      return ContentService.createTextOutput(JSON.stringify({
        "result": "success",
        "message": "Đã lưu & đồng bộ Đơn hàng lên Google Sheet 'Đơn Hàng & Giao Hàng'!"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // 3. Tính số thứ tự STT dòng tiếp theo
    var lastRow = sheet.getLastRow();
    var nextStt = lastRow > 1 ? lastRow - 1 : 1;

    // 4. Xử lý TỰ ĐỘNG UPLOAD ÁNH SẢN PHẨM & ÁNH PHẾ PHẨM LÊN GOOGLE DRIVE
    var uploadPhotosToDrive = function (photoArray, folderName, filePrefix, customFolderId) {
      var urls = [];
      if (!photoArray || !Array.isArray(photoArray) || photoArray.length === 0) return urls;
      try {
        var folder;
        if (customFolderId && customFolderId.trim() !== "") {
          try {
            folder = DriveApp.getFolderById(customFolderId.trim());
          } catch (eFolder) {
            console.log("Không tìm thấy Folder ID chỉ định, tự tạo theo tên: " + eFolder.toString());
          }
        }
        if (!folder) {
          var folders = DriveApp.getFoldersByName(folderName);
          folder = folders.hasNext() ? folders.next() : DriveApp.createFolder(folderName);
        }

        for (var i = 0; i < photoArray.length; i++) {
          var rawPhoto = photoArray[i];
          if (rawPhoto && typeof rawPhoto === 'string') {
            if (rawPhoto.indexOf("data:image") >= 0 || rawPhoto.length > 100) {
              var base64Data = rawPhoto;
              var mimeType = "image/jpeg";

              if (rawPhoto.indexOf("data:image") >= 0) {
                var parts = rawPhoto.split(",");
                var mimeMatch = parts[0].match(/:(.*?);/);
                if (mimeMatch) mimeType = mimeMatch[1];
                base64Data = parts[1] || parts[0];
              }

              var fileName = filePrefix + "_" + (data.worker || "Worker").replace(/\s+/g, "_") + "_" + (data.date || "") + "_STT" + nextStt + "_" + (i + 1) + ".jpg";
              var blob = Utilities.newBlob(Utilities.base64Decode(base64Data), mimeType, fileName);
              var file = folder.createFile(blob);

              file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
              urls.push(file.getUrl());
            } else if (rawPhoto.indexOf("http") === 0) {
              urls.push(rawPhoto);
            }
          }
        }
      } catch (errDrive) {
        console.log("Lỗi tạo file ảnh trên Google Drive (" + folderName + "): " + errDrive.toString());
      }
      return urls;
    };

    // Upload Ảnh Sản Phẩm Thành Phẩm & Ảnh Phế Phẩm
    var productPhotoUrls = uploadPhotosToDrive(data.product_photos, "Ảnh Báo Cáo Thành Phẩm GCCK 2026", "Anh_SanPham", PRODUCT_FOLDER_ID);
    var scrapPhotoUrls = uploadPhotosToDrive(data.photos, "Ảnh Báo Cáo Phế Phẩm GCCK 2026", "Anh_PhePham", SCRAP_FOLDER_ID);

    var allDriveUrls = [].concat(
      productPhotoUrls.map(function (u) { return "[Sản Phẩm]: " + u; }),
      scrapPhotoUrls.map(function (u) { return "[Phế Phẩm]: " + u; })
    );

    var photoCellContent = allDriveUrls.length > 0 ? allDriveUrls.join("\n") : "Không có ảnh";

    // 5. Thêm 1 dòng báo cáo sản lượng mới vào Google Sheets (Có đính kèm Link Google Drive)
    sheet.appendRow([
      nextStt,                     // STT
      new Date(),                  // Thời gian gửi hệ thống
      data.date || '',             // Ngày làm
      data.worker || '',           // Họ tên công nhân
      data.customer || '',         // Khách hàng
      data.product || '',          // Tên sản phẩm
      data.po || '',               // Số PO
      data.op || '',               // Nguyên công / Công đoạn
      data.machine || '',          // Máy gia công
      data.qty_dat || 0,           // SL Đạt (OK)
      data.qty_xuly || 0,          // SL Xử lý (Rework)
      data.qty_huy || 0,           // SL Hủy (Scrap)
      data.total_wage || 0,        // Lương khoán tạm tính (VNĐ)
      data.material || '',         // Vật tư / Chip dao
      data.qty_material || 0,      // Số lượng tiêu hao
      data.downtime_min || 0,      // Phát sinh dừng máy (Phút)
      data.downtime_note || '',    // Ghi chú phát sinh
      photoCellContent             // Link Google Drive hình ảnh sản phẩm & phế phẩm
    ]);

    // 6. Trả về phản hồi XÁC NHẬN THÀNH CÔNG cho Mini App
    return ContentService.createTextOutput(JSON.stringify({
      "result": "success",
      "message": "Đã lưu sản lượng và tải ảnh lên Google Drive thành công!"
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({
      "result": "error",
      "message": err.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// ==============================================================================
// 7. HÀM TỰ ĐỘNG ĐỐI SOÁT & CẢNH BÁO QUÁ HẠN BÁO CÁO QUA TELEGRAM BOT
// ==============================================================================

// Chạy tự động sau Ca 1 (Lúc 14h:15)
function checkShift1_14h() {
  checkOverdueReports("Ca 1 (Sáng)");
}

// Chạy tự động sau Ca 2 (Lúc 22h:15)
function checkShift2_22h() {
  checkOverdueReports("Ca 2 (Chiều)");
}

// Chạy tự động sau Ca 3 (Lúc 06h:15 sáng hôm sau)
function checkShift3_06h() {
  checkOverdueReports("Ca 3 (Đêm)");
}

function checkOverdueReports(shiftName) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Nhật Ký Sản Lượng");
    if (!sheet) sheet = ss.getSheets()[0];

    var todayStr = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd");
    var todayShortStr = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "dd/MM/yyyy");

    var data = sheet.getDataRange().getValues();
    var reportedWorkers = new Set();

    // Duyệt danh sách các báo cáo đã nộp hôm nay (Cột D là Tên Công Nhân - Index 3)
    for (var i = 1; i < data.length; i++) {
      var rowDate = data[i][2]; // Cột Ngày làm
      var workerName = data[i][3]; // Cột Công nhân

      var isToday = false;
      if (rowDate instanceof Date) {
        var rDateStr = Utilities.formatDate(rowDate, Session.getScriptTimeZone(), "yyyy-MM-dd");
        if (rDateStr === todayStr) isToday = true;
      } else if (typeof rowDate === 'string' && (rowDate.includes(todayStr) || rowDate.includes(todayShortStr))) {
        isToday = true;
      }

      if (isToday && workerName) {
        reportedWorkers.add(String(workerName).trim());
      }
    }

    // Đọc danh sách Công nhân 100% trực tiếp từ Google Sheet "Danh Sách Công Nhân"
    var allWorkers = [];
    var workerSheet = ss.getSheetByName("Danh Sách Công Nhân") || ss.getSheetByName("CongNhan");

    // Nếu chưa có Sheet "Danh Sách Công Nhân", tự động tạo Sheet trống chuẩn mẫu cho Quản đốc nhập tên
    if (!workerSheet) {
      workerSheet = ss.insertSheet("Danh Sách Công Nhân");
      workerSheet.appendRow(["Họ Và Tên Công Nhân", "Bộ Phận / Máy", "Trạng Thái"]);
      console.log("✅ Đã tự động tạo Sheet 'Danh Sách Công Nhân' trống trên Google Sheets!");
    }

    // Đọc dữ liệu công nhân từ Sheet "Danh Sách Công Nhân"
    var wData = workerSheet.getDataRange().getValues();
    for (var w = 1; w < wData.length; w++) {
      var name = wData[w][0] ? String(wData[w][0]).trim() : '';
      var status = wData[w][2] ? String(wData[w][2]).trim().toLowerCase() : '';

      // Bỏ qua dòng tiêu đề hoặc công nhân đã đánh dấu "Đã nghỉ" / "Nghỉ việc"
      if (name && name !== "Họ Và Tên Công Nhân" && status !== "nghỉ việc" && status !== "đã nghỉ") {
        allWorkers.push(name);
      }
    }

    // Nếu chưa có công nhân nào được nhập trên Google Sheet
    if (allWorkers.length === 0) {
      console.log("⚠️ Chưa có danh sách công nhân nào trong Sheet 'Danh Sách Công Nhân'. Quản đốc vui lòng điền tên công nhân vào Cột A của Sheet này!");
      return;
    }

    // Lọc công nhân chưa nộp báo cáo
    var missingWorkers = [];
    allWorkers.forEach(function (w) {
      if (!reportedWorkers.has(w)) {
        missingWorkers.push(w);
      }
    });

    if (missingWorkers.length === 0) {
      console.log("✅ Tất cả công nhân đã nộp báo cáo sản lượng đầy đủ cho " + shiftName + "!");
      return;
    }

    // Soạn tin nhắn HTML cảnh báo cho Telegram
    var messageText = "<b>⚠️ CẢNH BÁO QUÁ HẠN BÁO CÁO SẢN LƯỢNG GCCK</b>\n" +
      "--------------------------------------\n" +
      "📌 <b>Kiểm tra:</b> " + shiftName + "\n" +
      "📅 <b>Ngày:</b> " + todayShortStr + "\n" +
      "⏰ <b>Thời điểm:</b> " + Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "HH:mm") + "\n" +
      "--------------------------------------\n" +
      "🔴 <b>CÔNG NHÂN CHƯA NỘP BÁO CÁO (" + missingWorkers.length + " người):</b>\n";

    missingWorkers.forEach(function (w, idx) {
      messageText += (idx + 1) + ". <b>" + w + "</b>\n";
    });

    messageText += "--------------------------------------\n";
    if (MINI_APP_URL && MINI_APP_URL.trim() !== "") {
      messageText += "📲 <b>Bấm link bên dưới để nộp báo cáo ngay:</b>\n" + MINI_APP_URL.trim();
    } else {
      messageText += "👉 <i>Đề nghị công nhân truy cập Web App nộp báo cáo bổ sung ngay!</i>";
    }

    console.log(messageText);

    // Gửi cảnh báo qua Telegram Bot API
    sendTelegramMessage(messageText);

  } catch (err) {
    console.log("Lỗi kiểm tra cảnh báo quá hạn: " + err.toString());
  }
}

// Hàm gửi tin nhắn Telegram Bot chuẩn API
function sendTelegramMessage(htmlMessageText) {
  if (!TELEGRAM_BOT_TOKEN || TELEGRAM_BOT_TOKEN.trim() === "" || !TELEGRAM_CHAT_ID || TELEGRAM_CHAT_ID.trim() === "") {
    console.log("⚠️ Chưa cấu hình TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID");
    return;
  }

  try {
    var url = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN.trim() + "/sendMessage";
    var payload = {
      "chat_id": TELEGRAM_CHAT_ID.trim(),
      "text": htmlMessageText,
      "parse_mode": "HTML",
      "disable_web_page_preview": false
    };

    var options = {
      "method": "post",
      "contentType": "application/json",
      "payload": JSON.stringify(payload),
      "muteHttpExceptions": true
    };

    var response = UrlFetchApp.fetch(url, options);
    console.log("📲 Đã gửi cảnh báo Telegram thành công! Phản hồi: " + response.getContentText());
  } catch (eTelegram) {
    console.log("❌ Lỗi gửi tin nhắn Telegram: " + eTelegram.toString());
  }
}

// ==============================================================================
// 8. HÀM TỰ ĐỘNG TẠO BỘ HẸN GIỜ (TRIGGERS) CHO 3 CA (14H15, 22H15, 06H15)
// Chạy hàm này 1 lần duy nhất trong Apps Script để kích hoạt đặt lịch!
// ==============================================================================
function setupShiftTriggers() {
  // Xóa các trigger cũ nếu có
  var existingTriggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < existingTriggers.length; i++) {
    ScriptApp.deleteTrigger(existingTriggers[i]);
  }

  // Hẹn giờ Ca 1 (Sáng) - Chạy lúc 14:15 hàng ngày
  ScriptApp.newTrigger("checkShift1_14h")
    .timeBased()
    .everyDays(1)
    .atHour(14)
    .nearMinute(15)
    .create();

  // Hẹn giờ Ca 2 (Chiều) - Chạy lúc 22:15 hàng ngày
  ScriptApp.newTrigger("checkShift2_22h")
    .timeBased()
    .everyDays(1)
    .atHour(22)
    .nearMinute(15)
    .create();

  // Hẹn giờ Ca 3 (Đêm) - Chạy lúc 06:15 sáng hàng ngày
  ScriptApp.newTrigger("checkShift3_06h")
    .timeBased()
    .everyDays(1)
    .atHour(6)
    .nearMinute(15)
    .create();

  Logger.log("✅ ĐÃ CÀI ĐẶT THÀNH CÔNG BỘ HẸN GIỜ TỰ ĐỘNG CẢNH BÁO CHO 3 CA (14H15, 22H15, 06H15)!");
}

// ==============================================================================
// HÀM TEST CẤP QUYỀN TRUY CẬP GOOGLE DRIVE
// ==============================================================================
function testDrivePermissions() {
  var folderName = "Ảnh Báo Cáo Thành Phẩm GCCK 2026";
  var folders = DriveApp.getFoldersByName(folderName);
  var folder = folders.hasNext() ? folders.next() : DriveApp.createFolder(folderName);
  Logger.log("✅ Quyền truy cập Google Drive đã được phê duyệt thành công! Thư mục ID: " + folder.getId());
}

// ==============================================================================
// 9. MENU TỰ ĐỘNG & TẠO SHEET "ĐƠN HÀNG & GIAO HÀNG" CHUẨN MẪU
// ==============================================================================
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("⚙️ Quản Lý GCCK 2026")
    .addItem("📦 Khởi Tạo Sheet 'Đơn Hàng & Giao Hàng'", "createDonHangGiaoHangSheet")
    .addItem("⏰ Cài Đặt Bộ Hẹn Giờ Cảnh Báo 3 Ca", "setupShiftTriggers")
    .addToUi();
}

function createDonHangGiaoHangSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheetName = "Đơn Hàng & Giao Hàng";
  var sheet = ss.getSheetByName(sheetName);

  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
  }

  if (sheet.getLastRow() === 0) {
    // 1. Tiêu đề các cột tiêu chuẩn
    var headers = [
      "STT", 
      "Mã PO / Đơn Hàng", 
      "Khách Hàng", 
      "Tên Sản Phẩm", 
      "SL Đặt Hàng (Kế Hoạch)", 
      "SL Đã Gia Công (Đạt)", 
      "SL Đã Giao Hàng", 
      "SL Còn Lại (Nợ Hàng)", 
      "Ngày Đặt Hàng", 
      "Hạn Giao Hàng (Deadline)", 
      "Trạng Thái Đơn Hàng", 
      "Ghi Chú Chi Tiết"
    ];

    sheet.appendRow(headers);

    // Định dạng Thanh tiêu đề Header
    var headerRange = sheet.getRange(1, 1, 1, headers.length);
    headerRange.setFontWeight("bold");
    headerRange.setBackground("#1e293b");
    headerRange.setFontColor("#ffffff");
    headerRange.setHorizontalAlignment("center");
    headerRange.setVerticalAlignment("middle");
    sheet.setRowHeight(1, 35);
    sheet.setFrozenRows(1);

    // 2. Dữ liệu mẫu chuẩn hóa minh họa
    var sampleRows = [
      [1, "PO-2026-001", "Win-Win", "Trục Khuỷu Động Cơ Φ250", 1000, 850, 500, "=E2-G2", "2026-08-01", "2026-08-30", "Đang sản xuất", "Giao đợt 1 thành công 500 pcs"],
      [2, "PO-2026-002", "UCC", "Khuôn gá xích POWER", 200, 200, 200, "=E3-G3", "2026-08-05", "2026-08-20", "Đã giao đủ", "Hoàn thành 100% đúng hạn"],
      [3, "PO-2026-003", "Kachimizu", "Cụm Bán Thành Phẩm ALKTOP", 500, 120, 0, "=E4-G4", "2026-08-10", "2026-08-25", "Đang sản xuất", "Đã xong công đoạn phay"]
    ];

    for (var r = 0; r < sampleRows.length; r++) {
      sheet.appendRow(sampleRows[r]);
    }

    // Căn lề & Định dạng căn chỉnh
    var dataRange = sheet.getRange(2, 1, sampleRows.length, headers.length);
    dataRange.setVerticalAlignment("middle");
    sheet.getRange(2, 1, sampleRows.length, 1).setHorizontalAlignment("center"); // STT
    sheet.getRange(2, 5, sampleRows.length, 4).setHorizontalAlignment("right");  // Số lượng
    sheet.getRange(2, 9, sampleRows.length, 2).setHorizontalAlignment("center"); // Ngày
    sheet.getRange(2, 11, sampleRows.length, 1).setHorizontalAlignment("center"); // Trạng thái

    // Auto fit cột
    for (var col = 1; col <= headers.length; col++) {
      sheet.autoResizeColumn(col);
    }
    Logger.log("✅ Đã khởi tạo thành công Sheet 'Đơn Hàng & Giao Hàng' trên Google Sheets!");
  } else {
    Logger.log("ℹ️ Sheet 'Đơn Hàng & Giao Hàng' đã tồn tại sẵn.");
  }
  return sheet;
}

