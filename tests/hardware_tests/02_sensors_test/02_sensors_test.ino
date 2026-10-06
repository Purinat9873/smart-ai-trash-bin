/*
 * ----------------------------------------------------------------------------------
 * Hardware Test 2: Sensors Diagnostic & Calibration (ทดสอบและจูนเซนเซอร์ทั้งหมด)
 * ----------------------------------------------------------------------------------
 * วัตถุประสงค์:
 * 1. ตรวจสอบการอ่านค่าเซนเซอร์ FC-51 (IR) ทั้ง 5 ตัว:
 *    - ตัวที่ 1 หน้ากล้อง (GPIO 0 - Auto Scan)
 *    - ตัวที่ 2-5 ปากถัง 4 ช่อง (GPIO 41, 42, 45, 46)
 * 2. ตรวจสอบการวัดระยะ HC-SR04 (Ultrasonic) 4 ช่อง ผ่าน Trig รวม (GPIO 14)
 * 3. แสดงผลทั้งบน Serial Monitor และจอ OLED เพื่อให้จูน Potentiometer ได้ง่ายหน้างาน
 */

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

#define PIN_I2C_SDA      1
#define PIN_I2C_SCL      2

// IR Sensors
#define PIN_IR_AUTO      0
#define PIN_IR_GEN       41
#define PIN_IR_REC       42
#define PIN_IR_WET       45
#define PIN_IR_HAZ       46

// Ultrasonic Sensors
#define PIN_US_TRIG      14
#define PIN_US_ECHO_GEN  47
#define PIN_US_ECHO_REC  48
#define PIN_US_ECHO_WET  3
#define PIN_US_ECHO_HAZ  44

const int irPins[5]    = {PIN_IR_AUTO, PIN_IR_GEN, PIN_IR_REC, PIN_IR_WET, PIN_IR_HAZ};
const char* irNames[5] = {"CAM-AUTO", "DROP-GEN", "DROP-REC", "DROP-WET", "DROP-HAZ"};

const int echoPins[4]  = {PIN_US_ECHO_GEN, PIN_US_ECHO_REC, PIN_US_ECHO_WET, PIN_US_ECHO_HAZ};
const char* usNames[4] = {"GEN", "REC", "WET", "HAZ"};

float readUltrasonic(int echoPin) {
  digitalWrite(PIN_US_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_US_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_US_TRIG, LOW);

  long duration = pulseIn(echoPin, HIGH, 25000);
  if (duration == 0) return -1.0;
  return (duration * 0.0343) / 2.0;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("==========================================");
  Serial.println("   SMART TRASH BIN - SENSORS TEST SUITE   ");
  Serial.println("==========================================");

  // Setup IR Pins
  for (int i = 0; i < 5; i++) {
    pinMode(irPins[i], INPUT);
  }

  // Setup Ultrasonic Pins
  pinMode(PIN_US_TRIG, OUTPUT);
  for (int i = 0; i < 4; i++) {
    pinMode(echoPins[i], INPUT);
  }

  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  if (display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("SENSORS TEST MODE");
    display.display();
  }
}

void loop() {
  Serial.println("\n--- [REAL-TIME SENSOR DIAGNOSTIC] ---");

  // 1. อ่านค่า IR Sensors
  Serial.print("IR Sensors: ");
  String irStatusStr = "";
  for (int i = 0; i < 5; i++) {
    int val = digitalRead(irPins[i]);
    // val == LOW แปลว่ามีวัตถุตัดผ่าน
    Serial.printf("[%s: %s] ", irNames[i], (val == LOW) ? "DETECTED" : "CLEAR");
    if (i == 0) {
      irStatusStr += String("Cam:") + ((val == LOW) ? "YES " : "NO ");
    }
  }
  Serial.println();

  // 2. อ่านค่า Ultrasonic Sensors
  Serial.print("Ultrasonic Distances (cm): ");
  float dists[4];
  for (int i = 0; i < 4; i++) {
    dists[i] = readUltrasonic(echoPins[i]);
    if (dists[i] > 0) {
      Serial.printf("[%s: %.1f cm] ", usNames[i], dists[i]);
    } else {
      Serial.printf("[%s: NO ECHO] ", usNames[i]);
    }
    delay(30); // หน่วงเล็กน้อยระหว่างช่องเพื่อไม่ให้คลื่นสะท้อนตีกัน
  }
  Serial.println();

  // 3. อัปเดตขึ้นจอ OLED
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println(">> SENSORS DIAGNOSTIC <<");
  display.drawLine(0, 12, 127, 12, SSD1306_WHITE);
  
  display.setCursor(0, 16);
  display.print(irStatusStr);
  display.print(" D1:");
  display.print(digitalRead(irPins[1]) == LOW ? "X" : "-");
  display.print(" D2:");
  display.print(digitalRead(irPins[2]) == LOW ? "X" : "-");

  display.setCursor(0, 30);
  display.printf("G:%.0f R:%.0f", dists[0], dists[1]);

  display.setCursor(0, 44);
  display.printf("W:%.0f H:%.0f (cm)", dists[2], dists[3]);

  display.setCursor(0, 56);
  display.println("(Turn pot to tune IR)");
  display.display();

  delay(400);
}
