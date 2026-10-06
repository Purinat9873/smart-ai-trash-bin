"""
Smart AI Trash Bin - Full Master Model Training
================================================
สคริปต์เทรนโมเดล YOLOv8 ฉบับสมบูรณ์สำหรับขยะ 4 ประเภท
- ขยะทั่วไป (Class 0: General) - ซองขนมจริง, ถุงพลาสติก, กล่องโฟม
- ขยะรีไซเคิล (Class 1: Recyclable) - ขวดน้ำดื่มใสจริง, กระป๋องอลูมิเนียม
- ขยะเปียก (Class 2: Wet / Organic) - กล้วย, เปลือกผลไม้, เศษอาหาร
- ขยะอันตราย (Class 3: Hazardous) - ก้อนถ่านไฟฉาย, แบตเตอรี่, แผงยา
"""

import os
import sys
import shutil
import glob
import cv2
import numpy as np
from ultralytics import YOLO

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(PROJECT_DIR, "ai_training", "dataset")
TRAIN_IMG_DIR = os.path.join(DATASET_DIR, "images", "train")
TRAIN_LBL_DIR = os.path.join(DATASET_DIR, "labels", "train")
VAL_IMG_DIR = os.path.join(DATASET_DIR, "images", "val")
VAL_LBL_DIR = os.path.join(DATASET_DIR, "labels", "val")
DATA_YAML = os.path.join(DATASET_DIR, "data.yaml")
MODELS_DIR = os.path.join(PROJECT_DIR, "ai_training", "trained_models")
RUNS_DIR = os.path.join(PROJECT_DIR, "ai_training", "runs")
BEST_MODEL_PATH = os.path.join(MODELS_DIR, "smart_bin_best.pt")

os.makedirs(TRAIN_IMG_DIR, exist_ok=True)
os.makedirs(TRAIN_LBL_DIR, exist_ok=True)
os.makedirs(VAL_IMG_DIR, exist_ok=True)
os.makedirs(VAL_LBL_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

def add_augmented_samples(name_prefix, src_img_path, class_id, xc, yc, w, h):
    """สร้างภาพ Augmented หลากหลายสภาพแสงและมุมมอง พร้อมไฟล์ Label"""
    if not os.path.exists(src_img_path):
        print(f"[SKIP] ไม่พบภาพ {src_img_path}")
        return

    img = cv2.imread(src_img_path)
    if img is None:
        print(f"[SKIP] ไม่สามารถเปิดภาพ {src_img_path}")
        return

    # 1. Original
    orig_path = os.path.join(TRAIN_IMG_DIR, f"{name_prefix}_orig.jpg")
    cv2.imwrite(orig_path, img)
    with open(os.path.join(TRAIN_LBL_DIR, f"{name_prefix}_orig.txt"), "w") as f:
        f.write(f"{class_id} {xc:.4f} {yc:.4f} {w:.4f} {h:.4f}\n")

    # 2. Horizontal Flip
    flip_img = cv2.flip(img, 1)
    flip_path = os.path.join(TRAIN_IMG_DIR, f"{name_prefix}_flip.jpg")
    cv2.imwrite(flip_path, flip_img)
    flip_xc = 1.0 - xc
    with open(os.path.join(TRAIN_LBL_DIR, f"{name_prefix}_flip.txt"), "w") as f:
        f.write(f"{class_id} {flip_xc:.4f} {yc:.4f} {w:.4f} {h:.4f}\n")

    # 3. Bright (+30)
    bright_img = cv2.convertScaleAbs(img, alpha=1.15, beta=30)
    bright_path = os.path.join(TRAIN_IMG_DIR, f"{name_prefix}_bright.jpg")
    cv2.imwrite(bright_path, bright_img)
    with open(os.path.join(TRAIN_LBL_DIR, f"{name_prefix}_bright.txt"), "w") as f:
        f.write(f"{class_id} {xc:.4f} {yc:.4f} {w:.4f} {h:.4f}\n")

    # 4. Dark (-30)
    dark_img = cv2.convertScaleAbs(img, alpha=0.85, beta=-30)
    dark_path = os.path.join(TRAIN_IMG_DIR, f"{name_prefix}_dark.jpg")
    cv2.imwrite(dark_path, dark_img)
    with open(os.path.join(TRAIN_LBL_DIR, f"{name_prefix}_dark.txt"), "w") as f:
        f.write(f"{class_id} {xc:.4f} {yc:.4f} {w:.4f} {h:.4f}\n")

    # 5. Validation Sample (Blur)
    blur_img = cv2.GaussianBlur(img, (5, 5), 0)
    blur_path = os.path.join(VAL_IMG_DIR, f"{name_prefix}_blur.jpg")
    cv2.imwrite(blur_path, blur_img)
    with open(os.path.join(VAL_LBL_DIR, f"{name_prefix}_blur.txt"), "w") as f:
        f.write(f"{class_id} {xc:.4f} {yc:.4f} {w:.4f} {h:.4f}\n")

    print(f"  [+] เพิ่มข้อมูลชุด: {name_prefix} (Class {class_id}) -> 4 train + 1 val")

def prepare_dataset():
    print("\n--- 1. เตรียมชุดข้อมูล (Dataset Preparation) ---")
    
    # 1. ขยะทั่วไป (Class 0): ซองขนมจริง Café Amazon จากกล้อง
    real_snack = os.path.join(PROJECT_DIR, "captured_scans", "scan_20261004_010837_GENERAL.jpg")
    add_augmented_samples("real_snack_amazon", real_snack, 0, 0.65, 0.60, 0.55, 0.70)

    # 2. ขยะทั่วไป (Class 0): ถุงพลาสติก
    plastic_bag = os.path.join(PROJECT_DIR, "ai_training", "sample_images", "0_general_plastic_bag.jpg")
    add_augmented_samples("real_plastic_bag", plastic_bag, 0, 0.50, 0.48, 0.78, 0.78)

    # 3. ขยะรีไซเคิล (Class 1): ขวดน้ำดื่มใสจริงจากกล้อง
    real_bottle = os.path.join(PROJECT_DIR, "captured_scans", "scan_0001_latest.jpg")
    add_augmented_samples("real_clear_bottle", real_bottle, 1, 0.43, 0.48, 0.40, 0.75)

    # 4. ขยะเปียก (Class 2): เปลือกกล้วยจริง
    real_banana = os.path.join(PROJECT_DIR, "ai_training", "sample_images", "2_wet_banana_peel.jpg")
    add_augmented_samples("real_banana_peel", real_banana, 2, 0.40, 0.68, 0.48, 0.45)

    # 5. ขยะอันตราย (Class 3): ก้อนถ่านไฟฉายจริง
    real_battery = os.path.join(PROJECT_DIR, "ai_training", "sample_images", "4_hazard_battery.jpg")
    add_augmented_samples("real_hazard_battery", real_battery, 3, 0.50, 0.50, 0.75, 0.75)

    # ตรวจสอบจำนวนภาพใน Train และ Val
    train_count = len(glob.glob(os.path.join(TRAIN_IMG_DIR, "*.jpg")))
    val_count = len(glob.glob(os.path.join(VAL_IMG_DIR, "*.jpg")))
    print(f"\nสรุปข้อมูลใน Dataset:")
    print(f"  📸 ภาพสำหรับ Train: {train_count} ภาพ")
    print(f"  📸 ภาพสำหรับ Val  : {val_count} ภาพ")

    # อัปเดต data.yaml
    yaml_content = f"""path: {DATASET_DIR.replace(os.sep, '/')}
train: images/train
val: images/val

names:
  0: General
  1: Recyclable
  2: Wet
  3: Hazardous
"""
    with open(DATA_YAML, "w", encoding="utf-8") as f:
        f.write(yaml_content)
    print(f"  📝 อัปเดต data.yaml สำเร็จ!")

def train_model(epochs=20):
    print("\n--- 2. เริ่มการเทรนโมเดล YOLOv8 (Model Training) ---")
    base_model = os.path.join(PROJECT_DIR, "yolov8n.pt")
    if not os.path.exists(base_model):
        base_model = "yolov8n.pt"

    print(f"  🚀 โหลด Pretrained Weights จาก: {base_model}")
    model = YOLO(base_model)

    run_name = "smart_bin_master_v3"
    print(f"  🔄 กำลังเทรน {epochs} Epochs (imgsz=320, batch=16)...")
    
    results = model.train(
        data=DATA_YAML,
        epochs=epochs,
        imgsz=320,
        batch=16,
        project=RUNS_DIR,
        name=run_name,
        exist_ok=True,
        verbose=True,
        workers=4,
        patience=25
    )

    trained_best = os.path.join(RUNS_DIR, run_name, "weights", "best.pt")
    if os.path.exists(trained_best):
        shutil.copy(trained_best, BEST_MODEL_PATH)
        print(f"\n  ✅ [SUCCESS] บันทึกโมเดลหลักเรียบร้อย: {BEST_MODEL_PATH}")
    else:
        print("  ⚠️ [WARNING] ไม่พบไฟล์ weights/best.pt")

    return results

def test_inference():
    print("\n--- 3. ทดสอบการจำแนกภาพจริง (Inference Verification) ---")
    if not os.path.exists(BEST_MODEL_PATH):
        print("  ❌ ไม่พบโมเดล")
        return

    model = YOLO(BEST_MODEL_PATH)
    test_cases = [
        ("ขยะทั่วไป (ซองขนมจริง)", os.path.join(PROJECT_DIR, "captured_scans", "scan_20261004_010837_GENERAL.jpg"), 0),
        ("ขยะรีไซเคิล (ขวดน้ำดื่มจริง)", os.path.join(PROJECT_DIR, "captured_scans", "scan_0001_latest.jpg"), 1),
        ("ขยะเปียก (เปลือกกล้วย)", os.path.join(PROJECT_DIR, "ai_training", "sample_images", "2_wet_banana_peel.jpg"), 2),
        ("ขยะอันตราย (ก้อนถ่าน)", os.path.join(PROJECT_DIR, "ai_training", "sample_images", "4_hazard_battery.jpg"), 3)
    ]

    class_names = {0: "ขยะทั่วไป (General)", 1: "ขยะรีไซเคิล (Recyclable)", 2: "ขยะเปียก (Wet)", 3: "ขยะอันตราย (Hazardous)"}

    print("=" * 70)
    for title, img_path, expected_cls in test_cases:
        if not os.path.exists(img_path):
            continue
        res = model.predict(img_path, conf=0.15, verbose=False)[0]
        if len(res.boxes) > 0:
            best_box = max(res.boxes, key=lambda b: float(b.conf[0]))
            pred_cls = int(best_box.cls[0].item())
            conf = float(best_box.conf[0].item()) * 100.0
            status = "✅ ผ่าน (CORRECT)" if pred_cls == expected_cls else "❌ ผิดพลาด"
            print(f"  ● {title:30s} -> ทายได้: [{pred_cls}] {class_names[pred_cls]:25s} (มั่นใจ {conf:.1f}%) | {status}")
        else:
            print(f"  ● {title:30s} -> ไม่พบวัตถุ")
    print("=" * 70)

if __name__ == "__main__":
    epochs = 20
    if len(sys.argv) > 1:
        try:
            epochs = int(sys.argv[1])
        except:
            pass

    print("=" * 65)
    print("   🤖 SMART AI TRASH BIN - FULL MASTER AI TRAINING PIPELINE")
    print("=" * 65)
    prepare_dataset()
    train_model(epochs=epochs)
    test_inference()
    print("\n🎉 การเทรนและทดสอบเสร็จสมบูรณ์ 100%!")
