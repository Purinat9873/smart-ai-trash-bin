#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

Adafruit_SSD1306 display(128, 64, &Wire, -1);
bool screenWorking = false;

bool checkAndLightUp(int sda, int scl) {
  Wire.end();
  delay(10);
  Wire.begin(sda, scl);
  Wire.setClock(100000);
  Wire.setTimeOut(30);

  for (byte addr = 0x3C; addr <= 0x3D; addr++) {
    Wire.beginTransmission(addr);
    byte err = Wire.endTransmission();
    if (err == 0) {
      if (display.begin(SSD1306_SWITCHCAPVCC, addr, false, false)) {
        display.ssd1306_command(SSD1306_DISPLAYALLON_RESUME); // 0xA4: ยกเลิกจอขาว
        display.ssd1306_command(SSD1306_NORMALDISPLAY);       // 0xA6: โหมดปกติ
        display.dim(false);
        display.clearDisplay();
        display.fillRect(0, 0, 128, 14, SSD1306_WHITE);
        display.setTextColor(SSD1306_BLACK);
        display.setTextSize(1);
        display.setCursor(18, 3);
        display.println("OLED CONNECTED!");

        display.setTextColor(SSD1306_WHITE);
        display.setTextSize(2);
        display.setCursor(16, 20);
        display.println("SCREEN OK");

        display.setTextSize(1);
        display.setCursor(4, 44);
        display.printf("SDA: GPIO %d | SCL: %d\n", sda, scl);
        display.setCursor(4, 54);
        display.printf("I2C Addr: 0x%02X (READY)\n", addr);
        display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
        display.display();

        Serial.printf("\n🎉🎉🎉 [OLED DETECTED & ACTIVE!] SDA=%d, SCL=%d, Addr=0x%02X 🎉🎉🎉\n", sda, scl, addr);
        Serial.println(">> หน้าจอหายขาวแล้ว และแสดงผลตัวหนังสือสำเร็จ 100%! <<\n");
        return true;
      }
    }
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=======================================================");
  Serial.println("  LIVE REAL-TIME OLED RECOVERY & TESTER (ESP32-S3)     ");
  Serial.println("  กำลังรอตรวจจับสายจอ OLED แบบ Real-Time ทุกๆ 1 วินาที...");
  Serial.println("=======================================================");
}

unsigned long lastProbe = 0;

void loop() {
  unsigned long now = millis();
  if (now - lastProbe >= 1000) {
    lastProbe = now;

    // 1. ตรวจสอบพินเป้าหมายหลัก SDA=1, SCL=2
    if (checkAndLightUp(1, 2)) {
      screenWorking = true;
      return;
    }

    // 2. ตรวจสอบกรณีสลับสาย SDA=2, SCL=1
    if (checkAndLightUp(2, 1)) {
      screenWorking = true;
      return;
    }

    // 3. สแกนพินข้างเคียงของ ESP32-S3
    const int pairs[][2] = {
      {8, 9}, {9, 8},
      {2, 42}, {42, 2},
      {42, 41}, {41, 42},
      {5, 6}, {6, 5},
      {17, 18}, {18, 17}
    };
    for (auto& p : pairs) {
      if (checkAndLightUp(p[0], p[1])) {
        screenWorking = true;
        return;
      }
    }

    Serial.println("[WAITING] ยังไม่พบสัญญาณจอ OLED (จอขาวเพราะสาย I2C/GND ยังไม่ต่อถึงบอร์ด)");
  }
}
