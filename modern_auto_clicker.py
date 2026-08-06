import os
import sys
import time
import subprocess
import random
import cv2
import numpy as np
import datetime
import threading
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver

# Import mô-đun AI Captcha Solver mới
from ai_captcha_solver import (
    CaptchaDetector,
    YoloCaptchaDetector,
    BezierTrajectoryGenerator,
    ADBScriptExecutor
)

# Khởi tạo hỗ trợ màu ANSI trên Windows Terminal
if sys.platform.startswith('win'):
    os.system('')

# ANSI Colors
COLOR_GREEN = "\x1b[1;92m"
COLOR_RED = "\x1b[1;91m"
COLOR_YELLOW = "\x1b[1;93m"
COLOR_BLUE = "\x1b[1;94m"
COLOR_CYAN = "\x1b[1;96m"
COLOR_MAGENTA = "\x1b[1;95m"
COLOR_RESET = "\x1b[0m"
COLOR_GRAY = "\x1b[1;90m"

# ==========================================
# CẤU HÌNH LIÊN THÔNG VỚI WEB SOLVER LIVE
# ==========================================
PORT = 5000
RAW_DIR = "dataset/raw_captchas"

# Biến toàn cục chia sẻ giữa Web Server Thread và Main Bot Thread
captcha_event = threading.Event()
captcha_coordinates = None
captcha_active = False
completed_jobs = 0
current_status = "Đang khởi động bot..."

# Logger đẹp mắt
def log(msg, level="INFO"):
    global current_status
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
        prefix_lvl = "[CAPTCHA] 🧩"
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
    current_status = msg
    
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

# ==========================================
# GIAO DIỆN WEB GIẢI CAPTCHA LIVE SIÊU ĐẸP
# HỖ TRỢ CẢ CHẾ ĐỘ GIẢI LIVE VÀ DÁN NHÃN OFFLINE
# ==========================================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Captcha Live Solver & Labeler</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #070913;
            --bg-card: #0F1326;
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
        }

        header {
            width: 100%;
            padding: 20px 40px;
            background: rgba(15, 19, 38, 0.7);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        header h1 {
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(45deg, var(--primary), var(--blue-target));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .tabs-menu {
            display: flex;
            gap: 10px;
            background: rgba(255,255,255,0.02);
            padding: 5px;
            border-radius: 12px;
            border: 1px solid rgba(255,255,255,0.05);
        }

        .tab-btn {
            padding: 8px 16px;
            font-size: 14px;
            font-weight: 600;
            color: var(--text-muted);
            background: transparent;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            transition: all 0.2s ease;
            width: auto;
        }

        .tab-btn.active {
            color: white;
            background: var(--primary);
        }

        .container {
            max-width: 1200px;
            width: 100%;
            padding: 30px 20px;
            display: grid;
            grid-template-columns: 1.5fr 1fr;
            gap: 30px;
            flex-grow: 1;
        }

        .workspace-card {
            background-color: var(--bg-card);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 25px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
            position: relative;
            min-height: 550px;
        }

        .canvas-container {
            position: relative;
            cursor: crosshair;
            border-radius: 16px;
            overflow: hidden;
            border: 2px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        }

        #captcha-image {
            display: block;
            max-width: 100%;
            max-height: 70vh;
            height: auto;
            user-select: none;
            -webkit-user-drag: none;
        }

        .click-marker {
            position: absolute;
            transform: translate(-50%, -50%);
            pointer-events: none;
            box-shadow: 0 0 15px rgba(0,0,0,0.5);
        }

        .marker-blue {
            width: 35px;
            height: 35px;
            border: 3px solid var(--blue-target);
            background-color: rgba(0, 210, 255, 0.25);
            border-radius: 4px;
        }

        .marker-green {
            width: 40px;
            height: 40px;
            border: 3px dashed var(--green-target);
            background-color: rgba(0, 255, 135, 0.25);
            border-radius: 50%;
        }

        .control-panel {
            display: flex;
            flex-direction: column;
            gap: 25px;
        }

        .card {
            background-color: var(--bg-card);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }

        h2 {
            font-size: 20px;
            margin-bottom: 10px;
            font-weight: 600;
        }

        p.desc {
            color: var(--text-muted);
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 20px;
        }

        .step-indicator {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.04);
            padding: 14px 18px;
            border-radius: 12px;
            font-size: 14px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
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
            padding: 15px 20px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 14px;
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
            box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4);
        }

        .btn-secondary {
            background-color: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
            border: 1px solid rgba(255, 255, 255, 0.08);
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

        .status-box {
            display: flex;
            align-items: center;
            gap: 15px;
            background: rgba(255,255,255,0.02);
            padding: 15px;
            border-radius: 14px;
            border: 1px solid rgba(255, 255, 255, 0.04);
            margin-bottom: 20px;
        }

        .pulse-dot {
            width: 12px;
            height: 12px;
            background-color: #10B981;
            border-radius: 50%;
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
            animation: pulse 1.6s infinite;
        }

        .pulse-dot.active {
            background-color: #EF4444;
            box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
        }

        @keyframes pulse {
            0% {
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
            }
            70% {
                transform: scale(1);
                box-shadow: 0 0 0 10px rgba(16, 185, 129, 0);
            }
            100% {
                transform: scale(0.95);
                box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
            }
        }

        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }

        .stat-box {
            background: rgba(255,255,255,0.02);
            padding: 15px;
            border-radius: 14px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.04);
        }

        .stat-val {
            font-size: 28px;
            font-weight: 800;
            color: var(--primary);
            margin-top: 5px;
        }

        .waiting-state {
            text-align: center;
            padding: 40px;
        }

        .waiting-state h3 {
            font-size: 22px;
            margin-bottom: 12px;
            font-weight: 600;
        }

        .loading-ring {
            display: inline-block;
            width: 50px;
            height: 50px;
            border: 3px solid rgba(99, 102, 241, 0.2);
            border-radius: 50%;
            border-top-color: var(--primary);
            animation: spin 1s ease-in-out infinite;
            margin-bottom: 20px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <header>
        <h1>AI Captcha Live Solver & Labeler</h1>
        <div class="tabs-menu">
            <button id="tab-live" class="tab-btn active" onclick="switchTab('live')">Giải Live (Trực tiếp)</button>
            <button id="tab-offline" class="tab-btn" onclick="switchTab('offline')">Dán nhãn dữ liệu có sẵn</button>
        </div>
    </header>

    <div class="container">
        <!-- Vùng làm việc chính bên trái -->
        <div class="workspace-card" id="workspace">
            <!-- Vùng tương tác ảnh live & offline -->
            <div class="canvas-container" id="canvas-container" onclick="handleCanvasClick(event)" style="display: none;">
                <img id="captcha-image" src="" alt="Captcha Target">
                <div id="blue-marker" class="click-marker marker-blue" style="display: none;"></div>
                <div id="green-marker" class="click-marker marker-green" style="display: none;"></div>
            </div>
            
            <!-- Trạng thái chờ Captcha (Chế độ Live) -->
            <div id="waiting-message" class="waiting-state">
                <div class="loading-ring"></div>
                <h3>🤖 Bot đang cày tự động...</h3>
                <p class="desc">Hệ thống hoạt động ngầm. Khi xuất hiện Captcha trên điện thoại, giao diện web sẽ tự phát âm thanh và hiển thị ảnh tại đây để bạn giải thủ công.</p>
            </div>

            <!-- Trạng thái trống (Chế độ Offline) -->
            <div id="empty-message" class="waiting-state" style="display: none;">
                <h3>🎉 Tuyệt vời! Đã gán nhãn xong</h3>
                <p class="desc">Không còn ảnh Captcha thô nào cần gán nhãn trong thư mục dataset/raw_captchas.</p>
            </div>
        </div>

        <!-- Bảng điều khiển bên phải -->
        <div class="control-panel">
            <div class="card">
                <div class="status-box" id="bot-status-container">
                    <div id="status-dot" class="pulse-dot"></div>
                    <div>
                        <div style="font-size: 12px; color: var(--text-muted); font-weight: 600;">TRẠNG THÁI BOT</div>
                        <div id="status-text" style="font-size: 15px; font-weight: 600;">Đang hoạt động...</div>
                    </div>
                </div>

                <h2 id="panel-title">Giải Captcha Live</h2>
                <p class="desc" id="panel-desc">Khi xuất hiện màn hình Captcha, vui lòng định vị 2 điểm chuẩn trên ảnh:</p>
                
                <div class="step-indicator">
                    <span>Bước 1: Khối trượt màu xanh lam</span>
                    <span id="step1-status" class="step-active">Đợi click...</span>
                </div>
                <div class="step-indicator">
                    <span>Bước 2: Tâm vòng tròn đích đến</span>
                    <span id="step2-status" style="color: var(--text-muted);">Đợi click...</span>
                </div>

                <div class="btn-group">
                    <button id="btn-save" class="btn-primary" onclick="submitSolve()">Giải & Tiếp tục (Enter)</button>
                    <button class="btn-secondary" onclick="resetClicks()">Reset click (R)</button>
                    <button id="btn-skip" class="btn-danger" onclick="skipOfflineImage()" style="display: none;">Bỏ qua ảnh này (S)</button>
                </div>
            </div>

            <div class="card">
                <h2>Báo cáo hiệu suất</h2>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div>Job Hoàn Thành</div>
                        <div class="stat-val" id="stat-completed" style="color: var(--green-target);">0</div>
                    </div>
                    <div class="stat-box">
                        <div>Đã dán nhãn</div>
                        <div class="stat-val" id="stat-labeled">0</div>
                    </div>
                </div>
                
                <div style="margin-top: 25px;">
                    <button id="btn-train" class="btn-primary" style="background: linear-gradient(135deg, #00FF87, #00D2FF); color: #070913;" onclick="startTraining()">
                        🚀 Train mô hình YOLOv8
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let clicks = [];
        let currentTab = "live"; // "live" hoặc "offline"
        let isCaptchaActive = false;
        let audioCtx = null;
        
        // Trạng thái Offline Mode
        let offlineImagesList = [];
        let currentOfflineIndex = 0;

        // Chuyển đổi tab
        function switchTab(tabName) {
            currentTab = tabName;
            document.getElementById("tab-live").classList.remove("active");
            document.getElementById("tab-offline").classList.remove("active");
            
            if (tabName === "live") {
                document.getElementById("tab-live").classList.add("active");
                document.getElementById("bot-status-container").style.display = "flex";
                document.getElementById("panel-title").innerText = "Giải Captcha Live";
                document.getElementById("panel-desc").innerText = "Khi xuất hiện màn hình Captcha, vui lòng định vị 2 điểm chuẩn trên ảnh:";
                document.getElementById("btn-save").innerText = "Giải & Tiếp tục (Enter)";
                document.getElementById("btn-skip").style.display = "none";
                document.getElementById("empty-message").style.display = "none";
                
                if (isCaptchaActive) {
                    loadCaptchaImage();
                } else {
                    showWaiting();
                }
            } else {
                document.getElementById("tab-offline").classList.add("active");
                document.getElementById("bot-status-container").style.display = "none";
                document.getElementById("panel-title").innerText = "Dán nhãn ảnh mẫu";
                document.getElementById("panel-desc").innerText = "Nhấp chọn tâm khối trượt, tâm vòng tròn đích để dán nhãn tập huấn luyện:";
                document.getElementById("btn-save").innerText = "Lưu & Tiếp tục (Enter)";
                document.getElementById("btn-skip").style.display = "block";
                document.getElementById("waiting-message").style.display = "none";
                
                fetchOfflineImages();
            }
        }

        // Phát âm thanh cảnh báo khi có Captcha xuất hiện
        function playWarningBeep() {
            try {
                if (!audioCtx) {
                    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                }
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                
                osc.type = "sine";
                osc.frequency.setValueAtTime(880, audioCtx.currentTime);
                gain.gain.setValueAtTime(0.5, audioCtx.currentTime);
                
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                
                osc.start();
                osc.stop(audioCtx.currentTime + 0.35);
                
                if (navigator.vibrate) {
                    navigator.vibrate([200, 100, 200]);
                }
            } catch (err) {
                console.log(err);
            }
        }

        // Định kỳ kiểm tra trạng thái từ Bot (chỉ cần thiết cho Live Mode)
        async function checkStatus() {
            try {
                const res = await fetch("/api/status");
                const data = await res.json();
                
                document.getElementById("stat-completed").innerText = data.completed_jobs;
                document.getElementById("stat-labeled").innerText = data.labeled_count;
                document.getElementById("status-text").innerText = data.status;

                // Nếu đang ở Live Tab và phát hiện trạng thái Captcha đổi
                if (currentTab === "live") {
                    if (data.captcha_active && !isCaptchaActive) {
                        isCaptchaActive = true;
                        playWarningBeep();
                        loadCaptchaImage();
                    } else if (!data.captcha_active && isCaptchaActive) {
                        isCaptchaActive = false;
                        showWaiting();
                    }
                } else {
                    // Nếu ở tab Offline nhưng có captcha xuất hiện -> Cảnh báo
                    if (data.captcha_active && !isCaptchaActive) {
                        isCaptchaActive = true;
                        playWarningBeep();
                        if (confirm("🚨 PHÁT HIỆN CAPTCHA LIVE! Bạn có muốn chuyển sang Tab Live để giải ngay không?")) {
                            switchTab("live");
                        }
                    } else if (!data.captcha_active) {
                        isCaptchaActive = false;
                    }
                }

                // Cập nhật chấm xung nhịp
                const dot = document.getElementById("status-dot");
                if (data.captcha_active) {
                    dot.classList.add("active");
                } else {
                    dot.classList.remove("active");
                }
            } catch (err) {
                console.error("Lỗi kết nối API:", err);
            }
        }

        // Fetch danh sách ảnh chưa dán nhãn cho Offline mode
        async function fetchOfflineImages() {
            try {
                const res = await fetch("/api/images");
                const data = await res.json();
                offlineImagesList = data.unlabeled;
                
                if (offlineImagesList.length > 0) {
                    currentOfflineIndex = 0;
                    loadOfflineImage(offlineImagesList[0]);
                } else {
                    showEmpty();
                }
            } catch (err) {
                console.error(err);
            }
        }

        function loadOfflineImage(imgFilename) {
            const imgEl = document.getElementById("captcha-image");
            imgEl.src = "/images/" + encodeURIComponent(imgFilename);
            document.getElementById("canvas-container").style.display = "block";
            document.getElementById("empty-message").style.display = "none";
            resetClicks();
        }

        function skipOfflineImage() {
            if (currentTab !== "offline") return;
            offlineImagesList.shift();
            if (offlineImagesList.length > 0) {
                loadOfflineImage(offlineImagesList[0]);
            } else {
                showEmpty();
            }
        }

        function loadCaptchaImage() {
            const imgEl = document.getElementById("captcha-image");
            imgEl.src = "/images/current_captcha.png?t=" + new Date().getTime();
            document.getElementById("canvas-container").style.display = "block";
            document.getElementById("waiting-message").style.display = "none";
            resetClicks();
        }

        function showWaiting() {
            document.getElementById("canvas-container").style.display = "none";
            document.getElementById("waiting-message").style.display = "block";
            document.getElementById("empty-message").style.display = "none";
            resetClicks();
        }

        function showEmpty() {
            document.getElementById("canvas-container").style.display = "none";
            document.getElementById("empty-message").style.display = "block";
            document.getElementById("waiting-message").style.display = "none";
            resetClicks();
        }

        function handleCanvasClick(event) {
            if (clicks.length >= 2) return;

            const rect = event.target.getBoundingClientRect();
            const imgEl = document.getElementById("captcha-image");
            const scaleX = imgEl.naturalWidth / rect.width;
            const scaleY = imgEl.naturalHeight / rect.height;

            const clickX = Math.round((event.clientX - rect.left) * scaleX);
            const clickY = Math.round((event.clientY - rect.top) * scaleY);

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
                step1Status.innerText = "Đợi click...";
                step1Status.style.color = "var(--primary)";
                step2Status.innerText = "Đợi click...";
                step2Status.style.color = "var(--text-muted)";
                btnSave.disabled = true;
            } else if (clicks.length === 1) {
                blueMarker.style.left = clicks[0].px + "%";
                blueMarker.style.top = clicks[0].py + "%";
                blueMarker.style.display = "block";

                step1Status.innerText = `Xong! (${clicks[0].x}, ${clicks[0].y})`;
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

        async function submitSolve() {
            if (clicks.length < 2) return;

            // Xử lý gửi nhãn tùy thuộc vào tab hiện tại
            if (currentTab === "live") {
                const payload = {
                    blue: { x: clicks[0].x, y: clicks[0].y },
                    green: { x: clicks[1].x, y: clicks[1].y }
                };
                try {
                    const res = await fetch("/api/solve", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload)
                    });
                    if (res.ok) {
                        resetClicks();
                        showWaiting();
                    } else {
                        alert("Lỗi gửi tọa độ giải live!");
                    }
                } catch (err) {
                    console.error(err);
                }
            } else {
                // Chế độ Offline Labeling
                const payload = {
                    filename: offlineImagesList[0],
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
                        offlineImagesList.shift();
                        if (offlineImagesList.length > 0) {
                            loadOfflineImage(offlineImagesList[0]);
                        } else {
                            showEmpty();
                        }
                    } else {
                        alert("Lỗi dán nhãn ảnh offline!");
                    }
                } catch (err) {
                    console.error(err);
                }
            }
        }

        async function startTraining() {
            const btn = document.getElementById("btn-train");
            btn.disabled = true;
            btn.innerText = "⏳ Đang huấn luyện (Xem Terminal)...";
            try {
                const res = await fetch("/api/train", { method: "POST" });
                if (res.ok) {
                    alert("Đã bắt đầu huấn luyện mô hình YOLOv8 trên Terminal!");
                } else {
                    alert("Lỗi khi kích hoạt huấn luyện!");
                }
            } catch (err) {
                console.error(err);
            } finally {
                btn.disabled = false;
                btn.innerText = "🚀 Train mô hình YOLOv8";
            }
        }

        // Kiểm tra trạng thái bot định kỳ
        setInterval(checkStatus, 1200);

        // Phím tắt
        document.addEventListener("keydown", function(e) {
            if (e.key === "Enter") {
                submitSolve();
            } else if (e.key === "r" || e.key === "R") {
                resetClicks();
            } else if ((e.key === "s" || e.key === "S") && currentTab === "offline") {
                skipOfflineImage();
            }
        });
    </script>
</body>
</html>
"""

class LiveCaptchaHandler(BaseHTTPRequestHandler):
    """
    Xử lý Routing Server giao diện giải Captcha trực tiếp và gán nhãn offline.
    """
    def do_GET(self):
        global captcha_active, completed_jobs, current_status
        
        # Trang chủ HTML
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode("utf-8"))
            return

        # API kiểm tra trạng thái
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            # Đếm số lượng ảnh đã được gán nhãn
            labeled_count = 0
            if os.path.exists(RAW_DIR):
                for f in os.listdir(RAW_DIR):
                    if f.lower().endswith((".png", ".jpg")):
                        txt_file = os.path.splitext(f)[0] + ".txt"
                        if os.path.exists(os.path.join(RAW_DIR, txt_file)):
                            labeled_count += 1

            response = {
                "captcha_active": captcha_active,
                "completed_jobs": completed_jobs,
                "labeled_count": labeled_count,
                "status": current_status
            }
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return

        # API lấy danh sách ảnh chưa dán nhãn (cho chế độ offline)
        elif self.path == "/api/images":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            unlabeled = []
            if os.path.exists(RAW_DIR):
                for f in os.listdir(RAW_DIR):
                    if f.lower().endswith((".png", ".jpg")) and f != "current_captcha.png":
                        # Nếu chưa có tệp label txt tương ứng
                        txt_file = os.path.splitext(f)[0] + ".txt"
                        if not os.path.exists(os.path.join(RAW_DIR, txt_file)):
                            unlabeled.append(f)
            unlabeled.sort(reverse=True)
            self.wfile.write(json.dumps({"unlabeled": unlabeled}).encode("utf-8"))
            return

        # Phục vụ ảnh captcha live đang chờ xử lý
        elif self.path == "/images/current_captcha.png" or self.path.startswith("/images/current_captcha.png?"):
            file_path = os.path.join(RAW_DIR, "current_captcha.png")
            if os.path.exists(file_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File Not Found")
            return

        # Phục vụ các ảnh tĩnh từ raw_captchas (cho chế độ offline)
        elif self.path.startswith("/images/"):
            filename = urllib.parse.unquote(self.path[8:])
            file_path = os.path.join(RAW_DIR, filename)
            if os.path.exists(file_path):
                self.send_response(200)
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
        global captcha_coordinates
        
        # API giải và gửi tọa độ (chế độ Live)
        if self.path == "/api/solve":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode("utf-8"))

            blue = data["blue"]
            green = data["green"]

            # Lưu tọa độ để Main Thread đọc và thực hiện vuốt trượt
            captcha_coordinates = {
                "blue": (blue["x"], blue["y"]),
                "green": (green["x"], green["y"])
            }
            # Giải phóng Main Thread đang block
            captcha_event.set()

            self.send_response(200)
            self.end_headers()
            return

        # API dán nhãn ảnh offline
        elif self.path == "/api/label":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode("utf-8"))

            filename = data["filename"]
            blue = data["blue"]
            green = data["green"]

            img_path = os.path.join(RAW_DIR, filename)
            img = cv2.imread(img_path)
            if img is not None:
                h, w, _ = img.shape
                box_w = 80.0 / w
                box_h = 80.0 / h

                bx_c = blue["x"] / w
                by_c = blue["y"] / h
                gx_c = green["x"] / w
                gy_c = green["y"] / h

                txt_content = f"0 {bx_c:.6f} {by_c:.6f} {box_w:.6f} {box_h:.6f}\n"
                txt_content += f"1 {gx_c:.6f} {gy_c:.6f} {box_w:.6f} {box_h:.6f}\n"

                txt_filename = os.path.splitext(filename)[0] + ".txt"
                with open(os.path.join(RAW_DIR, txt_filename), "w", encoding="utf-8") as f:
                    f.write(txt_content)

                self.send_response(200)
                self.end_headers()
            else:
                self.send_error(400, "Không thể đọc kích thước ảnh")
            return

        # API train mô hình
        elif self.path == "/api/train":
            log("Nhận được lệnh huấn luyện YOLOv8 từ Web. Đang thực thi...", "INFO")
            try:
                subprocess.Popen([sys.executable, "train_yolo.py"])
                self.send_response(200)
                self.end_headers()
            except Exception as e:
                self.send_error(500, str(e))
            return
        else:
            self.send_error(404, "Not Found")

def run_web_server():
    os.makedirs(RAW_DIR, exist_ok=True)
    
    # Tự động quét và copy các ảnh mẫu captcha có sẵn trong thư mục gốc
    # để người dùng có thể bắt đầu dán nhãn chạy thử ngay lập tức!
    import shutil
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
        print(f"[WEB-LABEL] Đã tự động import {copied_count} ảnh mẫu có sẵn vào thư mục '{RAW_DIR}'!")
        
    server_address = ("", PORT)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(server_address, LiveCaptchaHandler) as httpd:
        httpd.serve_forever()


# ==========================================
# CẤU HÌNH ĐỘC LẬP ADB CONTROLLER
# ==========================================
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


class TemplateMatcher:
    def __init__(self, templates_dir, scale=1.0):
        self.templates_dir = templates_dir
        self.scale = scale
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
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= temp_data["threshold"]:
            center_x = max_loc[0] + temp_data["w"] // 2
            center_y = max_loc[1] + temp_data["h"] // 2
            return center_x, center_y, max_val
        return None

    def get_match_score(self, screen_img, template_name):
        if template_name not in self.loaded_templates:
            return 0.0
        res = cv2.matchTemplate(screen_img, self.loaded_templates[template_name]["image"], cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        return float(max_val)


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
        
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0 or not stdout:
                return None
            image_array = np.frombuffer(stdout, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            return image
        except:
            return None

    def tap(self, x, y):
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['shell', 'input', 'tap', str(int(x)), str(int(y))])
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except:
            return False

    def swipe(self, x1, y1, x2, y2, duration_ms=400):
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['shell', 'input', 'swipe', str(int(x1)), str(int(y1)), str(int(x2)), str(int(y2)), str(int(duration_ms))])
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except:
            return False

    def press_back(self):
        cmd = ['adb']
        if self.device_id:
            cmd.extend(['-s', self.device_id])
        cmd.extend(['shell', 'input', 'keyevent', '4'])
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except:
            return False


# ==========================================
# CÁC HÀM TƯƠNG TÁC TIKTOK & BẢO VỆ DEBUG
# ==========================================
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
            y_min, y_max = 200, 450
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
                if 1.5 < aspect_ratio < 8.0:
                    center_x = x + w // 2
                    if center_x > 500:
                        continue
                    if area > max_area:
                        max_area = area
                        center_y = y_min + y + h // 2
                        best_match = (center_x, center_y, area)
                        
        return best_match
    except Exception as e:
        log(f"Lỗi tìm Follow: {e}", "ERROR")
        return None

def perform_tiktok_action(screen, adb, matcher, is_like_job, scenario):
    if is_like_job:
        match_tim = matcher.find_match(screen, "icon_tim")
        if match_tim:
            tx, ty, score = match_tim
            log(f"❤️ Bấm tim TikTok tại ({tx}, {ty})", "TIKTOK")
            save_debug_image(screen, tx, ty, "Click Heart")
            adb.tap(tx, ty)
            sleep_countdown(3.0, "Chờ thả tim TikTok thành công")
            return True
        else:
            if scenario == 3:
                log("Thử Double-click video tại (360, 300) làm dự phòng...", "TIKTOK")
                adb.tap(360, 300)
                time.sleep(0.1)
                adb.tap(360, 300)
                sleep_countdown(3.0, "Chờ thả tim TikTok thành công")
                return True
            else:
                log("Không thấy biểu tượng Tim trắng TikTok.", "WARNING")
                return False
    else:
        follow_btn = find_tiktok_follow_button(screen, scenario)
        if follow_btn:
            fx, fy, area = follow_btn
            log(f"💖 Bấm Follow TikTok tại ({fx}, {fy})", "TIKTOK")
            save_debug_image(screen, fx, fy, "Click Follow")
            adb.tap(fx, fy)
            sleep_countdown(3.0, "Chờ follow TikTok thành công")
            return True
        else:
            log("Không thấy nút Follow TikTok màu đỏ.", "WARNING")
            return False


# ==========================================
# VÒNG LẶP ĐIỀU KHIỂN CHÍNH (STATE MACHINE)
# ==========================================
def main():
    global completed_jobs, captcha_active, captcha_coordinates
    
    # Khởi động Web Server trong Thread riêng
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    
    log(f"==================================================================", "SUCCESS")
    log(f"🚀 WEB SERVER ĐANG CHẠY TẠI: http://localhost:{PORT}", "SUCCESS")
    log(f"==================================================================", "SUCCESS")
    
    adb = ModernADBController()
    devices = adb.check_connection()
    if not devices:
        log("Không tìm thấy thiết bị Android. Dừng bot.", "ERROR")
        sys.exit(1)
        
    adb.device_id = devices[0]
    log(f"Đã kết nối thiết bị: {adb.device_id}", "SUCCESS")
    
    scenario = 3
    scale = 0.70 if scenario == 3 else 1.0
    matcher = TemplateMatcher(TEMPLATES_DIR, scale=scale)
    
    captcha_detector = CaptchaDetector()
    yolo_detector = YoloCaptchaDetector()
    script_executor = ADBScriptExecutor(device_id=adb.device_id)
    
    # Runtime states
    tiktok_clicked = False
    tiktok_action_done = False
    need_report_error = False
    waiting_for_job = False
    job_request_time = 0
    report_swipe_count = 0
    
    try:
        while True:
            start_loop_time = time.time()
            screen = adb.get_screenshot()
            if screen is None:
                time.sleep(2)
                continue
                
            # Trạng thái chờ load job
            if waiting_for_job:
                score_details = matcher.get_match_score(screen, "header_chi_tiet")
                score_popup = matcher.get_match_score(screen, "nut_dong_y")
                score_ok = matcher.get_match_score(screen, "nut_ok")
                
                thresh_details = TEMPLATES_CONFIG["header_chi_tiet"]["threshold"]
                thresh_popup = TEMPLATES_CONFIG["nut_dong_y"]["threshold"]
                thresh_ok = TEMPLATES_CONFIG["nut_ok"]["threshold"]
                
                has_details = score_details >= thresh_details
                has_popup = score_popup >= thresh_popup
                has_ok = score_ok >= thresh_ok
                has_captcha = captcha_detector.is_captcha_present(screen, scenario)
                
                if has_details or has_popup or has_ok or has_captcha:
                    waiting_for_job = False
                    log("Đã load xong giao diện.", "INFO")
                else:
                    if time.time() - job_request_time > 4.5:
                        waiting_for_job = False
                        log("Quá thời gian tải job. Tiếp tục...", "WARNING")
                    else:
                        time.sleep(0.8)
                        continue
            
            action_taken = False
            
            # ========================================================
            # 1. TRẠNG THÁI 2: XỬ LÝ CAPTCHA (ƯU TIÊN CAO NHẤT)
            # ========================================================
            if not action_taken and not tiktok_clicked:
                if not matcher.find_match(screen, "nut_nhan_job_ngay") and not matcher.find_match(screen, "header_chi_tiet") and not matcher.find_match(screen, "tab_danh_sach_cong_viec"):
                    if captcha_detector.is_captcha_present(screen, scenario):
                        log("Phát hiện màn hình Captcha Xác minh nhanh!", "CAPTCHA")
                        
                        # Thử dùng YOLO tự động trước
                        blue_center, green_center = yolo_detector.detect_objects(screen, scenario)
                        
                        # Nếu YOLO tự nhận diện thành công => giải tự động ngay
                        if blue_center and green_center:
                            log(f"[AUTO-AI] Tự động giải Captcha: {blue_center} -> {green_center}", "SUCCESS")
                            path = BezierTrajectoryGenerator.generate_path(blue_center, green_center, steps=45)
                            script_executor.execute_monkey_drag(path, total_duration_seconds=3.8)
                            sleep_countdown(3.0, "Đang chờ popup xác nhận")
                            action_taken = True
                        else:
                            # Nếu YOLO chưa được huấn luyện / hoặc không nhận diện được => Tương tác Giải thủ công trên Web!
                            log("YOLO không nhận diện được. Kích hoạt chế độ giải live trên Web...", "CAPTCHA")
                            
                            # Lưu ảnh hiện tại ra thư mục tĩnh của Web Server
                            cv2.imwrite(os.path.join(RAW_DIR, "current_captcha.png"), screen)
                            
                            # Gửi tín hiệu cảnh báo lên Web
                            captcha_active = True
                            captcha_event.clear()
                            captcha_coordinates = None
                            
                            log(f"🧩 Vui lòng mở http://localhost:{PORT} để giải Captcha bằng tay...", "CAPTCHA")
                            
                            # Chờ người dùng click trên Web (Blocking Wait)
                            # Nếu người dùng click giải xong trên web, web sẽ kích hoạt event.set() giải phóng đoạn code này
                            captcha_event.wait()
                            
                            # Thu hồi tọa độ click thực tế từ người dùng
                            blue_center = captcha_coordinates["blue"]
                            green_center = captcha_coordinates["green"]
                            
                            log(f"Đã nhận tọa độ từ Web: Blue={blue_center}, Green={green_center}. Đang thực thi vuốt...", "CAPTCHA")
                            
                            # Lưu vĩnh viễn hình ảnh + nhãn này để làm dataset train YOLO sau này
                            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            img_save_path = os.path.join(RAW_DIR, f"captcha_{ts}.png")
                            cv2.imwrite(img_save_path, screen)
                            
                            # Tính và xuất file txt YOLO
                            h_img, w_img, _ = screen.shape
                            box_w = 80.0 / w_img
                            box_h = 80.0 / h_img
                            bx_c = blue_center[0] / w_img
                            by_c = blue_center[1] / h_img
                            gx_c = green_center[0] / w_img
                            gy_c = green_center[1] / h_img
                            
                            txt_content = f"0 {bx_c:.6f} {by_c:.6f} {box_w:.6f} {box_h:.6f}\n"
                            txt_content += f"1 {gx_c:.6f} {gy_c:.6f} {box_w:.6f} {box_h:.6f}\n"
                            with open(os.path.splitext(img_save_path)[0] + ".txt", "w", encoding="utf-8") as f_lbl:
                                f_lbl.write(txt_content)
                                
                            # Tiến hành kéo thả live mượt mà bằng Bezier tay
                            path = BezierTrajectoryGenerator.generate_path(blue_center, green_center, steps=45)
                            script_executor.execute_monkey_drag(path, total_duration_seconds=3.8)
                            
                            # Thu hồi cờ captcha active để web quay về trạng thái chờ
                            captcha_active = False
                            sleep_countdown(3.0, "Đang chờ popup xác nhận sau giải Captcha")
                            action_taken = True

            # ========================================================
            # 2. TRẠNG THÁI 3: XỬ LÝ POPUP / QUẢNG CÁO CẢN TRỞ
            # ========================================================
            if not action_taken:
                match_close = matcher.find_match(screen, "nut_dong_quang_cao")
                if match_close:
                    cx, cy, _ = match_close
                    log("Đóng quảng cáo...", "WARNING")
                    adb.tap(cx, cy)
                    action_taken = True
                    time.sleep(1.2)
                    
            if not action_taken:
                match_continue = matcher.find_match(screen, "nut_tiep_tuc")
                if match_continue:
                    cx, cy, _ = match_continue
                    log("Click Tiếp tục quảng cáo...", "WARNING")
                    adb.tap(cx, cy)
                    action_taken = True
                    time.sleep(1.2)

            if not action_taken:
                match_dong_y = matcher.find_match(screen, "nut_dong_y")
                if match_dong_y:
                    dy_x, dy_y, _ = match_dong_y
                    log("Xử lý popup Đồng ý...", "INFO")
                    
                    match_da_hieu = matcher.find_match(screen, "txt_da_hieu")
                    if match_da_hieu:
                        dh_x, dh_y, _ = match_da_hieu
                        adb.tap(dh_x, dh_y)
                    else:
                        cb_x, cb_y = int(dy_x - 367 * scale), int(dy_y - 147 * scale)
                        adb.tap(cb_x, cb_y)
                        
                    time.sleep(0.8)
                    adb.tap(dy_x, dy_y)
                    action_taken = True
                    time.sleep(1.5)

            if not action_taken:
                match_ok = matcher.find_match(screen, "nut_ok")
                if match_ok:
                    cx, cy, _ = match_ok
                    log("Bấm OK nhận kết quả Job...", "INFO")
                    adb.tap(cx, cy)
                    action_taken = True
                    
                    match_xoa = matcher.find_match(screen, "txt_job_da_bi_xoa")
                    if match_xoa:
                        log("Job đã bị xóa hoặc hết hạn. Báo lỗi...", "WARNING")
                        need_report_error = True
                    
                    if not need_report_error:
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
                            
                            if completed_jobs > 0 and completed_jobs % 10 == 0:
                                log(f"Đã chạy {completed_jobs} job. Nghỉ ngơi 60s...", "SUCCESS")
                                sleep_countdown(60.0, "Nghỉ ngơi phục hồi thiết bị")
                        else:
                            log("Hệ thống báo lỗi. Bật cờ báo lỗi...", "WARNING")
                            need_report_error = True
                            
                    tiktok_clicked = False
                    tiktok_action_done = False
                    sleep_countdown(3.0, "Quay lại trang nhận Job mới")
                    
                    fresh_screen = adb.get_screenshot()
                    if fresh_screen is not None:
                        if matcher.find_match(fresh_screen, "header_chi_tiet"):
                            if scenario == 3:
                                adb.tap(50, 490)
                            else:
                                adb.press_back()
                            time.sleep(1.0)

            # ========================================================
            # 3. TRẠNG THÁI 5: BÁO LỖI TỰ ĐỘNG
            # ========================================================
            if not action_taken and need_report_error:
                if report_swipe_count > 3:
                    log("Quá giới hạn tìm nút báo lỗi. Hủy cờ.", "ERROR")
                    need_report_error = False
                    report_swipe_count = 0
                else:
                    match_gui_bc = matcher.find_match(screen, "nut_gui_bao_cao")
                    if match_gui_bc:
                        gx, gy, _ = match_gui_bc
                        log("Gửi báo cáo...", "JOB")
                        adb.tap(gx, gy)
                        need_report_error = False
                        report_swipe_count = 0
                        action_taken = True
                        time.sleep(1.5)
                    else:
                        match_bao_loi = matcher.find_match(screen, "nut_bao_loi")
                        if match_bao_loi:
                            bx, by, _ = match_bao_loi
                            log("Click Báo lỗi...", "JOB")
                            adb.tap(bx, by)
                            report_swipe_count = 0
                            action_taken = True
                            time.sleep(1.5)
                        else:
                            log("Vuốt lên tìm nút Báo lỗi...", "WARNING")
                            adb.swipe(360, 600, 360, 400, duration_ms=400)
                            report_swipe_count += 1
                            action_taken = True
                            time.sleep(0.8)

            # ========================================================
            # 4. TRẠNG THÁI 4: TƯƠNG TÁC TIKTOK
            # ========================================================
            if not action_taken:
                match_header_ct = matcher.find_match(screen, "header_chi_tiet")
                if match_header_ct:
                    zone_job = screen[500:750, 32:688] if scenario == 3 else screen[150:450, :]
                    is_like_job = matcher.find_match(zone_job, "job_like_indicator") is not None
                    
                    match_hoan_thanh = matcher.find_match(screen, "nut_hoan_thanh")
                    if match_hoan_thanh and tiktok_clicked:
                        hx, hy, _ = match_hoan_thanh
                        if not tiktok_action_done:
                            log("Chưa thấy tương tác, thực hiện lại...", "WARNING")
                            tiktok_action_done = perform_tiktok_action(screen, adb, matcher, is_like_job, scenario)
                            action_taken = True
                            
                        if not action_taken and tiktok_action_done:
                            log("Click Hoàn thành...", "JOB")
                            adb.tap(hx, hy)
                            action_taken = True
                            tiktok_clicked = False
                            tiktok_action_done = False
                            sleep_countdown(3.0, "Đang xử lý...")
                    else:
                        match_tiktok = matcher.find_match(screen, "nut_tiktok")
                        if not match_tiktok:
                            follow_btn_present = find_tiktok_follow_button(screen, scenario)
                            tim_present = matcher.find_match(screen, "icon_tim")
                            if (is_like_job and tim_present) or (not is_like_job and follow_btn_present):
                                log("Vuốt tìm nút Hoàn thành...", "INFO")
                                adb.swipe(360, 600, 360, 400, duration_ms=400)
                                tiktok_clicked = True
                                action_taken = True
                                time.sleep(0.8)
                                
                        if match_tiktok and not action_taken and not tiktok_clicked:
                            tx, ty, _ = match_tiktok
                            log("Bấm nút mở app TikTok...", "TIKTOK")
                            adb.tap(tx, ty)
                            tiktok_clicked = True
                            wait_time = random.uniform(9.5, 11.5) if is_like_job else random.uniform(7.5, 9.0)
                            sleep_countdown(wait_time, "Chờ TikTok load trang")
                            
                            fresh_screen = adb.get_screenshot()
                            if fresh_screen is not None:
                                tiktok_action_done = perform_tiktok_action(fresh_screen, adb, matcher, is_like_job, scenario)
                            action_taken = True
                            sleep_countdown(1.5, "Đang tiếp tục...")

            # ========================================================
            # 5. TRẠNG THÁI 1: NHẬN JOB
            # ========================================================
            if not action_taken:
                match_tab = matcher.find_match(screen, "tab_danh_sach_cong_viec")
                if match_tab:
                    match_nhan_job = matcher.find_match(screen, "nut_nhan_job_ngay")
                    if match_nhan_job:
                        cx, cy, _ = match_nhan_job
                        log("Nhận Job mới...", "JOB")
                        adb.tap(cx, cy)
                        action_taken = True
                        tiktok_clicked = False
                        tiktok_action_done = False
                        need_report_error = False
                        waiting_for_job = True
                        job_request_time = time.time()
                        time.sleep(1.0)
                    else:
                        log("Vuốt tìm Job mới...", "JOB")
                        adb.swipe(360, 1100, 360, 700, duration_ms=400)
                        action_taken = True
                        time.sleep(1.0)
            
            elapsed = time.time() - start_loop_time
            sleep_time = max(0.2, 1.2 - elapsed)
            time.sleep(sleep_time + random.uniform(0.0, 0.3))
            
    except KeyboardInterrupt:
        log("Dừng bot.", "SUCCESS")
    except Exception as e:
        log(f"Lỗi hệ thống: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
