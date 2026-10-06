/*
 * ==================================================================================
 * SMART TRASH BIN - ENHANCED OLED & SERIAL CONTROLLER (ESP32-S3 N16R8)
 * ระบบถังขยะอัจฉริยะ แสดงผลข้อความกราฟิกสวยงามบนจอ OLED 0.96 นิ้ว
 * ==================================================================================
 */

#include <Arduino.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
bool oledFound = false;

// ขาเซอร์โวมอเตอร์ 4 ช่อง
const int SERVO_PINS[4] = {21, 38, 39, 40};
Servo servos[4];

// ข้อมูลประเภทขยะ
struct BinInfo {
  const char* en_title;
  const char* bin_color;
  const char* desc;
};

BinInfo BINS[4] = {
  {"GENERAL",   "BLUE LID",   "General Waste"},
  {"RECYCLE",   "YELLOW LID", "Bottles & Cans"},
  {"ORGANIC",   "GREEN LID",  "Food & Fruit"},
  {"HAZARD!",   "RED LID",    "Battery/Chemical"}
};

void initOled() {
  Wire.begin(1, 2); // SDA = GPIO 1, SCL = GPIO 2
  if (display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    oledFound = true;
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);

    // หน้าจอต้อนรับ
    display.fillRect(0, 0, 128, 16, SSD1306_WHITE);
    display.setTextColor(SSD1306_BLACK);
    display.setTextSize(1);
    display.setCursor(12, 4);
    display.println("SMART AI TRASH BIN");

    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(2);
    display.setCursor(20, 26);
    display.println("ONLINE");

    display.setTextSize(1);
    display.setCursor(14, 50);
    display.println("Ready to detect...");
    display.display();
    Serial.println("[OLED] ตรวจพบจอ 0.96 นิ้ว (0x3C) - แสดงผลสำเร็จ!");
  } else {
    Serial.println("[OLED] ยังไม่พบจอ (ตรวจสอบการต่อขา SDA=1, SCL=2, VCC, GND)");
  }
}

void showStandby() {
  if (!oledFound) return;
  display.clearDisplay();
  
  // Header bar
  display.fillRect(0, 0, 128, 14, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(14, 3);
  display.println("SMART TRASH BIN");

  // Body
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(18, 24);
  display.println("[ READY ]");

  // Footer
  display.setTextSize(1);
  display.setCursor(8, 48);
  display.println("Show waste to camera");
  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  display.display();
}

void showBinResult(int binIndex) {
  if (!oledFound) return;
  display.clearDisplay();

  // แถบหัวเรื่อง
  display.fillRect(0, 0, 128, 14, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(10, 3);
  if (binIndex == 3) {
    display.println("!! DANGER DETECTED !!");
  } else {
    display.println("AI CLASSIFICATION");
  }

  // ชื่อประเภทขยะขนาดใหญ่ตรงกลาง
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  int xPos = (binIndex == 0) ? 22 : (binIndex == 1) ? 22 : (binIndex == 2) ? 22 : 16;
  display.setCursor(xPos, 22);
  display.println(BINS[binIndex].en_title);

  // คำอธิบายและสีถังด้านล่าง
  display.setTextSize(1);
  display.setCursor(8, 44);
  display.printf("Open: %s", BINS[binIndex].bin_color);
  display.setCursor(8, 54);
  display.println(BINS[binIndex].desc);

  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  display.display();

  // หากเป็นขยะอันตราย (คลาส 3) ให้กะพริบจอเตือนภัย
  if (binIndex == 3) {
    for (int f = 0; f < 3; f++) {
      display.invertDisplay(true);
      delay(120);
      display.invertDisplay(false);
      delay(120);
    }
  }
}

void openBin(int binIndex) {
  if (binIndex < 0 || binIndex > 3) return;

  Serial.printf("\n[ACTION] >>> สั่งเปิดฝาถังช่อง %d: %s (%s) <<<\n", 
                binIndex + 1, BINS[binIndex].en_title, BINS[binIndex].bin_color);
  
  showBinResult(binIndex);

  // สั่งเซอร์โวเปิด 90 องศา
  servos[binIndex].attach(SERVO_PINS[binIndex]);
  servos[binIndex].write(90);
  Serial.printf("[SERVO %d] GPIO %d -> 90 องศา (เปิดฝา)\n", binIndex + 1, SERVO_PINS[binIndex]);

  delay(3500); // เวลารอทิ้งขยะ

  // ปิดฝากลับ 0 องศา + Detach
  servos[binIndex].write(0);
  delay(600);
  servos[binIndex].detach();
  Serial.printf("[SERVO %d] GPIO %d -> 0 องศา (ปิดฝาสนิท)\n", binIndex + 1, SERVO_PINS[binIndex]);

  showStandby();
  Serial.println("[STATUS] ปิดฝาเรียบร้อย - พร้อมรับคำสั่งรอบใหม่\n");
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n========================================================");
  Serial.println("  ESP32-S3 SMART TRASH BIN - OLED & AI CONTROLLER       ");
  Serial.println("========================================================");

  initOled();

  // เซ็ตเซอร์โวเริ่มต้นที่ 0 องศา
  for (int i = 0; i < 4; i++) {
    servos[i].attach(SERVO_PINS[i]);
    servos[i].write(0);
    delay(80);
    servos[i].detach();
  }

  delay(1000);
  showStandby();

  Serial.println("[READY] ระบบพร้อมรับคำสั่งจาก Python AI ผ่าน Serial!");
  Serial.println("--------------------------------------------------------");
  Serial.println("คำสั่ง: BIN:0 (General), BIN:1 (Recycle), BIN:2 (Wet), BIN:3 (Hazard)");
  Serial.println("--------------------------------------------------------\n");
}

void loop() {
  // หากตอนบูตยังไม่พบจอ ให้ลองตรวจหาใหม่อัตโนมัติทุกๆ ครั้งที่เสียบสาย
  if (!oledFound && millis() % 3000 < 50) {
    initOled();
  }

  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.length() == 0) return;

    Serial.printf("[RECEIVED] คำสั่ง: '%s'\n", cmd.c_str());

    if (cmd.startsWith("BIN:")) {
      int bin = cmd.substring(4).toInt();
      if (bin >= 0 && bin <= 3) {
        Serial.printf("ACK:BIN:%d:OPENING\n", bin);
        openBin(bin);
        Serial.printf("ACK:BIN:%d:COMPLETED\n", bin);
      } else {
        Serial.println("ERR:INVALID_BIN");
      }
    } else if (cmd == "PING") {
      Serial.println("PONG:ESP32_S3_OLED_READY");
    }
  }
}
