package com.golike.autoclicker

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.Path
import android.graphics.PixelFormat
import android.graphics.PointF
import android.graphics.Rect
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.view.Display
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.TextView
import android.util.Log
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors

class MyAccessibilityService : AccessibilityService() {

    private var windowManager: WindowManager? = null
    private var floatingView: View? = null
    private var tvFloatingLog: TextView? = null
    private val mainHandler = Handler(Looper.getMainLooper())
    private val executorService = Executors.newSingleThreadExecutor()
    private lateinit var templateMatcher: TemplateMatcher

    private var automationThread: Thread? = null
    @Volatile
    var isRunning = false
        private set

    companion object {
        private const val TAG = "HCSAccessibility"
        
        @Volatile
        var instance: MyAccessibilityService? = null
            private set

        val isServiceRunning: Boolean
            get() = instance != null
    }

    var onFloatingWindowClosed: (() -> Unit)? = null
    var onLogReceived: ((String) -> Unit)? = null
    var onStateChanged: (() -> Unit)? = null

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.d(TAG, "Accessibility Service Connected")
        instance = this
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        
        templateMatcher = TemplateMatcher(this)
        templateMatcher.loadTemplates()
    }

    override fun onUnbind(intent: android.content.Intent?): Boolean {
        Log.d(TAG, "Accessibility Service Unbound")
        stopAutomation()
        hideFloatingWindow()
        instance = null
        return super.onUnbind(intent)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Không block sự kiện
    }

    override fun onInterrupt() {
        Log.d(TAG, "Accessibility Service Interrupted")
        stopAutomation()
        hideFloatingWindow()
        instance = null
    }

    override fun onDestroy() {
        super.onDestroy()
        stopAutomation()
        hideFloatingWindow()
        instance = null
    }

    fun log(message: String) {
        val timeStamp = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
        val formattedLog = "[$timeStamp] $message"
        Log.d(TAG, formattedLog)
        
        updateFloatingLog(message)
        onLogReceived?.invoke(message)
    }

    fun showFloatingWindow() {
        mainHandler.post {
            if (floatingView != null) return@post
            val wm = windowManager ?: return@post
            
            val layoutType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                @Suppress("DEPRECATION")
                WindowManager.LayoutParams.TYPE_PHONE
            }
            
            val params = WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                layoutType,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
                PixelFormat.TRANSLUCENT
            )
            
            params.gravity = Gravity.TOP or Gravity.START
            params.x = 100
            params.y = 200
            
            val inflater = getSystemService(Context.LAYOUT_INFLATER_SERVICE) as LayoutInflater
            val view = inflater.inflate(R.layout.floating_layout, null)
            floatingView = view
            
            tvFloatingLog = view.findViewById(R.id.tvFloatingLog)
            
            val btnStart = view.findViewById<View>(R.id.btnFloatingStart)
            val btnStop = view.findViewById<View>(R.id.btnFloatingStop)
            val btnClose = view.findViewById<View>(R.id.btnFloatingClose)
            
            btnStart.setOnClickListener {
                startAutomation()
            }
            
            btnStop.setOnClickListener {
                stopAutomation()
            }
            
            btnClose.setOnClickListener {
                stopAutomation()
                hideFloatingWindow()
                onFloatingWindowClosed?.invoke()
            }
            
            val topBar = view.findViewById<View>(R.id.llTopBar)
            topBar.setOnTouchListener(object : View.OnTouchListener {
                private var initialX = 0
                private var initialY = 0
                private var initialTouchX = 0f
                private var initialTouchY = 0f

                override fun onTouch(v: View, event: MotionEvent): Boolean {
                    when (event.action) {
                        MotionEvent.ACTION_DOWN -> {
                            initialX = params.x
                            initialY = params.y
                            initialTouchX = event.rawX
                            initialTouchY = event.rawY
                            return true
                        }
                        MotionEvent.ACTION_MOVE -> {
                            params.x = initialX + (event.rawX - initialTouchX).toInt()
                            params.y = initialY + (event.rawY - initialTouchY).toInt()
                            wm.updateViewLayout(view, params)
                            return true
                        }
                    }
                    return false
                }
            })
            
            try {
                wm.addView(view, params)
                updateFloatingLog(if (isRunning) "Đang hoạt động..." else "Chưa chạy. Bấm 'Chạy' để bắt đầu.")
            } catch (e: Exception) {
                Log.e(TAG, "Error adding floating window: " + e.message)
            }
        }
    }

    fun hideFloatingWindow() {
        mainHandler.post {
            val view = floatingView
            val wm = windowManager
            if (view != null && wm != null) {
                try {
                    wm.removeView(view)
                } catch (e: Exception) {
                    Log.e(TAG, "Error removing floating window: " + e.message)
                }
            }
            floatingView = null
            tvFloatingLog = null
        }
    }

    fun isFloatingWindowShowing(): Boolean {
        return floatingView != null
    }

    private fun updateFloatingLog(message: String) {
        mainHandler.post {
            tvFloatingLog?.text = message
        }
    }

    /**
     * DÒ TÌM VÀ CỬA HÀNG TỌA ĐỘ TEMPLATE HÌNH ẢNH DỰA TRÊN ẢNH MẪU (PNG)
     */
    fun findTemplate(templateName: String, threshold: Float = 0.68f): PointF? {
        var matchedPoint: PointF? = null
        val lock = Object()
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            takeScreenshot(Display.DEFAULT_DISPLAY, executorService, object : TakeScreenshotCallback {
                override fun onSuccess(screenshotResult: ScreenshotResult) {
                    val hardwareBuffer = screenshotResult.hardwareBuffer
                    val bitmap = Bitmap.wrapHardwareBuffer(hardwareBuffer, screenshotResult.colorSpace)
                    hardwareBuffer.close()
                    if (bitmap != null) {
                        val softwareBitmap = bitmap.copy(Bitmap.Config.ARGB_8888, false)
                        matchedPoint = templateMatcher.findMatch(softwareBitmap, templateName, threshold)
                        softwareBitmap.recycle()
                        bitmap.recycle()
                    }
                    synchronized(lock) {
                        lock.notify()
                    }
                }

                override fun onFailure(errorCode: Int) {
                    Log.e(TAG, "Failed to capture screen for template $templateName: $errorCode")
                    synchronized(lock) {
                        lock.notify()
                    }
                }
            })
            
            synchronized(lock) {
                try {
                    lock.wait(3000)
                } catch (e: Exception) {}
            }
        }
        return matchedPoint
    }

    fun clickTemplate(templateName: String, threshold: Float = 0.68f): Boolean {
        val point = findTemplate(templateName, threshold)
        if (point != null) {
            log("-> Khớp ảnh mẫu '$templateName' tại (${point.x.toInt()}, ${point.y.toInt()})")
            tap(point.x, point.y)
            return true
        }
        return false
    }

    /**
     * KIỂM TRA MÀN HÌNH CAPTCHA BẰNG CẢ ẢNH MẪU LẪN TRỢ NĂNG
     */
    fun isCaptchaPresent(): Boolean {
        // Nếu nhìn thấy nút Nhận Job hoặc nút mở TikTok thì chắc chắn không phải Captcha
        if (findTemplate("nut_nhan_job_ngay", 0.65f) != null || findTemplate("nut_tiktok", 0.65f) != null) {
            return false
        }
        if (findTemplate("captcha_title") != null || findTemplate("captcha_title_sc3") != null) {
            return true
        }
        return findNodeByText("Xác minh nhanh") != null || 
               findNodeByText("Xác minh") != null || 
               findNodeByText("Không phải người máy") != null || 
               findNodeByText("Hãy kéo mảnh ghép") != null
    }

    /**
     * THUẬT TOÁN TỰ ĐỘNG GIẢI CAPTCHA BẰNG CƠ CHẾ DÒ MÀU HSV (Giống 100% logic Python OpenCV)
     */
    fun solveCaptcha(bitmap: Bitmap, screenWidth: Float, screenHeight: Float): Boolean {
        val width = bitmap.width
        val height = bitmap.height
        
        val yStart = (height * 0.20f).toInt()
        val yEnd = (height * 0.80f).toInt()
        
        var blueSumX = 0L
        var blueSumY = 0L
        var blueCount = 0
        
        var greenSumX = 0L
        var greenSumY = 0L
        var greenCount = 0
        
        val hsv = FloatArray(3)
        
        for (y in yStart until yEnd step 4) {
            for (x in 0 until width step 4) {
                val pixel = bitmap.getPixel(x, y)
                Color.colorToHSV(pixel, hsv)
                
                val h = hsv[0]
                val s = hsv[1]
                val v = hsv[2]
                
                // 1. Khối vuông Xanh dương (H: 190..270, S: >=0.25, V: >=0.25)
                if (h in 190f..270f && s >= 0.25f && v >= 0.25f) {
                    if (x < width * 0.5f) {
                        blueSumX += x
                        blueSumY += y
                        blueCount++
                    }
                }
                
                // 2. Vòng tròn Xanh lá (H: 70..180, S: >=0.18, V: >=0.18)
                if (h in 70f..180f && s >= 0.18f && v >= 0.18f) {
                    if (x >= width * 0.5f) {
                        greenSumX += x
                        greenSumY += y
                        greenCount++
                    }
                }
            }
        }
        
        if (blueCount > 5 && greenCount > 5) {
            val blueX = (blueSumX / blueCount).toFloat()
            val blueY = (blueSumY / blueCount).toFloat()
            
            val greenX = (greenSumX / greenCount).toFloat()
            val greenY = (greenSumY / greenCount).toFloat()
            
            val scaleX = screenWidth / width
            val scaleY = screenHeight / height
            
            val startX = blueX * scaleX
            val startY = blueY * scaleY
            val endX = greenX * scaleX
            val endY = greenY * scaleY
            
            log("🧩 ĐÃ TÌM THẤY TỌA ĐỘ CAPTCHA: Blue(${startX.toInt()}, ${startY.toInt()}) -> Green(${endX.toInt()}, ${endY.toInt()})")
            log("-> Tiến hành kéo thả tự động...")
            
            swipe(startX, startY, endX, endY, 1500L)
            return true
        }
        
        return false
    }

    /**
     * THUẬT TOÁN TÌM NÚT THEO DÕI (FOLLOW) ĐỎ TRÊN TIKTOK BẰNG HSV (Giống 100% logic Python)
     */
    fun findTikTokFollowButton(bitmap: Bitmap, screenWidth: Float, screenHeight: Float): PointF? {
        val width = bitmap.width
        val height = bitmap.height
        
        val yStart = (height * 0.15f).toInt()
        val yEnd = (height * 0.70f).toInt()
        
        var minX = width
        var maxX = 0
        var minY = height
        var maxY = 0
        var redPixelCount = 0
        
        val hsv = FloatArray(3)
        
        for (y in yStart until yEnd step 4) {
            for (x in 0 until width step 4) {
                val pixel = bitmap.getPixel(x, y)
                Color.colorToHSV(pixel, hsv)
                val h = hsv[0]
                val s = hsv[1]
                val v = hsv[2]
                
                val isRed = (h in 0f..50f || h in 330f..360f) && s >= 0.30f && v >= 0.35f
                if (isRed) {
                    if (x < minX) minX = x
                    if (x > maxX) maxX = x
                    if (y < minY) minY = y
                    if (y > maxY) maxY = y
                    redPixelCount++
                }
            }
        }
        
        if (redPixelCount > 15) {
            val rectWidth = maxX - minX
            val rectHeight = maxY - minY
            val aspectRatio = rectWidth.toFloat() / rectHeight.toFloat()
            
            if (rectWidth in 60..500 && rectHeight in 25..180 && aspectRatio in 1.2f..6.5f) {
                val centerX = minX + rectWidth / 2f
                val centerY = minY + rectHeight / 2f
                
                val scaleX = screenWidth / width
                val scaleY = screenHeight / height
                
                return PointF(centerX * scaleX, centerY * scaleY)
            }
        }
        
        return null
    }

    /**
     * Chụp màn hình để xử lý giải thuật captcha màu
     */
    fun captureScreenAndProcess(screenWidth: Float, screenHeight: Float, mode: String, callback: (PointF?) -> Unit) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            takeScreenshot(Display.DEFAULT_DISPLAY, executorService, object : TakeScreenshotCallback {
                override fun onSuccess(screenshotResult: ScreenshotResult) {
                    val hardwareBuffer = screenshotResult.hardwareBuffer
                    val bitmap = Bitmap.wrapHardwareBuffer(hardwareBuffer, screenshotResult.colorSpace)
                    hardwareBuffer.close()
                    if (bitmap != null) {
                        val softwareBitmap = bitmap.copy(Bitmap.Config.ARGB_8888, false)
                        
                        if (mode == "CAPTCHA") {
                            val success = solveCaptcha(softwareBitmap, screenWidth, screenHeight)
                            callback(if (success) PointF(1f, 1f) else null)
                        } else if (mode == "FOLLOW") {
                            val followPoint = findTikTokFollowButton(softwareBitmap, screenWidth, screenHeight)
                            callback(followPoint)
                        }
                        
                        softwareBitmap.recycle()
                        bitmap.recycle()
                    } else {
                        callback(null)
                    }
                }

                override fun onFailure(errorCode: Int) {
                    Log.e(TAG, "Screenshot failed: $errorCode")
                    callback(null)
                }
            })
        } else {
            callback(null)
        }
    }

    /**
     * BẰNG CẢ ẢNH MẪU LẪN TRỢ NĂNG THEO LUỒNG TUYẾN TÍNH CỦA FILE PYTHON
     */
    fun startAutomation() {
        if (isRunning) {
            log("Hệ thống đã đang hoạt động.")
            return
        }

        isRunning = true
        onStateChanged?.invoke()
        log("--- BẮT ĐẦU CHẠY AUTO JOB GOLIKE TIKTOK ---")

        automationThread = Thread {
            var jobId = 1
            
            val displayMetrics = resources.displayMetrics
            val screenWidth = displayMetrics.widthPixels.toFloat()
            val screenHeight = displayMetrics.heightPixels.toFloat()
            
            log("Kích thước màn hình: ${screenWidth.toInt()}x${screenHeight.toInt()}")

            while (isRunning) {
                try {
                    // 0. Tự động tắt quảng cáo ban đầu
                    closeAdsIfAny()
                    Thread.sleep(800)

                    log("[Job #$jobId] --- BẮT ĐẦU VÒNG LẶP JOB MỚI (BƯỚC 1) ---")

                    // BƯỚC 1: Nhận Job
                    var clickedJob = false
                    for (i in 1..8) {
                        if (!isRunning) break
                        
                        closeAdsIfAny()

                        // 1. Quét tìm và Click Nhận Job ngay bằng Ảnh Mẫu
                        if (clickTemplate("nut_nhan_job_ngay", 0.65f)) {
                            log("-> Đã click 'Nhận job' (Quét khớp ảnh mẫu)")
                            clickedJob = true
                            break
                        }
                        
                        // 2. Dự phòng: Dùng Trợ năng text
                        if (clickByAnyText("Nhận Job ngay ->", "Nhận job ngay", "Bắt đầu kiếm xu ngay")) {
                            log("-> Đã click 'Nhận job' (Quét Trợ năng)")
                            clickedJob = true
                            break
                        }
                        
                        Thread.sleep(1000)
                    }

                    if (!clickedJob) {
                        log("[Cảnh báo] Không tìm thấy nút Nhận Job, khởi động lại vòng lặp...")
                        continue
                    }

                    // Chờ giao diện chuyển tiếp ổn định sau khi bấm nhận Job
                    Thread.sleep(3000)
                    if (!isRunning) break

                    // BƯỚC 2: KIỂM TRA CAPTCHA (Chỉ kiểm tra và giải SAU khi đã click Nhận Job)
                    log("--- KIỂM TRA CAPTCHA (BƯỚC 2) ---")
                    if (isCaptchaPresent()) {
                        log("🧩 PHÁT HIỆN CAPTCHA XÁC MINH! Đang tự động giải bằng cơ chế lọc màu HSV...")
                        
                        var captchaSolved = false
                        val lock = Object()
                        
                        captureScreenAndProcess(screenWidth, screenHeight, "CAPTCHA") { result ->
                            synchronized(lock) {
                                captchaSolved = (result != null)
                                lock.notify()
                            }
                        }
                        
                        synchronized(lock) {
                            lock.wait(3500)
                        }
                        
                        if (captchaSolved) {
                            log("-> Đã thực hiện kéo thả giải Captcha! Chờ popup xác nhận...")
                            Thread.sleep(4000)
                        } else {
                            log("[Cảnh báo] Tự động giải Captcha thất bại. Vui lòng tự giải tay...")
                            while (isCaptchaPresent() && isRunning) {
                                Thread.sleep(1500)
                            }
                            log("-> Đã qua màn hình Captcha.")
                        }
                    } else {
                        log("Không phát hiện Captcha. Bỏ qua.")
                    }

                    if (!isRunning) break

                    // BƯỚC 3: MỞ TIKTOK & LÀM WORK
                    log("--- LÀM JOB TIKTOK (BƯỚC 3) ---")
                    
                    // Xác định Job Like hay Follow
                    var isLikeJob = false
                    val detailRoot = rootInActiveWindow
                    if (detailRoot != null) {
                        val rootText = detailRoot.toString()
                        if (rootText.contains("like", ignoreCase = true) || 
                            rootText.contains("thích", ignoreCase = true) || 
                            rootText.contains("tim", ignoreCase = true)) {
                            isLikeJob = true
                        }
                    }
                    if (findTemplate("job_like_indicator") != null) {
                        isLikeJob = true
                    }
                    log("-> Loại công việc: " + (if (isLikeJob) "LIKE/TIM" else "FOLLOW/THEO DÕI"))

                    if (isLikeJob) {
                        log("⚠️ Phát hiện Job Tim/Like. Tự động báo lỗi bỏ qua...")
                        triggerErrorReporting(screenWidth, screenHeight)
                        continue
                    }

                    // Mở TikTok
                    var openedTikTok = false
                    for (i in 1..5) {
                        if (!isRunning) break
                        
                        if (clickTemplate("nut_tiktok")) {
                            log("-> Đã click mở TikTok (Quét khớp ảnh mẫu)")
                            openedTikTok = true
                            break
                        }
                        
                        if (clickByAnyText("TikTok", "Tiktok", "tiktok")) {
                            log("-> Đã click mở TikTok (Quét Trợ năng)")
                            openedTikTok = true
                            break
                        }
                        Thread.sleep(1000)
                    }

                    if (!openedTikTok) {
                        log("[Lỗi] Không mở được TikTok. Tiến hành báo lỗi...")
                        triggerErrorReporting(screenWidth, screenHeight)
                        continue
                    }

                    // Chờ TikTok mở lên và tải dữ liệu video/profile
                    log("-> Đang mở app TikTok, chờ tải dữ liệu (6 giây)...")
                    Thread.sleep(6000)
                    if (!isRunning) break

                    // Kiểm tra tài khoản riêng tư (Private Account)
                    val isPrivate = findNodeByText("tài khoản riêng tư") != null || 
                                    findNodeByText("riêng tư") != null ||
                                    findNodeByText("phê duyệt") != null
                    if (isPrivate) {
                        log("⚠️ Phát hiện tài khoản riêng tư! Tiến hành back về GoLike...")
                        performBack() // Đóng popup riêng tư
                        Thread.sleep(800)
                        performBack() // Quay lại GoLike
                        Thread.sleep(2500)
                        continue
                    }

                    // Thực hiện tương tác trên TikTok
                    var interacted = false

                    if (clickByAnyText("Follow", "Theo dõi", "Follow back", "Follow lại")) {
                        log("-> Đã bấm Follow/Theo dõi trên TikTok (Trợ năng)")
                        interacted = true
                    }
                    if (!interacted) {
                        log("-> Không tìm thấy text Follow. Quét ảnh tìm nút màu ĐỎ...")
                        var followPoint: PointF? = null
                        val lock = Object()
                        
                        captureScreenAndProcess(screenWidth, screenHeight, "FOLLOW") { point ->
                            synchronized(lock) {
                                followPoint = point
                                lock.notify()
                            }
                        }
                        
                        synchronized(lock) {
                            lock.wait(3000)
                        }
                        
                        val targetPoint = followPoint
                        if (targetPoint != null) {
                            log("-> Đã tìm thấy nút Follow đỏ bằng HSV! Click tại: (${targetPoint.x.toInt()}, ${targetPoint.y.toInt()})")
                            tap(targetPoint.x, targetPoint.y)
                            interacted = true
                        }
                    }

                    if (!interacted) {
                        log("⚠️ Không thể thực hiện tương tác trên TikTok (không tìm thấy Follow). Quay lại GoLike để báo lỗi...")
                        performBack()
                        Thread.sleep(2500)
                        triggerErrorReporting(screenWidth, screenHeight)
                        continue
                    }

                    // Chờ TikTok cập nhật trạng thái
                    Thread.sleep(2500)
                    if (!isRunning) break

                    // Back trở lại GoLike
                    log("-> Nhấn Back quay trở lại GoLike...")
                    performBack()
                    
                    // Đợi GoLike khôi phục màn hình
                    Thread.sleep(3000)
                    if (!isRunning) break
                    closeAdsIfAny()

                    // Bấm Hoàn thành
                    var clickedComplete = false
                    for (i in 1..4) {
                        if (!isRunning) break
                        
                        if (clickTemplate("nut_hoan_thanh")) {
                            log("-> Đã bấm Hoàn thành (Quét khớp ảnh mẫu)")
                            clickedComplete = true
                            break
                        }
                        
                        if (clickByAnyText("Hoàn thành", "hoàn thành")) {
                            log("-> Đã bấm Hoàn thành (Quét Trợ năng)")
                            clickedComplete = true
                            break
                        }
                        Thread.sleep(1000)
                    }

                    if (!clickedComplete) {
                        log("[Lỗi] Không thấy nút Hoàn thành. Quay lại trang chủ...")
                        performBack()
                        Thread.sleep(2000)
                        continue
                    }

                    // Chờ GoLike xử lý cộng xu
                    Thread.sleep(5000)
                    if (!isRunning) break

                    // Bấm OK popup thông báo kết quả
                    if (!clickTemplate("nut_ok")) {
                        clickByAnyText("OK", "Ok", "Đóng", "Đồng ý")
                    }
                    Thread.sleep(2000)

                    // Kiểm tra xem có bị lỗi chưa tương tác và bị giữ lại trang chi tiết không
                    var isStillInDetails = false
                    if (findTemplate("nut_hoan_thanh") != null || findTemplate("nut_bao_loi") != null) {
                        isStillInDetails = true
                    } else {
                        val currentRoot = rootInActiveWindow
                        if (currentRoot != null) {
                            val pageDump = currentRoot.toString()
                            if (pageDump.contains("Báo lỗi") || pageDump.contains("Hoàn thành")) {
                                isStillInDetails = true
                            }
                        }
                    }

                    if (isStillInDetails) {
                        log("⚠️ GoLike thông báo lỗi chưa hoàn thành. Kích hoạt báo lỗi tự động...")
                        triggerErrorReporting(screenWidth, screenHeight)
                    } else {
                        log("[Job #$jobId] THÀNH CÔNG! Đã cộng xu.")
                        jobId++
                    }

                    log("Nghỉ giãn cách 4 giây trước chu kỳ tiếp theo...")
                    Thread.sleep(4000)

                } catch (e: InterruptedException) {
                    log("Luồng auto đã được dừng.")
                    break
                } catch (e: Exception) {
                    log("[Lỗi hệ thống] " + e.message)
                    Thread.sleep(5000)
                }
            }
            isRunning = false
            onStateChanged?.invoke()
            log("--- ĐÃ DỪNG AUTO TOOL ---")
        }
        automationThread?.start()
    }

    fun stopAutomation() {
        if (!isRunning) return
        log("Đang dừng hoạt động...")
        isRunning = false
        automationThread?.interrupt()
        automationThread = null
        onStateChanged?.invoke()
    }

    /**
     * Kịch bản tự động gửi Báo lỗi cho GoLike (Đồng bộ bằng Ảnh Mẫu)
     */
    private fun triggerErrorReporting(screenWidth: Float, screenHeight: Float) {
        try {
            var clickedReport = false
            for (i in 1..3) {
                if (clickTemplate("nut_bao_loi")) {
                    clickedReport = true
                    break
                }
                if (clickByAnyText("Báo lỗi", "báo lỗi")) {
                    clickedReport = true
                    break
                }
                if (i == 2) {
                    tap(screenWidth * 0.5f, screenHeight * 0.45f)
                    clickedReport = true
                    break
                }
                Thread.sleep(1000)
            }
            
            if (!clickedReport) return
            Thread.sleep(2000)
            
            log("-> Vuốt cuộn tìm nút Gửi báo cáo...")
            swipe(screenWidth * 0.5f, screenHeight * 0.75f, screenWidth * 0.5f, screenHeight * 0.4f, 350L)
            Thread.sleep(1500)
            
            var sentReport = false
            for (i in 1..3) {
                if (clickTemplate("nut_gui_bao_cao")) {
                    sentReport = true
                    break
                }
                if (clickByAnyText("Gửi báo cáo", "Gửi", "gửi báo cáo")) {
                    sentReport = true
                    break
                }
                if (i == 2) {
                    tap(screenWidth * 0.5f, screenHeight * 0.88f)
                    sentReport = true
                    break
                }
                Thread.sleep(1000)
            }
            
            if (sentReport) {
                Thread.sleep(3000)
                if (!clickTemplate("nut_ok")) {
                    clickByAnyText("OK", "Ok", "Đồng ý", "Đã hiểu")
                }
                log("-> Hoàn tất chu trình gửi báo lỗi!")
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error in report sequence: " + e.message)
        }
    }

    /**
     * Tắt quảng cáo cản trở bằng cả Ảnh Mẫu
     */
    fun closeAdsIfAny() {
        if (clickTemplate("nut_dong_quang_cao") || clickTemplate("nut_tiep_tuc") || clickTemplate("nut_dong_y")) {
            Thread.sleep(1200)
        }
        clickByAnyText("Đóng quảng cáo", "Đóng", "Tiếp tục", "Đồng ý", "Đã hiểu", "OK", "Ok", "Đóng lại")
    }

    fun findNodeByText(text: String, exact: Boolean = false): AccessibilityNodeInfo? {
        val activeRoot = rootInActiveWindow
        if (activeRoot != null) {
            val node = findNodeRecursive(activeRoot, text, exact)
            if (node != null) return node
        }
        
        try {
            val allWindows = windows
            for (window in allWindows) {
                val root = window.root
                if (root != null) {
                    val node = findNodeRecursive(root, text, exact)
                    if (node != null) return node
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error reading windows: " + e.message)
        }
        return null
    }

    fun findNodeRecursive(node: AccessibilityNodeInfo?, text: String, exact: Boolean): AccessibilityNodeInfo? {
        if (node == null) return null
        
        val nodeText = node.text?.toString()
        if (nodeText != null) {
            if (exact) {
                if (nodeText.equals(text, ignoreCase = true)) return node
            } else {
                if (nodeText.contains(text, ignoreCase = true)) return node
            }
        }
        
        val contentDesc = node.contentDescription?.toString()
        if (contentDesc != null) {
            if (exact) {
                if (contentDesc.equals(text, ignoreCase = true)) return node
            } else {
                if (contentDesc.contains(text, ignoreCase = true)) return node
            }
        }
        
        for (i in 0 until node.childCount) {
            val child = node.getChild(i)
            val result = findNodeRecursive(child, text, exact)
            if (result != null) return result
        }
        return null
    }

    fun clickNode(node: AccessibilityNodeInfo?): Boolean {
        val tempNode = node ?: return false
        
        var current: AccessibilityNodeInfo? = tempNode
        while (current != null) {
            if (current.isClickable) {
                if (current.performAction(AccessibilityNodeInfo.ACTION_CLICK)) {
                    return true
                }
            }
            current = current.parent
        }
        
        val rect = Rect()
        tempNode.getBoundsInScreen(rect)
        val x = rect.centerX().toFloat()
        val y = rect.centerY().toFloat()
        return tap(x, y)
    }

    fun clickByText(text: String, exact: Boolean = false): Boolean {
        val node = findNodeByText(text, exact)
        return clickNode(node)
    }

    fun clickByAnyText(vararg texts: String): Boolean {
        for (text in texts) {
            if (clickByText(text)) {
                return true
            }
        }
        return false
    }

    fun performBack(): Boolean {
        return performGlobalAction(GLOBAL_ACTION_BACK)
    }

    fun tap(x: Float, y: Float): Boolean {
        if (x < 0 || y < 0) return false
        
        val path = Path()
        path.moveTo(x, y)
        
        val gestureBuilder = GestureDescription.Builder()
        gestureBuilder.addStroke(GestureDescription.StrokeDescription(path, 0, 50))
        
        val gesture = gestureBuilder.build()
        return dispatchGesture(gesture, object : GestureResultCallback() {
            override fun onCompleted(gestureDescription: GestureDescription?) {
                super.onCompleted(gestureDescription)
            }

            override fun onCancelled(gestureDescription: GestureDescription?) {
                super.onCancelled(gestureDescription)
            }
        }, null)
    }

    fun doubleTap(x: Float, y: Float): Boolean {
        tap(x, y)
        Thread.sleep(150)
        return tap(x, y)
    }

    fun swipe(startX: Float, startY: Float, endX: Float, endY: Float, duration: Long): Boolean {
        val path = Path()
        path.moveTo(startX, startY)
        path.lineTo(endX, endY)
        
        val gestureBuilder = GestureDescription.Builder()
        gestureBuilder.addStroke(GestureDescription.StrokeDescription(path, 0, duration))
        
        val gesture = gestureBuilder.build()
        return dispatchGesture(gesture, object : GestureResultCallback() {
            override fun onCompleted(gestureDescription: GestureDescription?) {
                super.onCompleted(gestureDescription)
            }

            override fun onCancelled(gestureDescription: GestureDescription?) {
                super.onCancelled(gestureDescription)
            }
        }, null)
    }
}
