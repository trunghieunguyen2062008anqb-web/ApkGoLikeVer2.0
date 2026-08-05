# HƯỚNG DẪN CÀI ĐẶT & SỬ DỤNG TOOL AUTO CLICKER ANDROID

Tài liệu này hướng dẫn chi tiết cách thiết lập môi trường, kết nối thiết bị Android (hoặc giả lập) qua ADB, cài đặt các thư viện Python cần thiết và vận hành tool Auto Clicker dựa trên thuật toán OpenCV Template Matching.

---

## 📌 Hướng Dẫn Cài Đặt Nhanh

### Bước 1: Cài đặt Python & Các Thư viện Cần thiết
Hãy chắc chắn rằng máy tính của bạn đã cài đặt **Python 3.8+**. Mở Command Prompt (cmd) hoặc PowerShell trên Windows và chạy lệnh sau để cài đặt OpenCV và NumPy:

```bash
pip install opencv-python numpy
```

---

### Bước 2: Cài đặt và Cấu hình ADB (Android Debug Bridge)
ADB là công cụ giao tiếp giữa máy tính và điện thoại Android của bạn.

#### Cách 1: Tải bộ ADB chính thức từ Google (Nếu dùng điện thoại thật)
1. Tải bản rút gọn tại: [Platform Tools dành cho Windows](https://dl.google.com/android/repository/platform-tools-latest-windows.zip).
2. Giải nén thư mục `platform-tools` vào một phân vùng bất kỳ (Ví dụ: `C:\platform-tools`).
3. Thêm đường dẫn `C:\platform-tools` vào biến môi trường **PATH** của Windows để có thể gọi lệnh `adb` từ bất kỳ đâu.
   - Nhấn phím `Windows`, tìm kiếm "Environment Variables" -> Chọn "Edit the system environment variables".
   - Bấm vào nút "Environment Variables...".
   - Tại phần "System variables", tìm dòng `Path` -> Bấm "Edit" -> Chọn "New" -> Điền `C:\platform-tools`.
   - Bấm OK để lưu lại.

#### Cách 2: Sử dụng ADB đi kèm của giả lập (LDPlayer, Nox, Memu...)
Nếu bạn dùng giả lập, trong thư mục cài đặt giả lập đã tích hợp sẵn công cụ `adb.exe` (hoặc `nox_adb.exe`).
- Bạn chỉ cần mở thư mục cài đặt giả lập (Ví dụ: `C:\LDPlayer\LDPlayer9`) và chạy cmd tại đó, hoặc thêm thư mục này vào PATH.
- *Lưu ý*: Hãy đảm bảo chỉ có 1 phiên bản ADB hoạt động để tránh xung đột cổng kết nối (`5037`).

---

### Bước 3: Cấu hình Kết Nối Điện thoại / Giả lập

#### 📱 Đối với Điện thoại Android thật:
1. Vào **Cài đặt** (Settings) -> **Thông tin điện thoại** (About Phone) -> Nhấp liên tục 7-10 lần vào mục **Số hiệu bản dựng** (Build Number) đến khi xuất hiện thông báo *"Bạn đã là nhà phát triển"*.
2. Quay lại menu Cài đặt chính -> Vào mục **Tùy chọn nhà phát triển** (Developer Options).
3. Tìm và bật tính năng **Gỡ lỗi USB** (USB Debugging). *Đối với một số máy Xiaomi/Oppo, bạn cần bật thêm cả mục "Gỡ lỗi USB (Cài đặt bảo mật)" để cho phép gửi lệnh nhấn/vuốt màn hình.*
4. Cắm cáp USB nối điện thoại vào máy tính. Điện thoại sẽ hiện một popup hỏi quyền gỡ lỗi từ máy tính, hãy chọn **Luôn cho phép từ máy tính này** (Always allow from this computer) và bấm **Cho phép**.

#### 💻 Đối với các phần mềm Giả lập (LDPlayer, Nox Player, BlueStacks):
1. Vào **Cài đặt giả lập** -> Mục **Khác/Tính năng nâng cao** -> Bật **Gỡ lỗi USB** hoặc **ADB Connection**.
2. Thường thì giả lập sẽ tự động kết nối ADB.

#### 🔍 Kiểm tra kết nối:
Mở cửa sổ dòng lệnh (cmd/PowerShell) và gõ:
```bash
adb devices
```
Nếu màn hình hiển thị tương tự dưới đây là đã kết nối thành công:
```text
List of devices attached
emulator-5554   device
```
*(Nếu hiển thị chữ `unauthorized` bên cạnh thiết bị, hãy kiểm tra màn hình điện thoại và bấm xác nhận đồng ý gỡ lỗi).*

---

## 📸 Cách Chụp & Cắt Ảnh Mẫu (Templates)

Để script có thể nhận diện chính xác các nút bấm, bạn cần chuẩn bị các ảnh mẫu như sau:

1. Chụp ảnh màn hình điện thoại của bạn lúc đang hiển thị giao diện cần tương tác.
2. Sử dụng công cụ cắt ảnh (như Snipping Tool của Windows, Paint, Photoshop, v.v.).
3. Cắt sát viền nút bấm hoặc biểu tượng cần nhận dạng:
   - Cắt thật chính xác nút bấm, tránh lấy quá nhiều phần nền thay đổi xung quanh nút.
   - Giữ nguyên độ phân giải gốc của ảnh chụp màn hình khi cắt (không co giãn/rescale ảnh).
4. Tạo thư mục tên là `templates` cùng cấp với file `auto_clicker.py`.
5. Lưu ảnh đã cắt vào thư mục đó với tên định sẵn:
   - Nút tắt quảng cáo: Lưu tên `nut_dong_quang_cao.png`
   - Nút tiếp tục: Lưu tên `nut_tiep_tuc.png`

> **💡 Mẹo:** Nếu ảnh mẫu trên điện thoại thay đổi kích thước do xoay ngang hoặc do giao diện hiển thị khác nhau, OpenCV có thể không tìm thấy. Hãy chắc chắn ảnh chụp màn hình mẫu và màn hình quét thực tế có cùng độ phân giải hiển thị.

---

## 🚀 Hướng Dẫn Vận Hành Tool

Sau khi đã có thiết bị kết nối và các ảnh mẫu trong thư mục `templates`, thực hiện chạy script bằng lệnh:

```bash
python auto_clicker.py
```

### 📊 Giải thích cơ chế hoạt động của Script:
1. **Kiểm tra thiết bị**: Tìm thiết bị kết nối thông qua lệnh `adb devices`. Nếu có nhiều thiết bị, mặc định sẽ lấy thiết bị đầu tiên.
2. **Load trước dữ liệu ảnh**: Đọc các ảnh mẫu trong `templates/` vào RAM để tăng tốc độ so khớp ảnh, tiết kiệm I/O ổ đĩa.
3. **Vòng lặp quét**:
   - Sử dụng `adb exec-out screencap -p` để truyền trực tiếp dữ liệu ảnh nhị phân từ Android về RAM của Python qua giao thức ống dẫn (Pipe), loại bỏ hoàn toàn việc lưu ảnh tạm thời giúp tốc độ cực kỳ nhanh (chỉ mất ~0.1 - 0.2s cho mỗi lần chụp và decode).
   - Dùng thuật toán **cv2.matchTemplate** của OpenCV (phương pháp `cv2.TM_CCOEFF_NORMED`) để quét ảnh.
   - Tìm kiếm tọa độ khớp nhất. Nếu độ tương đồng cao hơn ngưỡng `threshold` (mặc định là `0.8` tương đương 80%), thuật toán sẽ lấy tọa độ góc trên-trái cộng thêm một nửa chiều rộng & chiều cao của ảnh mẫu để lấy **tọa độ tâm**.
   - Gửi lệnh click qua `adb shell input tap x y`.
   - Nếu trong một chu kỳ quét đã tìm thấy và nhấn một nút (ví dụ `nut_dong_quang_cao`), script sẽ tạm nghỉ và chuyển sang chu kỳ tiếp theo để tránh nhấn đè hoặc thực hiện hành động thừa.
4. **Nghỉ thông minh**: Tự động tính toán thời gian chạy CPU và ngủ bù hợp lý để duy trì chu kỳ quét mỗi `1.0` giây ổn định mà không gây nóng máy tính.
