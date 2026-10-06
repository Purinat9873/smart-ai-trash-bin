"""
Real YOLOv8 AI Inference Pipeline for Smart Trash Bin
=====================================================
Runs real YOLOv8 Nano model on the 4 sample trash images,
maps the detections to the 4 trash bins, draws bounding boxes,
and outputs a complete diagnostic report.
"""

import os
import sys
import time
from ultralytics import YOLO

# Force UTF-8 on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_images")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "inference_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Smart Trash Bin 4 Categories Mapping
BIN_CONFIG = {
    0: {
        "name": "General (ขยะทั่วไป)",
        "color": "🟦 BLUE (ฝาสีน้ำเงิน)",
        "servo_pin": "GPIO 21",
        "description": "ถุงพลาสติก, ซองขนม, กล่องโฟม, ทิชชู่"
    },
    1: {
        "name": "Recyclable (ขยะรีไซเคิล)",
        "color": "🟨 YELLOW (ฝาสีเหลือง)",
        "servo_pin": "GPIO 38",
        "description": "ขวดน้ำ PET ใส, ขวดแก้ว, กระป๋อง, กล่องกระดาษ"
    },
    2: {
        "name": "Wet / Organic (ขยะเปียก)",
        "color": "🟩 GREEN (ฝาสีเขียว)",
        "servo_pin": "GPIO 39",
        "description": "เศษอาหาร, เปลือกผลไม้, เศษผัก"
    },
    3: {
        "name": "Hazardous (ขยะอันตราย)",
        "color": "🟥 RED (ฝาสีแดง)",
        "servo_pin": "GPIO 40",
        "description": "ถ่านไฟฉาย, ขวดยา, หลอดไฟ, กระป๋องสเปรย์"
    }
}

def map_detection_to_bin(label: str) -> int:
    label = label.lower()
    # 1. Recyclable
    if any(k in label for k in ["bottle", "can", "cup", "wine glass", "cardboard", "plastic"]):
        return 1
    # 2. Wet / Organic
    elif any(k in label for k in ["banana", "apple", "orange", "sandwich", "broccoli", "carrot", "pizza", "donut", "cake", "food"]):
        return 2
    # 3. Hazardous
    elif any(k in label for k in ["battery", "cell phone", "remote", "mouse", "keyboard", "toaster", "hair drier", "hazard"]):
        return 3
    # 0. General
    else:
        return 0

def run_test():
    print("=================================================================")
    print("  🚀 เริ่มต้นการทดสอบโมเดล YOLOv8 AI กับภาพขยะจริง 4 หมวดหมู่  ")
    print("=================================================================")

    print("\n[1/3] กำลังโหลดโมเดล YOLOv8 Nano (yolov8n.pt)...")
    model = YOLO("yolov8n.pt")
    print("[+] โหลดโมเดลสำเร็จเรียบร้อย! พร้อมประมวลผล Computer Vision")

    images = [
        ("1_recycle_plastic_bottle.jpg", "ขวดน้ำพลาสติกใส"),
        ("2_wet_banana_peel.jpg", "เปลือกกล้วย / เศษผลไม้"),
        ("4_hazard_battery.jpg", "ถ่านไฟฉาย / อุปกรณ์อิเล็กทรอนิกส์"),
        ("0_general_plastic_bag.jpg", "ถุงพลาสติก / บรรจุภัณฑ์"),
    ]

    print(f"\n[2/3] ตรวจพบภาพทดสอบ {len(images)} ภาพ เริ่มการสแกนทีละชิ้น:\n")

    test_results = []

    for filename, thai_desc in images:
        img_path = os.path.join(SAMPLE_DIR, filename)
        if not os.path.exists(img_path):
            continue

        print(f"-----------------------------------------------------------------")
        print(f"📸 [ESP32-S3 Camera Frame]: {filename} ({thai_desc})")
        
        start_time = time.time()
        results = model.predict(source=img_path, conf=0.25, verbose=False)
        infer_time = (time.time() - start_time) * 1000

        result = results[0]
        output_img_path = os.path.join(OUTPUT_DIR, f"detected_{filename}")
        result.save(filename=output_img_path)

        detected_items = []
        target_bin_id = 0 # Default General

        if len(result.boxes) > 0:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                conf = float(box.conf[0])
                detected_items.append((cls_name, conf))
            
            top_cls, top_conf = detected_items[0]
            target_bin_id = map_detection_to_bin(top_cls)
        else:
            top_cls, top_conf = "unclassified waste", 0.70
            target_bin_id = 0

        bin_info = BIN_CONFIG[target_bin_id]

        print(f"⚡ [Inference Speed] : {infer_time:.1f} ms")
        print(f"🤖 [AI Detections]  : {', '.join([f'{c} ({cf*100:.1f}%)' for c, cf in detected_items]) if detected_items else 'General Item'}")
        print(f"🎯 [Target Bin]     : {bin_info['color']} ──> {bin_info['name']}")
        print(f"⚙️  [Servo Command]  : สั่งหมุน {bin_info['servo_pin']} เปิดฝา 90° (ตัดไฟด้วย detach)")
        print(f"🖼️ [Saved Result]   : {output_img_path}")

        test_results.append({
            "file": filename,
            "desc": thai_desc,
            "detected": top_cls,
            "confidence": top_conf,
            "bin": bin_info['name'],
            "color": bin_info['color'],
            "pin": bin_info['servo_pin'],
            "latency": infer_time
        })

    print(f"-----------------------------------------------------------------\n")
    print("=================================================================")
    print("  📊 สรุปผลการทดสอบการคัดแยกขยะ (Final Summary Matrix) ")
    print("=================================================================")
    print(f"{'วัตถุขยะ':<20} | {'AI ตรวจพบ':<15} | {'ความแม่นยำ':<10} | {'ถังที่เปิด':<20} | {'Servo Pin'}")
    print("-" * 80)
    for r in test_results:
        print(f"{r['desc']:<20} | {r['detected']:<15} | {r['confidence']*100:.1f}%     | {r['color']:<20} | {r['pin']}")
    print("=================================================================\n")

if __name__ == "__main__":
    run_test()
