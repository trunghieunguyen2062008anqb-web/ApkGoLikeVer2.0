import os
import sys
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
import cv2
import subprocess
import shutil

# Đường dẫn dữ liệu
RAW_DIR = "dataset/raw_captchas"
PORT = 5000

# HTML Giao diện dán nhãn siêu đẹp (Premium Dark Mode)
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Captcha Trainer Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #0B0F19;
            --bg-card: #151D30;
            --primary: #6366F1;
            --primary-hover: #4F46E5;
            --blue-target: #00D2FF;
            --green-target: #00FF87;
            --text-main: #F3F4F6;
            --text-muted: #9CA3AF;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
        }

        body {
            background-color: var(--bg-main);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            overflow-x: hidden;
        }

        header {
            width: 100%;
            padding: 20px 40px;
            background: rgba(21, 29, 48, 0.5);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        header h1 {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(45deg, var(--primary), var(--blue-target));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .container {
            max-width: 1200px;
            width: 100%;
            padding: 40px 20px;
            display: grid;
            grid-template-columns: 1.5fr 1fr;
            gap: 30px;
            flex-grow: 1;
        }

        .workspace-card {
            background-color: var(--bg-card);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 25px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            min-height: 500px;
        }

        .canvas-container {
            position: relative;
            cursor: crosshair;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
            border: 2px solid rgba(255, 255, 255, 0.1);
        }

        #captcha-image {
            display: block;
            max-width: 100%;
            height: auto;
            user-select: none;
            -webkit-user-drag: none;
        }

        .click-marker {
            position: absolute;
            transform: translate(-50%, -50%);
            pointer-events: none;
            transition: all 0.1s ease;
            box-shadow: 0 0 15px rgba(0,0,0,0.5);
        }

        .marker-blue {
            width: 35px;
            height: 35px;
            border: 3px solid var(--blue-target);
            background-color: rgba(0, 210, 255, 0.2);
            border-radius: 4px;
        }

        .marker-green {
            width: 40px;
            height: 40px;
            border: 3px dashed var(--green-target);
            background-color: rgba(0, 255, 135, 0.2);
            border-radius: 50%;
        }

        .control-panel {
            display: flex;
            flex-direction: column;
            gap: 25px;
        }

        .card {
            background-color: var(--bg-card);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }

        h2 {
            font-size: 20px;
            margin-bottom: 15px;
            font-weight: 600;
        }

        p.desc {
            color: var(--text-muted);
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 20px;
        }

        .step-indicator {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.05);
            padding: 12px 15px;
            border-radius: 10px;
            font-size: 14px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
        }

        .step-active {
            color: var(--primary);
            font-weight: 600;
        }

        .btn-group {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 20px;
        }

        button {
            padding: 14px 20px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 12px;
            border: none;
            cursor: pointer;
            transition: all 0.2s ease;
            width: 100%;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--primary-hover));
            color: white;
        }

        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        }

        .btn-secondary {
            background-color: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .btn-secondary:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }

        .btn-danger {
            background-color: rgba(239, 68, 68, 0.1);
            color: #EF4444;
            border: 1px solid rgba(239, 68, 68, 0.2);
        }

        .btn-danger:hover {
            background-color: rgba(239, 68, 68, 0.2);
        }

        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 15px;
        }

        .stat-box {
            background: rgba(255,255,255,0.02);
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.03);
        }

        .stat-val {
            font-size: 24px;
            font-weight: 800;
            color: var(--primary);
            margin-top: 5px;
        }

        .empty-state {
            text-align: center;
            padding: 40px;
        }

        .empty-state h3 {
            font-size: 22px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <header>
        <h1>AI Captcha Trainer Dashboard</h1>
        <div style="font-size: 14px; color: var(--text-muted);">Zero-dependency Labeling Tool v1.0</div>
    </header>

    <div class="container">
        <!-- Vùng làm việc chính bên trái -->
        <div class="workspace-card" id="workspace">
            <div class="canvas-container" id="canvas-container" onclick="handleCanvasClick(event)">
                <img id="captcha-image" src="" alt="Captcha Image">
                <div id="blue-marker" class="click-marker marker-blue" style="display: none;"></div>
                <div id="green-marker" class="click-marker marker-green" style="display: none;"></div>
            </div>
            <div id="empty-message" class="empty-state" style="display: none;">
                <h3>🎉 Tuyệt vời! Đã dán nhãn xong</h3>
                <p class="desc">Không còn ảnh Captcha thô nào cần gán nhãn trong thư mục dataset/raw_captchas.</p>
            </div>
        </div>

        <!-- Bảng điều khiển bên phải -->
        <div class="control-panel">
            <div class="card">
                <h2>Hướng dẫn Gán nhãn</h2>
                <p class="desc">Bấm chuột lên ảnh để định vị các phần tử Captcha. Thao tác cực kỳ nhanh chóng:</p>
                
                <div class="step-indicator">
                    <span>Bước 1: Khối trượt màu xanh lam</span>
                    <span id="step1-status" class="step-active">Đang chờ click...</span>
                </div>
                <div class="step-indicator">
                    <span>Bước 2: Tâm vòng tròn đích đến</span>
                    <span id="step2-status" style="color: var(--text-muted);">Đang chờ...</span>
                </div>

                <div class="btn-group">
                    <button id="btn-save" class="btn-primary" onclick="saveLabel()" disabled>Lưu & Tiếp tục (Enter)</button>
                    <button class="btn-secondary" onclick="resetClicks()">Reset click lại (R)</button>
                    <button class="btn-danger" onclick="skipImage()">Bỏ qua ảnh này (S)</button>
                </div>
            </div>

            <div class="card">
                <h2>Trạng thái Dữ liệu</h2>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div>Chưa gán nhãn</div>
                        <div class="stat-val" id="stat-unlabeled">0</div>
                    </div>
                    <div class="stat-box">
                        <div>Đã gán nhãn</div>
                        <div class="stat-val" id="stat-labeled" style="color: var(--green-target);">0</div>
                    </div>
                </div>
                
                <div style="margin-top: 25px;">
                    <button id="btn-train" class="btn-primary" style="background: linear-gradient(135deg, #00FF87, #00D2FF); color: #0B0F19;" onclick="startTraining()">
                        🚀 Huấn luyện Mô hình YOLOv8
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentImage = "";
        let clicks = []; // Chứa tối đa 2 click coordinates
        let unlabeledList = [];
        let labeledCount = 0;

        // Fetch danh sách ảnh khi khởi động
        async function fetchImages() {
            try {
                const response = await fetch("/api/images");
                const data = await response.json();
                unlabeledList = data.unlabeled;
                labeledCount = data.labeled_count;
                
                updateStats();
                
                if (unlabeledList.length > 0) {
                    loadImage(unlabeledList[0]);
                } else {
                    showEmpty();
                }
            } catch (err) {
                console.error("Lỗi fetch danh sách ảnh:", err);
            }
        }

        function updateStats() {
            document.getElementById("stat-unlabeled").innerText = unlabeledList.length;
            document.getElementById("stat-labeled").innerText = labeledCount;
        }

        function showEmpty() {
            document.getElementById("canvas-container").style.display = "none";
            document.getElementById("empty-message").style.display = "block";
            document.getElementById("btn-save").disabled = true;
        }

        function loadImage(imgFilename) {
            currentImage = imgFilename;
            const imgEl = document.getElementById("captcha-image");
            imgEl.src = "/images/" + encodeURIComponent(imgFilename);
            
            document.getElementById("canvas-container").style.display = "block";
            document.getElementById("empty-message").style.display = "none";
            
            resetClicks();
        }

        function handleCanvasClick(event) {
            if (clicks.length >= 2) return;

            const rect = event.target.getBoundingClientRect();
            // Lấy tọa độ pixel thực tế trên ảnh
            const imgEl = document.getElementById("captcha-image");
            const scaleX = imgEl.naturalWidth / rect.width;
            const scaleY = imgEl.naturalHeight / rect.height;

            const clickX = Math.round((event.clientX - rect.left) * scaleX);
            const clickY = Math.round((event.clientY - rect.top) * scaleY);

            // Tọa độ phần trăm để hiển thị Marker HTML
            const pctX = ((event.clientX - rect.left) / rect.width) * 100;
            const pctY = ((event.clientY - rect.top) / rect.height) * 100;

            clicks.push({ x: clickX, y: clickY, px: pctX, py: pctY });

            renderMarkers();
        }

        function renderMarkers() {
            const blueMarker = document.getElementById("blue-marker");
            const greenMarker = document.getElementById("green-marker");
            const step1Status = document.getElementById("step1-status");
            const step2Status = document.getElementById("step2-status");
            const btnSave = document.getElementById("btn-save");

            if (clicks.length === 0) {
                blueMarker.style.display = "none";
                greenMarker.style.display = "none";
                step1Status.innerText = "Đang chờ click...";
                step1Status.style.color = "var(--primary)";
                step2Status.innerText = "Đang chờ...";
                step2Status.style.color = "var(--text-muted)";
                btnSave.disabled = true;
            } else if (clicks.length === 1) {
                blueMarker.style.left = clicks[0].px + "%";
                blueMarker.style.top = clicks[0].py + "%";
                blueMarker.style.display = "block";

                step1Status.innerText = `Xông! (${clicks[0].x}, ${clicks[0].y})`;
                step1Status.style.color = "var(--blue-target)";
                
                step2Status.innerText = "Đang chờ click...";
                step2Status.style.color = "var(--primary)";
                btnSave.disabled = true;
            } else if (clicks.length === 2) {
                greenMarker.style.left = clicks[1].px + "%";
                greenMarker.style.top = clicks[1].py + "%";
                greenMarker.style.display = "block";

                step2Status.innerText = `Xong! (${clicks[1].x}, ${clicks[1].y})`;
                step2Status.style.color = "var(--green-target)";
                
                btnSave.disabled = false;
            }
        }

        function resetClicks() {
            clicks = [];
            renderMarkers();
        }

        async function saveLabel() {
            if (clicks.length < 2) return;

            const payload = {
                filename: currentImage,
                blue: { x: clicks[0].x, y: clicks[0].y },
                green: { x: clicks[1].x, y: clicks[1].y }
            };

            try {
                const res = await fetch("/api/label", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                
                if (res.ok) {
                    labeledCount++;
                    unlabeledList.shift(); // Xóa ảnh đầu tiên khỏi hàng đợi
                    updateStats();
                    
                    if (unlabeledList.length > 0) {
                        loadImage(unlabeledList[0]);
                    } else {
                        showEmpty();
                    }
                } else {
                    alert("Không thể lưu nhãn!");
                }
            } catch (err) {
                console.error("Lỗi lưu nhãn:", err);
            }
        }

        function skipImage() {
            unlabeledList.shift();
            updateStats();
            if (unlabeledList.length > 0) {
                loadImage(unlabeledList[0]);
            } else {
                showEmpty();
            }
        }

        async function startTraining() {
            const btn = document.getElementById("btn-train");
            btn.disabled = true;
            btn.innerText = "⏳ Đang Huấn luyện (Xem Console)...";
            
            try {
                const res = await fetch("/api/train", { method: "POST" });
                if (res.ok) {
                    alert("Quá trình huấn luyện đã bắt đầu thành công trên Terminal!");
                } else {
                    alert("Lỗi kích hoạt huấn luyện!");
                }
            } catch (err) {
                console.error(err);
            } finally {
                btn.disabled = false;
                btn.innerText = "🚀 Huấn luyện Mô hình YOLOv8";
            }
        }

        // Lắng nghe phím tắt bàn phím
        document.addEventListener("keydown", function(e) {
            if (e.key === "Enter") {
                saveLabel();
            } else if (e.key === "r" || e.key === "R") {
                resetClicks();
            } else if (e.key === "s" || e.key === "S") {
                skipImage();
            }
        });

        // Khởi động load ảnh
        fetchImages();
    </script>
</body>
</html>
"""

class CaptchaLabelingHandler(BaseHTTPRequestHandler):
    """
    Xử lý các API Routing cho công cụ Web Gán nhãn.
    """
    def do_GET(self):
        # Router phục vụ trang chủ HTML
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
            return

        # API lấy danh sách ảnh
        elif self.path == "/api/images":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            unlabeled = []
            labeled_count = 0

            if os.path.exists(RAW_DIR):
                for f in os.listdir(RAW_DIR):
                    if f.lower().endswith((".png", ".jpg", ".jpeg")):
                        # Nếu ảnh chưa có tệp txt nhãn tương ứng => chưa gán nhãn
                        txt_file = os.path.splitext(f)[0] + ".txt"
                        if not os.path.exists(os.path.join(RAW_DIR, txt_file)):
                            unlabeled.append(f)
                        else:
                            labeled_count += 1
            
            # Sắp xếp để hiển thị ảnh mới nhất trước
            unlabeled.sort(reverse=True)

            response = {
                "unlabeled": unlabeled,
                "labeled_count": labeled_count
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return

        # Phục vụ file ảnh tĩnh từ thư mục dataset/raw_captchas/
        elif self.path.startswith("/images/"):
            filename = urllib.parse.unquote(self.path[8:])
            file_path = os.path.join(RAW_DIR, filename)

            if os.path.exists(file_path):
                self.send_response(200)
                # Đặt content-type tương ứng
                if filename.lower().endswith(".png"):
                    self.send_header("Content-Type", "image/png")
                else:
                    self.send_header("Content-Type", "image/jpeg")
                self.end_headers()

                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File Not Found")
            return

        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        # API lưu nhãn coordinates thành file YOLO txt
        if self.path == "/api/label":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode("utf-8"))

            filename = data["filename"]
            blue = data["blue"]
            green = data["green"]

            # Đọc kích thước ảnh để tính tọa độ chuẩn hóa YOLO
            img_path = os.path.join(RAW_DIR, filename)
            img = cv2.imread(img_path)
            if img is not None:
                h, w, _ = img.shape
                
                # YOLO format: class_id x_center y_center width height (Tất cả được chuẩn hóa về 0-1)
                # Giả định kích thước bounding box cho slider/target là 80x80 pixel
                box_w = 80.0 / w
                box_h = 80.0 / h

                # Class 0: blue_square
                bx_c = blue["x"] / w
                by_c = blue["y"] / h

                # Class 1: green_target
                gx_c = green["x"] / w
                gy_c = green["y"] / h

                txt_content = f"0 {bx_c:.6f} {by_c:.6f} {box_w:.6f} {box_h:.6f}\n"
                txt_content += f"1 {gx_c:.6f} {gy_c:.6f} {box_w:.6f} {box_h:.6f}\n"

                # Ghi đè file txt nhãn cùng thư mục với ảnh
                txt_filename = os.path.splitext(filename)[0] + ".txt"
                txt_path = os.path.join(RAW_DIR, txt_filename)
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(txt_content)

                print(f"[WEB-LABEL] Đã lưu nhãn thành công cho {filename}")
                self.send_response(200)
                self.end_headers()
            else:
                self.send_error(400, "Không thể đọc kích thước ảnh")
            return

        # API kích hoạt train YOLOv8
        elif self.path == "/api/train":
            print("\n🚀 [WEB-LABEL] Bắt đầu kích hoạt tiến trình huấn luyện 'train_yolo.py'...")
            
            # Khởi động train_yolo.py trong một tiến trình phụ không đồng bộ
            try:
                subprocess.Popen([sys.executable, "train_yolo.py"])
                self.send_response(200)
                self.end_headers()
            except Exception as e:
                print(f"❌ Lỗi kích hoạt tiến trình train: {e}")
                self.send_error(500, str(e))
            return

        else:
            self.send_error(404, "Not Found")

# Khởi chạy server
def run():
    # Đảm bảo tồn tại thư mục lưu ảnh trước khi chạy server
    os.makedirs(RAW_DIR, exist_ok=True)
    
    # Tự động quét và copy các ảnh mẫu captcha có sẵn trong thư mục gốc
    # để người dùng có thể bắt đầu gán nhãn chạy thử ngay lập tức!
    existing_samples = [
        "scrcpy_cropped_captcha2.png",
        "captcha_box.png",
        "crop1.png",
        "crop2.png",
        "test_screen.png",
        "current_screen.png"
    ]
    copied_count = 0
    for sample in existing_samples:
        if os.path.exists(sample):
            dest = os.path.join(RAW_DIR, sample)
            if not os.path.exists(dest):
                shutil.copy(sample, dest)
                copied_count += 1
    if copied_count > 0:
        print(f"[WEB-LABEL] Đã tự động copy {copied_count} ảnh mẫu có sẵn vào thư mục '{RAW_DIR}' để dán nhãn!")
    
    server_address = ("", PORT)
    # Cho phép tái sử dụng địa chỉ port để không bị kẹt cổng khi reload nhanh
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(server_address, CaptchaLabelingHandler) as httpd:
        print("=========================================================")
        print(f"🚀 AI CAPTCHA WEB DASHBOARD ĐANG CHẠY TẠI:")
        print(f"👉 http://localhost:{PORT}")
        print("=========================================================")
        print("💡 HƯỚNG DẪN:")
        print("  - Mở link trên bằng bất kỳ trình duyệt nào.")
        print("  - Click chọn tâm khối trượt, click chọn tâm vòng tròn đích.")
        print("  - Nhấn Enter để lưu và tự động chuyển ảnh tiếp theo.")
        print("  - Nhấn Ctrl+C ở terminal này để dừng Server.")
        print("=========================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nĐã dừng Server gán nhãn.")

if __name__ == "__main__":
    run()
