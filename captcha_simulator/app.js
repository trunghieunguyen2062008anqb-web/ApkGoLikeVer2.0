// Golike Captcha Simulator & Auto-Solver Logic

const canvas = document.getElementById('captchaCanvas');
const ctx = canvas.getContext('2d');

// DOM Elements
const statusBadge = document.getElementById('status-badge');
const valStart = document.getElementById('val-start');
const valCheck = document.getElementById('val-check');
const valEnd = document.getElementById('val-end');
const valCheckpointStatus = document.getElementById('val-checkpoint-status');
const logContainer = document.getElementById('log-container');
const logCount = document.getElementById('log-count');
const btnAuto = document.getElementById('btn-auto');
const btnReset = document.getElementById('btn-reset');
const btnExport = document.getElementById('btn-export');

// State Variables
let isDragging = false;
let checkpointPassed = false;
let manualPath = []; // Array of {x, y, time}
let startTime = 0;

// Game Objects
let square = { x: 50, y: 300, size: 40, color: '#1e90ff' }; // Blue Square
let dashedCircle = { x: 200, y: 150, radius: 35 }; // Dashed Checkpoint
let targetCircle = { x: 320, y: 280, radius: 30, color: '#4caf50' }; // Green Target

// Generate Random Positions for Captcha elements matching the layout
function randomizePositions() {
    // Square (Bottom-Left region)
    square.x = 40 + Math.random() * 60;
    square.y = 260 + Math.random() * 70;
    
    // Dashed Checkpoint (Top-Middle region)
    dashedCircle.x = 160 + Math.random() * 80;
    dashedCircle.y = 80 + Math.random() * 80;
    
    // Target Circle (Middle-Right region)
    targetCircle.x = 280 + Math.random() * 60;
    targetCircle.y = 200 + Math.random() * 100;
    
    checkpointPassed = false;
    manualPath = [];
    isDragging = false;
    
    updateBadge('SẴN SÀNG', 'ready');
    updateDashboard();
    draw();
}

// Draw Canvas elements
function draw() {
    // Clear canvas (white background like Golike popup)
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // 1. Draw Dashed Circle (Checkpoint)
    ctx.save();
    ctx.beginPath();
    ctx.arc(dashedCircle.x, dashedCircle.y, dashedCircle.radius, 0, Math.PI * 2);
    ctx.strokeStyle = '#78909c';
    ctx.lineWidth = 3;
    ctx.setLineDash([6, 6]); // Dashed line
    ctx.stroke();
    ctx.restore();
    
    // Add text inside checkpoint circle
    ctx.fillStyle = '#90a4ae';
    ctx.font = '10px Outfit';
    ctx.textAlign = 'center';
    ctx.fillText('Checkpoint', dashedCircle.x, dashedCircle.y - dashedCircle.radius - 6);

    // 2. Draw Target Circle (Green)
    ctx.beginPath();
    ctx.arc(targetCircle.x, targetCircle.y, targetCircle.radius, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(76, 175, 80, 0.15)'; // Translucent green fill
    ctx.fill();
    ctx.strokeStyle = targetCircle.color;
    ctx.lineWidth = 3;
    ctx.stroke();
    
    // Target label
    ctx.fillStyle = '#2e7d32';
    ctx.font = '11px Outfit';
    ctx.textAlign = 'center';
    ctx.fillText('ĐÍCH', targetCircle.x, targetCircle.y + 4);

    // 3. Draw Recorded Mouse Path Trajectory (Trailing line)
    if (manualPath.length > 1) {
        ctx.beginPath();
        ctx.moveTo(manualPath[0].x, manualPath[0].y);
        for (let i = 1; i < manualPath.length; i++) {
            ctx.lineTo(manualPath[i].x, manualPath[i].y);
        }
        ctx.strokeStyle = 'rgba(244, 63, 94, 0.6)'; // Red trailing line
        ctx.lineWidth = 4;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.stroke();
    }

    // 4. Draw Blue Square (Draggable element)
    ctx.save();
    ctx.beginPath();
    ctx.rect(square.x - square.size/2, square.y - square.size/2, square.size, square.size);
    ctx.fillStyle = square.color;
    // Round the square slightly
    ctx.shadowBlur = 10;
    ctx.shadowColor = 'rgba(30, 144, 255, 0.4)';
    ctx.fill();
    ctx.restore();
}

// Dashboard Update
function updateDashboard() {
    valStart.textContent = `(${Math.round(square.x)}, ${Math.round(square.y)})`;
    valCheck.textContent = `(${Math.round(dashedCircle.x)}, ${Math.round(dashedCircle.y)})`;
    valEnd.textContent = `(${Math.round(targetCircle.x)}, ${Math.round(targetCircle.y)})`;
    
    if (checkpointPassed) {
        valCheckpointStatus.textContent = 'ĐÃ VƯỢT QUA';
        valCheckpointStatus.className = 'value status-pass';
    } else {
        valCheckpointStatus.textContent = 'CHƯA QUA';
        valCheckpointStatus.className = 'value status-fail';
    }
    
    logCount.textContent = `${manualPath.length} points`;
}

// Log message to screen panel
function appendLog(message, type = '') {
    if (logContainer.querySelector('.log-placeholder')) {
        logContainer.innerHTML = '';
    }
    
    const div = document.createElement('div');
    div.className = `log-entry ${type}`;
    div.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    logContainer.appendChild(div);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Update Status Badge UI
function updateBadge(text, type) {
    statusBadge.textContent = text;
    statusBadge.className = 'status-badge';
    if (type === 'recording') statusBadge.classList.add('active-recording');
    if (type === 'success') statusBadge.classList.add('active-success');
}

// Collision Check: Circle and Rect center distance
function checkCheckpointCollision() {
    const dx = square.x - dashedCircle.x;
    const dy = square.y - dashedCircle.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    
    // If square center enters dashed circle
    if (dist < dashedCircle.radius) {
        if (!checkpointPassed) {
            checkpointPassed = true;
            appendLog('🚀 Đã đi qua Checkpoint nét đứt!', 'checkpoint');
            updateDashboard();
        }
    }
}

// Interaction Listeners (Mouse & Touch)
function getEventCoords(e) {
    const rect = canvas.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
        x: clientX - rect.left,
        y: clientY - rect.top
    };
}

function onStart(e) {
    const coords = getEventCoords(e);
    
    // Check if clicked inside blue square
    const half = square.size / 2;
    if (coords.x >= square.x - half && coords.x <= square.x + half &&
        coords.y >= square.y - half && coords.y <= square.y + half) {
        isDragging = true;
        checkpointPassed = false;
        manualPath = [{ x: square.x, y: square.y, time: 0 }];
        startTime = Date.now();
        
        updateBadge('GHI LẠI...', 'recording');
        logContainer.innerHTML = '';
        appendLog('Bắt đầu kéo thả khối vuông.', '');
        updateDashboard();
        e.preventDefault();
    }
}

function onMove(e) {
    if (!isDragging) return;
    
    const coords = getEventCoords(e);
    square.x = coords.x;
    square.y = coords.y;
    
    const elapsed = Date.now() - startTime;
    manualPath.push({ x: coords.x, y: coords.y, time: elapsed });
    
    appendLog(`Tọa độ: X:${Math.round(coords.x)}, Y:${Math.round(coords.y)} (${elapsed}ms)`);
    checkCheckpointCollision();
    updateDashboard();
    draw();
    e.preventDefault();
}

function onEnd(e) {
    if (!isDragging) return;
    isDragging = false;
    
    // Verify drop condition
    const dx = square.x - targetCircle.x;
    const dy = square.y - targetCircle.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    
    if (checkpointPassed && dist < targetCircle.radius) {
        updateBadge('THÀNH CÔNG', 'success');
        appendLog('🎉 Thành công! Đã giải xong Captcha!', 'success');
        btnExport.disabled = false;
    } else {
        updateBadge('THẤT BẠI', 'fail');
        appendLog('❌ Thất bại. Cần đi qua Checkpoint và thả vào ĐÍCH!', '');
        setTimeout(randomizePositions, 1500); // Auto reset on fail
    }
    
    e.preventDefault();
}

canvas.addEventListener('mousedown', onStart);
canvas.addEventListener('mousemove', onMove);
window.addEventListener('mouseup', onEnd);

canvas.addEventListener('touchstart', onStart, { passive: false });
canvas.addEventListener('touchmove', onMove, { passive: false });
window.addEventListener('touchend', onEnd, { passive: false });


// ==========================================
// THUẬT TOÁN AI AUTO-SOLVER (BEZIER CURVE)
// ==========================================
function solveCaptchaAI() {
    btnAuto.disabled = true;
    randomizePositions();
    
    // Start (P0), Checkpoint (P_check), Target (P2)
    const P0 = { x: square.x, y: square.y };
    const P_check = { x: dashedCircle.x, y: dashedCircle.y };
    const P2 = { x: targetCircle.x, y: targetCircle.y };
    
    // Calculate Quadratic Bezier Control Point (P1) so curve passes EXACTLY through P_check at t = 0.5
    // P1 = 2 * P_check - 0.5 * P0 - 0.5 * P2
    const P1 = {
        x: 2 * P_check.x - 0.5 * P0.x - 0.5 * P2.x,
        y: 2 * P_check.y - 0.5 * P0.y - 0.5 * P2.y
    };
    
    // Generate Bezier coordinates with bio-tremor (rung tay)
    const steps = 30; // 30 frames for a smooth human drag animation
    const bezierPath = [];
    
    // Helper to generate Gaussian random noise (Box-Muller transform)
    function randomNormal(mean, std) {
        let u = 0, v = 0;
        while(u === 0) u = Math.random();
        while(v === 0) v = Math.random();
        return mean + std * Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
    }
    
    const jitter_std = 2.0;
    const raw_noise_x = [];
    const raw_noise_y = [];
    for (let i = 0; i <= steps; i++) {
        raw_noise_x.push(randomNormal(0, jitter_std));
        raw_noise_y.push(randomNormal(0, jitter_std));
    }
    
    // Smooth noise using rolling average (window=3)
    const smooth_noise_x = [];
    const smooth_noise_y = [];
    const window_size = 3;
    for (let i = 0; i <= steps; i++) {
        const start = Math.max(0, i - window_size);
        const end = Math.min(steps, i + window_size);
        let sum_x = 0, sum_y = 0, count = 0;
        for (let j = start; j <= end; j++) {
            sum_x += raw_noise_x[j];
            sum_y += raw_noise_y[j];
            count++;
        }
        smooth_noise_x.push(sum_x / count);
        smooth_noise_y.push(sum_y / count);
    }
    
    for (let i = 0; i <= steps; i++) {
        const alpha = i / steps;
        // Smoothstep easing (3*x^2 - 2*x^3)
        const t = 3 * (alpha ** 2) - 2 * (alpha ** 3);
        
        // Base Bezier curve points
        const bx = (1-t)*(1-t)*P0.x + 2*(1-t)*t*P1.x + t*t*P2.x;
        const by = (1-t)*(1-t)*P0.y + 2*(1-t)*t*P1.y + t*t*P2.y;
        
        // Add smooth muscle tremor scaled by sin(t * pi) (no tremor at start and end points)
        const scale = Math.sin(t * Math.PI);
        const jx = bx + smooth_noise_x[i] * scale * 5.0; // Visual multiplier on 400px canvas
        const jy = by + smooth_noise_y[i] * scale * 5.0;
        
        bezierPath.push({ x: jx, y: jy });
    }
    
    // Animate the dragging process
    let currentStep = 0;
    updateBadge('AUTO SOLVING...', 'recording');
    logContainer.innerHTML = '';
    appendLog('AI: Khởi chạy giải thuật Bezier...', '');
    
    const interval = setInterval(() => {
        if (currentStep <= steps) {
            const point = bezierPath[currentStep];
            square.x = point.x;
            square.y = point.y;
            
            // Log coordinates
            manualPath.push({ x: point.x, y: point.y, time: currentStep * 30 });
            appendLog(`[AI] X:${Math.round(point.x)}, Y:${Math.round(point.y)}`);
            
            checkCheckpointCollision();
            updateDashboard();
            draw();
            currentStep++;
        } else {
            clearInterval(interval);
            // Auto complete check
            updateBadge('SUCCESS (AI)', 'success');
            appendLog('🎉 AI Giải captcha thành công!', 'success');
            btnExport.disabled = false;
            btnAuto.disabled = false;
        }
    }, 30); // 30ms per frame
}

// Reset and Export Events
btnReset.addEventListener('click', randomizePositions);
btnAuto.addEventListener('click', solveCaptchaAI);

btnExport.addEventListener('click', () => {
    // Export recorded path trajectory to a JSON file
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(manualPath, null, 2));
    const dlAnchorElem = document.createElement('a');
    dlAnchorElem.setAttribute("href", dataStr);
    dlAnchorElem.setAttribute("download", "captcha_trajectory.json");
    dlAnchorElem.click();
    appendLog('💾 Đã xuất file tọa độ captcha_trajectory.json!', 'success');
});

// Initial Setup
randomizePositions();
draw();
