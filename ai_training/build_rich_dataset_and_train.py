"""
Build Rich 4-Class Waste Sorting Dataset & Fine-Tune YOLOv8
===========================================================
Classes:
  0: General (ขยะทั่วไป - ซองขนม, ถุงพลาสติก, กล่องโฟม)
  1: Recyclable (ขยะรีไซเคิล - ขวดน้ำ, กระป๋อง, กล่องกระดาษ)
  2: Wet (ขยะเปียก - เศษอาหาร, เปลือกผลไม้)
  3: Hazardous (ขยะอันตราย - ถ่านชาร์จ, ถ่านไฟฉาย, แผงยา, อิเล็กทรอนิกส์)
"""

import os
import glob
import random
import cv2
import numpy as np
from ultralytics import YOLO

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_DIR = os.path.join(PROJECT_DIR, "ai_training", "dataset")

TRAIN_IMG = os.path.join(DATASET_DIR, "images", "train")
VAL_IMG   = os.path.join(DATASET_DIR, "images", "val")
TRAIN_LBL = os.path.join(DATASET_DIR, "labels", "train")
VAL_LBL   = os.path.join(DATASET_DIR, "labels", "val")

for d in [TRAIN_IMG, VAL_IMG, TRAIN_LBL, VAL_LBL]:
    os.makedirs(d, exist_ok=True)

# ลบไฟล์เก่าใน dataset เพื่อเทรนใหม่ให้สะอาด
for f in glob.glob(os.path.join(TRAIN_IMG, "*.*")) + glob.glob(os.path.join(VAL_IMG, "*.*")) + \
         glob.glob(os.path.join(TRAIN_LBL, "*.*")) + glob.glob(os.path.join(VAL_LBL, "*.*")):
    try:
        os.remove(f)
    except:
        pass

def save_sample(img, bbox_norm, class_id, base_name, is_val=False):
    """บันทึกภาพและไฟล์ label แบบ YOLO format"""
    img_dir = VAL_IMG if is_val else TRAIN_IMG
    lbl_dir = VAL_LBL if is_val else TRAIN_LBL
    
    img_path = os.path.join(img_dir, f"{base_name}.jpg")
    lbl_path = os.path.join(lbl_dir, f"{base_name}.txt")
    
    cv2.imwrite(img_path, img)
    xc, yc, w, h = bbox_norm
    with open(lbl_path, "w", encoding="utf-8") as f:
        f.write(f"{class_id} {xc:.5f} {yc:.5f} {w:.5f} {h:.5f}\n")

def augment_and_save(img, bbox, class_id, prefix):
    """สร้างภาพ Augmented หลากหลายมุมมอง แสง และตำแหน่ง"""
    h_img, w_img = img.shape[:2]
    x1, y1, x2, y2 = bbox
    
    xc = ((x1 + x2) / 2.0) / w_img
    yc = ((y1 + y2) / 2.0) / h_img
    w = (x2 - x1) / float(w_img)
    h = (y2 - y1) / float(h_img)
    bbox_norm = (xc, yc, w, h)
    
    # 1. ต้นฉบับ
    save_sample(img, bbox_norm, class_id, f"{prefix}_orig")
    
    # 2. แนวนอน Flip
    flipped = cv2.flip(img, 1)
    bbox_flip = (1.0 - xc, yc, w, h)
    save_sample(flipped, bbox_flip, class_id, f"{prefix}_flip")
    
    # 3. สว่างขึ้น
    bright = cv2.convertScaleAbs(img, alpha=1.25, beta=20)
    save_sample(bright, bbox_norm, class_id, f"{prefix}_bright")
    
    # 4. มืดลงเล็กน้อย
    dark = cv2.convertScaleAbs(img, alpha=0.85, beta=-15)
    save_sample(dark, bbox_norm, class_id, f"{prefix}_dark")
    
    # 5. เบลอเล็กน้อย (จำลองมือขยับ)
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    save_sample(blur, bbox_norm, class_id, f"{prefix}_blur", is_val=True)

print("=" * 65)
print("  🚀 เริ่มต้นสร้างชุดข้อมูลและเทรนโมเดลเฉพาะทางสำหรับถังขยะอัจฉริยะ")
print("=" * 65)

# โหลดภาพถ่ายจริงล่าสุดของผู้ใช้ (ถ่านชาร์จ)
last_scan = os.path.join(PROJECT_DIR, "RESULT_SCAN.jpg")
if os.path.exists(last_scan):
    img_user = cv2.imread(last_scan)
    if img_user is not None:
        # พิกัดถ่านชาร์จจริงในมือผู้ใช้
        battery_bbox = (450, 210, 535, 450)
        augment_and_save(img_user, battery_bbox, 3, "user_battery")
        print("  [DATA] นำเข้าภาพถ่ายจริง: ถ่านชาร์จในมือผู้ใช้ -> Class 3 (Hazardous)")

# สร้างตัวอย่างสังเคราะห์และตัวอย่างจริงเสริมสำหรับแต่ละคลาส
# สร้างภาพถ่านแบบต่างๆ (ทรงกระบอก เขียว/เงิน/ดำ/ทอง)
bg_colors = [(240, 240, 240), (40, 40, 40), (180, 190, 200), (120, 110, 100)]
for idx, bg in enumerate(bg_colors):
    canvas = np.full((640, 640, 3), bg, dtype=np.uint8)
    # วาดถ่านชาร์จ (สีเขียวหัวเงิน)
    cv2.rectangle(canvas, (280, 160), (360, 480), (30, 180, 40), -1) # ตัวถ่านเขียว
    cv2.rectangle(canvas, (300, 130), (340, 160), (200, 200, 200), -1) # ขั้วบวกเงิน
    cv2.rectangle(canvas, (280, 160), (360, 480), (10, 120, 20), 2)
    augment_and_save(canvas, (280, 130, 360, 480), 3, f"synth_battery_green_{idx}")

# ถ่านไฟฉายสีดำ-ทอง (Duracell style)
for idx, bg in enumerate(bg_colors[:2]):
    canvas = np.full((640, 640, 3), bg, dtype=np.uint8)
    cv2.rectangle(canvas, (270, 180), (370, 480), (30, 30, 30), -1)
    cv2.rectangle(canvas, (270, 180), (370, 270), (30, 150, 220), -1) # ส่วนสีทองแดง
    cv2.rectangle(canvas, (300, 150), (340, 180), (200, 200, 200), -1)
    augment_and_save(canvas, (270, 150, 370, 480), 3, f"synth_battery_duracell_{idx}")

# แผงยา (Medicine Blister Pack - Class 3)
for idx, bg in enumerate(bg_colors[:2]):
    canvas = np.full((640, 640, 3), bg, dtype=np.uint8)
    cv2.rectangle(canvas, (220, 200), (420, 440), (210, 210, 215), -1) # ฟอยล์เงิน
    for r in range(220, 430, 70):
        for c in range(240, 410, 80):
            cv2.circle(canvas, (c, r), 22, (240, 240, 245), -1)
            cv2.circle(canvas, (c, r), 22, (160, 160, 170), 2)
    augment_and_save(canvas, (220, 200, 420, 440), 3, f"synth_medicine_{idx}")

# ขวดน้ำพลาสติก PET (Class 1 - Recyclable)
for idx, bg in enumerate(bg_colors):
    canvas = np.full((640, 640, 3), bg, dtype=np.uint8)
    cv2.rectangle(canvas, (260, 200), (380, 520), (230, 240, 245), -1)
    cv2.rectangle(canvas, (260, 320), (380, 400), (240, 120, 80), -1) # ฉลากน้ำดื่ม
    cv2.rectangle(canvas, (300, 160), (340, 200), (40, 200, 60), -1) # ฝาสีเขียว
    augment_and_save(canvas, (260, 160, 380, 520), 1, f"synth_bottle_{idx}")

# กระป๋องอลูมิเนียม (Class 1 - Recyclable)
for idx, bg in enumerate(bg_colors[:2]):
    canvas = np.full((640, 640, 3), bg, dtype=np.uint8)
    cv2.rectangle(canvas, (270, 220), (370, 460), (40, 40, 220), -1) # กระป๋องโค้กสีแดง
    cv2.ellipse(canvas, (320, 220), (50, 15), 0, 0, 360, (200, 200, 200), -1)
    augment_and_save(canvas, (270, 205, 370, 460), 1, f"synth_can_{idx}")

# กล้วย / เปลือกผลไม้ (Class 2 - Wet)
for idx, bg in enumerate(bg_colors[:2]):
    canvas = np.full((640, 640, 3), bg, dtype=np.uint8)
    cv2.ellipse(canvas, (320, 320), (120, 45), 35, 0, 360, (40, 220, 240), -1) # กล้วยสีเหลือง
    cv2.circle(canvas, (220, 250), 15, (30, 80, 100), -1) # ปลายดำ
    augment_and_save(canvas, (200, 230, 440, 410), 2, f"synth_banana_{idx}")

# ซองขนม / ถุงพลาสติก (Class 0 - General)
for idx, bg in enumerate(bg_colors[:2]):
    canvas = np.full((640, 640, 3), bg, dtype=np.uint8)
    cv2.rectangle(canvas, (220, 200), (420, 460), (30, 180, 230), -1) # ซองเลย์สีเหลืองทอง
    cv2.putText(canvas, "SNACK", (260, 340), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)
    augment_and_save(canvas, (220, 200, 420, 460), 0, f"synth_snack_{idx}")

# สร้างไฟล์ data.yaml
yaml_path = os.path.join(DATASET_DIR, "data.yaml")
yaml_content = f"""path: {DATASET_DIR.replace(os.sep, '/')}
train: images/train
val: images/val

names:
  0: General
  1: Recyclable
  2: Wet
  3: Hazardous
"""

with open(yaml_path, "w", encoding="utf-8") as f:
    f.write(yaml_content)

train_count = len(glob.glob(os.path.join(TRAIN_IMG, "*.*")))
val_count = len(glob.glob(os.path.join(VAL_IMG, "*.*")))
print(f"  [DATASET READY] ภาพฝึกสอน: {train_count} รูป, ภาพทดสอบ: {val_count} รูป")
print("  ⚙️ กำลังเริ่มเทรนโมเดล YOLOv8n (Fine-Tuning 15 Epochs)...")

# เริ่มเทรนโมเดล
model = YOLO("yolov8n.pt")
results = model.train(
    data=yaml_path,
    epochs=15,
    imgsz=416,
    batch=8,
    device="cpu",
    project=os.path.join(PROJECT_DIR, "ai_training", "runs"),
    name="smart_bin_v2",
    exist_ok=True,
    verbose=False
)

best_trained = os.path.join(PROJECT_DIR, "ai_training", "runs", "smart_bin_v2", "weights", "best.pt")
final_model = os.path.join(PROJECT_DIR, "ai_training", "trained_models", "smart_bin_best.pt")

if os.path.exists(best_trained):
    import shutil
    shutil.copy(best_trained, final_model)
    print(f"\n  🎉 [SUCCESS] เทรนโมเดลสำเร็จ 100%! บันทึกไว้ที่: {final_model}")
else:
    print("\n  [WARN] ไม่พบไฟล์ weights best.pt")

print("=" * 65)
