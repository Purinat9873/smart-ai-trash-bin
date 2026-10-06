"""
Comprehensive 4-Class Waste Dataset Builder
============================================
Collects and formats ~800 diverse, high-quality images across:
- Class 0: General Waste (ซองขนม, กล่องโฟม, ทิชชู่, ถุงพลาสติก)
- Class 1: Recyclable (ขวดน้ำดื่ม PET, แก้วน้ำพลาสติก, กระป๋อง)
- Class 2: Organic / Wet (กล้วย, ส้ม, แอปเปิ้ล, เศษอาหาร, แซนวิช)
- Class 3: Hazardous (โทรศัพท์มือถือ, แบตเตอรี่, เม้าส์, รีโมท, ขยะอิเล็กทรอนิกส์)
- Negative Samples: คน/หน้าคน/ห้องว่าง (ไม่มีขยะ)
"""

import os
import sys
import glob
import shutil
import random
import requests
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(PROJECT_DIR, "ai_training", "comprehensive_dataset")
TRAIN_IMG = os.path.join(DATASET_DIR, "images", "train")
TRAIN_LBL = os.path.join(DATASET_DIR, "labels", "train")
VAL_IMG   = os.path.join(DATASET_DIR, "images", "val")
VAL_LBL   = os.path.join(DATASET_DIR, "labels", "val")
DATA_YAML = os.path.join(DATASET_DIR, "data.yaml")

COCO_VAL_LBL_DIR = os.path.join(PROJECT_DIR, "ai_training", "coco", "labels", "val2017")
COCO_IMG_BASE_URL = "http://images.cocodataset.org/val2017/"

# COCO Category IDs
COCO_CELL_PHONE = 67
COCO_REMOTE     = 65
COCO_MOUSE      = 64
COCO_KEYBOARD   = 66
COCO_LAPTOP     = 63

COCO_BOTTLE     = 39
COCO_CUP        = 41

COCO_BANANA     = 46
COCO_APPLE      = 47
COCO_ORANGE     = 49
COCO_SANDWICH   = 48
COCO_PIZZA      = 53
COCO_DONUT      = 54
COCO_CAKE       = 55
COCO_BROCCOLI   = 50
COCO_CARROT     = 51

COCO_PERSON     = 0

def init_dataset_dirs():
    shutil.rmtree(DATASET_DIR, ignore_errors=True)
    os.makedirs(TRAIN_IMG, exist_ok=True)
    os.makedirs(TRAIN_LBL, exist_ok=True)
    os.makedirs(VAL_IMG, exist_ok=True)
    os.makedirs(VAL_LBL, exist_ok=True)

def download_image(img_name):
    url = COCO_IMG_BASE_URL + img_name
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            arr = np.asarray(bytearray(r.content), dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            return img
    except Exception as e:
        pass
    return None

def main():
    init_dataset_dirs()
    print("[1/4] สแกน COCO val2017 เพื่อคัดเลือกภาพตรงตาม 4 คลาสขยะ...")

    if not os.path.exists(COCO_VAL_LBL_DIR):
        print(f"Error: ไม่พบ {COCO_VAL_LBL_DIR}")
        return

    label_files = os.listdir(COCO_VAL_LBL_DIR)
    random.seed(42)
    random.shuffle(label_files)

    hazard_files = []
    recycle_files = []
    organic_files = []
    person_only_files = []

    for f in label_files:
        p = os.path.join(COCO_VAL_LBL_DIR, f)
        with open(p, "r") as fl:
            classes = [int(line.split()[0]) for line in fl if line.strip()]

        cset = set(classes)
        # 1. Hazardous: มีโทรศัพท์, รีโมท, เม้าส์, คีย์บอร์ด, แลปท็อป
        if any(c in cset for c in [COCO_CELL_PHONE, COCO_REMOTE, COCO_MOUSE, COCO_KEYBOARD, COCO_LAPTOP]):
            hazard_files.append(f)
        # 2. Recyclable: มีขวดน้ำ, แก้วน้ำ (และไม่มีอุปกรณ์อิเล็กทรอนิกส์)
        elif any(c in cset for c in [COCO_BOTTLE, COCO_CUP]):
            recycle_files.append(f)
        # 3. Organic: มีอาหาร, ผลไม้, กล้วย, ส้ม, ขนมปัง
        elif any(c in cset for c in [COCO_BANANA, COCO_APPLE, COCO_ORANGE, COCO_SANDWICH, COCO_PIZZA, COCO_DONUT, COCO_CAKE, COCO_BROCCOLI, COCO_CARROT]):
            organic_files.append(f)
        # 4. Negative: มีเฉพาะคน ไม่มีขยะหรืออุปกรณ์ใดๆ
        elif cset == {COCO_PERSON}:
            person_only_files.append(f)

    # สุ่มเลือกจำนวนภาพที่สมดุลและครอบคลุม
    hazard_sel = hazard_files[:180]
    recycle_sel = recycle_files[:180]
    organic_sel = organic_files[:150]
    person_sel = person_only_files[:60]

    print(f"  ● Hazardous Candidates  : {len(hazard_sel)} ภาพ (โทรศัพท์มือถือ/อิเล็กทรอนิกส์)")
    print(f"  ● Recyclable Candidates : {len(recycle_sel)} ภาพ (ขวดน้ำดื่ม/แก้วน้ำ)")
    print(f"  ● Organic Candidates    : {len(organic_sel)} ภาพ (กล้วย/ส้ม/ผลไม้/อาหาร)")
    print(f"  ● Negative Candidates   : {len(person_sel)} ภาพ (คน/ใบหน้า ไม่มีขยะ)")

    all_coco_tasks = []
    for f in hazard_sel: all_coco_tasks.append((f, "hazard"))
    for f in recycle_sel: all_coco_tasks.append((f, "recycle"))
    for f in organic_sel: all_coco_tasks.append((f, "organic"))
    for f in person_sel: all_coco_tasks.append((f, "negative"))

    print(f"\n[2/4] เริ่มดาวน์โหลดและแปลงเลเบล COCO ({len(all_coco_tasks)} ภาพ) แบบขนาน...")

    downloaded = 0
    def process_item(item):
        nonlocal downloaded
        lbl_file, cat_type = item
        img_file = lbl_file.replace(".txt", ".jpg")
        img = download_image(img_file)
        if img is None:
            return

        lbl_path = os.path.join(COCO_VAL_LBL_DIR, lbl_file)
        target_boxes = []

        with open(lbl_path, "r") as fl:
            for line in fl:
                parts = line.strip().split()
                if not parts: continue
                c = int(parts[0])
                coords = [float(x) for x in parts[1:5]]

                # แมป COCO classes เข้ากับ 4 คลาสของเรา:
                # 0: General, 1: Recyclable, 2: Wet, 3: Hazardous
                if c in [COCO_CELL_PHONE, COCO_REMOTE, COCO_MOUSE, COCO_KEYBOARD, COCO_LAPTOP]:
                    target_boxes.append((3, *coords))
                elif c in [COCO_BOTTLE, COCO_CUP]:
                    target_boxes.append((1, *coords))
                elif c in [COCO_BANANA, COCO_APPLE, COCO_ORANGE, COCO_SANDWICH, COCO_PIZZA, COCO_DONUT, COCO_CAKE, COCO_BROCCOLI, COCO_CARROT]:
                    target_boxes.append((2, *coords))

        # สุ่ม 85% train, 15% val
        split = "train" if random.random() < 0.85 else "val"
        dest_img_dir = TRAIN_IMG if split == "train" else VAL_IMG
        dest_lbl_dir = TRAIN_LBL if split == "train" else VAL_LBL

        # ปรับขนาดภาพให้เป็น 320x240 เพื่อให้ตรงกับกล้อง OV2640 และโหลดเข้า RAM เร็ว
        resized = cv2.resize(img, (320, 240))
        out_name = f"coco_{cat_type}_{img_file[:-4]}"
        cv2.imwrite(os.path.join(dest_img_dir, f"{out_name}.jpg"), resized)

        with open(os.path.join(dest_lbl_dir, f"{out_name}.txt"), "w") as out_fl:
            for b in target_boxes:
                out_fl.write(f"{b[0]} {b[1]:.4f} {b[2]:.4f} {b[3]:.4f} {b[4]:.4f}\n")

        downloaded += 1
        if downloaded % 50 == 0 or downloaded == len(all_coco_tasks):
            print(f"  >> ดาวน์โหลดและแปลงแล้ว: {downloaded}/{len(all_coco_tasks)} ภาพ...")

    with ThreadPoolExecutor(max_workers=16) as executor:
        list(executor.map(process_item, all_coco_tasks))

    # =========================================================================
    # [3/4] ผสานภาพขยะจริงจากกล้อง OV2640 ของผู้ใช้ (Real Hardware Scans)
    # =========================================================================
    print("\n[3/4] กำลังผสานภาพถ่ายจริงจากกล้อง OV2640 (โทรศัพท์, แก้วน้ำ, ซองขนม, คน)...")
    
    # 1. โทรศัพท์มือถือของผู้ใช้ (Class 3: Hazardous)
    real_phone_scans = [
        ("raw_20261005_104605.jpg", [108, 48, 227, 240]),
        ("raw_20261005_101751.jpg", [120, 80, 240, 239]),
        ("raw_20261005_101729.jpg", [115, 65, 235, 239]),
        ("raw_20261005_101716.jpg", [110, 50, 230, 239]),
        ("raw_20261005_100323.jpg", [125, 75, 245, 239]),
        ("raw_20261005_094502.jpg", [110, 60, 220, 235])
    ]

    for fname, bbox in real_phone_scans:
        p = os.path.join(PROJECT_DIR, "captured_scans", fname)
        if os.path.exists(p):
            im = cv2.imread(p)
            if im is not None:
                h, w = im.shape[:2]
                xc = (bbox[0] + bbox[2]) / 2.0 / w
                yc = (bbox[1] + bbox[3]) / 2.0 / h
                bw = (bbox[2] - bbox[0]) / float(w)
                bh = (bbox[3] - bbox[1]) / float(h)
                
                # เพิ่ม Data Augmentation 8x สำหรับภาพโทรศัพท์จริง
                for aug_idx in range(8):
                    aug_im = im.copy()
                    if aug_idx == 1:
                        aug_im = cv2.flip(aug_im, 1)
                        axc = 1.0 - xc
                    else:
                        axc = xc
                    if aug_idx == 2:
                        aug_im = cv2.convertScaleAbs(aug_im, alpha=1.15, beta=25)
                    elif aug_idx == 3:
                        aug_im = cv2.convertScaleAbs(aug_im, alpha=0.85, beta=-25)
                    elif aug_idx == 4:
                        aug_im = cv2.GaussianBlur(aug_im, (5, 5), 0)

                    split = "val" if aug_idx == 5 else "train"
                    dest_img_dir = TRAIN_IMG if split == "train" else VAL_IMG
                    dest_lbl_dir = TRAIN_LBL if split == "train" else VAL_LBL

                    out_name = f"real_user_phone_{fname[:-4]}_aug{aug_idx}"
                    cv2.imwrite(os.path.join(dest_img_dir, f"{out_name}.jpg"), aug_im)
                    with open(os.path.join(dest_lbl_dir, f"{out_name}.txt"), "w") as fl:
                        fl.write(f"3 {axc:.4f} {yc:.4f} {bw:.4f} {bh:.4f}\n")

    # 2. แก้วน้ำพลาสติกของผู้ใช้ (Class 1: Recyclable)
    real_cup_scans = [
        ("raw_20261005_095039.jpg", [120, 95, 265, 239]),
        ("raw_20261005_095024.jpg", [110, 60, 240, 239]),
        ("raw_20261005_094654.jpg", [95, 35, 235, 239]),
        ("raw_20261005_094626.jpg", [215, 18, 319, 195]),
        ("raw_20261005_094546.jpg", [50, 95, 155, 220]),
        ("raw_20261005_094530.jpg", [60, 80, 160, 210])
    ]
    for fname, bbox in real_cup_scans:
        p = os.path.join(PROJECT_DIR, "captured_scans", fname)
        if os.path.exists(p):
            im = cv2.imread(p)
            if im is not None:
                h, w = im.shape[:2]
                xc = (bbox[0] + bbox[2]) / 2.0 / w
                yc = (bbox[1] + bbox[3]) / 2.0 / h
                bw = (bbox[2] - bbox[0]) / float(w)
                bh = (bbox[3] - bbox[1]) / float(h)
                for aug_idx in range(6):
                    aug_im = im.copy()
                    if aug_idx == 1:
                        aug_im = cv2.flip(aug_im, 1)
                        axc = 1.0 - xc
                    else:
                        axc = xc
                    if aug_idx == 2: aug_im = cv2.convertScaleAbs(aug_im, alpha=1.1, beta=15)
                    elif aug_idx == 3: aug_im = cv2.convertScaleAbs(aug_im, alpha=0.9, beta=-15)

                    split = "val" if aug_idx == 4 else "train"
                    dest_img_dir = TRAIN_IMG if split == "train" else VAL_IMG
                    dest_lbl_dir = TRAIN_LBL if split == "train" else VAL_LBL

                    out_name = f"real_user_cup_{fname[:-4]}_aug{aug_idx}"
                    cv2.imwrite(os.path.join(dest_img_dir, f"{out_name}.jpg"), aug_im)
                    with open(os.path.join(dest_lbl_dir, f"{out_name}.txt"), "w") as fl:
                        fl.write(f"1 {axc:.4f} {yc:.4f} {bw:.4f} {bh:.4f}\n")

    # 3. ขยะทั่วไป (Class 0: General) - ซองขนม ถุงพลาสติก กล่องโฟม
    sample_general = [
        os.path.join(PROJECT_DIR, "captured_scans", "scan_20261004_010837_GENERAL.jpg"),
        os.path.join(PROJECT_DIR, "ai_training", "sample_images", "0_general_plastic_bag.jpg")
    ]
    for s_path in sample_general:
        if os.path.exists(s_path):
            im = cv2.imread(s_path)
            if im is not None:
                for aug_idx in range(15):
                    aug_im = im.copy()
                    if aug_idx % 2 == 1: aug_im = cv2.flip(aug_im, 1)
                    if aug_idx % 3 == 0: aug_im = cv2.convertScaleAbs(aug_im, alpha=1.1, beta=20)
                    elif aug_idx % 3 == 1: aug_im = cv2.convertScaleAbs(aug_im, alpha=0.9, beta=-20)

                    split = "val" if aug_idx == 10 else "train"
                    dest_img_dir = TRAIN_IMG if split == "train" else VAL_IMG
                    dest_lbl_dir = TRAIN_LBL if split == "train" else VAL_LBL

                    out_name = f"real_general_{os.path.basename(s_path)[:-4]}_aug{aug_idx}"
                    cv2.imwrite(os.path.join(dest_img_dir, f"{out_name}.jpg"), aug_im)
                    with open(os.path.join(dest_lbl_dir, f"{out_name}.txt"), "w") as fl:
                        fl.write("0 0.5000 0.5000 0.7000 0.7000\n")

    # 4. Negative Samples - ใบหน้าคน / ร่างกายคน (ไม่มีขยะ)
    negative_scans = [
        "raw_20261004_232243.jpg", "raw_20261004_232227.jpg",
        "raw_20261004_232204.jpg", "raw_20261004_223804.jpg",
        "raw_20261004_223614.jpg", "raw_20261004_223550.jpg"
    ]
    for ntag in negative_scans:
        p = os.path.join(PROJECT_DIR, "captured_scans", ntag)
        if os.path.exists(p):
            im = cv2.imread(p)
            if im is not None:
                for aug_idx in range(4):
                    aug_im = im.copy()
                    if aug_idx == 1: aug_im = cv2.flip(aug_im, 1)
                    split = "val" if aug_idx == 3 else "train"
                    dest_img_dir = TRAIN_IMG if split == "train" else VAL_IMG
                    dest_lbl_dir = TRAIN_LBL if split == "train" else VAL_LBL

                    out_name = f"real_negative_person_{ntag[:-4]}_aug{aug_idx}"
                    cv2.imwrite(os.path.join(dest_img_dir, f"{out_name}.jpg"), aug_im)
                    with open(os.path.join(dest_lbl_dir, f"{out_name}.txt"), "w") as fl:
                        pass # Empty txt = Negative background

    # =========================================================================
    # [4/4] สร้าง data.yaml สำหรับ YOLOv8
    # =========================================================================
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

    train_cnt = len(glob.glob(os.path.join(TRAIN_IMG, "*.jpg")))
    val_cnt = len(glob.glob(os.path.join(VAL_IMG, "*.jpg")))

    print("\n========================================================")
    print(f"🎉 [DATASET COMPLETED] สร้างชุดข้อมูลสำเร็จสมบูรณ์!")
    print(f"   ● Train images : {train_cnt} ภาพ")
    print(f"   ● Val images   : {val_cnt} ภาพ")
    print(f"   ● รวมทั้งหมด    : {train_cnt + val_cnt} ภาพ")
    print("========================================================")

if __name__ == "__main__":
    main()
