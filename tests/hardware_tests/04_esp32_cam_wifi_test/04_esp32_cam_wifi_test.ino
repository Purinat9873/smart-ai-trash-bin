#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

const char* ssid = "ESP32-CAM-MB";
const char* password = "";

void showOled(const char* title, const char* status, const char* detail) {
  display.clearDisplay();
  display.fillRect(0, 0, 128, 14, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(4, 3);
  display.println(title);

  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(8, 22);
  display.println(status);

  display.setTextSize(1);
  display.setCursor(4, 48);
  display.println(detail);
  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  display.display();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n========================================================");
  Serial.println("  ESP32-S3 <--> ESP32-CAM (OV2640) WI-FI IMAGE CAPTURE  ");
  Serial.println("========================================================");

  Wire.begin(1, 2);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  showOled("OV2640 CAMERA LINK", "CONNECTING", "Finding ESP32-CAM...");

  Serial.printf("[WIFI] กำลังเชื่อมต่อ Wi-Fi ไปยัง '%s'...\n", ssid);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 20) {
    delay(500);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[WIFI CONNECTED] เชื่อมต่อสำเร็จ! IP ของ S3: %s\n", WiFi.localIP().toString().c_str());
    showOled("OV2640 CAMERA LINK", "CONNECTED!", "Fetching test image");

    // ทดสอบดึงภาพจากกล้อง OV2640
    Serial.println("[HTTP] กำลังทดสอบดึงภาพจาก http://192.168.4.1/capture ...");
    HTTPClient http;
    http.begin("http://192.168.4.1/capture");
    int httpCode = http.GET();

    if (httpCode == HTTP_CODE_OK) {
      int len = http.getSize();
      Serial.printf("[SUCCESS] ดึงภาพจากกล้อง OV2640 สำเร็จ! ขนาดภาพ: %d bytes\n", len);
      char buf[32];
      snprintf(buf, sizeof(buf), "Size: %d B", len);
      showOled("OV2640 CAMERA LINK", "CAM READY", buf);
    } else {
      Serial.printf("[WARN] HTTP Response Code: %d (กำลังลอง URL ทางเลือก /jpg) ...\n", httpCode);
      http.end();
      http.begin("http://192.168.4.1/jpg");
      httpCode = http.GET();
      if (httpCode == HTTP_CODE_OK) {
        int len = http.getSize();
        Serial.printf("[SUCCESS] ดึงภาพจาก /jpg สำเร็จ! ขนาด: %d bytes\n", len);
        showOled("OV2640 CAMERA LINK", "CAM READY", "Path: /jpg");
      } else {
        Serial.printf("[WARN] /jpg Code: %d\n", httpCode);
        showOled("OV2640 CAMERA LINK", "CHECK URL", "Code != 200");
      }
    }
    http.end();
  } else {
    Serial.println("\n[ERROR] ไม่สามารถเชื่อมต่อ Wi-Fi ESP32-CAM-MB ได้");
    showOled("OV2640 CAMERA LINK", "FAILED", "Check ESP32-CAM power");
  }
}

void loop() {
  delay(1000);
}
