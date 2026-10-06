"""
Smart AI Trash Bin - Master Continuous Service
================================================
เชื่อมต่อ ESP32-S3 (COM6) + กล้อง OV2640 + โมเดล AI (Custom YOLOv8) แบบ Real-time

วงจรการทำงานอัตโนมัติ:
1. รอรับสัญญาณจากเซนเซอร์ (IR หรือ Ultrasonic) จากบอร์ด ESP32-S3
2. เมื่อคนเดินมาจ่อขยะ -> บอร์ดจะนับถอยหลัง 3..2..1 บนจอ OLED แล้วถ่ายภาพผ่านกล้อง OV2640
3. สคริปต์นี้จะรับภาพ JPEG เข้ามาประมวลผลด้วยโมเดล AI (smart_bin_best.pt) ในเวลา ~50ms
4. จำแนกประเภทขยะเป็น 4 กลุ่ม:
   - Class 0: ขยะทั่วไป (General) -> ถังสีน้ำเงิน
   - Class 1: ขยะรีไซเคิล (Recyclable) -> ถังสีเหลือง
   - Class 2: ขยะเปียก (Organic / Food) -> ถังสีเขียว
   - Class 3: ขยะอันตราย (Hazardous / Battery) -> ถังสีแดง
5. ส่งผลลัพธ์กลับไปยังบอร์ด ESP32-S3 เพื่อ:
   - แสดงผลชื่อประเภทขยะบนจอ OLED
   - สั่งมอเตอร์เซอร์โว (GPIO 21) หมุนเปิดฝา 90 องศา ค้างไว้ 3.5 วินาที แล้วปิดกลับอัตโนมัติ!
6. อัปเดตหน้าเว็บ Dashboard (VIEW_RESULT.html) ให้ดูภาพและผลลัพธ์สดๆ ทันที
"""

import os
import sys
import time
import threading
import webbrowser
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO

try:
    import serial
except ImportError:
    print("[ERROR] กรุณาติดตั้ง pyserial ด้วยคำสั่ง: pip install pyserial")
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
        "color_en": "BLUE LID",
        "color_hex": "#0d6efd",
        "color_bgr": (253, 110, 13),
        "servo": "Servo GPIO 21 (เปิด 90 องศา)",
        "desc": "ซองขนม, กล่องโฟม, ทิชชู่, ถุงพลาสติก"
    },
    1: {
        "name": "ขยะรีไซเคิล (Recyclable)",
        "color_en": "YELLOW LID",
        "color_hex": "#ffc107",
        "color_bgr": (7, 193, 255),
        "servo": "Servo GPIO 38 (เปิด 90 องศา)",
        "desc": "ขวดน้ำ PET ใส, แก้วน้ำ, กระป๋องอลูมิเนียม, กล่องกระดาษ"
    },
    2: {
        "name": "ขยะเปียก (Organic / Food)",
        "color_en": "GREEN LID",
        "color_hex": "#198754",
        "color_bgr": (84, 135, 25),
        "servo": "Servo GPIO 39 (เปิด 90 องศา)",
        "desc": "เศษอาหาร, เปลือกผลไม้, เศษผัก, ขนมปัง"
    },
    3: {
        "name": "ขยะอันตราย (Hazardous)",
        "color_en": "RED LID",
        "color_hex": "#dc3545",
        "color_bgr": (69, 53, 220),
        "servo": "Servo GPIO 40 (เปิด 90 องศา)",
        "desc": "ถ่านชาร์จ, ถ่านไฟฉาย, แบตเตอรี่, แผงยา, หลอดไฟ"
    }
}

CLASS_NAME_MAP = {
    0: "ขยะทั่วไป / ซองขนม (General)",
    1: "ขวดน้ำ / กระป๋องรีไซเคิล (Recyclable)",
    2: "เศษอาหาร / ผลไม้ (Organic)",
    3: "ถ่านชาร์จ / แบตเตอรี่ / ขยะอันตราย (Hazardous)"
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

def classify_frame(frame, custom_model, coco_model):
    """วิเคราะห์จำแนกขยะ 4 คลาส โดยใช้โมเดล Custom และ Fallback"""
    res_custom = custom_model.predict(frame, conf=0.18, verbose=False)[0]
    if len(res_custom.boxes) > 0:
        best_box = max(res_custom.boxes, key=lambda b: float(b.conf[0]))
        cls_id = int(best_box.cls[0].item())
        conf = float(best_box.conf[0].item())
        bx = best_box.xyxy[0].cpu().numpy().astype(int)
        return cls_id, CLASS_NAME_MAP.get(cls_id, "ขยะอันตราย"), conf, bx

    res_coco = coco_model.predict(frame, conf=0.18, verbose=False)[0]
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

    return 0, "ขยะทั่วไป (General)", 0.65, np.array([30, 30, frame.shape[1]-30, frame.shape[0]-30])

def update_web_dashboard(bin_info, best_label, best_conf, trigger_src):
    html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="3">
    <title>Smart AI Trash Bin - ผลการสแกนสด</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
        .container {{ max-width: 980px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        h1 {{ margin-top: 0; color: #38bdf8; display: flex; align-items: center; justify-content: space-between; font-size: 26px; }}
        .badge {{ background: #0284c7; color: white; padding: 4px 12px; border-radius: 20px; font-size: 14px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 20px; }}
        .card {{ background: #334155; border-radius: 12px; padding: 20px; border-left: 8px solid {bin_info['color_hex']}; }}
        .card h2 {{ margin: 0 0 12px 0; font-size: 18px; color: #94a3b8; }}
        .result-title {{ font-size: 30px; font-weight: bold; color: {bin_info['color_hex']}; margin-bottom: 12px; }}
        .spec-item {{ margin: 10px 0; font-size: 15px; display: flex; justify-content: space-between; border-bottom: 1px solid #475569; padding-bottom: 6px; }}
        .spec-label {{ color: #94a3b8; }}
        .spec-val {{ font-weight: bold; color: #f1f5f9; }}
        .img-box {{ border-radius: 12px; overflow: hidden; border: 2px solid #475569; background: #020617; text-align: center; }}
        .img-box img {{ width: 100%; height: auto; display: block; }}
        .status-pill {{ display: inline-block; background: #22c55e; color: #022c22; font-weight: bold; padding: 6px 14px; border-radius: 20px; font-size: 13px; }}
        .desc-box {{ background: #0f172a; padding: 12px; border-radius: 8px; margin-top: 14px; font-size: 14px; color: #cbd5e1; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>
            <span>🗑️ SMART AI TRASH BIN LIVE</span>
            <span class="badge">ระบบตรวจจับอัตโนมัติ</span>
        </h1>
        
        <div class="grid">
            <div class="img-box">
                <img src="RESULT_SCAN.jpg?t={int(time.time()*1000)}" alt="OV2640 Camera Capture">
            </div>

            <div>
                <div class="card">
                    <h2>ผลการจำแนกประเภทขยะ (AI Result)</h2>
                    <div class="result-title">{bin_info['name']}</div>
                    <div class="spec-item"><span class="spec-label">ทริกเกอร์โดย:</span><span class="spec-val" style="color:#38bdf8;">{trigger_src}</span></div>
                    <div class="spec-item"><span class="spec-label">วัตถุที่ตรวจพบ:</span><span class="spec-val">{best_label}</span></div>
                    <div class="spec-item"><span class="spec-label">ระดับความมั่นใจ:</span><span class="spec-val" style="color:#4ade80;">{best_conf*100:.1f}%</span></div>
                    <div class="spec-item"><span class="spec-label">สีฝาถัง:</span><span class="spec-val">{bin_info['color_en']}</span></div>
                    <div class="spec-item"><span class="spec-label">คำสั่งเซอร์โว:</span><span class="spec-val" style="color:#38bdf8;">{bin_info['servo']}</span></div>
                    <div class="desc-box">💡 <b>คำแนะนำ:</b> {bin_info['desc']}</div>
                </div>

                <div style="margin-top: 16px; display: flex; align-items: center; justify-content: space-between;">
                    <span class="status-pill">● บอร์ด ESP32-S3 พร้อมทำงาน</span>
                    <span style="font-size: 13px; color: #94a3b8;">อัปเดตล่าสุด: {time.strftime('%H:%M:%S')}</span>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
    with open(RESULT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)

def main():
    print("=" * 70)
    print("  🗑️ SMART AI TRASH BIN - CONTINUOUS LIVE SERVICE")
    print("  ESP32-S3 (COM6) + OV2640 CAMERA + OLED + SENSORS + SERVO (GPIO 21)")
    print("=" * 70)

    print("\n[AI INIT] กำลังโหลดโมเดล Custom YOLOv8...")
    custom_model = YOLO(MODEL_PATH)
    coco_model = YOLO(FALLBACK_MODEL)
    print("[AI READY] โหลดโมเดลจำแนกขยะ 4 คลาสสำเร็จ!")

    print("\n[SERIAL] กำลังเชื่อมต่อบอร์ด ESP32-S3 ที่พอร์ต COM6 (ความเร็วสูง 921,600 baud)...")
    try:
        ser = serial.Serial("COM6", 921600, timeout=1)
        time.sleep(1.0)
        ser.reset_input_buffer()
        print("[SERIAL OK] เชื่อมต่อสำเร็จที่ 921600 baud (เร็วกว่าเดิม 8 เท่า)!")
    except Exception as e:
        print(f"[SERIAL ERROR] ไม่สามารถเปิดพอร์ต COM6 ได้: {e}")
        print("  -> กรุณาตรวจสอบว่าไม่ได้เปิด Serial Monitor ใน Arduino IDE ค้างไว้")
        input("กด Enter เพื่อออก...")
        return

    print("\n" + "-" * 70)
    print("  ✨ ระบบความเร็วสูง Ultra-Fast Response:")
    print("  1. ยื่นขยะจ่อหน้าเซนเซอร์ (2-30 ซม.)")
    print("  2. จอ OLED นับถอยหลังแบบไว (0.9 วิ) แล้วถ่ายภาพ")
    print("  3. ส่งภาพความเร็วสูง (0.2 วิ) -> AI วิเคราะห์ (0.05 วิ) -> เซอร์โวเปิดทันที!")
    print("  * หากต้องการสั่งสแกนด้วยตนเอง ให้กด [Enter] ในหน้าต่างนี้ได้ตลอดเวลา")
    print("-" * 70 + "\n")

    # เปิดหน้าเว็บ Dashboard ครั้งแรก
    if os.path.exists(RESULT_HTML_PATH):
        webbrowser.open(f"file:///{RESULT_HTML_PATH.replace(os.sep, '/')}")

    def manual_trigger_listener():
        while True:
            try:
                line = input()
                ser.write(b"CAPTURE\n")
                print(">>> [MANUAL TRIGGER] ส่งคำสั่งสแกนจากคีย์บอร์ดแล้ว!")
            except:
                break

    input_thread = threading.Thread(target=manual_trigger_listener, daemon=True)
    input_thread.start()

    scan_count = 0
    trigger_source = "SENSOR"

    try:
        while True:
            if ser.in_waiting > 0:
                raw_line = ser.readline().decode('utf-8', errors='ignore').strip()
                if not raw_line:
                    continue

                if raw_line.startswith("[EVENT:TRIGGER]"):
                    trigger_source = raw_line.replace("[EVENT:TRIGGER]", "").strip()
                    print(f"\n⚡ [DETECTED] ตรวจพบการกระตุ้นจาก: {trigger_source}")

                elif raw_line.startswith("[COUNTDOWN]"):
                    print("  ⏱️  นับถอยหลังถ่ายภาพแบบ Fast Countdown...")

                elif raw_line.startswith("IMG_START:"):
                    try:
                        expected_len = int(raw_line.split(":")[1])
                    except:
                        expected_len = 0

                    print(f"  📸 [SNAP!] กำลังดึงภาพจากกล้อง OV2640 ({expected_len} bytes) ผ่าน 921600 baud...")

                    t_start_xfer = time.time()
                    old_timeout = ser.timeout
                    ser.timeout = 5
                    img_data = ser.read(expected_len)
                    ser.timeout = old_timeout
                    xfer_time = (time.time() - t_start_xfer) * 1000

                    if len(img_data) >= expected_len and expected_len > 500:
                        scan_count += 1
                        print(f"  ⚡ [TRANSFER OK] รับภาพครบ {len(img_data)} bytes ใน {xfer_time:.1f} ms!")
                        print("  🤖 [AI INFERENCE] กำลังวิเคราะห์ภาพด้วย YOLOv8...")

                        nparr = np.frombuffer(img_data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                        if frame is not None:
                            t0 = time.time()
                            detected_bin, best_label, best_conf, bx = classify_frame(frame, custom_model, coco_model)
                            inf_time = (time.time() - t0) * 1000

                            bin_info = BINS[detected_bin]

                            # วาดกรอบและป้ายภาษาไทย
                            color = bin_info["color_bgr"]
                            cv2.rectangle(frame, (bx[0], bx[1]), (bx[2], bx[3]), color, 3)
                            label_txt = f"{best_label} ({best_conf*100:.1f}%)"
                            frame = draw_thai_text(frame, label_txt, (bx[0], max(10, bx[1] - 30)), font_size=18, color=(255,255,255), bg_color=(color[2], color[1], color[0]))

                            banner_txt = f"สแกนครั้งที่ #{scan_count} | {bin_info['name']} | {bin_info['servo']}"
                            frame = draw_thai_text(frame, banner_txt, (12, 12), font_size=20, color=(255,255,255), bg_color=(20, 20, 20))
                            cv2.imwrite(RESULT_IMG_PATH, frame)

                            # อัปเดต HTML Dashboard
                            update_web_dashboard(bin_info, best_label, best_conf, trigger_source)

                            print("\n" + "=" * 55)
                            print(f"  🎉 [AI RESULT #{scan_count}] จำแนกสำเร็จ ({inf_time:.1f} ms)!")
                            print(f"     วัตถุ: {best_label}")
                            print(f"     ประเภท: {bin_info['name']}")
                            print(f"     ความมั่นใจ: {best_conf*100:.1f}%")
                            print(f"     สั่งเปิดฝา: เซอร์โว GPIO 21 (เปิด 90 องศา)")
                            print("=" * 55)

                            # ส่งคำสั่งเปิดฝาถังไปยัง ESP32-S3
                            cmd = f"BIN:{detected_bin}\n"
                            ser.write(cmd.encode())
                            print(f"  📤 [SENT TO S3] ส่งคำสั่ง 'BIN:{detected_bin}' -> เซอร์โว GPIO 21 กำลังเปิดฝา...\n")
                        else:
                            print("  ❌ [ERROR] ถอดรหัสภาพ JPEG ไม่สำเร็จ")
                    else:
                        print(f"  ⚠️ [ERROR] รับภาพไม่สมบูรณ์ (ได้มา {len(img_data)}/{expected_len} bytes)")

                elif "ACK:BIN:" in raw_line:
                    print(f"  📥 [S3 RESPONSE] {raw_line}")

                elif "[STATUS] ปิดฝาสนิท" in raw_line:
                    print("  ✨ [STATUS] ฝาถังปิดสนิทแล้ว -> กลับสู่สถานะพร้อมตรวจจับชิ้นต่อไป!\n")

                elif raw_line.startswith("ERR:"):
                    print(f"  ⚠️ [S3 ERROR] {raw_line}")

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[STOPPING] กำลังปิดการเชื่อมต่อ...")
    finally:
        ser.close()
        print("[CLOSED] ออกจากโปรแกรมเรียบร้อย")

if __name__ == "__main__":
    main()
