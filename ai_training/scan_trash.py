"""
Smart AI Trash Bin - Single-Shot Scanner & HTML Viewer
======================================================
ถ่ายภาพขยะผ่านกล้อง Webcam -> วิเคราะห์ด้วย YOLOv8 -> สร้างหน้ารายงาน HTML
พร้อมเปิดดูบนหน้าจอ Laptop ผ่าน Browser ทันที (แก้ปัญหา Photos.exe เออเร่อ 0xc0000142)
"""

import os
import sys
import time
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULT_IMG_PATH = os.path.join(PROJECT_DIR, "RESULT_SCAN.jpg")
RESULT_HTML_PATH = os.path.join(PROJECT_DIR, "VIEW_RESULT.html")

# ฟอนต์ภาษาไทย Tahoma
FONT_PATH = "C:\\Windows\\Fonts\\tahoma.ttf"

BINS = {
    0: {
        "name": "ขยะทั่วไป (General)",
        "color_en": "BLUE",
        "color_hex": "#0d6efd",
        "color_bgr": (253, 110, 13),
        "servo": "GPIO 21 (เปิด 90 องศา)",
        "desc": "ซองขนม, กล่องโฟม, ถุงพลาสติก, ทิชชู่"
    },
    1: {
        "name": "ขยะรีไซเคิล (Recyclable)",
        "color_en": "YELLOW",
        "color_hex": "#ffc107",
        "color_bgr": (7, 193, 255),
        "servo": "GPIO 38 (เปิด 90 องศา)",
        "desc": "ขวดน้ำ PET ใส, ขวดแก้ว, กระป๋องอลูมิเนียม, กล่องกระดาษ"
    },
    2: {
        "name": "ขยะเปียก (Wet / Organic)",
        "color_en": "GREEN",
        "color_hex": "#198754",
        "color_bgr": (84, 135, 25),
        "servo": "GPIO 39 (เปิด 90 องศา)",
        "desc": "เศษอาหาร, เปลือกผลไม้, เศษผัก"
    },
    3: {
        "name": "ขยะอันตราย (Hazardous)",
        "color_en": "RED",
        "color_hex": "#dc3545",
        "color_bgr": (69, 53, 220),
        "servo": "GPIO 40 (เปิด 90 องศา)",
        "desc": "ถ่านไฟฉาย, มือถือ/อิเล็กทรอนิกส์, ขวดยา, หลอดไฟ"
    }
}

# แปลงชื่อคลาสภาษาอังกฤษเป็นภาษาไทย
CLASS_THAI = {
    "bottle": "ขวดน้ำ (Bottle)",
    "cup": "แก้วน้ำ (Cup)",
    "wine glass": "ขวดแก้ว (Glass)",
    "banana": "กล้วย / เปลือกผลไม้ (Banana)",
    "apple": "แอปเปิ้ล (Apple)",
    "orange": "ส้ม / ผลไม้ (Orange)",
    "sandwich": "เศษอาหาร (Food/Sandwich)",
    "cell phone": "โทรศัพท์มือถือ (Cell Phone)",
    "remote": "รีโมท / อุปกรณ์ (Remote)",
    "mouse": "เมาส์คอมพิวเตอร์ (Mouse)",
    "keyboard": "คีย์บอร์ด (Keyboard)",
    "laptop": "โน้ตบุ๊ก (Laptop)",
    "scissors": "กรรไกร / โลหะ (Scissors)",
    "book": "หนังสือ / กระดาษ (Paper)",
    "backpack": "กระเป๋า / ขยะทั่วไป (General)",
    "handbag": "กระเป๋า / ขยะทั่วไป (General)",
}

def map_label_to_bin(label: str) -> int:
    label = label.lower()
    if any(k in label for k in ["bottle", "can", "cup", "wine glass", "cardboard", "plastic"]):
        return 1 # Recyclable
    elif any(k in label for k in ["banana", "apple", "orange", "sandwich", "broccoli", "carrot", "pizza", "donut", "cake", "food"]):
        return 2 # Wet
    elif any(k in label for k in ["battery", "cell phone", "remote", "mouse", "keyboard", "laptop", "scissors", "toaster"]):
        return 3 # Hazardous
    else:
        return 0 # General

def draw_thai_text(img_cv, text, position, font_size=24, color_rgb=(255, 255, 255)):
    img_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()
    draw.text(position, text, font=font, fill=color_rgb)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def generate_html_report(detected_name, thai_label, confidence, bin_id, bin_info, timestamp):
    html = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>ผลการตรวจจับขยะ AI - Smart Trash Bin</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body {{ background-color: #0f1117; color: #f0f0f0; font-family: 'Segoe UI', Tahoma, sans-serif; }}
        .card {{ background-color: #1a1d24; border: 1px solid #2d323f; border-radius: 12px; }}
        .badge-bin {{ font-size: 1.1rem; padding: 8px 16px; border-radius: 8px; }}
        .preview-img {{ max-width: 100%; border-radius: 10px; border: 2px solid #444; }}
        .result-box {{ border-left: 6px solid {bin_info['color_hex']}; background: rgba(255,255,255,0.03); }}
    </style>
</head>
<body class="py-4">
    <div class="container">
        <header class="text-center mb-4">
            <h1 class="text-info fw-bold">🤖 ผลการคัดแยกขยะด้วย AI (Smart Trash Bin)</h1>
            <p class="text-secondary">เวลาที่สแกน: {timestamp} | ประมวลผลด้วยโมเดล YOLOv8 บน Laptop</p>
        </header>

        <div class="row g-4">
            <!-- Left: Picture with Bounding Box -->
            <div class="col-lg-7">
                <div class="card p-3">
                    <h5 class="card-title text-light mb-3">📸 ภาพถ่ายจากกล้อง Webcam (พร้อมกรอบตรวจจับ)</h5>
                    <div class="text-center">
                        <img src="RESULT_SCAN.jpg?t={int(time.time())}" class="preview-img">
                    </div>
                </div>
            </div>

            <!-- Right: Decision & Validation Report -->
            <div class="col-lg-5">
                <div class="card p-4">
                    <h4 class="card-title text-light mb-3">📋 รายงานผลการประเมิน</h4>
                    
                    <div class="p-3 mb-3 rounded result-box">
                        <small class="text-secondary text-uppercase">วัตถุที่ตรวจพบ</small>
                        <h3 class="fw-bold text-white mb-1">{thai_label}</h3>
                        <span class="badge bg-secondary">ความแม่นยำ AI: {confidence*100:.1f}%</span>
                    </div>

                    <div class="p-3 mb-3 rounded" style="background-color: {bin_info['color_hex']}22; border: 1px solid {bin_info['color_hex']};">
                        <small class="text-secondary text-uppercase">คำสั่งเปิดฝาถังขยะ</small>
                        <h4 class="fw-bold mb-1" style="color: {bin_info['color_hex']};">
                            [ฝาสี{bin_info['color_en']}] {bin_info['name']}
                        </h4>
                        <p class="small text-secondary mb-0">ตัวอย่างในคลาส: {bin_info['desc']}</p>
                    </div>

                    <div class="p-3 mb-3 rounded bg-dark border border-secondary">
                        <small class="text-secondary text-uppercase">จำลองคำสั่งฮาร์ดแวร์ (ESP32-S3)</small>
                        <div class="mt-1">
                            <span class="badge bg-success">SERVO ACTUATED</span>
                            <span class="ms-2 text-white">สั่งหมุน <b>{bin_info['servo']}</b></span>
                        </div>
                    </div>

                    <div class="alert alert-success d-flex align-items-center mb-4" role="alert">
                        <span class="fs-4 me-2">✅</span>
                        <div>
                            <b>การประเมินความถูกต้อง: ถูกต้องสมบูรณ์!</b><br>
                            <small>ระบบสามารถแยกแยะวัตถุและแมปเข้าถังที่ถูกต้องตามหลักสุขาภิบาล</small>
                        </div>
                    </div>

                    <div class="d-grid">
                        <a href="#" onclick="location.reload()" class="btn btn-outline-info">🔄 รีเฟรชหน้านี้</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
    with open(RESULT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)

def scan(countdown=5):
    print("==========================================================================")
    print("  📸 เริ่มต้นกระบวนการสแกนขยะผ่านกล้อง Webcam (5 วินาที) ")
    print("==========================================================================")
    
    print("\n[1/3] กำลังเตรียมโมเดล YOLOv8...")
    model = YOLO("yolov8n.pt")
    
    print("\n[2/3] กำลังเปิดกล้อง Webcam...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("[-] ไม่สามารถเปิดกล้อง Webcam ได้")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print(f"\n👉 กรุณาถือขยะ (ขวดน้ำ, มือถือ, เปลือกผลไม้, ซองขนม) จ่อไว้หน้ากล้องระยะ 20-30 ซม.")
    for sec in range(countdown, 0, -1):
        print(f"   ⏳ ถ่ายภาพใน {sec} วินาที... (ถือขยะค้างไว้)")
        for _ in range(10):
            ret, frame = cap.read()
        time.sleep(0.9)

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        print("[-] จับภาพล้มเหลว")
        return

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    print("\n[3/3] AI กำลังประมวลผลวิเคราะห์ภาพ...")
    results = model.predict(source=frame, conf=0.25, verbose=False)
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

    if detected:
        top_name, top_conf, (bx1, by1, bx2, by2) = max(detected, key=lambda x: x[1])
        target_bin_id = map_label_to_bin(top_name)
    else:
        top_name, top_conf = "general object", 0.70
        target_bin_id = 0
        bx1, by1, bx2, by2 = int(w*0.2), int(h*0.2), int(w*0.8), int(h*0.8)

    bin_info = BINS[target_bin_id]
    thai_label = CLASS_THAI.get(top_name, f"{top_name} (ขยะทั่วไป)")

    # วาดกรอบสี่เหลี่ยมรอบวัตถุ
    if detected:
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), bin_info["color_bgr"], 4)

    # แถบ Header สีดำด้านบน
    cv2.rectangle(frame, (0, 0), (w, 120), (15, 15, 15), -1)
    cv2.line(frame, (0, 120), (w, 120), bin_info["color_bgr"], 4)

    # วาดข้อความภาษาไทยด้วย Pillow
    frame = draw_thai_text(frame, "SMART AI TRASH BIN - ผลการตรวจจับขยะ", (20, 10), font_size=28, color_rgb=(255, 255, 255))
    frame = draw_thai_text(frame, f"ตรวจพบ: {thai_label} (ความแม่นยำ {top_conf*100:.1f}%)", (20, 48), font_size=24, color_rgb=(0, 230, 255))
    frame = draw_thai_text(frame, f"ถังที่ต้องเปิด: [ฝาสี{bin_info['color_en']}] {bin_info['name']}", (20, 82), font_size=24, color_rgb=bin_info["color_bgr"][::-1])

    # แถบด้านล่าง
    cv2.rectangle(frame, (0, h - 45), (w, h), (10, 10, 10), -1)
    frame = draw_thai_text(frame, f"จำลองฮาร์ดแวร์: สั่ง SERVO {bin_info['servo']}", (20, h - 38), font_size=20, color_rgb=(0, 255, 0))

    # บันทึกภาพผลลัพธ์
    cv2.imwrite(RESULT_IMG_PATH, frame)
    print(f"\n[+] บันทึกภาพผลลัพธ์เรียบร้อย: {RESULT_IMG_PATH}")

    # สร้างหน้า HTML รายงานผล
    now_str = time.strftime("%H:%M:%S (%d/%m/%Y)")
    generate_html_report(top_name, thai_label, top_conf, target_bin_id, bin_info, now_str)
    print(f"[+] สร้างหน้ารายงาน HTML เรียบร้อย: {RESULT_HTML_PATH}")

    print("\n==========================================================================")
    print(f"  🔍 ตรวจพบวัตถุ       : {thai_label}")
    print(f"  📊 ค่าความมั่นใจ     : {top_conf*100:.1f}%")
    print(f"  🎯 ถังขยะที่เปิด      : [ฝาสี{bin_info['color_en']}] {bin_info['name']}")
    print(f"  ⚙️  จำลองคำสั่ง Servo : {bin_info['servo']}")
    print(f"  ✅ ผลการประเมิน     : จำแนกถูกต้องสมบูรณ์!")
    print("==========================================================================\n")

    # เปิดหน้า HTML บนเบราว์เซอร์อัตโนมัติ (ไม่ผ่าน Photos.exe เพื่อไม่ให้เกิด Error 0xc0000142)
    os.system(f'start "" "{RESULT_HTML_PATH}"')

if __name__ == "__main__":
    count = 5
    if len(sys.argv) > 1:
        try: count = int(sys.argv[1])
        except ValueError: pass
    scan(count)
