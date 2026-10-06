"""
YOLOv8 Nano Training Script for 4-Class Waste Sorting
=====================================================
Target Classes:
  0: General (ขยะทั่วไป - ซองขนม, กล่องโฟม, ถุงพลาสติก, ทิชชู่)
  1: Recyclable (รีไซเคิล - ขวดพลาสติกใส, ขวดแก้ว, กระป๋องอลูมิเนียม, กล่องลัง)
  2: Wet (ขยะเปียก - เศษอาหาร, เปลือกผลไม้, เศษผัก)
  3: Hazardous (ขยะอันตราย - ถ่านไฟฉาย, หลอดไฟ, กระป๋องสเปรย์, ขวดยา)

Usage:
  1. pip install ultralytics roboflow
  2. python train_yolov8.py --api_key YOUR_ROBOFLOW_API_KEY
"""

import os
import argparse
from ultralytics import YOLO

def train(api_key, workspace, project_name, version, epochs=50, imgsz=416, batch=16):
    print("==========================================================")
    print("  Starting YOLOv8n Training for Smart Waste Sorting Bin")
    print("==========================================================")
    
    data_yaml_path = "data.yaml"

    if api_key:
        try:
            from roboflow import Roboflow
            print("[1/3] Downloading dataset from Roboflow...")
            rf = Roboflow(api_key=api_key)
            project = rf.workspace(workspace).project(project_name)
            dataset = project.version(version).download("yolov8")
            data_yaml_path = f"{dataset.location}/data.yaml"
            print(f"[+] Dataset downloaded to: {dataset.location}")
        except Exception as e:
            print(f"[-] Roboflow download failed: {e}")
            print("[*] Will look for local data.yaml instead.")

    # Load YOLOv8 Nano pre-trained model
    print("\n[2/3] Initializing YOLOv8 Nano model...")
    model = YOLO("yolov8n.pt")

    # Train model
    print(f"\n[3/3] Training for {epochs} epochs on image size {imgsz}x{imgsz}...")
    results = model.train(
        data=data_yaml_path,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        name="smart_bin_yolov8n",
        device="cpu", # Automatically uses GPU if available
        augment=True, # Critical for handheld variation (Crop, Brightness, Scale)
        fliplr=0.5,
        mosaic=1.0,
    )

    print("\n==========================================================")
    print("  Training Completed Successfully!")
    print("  Best weights saved at: runs/detect/smart_bin_yolov8n/weights/best.pt")
    print("  You can deploy best.pt directly to Roboflow Hosted API!")
    print("==========================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train YOLOv8 on Waste Dataset")
    parser.add_argument("--api_key", type=str, default="", help="Roboflow API Key (optional)")
    parser.add_argument("--workspace", type=str, default="waste-sorting", help="Roboflow Workspace")
    parser.add_argument("--project", type=str, default="smart-trash-bin", help="Roboflow Project Name")
    parser.add_argument("--version", type=int, default=1, help="Roboflow Dataset Version")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    parser.add_argument("--imgsz", type=int, default=416, help="Image resolution")
    args = parser.parse_args()

    train(args.api_key, args.workspace, args.project, args.version, args.epochs, args.imgsz)
