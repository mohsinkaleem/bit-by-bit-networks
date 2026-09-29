#!/usr/bin/env python3
"""Chapter 28 lab: congestion control, simulated one round trip at a time.

    python3 ccsim.py                      Reno through a link with a modest buffer
    python3 ccsim.py --algo cubic         the algorithm Linux, macOS and Windows use by default
    python3 ccsim.py --algo bbr           Google's model-based algorithm
    python3 ccsim.py --buffer 400         a huge buffer: full speed, but look at the delay (bufferbloat)
    python3 ccsim.py --flows 2            two connections sharing the link: do they share fairly?

The link carries --rate packets per millisecond, the empty round trip takes --rtt ms, and the
router in the middle can queue --buffer packets. Anything more is dropped.
"""
import argparse


# --8<-- [start:algos]
class Reno:
    """Slow start, then additive increase, multiplicative decrease (AIMD)."""
    def __init__(self):
        self.cwnd, self.ssthresh = 10.0, float("inf")      # 10 segments: the usual starting window

    def on_round(self, lost, rtt, delivered):
        if lost:
            self.ssthresh = max(2.0, self.cwnd // 2)         # halve it…
            self.cwnd = self.ssthresh
        elif self.cwnd < self.ssthresh:
            self.cwnd *= 2                                   # slow start: double every round trip
        else:
            self.cwnd += 1                                   # congestion avoidance: one more per round trip


class Cubic(Reno):
    """After a loss, grow back quickly to where the loss happened, then carefully, then quickly again.
    On short round trips it never grows slower than Reno would (the “TCP-friendly” rule)."""
    C, BETA = 0.4, 0.7

    def __init__(self):
        super().__init__()
        self.wmax, self.t = 0.0, 0.0

    def on_round(self, lost, rtt, delivered):
        if lost:
            self.wmax = self.cwnd
            self.cwnd = self.ssthresh = max(2.0, self.cwnd * self.BETA)   # only down to 70%
            self.t = 0.0
        elif self.cwnd < self.ssthresh:
            self.cwnd *= 2
        else:
            self.t += rtt / 1000                             # seconds since the last loss
            k = (self.wmax * (1 - self.BETA) / self.C) ** (1 / 3)
            cubic = self.C * (self.t - k) ** 3 + self.wmax
            reno = self.wmax * self.BETA + 3 * (1 - self.BETA) / (1 + self.BETA) * self.t * 1000 / rtt
            self.cwnd = max(cubic, reno)


class BBR:
    """Don't wait for losses: measure the bottleneck's speed and the empty round trip, and send just that."""
    GAINS = [1.25, 0.75, 1, 1, 1, 1, 1, 1]

    def __init__(self):
        self.cwnd, self.btlbw, self.minrtt, self.round, self.startup = 10.0, 0.0, float("inf"), 0, True

    def on_round(self, lost, rtt, delivered):
        self.round += 1
        self.minrtt = min(self.minrtt, rtt)
        rate = delivered / rtt                               # packets per ms actually delivered
        if self.startup and rate < self.btlbw * 1.25:
            self.startup = False                             # stopped getting faster: the pipe is full
        self.btlbw = max(self.btlbw, rate)
        bdp = self.btlbw * self.minrtt
        gain = 2.0 if self.startup else self.GAINS[self.round % len(self.GAINS)]
        self.cwnd = max(4.0, gain * bdp)
# --8<-- [end:algos]


# --8<-- [start:link]
def simulate(algos, rate, base_rtt, buffer, rounds):
    """One line per round trip. The link can deliver rate * base_rtt packets per round (the BDP);
    anything beyond that waits in the queue, and anything beyond the queue is dropped."""
    bdp = rate * base_rtt
    queue = 0.0
    history = []
    for r in range(rounds):
        want = sum(a.cwnd for a in algos)
        queue = max(0.0, want - bdp)                          # what doesn't fit in the pipe waits
        lost = queue > buffer
        queue = min(queue, buffer)
        rtt = base_rtt + queue / rate                         # waiting in the queue adds delay
        delivered_total = min(want, bdp + buffer)
        for a in algos:
            share = a.cwnd / want if want else 0
            # the biggest sender is the most likely to see a drop
            a.on_round(lost and (share >= 1 / len(algos) or len(algos) == 1), rtt, delivered_total * share)
        history.append((r, [a.cwnd for a in algos], queue, rtt, lost, min(1.0, want / bdp)))
    return history, bdp
# --8<-- [end:link]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--algo", choices=["reno", "cubic", "bbr"], default="reno")
    p.add_argument("--rate", type=float, default=10, help="packets per ms the link can carry (10 ≈ 120 Mbit/s)")
    p.add_argument("--rtt", type=float, default=12, help="round-trip time with empty queues, ms")
    p.add_argument("--buffer", type=float, default=60, help="packets the router can queue")
    p.add_argument("--flows", type=int, default=1)
    p.add_argument("--rounds", type=int, default=None, help="round trips to simulate")
    args = p.parse_args()
    make = {"reno": Reno, "cubic": Cubic, "bbr": BBR}[args.algo]
    args.rounds = args.rounds or (240 if args.algo == "cubic" else 80)
    history, bdp = simulate([make() for _ in range(args.flows)], args.rate, args.rtt, args.buffer, args.rounds)
    print(f"{args.algo}: pipe holds {bdp:.0f} packets, router queue {args.buffer:.0f} more; "
          f"'|' marks the pipe, ':' pipe + queue\n")
    scale = 60 / (bdp + args.buffer) * 0.8
    step = max(1, args.rounds // 60)                      # long runs: show every few rounds, and every loss
    for r, cwnds, queue, rtt, lost, util in history:
        if r % step and not lost:
            continue
        line = [" "] * 62
        for i, c in enumerate(cwnds):
            for x in range(min(61, int(c * scale))):
                line[x] = "▒" if i else "█"
        line[min(61, int(bdp * scale))] = "|"
        line[min(61, int((bdp + args.buffer) * scale))] = ":"
        flows = " ".join(f"{c:5.0f}" for c in cwnds)
        print(f"{r:3d} {''.join(line)} {flows}  RTT {rtt:5.1f} ms" + ("  ✗ loss" if lost else ""))
    tail = history[len(history) // 2:]
    print(f"\nsecond half: link busy {100 * sum(h[5] for h in tail) / len(tail):.0f}% of the time, "
          f"average RTT {sum(h[3] for h in tail) / len(tail):.1f} ms (empty: {args.rtt:.0f} ms), "
          f"{sum(1 for h in tail if h[4])} rounds with losses")


if __name__ == "__main__":
    main()
