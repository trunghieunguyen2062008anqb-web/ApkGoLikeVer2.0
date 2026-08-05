import cv2
import numpy as np
import os
import sys
from auto_clicker import ADBController, TemplateMatcher, TEMPLATES_CONFIG, TEMPLATES_DIR

def run_debug():
    print("=====================================================")
    print("         DIAGNOSTIC TEMPLATE MATCHING TOOL           ")
    print("=====================================================")
    
    adb = ADBController()
    devices = adb.check_connection()
    if not devices:
        print("[ERROR] Không tìm thấy thiết bị Android. Hãy cắm cáp và bật USB Debugging.")
        return
        
    adb.device_id = devices[0]
    print(f"[INFO] Đang kết nối tới thiết bị: {adb.device_id}")
    
    print("[INFO] Đang chụp màn hình điện thoại...")
    screen = adb.get_screenshot()
    if screen is None:
        print("[ERROR] Không thể chụp màn hình điện thoại qua ADB.")
        return
        
    h, w = screen.shape[:2]
    print(f"[INFO] Độ phân giải ảnh chụp: {w}x{h}")
    
    # Lưu ảnh chụp màn hình thô
    cv2.imwrite("debug_raw_screenshot.png", screen)
    print("[INFO] Đã lưu ảnh chụp gốc thành debug_raw_screenshot.png")
    
    matcher = TemplateMatcher(TEMPLATES_DIR)
    
    # Vẽ kết quả lên ảnh để kiểm tra trực quan
    output_img = screen.copy()
    
    print("\n--- BẮT ĐẦU QUÉT ẢNH MẪU ---")
    for name, config in TEMPLATES_CONFIG.items():
        template_path = os.path.join(TEMPLATES_DIR, config["filename"])
        if not os.path.exists(template_path):
            print(f"[-] {name}: Không tìm thấy file '{template_path}'")
            continue
            
        temp = cv2.imread(template_path)
        if temp is None:
            print(f"[-] {name}: Lỗi đọc file '{template_path}'")
            continue
            
        th, tw = temp.shape[:2]
        
        # Chạy matchTemplate
        res = cv2.matchTemplate(screen, temp, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        status = "✅ KHỚP" if max_val >= config["threshold"] else "❌ KHÔNG KHỚP"
        print(f"[{status}] {name} ({config['description']}):")
        print(f"  - Điểm số khớp tốt nhất: {max_val:.4f} (Ngưỡng yêu cầu: {config['threshold']})")
        print(f"  - Tọa độ tìm thấy (Top-Left): {max_loc}")
        print(f"  - Kích thước ảnh mẫu: {tw}x{th}")
        
        # Vẽ khung chữ nhật lên ảnh output
        color = (0, 255, 0) if max_val >= config["threshold"] else (0, 0, 255)
        # Điểm center
        cx, cy = max_loc[0] + tw // 2, max_loc[1] + th // 2
        cv2.rectangle(output_img, max_loc, (max_loc[0] + tw, max_loc[1] + th), color, 3)
        cv2.putText(output_img, f"{name}: {max_val:.2f}", (max_loc[0], max_loc[1] - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    
    # Lưu ảnh kết quả
    cv2.imwrite("debug_matching_result.png", output_img)
    print("\n=====================================================")
    print("[SUCCESS] Đã quét xong! Kết quả trực quan được lưu tại:")
    print("👉 debug_matching_result.png")
    print("Sếp hãy mở file debug_matching_result.png để xem ô đỏ/xanh nhé!")
    print("=====================================================")

if __name__ == "__main__":
    run_debug()
