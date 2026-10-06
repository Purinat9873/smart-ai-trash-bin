"""
Smart AI Trash Bin - Model Retraining Pipeline
================================================
สคริปต์สำหรับเทรน AI เพิ่มเติม (Fine-tuning Custom YOLOv8)
เมื่อต้องการเพิ่มภาพตัวอย่างขยะใหม่ๆ ให้แม่นยำยิ่งขึ้น:
1. ใส่ภาพขยะใหม่ลงในโฟลเดอร์: ai_training/dataset/images/train/
2. รันสคริปต์นี้: python ai_training/retrain_custom_model.py
3. ระบบจะเทรนและอัปเดต smart_bin_best.pt ให้อัตโนมัติทันที
"""

import os
import sys
import time
from ultralytics import YOLO

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_YAML = os.path.join(PROJECT_DIR, "ai_training", "dataset", "data.yaml")
MODEL_DIR = os.path.join(PROJECT_DIR, "ai_training", "trained_models")
BEST_MODEL_PATH = os.path.join(MODEL_DIR, "smart_bin_best.pt")

def retrain(epochs=25, imgsz=640, batch=8):
    print("=" * 65)
    print("  🚀 SMART AI TRASH BIN - RETRAIN CUSTOM YOLOv8 MODEL")
    print("=" * 65)
    print(f"Dataset config: {DATA_YAML}")
    print(f"Target model output: {BEST_MODEL_PATH}")

    if not os.path.exists(DATA_YAML):
        print(f"[ERROR] ไม่พบไฟล์ {DATA_YAML}")
        return

    # เริ่มเทรนจาก Base Model หรือโมเดลเดิม
    base_model = BEST_MODEL_PATH if os.path.exists(BEST_MODEL_PATH) else "yolov8n.pt"
    print(f"\n[START TRAINING] โหลด Base Weights จาก: {base_model}")
    model = YOLO(base_model)

    print(f"กำลังเริ่มเทรน {epochs} Epochs...")
    results = model.train(
        data=DATA_YAML,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        project=os.path.join(PROJECT_DIR, "ai_training", "runs"),
        name="retrained_smart_bin",
        exist_ok=True,
        verbose=True
    )

    trained_best = os.path.join(PROJECT_DIR, "ai_training", "runs", "retrained_smart_bin", "weights", "best.pt")
    if os.path.exists(trained_best):
        import shutil
        os.makedirs(MODEL_DIR, exist_ok=True)
        shutil.copy(trained_best, BEST_MODEL_PATH)
        print("\n" + "=" * 65)
        print("  🎉 [SUCCESS] เทรนสำเร็จและอัปเดตโมเดลเรียบร้อยแล้ว!")
        print(f"  📁 โมเดลใหม่บันทึกที่: {BEST_MODEL_PATH}")
        print("  ⚡ เซิร์ฟเวอร์ Cloud AI จะนำโมเดลใหม่ไปใช้งานทันที!")
        print("=" * 65)
    else:
        print("[WARNING] ไม่พบไฟล์ weights/best.pt")

if __name__ == "__main__":
    epochs = 25
    if len(sys.argv) > 1:
        try:
            epochs = int(sys.argv[1])
        except:
            pass
    retrain(epochs=epochs)
