import os
import sys
import cv2
import numpy as np
import subprocess

def get_screenshot(device_id=None):
    cmd = ['adb']
    if device_id:
        cmd.extend(['-s', device_id])
    cmd.extend(['exec-out', 'screencap', '-p'])
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0 or not stdout:
            return None
        image_array = np.frombuffer(stdout, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        return image
    except Exception as e:
        print(f"Lỗi chụp màn hình: {e}")
        return None

def check_connection():
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
    except Exception as e:
        print(f"Lỗi adb: {e}")
        return []

def main():
    print("==================================================")
    print("      CHƯƠNG TRÌNH DEBUG CAPTCHA GOLIKE")
    print("==================================================")
    
    devices = check_connection()
    if not devices:
        print("❌ Không tìm thấy thiết bị Android nào qua ADB!")
        sys.exit(1)
        
    device_id = devices[0]
    print(f"✅ Đang kết nối tới thiết bị: {device_id}")
    
    screen = get_screenshot(device_id)
    if screen is None:
        print("❌ Không thể chụp ảnh màn hình thiết bị!")
        sys.exit(1)
        
    # 1. Lưu ảnh gốc màn hình
    cv2.imwrite("debug_screen_original.png", screen)
    print("💾 Đã lưu ảnh gốc màn hình: 'debug_screen_original.png'")
    
    height, width, _ = screen.shape
    print(f"ℹ️ Kích thước màn hình: {width}x{height}")
    
    # Tìm mốc tiêu đề
    scenario = 3
    template_path = "templates/captcha_title_sc3.png" if scenario == 3 else "templates/captcha_title.png"
    if not os.path.exists(template_path):
        template_path = "templates/captcha_title.png"
    if not os.path.exists(template_path):
        print(f"❌ Thiếu ảnh mẫu tiêu đề tại '{template_path}'!")
        sys.exit(1)
        
    temp_title = cv2.imread(template_path)
    tx, ty = None, None
    
    if scenario == 3 and template_path.endswith("captcha_title_sc3.png"):
        temp_scaled = temp_title
    else:
        scale_val = 2.667
        tw = int(temp_title.shape[1] * scale_val)
        th = int(temp_title.shape[0] * scale_val)
        temp_scaled = cv2.resize(temp_title, (tw, th), interpolation=cv2.INTER_CUBIC)
        
    tw = temp_scaled.shape[1]
    th = temp_scaled.shape[0]
    res_title = cv2.matchTemplate(screen, temp_scaled, cv2.TM_CCOEFF_NORMED)
    
    # Ràng buộc tìm tiêu đề ở nửa dưới và giữa màn hình
    if scenario == 3:
        res_title[:640, :] = 0
        res_title[820:, :] = 0
        # Ràng buộc tìm tiêu đề X (sát mép trái cửa sổ nổi)
        res_title[:, :100] = 0
        res_title[:, 140:] = 0
    else:
        res_title[:450, :] = 0
        res_title[850:, :] = 0
        res_title[:, :160] = 0
        res_title[:, 300:] = 0
        
    min_val, score_title, min_loc, loc_title = cv2.minMaxLoc(res_title)
    
    thresh_title = 0.30 if scenario == 3 else 0.50
    print(f"ℹ️ Điểm trùng khớp tiêu đề: {score_title:.4f} (Ngưỡng = {thresh_title:.2f})")
    if score_title >= thresh_title:
        tx, ty = loc_title
        print(f"✅ Tìm thấy tiêu đề tại tọa độ: ({tx}, {ty})")
    else:
        print("❌ Không tìm thấy tiêu đề trên màn hình!")
        tx, ty = width // 2 - 200, height // 2 - 200
        print(f"⚠️ Sử dụng tọa độ giả định ở giữa: ({tx}, {ty})")
        
    debug_result = screen.copy()
    if tx is not None and ty is not None:
        cv2.rectangle(debug_result, (tx, ty), (tx + tw, ty + th), (0, 0, 255), 2)
        cv2.putText(debug_result, f"Title ({score_title:.2f})", (tx, ty - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # 2. Định vị vùng quét động (ROI) và các ngưỡng kích thước theo Scenario
    if scenario == 3:
        # ROI quét Blue (nửa trái card)
        x_min_blue = max(0, tx + 15)
        x_max_blue = min(width, tx + 140)
        y_min = max(0, ty + 60)
        y_max = min(height, ty + 115)
        
        # Ngưỡng kích thước Blue Square
        min_sz_b, max_sz_b = 20, 80
        
        # ROI quét Green (nửa phải card)
        x_min_green = max(0, tx + 200)
        x_max_green = min(width, tx + 480)
        min_radius, max_radius = 15, 30
        y_limit_min = ty + 60
        y_limit_max = ty + 115
        
        # Kích thước Green bằng lọc màu (nếu có)
        min_sz_g, max_sz_g = 20, 90
    else:
        # ROI quét Blue (nửa trái card)
        x_min_blue = max(0, tx - 150)
        x_max_blue = min(width, tx + 200)
        y_min = max(0, ty + 60)
        y_max = min(height, ty + 420)
        
        # Ngưỡng kích thước Blue Square
        min_sz_b, max_sz_b = 35, 110
        
        # ROI quét Green (nửa phải card)
        x_min_green = max(0, tx + 300)
        x_max_green = min(width, tx + 650)
        min_radius, max_radius = 25, 45
        y_limit_min = ty + 50
        y_limit_max = ty + 180
        
        # Kích thước Green bằng lọc màu (nếu có)
        min_sz_g, max_sz_g = 35, 130

    print(f"ℹ️ Vùng quét ROI Blue (nửa trái): X=[{x_min_blue} -> {x_max_blue}], Y=[{y_min} -> {y_max}]")
    print(f"ℹ️ Vùng quét ROI Green (nửa phải): X=[{x_min_green} -> {x_max_green}], Y=[{y_min} -> {y_max}]")
    cv2.rectangle(debug_result, (x_min_blue, y_min), (x_max_blue, y_max), (255, 255, 0), 1)
    cv2.rectangle(debug_result, (x_min_green, y_min), (x_max_green, y_max), (0, 255, 255), 1)
    
    hsv = cv2.cvtColor(screen, cv2.COLOR_BGR2HSV)
    
    # 3. Phân tích Khối vuông màu xanh dương (chỉ tìm trong nửa trái card)
    lower_blue = np.array([80, 8, 50])
    upper_blue = np.array([135, 255, 255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
    
    mask_blue_roi = np.zeros_like(mask_blue)
    mask_blue_roi[y_min:y_max, x_min_blue:x_max_blue] = mask_blue[y_min:y_max, x_min_blue:x_max_blue]
    
    cv2.imwrite("debug_mask_blue.png", mask_blue_roi)
    print("💾 Đã lưu ảnh mask xanh dương: 'debug_mask_blue.png'")
    
    # Giãn nở dọc (Vertical Dilation) để nối liền các mảnh bị đứt gãy do nền TikTok trong suốt
    kernel = np.ones((15, 3), np.uint8)
    mask_blue_roi = cv2.dilate(mask_blue_roi, kernel, iterations=1)
    
    contours_blue, _ = cv2.findContours(mask_blue_roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours_blue = sorted(contours_blue, key=cv2.contourArea, reverse=True)
    print(f"\n--- DANH SÁCH CONTOUR XANH DƯƠNG (Tổng: {len(contours_blue)}) ---")
    
    blue_center = None
    for idx, c in enumerate(contours_blue):
        area = cv2.contourArea(c)
        x, y, bw, bh = cv2.boundingRect(c)
        aspect = float(bw) / bh if bh > 0 else 0
        is_match = (min_sz_b <= bw <= 100) and (10 <= bh <= max_sz_b) and (0.50 < aspect < 2.50)
        
        print(f"Contour #{idx}: Area={area:.1f}, BBox=[{x},{y}, w={bw},h={bh}], Aspect={aspect:.2f} | Trùng khớp bộ lọc: {is_match}")
        
        color = (0, 255, 0) if is_match else (0, 0, 100)
        cv2.rectangle(debug_result, (x, y), (x + bw, y + bh), color, 1)
        cv2.putText(debug_result, f"B{idx}(a={area:.0f})", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        if is_match and blue_center is None:
            blue_center = (x + min(bw, bh)//2, y + bh//2)
            cv2.circle(debug_result, blue_center, 6, (0, 255, 0), -1)
            print(f"🎯 ĐÃ PHÁT HIỆN KHỐI VUÔNG BLUE TẠI: {blue_center}")

    if blue_center is None:
        print("\n⚠️ Bộ lọc màu HSV Blue thất bại. Chuyển sang quét BGR Fallback...")
        b_ch, g_ch, r_ch = cv2.split(screen)
        bgr_mask = (b_ch > g_ch + 20) & (b_ch > r_ch - 10) & (b_ch > 50) & (r_ch < 160)
        mask_bgr = bgr_mask.astype(np.uint8) * 255
        
        mask_bgr_roi = np.zeros_like(mask_bgr)
        mask_bgr_roi[y_min:y_max, x_min_blue:x_max_blue] = mask_bgr[y_min:y_max, x_min_blue:x_max_blue]
        
        contours_bgr, _ = cv2.findContours(mask_bgr_roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        print(f"--- DANH SÁCH CONTOUR BGR BLUE (Tổng: {len(contours_bgr)}) ---")
        for idx, c in enumerate(contours_bgr):
            area = cv2.contourArea(c)
            x, y, bw, bh = cv2.boundingRect(c)
            aspect = float(bw) / bh if bh > 0 else 0
            is_match = (min_sz_b <= bw <= 100) and (10 <= bh <= max_sz_b) and (0.50 < aspect < 2.50)
            
            print(f"BGR Contour #{idx}: Area={area:.1f}, BBox=[{x},{y}, w={bw},h={bh}], Aspect={aspect:.2f} | Trùng khớp: {is_match}")
            
            color = (0, 200, 255) if is_match else (0, 0, 100)
            cv2.rectangle(debug_result, (x, y), (x + bw, y + bh), color, 1)
            
            if is_match and blue_center is None:
                blue_center = (x + min(bw, bh)//2, y + bh//2)
                cv2.circle(debug_result, blue_center, 6, (0, 200, 255), -1)
                print(f"🎯 ĐÃ PHÁT HIỆN KHỐI VUÔNG BLUE (BGR FALLBACK) TẠI: {blue_center}")

    # 4. Phân tích Vòng tròn đích màu xanh lá
    lower_green = np.array([35, 12, 35])
    upper_green = np.array([95, 255, 255])
    mask_green = cv2.inRange(hsv, lower_green, upper_green)
    
    mask_green_roi = np.zeros_like(mask_green)
    mask_green_roi[y_min:y_max, x_min_green:x_max_green] = mask_green[y_min:y_max, x_min_green:x_max_green]
    
    cv2.imwrite("debug_mask_green.png", mask_green_roi)
    print("💾 Đã lưu ảnh mask xanh lá: 'debug_mask_green.png'")
    
    contours_green, _ = cv2.findContours(mask_green_roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"\n--- DANH SÁCH CONTOUR XANH LÁ (Tổng: {len(contours_green)}) ---")
    
    green_center = None
    for idx, c in enumerate(contours_green):
        area = cv2.contourArea(c)
        x, y, gw, gh = cv2.boundingRect(c)
        aspect = float(gw) / gh if gh > 0 else 0
        is_match = (min_sz_g <= gw <= max_sz_g) and (min_sz_g <= gh <= max_sz_g) and (0.60 < aspect < 1.60)
        
        print(f"Contour #{idx}: Area={area:.1f}, BBox=[{x},{y}, w={gw},h={gh}], Aspect={aspect:.2f} | Trùng khớp bộ lọc: {is_match}")
        
        color = (255, 0, 0) if is_match else (0, 0, 100)
        cv2.rectangle(debug_result, (x, y), (x + gw, y + gh), color, 1)
        cv2.putText(debug_result, f"G{idx}(a={area:.0f})", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        if is_match and green_center is None:
            green_center = (x + gw//2, y + gh//2)
            cv2.circle(debug_result, green_center, 6, (255, 0, 0), -1)
            print(f"🎯 ĐÃ PHÁT HIỆN VÒNG TRÒN GREEN (BẰNG MÀU) TẠI: {green_center}")

    # Fallback Hough Circles
    if green_center is None and blue_center is not None:
        print("\n⚠️ Bộ lọc màu Green thất bại (do đổi sắc độ). Chuyển sang quét Hough Circles...")
        roi_green = screen[y_min:y_max, x_min_green:x_max_green]
        gray = cv2.cvtColor(roi_green, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1, minDist=30,
                                   param1=50, param2=15, minRadius=min_radius, maxRadius=max_radius)
        if circles is not None:
            circles = np.uint16(np.around(circles))
            candidates = []
            for idx, circle in enumerate(circles[0, :]):
                real_x = x_min_green + circle[0]
                real_y = y_min + circle[1]
                radius = circle[2]
                
                # Ràng buộc hình học
                geom_ok = (real_x > tx + 200) and (y_limit_min <= real_y <= y_limit_max)
                print(f"Ứng viên Hough Circle #{idx}: Center=({real_x}, {real_y}), Radius={radius} | Hình học OK: {geom_ok}")
                
                if geom_ok:
                    candidates.append((real_x, real_y, radius))
                    cv2.circle(debug_result, (real_x, real_y), radius, (255, 100, 0), 1)
                    
            if candidates:
                blue_y = blue_center[1]
                best_candidate = min(candidates, key=lambda c: abs(int(c[1]) - int(blue_y)))
                green_center = (int(best_candidate[0]), int(best_candidate[1]))
                cv2.circle(debug_result, green_center, 6, (0, 255, 255), -1)
                print(f"🎯 ĐÃ PHÁT HIỆN VÒNG TRÒN GREEN (HOUGH CIRCLES) TẠI: {green_center}")

    # 5. Lưu ảnh kết quả cuối cùng
    cv2.imwrite("debug_result_detected.png", debug_result)
    print("\n==================================================")
    print("💾 Đã lưu ảnh kết quả vẽ định vị: 'debug_result_detected.png'")
    
    print(f"➡️ Kết quả in ra Terminal:")
    print(f"  - Tọa độ Blue Square: {blue_center}")
    print(f"  - Tọa độ Green Target: {green_center}")
    print("==================================================")

if __name__ == "__main__":
    main()
