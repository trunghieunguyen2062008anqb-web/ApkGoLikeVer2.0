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
    "job_like_indicator": {"filename": "job_like_indicator.png", "threshold": 0.55},
    "job_like_text": {"filename": "job_like_text.png", "threshold": 0.80},
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
    try:
        print(formatted)
    except:
        try:
            clean_prefix = prefix_lvl.encode('ascii', errors='ignore').decode('ascii').strip()
            clean_msg = msg.encode('ascii', errors='ignore').decode('ascii')
            print(f"[{now_str}] [{clean_prefix}] {clean_msg}")
        except:
            pass
    
    try:
        with open("debug_run_modern.log", "a", encoding="utf-8") as f:
            f.write(f"[{now_str}] [{level}] {msg}\n")
    except:
        pass

def sleep_countdown(duration, message="Đang chờ"):
    rainbow_colors = [COLOR_CYAN, COLOR_YELLOW, COLOR_GREEN, COLOR_BLUE, COLOR_MAGENTA]
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        remaining = duration - elapsed
        if remaining <= 0:
            break
        
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        prefix = f"{COLOR_GRAY}[{now_str}]{COLOR_RESET}"
        color = rainbow_colors[int(remaining * 2) % len(rainbow_colors)]
        
        try:
            sys.stdout.write(f"\r{prefix} {color}>>> {message}... ({remaining:.1f}s){COLOR_RESET}")
            sys.stdout.flush()
        except:
            pass
        time.sleep(0.05)
        
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    prefix = f"{COLOR_GRAY}[{now_str}]{COLOR_RESET}"
    try:
        sys.stdout.write(f"\r{prefix} {COLOR_GREEN}✓ {message} Hoàn tất!                                            {COLOR_RESET}\n")
        sys.stdout.flush()
    except:
        print(f"[{now_str}] ✓ {message} Hoàn tất!")


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
            if image is not None:
                h, w, _ = image.shape
                if w > h:
                    log("Phát hiện điện thoại bị xoay ngang! Tự động xoay dọc lại Portrait...", "WARNING")
                    rot_cmd = ['adb']
                    if self.device_id:
                        rot_cmd.extend(['-s', self.device_id])
                    subprocess.run(rot_cmd + ['shell', 'settings', 'put', 'system', 'user_rotation', '0'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(rot_cmd + ['shell', 'settings', 'put', 'system', 'accelerometer_rotation', '0'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(1.0)
                    # Chụp lại màn hình mới sau khi xoay dọc
                    process_retry = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout_retry, _ = process_retry.communicate(timeout=6.0)
                    if process_retry.returncode == 0 and stdout_retry:
                        image_array = np.frombuffer(stdout_retry, dtype=np.uint8)
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
#         python auto_clicker.py 
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
    def __init__(self, template_path="templates/captcha_title.png", threshold=0.60):
        self.template_path = template_path
        self.threshold = threshold

    def find_captcha_markers(self, screen_img):
        """Find the blue drag block and green target ring that only appear inside captcha."""
        try:
            height, width, _ = screen_img.shape
            hsv = cv2.cvtColor(screen_img, cv2.COLOR_BGR2HSV)
            y_min = int(height * 0.25)
            y_max = int(height * 0.86)

            mask_blue = cv2.inRange(hsv, np.array([95, 70, 120]), np.array([125, 255, 255]))
            cnts_b, _ = cv2.findContours(mask_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            blue_candidates = []
            for cnt in cnts_b:
                area = cv2.contourArea(cnt)
                x, y, w, h = cv2.boundingRect(cnt)
                if not (y_min <= y <= y_max):
                    continue
                if not (12 <= w <= 85 and 12 <= h <= 85):
                    continue
                ratio = w / float(h)
                fill = area / float(max(1, w * h))
                if 0.55 <= ratio <= 1.65 and fill >= 0.35 and x < width * 0.48:
                    blue_candidates.append((area, x + w // 2, y + h // 2, x, y, w, h))

            mask_green = cv2.inRange(hsv, np.array([38, 45, 60]), np.array([95, 255, 255]))
            cnts_g, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            green_candidates = []
            for cnt in cnts_g:
                area = cv2.contourArea(cnt)
                x, y, w, h = cv2.boundingRect(cnt)
                if not (y_min <= y <= y_max):
                    continue
                if not (22 <= w <= 105 and 22 <= h <= 105):
                    continue
                ratio = w / float(h)
                fill = area / float(max(1, w * h))
                if 0.60 <= ratio <= 1.60 and 0.08 <= fill <= 0.90 and x > width * 0.50:
                    green_candidates.append((area, x + w // 2, y + h // 2, x, y, w, h))

            best_pair = None
            best_score = -1
            for b in blue_candidates:
                for g in green_candidates:
                    bx, by = b[1], b[2]
                    gx, gy = g[1], g[2]
                    dx = gx - bx
                    dy = abs(gy - by)
                    if not (width * 0.32 <= dx <= width * 0.88):
                        continue
                    if dy > height * 0.22:
                        continue
                    score = b[0] + g[0] - dy * 2
                    if score > best_score:
                        best_score = score
                        best_pair = {
                            "blue": (int(bx), int(by)),
                            "green": (int(gx), int(gy)),
                            "blue_box": tuple(int(v) for v in b[3:]),
                            "green_box": tuple(int(v) for v in g[3:]),
                        }
            return best_pair
        except Exception:
            return None

    def is_captcha_present(self, screen_img, scenario=3, matcher=None) -> bool:
        markers = self.find_captcha_markers(screen_img)
        if markers is not None:
            log(f"Nhận diện Captcha qua marker: blue={markers['blue']}, green={markers['green']}", "CAPTCHA")
            return True

        if matcher is not None:
            if matcher.find_match(screen_img, "nut_tiktok") or matcher.find_match(screen_img, "nut_ok"):
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
            res_title = cv2.matchTemplate(screen_img, temp_title, cv2.TM_CCOEFF_NORMED)
            res_title[:640, :] = 0
            res_title[820:, :] = 0
            res_title[:, :100] = 0
            res_title[:, 140:] = 0
            _, score_title, _, _ = cv2.minMaxLoc(res_title)
            best_score = score_title
        else:
            # Thử nghiệm các tỷ lệ khác nhau xung quanh tỉ lệ chuẩn để tìm ra điểm số cao nhất
            base_scale = 2.667 * (screen_img.shape[1] / 1080.0)
            best_score = -1.0
            
            for scale_offset in [-0.25, 0.0, 0.25]:
                scale_val = base_scale + scale_offset
                tw = int(temp_title.shape[1] * scale_val)
                th = int(temp_title.shape[0] * scale_val)
                if tw <= 0 or th <= 0:
                    continue
                temp_scaled = cv2.resize(temp_title, (tw, th), interpolation=cv2.INTER_CUBIC)
                
                res_title = cv2.matchTemplate(screen_img, temp_scaled, cv2.TM_CCOEFF_NORMED)
                res_title[:200, :] = 0
                res_title[1400:, :] = 0
                res_title[:, :50] = 0
                res_title[:, 600:] = 0
                
                _, score_title, _, _ = cv2.minMaxLoc(res_title)
                if score_title > best_score:
                    best_score = score_title
                    
        thresh = 0.30 if scenario == 3 else self.threshold
        return best_score >= max(thresh + 0.22, 0.82)


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
            x_min_f, x_max_f = 30, int(width * 0.60)
        elif scenario == 3:
            y_min, y_max = 240, 650
            x_min_f, x_max_f = 20, int(width * 0.55)  # Khóa chặt cột bên trái nơi nút Follow luôn hiển thị
        else:
            y_min, y_max = 200, 750
            x_min_f, x_max_f = 20, int(width * 0.60)
        
        zone = screen_img[y_min:y_max, x_min_f:x_max_f]
        hsv = cv2.cvtColor(zone, cv2.COLOR_BGR2HSV)
        
        lower_red1 = np.array([0, 50, 70])
        upper_red1 = np.array([25, 255, 255])
        lower_red2 = np.array([155, 50, 70])
        upper_red2 = np.array([180, 255, 255])
        
        mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        best_match = None
        max_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 1200:  # Nút Follow kích thước lớn thực tế (~8000-15000px^2)
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = float(w) / h if h > 0 else 0
                if 1.5 < aspect_ratio < 6.0 and w > 90 and h > 25:
                    center_x = x_min_f + x + w // 2
                    center_y = y_min + y + h // 2
                    if area > max_area:
                        max_area = area
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
        
    # 2. Nếu không tìm thấy nút Follow -> Trả về False (để luồng ngoài báo lỗi)
    log("[TIKTOK] Không tìm thấy nút Follow trên màn hình TikTok.", "WARNING")
    return False


def solve_captcha(screen, adb, matcher, captcha_detector, scenario=3) -> bool:
    log("Phát hiện màn hình Captcha Xác minh nhanh! Bắt đầu giải...", "CAPTCHA")
    
    for attempt in range(1, 4):
        log(f"Đang quét tìm khối vuông và đích (Lần thử {attempt}/3)...", "CAPTCHA")
        
        height, width, _ = screen.shape
        marker_hint = captcha_detector.find_captcha_markers(screen)
        path = "templates/captcha_title_sc3.png" if scenario == 3 else "templates/captcha_title.png"
        if not os.path.exists(path):
            path = "templates/captcha_title.png"

        tx, ty = None, None
        if os.path.exists(path):
            temp_title = cv2.imread(path)
            if temp_title is not None:
                if scenario == 3 and path.endswith("captcha_title_sc3.png"):
                    res_title = cv2.matchTemplate(screen, temp_title, cv2.TM_CCOEFF_NORMED)
                    res_title[:640, :] = 0
                    res_title[820:, :] = 0
                    res_title[:, :100] = 0
                    res_title[:, 140:] = 0
                    _, score_title, _, loc_title = cv2.minMaxLoc(res_title)
                    if score_title >= 0.30:
                        tx, ty = loc_title
                else:
                    base_scale = 2.667 * (screen.shape[1] / 1080.0)
                    best_score = -1.0
                    best_loc = None
                    for scale_offset in [-0.25, 0.0, 0.25]:
                        scale_val = base_scale + scale_offset
                        tw = int(temp_title.shape[1] * scale_val)
                        th = int(temp_title.shape[0] * scale_val)
                        if tw <= 0 or th <= 0:
                            continue
                        temp_scaled = cv2.resize(temp_title, (tw, th), interpolation=cv2.INTER_CUBIC)
                        
                        res_title = cv2.matchTemplate(screen, temp_scaled, cv2.TM_CCOEFF_NORMED)
                        res_title[:200, :] = 0
                        res_title[1400:, :] = 0
                        res_title[:, :50] = 0
                        res_title[:, 600:] = 0
                        
                        _, score_title, _, loc_title = cv2.minMaxLoc(res_title)
                        if score_title > best_score:
                            best_score = score_title
                            best_loc = loc_title
                    if best_score >= 0.50:
                        tx, ty = best_loc
                
        if (tx is None or ty is None) and marker_hint is None:
            log("Không tìm thấy tiêu đề Captcha làm mốc quét. Bỏ qua...", "WARNING")
            time.sleep(2)
            screen = adb.get_screenshot()
            if screen is None:
                break
            continue
        elif tx is None or ty is None:
            tx = max(0, marker_hint["blue"][0] - 80)
            ty = max(0, min(marker_hint["blue"][1], marker_hint["green"][1]) - 170)
            
        # 1. TÌM CHÍNH XÁC HỘP THẺ TRẮNG CAPTCHA BÊN TRONG CỬA SỔ NỔI GOLIKE
        gray_screen = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        _, thresh_card = cv2.threshold(gray_screen, 245, 255, cv2.THRESH_BINARY)
        contours_card, _ = cv2.findContours(thresh_card, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        card_box = None
        if marker_hint is not None:
            bx, by = marker_hint["blue"]
            gx, gy = marker_hint["green"]
            left = max(0, min(bx, gx) - 120)
            top = max(0, min(by, gy) - 130)
            right = min(width, max(bx, gx) + 120)
            bottom = min(height, max(by, gy) + 210)
            if right - left >= 260 and bottom - top >= 220:
                card_box = (left, top, right - left, bottom - top)
        if card_box is None and scenario == 3:
            for cnt in contours_card:
                x, y, cw, ch = cv2.boundingRect(cnt)
                if 340 < cw < 520 and 180 < ch < 360 and y > 400:
                    card_box = (x, y, cw, ch)
                    break
                
        if card_box is not None:
            cx, cy, cw, ch = card_box
        else:
            if scenario == 3:
                cx = max(0, tx - 30)
                cy = max(0, ty + 60)
                cw = min(width - cx, 430)
                ch = min(height - cy, 300)
            else:
                scale_ratio = width / 1080.0
                cw = int(900 * scale_ratio)
                cx = max(0, (width - cw) // 2)
                cy = ty + int(40 * scale_ratio)
                ch = int(600 * scale_ratio)
                if cy + ch > height:
                    ch = height - cy
            
        card_bgr = screen[cy:cy+ch, cx:cx+cw]
        try:
            cv2.imwrite("debug_captcha_card.png", card_bgr)
        except:
            pass
        card_hsv = cv2.cvtColor(card_bgr, cv2.COLOR_BGR2HSV)
        card_gray = gray_screen[cy:cy+ch, cx:cx+cw]
        
        # 2. Phát hiện Khối vuông xanh dương (Start Point)
        mask_blue = cv2.inRange(card_hsv, np.array([95, 60, 150]), np.array([125, 255, 255]))
        cnts_b, _ = cv2.findContours(mask_blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        x1, y1 = None, None
        max_b_area = -1
        for cb in cnts_b:
            area = cv2.contourArea(cb)
            if area > 20 and area > max_b_area:
                bx, by, bw, bh = cv2.boundingRect(cb)
                # Khối xanh dương bắt buộc phải nằm ở 35% phía bên trái của thẻ
                if bx < cw * 0.35:
                    x1 = cx + bx + bw // 2
                    y1 = cy + by + bh // 2
                    max_b_area = area
                 
        if x1 is None or y1 is None:
            x1 = cx + int(cw * 0.12)
            y1 = cy + int(ch * 0.5)
            log("Không tìm thấy khối xanh qua HSV, dùng tọa độ mặc định.", "WARNING")
            
        # 3. Phát hiện Vòng tròn xanh lá (End Point)
        mask_green = cv2.inRange(card_hsv, np.array([35, 25, 20]), np.array([95, 255, 255]))
        cnts_g, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        x3, y3 = None, None
        max_g_area = -1
        for cg in cnts_g:
            area = cv2.contourArea(cg)
            if area > 2 and area > max_g_area:
                gx, gy, gw, gh = cv2.boundingRect(cg)
                # Vòng tròn xanh lá bắt buộc phải nằm ở 35% phía bên phải của thẻ
                if gx > cw * 0.65:
                    x3 = cx + gx + gw // 2
                    y3 = cy + gy + gh // 2
                    max_g_area = area
                 
        if x3 is None or y3 is None:
            x3 = cx + int(cw * 0.88)
            y3 = y1
            log("Không tìm thấy vòng tròn đích qua HSV, dùng tọa độ mặc định.", "WARNING")
            
        # 4. Phát hiện trực tiếp Vòng tròn Nét Đứt (Waypoint x2, y2)
        dot_x1 = int(cw * 0.15)
        dot_x2 = int(cw * 0.85)
        mid_gray = card_gray[:, dot_x1:dot_x2]
        mid_hsv = card_hsv[:, dot_x1:dot_x2]
        
        mask_dot = cv2.inRange(mid_gray, 0, 235)
        mask_dot_b = cv2.inRange(mid_hsv, np.array([85, 40, 40]), np.array([140, 255, 255]))
        mask_dot_g = cv2.inRange(mid_hsv, np.array([35, 25, 20]), np.array([95, 255, 255]))
        mask_dot = cv2.bitwise_and(mask_dot, cv2.bitwise_not(mask_dot_b))
        mask_dot = cv2.bitwise_and(mask_dot, cv2.bitwise_not(mask_dot_g))
        
        cnts_dot, _ = cv2.findContours(mask_dot, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        dashes = []
        for cd in cnts_dot:
            area = cv2.contourArea(cd)
            if 1 <= area < 100:
                bx, by, bw, bh = cv2.boundingRect(cd)
                d_cx = cx + dot_x1 + bx + bw // 2
                d_cy = cy + by + bh // 2
                # Chỉ lấy các nét đứt nằm trong khoảng giữa của thẻ
                if (cx + cw * 0.18) <= d_cx <= (cx + cw * 0.82):
                    dashes.append((d_cx, d_cy))
                    
        x2, y2 = None, None
        if len(dashes) >= 5:
            # Dùng Trung vị (Median) để tìm ra 100% TÂM HÌNH HỌC THỰC TẾ của vòng nét đứt, triệt tiêu mọi nhiễu
            xs = [p[0] for p in dashes]
            ys = [p[1] for p in dashes]
            x2 = int(np.median(xs))
            y2 = int(np.median(ys))
            log(f"Phát hiện CHUẨN XÁC Tâm Vòng Nét Đứt tại ({x2}, {y2}) [từ {len(dashes)} nét đứt]", "CAPTCHA")
                
        if x2 is None or y2 is None:
            x2 = (x1 + x3) // 2
            scale_ratio = cw / 900.0
            y2 = y1 - int(160 * scale_ratio)
            log(f"Dự phòng Vòng nét đứt tại ({x2}, {y2})", "WARNING")
            
        log("=== DEBUG CAPTCHA ===", "CAPTCHA")
        log(f"Thẻ Captcha: Y=[{cy}, {cy+ch}], X=[{cx}, {cx+cw}]", "CAPTCHA")
        log(f"Mốc tiêu đề (tx, ty): ({tx}, {ty})", "CAPTCHA")
        log(f"Khối xanh phát hiện: Blue({x1},{y1})", "CAPTCHA")
        log(f"Vòng tròn đích: Đích({x3},{y3})", "CAPTCHA")
        log(f"Nét đứt Waypoint: Nét đứt({x2},{y2})", "CAPTCHA")
        
        # Vẽ debug kết quả
        try:
            debug_res = card_bgr.copy()
            if x1 is not None and y1 is not None:
                cv2.circle(debug_res, (x1 - cx, y1 - cy), 15, (255, 0, 0), -1)
            if x3 is not None and y3 is not None:
                cv2.circle(debug_res, (x3 - cx, y3 - cy), 15, (0, 255, 0), 2)
            if x2 is not None and y2 is not None:
                cv2.circle(debug_res, (x2 - cx, y2 - cy), 10, (0, 0, 255), 1)
            cv2.imwrite("debug_captcha_result.png", debug_res)
        except:
            pass
        
        # 5. Tạo đường vuốt 2 chặng đi XUYÊN THẲNG VÀO TÂM VÒNG NÉT ĐỨT + RUNG TAY NGƯỜI THẬT
        path = []
        steps_per_seg = 12
        
        # Chặng 1: (x1, y1) -> ĐI VÀO TÂM VÒNG NÉT ĐỨT (x2, y2)
        c1x = int(0.5 * (x1 + x2))
        c1y = int(0.6 * y1 + 0.4 * y2)
        for i in range(steps_per_seg):
            t = i / float(steps_per_seg)
            bx = (1.0 - t)**2 * x1 + 2.0 * (1.0 - t) * t * c1x + t**2 * x2
            by = (1.0 - t)**2 * y1 + 2.0 * (1.0 - t) * t * c1y + t**2 * y2
            jx = int(round(bx)) + (random.choice([-1, 0, 1]) if 0 < i < steps_per_seg - 1 else 0)
            jy = int(round(by)) + (random.choice([-1, 0, 1]) if 0 < i < steps_per_seg - 1 else 0)
            path.append((jx, jy))
            
        # Chặng 2: TÂM VÒNG NÉT ĐỨT (x2, y2) -> ĐI VÀO TÂM VÒNG ĐÍCH (x3, y3)
        c2x = int(0.5 * (x2 + x3))
        c2y = int(0.4 * y2 + 0.6 * y3)
        for i in range(steps_per_seg + 1):
            t = i / float(steps_per_seg)
            bx = (1.0 - t)**2 * x2 + 2.0 * (1.0 - t) * t * c2x + t**2 * x3
            by = (1.0 - t)**2 * y2 + 2.0 * (1.0 - t) * t * c2y + t**2 * y3
            jx = int(round(bx)) + (random.choice([-1, 0, 1]) if 0 < i < steps_per_seg else 0)
            jy = int(round(by)) + (random.choice([-1, 0, 1]) if 0 < i < steps_per_seg else 0)
            path.append((jx, jy))
            
        # 6. Viết kịch bản Monkey Script (Tổng thời gian vuốt nhanh hơn 0.5s ~ 2.9 - 3.0 giây)
        monkey_lines = []
        monkey_lines.append("type= raw events")
        monkey_lines.append("count= 1000")
        monkey_lines.append("speed= 1.0")
        monkey_lines.append("start data >>")
        
        # DOWN event (chạm giữ 120ms để khóa ngón tay vào khối vuông)
        monkey_lines.append(f"DispatchPointer(0, 0, 0, {path[0][0]}, {path[0][1]}, 1.0, 1.0, 0, 0.0, 0.0, 0, 0)")
        monkey_lines.append("UserWait(120)")
        
        # MOVE events (Tốc độ 40ms/bước cho 24 bước = 960ms)
        for idx, (px, py) in enumerate(path[1:-1]):
            # idx + 1 == steps_per_seg tương ứng với waypoint (x2, y2) ở vị trí path[12]
            if idx + 1 == steps_per_seg:
                # Dừng lại 150ms tại vòng nét đứt để Android bắt tọa độ chính xác, tránh bị cắt góc
                monkey_lines.append(f"DispatchPointer(0, 0, 2, {px}, {py}, 1.0, 1.0, 0, 0.0, 0.0, 0, 0)")
                monkey_lines.append("UserWait(150)")
            else:
                monkey_lines.append(f"DispatchPointer(0, 0, 2, {px}, {py}, 1.0, 1.0, 0, 0.0, 0.0, 0, 0)")
                monkey_lines.append("UserWait(40)")
            
        # UP event (thả tay chính xác tại đích)
        monkey_lines.append(f"DispatchPointer(0, 0, 2, {path[-1][0]}, {path[-1][1]}, 1.0, 1.0, 0, 0.0, 0.0, 0, 0)")
        monkey_lines.append("UserWait(80)")
        monkey_lines.append(f"DispatchPointer(0, 0, 1, {path[-1][0]}, {path[-1][1]}, 1.0, 1.0, 0, 0.0, 0.0, 0, 0)")
        monkey_content = "\n".join(monkey_lines) + "\n"
        
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
        run_cmd.extend(['shell', 'monkey', '--pct-rotation', '0', '-f', device_path, '1'])
        
        try:
            log(f"Đang chạm giữ tại Blue ({x1}, {y1})...", "CAPTCHA")
            log(f"Đang kéo Bézier mượt mà qua Waypoint Nét đứt ({x2}, {y2})...", "CAPTCHA")
            log(f"Đang thả tay tại Đích ({x3}, {y3})...", "CAPTCHA")
            
            subprocess.run(push_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(run_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log("Đã chạy thành công lệnh monkey kéo thả Bézier mượt mà trên thiết bị.", "CAPTCHA")
        except Exception as e:
            log(f"Lỗi chạy script kéo Bézier: {e}", "ERROR")
            
        sleep_countdown(2.0, "Chờ kiểm tra kết quả Captcha")
        
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


def trigger_report_error(screen, adb, matcher):
    """
    Tự động thực hiện các bước báo lỗi công việc trên màn hình chi tiết job.
    """
    log("Hệ thống thông báo chưa hoàn thành (Lỗi). Tiến hành Báo lỗi tự động...", "WARNING")
    # 1. Bấm nút Báo lỗi
    match_bl = matcher.find_match(screen, "nut_bao_loi")
    if match_bl:
        log("Click Báo lỗi...", "JOB")
        adb.tap(match_bl[0], match_bl[1])
        time.sleep(1.5)
        
        # 2. Vuốt cuộn 5 nhịp ngắn
        log("Vuốt cuộn tìm nút Gửi báo cáo (5 nhịp)...", "JOB")
        for _ in range(5):
            adb.swipe(360, 1150, 360, 850, duration_ms=250)
            time.sleep(0.4)
        time.sleep(0.8)
        
        # 3. Bấm Gửi báo cáo
        bc_screen = adb.get_screenshot()
        if bc_screen is not None:
            match_gui_bc = matcher.find_match(bc_screen, "nut_gui_bao_cao")
            if match_gui_bc:
                log("Gửi báo cáo lỗi...", "JOB")
                adb.tap(match_gui_bc[0], match_gui_bc[1])
                time.sleep(3.0)
                
                # 4. Bấm OK xác nhận
                ok_bc_screen = adb.get_screenshot()
                if ok_bc_screen is not None:
                    match_ok_bc = matcher.find_match(ok_bc_screen, "nut_ok")
                    if match_ok_bc:
                        log("Bấm OK xác nhận báo cáo lỗi...", "INFO")
                        adb.tap(match_ok_bc[0], match_ok_bc[1])
                        time.sleep(2.0)
                        return True
    return False


def main():
    global completed_jobs
    
    log("==================================================================", "SUCCESS")
    log("🚀 KHỞI ĐỘNG THÀNH CÔNG - CHÚC LỤM MÚA ", "SUCCESS")
    log("==================================================================", "SUCCESS")
    
    adb = ModernADBController()
    devices = adb.check_connection()
    if not devices:
        log("Không tìm thấy thiết bị Android. Dừng bot.", "ERROR")
        sys.exit(1)
        
    adb.device_id = devices[0]
    log(f"Đã kết nối thiết bị: {adb.device_id}", "SUCCESS")
    
    # Khóa cứng điện thoại ở hướng dọc Portrait
    rot_cmd = ['adb']
    if adb.device_id:
        rot_cmd.extend(['-s', adb.device_id])
    subprocess.run(rot_cmd + ['shell', 'settings', 'put', 'system', 'user_rotation', '0'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(rot_cmd + ['shell', 'settings', 'put', 'system', 'accelerometer_rotation', '0'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    scenario = 2
    init_screen = adb.get_screenshot()
    width = 1080
    if init_screen is not None:
        width = init_screen.shape[1]
        
    scale = 0.70 if scenario == 3 else (width / 720.0)
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
            has_captcha = False
            
            # Chờ động tối đa 12 giây để Captcha, Chi tiết Job hoặc Popup xuất hiện
            start_wait = time.time()
            screen = None
            while time.time() - start_wait < 12.0:
                screen = adb.get_screenshot()
                if screen is not None:
                    # 1. Kiểm tra Captcha
                    if captcha_detector.is_captcha_present(screen, scenario, matcher):
                        has_captcha = True
                        break
                    # 2. Kiểm tra nếu đã chuyển sang Chi tiết Job
                    if matcher.find_match(screen, "header_chi_tiet"):
                        break
                    # 3. Kiểm tra nếu có popup cản trở (Thông báo / OK)
                    if matcher.find_match(screen, "nut_ok"):
                        break
                time.sleep(0.5)
                
            if has_captcha:
                log("Phát hiện màn hình Captcha Xác minh nhanh! Bắt đầu giải...", "CAPTCHA")
                for cap_att in range(3):
                    solve_captcha(screen, adb, matcher, captcha_detector, scenario)
                    sleep_countdown(2.5, "Chờ kết quả giải Captcha")
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

                # 1. Check popup thông báo OK (Sau khi bấm Hoàn thành)
                match_ok = matcher.find_match(screen, "nut_ok")
                if match_ok:
                    cx, cy, _ = match_ok
                    log("Bấm OK nhận kết quả Job...", "INFO")
                    adb.tap(cx, cy)
                    time.sleep(1.5)
                    
                    # Chụp màn hình mới sau khi bấm OK để kiểm tra xem đã về Home (Thành công) hay còn ở Chi tiết (Lỗi)
                    post_ok_screen = adb.get_screenshot()
                    if post_ok_screen is not None:
                        is_still_detail = matcher.find_match(post_ok_screen, "header_chi_tiet") is not None
                        match_bao_loi_now = matcher.find_match(post_ok_screen, "nut_bao_loi") is not None
                        
                        if is_still_detail or match_bao_loi_now:
                            trigger_report_error(post_ok_screen, adb, matcher)
                        else:
                            # TRƯỜNG HỢP 2: THÀNH CÔNG (Golike cộng xu và tự động đóng về Home)
                            completed_jobs += 1
                            log(f"Đã hoàn thành thành công {completed_jobs} job!", "SUCCESS")

                            if completed_jobs > 0 and completed_jobs % 10 == 0:
                                log(f"Đã chạy {completed_jobs} job. Nghỉ ngơi 60s...", "SUCCESS")
                                sleep_countdown(60.0, "Nghỉ ngơi phục hồi thiết bị")
                                
                    # Kết thúc chu trình job này và quay về Bước 1
                    break

                # 3. Giao diện Chi tiết Job: Mở TikTok / Hoàn thành
                match_header_ct = matcher.find_match(screen, "header_chi_tiet")
                if match_header_ct:
                    if not tiktok_clicked:
                        # Chỉ kiểm tra loại job khi chưa click mở TikTok
                        if scenario == 3:
                            zone_job = screen[500:750, 32:688]
                        else:
                            zone_job = screen[160:600, :]
                        is_like_job = False
                        # 1. Check by icon (job_like_indicator)
                        temp_data = matcher.loaded_templates.get("job_like_indicator")
                        if temp_data is not None:
                            job_like_scale = screen.shape[1] / 1080.0
                            tw = int(temp_data["image"].shape[1] * job_like_scale / matcher.scale)
                            th = int(temp_data["image"].shape[0] * job_like_scale / matcher.scale)
                            if tw > 0 and th > 0:
                                temp_img = cv2.resize(temp_data["image"], (tw, th), interpolation=cv2.INTER_AREA)
                                res = cv2.matchTemplate(zone_job, temp_img, cv2.TM_CCOEFF_NORMED)
                                _, max_val, _, _ = cv2.minMaxLoc(res)
                                if max_val >= temp_data["threshold"]:
                                    is_like_job = True
                        
                        # 2. Check by text (job_like_text)
                        if not is_like_job:
                            is_like_job = matcher.find_match(zone_job, "job_like_text") is not None
                        log(f"Loại Job nhận dạng: {'TIM/LIKE' if is_like_job else 'FOLLOW/THEO DÕI'}", "JOB")
                        
                        if is_like_job:
                            log("Phát hiện Job Tim/Like. Tự động báo lỗi bỏ qua theo yêu cầu...", "WARNING")
                            trigger_report_error(screen, adb, matcher)
                            break
                        
                    match_hoan_thanh = matcher.find_match(screen, "nut_hoan_thanh")
                    if match_hoan_thanh and tiktok_clicked and tiktok_action_done:
                        log("Bấm Hoàn thành...", "JOB")
                        adb.tap(match_hoan_thanh[0], match_hoan_thanh[1])
                        time.sleep(3.5)
                        continue
                        
                    match_tiktok = matcher.find_match(screen, "nut_tiktok")
                    if match_tiktok and not tiktok_clicked:
                        log("Bấm nút mở app TikTok...", "TIKTOK")
                        adb.tap(match_tiktok[0], match_tiktok[1])
                        tiktok_clicked = True
                        
                        sleep_countdown(8.0, "Chờ TikTok tải trang và ổn định")
                            
                        tiktok_action_done = False
                        # Thử quét liên tục trong 10 giây (mỗi giây thử 1 lần cho tới khi trang tải xong)
                        for load_att in range(10):
                            fresh_screen = adb.get_screenshot()
                            if fresh_screen is not None:
                                # Nếu phát hiện màn hình đã tự động quay về GoLike chi tiết (hệ thống lỗi)
                                if matcher.find_match(fresh_screen, "header_chi_tiet"):
                                    log("Phát hiện màn hình đã tự động quay về Chi tiết GoLike (Lỗi link/app). Không đợi nữa.", "WARNING")
                                    break
                                tiktok_action_done = perform_tiktok_action(fresh_screen, adb, matcher, is_like_job, scenario)
                                if tiktok_action_done:
                                    break
                            time.sleep(1.0)
                        
                        if tiktok_action_done:
                            log("Quay lại GoLike...", "TIKTOK")
                            adb.press_back()
                            sleep_countdown(1.0, "Chờ GoLike hiển thị")
                            log("[TIKTOK] Đã hoàn thành tương tác trên TikTok. Tiến hành bấm Hoàn thành ngay...", "JOB")
                            
                            # Sử dụng trực tiếp tọa độ đã tìm được trước đó để click NGAY LẬP TỨC
                            if match_hoan_thanh:
                                log("Bấm Hoàn thành...", "JOB")
                                adb.tap(match_hoan_thanh[0], match_hoan_thanh[1])
                                sleep_countdown(2.0, "Chờ phản hồi kết quả từ GoLike")
                            else:
                                post_screen = adb.get_screenshot()
                                if post_screen is not None:
                                    match_ht_now = matcher.find_match(post_screen, "nut_hoan_thanh")
                                    if match_ht_now:
                                        log("Bấm Hoàn thành...", "JOB")
                                        adb.tap(match_ht_now[0], match_ht_now[1])
                                        sleep_countdown(2.0, "Chờ phản hồi kết quả từ GoLike")
                        else:
                            log("Không thực hiện được tương tác trên TikTok sau thời gian chờ.", "WARNING")
                            check_scr = adb.get_screenshot()
                            if check_scr is not None and matcher.find_match(check_scr, "header_chi_tiet"):
                                log("Vẫn đang ở màn hình Chi tiết GoLike. Báo lỗi ngay...", "WARNING")
                                trigger_report_error(check_scr, adb, matcher)
                            else:
                                log("Đang ở màn hình khác. Quay lại GoLike để báo lỗi...", "WARNING")
                                adb.press_back()
                                sleep_countdown(2.5, "Quay lại GoLike để báo lỗi")
                                post_screen = adb.get_screenshot()
                                if post_screen is not None:
                                    trigger_report_error(post_screen, adb, matcher)
                            break
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
            print("------------------------------------------------------------------")
            
    except KeyboardInterrupt:
        log("Dừng bot.", "SUCCESS")
    except Exception as e:
        log(f"Lỗi hệ thống: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
