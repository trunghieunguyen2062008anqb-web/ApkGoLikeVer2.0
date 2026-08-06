import os
import sys
import time
import subprocess
import re
import cv2
import numpy as np
import random
import datetime

# Khởi tạo hỗ trợ màu ANSI trên Windows Terminal/PowerShell/CMD
if sys.platform.startswith('win'):
    os.system('') # Kích hoạt chế độ xử lý mã màu ANSI của Windows

# Lưu cấu hình print gốc
_original_print = print

# Định nghĩa các mã màu ANSI bằng ký tự Escape \x1b (Thêm cờ 1; để in đậm cực kỳ nổi bật)
COLOR_GREEN = "\x1b[1;92m"
COLOR_RED = "\x1b[1;91m"
COLOR_YELLOW = "\x1b[1;93m"
COLOR_BLUE = "\x1b[1;94m"
COLOR_CYAN = "\x1b[1;96m"
COLOR_MAGENTA = "\x1b[1;95m"
COLOR_RESET = "\x1b[0m"
COLOR_GRAY = "\x1b[1;90m"

# Ghi đè hàm print để hiển thị log ngắn gọn, tô màu rực rỡ toàn dòng
def print(*args, **kwargs):
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    prefix = f"{COLOR_GRAY}[{now_str}]{COLOR_RESET}"
    msg = " ".join(str(arg) for arg in args)
    
    color = ""
    # Xác định màu cho toàn bộ dòng chữ dựa vào nhãn
    if "[SUCCESS]" in msg:
        color = COLOR_GREEN
        msg = msg.replace("[SUCCESS]", "🏆 SUCCESS")
    elif "[ERROR]" in msg or "[CRITICAL]" in msg:
        color = COLOR_RED
        msg = msg.replace("[ERROR]", "🔴 ERROR").replace("[CRITICAL]", "🔥 CRITICAL")
    elif "[WARNING]" in msg:
        color = COLOR_YELLOW
        msg = msg.replace("[WARNING]", "🟡 WARNING")
    elif "[INFO]" in msg:
        color = COLOR_CYAN
        msg = msg.replace("[INFO]", "ℹ️ INFO")
    elif "[BƯỚC CAPTCHA]" in msg:
        color = COLOR_MAGENTA
        msg = msg.replace("[BƯỚC CAPTCHA]", "[CAPTCHA] 🧩")
    elif "[BƯỚC 1.5]" in msg:
        color = COLOR_BLUE
        msg = msg.replace("[BƯỚC 1.5]", "[BƯỚC 1.5] 🛡️ POPUP")
    elif "[BƯỚC 1]" in msg:
        color = COLOR_YELLOW
        msg = msg.replace("[BƯỚC 1]", "[BƯỚC 1] ⚡ JOB")
    elif "[BƯỚC 2]" in msg:
        color = COLOR_CYAN
        msg = msg.replace("[BƯỚC 2]", "[BƯỚC 2] 🎬 TIKTOK")
    elif "[BƯỚC 3]" in msg:
        color = COLOR_MAGENTA
        msg = msg.replace("[BƯỚC 3]", "[BƯỚC 3] 💖 ACTION")
    elif "[BƯỚC 4]" in msg:
        color = COLOR_GREEN
        msg = msg.replace("[BƯỚC 4]", "[BƯỚC 4] ✅ FINISH")
    elif "[BƯỚC 6]" in msg:
        color = COLOR_GREEN
        msg = msg.replace("[BƯỚC 6]", "[BƯỚC 6] 🆗 OK")
    elif "[BÁO LỖI]" in msg:
        color = COLOR_RED
        msg = msg.replace("[BÁO LỖI]", "[BÁO LỖI] ⚠️ REPORT")
        
    if color:
        formatted_msg = f"{prefix} {color}{msg}{COLOR_RESET}"
    else:
        formatted_msg = f"{prefix} {msg}"
        
    _original_print(formatted_msg, **kwargs)
    
    # Ghi log không màu ra file debug_run.log để theo dõi lâu dài
    try:
        with open("debug_run.log", "a", encoding="utf-8") as f:
            f.write(f"[{now_str}] {msg}\n")
    except:
        pass

# Đảm bảo console Windows hiển thị đúng tiếng Việt có dấu không bị lỗi font/crash
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass # Dự phòng cho các phiên bản Python cũ hơn 3.7

def sleep_countdown(duration, message="Đang chờ"):
    """
    Nghỉ (sleep) có đếm ngược từng giây in trên cùng một dòng trong console, hiển thị màu sắc sinh động.
    """
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    prefix = f"{COLOR_GRAY}[{now_str}]{COLOR_RESET}"
    
    # Định nghĩa màu sắc sặc sỡ thay đổi theo thời gian
    rainbow_colors = [COLOR_CYAN, COLOR_YELLOW, COLOR_GREEN, COLOR_BLUE, COLOR_MAGENTA]
    
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        remaining = duration - elapsed
        if remaining <= 0:
            break
        
        # Chọn màu sắc thay đổi động mỗi 0.5s
        color = rainbow_colors[int(remaining * 2) % len(rainbow_colors)]
        
        # In đè lên dòng cũ bằng \r
        sys.stdout.write(f"\r{prefix} {color}⏳ {message}... ({remaining:.1f}s còn lại){COLOR_RESET}")
        sys.stdout.flush()
        time.sleep(0.05)
        
    # Xóa sạch dòng đếm ngược khi hoàn thành
    sys.stdout.write(f"\r{prefix} {COLOR_GREEN}✓ {message} Hoàn tất!                                            {COLOR_RESET}\n")
    sys.stdout.flush()

# ==========================================
# CẤU HÌNH HỆ THỐNG
# ==========================================
# Thư mục lưu trữ các hình ảnh mẫu (template images)
TEMPLATES_DIR = "templates"

# Tên các file ảnh mẫu cần tìm kiếm và ngưỡng tương đồng (threshold)
TEMPLATES_CONFIG = {
    "nut_dong_quang_cao": {
        "filename": "nut_dong_quang_cao.png",
        "threshold": 0.8,
        "description": "Nút đóng quảng cáo"
    },
    "nut_tiep_tuc": {
        "filename": "nut_tiep_tuc.png",
        "threshold": 0.8,
        "description": "Nút tiếp tục"
    },
    "nut_nhan_job_ngay": {
        "filename": "nut_nhan_job_ngay.png",
        "threshold": 0.8,
        "description": "Nút nhận Job ngay"
    },
    "tab_danh_sach_cong_viec": {
        "filename": "tab_danh_sach_cong_viec.png",
        "threshold": 0.8,
        "description": "Tab Danh sách công việc"
    },
    "nut_dong_y": {
        "filename": "nut_dong_y.png",
        "threshold": 0.75,
        "description": "Nút Đồng ý"
    },
    "txt_da_hieu": {
        "filename": "txt_da_hieu.png",
        "threshold": 0.75,
        "description": "Checkbox Đã hiểu"
    },
    "header_chi_tiet": {
        "filename": "header_chi_tiet.png",
        "threshold": 0.70,
        "description": "Header Chi tiết"
    },
    "nut_tiktok": {
        "filename": "nut_tiktok.png",
        "threshold": 0.70,
        "description": "Nút mở TikTok"
    },
    "nut_hoan_thanh": {
        "filename": "nut_hoan_thanh.png",
        "threshold": 0.75,
        "description": "Nút Hoàn thành"
    },
    "nut_ok": {
        "filename": "nut_ok.png",
        "threshold": 0.70,
        "description": "Nút OK"
    },
    "icon_tim": {
        "filename": "icon_tim.png",
        "threshold": 0.75,
        "description": "Biểu tượng Tim trắng TikTok"
    },
    "job_like_indicator": {
        "filename": "job_like_indicator.png",
        "threshold": 0.65,
        "description": "Biểu tượng Tim đỏ của Job Tăng Like"
    },
    "nut_bao_loi": {
        "filename": "nut_bao_loi.png",
        "threshold": 0.70,
        "description": "Nút Báo lỗi"
    },
    "nut_gui_bao_cao": {
        "filename": "nut_gui_bao_cao.png",
        "threshold": 0.70,
        "description": "Nút Gửi báo cáo"
    },
    "txt_job_da_bi_xoa": {
        "filename": "txt_job_da_bi_xoa.png",
        "threshold": 0.75,
        "description": "Chữ thông báo Job đã bị xóa"
    },
    "icon_thanh_cong": {
        "filename": "icon_thanh_cong.png",
        "threshold": 0.6,
        "description": "Biểu tượng thành công màu xanh lá"
    }
}

# Thời gian nghỉ (giây) giữa các lần quét để tránh quá tải CPU
LOOP_INTERVAL = 1.0  # Quét mỗi 1 giây

# ==========================================
# LỚP ĐIỀU KHIỂN ADB (ANDROID DEBUG BRIDGE)
# ==========================================
class ADBController:
    def __init__(self, device_id=None):
        self.device_id = device_id
        self.tiktok_wait_count = 0 
        self.tiktok_clicked = False 
        self.need_report_error = False # Trạng thái cần báo lỗi cho job hiện tại
        self.waiting_for_job = False # Chờ mạng tải job
        self.job_request_time = 0 # Thời điểm bấm nhận job
        self.tiktok_action_done = False # Đánh dấu đã bấm Follow/Like thành công hay chưa
        
    def press_back(self):
        """
        Gửi lệnh nhấn phím Back (Quay lại) trên thiết bị.
        """
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['shell', 'input', 'keyevent', '4'])
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"[ERROR] Lỗi gửi phím Back: {e}")
            return False

    def bring_golike_to_foreground(self):
        """
        Đưa ứng dụng Golike lên màn hình chính (foreground) bằng lệnh monkey.
        """
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['shell', 'monkey', '-p', 'com.golike', '-c', 'android.intent.category.LAUNCHER', '1'])
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"[ERROR] Lỗi chuyển app Golike lên foreground: {e}")
            return False

    def check_connection(self):
        """
        Kiểm tra danh sách thiết bị Android đang kết nối thông qua ADB.
        """
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')
            devices = []
            
            # Dòng đầu tiên là tiêu đề "List of devices attached", bỏ qua dòng đó
            for line in lines[1:]:
                if line.strip():
                    parts = re.split(r'\s+', line.strip())
                    if len(parts) >= 2 and parts[1] == 'device':
                        devices.append(parts[0])
            
            return devices
        except FileNotFoundError:
            print("[ERROR] Không tìm thấy lệnh 'adb'.")
            return []
        except Exception as e:
            print(f"[ERROR] Lỗi kết nối ADB: {e}")
            return []

    def get_screenshot(self):
        """
        Chụp màn hình thiết bị Android trực tiếp vào bộ nhớ đệm (RAM) sử dụng exec-out.
        """
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['exec-out', 'screencap', '-p'])
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0 or not stdout:
                return None
            
            # Chuyển đổi dữ liệu byte thành mảng numpy và decode thành ảnh OpenCV
            image_array = np.frombuffer(stdout, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            return image
        except Exception as e:
            return None

    def tap(self, x, y):
        """
        Gửi lệnh click (tap) vào tọa độ (x, y) trên màn hình thiết bị.
        """
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['shell', 'input', 'tap', str(int(x)), str(int(y))])
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"[ERROR] Lỗi gửi lệnh click: {e}")
            return False

    def swipe(self, x1, y1, x2, y2, duration_ms=500):
        """
        Gửi lệnh vuốt (swipe) từ tọa độ (x1, y1) sang (x2, y2) trong khoảng thời gian duration_ms.
        """
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['shell', 'input', 'swipe', str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(int(duration_ms))])
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"[ERROR] Lỗi gửi lệnh vuốt: {e}")
            return False

    def execute_monkey_drag(self, path):
        """
        Tạo file Monkey Script từ danh sách tọa độ vuốt qua nhiều điểm,
        đẩy vào điện thoại và thực thi để giả lập kéo thả mượt mà/rung tay chậm rãi.
        """
        # Tính toán thời gian đợi giữa mỗi điểm để tổng thời gian kéo luôn xấp xỉ 3.5 giây (3500ms)
        n_points = len(path)
        wait_ms = max(10, min(100, int(3500 / n_points))) if n_points > 0 else 100
        
        script_lines = [
            "type= raw events",
            f"count= {len(path) * 2 + 5}",
            "speed= 1.0",
            "start data >>"
        ]
        
        # 1. DOWN event
        x0, y0 = path[0]
        script_lines.append(f"DispatchPointer(0, 0, 0, {x0}, {y0}, 1.0, 1.0, 0, 0.0, 0.0, 0, 0)")
        script_lines.append(f"UserWait({wait_ms})")
        
        # 2. MOVE events
        for x, y in path[1:-1]:
            script_lines.append(f"DispatchPointer(0, 0, 2, {x}, {y}, 1.0, 1.0, 0, 0.0, 0.0, 0, 0)")
            script_lines.append(f"UserWait({wait_ms})")
            
        # 3. UP event
        xn, yn = path[-1]
        script_lines.append(f"DispatchPointer(0, 0, 1, {xn}, {yn}, 1.0, 1.0, 0, 0.0, 0.0, 0, 0)")
        
        local_path = "temp_monkey_drag.txt"
        try:
            with open(local_path, "w") as f:
                f.write("\n".join(script_lines) + "\n")
                
            cmd_push = ['adb']
            if self.device_id:
                cmd_push.extend(['-s', self.device_id])
            cmd_push.extend(['push', local_path, '/data/local/tmp/monkey_drag.txt'])
            subprocess.run(cmd_push, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            cmd_run = ['adb']
            if self.device_id:
                cmd_run.extend(['-s', self.device_id])
            cmd_run.extend(['shell', 'monkey', '-f', '/data/local/tmp/monkey_drag.txt', '1'])
            subprocess.run(cmd_run, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"[ERROR] Lỗi kéo thả Monkey Script: {e}")
            return False
        finally:
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except:
                    pass


# ==========================================
# LỚP XỬ LÝ HÌNH ẢNH (OPENCV TEMPLATE MATCHING)
# ==========================================
class TemplateMatcher:
    def __init__(self, templates_dir, scale=1.0):
        self.templates_dir = templates_dir
        self.scale = scale
        self.loaded_templates = {}
        self.initialize_templates()

    def initialize_templates(self):
        """
        Tải trước các mẫu ảnh từ đĩa vào RAM để tối ưu hiệu suất.
        """
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            
        loaded_count = 0
        for name, config in TEMPLATES_CONFIG.items():
            path = os.path.join(self.templates_dir, config["filename"])
            if os.path.exists(path):
                img = cv2.imread(path, cv2.IMREAD_COLOR)
                if img is not None:
                    # Không scale ảnh mẫu icon_tim của TikTok nền dưới ở kịch bản 3 cửa sổ nổi
                    if self.scale != 1.0 and name not in ["icon_tim"]:
                        tw = int(img.shape[1] * self.scale)
                        th = int(img.shape[0] * self.scale)
                        img = cv2.resize(img, (tw, th), interpolation=cv2.INTER_CUBIC)
                    h, w, _ = img.shape
                    self.loaded_templates[name] = {
                        "image": img,
                        "w": w,
                        "h": h,
                        "threshold": config["threshold"],
                        "description": config["description"]
                    }
                    loaded_count += 1
            else:
                print(f"[WARNING] Thiếu ảnh mẫu: '{path}'. Chức năng tìm nút này sẽ bị bỏ qua.")
        print(f"[SUCCESS] Đã load thành công {loaded_count} ảnh mẫu từ thư mục '{self.templates_dir}'.")

    def find_match(self, screen_img, template_name):
        """
        Tìm kiếm vị trí của ảnh mẫu trong ảnh chụp màn hình bằng cv2.matchTemplate.
        """
        if template_name not in self.loaded_templates:
            return None
            
        template_data = self.loaded_templates[template_name]
        template_img = template_data["image"]
        threshold = template_data["threshold"]
        w = template_data["w"]
        h = template_data["h"]

        res = cv2.matchTemplate(screen_img, template_img, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        if max_val >= threshold:
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return center_x, center_y, max_val
            
        return None

    def get_match_score(self, screen_img, template_name):
        """
        Lấy điểm số matching score cao nhất của một ảnh mẫu mà không cần lọc theo threshold.
        """
        if template_name not in self.loaded_templates:
            return 0.0
        template_data = self.loaded_templates[template_name]
        template_img = template_data["image"]
        res = cv2.matchTemplate(screen_img, template_img, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        return float(max_val)


# ==========================================
# HÀM PHÁT HIỆN NÚT FOLLOW MÀU ĐỎ CỦA TIKTOK
# ==========================================
def find_tiktok_follow_button(screen_img, scenario=1):
    """
    Tìm kiếm nút Follow (hoặc Theo dõi) màu đỏ/hồng của TikTok.
    - Kịch bản 1 (chia đôi): Tìm ở nửa dưới (Y: 850 đến 1500) để tránh Golike ở trên.
    - Kịch bản 2 (toàn màn hình): Tìm ở nửa trên (Y: 200 đến 700) để tránh các video ghim ở dưới.
    - Kịch bản 3 (cửa sổ nổi): Tìm ở vùng nền trên (Y: 200 đến 450) để tránh cửa sổ nổi ở dưới.
    """
    try:
        height, width, _ = screen_img.shape
        if scenario == 1:
            y_min, y_max = 850, 1500
        elif scenario == 3:
            y_min, y_max = 200, 450
        else:
            y_min, y_max = 200, 700
        
        # Cắt vùng quét theo kịch bản
        zone = screen_img[y_min:y_max, :]
        hsv = cv2.cvtColor(zone, cv2.COLOR_BGR2HSV)
        
        # Dải màu rộng bao phủ từ đỏ tươi đến hồng đào/cam đào của TikTok
        lower_red1 = np.array([0, 80, 100])
        upper_red1 = np.array([25, 255, 255])
        lower_red2 = np.array([165, 80, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        best_match = None
        max_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            # Nút Follow có diện tích trung bình > 500 pixel
            if area > 500:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                # Tỷ lệ dài/rộng của nút Follow nằm trong khoảng 1.5 đến 8.0
                if 1.5 < aspect_ratio < 8.0:
                    center_x = x + w // 2
                    # Lọc bỏ Avatar hoặc các nút bên phải bằng tọa độ X (Nút Follow luôn nằm ở phía bên trái/giữa, X < 500)
                    if center_x > 500:
                        continue
                    if area > max_area:
                        max_area = area
                        center_y = y_min + y + h // 2
                        best_match = (center_x, center_y, area)
                        
        return best_match
    except Exception as e:
        return None


# ==========================================
# HÀM THỰC HIỆN TƯƠNG TÁC TIKTOK (FOLLOW / THẢ TIM)
# ==========================================
def perform_tiktok_action(fresh_screen, adb, matcher, is_like_job, scenario):
    """
    Tìm và thực hiện bấm Follow hoặc thả Tim trên màn hình TikTok.
    """
    if is_like_job:
        # Ưu tiên tìm và bấm trực tiếp vào biểu tượng Tim trắng của TikTok trước
        match_tim = matcher.find_match(fresh_screen, "icon_tim")
        if match_tim:
            tx_tim, ty_tim, score_tim = match_tim
            print(f"[BƯỚC 3] ❤️ Bấm Tim TikTok tại ({tx_tim}, {ty_tim})")
            save_debug_image(fresh_screen, tx_tim, ty_tim, "Click Heart")
            adb.tap(tx_tim, ty_tim)
            adb.tiktok_action_done = True
            sleep_countdown(3.0, "Chờ thả tim TikTok thành công")
        else:
            if scenario == 3:
                # Cửa sổ nổi: Dự phòng double-click vào video ở nền trên nếu không khớp được Tim trắng
                print("[BƯỚC 3] ❤️ [CỬA SỔ NỔI] Không tìm thấy tim trắng. Thử Double-click video tại (360, 300)...")
                adb.tap(360, 300)
                time.sleep(0.1)
                adb.tap(360, 300)
                adb.tiktok_action_done = True
                sleep_countdown(3.0, "Chờ thả tim TikTok thành công")
            else:
                print("[BƯỚC 3] ⚠️ Không tìm thấy biểu tượng Tim trắng TikTok để bấm.")
    else:
        follow_btn = find_tiktok_follow_button(fresh_screen, scenario)
        if follow_btn:
            fx, fy, area = follow_btn
            print(f"[BƯỚC 3] 💖 ACTION 🎬 Bấm Follow TikTok tại ({fx}, {fy})")
            save_debug_image(fresh_screen, fx, fy, "Click Follow")
            adb.tap(fx, fy)
            adb.tiktok_action_done = True
            sleep_countdown(3.0, "Chờ follow TikTok thành công")
        else:
            print("[BƯỚC 3] ⚠️ Không tìm thấy nút Follow TikTok màu đỏ để bấm.")


# ==========================================
# HÀM LƯU HÌNH ẢNH DEBUG CLICK
# ==========================================
def save_debug_image(screen, x, y, label):
    """
    Vẽ một vòng tròn đỏ tại tọa độ click và nhãn mô tả, lưu lại thành file debug_last_click.png
    """
    try:
        debug_img = screen.copy()
        cv2.circle(debug_img, (int(x), int(y)), 25, (0, 0, 255), 3)
        cv2.circle(debug_img, (int(x), int(y)), 4, (0, 0, 255), -1)
        cv2.putText(debug_img, label, (int(x) + 35, int(y) + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.imwrite('debug_last_click.png', debug_img)
    except Exception as e:
        pass


# ==========================================
# HÀM SINH QUỸ ĐẠO KÉO GESTURE RUNG TAY
# ==========================================
def generate_human_captcha_path(P0, P_check, P2, steps=40, jitter_std=2.0):
    """
    Tạo ra một danh sách tọa độ vuốt (X, Y) đi từ P0 qua P_check tới P2,
    áp dụng hiệu ứng giảm tốc/tăng tốc (easing) và độ rung cơ tay sinh học (jitter/tremor).
    """
    P1 = (2 * P_check[0] - 0.5 * P0[0] - 0.5 * P2[0],
          2 * P_check[1] - 0.5 * P0[1] - 0.5 * P2[1])
    
    path = []
    
    raw_noise_x = [np.random.normal(0, jitter_std) for _ in range(steps + 1)]
    raw_noise_y = [np.random.normal(0, jitter_std) for _ in range(steps + 1)]
    
    smooth_noise_x = []
    smooth_noise_y = []
    window = 3
    for i in range(steps + 1):
        start_idx = max(0, i - window)
        end_idx = min(steps, i + window) + 1
        smooth_noise_x.append(float(np.mean(raw_noise_x[start_idx:end_idx])))
        smooth_noise_y.append(float(np.mean(raw_noise_y[start_idx:end_idx])))
        
    for i in range(steps + 1):
        alpha = i / steps
        t = 3 * (alpha ** 2) - 2 * (alpha ** 3)
        
        bx = (1 - t)**2 * P0[0] + 2 * (1 - t) * t * P1[0] + t**2 * P2[0]
        by = (1 - t)**2 * P0[1] + 2 * (1 - t) * t * P1[1] + t**2 * P2[1]
        
        scale = np.sin(t * np.pi)
        jx = bx + smooth_noise_x[i] * scale * 10.0 
        jy = by + smooth_noise_y[i] * scale * 10.0
        
        path.append((int(jx), int(jy)))
        
    return path


# ==========================================
# HÀM NẮN QUỸ ĐẠO HỌC TẬP TỪ FILE GIẢI TAY CỦA SẾP
# ==========================================
def generate_human_morphed_path(P0, P_check, P2):
    """
    Đọc ngẫu nhiên 1 trong các file tọa độ xuất từ Simulator giải tay của sếp,
    sau đó nắn dòng (morph/scale) để khớp chính xác với Start (P0), Checkpoint (P_check) và End (P2).
    """
    import os
    import json
    import random
    
    try:
        # Tìm danh sách các file xuất quỹ đạo
        trajectory_files = [f for f in os.listdir('.') if f.startswith('captcha_trajectory') and f.endswith('.json')]
        if not trajectory_files:
            return None
            
        # Chọn ngẫu nhiên 1 file
        chosen_file = random.choice(trajectory_files)
        with open(chosen_file, 'r', encoding='utf-8') as f:
            human_path = json.load(f)
            
        if not human_path or len(human_path) < 10:
            return None
            
        # Tìm các điểm mốc trong đường đi của con người
        start_h = human_path[0]
        end_h = human_path[-1]
        
        # Điểm checkpoint là điểm có Y nhỏ nhất (cao nhất trên màn hình)
        check_idx = 0
        min_y = float('inf')
        for idx, pt in enumerate(human_path):
            if pt['y'] < min_y:
                min_y = pt['y']
                check_idx = idx
        check_h = human_path[check_idx]
        
        # Trích xuất tọa độ
        sx_h, sy_h = start_h['x'], start_h['y']
        cx_h, cy_h = check_h['x'], check_h['y']
        ex_h, ey_h = end_h['x'], end_h['y']
        
        # Tính khoảng cách để scale
        dx1_h = cx_h - sx_h
        dy1_h = cy_h - sy_h
        dx2_h = ex_h - cx_h
        dy2_h = ey_h - cy_h
        
        # Bảo vệ chia cho 0
        dx1_h = dx1_h if abs(dx1_h) > 1 else 1
        dy1_h = dy1_h if abs(dy1_h) > 1 else 1
        dx2_h = dx2_h if abs(dx2_h) > 1 else 1
        dy2_h = dy2_h if abs(dy2_h) > 1 else 1
        
        # Khoảng cách mục tiêu
        dx1_t = P_check[0] - P0[0]
        dy1_t = P_check[1] - P0[1]
        dx2_t = P2[0] - P_check[0]
        dy2_t = P2[1] - P_check[1]
        
        morphed_path = []
        n = len(human_path)
        
        for i in range(n):
            pt = human_path[i]
            px, py = pt['x'], pt['y']
            
            if i <= check_idx:
                # Phân đoạn 1: Đi từ Start đến Checkpoint
                mx = P0[0] + (px - sx_h) * (dx1_t / dx1_h)
                my = P0[1] + (py - sy_h) * (dy1_t / dy1_h)
            else:
                # Phân đoạn 2: Đi từ Checkpoint đến End
                mx = P_check[0] + (px - cx_h) * (dx2_t / dx2_h)
                my = P_check[1] + (py - cy_h) * (dy2_t / dy2_h)
                
            morphed_path.append((int(mx), int(my)))
            
        # Bảo đảm khớp chính xác điểm đầu, checkpoint và cuối
        morphed_path[0] = (int(P0[0]), int(P0[1]))
        morphed_path[check_idx] = (int(P_check[0]), int(P_check[1]))
        morphed_path[-1] = (int(P2[0]), int(P2[1]))
        
        return morphed_path
        
    except Exception as e:
        print(f"[ERROR] Lỗi nắn dòng quỹ đạo: {e}")
        return None


# ==========================================
# THUẬT TOÁN TỰ ĐỘNG GIẢI CAPTCHA XÁC MINH NHANH
# ==========================================
def handle_captcha_if_present(screen, adb, scenario=1):
    """
    Kiểm tra và tự động giải quyết Captcha Xác minh nhanh.
    """
    try:
        # Kiểm tra tiêu đề "Xác minh nhanh" để đảm bảo thực sự có captcha popup trước khi quét màu
        temp_title = cv2.imread('templates/captcha_title.png')
        tx, ty = 0, 0
        if temp_title is not None:
            scale_val = 1.867 if scenario == 3 else 2.667
            tw = int(temp_title.shape[1] * scale_val)
            th = int(temp_title.shape[0] * scale_val)
            temp_scaled = cv2.resize(temp_title, (tw, th), interpolation=cv2.INTER_CUBIC)
            
            # Quét trên toàn màn hình để tìm vị trí thực tế của tiêu đề
            res_title = cv2.matchTemplate(screen, temp_scaled, cv2.TM_CCOEFF_NORMED)
            _, score_title, _, loc_title = cv2.minMaxLoc(res_title)
            if score_title < 0.60:
                # Không tìm thấy tiêu đề "Xác minh nhanh" => Chắc chắn không có captcha!
                return False
            tx, ty = loc_title
                
        hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
        height, width, _ = screen.shape
        
        # Thiết lập dải quét tùy theo kịch bản chạy (Kịch bản 1: Chia đôi màn hình, Kịch bản 2: Toàn màn hình, Kịch bản 3: Cửa sổ nổi)
        if scenario == 1:
            x_min, x_max = 36, 684
            y_min, y_max = 300, 800
            y_min_gray = 360
            area_thresh = 250
        elif scenario == 3:
            # Cửa sổ nổi: Tính toán tọa độ quét động dựa trên vị trí tìm thấy của tiêu đề Captcha
            x_min = max(0, tx - 100)
            x_max = min(width, tx + 550)
            y_min = max(0, ty + 300)
            y_max = min(height, ty + 950)
            y_min_gray = y_min
            area_thresh = 120
        else: # scenario == 2
            x_min, x_max = 36, 684
            y_min, y_max = 300, 1300
            y_min_gray = 360
            area_thresh = 250
        
        # 1. Dò tìm khối vuông màu xanh lam (Blue Square)
        lower_blue = np.array([100, 150, 150])
        upper_blue = np.array([125, 255, 255])
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        mask_blue[:y_min, :] = 0
        mask_blue[y_max:, :] = 0
        mask_blue[:, :x_min] = 0
        mask_blue[:, x_max:] = 0
        
        contours_blue, _ = cv2.findContours(mask_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # Sắp xếp các contour từ trái qua phải để luôn ưu tiên tìm khối trượt xanh lam trước (nút này luôn nằm bên trái nhất)
        contours_blue = sorted(contours_blue, key=lambda c: cv2.boundingRect(c)[0] + cv2.boundingRect(c)[2]//2)
        blue_center = None
        for c in contours_blue:
            area = cv2.contourArea(c)
            if area > (80 if scenario == 3 else 200):
                x, y, bw, bh = cv2.boundingRect(c)
                blue_center = (x + bw//2, y + bh//2)
                break
                
        # 2. Dò tìm vòng tròn đích màu xanh lá (Green Target)
        lower_green = np.array([45, 80, 80])
        upper_green = np.array([75, 255, 255])
        mask_green = cv2.inRange(hsv, lower_green, upper_green)
        mask_green[:y_min, :] = 0
        mask_green[y_max:, :] = 0
        mask_green[:, :x_min] = 0
        mask_green[:, x_max:] = 0
        
        contours_green, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # Sắp xếp các contour từ phải qua trái để luôn ưu tiên tìm vòng tròn đích xanh lá trước (nút này luôn nằm bên phải nhất)
        contours_green = sorted(contours_green, key=lambda c: cv2.boundingRect(c)[0] + cv2.boundingRect(c)[2]//2, reverse=True)
        green_center = None
        for c in contours_green:
            area = cv2.contourArea(c)
            if area > 40:
                x, y, gw, gh = cv2.boundingRect(c)
                aspect = float(gw)/gh if gh > 0 else 0
                if 0.5 < aspect < 2.0:
                    green_center = (x + gw//2, y + gh//2)
                    break
                    
        # Nếu tìm thấy cả khối vuông xanh lam và đích xanh lá => Có Captcha!
        if not (blue_center and green_center):
            if temp_title is not None:
                print(f"[CAPTCHA] ⚠️ Không đủ điều kiện giải tự động (Blue={blue_center}, Green={green_center}).")
                print("[CAPTCHA] 👆 Vui lòng tự tay giải Captcha này trên màn hình. Tool sẽ tự động chạy tiếp khi sếp giải xong...")
                
                # Vòng lặp chờ sếp giải tay
                while True:
                    time.sleep(2.0)
                    fresh_screen = adb.get_screenshot()
                    if fresh_screen is None:
                        continue
                    res_title_check = cv2.matchTemplate(fresh_screen, temp_scaled, cv2.TM_CCOEFF_NORMED)
                    _, score_title_check, _, _ = cv2.minMaxLoc(res_title_check)
                    if score_title_check < 0.60:
                        print("[CAPTCHA] ✅ Đã giải xong Captcha! Tiếp tục cày...")
                        break
            return True
                
        if blue_center and green_center:
            print("[BƯỚC CAPTCHA] 🧩 Phát hiện màn hình giải Captcha...")
            
            # 3. Dò tìm vòng tròn nét đứt (Dashed Checkpoint)
            gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
            mask_gray = (gray < 225) & (gray > 120)
            mask_gray[:y_min_gray, :] = 0  
            mask_gray[y_max:, :] = 0  
            mask_gray[:, :x_min] = 0   
            mask_gray[:, x_max:] = 0  
            
            # Điều chỉnh kích thước bộ lọc theo kịch bản
            cw_min, cw_max = (4, 25) if scenario == 3 else (6, 35)
            exclude_dist = 25 if scenario == 3 else 35
            r_min, r_max = (35, 60) if scenario == 3 else (50, 85)
            
            contours_all, _ = cv2.findContours(mask_gray.astype(np.uint8)*255, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            dash_centers = []
            for c in contours_all:
                x, y, cw, ch = cv2.boundingRect(c)
                if cw_min <= cw <= cw_max and cw_min <= ch <= cw_max:
                    cx = x + cw/2
                    cy = y + ch/2
                    if abs(cx - blue_center[0]) < exclude_dist and abs(cy - blue_center[1]) < exclude_dist:
                        continue
                    if abs(cx - green_center[0]) < exclude_dist and abs(cy - green_center[1]) < exclude_dist:
                        continue
                    dash_centers.append((cx, cy))
                    
            dashed_center = None
            if len(dash_centers) >= 5:
                best_center = None
                max_inliers = 0
                
                pts = np.array(dash_centers)
                for _ in range(500):
                    idx = random.sample(range(len(pts)), 3)
                    p1, p2, p3 = pts[idx[0]], pts[idx[1]], pts[idx[2]]
                    
                    d = 2 * (p1[0]*(p2[1] - p3[1]) + p2[0]*(p3[1] - p1[1]) + p3[0]*(p1[1] - p2[1]))
                    if abs(d) < 1e-5:
                        continue
                    ux = ((p1[0]**2 + p1[1]**2)*(p2[1] - p3[1]) + (p2[0]**2 + p2[1]**2)*(p3[1] - p1[1]) + (p3[0]**2 + p3[1]**2)*(p1[1] - p2[1])) / d
                    uy = ((p1[0]**2 + p1[1]**2)*(p3[0] - p2[0]) + (p2[0]**2 + p2[1]**2)*(p1[0] - p3[0]) + (p3[0]**2 + p3[1]**2)*(p2[0] - p1[0])) / d
                    r = np.sqrt((p1[0] - ux)**2 + (p1[1] - uy)**2)
                    
                    if r_min <= r <= r_max:
                        dists = np.sqrt((pts[:, 0] - ux)**2 + (pts[:, 1] - uy)**2)
                        inliers = np.sum(abs(dists - r) < 8.0)
                        if inliers > max_inliers:
                            max_inliers = inliers
                            best_center = (int(ux), int(uy))
                            
                if best_center:
                    dashed_center = best_center
                    
            if not dashed_center:
                if scenario == 3:
                    # Cửa sổ nổi: Không dùng tọa độ dự phòng để tránh tuyệt đối click ảo khi không có captcha thực tế
                    return False
                else:
                    fallback_x = int((blue_center[0] + green_center[0]) / 2)
                    fallback_y = int(min(blue_center[1], green_center[1]) - 100)
                    dashed_center = (fallback_x, fallback_y)
                
            # 4. Sinh quỹ đạo kéo mượt có Rung tay sinh học 4.0s (Nắn chỉnh từ file giải tay thật của sếp)
            path = generate_human_morphed_path(blue_center, dashed_center, green_center)
            if not path:
                # Dự phòng thuật toán Bezier nếu không load được file
                path = generate_human_captcha_path(blue_center, dashed_center, green_center, steps=40)
            
            # Vẽ ảnh debug
            debug_img = screen.copy()
            for i in range(len(path) - 1):
                cv2.line(debug_img, path[i], path[i+1], (0, 0, 255), 3)
            cv2.circle(debug_img, blue_center, 25, (255, 0, 0), 2)
            cv2.circle(debug_img, dashed_center, 35, (0, 255, 255), 2)
            cv2.circle(debug_img, green_center, 30, (0, 255, 0), 2)
            cv2.imwrite('debug_captcha_solve.png', debug_img)
            
            # 5. Thực thi kéo thả bằng Monkey Script
            print("[BƯỚC CAPTCHA] Đang thực thi giải captcha bằng Rung tay (4.0 giây)...")
            success = adb.execute_monkey_drag(path)
            if success:
                sleep_countdown(3.0, "Đang chờ popup xác nhận sau giải Captcha")
            return True
            
    except Exception as e:
        pass
        
    return False


# ==========================================
# HÀM KHỞI CHẠY CHÍNH (MAIN STATE MACHINE)
# ==========================================
def main():
    print("==================================================================")
    print("        AUTO GOLIKE TIKTOK - PHIÊN BẢN CỬA SỔ NỔI (FLOATING WINDOW)")
    print("==================================================================")
    
    adb = ADBController()
    completed_jobs = 0
    scenario = 3
    completed_jobs = 0
    
    print("\n" + "="*80)
    print("📢 HƯỚNG DẪN CHẠY:")
    print("Hãy mở Golike ở dạng Cửa sổ nổi (Floating Window) đè lên màn hình TikTok.")
    print("Tool sẽ tự động nhận job, click TikTok, follow/like và hoàn thành siêu tốc.")
    print("="*80 + "\n")
    print(f"[INFO] Bắt đầu đếm từ: {completed_jobs} job.")
    
    devices = adb.check_connection()
    if not devices:
        print("[CRITICAL] Không tìm thấy thiết bị Android đang kết nối.")
        sys.exit(1)
        
    print(f"[INFO] Kết nối thành công tới thiết bị: {devices[0]}")
    adb.device_id = devices[0]
    
    scale = 0.70 if scenario == 3 else 1.0
    matcher = TemplateMatcher(TEMPLATES_DIR, scale=scale)
    
    if not matcher.loaded_templates:
        print("\n[WARNING] Không có ảnh mẫu nào được tải thành công.")
        sys.exit(1)

    print("\n[INFO] Khởi động auto clicker... Nhấn Ctrl + C để dừng.")
    print("------------------------------------------------------------------")

    try:
        while True:
            start_time = time.time()
            
            screen = adb.get_screenshot()
            if screen is None:
                time.sleep(2)
                continue
                
            # --- KIỂM TRA CHỜ ĐỢI TẢI JOB (MẠNG CHẬM) ---
            if adb.waiting_for_job:
                # Quét và tính điểm số khớp thực tế của các giao diện đích
                score_details = matcher.get_match_score(screen, "header_chi_tiet")
                score_popup = matcher.get_match_score(screen, "nut_dong_y")
                score_ok = matcher.get_match_score(screen, "nut_ok")
                
                # Trích xuất config thresholds để so sánh
                thresh_details = TEMPLATES_CONFIG["header_chi_tiet"]["threshold"]
                thresh_popup = TEMPLATES_CONFIG["nut_dong_y"]["threshold"]
                thresh_ok = TEMPLATES_CONFIG["nut_ok"]["threshold"]
                
                has_details = score_details >= thresh_details
                has_popup = score_popup >= thresh_popup
                has_ok = score_ok >= thresh_ok
                
                # Kiểm tra xem Captcha có xuất hiện trong lúc chờ không
                is_captcha = False
                temp_title = cv2.imread('templates/captcha_title.png')
                if temp_title is not None:
                    scale_val = 1.867 if scenario == 3 else 2.667
                    tw = int(temp_title.shape[1] * scale_val)
                    th = int(temp_title.shape[0] * scale_val)
                    temp_scaled = cv2.resize(temp_title, (tw, th), interpolation=cv2.INTER_CUBIC)
                    
                    # Quét trên toàn màn hình để tránh phụ thuộc vị trí cửa sổ nổi
                    res_title = cv2.matchTemplate(screen, temp_scaled, cv2.TM_CCOEFF_NORMED)
                    _, score_title, _, _ = cv2.minMaxLoc(res_title)
                    if score_title >= 0.60:
                        is_captcha = True
                
                if has_details or has_popup or has_ok or is_captcha:
                    adb.waiting_for_job = False
                    if is_captcha:
                        print("[INFO] 🧩 Phát hiện Captcha xuất hiện trong lúc chờ tải Job! Tiến hành giải...")
                    else:
                        print("[INFO] Đã nhận diện được giao diện mới. Kết thúc chế độ chờ.")
                else:
                    if time.time() - adb.job_request_time > 4.0:
                        adb.waiting_for_job = False
                        print("[WARNING] Hết thời gian chờ tải Job (4s). Tiếp tục quét màn hình...")
                    else:
                        print(f"⏳ Đang chờ trang Chi tiết hoặc Popup load... (Scores: Chi tiết={score_details:.2f}/{thresh_details}, Đồng ý={score_popup:.2f}/{thresh_popup}, OK={score_ok:.2f}/{thresh_ok})")
                        time.sleep(1.0)
                        continue
                        
            action_taken = False
            
            # --- BƯỚC 6: OK POPUP (THÀNH CÔNG / LỖI) ---
            if not action_taken:
                match_ok = matcher.find_match(screen, "nut_ok")
                if match_ok:
                    cx, cy, score = match_ok
                    save_debug_image(screen, cx, cy, "Click OK")
                    adb.tap(cx, cy)
                    action_taken = True
                    
                    # Kiểm tra xem có phải popup thông báo "Job đã bị xóa / quá hạn" hay không
                    match_xoa = matcher.find_match(screen, "txt_job_da_bi_xoa")
                    if match_xoa:
                        print("[WARNING] Phát hiện Job đã bị xóa hoặc quá hạn làm việc! Sẽ tự động báo lỗi...")
                        adb.need_report_error = True
                    
                    if not adb.need_report_error:
                        # Kiểm tra xem có tìm thấy biểu tượng Thành công màu xanh lá trên màn hình không
                        match_success = matcher.find_match(screen, "icon_thanh_cong")
                        
                        # Fallback: Kiểm tra màu xanh lá phía trên nút OK để đề phòng lệch ảnh mẫu
                        height, width, _ = screen.shape
                        scale_val = 0.70 if scenario == 3 else 1.0
                        y1 = max(0, int(cy - 370 * scale_val))
                        y2 = min(height, int(cy - 180 * scale_val))
                        x1 = max(0, int(cx - 90 * scale_val))
                        x2 = min(width, int(cx + 90 * scale_val))
                        crop = screen[y1:y2, x1:x2]
                        hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                        green_mask = cv2.inRange(hsv_crop, np.array([35, 20, 50]), np.array([85, 255, 255]))
                        green_pixels = cv2.countNonZero(green_mask)
                        
                        if match_success or (green_pixels > 30):
                            completed_jobs += 1
                            print(f"[SUCCESS] 🎉 BÁO CÁO THÀNH CÔNG! Hôm nay sếp đã hoàn thành {completed_jobs}/300 job! 🚀🔥")
                            print("--------------------------------------")
                            
                            # Cứ mỗi 10 job hoàn thành thành công thì nghỉ ngơi 1 phút (60 giây) tránh lag máy
                            if completed_jobs > 0 and completed_jobs % 10 == 0:
                                print(f"\n[INFO] ☕ Đã cày liên tục {completed_jobs} job. Nghỉ ngơi 1 phút (60s) để tránh nóng máy và giảm lag...")
                                sleep_countdown(60.0, "Nghỉ ngơi phục hồi thiết bị")
                        else:
                            print("[WARNING] Hệ thống báo Lỗi hoặc cảnh báo chưa thực hiện thao tác! Sẽ tiến hành báo lỗi...")
                            adb.need_report_error = True
                    
                    adb.tiktok_wait_count = 0
                    adb.tiktok_clicked = False 
                    sleep_countdown(3.0, "Đang quay lại trang nhận Job mới")
                    
                    # Kiểm tra xem có còn ở trang Chi tiết không để tự động back về trang nhận Job
                    fresh_screen = adb.get_screenshot()
                    if fresh_screen is not None:
                        if matcher.find_match(fresh_screen, "header_chi_tiet"):
                            print("[BƯỚC 6] 🔙 Vẫn ở trang Chi tiết. Nhấn Back để quay lại trang nhận Job...")
                            if scenario == 3:
                                adb.tap(50, 490) # Nhấn nút back < ở góc trên bên trái của cửa sổ nổi
                            else:
                                adb.press_back()
                            time.sleep(1.0) 

            # --- BƯỚC BÁO LỖI TỰ ĐỘNG (JOB QUÁ HẠN / ĐÃ XÓA) ---
            if not action_taken and adb.need_report_error:
                # Khởi tạo thuộc tính đếm số lần cuộn nếu chưa có
                if not hasattr(adb, "report_swipe_count"):
                    adb.report_swipe_count = 0
                    
                if adb.report_swipe_count > 3:
                    print("[BÁO LỖI] ⚠️ Đã cuộn tìm quá 3 lần không thấy nút Báo lỗi/Gửi báo cáo. Hủy chế độ báo lỗi.")
                    adb.need_report_error = False
                    adb.report_swipe_count = 0
                else:
                    # 1. Kiểm tra nếu tìm thấy nút "Gửi báo cáo" (đang ở trang báo lỗi)
                    match_gui_bc = matcher.find_match(screen, "nut_gui_bao_cao")
                    if match_gui_bc:
                        gx, gy, score = match_gui_bc
                        print(f"[BÁO LỖI] ✅ Click nút Gửi báo cáo tại ({gx}, {gy})")
                        save_debug_image(screen, gx, gy, "Gui Bao Cao")
                        adb.tap(gx, gy)
                        print("--------------------------------------")
                        adb.need_report_error = False
                        adb.report_swipe_count = 0
                        action_taken = True
                        time.sleep(1.5)
                    else:
                        # 2. Kiểm tra nếu tìm thấy nút "Báo lỗi" (đang ở trang chi tiết công việc)
                        match_bao_loi = matcher.find_match(screen, "nut_bao_loi")
                        if match_bao_loi:
                            bx, by, score = match_bao_loi
                            print(f"[BÁO LỖI] 🛠️ Click nút Báo lỗi tại ({bx}, {by})")
                            save_debug_image(screen, bx, by, "Bao Loi")
                            adb.tap(bx, by)
                            adb.report_swipe_count = 0
                            action_taken = True
                            time.sleep(1.5)
                        else:
                            # 3. Chưa thấy nút Báo lỗi hay Gửi báo cáo -> Cuộn màn hình để tìm
                            # Kiểm tra xem có đang ở trang Chi tiết (có header_chi_tiet) không
                            match_header = matcher.find_match(screen, "header_chi_tiet")
                            if match_header:
                                print("[BÁO LỖI] Chưa thấy nút Báo lỗi. Vuốt lên để tìm...")
                                adb.swipe(360, 600, 360, 400, duration_ms=400)
                            else:
                                print("[BÁO LỖI] Đang ở trang báo lỗi/Trang chủ. Chưa thấy nút Gửi báo cáo. Vuốt lên để tìm...")
                                adb.swipe(360, 600, 360, 400, duration_ms=400)
                            adb.report_swipe_count += 1
                            action_taken = True
                            time.sleep(0.8)
            
            # --- BƯỚC 1.5: POPUP CẢNH BÁO (ĐỒNG Ý LÀM BẰNG APP) ---
            if not action_taken:
                match_dong_y = matcher.find_match(screen, "nut_dong_y")
                if match_dong_y:
                    dy_x, dy_y, dy_score = match_dong_y
                    print("[BƯỚC 1.5] Phát hiện popup. Đang đồng ý...")
                    
                    # Tìm checkbox 'Đã hiểu' bằng Template Matching để tương thích mọi thiết bị
                    match_da_hieu = matcher.find_match(screen, "txt_da_hieu")
                    if match_da_hieu:
                        dh_x, dh_y, dh_score = match_da_hieu
                        print(f"[BƯỚC 1.5] 🆗 Tìm thấy checkbox 'Đã hiểu' tại ({dh_x}, {dh_y})")
                        save_debug_image(screen, dh_x, dh_y, "Tick Da Hieu")
                        adb.tap(dh_x, dh_y)
                    else:
                        # Fallback tính toán tọa độ động nếu không khớp ảnh mẫu
                        cb_x, cb_y = int(dy_x - 367), int(dy_y - 147)
                        print(f"[BƯỚC 1.5] ⚠️ Tự động tính tọa độ Checkbox tại ({cb_x}, {cb_y})")
                        save_debug_image(screen, cb_x, cb_y, "Tick Da Hieu Fallback")
                        adb.tap(cb_x, cb_y)
                        
                    time.sleep(0.8) 
                    
                    fresh_screen = adb.get_screenshot()
                    if fresh_screen is not None:
                        save_debug_image(fresh_screen, dy_x, dy_y, "Bam Dong Y")
                    adb.tap(dy_x, dy_y)
                    action_taken = True
                    time.sleep(1.5)

            # --- BƯỚC CAPTCHA: VƯỢT CAPTCHA XÁC MINH NHANH ---
            # Chỉ chạy khi chưa mở TikTok, không ở màn hình chính nhận Job, và không ở trang Chi tiết (tránh nhận diện nhầm)
            if not action_taken and not adb.tiktok_clicked:
                if not matcher.find_match(screen, "nut_nhan_job_ngay") and not matcher.find_match(screen, "header_chi_tiet"):
                    action_taken = handle_captcha_if_present(screen, adb, scenario)

            # --- BƯỚC ĐÓNG QUẢNG CÁO ---
            if not action_taken:
                match_close = matcher.find_match(screen, "nut_dong_quang_cao")
                if match_close:
                    cx, cy, score = match_close
                    print(f"❌ Đóng quảng cáo tại ({cx}, {cy})")
                    save_debug_image(screen, cx, cy, "Dong Quang Cao")
                    adb.tap(cx, cy)
                    action_taken = True
                    time.sleep(1.0)
                
                if not action_taken:
                    match_continue = matcher.find_match(screen, "nut_tiep_tuc")
                    if match_continue:
                        cx, cy, score = match_continue
                        print(f"❌ Click tiếp tục tại ({cx}, {cy})")
                        save_debug_image(screen, cx, cy, "Tiep Tuc")
                        adb.tap(cx, cy)
                        action_taken = True
                        time.sleep(1.0)

            # --- BƯỚC 2, 3, 4: CHI TIẾT CÔNG VIỆC ---
            if not action_taken:
                match_header_ct = matcher.find_match(screen, "header_chi_tiet")
                if match_header_ct:
                    # Xác định vùng quét loại Job (Like/Follow) để tránh nhận diện nhầm vào nền video TikTok
                    if scenario == 1:
                        zone_job = screen[100:400, :]
                    elif scenario == 3:
                        zone_job = screen[500:750, 32:688]
                    else: # scenario == 2
                        zone_job = screen[150:450, :]
                    is_like_job = matcher.find_match(zone_job, "job_like_indicator") is not None
                    
                    # 1. Kiểm tra nút Hoàn thành (Chỉ click được nếu đã mở TikTok trước)
                    match_hoan_thanh = matcher.find_match(screen, "nut_hoan_thanh")
                    if match_hoan_thanh and adb.tiktok_clicked:
                        hx, hy, h_score = match_hoan_thanh
                        
                        if is_like_job:
                            # Job Like: Tìm và bấm Tim trắng TikTok
                            match_tim = matcher.find_match(screen, "icon_tim")
                            if match_tim:
                                tx, ty, t_score = match_tim
                                print(f"[BƯỚC 3] ❤️ Bấm Tim TikTok tại ({tx}, {ty})")
                                save_debug_image(screen, tx, ty, "Click Heart")
                                adb.tap(tx, ty)
                                adb.tiktok_action_done = True
                                action_taken = True
                                time.sleep(1.0)
                        else:
                            # Job Follow: Tìm và bấm Follow đỏ TikTok
                            follow_btn = find_tiktok_follow_button(screen, scenario)
                            if follow_btn:
                                fx, fy, area = follow_btn
                                print(f"[BƯỚC 3] ❤️ Bấm Follow TikTok tại ({fx}, {fy})")
                                save_debug_image(screen, fx, fy, "Click Follow")
                                adb.tap(fx, fy)
                                adb.tiktok_action_done = True
                                action_taken = True
                                time.sleep(3.0)
                        
                        if not action_taken:
                            if adb.tiktok_action_done:
                                # Đã hoàn thành follow/like -> Click Hoàn thành
                                print(f"[BƯỚC 4] ✅ Click Hoàn thành tại ({hx}, {hy})")
                                save_debug_image(screen, hx, hy, "Click Hoan Thanh")
                                adb.tap(hx, hy)
                                action_taken = True
                                adb.tiktok_clicked = False
                                adb.tiktok_action_done = False # Reset cho job sau
                            else:
                                # Chưa thực hiện bấm Follow/Like, tuyệt đối không được bấm Hoàn thành!
                                print("[BƯỚC 4] ⚠️ CẢNH BÁO: Chưa thực hiện Follow/Like! Sẽ mở lại TikTok...")
                                match_tiktok = matcher.find_match(screen, "nut_tiktok")
                                if match_tiktok:
                                    tx, ty, score = match_tiktok
                                    print(f"[BƯỚC 2] 🎬 Click mở lại TikTok tại ({tx}, {ty})")
                                    adb.tap(tx, ty)
                                    adb.tiktok_clicked = True
                                    wait_time = 10.0 if is_like_job else 8.0
                                    sleep_countdown(wait_time, "Đang đợi TikTok tải trang để làm lại")
                                    # Thực hiện thao tác luôn sau khi load lại trang
                                    fresh_screen = adb.get_screenshot()
                                    if fresh_screen is not None:
                                        perform_tiktok_action(fresh_screen, adb, matcher, is_like_job, scenario)
                                action_taken = True
                            sleep_countdown(3.0, "Đang xử lý hoàn thành công việc")
                    else:
                        # 2. Chưa bấm TikTok hoặc chưa có nút Hoàn thành -> Tìm/mở TikTok
                        match_tiktok = matcher.find_match(screen, "nut_tiktok")
                        
                        if not match_tiktok:
                            # Kiểm tra TikTok đã mở ở nửa dưới chưa
                            follow_btn_present = find_tiktok_follow_button(screen, scenario)
                            tim_present = matcher.find_match(screen, "icon_tim")
                            
                            tiktok_opened = False
                            if is_like_job and tim_present:
                                tiktok_opened = True
                            elif not is_like_job and follow_btn_present:
                                tiktok_opened = True
                                
                            if tiktok_opened:
                                # Đã mở TikTok -> vuốt lên nhẹ hiển thị Hoàn thành
                                print("[BƯỚC 4] Chưa thấy nút Hoàn thành. Vuốt lên để tìm...")
                                adb.swipe(360, 600, 360, 400, duration_ms=400)
                                action_taken = True
                                adb.tiktok_clicked = True 
                                time.sleep(0.8)
                        
                        # Click mở TikTok (Chỉ click nếu chưa click mở cho job này)
                        if match_tiktok and not action_taken and not adb.tiktok_clicked:
                            tx, ty, t_score = match_tiktok
                            print(f"[BƯỚC 2] 🎬 Click mở TikTok tại ({tx}, {ty})")
                            save_debug_image(screen, tx, ty, "Click TikTok")
                            adb.tap(tx, ty)
                            adb.tiktok_clicked = True 
                            
                            # Đợi tùy theo loại Job (Job Follow đợi 8s, Job Like/Tim đợi 10s)
                            wait_time = 10.0 if is_like_job else 8.0
                            sleep_countdown(wait_time, "Đang đợi TikTok tải trang")
                            
                            # Thao tác bấm Follow/Like luôn ngay sau khi phát hiện load xong
                            fresh_screen = adb.get_screenshot()
                            if fresh_screen is not None:
                                perform_tiktok_action(fresh_screen, adb, matcher, is_like_job, scenario)
                            
                            # Quay lại Golike (Chỉ cần thiết ở kịch bản 2 toàn màn hình)
                            if scenario == 2:
                                print("[BƯỚC 3] 🔙 Đang quay lại Golike (nhấn Back 1 lần và đưa Golike lên foreground)...")
                                adb.press_back() # Gửi phím Back duy nhất 1 lần để thoát TikTok
                                time.sleep(0.5)
                                adb.bring_golike_to_foreground() # Đưa Golike trở lại foreground trực tiếp bằng ADB Monkey
                                sleep_countdown(3.0, "Đang quay lại Golike")
                            elif scenario == 3:
                                print("[BƯỚC 3] ☕ Chế độ Cửa sổ nổi: Golike luôn ở phía trên, không cần chuyển app.")
                                sleep_countdown(1.0, "Đang xử lý tiếp tục")
                            else:
                                print("[BƯỚC 3] ☕ Chế độ Chia đôi màn hình: Golike luôn hiển thị, không cần back.")
                                sleep_countdown(1.0, "Đang xử lý tiếp tục")
                            action_taken = True
            
            # --- BƯỚC 1: NHẬN JOB ---
            if not action_taken:
                match_nhan_job = matcher.find_match(screen, "nut_nhan_job_ngay")
                if match_nhan_job:
                    cx, cy, score = match_nhan_job
                    print(f"[BƯỚC 1] ⚡ Click Nhận Job ngay tại ({cx}, {cy})")
                    save_debug_image(screen, cx, cy, "Nhan Job Ngay")
                    adb.tap(cx, cy)
                    action_taken = True
                    adb.tiktok_clicked = False
                    adb.tiktok_action_done = False # Reset trạng thái tương tác cho job mới
                    # Kích hoạt cờ chờ mạng tải job
                    adb.waiting_for_job = True
                    adb.job_request_time = time.time()
                    print("[BƯỚC 1] ⏳ Đã bấm Nhận Job. Đợi trang Chi tiết hoặc Popup load...")
                    time.sleep(1.0)
                else:
                    match_tab = matcher.find_match(screen, "tab_danh_sach_cong_viec")
                    if match_tab:
                        print("⏳ Vuốt tìm Job mới...")
                        if scenario == 3:
                            # Vuốt cuộn bên trong Cửa sổ nổi
                            adb.swipe(360, 1100, 360, 700, duration_ms=400)
                        else:
                            adb.swipe(360, 600, 360, 400, duration_ms=400)
                        action_taken = True
                        time.sleep(1.0) 
                
            elapsed = time.time() - start_time
            sleep_time = max(0.1, LOOP_INTERVAL - elapsed)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\n[INFO] Đã dừng chương trình auto clicker.")
    except Exception as e:
        print(f"\n[CRITICAL] Lỗi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
