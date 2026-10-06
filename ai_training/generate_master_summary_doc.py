import os
import subprocess

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HTML_PATH = os.path.join(PROJECT_DIR, "SMART_AI_TRASH_BIN_MASTER_SUMMARY.html")
PDF_PATH = os.path.join(PROJECT_DIR, "SMART_AI_TRASH_BIN_MASTER_SUMMARY.pdf")
MD_PATH = os.path.join(PROJECT_DIR, "SMART_AI_TRASH_BIN_MASTER_SUMMARY.md")

html_content = """<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>เอกสารสรุปโครงการฉบับสมบูรณ์ - ถังขยะอัจฉริยะคัดแยก 4 ประเภทด้วย AI (Smart AI Trash Bin)</title>
    <style>
        @page {
            size: A4;
            margin: 12mm 14mm 12mm 14mm;
        }
        * {
            box-sizing: border-box;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
        body {
            font-family: 'Sarabun', 'Tahoma', 'Segoe UI', sans-serif;
            color: #1e293b;
            background: #ffffff;
            margin: 0;
            padding: 0;
            font-size: 13px;
            line-height: 1.5;
        }
        .header-banner {
            background: linear-gradient(135deg, #0f172a, #1e3a8a);
            color: #ffffff;
            padding: 20px 24px;
            border-radius: 12px;
            margin-bottom: 16px;
            border-bottom: 4px solid #38bdf8;
        }
        .header-banner h1 {
            margin: 0 0 6px 0;
            font-size: 22px;
            color: #38bdf8;
            font-weight: 700;
        }
        .header-banner p {
            margin: 0;
            font-size: 12.5px;
            color: #cbd5e1;
        }
        .header-meta {
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
            font-size: 11px;
            color: #94a3b8;
            border-top: 1px solid rgba(255,255,255,0.15);
            padding-top: 8px;
        }
        h2 {
            font-size: 15px;
            color: #0f172a;
            border-left: 5px solid #0284c7;
            padding-left: 10px;
            margin: 18px 0 10px 0;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }
        h3 {
            font-size: 13px;
            color: #1e40af;
            margin: 12px 0 6px 0;
        }
        p, li {
            font-size: 12.5px;
            color: #334155;
            margin: 4px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0 14px 0;
            font-size: 12px;
        }
        th, td {
            border: 1px solid #cbd5e1;
            padding: 7px 10px;
            text-align: left;
        }
        th {
            background: #f1f5f9;
            color: #0f172a;
            font-weight: 600;
        }
        tr:nth-child(even) td {
            background: #f8fafc;
        }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 10.5px;
            font-weight: bold;
            color: white;
        }
        .badge-blue { background: #0284c7; }
        .badge-yellow { background: #d97706; }
        .badge-green { background: #16a34a; }
        .badge-red { background: #dc2626; }
        .badge-purple { background: #7c3aed; }
        .badge-gray { background: #475569; }

        .callout {
            border-radius: 8px;
            padding: 10px 14px;
            margin: 10px 0;
            font-size: 12px;
            line-height: 1.45;
        }
        .callout-info {
            background: #f0f9ff;
            border-left: 4px solid #0284c7;
            color: #0369a1;
        }
        .callout-success {
            background: #f0fdf4;
            border-left: 4px solid #16a34a;
            color: #15803d;
        }
        .callout-warning {
            background: #fffbeb;
            border-left: 4px solid #f59e0b;
            color: #b45309;
        }
        .callout-danger {
            background: #fef2f2;
            border-left: 4px solid #ef4444;
            color: #b91c1c;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .grid-4 {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
        }
        .card {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 10px 12px;
            background: #ffffff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .card h4 {
            margin: 0 0 6px 0;
            font-size: 13px;
        }
        .code-inline {
            background: #f1f5f9;
            color: #0f172a;
            padding: 1px 5px;
            border-radius: 4px;
            font-family: Consolas, monospace;
            font-size: 11.5px;
            border: 1px solid #e2e8f0;
        }
        .page-break {
            page-break-after: always;
            break-after: page;
        }
    </style>
</head>
<body>

    <!-- ==================== PAGE 1 ==================== -->
    <div class="header-banner">
        <h1>📑 เอกสารสรุปโครงการฉบับสมบูรณ์ (Master Project Summary)</h1>
        <p>ระบบถังขยะอัจฉริยะคัดแยก 4 ประเภทด้วย AI (Smart AI 4-Class Sorting Trash Bin)</p>
        <div class="header-meta">
            <span><b>บอร์ดประมวลผล:</b> ESP32-S3 N16R8 (16MB Flash, 8MB PSRAM)</span>
            <span><b>โมเดล AI:</b> Dual-Intelligence (Cloud YOLOv8 + Onboard Edge AI)</span>
            <span><b>สถานะระบบ:</b> Standalone 100% Ready (ทำงานได้โดยไม่ต้องเสียบโน้ตบุ๊ก)</span>
        </div>
    </div>

    <div class="callout callout-success">
        <b>🌟 สรุปภาพรวมความสำเร็จของโครงการ:</b><br/>
        ระบบสามารถตรวจจับวัตถุขยะอัตโนมัติผ่านเซนเซอร์อินฟราเรด (FC-51) สั่งกล้อง OV2640 ถ่ายภาพ และทำการจำแนกประเภทขยะออกเป็น <b>4 ประเภท</b> (ขยะทั่วไป, ขยะรีไซเคิล, ขยะเปียก, ขยะอันตราย) สั่งเปิดฝาถังขยะช่องที่ถูกต้องด้วยเซอร์โวมอเตอร์ (SG90) พร้อมระบบวัดระดับขยะเต็ม (HC-SR04) ตรวจเช็คความจุและล็อกฝาถังเตือนอัตโนมัติ โดยระบบรองรับการทำงาน <b>2 โหมดอย่างราบรื่น: โหมด Standalone พกพาไปที่ไหนก็ได้โดยไม่ต้องมีคอมพิวเตอร์ และ โหมด Cloud AI ผ่านอินเทอร์เน็ต</b>
    </div>

    <h2>1. ข้อมูลถังขยะ 4 ประเภท และการสั่งการฮาร์ดแวร์</h2>
    <div class="grid-4">
        <div class="card" style="border-top: 4px solid #0d6efd;">
            <h4><span class="badge badge-blue">ช่อง 1: ทั่วไป</span></h4>
            <p><b>ชื่อ:</b> General Waste</p>
            <p><b>สีฝา:</b> ฝาสีน้ำเงิน</p>
            <p><b>เซอร์โว:</b> <span class="code-inline">GPIO 21</span></p>
            <p><b>อัลตราโซนิค:</b> <span class="code-inline">Echo 47</span></p>
            <p style="font-size:11px; color:#64748b;">ซองขนม, กล่องโฟม, ถุงพลาสติก, ทิชชู่</p>
        </div>
        <div class="card" style="border-top: 4px solid #ffc107;">
            <h4><span class="badge badge-yellow">ช่อง 2: รีไซเคิล</span></h4>
            <p><b>ชื่อ:</b> Recyclable</p>
            <p><b>สีฝา:</b> ฝาสีเหลือง</p>
            <p><b>เซอร์โว:</b> <span class="code-inline">GPIO 38</span></p>
            <p><b>อัลตราโซนิค:</b> <span class="code-inline">Echo 48</span></p>
            <p style="font-size:11px; color:#64748b;">ขวดน้ำ PET ใส, แก้วพลาสติก, กระป๋อง</p>
        </div>
        <div class="card" style="border-top: 4px solid #198754;">
            <h4><span class="badge badge-green">ช่อง 3: ขยะเปียก</span></h4>
            <p><b>ชื่อ:</b> Organic / Food</p>
            <p><b>สีฝา:</b> ฝาสีเขียว</p>
            <p><b>เซอร์โว:</b> <span class="code-inline">GPIO 39</span></p>
            <p><b>อัลตราโซนิค:</b> <span class="code-inline">Echo 3</span></p>
            <p style="font-size:11px; color:#64748b;">เศษอาหาร, เปลือกกล้วย, ผลไม้, ผัก</p>
        </div>
        <div class="card" style="border-top: 4px solid #dc3545;">
            <h4><span class="badge badge-red">ช่อง 4: อันตราย</span></h4>
            <p><b>ชื่อ:</b> Hazardous</p>
            <p><b>สีฝา:</b> ฝาสีแดง</p>
            <p><b>เซอร์โว:</b> <span class="code-inline">GPIO 40</span></p>
            <p><b>อัลตราโซนิค:</b> <span class="code-inline">Echo 10</span></p>
            <p style="font-size:11px; color:#64748b;">ถ่านไฟฉาย, แบตเตอรี่, หลอดไฟ, แผงยา</p>
        </div>
    </div>

    <h2>2. สถาปัตยกรรมสมองกลแบบคู่ (Dual-Intelligence Architecture)</h2>
    <table>
        <thead>
            <tr>
                <th style="width:22%;">คุณสมบัติ</th>
                <th style="width:39%;">โหมด 1: Autonomous Onboard Edge AI</th>
                <th style="width:39%;">โหมด 2: Production Cloud AI</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><b>สถานที่ประมวลผล</b></td>
                <td><b>บนชิป ESP32-S3 ในตัว 100%</b></td>
                <td>เซิร์ฟเวอร์ Cloud (Python YOLOv8)</td>
            </tr>
            <tr>
                <td><b>ความต้องการระบบ</b></td>
                <td><span class="badge badge-green">ไม่ต้องต่อเน็ต</span> <span class="badge badge-green">ไม่ต้องมีคอมพิวเตอร์</span></td>
                <td>Wi-Fi บ้าน หรือ Hotspot มือถือ</td>
            </tr>
            <tr>
                <td><b>เทคโนโลยีที่ใช้งาน</b></td>
                <td>ไลบรารี <b>TJpg_Decoder</b> ถอดรหัสภาพ JPEG ลง PSRAM 8MB วิเคราะห์ค่าสี HSV, แสงสะท้อนขวดใส (Specular), และพื้นผิว</td>
                <td>โมเดล <b>Custom YOLOv8 (smart_bin_best.pt)</b> ผ่านการ Fine-tuning ด้วยภาพจริง มั่นใจ 94.6%</td>
            </tr>
            <tr>
                <td><b>เวลาประมวลผล</b></td>
                <td><b>~20 - 80 มิลลิวินาที</b> (เร็วทันใจ ไม่ดีเลย์)</td>
                <td><b>~3.5 วินาที</b> (รวมสลับ Wi-Fi ส่งภาพและรับผล)</td>
            </tr>
            <tr>
                <td><b>ความเหมาะสม</b></td>
                <td>ยกไปตั้งโชว์นอกสถานที่, เสียบ Power Bank เดี่ยวๆ</td>
                <td>สาธิตงานใหญ่, มี Dashboard โชว์ขึ้นจอโปรเจกเตอร์</td>
            </tr>
        </tbody>
    </table>

    <div class="page-break"></div>

    <!-- ==================== PAGE 2 ==================== -->
    <h2>3. ตารางการต่อสายฮาร์ดแวร์แบบละเอียดทุกพิน (Hardware Pinout Map)</h2>
    <table>
        <thead>
            <tr>
                <th>อุปกรณ์</th>
                <th>ขาบนอุปกรณ์</th>
                <th>เชื่อมต่อไปยัง</th>
                <th>พินบน ESP32-S3</th>
                <th>หน้าที่และข้อกำหนด</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td rowspan="4"><b>จอแสดงผล OLED 0.96"</b><br/>(I2C SSD1306, 0x3C)</td>
                <td>VCC</td>
                <td>5V Rail หรือ 3.3V</td>
                <td>-</td>
                <td>ไฟเลี้ยงจอแสดงผล</td>
            </tr>
            <tr>
                <td>GND</td>
                <td>Common GND</td>
                <td>GND</td>
                <td>กราวด์ร่วมระบบ</td>
            </tr>
            <tr>
                <td>SDA</td>
                <td>ขาข้อมูล I2C</td>
                <td><b>GPIO 1</b></td>
                <td>ส่งข้อมูลภาพ/ตัวอักษร</td>
            </tr>
            <tr>
                <td>SCL</td>
                <td>ขานาฬิกา I2C</td>
                <td><b>GPIO 2</b></td>
                <td>สัญญาณ Clock I2C</td>
            </tr>
            <tr style="border-top: 2px solid #cbd5e1;">
                <td rowspan="3"><b>เซนเซอร์อินฟราเรด FC-51</b><br/>(ตรวจขยะหน้ากล้อง)</td>
                <td>VCC</td>
                <td>5V Rail หรือ 3.3V</td>
                <td>-</td>
                <td>ไฟเลี้ยงเซนเซอร์</td>
            </tr>
            <tr>
                <td>GND</td>
                <td>Common GND</td>
                <td>GND</td>
                <td>กราวด์ร่วมระบบ</td>
            </tr>
            <tr>
                <td>OUT</td>
                <td>ขาสัญญาณทริกเกอร์</td>
                <td><b>GPIO 0</b></td>
                <td>เมื่อมีวัตถุจ่อ ส่งสัญญาณ LOW (Active-Low)</td>
            </tr>
            <tr style="border-top: 2px solid #cbd5e1;">
                <td rowspan="4"><b>เซอร์โวมอเตอร์ 4 ตัว</b><br/>(SG90 9g เปิด-ปิดฝา)</td>
                <td>Servo 1 (ทั่วไป) สัญญาณ</td>
                <td>สายสีส้ม/เหลือง</td>
                <td><b>GPIO 21</b></td>
                <td>เปิดฝาถังขยะทั่วไป 90 องศา (3.5 วินาที)</td>
            </tr>
            <tr>
                <td>Servo 2 (รีไซเคิล) สัญญาณ</td>
                <td>สายสีส้ม/เหลือง</td>
                <td><b>GPIO 38</b></td>
                <td>เปิดฝาถังขยะรีไซเคิล 90 องศา (3.5 วินาที)</td>
            </tr>
            <tr>
                <td>Servo 3 (ขยะเปียก) สัญญาณ</td>
                <td>สายสีส้ม/เหลือง</td>
                <td><b>GPIO 39</b></td>
                <td>เปิดฝาถังขยะเปียก 90 องศา (3.5 วินาที)</td>
            </tr>
            <tr>
                <td>Servo 4 (อันตราย) สัญญาณ</td>
                <td>สายสีส้ม/เหลือง</td>
                <td><b>GPIO 40</b></td>
                <td>เปิดฝาถังขยะอันตราย 90 องศา (3.5 วินาที)</td>
            </tr>
            <tr style="border-top: 2px solid #cbd5e1;">
                <td rowspan="5"><b>เซนเซอร์อัลตราโซนิค 4 ตัว</b><br/>(HC-SR04 ตรวจถังเต็ม)</td>
                <td>Trig (ร่วม 4 ตัว)</td>
                <td>พ่วงขา Trig ทั้ง 4 ตัว</td>
                <td><b>GPIO 14</b></td>
                <td>ยิงคลื่นอัลตราโซนิคพร้อมกันทุกๆ 2.5 วินาที</td>
            </tr>
            <tr>
                <td>Echo 1 (ทั่วไป)</td>
                <td>ผ่านตัวต้านทาน 1k+2k</td>
                <td><b>GPIO 47</b></td>
                <td>วัดระยะผิวขยะถังทั่วไป (เตือนเมื่อ &le; 8 ซม.)</td>
            </tr>
            <tr>
                <td>Echo 2 (รีไซเคิล)</td>
                <td>ผ่านตัวต้านทาน 1k+2k</td>
                <td><b>GPIO 48</b></td>
                <td>วัดระยะผิวขยะถังรีไซเคิล (เตือนเมื่อ &le; 8 ซม.)</td>
            </tr>
            <tr>
                <td>Echo 3 (ขยะเปียก)</td>
                <td>ผ่านตัวต้านทาน 1k+2k</td>
                <td><b>GPIO 3</b></td>
                <td>วัดระยะผิวขยะถังขยะเปียก (เตือนเมื่อ &le; 8 ซม.)</td>
            </tr>
            <tr>
                <td>Echo 4 (อันตราย)</td>
                <td>ผ่านตัวต้านทาน 1k+2k</td>
                <td><b>GPIO 10</b></td>
                <td>วัดระยะผิวขยะถังอันตราย (เตือนเมื่อ &le; 8 ซม.)</td>
            </tr>
            <tr style="border-top: 2px solid #cbd5e1;">
                <td rowspan="2"><b>โมดูลกล้อง ESP32-CAM</b><br/>(OV2640 Wi-Fi Node)</td>
                <td>5V</td>
                <td>รางไฟ 5V Rail</td>
                <td>-</td>
                <td>ไฟเลี้ยงกล้องแยก ต้องการกระแสเสถียร (&ge; 1A)</td>
            </tr>
            <tr>
                <td>GND</td>
                <td>Common GND</td>
                <td>GND</td>
                <td>กราวด์ร่วม สื่อสารไร้สายผ่าน Wi-Fi ภายใน (192.168.4.1)</td>
            </tr>
        </tbody>
    </table>

    <div class="callout callout-warning">
        <b>⚡ ข้อควรระวังเรื่องระบบไฟฟ้า (Critical Electrical Safety):</b><br/>
        1. <b>ห้ามดึงไฟ 5V/3.3V จากขาบอร์ด ESP32 ไปเลี้ยงมอเตอร์เซอร์โว:</b> เนื่องจากเซอร์โว 4 ตัวกินกระแสไฟสูง กระชากไฟได้ถึง 1A–2A ต้องใช้ไฟตรงจาก <b>Step-Down Buck Converter (5.0V เสถียร)</b> หรืออะแดปเตอร์แยก<br/>
        2. <b>ต้องต่อ Common Ground (GND ร่วม):</b> ขั้วลบ (GND) ของแหล่งจ่ายไฟ, บอร์ด ESP32-S3, ESP32-CAM, มอเตอร์เซอร์โว และเซนเซอร์ทุกตัว <b>ต้องเชื่อมต่อถึงกันทั้งหมด</b> มิฉะนั้นมอเตอร์จะกระตุกและเซนเซอร์จะอ่านค่าผิดพลาด
    </div>

    <div class="page-break"></div>

    <!-- ==================== PAGE 3 ==================== -->
    <h2>4. ลำดับขั้นตอนการทำงานของระบบ (System Operational Flow)</h2>
    <div class="grid-2">
        <div class="card">
            <h4>🟢 ลำดับการสแกนและเปิดฝาถัง:</h4>
            <ol style="padding-left: 18px; margin: 6px 0;">
                <li><b>สแตนด์บาย [ READY ]:</b> เซนเซอร์อัลตราโซนิควัดระดับถังทุก 2.5 วินาที จอโชว์ <span class="code-inline">G:OK R:OK W:OK H:OK</span></li>
                <li><b>ตรวจพบขยะ:</b> ผู้ใช้นำขยะมาจ่อหน้าเซนเซอร์ IR (ระยะ 3–8 ซม.)</li>
                <li><b>นับถอยหลัง:</b> จอ OLED ขึ้นเลขนับถอยหลัง <span class="code-inline">[ 3 ] -> [ 2 ] -> [ 1 ]</span></li>
                <li><b>ถ่ายภาพ [ >> SNAP! << ]:</b> ESP32-S3 ดึงภาพ JPEG จากกล้อง OV2640 ผ่าน Wi-Fi วงปิดในตัว</li>
                <li><b>ประมวลผลจำแนก:</b> เลือกระหว่าง Onboard Edge AI (~20ms) หรือ Cloud AI (~3.5s)</li>
                <li><b>ตรวจสอบถังเต็ม:</b> เช็คระยะอัลตราโซนิคของถังเป้าหมาย</li>
                <li><b>เปิดฝาถัง:</b> เซอร์โวหมุนเปิด 90 องศา ค้างไว้ 3.5 วินาที แล้วหมุนปิด 0 องศา</li>
            </ol>
        </div>
        <div class="card">
            <h4>🔴 ระบบป้องกันถังเต็ม (Full-Bin Lockout):</h4>
            <p>เมื่อระยะผิวขยะในถังช่องใดวัดได้ <b>&le; 8.0 ซม.</b>:</p>
            <ul style="padding-left: 18px; margin: 6px 0;">
                <li>หน้าจอ Standby จะแสดงสถานะถังช่องนั้นเป็น <b><span style="color:#dc2626;">!FULL</span></b></li>
                <li>หากผู้ใช้สแกนขยะประเภทนั้น หน้าจอ OLED จะกระพริบเตือนสีขาว-ดำ 4 ครั้ง:
                    <div style="background:#0f172a; color:#f8fafc; padding:8px; border-radius:6px; margin:6px 0; font-family:monospace; font-size:11px;">
                        !! BIN FULL ALERT !!<br/>
                        [ RECYCLE ]<br/>
                        LID LOCKED: CANNOT OPEN<br/>
                        Waste Level: 6.2 cm
                    </div>
                </li>
                <li><b>เซอร์โวจะถูกล็อกไม่เปิดเด็ดขาด</b> ป้องกันขยะล้นถัง</li>
            </ul>
        </div>
    </div>

    <h2>5. วิธีการเปิดเครื่องใช้งานจริง (Checklist สำหรับการสาธิต)</h2>
    <div class="grid-2">
        <div class="card">
            <h4>🔋 โหมดพกพา Standalone (ไม่เสียบสายคอม):</h4>
            <ol style="padding-left: 18px; margin: 6px 0;">
                <li>เสียบสาย USB-C ของ ESP32-S3 เข้ากับ <b>หัวชาร์จ 5V</b> หรือ <b>Power Bank</b></li>
                <li>ตรวจดูว่าไฟเลี้ยงบอร์ดกล้อง ESP32-CAM ติดสว่าง</li>
                <li>รอประมาณ 4–6 วินาที หน้าจอ OLED จะขึ้นข้อความ <b><span class="code-inline">[ READY ]</span></b></li>
                <li>นำขยะมาจ่อหน้าเซนเซอร์ IR เพื่อเริ่มใช้งานได้ทันที 100%!</li>
            </ol>
        </div>
        <div class="card">
            <h4>💻 โหมด Cloud AI พร้อมหน้าเว็บ Dashboard:</h4>
            <ol style="padding-left: 18px; margin: 6px 0;">
                <li>เปิดเซิร์ฟเวอร์บนโน้ตบุ๊กโดยดับเบิลคลิกไฟล์ <b><span class="code-inline">RUN_SMART_BIN_LIVE.bat</span></b></li>
                <li>เปิดดูผลการสแกนสดพร้อมแกลเลอรีภาพถ่ายผ่านไฟล์ <b><span class="code-inline">VIEW_RESULT.html</span></b></li>
                <li>ถังขยะจะเชื่อมต่อ Wi-Fi และส่งภาพขึ้น Cloud อัตโนมัติ</li>
                <li>ทุกภาพที่สแกนจะถูกบันทึกลงโฟลเดอร์ <b><span class="code-inline">captured_scans/</span></b></li>
            </ol>
        </div>
    </div>

    <h2>6. โครงสร้างไฟล์และสคริปต์สำคัญของโครงการ (Project Directory)</h2>
    <table>
        <thead>
            <tr>
                <th style="width:38%;">ไฟล์ / โฟลเดอร์</th>
                <th style="width:62%;">คำอธิบายหน้าที่</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="code-inline">src/smart_trash_bin_ov2640/smart_trash_bin_ov2640.ino</span></td>
                <td>โค้ดเฟิร์มแวร์หลักของ ESP32-S3 (รวมระบบ Edge AI, Dual-Hop Wi-Fi, เซอร์โว 4 ตัว, อัลตราโซนิค 4 ตัว)</td>
            </tr>
            <tr>
                <td><span class="code-inline">ai_training/cloud_ai_server.py</span></td>
                <td>เซิร์ฟเวอร์ Cloud AI (Flask + YOLOv8) รองรับการสแกนสด, API /classify, และ แกลเลอรีภาพ</td>
            </tr>
            <tr>
                <td><span class="code-inline">ai_training/trained_models/smart_bin_best.pt</span></td>
                <td>ไฟล์โมเดล Custom YOLOv8 ที่ผ่านการเทรนและ Fine-tuning (ตรวจจับขวดน้ำแม่นยำ 94.6%)</td>
            </tr>
            <tr>
                <td><span class="code-inline">captured_scans/</span></td>
                <td>โฟลเดอร์จัดเก็บภาพถ่ายจริงจากการสแกนทุกชิ้น ระบุชื่อตามวันเวลาและประเภท</td>
            </tr>
            <tr>
                <td><span class="code-inline">VIEW_RESULT.html</span></td>
                <td>หน้าเว็บ Dashboard แสดงผลการจำแนกสดแบบเรียลไทม์ พร้อมแกลเลอรีภาพถ่ายย้อนหลัง</td>
            </tr>
            <tr>
                <td><span class="code-inline">RUN_SMART_BIN_LIVE.bat</span></td>
                <td>สคริปต์เปิดระบบเซิร์ฟเวอร์ Cloud AI และหน้าต่าง Dashboard อัตโนมัติในคลิกเดียว</td>
            </tr>
        </tbody>
    </table>

</body>
</html>
"""

# 1. เขียนไฟล์ HTML
with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"HTML Summary created at: {HTML_PATH}")

# 2. แปลงเป็น PDF ผ่าน Microsoft Edge Headless
edge_paths = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe"
]
browser_path = None
for p in edge_paths:
    if os.path.exists(p):
        browser_path = p
        break

if browser_path:
    cmd = [
        browser_path,
        "--headless",
        "--disable-gpu",
        f"--print-to-pdf={PDF_PATH}",
        "--no-pdf-header-footer",
        HTML_PATH
    ]
    print(f"Generating PDF with: {browser_path}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(PDF_PATH):
        print(f"SUCCESS: PDF generated at: {PDF_PATH} (Size: {os.path.getsize(PDF_PATH)} bytes)")
    else:
        print(f"Error generating PDF: {res.stderr}")
else:
    print("Browser not found for PDF generation.")
