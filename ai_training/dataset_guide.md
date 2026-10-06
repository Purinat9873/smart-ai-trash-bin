# คู่มือการเตรียม Dataset และเทรนโมเดล YOLOv8 (AI Dataset & Deployment Guide)

เอกสารนี้จะแนะนำขั้นตอนการเตรียมชุดข้อมูลภาพขยะ 4 คลาส, การจัดการกรณีผู้ใช้ "ถือขยะด้วยมือ", การเทรนบน Roboflow/Google Colab และการรับ API Key สำหรับ ESP32-S3

---

## 1. การแบ่ง 4 คลาสมาตรฐาน (Class Taxonomy)

โมเดลถูกกำหนดให้จำแนกขยะออกเป็น 4 ประเภทหลัก:

| Class ID | ชื่อคลาส | วัตถุตัวอย่างในคลาส | สังเกต |
| :---: | :--- | :--- | :--- |
| `0` | **General (ทั่วไป)** | ถุงพลาสติก, ซองขนม, กล่องโฟม, ซองบะหมี่, กระดาษทิชชู่ใช้แล้ว | ขยะย่อยสลายยากและไม่คุ้มรีไซเคิล |
| `1` | **Recyclable (รีไซเคิล)** | ขวดพลาสติก PET ใส, ขวดแก้ว, กระป๋องอลูมิเนียม, กล่องลัง/กระดาษขาว | มีมูลค่านำกลับมาแปรรูปได้ |
| `2` | **Wet (ขยะเปียก)** | เศษอาหาร, เปลือกผลไม้ (กล้วย ส้ม), เศษผัก, กากกาแฟ | ย่อยสลายได้ทางชีวภาพ เน่าเสียง่าย |
| `3` | **Hazardous (ขยะอันตราย)**| ถ่านไฟฉาย/แบตเตอรี่, หลอดไฟนีออน, กระป๋องสเปรย์, ขวดยา | สารเคมีอันตราย ต้องทิ้งแยกพิเศษ |

---

## 2. แหล่ง Dataset ฟรีแนะนำ (Free Open-Source Datasets)

1. **TrashNet Dataset (Stanford University):**
   - มีรูปภาพขยะกว่า 2,527 รูป พร้อมจัดกลุ่ม Glass, Paper, Cardboard, Plastic, Metal, Trash
   - ดาวน์โหลดได้จาก GitHub / Kaggle หรือ Search บน Roboflow Universe
2. **TACO (Trash Annotations in Context):**
   - ภาพขยะในสภาพแวดล้อมจริงแบบเปิด (Real-world waste)
3. **Roboflow Universe (แนะนำที่สุด):**
   - มีโปรเจกต์ `Waste Classification` และ `Garbage Detection` พร้อม Bounding Box นับหมื่นภาพ สามารถ Fork/Clone เข้าบัญชีตัวเองได้ทันทีใน 1 คลิก

---

## 3. เทคนิคพิเศษ: การเทรนให้แม่นยำเมื่อ "ถือขยะด้วยมือ" (Handheld Optimization)

เนื่องจากระบบออกแบบให้ผู้ใช้ถือขยะยื่นเข้าหากล้อง:
1. **เพิ่มภาพถ่ายจริง (Custom Dataset):**
   - ใช้โทรศัพท์มือถือถ่ายภาพตอนคุณ **"ใช้มือถือขยะจริง"** หน้าฉากหลังห้อง ประมาณ 20–30 รูปต่อคลาส (รวม 80–120 รูป)
   - วาด Bounding Box ครอบเฉพาะ "ตัวขยะ" (ไม่ครอบทั้งมือและแขน)
2. **ตั้งค่า Data Augmentation บน Roboflow:**
   - **Crop:** 0% to 20% (จำลองมือที่อาจบังขอบขยะบางส่วน)
   - **Brightness:** Between -20% and +20% (จำลองแสงในห้องเปลี่ยน)
   - **Rotation:** Between -15° and +15° (จำลองการเอียงมือ)

---

## 4. ขั้นตอนการเทรนและรับ Hosted API Key (Roboflow)

1. สมัครใช้งานฟรีที่ [roboflow.com](https://roboflow.com)
2. สร้าง Project ประเภท **Object Detection**
3. อัปโหลดรูปภาพและทำ Annotation กำหนดป้าย 4 คลาส (`General`, `Recyclable`, `Wet`, `Hazardous`)
4. กด **Generate Version** -> เลือก Augmentation ตามข้อ 3
5. กด **Train Model** (เลือก Train with Roboflow แบบ Fast/Accurate) หรือ Export เพื่อไปรันบน Google Colab ด้วยไฟล์ `train_yolov8.py`
6. เมื่อเทรนเสร็จ ไปที่แท็บ **Deploy**
   - คุณจะได้รับ Endpoint URL เช่น:
     `https://detect.roboflow.com/smart-trash-bin/1?api_key=xyz123abc`
7. นำ URL และ API Key นี้ไปใส่ในตัวแปร `ROBOFLOW_API_URL` ในไฟล์ `smart_trash_bin.ino`

---

## 5. การทดสอบก่อนต่อกล้องจริง (Testing via Mock Server)
หากยังไม่ได้เทรนโมเดล หรือต้องการทดสอบโค้ด ESP32-S3 บนเครื่องคอมพิวเตอร์ก่อน:
1. เปิด Terminal ในโฟลเดอร์โปรเจกต์:
   ```powershell
   python tests/mock_server/mock_api_server.py
   ```
2. แก้ไข URL ในโค้ด ESP32 ให้ชี้มาที่ IP เครื่องคอมพิวเตอร์ของคุณ:
   ```cpp
   const char* API_INFERENCE_URL = "http://192.168.1.xxx:5000/predict";
   ```
3. เมื่อ ESP32 สแกนภาพ จะส่งรูปเข้ามาและเซิร์ฟเวอร์จะตอบกลับผลลัพธ์ทันที พร้อมบันทึกภาพลงโฟลเดอร์ `tests/mock_server/received_images/` ให้ตรวจสอบคุณภาพเลนส์ได้ทันที!
