import cv2
import numpy as np
import os
import sys
import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from auto_clicker import TEMPLATES_CONFIG, TEMPLATES_DIR, TemplateMatcher, ModernADBController, CaptchaDetector
except ImportError as e:
    print(f"Loi: Khong the import cau hinh tu auto_clicker.py. Chi tiet: {e}")
    sys.exit(1)

def main():
    print("==================================================================")
    print("CHUONG TRINH CHAN DOAN & THU NGHIEM THIET BI (DIAGNOSTICS)")
    print("==================================================================")
    
    adb = ModernADBController()
    devices = adb.check_connection()
    if not devices:
        print("Loi: Khong tim thay thiet bi Android nao ket noi qua ADB.")
        sys.exit(1)
        
    adb.device_id = devices[0]
    print(f"Connected: {adb.device_id}")
    
    screen = adb.get_screenshot()
    if screen is None:
        print("Loi: Khong the chup man hinh.")
        sys.exit(1)
        
    height, width, _ = screen.shape
    print(f"Resolution: {width}x{height}")
    
    scale = width / 720.0
    print(f"Scale (Base 720p): {scale:.3f}")
    
    matcher = TemplateMatcher(TEMPLATES_DIR, scale=scale)
    diag_img = screen.copy()
    
    print("\n--- KET QUA SO KHOP ANH MAU (TEMPLATES MATCHING) ---")
    print(f"{'Template':<30} | {'Score':<9} | {'Thresh':<8} | {'Status':<10} | {'Coords (X, Y)'}")
    print("-" * 80)
    
    for name, config in TEMPLATES_CONFIG.items():
        if name not in matcher.loaded_templates:
            print(f"{name:<30} | {'Missing':<9} | {config['threshold']:<8} | {'SKIP':<10} | N/A")
            continue
            
        temp_data = matcher.loaded_templates[name]
        res = cv2.matchTemplate(screen, temp_data["image"], cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        
        req_thresh = config["threshold"]
        status = "MATCH" if max_val >= req_thresh else "NO"
        
        loc_str = f"({max_loc[0] + temp_data['w']//2}, {max_loc[1] + temp_data['h']//2})" if max_val >= req_thresh else f"({max_loc[0]}, {max_loc[1]})"
        print(f"{name:<30} | {max_val:.4f}  | {req_thresh:<8.2f} | {status:<10} | {loc_str}")
        
        if max_val >= req_thresh:
            cv2.rectangle(diag_img, max_loc, (max_loc[0] + temp_data["w"], max_loc[1] + temp_data["h"]), (0, 255, 0), 2)
            cv2.putText(diag_img, name, (max_loc[0], max_loc[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
    print("\n--- CAPTCHA STATUS ---")
    detector = CaptchaDetector(threshold=0.60)
    has_captcha = detector.is_captcha_present(screen, scenario=2, matcher=matcher)
    print(f"Is Captcha Present: {has_captcha}")
    
    out_filename = "diagnose_match_visual.png"
    cv2.imwrite(out_filename, diag_img)
    print(f"\nSaved visual diag to: {out_filename}")
    print("==================================================================")

if __name__ == "__main__":
    main()
