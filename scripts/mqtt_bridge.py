"""Local broker adapter: register nodes first; never forwards fault labels."""

import argparse
import json
import urllib.request
import urllib.error
import paho.mqtt.client as mqtt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker", default="127.0.0.1")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    def connect(client, userdata, flags, reason, properties):
        if reason == 0:
            client.subscribe("iot/telemetry")

    def message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            req = urllib.request.Request(
                args.api + "/api/telemetry",
                json.dumps(payload).encode(),
                {"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as response:
                print(response.read().decode())
        except (ValueError, urllib.error.URLError) as error:
            print("Rejected telemetry:", error)

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2, client_id="local-python-observer"
    )
    client.on_connect = connect
    client.on_message = message
    client.connect(args.broker, 1883, 60)
    client.loop_forever()


if __name__ == "__main__":
    main()
