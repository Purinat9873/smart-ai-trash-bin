#include <Arduino.h>

const int SERVO_PINS[4] = {21, 38, 39, 40};

void setServoAngle(int pin, int angle) {
  ledcAttach(pin, 50, 14); // 50Hz, 14-bit resolution (0..16383)
  int us = map(constrain(angle, 0, 180), 0, 180, 544, 2400);
  uint32_t duty = (uint32_t)((us * 16384ULL) / 20000ULL);
  ledcWrite(pin, duty);
}

void detachServo(int pin) {
  ledcDetach(pin);
  pinMode(pin, OUTPUT);
  digitalWrite(pin, LOW);
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 4; i++) {
    detachServo(SERVO_PINS[i]);
  }
}

void loop() {
  for (int i = 0; i < 4; i++) {
    setServoAngle(SERVO_PINS[i], 90);
    delay(1000);
    setServoAngle(SERVO_PINS[i], 0);
    delay(500);
    detachServo(SERVO_PINS[i]);
    delay(1000);
  }
}
