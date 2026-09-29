#!/usr/bin/env python3
"""Chapter 2 lab, part 2: a "live" wire with real clocks.

Alice and Bob are two threads. The wire is a shared variable holding a voltage.
Alice sets the voltage once per bit-time; Bob wakes up on his own schedule to read it.

    python3 live_wire.py "HI" --bit-time 0.2          slow enough to watch
    python3 live_wire.py "HI BOB" --bit-time 0.01     100 bits per second
    python3 live_wire.py "HI BOB" --bit-time 0.001    1000 bits per second: does it survive?
    python3 live_wire.py "HI BOB" --bit-time 0.05 --drift 5
"""
import argparse
import sys
import threading
import time

SYMBOLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ .,?!~"
HIGH, LOW, IDLE = 5.0, -5.0, 0.0

wire = {"volts": IDLE}          # the shared "wire"


def wait_until(deadline):
    """Sleep until time.perf_counter() reaches deadline (sleep most of the way, then spin)."""
    while True:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            return
        time.sleep(remaining / 2 if remaining > 0.002 else 0)


def alice(bits, bit_time, lateness, show):
    start = time.perf_counter() + 0.05
    for i, bit in enumerate(bits):
        planned = start + i * bit_time
        wait_until(planned)
        wire["volts"] = HIGH if bit == "1" else LOW
        lateness.append(time.perf_counter() - planned)
        if show:
            sys.stdout.write("\033[42m \033[0m" if bit == "1" else "\033[41m \033[0m")
            sys.stdout.flush()
    wait_until(start + len(bits) * bit_time)
    wire["volts"] = IDLE


def bob(bit_time, drift, received):
    while abs(wire["volts"]) < 2:              # wait for the line to wake up
        time.sleep(0)
    t0 = time.perf_counter()
    my_bit_time = bit_time * (1 + drift / 100)
    i = 0
    while True:
        wait_until(t0 + (i + 0.5) * my_bit_time)
        v = wire["volts"]
        if abs(v) < 2:                         # quiet line: message is over
            return
        received.append("1" if v > 0 else "0")
        i += 1


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("text", nargs="?", default="HI BOB")
    p.add_argument("--bit-time", type=float, default=0.1, help="seconds per bit")
    p.add_argument("--drift", type=float, default=0.0, help="Bob's clock error in percent")
    args = p.parse_args()

    bits = "".join(format(SYMBOLS.index(c), "05b") for c in args.text.upper())
    lateness, received = [], []
    show = args.bit_time >= 0.05
    b = threading.Thread(target=bob, args=(args.bit_time, args.drift, received))
    a = threading.Thread(target=alice, args=(bits, args.bit_time, lateness, show))
    b.start()
    a.start()
    a.join()
    b.join(timeout=5)
    if show:
        print()

    got = "".join(received)
    wrong = sum(1 for i, bit in enumerate(bits) if i >= len(got) or got[i] != bit)
    text = "".join(SYMBOLS[int(got[i:i + 5], 2)] for i in range(0, len(got) - len(got) % 5, 5))
    print(f"bit-time {args.bit_time * 1000:g} ms  ({1 / args.bit_time:,.0f} bits/second)")
    print(f"Alice was late by up to {max(lateness) * 1000:.3f} ms "
          f"({max(lateness) / args.bit_time:.0%} of a bit)")
    print("sent:", bits)
    print("got: ", got)
    print(f"Bob decodes {text!r} with {wrong} bad bits")


if __name__ == "__main__":
    main()
