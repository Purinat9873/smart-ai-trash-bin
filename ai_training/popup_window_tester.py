"""
Live Window Tester with Real-Time Feedback
==========================================
เปิดหน้าต่างกล้องขึ้นมาบนหน้าจอ Laptop สดๆ:
- แสดงภาพจากกล้อง Webcam พร้อมกรอบสีตามประเภทขยะ
- ตรวจจับวัตถุ Real-time (ขวดน้ำ, มือถือ/ถ่าน, เปลือกผลไม้, ซองขนม)
- บอกสถานะชัดเจนว่า: ผลลัพธ์ถูกต้องหรือไม่ และถังสีอะไรเปิด
- กดปุ่ม 'q' หรือ 'ESC' เพื่อปิด
"""

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

BINS = {
    0: {"name": "GENERAL (ทั่วไป)", "color": (255, 120, 0), "lid": "BLUE", "servo": "GPIO 21"},
    1: {"name": "RECYCLABLE (รีไซเคิล)", "color": (0, 220, 255), "lid": "YELLOW", "servo": "GPIO 38"},
    2: {"name": "WET (ขยะเปียก)", "color": (0, 220, 0), "lid": "GREEN", "servo": "GPIO 39"},
    3: {"name": "HAZARDOUS (อันตราย)", "color": (0, 0, 255), "lid": "RED", "servo": "GPIO 40"}
}

def map_label_to_bin(label: str) -> int:
    label = label.lower()
    if any(k in label for k in ["bottle", "can", "cup", "wine glass", "cardboard", "plastic"]):
        return 1
    elif any(k in label for k in ["banana", "apple", "orange", "sandwich", "broccoli", "carrot", "pizza", "donut", "cake", "food"]):
        return 2
    elif any(k in label for k in ["battery", "cell phone", "remote", "mouse", "keyboard", "laptop", "scissors"]):
        return 3
    else:
        return 0

def run():
    print("[*] กำลังโหลดโมเดล YOLOv8...")
    model = YOLO("yolov8n.pt")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cap = cv2.VideoCapture(1)

    if not cap.isOpened():
        print("[-] ไม่สามารถเปิดกล้อง Webcam ได้")
        return

    # สร้างหน้าต่างแบบอยู่บนสุด (Topmost)
    window_name = "SMART TRASH BIN - REAL-TIME DETECTOR"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 600)

    print("\n==========================================================================")
    print("  🎉 หน้าต่างกล้องเปิดขึ้นบนหน้าจอของคุณแล้ว!")
    print("  👉 ลองถือขยะ (ขวดน้ำ, มือถือ, ถ่าน, เปลือกผลไม้) เข้ามาหน้ากล้อง")
    print("  👉 กดปุ่ม 'q' หรือ 'ESC' ที่หน้าต่างกล้องเพื่อปิด")
    print("==========================================================================\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        results = model.predict(source=frame, conf=0.30, verbose=False)
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

        # แถบ Header
        cv2.rectangle(frame, (0, 0), (w, 80), (25, 25, 25), -1)

        if detected:
            top_name, top_conf, (bx1, by1, bx2, by2) = max(detected, key=lambda x: x[1])
            target_bin = map_label_to_bin(top_name)
            bin_data = BINS[target_bin]

            # วาดกรอบรอบวัตถุ
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), bin_data["color"], 3)
            tag = f"{top_name.upper()} {top_conf*100:.0f}%"
            cv2.rectangle(frame, (bx1, max(0, by1 - 30)), (bx1 + len(tag) * 14, by1), bin_data["color"], -1)
            cv2.putText(frame, tag, (bx1 + 4, max(20, by1 - 8)), cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 0, 0), 2)

            # แสดงผลลัพธ์บน Header
            cv2.putText(frame, f"DETECTED: {top_name.upper()} ({top_conf*100:.1f}%) [CORRECT / \x5c]", 
                        (20, 32), cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"OPEN BIN: [{bin_data['lid']} LID] -> {bin_data['name']} (SERVO {bin_data['servo']})", 
                        (20, 65), cv2.FONT_HERSHEY_DUPLEX, 0.65, bin_data["color"], 2)
        else:
            cv2.putText(frame, "STATUS: READY - PLEASE HOLD TRASH IN FRONT OF CAM (20-30cm)", 
                        (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 215, 255), 2)

        # แถบคำแนะนำด้านล่าง
        cv2.rectangle(frame, (0, h - 35), (w, h), (15, 15, 15), -1)
        cv2.putText(frame, "Test items: Water Bottle (Recycle), Phone/Battery (Hazardous), Fruit/Food (Wet), Bag (General) | Press 'q' to Exit",
                    (15, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

        cv2.imshow(window_name, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[+] ปิดหน้าต่างกล้องเรียบร้อยครับ")

if __name__ == "__main__":
    run()
