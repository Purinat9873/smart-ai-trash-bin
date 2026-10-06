#include <Arduino.h>

void setup() {
  Serial.begin(115200);
}

void loop() {
  Serial.println("HELLO_FROM_ESP32_S3");
  delay(1000);
}
