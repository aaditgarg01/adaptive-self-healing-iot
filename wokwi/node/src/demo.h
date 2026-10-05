#pragma once
#include <WiFi.h>
#include <PubSubClient.h>

// Optional demonstrator only. No fault-mode labels are sent to the observer.
namespace demo {
enum Mode { NONE, BIAS, NOISE, LOSS, LATENCY, FAILURE, INTERMITTENT };
const char* names[] = {"NONE", "BIAS", "NOISE", "LOSS", "LATENCY", "FAILURE", "INTERMITTENT"};
Mode mode = NONE;
WiFiClient socket;
PubSubClient mqtt(socket);
char clientId[80];
String command;
uint32_t rng = 12345;
uint64_t reconnectAt = 0;
struct Pending { String payload; uint64_t due = 0; } pending[8];
uint32_t randomValue() { rng ^= rng << 13; rng ^= rng >> 17; rng ^= rng << 5; return rng; }
void nextMode() { mode = static_cast<Mode>((mode + 1) % 7); }
void begin(const char* boot) {
  snprintf(clientId, sizeof(clientId), "%s-%s", config::NODE_ID, boot);
  mqtt.setServer("host.wokwi.internal", 1883);
  mqtt.setBufferSize(768);
  mqtt.setSocketTimeout(1);
  WiFi.begin("Wokwi-GUEST", "", 6);
}
void transmit(const char* payload) {
  Serial.println(payload);
  if (mqtt.connected()) mqtt.publish("iot/raw", payload);
}
void service(uint64_t now) {
  while (Serial.available()) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n') {
      command.trim(); command.toUpperCase();
      for (int i = 0; i < 7; ++i) if (command == names[i]) mode = static_cast<Mode>(i);
      command = "";
    } else if (command.length() < 32) command += c;
  }
  if (WiFi.status() == WL_CONNECTED && !mqtt.connected() && now >= reconnectAt) {
    reconnectAt = now + 5000;
    mqtt.connect(clientId);
  }
  mqtt.loop();
  for (auto& item : pending) if (item.due && now >= item.due) {
    transmit(item.payload.c_str()); item.due = 0; item.payload = "";
  }
}
void alter(float& temperature, uint64_t now) {
  if (mode == BIAS || (mode == INTERMITTENT && (now / 10000) % 2)) temperature += 15;
  if (mode == NOISE) temperature += (static_cast<int>(randomValue() % 2401) - 1200) / 100.0f;
}
void send(const char* line, uint64_t now) {
  if (mode == FAILURE || (mode == LOSS && randomValue() % 100 < 70)) return;
  if (mode == LATENCY) {
    for (auto& item : pending) if (!item.due) { item.payload = line; item.due = now + 6000; return; }
    return;
  }
  transmit(line);
}
}  // namespace demo
