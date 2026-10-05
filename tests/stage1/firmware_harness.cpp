// Executes the actual firmware against deterministic hardware substitutes.
// This checks application behavior; it does not emulate DHT timing or an ESP32.
#include "Arduino.h"
#include "DHTesp.h"
#include <cassert>
#include <iostream>
#include <limits>

uint64_t fakeTimeMs = 0;
int pinValues[40] = {};
int pinModes[40] = {};
TempAndHumidity fakeReading{27.0f, 58.0f};
int fakeSensorStatus = 0;
unsigned sensorReads = 0;
TestSerial Serial;

#include "../../wokwi/node/src/main.cpp"

void tick(uint64_t time) { fakeTimeMs = time; loop(); }

int main() {
  pinValues[23] = HIGH;
  setup();
  assert(Serial.baud == 115200 && sensor.configuredPin == 15);
  assert(pinModes[23] == INPUT_PULLUP);
  assert(pinModes[18] == OUTPUT && pinModes[19] == OUTPUT);
  assert(pinValues[18] == LOW && pinValues[19] == LOW);
  tick(1999);
  assert(sensorReads == 0 && Serial.lines.empty());
  tick(2000);
  assert(sensorReads == 1 && pinValues[18] == HIGH && pinValues[19] == LOW);
  fakeReading = {35.5f, 72.0f};
  tick(3999);
  assert(sensorReads == 1);
  tick(4000);
  assert(sensorReads == 2);

  // Contact bounce must not trigger an LED test; one stable press does.
  pinValues[23] = LOW; tick(4100);
  pinValues[23] = HIGH; tick(4110);
  pinValues[23] = LOW; tick(4120);
  tick(4159); assert(pinValues[19] == LOW);
  tick(4160); assert(pinValues[18] == HIGH && pinValues[19] == HIGH);
  tick(4659); assert(pinValues[19] == HIGH);
  tick(4660); assert(pinValues[19] == LOW);
  tick(5000); assert(pinValues[19] == LOW); // Holding does not retrigger.
  pinValues[23] = HIGH; tick(5100); tick(5140);
  tick(6000); // Button must not change measurements or sampling cadence.

  fakeReading.temperature = std::numeric_limits<float>::quiet_NaN();
  tick(8000); assert(pinValues[18] == LOW && pinValues[19] == HIGH);
  fakeReading = {27, 58}; fakeSensorStatus = DHTesp::ERROR_TIMEOUT;
  tick(10000); assert(pinValues[19] == HIGH);
  fakeSensorStatus = DHTesp::ERROR_NONE; fakeReading.humidity = 101;
  tick(12000);
  fakeReading = {-40, 0}; tick(14000);
  assert(pinValues[18] == HIGH && pinValues[19] == LOW);
  fakeReading = {80, 100}; tick(16000);
  fakeReading = {std::numeric_limits<float>::infinity(), 58}; tick(18000);
  fakeReading = {27, 58}; fakeSensorStatus = DHTesp::ERROR_CHECKSUM; tick(20000);
  fakeSensorStatus = DHTesp::ERROR_NONE;

  // A late scheduler produces one sample, never a catch-up burst.
  tick(27000); const auto afterDelay = Serial.lines.size();
  tick(27005); assert(Serial.lines.size() == afterDelay);
  tick(29000);
  tick((1ULL << 32) + 2000); // Beyond millis() rollover.
  const auto afterRollover = Serial.lines.size();
  tick((1ULL << 32) + 2001); assert(Serial.lines.size() == afterRollover);
  tick((1ULL << 32) + 4000);
  for (const auto& line : Serial.lines) std::cout << line << '\n';
}
