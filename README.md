# 🤖 ถังขยะอัจฉริยะคัดแยก 4 ประเภทด้วยระบบปัญญาประดิษฐ์ (Smart AI Trash Bin)
### สถาปัตยกรรมระบบสมบูรณ์แบบ: ESP32-S3 + Custom YOLOv8 + Dual-Hop Wireless + Native LEDC PWM + Real-Time Web Dashboard

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-orange.svg)](https://docs.ultralytics.com/)
[![ESP32-S3](https://img.shields.io/badge/Hardware-ESP32--S3-red.svg)](https://www.espressif.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📌 สารบัญ (Table of Contents)
1. [ภาพรวมของโปรเจกต์ (Project Overview)](#-ภาพรวมของโปรเจกต์)
2. [สถาปัตยกรรมระบบ (System Architecture)](#-สถาปัตยกรรมระบบ)
3. [โครงสร้างไดเรกทอรีโปรเจกต์ (Project Structure)](#-โครงสร้างไดเรกทอรีโปรเจกต์)
4. [ตารางผังการต่อขา GPIO (Safe Pinout Table)](#-ตารางผังการต่อขา-gpio)
5. [ระบบปัญญาประดิษฐ์และชุดข้อมูล (AI & Dataset)](#-ระบบปัญญาประดิษฐ์และชุดข้อมูล)
6. [การเริ่มต้นใช้งานจริง (Getting Started)](#-การเริ่มต้นใช้งานจริง)
7. [เอกสารคู่มือและเครื่องมือ (Documentation & Tools)](#-เอกสารคู่มือและเครื่องมือ)

---

## 🌟 ภาพรวมของโปรเจกต์

โปรเจกต์นี้เป็นการผสานเทคโนโลยี **AI Computer Vision (Custom YOLOv8 Nano)** เข้ากับ **Embedded IoT (ESP32-S3 + OV2640)** เพื่อสร้างระบบถังขยะคัดแยกอัตโนมัติ 4 ประเภทตามมาตรฐานสิ่งแวดล้อมสากล:
1. **ทั่วไป (General - ฝาสีน้ำเงิน):** ซองขนม, กล่องโฟม, ถุงพลาสติก, ทิชชู่, ม้วนเทปใส (ควบคุมด้วยเซอร์โว GPIO 21)
2. **รีไซเคิล (Recyclable - ฝาสีเหลือง):** ขวดน้ำดื่ม PET ใส, แก้วน้ำพลาสติก, กระป๋องอลูมิเนียม, กล่องกระดาษ (ควบคุมด้วยเซอร์โว GPIO 38)
3. **เปียก (Organic / Food - ฝาสีเขียว):** เศษอาหาร, เปลือกผลไม้, พืชผัก (ควบคุมด้วยเซอร์โว GPIO 39)
4. **อันตราย (Hazardous / E-Waste - ฝาสีแดง):** โทรศัพท์มือถือ, แบตเตอรี่, ม้วนตะกั่วบัดกรี, แผงกาวตราช้าง, หลอดไฟ (ควบคุมด้วยเซอร์โว GPIO 40)

### จุดเด่นเชิงวิศวกรรมและนวัตกรรม:
* **สถาปัตยกรรม Dual-Hop Wireless:** บอร์ด ESP32-S3 ดึงภาพจากกล้อง OV2640 ผ่าน Wi-Fi วงปิด แล้วสลับคลื่นความถี่ส่งต่อขึ้น Cloud AI Server ผ่าน Hotspot/Wi-Fi โดยถังขยะทำงานแบบไร้สาย 100%
* **ระบบตัดไฟตก Brownout (8.5 dBm):** หรี่กำลังส่งเสาอากาศ Wi-Fi ลดกระแสกระชากจาก 450mA เหลือ 140mA บอร์ดทำงานนิ่งสนิทบนแบตเตอรี่ 7.4V
* **Native ESP32 LEDC PWM Servo Control:** ควบคุมเซอร์โวมอเตอร์ด้วย Hardware PWM ความถี่ 50Hz ความละเอียด 14-bit และสั่ง `ledcDetach` ทันทีที่ปิดฝาเสร็จ ป้องกันมอเตอร์สั่น ไม่ร้อน และไม่กินไฟแช่
* **Spatial Face & Empty Hand Guardrail:** กรองพื้นที่ส่วนศีรษะคนออก (Upper 20% Head Threshold) ไม่เปิดฝามั่วเมื่อคนเดินผ่าน และล็อกฝาหากไม่พบขยะในมือ
* **4x Ultrasonic Full-Bin Protection:** ตรวจวัดระดับความจุขยะทั้ง 4 ช่อง หากระยะผิวขยะ $\le 8.0$ ซม. หน้าจอ OLED จะขึ้นเตือน `!! BIN FULL !!` และสั่งล็อกฝาถังไม่ให้เปิด

---

## 🏗️ สถาปัตยกรรมระบบ

```
[ผู้ใช้ยื่นขยะหน้ากล้อง] ──> [IR Sensor FC-51 (GPIO 4)] ──> [OLED นับถอยหลัง 3.. 2.. 1..]
                                                                        │
                                                         (ถ่ายภาพ JPEG ความละเอียด 320x240)
                                                                        ▼
   [Cloud AI: Ensemble YOLOv8 Engine] <── [ส่งภาพ HTTP POST] <── [ESP32-S3 (Dual-Hop Wi-Fi)]
                │
    (จำแนกขยะ 4 คลาส + กรองหน้าคน)
                ▼
   [ส่ง JSON ผลลัพธ์กลับมายัง ESP32-S3]
                │
                ├───────────────────────────────────────────────────────┐
                ▼                                                       ▼
   [HC-SR04 เช็กความจุขยะ]                                    [อัปเดต Live Dashboard]
   - ถ้าถังเต็ม <= 8 cm ──> OLED เตือน !! BIN FULL !! (ล็อกฝา)   - แสดงรูปถ่ายสดบน VIEW_RESULT.html
   - ถ้าถังว่าง ──> Native LEDC PWM หมุนเปิดฝา 90° ค้าง 3.5 วินาที
```

---

## 📁 โครงสร้างไดเรกทอรีโปรเจกต์

```text
smart-ai-trash-bin/
├── src/
│   └── smart_trash_bin_ov2640/
│       └── smart_trash_bin_ov2640.ino          # [เฟิร์มแวร์หลัก] โค้ด C++/Arduino บน ESP32-S3 (1,130 บรรทัด)
├── ai_training/
│   ├── cloud_ai_server.py                      # [เซิร์ฟเวอร์หลัก] Flask REST API + Ensemble YOLOv8
│   ├── train_comprehensive_model.py            # [การฝึกสอน] เทรน YOLOv8 Nano บน CPU 20 เธรด
│   ├── build_comprehensive_dataset.py          # [ไปป์ไลน์ข้อมูล] สคริปต์ดาวน์โหลด COCO + แปลงคลาส
│   ├── prepare_user_held_items_dataset.py      # [ข้อมูลจริง] สคริปต์ผสานภาพสแกนจริงจากกล้อง OV2640
│   ├── expand_general_class.py                 # [ปรับสมดุล] เพิ่มภาพขยะทั่วไป Class 0
│   ├── test_all_user_items.py                  # [ชุดทดสอบ] ตรวจสอบความถูกต้องกับวัตถุจริง 16 รายการ
│   ├── trained_models/
│   │   └── smart_bin_best.pt                   # โมเดลน้ำหนักที่ดีที่สุด (ขนาด 6.2 MB)
│   ├── yolov8n.pt                              # โมเดลรากฐาน (COCO Pretrained Base)
│   └── comprehensive_dataset/                  # ชุดข้อมูล 1,224 ภาพพร้อม YOLO Labels
│       ├── data.yaml
│       ├── images/ (train, val)
│       └── labels/ (train, val)
├── docs/
│   ├── pinout_and_circuit.md                   # ผังการต่อสายและวงจรอย่างละเอียด
│   ├── calibration_guide.md                    # คู่มือการปรับแต่งและจูนเซนเซอร์
│   └── bill_of_materials.md                    # ตารางแจกแจงรายการและราคาอุปกรณ์
├── captured_scans/                             # ประวัติภาพถ่ายจริงจากกล้อง OV2640
├── tests/                                      # สเก็ตช์ทดสอบฮาร์ดแวร์แยกชิ้น
├── VIEW_RESULT.html                            # แดชบอร์ดเว็บแสดงผลสด (Real-Time Auto Refresh)
├── smart-trash-bin.code-workspace              # ไฟล์โปรเจกต์สำหรับเปิดใน VS Code
├── PROJECT_CODEBASE_EXPLANATION.md             # คู่มืออธิบายโค้ดทั้งหมดอย่างละเอียด
├── MASTER_WIRING_GUIDE.md                      # คู่มือการต่อสายไฟระบบความปลอดภัย
├── RUN_CLOUD_AI_SERVER.bat                     # สคริปต์ดับเบิลคลิกเปิดเซิร์ฟเวอร์
├── RUN_SMART_BIN_LIVE.bat                      # สคริปต์เปิดการทำงานสด
├── TEST_SERVO.bat                              # สคริปต์ทดสอบเซอร์โว
├── TEST_SENSORS.bat                            # สคริปต์ทดสอบเซนเซอร์
├── UPLOAD_FIRMWARE.bat                         # สคริปต์อัปโหลดเฟิร์มแวร์
└── README.md                                   # เอกสารภาพรวมหลัก
```

---

## 🔌 ตารางผังการต่อขา GPIO

*ออกแบบให้ปลอดภัยและไม่ชนกับ Octal PSRAM (GPIO 33-37)*

| อุปกรณ์ | ขาบนอุปกรณ์ | ขาบน ESP32-S3 | หน้าที่ / พฤติกรรม |
| :--- | :--- | :---: | :--- |
| **เซนเซอร์ตรวจจับขยะ** | FC-51 OUT | **GPIO 4** | เมื่อมีวัตถุจ่อหน้ากล้อง ส่งสัญญาณ LOW (Active-Low) |
| **จอแสดงผล OLED 0.96"** | SDA | **GPIO 1** | ส่งสัญญาณข้อมูล I2C แสดงผลข้อความ/แอนิเมชัน |
| | SCL | **GPIO 2** | ส่งสัญญาณนาฬิกา I2C |
| **เซอร์โว 1 (ขยะทั่วไป)** | สายสัญญาณ (ส้ม) | **GPIO 21** | ฝาสีน้ำเงิน (ซองขนม, กล่องโฟม, ทิชชู่, เทป) |
| **เซอร์โว 2 (ขยะรีไซเคิล)**| สายสัญญาณ (ส้ม) | **GPIO 38** | ฝาสีเหลือง (ขวดน้ำดื่ม PET, แก้วน้ำ, กระป๋อง) |
| **เซอร์โว 3 (ขยะเปียก)** | สายสัญญาณ (ส้ม) | **GPIO 39** | ฝาสีเขียว (เศษอาหาร, เปลือกผลไม้, ผัก) |
| **เซอร์โว 4 (ขยะอันตราย)** | สายสัญญาณ (ส้ม) | **GPIO 40** | ฝาสีแดง (โทรศัพท์, แบตเตอรี่, ตะกั่ว, กาวตราช้าง) |
| **อัลตราโซนิค 4 ตัว** | TRIG รวม | **GPIO 14** | ขา Trigger ร่วม ยิงสัญญาณพร้อมกันทั้ง 4 ตัว |
| **อัลตราโซนิค ถังทั่วไป** | ECHO | **GPIO 47** | ตรวจระยะผิวขยะถังทั่วไป (เตือนเมื่อ $\le$ 8.0 ซม.) |
| **อัลตราโซนิค ถังรีไซเคิล**| ECHO | **GPIO 48** | ตรวจระยะผิวขยะถังรีไซเคิล (เตือนเมื่อ $\le$ 8.0 ซม.) |
| **อัลตราโซนิค ถังเปียก** | ECHO | **GPIO 3** | ตรวจระยะผิวขยะถังขยะเปียก (เตือนเมื่อ $\le$ 8.0 ซม.) |
| **อัลตราโซนิค ถังอันตราย** | ECHO | **GPIO 10** | ตรวจระยะผิวขยะถังอันตราย (เตือนเมื่อ $\le$ 8.0 ซม.) |
| **กล้อง ESP32-CAM** | ไร้สาย Wi-Fi AP | **ESP32-CAM-MB** | สื่อสารไร้สายวงปิดในตัวที่ IP 192.168.4.1 |

---

## 🧠 ระบบปัญญาประดิษฐ์และชุดข้อมูล

* **สถาปัตยกรรมโมเดล:** YOLOv8 Nano (`yolov8n`) ปรับแต่งเฉพาะทาง (3.2M Parameters, ขนาดไฟล์ 6.2 MB)
* **ความเร็วในการประมวลผล:** 30 - 65 มิลลิวินาทีต่อภาพบน CPU
* **ชุดข้อมูลทั้งหมด (1,224 รูปภาพ):**
  * **Train Set:** 1,021 ภาพ (83.4%)
  * **Validation Set:** 203 ภาพ (16.6%)
  * **แหล่งข้อมูล:** ผสานระหว่าง Microsoft COCO val2017 (640 ภาพ), ภาพสแกนจริงจากกล้อง OV2640 (432 ภาพ), และ Synthetic Augmentation (152 ภาพ)
* **โมเดลน้ำหนักที่ดีที่สุด:** บันทึกอยู่ที่ `ai_training/trained_models/smart_bin_best.pt`

---

## 🚀 การเริ่มต้นใช้งานจริง

### 1. เปิดเซิร์ฟเวอร์ Cloud AI Server:
ดับเบิลคลิกไฟล์ `RUN_CLOUD_AI_SERVER.bat` หรือรันผ่านเทอร์มินัล:
```powershell
python ai_training/cloud_ai_server.py
```
เซิร์ฟเวอร์จะเปิดทำงานที่พอร์ต 5000 (เช่น `http://10.221.244.85:5000`)

### 2. ดูผลลัพธ์ผ่านเว็บเบราว์เซอร์:
เปิดไฟล์ `VIEW_RESULT.html` ใน Google Chrome หรือ Edge เพื่อดูภาพสแกนสดและประวัติการจำแนกขยะแบบเรียลไทม์

### 3. รันชุดทดสอบความถูกต้องของโมเดล:
```powershell
python ai_training/test_all_user_items.py
```

---

## 📄 เอกสารคู่มือและเครื่องมือ

โครงการจัดทำเอกสารและเครื่องมือสำหรับการพัฒนาต่อยอด:
* 📖 **คู่มืออธิบายโค้ดทั้งหมด (VS Code Guide):** [`PROJECT_CODEBASE_EXPLANATION.md`](PROJECT_CODEBASE_EXPLANATION.md)
* ⚡ **คู่มือการต่อสายและระบบความปลอดภัย:** [`MASTER_WIRING_GUIDE.md`](MASTER_WIRING_GUIDE.md)
* 🖥️ **ไฟล์ Workspace สำหรับ VS Code:** [`smart-trash-bin.code-workspace`](smart-trash-bin.code-workspace)
