"""
IoT camera simulator.
Every few seconds it "reads" a random license plate and sends it to the API
as an HTTP POST, the same way the real camera would.
Uses only the Python standard library, so the image needs no pip install.
"""
import json
import os
import random
import time
import urllib.error
import urllib.request

API_URL = os.getenv("API_URL", "http://api:5000/api/cars")
MIN_SECONDS = float(os.getenv("CAMERA_INTERVAL_MIN", "6"))
MAX_SECONDS = float(os.getenv("CAMERA_INTERVAL_MAX", "15"))
GATES = ["A", "B"]


def random_plate():
    if random.random() < 0.5:
        d = f"{random.randint(0, 9_999_999):07d}"
        return f"{d[:2]}-{d[2:5]}-{d[5:]}"
    d = f"{random.randint(0, 99_999_999):08d}"
    return f"{d[:3]}-{d[3:5]}-{d[5:]}"


def send(plate):
    body = json.dumps({"plate": plate, "gate": random.choice(GATES)}).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            print(f"[camera] {plate} -> {res.status}", flush=True)
    except urllib.error.HTTPError as e:      # API answered with 4xx/5xx (e.g. 409 lot full)
        print(f"[camera] {plate} -> {e.code} {e.read().decode()}", flush=True)
    except urllib.error.URLError as e:       # API not reachable
        print(f"[camera] API unreachable: {e.reason}", flush=True)


if __name__ == "__main__":
    print(f"[camera] started, posting to {API_URL}", flush=True)
    while True:
        send(random_plate())
        time.sleep(random.uniform(MIN_SECONDS, MAX_SECONDS))
