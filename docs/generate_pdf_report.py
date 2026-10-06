"""
Generate Professional PDF Report for Project Criteria Evaluation (Clean Typography)
==================================================================================
สร้างรายงานการประเมินความสอดคล้องตามเกณฑ์การตัดสิน (Scoring Criteria Report)
เป็นไฟล์ PDF ภาษาไทยที่สวยงามและสมบูรณ์แบบ ปราศจาก Warning
"""

import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

FONT_PATH = r"C:\Windows\Fonts\tahoma.ttf"
OUTPUT_PDF = os.path.join(os.path.dirname(__file__), "Smart_Trash_Bin_Criteria_Evaluation_Report.pdf")

class PDFReport(FPDF):
    def header(self):
        self.set_font('Tahoma', '', 8.5)
        self.set_text_color(120, 120, 120)
        self.cell(0, 7, 'รายงานการประเมินความสอดคล้องตามเกณฑ์การตัดสิน (Criteria Alignment Report) | Smart AI Trash Bin', 
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='R')
        self.line(10, 15, 200, 15)
        self.ln(3)

    def footer(self):
        self.set_y(-14)
        self.set_font('Tahoma', '', 8.5)
        self.set_text_color(140, 140, 140)
        self.cell(0, 8, f'หน้า {self.page_no()}/{{nb}} | โครงงานถังขยะอัจฉริยะคัดแยก 4 ประเภทด้วย AI (ESP32-S3 + YOLOv8)', 
                  new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')

    def chapter_title(self, title):
        self.set_font('Tahoma', '', 13)
        self.set_text_color(26, 54, 93) # Navy blue
        self.set_fill_color(238, 242, 246)
        self.cell(0, 8.5, f'  {title}', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(2)

    def section_title(self, title, weight_str=""):
        self.set_font('Tahoma', '', 10.5)
        self.set_text_color(13, 148, 136) # Teal
        text = f'- {title} [{weight_str}]' if weight_str else f'- {title}'
        self.cell(0, 6.5, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.ln(1)

    def body_text(self, text):
        self.set_font('Tahoma', '', 9.2)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.2, text)
        self.ln(1.5)

    def callout_box(self, title, content):
        self.set_fill_color(245, 248, 250)
        self.set_draw_color(13, 148, 136)
        self.set_line_width(0.3)
        self.set_font('Tahoma', '', 9)
        
        self.set_text_color(13, 148, 136)
        self.cell(0, 5.8, f'  >> ข้อเสนอแนะเชิงกลยุทธ์สู่คะแนนเต็ม: {title}', border=1, fill=True, 
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        self.set_text_color(60, 60, 60)
        self.set_line_width(0.2)
        self.set_draw_color(210, 215, 220)
        self.multi_cell(0, 4.8, f'  {content}', border=1, fill=True)
        self.ln(2.5)

def create_report():
    pdf = PDFReport()
    pdf.alias_nb_pages()
    pdf.add_font('Tahoma', '', FONT_PATH)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Document Header Title
    pdf.set_font('Tahoma', '', 16)
    pdf.set_text_color(26, 54, 93)
    pdf.cell(0, 9, 'รายงานการประเมินความสอดคล้องตามเกณฑ์การตัดสิน (Criteria Report)', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    
    pdf.set_font('Tahoma', '', 10.5)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5.5, 'โครงงาน: ถังขยะอัจฉริยะคัดแยก 4 ประเภทด้วย AI (Smart AI Trash Bin Prototype)', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.cell(0, 5.5, 'สถาปัตยกรรมระบบ: ESP32-S3 (N16R8) + OV2640 + YOLOv8 Nano + Power Management 2S', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(3)

    # 1. Executive Summary Table
    pdf.chapter_title('1. บทสรุปภาพรวมผลการประเมิน (Executive Scorecard)')
    pdf.body_text(
        'จากการวิเคราะห์เกณฑ์การตัดสิน (Scoring Criteria) ของคณะกรรมการ พบว่าตัวต้นแบบ (Prototype) '
        'ของโปรเจกต์นี้ตอบโจทย์และตรงตามข้อกำหนดในระดับดีเยี่ยม (มากกว่า 95%) '
        'เนื่องจากโครงงานได้รับการออกแบบเชิงวิศวกรรมที่สมบูรณ์ ทั้งด้าน AI, วงจรไฟฟ้า, ความปลอดภัย และความคุ้มค่า'
    )

    # Table Header
    pdf.set_font('Tahoma', '', 9)
    pdf.set_fill_color(26, 54, 93)
    pdf.set_text_color(255, 255, 255)
    col_widths = [65, 22, 28, 75]
    pdf.cell(col_widths[0], 6.5, ' เกณฑ์การประเมิน (Criteria)', border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
    pdf.cell(col_widths[1], 6.5, ' น้ำหนัก', border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
    pdf.cell(col_widths[2], 6.5, ' คะแนนคาดการณ์', border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
    pdf.cell(col_widths[3], 6.5, ' สถานะความสอดคล้องในโปรเจกต์', border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')

    # Table Rows
    pdf.set_text_color(40, 40, 40)
    rows = [
        ('1. Technical Innovation', '25%', '24.0 / 25', 'ตอบโจทย์สูงมาก (Hands-free + Interlock)'),
        ('2. AI System Design', '20%', '19.5 / 20', 'ดีเยี่ยม (YOLOv8n + Edge-to-Cloud API)'),
        ('3. AI Application & Integration', '20%', '19.5 / 20', 'สมบูรณ์แบบ (End-to-End IoT Integration)'),
        ('4. Technical Feasibility', '15%', '15.0 / 15', 'คะแนนเต็ม (แก้ไฟตก + ต้นทุนเพียง 720 บาท)'),
        ('5. Prototype & Demonstration', '15%', '14.5 / 15', 'พร้อมสาธิตจริง (ถัง 4 สี + ระบบจำลองสด)'),
        ('6. Presentation', '5%', '5.0 / 5', 'ชัดเจน (มีสถาปัตยกรรมและไดอะแกรมรองรับ)'),
    ]
    for r in rows:
        pdf.cell(col_widths[0], 6, f' {r[0]}', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='L')
        pdf.cell(col_widths[1], 6, f'{r[1]}', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        pdf.cell(col_widths[2], 6, f'{r[2]}', border=1, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
        pdf.cell(col_widths[3], 6, f' {r[3]}', border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')

    # Total Score
    pdf.set_fill_color(240, 253, 244)
    pdf.set_text_color(22, 101, 52)
    pdf.cell(col_widths[0] + col_widths[1], 6.5, ' รวมคะแนนประเมินภาพรวม (Total Score)', border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP, align='R')
    pdf.cell(col_widths[2], 6.5, '97.5 / 100%', border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP, align='C')
    pdf.cell(col_widths[3], 6.5, ' ระดับดีเยี่ยม (Top Tier Standard)', border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
    pdf.ln(3)

    # 2. Detailed Breakdown
    pdf.chapter_title('2. บทวิเคราะห์เจาะลึกรายเกณฑ์ทั้ง 6 ด้าน (Detailed Criteria Analysis)')

    # Criteria 1
    pdf.section_title('เกณฑ์ที่ 1: Technical Innovation (น้ำหนัก 25%)', 'คะแนนเป้าหมาย: 24/25')
    pdf.body_text(
        '- สิ่งที่โปรเจกต์มี: มีระบบ Hands-Free Auto-Scan ที่ผสานเซนเซอร์ IR ตรวจจับการยื่นมือเข้าหากล้องอัตโนมัติ '
        'พร้อมระบบ Dual-Sensor Safety Interlock (เช็กความจุถังก่อนเปิดด้วย Ultrasonic และเช็กการตกจริงของขยะก่อนปิดด้วย IR)\n'
        '- ความโดดเด่น: แก้ปัญหา Pain Point สุขอนามัยในที่สาธารณะ (ผู้ใช้ไม่ยอมแตะถังขยะ) ได้อย่างชาญฉลาด'
    )
    pdf.callout_box(
        'เพิ่มมิติ BCG Economy และ Carbon Offset',
        'นำเสนอการคำนวณลดก๊าซเรือนกระจก เช่น "การคัดแยกขวดพลาสติก 1 ใบ ช่วยลด CO2 ได้ 0.08 kg CO2e" '
        'โดยแสดงผลบนหน้าจอ OLED หรือส่งเข้า LINE OA จะช่วยดึงดูดคะแนนด้านนวัตกรรมสร้างสรรค์เพื่อสิ่งแวดล้อมได้เต็ม 25%'
    )

    # Criteria 2
    pdf.section_title('เกณฑ์ที่ 2: AI System Design (น้ำหนัก 20%)', 'คะแนนเป้าหมาย: 19.5/20')
    pdf.body_text(
        '- การเลือก Model: เลือกใช้ YOLOv8 Nano ซึ่งมีพารามิเตอร์เพียง 3 ล้านตัว ให้ความเร็วระดับ 20-50 ms เหมาะสมสูงสุดกับ Edge/Cloud IoT\n'
        '- สถาปัตยกรรมข้อมูล: ออกแบบ 4 คลาสตามมาตรฐานสากล (General, Recyclable, Wet, Hazardous) '
        'พร้อมจัดการหน่วยความจำ Octal PSRAM 8MB บน ESP32-S3 สำหรับพักภาพ Binary JPEG ส่งตรงขึ้น Cloud API อย่างมีเสถียรภาพ'
    )
    pdf.callout_box(
        'การตอบคำถามเรื่อง Model Justification',
        'หากกรรมการถามว่า "ทำไมไม่ใช้ Classification ทั่วไป (เช่น MobileNet)?" ให้ตอบว่า: '
        '"เพราะ YOLOv8 เป็น Object Detection ที่มี Bounding Box ช่วยโฟกัสเฉพาะชิ้นขยะ และตัดภาพมือคนหรือฉากหลังออก '
        'ทำให้ค่าความแม่นยำสูงกว่าการทำ Image Classification แบบเดิมอย่างมีนัยสำคัญ"'
    )

    # Criteria 3
    pdf.section_title('เกณฑ์ที่ 3: AI Application & Integration (น้ำหนัก 20%)', 'คะแนนเป้าหมาย: 19.5/20')
    pdf.body_text(
        '- การบูรณาการครบวงจร (End-to-End Integration): เชื่อมโยงเซนเซอร์ กล้อง AI คลาวด์ มอเตอร์ฝาถัง และระบบแจ้งเตือนแบบไร้รอยต่อ\n'
        '- การแก้ปัญหาที่แท้จริง: ตอบโจทย์ "การคัดแยกขยะตั้งแต่ต้นทาง (Source Segregation)" ซึ่งเป็นปัญหาใหญ่ระดับชาติ '
        'โดยช่วยลดภาระพนักงานเก็บขยะและเพิ่มอัตราการนำกลับมารีไซเคิลอย่างเป็นรูปธรรม'
    )

    # Page Break for clean reading
    pdf.add_page()

    # Criteria 4
    pdf.section_title('เกณฑ์ที่ 4: Technical Feasibility (น้ำหนัก 15%)', 'คะแนนเป้าหมาย: 15/15 (คะแนนเต็ม)')
    pdf.body_text(
        '- การแก้ปัญหาไฟตก (Zero Brownout): ใช้ระบบไฟ 2S (7.4V) ผ่าน Step-Down Buck 5.0V และใส่ C 1000uF แก้ปัญหาไฟวูบที่โปรเจกต์อื่นมักล้มเหลว\n'
        '- เทคนิคการประหยัดพลังงาน: ใช้คำสั่ง detach() ตัดไฟมอเตอร์เซอร์โวหลังเปิด-ปิดเสร็จ ช่วยประหยัดแบตเตอรี่ได้กว่า 80% มอเตอร์ไม่ไหม้\n'
        '- ความคุ้มค่าทางเศรษฐศาสตร์: ต้นทุนรวมฮาร์ดแวร์ทั้งระบบเพียง ~720 บาท ทำให้มีความเป็นไปได้สูงมากในการผลิตใช้งานจริงตามโรงเรียนและชุมชน'
    )

    # Criteria 5
    pdf.section_title('เกณฑ์ที่ 5: Prototype & Demonstration (น้ำหนัก 15%)', 'คะแนนเป้าหมาย: 14.5/15')
    pdf.body_text(
        '- ความสมบูรณ์ของตัวต้นแบบ: ตัวถังกระดาษลังผสมฝาฟิวเจอร์บอร์ด 4 สี น้ำหนักเบา ทนทาน ไม่เปื่อยยุ่ยเมื่อเจอขยะเปียก\n'
        '- เครื่องมือสาธิต: มีทั้งฮาร์ดแวร์จริง และโปรแกรม Live Webcam Simulator บนคอมพิวเตอร์ที่พร้อมเดโมสดได้ทุกสถานการณ์'
    )
    pdf.callout_box(
        'การเตรียมอุปกรณ์สาธิตในวันเดโม (Demo Props)',
        'เตรียมขยะจริง 4 ชิ้น: 1.ขวดน้ำพลาสติก 2.เปลือกกล้วย/ผลไม้ 3.ถ่านไฟฉาย/แผงยา 4.ซองขนม '
        'เมื่อชูขยะแต่ละชิ้น ฝาถังสีที่ถูกต้องจะเปิดทันที เป็นการพิสูจน์ความสามารถของโปรเจกต์ที่เห็นผลชัดเจนที่สุด'
    )

    # Criteria 6
    pdf.section_title('เกณฑ์ที่ 6: Presentation (น้ำหนัก 5%)', 'คะแนนเป้าหมาย: 5/5')
    pdf.body_text(
        '- สื่อสารแนวคิด กระบวนการ และวงจรทางเทคนิคอย่างเป็นระบบ มีบล็อกไดอะแกรม ตาราง Pinout และสถิติความแม่นยำรองรับครบถ้วน'
    )
    pdf.ln(1)

    # 3. 3-Minute Pitch Framework
    pdf.chapter_title('3. โครงสร้างบทนำเสนอ 3 นาที ชนะใจกรรมการ (3-Minute Winning Pitch)')
    
    pitch_steps = [
        ('นาทีที่ 1: ปัญหาและแนวคิด (The Hook & Problem)', 
         'เกริ่นถึงปัญหาขยะปนเปื้อนในประเทศไทยที่ทำให้รีไซเคิลไม่ได้ + ปัญหาคนไม่อยากสัมผัสถังขยะสกปรก '
         'จึงพัฒนานวัตกรรม "ถังขยะอัจฉริยะ AI ไร้สัมผัส 4 คลาส" ที่ช่วยคัดแยกขยะต้นทางอย่างแม่นยำ'),
        ('นาทีที่ 2: สถาปัตยกรรมและเทคโนโลยี (Technical Deep Dive)', 
         'อธิบายการทำงานของ ESP32-S3 ร่วมกับโมเดล YOLOv8 Nano ผ่านระบบ Hands-Free Auto-Scan '
         'ชูจุดเด่นระบบความปลอดภัย Dual Interlock และระบบไฟ 2S Step-Down ที่เสถียร ไม่เกิดไฟตก'),
        ('นาทีที่ 3: การสาธิตและความคุ้มค่า (Live Demo & Feasibility)', 
         'สาธิตการชูขยะจริงให้ฝาถังแต่ละสีเปิดออก สรุปจุดเด่นต้นทุนเพียง 720 บาท พร้อมขยายผลเชิงพาณิชย์ '
         'ตอบโจทย์โมเดลเศรษฐกิจ BCG Economy ของประเทศได้อย่างสมบูรณ์แบบ')
    ]

    for title, desc in pitch_steps:
        pdf.set_font('Tahoma', '', 9.8)
        pdf.set_text_color(26, 54, 93)
        pdf.cell(0, 5.5, f'[STEP] {title}', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='L')
        pdf.set_font('Tahoma', '', 9)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 4.8, desc)
        pdf.ln(1.5)

    pdf.output(OUTPUT_PDF)
    print(f"[+] สร้างไฟล์ PDF สำเร็จเรียบร้อย: {OUTPUT_PDF}")

if __name__ == '__main__':
    create_report()
