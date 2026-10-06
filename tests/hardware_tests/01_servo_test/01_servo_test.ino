/*
 * -------------------------------------------------------------
 * Hardware Test 1: Servo Motors Sequential Test (การทดสอบเซอร์โว 4 ตัว)
 * -------------------------------------------------------------
 * วัตถุประสงค์:
 * 1. ทดสอบการเปิด-ปิดฝาฟิวเจอร์บอร์ดทีละช่อง เพื่อตรวจเช็กการติดขัดของบานพับ
 * 2. ตรวจสอบว่าระบบไฟ (ถ่าน 7.4V -> Step-Down 5.0V) นิ่งสนิท ไม่มีไฟตก
 * 3. ตรวจสอบมุมองศา (0 องศา = ปิดสนิท, 90 องศา = เปิดสุด)
 */

#include <Arduino.h>
#include <ESP32Servo.h>

const int servoPins[4] = {21, 38, 39, 40};
const char* binNames[4] = {"1: General (ทั่วไป)", "2: Recycle (รีไซเคิล)", "3: Wet (ขยะเปียก)", "4: Hazardous (อันตราย)"};
Servo myServo;

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("==========================================");
  Serial.println("   SMART TRASH BIN - SERVO TEST SUITE     ");
  Serial.println("==========================================");
}

void loop() {
  for (int i = 0; i < 4; i++) {
    Serial.printf("\n[TESTING] กำลังทดสอบช่องที่ %s (GPIO %d)...\n", binNames[i], servoPins[i]);
    
    // 1. ต่อสัญญาณ PWM
    myServo.attach(servoPins[i]);
    
    // 2. สั่งเปิด 90 องศา
    Serial.println(" -> สั่งเปิดฝา 90 องศา");
    myServo.write(90);
    delay(1000); // เปิดค้างไว้ 1 วินาที
    
    // 3. สั่งปิด 0 องศา
    Serial.println(" -> สั่งปิดฝา 0 องศา");
    myServo.write(0);
    delay(800);
    
    // 4. ตัดสัญญาณ PWM ป้องกันมอเตอร์ร้อนและประหยัดไฟ
    myServo.detach();
    Serial.println(" -> ตัดสัญญาณ PWM (detach) เรียบร้อย");
    
    delay(1500); // พัก 1.5 วินาทีก่อนทดสอบตัวถัดไป
  }

  Serial.println("\n--- จบรอบการทดสอบมอเตอร์ทั้ง 4 ตัว (พัก 5 วินาที) ---");
  delay(5000);
}
