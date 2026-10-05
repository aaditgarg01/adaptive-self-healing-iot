"""Run application tests locally without hardware, cloud simulation or dependencies."""

import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import tomllib

ROOT = Path(__file__).resolve().parents[2]
TESTS = Path(__file__).resolve().parent


class StageOneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which("clang++") or shutil.which("g++")
        if not compiler:
            raise RuntimeError("Install a C++ compiler (clang++ or g++).")
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "stage1-harness"
            subprocess.run(
                [
                    compiler,
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-I",
                    str(TESTS / "stubs"),
                    str(TESTS / "firmware_harness.cpp"),
                    "-o",
                    str(binary),
                ],
                check=True,
            )
            output = subprocess.check_output([str(binary)], text=True)
        cls.lines = output.splitlines()

        def reject_nonfinite(value):
            raise ValueError(f"Invalid JSON number: {value}")

        cls.records = [
            json.loads(line, parse_constant=reject_nonfinite) for line in cls.lines
        ]

    def test_json_contract_and_session(self):
        self.assertEqual(len(self.records), 14)
        keys = {
            "node_id",
            "boot_id",
            "sequence",
            "uptime_ms",
            "temperature",
            "humidity",
            "timestamp",
            "sensor_ok",
        }
        for index, record in enumerate(self.records, 1):
            self.assertEqual(set(record), keys)
            self.assertEqual(record["node_id"], "N01")
            self.assertRegex(record["boot_id"], r"^[0-9a-f]{32}$")
            self.assertEqual(record["boot_id"], self.records[0]["boot_id"])
            self.assertEqual(record["sequence"], index)
            self.assertIsNone(record["timestamp"])

    def test_sampling_and_long_uptime(self):
        times = [r["uptime_ms"] for r in self.records]
        self.assertEqual(times[:10], list(range(2000, 20001, 2000)))
        self.assertEqual(times[10:12], [27000, 29000])
        self.assertEqual(times[-2:], [(1 << 32) + 2000, (1 << 32) + 4000])
        self.assertTrue(all(b - a >= 2000 for a, b in zip(times, times[1:])))

    def test_changed_sensor_and_button_preserve_data(self):
        self.assertEqual(
            (self.records[0]["temperature"], self.records[0]["humidity"]), (27, 58)
        )
        for index in [1, 2]:
            self.assertEqual(
                (self.records[index]["temperature"], self.records[index]["humidity"]),
                (35.5, 72),
            )

    def test_errors_and_recovery(self):
        for index in [3, 4, 5, 8, 9]:
            self.assertFalse(self.records[index]["sensor_ok"])
            self.assertIsNone(self.records[index]["temperature"])
            self.assertIsNone(self.records[index]["humidity"])
        for index in [0, 1, 2, 6, 7, 10, 11, 12, 13]:
            self.assertTrue(self.records[index]["sensor_ok"])
        self.assertEqual(self.records[6]["temperature"], -40)
        self.assertEqual(self.records[7]["humidity"], 100)

    def test_diagram_and_build_paths(self):
        node = ROOT / "wokwi/node"
        diagram = json.loads((node / "diagram.json").read_text())
        ids = [part["id"] for part in diagram["parts"]]
        self.assertEqual(len(ids), len(set(ids)))
        parts = {p["id"]: p for p in diagram["parts"]}
        self.assertEqual(parts["dht"]["attrs"], {"temperature": "27", "humidity": "58"})
        edges = {frozenset(pair[:2]) for pair in diagram["connections"]}
        expected = [
            ("esp:D15", "dht:SDA"),
            ("esp:3V3", "dht:VCC"),
            ("esp:GND.1", "dht:GND"),
            ("esp:D23", "button:1.l"),
            ("button:2.l", "esp:GND.1"),
            ("esp:D18", "green_r:1"),
            ("green_r:2", "green:A"),
            ("green:C", "esp:GND.1"),
            ("esp:D19", "red_r:1"),
            ("red_r:2", "red:A"),
            ("red:C", "esp:GND.1"),
            ("esp:3V3", "pullup:1"),
            ("pullup:2", "dht:SDA"),
            ("esp:TX0", "$serialMonitor:RX"),
        ]
        for pair in expected:
            self.assertIn(frozenset(pair), edges)
        config = tomllib.loads((node / "wokwi.toml").read_text())["wokwi"]
        self.assertEqual(config["firmware"], ".pio/build/esp32dev/firmware.bin")
        self.assertEqual(config["elf"], ".pio/build/esp32dev/firmware.elf")


if __name__ == "__main__":
    unittest.main(verbosity=2)
