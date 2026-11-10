"""
Smart Parking API
-----------------
POST   /api/cars          <- the IoT camera reports a car that entered
GET    /api/cars          <- the dashboard reads the cars currently inside
DELETE /api/cars/<plate>  <- the guard releases a car (returns the price)
GET    /api/stats         <- capacity, revenue, last exits
GET    /api/health        <- used by the Docker healthcheck

Redis data model:
  parking:inside   sorted set   member = plate, score = entry time (epoch)
  car:<plate>      hash         plate, entered_at, gate, message
  parking:history  list         JSON of the last 20 cars that left
  stats:total_entries / stats:revenue   counters
"""
import json
import os
import time

import redis
from flask import Flask, jsonify, request

from logic import calc_price, entry_message, normalize_plate

# ---- configuration (all of it comes from environment variables in docker-compose.yml)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
MAX_CAPACITY = int(os.getenv("MAX_CAPACITY", "20"))
BILLING_UNIT_SECONDS = int(os.getenv("BILLING_UNIT_SECONDS", "3600"))
PRICE_FIRST_UNIT = int(os.getenv("PRICE_FIRST_UNIT", "15"))
PRICE_NEXT_UNIT = int(os.getenv("PRICE_NEXT_UNIT", "10"))

INSIDE = "parking:inside"
HISTORY = "parking:history"

app = Flask(__name__)
app.json.ensure_ascii = False  # return Hebrew as Hebrew, not ב...

# decode_responses=True -> we get str back from Redis instead of bytes
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


class AlreadyInside(Exception):
    pass


class LotFull(Exception):
    pass


def car_view(car, now):
    """Builds the JSON the dashboard gets for one car."""
    entered_at = float(car["entered_at"])
    units, price = calc_price(entered_at, now, BILLING_UNIT_SECONDS,
                              PRICE_FIRST_UNIT, PRICE_NEXT_UNIT, car["plate"])
    return {
        "plate": car["plate"],
        "entered_at": entered_at,
        "duration_seconds": int(now - entered_at),
        "units": units,
        "price": price,
        "gate": car.get("gate", "A"),
        "message": car.get("message", ""),
    }


@app.get("/api/health")
def health():
    try:
        r.ping()
        return jsonify(status="ok", redis="up")
    except redis.RedisError:
        return jsonify(status="error", redis="down"), 503


@app.post("/api/cars")
def car_entered():
    body = request.get_json(silent=True) or {}
    try:
        plate = normalize_plate(body.get("plate", ""))
    except ValueError as e:
        return jsonify(error=str(e)), 400

    gate = str(body.get("gate", "A"))[:10]
    now = time.time()
    message = entry_message(plate)

    # WATCH + MULTI makes "check capacity, then add" atomic: if two cameras
    # report at the same moment, Redis retries instead of overfilling the lot.
    def enter(pipe):
        if pipe.zscore(INSIDE, plate) is not None:
            raise AlreadyInside()
        if pipe.zcard(INSIDE) >= MAX_CAPACITY:
            raise LotFull()
        pipe.multi()
        pipe.zadd(INSIDE, {plate: now})
        pipe.hset(f"car:{plate}", mapping={
            "plate": plate, "entered_at": now, "gate": gate, "message": message,
        })
        pipe.incr("stats:total_entries")

    try:
        r.transaction(enter, INSIDE)
    except AlreadyInside:
        return jsonify(error=f"{plate} is already inside"), 409
    except LotFull:
        return jsonify(error="parking lot is full", full=True), 409

    car = {"plate": plate, "entered_at": now, "gate": gate, "message": message}
    return jsonify(car_view(car, now)), 201


@app.get("/api/cars")
def list_cars():
    now = time.time()
    plates = r.zrevrange(INSIDE, 0, -1)  # newest first
    pipe = r.pipeline()
    for p in plates:
        pipe.hgetall(f"car:{p}")
    cars = [car_view(c, now) for c in pipe.execute() if c]
    return jsonify(cars)


@app.delete("/api/cars/<plate>")
def release_car(plate):
    try:
        plate = normalize_plate(plate)
    except ValueError as e:
        return jsonify(error=str(e)), 400

    car = r.hgetall(f"car:{plate}")
    if not car:
        return jsonify(error=f"{plate} is not inside"), 404

    now = time.time()
    view = car_view(car, now)
    view["left_at"] = now

    pipe = r.pipeline()  # pipeline() is transactional (MULTI/EXEC) by default
    pipe.zrem(INSIDE, plate)
    pipe.delete(f"car:{plate}")
    pipe.lpush(HISTORY, json.dumps(view, ensure_ascii=False))
    pipe.ltrim(HISTORY, 0, 19)  # keep only the last 20 exits
    pipe.incrby("stats:revenue", view["price"])
    pipe.execute()
    return jsonify(view)


@app.get("/api/stats")
def stats():
    inside = r.zcard(INSIDE)
    return jsonify(
        inside=inside,
        capacity=MAX_CAPACITY,
        free=max(0, MAX_CAPACITY - inside),
        is_full=inside >= MAX_CAPACITY,
        total_entries=int(r.get("stats:total_entries") or 0),
        revenue=int(r.get("stats:revenue") or 0),
        pricing={
            "unit_seconds": BILLING_UNIT_SECONDS,
            "first_unit": PRICE_FIRST_UNIT,
            "next_unit": PRICE_NEXT_UNIT,
        },
        history=[json.loads(h) for h in r.lrange(HISTORY, 0, 9)],
    )


if __name__ == "__main__":
    # Only for running locally without Docker. In the container gunicorn runs the app.
    app.run(host="0.0.0.0", port=5000, debug=True)
