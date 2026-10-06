"""
Smart AI Trash Bin - Retrain Master Model with Real Mobile Phone (Class 3: Hazardous)
=====================================================================================
สคริปต์เทรนโมเดล YOLOv8 เพิ่มประเภทโทรศัพท์มือถือ (Smartphone / E-Waste) เข้า Class 3: ขยะอันตราย
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

# เคลียร์และสร้างโฟลเดอร์ Dataset ใหม่
shutil.rmtree(DATASET_DIR, ignore_errors=True)
os.makedirs(TRAIN_IMG_DIR, exist_ok=True)
os.makedirs(TRAIN_LBL_DIR, exist_ok=True)
os.makedirs(VAL_IMG_DIR, exist_ok=True)
os.makedirs(VAL_LBL_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

def save_sample(split, name, img, cls_id, xc, yc, w, h):
    img_dir = TRAIN_IMG_DIR if split == "train" else VAL_IMG_DIR
    lbl_dir = TRAIN_LBL_DIR if split == "train" else VAL_LBL_DIR
    cv2.imwrite(os.path.join(img_dir, f"{name}.jpg"), img)
    with open(os.path.join(lbl_dir, f"{name}.txt"), "w") as f:
        f.write(f"{cls_id} {xc:.4f} {yc:.4f} {w:.4f} {h:.4f}\n")

def augment_and_add(name_prefix, img, cls_id, xc, yc, w, h):
    # 1. Original (train)
    save_sample("train", f"{name_prefix}_orig", img, cls_id, xc, yc, w, h)
    
    # 2. Horizontal Flip (train)
    flip_img = cv2.flip(img, 1)
    save_sample("train", f"{name_prefix}_flip", flip_img, cls_id, 1.0 - xc, yc, w, h)
    
    # 3. Bright (train)
    bright = cv2.convertScaleAbs(img, alpha=1.15, beta=25)
    save_sample("train", f"{name_prefix}_bright", bright, cls_id, xc, yc, w, h)
    
    # 4. Dark (train)
    dark = cv2.convertScaleAbs(img, alpha=0.85, beta=-25)
    save_sample("train", f"{name_prefix}_dark", dark, cls_id, xc, yc, w, h)
    
    # 5. Blur (val)
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    save_sample("val", f"{name_prefix}_val", blur, cls_id, xc, yc, w, h)

def generate_phone_samples():
    """สร้างตัวอย่างโทรศัพท์มือถือหลากหลายแบบสำหรับ Class 3: ขยะอันตราย"""
    print("\n[PREPARE] กำลังสกัดและเพิ่มข้อมูลโทรศัพท์มือถือเข้า Class 3 (ขยะอันตราย)...")
    
    # 1. โทรศัพท์จริงจากภาพสแกน 1 (scan_20261004_104556)
    p1 = os.path.join(PROJECT_DIR, "captured_scans", "scan_20261004_104556_GENERAL.jpg")
    if os.path.exists(p1):
        img1 = cv2.imread(p1)
        # Bbox โทรศัพท์: [144, 48, 276, 224]
        # xc=0.656, yc=0.567, w=0.413, h=0.733
        augment_and_add("real_phone_1", img1, 3, 0.6562, 0.5667, 0.4125, 0.7333)

        # สกัด Crop โทรศัพท์เพื่อแปะบน Background อื่นๆ
        phone_crop = img1[48:224, 144:276]
        # สร้างภาพสังเคราะห์โทรศัพท์อยู่กึ่งกลาง
        bg = np.ones((240, 320, 3), dtype=np.uint8) * 90
        ph_h, ph_w = phone_crop.shape[:2]
        y_off = (240 - ph_h) // 2
        x_off = (320 - ph_w) // 2
        bg[y_off:y_off+ph_h, x_off:x_off+ph_w] = phone_crop
        augment_and_add("phone_center_synthetic", bg, 3, 0.50, 0.50, ph_w/320.0, ph_h/240.0)

    # 2. โทรศัพท์จริงจากภาพสแกน 2 (scan_20261004_104642)
    p2 = os.path.join(PROJECT_DIR, "captured_scans", "scan_20261004_104642_GENERAL.jpg")
    if os.path.exists(p2):
        img2 = cv2.imread(p2)
        # Bbox โทรศัพท์: [98, 36, 308, 238]
        # xc=0.634, yc=0.571, w=0.656, h=0.842
        augment_and_add("real_phone_2", img2, 3, 0.6344, 0.5708, 0.6562, 0.8417)

    # 3. ถ่านไฟฉายและแบตเตอรี่ Class 3 เดิม
    batt = os.path.join(PROJECT_DIR, "ai_training", "sample_images", "4_hazard_battery.jpg")
    if os.path.exists(batt):
        img_b = cv2.imread(batt)
        augment_and_add("real_battery", img_b, 3, 0.50, 0.50, 0.75, 0.75)

    # 4. ขยะทั่วไป (Class 0): ซองขนมจริง และถุงพลาสติก
    snack = os.path.join(PROJECT_DIR, "captured_scans", "scan_20261004_010837_GENERAL.jpg")
    if os.path.exists(snack):
        img_s = cv2.imread(snack)
        augment_and_add("real_snack_amazon", img_s, 0, 0.65, 0.60, 0.55, 0.70)

    bag = os.path.join(PROJECT_DIR, "ai_training", "sample_images", "0_general_plastic_bag.jpg")
    if os.path.exists(bag):
        img_bag = cv2.imread(bag)
        augment_and_add("real_plastic_bag", img_bag, 0, 0.50, 0.48, 0.78, 0.78)

    # 5. ขยะรีไซเคิล (Class 1): ขวดน้ำดื่มใส
    bottle1 = os.path.join(PROJECT_DIR, "captured_scans", "scan_0001_latest.jpg")
    if os.path.exists(bottle1):
        img_bot1 = cv2.imread(bottle1)
        augment_and_add("real_bottle_1", img_bot1, 1, 0.43, 0.48, 0.40, 0.75)

    bottle2 = os.path.join(PROJECT_DIR, "ai_training", "sample_images", "1_recycle_plastic_bottle.jpg")
    if os.path.exists(bottle2):
        img_bot2 = cv2.imread(bottle2)
        augment_and_add("real_bottle_2", img_bot2, 1, 0.50, 0.50, 0.55, 0.85)

    # 6. ขยะเปียก (Class 2): เปลือกกล้วย
    banana = os.path.join(PROJECT_DIR, "ai_training", "sample_images", "2_wet_banana_peel.jpg")
    if os.path.exists(banana):
        img_ban = cv2.imread(banana)
        augment_and_add("real_banana_peel", img_ban, 2, 0.40, 0.68, 0.48, 0.45)

    # สร้าง data.yaml
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

    print(f"[DATASET READY] Train: {len(glob.glob(os.path.join(TRAIN_IMG_DIR, '*.jpg')))} ภาพ, Val: {len(glob.glob(os.path.join(VAL_IMG_DIR, '*.jpg')))} ภาพ")

def train():
    generate_phone_samples()
    base_model = os.path.join(PROJECT_DIR, "yolov8n.pt")
    model = YOLO(base_model)
    
    print("\n[TRAIN] กำลังเริ่มเทรนโมเดล YOLOv8 25 Epochs...")
    run_name = "smart_bin_phone_hazard"
    results = model.train(
        data=DATA_YAML,
        epochs=25,
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
        print(f"\n✅ [SUCCESS] บันทึกโมเดลอัปเดตใหม่เรียบร้อย: {BEST_MODEL_PATH}")
    else:
        print("⚠️ ไม่พบ weights/best.pt")

def verify():
    print("\n--- ตรวจสอบผลการจำแนกภาพจริงหลังเทรน (Inference Test) ---")
    model = YOLO(BEST_MODEL_PATH)
    test_files = [
        ("โทรศัพท์มือถือ 1 (User Phone)", os.path.join(PROJECT_DIR, "captured_scans", "scan_20261004_104556_GENERAL.jpg"), 3),
        ("โทรศัพท์มือถือ 2 (User Phone)", os.path.join(PROJECT_DIR, "captured_scans", "scan_20261004_104642_GENERAL.jpg"), 3),
        ("ก้อนถ่านไฟฉาย (Battery)", os.path.join(PROJECT_DIR, "ai_training", "sample_images", "4_hazard_battery.jpg"), 3),
        ("ขวดน้ำใส (Recycle)", os.path.join(PROJECT_DIR, "captured_scans", "scan_0001_latest.jpg"), 1),
        ("เปลือกกล้วย (Wet)", os.path.join(PROJECT_DIR, "ai_training", "sample_images", "2_wet_banana_peel.jpg"), 2),
        ("ซองขนม (General)", os.path.join(PROJECT_DIR, "captured_scans", "scan_20261004_010837_GENERAL.jpg"), 0)
    ]
    
    cls_names = {0: "ขยะทั่วไป (General)", 1: "ขยะรีไซเคิล (Recyclable)", 2: "ขยะเปียก (Wet)", 3: "ขยะอันตราย (Hazardous)"}
    print("=" * 80)
    for title, fpath, expected_cls in test_files:
        if not os.path.exists(fpath):
            continue
        res = model.predict(fpath, conf=0.15, verbose=False)[0]
        if len(res.boxes) > 0:
            best_b = max(res.boxes, key=lambda b: float(b.conf[0]))
            pred_cls = int(best_b.cls[0].item())
            conf = float(best_b.conf[0].item()) * 100.0
            status = "✅ ผ่าน (CORRECT!)" if pred_cls == expected_cls else "❌ ผิดพลาด"
            print(f"  ● {title:32s} -> ทายได้: [{pred_cls}] {cls_names[pred_cls]:25s} (มั่นใจ {conf:.1f}%) | {status}")
        else:
            print(f"  ● {title:32s} -> ❌ ไม่พบวัตถุ")
    print("=" * 80)

if __name__ == "__main__":
    train()
    verify()
