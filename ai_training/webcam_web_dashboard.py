"""
Smart Trash Bin - Web-Based Real-Time Webcam Simulator & Dashboard
==================================================================
Runs YOLOv8 real-time computer vision on your webcam and streams the result
to a web dashboard at http://localhost:8080.

Features:
- Live MJPEG video stream with bounding boxes
- Virtual OLED 0.96" display emulator
- 4 Virtual animated trash bins (General, Recyclable, Wet, Hazardous)
- Sound effects via Web Audio API
- Real-time classification status and servo actuation logs
"""

import os
import sys
import time
import json
import threading
import cv2
from http.server import HTTPServer, BaseHTTPRequestHandler
from ultralytics import YOLO

PORT = 8080

# Load YOLOv8 model
print("[*] กำลังโหลดโมเดล YOLOv8 Nano...")
model = YOLO("yolov8n.pt")
print("[+] โหลดโมเดล YOLOv8 สำเร็จเรียบร้อย!")

# Global state
camera_lock = threading.Lock()
current_frame_jpeg = None
current_status = {
    "detected_class": "None",
    "confidence": 0.0,
    "bin_id": 0,
    "bin_name": "Standby",
    "bin_color": "gray",
    "servo_pin": "-",
    "is_open": False,
    "closing_in": 0.0,
    "fps": 0.0,
    "timestamp": ""
}

BINS = {
    0: {"name": "General (ขยะทั่วไป)", "color": "#007bff", "pin": "GPIO 21", "lid": "BLUE"},
    1: {"name": "Recyclable (รีไซเคิล)", "color": "#ffc107", "pin": "GPIO 38", "lid": "YELLOW"},
    2: {"name": "Wet / Organic (ขยะเปียก)", "color": "#28a745", "pin": "GPIO 39", "lid": "GREEN"},
    3: {"name": "Hazardous (ขยะอันตราย)", "color": "#dc3545", "pin": "GPIO 40", "lid": "RED"}
}

def map_label_to_bin(label: str) -> int:
    label = label.lower()
    if any(k in label for k in ["bottle", "can", "cup", "wine glass", "cardboard", "plastic"]):
        return 1
    elif any(k in label for k in ["banana", "apple", "orange", "sandwich", "broccoli", "carrot", "pizza", "donut", "cake", "food"]):
        return 2
    elif any(k in label for k in ["battery", "cell phone", "remote", "mouse", "keyboard", "laptop", "scissors", "toaster"]):
        return 3
    else:
        return 0

def camera_loop():
    global current_frame_jpeg, current_status
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("[-] ไม่สามารถเชื่อมต่อกล้อง Webcam ได้")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    lid_open_until = 0
    active_bin = 0
    active_label = "None"
    active_conf = 0.0

    fps_time = time.time()
    fps = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        frame = cv2.flip(frame, 1)

        # Run YOLO inference
        results = model.predict(source=frame, conf=0.35, verbose=False)
        result = results[0]

        detected = []
        if len(result.boxes) > 0:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                conf = float(box.conf[0])

                if cls_name == "person":
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detected.append((cls_name, conf, (x1, y1, x2, y2)))

        now = time.time()

        # Trigger logic
        if detected and (now > lid_open_until):
            top_name, top_conf, top_box = max(detected, key=lambda x: x[1])
            target_bin = map_label_to_bin(top_name)
            active_bin = target_bin
            active_label = top_name
            active_conf = top_conf
            lid_open_until = now + 4.0

        is_open = (now < lid_open_until)
        remain = max(0.0, lid_open_until - now) if is_open else 0.0

        # Draw bounding boxes
        for cls_name, conf, (x1, y1, x2, y2) in detected:
            b_id = map_label_to_bin(cls_name)
            # Box color
            colors_bgr = {0: (220, 80, 20), 1: (0, 215, 255), 2: (30, 200, 30), 3: (30, 30, 230)}
            col = colors_bgr.get(b_id, (255, 255, 255))

            cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
            lbl = f"{cls_name} {conf*100:.0f}%"
            cv2.rectangle(frame, (x1, y1 - 22), (x1 + len(lbl)*10, y1), col, -1)
            cv2.putText(frame, lbl, (x1 + 4, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

        # FPS calculation
        fps = 0.9 * fps + 0.1 * (1.0 / max(0.001, (time.time() - fps_time)))
        fps_time = time.time()

        # Update status
        b_data = BINS[active_bin] if is_open else {"name": "Standby (รอรับขยะ)", "color": "#6c757d", "pin": "-", "lid": "NONE"}
        with camera_lock:
            current_status = {
                "detected_class": active_label if is_open else "None",
                "confidence": round(active_conf * 100, 1) if is_open else 0.0,
                "bin_id": active_bin if is_open else -1,
                "bin_name": b_data["name"],
                "bin_color": b_data["color"],
                "servo_pin": b_data["pin"],
                "lid": b_data["lid"],
                "is_open": is_open,
                "closing_in": round(remain, 1),
                "fps": round(fps, 1),
                "timestamp": time.strftime("%H:%M:%S")
            }

            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
            current_frame_jpeg = buffer.tobytes()

        time.sleep(0.03)

class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html lang="th">
            <head>
                <meta charset="UTF-8">
                <title>🤖 Smart AI Trash Bin - Live Webcam Simulator</title>
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
                <style>
                    body { background-color: #121212; color: #e0e0e0; font-family: 'Segoe UI', Tahoma, sans-serif; }
                    .card { background-color: #1e1e1e; border: 1px solid #333; }
                    .video-container { border-radius: 12px; overflow: hidden; border: 2px solid #444; box-shadow: 0 0 20px rgba(0,0,0,0.8); }
                    .oled-screen {
                        background-color: #000;
                        border: 3px solid #0dcaf0;
                        border-radius: 8px;
                        padding: 15px;
                        font-family: 'Courier New', Courier, monospace;
                        color: #0dcaf0;
                        min-height: 150px;
                        box-shadow: inset 0 0 10px rgba(13,202,240,0.5);
                    }
                    .bin-card {
                        border-radius: 10px;
                        padding: 15px;
                        text-align: center;
                        transition: all 0.3s ease;
                        opacity: 0.45;
                        border: 2px solid transparent;
                    }
                    .bin-card.active {
                        opacity: 1.0;
                        transform: scale(1.05);
                        box-shadow: 0 0 25px currentColor;
                        border-color: #fff;
                    }
                    .bin-blue { background-color: rgba(13, 110, 253, 0.25); color: #0d6efd; border-color: #0d6efd; }
                    .bin-yellow { background-color: rgba(255, 193, 7, 0.25); color: #ffc107; border-color: #ffc107; }
                    .bin-green { background-color: rgba(25, 135, 84, 0.25); color: #198754; border-color: #198754; }
                    .bin-red { background-color: rgba(220, 53, 69, 0.25); color: #dc3545; border-color: #dc3545; }
                    .log-table { font-size: 0.85rem; max-height: 200px; overflow-y: auto; }
                </style>
            </head>
            <body class="p-3">
                <div class="container-fluid">
                    <header class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary">
                        <h2 class="mb-0 text-info">🤖 Smart AI Trash Bin <span class="badge bg-secondary fs-6">Live Webcam Simulator</span></h2>
                        <div>
                            <span class="badge bg-dark border border-secondary p-2">FPS: <span id="fps-val">0</span></span>
                            <span class="badge bg-success p-2">● SYSTEM ONLINE</span>
                        </div>
                    </header>

                    <div class="row g-3">
                        <!-- Left: Live Video Stream -->
                        <div class="col-lg-7">
                            <div class="card p-2">
                                <h5 class="card-title text-light ps-2">📹 Live Webcam Stream (Auto-Scan Mode)</h5>
                                <div class="video-container text-center bg-black">
                                    <img src="/video_feed" style="width: 100%; max-height: 520px; object-fit: contain;">
                                </div>
                                <p class="text-secondary small mt-2 mb-0 ps-2">
                                    👉 ยื่นขยะ (ขวดน้ำ, เปลือกผลไม้, โทรศัพท์/ถ่าน, ถุงพลาสติก) เข้ามาหน้ากล้องเพื่อทดสอบ
                                </p>
                            </div>
                        </div>

                        <!-- Right: Virtual OLED & Bins -->
                        <div class="col-lg-5">
                            <!-- OLED Display -->
                            <div class="card p-3 mb-3">
                                <h6 class="text-uppercase text-secondary mb-2">📟 Virtual OLED 0.96" Display (SSD1306)</h6>
                                <div class="oled-screen" id="oled-box">
                                    <div class="fw-bold">&gt;&gt; SMART AI BIN &lt;&lt;</div>
                                    <hr class="my-1 border-info">
                                    <div id="oled-line1" class="mt-2 text-white">SYSTEM READY</div>
                                    <div id="oled-line2" class="text-warning">Hold trash 20cm</div>
                                    <div id="oled-line3" class="text-info">Auto-Scanning...</div>
                                </div>
                            </div>

                            <!-- 4 Virtual Bins -->
                            <div class="card p-3 mb-3">
                                <h6 class="text-uppercase text-secondary mb-2">🗑️ ถังขยะทั้ง 4 ช่อง (Servo Control Status)</h6>
                                <div class="row g-2">
                                    <div class="col-6">
                                        <div class="bin-card bin-blue" id="bin-card-0">
                                            <div class="fw-bold fs-5">1. ทั่วไป</div>
                                            <small>GPIO 21 (PWM)</small>
                                            <div class="mt-1 fw-bold status-lid">ฝาปิด 0°</div>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="bin-card bin-yellow" id="bin-card-1">
                                            <div class="fw-bold fs-5">2. รีไซเคิล</div>
                                            <small>GPIO 38 (PWM)</small>
                                            <div class="mt-1 fw-bold status-lid">ฝาปิด 0°</div>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="bin-card bin-green" id="bin-card-2">
                                            <div class="fw-bold fs-5">3. ขยะเปียก</div>
                                            <small>GPIO 39 (PWM)</small>
                                            <div class="mt-1 fw-bold status-lid">ฝาปิด 0°</div>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="bin-card bin-red" id="bin-card-3">
                                            <div class="fw-bold fs-5">4. อันตราย</div>
                                            <small>GPIO 40 (PWM)</small>
                                            <div class="mt-1 fw-bold status-lid">ฝาปิด 0°</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Live Event Log -->
                            <div class="card p-3">
                                <h6 class="text-uppercase text-secondary mb-2">📋 บันทึกประวัติการสแกน (Detection History)</h6>
                                <div class="log-table table-responsive">
                                    <table class="table table-dark table-sm table-striped">
                                        <thead>
                                            <tr>
                                                <th>เวลา</th>
                                                <th>วัตถุ</th>
                                                <th>ความมั่นใจ</th>
                                                <th>ถังขยะที่เปิด</th>
                                            </tr>
                                        </thead>
                                        <tbody id="log-body">
                                            <tr><td colspan="4" class="text-center text-muted">รอการตรวจจับขยะ...</td></tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <script>
                    let lastTriggerState = false;
                    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

                    function playBeep() {
                        try {
                            const osc = audioCtx.createOscillator();
                            const gain = audioCtx.createGain();
                            osc.connect(gain);
                            gain.connect(audioCtx.destination);
                            osc.frequency.value = 1200;
                            gain.gain.value = 0.15;
                            osc.start();
                            osc.stop(audioCtx.currentTime + 0.12);
                        } catch(e) {}
                    }

                    function updateStatus() {
                        fetch('/status')
                            .then(r => r.json())
                            .then(data => {
                                document.getElementById('fps-val').innerText = data.fps;

                                // Update OLED
                                if (data.is_open) {
                                    document.getElementById('oled-line1').innerText = "DETECT: " + data.detected_class;
                                    document.getElementById('oled-line2').innerText = "OPEN: " + data.lid + " LID (90°)";
                                    document.getElementById('oled-line3').innerText = "Closing in: " + data.closing_in + "s";
                                } else {
                                    document.getElementById('oled-line1').innerText = "SYSTEM READY";
                                    document.getElementById('oled-line2').innerText = "Hold trash 20cm";
                                    document.getElementById('oled-line3').innerText = "Auto-Scanning...";
                                }

                                // Update Bins
                                for (let i = 0; i < 4; i++) {
                                    const card = document.getElementById('bin-card-' + i);
                                    const statusLabel = card.querySelector('.status-lid');
                                    if (data.is_open && data.bin_id === i) {
                                        card.classList.add('active');
                                        statusLabel.innerText = ">> เปิดฝา 90° <<";
                                    } else {
                                        card.classList.remove('active');
                                        statusLabel.innerText = "ฝาปิด 0°";
                                    }
                                }

                                // Trigger sound & log
                                if (data.is_open && !lastTriggerState) {
                                    playBeep();
                                    addLog(data);
                                }
                                lastTriggerState = data.is_open;
                            })
                            .catch(err => console.error(err));
                    }

                    function addLog(data) {
                        const tbody = document.getElementById('log-body');
                        if (tbody.querySelector('.text-muted')) {
                            tbody.innerHTML = '';
                        }
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${data.timestamp}</td>
                            <td><span class="badge bg-secondary">${data.detected_class}</span></td>
                            <td>${data.confidence}%</td>
                            <td class="fw-bold" style="color:${data.bin_color}">${data.bin_name}</td>
                        `;
                        tbody.insertBefore(tr, tbody.firstChild);
                    }

                    setInterval(updateStatus, 250);
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))

        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            with camera_lock:
                status_json = json.dumps(current_status).encode('utf-8')
            self.wfile.write(status_json)

        elif self.path == '/video_feed':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    with camera_lock:
                        frame_bytes = current_frame_jpeg

                    if frame_bytes is not None:
                        self.wfile.write(b'--frame\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', str(len(frame_bytes)))
                        self.end_headers()
                        self.wfile.write(frame_bytes)
                        self.wfile.write(b'\r\n')
                    time.sleep(0.04)
            except (ConnectionResetError, BrokenPipeError):
                pass

def run():
    cam_thread = threading.Thread(target=camera_loop, daemon=True)
    cam_thread.start()

    server = HTTPServer(('0.0.0.0', PORT), WebHandler)
    print("=================================================================")
    print(f"  🤖 Smart Trash Bin - Live Web Dashboard Started!")
    print(f"  🌐 เปิดเบราว์เซอร์ไปที่: http://localhost:{PORT}")
    print("=================================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard.")

if __name__ == "__main__":
    run()
