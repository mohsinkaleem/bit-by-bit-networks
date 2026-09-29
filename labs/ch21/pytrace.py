#!/usr/bin/env python3
"""Chapter 21 lab: traceroute, written from scratch on top of pyping.py. No sudo needed.

    python3 pytrace.py 1.1.1.1                   every router on the way, three tries each
    python3 pytrace.py info.cern.ch --max 25     further away: can you spot the ocean?

Like "traceroute -I", it sends pings with a hop limit of 1, then 2, then 3… Each router that
throws one away says so, and that tells us who it is.
"""
import argparse
import socket
import time

from pyping import Pinger


# --8<-- [start:trace]
def trace(host, max_hops=30, tries=3, timeout=2.0):
    address = socket.gethostbyname(host)
    pinger = Pinger()
    print(f"route to {host} ({address}), at most {max_hops} hops")
    seq = 0
    for ttl in range(1, max_hops + 1):
        pinger.set_ttl(ttl)                             # the only thing that changes from one line to the next
        results, reached = [], False
        for _ in range(tries):
            seq += 1
            sent_at = time.time()
            pinger.send(address, seq)
            while True:
                got = pinger.receive(max(0, sent_at + timeout - time.time()))
                if got is None:
                    results.append(None)                # no answer: this router keeps quiet
                    break
                kind, sender, _, _, qseq = got
                if qseq != seq:
                    continue                            # an answer to an earlier probe, arriving late
                results.append((sender, (time.time() - sent_at) * 1000))
                reached = reached or kind == "echo reply"
                break
        print(f"{ttl:>2}  " + line(results))
        if reached:
            return
# --8<-- [end:trace]


def line(results):
    out, last = [], None
    for r in results:
        if r is None:
            out.append("*")
            continue
        sender, ms = r
        if sender != last:
            out.append(sender)                          # different routers can answer different tries
            last = sender
        out.append(f"{ms:.1f} ms")
    return "  ".join(out)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("host")
    p.add_argument("--max", type=int, default=30)
    p.add_argument("--tries", type=int, default=3)
    args = p.parse_args()
    try:
        trace(args.host, args.max, args.tries)
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
