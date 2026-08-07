import os
import sys
import time
import subprocess
import random
import cv2
import numpy as np
import datetime
import json

# ANSI Colors
COLOR_GREEN = "\x1b[1;92m"
COLOR_RED = "\x1b[1;91m"
COLOR_YELLOW = "\x1b[1;93m"
COLOR_BLUE = "\x1b[1;94m"
COLOR_CYAN = "\x1b[1;96m"
COLOR_MAGENTA = "\x1b[1;95m"
COLOR_RESET = "\x1b[0m"
COLOR_GRAY = "\x1b[1;90m"

# Cấu hình thư mục và thông số
TEMPLATES_DIR = "templates"
TEMPLATES_CONFIG = {
    "nut_dong_quang_cao": {"filename": "nut_dong_quang_cao.png", "threshold": 0.8},
    "nut_tiep_tuc": {"filename": "nut_tiep_tuc.png", "threshold": 0.8},
    "nut_nhan_job_ngay": {"filename": "nut_nhan_job_ngay.png", "threshold": 0.75},
    "tab_danh_sach_cong_viec": {"filename": "tab_danh_sach_cong_viec.png", "threshold": 0.75},
    "nut_dong_y": {"filename": "nut_dong_y.png", "threshold": 0.75},
    "txt_da_hieu": {"filename": "txt_da_hieu.png", "threshold": 0.75},
    "header_chi_tiet": {"filename": "header_chi_tiet.png", "threshold": 0.70},
    "nut_tiktok": {"filename": "nut_tiktok.png", "threshold": 0.70},
    "nut_hoan_thanh": {"filename": "nut_hoan_thanh.png", "threshold": 0.75},
    "nut_ok": {"filename": "nut_ok.png", "threshold": 0.60},
    "icon_tim": {"filename": "icon_tim.png", "threshold": 0.75},
    "job_like_indicator": {"filename": "job_like_indicator.png", "threshold": 0.65},
    "nut_bao_loi": {"filename": "nut_bao_loi.png", "threshold": 0.70},
    "nut_gui_bao_cao": {"filename": "nut_gui_bao_cao.png", "threshold": 0.70},
    "txt_job_da_bi_xoa": {"filename": "txt_job_da_bi_xoa.png", "threshold": 0.75},
    "icon_thanh_cong": {"filename": "icon_thanh_cong.png", "threshold": 0.6}
}

completed_jobs = 0

def log(msg, level="INFO"):
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    prefix = f"{COLOR_GRAY}[{now_str}]{COLOR_RESET}"
    
    if level == "SUCCESS":
        color = COLOR_GREEN
        prefix_lvl = "🏆 SUCCESS"
    elif level == "ERROR":
        color = COLOR_RED
        prefix_lvl = "🔴 ERROR"
    elif level == "WARNING":
        color = COLOR_YELLOW
        prefix_lvl = "🟡 WARNING"
    elif level == "CAPTCHA":
        color = COLOR_MAGENTA
        prefix_lvl = "[CAPTCHA]"
    elif level == "JOB":
        color = COLOR_YELLOW
        prefix_lvl = "[JOB] ⚡"
    elif level == "TIKTOK":
        color = COLOR_CYAN
        prefix_lvl = "[TIKTOK] 🎬"
    else:
        color = COLOR_BLUE
        prefix_lvl = "ℹ️ INFO"
        
    formatted = f"{prefix} {color}{prefix_lvl} {msg}{COLOR_RESET}"
    print(formatted)
    
    try:
        with open("debug_run_modern.log", "a", encoding="utf-8") as f:
            f.write(f"[{now_str}] [{level}] {msg}\n")
    except:
        pass

def sleep_countdown(duration, message="Đang chờ"):
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    prefix = f"{COLOR_GRAY}[{now_str}]{COLOR_RESET}"
    rainbow_colors = [COLOR_CYAN, COLOR_YELLOW, COLOR_GREEN, COLOR_BLUE, COLOR_MAGENTA]
    
    start_time = time.time()
    while True:
        elapsed = time.time() - start_time
        remaining = duration - elapsed
        if remaining <= 0:
            break
        color = rainbow_colors[int(remaining * 2) % len(rainbow_colors)]
        sys.stdout.write(f"\r{prefix} {color}⏳ {message}... ({remaining:.1f}s còn lại){COLOR_RESET}")
        sys.stdout.flush()
        time.sleep(0.05)
        
    sys.stdout.write(f"\r{prefix} {COLOR_GREEN}✓ {message} Hoàn tất!                                            {COLOR_RESET}\n")
    sys.stdout.flush()


class ModernADBController:
    def __init__(self, device_id=None):
        self.device_id = device_id
        
    def check_connection(self):
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')
            devices = []
            for line in lines[1:]:
                if line.strip():
                    parts = line.strip().split()
                    if len(parts) >= 2 and parts[1] == 'device':
                        devices.append(parts[0])
            return devices
        except:
            return []

    def get_screenshot(self):
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['exec-out', 'screencap', '-p'])
        
        process = None
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(timeout=6.0)
            if process.returncode != 0 or not stdout:
                return None
            image_array = np.frombuffer(stdout, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            return image
        except Exception:
            if process:
                try:
                    process.kill()
                except Exception:
                    pass
            return None

    def tap(self, x, y):
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['shell', 'input', 'tap', str(int(x)), str(int(y))])
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4.0)
            return True
        except Exception:
            return False

    def swipe(self, x1, y1, x2, y2, duration_ms=400):
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['shell', 'input', 'swipe', str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(int(duration_ms))])
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5.0)
            return True
        except Exception:
            return False

    def press_back(self):
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['shell', 'input', 'keyevent', '4'])
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4.0)
            return True
        except Exception:
            return False

    def force_stop_app(self, package_name):
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['shell', 'am', 'force-stop', package_name])
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4.0)
            return True
        except Exception:
            return False

    def launch_app(self, package_name):
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['shell', 'monkey', '-p', package_name, '-c', 'android.intent.category.LAUNCHER', '1'])
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except:
            return False


class TemplateMatcher:
    def __init__(self, templates_dir, scale=1.0, scenario=None):
        self.templates_dir = templates_dir
        self.scale = scale
        self.scenario = scenario
        self.loaded_templates = {}
        self.initialize_templates()

    def initialize_templates(self):
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            
        loaded_count = 0
        for name, config in TEMPLATES_CONFIG.items():
            path = os.path.join(self.templates_dir, config["filename"])
            if os.path.exists(path):
                img = cv2.imread(path, cv2.IMREAD_COLOR)
                if img is not None:
                    if self.scale != 1.0 and name not in ["icon_tim"]:
                        tw = int(img.shape[1] * self.scale)
                        th = int(img.shape[0] * self.scale)
                        img = cv2.resize(img, (tw, th), interpolation=cv2.INTER_CUBIC)
                    h, w, _ = img.shape
                    self.loaded_templates[name] = {
                        "image": img,
                        "w": w,
                        "h": h,
                        "threshold": config["threshold"]
                    }
                    loaded_count += 1
            else:
                log(f"Thiếu ảnh mẫu: '{path}'. Bỏ qua.", "WARNING")
        log(f"Đã load thành công {loaded_count} ảnh mẫu.")

    def find_match(self, screen_img, template_name):
        if template_name not in self.loaded_templates:
            return None
        temp_data = self.loaded_templates[template_name]
        res = cv2.matchTemplate(screen_img, temp_data["image"], cv2.TM_CCOEFF_NORMED)
        
        # Nếu ở chế độ cửa sổ nổi, mọi nút Golike chỉ tìm ở nửa dưới màn hình (Y >= 640) để tránh quét nhầm TikTok
        if self.scenario == 3 and template_name not in ["icon_tim", "job_like_indicator"]:
            res[:640, :] = 0
            
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= temp_data["threshold"]:
            center_x = max_loc[0] + temp_data["w"] // 2
            center_y = max_loc[1] + temp_data["h"] // 2
            return center_x, center_y, max_val
        return None

    def get_match_score(self, screen_img, template_name):
        if template_name not in self.loaded_templates:
            return 0.0
        temp_data = self.loaded_templates[template_name]
        res = cv2.matchTemplate(screen_img, temp_data["image"], cv2.TM_CCOEFF_NORMED)
        
        # Nếu ở chế độ cửa sổ nổi, mọi nút Golike chỉ tìm ở nửa dưới màn hình (Y >= 640) để tránh quét nhầm TikTok
        if self.scenario == 3 and template_name not in ["icon_tim", "job_like_indicator"]:
            res[:640, :] = 0
            
        _, max_val, _, _ = cv2.minMaxLoc(res)
        return max_val


class CaptchaDetector:
    def __init__(self, template_path="templates/captcha_title.png", threshold=0.50):
        self.template_path = template_path
        self.threshold = threshold

    def is_captcha_present(self, screen_img, scenario=3, matcher=None) -> bool:
        if matcher is not None:
            if matcher.find_match(screen_img, "nut_tiktok") or matcher.find_match(screen_img, "nut_nhan_job_ngay"):
                return False
                
        if scenario == 3:
            path = "templates/captcha_title_sc3.png"
            if not os.path.exists(path):
                path = self.template_path
        else:
            path = self.template_path

        if not os.path.exists(path):
            return False

        temp_title = cv2.imread(path)
        if temp_title is None:
            return False

        if scenario == 3 and path.endswith("captcha_title_sc3.png"):
            temp_scaled = temp_title
        else:
            scale_val = 2.667
            tw = int(temp_title.shape[1] * scale_val)
            th = int(temp_title.shape[0] * scale_val)
            temp_scaled = cv2.resize(temp_title, (tw, th), interpolation=cv2.INTER_CUBIC)

        res_title = cv2.matchTemplate(screen_img, temp_scaled, cv2.TM_CCOEFF_NORMED)
        # Ràng buộc Y (chỉ tìm tiêu đề ở nửa dưới và giữa màn hình)
        if scenario == 3:
            res_title[:640, :] = 0
            res_title[820:, :] = 0
            # Ràng buộc X (chỉ tìm tiêu đề sát mép trái cửa sổ nổi)
            res_title[:, :100] = 0
            res_title[:, 140:] = 0
        else:
            res_title[:450, :] = 0
            res_title[850:, :] = 0
            res_title[:, :160] = 0
            res_title[:, 300:] = 0
            
        _, score_title, _, _ = cv2.minMaxLoc(res_title)
        thresh = 0.30 if scenario == 3 else self.threshold
        return score_title >= thresh


def save_debug_image(screen, x, y, label):
    try:
        debug_img = screen.copy()
        cv2.circle(debug_img, (int(x), int(y)), 25, (0, 0, 255), 3)
        cv2.circle(debug_img, (int(x), int(y)), 4, (0, 0, 255), -1)
        cv2.putText(debug_img, label, (int(x) + 35, int(y) + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.imwrite('debug_last_click.png', debug_img)
    except:
        pass


def find_tiktok_follow_button(screen_img, scenario=3):
    try:
        height, width, _ = screen_img.shape
        if scenario == 1:
            y_min, y_max = 850, 1500
        elif scenario == 3:
            y_min, y_max = 200, 515
        else:
            y_min, y_max = 200, 700
        
        zone = screen_img[y_min:y_max, :]
        hsv = cv2.cvtColor(zone, cv2.COLOR_BGR2HSV)
        
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
            if area > 450:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                if 1.5 < aspect_ratio < 10.0:
                    center_x = x + w // 2
                    if center_x > 500:
                        continue
                    if area > max_area:
                        max_area = area
                        center_y = y_min + y + h // 2
                        best_match = (center_x, center_y, area)
                        
        if best_match:
            return best_match
            
        y_min_av, y_max_av = 300, 750
        x_min_av = int(width * 0.75)
        
        zone_av = screen_img[y_min_av:y_max_av, x_min_av:]
        hsv_av = cv2.cvtColor(zone_av, cv2.COLOR_BGR2HSV)
        mask_av = cv2.inRange(hsv_av, lower_red1, upper_red1) | cv2.inRange(hsv_av, lower_red2, upper_red2)
        contours_av, _ = cv2.findContours(mask_av, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours_av:
            area = cv2.contourArea(contour)
            if 60 < area < 400:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h
                if 0.7 < aspect_ratio < 1.3:
                    center_x = x_min_av + x + w // 2
                    center_y = y_min_av + y + h // 2
                    return (center_x, center_y, area)
                    
        return None
    except Exception as e:
        log(f"Lỗi tìm Follow: {e}", "ERROR")
        return None


def perform_tiktok_action(screen, adb, matcher, is_like_job, scenario):
    height, width, _ = screen.shape
    
    # 1. Kiểm tra sự xuất hiện của nút Follow ở nửa trên màn hình TikTok
    follow_btn = find_tiktok_follow_button(screen, scenario)
    if follow_btn:
        fx, fy, area = follow_btn
        log("[TIKTOK] Phát hiện Job Follow", "TIKTOK")
        log(f"Bấm Follow TikTok tại ({fx}, {fy})", "TIKTOK")
        save_debug_image(screen, fx, fy, "Click Follow")
        adb.tap(fx, fy)
        time.sleep(0.5)
        return True
        
    # 2. Nếu không tìm thấy nút Follow -> Thực hiện Job Tim
    log("[TIKTOK] Phát hiện Job Tim", "TIKTOK")
    
    # Giới hạn vùng quét ở cột bên phải màn hình
    x_min = int(width * 0.8)
    if scenario == 3:
        y_min_crop = 100
        y_max_crop = 480
    else:
        y_min_crop = 350
        y_max_crop = 1100
        
    right_col = screen[y_min_crop:y_max_crop, x_min:width]
    match_tim = matcher.find_match(right_col, "icon_tim")
    
    if match_tim:
        tx, ty, score = match_tim
        screen_tx = x_min + tx
        screen_ty = y_min_crop + ty
        log(f"Bấm tim TikTok tại ({screen_tx}, {screen_ty})", "TIKTOK")
        save_debug_image(screen, screen_tx, screen_ty, "Click Heart")
        adb.tap(screen_tx, screen_ty)
        time.sleep(0.5)
        return True
    else:
        # Dự phòng bằng Double-click vào giữa màn hình video
        cx = int(width * 0.5)
        cy = int((y_min_crop + y_max_crop) * 0.5)
        log(f"Không thấy nút Tim. Thử Double-click video tại ({cx}, {cy}) làm dự phòng...", "TIKTOK")
        adb.tap(cx, cy)
        time.sleep(0.15)
        adb.tap(cx, cy)
        time.sleep(0.5)
        return True


def solve_captcha(screen, adb, matcher, captcha_detector, scenario=3) -> bool:
    log("Phát hiện màn hình Captcha Xác minh nhanh! Bắt đầu giải...", "CAPTCHA")
    
    for attempt in range(1, 4):
        log(f"Đang quét tìm khối vuông và đích (Lần thử {attempt}/3)...", "CAPTCHA")
        
        height, width, _ = screen.shape
        path = "templates/captcha_title_sc3.png" if scenario == 3 else "templates/captcha_title.png"
        if not os.path.exists(path):
            path = "templates/captcha_title.png"

        tx, ty = None, None
        if os.path.exists(path):
            temp_title = cv2.imread(path)
            if temp_title is not None:
                if scenario == 3 and path.endswith("captcha_title_sc3.png"):
                    temp_scaled = temp_title
                else:
                    scale_val = 2.667
                    tw = int(temp_title.shape[1] * scale_val)
                    th = int(temp_title.shape[0] * scale_val)
                    temp_scaled = cv2.resize(temp_title, (tw, th), interpolation=cv2.INTER_CUBIC)
                
                res_title = cv2.matchTemplate(screen, temp_scaled, cv2.TM_CCOEFF_NORMED)
                # Ràng buộc Y (tiêu đề ở nửa dưới và giữa màn hình)
                if scenario == 3:
                    res_title[:640, :] = 0
                    res_title[820:, :] = 0
                    res_title[:, :100] = 0
                    res_title[:, 140:] = 0
                else:
                    res_title[:450, :] = 0
                    res_title[850:, :] = 0
                    res_title[:, :160] = 0
                    res_title[:, 300:] = 0
                
                _, score_title, _, loc_title = cv2.minMaxLoc(res_title)
                thresh = 0.30 if scenario == 3 else 0.50
                if score_title >= thresh:
                    tx, ty = loc_title
                    # Click nhẹ vào vùng trống tiêu đề để xóa bỏ vết bôi xanh (highlight) văn bản nếu có
                    adb.tap(tx + 200, ty + 20)
                    time.sleep(0.3)
                    # Chụp lại màn hình sạch sau khi xóa bôi xanh
                    screen = adb.get_screenshot()
                    if screen is None:
                        break
                
        if tx is None or ty is None:
            log("Không tìm thấy tiêu đề Captcha làm mốc quét. Bỏ qua...", "WARNING")
            time.sleep(2)
            screen = adb.get_screenshot()
            if screen is None:
                break
            continue
            
        # 1. KHOANH VÙNG TUYỆT ĐỐI (ROI) CỬA SỔ GOLIKE
        roi_y_min = ty + 50
        roi_y_max = ty + 550  # Mở rộng đủ sâu để tránh bị cắt mất các khối ở hàng 3 dưới đáy (Y=1209)
        roi_x_min = tx - 30
        roi_x_max = tx + 550  # Mở rộng thêm biên phải để tránh bị cắt mất đích
        
        # Chuyển đổi sang HSV để tìm kiếm bằng contour
        hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
        
        # 2. Phát hiện Khối vuông xanh dương (Start Point)
        # Chúng ta lọc màu xanh dương bão hòa cao trong vùng nửa trái ROI
        x1, y1 = None, None
        lower_blue = np.array([90, 80, 50])
        upper_blue = np.array([135, 255, 255])
        
        # Crop nửa trái màn hình theo mốc ROI
        crop_y_min = max(0, roi_y_min)
        crop_y_max = min(height, roi_y_max)
        crop_x_min_b = max(0, roi_x_min)
        crop_x_max_b = width // 2  # Nửa trái màn hình
        
        blue_mask = cv2.inRange(hsv[crop_y_min:crop_y_max, crop_x_min_b:crop_x_max_b], lower_blue, upper_blue)
        contours_blue, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        best_blue_area = -1
        for cnt in contours_blue:
            area = cv2.contourArea(cnt)
            if 150 < area < 3000:
                x, y, w, h = cv2.boundingRect(cnt)
                if w > 70 or h > 70 or w < 12 or h < 12:
                    continue
                aspect = float(w) / h if h > 0 else 0
                if aspect < 0.5 or aspect > 2.0:
                    continue
                cx = crop_x_min_b + x + w // 2
                cy = crop_y_min + y + h // 2
                if area > best_blue_area:
                    best_blue_area = area
                    x1, y1 = cx, cy
                    
        # Dự phòng (Fallback) nếu lọc màu HSV thất bại (mặc định ở hàng 2)
        if x1 is None or y1 is None:
            x1 = tx + 36
            y1 = ty + 383
            log("Không tìm thấy khối xanh qua HSV, dùng tọa độ mặc định.", "WARNING")
            
        # 3. Phát hiện Vòng tròn xanh lá (End Point)
        # Chúng ta lọc màu xanh lá trong vùng nửa phải ROI
        x3, y3 = None, None
        lower_green = np.array([35, 30, 20])
        upper_green = np.array([95, 255, 255])
        
        crop_x_min_g = width // 2  # Nửa phải màn hình
        crop_x_max_g = min(width, roi_x_max)
        
        green_mask = cv2.inRange(hsv[crop_y_min:crop_y_max, crop_x_min_g:crop_x_max_g], lower_green, upper_green)
        contours_green, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        best_green_area = -1
        for cnt in contours_green:
            area = cv2.contourArea(cnt)
            if 100 < area < 3000:
                x, y, w, h = cv2.boundingRect(cnt)
                # Bộ lọc kích thước rộng rãi hơn để bao phủ trọn vẹn vòng tròn đích thực tế (khoảng 40-50px)
                if w > 70 or h > 70 or w < 12 or h < 12:
                    continue
                aspect = float(w) / h if h > 0 else 0
                if aspect < 0.5 or aspect > 2.0:
                    continue
                cx = crop_x_min_g + x + w // 2
                cy = crop_y_min + y + h // 2
                if area > best_green_area:
                    best_green_area = area
                    x3, y3 = cx, cy
                    
        # Dự phòng (Fallback) nếu lọc màu HSV thất bại (mặc định ở hàng 2)
        if x3 is None or y3 is None:
            x3 = tx + 478
            y3 = ty + 383
            log("Không tìm thấy vòng tròn đích qua HSV, dùng tọa độ mặc định.", "WARNING")
            
        # 4. Tính toán Waypoint (x2, y2)
        x2 = (x1 + x3) // 2
        # Nếu start và end cùng ở một mốc Y (gần nhau), Waypoint sẽ ở mốc Y khác để tạo hình vòng cung
        if abs(y1 - y3) < 40:
            row_spacing = 150
            if y1 > ty + 350:
                y2 = y1 - row_spacing
            elif y1 < ty + 200:
                y2 = y1 + row_spacing
            else:
                y2 = y1 + row_spacing
        else:
            y2 = (y1 + y3) // 2
            
        log("=== DEBUG CAPTCHA ===", "CAPTCHA")
        log(f"ROI quét: Y=[{roi_y_min}, {roi_y_max}], X=[{roi_x_min}, {roi_x_max}]", "CAPTCHA")
        log(f"Mốc tiêu đề (tx, ty): ({tx}, {ty})", "CAPTCHA")
        log(f"Khối xanh phát hiện: Blue({x1},{y1})", "CAPTCHA")
        log(f"Vòng tròn đích: Đích({x3},{y3})", "CAPTCHA")
        log(f"Nét đứt Waypoint: Nét đứt({x2},{y2})", "CAPTCHA")
        
        # 5. Tạo đường kéo Bézier mượt mà (35 bước)
        steps = 35
        path = []
        for i in range(steps + 1):
            t = i / steps
            bx = (1 - t)**2 * x1 + 2 * (1 - t) * t * x2 + t**2 * x3
            by = (1 - t)**2 * y1 + 2 * (1 - t) * t * y2 + t**2 * y3
            xj = int(bx) + random.randint(-1, 1)
            yj = int(by) + random.randint(-1, 1)
            path.append((xj, yj))
            
        # 6. Viết kịch bản Monkey Script để duy trì Touch Down session thực tế
        monkey_lines = []
        monkey_lines.append("type= raw events")
        monkey_lines.append("count= 10")
        monkey_lines.append("speed= 1.0")
        monkey_lines.append("start data >>")
        
        # DOWN event
        monkey_lines.append(f"DispatchPointer(0, 0, 0, {path[0][0]}, {path[0][1]}, 1.0, 1.0, 0, 0.0, 0.0, 0, 0)")
        monkey_lines.append("UserWait(50)")
        
        # MOVE events (Khoảng 30-40ms mỗi bước là cực kì mượt mà và thực tế)
        for px, py in path[1:-1]:
            monkey_lines.append(f"DispatchPointer(0, 0, 2, {px}, {py}, 1.0, 1.0, 0, 0.0, 0.0, 0, 0)")
            monkey_lines.append("UserWait(40)")
            
        # UP event
        monkey_lines.append(f"DispatchPointer(0, 0, 1, {path[-1][0]}, {path[-1][1]}, 1.0, 1.0, 0, 0.0, 0.0, 0, 0)")
        monkey_content = "\n".join(monkey_lines) + "\n"
        
        # Ghi file log chi tiết
        log_file_path = "drag_log.txt"
        try:
            with open(log_file_path, "w", encoding="utf-8") as lf:
                lf.write(f"=== ĐƯỜNG KÉO CAPTCHA BÉZIER (MONKEY) ===\n")
                lf.write(f"Tọa độ bắt đầu (Blue): ({x1}, {y1})\n")
                lf.write(f"Tọa độ trung gian (Nét đứt): ({x2}, {y2})\n")
                lf.write(f"Tọa độ kết thúc (Đích): ({x3}, {y3})\n\n")
                lf.write(f"=== KỊCH BẢN MONKEY SCRIPT ===\n")
                lf.write(monkey_content)
        except Exception as e:
            log(f"Không thể tạo file debug drag_log.txt: {e}", "WARNING")
            
        # Ghi file monkey script tạm ở máy tính
        local_path = "monkey_drag.txt"
        try:
            with open(local_path, "w", newline="\n") as f:
                f.write(monkey_content)
        except Exception as e:
            log(f"Lỗi tạo file monkey script tạm: {e}", "ERROR")
            
        # Push lên điện thoại và chạy monkey script
        device_path = "/data/local/tmp/monkey_drag.txt"
        push_cmd = ['adb']
        if adb.device_id:
            push_cmd.extend(['-s', adb.device_id])
        push_cmd.extend(['push', local_path, device_path])
        
        run_cmd = ['adb']
        if adb.device_id:
            run_cmd.extend(['-s', adb.device_id])
        run_cmd.extend(['shell', 'monkey', '-f', device_path, '1'])
        
        try:
            log(f"Đang chạm giữ tại Blue ({x1}, {y1})...", "CAPTCHA")
            log(f"Đang kéo Bézier mượt mà qua Waypoint Nét đứt ({x2}, {y2})...", "CAPTCHA")
            log(f"Đang thả tay tại Đích ({x3}, {y3})...", "CAPTCHA")
            
            subprocess.run(push_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(run_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log("Đã chạy thành công lệnh monkey kéo thả Bézier mượt mà trên thiết bị.", "CAPTCHA")
        except Exception as e:
            log(f"Lỗi chạy script kéo Bézier: {e}", "ERROR")
            
        sleep_countdown(3.5, "Chờ kiểm tra kết quả Captcha")
        
        screen = adb.get_screenshot()
        if screen is None:
            break
            
        if not captcha_detector.is_captcha_present(screen, scenario, matcher):
            log("Giải Captcha Xác minh nhanh thành công!", "SUCCESS")
            return True
        else:
            log("Captcha vẫn xuất hiện. Kéo thả thất bại.", "WARNING")
            
    log("Không thể tự động giải Captcha sau 3 lần thử.", "ERROR")
    return False


def main():
    global completed_jobs
    
    log("==================================================================", "SUCCESS")
    log("🚀 KHỞI ĐỘNG AUTO-CLICKER GOLIKE HOÀN TOÀN TỰ ĐỘNG (KHÔNG DÙNG AI)", "SUCCESS")
    log("==================================================================", "SUCCESS")
    
    adb = ModernADBController()
    devices = adb.check_connection()
    if not devices:
        log("Không tìm thấy thiết bị Android. Dừng bot.", "ERROR")
        sys.exit(1)
        
    adb.device_id = devices[0]
    log(f"Đã kết nối thiết bị: {adb.device_id}", "SUCCESS")
    
    scenario = 3
    scale = 0.70 if scenario == 3 else 1.0
    matcher = TemplateMatcher(TEMPLATES_DIR, scale=scale, scenario=scenario)
    
    captcha_detector = CaptchaDetector()
    
    tiktok_clicked = False
    tiktok_action_done = False
    need_report_error = False
    waiting_for_job = False
    job_request_time = 0
    report_swipe_count = 0
    
    last_state = "STATE_UNKNOWN"
    state_start_time = time.time()
    last_state_recovery_time = time.time()
    
    try:
        while True:
            # ================= BƯỚC 1: VUỐT VÀ NHẬN JOB =================
            log("--- BẮT ĐẦU VÒNG LẶP JOB MỚI (BƯỚC 1) ---", "JOB")
            job_clicked = False
            for att in range(10):
                screen = adb.get_screenshot()
                if screen is None:
                    time.sleep(1.0)
                    continue
                
                # Đóng các quảng cáo/popup cản trở nếu xuất hiện
                match_close = matcher.find_match(screen, "nut_dong_quang_cao")
                if match_close:
                    log("Đóng quảng cáo...", "WARNING")
                    adb.tap(match_close[0], match_close[1])
                    time.sleep(1.5)
                    continue
                    
                match_continue = matcher.find_match(screen, "nut_tiep_tuc")
                if match_continue:
                    log("Click Tiếp tục quảng cáo...", "WARNING")
                    adb.tap(match_continue[0], match_continue[1])
                    time.sleep(1.5)
                    continue
                
                match_ok = matcher.find_match(screen, "nut_ok")
                if match_ok:
                    log("Đóng popup cản trở...", "WARNING")
                    adb.tap(match_ok[0], match_ok[1])
                    time.sleep(1.5)
                    continue
                    
                match_dong_y = matcher.find_match(screen, "nut_dong_y")
                if match_dong_y:
                    dy_x, dy_y, _ = match_dong_y
                    log("Xử lý popup Đồng ý...", "INFO")
                    match_da_hieu = matcher.find_match(screen, "txt_da_hieu")
                    if match_da_hieu:
                        adb.tap(match_da_hieu[0], match_da_hieu[1])
                    else:
                        cb_x, cb_y = int(dy_x - 367 * scale), int(dy_y - 147 * scale)
                        adb.tap(cb_x, cb_y)
                    time.sleep(0.8)
                    adb.tap(dy_x, dy_y)
                    time.sleep(1.5)
                    continue

                match_nhan_job = matcher.find_match(screen, "nut_nhan_job_ngay")
                if match_nhan_job:
                    cx, cy, _ = match_nhan_job
                    log("Nhận Job mới (Click 'Bắt đầu kiếm xu ngay')...", "JOB")
                    adb.tap(cx, cy)
                    job_clicked = True
                    time.sleep(2.0)  # Chờ giao diện chuyển tiếp ổn định
                    break
                else:
                    match_tab = matcher.find_match(screen, "tab_danh_sach_cong_viec")
                    if match_tab:
                        log("Vuốt màn hình để tìm nút Nhận Job...", "JOB")
                        adb.swipe(360, 1100, 360, 700, duration_ms=400)
                        time.sleep(1.5)
                    else:
                        time.sleep(1.0)

            if not job_clicked:
                log("Không tìm thấy nút Nhận Job, khởi động lại vòng lặp...", "WARNING")
                continue

            # ================= BƯỚC 2: KIỂM TRA CAPTCHA =================
            log("--- KIỂM TRA CAPTCHA (BƯỚC 2) ---", "JOB")
            screen = adb.get_screenshot()
            if screen is not None and captcha_detector.is_captcha_present(screen, scenario, matcher):
                log("Phát hiện màn hình Captcha Xác minh nhanh! Bắt đầu giải...", "CAPTCHA")
                for cap_att in range(3):
                    solve_captcha(screen, adb, matcher, captcha_detector, scenario)
                    time.sleep(2.5)
                    screen = adb.get_screenshot()
                    if screen is None or not captcha_detector.is_captcha_present(screen, scenario, matcher):
                        log("Giải Captcha thành công hoặc màn hình đã thay đổi!", "CAPTCHA")
                        break
            else:
                log("Không phát hiện Captcha. Bỏ qua.", "JOB")

            # ================= BƯỚC 3: LÀM JOB TIKTOK & HOÀN THÀNH =================
            log("--- LÀM JOB TIKTOK (BƯỚC 3) ---", "JOB")
            tiktok_action_done = False
            tiktok_clicked = False
            need_report_error = False
            report_swipe_count = 0
            
            for action_att in range(15):
                screen = adb.get_screenshot()
                if screen is None:
                    time.sleep(1.0)
                    continue

                # 1. Check popup thông báo OK (Thành công / Lỗi)
                match_ok = matcher.find_match(screen, "nut_ok")
                if match_ok:
                    cx, cy, _ = match_ok
                    log("Bấm OK nhận kết quả Job...", "INFO")
                    adb.tap(cx, cy)
                    
                    match_xoa = matcher.find_match(screen, "txt_job_da_bi_xoa")
                    if match_xoa:
                        log("Job đã bị xóa hoặc hết hạn. Tiến hành báo lỗi...", "WARNING")
                        need_report_error = True
                        time.sleep(1.5)
                        continue
                    
                    # Xác định thành công hay lỗi
                    match_success = matcher.find_match(screen, "icon_thanh_cong")
                    height, width, _ = screen.shape
                    y1 = max(0, int(cy - 370 * scale))
                    y2 = min(height, int(cy - 180 * scale))
                    x1 = max(0, int(cx - 90 * scale))
                    x2 = min(width, int(cx + 90 * scale))
                    crop = screen[y1:y2, x1:x2]
                    hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                    green_mask = cv2.inRange(hsv_crop, np.array([35, 20, 50]), np.array([85, 255, 255]))
                    green_pixels = cv2.countNonZero(green_mask)
                    
                    if match_success or (green_pixels > 30):
                        completed_jobs += 1
                        log(f"Đã hoàn thành thành công {completed_jobs} job!", "SUCCESS")
                        print("------------------------------------------------------------------")
                        if completed_jobs > 0 and completed_jobs % 10 == 0:
                            log(f"Đã chạy {completed_jobs} job. Nghỉ ngơi 60s...", "SUCCESS")
                            sleep_countdown(60.0, "Nghỉ ngơi phục hồi thiết bị")
                    else:
                        log("Hệ thống báo lỗi. Kích hoạt cờ báo lỗi...", "WARNING")
                        need_report_error = True
                        time.sleep(1.5)
                        continue
                    
                    # Kết thúc 1 chu trình job
                    break

                # 2. Xử lý báo lỗi nếu có cờ báo lỗi
                if need_report_error:
                    if report_swipe_count > 3:
                        log("Quá giới hạn tìm nút báo lỗi. Hủy cờ.", "ERROR")
                        need_report_error = False
                        report_swipe_count = 0
                        break
                    
                    match_gui_bc = matcher.find_match(screen, "nut_gui_bao_cao")
                    if match_gui_bc:
                        log("Gửi báo cáo lỗi...", "JOB")
                        adb.tap(match_gui_bc[0], match_gui_bc[1])
                        time.sleep(2.0)
                        
                        # Chờ và click OK để đóng popup thông báo gửi thành công
                        ok_screen = adb.get_screenshot()
                        if ok_screen is not None:
                            match_ok = matcher.find_match(ok_screen, "nut_ok")
                            if match_ok:
                                log("Bấm OK xác nhận báo cáo lỗi...", "INFO")
                                adb.tap(match_ok[0], match_ok[1])
                                time.sleep(1.5)
                        
                        need_report_error = False
                        report_swipe_count = 0
                        break
                    
                    match_bao_loi = matcher.find_match(screen, "nut_bao_loi")
                    if match_bao_loi:
                        log("Click Báo lỗi...", "JOB")
                        adb.tap(match_bao_loi[0], match_bao_loi[1])
                        report_swipe_count = 0
                        time.sleep(1.5)
                    else:
                        log("Vuốt tìm nút Báo lỗi...", "WARNING")
                        adb.swipe(360, 1100, 360, 700, duration_ms=400)
                        report_swipe_count += 1
                        time.sleep(1.0)
                    continue

                # 3. Giao diện Chi tiết Job: Mở TikTok / Hoàn thành
                match_header_ct = matcher.find_match(screen, "header_chi_tiet")
                if match_header_ct:
                    zone_job = screen[500:750, 32:688] if scenario == 3 else screen[150:450, :]
                    is_like_job = matcher.find_match(zone_job, "job_like_indicator") is not None
                    
                    match_hoan_thanh = matcher.find_match(screen, "nut_hoan_thanh")
                    if match_hoan_thanh and tiktok_clicked:
                        log("Bấm Hoàn thành...", "JOB")
                        adb.tap(match_hoan_thanh[0], match_hoan_thanh[1])
                        time.sleep(3.5)
                        continue
                        
                    match_tiktok = matcher.find_match(screen, "nut_tiktok")
                    if match_tiktok and not tiktok_clicked:
                        log("Bấm nút mở app TikTok...", "TIKTOK")
                        adb.tap(match_tiktok[0], match_tiktok[1])
                        tiktok_clicked = True
                        wait_time = random.uniform(9.5, 11.5) if is_like_job else random.uniform(7.5, 9.0)
                        sleep_countdown(wait_time, "Chờ TikTok load trang")
                        
                        fresh_screen = adb.get_screenshot()
                        if fresh_screen is not None:
                            tiktok_action_done = perform_tiktok_action(fresh_screen, adb, matcher, is_like_job, scenario)
                        time.sleep(0.1)
                        log("[TIKTOK] Đã hoàn thành tương tác trên TikTok. Chuẩn bị click Hoàn thành...", "JOB")
                        time.sleep(0.1)
                        continue
                    
                    if not match_tiktok and not tiktok_clicked:
                        log("Không tìm thấy nút TikTok trên màn hình chi tiết job...", "WARNING")
                        time.sleep(0.5)
                            
            # Đảm bảo tắt màn hình chi tiết job cũ để về Home
            fresh_screen = adb.get_screenshot()
            if fresh_screen is not None and matcher.find_match(fresh_screen, "header_chi_tiet"):
                if scenario == 3:
                    adb.tap(50, 490)
                else:
                    adb.press_back()
                time.sleep(1.0)
            
    except KeyboardInterrupt:
        log("Dừng bot.", "SUCCESS")
    except Exception as e:
        log(f"Lỗi hệ thống: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
