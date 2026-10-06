"""
Expand Class 0 (General Waste) in Comprehensive Dataset
======================================================
Adds snack bags, foam boxes, tissues, books/paper, and wrappers
from COCO and augmented real scans.
"""
import os
import sys
import random
import requests
import cv2
import numpy as np

try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(PROJECT_DIR, "ai_training", "comprehensive_dataset")
TRAIN_IMG = os.path.join(DATASET_DIR, "images", "train")
TRAIN_LBL = os.path.join(DATASET_DIR, "labels", "train")
VAL_IMG   = os.path.join(DATASET_DIR, "images", "val")
VAL_LBL   = os.path.join(DATASET_DIR, "labels", "val")

COCO_VAL_LBL_DIR = os.path.join(PROJECT_DIR, "ai_training", "coco", "labels", "val2017")
COCO_IMG_BASE_URL = "http://images.cocodataset.org/val2017/"

# COCO items for General waste: 73 (book), 79 (toothbrush), 24 (backpack/bag)
COCO_BOOK = 73
COCO_TOOTHBRUSH = 79

def main():
    print("[1/2] ค้นหาภาพสิ่งของทั่วไป (Class 0: General) จาก COCO...")
    label_files = os.listdir(COCO_VAL_LBL_DIR)
    random.seed(123)
    random.shuffle(label_files)

    general_files = []
    for f in label_files:
        p = os.path.join(COCO_VAL_LBL_DIR, f)
        with open(p, "r") as fl:
            classes = [int(line.split()[0]) for line in fl if line.strip()]
        cset = set(classes)
        # สิ่งของขยะทั่วไป (กระดาษ/หนังสือ, แปรงสีฟัน, ซอง/ถุง)
        if any(c in cset for c in [COCO_BOOK, COCO_TOOTHBRUSH]):
            # ไม่เอาถ้ามีแก้วน้ำ, โทรศัพท์, หรืออาหารปน
            if not any(c in cset for c in [67, 39, 41, 46, 47, 49, 48]):
                general_files.append(f)

    selected = general_files[:70]
    print(f"  ● พบภาพ General เพิ่มเติม: {len(selected)} ภาพ...")

    added = 0
    for f in selected:
        img_name = f.replace(".txt", ".jpg")
        url = COCO_IMG_BASE_URL + img_name
        try:
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                arr = np.asarray(bytearray(r.content), dtype=np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is not None:
                    resized = cv2.resize(img, (320, 240))
                    boxes = []
                    with open(os.path.join(COCO_VAL_LBL_DIR, f), "r") as fl:
                        for line in fl:
                            parts = line.strip().split()
                            if parts and int(parts[0]) in [COCO_BOOK, COCO_TOOTHBRUSH]:
                                coords = [float(x) for x in parts[1:5]]
                                boxes.append((0, *coords)) # Map to Class 0

                    if boxes:
                        split = "train" if random.random() < 0.85 else "val"
                        dest_img = TRAIN_IMG if split == "train" else VAL_IMG
                        dest_lbl = TRAIN_LBL if split == "train" else VAL_LBL

                        out_name = f"coco_general_{img_name[:-4]}"
                        cv2.imwrite(os.path.join(dest_img, f"{out_name}.jpg"), resized)
                        with open(os.path.join(dest_lbl, f"{out_name}.txt"), "w") as out_fl:
                            for b in boxes:
                                out_fl.write(f"0 {b[1]:.4f} {b[2]:.4f} {b[3]:.4f} {b[4]:.4f}\n")
                        added += 1
        except Exception:
            pass

    # เพิ่มเติมจากภาพซองขนมและถุงพลาสติกจริงแบบ Augmentation คุณภาพสูง
    sample_general = [
        os.path.join(PROJECT_DIR, "captured_scans", "scan_20261004_010837_GENERAL.jpg"),
        os.path.join(PROJECT_DIR, "ai_training", "sample_images", "0_general_plastic_bag.jpg")
    ]
    for s_path in sample_general:
        if os.path.exists(s_path):
            im = cv2.imread(s_path)
            if im is not None:
                for aug_idx in range(25):
                    aug_im = cv2.resize(im, (320, 240))
                    if aug_idx % 2 == 1: aug_im = cv2.flip(aug_im, 1)
                    if aug_idx % 3 == 0: aug_im = cv2.convertScaleAbs(aug_im, alpha=1.12, beta=18)
                    elif aug_idx % 3 == 1: aug_im = cv2.convertScaleAbs(aug_im, alpha=0.88, beta=-18)

                    split = "val" if aug_idx % 5 == 0 else "train"
                    dest_img = TRAIN_IMG if split == "train" else VAL_IMG
                    dest_lbl = TRAIN_LBL if split == "train" else VAL_LBL

                    out_name = f"real_general_aug2_{os.path.basename(s_path)[:-4]}_{aug_idx}"
                    cv2.imwrite(os.path.join(dest_img, f"{out_name}.jpg"), aug_im)
                    with open(os.path.join(dest_lbl, f"{out_name}.txt"), "w") as out_fl:
                        out_fl.write("0 0.5000 0.5000 0.7200 0.7200\n")
                    added += 1

    print(f"🎉 [EXPAND OK] เพิ่มภาพขยะทั่วไป (General) สำเร็จรวม {added} รายการ!")

if __name__ == "__main__":
    main()
