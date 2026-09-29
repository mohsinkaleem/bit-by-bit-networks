#!/usr/bin/env python3
"""Chapter 19 lab: Wi-Fi's "listen, wait a random while, then talk" (CSMA/CA), slot by slot.

Every station always has something to send (the busiest possible evening in Alice's dorm).

    python3 wifi_sim.py                          2, 5, 10, 20 and 50 stations sharing one channel
    python3 wifi_sim.py --stations 4 --slow 1    ...one of them far away, sending 8 times slower
    python3 wifi_sim.py --stations 6 --hidden    half the stations can't hear the other half
    python3 wifi_sim.py --stations 6 --hidden --rts   ...so they ask permission first (RTS/CTS)
    python3 wifi_sim.py --stations 3 --show 120  draw the first 120 slots
"""
import argparse
import random

SLOT_US = 9                 # one backoff slot on 5 GHz Wi-Fi is 9 microseconds
DIFS = 4                    # quiet slots a station waits before it starts counting down
FRAME = 20                  # a data frame plus its ACK, in slots (about 180 µs)
RTS_CTS = 3                 # "may I?" plus "go ahead", in slots
CW_MIN, CW_MAX, RETRIES = 15, 1023, 7


class Station:
    def __init__(self, name, group, slow=False):
        self.name, self.group, self.slow = name, group, slow
        self.cw = CW_MIN
        self.backoff = random.randint(0, self.cw)
        self.quiet = 0              # how many quiet slots in a row this station has heard
        self.sending = 0            # slots left of the current transmission
        self.clean = True           # has anything else been sent at the same time?
        self.asking = False         # is the current transmission an RTS?
        self.tries = 0
        self.delivered = self.lost = self.collisions = self.airtime = 0

    def duration(self):
        return FRAME * (8 if self.slow else 1)


# --8<-- [start:sim]
def simulate(stations, slots, rts=False, hidden=False, trace=None):
    nav = 0                                         # slots everyone must stay quiet, after a CTS
    for t in range(slots):
        talking = [s for s in stations if s.sending]
        if len(talking) > 1:                        # two at once: the access point hears only noise
            for s in talking:
                s.clean = False
        for s in stations:
            hears_someone = any(o is not s and (not hidden or o.group == s.group) for o in talking)
            if s.sending:
                s.sending -= 1
                s.airtime += 1
                if s.sending == 0:
                    nav = finish(s, rts, nav)
            elif nav or hears_someone:
                s.quiet = 0                         # busy: freeze the countdown
            else:
                s.quiet += 1
                if s.quiet > DIFS:
                    if s.backoff == 0:
                        s.asking = rts
                        s.sending = RTS_CTS if rts else s.duration()
                        s.clean = True
                    else:
                        s.backoff -= 1
        nav = max(0, nav - 1)
        if trace is not None:
            trace.append([("x" if not s.clean else "r" if s.asking else "#") if s.sending else "." for s in stations])
    return stations


def finish(s, rts, nav):
    """A transmission just ended. Did it get through?"""
    if s.clean and s.asking:                        # the RTS got through: the CTS silences everyone
        s.asking = False
        s.sending = s.duration()
        return s.duration()
    if s.clean:
        s.delivered += 1
        s.cw, s.tries = CW_MIN, 0                   # success: back to a small window
    else:
        s.collisions += 1
        s.tries += 1
        s.cw = min(2 * s.cw + 1, CW_MAX)            # no ACK: assume a collision, double the window
        if s.tries > RETRIES:
            s.lost += 1
            s.cw, s.tries = CW_MIN, 0
    s.backoff = random.randint(0, s.cw)
    s.asking = False
    return nav
# --8<-- [end:sim]


def run(n, slots, slow=0, hidden=False, rts=False, seed=1, trace=None):
    random.seed(seed)
    stations = [Station(chr(65 + i) if i < 26 else str(i), group=i % 2, slow=i < slow) for i in range(n)]
    return simulate(stations, slots, rts=rts, hidden=hidden, trace=trace)


def report(stations, slots):
    useful = sum(s.delivered * FRAME for s in stations)          # the data itself, at full speed
    frames = sum(s.delivered for s in stations)
    tries = frames + sum(s.collisions for s in stations)
    seconds = slots * SLOT_US / 1e6
    return useful / slots, (tries - frames) / max(tries, 1), frames / seconds


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--stations", type=int, nargs="*", default=[2, 5, 10, 20, 50])
    p.add_argument("--slow", type=int, default=0, help="how many stations send 8 times slower")
    p.add_argument("--hidden", action="store_true", help="odd and even stations can't hear each other")
    p.add_argument("--rts", action="store_true", help="ask permission with RTS/CTS before each frame")
    p.add_argument("--show", type=int, metavar="SLOTS", help="draw the first SLOTS slots")
    p.add_argument("--slots", type=int, default=200_000)
    args = p.parse_args()
    if args.show:
        trace = []
        run(args.stations[0], args.show, args.slow, args.hidden, args.rts, trace=trace)
        print("# = sending   x = sending, but colliding   r = RTS   . = quiet\n")
        for i in range(args.stations[0]):
            print(f"{chr(65 + i)}  " + "".join(row[i] for row in trace))
        return
    print(f"{'stations':>9} {'air used for data':>18} {'attempts that collided':>23} {'frames per second':>18}")
    for n in args.stations:
        stations = run(n, args.slots, args.slow, args.hidden, args.rts)
        used, collided, fps = report(stations, args.slots)
        print(f"{n:>9} {used:>18.0%} {collided:>23.0%} {fps:>18,.0f}")
        if len(args.stations) == 1:
            print()
            total_air = sum(s.airtime for s in stations)
            for s in stations:
                kind = "slow, 8× longer frames" if s.slow else "normal"
                print(f"   station {s.name} ({kind}): {s.delivered:>6,} frames delivered, "
                      f"{s.airtime / total_air:>4.0%} of the airtime, {s.lost} given up")


if __name__ == "__main__":
    main()
