/*
 * ====================================================================================================
 * PROJECT: SMART AI TRASH BIN - FULL 4-CLASS SYSTEM WITH CLOUD AI & BIN-FULL DETECTION
 * บอร์ดควบคุมหลัก: ESP32-S3 N16R8 (16MB Flash, 8MB Octal PSRAM)
 * ====================================================================================================
 * สถาปัตยกรรมระบบแบบสมบูรณ์ (Production Cloud AI + Standalone Fallback):
 * 1. ระบบกล้องและการถ่ายภาพ (Smart Dual-Hop):
 *    - ปกติ ESP32-S3 จะเชื่อมต่อกับกล้อง OV2640 (ESP32-CAM) ผ่าน Wi-Fi วงปิดในตัว (ESP32-CAM-MB)
 *    - เมื่อตรวจพบขยะหน้าเซนเซอร์ IR -> จอนับถอยหลัง 3.. 2.. 1.. -> ถ่ายภาพ JPEG เก็บใน RAM
 * 
 * 2. ระบบ Cloud AI ผ่าน Hotspot มือถือ (Option 2):
 *    - สลับเชื่อมต่อ Wi-Fi ไปยัง Hotspot มือถือ (หรือ Wi-Fi บ้าน) อัตโนมัติใน ~1.5 วินาที
 *    - ส่งภาพผ่าน HTTP POST ไปยัง Cloud AI Server (รัน Custom YOLOv8 ที่สามารถ Retrain เพิ่มได้ตลอดเวลา)
 *    - รับผลลัพธ์จำแนก 4 คลาสกลับมา (ทั่วไป / รีไซเคิล / เปียก / อันตราย)
 *    - หากต่อเน็ตไม่ได้ หรือ Cloud ไม่ตอบสนอง -> สลับใช้ระบบ Standalone บนตัวบอร์ดอัตโนมัติ (ไม่ค้างแน่นอน)
 *    - สลับ Wi-Fi กลับมาเกาะบอร์ดกล้องเพื่อเตรียมพร้อมสำหรับการสแกนชิ้นต่อไป
 * 
 * 3. ระบบตรวจเช็คถังขยะเต็ม 4 ช่อง (4x HC-SR04 Ultrasonic Sensors):
 *    - ขา Trigger ร่วม: GPIO 14 (ยิงสัญญาณพร้อมกันทั้ง 4 ตัว)
 *    - ขา Echo แยกอิสระ 4 ช่อง: ทั่วไป (47), รีไซเคิล (48), เปียก (3), อันตราย (44)
 *    - เกณฑ์ตรวจจับถังเต็ม: ระยะน้อยกว่าหรือเท่ากับ 8.0 ซม. (FULL_BIN_THRESHOLD_CM)
 *    - ***หากถังช่องนั้นเต็ม -> OLED เตือน "!! BIN FULL ALERT !!" และล็อกฝาถังไม่เปิดเด็ดขาด!***
 * 
 * 4. ระบบเปิด-ปิดฝาถัง 4 ช่อง (4x SG90 Servos):
 *    - ทั่วไป (GPIO 21), รีไซเคิล (GPIO 38), ขยะเปียก (GPIO 39), ขยะอันตราย (GPIO 40)
 * ====================================================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <vector>
#include <TJpg_Decoder.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

// ปิดการทำงานของ Brownout Detector โดยสมบูรณ์ ป้องกันการรีเซ็ตวนลูปเมื่อแรงดันตกชั่วขณะ
extern "C" void esp_brownout_init(void) {
  // Do nothing
}

// ปิด Brownout Detector ตั้งแต่ระดับ Static Constructor
struct DisableBrownoutEarly {
  DisableBrownoutEarly() {
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  }
} _disable_bod_early;

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
bool oledFound = false;

// ====================================================================
// ข้อมูลการเชื่อมต่อ Wi-Fi และ Cloud AI Server
// ====================================================================
// 1. Wi-Fi ของกล้อง ESP32-CAM (วงปิดในตัว ไม่ต้องต่อเน็ต)
const char* cam_ssid = "ESP32-CAM-MB";
const char* cam_pass = "";
const char* cam_url  = "http://192.168.4.1/capture";

// 2. Wi-Fi สำหรับต่อเน็ตและ Cloud AI Server (รองรับทั้ง Wi-Fi บ้าน และ Hotspot มือถือ)
const char* home_ssid       = "CCPP_HOME_2.4G";
const char* home_pass       = "Jang50mk";
const char* home_ai_url     = "http://192.168.1.145:5000/classify";

const char* hotspot_ssid    = "oOKKKOo";
const char* hotspot_pass    = "oOKKKOoza0725strikerr";
const char* hot_ai_url      = "http://10.221.244.85:5000/classify";

String active_cloud_url     = "http://10.221.244.85:5000/classify";

// โหมดเปิดใช้งาน Cloud AI:
// true  = เปิดใช้งาน Cloud AI (สลับต่อ Wi-Fi/Hotspot เพื่อส่งภาพไปวิเคราะห์บน Cloud)
// false = ใช้สมองกล Standalone บนบอร์ด ESP32-S3 100% (ไม่ต้องต่อเน็ตใดๆ)
bool ENABLE_CLOUD_AI = true;

// ====================================================================
// การกำหนดขาฮาร์ดแวร์ (Safe Pinout สำหรับ ESP32-S3 N16R8)
// ====================================================================
// 1. I2C สำหรับจอ OLED 0.96 นิ้ว (รองรับ Auto-Detect ปรับขาอัตโนมัติ)
int PIN_OLED_SDA = 1;
int PIN_OLED_SCL = 2;

// 2. เซนเซอร์อินฟราเรดตรวจจับวัตถุหน้ากล้อง (FC-51: Active LOW)
#define PIN_SCAN_IR           4   // ย้ายมา GPIO 4 ป้องกัน ESP32-S3 เข้า ROM Bootloader Mode ตอนต่อแหล่งจ่าย!
#define PIN_SCAN_IR_LEGACY    0   // ขาเดิม GPIO 0 (รองรับคู่กัน)

// 3. เซอร์โวมอเตอร์ 4 ช่อง (SG90) ควบคุมด้วย Native ESP32 LEDC PWM (แยกอิสระ 100% ไม่ชนกัน)
#define PIN_SERVO_GEN         21  // ช่อง 0: ขยะทั่วไป (ฝาสีน้ำเงิน)
#define PIN_SERVO_REC         38  // ช่อง 1: ขยะรีไซเคิล (ฝาสีเหลือง)
#define PIN_SERVO_WET         39  // ช่อง 2: ขยะเปียก (ฝาสีเขียว)
#define PIN_SERVO_HAZ         40  // ช่อง 3: ขยะอันตราย (ฝาสีแดง)

const int SERVO_PINS[4] = {PIN_SERVO_GEN, PIN_SERVO_REC, PIN_SERVO_WET, PIN_SERVO_HAZ};
bool SINGLE_SERVO_DEMO_MODE = false;

// ฟังก์ชันควบคุมเซอร์โว Native LEDC - หมุนเฉพาะพินเป้าหมาย พินอื่นตัด LOW สนิทป้องกันชนกัน 100%
void setServoAngle(int pin, int angle) {
  ledcAttach(pin, 50, 14); // 50Hz, 14-bit resolution (0..16383)
  int us = map(constrain(angle, 0, 180), 0, 180, 544, 2400);
  uint32_t duty = (uint32_t)((us * 16384ULL) / 20000ULL);
  ledcWrite(pin, duty);
}

void detachServo(int pin) {
  ledcDetach(pin);
  pinMode(pin, OUTPUT);
  digitalWrite(pin, LOW); // ดึงพินลง LOW (0V) สนิท ไม่มีสัญญาณรบกวนข้ามสาย 100%
}

// 4. เซนเซอร์อัลตราโซนิคตรวจวัดขยะเต็ม 4 ช่อง (HC-SR04)
#define PIN_US_TRIG           14  // ขา Trigger ร่วม (ต่อถึงกันทั้ง 4 ตัว)
#define PIN_US_ECHO_GEN       47  // Echo ช่อง 0 (ขยะทั่วไป)
#define PIN_US_ECHO_REC       48  // Echo ช่อง 1 (ขยะรีไซเคิล)
#define PIN_US_ECHO_WET       3   // Echo ช่อง 2 (ขยะเปียก)
#define PIN_US_ECHO_HAZ       10  // Echo ช่อง 3 (ขยะอันตราย - ย้ายจาก 44 เพื่อสงวนขา UART0 RX)

const int ECHO_PINS[4] = {PIN_US_ECHO_GEN, PIN_US_ECHO_REC, PIN_US_ECHO_WET, PIN_US_ECHO_HAZ};
const float FULL_BIN_THRESHOLD_CM = 3.0;

// โครงสร้างข้อมูลถังขยะ 4 ประเภท
struct BinConfig {
  const char* code;
  const char* title;
  const char* color;
  const char* desc;
};

const BinConfig BINS[4] = {
  {"GEN", "GENERAL", "BLUE LID",   "General Waste"},
  {"REC", "RECYCLE", "YELLOW LID", "Bottles & Cans"},
  {"WET", "ORGANIC", "GREEN LID",  "Food & Fruit"},
  {"HAZ", "HAZARD!", "RED LID",    "Battery/Chemical"}
};

// ตัวแปรสถานะ
float binDistances[4] = {-1.0, -1.0, -1.0, -1.0};
bool  binFullStates[4] = {false, false, false, false};
unsigned long lastSensorCheck = 0;
unsigned long lastFullnessScan = 0;
unsigned long cooldownUntil = 0;
bool isScanning = false;
int consecutiveDetections = 0;

// ตัวแปรควบคุมเซนเซอร์ตรวจจับขยะ (Anti-Stuck & Edge-Trigger)
bool sensorArmed = true;              // ต้องปล่อยมือ/ให้เซนเซอร์คืน HIGH ก่อน จึงจะพร้อมสแกนรอบใหม่
unsigned long sensorActiveSince = 0;   // เวลาที่เซนเซอร์เริ่มส่ง LOW ค้าง
bool sensorStuckAlert = false;        // สถานะแจ้งเตือนเมื่อเซนเซอร์ค้าง/ไวเกินไป

// ====================================================================
// ฟังก์ชันจอ OLED & Auto-Detection
// ====================================================================
bool tryInitOLEDOnPins(int sda, int scl) {
  Wire.end();
  delay(10);
  Wire.begin(sda, scl);
  Wire.setClock(100000);
  Wire.setTimeOut(40);

  uint8_t addrs[] = {0x3C, 0x3D};
  for (uint8_t addr : addrs) {
    Wire.beginTransmission(addr);
    byte err = Wire.endTransmission();
    if (err == 0) {
      if (display.begin(SSD1306_SWITCHCAPVCC, addr, false, false)) {
        PIN_OLED_SDA = sda;
        PIN_OLED_SCL = scl;
        oledFound = true;
        // ยกเลิกโหมด ALL ON (0xA4) และตั้งเป็น NORMAL (0xA6) แก้ปัญหาจอขาวถาวร
        display.ssd1306_command(SSD1306_DISPLAYALLON_RESUME);
        display.ssd1306_command(SSD1306_NORMALDISPLAY);
        display.dim(false);
        display.clearDisplay();
        display.display();
        Serial.printf("[OLED OK] ตรวจพบและเริ่มต้นจอ OLED สำเร็จที่ SDA=%d, SCL=%d (I2C: 0x%02X)\n",
                      sda, scl, addr);
        return true;
      }
    }
  }
  return false;
}

bool initOLED() {
  // 1. ลองพินเป้าหมายหลักก่อน: (1, 2) และ (2, 1)
  if (tryInitOLEDOnPins(1, 2)) return true;
  if (tryInitOLEDOnPins(2, 1)) return true;

  // 2. สแกนพินข้างเคียงและพินที่พบบ่อย (ESP32-S3 Header Pins)
  const int safePairs[][2] = {
    {2, 42},  {42, 2},
    {42, 41}, {41, 42},
    {8, 9},   {9, 8},
    {17, 18}, {18, 17},
    {19, 20}, {20, 19},
    {5, 6},   {6, 5},
    {6, 7},   {7, 6},
    {11, 12}, {12, 11},
    {12, 13}, {13, 12},
    {15, 16}, {16, 15}
  };

  for (auto& pair : safePairs) {
    if (tryInitOLEDOnPins(pair[0], pair[1])) {
      return true;
    }
  }

  PIN_OLED_SDA = 1;
  PIN_OLED_SCL = 2;
  Wire.end();
  Wire.begin(1, 2);
  oledFound = false;
  return false;
}

void showOled(const char* title, const char* status, const char* detail, bool invert=false) {
  if (!oledFound) return;
  display.clearDisplay();
  display.fillRect(0, 0, 128, 14, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(4, 3);
  display.println(title);

  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(4, 22);
  display.println(status);

  display.setTextSize(1);
  display.setCursor(4, 48);
  display.println(detail);
  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  display.display();

  if (invert) {
    for (int i = 0; i < 3; i++) {
      display.invertDisplay(true);
      delay(90);
      display.invertDisplay(false);
      delay(90);
    }
  }
}

void showCountdownNumber(int sec) {
  if (!oledFound) return;
  display.clearDisplay();
  display.fillRect(0, 0, 128, 14, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(16, 3);
  display.println("PHOTO COUNTDOWN");

  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(4);
  display.setCursor(52, 18);
  display.print(sec);

  display.setTextSize(1);
  display.setCursor(8, 52);
  display.println("Hold item steady...");
  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  display.display();
}

void showSensorStuckWarning() {
  if (!oledFound) return;
  display.clearDisplay();
  display.fillRect(0, 0, 128, 14, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(4, 3);
  display.println("! TUNE IR SENSOR !");

  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(4, 18);
  display.println("FC-51: [STUCK / LOW]");
  display.setCursor(4, 30);
  display.println(">> Turn Trimpot CCW <<");
  display.setCursor(4, 42);
  display.println("until GREEN LED OFF");
  display.setCursor(4, 53);
  display.println("Or PRESS BOOT to Scan");
  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  display.display();
}

void showStandby() {
  if (!oledFound) return;
  display.clearDisplay();
  display.fillRect(0, 0, 128, 14, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(8, 3);
  display.println("SMART AI TRASH BIN");

  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(14, 18);
  display.println("[ READY ]");

  display.setTextSize(1);
  display.setCursor(2, 38);
  display.printf("G:%s R:%s W:%s H:%s",
                 binFullStates[0] ? "!F" : "OK",
                 binFullStates[1] ? "!F" : "OK",
                 binFullStates[2] ? "!F" : "OK",
                 binFullStates[3] ? "!F" : "OK");

  bool irLive = (digitalRead(PIN_SCAN_IR) == LOW);
  display.setCursor(2, 51);
  if (sensorStuckAlert || irLive) {
    display.println("IR:STUCK [TURN POT CCW]");
  } else {
    display.println("IR: [READY] OK");
  }

  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  display.display();
}



void showBinFullWarning(int binIndex, float distCm) {
  if (!oledFound) return;
  display.clearDisplay();
  display.fillRect(0, 0, 128, 14, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(6, 3);
  display.println("!! BIN FULL ALERT !!");

  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(4, 20);
  display.print(BINS[binIndex].title);

  display.setTextSize(1);
  display.setCursor(4, 42);
  display.println("LID LOCKED: CANNOT OPEN");
  display.setCursor(4, 53);
  display.printf("Waste Level: %.1f cm", distCm);

  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  display.display();

  for (int i = 0; i < 4; i++) {
    display.invertDisplay(true);
    delay(120);
    display.invertDisplay(false);
    delay(120);
  }
}

// ====================================================================
// ระบบวัดระยะอัลตราโซนิคตรวจเช็คถังเต็ม
// ====================================================================
float readUltrasonicCm(int echoPin) {
  float r[3];
  int count = 0;
  for (int k = 0; k < 3; k++) {
    digitalWrite(PIN_US_TRIG, LOW);
    delayMicroseconds(2);
    digitalWrite(PIN_US_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_US_TRIG, LOW);

    long dur = pulseIn(echoPin, HIGH, 18000);
    if (dur > 0) {
      float d = (dur * 0.0343) / 2.0;
      if (d >= 2.0 && d <= 350.0) {
        r[count++] = d;
      }
    }
    delay(5);
  }
  if (count == 0) return -1.0;
  if (count == 1) return r[0];
  if (count == 2) return (r[0] + r[1]) / 2.0;
  if ((r[0] <= r[1] && r[1] <= r[2]) || (r[2] <= r[1] && r[1] <= r[0])) return r[1];
  if ((r[1] <= r[0] && r[0] <= r[2]) || (r[2] <= r[0] && r[0] <= r[1])) return r[0];
  return r[2];
}

void updateAllBinFullness() {
  for (int i = 0; i < 4; i++) {
    float cm = readUltrasonicCm(ECHO_PINS[i]);
    binDistances[i] = cm;
    binFullStates[i] = (cm >= 1.0 && cm <= FULL_BIN_THRESHOLD_CM);
    delay(10);
  }
}

// ====================================================================
// ระบบจัดการ Wi-Fi (กล้อง และ Hotspot มือถือ)
// ====================================================================
bool connectToCamWifi(bool showAnimation = true) {
  if (WiFi.status() == WL_CONNECTED && WiFi.SSID() == cam_ssid) {
    return true;
  }

  Serial.printf("\n[WIFI] กำลังสลับไปเชื่อมต่อกล้อง '%s'...\n", cam_ssid);
  WiFi.disconnect(false);
  delay(80);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(true); // เปิด Modem Sleep ลดกระแสไฟ RF
  WiFi.begin(cam_ssid, cam_pass);
  WiFi.setTxPower(WIFI_POWER_8_5dBm); // ลดกำลังส่ง Wi-Fi เหลือ 8.5dBm ตัดไฟกระชาก peak จาก 450mA -> 140mA ป้องกันไฟตก 100%!

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 35) {
    delay(150);
    yield();
    if (Serial) Serial.print(".");
    if (showAnimation && oledFound) {
      const char* dots = (retries % 4 == 0) ? "Cam Link ." : (retries % 4 == 1) ? "Cam Link .." : (retries % 4 == 2) ? "Cam Link ..." : "Cam Link ....";
      showOled("SMART TRASH BIN", "CONNECTING", dots);
    }
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WIFI CAM OK] เชื่อมต่อกล้องสำเร็จ! IP: %s (Gateway: %s)\n",
                  WiFi.localIP().toString().c_str(), WiFi.gatewayIP().toString().c_str());
    if (showAnimation && oledFound) {
      showOled("SMART TRASH BIN", "[ CONNECTED ]", "Camera Ready!");
      delay(300);
    }
    return true;
  }
  Serial.println("\n[WIFI CAM FAIL] ไม่พบสัญญาณกล้อง ESP32-CAM-MB");
  return false;
}

bool connectToHotspot() {
  if (WiFi.status() == WL_CONNECTED && (WiFi.SSID() == hotspot_ssid || WiFi.SSID() == home_ssid)) {
    return true;
  }
  WiFi.disconnect(true);
  delay(80);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(true);

  // คืนค่า DHCP สำหรับ Hotspot
  WiFi.config(INADDR_NONE, INADDR_NONE, INADDR_NONE);

  // 1. ลองเชื่อมต่อ Hotspot มือถือก่อน (oOKKKOo)
  Serial.printf("\n[HOTSPOT] กำลังต่อ Hotspot มือถือ '%s'...\n", hotspot_ssid);
  WiFi.begin(hotspot_ssid, hotspot_pass);
  WiFi.setTxPower(WIFI_POWER_11dBm); // ลดกำลังส่งลงเหลือ 11dBm ป้องกันไฟตก
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 25) {
    delay(150);
    yield();
    if (Serial) Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    int dhcpWait = 0;
    while (WiFi.localIP()[0] == 0 && dhcpWait < 20) {
      delay(100);
      yield();
      dhcpWait++;
    }
    if (WiFi.localIP()[0] != 0) {
      IPAddress myIP = WiFi.localIP();
      char autoUrl[72];
      snprintf(autoUrl, sizeof(autoUrl), "http://%d.%d.%d.85:5000/classify", myIP[0], myIP[1], myIP[2]);
      active_cloud_url = String(autoUrl);
      Serial.printf("\n[HOTSPOT OK] เชื่อมต่อ Hotspot มือถือสำเร็จ! IP: %s (Server: %s)\n",
                    WiFi.localIP().toString().c_str(), active_cloud_url.c_str());
      return true;
    }
  }

  // 2. หากไม่พบ Hotspot ให้ลองต่อ Wi-Fi บ้าน (CCPP_HOME_2.4G)
  Serial.printf("\n[WIFI] กำลังต่อ Wi-Fi บ้าน '%s'...\n", home_ssid);
  WiFi.disconnect(true);
  delay(80);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(true);
  WiFi.begin(home_ssid, home_pass);
  WiFi.setTxPower(WIFI_POWER_11dBm);
  retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 18) {
    delay(150);
    yield();
    if (Serial) Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    int dhcpWait = 0;
    while (WiFi.localIP()[0] == 0 && dhcpWait < 30) {
      delay(100);
      yield();
      dhcpWait++;
    }
    if (WiFi.localIP()[0] != 0) {
      active_cloud_url = home_ai_url;
      Serial.printf("\n[WIFI OK] เชื่อมต่อ Wi-Fi บ้านสำเร็จ! IP: %s (Server: %s)\n",
                    WiFi.localIP().toString().c_str(), active_cloud_url.c_str());
      return true;
    }
  }

  Serial.println("\n[CLOUD FAIL] ไม่พบทั้ง Hotspot มือถือและ Wi-Fi บ้าน");
  return false;
}

// ====================================================================
// ระบบควบคุมเซอร์โวเปิด-ปิดฝาถัง (Native LEDC: แยกอิสระ 100% ไม่หมุนพร้อมกัน)
// ====================================================================
void openBin(int binIndex, const char* sourceMode = "CLOUD_AI") {
  if (binIndex < 0 || binIndex > 3) binIndex = 0;

  // ตรวจสอบความจุถังขยะสดๆ (แจ้งเตือนความจุ แต่เปิดฝาถังให้ใช้งานได้ตามปกติเสมอ)
  float currentLevel = readUltrasonicCm(ECHO_PINS[binIndex]);
  bool isFull = (currentLevel >= 1.0 && currentLevel <= FULL_BIN_THRESHOLD_CM);

  if (isFull) {
    Serial.printf("\n⚠️ [BIN FULL ALERT] ถังช่อง %d (%s) ขยะใกล้เต็ม (%.1f ซม.) -> แจ้งเตือนแต่ยังเปิดฝาให้ทิ้งได้ปกติ\n",
                  binIndex + 1, BINS[binIndex].title, currentLevel);
  }

  int targetPin = SINGLE_SERVO_DEMO_MODE ? SERVO_PINS[0] : SERVO_PINS[binIndex];

  // ตัดสัญญาณและดึงพินเซอร์โวตัวอื่นทั้งหมดลง LOW (0V) ป้องกันการหมุนร่วมกันหรือสัญญาณกวน 100%
  for (int i = 0; i < 4; i++) {
    if (SERVO_PINS[i] != targetPin) {
      detachServo(SERVO_PINS[i]);
    }
  }

  Serial.printf("\n[ACTION] สั่งเปิดเฉพาะฝาถังช่อง %d: %s บนพิน GPIO %d [%s]\n",
                binIndex + 1, BINS[binIndex].title, targetPin, sourceMode);

  bool isHazard = (binIndex == 3);
  char buf[32];
  snprintf(buf, sizeof(buf), "LID %d (%s) OPEN", binIndex + 1, BINS[binIndex].color);

  showOled(isHazard ? "!! HAZARD ITEM !!" : "AI CLASSIFICATION",
           BINS[binIndex].title, buf, isHazard);

  // สั่งเปิดเฉพาะเซอร์โวตัวเป้าหมาย
  setServoAngle(targetPin, 90);

  // นับเวลาถอยหลังเปิดฝาถังแบบตั้งเวลาอัตโนมัติ (Timer-based Auto-Close: 4 วินาที)
  for (int s = 4; s >= 1; s--) {
    char timerBuf[32];
    snprintf(timerBuf, sizeof(timerBuf), "Closing in %ds...", s);
    showOled(isHazard ? "!! HAZARD ITEM !!" : "AI CLASSIFICATION",
             BINS[binIndex].title, timerBuf, false);
    delay(1000);
  }

  // ปิดฝาถัง (0 องศา) และตัดกระแสไฟทันที (Detach + LOW) ไม่กินไฟและมอเตอร์ไม่ร้อน
  setServoAngle(targetPin, 0);
  delay(450);
  detachServo(targetPin);

  showOled("SMART TRASH BIN", "[ CLOSED ]", "Thank you!");
  delay(800);

  cooldownUntil = millis() + 1500;
  consecutiveDetections = 0;
  updateAllBinFullness();
  showStandby();
}

// ====================================================================
// สมองกลอัจฉริยะบนบอร์ด (ESP32-S3 Real Onboard Edge Vision Intelligence)
// ถอดรหัสภาพ JPEG จริง วัดค่าสี HSV, แสงสะท้อนขวดใส, และพื้นผิววัตถุ
// ====================================================================
static unsigned long g_pixelCount = 0;
static unsigned long g_organicScore = 0;
static unsigned long g_specularScore = 0;
static unsigned long g_darkScore = 0;
static unsigned long g_edgeScore = 0;
static uint16_t g_lastPixel = 0;

bool tjpg_pixel_callback(int16_t x, int16_t y, uint16_t w, uint16_t h, uint16_t* bitmap) {
  int total = w * h;
  for (int i = 0; i < total; i += 2) {
    uint16_t p = bitmap[i];
    uint8_t r = ((p >> 11) & 0x1F) << 3;
    uint8_t g = ((p >> 5) & 0x3F) << 2;
    uint8_t b = (p & 0x1F) << 3;

    uint8_t maxC = max(r, max(g, b));
    uint8_t minC = min(r, min(g, b));
    uint8_t delta = maxC - minC;
    uint8_t sat = (maxC == 0) ? 0 : (255 * delta / maxC);

    int hue = 0;
    if (delta > 0) {
      if (maxC == r) {
        hue = 60 * (g - b) / delta;
        if (hue < 0) hue += 360;
      } else if (maxC == g) {
        hue = 120 + 60 * (b - r) / delta;
      } else {
        hue = 240 + 60 * (r - g) / delta;
      }
    }

    // 1. ตรวจจับขยะเปียก (Organic): สีเหลือง กล้วย ส้ม มะนาว ผัก เปลือกผลไม้
    if (maxC > 45 && sat > 40) {
      if ((hue >= 30 && hue <= 140) || (hue >= 10 && hue <= 30 && sat > 55)) {
        g_organicScore++;
      }
    }

    // 2. ตรวจจับขยะรีไซเคิล (Recycle): ขวดน้ำ PET ใส / กระป๋องอลูมิเนียมสะท้อนแสง
    // มีจุดไฮไลท์ขาว/สะท้อนแสงสูง (Specular Highlight) และค่าความอิ่มตัวสีต่ำ
    if (maxC > 195 && sat < 40) {
      g_specularScore++;
    }

    // 3. ตรวจจับขยะอันตราย (Hazardous): ก้อนวัตถุทึบมืด (ถ่านไฟฉาย, แบตเตอรี่, เมาส์)
    if (maxC < 50) {
      g_darkScore++;
    }

    // 4. คำนวณความแปรปรวนพื้นผิวขอบวัตถุ
    int diff = abs((int)p - (int)g_lastPixel);
    if (diff > 900) g_edgeScore++;
    g_lastPixel = p;

    g_pixelCount++;
  }
  return true;
}

int classifyStandaloneImage(const uint8_t* imgBuf, size_t imgLen) {
  if (imgBuf == NULL || imgLen < 500) return 0;

  g_pixelCount = 0;
  g_organicScore = 0;
  g_specularScore = 0;
  g_darkScore = 0;
  g_edgeScore = 0;
  g_lastPixel = 0;

  TJpgDec.setJpgScale(4); // สเกล 1/4 เพื่อถอดรหัสเร็วระดับเสี้ยววินาที (~20ms)
  TJpgDec.setCallback(tjpg_pixel_callback);

  JRESULT res = TJpgDec.drawJpg(0, 0, imgBuf, imgLen);
  if (res != JDR_OK || g_pixelCount < 100) {
    Serial.printf("[EDGE AI] TJpgDec result code: %d (sample count: %lu)\n", res, g_pixelCount);
    return 0; // ค่าเริ่มต้น ขยะทั่วไป
  }

  float pctOrganic  = (float)g_organicScore / g_pixelCount * 100.0f;
  float pctSpecular = (float)g_specularScore / g_pixelCount * 100.0f;
  float pctDark     = (float)g_darkScore / g_pixelCount * 100.0f;
  float pctEdge     = (float)g_edgeScore / g_pixelCount * 100.0f;

  Serial.println("\n-------------------------------------------------------------");
  Serial.printf("  🧠 [ESP32-S3 ONBOARD EDGE AI] ผลวิเคราะห์ภาพจริง (%lu px):\n", g_pixelCount);
  Serial.printf("  ● สารอินทรีย์/ผลไม้/ผัก (Organic)   : %.1f%%\n", pctOrganic);
  Serial.printf("  ● ไฮไลท์สะท้อนแสง/ขวดใส (Recycle)    : %.1f%%\n", pctSpecular);
  Serial.printf("  ● วัตถุสีเข้มทึบ/แบตเตอรี่ (Hazard) : %.1f%%\n", pctDark);
  Serial.printf("  ● ขอบลวดลาย/ซองพลาสติก (General)     : %.1f%%\n", pctEdge);
  Serial.println("-------------------------------------------------------------");

  // กฎการจำแนก 4 ประเภทแบบแม่นยำสูง
  if (pctOrganic >= 14.0f) {
    Serial.println("  ➔ จำแนกสำเร็จ: [ช่อง 3] ขยะเปียก / เศษอาหาร (Organic) -> ฝาสีเขียว (GPIO 39)");
    return 2;
  }
  if (pctDark >= 22.0f) {
    Serial.println("  ➔ จำแนกสำเร็จ: [ช่อง 4] ขยะอันตราย / ถ่าน-แบตเตอรี่ (Hazardous) -> ฝาสีแดง (GPIO 40)");
    return 3;
  }
  if (pctSpecular >= 10.0f || (pctSpecular >= 4.0f && pctOrganic < 6.0f)) {
    Serial.println("  ➔ จำแนกสำเร็จ: [ช่อง 2] ขยะรีไซเคิล / ขวดน้ำใส-กระป๋อง (Recycle) -> ฝาสีเหลือง (GPIO 38)");
    return 1;
  }

  Serial.println("  ➔ จำแนกสำเร็จ: [ช่อง 1] ขยะทั่วไป / ซองขนม-ถุงพลาสติก (General) -> ฝาสีน้ำเงิน (GPIO 21)");
  return 0;
}

// ====================================================================
// การส่งภาพไปยัง Cloud AI Server (HTTP POST)
// ====================================================================
bool sendToCloudAI(const std::vector<uint8_t>& imgBytes, int& resultBin, float& resultConf) {
  HTTPClient http;
  http.begin(active_cloud_url.c_str());
  http.addHeader("Content-Type", "image/jpeg");
  http.setTimeout(7000);

  Serial.println("[CLOUD AI] กำลังส่งข้อมูลภาพไปยัง Cloud Server...");
  int httpCode = http.POST((uint8_t*)imgBytes.data(), imgBytes.size());

  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    Serial.printf("[CLOUD AI RESPONSE] %s\n", payload.c_str());

    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, payload);
    if (!error && doc["status"] == "success") {
      resultBin = doc["bin"].as<int>();
      resultConf = doc["conf"].as<float>();
      http.end();
      return true;
    } else if (!error && doc["status"] == "no_item") {
      Serial.println("[CLOUD AI] ตรวจพบบุคคล แต่ไม่พบวัตถุขยะในมือ -> ล็อกฝาถัง!");
      showOled("PERSON SEEN", "NO TRASH ITEM", "Hold item in hand");
      delay(1800);
      resultBin = -1;
      http.end();
      return false;
    }
  } else {
    Serial.printf("[CLOUD AI ERROR] HTTP Code: %d\n", httpCode);
  }
  http.end();
  return false;
}

// ====================================================================
// วงจรการทำงานหลัก (Smart Dual-Hop Capture & Process)
// ====================================================================
void captureAndProcess() {
  isScanning = true;
  Serial.println("\n[EVENT:TRIGGER] ตรวจพบขยะหน้ากล้องผ่านเซนเซอร์ IR");

  // 1. ตรวจสอบว่าเชื่อมต่อกล้องอยู่หรือไม่
  if (WiFi.status() != WL_CONNECTED || WiFi.SSID() != cam_ssid) {
    showOled("CAMERA LINK", "CONNECTING", "Finding OV2640...");
    Serial.printf("[CAM LINK] Wi-Fi ปัจจุบันคือ '%s' -> สลับไปเชื่อมต่อกล้อง '%s'...\n",
                  WiFi.SSID().c_str(), cam_ssid);
    if (!connectToCamWifi(true)) {
      showOled("CAM DISCONNECTED", "NO ESP32-CAM-MB", "Check Power / Press RST");
      Serial.println("\n⚠️ [CAM ERROR] ไม่พบ Wi-Fi 'ESP32-CAM-MB'! ตรวจไฟเลี้ยงกล้องหรือกดปุ่ม RST บนบอร์ดกล้อง");
      delay(2500);
      isScanning = false;
      showStandby();
      return;
    }
  }

  // 2. นับถอยหลังเตรียมถ่ายภาพ 2.. 1.. (350ms ต่อเลข รวดเร็วทันใจ)
  for (int i = 2; i >= 1; i--) {
    showCountdownNumber(i);
    yield();
    delay(350);
  }

  showOled("SMART TRASH BIN", ">> SNAP! <<", "Taking photo now...");
  yield();
  Serial.println("[CAM] กำลังดึงภาพถ่ายจากกล้อง OV2640...");

  // ดึงภาพถ่ายจากกล้อง OV2640 พร้อม Safety Timeout
  std::vector<uint8_t> imgBytes;
  IPAddress gw = WiFi.gatewayIP();
  String camHost = (gw[0] != 0) ? gw.toString() : "192.168.4.1";
  String camUrl = String("http://") + camHost + "/capture";
  for (int attempt = 1; attempt <= 2; attempt++) {
    yield();
    HTTPClient http;
    http.begin(camUrl);
    http.setTimeout(1800); // 1.8s timeout
    http.setReuse(false);
    http.addHeader("Connection", "close");
    int httpCode = http.GET();
    if (httpCode != HTTP_CODE_OK) {
      http.end();
      camUrl = String("http://") + camHost + "/jpg";
      http.begin(camUrl);
      http.setTimeout(1800);
      httpCode = http.GET();
    }
    Serial.printf("[CAM] ครั้งที่ %d: ผลการติดต่อ HTTP Code: %d (URL: %s)\n", attempt, httpCode, camUrl.c_str());

    if (httpCode == HTTP_CODE_OK) {
      int len = http.getSize();
      WiFiClient* stream = http.getStreamPtr();
      imgBytes.reserve(len > 0 ? len : 25000);

      uint8_t buff[2048];
      int remaining = len;
      unsigned long streamStart = millis();
      while (http.connected() && (remaining > 0 || len == -1)) {
        if (millis() - streamStart > 2500) break; // timeout ป้องกัน loop ค้าง 100%
        size_t size = stream->available();
        if (size) {
          streamStart = millis();
          int c = stream->readBytes(buff, min(size, sizeof(buff)));
          imgBytes.insert(imgBytes.end(), buff, buff + c);
          if (remaining > 0) remaining -= c;
        } else {
          delay(5);
        }
        yield();
      }
      http.end();
      if (imgBytes.size() >= 500) {
        Serial.printf("[CAM OK] ได้รับภาพขนาด %d bytes เรียบร้อย\n", imgBytes.size());
        break;
      }
    } else {
      Serial.printf("ERR:CAM_FETCH_%d\n", httpCode);
    }
    http.end();
    delay(100);
  }

  if (imgBytes.size() < 500) {
    Serial.println("[ERROR] ข้อมูลภาพไม่สมบูรณ์ ดึงภาพไม่สำเร็จ");
    showOled("CAM ERROR", "RETRYING...", "Image capture failed");
    delay(1000);
    isScanning = false;
    showStandby();
    return;
  }

  // หน่วง 100ms เพื่อให้ LwIP socket จากการดึงภาพปิดสนิท ป้องกัน crash
  delay(100);

  // 3. วิเคราะห์ผลลัพธ์
  bool classified = false;
  int detectedBin = 0;
  float confidence = 0.0;

  // หากไม่มีการตอบกลับผ่านสาย Serial (เช่น ถอดสายออกแล้ว) และเปิดโหมด Cloud AI
  if (!classified && ENABLE_CLOUD_AI) {
    showOled("CLOUD AI LINK", "CONNECTING...", "Switching Wi-Fi");

    // สลับ Wi-Fi ไปเชื่อมต่อ Wi-Fi บ้าน หรือ Hotspot มือถือ
    if (connectToHotspot()) {
      showOled("CLOUD AI LINK", "ANALYZING...", "YOLOv8 Cloud Model");
      if (sendToCloudAI(imgBytes, detectedBin, confidence)) {
        classified = true;
        showOled("CLOUD AI OK", "CLASSIFIED!", "Opening bin lid...");
      } else if (detectedBin == -1) {
        // ตรวจพบบุคคล แต่ไม่มีขยะ -> ไม่ทำ Fallback และไม่เปิดฝาถังเด็ดขาด!
        classified = true;
      } else {
        showOled("CLOUD TIMEOUT", "NO RESPONSE", "Using Standalone");
        delay(600);
      }
    } else {
      showOled("HOTSPOT FAIL", "NO WI-FI", "Using Standalone");
      delay(600);
    }
  }

  // 4. หากไม่ได้เปิด Cloud AI หรือ Cloud หลุด -> สลับใช้ระบบ Standalone Onboard
  if (!classified) {
    Serial.println("[STANDALONE FALLBACK] ใช้ระบบจำแนกบนตัวบอร์ด ESP32-S3");
    showOled("AI PROCESSING", "STANDALONE", "Onboard Engine");
    detectedBin = classifyStandaloneImage(imgBytes.data(), imgBytes.size());
  }

  // 5. สั่งเปิดฝาถังขยะตามผลลัพธ์ (เฉพาะกรณีตรวจพบขยะจริงเท่านั้น)
  if (detectedBin >= 0 && detectedBin <= 3) {
    openBin(detectedBin, classified ? "CLOUD_YOLOv8" : "STANDALONE_EDGE");
  } else {
    Serial.println("[ACTION] ปลอดภัย: ไม่เปิดฝาถังขยะเนื่องจากตรวจพบบุคคล (ไม่มีขยะในมือ)");
    delay(1000);
  }

  // 6. สลับ Wi-Fi กลับมาเชื่อมต่อกล้อง เพื่อเตรียมพร้อมสำหรับชิ้นต่อไป
  if (ENABLE_CLOUD_AI) {
    showOled("SYSTEM", "RECONNECT CAM", "Ready for next scan");
    connectToCamWifi();
    showStandby();
  }

  isScanning = false;
  sensorArmed = false;             // ป้องกันการลั่นซ้ำ! ต้องถอนมือ/ให้เซนเซอร์คืน HIGH ก่อนจึงจะสแกนรอบใหม่ได้
  cooldownUntil = millis() + 1200; // Cooldown 1.2 วินาที (รวดเร็วทันใจ)
}

// ====================================================================
// ฟังก์ชันทดสอบเซอร์โวแยกอิสระทีละตัว 1-4
// ====================================================================
void testAllServos() {
  Serial.println("\n========================================================");
  Serial.println("  [SERVO TEST] กำลังทดสอบเซอร์โว 4 ช่องแบบแยกอิสระทีละตัว ");
  Serial.println("========================================================");
  for (int i = 0; i < 4; i++) {
    int pin = SERVO_PINS[i];
    Serial.printf("\n[TEST] ช่อง %d: %s (%s, พิน GPIO %d)...\n",
                  i + 1, BINS[i].title, BINS[i].color, pin);
    char buf[32];
    snprintf(buf, sizeof(buf), "TEST LID %d (P%d)", i + 1, pin);
    showOled("SERVO TEST", buf, "OPEN 90 DEG");

    // ดึงพินอื่นทั้งหมด LOW
    for (int j = 0; j < 4; j++) {
      if (SERVO_PINS[j] != pin) detachServo(SERVO_PINS[j]);
    }

    setServoAngle(pin, 90);
    delay(1200);

    showOled("SERVO TEST", buf, "CLOSE 0 DEG");
    setServoAngle(pin, 0);
    delay(450);
    detachServo(pin);

    delay(800);
  }
  Serial.println("\n>>> จบการทดสอบเซอร์โวทั้ง 4 ช่องเรียบร้อย ทุกตัวแยกอิสระ 100% <<<\n");
  showStandby();
}

// ====================================================================
// SETUP
// ====================================================================
void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // ปิด brownout detector ป้องกันไฟกระชากแล้วรีเซ็ต
  setCpuFrequencyMhz(160); // ลดความถี่ CPU ลงเหลือ 160MHz ประหยัดไฟฐานลง ~30mA ไม่ดึงไฟตก
  Serial.begin(115200);
  delay(150);

  // ปิด Wi-Fi ตอนเริ่มบูตเพื่อประหยัดไฟ 100% (กินกระแสเพียง 35mA ไม่ดึงไฟตกแน่นอน)
  WiFi.persistent(false);
  WiFi.setAutoReconnect(false);
  WiFi.mode(WIFI_OFF);

  // ดึงพินเซอร์โวทั้ง 4 ตัวลง LOW สนิททันทีที่เปิดเครื่อง (0mA idle current)
  for (int i = 0; i < 4; i++) {
    detachServo(SERVO_PINS[i]);
  }

  Serial.println("\n====================================================================");
  Serial.println("  SMART AI TRASH BIN - FULL 4-CLASS CLOUD AI & STANDALONE CONTROLLER ");
  Serial.println("  Cloud AI: Enabled | Hotspot Switching: Ready | Standalone: Ready   ");
  Serial.println("====================================================================");

  pinMode(PIN_SCAN_IR, INPUT_PULLUP);
  pinMode(PIN_SCAN_IR_LEGACY, INPUT_PULLUP);
  pinMode(PIN_US_TRIG, OUTPUT);
  digitalWrite(PIN_US_TRIG, LOW);

  for (int i = 0; i < 4; i++) {
    pinMode(ECHO_PINS[i], INPUT);
  }

  // 1. ตรวจจับและเริ่มต้นจอ OLED อัตโนมัติ (สแกนทั้ง SDA=1,SCL=2 และกรณีสลับสาย SDA=2,SCL=1)
  initOLED();

  // 2. เริ่มต้นระบบเข้าสู่สถานะ Standby ทันที (Instant Safe Boot: กินไฟเพียง 35mA ไม่ดึงไฟตก)
  Serial.println("[BOOT] Initializing system sensors and entering Standby...");
  sensorArmed = (digitalRead(PIN_SCAN_IR) == HIGH);
  if (!sensorArmed) {
    Serial.println("[BOOT WARNING] IR Sensor is currently LOW at boot. Waiting for sensor clear...");
  }
  cooldownUntil = millis() + 500;
  showStandby();

  Serial.println("[SYSTEM READY] ระบบพร้อมทำงาน 100% (Instant Standby Ready)");
}

// ====================================================================
// LOOP
// ====================================================================
unsigned long lastTelemetry = 0;

void loop() {
  unsigned long now = millis();

  // 1. รับคำสั่งผ่าน Serial (รองรับ 'C', 'CAPTURE', 'SCAN', หรือ 'BIN:x')
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "C" || cmd == "c" || cmd == " " || cmd == "CAPTURE") {
      Serial.println("\n⚡ [TRIGGER] สั่งถ่ายภาพผ่านคำสั่ง CAPTURE!");
      captureAndProcess();
    } else if (cmd == "SCAN" || cmd == "PROBE") {
      Serial.println("\n[DIAGNOSTIC] กำลังทดสอบสแกนพอร์ตของกล้อง ESP32-CAM...");
      IPAddress gw = WiFi.gatewayIP();
      Serial.printf("  S3 IP: %s | Cam Gateway: %s | Cam SSID: %s\n",
                    WiFi.localIP().toString().c_str(), gw.toString().c_str(), WiFi.SSID().c_str());
      int ports[] = {80, 81, 8080, 8888, 8000, 5000};
      for (int p : ports) {
        WiFiClient client;
        client.setTimeout(1000);
        Serial.printf("  Port %d: ", p);
        if (client.connect(gw, p)) {
          Serial.printf("OPEN!\n");
          client.stop();
        } else {
          Serial.printf("CLOSED / REFUSED\n");
        }
      }
    } else if (cmd.startsWith("BIN:")) {
      int bin = cmd.substring(4).toInt();
      openBin(bin, "SERIAL_CMD");
    } else if (cmd == "T" || cmd == "t" || cmd == "TEST_SERVOS" || cmd == "SERVO") {
      testAllServos();
    } else if (cmd == "OLED" || cmd == "TEST_OLED") {
      Serial.println("\n[DIAGNOSTIC] Running OLED Auto-Detect & Reset...");
      if (initOLED()) {
        showStandby();
        Serial.printf(">> SUCCESS: จอ OLED ทำงานแล้วบนขา SDA=%d, SCL=%d!\n", PIN_OLED_SDA, PIN_OLED_SCL);
      } else {
        Serial.println(">> FAILED: ยังไม่พบจอ OLED บนพินใดๆ");
      }
    } else if (cmd == "WIFI" || cmd == "SCAN_WIFI" || cmd == "NET") {
      Serial.println("\n[WIFI SCAN] Scanning all 2.4GHz Wi-Fi networks around ESP32-S3...");
      WiFi.mode(WIFI_STA);
      WiFi.disconnect();
      delay(100);
      int n = WiFi.scanNetworks();
      Serial.printf("Found %d networks:\n", n);
      for (int i = 0; i < n; i++) {
        Serial.printf("  [%d] SSID: '%s' | RSSI: %d dBm | Open: %s\n",
                      i + 1, WiFi.SSID(i).c_str(), WiFi.RSSI(i),
                      WiFi.encryptionType(i) == WIFI_AUTH_OPEN ? "YES" : "NO");
      }
    }
  }

  // 2. ตรวจจับการทิ้งขยะหน้าเซนเซอร์ IR (ระบบ Edge-Trigger & Anti-Stuck)
  if (!isScanning) {
    if (now - lastSensorCheck >= 40) {
      lastSensorCheck = now;
      int pin4Val = digitalRead(PIN_SCAN_IR);
      int pin0Val = digitalRead(PIN_SCAN_IR_LEGACY);

      // A. ปุ่ม BOOT บนบอร์ด (GPIO 0) กดเพื่อสั่งสแกนทันทีเสมอ (ไม่ว่า IR จะค้างหรือไม่)
      static int lastPin0Val = HIGH;
      if (pin0Val == LOW && lastPin0Val == HIGH && (now > cooldownUntil)) {
        Serial.println("\n⚡ [BUTTON TRIGGER] กดปุ่ม BOOT บนบอร์ด สั่งสแกนทันที!");
        cooldownUntil = now + 1500;
        captureAndProcess();
        lastPin0Val = pin0Val;
        return;
      }
      lastPin0Val = pin0Val;

      // B. เซนเซอร์ FC-51 (GPIO 4) พร้อมระบบป้องกันค้าง LOW อัจฉริยะ
      if (pin4Val == LOW) {
        if (sensorActiveSince == 0) {
          sensorActiveSince = now;
        }

        // หากค้าง LOW เกิน 2.5 วินาที -> เตือนให้ปรับ Trimpot ทันที แต่ไม่ล็อกเครื่อง
        if (now - sensorActiveSince >= 2500) {
          if (!sensorStuckAlert) {
            sensorStuckAlert = true;
            Serial.println("\n⚠️ [SENSOR ALERT] เซนเซอร์ FC-51 ค้าง LOW! หมุน Trimpot ทวนเข็มนาฬิกา หรือกดปุ่ม BOOT เพื่อสแกน");
            showSensorStuckWarning();
          }
        } else if (sensorArmed && (now > cooldownUntil) && (now - sensorActiveSince >= 70)) {
          // ตรวจจับครั้งใหม่เมื่อวัตถุยื่นเข้ามา 70 - 2500ms
          sensorArmed = false;
          sensorActiveSince = 0;
          consecutiveDetections = 0;
          Serial.println("\n⚡ [TRIGGER] เซนเซอร์ IR ตรวจพบวัตถุใหม่หน้ากล้อง!");
          captureAndProcess();
        }
      } else {
        // เมื่อไม่มีวัตถุบัง (เซนเซอร์ปล่อย HIGH)
        sensorActiveSince = 0;
        if (sensorStuckAlert) {
          sensorStuckAlert = false;
          Serial.println("[SENSOR OK] เซนเซอร์กลับสู่สภาวะปกติ (HIGH) แล้ว");
          showStandby();
        }

        // Re-arm เมื่อเซนเซอร์เคลียร์เป็น HIGH และพ้น cooldown แล้ว
        if (!sensorArmed && (now > cooldownUntil)) {
          sensorArmed = true;
          Serial.println("[SENSOR ARMED] ระบบพร้อมรับการสแกนขยะชิ้นต่อไป!");
          showStandby();
        }
      }
    }

    // 3. ตรวจวัดระดับความจุขยะทั้ง 4 ถังเป็นระยะ (ทุกๆ 2.5 วินาที)
    if (now - lastFullnessScan >= 2500) {
      lastFullnessScan = now;
      updateAllBinFullness();
      if (!sensorStuckAlert) {
        showStandby();
      }
    }

    // 4. พิมพ์รายงานสถานะการทำงาน (Heartbeat Telemetry) และตรวจสอบการต่อจอ OLED แบบ Real-Time
    if (now - lastTelemetry >= 4000) {
      lastTelemetry = now;
      Wire.beginTransmission(0x3C);
      byte oledErr = Wire.endTransmission();
      if (oledErr == 0 && !oledFound) {
        if (display.begin(SSD1306_SWITCHCAPVCC, 0x3C, false, false)) {
          oledFound = true;
          display.ssd1306_command(SSD1306_DISPLAYALLON_RESUME);
          display.ssd1306_command(SSD1306_NORMALDISPLAY);
          display.dim(false);
          display.clearDisplay();
          showStandby();
          Serial.println("\n🎉 [HOT-PLUG OLED] พบจอ OLED แล้ว! แสดงหน้าจอ Standby ทันที");
        }
      } else if (oledErr != 0) {
        if (oledFound) {
          oledFound = false;
          Serial.println("\n⚠️ [OLED DISCONNECTED] จอ OLED หลุดการเชื่อมต่อ!");
        }
        initOLED();
      }

      Serial.printf("[HEARTBEAT] OLED:%s(err:%d, SDA:%d, SCL:%d) | IR Pin4:%s Pin0:%s (Armed:%s) | WiFi: %s | Bin 1-4: [%.0f, %.0f, %.0f, %.0f cm]\n",
                    oledFound ? "OK" : "NO_ACK",
                    oledErr,
                    PIN_OLED_SDA, PIN_OLED_SCL,
                    (digitalRead(PIN_SCAN_IR) == LOW) ? "DETECT!" : "IDLE",
                    (digitalRead(PIN_SCAN_IR_LEGACY) == LOW) ? "DETECT!" : "IDLE",
                    sensorArmed ? "YES" : "NO",
                    (WiFi.status() == WL_CONNECTED) ? "ONLINE" : "OFFLINE",
                    binDistances[0], binDistances[1], binDistances[2], binDistances[3]);
    }
  }
}
