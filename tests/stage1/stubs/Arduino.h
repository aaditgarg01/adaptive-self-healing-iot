#pragma once
#include <cstdint>
#include <string>
#include <vector>

constexpr int LOW = 0;
constexpr int HIGH = 1;
constexpr int OUTPUT = 1;
constexpr int INPUT_PULLUP = 2;
extern uint64_t fakeTimeMs;
extern int pinValues[40];
extern int pinModes[40];
inline void pinMode(int pin, int mode) { pinModes[pin] = mode; }
inline int digitalRead(int pin) { return pinValues[pin]; }
inline void digitalWrite(int pin, int value) { pinValues[pin] = value; }
inline void delay(unsigned long ms) { fakeTimeMs += ms; }
struct TestSerial {
  unsigned long baud = 0;
  std::vector<std::string> lines;
  void begin(unsigned long value) { baud = value; }
  void println(const char* line) { lines.emplace_back(line); }
};
extern TestSerial Serial;
