"""
Local Image Inference & AI Test Tool
====================================
This script lets you test your images locally without needing an ESP32-S3.
You can:
  1. Test against your Roboflow Hosted API.
  2. Test against the local Mock Server.
  3. Validate how the 4-class sorting logic maps each prediction to a specific bin.

Usage:
  python ai_training/test_image_inference.py --image path/to/trash.jpg --api_url https://detect.roboflow.com/...
"""

import os
import sys
import json
import argparse
import urllib.request

BIN_NAMES = {
    0: "General (ขยะทั่วไป - ฝาสีน้ำเงิน)",
    1: "Recyclable (ขยะรีไซเคิล - ฝาสีเหลือง)",
    2: "Wet / Organic (ขยะเปียก - ฝาสีเขียว)",
    3: "Hazardous (ขยะอันตราย - ฝาสีแดง)",
}

def map_label_to_bin(label: str) -> int:
    label = label.lower()
    if any(k in label for k in ["recycle", "bottle", "can", "cardboard", "plastic", "glass"]):
        return 1
    elif any(k in label for k in ["wet", "food", "organic", "fruit", "peel", "banana"]):
        return 2
    elif any(k in label for k in ["hazard", "battery", "bulb", "spray", "medicine"]):
        return 3
    else:
        return 0

def test_inference(image_path: str, api_url: str):
    if not os.path.isfile(image_path):
        print(f"[-] Image not found: {image_path}")
        return

    print(f"\n[1] Reading test image: {image_path}")
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    print(f"    Size: {len(img_bytes)} bytes")

    print(f"[2] Sending HTTP POST to AI Endpoint: {api_url}")
    req = urllib.request.Request(
        api_url,
        data=img_bytes,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            resp_body = response.read().decode("utf-8")
            data = json.loads(resp_body)
            print(f"[3] AI Cloud Response (HTTP {response.status}):")
            print(json.dumps(data, indent=2))

            preds = data.get("predictions", [])
            if preds:
                top_pred = preds[0]
                cls_name = top_pred.get("class", "unknown")
                conf = top_pred.get("confidence", 0.0)
                bin_id = map_label_to_bin(cls_name)

                print("\n=======================================================")
                print(f"  AI Prediction : '{cls_name}' (Confidence: {conf*100:.1f}%)")
                print(f"  Target Bin ID : {bin_id}")
                print(f"  Action        : สั่งเปิดฝาช่อง -> {BIN_NAMES[bin_id]}")
                print("=======================================================\n")
            else:
                print("\n[!] No objects detected with sufficient confidence.")
                print(f"    Fallback -> จัดเข้าสู่ {BIN_NAMES[0]}")
    except Exception as e:
        print(f"[-] Inference failed: {e}")
        print("    Tip: If using local mock server, make sure to run:")
        print("         python tests/mock_server/mock_api_server.py")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test trash images with AI API")
    parser.add_argument("--image", type=str, default="", help="Path to image file")
    parser.add_argument("--api_url", type=str, default="http://127.0.0.1:5000/predict", help="AI Endpoint URL")
    args = parser.parse_args()

    # If no image provided, create a dummy test image
    test_img = args.image
    if not test_img:
        sample_dir = os.path.join(os.path.dirname(__file__), "sample_images")
        os.makedirs(sample_dir, exist_ok=True)
        test_img = os.path.join(sample_dir, "sample_bottle.jpg")
        if not os.path.exists(test_img):
            # Create a simple dummy JPEG binary file for testing
            with open(test_img, "wb") as f:
                f.write(b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB\x00C\x00' + b'MOCK_BOTTLE_IMAGE_BYTES')
        print(f"[*] No --image passed. Using sample test image: {test_img}")

    test_inference(test_img, args.api_url)
