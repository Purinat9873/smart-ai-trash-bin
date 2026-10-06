"""
Train Comprehensive 4-Class Waste Model
========================================
Trains YOLOv8 on 786 comprehensive images covering:
- Class 0: General Waste (393 objects)
- Class 1: Recyclable (743 objects)
- Class 2: Wet / Organic (896 objects)
- Class 3: Hazardous / E-Waste (400 objects)
- Negative Background: 18+ person/room images
"""

import os
import sys
import time
import shutil
import torch
from ultralytics import YOLO

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_YAML = os.path.join(PROJECT_DIR, "ai_training", "comprehensive_dataset", "data.yaml")
MODELS_DIR = os.path.join(PROJECT_DIR, "ai_training", "trained_models")
RUNS_DIR = os.path.join(PROJECT_DIR, "ai_training", "runs")
BEST_MODEL_PATH = os.path.join(MODELS_DIR, "smart_bin_best.pt")

def main():
    print("====================================================================")
    print("  🚀 SMART AI TRASH BIN - COMPREHENSIVE 4-CLASS YOLOv8 TRAINING      ")
    print("====================================================================")
    print(f"Data YAML: {DATA_YAML}")
    print(f"Target Model: {BEST_MODEL_PATH}")

    # ใช้ CPU 24 Cores ให้เต็มประสิทธิภาพ
    num_threads = min(20, os.cpu_count() or 4)
    torch.set_num_threads(num_threads)
    print(f"PyTorch CPU Threads: {num_threads} / {os.cpu_count()} cores")

    # ใช้ smart_bin_best.pt เป็นฐานในการ fine-tune ต่อเนื่อง
    if os.path.exists(BEST_MODEL_PATH):
        base_model = BEST_MODEL_PATH
        print(f"Using pretrained smart_bin_best.pt for transfer learning: {base_model}")
    else:
        base_model = os.path.join(PROJECT_DIR, "yolov8n.pt")
        print(f"Using yolov8n.pt: {base_model}")
    model = YOLO(base_model)

    print("\n[TRAINING] เริ่มต้นการฝึกสอนโมเดล Comprehensive YOLOv8 (25 Epochs)...")
    t_start = time.time()

    results = model.train(
        data=DATA_YAML,
        epochs=25,
        imgsz=320,
        batch=16,
        workers=8,
        cache=True,
        project=RUNS_DIR,
        name="comprehensive_bin_v5",
        exist_ok=True,
        pretrained=True,
        patience=15,
        save=True,
        verbose=True,
        plots=False,
        # Augmentation hyperparameters
        hsv_h=0.015,
        hsv_s=0.6,
        hsv_v=0.4,
        fliplr=0.5,
        flipud=0.0,
        scale=0.4,
        mosaic=0.7,
        close_mosaic=6
    )

    t_elapsed = time.time() - t_start
    print(f"\n🎉 [TRAIN FINISHED] ฝึกสอนเสร็จสมบูรณ์ในเวลา {t_elapsed/60:.1f} นาที!")

    # ค้นหาโมเดล best.pt จากการเทรน
    trained_best = os.path.join(RUNS_DIR, "comprehensive_bin_v5", "weights", "best.pt")
    if os.path.exists(trained_best):
        os.makedirs(MODELS_DIR, exist_ok=True)
        shutil.copy2(trained_best, BEST_MODEL_PATH)
        print(f"✅ บันทึกโมเดลอัปเดตใหม่เรียบร้อยแล้ว: {BEST_MODEL_PATH}")
    else:
        print(f"⚠️ ไม่พบ {trained_best}")

    # ทดสอบโมเดลกับภาพจริงของผู้ใช้ทุกประเภท
    print("\n--------------------------------------------------------------------")
    print("  🧪 ทดสอบโมเดลใหม่กับภาพจริงของผู้ใช้ (User Real Scans Validation)  ")
    print("--------------------------------------------------------------------")
    test_model = YOLO(BEST_MODEL_PATH)
    test_cases = [
        ("ม้วนเทปใส (ต้องเป็น General)", "raw_20261005_150030.jpg"),
        ("ม้วนเทปใส (ต้องเป็น General)", "raw_20261005_150019.jpg"),
        ("ม้วนเทปเอียง (ต้องเป็น General)", "raw_20261005_154001.jpg"),
        ("ห่อทิชชู่เขียวเดิม (ต้องเป็น General)", "raw_20261005_145914.jpg"),
        ("ห่อทิชชู่ดึงกระดาษ (ต้องเป็น General)", "raw_20261005_153910.jpg"),
        ("ห่อทิชชู่โชว์ก้นขาว (ต้องเป็น General)", "raw_20261005_153928.jpg"),
        ("ห่อทิชชู่ดึงสูง (ต้องเป็น General)", "raw_20261005_154157.jpg"),
        ("ห่อทิชชู่เอียง (ต้องเป็น General)", "raw_20261005_154226.jpg"),
        ("ม้วนตะกั่วบัดกรี (ต้องเป็น Hazardous)", "raw_20261005_145940.jpg"),
        ("ม้วนตะกั่วบัดกรี 2 (ต้องเป็น Hazardous)", "raw_20261005_145952.jpg"),
        ("กาวตราช้าง Power Glue (ต้องเป็น Hazardous)", "raw_20261005_150153.jpg"),
        ("กาวตราช้าง Power Glue (ต้องเป็น Hazardous)", "raw_20261005_150131.jpg"),
        ("แฟ้มสีน้ำเงิน (ต้องเป็น General)", "raw_20261005_150050.jpg"),
        ("โทรศัพท์มือถือ (ต้องเป็น Hazardous)", "raw_20261005_145817.jpg"),
        ("โทรศัพท์มือถือ (ต้องเป็น Hazardous)", "raw_20261005_143801.jpg"),
        ("ขวดน้ำดื่มใส (ต้องเป็น Recyclable)", "raw_20261005_155038.jpg"),
        ("แก้วน้ำพลาสติก (ต้องเป็น Recyclable)", "raw_20261005_095039.jpg"),
        ("คนยืนหน้ากล้องไม่มีขยะ (ต้องไม่จับ)", "raw_20261004_232243.jpg"),
    ]

    for label, fname in test_cases:
        p = os.path.join(PROJECT_DIR, "captured_scans", fname)
        if os.path.exists(p):
            res = test_model.predict(p, conf=0.20, verbose=False)[0]
            boxes_str = []
            for b in res.boxes:
                cls_id = int(b.cls[0].item())
                conf = float(b.conf[0].item())
                cname = test_model.names[cls_id]
                boxes_str.append(f"Class {cls_id}: {cname} ({conf*100:.1f}%)")
            det_txt = ", ".join(boxes_str) if boxes_str else "No Trash Detected (Negative OK)"
            print(f"  ● [{fname}] {label} ➔ {det_txt}")

    print("--------------------------------------------------------------------")

if __name__ == "__main__":
    main()
