#pragma once
#include <cstdint>
struct TempAndHumidity { float temperature; float humidity; };
extern TempAndHumidity fakeReading;
extern int fakeSensorStatus;
extern unsigned sensorReads;
class DHTesp {
 public:
  enum DHT_MODEL_t { DHT22 };
  enum DHT_ERROR_t { ERROR_NONE, ERROR_TIMEOUT, ERROR_CHECKSUM };
  uint8_t configuredPin = 0;
  void setup(uint8_t pin, DHT_MODEL_t) { configuredPin = pin; }
  TempAndHumidity getTempAndHumidity() { ++sensorReads; return fakeReading; }
  int getStatus() { return fakeSensorStatus; }
};
