#include <Arduino.h>
#include <DHTesp.h>
#include <esp_system.h>
#include <esp_timer.h>
#include <cmath>
#include <cstdio>

namespace config {
#ifndef NODE_ID_VALUE
#define NODE_ID_VALUE "N01"
#endif
constexpr char NODE_ID[] = NODE_ID_VALUE;
constexpr uint8_t DHT_PIN = 15;
constexpr uint8_t GREEN_LED_PIN = 18;
constexpr uint8_t RED_LED_PIN = 19;
constexpr uint8_t BUTTON_PIN = 23;
constexpr uint32_t SERIAL_BAUD = 115200;
constexpr uint64_t SAMPLE_INTERVAL_MS = 2000;
constexpr uint64_t DEBOUNCE_MS = 40;
constexpr uint64_t LED_TEST_MS = 500;
}  // namespace config

struct SensorReading {
  float temperature;
  float humidity;
  bool valid;
};

struct ButtonState {
  bool rawPressed = false;
  bool stablePressed = false;
  uint64_t changedAtMs = 0;
  uint64_t ledTestUntilMs = 0;
};

#ifdef IOT_DEMO
#include "demo.h"
#endif

DHTesp sensor;
ButtonState button;
char bootId[33] = {};
uint64_t sequenceNumber = 0;
uint64_t lastSampleMs = 0;
bool sampleValid = false;
bool sampled = false;

uint64_t uptimeMs() {
  // The ESP32's 64-bit monotonic timer avoids millis()'s 49-day rollover.
  return static_cast<uint64_t>(esp_timer_get_time()) / 1000;
}

void initializeBootId() {
  // Diagnostic session identifier, not a security token. Simulators may replay RNG state.
  for (size_t index = 0; index < 4; ++index) {
    snprintf(bootId + index * 8, 9, "%08lx", static_cast<unsigned long>(esp_random()));
  }
}

SensorReading readSensor() {
  const TempAndHumidity value = sensor.getTempAndHumidity();
  const bool valid = sensor.getStatus() == DHTesp::ERROR_NONE &&
                     std::isfinite(value.temperature) && std::isfinite(value.humidity) &&
                     value.temperature >= -40.0f && value.temperature <= 80.0f &&
                     value.humidity >= 0.0f && value.humidity <= 100.0f;
  return {value.temperature, value.humidity, valid};
}

void emitTelemetry(const SensorReading& reading, uint64_t capturedAtMs) {
  char temperature[24] = "null";
  char humidity[24] = "null";
  if (reading.valid) {
    snprintf(temperature, sizeof(temperature), "%.2f", reading.temperature);
    snprintf(humidity, sizeof(humidity), "%.2f", reading.humidity);
  }

  // No RTC/NTP in Stage 1. Unknown UTC is JSON null, never fabricated from uptime.
  char line[384];
  const int length = snprintf(
      line, sizeof(line),
      "{\"node_id\":\"%s\",\"boot_id\":\"%s\",\"sequence\":%llu,"
      "\"uptime_ms\":%llu,\"temperature\":%s,\"humidity\":%s,"
      "\"timestamp\":null,\"sensor_ok\":%s}",
      config::NODE_ID, bootId, static_cast<unsigned long long>(sequenceNumber),
      static_cast<unsigned long long>(capturedAtMs), temperature, humidity,
      reading.valid ? "true" : "false");
  if (length > 0 && static_cast<size_t>(length) < sizeof(line)) {
    #ifdef IOT_DEMO
    demo::send(line, uptimeMs());
    #else
    Serial.println(line);
    #endif
  } else {
    Serial.println("{\"type\":\"error\",\"code\":\"telemetry_overflow\"}");
  }
}

void serviceButton(uint64_t nowMs) {
  const bool pressed = digitalRead(config::BUTTON_PIN) == LOW;
  if (pressed != button.rawPressed) {
    button.rawPressed = pressed;
    button.changedAtMs = nowMs;
  }
  if (nowMs - button.changedAtMs >= config::DEBOUNCE_MS &&
      pressed != button.stablePressed) {
    button.stablePressed = pressed;
    if (pressed) {
      // Reserve this input for later fault modes. Stage 1 only exercises the LEDs.
      button.ledTestUntilMs = nowMs + config::LED_TEST_MS;
      #ifdef IOT_DEMO
      demo::nextMode();
      #endif
    }
  }
}

void updateStatusLeds(uint64_t nowMs) {
  const bool ledTest = nowMs < button.ledTestUntilMs;
  digitalWrite(config::GREEN_LED_PIN, (sampled && sampleValid) || ledTest ? HIGH : LOW);
  digitalWrite(config::RED_LED_PIN, (sampled && !sampleValid) || ledTest ? HIGH : LOW);
}

void setup() {
  Serial.begin(config::SERIAL_BAUD);
  pinMode(config::GREEN_LED_PIN, OUTPUT);
  pinMode(config::RED_LED_PIN, OUTPUT);
  pinMode(config::BUTTON_PIN, INPUT_PULLUP);
  digitalWrite(config::GREEN_LED_PIN, LOW);
  digitalWrite(config::RED_LED_PIN, LOW);
  initializeBootId();
  sensor.setup(config::DHT_PIN, DHTesp::DHT22);
  lastSampleMs = uptimeMs();
  #ifdef IOT_DEMO
  demo::begin(bootId);
  #endif
}

void loop() {
  const uint64_t nowMs = uptimeMs();
  serviceButton(nowMs);
  #ifdef IOT_DEMO
  demo::service(nowMs);
  #endif
  if (nowMs - lastSampleMs >= config::SAMPLE_INTERVAL_MS) {
    // No catch-up bursts: allow a full sensor interval after a delayed sample.
    lastSampleMs = nowMs;
    SensorReading reading = readSensor();
    #ifdef IOT_DEMO
    demo::alter(reading.temperature, nowMs);
    #endif
    sampled = true;
    sampleValid = reading.valid;
    ++sequenceNumber;
    emitTelemetry(reading, nowMs);
  }
  updateStatusLeds(uptimeMs());
  delay(5);
}
