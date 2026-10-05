import tempfile, unittest
from fastapi.testclient import TestClient
from backend.main import create_app


class ApiTests(unittest.TestCase):
    def test_control_validation_telemetry_and_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = directory + "/test.sqlite3"
            with TestClient(create_app(path)) as client:
                self.assertEqual(client.get("/api/health").status_code, 200)
                self.assertEqual(
                    client.post(
                        "/api/simulation", json={"scenario": "madeup"}
                    ).status_code,
                    422,
                )
                self.assertEqual(
                    client.post("/api/simulation", json={"nodes": 200}).status_code, 422
                )
                self.assertEqual(
                    client.post(
                        "/api/faults", json={"node_id": 500, "mode": "node_failure"}
                    ).status_code,
                    422,
                )
                client.post(
                    "/api/simulation",
                    json={"nodes": 9, "steps": 30, "scenario": "environment"},
                )
                for _ in range(30):
                    self.assertEqual(client.post("/api/step").status_code, 200)
                self.assertEqual(len(client.get("/api/runs").json()), 1)
                payload = {
                    "node_id": "N01",
                    "boot_id": "a" * 32,
                    "sequence": 1,
                    "uptime_ms": 2000,
                    "temperature": 27.0,
                    "humidity": 58.0,
                    "timestamp": None,
                    "sensor_ok": True,
                }
                self.assertEqual(
                    client.post("/api/telemetry", json=payload).status_code, 422
                )
                self.assertEqual(
                    client.post(
                        "/api/nodes", json={"node_id": "N01", "x": 0, "y": 0}
                    ).status_code,
                    200,
                )
                self.assertTrue(
                    client.post("/api/telemetry", json=payload).json()["accepted"]
                )
                self.assertFalse(
                    client.post("/api/telemetry", json=payload).json()["accepted"]
                )
                self.assertEqual(
                    client.post(
                        "/api/telemetry", json={**payload, "temperature": None}
                    ).status_code,
                    422,
                )
                self.assertEqual(
                    client.post(
                        "/api/telemetry", json={**payload, "fault": "sensor_bias"}
                    ).status_code,
                    422,
                )
                self.assertEqual(
                    client.post(
                        "/api/telemetry",
                        json={**payload, "sequence": 2, "uptime_ms": 1000},
                    ).status_code,
                    422,
                )
            with TestClient(create_app(path)) as client:
                self.assertEqual(len(client.get("/api/runs").json()), 1)
                self.assertEqual(
                    client.get("/api/live").json()["nodes"][0]["node_id"], "N01"
                )
                self.assertFalse(
                    client.post("/api/telemetry", json=payload).json()["accepted"]
                )


if __name__ == "__main__":
    unittest.main()
