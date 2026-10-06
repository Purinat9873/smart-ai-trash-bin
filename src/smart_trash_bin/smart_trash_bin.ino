/*
 * ======================================================================================
 * Project: Smart AI Trash Bin (ถังขยะอัจฉริยะคัดแยก 4 ประเภทด้วย AI)
 * Hardware: ESP32-S3 (N16R8), OV2640, OLED 0.96" I2C, 4x SG90 Servos, 5x FC-51 IR, 4x HC-SR04
 * Power: 2x 18650 Li-ion in Series (7.4V) -> Step-Down Buck Converter (5.0V)
 * Architecture: Non-blocking State Machine, Auto-Scan Presence Detection, Detached Servos
 * ======================================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "esp_camera.h"

// ==========================================
// 1. ตั้งค่าการเชื่อมต่อ Wi-Fi และ Cloud API
// ==========================================
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Roboflow Hosted Inference API (ใส่ Model ID และ API Key ของคุณ)
// หรือชี้มาที่ Mock Server ภายใน LAN เช่น "http://192.168.1.100:5000/predict"
const char* API_INFERENCE_URL = "https://detect.roboflow.com/trash-sorting-demo/1?api_key=YOUR_API_KEY&confidence=40";

// Webhook สำหรับแจ้งเตือนถังเต็ม (LINE OA ผ่าน Google Apps Script หรือ Webhook อื่นๆ)
const char* FULL_BIN_WEBHOOK_URL = "https://script.google.com/macros/s/YOUR_GAS_ID/exec";

// ==========================================
// 2. กำหนดขา GPIO (Safe Pinout - เลี่ยง GPIO 33-37 สำหรับ Octal PSRAM)
// ==========================================
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

#define PIN_I2C_SDA          1
#define PIN_I2C_SCL          2

// เซนเซอร์ IR หน้ากล้องสำหรับ Auto-Scan (ยื่นมือบัง = LOW)
#define PIN_AUTO_SCAN_IR     0

// Servo Motors (SG90) สำหรับเปิด-ปิดฝา 4 ช่อง
#define PIN_SERVO_GEN        21  // ช่อง 1: ขยะทั่วไป (General)
#define PIN_SERVO_REC        38  // ช่อง 2: ขยะรีไซเคิล (Recyclable)
#define PIN_SERVO_WET        39  // ช่อง 3: ขยะเปียก (Wet / Organic)
#define PIN_SERVO_HAZ        40  // ช่อง 4: ขยะอันตราย (Hazardous)

// FC-51 IR Sensors ติดปากถังสำหรับตรวจขยะหล่น
#define PIN_IR_GEN           41
#define PIN_IR_REC           42
#define PIN_IR_WET           45
#define PIN_IR_HAZ           46

// HC-SR04 Ultrasonic Sensors สำหรับตรวจวัดระดับขยะเต็ม
#define PIN_US_TRIG          14  // ขา Trigger ร่วม (ต่อพ่วงถึงกันทั้ง 4 ตัว)
#define PIN_US_ECHO_GEN      47  // Echo ช่อง 1 (ผ่าน R-divider 1k + 2k)
#define PIN_US_ECHO_REC      48  // Echo ช่อง 2 (ผ่าน R-divider 1k + 2k)
#define PIN_US_ECHO_WET      3   // Echo ช่อง 3 (ผ่าน R-divider 1k + 2k)
#define PIN_US_ECHO_HAZ      44  // Echo ช่อง 4 (ผ่าน R-divider 1k + 2k)

// เกณฑ์วัดระดับขยะเต็ม (หน่วย cm): ถ้าระยะจากเซนเซอร์ถึงผิวขยะน้อยกว่าเกณฑ์ = ถังเต็ม
#define FULL_BIN_THRESHOLD_CM 7.0

// กำหนดขา DVP Camera OV2640 สำหรับ ESP32-S3
#define PWDN_GPIO_NUM        -1
#define RESET_GPIO_NUM       -1
#define XCLK_GPIO_NUM        15
#define SIOD_GPIO_NUM         4
#define SIOC_GPIO_NUM         5
#define Y9_GPIO_NUM          16
#define Y8_GPIO_NUM          17
#define Y7_GPIO_NUM          18
#define Y6_GPIO_NUM          12
#define Y5_GPIO_NUM          10
#define Y4_GPIO_NUM           8
#define Y3_GPIO_NUM           9
#define Y2_GPIO_NUM          11
#define VSYNC_GPIO_NUM        6
#define HREF_GPIO_NUM         7
#define PCLK_GPIO_NUM        13

// ==========================================
// 3. ตารางข้อมูลและออบเจกต์
// ==========================================
Servo servos[4];
const int servoPins[4]  = {PIN_SERVO_GEN, PIN_SERVO_REC, PIN_SERVO_WET, PIN_SERVO_HAZ};
const int irPins[4]     = {PIN_IR_GEN, PIN_IR_REC, PIN_IR_WET, PIN_IR_HAZ};
const int echoPins[4]   = {PIN_US_ECHO_GEN, PIN_US_ECHO_REC, PIN_US_ECHO_WET, PIN_US_ECHO_HAZ};
const char* binNames[4] = {"General (ทั่วไป)", "Recycle (รีไซเคิล)", "Wet (ขยะเปียก)", "Hazardous (อันตราย)"};

// ฟังก์ชันแสดงข้อความบนจอ OLED
void showOLED(const String& line1, const String& line2 = "", const String& line3 = "") {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 2);
  display.println(">> SMART AI BIN <<");
  display.drawLine(0, 14, 127, 14, SSD1306_WHITE);
  display.setCursor(0, 20);
  display.println(line1);
  if (line2.length() > 0) { display.setCursor(0, 35); display.println(line2); }
  if (line3.length() > 0) { display.setCursor(0, 50); display.println(line3); }
  display.display();
}

// เริ่มต้นระบบกล้อง OV2640 โดยใช้หน่วยความจำ PSRAM
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAMESIZE_QVGA;     // 320x240 ส่งขึ้น Cloud ไวมาก (~20-30KB)
  config.jpeg_quality = 12;                 // 0-63 (ตัวเลขน้อยคุณภาพยิ่งสูง)
  config.fb_count     = 1;
  config.fb_location  = CAMERA_FB_IN_PSRAM; // บังคับเก็บเฟรมภาพใน Octal PSRAM

  esp_err_t err = esp_camera_init(&config);
  return (err == ESP_OK);
}

// อ่านระยะทางจากเซนเซอร์ Ultrasonic HC-SR04
float readUltrasonicCM(int echoPin) {
  digitalWrite(PIN_US_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_US_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_US_TRIG, LOW);

  long duration = pulseIn(echoPin, HIGH, 25000); // Timeout 25ms (~4.3 เมตร)
  if (duration == 0) return 999.0;
  return (duration * 0.0343) / 2.0;
}

// ส่งแจ้งเตือน Webhook เมื่อถังเต็ม
void sendFullBinAlert(int binIndex) {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  String targetUrl = String(FULL_BIN_WEBHOOK_URL) + "?bin=" + binNames[binIndex] + "&status=FULL";
  http.begin(targetUrl);
  http.setTimeout(4000);
  http.GET();
  http.end();
}

// จับภาพและส่ง HTTP POST ขึ้น Cloud AI จำแนกประเภท
int classifyTrashOnline() {
  showOLED("AI INFERENCE...", "Capturing image...", "Sending to Cloud");

  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[CAM ERROR] Capture Failed!");
    return 0; // Fallback to General
  }

  int detectedBin = 0; // Default: General
  WiFiClientSecure secureClient;
  secureClient.setInsecure(); // ข้ามการเช็ค SSL Root CA เพื่อความเร็วและประหยัด RAM

  HTTPClient http;
  bool isHttps = String(API_INFERENCE_URL).startsWith("https://");

  bool beginSuccess = false;
  if (isHttps) {
    beginSuccess = http.begin(secureClient, API_INFERENCE_URL);
  } else {
    WiFiClient standardClient;
    beginSuccess = http.begin(standardClient, API_INFERENCE_URL);
  }

  if (beginSuccess) {
    http.addHeader("Content-Type", "application/x-www-form-urlencoded");
    http.setTimeout(7000); // 7s Timeout

    int httpResponseCode = http.POST(fb->buf, fb->len);
    Serial.printf("[HTTP] POST Code: %d, Image Size: %u bytes\n", httpResponseCode, fb->len);

    if (httpResponseCode == 200) {
      String response = http.getString();
      Serial.println("[API Response]: " + response);

      DynamicJsonDocument doc(2048);
      DeserializationError error = deserializeJson(doc, response);

      if (!error && doc["predictions"].size() > 0) {
        String label = doc["predictions"][0]["class"].as<String>();
        float conf   = doc["predictions"][0]["confidence"].as<float>();
        label.toLowerCase();

        Serial.printf("[AI DETECTED] Class: %s (Confidence: %.2f)\n", label.c_str(), conf);

        if (label.indexOf("recycle") >= 0 || label.indexOf("bottle") >= 0 || label.indexOf("can") >= 0 || label.indexOf("cardboard") >= 0) {
          detectedBin = 1; // Recyclable
        } else if (label.indexOf("wet") >= 0 || label.indexOf("food") >= 0 || label.indexOf("organic") >= 0) {
          detectedBin = 2; // Wet
        } else if (label.indexOf("hazard") >= 0 || label.indexOf("battery") >= 0 || label.indexOf("bulb") >= 0) {
          detectedBin = 3; // Hazardous
        } else {
          detectedBin = 0; // General
        }
      }
    } else {
      Serial.printf("[HTTP ERROR] Failed with code %d\n", httpResponseCode);
    }
    http.end();
  }

  esp_camera_fb_return(fb); // คืนบัฟเฟอร์ภาพสู่ PSRAM ทันที
  return detectedBin;
}

// กระบวนการเปิด-ปิดฝา ตรวจจับขยะตก และ Safety Loop
void handleBinOperation(int binIndex) {
  // 1. ตรวจสอบความจุของถังช่องนั้นก่อน
  float distance = readUltrasonicCM(echoPins[binIndex]);
  Serial.printf("[ULTRASONIC] ช่อง %s ระยะ: %.1f cm\n", binNames[binIndex], distance);

  if (distance > 0 && distance <= FULL_BIN_THRESHOLD_CM) {
    showOLED("WARNING: FULL!", String(binNames[binIndex]), "Cannot open lid!");
    sendFullBinAlert(binIndex);
    delay(2500);
    return;
  }

  // 2. ถ้าไม่เต็ม -> สั่งเปิดฝาฟิวเจอร์บอร์ด
  showOLED("MATCH: " + String(binNames[binIndex]), "Please drop trash...", "Lid Open (Max 5s)");

  // สั่ง Servo เปิด 90 องศา แล้วสั่ง detach() เพื่อตัดไฟ ป้องกันไฟตกและเสียงหึ่ง
  servos[binIndex].attach(servoPins[binIndex]);
  servos[binIndex].write(90);
  delay(350);
  servos[binIndex].detach();

  // 3. วนลูป Non-blocking รอจับการตกของขยะผ่าน FC-51 หรือหมดเวลา 5 วินาที
  unsigned long openTime = millis();
  bool trashDropped = false;

  while (millis() - openTime < 5000) {
    if (digitalRead(irPins[binIndex]) == LOW) { // ตรวจเจอขยะตัดผ่านลำแสง IR
      trashDropped = true;
      delay(300); // หน่วงเวลาให้ขยะหล่นพ้นฝาลงไปสนิท
      break;
    }
    delay(20);
  }

  // 4. สั่งปิดฝา 0 องศา แล้วตัดไฟด้วย detach()
  servos[binIndex].attach(servoPins[binIndex]);
  servos[binIndex].write(0);
  delay(350);
  servos[binIndex].detach();

  if (trashDropped) {
    showOLED("THANK YOU!", "Trash Received", "Bin Closed.");
  } else {
    showOLED("TIMEOUT!", "No trash dropped", "Auto-closed.");
  }
  delay(1500);
}

// ==========================================
// 4. Setup & Main Loop
// ==========================================
void setup() {
  Serial.begin(115200);
  pinMode(PIN_AUTO_SCAN_IR, INPUT); // เซนเซอร์ตรวจจับมือหน้ากล้อง
  pinMode(PIN_US_TRIG, OUTPUT);

  for (int i = 0; i < 4; i++) {
    pinMode(irPins[i], INPUT);
    pinMode(echoPins[i], INPUT);
  }

  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("[OLED ERROR] Display init failed!");
  }
  showOLED("Booting System...", "Testing Sensors", "Please wait...");

  if (!initCamera()) {
    showOLED("CAMERA ERROR!", "Check Ribbon cable", "System Halted.");
    while (true) delay(1000);
  }

  // เชื่อมต่อ Wi-Fi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 25) {
    delay(400);
    retry++;
  }

  // เซ็ตตำแหน่งเริ่มต้นให้ฝาปิดสนิททุกช่อง
  for (int i = 0; i < 4; i++) {
    servos[i].attach(servoPins[i]);
    servos[i].write(0);
    delay(120);
    servos[i].detach();
  }

  showOLED("READY TO SCAN", "Hold trash 15-20cm", "in front of cam...");
}

void loop() {
  // ตรวจสอบและเชื่อมต่อ Wi-Fi ใหม่หากหลุด
  if (WiFi.status() != WL_CONNECTED) {
    WiFi.reconnect();
  }

  // ระบบ Auto-Scan: เมื่อผู้ใช้ยื่นมือถือขยะมาหน้าเลนส์ (FC-51 ส่ง LOW)
  if (digitalRead(PIN_AUTO_SCAN_IR) == LOW) {
    showOLED("OBJECT DETECTED!", "Hold still 1 sec...", "Preparing scan");
    
    // หน่วง 800ms เพื่อให้มือนิ่ง ลดการเบลอของภาพ และตัด False Trigger
    delay(800);
    if (digitalRead(PIN_AUTO_SCAN_IR) == LOW) {
      int targetBin = classifyTrashOnline();
      handleBinOperation(targetBin);

      // หน่วง 2 วินาทีให้ผู้ใช้ดึงมือออก ก่อนพร้อมสแกนชิ้นถัดไป
      delay(2000);
      showOLED("READY TO SCAN", "Hold trash 15-20cm", "in front of cam...");
    }
  }

  delay(40);
}
