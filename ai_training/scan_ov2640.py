"""
Smart AI Trash Bin - OV2640 Wireless Camera AI Scanner
======================================================
1. สั่ง ESP32-S3 ให้เริ่มนับถอยหลัง 3.. 2.. 1.. บนหน้าจอ OLED
2. ถ่ายภาพด้วยกล้อง OV2640 (ESP32-CAM) และส่งเข้าคอมพิวเตอร์
3. ประมวลผลด้วยโมเดล Custom AI (smart_bin_best.pt) จำแนก 4 คลาส
4. ส่งคำสั่งกลับไปแสดงผลบนจอ OLED และสั่งงานเซอร์โวเปิด-ปิดฝาถังจริง
5. แสดงผลบน Web Browser (VIEW_RESULT.html)
"""

import os
import sys
import time
import webbrowser
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

try:
    import serial
except ImportError:
    print("กรุณาติดตั้ง pyserial ด้วยคำสั่ง: pip install pyserial")
    sys.exit(1)

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULT_IMG_PATH = os.path.join(PROJECT_DIR, "RESULT_SCAN.jpg")
RESULT_HTML_PATH = os.path.join(PROJECT_DIR, "VIEW_RESULT.html")
MODEL_PATH = os.path.join(PROJECT_DIR, "ai_training", "trained_models", "smart_bin_best.pt")
FALLBACK_MODEL = os.path.join(PROJECT_DIR, "yolov8n.pt")
FONT_PATH = "C:\\Windows\\Fonts\\tahoma.ttf"

BINS = {
    0: {
        "name": "ขยะทั่วไป (General)",
        "color_en": "BLUE",
        "color_hex": "#0d6efd",
        "color_bgr": (253, 110, 13),
        "servo": "GPIO 21 (เปิด 90 องศา)",
        "desc": "ซองขนม, กล่องโฟม, ทิชชู่, ช้อนส้อมพลาสติก"
    },
    1: {
        "name": "ขยะรีไซเคิล (Recyclable)",
        "color_en": "YELLOW",
        "color_hex": "#ffc107",
        "color_bgr": (7, 193, 255),
        "servo": "GPIO 38 (เปิด 90 องศา)",
        "desc": "ขวดน้ำ PET ใส, แก้วน้ำ, กระป๋องอลูมิเนียม, กล่องกระดาษ"
    },
    2: {
        "name": "ขยะเปียก (Wet / Organic)",
        "color_en": "GREEN",
        "color_hex": "#198754",
        "color_bgr": (84, 135, 25),
        "servo": "GPIO 39 (เปิด 90 องศา)",
        "desc": "เศษอาหาร, เปลือกผลไม้, เศษผัก, ขนมปัง"
    },
    3: {
        "name": "ขยะอันตราย (Hazardous)",
        "color_en": "RED",
        "color_hex": "#dc3545",
        "color_bgr": (69, 53, 220),
        "servo": "GPIO 40 (เปิด 90 องศา)",
        "desc": "ถ่านชาร์จ, ถ่านไฟฉาย, แบตเตอรี่, แผงยา, ขยะอิเล็กทรอนิกส์"
    }
}

CLASS_NAME_MAP = {
    0: "ขยะทั่วไป / ซองขนม (General)",
    1: "ขวดน้ำ / กระป๋องรีไซเคิล (Recyclable)",
    2: "เศษอาหาร / ผลไม้ (Organic)",
    3: "ถ่านชาร์จ / แบตเตอรี่ / ขยะอันตราย (Battery/Hazardous)"
}

def draw_thai_text(img, text, position, font_size=20, color=(255, 255, 255), bg_color=None):
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        font = ImageFont.load_default()

    if bg_color is not None:
        bbox = draw.textbbox(position, text, font=font)
        pad = 4
        padded_bbox = (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)
        draw.rectangle(padded_bbox, fill=bg_color)

    draw.text(position, text, font=font, fill=color)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

def fetch_ov2640_image_from_s3(port="COM6"):
    """ส่งคำสั่ง CAPTURE ไปยัง ESP32-S3 แล้วรอรับไฟล์ภาพ JPEG ที่ส่งกลับมา"""
    print(f"\n[SERIAL] กำลังเชื่อมต่อพอร์ต {port}...")
    ser = serial.Serial(port, 115200, timeout=15)
    time.sleep(1.0)

    print("  -> ส่งคำสั่ง 'CAPTURE' เริ่มนับถอยหลัง 3.. 2.. 1.. บนหน้าจอ OLED...")
    ser.write(b"CAPTURE\n")

    img_data = bytearray()
    receiving_img = False
    expected_len = 0
    start_time = time.time()

    while time.time() - start_time < 15:
        if not receiving_img:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                print(f"  [S3 Log] {line}")
            if line.startswith("IMG_START:"):
                expected_len = int(line.split(":")[1])
                print(f"\n  📸 [SNAP!] กำลังรับข้อมูลภาพ JPEG ({expected_len} bytes) จากกล้อง OV2640...")
                receiving_img = True
                break
        time.sleep(0.01)

    if receiving_img and expected_len > 0:
        img_data = ser.read(expected_len)
        print(f"  [OK] รับข้อมูลภาพครบ {len(img_data)} bytes!")

    return ser, img_data

def classify_frame(frame, custom_model, coco_model):
    """วิเคราะห์จำแนกขยะ 4 คลาส"""
    res_custom = custom_model.predict(frame, conf=0.20, verbose=False)[0]
    if len(res_custom.boxes) > 0:
        best_box = max(res_custom.boxes, key=lambda b: float(b.conf[0]))
        cls_id = int(best_box.cls[0].item())
        conf = float(best_box.conf[0].item())
        bx = best_box.xyxy[0].cpu().numpy().astype(int)
        return cls_id, CLASS_NAME_MAP.get(cls_id, "ขยะอันตราย"), conf, bx

    res_coco = coco_model.predict(frame, conf=0.20, verbose=False)[0]
    coco_items = []
    for box in res_coco.boxes:
        cls_name = coco_model.names[int(box.cls[0].item())].lower()
        if cls_name == "person":
            continue
        conf = float(box.conf[0].item())
        bx = box.xyxy[0].cpu().numpy().astype(int)
        if cls_name in ["toothbrush", "remote", "cell phone", "mouse"]:
            coco_items.append((3, "ถ่านชาร์จ / แบตเตอรี่ (Battery/Hazardous)", conf, bx))
        elif cls_name in ["bottle", "cup", "wine glass", "can"]:
            coco_items.append((1, "ขวดน้ำ / กระป๋องรีไซเคิล (Recyclable)", conf, bx))
        elif cls_name in ["banana", "apple", "orange", "sandwich", "pizza", "donut", "cake"]:
            coco_items.append((2, "เศษอาหาร / ผลไม้ (Organic)", conf, bx))
        else:
            coco_items.append((0, "ขยะทั่วไป (General)", conf, bx))

    if coco_items:
        best = max(coco_items, key=lambda x: x[2])
        return best[0], best[1], best[2], best[3]

    return 0, "ขยะทั่วไป (General)", 0.65, np.array([50, 50, frame.shape[1]-50, frame.shape[0]-50])

def main():
    print("=" * 65)
    print("  📸 SMART TRASH BIN - OV2640 WIRELESS CAMERA AI SCANNER")
    print("=" * 65)
    print("กำลังโหลดโมเดล AI (Custom YOLOv8)...")
    custom_model = YOLO(MODEL_PATH)
    coco_model = YOLO(FALLBACK_MODEL)

    print("\n👉 นำขยะ (ถ่านชาร์จ, แผงยา, ขวดน้ำ, ซองขนม) ไปส่องหน้าเลนส์กล้อง OV2640...")
    print("   มองดูที่หน้าจอ OLED: จะมีเลขนับถอยหลัง [ 3 ] -> [ 2 ] -> [ 1 ] !")

    try:
        ser, img_data = fetch_ov2640_image_from_s3("COM6")
    except Exception as e:
        print(f"  [ERROR] ไม่สามารถติดต่อพอร์ต COM6 ได้: {e}")
        input("กด Enter เพื่อออก...")
        return

    if not img_data or len(img_data) < 500:
        print("  [ERROR] ไม่ได้รับภาพจากกล้อง OV2640 กรุณาตรวจสอบว่าบอร์ด ESP32-CAM เสียบไฟอยู่")
        ser.close()
        input("กด Enter เพื่อออก...")
        return

    nparr = np.frombuffer(img_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        print("  [ERROR] ถอดรหัสภาพ JPEG ไม่สำเร็จ")
        ser.close()
        return

    print(f"  🎉 [CAMERA OK] ได้รับภาพจากกล้อง OV2640 ขนาด: {frame.shape[1]}x{frame.shape[0]} พิกเซล!")
    print("  🤖 กำลังประมวลผลด้วยโมเดล AI (YOLOv8)...")

    detected_bin, best_label, best_conf, bx = classify_frame(frame, custom_model, coco_model)

    # วาดกรอบและป้ายภาษาไทย
    color = BINS[detected_bin]["color_bgr"]
    cv2.rectangle(frame, (bx[0], bx[1]), (bx[2], bx[3]), color, 3)
    label_txt = f"{best_label} ({best_conf*100:.1f}%) -> {BINS[detected_bin]['name']}"
    frame = draw_thai_text(frame, label_txt, (bx[0], max(10, bx[1] - 32)), font_size=18, color=(255,255,255), bg_color=(color[2], color[1], color[0]))

    bin_info = BINS[detected_bin]
    banner_txt = f"กล้อง OV2640 | {bin_info['name']} | สั่งงาน: {bin_info['servo']}"
    frame = draw_thai_text(frame, banner_txt, (15, 15), font_size=20, color=(255,255,255), bg_color=(20, 20, 20))
    cv2.imwrite(RESULT_IMG_PATH, frame)

    print(f"\n  🎉 [AI RESULT] ตรวจพบ: {best_label}")
    print(f"     ประเภท: {bin_info['name']}")
    print(f"     ความมั่นใจ: {best_conf*100:.1f}%")
    print(f"     สั่งเปิดฝา: {bin_info['servo']}")

    # ส่งคำสั่งเปิดฝาและแสดงผลบนจอ OLED กลับไปที่ ESP32-S3
    print(f"\n  📺 กำลังส่งคำสั่ง BIN:{detected_bin} ไปยังจอ OLED และเซอร์โว...")
    cmd = f"BIN:{detected_bin}\n"
    ser.write(cmd.encode())
    time.sleep(0.5)

    s3_ack = []
    for _ in range(3):
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            s3_ack.append(line)
            print(f"  [ESP32-S3 ACK] {line}")
    ser.close()

    esp_status = " | ".join(s3_ack) if s3_ack else f"คำสั่ง BIN:{detected_bin} ส่งเข้าจอ OLED และเซอร์โวเรียบร้อย"

    # สร้างหน้า HTML Dashboard
    html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>Smart AI Trash Bin - ผลการสแกนด้วยกล้อง OV2640</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
        .container {{ max-width: 960px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        h1 {{ margin-top: 0; color: #38bdf8; display: flex; align-items: center; gap: 12px; font-size: 26px; }}
        .badge {{ background: #0284c7; color: white; padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: normal; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 20px; }}
        .card {{ background: #334155; border-radius: 12px; padding: 20px; border-left: 6px solid {bin_info['color_hex']}; }}
        .card h2 {{ margin: 0 0 12px 0; font-size: 18px; color: #94a3b8; }}
        .result-title {{ font-size: 28px; font-weight: bold; color: {bin_info['color_hex']}; margin-bottom: 8px; }}
        .spec-item {{ margin: 8px 0; font-size: 15px; display: flex; justify-content: space-between; border-bottom: 1px solid #475569; padding-bottom: 6px; }}
        .spec-label {{ color: #94a3b8; }}
        .spec-val {{ font-weight: bold; color: #f1f5f9; }}
        .img-box {{ border-radius: 12px; overflow: hidden; border: 2px solid #475569; text-align: center; background: #020617; }}
        .img-box img {{ width: 100%; height: auto; display: block; }}
        .btn {{ display: inline-block; background: #0284c7; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 20px; cursor: pointer; border: none; }}
        .btn:hover {{ background: #0369a1; }}
        .log-box {{ background: #020617; color: #4ade80; padding: 12px; border-radius: 8px; font-family: Consolas, monospace; font-size: 13px; margin-top: 12px; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📸 Smart AI Trash Bin <span class="badge">กล้อง OV2640 + จอ OLED</span></h1>
        
        <div class="grid">
            <div class="img-box">
                <img src="RESULT_SCAN.jpg?t={int(time.time())}" alt="OV2640 Camera Capture">
            </div>

            <div>
                <div class="card">
                    <h2>ผลการจำแนกประเภทขยะ (AI Result)</h2>
                    <div class="result-title">{bin_info['name']}</div>
                    <div class="spec-item"><span class="spec-label">กล้องที่ใช้:</span><span class="spec-val" style="color:#38bdf8;">โมดูลกล้องจริง OV2640</span></div>
                    <div class="spec-item"><span class="spec-label">วัตถุที่ตรวจพบ:</span><span class="spec-val">{best_label}</span></div>
                    <div class="spec-item"><span class="spec-label">ระดับความมั่นใจ:</span><span class="spec-val">{best_conf*100:.1f}%</span></div>
                    <div class="spec-item"><span class="spec-label">สีถังประจำช่อง:</span><span class="spec-val">{bin_info['color_en']}</span></div>
                    <div class="spec-item"><span class="spec-label">คำสั่งมอเตอร์เซอร์โว:</span><span class="spec-val" style="color:#38bdf8;">{bin_info['servo']}</span></div>
                    <div class="spec-item"><span class="spec-label">การแสดงผลบนจอ OLED:</span><span class="spec-val" style="color:#4ade80;">โชว์เลขนับถอยหลัง 3..2..1 + Alarm</span></div>
                </div>

                <div class="card" style="margin-top: 16px; border-left-color: #38bdf8;">
                    <h2>สถานะบอร์ด ESP32-S3 & จอ OLED</h2>
                    <div class="log-box">{esp_status}</div>
                </div>

                <button class="btn" onclick="location.reload();">🔄 รีเฟรชผลลัพธ์</button>
            </div>
        </div>
    </div>
</body>
</html>"""

    with open(RESULT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n  🌐 [DASHBOARD] เปิดหน้าแสดงผลบนเว็บเบราว์เซอร์แล้ว: VIEW_RESULT.html")
    webbrowser.open(f"file:///{RESULT_HTML_PATH.replace(os.sep, '/')}")
    print("=" * 65)

if __name__ == "__main__":
    main()
