#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "ESP32-CAM-MB";
const char* pass = "";

void setup() {
  Serial.begin(921600);
  delay(1000);
  Serial.println("\n[PROBE] Starting ESP32-CAM Diagnostic Probe...");

  WiFi.disconnect(true);
  delay(100);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass);

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 25) {
    delay(200);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\n[PROBE FAIL] Cannot connect to ESP32-CAM-MB Wi-Fi");
    return;
  }

  IPAddress gw = WiFi.gatewayIP();
  Serial.printf("\n[PROBE OK] Connected! S3 IP: %s | Gateway (Cam) IP: %s\n",
                WiFi.localIP().toString().c_str(), gw.toString().c_str());

  // Test common ports
  int testPorts[] = {80, 81, 8080, 8888, 8000, 5000};
  for (int p : testPorts) {
    WiFiClient client;
    client.setTimeout(1000);
    Serial.printf("[PORT SCAN] Testing %s:%d ... ", gw.toString().c_str(), p);
    if (client.connect(gw, p)) {
      Serial.printf("OPEN!\n");
      client.stop();
    } else {
      Serial.printf("CLOSED / REFUSED\n");
    }
  }

  // Test port 80: /capture and /
  for (const char* pth : {"/capture", "/", "/status"}) {
    Serial.printf("[PROBE 80] GET %s on port 80 ...\n", pth);
    WiFiClient c;
    if (c.connect(gw, 80)) {
      c.printf("GET %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n", pth, gw.toString().c_str());
      unsigned long t0 = millis();
      while (!c.available() && millis() - t0 < 6000) {
        if (!c.connected()) break;
        delay(50);
      }
      Serial.printf("  -> Connected: %d, Available: %d bytes (time: %lu ms)\n", c.connected(), c.available(), millis() - t0);
      int n = 0;
      while (c.available() && n < 200) {
        Serial.write(c.read());
        n++;
      }
      Serial.println("\n");
      c.stop();
    } else {
      Serial.println("  -> Cannot connect port 80");
    }
  }

  // Test port 81: /stream
  Serial.println("[PROBE 81] Testing port 81 stream...");
  WiFiClient c81;
  if (c81.connect(gw, 81)) {
    c81.printf("GET /stream HTTP/1.1\r\nHost: %s:81\r\nConnection: close\r\n\r\n", gw.toString().c_str());
    unsigned long t0 = millis();
    while (!c81.available() && millis() - t0 < 5000) {
      if (!c81.connected()) break;
      delay(50);
    }
    Serial.printf("  -> Port 81: Connected: %d, Available: %d bytes (time: %lu ms)\n", c81.connected(), c81.available(), millis() - t0);
    int n = 0;
    while (c81.available() && n < 200) {
      Serial.write(c81.read());
      n++;
    }
    Serial.println("\n");
    c81.stop();
  }

  Serial.println("[PROBE FINISHED]\n");
}

void loop() {
  delay(2000);
}
