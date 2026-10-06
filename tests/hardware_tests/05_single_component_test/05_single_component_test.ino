/*
 * ==================================================================================
 * Hardware Diagnostic: Single Component Test (Servo + IR + Ultrasonic + OLED)
 * ทดสอบฮาร์ดแวร์ 3 ชิ้นอย่างละ 1 ตัว: เซอร์โว 1 ตัว, IR 1 ตัว, Ultrasonic 1 ตัว
 * ==================================================================================
 * พินที่ใช้:
 * - Servo 1       : GPIO 21 (PWM)
 * - IR FC-51      : GPIO 0  (Active LOW)
 * - HC-SR04 Trig  : GPIO 14 (Output)
 * - HC-SR04 Echo  : GPIO 47 (Input)
 * - OLED SDA / SCL: GPIO 1 / GPIO 2 (I2C)
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

#define PIN_SERVO     21
#define PIN_IR        0
#define PIN_TRIG      14
#define PIN_ECHO      47

Servo testServo;
int servoAngle = 0;
unsigned long lastMeasureTime = 0;
unsigned long lastActionTime = 0;
bool irTriggered = false;
float currentDistance = 0.0;

float readUltrasonic() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);

  long duration = pulseIn(PIN_ECHO, HIGH, 30000); // timeout 30ms (~5 เมตร)
  if (duration == 0) return -1.0; // วัดไม่ได้ / เกินระยะ

  float distanceCm = (duration * 0.0343) / 2.0;
  return distanceCm;
}

void updateOled(float dist, bool irDetected, int angle) {
  if (!oledFound) return;
  display.clearDisplay();

  // แถบหัวเรื่อง
  display.fillRect(0, 0, 128, 14, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK);
  display.setTextSize(1);
  display.setCursor(8, 3);
  display.println("HARDWARE TEST SUITE");

  // แสดงผลค่า IR
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(4, 20);
  display.print("IR Sensor : ");
  if (irDetected) {
    display.setTextColor(SSD1306_BLACK, SSD1306_WHITE);
    display.println(" DETECTED! ");
    display.setTextColor(SSD1306_WHITE);
  } else {
    display.println("CLEAR");
  }

  // แสดงผลค่าระยะ Ultrasonic
  display.setCursor(4, 34);
  display.print("Distance  : ");
  if (dist > 0) {
    display.printf("%.1f cm", dist);
  } else {
    display.print("Out of range");
  }

  // แสดงผลสถานะเซอร์โว
  display.setCursor(4, 48);
  display.print("Servo (21): ");
  display.printf("%d deg ", angle);
  if (angle > 45) {
    display.print("[OPEN]");
  } else {
    display.print("[CLOSED]");
  }

  display.drawRect(0, 0, 128, 64, SSD1306_WHITE);
  display.display();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n========================================================");
  Serial.println("  HARDWARE DIAGNOSTIC: SERVO + IR + ULTRASONIC TEST     ");
  Serial.println("========================================================");

  pinMode(PIN_IR, INPUT_PULLUP);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);

  Wire.begin(1, 2);
  if (display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    oledFound = true;
    Serial.println("[OLED] ตรวจพบจอ 0.96 นิ้ว (0x3C)");
  }

  // ทดสอบขยับเซอร์โวเบื้องต้น
  testServo.attach(PIN_SERVO);
  testServo.write(0);
  delay(500);
  testServo.detach();

  Serial.println("[SYSTEM READY] วางมือหน้าเซนเซอร์ IR หรือ Ultrasonic เพื่อทดสอบ");
  Serial.println("  -> เมื่อ IR ตรวจพบวัตถุ เซอร์โวจะหมุนเปิด 90 องศาอัตโนมัติ!");
}

void loop() {
  unsigned long now = millis();

  // อ่านค่าทุก 100ms
  if (now - lastMeasureTime >= 100) {
    lastMeasureTime = now;

    // อ่านค่า IR (Active LOW: ค่า 0 = มีวัตถุบัง)
    irTriggered = (digitalRead(PIN_IR) == LOW);

    // อ่านค่าระยะ Ultrasonic
    currentDistance = readUltrasonic();

    // ควบคุมเซอร์โวสัมพันธ์กับ IR
    if (irTriggered) {
      if (servoAngle != 90) {
        servoAngle = 90;
        testServo.attach(PIN_SERVO);
        testServo.write(90);
        Serial.println("\n>>> [IR TRIGGERED] ตรวจพบวัตถุ! -> เซอร์โวหมุนไปที่ 90 องศา (เปิดฝา)");
      }
      lastActionTime = now;
    } else {
      // เมื่อเอามือออกครบ 2 วินาที ให้ปิดกลับ
      if (servoAngle == 90 && (now - lastActionTime >= 2000)) {
        servoAngle = 0;
        testServo.write(0);
        delay(400);
        testServo.detach();
        Serial.println(">>> [AUTO CLOSE] วัตถุพ้นระยะ -> เซอร์โวหมุนกลับ 0 องศา (ปิดฝา)\n");
      }
    }

    // อัปเดตหน้าจอ OLED
    updateOled(currentDistance, irTriggered, servoAngle);
  }

  // พิมพ์ลง Serial ทุกๆ 1 วินาที
  static unsigned long lastSerialPrint = 0;
  if (now - lastSerialPrint >= 1000) {
    lastSerialPrint = now;
    Serial.printf("[DIAGNOSTIC] IR: %s | Dist: %.1f cm | Servo: %d deg\n",
                  irTriggered ? "DETECTED" : "CLEAR",
                  currentDistance,
                  servoAngle);
  }
}
