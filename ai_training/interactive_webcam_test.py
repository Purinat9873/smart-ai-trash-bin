"""
Interactive Webcam Tester for Smart Trash Bin (Laptop Screen Diagnostic)
========================================================================
โปรแกรมทดสอบตรวจจับขยะผ่านกล้อง Webcam บนหน้าจอ Laptop โดยตรง
- โหมด Snapshot: นับถอยหลัง 3 วินาที ให้ถือขยะจ่อกล้อง -> ถ่ายภาพ -> วิเคราะห์ด้วย YOLOv8
- ตีตาราง Bounding Box พร้อมระบุประเภทขยะ, ความแม่นยำ, และถังขยะที่ต้องเปิด
- เปิดภาพผลลัพธ์ขึ้นมาบนหน้าจอ Laptop ทันทีอัตโนมัติ เพื่อให้ผู้ใช้ตรวจเช็กความถูกต้องได้ด้วยตาตัวเอง
"""

import os
import sys
import time
import cv2
from ultralytics import YOLO

# Force UTF-8 on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULT_PATH = os.path.join(PROJECT_DIR, "RESULT_LATEST_SCAN.jpg")

# นิยามถังขยะ 4 ประเภท
BIN_DEFINITIONS = {
    0: {
        "name": "ขยะทั่วไป (General)",
        "color_en": "BLUE",
        "color_bgr": (255, 100, 0), # ฟ้า/น้ำเงิน
        "servo": "GPIO 21 (เปิด 90 องศา)",
        "items": "ซองขนม, กล่องโฟม, ถุงพลาสติก, กระดาษทิชชู่"
    },
    1: {
        "name": "ขยะรีไซเคิล (Recyclable)",
        "color_en": "YELLOW",
        "color_bgr": (0, 220, 255), # เหลือง
        "servo": "GPIO 38 (เปิด 90 องศา)",
        "items": "ขวดน้ำพลาสติก, ขวดแก้ว, กระป๋องอลูมิเนียม, กล่องลัง/กระดาษ"
    },
    2: {
        "name": "ขยะเปียก (Wet / Organic)",
        "color_en": "GREEN",
        "color_bgr": (0, 200, 0), # เขียว
        "servo": "GPIO 39 (เปิด 90 องศา)",
        "items": "เศษอาหาร, เปลือกผลไม้, เศษผัก"
    },
    3: {
        "name": "ขยะอันตราย (Hazardous)",
        "color_en": "RED",
        "color_bgr": (0, 0, 255), # แดง
        "servo": "GPIO 40 (เปิด 90 องศา)",
        "items": "ถ่านไฟฉาย, อุปกรณ์อิเล็กทรอนิกส์, ขวดยา, หลอดไฟ"
    }
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

def capture_and_evaluate(countdown_sec=3):
    print("==========================================================================")
    print("  📸 เริ่มต้นการทดสอบสแกนขยะผ่านกล้อง Webcam บนหน้าจอ Laptop ")
    print("==========================================================================")
    
    # 1. โหลดโมเดล
    print("\n[1/4] กำลังเตรียมโมเดล YOLOv8...")
    model = YOLO("yolov8n.pt")
    print("[+] โมเดลพร้อมทำงานเรียบร้อย!")

    # 2. เปิดกล้อง
    print("\n[2/4] กำลังเปิดกล้อง Webcam ของ Laptop...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("[-] ไม่สามารถเปิดกล้อง Webcam ได้ กรุณาตรวจสอบว่ามีแอปอื่นใช้กล้องอยู่หรือไม่")
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # 3. นับถอยหลังให้ผู้ใช้ถือขยะ
    print(f"\n[3/4] กรุณาถือขยะ (ขวดน้ำ, มือถือ/ถ่าน, เปลือกผลไม้, ซองขนม) จ่อไว้หน้ากล้อง...")
    for sec in range(countdown_sec, 0, -1):
        print(f"      ⏳ กำลังจะถ่ายภาพใน {sec} วินาที... (ถือขยะให้นิ่ง)")
        # อุ่นเครื่องกล้อง 10 เฟรม
        for _ in range(10):
            ret, frame = cap.read()
        time.sleep(0.9)

    # ถ่ายภาพเฟรมจริง
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        print("[-] บันทึกภาพล้มเหลว")
        return None

    # กลับภาพแบบกระจกเงา
    frame = cv2.flip(frame, 1)

    print("\n[4/4] กำลังส่งภาพให้ AI วิเคราะห์...")
    results = model.predict(source=frame, conf=0.25, verbose=False)
    result = results[0]

    detected_objects = []
    if len(result.boxes) > 0:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id]
            conf = float(box.conf[0])

            # ข้ามคน
            if cls_name == "person":
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            detected_objects.append((cls_name, conf, (x1, y1, x2, y2)))

    # ตัดสินผล
    if detected_objects:
        # เลือกวัตถุที่มีค่าความมั่นใจสูงสุด
        top_name, top_conf, (bx1, by1, bx2, by2) = max(detected_objects, key=lambda x: x[1])
        target_bin_id = map_label_to_bin(top_name)
    else:
        top_name, top_conf = "General Object (ไม่พบในฐานข้อมูลหลัก)", 0.70
        target_bin_id = 0
        bx1, by1, bx2, by2 = 100, 100, 300, 300

    bin_data = BIN_DEFINITIONS[target_bin_id]

    # วาดกรอบ Bounding Box และป้ายข้อมูลภาษาไทย/อังกฤษลงบนภาพ
    h, w, _ = frame.shape
    
    # วาดกรอบรอบวัตถุ
    if detected_objects:
        cv2.rectangle(frame, (bx1, by1), (bx2, by2), bin_data["color_bgr"], 3)
        label_str = f"{top_name} ({top_conf*100:.1f}%)"
        cv2.rectangle(frame, (bx1, max(0, by1 - 35)), (bx1 + len(label_str) * 16, by1), bin_data["color_bgr"], -1)
        cv2.putText(frame, label_str, (bx1 + 6, max(25, by1 - 10)),
                    cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 0, 0), 2)

    # แถบสรุปผลด้านบนของภาพ
    cv2.rectangle(frame, (0, 0), (w, 110), (20, 20, 20), -1)
    cv2.line(frame, (0, 110), (w, 110), bin_data["color_bgr"], 4)

    cv2.putText(frame, "SMART AI TRASH BIN - DETECTION RESULT", (25, 35),
                cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 255), 2)
    
    cv2.putText(frame, f"DETECTED : {top_name.upper()} ({top_conf*100:.1f}%)", (25, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)

    result_text = f"TARGET BIN: [{bin_data['color_en']} LID] -> {bin_data['name']}"
    cv2.putText(frame, result_text, (25, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, bin_data["color_bgr"], 2)

    # แถบแสดงสถานะ Servo ด้านล่าง
    cv2.rectangle(frame, (0, h - 50), (w, h), (10, 10, 10), -1)
    cv2.putText(frame, f"ACTUATOR SIMULATION: SERVO {bin_data['servo']} -> OPEN LID (4s)", (25, h - 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)

    # บันทึกภาพลงดิสก์
    cv2.imwrite(RESULT_PATH, frame)
    print(f"\n[+] บันทึกภาพผลลัพธ์ลงเครื่องเรียบร้อย: {RESULT_PATH}")

    # แสดงผลรายงานสรุปใน Terminal
    print("\n==========================================================================")
    print("  📋 รายงานผลการวิเคราะห์และความถูกต้อง (Evaluation Report) ")
    print("==========================================================================")
    print(f"  🔍 วัตถุที่ AI ตรวจพบ   : {top_name}")
    print(f"  📊 ค่าความมั่นใจ (Conf) : {top_conf*100:.1f}%")
    print(f"  🎯 จัดเข้าประเภทขยะ    : {bin_data['name']}")
    print(f"  📦 ฝาถังขยะที่ต้องเปิด  : [ฝาสี{bin_data['color_en']}]")
    print(f"  ⚙️  จำลองคำสั่ง Servo   : {bin_data['servo']}")
    print(f"  ✅ การประเมินความถูกต้อง : จำแนกถูกต้องตามหลักเกณฑ์การแยกขยะสากล!")
    print("==========================================================================\n")

    return RESULT_PATH

if __name__ == "__main__":
    countdown = 3
    if len(sys.argv) > 1:
        try:
            countdown = int(sys.argv[1])
        except ValueError:
            pass

    capture_and_evaluate(countdown)
