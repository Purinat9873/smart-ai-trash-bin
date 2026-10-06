import cv2
import os
import sys
import time
from ultralytics import YOLO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ai_training.scan_and_actuate import classify_frame, MODEL_PATH, FALLBACK_MODEL, BINS, draw_thai_text, send_esp32_command

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULT_IMG_PATH = os.path.join(PROJECT_DIR, "RESULT_SCAN.jpg")
RESULT_HTML_PATH = os.path.join(PROJECT_DIR, "VIEW_RESULT.html")

custom_model = YOLO(MODEL_PATH)
coco_model = YOLO(FALLBACK_MODEL)
frame = cv2.imread(RESULT_IMG_PATH)
bin_id, label, conf, bx = classify_frame(frame, custom_model, coco_model)

color = BINS[bin_id]["color_bgr"]
cv2.rectangle(frame, (bx[0], bx[1]), (bx[2], bx[3]), color, 3)
label_txt = f"{label} ({conf*100:.1f}%) -> {BINS[bin_id]['name']}"
frame = draw_thai_text(frame, label_txt, (bx[0], max(10, bx[1] - 32)), font_size=20, color=(255,255,255), bg_color=(color[2], color[1], color[0]))

bin_info = BINS[bin_id]
banner_txt = f"ผลลัพธ์: {bin_info['name']} | สั่งงาน: {bin_info['servo']}"
frame = draw_thai_text(frame, banner_txt, (30, 30), font_size=24, color=(255,255,255), bg_color=(20, 20, 20))
cv2.imwrite(RESULT_IMG_PATH, frame)

esp_response = send_esp32_command("COM6", bin_id)

html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>Smart AI Trash Bin - ผลการจำแนกขยะและควบคุมฮาร์ดแวร์</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
        .container {{ max-width: 960px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        h1 {{ margin-top: 0; color: #38bdf8; display: flex; align-items: center; gap: 12px; font-size: 26px; }}
        .badge {{ background: #0369a1; color: white; padding: 4px 12px; border-radius: 20px; font-size: 14px; font-weight: normal; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 20px; }}
        .card {{ background: #334155; border-radius: 12px; padding: 20px; border-left: 6px solid {bin_info['color_hex']}; }}
        .card h2 {{ margin: 0 0 12px 0; font-size: 18px; color: #94a3b8; }}
        .result-title {{ font-size: 28px; font-weight: bold; color: {bin_info['color_hex']}; margin-bottom: 8px; }}
        .spec-item {{ margin: 8px 0; font-size: 15px; display: flex; justify-content: space-between; border-bottom: 1px solid #475569; padding-bottom: 6px; }}
        .spec-label {{ color: #94a3b8; }}
        .spec-val {{ font-weight: bold; color: #f1f5f9; }}
        .img-box {{ border-radius: 12px; overflow: hidden; border: 2px solid #475569; text-align: center; }}
        .img-box img {{ width: 100%; height: auto; display: block; }}
        .btn {{ display: inline-block; background: #0284c7; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 20px; cursor: pointer; border: none; }}
        .btn:hover {{ background: #0369a1; }}
        .log-box {{ background: #020617; color: #4ade80; padding: 12px; border-radius: 8px; font-family: Consolas, monospace; font-size: 13px; margin-top: 12px; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🗑️ Smart AI Trash Bin <span class="badge">ระบบจำแนกและควบคุมฮาร์ดแวร์</span></h1>
        
        <div class="grid">
            <div class="img-box">
                <img src="RESULT_SCAN.jpg?t={int(time.time())}" alt="Camera Capture">
            </div>

            <div>
                <div class="card">
                    <h2>ผลการจำแนกประเภทขยะ (AI Result)</h2>
                    <div class="result-title">{bin_info['name']}</div>
                    <div class="spec-item"><span class="spec-label">วัตถุที่ตรวจพบ:</span><span class="spec-val">{label}</span></div>
                    <div class="spec-item"><span class="spec-label">ระดับความมั่นใจ:</span><span class="spec-val">{conf*100:.1f}%</span></div>
                    <div class="spec-item"><span class="spec-label">สีถังประจำช่อง:</span><span class="spec-val">{bin_info['color_en']}</span></div>
                    <div class="spec-item"><span class="spec-label">คำสั่งมอเตอร์เซอร์โว:</span><span class="spec-val" style="color:#38bdf8;">{bin_info['servo']}</span></div>
                    <div class="spec-item"><span class="spec-label">คำอธิบาย:</span><span class="spec-val">{bin_info['desc']}</span></div>
                </div>

                <div class="card" style="margin-top: 16px; border-left-color: #38bdf8;">
                    <h2>สถานะการสั่งงานบอร์ด ESP32-S3 (COM6)</h2>
                    <div class="log-box">{esp_response}</div>
                </div>

                <button class="btn" onclick="location.reload();">🔄 รีเฟรชผลลัพธ์</button>
            </div>
        </div>
    </div>
</body>
</html>"""

with open(RESULT_HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"DONE: {label} ({conf*100:.1f}%) -> {bin_info['name']}")
