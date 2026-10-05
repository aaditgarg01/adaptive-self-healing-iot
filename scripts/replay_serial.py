"""Replay a local captured JSONL file; ignores ESP32 boot text."""

import argparse, json, time, urllib.request

p = argparse.ArgumentParser()
p.add_argument("file")
p.add_argument("--api", default="http://127.0.0.1:8000")
p.add_argument("--interval", type=float, default=2.0)
args = p.parse_args()
with open(args.file) as source:
    for line in source:
        if not line.lstrip().startswith("{"):
            continue
        payload = json.loads(line)
        req = urllib.request.Request(
            args.api + "/api/telemetry",
            json.dumps(payload).encode(),
            {"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            print(response.read().decode())
        time.sleep(args.interval)
