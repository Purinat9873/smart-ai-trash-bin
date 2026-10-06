#include <Arduino.h>

#define CAM_RX 18 // รับจาก U0T ของ ESP32-CAM
#define CAM_TX 17 // ส่งไป U0R ของ ESP32-CAM

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("\n========================================================");
  Serial.println("   [DIAGNOSTIC] ESP32-S3 <--> ESP32-CAM CONNECTION TEST ");
  Serial.println("========================================================");
  Serial.println("[INFO] ระบบเปิดรับสัญญาณ Serial2 ที่ขา RX=18, TX=17 เรียบร้อย");
  Serial.println("[TEST] ลองกดปุ่ม 'RST' สีดำเล็กๆ บนบอร์ด ESP32-CAM 1 ครั้ง...");
  Serial.println("       ถ้าไฟเข้าและต่อสายถูก จะมีข้อความ Boot Log ไหลขึ้นมาทันที!");
  Serial.println("========================================================\n");

  Serial2.begin(115200, SERIAL_8N1, CAM_RX, CAM_TX);
}

void loop() {
  while (Serial2.available()) {
    char c = Serial2.read();
    Serial.write(c);
  }
  while (Serial.available()) {
    char c = Serial.read();
    Serial2.write(c);
  }
}
