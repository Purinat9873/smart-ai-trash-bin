"""
Test Live Server Classification Prediction
"""
import requests
import json

tests = [
    ("โทรศัพท์มือถือ (ต้องเป็น HAZARD)", "captured_scans/raw_20261005_104605.jpg"),
    ("แก้วน้ำพลาสติก (ต้องเป็น RECYCLE)", "captured_scans/raw_20261005_095039.jpg")
]

for label, img_path in tests:
    with open(img_path, "rb") as f:
        data = f.read()
    r = requests.post("http://127.0.0.1:5000/classify", data=data, headers={"Content-Type": "image/jpeg"}, timeout=10)
    print(f"=== {label} ===")
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))
