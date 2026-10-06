"""
Prepare and Augment User Scanned Items for Training
===================================================
Adds high-resolution real captures of items held by user in front of ESP32-S3:
- Tape rolls (Class 0: General)
- Tissue packs (Class 0: General)
- Blue folder (Class 0: General)
- Plastic cups / bottles (Class 1: Recyclable)
- Solder wire spool (Class 3: Hazardous / E-waste)
- Power Glue blister pack (Class 3: Hazardous / Chemical)
- Mobile phones (Class 3: Hazardous / E-waste)
- Empty-handed persons (Negative background)
"""

import os
import sys
import glob
import cv2
import numpy as np
import random

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

random.seed(42)
np.random.seed(42)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(BASE_DIR, "ai_training", "comprehensive_dataset")
TRAIN_IMG = os.path.join(DATASET_DIR, "images", "train")
TRAIN_LBL = os.path.join(DATASET_DIR, "labels", "train")
VAL_IMG = os.path.join(DATASET_DIR, "images", "val")
VAL_LBL = os.path.join(DATASET_DIR, "labels", "val")

# Annotated User Items: (filename, class_id, [x1, y1, x2, y2], name)
USER_ANNOTATIONS = [
    # Solder wire spool (Class 3: Hazardous)
    ("raw_20261005_145940.jpg", 3, [130, 100, 190, 165], "user_solder_1"),
    ("raw_20261005_145952.jpg", 3, [130, 100, 200, 185], "user_solder_2"),
    ("raw_20261005_154606.jpg", 3, [65, 95, 185, 238], "user_solder_3"),

    # Tissue packs - ALL ANGLES (Class 0: General)
    ("raw_20261005_145914.jpg", 0, [85, 110, 215, 235], "user_tissue_1"),
    ("raw_20261005_145903.jpg", 0, [90, 105, 230, 235], "user_tissue_2"),
    ("raw_20261005_153910.jpg", 0, [90, 130, 225, 239], "user_tissue_3"),
    ("raw_20261005_153928.jpg", 0, [50, 130, 215, 238], "user_tissue_4"),
    ("raw_20261005_154143.jpg", 0, [95, 115, 235, 235], "user_tissue_5"),
    ("raw_20261005_154157.jpg", 0, [120, 115, 245, 235], "user_tissue_6"),
    ("raw_20261005_154226.jpg", 0, [90, 115, 240, 238], "user_tissue_7"),
    ("raw_20261005_154304.jpg", 0, [100, 115, 245, 230], "user_tissue_8"),
    ("raw_20261005_154325.jpg", 0, [75, 120, 235, 235], "user_tissue_9"),

    # Tape rolls (Class 0: General)
    ("raw_20261005_150030.jpg", 0, [125, 95, 245, 215], "user_tape_1"),
    ("raw_20261005_150019.jpg", 0, [115, 135, 225, 195], "user_tape_2"),
    ("raw_20261005_154001.jpg", 0, [80, 100, 205, 215], "user_tape_3"),
    
    # Blue folder / notebook (Class 0: General)
    ("raw_20261005_150050.jpg", 0, [115, 55, 310, 240], "user_folder_1"),
    
    # Power Glue pack & chemicals (Class 3: Hazardous)
    ("raw_20261005_150153.jpg", 3, [115, 100, 215, 238], "user_glue_1"),
    ("raw_20261005_150131.jpg", 3, [140, 5, 290, 240], "user_glue_2"),
    ("raw_20261005_154533.jpg", 3, [125, 55, 265, 238], "user_glue_3"),
    
    # Mobile phones (Class 3: Hazardous)
    ("raw_20261005_145817.jpg", 3, [116, 60, 206, 185], "user_phone_1"),
    ("raw_20261005_145728.jpg", 3, [115, 60, 205, 185], "user_phone_2"),
    ("raw_20261005_145616.jpg", 3, [115, 60, 205, 185], "user_phone_3"),
    ("raw_20261005_143801.jpg", 3, [83, 46, 185, 238], "user_phone_hand"),
    ("raw_20261005_104605.jpg", 3, [115, 55, 205, 185], "user_phone_4"),
    ("raw_20261005_101751.jpg", 3, [115, 55, 205, 185], "user_phone_5"),
    ("raw_20261005_101729.jpg", 3, [115, 55, 205, 185], "user_phone_6"),
    ("raw_20261005_101716.jpg", 3, [115, 55, 205, 185], "user_phone_7"),
    
    # Plastic cups & bottles (Class 1: Recyclable)
    ("raw_20261005_155038.jpg", 1, [110, 15, 220, 239], "user_bottle_real"),
    ("raw_20261005_155056.jpg", 1, [80, 25, 225, 236], "user_bottle_real2"),
    ("raw_20261005_145753.jpg", 1, [130, 70, 220, 220], "user_bottle_1"),
    ("raw_20261005_144311.jpg", 1, [130, 70, 220, 220], "user_bottle_2"),
    ("raw_20261005_143653.jpg", 1, [130, 70, 220, 220], "user_bottle_3"),
    ("raw_20261005_143439.jpg", 1, [130, 70, 220, 220], "user_bottle_4"),
    ("raw_20261005_100527.jpg", 1, [120, 70, 210, 220], "user_cup_2"),
    ("raw_20261005_100525.jpg", 1, [120, 70, 210, 220], "user_cup_3"),
    ("raw_20261005_100523.jpg", 1, [120, 70, 210, 220], "user_cup_4"),
    ("raw_20261005_100316.jpg", 1, [120, 70, 210, 220], "user_cup_5"),
    ("raw_20261005_100211.jpg", 1, [120, 70, 210, 220], "user_cup_6"),
    ("raw_20261005_100133.jpg", 1, [120, 70, 210, 220], "user_cup_7"),
    ("raw_20261005_095039.jpg", 1, [120, 70, 210, 220], "user_cup_8"),
    ("raw_20261005_095024.jpg", 1, [120, 70, 210, 220], "user_cup_9"),
]

# Negative Person Images (No objects - empty label file)
NEGATIVE_PERSON_SCANS = [
    "raw_20261005_143801.jpg",
    "raw_20261005_143748.jpg",
    "raw_20261005_142300.jpg",
    "raw_20261005_142222.jpg",
    "raw_20261005_142147.jpg",
    "raw_20261005_101331.jpg",
    "raw_20261005_100529.jpg",
    "raw_20261004_232243.jpg",
    "raw_20261004_223536.jpg",
]

def to_yolo(box, img_w=320, img_h=240):
    x1, y1, x2, y2 = box
    x_c = ((x1 + x2) / 2.0) / img_w
    y_c = ((y1 + y2) / 2.0) / img_h
    w = (x2 - x1) / float(img_w)
    h = (y2 - y1) / float(img_h)
    return max(0.0, min(1.0, x_c)), max(0.0, min(1.0, y_c)), max(0.01, min(1.0, w)), max(0.01, min(1.0, h))

def augment_sample(img, box):
    """สร้างภาพดัดแปลงหลายรูปแบบ (Flip, Brightness, Contrast, Scale)"""
    h, w = img.shape[:2]
    x1, y1, x2, y2 = box
    results = []

    # 1. Original
    results.append((img.copy(), box))

    # 2. Horizontal Flip
    f_img = cv2.flip(img, 1)
    f_box = [w - x2, y1, w - x1, y2]
    results.append((f_img, f_box))

    # 3. Brightness +30
    b_up = cv2.convertScaleAbs(img, alpha=1.0, beta=30)
    results.append((b_up, box))

    # 4. Brightness -30
    b_down = cv2.convertScaleAbs(img, alpha=1.0, beta=-30)
    results.append((b_down, box))

    # 5. Contrast Up
    c_up = cv2.convertScaleAbs(img, alpha=1.25, beta=0)
    results.append((c_up, box))

    # 6. Contrast Down
    c_down = cv2.convertScaleAbs(img, alpha=0.8, beta=10)
    results.append((c_down, box))

    # 7. Shift Right +12px
    M_right = np.float32([[1, 0, 12], [0, 1, 0]])
    s_r = cv2.warpAffine(img, M_right, (w, h), borderMode=cv2.BORDER_REFLECT)
    s_r_box = [min(w-1, x1+12), y1, min(w-1, x2+12), y2]
    results.append((s_r, s_r_box))

    # 8. Shift Left -12px
    M_left = np.float32([[1, 0, -12], [0, 1, 0]])
    s_l = cv2.warpAffine(img, M_left, (w, h), borderMode=cv2.BORDER_REFLECT)
    s_l_box = [max(0, x1-12), y1, max(0, x2-12), y2]
    results.append((s_l, s_l_box))

    # 9. Shift Down +10px
    M_down = np.float32([[1, 0, 0], [0, 1, 10]])
    s_d = cv2.warpAffine(img, M_down, (w, h), borderMode=cv2.BORDER_REFLECT)
    s_d_box = [x1, min(h-1, y1+10), x2, min(h-1, y2+10)]
    results.append((s_d, s_d_box))

    # 10. Zoom In 10%
    crop_x = int(w * 0.05)
    crop_y = int(h * 0.05)
    cropped = img[crop_y:h-crop_y, crop_x:w-crop_x]
    zoomed = cv2.resize(cropped, (w, h))
    scale_x = w / (w - 2 * crop_x)
    scale_y = h / (h - 2 * crop_y)
    z_x1 = max(0, int((x1 - crop_x) * scale_x))
    z_y1 = max(0, int((y1 - crop_y) * scale_y))
    z_x2 = min(w, int((x2 - crop_x) * scale_x))
    z_y2 = min(h, int((y2 - crop_y) * scale_y))
    results.append((zoomed, [z_x1, z_y1, z_x2, z_y2]))

    return results

def main():
    print("====================================================================")
    print("  📦 PREPARING REAL USER SCANNED ITEMS FOR TRAINING")
    print("====================================================================")
    
    total_added = 0
    train_count = 0
    val_count = 0

    # 1. Process Annotated Items
    for fname, cid, box, prefix in USER_ANNOTATIONS:
        fpath = os.path.join(BASE_DIR, "captured_scans", fname)
        if not os.path.exists(fpath):
            print(f"[SKIP] File not found: {fname}")
            continue

        img = cv2.imread(fpath)
        if img is None:
            continue

        variants = augment_sample(img, box)
        for idx, (var_img, var_box) in enumerate(variants):
            img_h, img_w = var_img.shape[:2]
            xc, yc, bw, bh = to_yolo(var_box, img_w, img_h)
            lbl_line = f"{cid} {xc:.6f} {yc:.6f} {bw:.6f} {bh:.6f}\n"

            # 85% train, 15% val
            is_val = (idx % 7 == 0)
            target_img_dir = VAL_IMG if is_val else TRAIN_IMG
            target_lbl_dir = VAL_LBL if is_val else TRAIN_LBL

            out_base = f"aug_{prefix}_v{idx}"
            out_img_path = os.path.join(target_img_dir, f"{out_base}.jpg")
            out_lbl_path = os.path.join(target_lbl_dir, f"{out_base}.txt")

            cv2.imwrite(out_img_path, var_img)
            with open(out_lbl_path, "w") as f:
                f.write(lbl_line)

            total_added += 1
            if is_val:
                val_count += 1
            else:
                train_count += 1

    print(f"✅ Added {total_added} augmented labeled samples (Train: {train_count}, Val: {val_count})")

    # 2. Process Negative Person Scans
    neg_added = 0
    for neg_idx, fname in enumerate(NEGATIVE_PERSON_SCANS):
        fpath = os.path.join(BASE_DIR, "captured_scans", fname)
        if not os.path.exists(fpath):
            continue
        img = cv2.imread(fpath)
        if img is None:
            continue

        # Add original and flipped negative
        for f_idx, aug_img in enumerate([img, cv2.flip(img, 1)]):
            is_val = (neg_idx % 4 == 0)
            target_img_dir = VAL_IMG if is_val else TRAIN_IMG
            target_lbl_dir = VAL_LBL if is_val else TRAIN_LBL

            out_base = f"neg_person_scan_{neg_idx}_v{f_idx}"
            out_img_path = os.path.join(target_img_dir, f"{out_base}.jpg")
            out_lbl_path = os.path.join(target_lbl_dir, f"{out_base}.txt")

            cv2.imwrite(out_img_path, aug_img)
            with open(out_lbl_path, "w") as f:
                f.write("") # Empty file = Negative sample

            neg_added += 1

    print(f"✅ Added {neg_added} negative person samples (empty labels for background learning)")
    
    # Check total dataset counts
    all_train = glob.glob(os.path.join(TRAIN_IMG, "*.jpg"))
    all_val = glob.glob(os.path.join(VAL_IMG, "*.jpg"))
    print(f"\n📊 Total Comprehensive Dataset: {len(all_train)} Train, {len(all_val)} Val (Total: {len(all_train) + len(all_val)} images)")

if __name__ == "__main__":
    main()
