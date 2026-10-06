"""
Prepare 4-Class Waste Sorting Dataset and Train YOLOv8
======================================================
Prepares training images & YOLO labels for the 4 waste classes:
  0: General (ขยะทั่วไป)
  1: Recyclable (ขยะรีไซเคิล)
  2: Wet / Organic (ขยะเปียก)
  3: Hazardous (ขยะอันตราย - รวมแผงยา, ถ่าน, มือถือ)

Trains custom YOLOv8n weights on the dataset.
"""

import os
import shutil
import cv2
from ultralytics import YOLO

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(ROOT_DIR, "ai_training", "dataset")

TRAIN_IMG = os.path.join(DATASET_DIR, "images", "train")
VAL_IMG   = os.path.join(DATASET_DIR, "images", "val")
TRAIN_LBL = os.path.join(DATASET_DIR, "labels", "train")
VAL_LBL   = os.path.join(DATASET_DIR, "labels", "val")

for d in [TRAIN_IMG, VAL_IMG, TRAIN_LBL, VAL_LBL]:
    os.makedirs(d, exist_ok=True)

# 1. รวบรวมภาพที่มีอยู่เข้ามาในชุดข้อมูล
# ภาพตัวอย่างที่ดาวน์โหลดไว้ + ภาพจริงจากกล้องของผู้ใช้
SOURCE_IMAGES = [
    # (source_path, class_id, is_train)
    (os.path.join(ROOT_DIR, "ai_training", "sample_images", "0_general_plastic_bag.jpg"), 0, True),
    (os.path.join(ROOT_DIR, "ai_training", "sample_images", "1_recycle_plastic_bottle.jpg"), 1, True),
    (os.path.join(ROOT_DIR, "ai_training", "sample_images", "2_wet_banana_peel.jpg"), 2, True),
    (os.path.join(ROOT_DIR, "ai_training", "sample_images", "4_hazard_battery.jpg"), 3, True),
    # ภาพถ่ายจริงแผงยาของผู้ใช้ -> กำหนดเป็น Class 3 (ขยะอันตราย)
    (os.path.join(ROOT_DIR, "RESULT_SCAN.jpg"), 3, False), # ใส่ใน Validation
]

print("==========================================================================")
print("  📦 กำลังเตรียมชุดข้อมูล Dataset สำหรับ 4 คลาสขยะ...")
print("==========================================================================")

def write_yolo_label(lbl_path, class_id, x_center=0.5, y_center=0.5, width=0.7, height=0.7):
    with open(lbl_path, "w", encoding="utf-8") as f:
        f.write(f"{class_id} {x_center:.4f} {y_center:.4f} {width:.4f} {height:.4f}\n")

# ทำ Data Augmentation เบื้องต้น (Flip, Brightness) เพื่อเพิ่มจำนวนภาพฝึกสอน
sample_count = 0
for src, cls_id, is_train in SOURCE_IMAGES:
    if not os.path.exists(src):
        continue
    
    img = cv2.imread(src)
    if img is None:
        continue

    base_name = os.path.splitext(os.path.basename(src))[0]
    
    # ภาพต้นฉบับ
    dst_img = os.path.join(TRAIN_IMG if is_train else VAL_IMG, f"{base_name}_orig.jpg")
    dst_lbl = os.path.join(TRAIN_LBL if is_train else VAL_LBL, f"{base_name}_orig.txt")
    cv2.imwrite(dst_img, img)
    # กรอบวัตถุโดยประมาณตรงกลาง
    write_yolo_label(dst_lbl, cls_id, 0.5, 0.5, 0.65, 0.65)
    sample_count += 1

    # Augmentation 1: พลิกภาพแนวนอน (Horizontal Flip)
    flipped = cv2.flip(img, 1)
    dst_flip = os.path.join(TRAIN_IMG, f"{base_name}_flip.jpg")
    dst_lbl_flip = os.path.join(TRAIN_LBL, f"{base_name}_flip.txt")
    cv2.imwrite(dst_flip, flipped)
    write_yolo_label(dst_lbl_flip, cls_id, 0.5, 0.5, 0.65, 0.65)
    sample_count += 1

    # Augmentation 2: ปรับความสว่าง (Brightness)
    bright = cv2.convertScaleAbs(img, alpha=1.2, beta=15)
    dst_bright = os.path.join(TRAIN_IMG, f"{base_name}_bright.jpg")
    dst_lbl_bright = os.path.join(TRAIN_LBL, f"{base_name}_bright.txt")
    cv2.imwrite(dst_bright, bright)
    write_yolo_label(dst_lbl_bright, cls_id, 0.5, 0.5, 0.65, 0.65)
    sample_count += 1

# สร้าง data.yaml
yaml_path = os.path.join(DATASET_DIR, "data.yaml")
yaml_content = f"""path: {DATASET_DIR.replace(chr(92), '/')}
train: images/train
val: images/val

nc: 4
names: ['General', 'Recyclable', 'Wet', 'Hazardous']
"""

with open(yaml_path, "w", encoding="utf-8") as f:
    f.write(yaml_content)

print(f"[+] สร้างชุดข้อมูลสำเร็จ: {sample_count} ภาพ พร้อมไฟล์ data.yaml")
print(f"[+] ไฟล์ data.yaml: {yaml_path}")

# 2. เริ่มเทรนโมเดล YOLOv8
print("\n==========================================================================")
print("  🚀 กำลังเริ่มต้นเทรนโมเดล YOLOv8 Nano (Fine-tuning 5 Epochs)...")
print("==========================================================================")

model = YOLO("yolov8n.pt")

results = model.train(
    data=yaml_path,
    epochs=5,
    imgsz=320,
    batch=4,
    name="smart_bin_custom",
    project=os.path.join(ROOT_DIR, "ai_training", "runs"),
    exist_ok=True,
    verbose=True
)

# บันทึกโมเดลที่เทรนเสร็จแล้ว
trained_model_dir = os.path.join(ROOT_DIR, "ai_training", "trained_models")
os.makedirs(trained_model_dir, exist_ok=True)
best_src = os.path.join(ROOT_DIR, "ai_training", "runs", "smart_bin_custom", "weights", "best.pt")
best_dst = os.path.join(trained_model_dir, "smart_bin_best.pt")

if os.path.exists(best_src):
    shutil.copy(best_src, best_dst)
    print(f"\n[🎉 SUCCESS] เทรนโมเดลเสร็จสมบูรณ์!")
    print(f"[+] บันทึกน้ำหนักโมเดลใหม่ไว้ที่: {best_dst}")
