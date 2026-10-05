#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
WiFiClient socket;
PubSubClient mqtt(socket);
uint32_t retryAt = 0;
uint32_t blinkAt = 0;
void received(char*, byte* payload, unsigned int length) {
  // Forward unchanged so the backend owns validation and duplicate detection.
  if (length > 700) return;
  Serial.write(payload, length); Serial.println();
  mqtt.publish("iot/telemetry", payload, length, false);
  digitalWrite(18, HIGH); blinkAt = millis();
}
void setup() {
  Serial.begin(115200); pinMode(18, OUTPUT);
  WiFi.begin("Wokwi-GUEST", "", 6);
  mqtt.setServer("host.wokwi.internal", 1883);
  mqtt.setBufferSize(768); mqtt.setSocketTimeout(1); mqtt.setCallback(received);
}
void loop() {
  const uint32_t now = millis();
  if (WiFi.status() == WL_CONNECTED && !mqtt.connected() && now - retryAt >= 5000) {
    retryAt = now;
    if (mqtt.connect("iot-gateway-demo")) mqtt.subscribe("iot/raw");
  }
  mqtt.loop();
  if (now - blinkAt >= 100) digitalWrite(18, LOW);
  delay(5);
}
