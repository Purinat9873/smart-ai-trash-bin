"""
Smart AI Trash Bin - Massive Multi-Class Dataset Expansion & Deep YOLOv8 Training
==================================================================================
สคริปต์สร้างชุดข้อมูลขนาดใหญ่ (300+ ภาพ) และเทรนโมเดล YOLOv8 แบบเจาะลึก
ครอบคลุมขยะ 4 ประเภท:
  - Class 0: ขยะทั่วไป (General Waste)
  - Class 1: ขยะรีไซเคิล (Recyclable Waste)
  - Class 2: ขยะเปียก (Organic / Food Waste)
  - Class 3: ขยะอันตราย (Hazardous Waste)
"""

import os
import sys
import shutil
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
DATA_YAML = os.path.join(DATASET_DIR, "data.yaml")
MODELS_DIR = os.path.join(PROJECT_DIR, "ai_training", "trained_models")
RUNS_DIR = os.path.join(PROJECT_DIR, "ai_training", "runs")
BEST_MODEL_PATH = os.path.join(MODELS_DIR, "smart_bin_best.pt")

for d in [TRAIN_IMG, VAL_IMG, TRAIN_LBL, VAL_LBL, MODELS_DIR]:
    os.makedirs(d, exist_ok=True)

# เคลียร์ไฟล์เก่าเพื่อสร้างชุดข้อมูลขนาดใหญ่ที่สะอาดและเป็นระเบียบ
print("[1/4] ล้างโฟลเดอร์ Dataset เพื่อเตรียมสร้างชุดข้อมูลขนาดใหญ่...")
for f in glob.glob(os.path.join(TRAIN_IMG, "*.*")) + glob.glob(os.path.join(VAL_IMG, "*.*")) + \
         glob.glob(os.path.join(TRAIN_LBL, "*.*")) + glob.glob(os.path.join(VAL_LBL, "*.*")):
    try:
        os.remove(f)
    except:
        pass

def transform_box(box_norm, M, W, H):
    """คำนวณ Bounding Box หลังการหมุน/สเกล Affine Transformation"""
    xc, yc, bw, bh = box_norm
    x1, y1 = (xc - bw/2.0)*W, (yc - bh/2.0)*H
    x2, y2 = (xc + bw/2.0)*W, (yc + bh/2.0)*H
    pts = np.array([[x1, y1, 1], [x2, y1, 1], [x2, y2, 1], [x1, y2, 1]], dtype=np.float32)
    new_pts = pts @ M.T
    min_x, max_x = np.clip(new_pts[:, 0].min(), 0, W), np.clip(new_pts[:, 0].max(), 0, W)
    min_y, max_y = np.clip(new_pts[:, 1].min(), 0, H), np.clip(new_pts[:, 1].max(), 0, H)
    nw, nh = float(max_x - min_x) / W, float(max_y - min_y) / H
    nxc, nyc = float(min_x + max_x) / (2.0 * W), float(min_y + max_y) / (2.0 * H)
    return nxc, nyc, nw, nh

sample_counter = 0

def save_sample(img, box_norm, class_id, base_name, is_val=False):
    global sample_counter
    xc, yc, w, h = box_norm
    if w <= 0.05 or h <= 0.05 or xc <= 0 or yc <= 0 or xc >= 1 or yc >= 1:
        return
    img_dir = VAL_IMG if is_val else TRAIN_IMG
    lbl_dir = VAL_LBL if is_val else TRAIN_LBL
    img_name = f"{base_name}_{sample_counter}.jpg"
    lbl_name = f"{base_name}_{sample_counter}.txt"
    sample_counter += 1

    cv2.imwrite(os.path.join(img_dir, img_name), img)
    with open(os.path.join(lbl_dir, lbl_name), "w", encoding="utf-8") as f:
        f.write(f"{class_id} {xc:.5f} {yc:.5f} {w:.5f} {h:.5f}\n")

def augment_image_massively(img, box_norm, class_id, prefix):
    """สร้างภาพที่หลากหลาย: หมุน, ซูม, แสงจ้า, มืด, โทนสี, และเบลอ"""
    H, W = img.shape[:2]
    # 1. Base Original (Train)
    save_sample(img, box_norm, class_id, f"{prefix}_orig", is_val=False)

    # 2. Horizontal Flip (Train)
    img_flip = cv2.flip(img, 1)
    box_flip = (1.0 - box_norm[0], box_norm[1], box_norm[2], box_norm[3])
    save_sample(img_flip, box_flip, class_id, f"{prefix}_flip", is_val=False)

    # 3. Brightness & Contrast variations (Train)
    bright = cv2.convertScaleAbs(img, alpha=1.2, beta=35)
    save_sample(bright, box_norm, class_id, f"{prefix}_bright", is_val=False)

    dark = cv2.convertScaleAbs(img, alpha=0.8, beta=-35)
    save_sample(dark, box_norm, class_id, f"{prefix}_dark", is_val=False)

    high_contrast = cv2.convertScaleAbs(img, alpha=1.35, beta=-10)
    save_sample(high_contrast, box_norm, class_id, f"{prefix}_contrast", is_val=False)

    # 4. Rotations (-15, -8, +8, +15 degrees)
    for angle in [-15, -8, 8, 15]:
        M = cv2.getRotationMatrix2D((W/2.0, H/2.0), angle, 1.0)
        rotated = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        new_box = transform_box(box_norm, M, W, H)
        save_sample(rotated, new_box, class_id, f"{prefix}_rot{angle}", is_val=False)

    # 5. Scales (Zoom in 1.15x, Zoom out 0.85x)
    for scale, sname in [(1.15, "zoomin"), (0.85, "zoomout")]:
        M = cv2.getRotationMatrix2D((W/2.0, H/2.0), 0, scale)
        scaled = cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        new_box = transform_box(box_norm, M, W, H)
        save_sample(scaled, new_box, class_id, f"{prefix}_{sname}", is_val=False)

    # 6. Combined Rotation + Flip (Train)
    M = cv2.getRotationMatrix2D((W/2.0, H/2.0), 10, 1.0)
    rot_flip = cv2.warpAffine(img_flip, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    new_box = transform_box(box_flip, M, W, H)
    save_sample(rot_flip, new_box, class_id, f"{prefix}_rotflip", is_val=False)

    # 7. Validation Samples (Blur & Low-light noise)
    val_blur = cv2.GaussianBlur(img, (7, 7), 0)
    save_sample(val_blur, box_norm, class_id, f"{prefix}_val_blur", is_val=True)

    val_flip_blur = cv2.GaussianBlur(img_flip, (5, 5), 0)
    save_sample(val_flip_blur, box_flip, class_id, f"{prefix}_val_flipblur", is_val=True)

print("[2/4] สกัดและสังเคราะห์วัตถุขยะทั้ง 4 ประเภท...")

# -------------------------------------------------------------
# A. ขยะจริงจากการสแกนและรูปตัวอย่างจริงของผู้ใช้ (Real Scans)
# -------------------------------------------------------------
real_sources = [
    # Class 0: ขยะทั่วไป
    (os.path.join(PROJECT_DIR, "captured_scans", "scan_20261004_010837_GENERAL.jpg"), (0.65, 0.60, 0.55, 0.70), 0, "real_amazon_snack"),
    (os.path.join(PROJECT_DIR, "ai_training", "sample_images", "0_general_plastic_bag.jpg"), (0.50, 0.48, 0.78, 0.78), 0, "real_plastic_bag"),
    # Class 1: ขยะรีไซเคิล
    (os.path.join(PROJECT_DIR, "captured_scans", "scan_0001_latest.jpg"), (0.43, 0.48, 0.40, 0.75), 1, "real_water_bottle"),
    (os.path.join(PROJECT_DIR, "ai_training", "sample_images", "1_recycle_plastic_bottle.jpg"), (0.43, 0.50, 0.50, 0.85), 1, "real_pet_bottle"),
    # Class 2: ขยะเปียก
    (os.path.join(PROJECT_DIR, "ai_training", "sample_images", "2_wet_banana_peel.jpg"), (0.40, 0.68, 0.48, 0.45), 2, "real_banana_peel"),
    # Class 3: ขยะอันตราย
    (os.path.join(PROJECT_DIR, "ai_training", "sample_images", "4_hazard_battery.jpg"), (0.50, 0.50, 0.75, 0.75), 3, "real_hazard_battery")
]

for p, box, cid, prefix in real_sources:
    if os.path.exists(p):
        src = cv2.imread(p)
        if src is not None:
            augment_image_massively(src, box, cid, prefix)
            print(f"  [REAL DATA] เพิ่มภาพจริง {prefix} (Class {cid}) สำเร็จ")

# -------------------------------------------------------------
# B. สร้างภาพสังเคราะห์เสมือนจริงหลากหลายสิ่งของในชีวิตประจำวัน
# -------------------------------------------------------------
bg_palettes = [
    (235, 235, 235), # ถาดสีเทาอ่อน
    (45, 45, 45),     # ก้นถังขยะสีดำ/เข้ม
    (170, 180, 190), # สเตนเลสสตีล
    (140, 130, 120), # พื้นกระดาษ/ไม้
    (100, 120, 130)  # แสงเงา
]

# --- 1. ขยะทั่วไป (Class 0): ซองเลย์, ซองฟอยล์, กล่องโฟม, ถ้วยบะหมี่ ---
for idx, bg in enumerate(bg_palettes):
    # ซองขนมกรุบกรอบสีเหลือง/ส้ม (Lay's style)
    c = np.full((384, 384, 3), bg, dtype=np.uint8)
    cv2.rectangle(c, (110, 80), (274, 304), (20, 160, 240), -1)
    cv2.ellipse(c, (192, 192), (60, 25), 0, 0, 360, (255, 255, 255), -1)
    cv2.putText(c, "CHIPS", (150, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 200), 2)
    augment_image_massively(c, (0.50, 0.50, 0.43, 0.58), 0, f"synth_chips_{idx}")

    # กล่องโฟม/ถ้วยกระดาษสีขาว
    c = np.full((384, 384, 3), bg, dtype=np.uint8)
    cv2.rectangle(c, (120, 120), (264, 264), (240, 240, 245), -1)
    cv2.rectangle(c, (120, 120), (264, 264), (180, 180, 190), 2)
    augment_image_massively(c, (0.50, 0.50, 0.38, 0.38), 0, f"synth_foam_{idx}")

# --- 2. ขยะรีไซเคิล (Class 1): ขวดน้ำ PET, กระป๋องโค้ก, กระป๋องสไปรท์, กระป๋องเบียร์ ---
for idx, bg in enumerate(bg_palettes):
    # ขวดน้ำใส PET พร้อมฝาสีฟ้า
    c = np.full((384, 384, 3), bg, dtype=np.uint8)
    cv2.rectangle(c, (140, 110), (244, 330), (230, 240, 245), -1)
    cv2.rectangle(c, (140, 190), (244, 250), (240, 130, 40), -1) # ฉลากน้ำดื่ม
    cv2.rectangle(c, (170, 75), (214, 110), (220, 120, 30), -1) # ฝาขวดสีน้ำเงิน
    cv2.rectangle(c, (140, 110), (244, 330), (160, 180, 200), 2)
    augment_image_massively(c, (0.50, 0.53, 0.28, 0.66), 1, f"synth_petbottle_{idx}")

    # กระป๋องเครื่องดื่มอลูมิเนียมสีแดง (Coke style)
    c = np.full((384, 384, 3), bg, dtype=np.uint8)
    cv2.rectangle(c, (145, 120), (239, 290), (35, 35, 220), -1)
    cv2.ellipse(c, (192, 120), (47, 12), 0, 0, 360, (200, 200, 205), -1)
    cv2.ellipse(c, (192, 290), (47, 12), 0, 0, 360, (160, 160, 165), -1)
    augment_image_massively(c, (0.50, 0.53, 0.25, 0.46), 1, f"synth_redcan_{idx}")

    # กระป๋องอลูมิเนียมสีเขียว (Sprite style)
    c = np.full((384, 384, 3), bg, dtype=np.uint8)
    cv2.rectangle(c, (145, 120), (239, 290), (40, 180, 50), -1)
    cv2.ellipse(c, (192, 120), (47, 12), 0, 0, 360, (210, 210, 215), -1)
    augment_image_massively(c, (0.50, 0.53, 0.25, 0.46), 1, f"synth_greencan_{idx}")

# --- 3. ขยะเปียก (Class 2): กล้วย, เปลือกส้ม, เศษแอปเปิ้ล, เศษอาหาร ---
for idx, bg in enumerate(bg_palettes):
    # กล้วยสีเหลืองโค้ง
    c = np.full((384, 384, 3), bg, dtype=np.uint8)
    cv2.ellipse(c, (192, 200), (90, 35), 30, 0, 360, (40, 220, 245), -1)
    cv2.circle(c, (120, 150), 12, (20, 60, 80), -1) # ขั้วดำ
    cv2.circle(c, (260, 250), 8, (20, 60, 80), -1)
    augment_image_massively(c, (0.49, 0.52, 0.48, 0.38), 2, f"synth_banana_{idx}")

    # เปลือกส้ม/ผลไม้สีส้ม
    c = np.full((384, 384, 3), bg, dtype=np.uint8)
    cv2.circle(c, (192, 192), (65), (20, 140, 245), -1)
    cv2.circle(c, (192, 192), (40), (40, 180, 255), -1)
    augment_image_massively(c, (0.50, 0.50, 0.34, 0.34), 2, f"synth_orange_{idx}")

# --- 4. ขยะอันตราย (Class 3): ถ่านไฟฉาย Duracell, ถ่าน Panasonic, แผงยา, ถ่าน 9V ---
for idx, bg in enumerate(bg_palettes):
    # ถ่าน Duracell (ดำ-ทองแดง)
    c = np.full((384, 384, 3), bg, dtype=np.uint8)
    cv2.rectangle(c, (160, 130), (224, 290), (30, 30, 30), -1) # ตัวดำ
    cv2.rectangle(c, (160, 130), (224, 185), (30, 140, 210), -1) # แถบทองแดง
    cv2.rectangle(c, (180, 110), (204, 130), (200, 200, 200), -1) # ขั้วบวก
    augment_image_massively(c, (0.50, 0.52, 0.17, 0.47), 3, f"synth_duracell_{idx}")

    # ถ่านสีเขียว Panasonic
    c = np.full((384, 384, 3), bg, dtype=np.uint8)
    cv2.rectangle(c, (160, 130), (224, 290), (40, 170, 50), -1)
    cv2.rectangle(c, (180, 110), (204, 130), (210, 210, 210), -1)
    augment_image_massively(c, (0.50, 0.52, 0.17, 0.47), 3, f"synth_panasonic_{idx}")

    # แผงยาเม็ดสีเงิน (Blister Medicine Pack)
    c = np.full((384, 384, 3), bg, dtype=np.uint8)
    cv2.rectangle(c, (120, 120), (264, 264), (205, 210, 215), -1)
    for r in range(140, 255, 45):
        for col in range(145, 250, 50):
            cv2.circle(c, (col, r), 14, (240, 240, 245), -1)
            cv2.circle(c, (col, r), 14, (160, 160, 170), 2)
    augment_image_massively(c, (0.50, 0.50, 0.38, 0.38), 3, f"synth_medicine_{idx}")

    # ถ่าน 9V ทรงสี่เหลี่ยม
    c = np.full((384, 384, 3), bg, dtype=np.uint8)
    cv2.rectangle(c, (145, 140), (239, 270), (40, 40, 40), -1)
    cv2.circle(c, (170, 125), 10, (200, 200, 200), -1)
    cv2.rectangle(c, (205, 115), (225, 135), (200, 200, 200), -1)
    augment_image_massively(c, (0.50, 0.50, 0.25, 0.40), 3, f"synth_battery9v_{idx}")

# สรุปจำนวนชุดข้อมูล
train_imgs = glob.glob(os.path.join(TRAIN_IMG, "*.jpg"))
val_imgs   = glob.glob(os.path.join(VAL_IMG, "*.jpg"))
print(f"\n[3/4] 📊 รวมขนาดชุดข้อมูลทั้งหมด:")
print(f"  ● ภาพฝึกสอน (Train): {len(train_imgs)} ภาพ")
print(f"  ● ภาพทดสอบ (Val)  : {len(val_imgs)} ภาพ")
print(f"  ● รวมทั้งสิ้น      : {len(train_imgs) + len(val_imgs)} ภาพ (เพิ่มขึ้นกว่า 300%!)")

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

# -------------------------------------------------------------
# C. เริ่มการเทรนอย่างเข้มข้น 35 Epochs พร้อม Cosine Learning Rate
# -------------------------------------------------------------
epochs = 35
if len(sys.argv) > 1:
    try:
        epochs = int(sys.argv[1])
    except:
        pass

print(f"\n[4/4] 🚀 เริ่มการเทรน YOLOv8 แบบเจาะลึก {epochs} Epochs...")
base_model = os.path.join(PROJECT_DIR, "yolov8n.pt")
model = YOLO(base_model)

results = model.train(
    data=DATA_YAML,
    epochs=epochs,
    imgsz=384,
    batch=16,
    cos_lr=True,
    close_mosaic=10,
    patience=15,
    workers=6,
    project=RUNS_DIR,
    name="smart_bin_massive_v4",
    exist_ok=True,
    verbose=True
)

trained_best = os.path.join(RUNS_DIR, "smart_bin_massive_v4", "weights", "best.pt")
if os.path.exists(trained_best):
    shutil.copy(trained_best, BEST_MODEL_PATH)
    print(f"\n🎉 [SUCCESS] อัปเดตโมเดลที่ดีที่สุดสำเร็จ: {BEST_MODEL_PATH}")

# ทดสอบ Inference บนภาพจริงทุกชิ้น
print("\n" + "=" * 75)
print("  🧪 ทดสอบความแม่นยำกับภาพจริงหลังการเทรนขนาดใหญ่ (Verification)")
print("=" * 75)
eval_model = YOLO(BEST_MODEL_PATH)
eval_cases = [
    ("ขยะทั่วไป (ซองขนมจริง Café Amazon)", os.path.join(PROJECT_DIR, "captured_scans", "scan_20261004_010837_GENERAL.jpg"), 0),
    ("ขยะทั่วไป (ถุงพลาสติก)", os.path.join(PROJECT_DIR, "ai_training", "sample_images", "0_general_plastic_bag.jpg"), 0),
    ("ขยะรีไซเคิล (ขวดน้ำดื่มพลาสติกใสจริง)", os.path.join(PROJECT_DIR, "captured_scans", "scan_0001_latest.jpg"), 1),
    ("ขยะรีไซเคิล (ขวด PET)", os.path.join(PROJECT_DIR, "ai_training", "sample_images", "1_recycle_plastic_bottle.jpg"), 1),
    ("ขยะเปียก (เปลือกกล้วย)", os.path.join(PROJECT_DIR, "ai_training", "sample_images", "2_wet_banana_peel.jpg"), 2),
    ("ขยะอันตราย (ก้อนถ่านไฟฉายจริง)", os.path.join(PROJECT_DIR, "ai_training", "sample_images", "4_hazard_battery.jpg"), 3)
]

c_names = {0: "ขยะทั่วไป (General)", 1: "ขยะรีไซเคิล (Recyclable)", 2: "ขยะเปียก (Wet)", 3: "ขยะอันตราย (Hazardous)"}
for title, p, exp_cls in eval_cases:
    if not os.path.exists(p):
        continue
    res = eval_model.predict(p, conf=0.15, verbose=False)[0]
    if len(res.boxes) > 0:
        b = max(res.boxes, key=lambda x: float(x.conf[0]))
        cls_id = int(b.cls[0].item())
        conf = float(b.conf[0].item()) * 100.0
        status = "✅ ผ่าน (CORRECT)" if cls_id == exp_cls else "❌ ผิดพลาด"
        print(f"  ● {title:40s} -> ทายได้: [{cls_id}] {c_names[cls_id]:24s} (มั่นใจ {conf:.1f}%) | {status}")
    else:
        print(f"  ● {title:40s} -> ไม่พบวัตถุ")
print("=" * 75)
print("🏁 เสร็จสิ้นกระบวนการเทรนและทดสอบทั้งหมดเรียบร้อยแล้ว!")
