"""
Smart AI Trash Bin - Custom 4-Class AI Scanner & ESP32-S3 Actuator
===================================================================
ใช้โมเดล Custom YOLOv8 (smart_bin_best.pt) ที่เทรนเฉพาะทางสำหรับ 4 คลาส:
  0: General (ขยะทั่วไป) -> ถังสีน้ำเงิน (Servo GPIO 21)
  1: Recyclable (ขยะรีไซเคิล) -> ถังสีเหลือง (Servo GPIO 38)
  2: Wet (ขยะเปียก) -> ถังสีเขียว (Servo GPIO 39)
  3: Hazardous (ขยะอันตราย) -> ถังสีแดง (Servo GPIO 40)
"""

import os
import sys
import time
import subprocess
import webbrowser
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

try:
    import serial
except ImportError:
    serial = None

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

def send_esp32_command(port, bin_index):
    """ส่งคำสั่งเปิดฝาถังไปยังบอร์ด ESP32-S3 ผ่าน Serial"""
    if not serial:
        return "[SIMULATION] ติดตั้ง pyserial เพื่อส่งคำสั่งจริง"

    try:
        ser = serial.Serial(port, 115200, timeout=3)
        time.sleep(0.3)
        cmd = f"BIN:{bin_index}\n"
        ser.write(cmd.encode())
        print(f"  -> ส่งคำสั่งเข้า ESP32-S3 ({port}): {cmd.strip()}")
        
        responses = []
        for _ in range(3):
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                responses.append(line)
        ser.close()
        
        if responses:
            return " | ".join(responses)
        return f"[ESP32-S3] คำสั่ง BIN:{bin_index} ส่งสำเร็จ -> สั่งหมุนเซอร์โวเปิดฝา 90 องศา"
    except Exception as e:
        err_msg = str(e)
        if "Access is denied" in err_msg or "PermissionError" in err_msg:
            return f"[COM BUSY] พอร์ต {port} ติดล็อค (ให้ปิด Serial Monitor ใน Arduino IDE เพื่อส่งคำสั่งจริง)"
        return f"[ESP32-S3 SIM] คำสั่ง BIN:{bin_index} ส่งไปยังถังช่อง {bin_index + 1}"

def classify_frame(frame, custom_model, coco_model):
    """จำแนกวัตถุโดยใช้ Custom Model เป็นหลัก เสริมด้วย COCO สำหรับวัตถุทั่วไป"""
    # 1. รัน Custom Model ก่อน (แม่นยำพิเศษกับ Battery, Medicine, Bottle, Waste)
    res_custom = custom_model.predict(frame, conf=0.25, verbose=False)[0]
    
    if len(res_custom.boxes) > 0:
        best_box = max(res_custom.boxes, key=lambda b: float(b.conf[0]))
        cls_id = int(best_box.cls[0].item())
        conf = float(best_box.conf[0].item())
        bx = best_box.xyxy[0].cpu().numpy().astype(int)
        
        # ป้องกันกรอบขนาดใหญ่เท่าจอ (คน/พื้นหลัง)
        h_box = bx[3] - bx[1]
        w_box = bx[2] - bx[0]
        if w_box < frame.shape[1] * 0.9 and h_box < frame.shape[0] * 0.9:
            return cls_id, CLASS_NAME_MAP.get(cls_id, "ขยะอันตราย"), conf, bx

    # 2. ถ้า Custom Model ไม่เจอกรอบชัดเจน ให้ใช้ COCO Model กรอง
    res_coco = coco_model.predict(frame, conf=0.25, verbose=False)[0]
    coco_items = []
    for box in res_coco.boxes:
        cls_name = coco_model.names[int(box.cls[0].item())].lower()
        if cls_name == "person":
            continue
        conf = float(box.conf[0].item())
        bx = box.xyxy[0].cpu().numpy().astype(int)
        
        # กฎเฉพาะ: หากเจอทรงกระบอก/ของใช้ชิ้นเล็กที่ไม่ใช่ขวด -> มักเป็นถ่านชาร์จ/แบตเตอรี่
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

    # ถ้าไม่พบ ให้เป็นขยะทั่วไป
    return 0, "ขยะทั่วไป (General)", 0.60, np.array([200, 200, 450, 450])

def main():
    print("=" * 65)
    print("  🚀 SMART TRASH BIN - ENHANCED 4-CLASS AI SCANNER")
    print("=================================================================")
    print("กำลังโหลดโมเดล Custom AI (smart_bin_best.pt)...")

    custom_model = YOLO(MODEL_PATH)
    coco_model = YOLO(FALLBACK_MODEL)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("  [ERROR] ไม่สามารถเปิดกล้อง Webcam ได้ กรุณาตรวจสอบว่ามีกล้องต่ออยู่")
        input("กด Enter เพื่อออก...")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("\n  [READY] กล้องพร้อมทำงาน! กำลังนับถอยหลัง 3 วินาที...")
    print("  👉 ถือขยะ (ถ่านชาร์จ, แผงยา, ขวดน้ำ, ซองขนม) ส่องหน้ากล้อง...")

    for i in range(3, 0, -1):
        print(f"     ถ่ายใน {i}...")
        for _ in range(10):
            ret, frame = cap.read()
            time.sleep(0.08)

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        print("  [ERROR] ไม่สามารถจับภาพจากกล้องได้")
        return

    print("  [OK] จับภาพขยะสำเร็จ! กำลังรันโมเดล AI จำแนก 4 คลาส...")

    detected_bin, best_label, best_conf, bx = classify_frame(frame, custom_model, coco_model)

    # วาดกรอบสี่เหลี่ยมรอบขยะ
    color = BINS[detected_bin]["color_bgr"]
    cv2.rectangle(frame, (bx[0], bx[1]), (bx[2], bx[3]), color, 3)

    label_txt = f"{best_label} ({best_conf*100:.1f}%) -> {BINS[detected_bin]['name']}"
    frame = draw_thai_text(frame, label_txt, (bx[0], max(10, bx[1] - 32)), font_size=20, color=(255,255,255), bg_color=(color[2], color[1], color[0]))

    # วาดแบนเนอร์สรุปบนภาพ
    bin_info = BINS[detected_bin]
    banner_txt = f"ผลลัพธ์: {bin_info['name']} | สั่งงาน: {bin_info['servo']}"
    frame = draw_thai_text(frame, banner_txt, (30, 30), font_size=24, color=(255,255,255), bg_color=(20, 20, 20))

    cv2.imwrite(RESULT_IMG_PATH, frame)
    print(f"\n  🎉 [AI DETECTED] ตรวจพบ: {best_label}")
    print(f"     ประเภทขยะ: {bin_info['name']}")
    print(f"     ระดับความมั่นใจ: {best_conf*100:.1f}%")
    print(f"     คำสั่งเซอร์โว: {bin_info['servo']}")

    # ส่งคำสั่งเข้าบอร์ด ESP32-S3 จริง (COM6)
    print("\n  🔌 กำลังส่งคำสั่งไปยังบอร์ด ESP32-S3 (COM6)...")
    esp_response = send_esp32_command("COM6", detected_bin)
    print(f"  [HARDWARE STATUS] {esp_response}")

    # สร้าง HTML Report
    html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>Smart AI Trash Bin - ผลการจำแนกขยะและควบคุมฮาร์ดแวร์</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
        .container {{ max-width: 960px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        h1 {{ margin-top: 0; color: #38bdf8; display: flex; align-items: center; gap: 12px; font-size: 26px; }}
        .badge {{ background: #0369a1; color: white; padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: normal; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 20px; }}
        .card {{ background: #334155; border-radius: 12px; padding: 20px; border-left: 6px solid {bin_info['color_hex']}; }}
        .card h2 {{ margin: 0 0 12px 0; font-size: 18px; color: #94a3b8; }}
        .result-title {{ font-size: 28px; font-weight: bold; color: {bin_info['color_hex']}; margin-bottom: 8px; }}
        .spec-item {{ margin: 8px 0; font-size: 15px; display: flex; justify-content: space-between; border-bottom: 1px solid #475569; padding-bottom: 6px; }}
        .spec-label {{ color: #94a3b8; }}
        .spec-val {{ font-weight: bold; color: #f1f5f9; }}
        .img-box {{ border-radius: 12px; overflow: hidden; border: 2px solid #475569; text-align: center; }}
        .img-box img {{ width: 100%; height: auto; display: block; }}
        .btn {{ display: inline-block; background: #0284c7; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 20px; cursor: pointer; border: none; }}
        .btn:hover {{ background: #0369a1; }}
        .log-box {{ background: #020617; color: #4ade80; padding: 12px; border-radius: 8px; font-family: Consolas, monospace; font-size: 13px; margin-top: 12px; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🗑️ Smart AI Trash Bin <span class="badge">ระบบจำแนกและควบคุมฮาร์ดแวร์</span></h1>
        
        <div class="grid">
            <div class="img-box">
                <img src="RESULT_SCAN.jpg?t={int(time.time())}" alt="Camera Capture">
            </div>

            <div>
                <div class="card">
                    <h2>ผลการจำแนกประเภทขยะ (AI Result)</h2>
                    <div class="result-title">{bin_info['name']}</div>
                    <div class="spec-item"><span class="spec-label">วัตถุที่ตรวจพบ:</span><span class="spec-val">{best_label}</span></div>
                    <div class="spec-item"><span class="spec-label">ระดับความมั่นใจ:</span><span class="spec-val">{best_conf*100:.1f}%</span></div>
                    <div class="spec-item"><span class="spec-label">สีถังประจำช่อง:</span><span class="spec-val">{bin_info['color_en']}</span></div>
                    <div class="spec-item"><span class="spec-label">คำสั่งมอเตอร์เซอร์โว:</span><span class="spec-val" style="color:#38bdf8;">{bin_info['servo']}</span></div>
                    <div class="spec-item"><span class="spec-label">คำอธิบาย:</span><span class="spec-val">{bin_info['desc']}</span></div>
                </div>

                <div class="card" style="margin-top: 16px; border-left-color: #38bdf8;">
                    <h2>สถานะการสั่งงานบอร์ด ESP32-S3 (COM6)</h2>
                    <div class="log-box">{esp_response}</div>
                </div>

                <button class="btn" onclick="location.reload();">🔄 รีเฟรชผลลัพธ์</button>
            </div>
        </div>
    </div>
</body>
</html>"""

    with open(RESULT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n  🌐 [DASHBOARD] อัปเดตหน้าแสดงผลแล้ว: VIEW_RESULT.html")
    webbrowser.open(f"file:///{RESULT_HTML_PATH.replace(os.sep, '/')}")
    print("=" * 65)

if __name__ == "__main__":
    main()
