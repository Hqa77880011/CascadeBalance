import collections

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


METHODS = ["sparse_public", "dense_public", "no_defense", "poisson_cover", "queue_driven"]


def calendar(config, dense=False):
    mixes, users, ticks = config["mixes"], config["users"], config["ticks"]
    capacity, gap, quota = config["capacity"], config["gap"], config["quota"]
    size = mixes * users * ticks
    rows, low, high = [], [], []
    for m in range(mixes):
        for t in range(ticks):
            row = np.zeros(size)
            for u in range(users):
                row[(m * users + u) * ticks + t] = 1
            rows.append(row)
            low.append(0)
            high.append(capacity)
        for u in range(users):
            for t in range(ticks):
                row = np.zeros(size)
                for j in range(gap):
                    row[(m * users + u) * ticks + (t + j) % ticks] += 1
                rows.append(row)
                low.append(quota)
                high.append(np.inf)
    if dense:
        slots_per_pair = int(np.ceil(quota / gap))
        result = np.full((mixes, users, ticks), slots_per_pair, dtype=int)
        if users * slots_per_pair > capacity:
            raise ValueError("Dense calendar exceeds public node capacity")
        return result
    objective = 1 + np.arange(size) * 1e-8
    result = milp(
        objective,
        integrality=np.ones(size),
        bounds=Bounds(np.zeros(size), np.full(size, capacity)),
        constraints=LinearConstraint(np.asarray(rows), np.asarray(low), np.asarray(high)),
        options={"time_limit": 30},
    )
    if not result.success:
        raise ValueError("Public service class is not certified feasible: " + result.message)
    values = np.rint(result.x).astype(int)
    matrix = np.asarray(rows) @ values
    if np.any(matrix < np.asarray(low) - 1e-7) or np.any(matrix > np.asarray(high) + 1e-7):
        raise ValueError("Calendar violates a capacity/window constraint")
    return values.reshape(mixes, users, ticks)


def generate(rng, count):
    for index in range(count):
        topic = rng.randrange(2)
        config = {
            "mixes": 2,
            "users": 2,
            "ticks": 16,
            "capacity": 2,
            "gap": 4,
            "quota": 1,
            "epochs": 4,
            "delta": 0.05,
            "packet_bytes": 512,
        }
        packets = []
        for i in range(12):
            packets.append(
                {
                    "id": str(i),
                    "mix": topic if rng.random() < 0.8 else 1 - topic,
                    "user": rng.randrange(2),
                    "arrival": rng.randrange(32),
                    "deadline": 16,
                    "loop": i % 4 == 0,
                    "attacked": i % 4 == 0 and rng.random() < 0.3,
                }
            )
        yield {
            "id": str(index),
            "family": f"episode-{index}",
            "config": config,
            "packets": packets,
            "topic": topic,
            "seed": rng.randrange(2**31),
        }


def run_case(case, method):
    cfg = case["config"]
    schedule = calendar(cfg, method == "dense_public")
    queues = {(m, u): collections.deque() for m in range(cfg["mixes"]) for u in range(cfg["users"])}
    arrivals = collections.defaultdict(list)
    for packet in sorted(case["packets"], key=lambda p: (p["arrival"], p["id"])):
        arrivals[packet["arrival"]].append(packet)
    trace = []
    delivered, expired, waits = [], [], []
    rng = np.random.default_rng(case["seed"])
    total_ticks = cfg["ticks"] * cfg["epochs"]
    for t in range(total_ticks):
        for packet in arrivals[t]:
            queues[packet["mix"], packet["user"]].append(packet)
        for pair, queue in queues.items():
            m, u = pair
            while queue and t - queue[0]["arrival"] > queue[0]["deadline"]:
                expired.append(queue.popleft()["id"])
            slots = int(schedule[m, u, t % cfg["ticks"]])
            if method in ("no_defense", "queue_driven"):
                slots = min(cfg["capacity"], len(queue))
            elif method == "poisson_cover":
                slots = int(rng.poisson(schedule.mean())) + len(arrivals[t]) * int(bool(queue))
            for _ in range(slots):
                trace.append([t, m, u, cfg["packet_bytes"]])
                if queue:
                    packet = queue.popleft()
                    if not packet["attacked"]:
                        delivered.append(packet["id"])
                        waits.append(t - packet["arrival"])
    pending = [p["id"] for queue in queues.values() for p in queue]
    feature = np.zeros((cfg["mixes"], cfg["users"], 8))
    for t, m, u, size in trace:
        feature[m, u, min(7, t * 8 // total_ticks)] += size
    loop_ids = {p["id"] for p in case["packets"] if p["loop"]}
    alarm = loop_ids - set(delivered)
    return {
        "delivered": delivered,
        "expired": expired + pending,
        "wait_ticks": waits,
        "trace": trace,
        "alarms": sorted(alarm),
        "features": feature.ravel().tolist(),
        "attack_label": case["topic"],
    }


def score(case, result):
    real = [p for p in case["packets"] if not p["loop"]]
    loops = [p for p in case["packets"] if p["loop"]]
    attacked = [p for p in loops if p["attacked"]]
    benign = [p for p in loops if not p["attacked"]]
    waits = result["wait_ticks"]
    total = len(result["trace"]) * case["config"]["packet_bytes"]
    return {
        "real_delivery": sum(p["id"] in result["delivered"] for p in real) / len(real)
        if real
        else None,
        "loop_tpr": sum(p["id"] in result["alarms"] for p in attacked) / len(attacked)
        if attacked
        else None,
        "loop_fpr": sum(p["id"] in result["alarms"] for p in benign) / len(benign)
        if benign
        else None,
        "byte_ratio": total / (len(case["packets"]) * case["config"]["packet_bytes"]),
        "scheduled_bytes": total,
        "mean_wait_seconds": float(np.mean(waits)) * case["config"]["delta"] if waits else None,
        "p95_wait_seconds": float(np.quantile(waits, 0.95)) * case["config"]["delta"]
        if waits
        else None,
        "expiry_count": len(result["expired"]),
        "legal_effects": len(result["delivered"]),
    }
