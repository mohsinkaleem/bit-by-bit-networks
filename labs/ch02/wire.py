#!/usr/bin/env python3
"""Chapter 2 lab: a simulated wire between Alice's and Bob's houses.

Alice turns bits into a voltage that changes over time. Bob measures the voltage
using HIS clock, which may not tick at exactly the same speed as hers.

    python3 wire.py "HI BOB"                               perfect clocks, no noise
    python3 wire.py "HI BOB" --drift 4                     Bob's clock runs 4% slow
    python3 wire.py "HI BOB" --drift 4 --scheme letters    resync at the start of every letter
    python3 wire.py "HI BOB" --drift 4 --scheme manchester a clock edge inside every bit
    python3 wire.py "HI BOB" --noise 2.5                   add electrical noise to the wire
"""
import argparse
import random

SYMBOLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ .,?!~"

HIGH, LOW, IDLE = +5.0, -5.0, 0.0
THRESHOLD = 2.0          # above +2 V reads as 1, below -2 V reads as 0
STEPS = 20               # simulation steps per bit (how finely we model time)


def text_to_bits(text):
    return "".join(format(SYMBOLS.index(ch), "05b") for ch in text.upper())


def bits_to_text(bits):
    out = ""
    for i in range(0, len(bits) - len(bits) % 5, 5):
        chunk = bits[i:i + 5]
        out += SYMBOLS[int(chunk, 2)] if set(chunk) <= {"0", "1"} else "�"
    return out


def level(bit):
    return HIGH if bit == "1" else LOW


# ------------------------------------------------------------------ Alice's side
# A signal is a list of voltages, one per simulation step.

# --8<-- [start:send]
def send_plain(bits):
    """Hold each bit's voltage for exactly one bit-time. Nothing in between."""
    signal = [IDLE] * STEPS                      # the line is quiet before we start
    for bit in bits:
        signal += [level(bit)] * STEPS
    return signal + [IDLE] * STEPS * 2           # and quiet again afterwards


def send_letters(bits):
    """Each 5-bit letter gets a start pulse in front and a rest after it."""
    signal = [IDLE] * STEPS
    for i in range(0, len(bits), 5):
        signal += [HIGH] * STEPS                 # start pulse: "a letter is coming!"
        for bit in bits[i:i + 5]:
            signal += [level(bit)] * STEPS
        signal += [IDLE] * STEPS                 # rest: back to 0 V
    return signal + [IDLE] * STEPS


def send_manchester(bits):
    """Every bit flips halfway through: 1 is low-then-high, 0 is high-then-low."""
    half = STEPS // 2
    signal = [IDLE] * STEPS
    for bit in bits:
        first, second = (LOW, HIGH) if bit == "1" else (HIGH, LOW)
        signal += [first] * half + [second] * half
    return signal + [IDLE] * STEPS * 2
# --8<-- [end:send]


def add_noise(signal, amount, seed=7):
    rng = random.Random(seed)
    return [v + rng.gauss(0, amount) for v in signal]


# ------------------------------------------------------------------ Bob's side

def read(v):
    if v > THRESHOLD:
        return "1"
    if v < -THRESHOLD:
        return "0"
    return "?"


def first_edge(signal, start=0, settle=STEPS // 4):
    """Index where the line leaves 0 V and STAYS away for a moment (at or after start).

    Requiring a few steps in a row stops a single spike of noise on the quiet
    line from looking like the start of a message.
    """
    run = 0
    for i in range(start, len(signal)):
        run = run + 1 if abs(signal[i]) > THRESHOLD else 0
        if run == settle:
            return i - settle + 1
    return None


# --8<-- [start:receive]
def receive_plain(signal, drift):
    """Start the clock on the first edge, then sample the middle of every bit-time."""
    bit_time = STEPS * (1 + drift / 100)          # how long Bob THINKS a bit lasts
    t = first_edge(signal) + bit_time / 2
    bits, samples = "", []
    while t < len(signal):
        samples.append(int(t))
        bits += read(signal[int(t)])
        t += bit_time
    return bits.rstrip("?"), samples              # trailing ?s are just the quiet line


def receive_letters(signal, drift):
    """Restart the clock on every start pulse, so drift only builds up over 6 bits."""
    bit_time = STEPS * (1 + drift / 100)
    bits, samples, pos = "", [], 0
    while True:
        edge = first_edge(signal, pos)
        if edge is None:
            break
        for k in range(1, 6):                     # skip the start pulse, read 5 bits
            t = int(edge + (k + 0.5) * bit_time)
            if t >= len(signal):
                break
            samples.append(t)
            bits += read(signal[t])
        pos = int(edge + 6 * bit_time)            # wait for the rest period...
        while pos < len(signal) and abs(signal[pos]) > THRESHOLD:
            pos += 1                              # ...i.e. the line going back to 0 V
    return bits, samples


def receive_manchester(signal, drift):
    """Every bit has a flip in the middle; Bob re-aligns his clock on each flip."""
    bit_time = STEPS * (1 + drift / 100)
    mid = first_edge(signal) + bit_time / 2       # where Bob expects the first flip
    bits, samples = "", []
    while mid + bit_time / 4 < len(signal):
        a, b = int(mid - bit_time / 4), int(mid + bit_time / 4)
        before, after = read(signal[a]), read(signal[b])
        if before == after == "?":
            break                                 # line has gone quiet: message over
        samples += [a, b]
        bits += {("0", "1"): "1", ("1", "0"): "0"}.get((before, after), "?")
        for i in range(a, b):                     # find the real flip and snap to it
            if (signal[i] > 0) != (signal[i + 1] > 0):
                mid = i + 0.5
                break
        mid += bit_time
    return bits, samples
# --8<-- [end:receive]


# ------------------------------------------------------------------ drawing

def scope(signal, samples, cols_per_bit=4, max_bits=40):
    """Draw the signal like an oscilloscope screen, with Bob's samples marked ▲."""
    step = STEPS // cols_per_bit
    width = min(len(signal) // step, max_bits * cols_per_bit)
    rows = {"+5V ": "", "  0 ": "", "-5V ": ""}
    marks = ""
    sample_cols = {s // step for s in samples}
    for c in range(width):
        v = sum(signal[c * step:(c + 1) * step]) / step
        rows["+5V "] += "█" if v > THRESHOLD else " "
        rows["-5V "] += "█" if v < -THRESHOLD else " "
        rows["  0 "] += "─" if abs(v) <= THRESHOLD else " "
        marks += "▲" if c in sample_cols else " "
    lines = [label + "│" + row for label, row in rows.items()]
    lines.append("Bob │" + marks)
    return "\n".join(lines)


def compare(sent, got):
    marks = ""
    for i, bit in enumerate(sent):
        marks += " " if i < len(got) and got[i] == bit else "^"
    return marks


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("text", nargs="?", default="HI BOB")
    p.add_argument("--scheme", choices=["plain", "letters", "manchester"], default="plain")
    p.add_argument("--drift", type=float, default=0.0, help="Bob's clock error in percent (positive = slow)")
    p.add_argument("--noise", type=float, default=0.0, help="noise level in volts (try 1 to 3)")
    args = p.parse_args()

    bits = text_to_bits(args.text)
    sender = {"plain": send_plain, "letters": send_letters, "manchester": send_manchester}[args.scheme]
    receiver = {"plain": receive_plain, "letters": receive_letters, "manchester": receive_manchester}[args.scheme]

    signal = sender(bits)
    if args.noise:
        signal = add_noise(signal, args.noise)
    got, samples = receiver(signal, args.drift)

    print(f"scheme: {args.scheme}   Bob's clock: {args.drift:+.1f}%   noise: {args.noise} V\n")
    print(scope(signal, samples))
    print()
    print("Alice sent:", bits)
    print("Bob read:  ", got)
    print("errors:    ", compare(bits, got))
    wrong = compare(bits, got).count("^")
    print(f"\nBob decodes: {bits_to_text(got)!r}   ({wrong} of {len(bits)} bits wrong)")


if __name__ == "__main__":
    main()
