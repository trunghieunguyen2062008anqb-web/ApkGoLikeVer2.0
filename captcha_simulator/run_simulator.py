import http.server
import socketserver
import webbrowser
import threading
import time
import sys

PORT = 8000

class SilentHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Tắt bớt log request để console trông sạch sẽ hơn
        pass

def start_server():
    try:
        with socketserver.TCPServer(("", PORT), SilentHTTPRequestHandler) as httpd:
            print(f"[SUCCESS] Server giả lập đang chạy tại: http://localhost:{PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"[ERROR] Không thể chạy server tại cổng {PORT}: {e}")

if __name__ == "__main__":
    print("==================================================================")
    print("      GOLIKE CAPTCHA SIMULATOR SERVER (HTTP LOCALHOST)")
    print("==================================================================")
    
    # Chạy server ở chế độ daemon thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Đợi 1 giây cho server khởi động rồi tự động mở trình duyệt
    time.sleep(1.0)
    print(f"[INFO] Đang tự động mở trình duyệt tới địa chỉ http://localhost:{PORT}/captcha_simulator/ ...")
    webbrowser.open(f"http://localhost:{PORT}/captcha_simulator/")
    
    print("\n[INFO] Nhấn Ctrl + C để tắt Server giả lập.")
    print("------------------------------------------------------------------")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[INFO] Đã nhận lệnh ngắt. Đang dừng Server giả lập.")
        sys.exit(0)
