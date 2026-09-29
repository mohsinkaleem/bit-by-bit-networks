#!/usr/bin/env python3
"""Chapter 8 lab: many computers sharing one wire. Who wins, and how often do they collide?

Time is split into slots. Every frame takes FRAME slots to send. Each station gets new
frames to send at random. Three sets of manners to compare:

    aloha    just talk whenever you have something to say (retry after a random wait)
    csma     listen first: only start if the wire sounds quiet
    csmacd   listen first, keep listening, stop the moment you hear a collision,
             then wait a random time from a range that doubles after every collision

    python3 bus_sim.py                              csmacd, 6 stations, moderate load
    python3 bus_sim.py --mode aloha --load 0.5
    python3 bus_sim.py --sweep                      compare all three at many loads
"""
import argparse
import random

FRAME = 8          # slots per frame
SENSE_DELAY = 1    # it takes a slot for a new signal to reach everyone on the wire


class Station:
    def __init__(self, name):
        self.name = name
        self.queue = []            # arrival times of frames waiting to be sent
        self.wait_until = 0        # backoff
        self.attempts = 0
        self.sending = None        # the transmission in progress, if any


# --8<-- [start:backoff]
def backoff(station, mode, rng):
    """How many slots to wait before trying again."""
    station.attempts += 1
    if mode == "csmacd":
        k = min(station.attempts, 10)
        return rng.randint(0, 2 ** k - 1)                   # binary exponential backoff (in slots)
    return rng.randint(1, 20 * FRAME)                       # a plain random wait
# --8<-- [end:backoff]


def simulate(mode, n_stations, load, slots, seed=1, timeline=0):
    rng = random.Random(seed)
    stations = [Station(chr(ord("A") + i)) for i in range(n_stations)]
    per_station = load / FRAME / n_stations       # chance per slot that a station gets a new frame
    active = []                                    # transmissions currently on the wire
    good_slots = collisions = delivered = dropped = 0
    delays = []
    rows = {s.name: "" for s in stations}
    wire_row = ""

    for t in range(slots):
        for s in stations:
            if rng.random() < per_station:
                s.queue.append(t)

        # --8<-- [start:decide]
        # what does the wire sound like to everyone right now?
        busy = any(tx["start"] <= t - SENSE_DELAY for tx in active)
        for s in stations:
            if s.sending or not s.queue or t < s.wait_until:
                continue
            if mode in ("csma", "csmacd") and busy:
                continue                               # polite: wait for quiet
            tx = {"station": s, "start": t, "end": t + FRAME, "collided": False}
            s.sending = tx
            active.append(tx)
        if len(active) > 1:                            # two or more on the wire at once
            for tx in active:
                tx["collided"] = True
        # --8<-- [end:decide]

        # collision detection: senders notice once the other signal has reached them
        if mode == "csmacd":
            for tx in active:
                if tx["collided"] and t - tx["start"] >= SENSE_DELAY and tx["end"] > t + 1:
                    tx["end"] = t + 1                   # stop now (send a short jam signal)

        if timeline and t < timeline:
            for s in stations:
                tx = s.sending
                rows[s.name] += "." if not tx else ("#" if tx["collided"] else "█")
            wire_row += "." if not active else ("#" if len(active) > 1 or any(x["collided"] for x in active) else "█")

        for tx in list(active):
            if tx["end"] == t + 1:                      # finishes at the end of this slot
                active.remove(tx)
                s = tx["station"]
                s.sending = None
                if tx["collided"]:
                    collisions += 1
                    if s.attempts >= 15:
                        s.queue.pop(0)
                        s.attempts = 0
                        dropped += 1
                    else:
                        s.wait_until = t + 1 + backoff(s, mode, rng)
                else:
                    good_slots += FRAME
                    delivered += 1
                    delays.append(t + 1 - s.queue.pop(0))
                    s.attempts = 0

    if timeline:
        print(f"first {timeline} slots   █ = sending   # = collision   . = quiet")
        for name, row in rows.items():
            print(f"  station {name} │{row}")
        print(f"  the wire  │{wire_row}\n")
    return {
        "throughput": good_slots / slots,
        "delivered": delivered,
        "collisions": collisions,
        "dropped": dropped,
        "avg_delay": sum(delays) / len(delays) if delays else float("nan"),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["aloha", "csma", "csmacd"], default="csmacd")
    p.add_argument("--stations", type=int, default=6)
    p.add_argument("--load", type=float, default=0.6, help="offered load: 1.0 = exactly enough to fill the wire")
    p.add_argument("--slots", type=int, default=20000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--sweep", action="store_true")
    args = p.parse_args()

    if args.sweep:
        loads = [0.1, 0.3, 0.5, 0.7, 0.9, 1.2, 1.5, 2.0]
        print(f"useful throughput (fraction of time the wire carries a frame that gets through), {args.stations} stations")
        print(f"{'load':>6} " + " ".join(f"{m:>8}" for m in ("aloha", "csma", "csmacd")))
        for load in loads:
            row = [simulate(m, args.stations, load, args.slots, args.seed)["throughput"] for m in ("aloha", "csma", "csmacd")]
            print(f"{load:>6.1f} " + " ".join(f"{x:>8.0%}" for x in row))
        return

    r = simulate(args.mode, args.stations, args.load, args.slots, args.seed, timeline=96)
    print(f"mode={args.mode}  stations={args.stations}  offered load={args.load:.0%}  ({args.slots} slots)")
    print(f"  useful throughput: {r['throughput']:.0%} of the wire's capacity")
    print(f"  frames delivered:  {r['delivered']}")
    print(f"  collisions:        {r['collisions']}")
    print(f"  frames given up:   {r['dropped']}")
    print(f"  average wait:      {r['avg_delay']:.1f} slots from 'I have a frame' to 'it arrived'")


if __name__ == "__main__":
    main()
