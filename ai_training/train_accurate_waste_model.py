"""
Smart AI Trash Bin - Accurate Waste Model Training Pipeline
============================================================
Retrains YOLOv8 on real OV2640 camera captures:
- Class 0: General (ซองขนม, กล่องโฟม, ถุงพลาสติก)
- Class 1: Recyclable (แก้วน้ำพลาสติกใส, ขวดน้ำดื่ม, แก้วกาแฟ, กระป๋อง)
- Class 2: Wet / Organic (เศษอาหาร, เปลือกผลไม้)
- Class 3: Hazardous (แบตเตอรี่, ถ่านไฟฉาย, อุปกรณ์อิเล็กทรอนิกส์)
- Negative Samples: ใบหน้า/ตัวคน (สอนให้โมเดลไม่จับหน้าคนเป็นขยะ)
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
TRAIN_IMG = os.path.join(DATASET_DIR, "images", "train")
TRAIN_LBL = os.path.join(DATASET_DIR, "labels", "train")
VAL_IMG   = os.path.join(DATASET_DIR, "images", "val")
VAL_LBL   = os.path.join(DATASET_DIR, "labels", "val")
DATA_YAML = os.path.join(DATASET_DIR, "data.yaml")
MODELS_DIR = os.path.join(PROJECT_DIR, "ai_training", "trained_models")
RUNS_DIR = os.path.join(PROJECT_DIR, "ai_training", "runs")
BEST_MODEL_PATH = os.path.join(MODELS_DIR, "smart_bin_best.pt")

def init_dirs():
    shutil.rmtree(DATASET_DIR, ignore_errors=True)
    os.makedirs(TRAIN_IMG, exist_ok=True)
    os.makedirs(TRAIN_LBL, exist_ok=True)
    os.makedirs(VAL_IMG, exist_ok=True)
    os.makedirs(VAL_LBL, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

def save_box(split, name, img, boxes):
    """
    boxes: list of (cls_id, xc, yc, w, h) in normalized coords [0..1]
    or empty list for negative (background) images!
    """
    img_dir = TRAIN_IMG if split == "train" else VAL_IMG
    lbl_dir = TRAIN_LBL if split == "train" else VAL_LBL
    cv2.imwrite(os.path.join(img_dir, f"{name}.jpg"), img)
    with open(os.path.join(lbl_dir, f"{name}.txt"), "w") as f:
        for b in boxes:
            cls_id, xc, yc, w, h = b
            f.write(f"{cls_id} {xc:.4f} {yc:.4f} {w:.4f} {h:.4f}\n")

def augment(name_prefix, img, boxes):
    h_img, w_img = img.shape[:2]
    # 1. Original
    save_box("train", f"{name_prefix}_orig", img, boxes)

    # 2. Horizontal Flip
    flip_img = cv2.flip(img, 1)
    flip_boxes = [(c, 1.0 - xc, yc, w, h) for (c, xc, yc, w, h) in boxes]
    save_box("train", f"{name_prefix}_flip", flip_img, flip_boxes)

    # 3. Brightness +
    bright = cv2.convertScaleAbs(img, alpha=1.12, beta=20)
    save_box("train", f"{name_prefix}_bright", bright, boxes)

    # 4. Brightness -
    dark = cv2.convertScaleAbs(img, alpha=0.88, beta=-20)
    save_box("train", f"{name_prefix}_dark", dark, boxes)

    # 5. Blur / Val split
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    save_box("val", f"{name_prefix}_val", blur, boxes)

def xyxy_to_norm(bx, img_w=320, img_h=240):
    x1, y1, x2, y2 = bx
    xc = (x1 + x2) / 2.0 / img_w
    yc = (y1 + y2) / 2.0 / img_h
    w = (x2 - x1) / float(img_w)
    h = (y2 - y1) / float(img_h)
    return (xc, yc, w, h)

def build_dataset():
    init_dirs()
    print("[1/3] กำลังเตรียม Dataset ขยะจริง 4 คลาส + ภาพ Negative (หน้าคน)...")

    # =========================================================================
    # CLASS 1: RECYCLABLE (แก้วน้ำพลาสติกใส / ขวดน้ำดื่ม / กระป๋อง)
    # =========================================================================
    # แก้วน้ำจริงจากภาพสแกนของผู้ใช้:
    cup_scans = [
        ("cup_1", "raw_20261005_095039.jpg", [120, 95, 265, 239]),
        ("cup_2", "raw_20261005_095024.jpg", [110, 60, 240, 239]),
        ("cup_3", "raw_20261005_094654.jpg", [95, 35, 235, 239]),
        ("cup_4", "raw_20261005_094626.jpg", [215, 18, 319, 195]),
        ("cup_5", "raw_20261005_094546.jpg", [50, 95, 155, 220]),
        ("cup_6", "raw_20261005_094530.jpg", [60, 80, 160, 210]),
        ("cup_7", "raw_20261005_094515.jpg", [55, 75, 165, 215]),
        ("cup_8", "raw_20261005_094502.jpg", [60, 70, 170, 220]),
        ("cup_9", "raw_20261005_094412.jpg", [65, 80, 165, 210]),
        ("cup_10", "raw_20261005_094400.jpg", [70, 75, 170, 215])
    ]

    for tag, fname, bbox in cup_scans:
        p = os.path.join(PROJECT_DIR, "captured_scans", fname)
        if os.path.exists(p):
            im = cv2.imread(p)
            if im is not None:
                h, w = im.shape[:2]
                norm_box = xyxy_to_norm(bbox, w, h)
                augment(f"real_{tag}", im, [(1, *norm_box)])

    # ขวดน้ำดื่มใส Class 1 เดิม
    p_bot1 = os.path.join(PROJECT_DIR, "captured_scans", "scan_0001_latest.jpg")
    if os.path.exists(p_bot1):
        im = cv2.imread(p_bot1)
        if im is not None:
            augment("real_bottle_pet1", im, [(1, 0.43, 0.48, 0.40, 0.75)])

    p_bot2 = os.path.join(PROJECT_DIR, "ai_training", "sample_images", "1_recycle_plastic_bottle.jpg")
    if os.path.exists(p_bot2):
        im = cv2.imread(p_bot2)
        if im is not None:
            augment("real_bottle_pet2", im, [(1, 0.50, 0.50, 0.55, 0.85)])

    # =========================================================================
    # CLASS 0: GENERAL (ซองขนม, กล่องโฟม, ถุงพลาสติก, กระดาษ)
    # =========================================================================
    p_snack = os.path.join(PROJECT_DIR, "captured_scans", "scan_20261004_010837_GENERAL.jpg")
    if os.path.exists(p_snack):
        im = cv2.imread(p_snack)
        if im is not None:
            augment("real_snack_pack", im, [(0, 0.65, 0.60, 0.55, 0.70)])

    p_bag = os.path.join(PROJECT_DIR, "ai_training", "sample_images", "0_general_plastic_bag.jpg")
    if os.path.exists(p_bag):
        im = cv2.imread(p_bag)
        if im is not None:
            augment("real_plastic_bag", im, [(0, 0.50, 0.48, 0.78, 0.78)])

    # =========================================================================
    # CLASS 2: ORGANIC / WET (เศษอาหาร, เปลือกผลไม้)
    # =========================================================================
    p_ban = os.path.join(PROJECT_DIR, "ai_training", "sample_images", "2_wet_banana_peel.jpg")
    if os.path.exists(p_ban):
        im = cv2.imread(p_ban)
        if im is not None:
            augment("real_banana_peel", im, [(2, 0.40, 0.68, 0.48, 0.45)])

    # =========================================================================
    # CLASS 3: HAZARDOUS (ถ่านไฟฉาย, แบตเตอรี่, ขยะอันตราย)
    # =========================================================================
    p_batt = os.path.join(PROJECT_DIR, "ai_training", "sample_images", "4_hazard_battery.jpg")
    if os.path.exists(p_batt):
        im = cv2.imread(p_batt)
        if im is not None:
            augment("real_battery_hazard", im, [(3, 0.50, 0.50, 0.75, 0.75)])

    # =========================================================================
    # NEGATIVE SAMPLES: ใบหน้าคน / ตัวคนถ่ายรูป (Background - ไม่มีขยะในมือ)
    # เพื่อสอนให้โมเดลรู้ว่าหน้าคน / ตัวคน ไม่ใช่ขยะรีไซเคิล และไม่ใช่ขยะใดๆ!
    # =========================================================================
    negative_scans = [
        "raw_20261004_232243.jpg",
        "raw_20261004_232227.jpg",
        "raw_20261004_232204.jpg",
        "raw_20261004_223804.jpg",
        "raw_20261004_223614.jpg",
        "raw_20261004_223550.jpg",
        "raw_20261004_223228.jpg"
    ]
    for ntag in negative_scans:
        p = os.path.join(PROJECT_DIR, "captured_scans", ntag)
        if os.path.exists(p):
            im = cv2.imread(p)
            if im is not None:
                # บันทึกเป็นภาพ Negative (boxes=[])
                augment(f"neg_{ntag[:-4]}", im, [])

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

    train_count = len(glob.glob(os.path.join(TRAIN_IMG, "*.jpg")))
    val_count = len(glob.glob(os.path.join(VAL_IMG, "*.jpg")))
    print(f"[DATASET READY] Train: {train_count} ภาพ, Val: {val_count} ภาพ พร้อมใช้งาน!")

def train():
    build_dataset()
    base_model = os.path.join(PROJECT_DIR, "yolov8n.pt")
    model = YOLO(base_model)

    print("\n[2/3] กำลังเริ่มเทรนโมเดล Custom YOLOv8 บนขยะจริงและแก้วน้ำ (30 Epochs)...")
    run_name = "smart_bin_accurate_v2"
    results = model.train(
        data=DATA_YAML,
        epochs=30,
        imgsz=320,
        batch=16,
        project=RUNS_DIR,
        name=run_name,
        exist_ok=True,
        verbose=False,
        workers=2,
        patience=20
    )

    trained_best = os.path.join(RUNS_DIR, run_name, "weights", "best.pt")
    if os.path.exists(trained_best):
        shutil.copy(trained_best, BEST_MODEL_PATH)
        print(f"\n✅ [SUCCESS] บันทึกโมเดลอัปเดตใหม่เรียบร้อย: {BEST_MODEL_PATH}")
    else:
        print("⚠️ ไม่พบ weights/best.pt")

def verify():
    print("\n[3/3] ตรวจสอบความแม่นยำหลังเทรน (Validation Test)...")
    model = YOLO(BEST_MODEL_PATH)
    
    test_cases = [
        ("แก้วน้ำพลาสติก 1 (User Drink Cup)", "captured_scans/raw_20261005_095039.jpg", 1),
        ("แก้วน้ำพลาสติก 2 (User Drink Cup)", "captured_scans/raw_20261005_095024.jpg", 1),
        ("แก้วน้ำพลาสติก 3 (User Drink Cup)", "captured_scans/raw_20261005_094654.jpg", 1),
        ("ขวดน้ำดื่ม PET (Recycle Bottle)", "captured_scans/scan_0001_latest.jpg", 1),
        ("ซองขนม (General Snack)", "captured_scans/scan_20261004_010837_GENERAL.jpg", 0),
        ("ก้อนถ่านไฟฉาย (Battery)", "ai_training/sample_images/4_hazard_battery.jpg", 3),
        ("เปลือกกล้วย (Banana Peel)", "ai_training/sample_images/2_wet_banana_peel.jpg", 2)
    ]
    
    cls_names = {0: "General", 1: "Recyclable", 2: "Wet", 3: "Hazardous"}
    print("=" * 80)
    for title, rel_path, expected in test_cases:
        p = os.path.join(PROJECT_DIR, rel_path)
        if not os.path.exists(p):
            continue
        res = model.predict(p, conf=0.15, verbose=False)[0]
        if len(res.boxes) > 0:
            best_b = max(res.boxes, key=lambda b: float(b.conf[0]))
            pred_cls = int(best_b.cls[0].item())
            conf = float(best_b.conf[0].item()) * 100.0
            status = "✅ ผ่าน (CORRECT!)" if pred_cls == expected else f"❌ ผิด (ได้ {cls_names[pred_cls]})"
            print(f"  ● {title:35s} -> ผลลัพธ์: [{pred_cls}] {cls_names[pred_cls]:12s} ({conf:.1f}%) | {status}")
        else:
            print(f"  ● {title:35s} -> ❌ ไม่พบวัตถุ")
    print("=" * 80)

if __name__ == "__main__":
    train()
    verify()
