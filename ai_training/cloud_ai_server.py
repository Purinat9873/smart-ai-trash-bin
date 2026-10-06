"""
Smart AI Trash Bin - Production Cloud AI Server
=================================================
เซิร์ฟเวอร์ Cloud AI ประสิทธิภาพสูงสำหรับประมวลผลจำแนกประเภทขยะ
- รองรับการเชื่อมต่อจาก ESP32-S3 ผ่านอินเทอร์เน็ต / Hotspot มือถือ / Wi-Fi
- รันโมเดล Custom YOLOv8 (smart_bin_best.pt) คัดแยก 4 ประเภทแบบแม่นยำสูง
- รองรับการ Retrain และอัปเดตโมเดลได้ตลอดเวลา
"""

import os
import sys
import time
import socket
import webbrowser
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request, jsonify, render_template_string, send_file, send_from_directory
from ultralytics import YOLO

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULT_IMG_PATH = os.path.join(PROJECT_DIR, "RESULT_SCAN.jpg")
RESULT_HTML_PATH = os.path.join(PROJECT_DIR, "VIEW_RESULT.html")
CAPTURED_DIR = os.path.join(PROJECT_DIR, "captured_scans")
os.makedirs(CAPTURED_DIR, exist_ok=True)

MODEL_PATH = os.path.join(PROJECT_DIR, "ai_training", "trained_models", "smart_bin_best.pt")
FALLBACK_MODEL = os.path.join(PROJECT_DIR, "yolov8n.pt")
FONT_PATH = "C:\\Windows\\Fonts\\tahoma.ttf"

# โครงสร้างข้อมูลถังขยะ 4 ประเภท
BINS = {
    0: {
        "title": "GENERAL",
        "name": "ขยะทั่วไป (General)",
        "color_en": "BLUE LID",
        "color_hex": "#0d6efd",
        "color_bgr": (253, 110, 13),
        "servo_pin": 21,
        "desc": "ซองขนม, กล่องโฟม, ทิชชู่, ถุงพลาสติก"
    },
    1: {
        "title": "RECYCLE",
        "name": "ขยะรีไซเคิล (Recyclable)",
        "color_en": "YELLOW LID",
        "color_hex": "#ffc107",
        "color_bgr": (7, 193, 255),
        "servo_pin": 38,
        "desc": "ขวดน้ำ PET ใส, แก้วน้ำ, กระป๋องอลูมิเนียม, กล่องกระดาษ"
    },
    2: {
        "title": "ORGANIC",
        "name": "ขยะเปียก (Organic / Food)",
        "color_en": "GREEN LID",
        "color_hex": "#198754",
        "color_bgr": (84, 135, 25),
        "servo_pin": 39,
        "desc": "เศษอาหาร, เปลือกผลไม้, เศษผัก, ขนมปัง"
    },
    3: {
        "title": "HAZARD!",
        "name": "ขยะอันตราย (Hazardous / E-Waste)",
        "color_en": "RED LID",
        "color_hex": "#dc3545",
        "color_bgr": (69, 53, 220),
        "servo_pin": 40,
        "desc": "โทรศัพท์มือถือ, แบตเตอรี่, ถ่านไฟฉาย, อุปกรณ์อิเล็กทรอนิกส์, หลอดไฟ"
    }
}

CLASS_NAME_MAP = {
    0: "ขยะทั่วไป / ซองขนม (General)",
    1: "ขวดน้ำ / กระป๋องรีไซเคิล (Recyclable)",
    2: "เศษอาหาร / ผลไม้ (Organic)",
    3: "โทรศัพท์มือถือ / แบตเตอรี่ / ขยะอันตราย (Hazardous)"
}

print("[INIT] กำลังโหลดโมเดล Custom YOLOv8...")
custom_model = YOLO(MODEL_PATH)
coco_model = YOLO(FALLBACK_MODEL)
last_model_mtime = os.path.getmtime(MODEL_PATH) if os.path.exists(MODEL_PATH) else 0
print("[INIT OK] โหลดโมเดลจำแนกขยะ 4 คลาสสำเร็จ!")

def check_and_reload_model():
    """ตรวจสอบไฟล์โมเดล หากมีการอัปเดตใหม่จากการเทรน จะโหลดเวอร์ชันใหม่โดยอัตโนมัติทันที"""
    global custom_model, last_model_mtime
    try:
        if os.path.exists(MODEL_PATH):
            mtime = os.path.getmtime(MODEL_PATH)
            if mtime > last_model_mtime:
                print(f"\n🔄 [AUTO-RELOAD] พบโมเดลใหม่ ({MODEL_PATH}) กำลังอัปเดตน้ำหนัก...")
                custom_model = YOLO(MODEL_PATH)
                last_model_mtime = mtime
                print("✅ [AUTO-RELOAD OK] อัปเดตโมเดลเวอร์ชันล่าสุดเข้าสู่ระบบเรียบร้อย!\n")
    except Exception as e:
        print(f"[WARN] ไม่สามารถโหลดโมเดลใหม่: {e}")

app = Flask(__name__)
scan_history = []

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def draw_thai_text(img, text, position, font_size=20, color=(255, 255, 255), bg_color=None):
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except:
        font = ImageFont.load_default()

    if bg_color is not None:
        bbox = draw.textbbox(position, text, font=font)
        pad = 4
        padded_bbox = (bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad)
        draw.rectangle(padded_bbox, fill=bg_color)

    draw.text(position, text, font=font, fill=color)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

def is_person_box(bx, frame_shape, person_boxes):
    """ตรวจว่ากรอบนี้เป็นตัวคน/เสื้อผ้า (ไม่ใช่ขยะ) หรือไม่"""
    h, w = frame_shape[:2]
    bx_w = bx[2] - bx[0]
    bx_h = bx[3] - bx[1]
    bx_area = bx_w * bx_h
    frame_area = w * h

    # 1. กรอบครอบคลุมพื้นที่มากกว่า 60% ของภาพทั้งหมด มักเป็นตัวคนหรือพื้นหลัง
    if bx_area > 0.60 * frame_area:
        return True

    # 2. ตรวจสอบการทับซ้อนกับกรอบ Person ของ COCO
    for p in person_boxes:
        ix1 = max(bx[0], p[0])
        iy1 = max(bx[1], p[1])
        ix2 = min(bx[2], p[2])
        iy2 = min(bx[3], p[3])
        if ix2 > ix1 and iy2 > iy1:
            inter = (ix2 - ix1) * (iy2 - iy1)
            # ถ้ารูปทรงกลืนไปกับตัวคนเกิน 70% และเริ่มจากด้านบน (ศีรษะ/ใบหน้า)
            if inter / bx_area > 0.70 and bx[1] < 60 and bx_h > 130:
                return True
    return False

def is_face_or_head(bx, person_boxes, conf=0.0):
    """ตรวจว่ากรอบนี้เป็นส่วนใบหน้า/ศีรษะคนเปล่าๆ หรือไม่
    - หาก AI มีความมั่นใจว่าเป็นขยะจริง (conf >= 0.35) จะไม่นับเป็นหน้า
    - ป้องกันการตัดวัตถุที่ผู้ใช้ถือหน้าอกหรือใต้คางทิ้งโดยเด็ดขาด
    """
    if conf >= 0.35:
        return False

    bx_cy = (bx[1] + bx[3]) / 2.0
    bx_cx = (bx[0] + bx[2]) / 2.0

    for p in person_boxes:
        p_h = p[3] - p[1]
        # บริเวณหน้าผาก/ศีรษะ คือ 20% บนสุดของตัวคนเท่านั้น
        head_bottom = p[1] + int(p_h * 0.20)
        
        # วัตถุจะถือว่าเป็นศีรษะคน ก็ต่อเมื่อกรอบทั้งหมดอยู่บนหัวคนและไม่ยื่นลงมา
        if p[0] <= bx_cx <= p[2] and bx_cy <= head_bottom and bx[3] <= p[1] + int(p_h * 0.28):
            return True
    return False

def trim_box_away_from_face(bx, person_boxes):
    """หากกรอบวัตถุยื่นขึ้นไปโดนใบหน้าคน ให้ตัดส่วนบนออกเพื่อโฟกัสที่มือและตัววัตถุ"""
    for p in person_boxes:
        p_h = p[3] - p[1]
        face_bottom = p[1] + int(p_h * 0.30)
        if bx[1] < face_bottom and bx[3] > face_bottom + 30:
            bx[1] = max(face_bottom, bx[1] + int((face_bottom - bx[1]) * 0.7))
    return bx

def classify_frame(frame):
    """วิเคราะห์จำแนกขยะ 4 คลาสด้วย Ensemble AI (Custom YOLOv8 + COCO Master Model)
    Class 0: ขยะทั่วไป (General) - ซองขนม, ทิชชู่, เทปกาว, โฟม, ถุงพลาสติก
    Class 1: ขยะรีไซเคิล (Recyclable) - แก้วน้ำ, ขวดน้ำ, กระป๋อง, กล่องกระดาษ
    Class 2: ขยะเปียก (Organic) - เศษอาหาร, เปลือกผลไม้, เศษผัก
    Class 3: ขยะอันตราย (Hazardous) - โทรศัพท์มือถือ, แบตเตอรี่, ตะกั่วบัดกรี, กาวช้าง, สารเคมี
    """
    
    # 1. รัน COCO Model หาคน และจับวัตถุมาตรฐาน COCO
    r_coco = coco_model.predict(frame, conf=0.18, verbose=False)[0]
    person_boxes = []
    coco_candidates = []
    
    for b in r_coco.boxes:
        cname = coco_model.names[int(b.cls[0].item())].lower()
        conf = float(b.conf[0].item())
        bx = b.xyxy[0].cpu().numpy().astype(int)

        if cname == "person":
            person_boxes.append(bx)
        elif cname in ["bottle", "cup", "wine glass", "can"]:
            coco_candidates.append((1, "แก้วน้ำ / ขวดน้ำ / กระป๋องรีไซเคิล (Recyclable)", conf, bx))
        elif cname in ["banana", "apple", "orange", "sandwich", "pizza", "donut", "cake", "carrot", "broccoli"]:
            if conf >= 0.40: # ขยะเปียกจาก COCO ต้องมีความมั่นใจสูง ไม่เอาผลมั่วจากม้วนเทป/ทิชชู่ (cake 0.26)
                coco_candidates.append((2, "เศษอาหาร / ผลไม้ (Organic)", conf, bx))
        elif cname in ["cell phone", "remote", "mouse", "keyboard", "laptop"]:
            coco_candidates.append((3, "โทรศัพท์มือถือ / ขยะอิเล็กทรอนิกส์ (Hazardous)", conf * 1.15, bx))
        elif cname in ["frisbee", "bowl"]:
            # ม้วนเทป, บรรจุภัณฑ์กลม, จานโฟม
            coco_candidates.append((0, "ม้วนเทป / บรรจุภัณฑ์ทั่วไป (General)", conf, bx))
        elif cname in ["book", "toothbrush", "hair drier"]:
            coco_candidates.append((0, "ของใช้ / ทิชชู่ / ขยะทั่วไป (General)", conf, bx))

    # 2. รัน Custom YOLOv8 ที่เทรนตรงกับขยะจริงและภาพของผู้ใช้
    custom_candidates = []
    r_custom = custom_model.predict(frame, conf=0.18, verbose=False)[0]
    for b in r_custom.boxes:
        cls_id = int(b.cls[0].item())
        conf = float(b.conf[0].item())
        bx = b.xyxy[0].cpu().numpy().astype(int)

        # ตัดกรอบที่อยู่บนศีรษะคนเปล่าๆ ออก
        if is_face_or_head(bx, person_boxes, conf=conf):
            continue

        # โมเดล Custom ให้ความมั่นใจ x1.25 เพื่อให้นำหน้าโมเดลสากลเสมอ
        c_weight = conf * 1.25

        if cls_id == 0:
            custom_candidates.append((0, "ขยะทั่วไป / ซองขนม / ทิชชู่ / เทป (General)", c_weight, bx))
        elif cls_id == 1:
            custom_candidates.append((1, "แก้วน้ำ / ขวดน้ำ / รีไซเคิล (Recyclable)", c_weight, bx))
        elif cls_id == 2:
            custom_candidates.append((2, "เศษอาหาร / ผลไม้ (Organic)", c_weight, bx))
        elif cls_id == 3:
            custom_candidates.append((3, "ขยะอันตราย / โทรศัพท์ / กาว / ตะกั่ว (Hazardous)", c_weight, bx))

    # รวม Candidates โดยกรองหน้าคนออก
    all_candidates = custom_candidates + coco_candidates
    valid_candidates = [c for c in all_candidates if not is_face_or_head(c[3], person_boxes, conf=c[2])]

    if valid_candidates:
        # 1. ขยะอันตราย (Hazardous): ป้องกันอันตรายสูงสุด ถ้ามีความมั่นใจ >= 0.35
        hazard_candidates = [c for c in valid_candidates if c[0] == 3 and c[2] >= 0.35]
        if hazard_candidates:
            best = max(hazard_candidates, key=lambda x: x[2])
            return best[0], best[1], min(0.99, best[2]), best[3]

        # 2. เลือกผลลัพธ์ที่มีคะแนนความมั่นใจสูงสุด
        best = max(valid_candidates, key=lambda x: x[2])
        return best[0], best[1], min(0.99, best[2]), best[3]

    # หากตรวจพบคนในภาพ แต่ไม่มีขยะในมือ -> แสดงบุคคล และไม่เปิดฝาถัง
    if person_boxes:
        return -1, "ตรวจพบบุคคล (กรุณายื่นขยะหน้ากล้อง)", 0.85, person_boxes[0]

    # กรณีไม่มีคน และไม่พบวัตถุใดๆ -> ไม่เปิดฝาถัง
    return -1, "ไม่พบวัตถุขยะในภาพ (No Trash Detected)", 0.0, np.array([40, 40, frame.shape[1]-40, frame.shape[0]-40])

def get_recent_scans(limit=16):
    if not os.path.exists(CAPTURED_DIR):
        return []
    files = [f for f in os.listdir(CAPTURED_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    files.sort(key=lambda x: os.path.getmtime(os.path.join(CAPTURED_DIR, x)), reverse=True)
    return files[:limit]

@app.route("/", methods=["GET"])
def index():
    local_ip = get_local_ip()
    recent_files = get_recent_scans(16)
    gallery_html = ""
    for fname in recent_files:
        gallery_html += f"""
        <div style="background:#1e293b; border-radius:10px; overflow:hidden; border:1px solid #475569; text-align:center;">
            <a href="/scans/{fname}" target="_blank">
                <img src="/scans/{fname}" style="width:100%; height:130px; object-fit:cover; display:block;" alt="{fname}">
            </a>
            <div style="padding:8px; font-size:12px; color:#cbd5e1; word-break:break-all;">{fname}</div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>Smart AI Trash Bin - Cloud AI Dashboard</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
        .container {{ max-width: 1040px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        h1 {{ color: #38bdf8; display: flex; align-items: center; justify-content: space-between; margin-top: 0; }}
        .badge {{ background: #16a34a; color: white; padding: 4px 14px; border-radius: 20px; font-size: 14px; }}
        .code-box {{ background: #020617; padding: 14px; border-radius: 8px; font-family: Consolas, monospace; color: #4ade80; margin: 14px 0; border: 1px solid #334155; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }}
        .card {{ background: #334155; border-radius: 12px; padding: 18px; }}
        .img-box img {{ width: 100%; height: auto; border-radius: 8px; border: 2px solid #475569; }}
        .gallery-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; margin-top: 14px; }}
        .btn {{ display: inline-block; background: #0284c7; color: white; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>
            <span>🌐 SMART AI TRASH BIN - CLOUD SERVER</span>
            <span class="badge">● ONLINE</span>
        </h1>
        <p>เซิร์ฟเวอร์ Cloud AI สำหรับประมวลผลจำแนกขยะ 4 ประเภทแบบเรียลไทม์</p>
        <div class="code-box">
            <b>📡 ที่อยู่สำหรับตั้งค่าในโค้ด ESP32-S3:</b><br/>
            URL: <span style="color:#38bdf8; font-size:16px;">http://{local_ip}:5000/classify</span>
        </div>
        
        <div class="grid">
            <div class="img-box">
                <h3>📸 ภาพถ่ายการสแกนล่าสุด (Latest Scan)</h3>
                <img src="/latest_image?t={int(time.time()*1000)}" alt="Latest AI Scan">
            </div>
            <div class="card">
                <h2>📊 สถานะการทำงาน</h2>
                <p>จำนวนครั้งที่สแกนแล้ว: <b>{len(scan_history)}</b> ครั้ง</p>
                <p>จำนวนภาพในประวัติ: <b>{len(recent_files)}</b> ภาพ</p>
                <p>โมเดล AI ที่ใช้งาน: <b>Custom YOLOv8 (smart_bin_best.pt)</b></p>
                <p>รองรับการส่งภาพผ่าน: <code>POST /classify</code></p>
                <hr style="border-color:#475569; margin: 16px 0;"/>
                <p>💡 <b>ทริค:</b> ทุกภาพที่ถ่ายจะถูกบันทึกเก็บไว้ในโฟลเดอร์ <code>captured_scans</code> โดยอัตโนมัติ</p>
            </div>
        </div>

        <div style="margin-top: 32px; background: #0f172a; padding: 20px; border-radius: 12px; border: 1px solid #334155;">
            <h2 style="margin-top:0; color:#38bdf8;">🗂️ ประวัติภาพถ่ายที่สแกนทั้งหมด (Captured Scans Gallery)</h2>
            <p style="color:#94a3b8; font-size:14px;">คลิกที่ภาพเพื่อดูขนาดเต็มความละเอียดสูง</p>
            <div class="gallery-grid">
                {gallery_html if gallery_html else '<p style="color:#64748b;">ยังไม่มีภาพที่บันทึก</p>'}
            </div>
        </div>
    </div>
</body>
</html>"""

@app.route("/latest_image", methods=["GET"])
def latest_image():
    if os.path.exists(RESULT_IMG_PATH):
        return send_file(RESULT_IMG_PATH, mimetype="image/jpeg")
    return "No image", 404

@app.route("/scans/<path:filename>", methods=["GET"])
def get_scan(filename):
    return send_from_directory(CAPTURED_DIR, filename)

@app.route("/classify", methods=["POST"])
def classify():
    """Endpoint สำหรับรับข้อมูลภาพ JPEG จาก ESP32-S3 ผ่าน HTTP POST"""
    check_and_reload_model()
    t0 = time.time()
    img_bytes = request.get_data()

    if not img_bytes or len(img_bytes) < 500:
        return jsonify({"status": "error", "message": "Invalid or empty image data"}), 400

    nparr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if frame is None:
        return jsonify({"status": "error", "message": "Failed to decode JPEG"}), 400

    raw_frame = frame.copy()

    # ประมวลผลด้วยโมเดล YOLOv8
    detected_bin, best_label, best_conf, bx = classify_frame(frame)
    if detected_bin == -1:
        if "บุคคล" in best_label:
            bin_info = {
                "title": "PERSON",
                "name": "ตรวจพบบุคคล (ไม่พบขยะในมือ)",
                "color_en": "NO ACTION",
                "color_hex": "#f59e0b",
                "color_bgr": (11, 158, 245),
                "servo_pin": -1,
                "desc": "ตรวจพบเฉพาะบุคคล ไม่พบวัตถุขยะในมือ กรุณายื่นขยะเข้าใกล้กล้องเพื่อแยกทิ้ง"
            }
        else:
            bin_info = {
                "title": "NO_ITEM",
                "name": "ไม่พบวัตถุขยะ (No Trash Detected)",
                "color_en": "NO ACTION",
                "color_hex": "#64748b",
                "color_bgr": (139, 116, 100),
                "servo_pin": -1,
                "desc": "ไม่พบวัตถุขยะในภาพ กรุณานำขยะมาจ่อที่หน้ากล้องระยะ 15-25 ซม."
            }
    else:
        bin_info = BINS[detected_bin]
    inf_time_ms = (time.time() - t0) * 1000

    # วาดกรอบและป้ายภาษาไทย
    color = bin_info["color_bgr"]
    cv2.rectangle(frame, (bx[0], bx[1]), (bx[2], bx[3]), color, 3)
    label_txt = f"{best_label} ({best_conf*100:.1f}%)"
    frame = draw_thai_text(frame, label_txt, (bx[0], max(10, bx[1] - 30)), font_size=18, color=(255,255,255), bg_color=(color[2], color[1], color[0]))

    if detected_bin == -1:
        banner_txt = f"CLOUD AI | {bin_info['name']}"
    else:
        banner_txt = f"CLOUD AI | {bin_info['name']} | เซอร์โว GPIO {bin_info['servo_pin']}"
    frame = draw_thai_text(frame, banner_txt, (12, 12), font_size=18, color=(255,255,255), bg_color=(20, 20, 20))
    cv2.imwrite(RESULT_IMG_PATH, frame)

    # บันทึกภาพลงในโฟลเดอร์ประวัติการสแกน (captured_scans)
    timestamp_str = time.strftime('%Y%m%d_%H%M%S')
    history_filename = f"scan_{timestamp_str}_{bin_info['title']}.jpg"
    history_filepath = os.path.join(CAPTURED_DIR, history_filename)
    cv2.imwrite(history_filepath, frame)
    cv2.imwrite(os.path.join(CAPTURED_DIR, f"raw_{timestamp_str}.jpg"), raw_frame)

    # อัปเดตไปยัง artifact directory เพื่อให้เปิดดูภาพสดในระบบได้ทันที
    artifact_img = r"C:\Users\purin\.gemini\antigravity-cli\brain\4b99c193-882c-451b-b67f-1c7e4e5403d2\latest_scan.jpg"
    try:
        cv2.imwrite(artifact_img, frame)
    except:
        pass

    # อัปเดตไฟล์ VIEW_RESULT.html เพื่อให้หน้าเว็บบนคอมพิวเตอร์แสดงผลสดๆ ทันที
    try:
        t_now_str = time.strftime('%H:%M:%S')
        recent_scans = get_recent_scans(12)
        gallery_items = "".join([f'<div style="background:#1e293b; border-radius:8px; overflow:hidden; border:1px solid #475569;"><a href="captured_scans/{f}" target="_blank"><img src="captured_scans/{f}" style="width:100%; height:120px; object-fit:cover; display:block;" alt="{f}"></a><div style="padding:6px; font-size:11px; color:#cbd5e1; word-break:break-all;">{f}</div></div>' for f in recent_scans])

        html_content = f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="3">
    <title>Smart AI Trash Bin - ผลการสแกนสด (Cloud AI)</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
        .container {{ max-width: 1040px; margin: 0 auto; background: #1e293b; border-radius: 16px; padding: 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
        h1 {{ margin-top: 0; color: #38bdf8; display: flex; align-items: center; justify-content: space-between; font-size: 26px; }}
        .badge {{ background: #16a34a; color: white; padding: 4px 12px; border-radius: 20px; font-size: 14px; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 20px; }}
        .card {{ background: #334155; border-radius: 12px; padding: 20px; border-left: 8px solid {bin_info['color_hex']}; }}
        .card h2 {{ margin: 0 0 12px 0; font-size: 18px; color: #94a3b8; }}
        .result-title {{ font-size: 30px; font-weight: bold; color: {bin_info['color_hex']}; margin-bottom: 12px; }}
        .spec-item {{ margin: 10px 0; font-size: 15px; display: flex; justify-content: space-between; border-bottom: 1px solid #475569; padding-bottom: 6px; }}
        .spec-label {{ color: #94a3b8; }}
        .spec-val {{ font-weight: bold; color: #f1f5f9; }}
        .img-box {{ border-radius: 12px; overflow: hidden; border: 2px solid #475569; background: #020617; text-align: center; }}
        .img-box img {{ width: 100%; height: auto; display: block; }}
        .status-pill {{ display: inline-block; background: #22c55e; color: #022c22; font-weight: bold; padding: 6px 14px; border-radius: 20px; font-size: 13px; }}
        .desc-box {{ background: #0f172a; padding: 12px; border-radius: 8px; margin-top: 14px; font-size: 14px; color: #cbd5e1; }}
        .gallery-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; margin-top: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>
            <span>🗑️ SMART AI TRASH BIN - CLOUD AI LIVE</span>
            <span class="badge">● เชื่อมต่อไร้สายสำเร็จ</span>
        </h1>
        
        <div class="grid">
            <div class="img-box">
                <img src="RESULT_SCAN.jpg?t={int(time.time()*1000)}" alt="OV2640 Camera Capture">
            </div>

            <div>
                <div class="card">
                    <h2>ผลการจำแนกประเภทขยะ (YOLOv8 Cloud Model)</h2>
                    <div class="result-title">{bin_info['name']}</div>
                    <div class="spec-item"><span class="spec-label">วิธีการประมวลผล:</span><span class="spec-val" style="color:#38bdf8;">Cloud AI (HTTP POST)</span></div>
                    <div class="spec-item"><span class="spec-label">วัตถุที่ตรวจพบ:</span><span class="spec-val">{best_label}</span></div>
                    <div class="spec-item"><span class="spec-label">ระดับความมั่นใจ:</span><span class="spec-val" style="color:#4ade80;">{best_conf*100:.1f}%</span></div>
                    <div class="spec-item"><span class="spec-label">สีฝาถัง:</span><span class="spec-val">{bin_info['color_en']}</span></div>
                    <div class="spec-item"><span class="spec-label">เซอร์โวเป้าหมาย:</span><span class="spec-val" style="color:#38bdf8;">GPIO {bin_info['servo_pin']}</span></div>
                    <div class="spec-item"><span class="spec-label">เวลาประมวลผล:</span><span class="spec-val">{inf_time_ms:.1f} ms</span></div>
                    <div class="desc-box">💡 <b>คำแนะนำ:</b> {bin_info['desc']}</div>
                </div>

                <div style="margin-top: 16px; display: flex; align-items: center; justify-content: space-between;">
                    <span class="status-pill">● สแกนครั้งที่ {len(scan_history) + 1}</span>
                    <span style="font-size: 13px; color: #94a3b8;">อัปเดตล่าสุด: {t_now_str}</span>
                </div>
            </div>
        </div>

        <div style="margin-top: 28px; background: #0f172a; padding: 18px; border-radius: 12px; border: 1px solid #334155;">
            <h3 style="margin-top:0; color:#38bdf8;">🗂️ ประวัติภาพถ่ายการสแกนทั้งหมด (Captured Scans Gallery)</h3>
            <div class="gallery-grid">
                {gallery_items if gallery_items else '<p style="color:#64748b;">ยังไม่มีประวัติภาพถ่าย</p>'}
            </div>
        </div>
    </div>
</body>
</html>"""
        with open(RESULT_HTML_PATH, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        print(f"[WARN] ไม่สามารถอัปเดต VIEW_RESULT.html: {e}")

    if detected_bin == -1:
        result = {
            "status": "no_item",
            "bin": -1,
            "title": bin_info["title"],
            "name": bin_info["name"],
            "color": bin_info["color_en"],
            "servo_pin": -1,
            "conf": round(best_conf * 100, 1),
            "object": best_label,
            "inference_ms": round(inf_time_ms, 1),
            "message": "ตรวจพบบุคคล ไม่พบวัตถุขยะในมือ กรุณายื่นวัตถุขยะหน้ากล้อง"
        }
    else:
        result = {
            "status": "success",
            "bin": detected_bin,
            "title": bin_info["title"],
            "name": bin_info["name"],
            "color": bin_info["color_en"],
            "servo_pin": bin_info["servo_pin"],
            "conf": round(best_conf * 100, 1),
            "object": best_label,
            "inference_ms": round(inf_time_ms, 1)
        }

    scan_history.append(result)
    print(f"\n⚡ [CLOUD AI REQUEST] ได้รับภาพ ({len(img_bytes)} bytes)")
    if detected_bin == -1:
        print(f"   👤 [PERSON DETECTED] ตรวจพบบุคคล แต่ไม่พบวัตถุขยะในมือ -> ล็อกฝาถังขยะ!")
    else:
        print(f"   ➔ จำแนกสำเร็จ: {bin_info['name']} ({best_conf*100:.1f}%) ใน {inf_time_ms:.1f} ms")
        print(f"   ➔ สั่งเปิดถังช่อง: {detected_bin + 1} (GPIO {bin_info['servo_pin']})")
    print(f"   ➔ อัปเดตหน้าเว็บ VIEW_RESULT.html เรียบร้อย!")

    return jsonify(result)

def main():
    local_ip = get_local_ip()
    port = 5000
    print("=" * 70)
    print("  🌐 SMART AI TRASH BIN - PRODUCTION CLOUD AI SERVER")
    print("=" * 70)
    print(f"  ● เซิร์ฟเวอร์ทำงานที่: http://{local_ip}:{port}")
    print(f"  ● Endpoint สำหรับ ESP32-S3: http://{local_ip}:{port}/classify")
    print(f"  ● ดูผลลัพธ์ผ่านเว็บเบราว์เซอร์: http://localhost:{port}")
    print("=" * 70 + "\n")

    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    main()
