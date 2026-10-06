"""
Live Webcam Smart Trash Bin Simulator (ESP32-S3 + YOLOv8 Emulation)
===================================================================
โปรแกรมจำลองถังขยะอัจฉริยะแบบ Real-Time ผ่านกล้อง Webcam ของคอมพิวเตอร์
- ใช้โมเดล YOLOv8 ตรวจจับขยะที่ถือเข้ามาหน้ากล้องสดๆ
- มีหน้าต่างจำลองจอ OLED และจำลองฝาถังขยะ 4 สี (น้ำเงิน, เหลือง, เขียว, แดง)
- เมื่อถือขยะเข้ามา ระบบจะตรวจจับ จำแนกประเภท และสั่ง "เปิดฝาถัง" สีที่ถูกต้องแบบ Real-time!

การใช้งาน:
  python ai_training/live_webcam_smart_bin.py
  (กดปุ่ม 'q' หรือ 'ESC' เพื่อปิดโปรแกรม)
"""

import os
import sys
import time
import cv2
import numpy as np
from ultralytics import YOLO

# พยายาม import winsound สำหรับเสียงบี๊บแจ้งเตือน (เฉพาะ Windows)
try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

# Force UTF-8 on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# กำหนดข้อมูลของถังขยะทั้ง 4 หมวดหมู่
BINS = {
    0: {
        "name": "GENERAL",
        "thai": "ขยะทั่วไป",
        "color_bgr": (220, 80, 20),      # น้ำเงิน (BGR)
        "color_name": "BLUE",
        "pin": "GPIO 21",
        "examples": "ซองขนม, กล่องโฟม, ถุงพลาสติก"
    },
    1: {
        "name": "RECYCLABLE",
        "thai": "ขยะรีไซเคิล",
        "color_bgr": (0, 215, 255),      # เหลืองทอง (BGR)
        "color_name": "YELLOW",
        "pin": "GPIO 38",
        "examples": "ขวดน้ำใส, ขวดแก้ว, กระป๋อง"
    },
    2: {
        "name": "WET / ORGANIC",
        "thai": "ขยะเปียก",
        "color_bgr": (30, 200, 30),      # เขียว (BGR)
        "color_name": "GREEN",
        "pin": "GPIO 39",
        "examples": "เศษอาหาร, เปลือกผลไม้, เศษผัก"
    },
    3: {
        "name": "HAZARDOUS",
        "thai": "ขยะอันตราย",
        "color_bgr": (30, 30, 230),      # แดง (BGR)
        "color_name": "RED",
        "pin": "GPIO 40",
        "examples": "ถ่านไฟฉาย, มือถือ, ขวดยา"
    }
}

def map_label_to_bin(label: str) -> int:
    label = label.lower()
    # 1. Recyclable
    if any(k in label for k in ["bottle", "can", "cup", "wine glass", "cardboard", "plastic"]):
        return 1
    # 2. Wet / Organic
    elif any(k in label for k in ["banana", "apple", "orange", "sandwich", "broccoli", "carrot", "pizza", "donut", "cake", "food"]):
        return 2
    # 3. Hazardous (รวมอุปกรณ์อิเล็กทรอนิกส์/แบตเตอรี่)
    elif any(k in label for k in ["battery", "cell phone", "remote", "mouse", "keyboard", "laptop", "scissors", "toaster"]):
        return 3
    # 0. General
    else:
        return 0

def draw_hud(frame, target_bin_id, active_label, confidence, active_until):
    h, w, _ = frame.shape
    now = time.time()
    is_lid_open = (now < active_until) and (target_bin_id is not None)

    # 1. แถบ Header ด้านบน
    header_h = 50
    cv2.rectangle(frame, (0, 0), (w, header_h), (25, 25, 25), -1)
    cv2.line(frame, (0, header_h), (w, header_h), (100, 100, 100), 2)
    cv2.putText(frame, "SMART AI TRASH BIN - LIVE SIMULATOR", (20, 32),
                cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2)

    status_txt = "STATUS: [LID OPEN - DROPPING TRASH]" if is_lid_open else "STATUS: [READY - HOLD TRASH IN FRONT OF CAM]"
    status_col = (0, 255, 0) if is_lid_open else (0, 200, 255)
    cv2.putText(frame, status_txt, (w - 470, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_col, 1)

    # 2. จำลองหน้าจอ OLED (มุมขวาบน)
    oled_w, oled_h = 240, 130
    oled_x = w - oled_w - 15
    oled_y = header_h + 15

    # กรอบ OLED สีดำขอบสีฟ้า
    cv2.rectangle(frame, (oled_x, oled_y), (oled_x + oled_w, oled_y + oled_h), (10, 10, 10), -1)
    cv2.rectangle(frame, (oled_x, oled_y), (oled_x + oled_w, oled_y + oled_h), (255, 180, 0), 2)
    cv2.putText(frame, "OLED 0.96 DISPLAY", (oled_x + 10, oled_y + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 50), 1)
    cv2.line(frame, (oled_x + 5, oled_y + 26), (oled_x + oled_w - 5, oled_y + 26), (80, 80, 80), 1)

    if is_lid_open:
        bin_data = BINS[target_bin_id]
        remain = max(0.0, active_until - now)
        cv2.putText(frame, f"CLASS: {active_label[:14]}", (oled_x + 10, oled_y + 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        cv2.putText(frame, f"OPEN: {bin_data['color_name']} LID", (oled_x + 10, oled_y + 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        cv2.putText(frame, f"CLOSING IN: {remain:.1f}s", (oled_x + 10, oled_y + 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
    else:
        cv2.putText(frame, "SYSTEM READY", (oled_x + 10, oled_y + 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        cv2.putText(frame, "Hold object 20cm", (oled_x + 10, oled_y + 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
        cv2.putText(frame, "Auto-Scanning...", (oled_x + 10, oled_y + 105),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (120, 220, 120), 1)

    # 3. จำลองถังขยะ 4 สีด้านล่างหน้าจอ
    footer_h = 100
    footer_y = h - footer_h
    cv2.rectangle(frame, (0, footer_y), (w, h), (20, 20, 20), -1)
    cv2.line(frame, (0, footer_y), (w, footer_y), (80, 80, 80), 2)

    box_w = int((w - 50) / 4)
    for i in range(4):
        bx = 10 + i * (box_w + 10)
        by = footer_y + 10
        bin_info = BINS[i]
        is_this_bin_open = is_lid_open and (target_bin_id == i)

        if is_this_bin_open:
            # กล่องไฮไลต์สว่างเมื่อฝาเปิด
            cv2.rectangle(frame, (bx, by), (bx + box_w, by + footer_h - 20), bin_info["color_bgr"], -1)
            text_color = (0, 0, 0)
            status_lid = ">> LID OPEN 90* <<"
        else:
            # กล่องหรี่เมื่อฝาปิด
            cv2.rectangle(frame, (bx, by), (bx + box_w, by + footer_h - 20), (45, 45, 45), -1)
            cv2.rectangle(frame, (bx, by), (bx + box_w, by + footer_h - 20), bin_info["color_bgr"], 2)
            text_color = (255, 255, 255)
            status_lid = "[LID CLOSED 0*]"

        cv2.putText(frame, f"{i+1}. {bin_info['name']}", (bx + 8, by + 22),
                    cv2.FONT_HERSHEY_DUPLEX, 0.45, text_color, 1)
        cv2.putText(frame, f"Pin: {bin_info['pin']}", (bx + 8, by + 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, text_color, 1)
        cv2.putText(frame, status_lid, (bx + 8, by + 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255) if is_this_bin_open else (140, 140, 140), 1)

    return frame

def main():
    print("=================================================================")
    print("  🚀 เริ่มต้นโปรแกรมจำลองถังขยะอัจฉริยะ (Live Webcam AI Simulator) ")
    print("=================================================================")
    print("[*] กำลังโหลดโมเดล YOLOv8 Nano...")
    model = YOLO("yolov8n.pt")
    print("[+] โหลดโมเดลเสร็จสมบูรณ์!")

    print("[*] กำลังเชื่อมต่อกล้อง Webcam...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[-] ไม่สามารถเปิดกล้อง Index 0 ได้ กำลังลอง Index 1...")
        cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("[!] ไม่พบกล้อง Webcam ที่เชื่อมต่อกับเครื่องคอมพิวเตอร์!")
        return

    # ตั้งค่าความละเอียด
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

    print("\n=================================================================")
    print("  🎉 กล้องพร้อมทำงานแล้ว! หน้าต่างจำลองกำลังเปิดขึ้น...")
    print("  👉 ลองหยิบขยะ (ขวดน้ำ, โทรศัพท์/ถ่าน, เปลือกผลไม้, ถุงขนม) มาถือหน้ากล้อง")
    print("  👉 กดปุ่ม 'q' หรือ 'ESC' ที่หน้าต่างกล้องเพื่อออกจากโปรแกรม")
    print("=================================================================\n")

    last_trigger_time = 0
    active_bin_id = None
    active_label = ""
    active_conf = 0.0
    lid_open_until = 0

    fps_t = time.time()
    fps = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[-] สัญญาณภาพจากกล้องขาดหาย")
            break

        # กลับภาพซ้ายขวาแบบกระจกเงา (Mirror) เพื่อให้ใช้งานง่าย
        frame = cv2.flip(frame, 1)

        # วิ่ง YOLOv8 ตรวจจับวัตถุ
        results = model.predict(source=frame, conf=0.35, verbose=False)
        result = results[0]

        detected_in_frame = []
        if len(result.boxes) > 0:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                conf = float(box.conf[0])

                # ข้ามการตรวจจับบุคคลทั่วไป (คนถือขยะ) เพื่อเน้นเฉพาะตัวขยะ
                if cls_name == "person":
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detected_in_frame.append((cls_name, conf, (x1, y1, x2, y2)))

        now = time.time()

        # ตรรกะสั่งเปิดฝาถังอัตโนมัติ (Trigger)
        if detected_in_frame and (now > lid_open_until):
            # เลือกวัตถุที่มีค่าความมั่นใจสูงสุด
            top_name, top_conf, top_box = max(detected_in_frame, key=lambda x: x[1])
            target_bin = map_label_to_bin(top_name)

            active_bin_id = target_bin
            active_label = top_name
            active_conf = top_conf
            lid_open_until = now + 4.0  # สั่งเปิดฝาค้างไว้ 4 วินาที

            bin_data = BINS[target_bin]
            print(f"\n[🔔 AUTO-SCAN DETECTED] ขยะ: '{top_name}' ({top_conf*100:.1f}%)")
            print(f"   -> คำสั่ง: เปิดฝาช่อง {bin_data['color_name']} ({bin_data['name']}) [Pin {bin_data['pin']}]")

            # ส่งเสียงบี๊บเตือน (Windows)
            if HAS_SOUND:
                try:
                    winsound.Beep(1400, 120)
                except Exception:
                    pass

        # วาด Bounding Box รอบวัตถุที่ตรวจพบ
        for cls_name, conf, (x1, y1, x2, y2) in detected_in_frame:
            b_id = map_label_to_bin(cls_name)
            box_col = BINS[b_id]["color_bgr"]

            cv2.rectangle(frame, (x1, y1), (x2, y2), box_col, 2)
            label_text = f"{cls_name} {conf*100:.0f}%"
            cv2.rectangle(frame, (x1, y1 - 22), (x1 + len(label_text) * 11, y1), box_col, -1)
            cv2.putText(frame, label_text, (x1 + 4, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)

        # วาดหน้าจอ HUD และจำลองถังขยะ
        frame = draw_hud(frame, active_bin_id, active_label, active_conf, lid_open_until)

        # คำนวณ FPS
        fps = 0.9 * fps + 0.1 * (1.0 / max(0.001, (time.time() - fps_t)))
        fps_t = time.time()
        cv2.putText(frame, f"FPS: {fps:.0f}", (frame.shape[1] - 80, frame.shape[0] - 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

        cv2.imshow("Smart Trash Bin - Live AI Simulator", frame)

        # ตรวจสอบปุ่มกดออก ('q' หรือ ESC)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            print("\n[*] ผู้ใช้กดปิดโปรแกรมจำลอง")
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[+] ปิดกล้องและโปรแกรมจำลองเรียบร้อยครับ")

if __name__ == "__main__":
    main()
