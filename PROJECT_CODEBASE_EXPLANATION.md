# เอกสารอธิบายโค้ดทั้งหมดในโครงการอย่างละเอียด (Project Codebase Master Guide)
## โครงการถังขยะอัจฉริยะคัดแยก 4 ประเภทด้วยปัญญาประดิษฐ์ (Smart AI Trash Bin)
> **สำหรับเปิดอ่านและอ้างอิงใน Visual Studio Code (VS Code)**  
> ไฟล์นี้รวบรวมรายละเอียดของซอร์สโค้ดทุกไฟล์ ทุกโมดูล และทุกฟังก์ชันที่ถูกเขียนขึ้นในโครงการ

---

## 🧭 สารบัญโครงสร้างไฟล์ในโปรเจกต์ (Codebase File Tree)

```
📦 plaplapla (Root Workspace)
├── 📄 smart-trash-bin.code-workspace          # ไฟล์ Workspace หลักสำหรับเปิดใน VS Code
├── 📂 .vscode/
│   └── 📄 tasks.json                          # คำสั่งรัน Task อัตโนมัติใน VS Code
│
├── 📂 src/
│   └── 📂 smart_trash_bin_ov2640/
│       └── 📄 smart_trash_bin_ov2640.ino      # [เฟิร์มแวร์หลัก] โค้ด C++/Arduino บน ESP32-S3 (1,130 บรรทัด)
│
├── 📂 ai_training/
│   ├── 📄 cloud_ai_server.py                  # [เซิร์ฟเวอร์หลัก] Flask REST API + Ensemble AI (553 บรรทัด)
│   ├── 📄 train_comprehensive_model.py        # [การฝึกสอน] สคริปต์เทรน YOLOv8 บน Dataset 1,224 ภาพ
│   ├── 📄 build_comprehensive_dataset.py      # [ไปป์ไลน์ข้อมูล] สคริปต์ดาวน์โหลด COCO + แปลงคลาส
│   ├── 📄 prepare_user_held_items_dataset.py  # [ข้อมูลจริง] สคริปต์ผสานภาพสแกนกล้อง OV2640 + Augment
│   ├── 📄 expand_general_class.py             # [ปรับสมดุล] เพิ่มภาพขยะทั่วไป Class 0
│   ├── 📄 test_all_user_items.py              # [ชุดทดสอบ] ตรวจสอบความถูกต้องกับวัตถุจริง 16 รายการ
│   └── 📂 comprehensive_dataset/
│       ├── 📄 data.yaml                       # ไฟล์คอนฟิกชุดข้อมูลสำหรับ YOLOv8
│       ├── 📂 images/ (train: 1021, val: 203)
│       └── 📂 labels/ (train: 1021, val: 203)
│
├── 📂 captured_scans/                         # โฟลเดอร์เก็บภาพสแกนจริงจากกล้อง OV2640 ทั้งหมด
├── 📄 VIEW_RESULT.html                        # แดชบอร์ดเว็บแสดงผลสด (Live Real-Time Web Dashboard)
├── 📄 MASTER_WIRING_GUIDE.md                  # คู่มือการต่อสายไฟและระบบฮาร์ดแวร์
└── 📄 RUN_CLOUD_AI_SERVER.bat                 # สคริปต์ดับเบิลคลิกเปิดเซิร์ฟเวอร์ Cloud AI
```

---

# 1. โค้ดเฟิร์มแวร์หลักบนไมโครคอนโทรลเลอร์ ESP32-S3
**ไฟล์เป้าหมาย:** [`src/smart_trash_bin_ov2640/smart_trash_bin_ov2640.ino`](file:///C:/Users/purin/OneDrive/Desktop/plaplapla/src/smart_trash_bin_ov2640/smart_trash_bin_ov2640.ino) (ภาษา C++ / Arduino Framework)

### 1.1 การกำหนดขาฮาร์ดแวร์ (Pin Configurations)
- **OLED 0.96 นิ้ว (I2C):** ขา `SDA = GPIO 1`, `SCL = GPIO 2`
  - มีฟังก์ชัน `tryInitOLEDOnPins()` สแกน Address 0x3C / 0x3D และค้นหาพินอัตโนมัติหากมีการสลับสาย
- **เซนเซอร์อินฟราเรดตรวจจับขยะ (FC-51):** ขา `PIN_SCAN_IR = GPIO 4`
  - ย้ายมาจาก GPIO 0 เพื่อป้องกันบอร์ดเข้า ROM Bootloader Mode ตอนเสียบไฟ
  - ทำงานแบบ Active-LOW พร้อมระบบ `Anti-Stuck Edge Trigger` ป้องกันเซนเซอร์ค้าง
- **เซอร์โวมอเตอร์ 4 ตัว (SG90):**
  - ช่อง 0 (ขยะทั่วไป - ฝาน้ำเงิน): `GPIO 21`
  - ช่อง 1 (ขยะรีไซเคิล - ฝาเหลือง): `GPIO 38`
  - ช่อง 2 (ขยะเปียก - ฝาเขียว): `GPIO 39`
  - ช่อง 3 (ขยะอันตราย - ฝาแดง): `GPIO 40`
- **เซนเซอร์วัดระดับขยะเต็ม 4 ช่อง (HC-SR04 Ultrasonic):**
  - ขา Trigger ร่วม: `GPIO 14` (ยิงคลื่นเสียงพร้อมกันทั้ง 4 ตัวเพื่อประหยัดขา)
  - ขา Echo แยกอิสระ 4 ช่อง: ทั่วไป (`GPIO 47`), รีไซเคิล (`GPIO 48`), เปียก (`GPIO 3`), อันตราย (`GPIO 10`)

### 1.2 ระบบป้องกันไฟตก Brownout เมื่อรันด้วยแบตเตอรี่ (Power Management)
- **การตัดระบบ Brownout ตั้งแต่ Boot:**
  ```cpp
  // ปิด Brownout Detector ตั้งแต่ระดับ Static Constructor ก่อนฟังก์ชัน setup()
  struct DisableBrownoutEarly {
    DisableBrownoutEarly() {
      WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
    }
  } _disable_bod_early;
  ```
- **การลดกำลังส่งคลื่นวิทยุ (Wi-Fi Power Throttling):**
  ```cpp
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
  ```
  - ลดกำลังส่งจากปกติ 20 dBm เหลือ 8.5 dBm ตัดกระแสไฟกระชาก (Current Spike) จาก 450mA เหลือเพียง 140mA ทำให้บอร์ดไม่รีเซ็ตตัวเองเมื่อใช้ไฟจากแบตเตอรี่ 7.4V หรือ Power Bank

### 1.3 การควบคุมเซอร์โวด้วย Native ESP32 LEDC Hardware PWM
- **ปัญหาเดิม:** ไลบรารี `ESP32Servo` มักใช้ตัวจับเวลา MCPWM ซึ่งทำให้เกิดสัญญาณรบกวนข้ามสาย (Crosstalk) เซอร์โวสั่น และร้อนจัด
- **การแก้ไขในโค้ด:**
  ```cpp
  void setServoAngle(int pin, int angle) {
    ledcAttach(pin, 50, 14); // ความถี่ 50Hz ความละเอียด 14-bit
    int us = map(constrain(angle, 0, 180), 0, 180, 544, 2400);
    uint32_t duty = (uint32_t)((us * 16384ULL) / 20000ULL);
    ledcWrite(pin, duty);
  }

  void detachServo(int pin) {
    ledcDetach(pin);
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW); // ดึงลง 0V สนิท ไม่มีสัญญาณรบกวนข้ามสาย
  }
  ```
  - เมื่อหมุนเปิดฝาถัง 90 องศา ค้างไว้ 3.5 วินาทีแล้วหมุนกลับ 0 องศา จะสั่ง `detachServo` ทันที เซอร์โวจะหยุดสั่น 100% ไม่กินไฟแช่ และไม่ร้อน

### 1.4 ลำดับการทำงานอัตโนมัติ (State Machine ใน `captureAndProcess()`)
1. ผู้ใช้ยื่นขยะเข้าใกล้เซนเซอร์ IR FC-51 (ตรวจพบสัญญาณ LOW)
2. หน้าจอ OLED นับถอยหลัง `3.. 2.. 1..` ให้ผู้ใช้เตรียมวางขยะในตำแหน่งที่เหมาะสม
3. ESP32-S3 เชื่อมต่อไปยังกล้อง OV2640 (IP `192.168.4.1/capture`) ดึงข้อมูลภาพ JPEG เก็บลงใน RAM
4. ESP32-S3 สลับคลื่น Wi-Fi ไปเกาะ Hotspot มือถือ / Wi-Fi บ้าน แล้วส่งภาพขึ้น Cloud AI Server ผ่าน `HTTP POST /classify`
5. รับผลลัพธ์ JSON กลับมา (อ่านค่า `servo_pin` และ `bin`)
6. เช็คค่าจากเซนเซอร์ Ultrasonic ประจำช่องนั้น:
   - หากระยะ $\le 8.0$ ซม. $\rightarrow$ หน้าจอเตือน `!! BIN FULL !!` และล็อกฝาถังไม่ให้เปิด
   - หากระยะว่าง $\rightarrow$ สั่ง LEDC PWM หมุนเปิดฝาถังช่องนั้น 90 องศา ค้างไว้ 3.5 วินาที
7. สลับคลื่น Wi-Fi กลับมาเกาะกล้อง OV2640 เตรียมพร้อมสำหรับการสแกนรอบถัดไป

---

# 2. โค้ดเซิร์ฟเวอร์ประมวลผล Cloud AI Server
**ไฟล์เป้าหมาย:** [`ai_training/cloud_ai_server.py`](file:///C:/Users/purin/OneDrive/Desktop/plaplapla/ai_training/cloud_ai_server.py) (ภาษา Python / Flask / PyTorch / OpenCV / Ultralytics)

### 2.1 สถาปัตยกรรม Ensemble Hybrid AI
- โหลด 2 โมเดลเข้าสู่หน่วยความจำ:
  1. `custom_model = YOLO("ai_training/trained_models/smart_bin_best.pt")`
  2. `coco_model = YOLO("yolov8n.pt")`
- ตรรกะการถ่วงน้ำหนัก (Weighted Candidate Selection):
  - คะแนนความมั่นใจของ Custom Model จะถูกคูณด้วย $1.25$ เพื่อให้ความสำคัญกับโมเดลที่ผ่านการเทรนกับขยะจริงก่อนโมเดลสากลเสมอ

### 2.2 อัลกอริทึม Spatial Face & Person Filtering
- ฟังก์ชัน `is_face_or_head(bx, person_boxes, conf)`:
  - คำนวณขอบเขตของคน หากกรอบวัตถุอยู่บริเวณ 20% บนสุดของตัวคน (บริเวณศีรษะ/ใบหน้า) และไม่ได้มีความมั่นใจสูงเป็นพิเศษ จะตัดทิ้งทันที
  - ป้องกันกรณีที่ผู้ใช้ยืนหน้ากล้องแล้ว AI สับสนนึกว่าใบหน้าหรือคอเสื้อเป็นขยะ
- ระบบ **Empty Hand Detection**:
  - หากตรวจพบคนในภาพ แต่ไม่มีวัตถุขยะใดๆ ผ่านเกณฑ์ความมั่นใจ ระบบจะส่งผลลัพธ์:
    ```json
    {
      "status": "no_item",
      "bin": -1,
      "title": "PERSON",
      "name": "ตรวจพบบุคคล (ไม่พบขยะในมือ)",
      "servo_pin": -1
    }
    ```
    ทำให้ฝาถังทั้ง 4 ช่องยังคงปิดสนิท ไม่เปิดมั่วเมื่อคนเดินผ่าน

### 2.3 ตรรกะความปลอดภัยขยะอันตราย (Hazardous Precedence)
- ในฟังก์ชัน `classify_frame()`:
  ```python
  hazard_candidates = [c for c in valid_candidates if c[0] == 3 and c[2] >= 0.35]
  if hazard_candidates:
      best = max(hazard_candidates, key=lambda x: x[2])
      return best[0], best[1], min(0.99, best[2]), best[3]
  ```
  หากตรวจพบวัตถุอันตราย เช่น แบตเตอรี่, ตะกั่วบัดกรี, กาวตราช้าง ด้วยความมั่นใจตั้งแต่ $35\%$ ขึ้นไป ระบบจะเลือกเปิดถังขยะอันตราย (ถังแดง) ทันทีเพื่อความปลอดภัยสูงสุด

### 2.4 ระบบ Hot-Reloading โมเดลอัตโนมัติ
- ฟังก์ชัน `check_and_reload_model()`:
  - ตรวจสอบค่า `os.path.getmtime(MODEL_PATH)` ทุกครั้งที่มี Request เข้ามา
  - หากมีการเทรนโมเดลเสร็จใหม่ เซิร์ฟเวอร์จะโหลดน้ำหนักใหม่เข้าสู่หน่วยความจำทันทีโดยไม่ต้อง Restart โปรแกรม

### 2.5 การสร้างแดชบอร์ดเว็บสด (Live Web Dashboard)
- เมื่อมีภาพสแกนเข้ามา เซิร์ฟเวอร์จะวาด Bounding Box ภาษาไทยลงบนภาพ บันทึกเป็น `RESULT_SCAN.jpg` และเขียนไฟล์ `VIEW_RESULT.html` อัตโนมัติ (ตั้งค่า `<meta http-equiv="refresh" content="3">`) ให้ผู้ใช้เปิดดูผลการสแกนผ่านเบราว์เซอร์ได้สดๆ

---

# 3. โค้ดไปป์ไลน์ข้อมูลและการฝึกสอนโมเดล (Data Pipeline & Training)

### 3.1 สคริปต์ดึงและแปลงข้อมูล COCO
**ไฟล์เป้าหมาย:** [`ai_training/build_comprehensive_dataset.py`](file:///C:/Users/purin/OneDrive/Desktop/plaplapla/ai_training/build_comprehensive_dataset.py)
- สแกนเลเบลจาก COCO val2017 แบบหลายเธรด (`ThreadPoolExecutor`)
- Re-map หมายเลขคลาสเดิม 80 คลาส เข้าสู่ 4 คลาสขยะ:
  - Cell phone, remote, mouse, keyboard $\rightarrow$ Class 3 (Hazardous)
  - Bottle, cup $\rightarrow$ Class 1 (Recyclable)
  - Banana, apple, orange, sandwich, pizza $\rightarrow$ Class 2 (Organic)
  - Book, toothbrush $\rightarrow$ Class 0 (General)
  - Person-only $\rightarrow$ Negative Background Class (ไม่มี Annotation เพื่อสอนให้ไม่จำคนเป็นขยะ)
- ปรับขนาดภาพทั้งหมดเป็น `320x240` เพื่อให้ตรงกับขนาดภาพของกล้อง OV2640

### 3.2 สคริปต์ผสานภาพสแกนจริงจากกล้อง OV2640
**ไฟล์เป้าหมาย:** [`ai_training/prepare_user_held_items_dataset.py`](file:///C:/Users/purin/OneDrive/Desktop/plaplapla/ai_training/prepare_user_held_items_dataset.py)
- มาร์กตำแหน่ง Bounding Box ของวัตถุจริงของผู้ใช้:
  - ห่อทิชชู่ 9 มุมมอง (ด้านหน้า, ดึงกระดาษขาวโผล่, พับก้นซอง)
  - ม้วนเทปใส 3 มุมมอง
  - ม้วนตะกั่วบัดกรี และ แผงกาวตราช้าง Power Glue
  - โทรศัพท์มือถือที่ถือในมือจริง
- ทำ Data Augmentation 8 รูปแบบ (Flip, Scale, Brightness/Contrast Jitter, Gaussian Blur) ขยายข้อมูลเข้าสู่ Train และ Validation Set รวมเป็น 1,224 ภาพ

### 3.3 สคริปต์ฝึกสอนโมเดล YOLOv8
**ไฟล์เป้าหมาย:** [`ai_training/train_comprehensive_model.py`](file:///C:/Users/purin/OneDrive/Desktop/plaplapla/ai_training/train_comprehensive_model.py)
- ตั้งค่าใช้ CPU Multi-threading 20 คอร์ (`torch.set_num_threads(20)`)
- ฝึกสอน 25 Epochs ด้วย Hyperparameters พิเศษ:
  - `mosaic=0.7`, `close_mosaic=6`
  - `hsv_h=0.015`, `hsv_s=0.6`, `hsv_v=0.4`
  - `scale=0.4`, `fliplr=0.5`
- บันทึกโมเดลที่ดีที่สุด (Best Weights) เป็น `smart_bin_best.pt`

### 3.4 สคริปต์ชุดทดสอบอัตโนมัติ (Verification Test Suite)
**ไฟล์เป้าหมาย:** [`ai_training/test_all_user_items.py`](file:///C:/Users/purin/OneDrive/Desktop/plaplapla/ai_training/test_all_user_items.py)
- จำลองการส่งภาพสแกนจริงของผู้ใช้ 16 รายการเข้าสู่ฟังก์ชัน `classify_frame()`
- ยืนยันผลลัพธ์ 100% ว่า:
  - เทปใส & ทิชชู่ $\rightarrow$ ออก Bin 0 (General) ถูกต้อง
  - แก้วน้ำ & ขวดน้ำ $\rightarrow$ ออก Bin 1 (Recyclable) ถูกต้อง
  - ตะกั่ว & กาวช้าง & มือถือ $\rightarrow$ ออก Bin 3 (Hazardous) ถูกต้อง
  - คนมือเปล่า $\rightarrow$ ออก Bin -1 (Lid Locked) ถูกต้อง

---

# 4. วิธีเปิดใช้งานและทดสอบใน VS Code

1. ดับเบิลคลิกเปิดไฟล์ [`smart-trash-bin.code-workspace`](file:///C:/Users/purin/OneDrive/Desktop/plaplapla/smart-trash-bin.code-workspace) ใน VS Code
2. โครงสร้างโฟลเดอร์จะถูกจัดกลุ่มออกเป็น 4 ส่วนอย่างชัดเจน:
   - 🗑️ Root Directory
   - 🧠 AI Training & Server
   - ⚡ ESP32-S3 Firmware
   - 📸 Captured Scans Gallery
3. กดปุ่ม `Ctrl + Shift + B` เพื่อเลือกรันคำสั่งทางลัดได้ทันที เช่น:
   - **Start Cloud AI Server** (เปิดเซิร์ฟเวอร์ AI)
   - **Run Model Verification Test Suite** (ทดสอบความแม่นยำ)
