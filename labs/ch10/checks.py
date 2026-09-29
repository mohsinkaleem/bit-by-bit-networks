#!/usr/bin/env python3
"""Chapter 10 lab: four ways to notice damaged data, and a contest between them.

    python3 checks.py demo "HI BOB"      compute every check for a message
    python3 checks.py contest            damage thousands of messages in different ways;
                                         see how often each check notices
    python3 checks.py hamming 1011       protect 4 bits so that any single flip can be FIXED
"""
import random
import sys
import zlib


# --8<-- [start:parity]
def parity(data):
    """1 extra bit: makes the total number of 1 bits even."""
    ones = sum(bin(byte).count("1") for byte in data)
    return ones % 2
# --8<-- [end:parity]


# --8<-- [start:sums]
def sum8(data):
    """Add up every byte, keep only the last 8 bits (the remainder after dividing by 256)."""
    return sum(data) % 256


def internet_checksum(data):
    """The 16-bit checksum used by IP, UDP and TCP (RFC 1071): add 16-bit words
    with end-around carry, then flip all the bits."""
    if len(data) % 2:
        data += b"\x00"
    total = 0
    for i in range(0, len(data), 2):
        total += (data[i] << 8) | data[i + 1]
        total = (total & 0xFFFF) + (total >> 16)      # wrap any carry back into the bottom
    return ~total & 0xFFFF
# --8<-- [end:sums]


# --8<-- [start:crc]
def crc32(data):
    """CRC-32, the check at the end of every Ethernet frame (and every PNG chunk, and every
    ZIP file). It's long division by a fixed 33-bit number, where subtraction is XOR.
    This is the classic bit-by-bit version; real hardware does the same thing in a circuit."""
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320      # the divisor, bits written in reverse order
            else:
                crc >>= 1
    return crc ^ 0xFFFFFFFF
# --8<-- [end:crc]


# zlib.crc32 gives exactly the same answers as our crc32() (the demo checks this), but it's
# written in C and about 100 times faster, which matters when we run it 300,000 times.
# --8<-- [start:hamming]
# Hamming(7,4): 4 data bits plus 3 parity bits. Each parity bit covers its own circle of the
# diagram, and every data bit sits in a different combination of circles.
CIRCLES = {"p1": ("d1", "d2", "d4"), "p2": ("d1", "d3", "d4"), "p3": ("d2", "d3", "d4")}


def hamming_encode(data_bits):
    bits = dict(zip(("d1", "d2", "d3", "d4"), data_bits))
    for p, members in CIRCLES.items():
        bits[p] = sum(bits[d] for d in members) % 2        # make each circle hold an even number of 1s
    return bits


def hamming_fix(bits):
    odd = {p for p, members in CIRCLES.items() if (bits[p] + sum(bits[d] for d in members)) % 2}
    if not odd:
        return bits, None
    for name in bits:                                       # find the one bit that's in exactly those circles
        if {p for p, members in CIRCLES.items() if name == p or name in members} == odd:
            fixed = dict(bits)
            fixed[name] ^= 1
            return fixed, name
# --8<-- [end:hamming]


CHECKS = {"parity": parity, "sum8": sum8, "internet": internet_checksum, "crc32": zlib.crc32}


# ------------------------------------------------------------------ ways to damage a message

def flip_bits(data, n, rng):
    data = bytearray(data)
    for pos in rng.sample(range(len(data) * 8), n):
        data[pos // 8] ^= 1 << (pos % 8)
    return bytes(data)


def burst(data, length, rng):
    """Garble `length` bits in a row (the first and last are always flipped)."""
    data = bytearray(data)
    start = rng.randrange(len(data) * 8 - length)
    for i in range(length):
        if i in (0, length - 1) or rng.random() < 0.5:
            pos = start + i
            data[pos // 8] ^= 1 << (pos % 8)
    return bytes(data)


def swap_bytes(data, rng):
    data = bytearray(data)
    while True:
        i, j = rng.sample(range(len(data)), 2)
        if data[i] != data[j]:
            data[i], data[j] = data[j], data[i]
            return bytes(data)


DAMAGE = {
    "1 flipped bit": lambda d, r: flip_bits(d, 1, r),
    "2 flipped bits": lambda d, r: flip_bits(d, 2, r),
    "3 flipped bits": lambda d, r: flip_bits(d, 3, r),
    "burst of 8 bits": lambda d, r: burst(d, 8, r),
    "burst of 32 bits": lambda d, r: burst(d, 32, r),
    "burst of 100 bits": lambda d, r: burst(d, 100, r),
    "two bytes swapped": swap_bytes,
    "random garbage": lambda d, r: bytes(r.randrange(256) for _ in d),
}


def contest(trials=10000, size=64, seed=1):
    rng = random.Random(seed)
    print(f"{trials} random {size}-byte messages per row. How often does each check notice the damage?\n")
    print(f"{'damage':<20}" + "".join(f"{name:>11}" for name in CHECKS))
    for label, damage in DAMAGE.items():
        caught = dict.fromkeys(CHECKS, 0)
        for _ in range(trials):
            msg = bytes(rng.randrange(256) for _ in range(size))
            bad = damage(msg, rng)
            for name, check in CHECKS.items():
                if check(msg) != check(bad):
                    caught[name] += 1
        print(f"{label:<20}" + "".join(f"{100 * caught[n] / trials:>10.2f}%" for n in CHECKS))


def demo(text):
    data = text.encode()
    assert crc32(data) == zlib.crc32(data), "our CRC-32 should match Python's built-in one"
    print(f"message: {text!r}  bytes: {data.hex(' ')}")
    print(f"  parity bit:        {parity(data)}")
    print(f"  8-bit sum:         {sum8(data)} (0x{sum8(data):02x})")
    print(f"  internet checksum: 0x{internet_checksum(data):04x}")
    print(f"  CRC-32:            0x{crc32(data):08x}   (zlib agrees: 0x{zlib.crc32(data):08x})")


def hamming_demo(word):
    data = [int(c) for c in word]
    assert len(data) == 4 and set(data) <= {0, 1}, "give me exactly 4 bits, like 1011"
    sent = hamming_encode(data)
    order = ["d1", "d2", "d3", "d4", "p1", "p2", "p3"]
    show = lambda bits: " ".join(f"{n}={bits[n]}" for n in order)
    print(f"data {word} is sent as 7 bits: {show(sent)}\n")
    for victim in order:
        damaged = dict(sent)
        damaged[victim] ^= 1
        fixed, culprit = hamming_fix(damaged)
        print(f"  noise flips {victim}: the receiver blames {culprit}, flips it back → "
              f"{'✓ fixed' if fixed == sent else '✗ still wrong'}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["demo"]:
        demo(" ".join(sys.argv[2:]) or "HI BOB")
    elif sys.argv[1:2] == ["contest"]:
        contest()
    elif sys.argv[1:2] == ["hamming"]:
        hamming_demo(sys.argv[2] if len(sys.argv) > 2 else "1011")
    else:
        print(__doc__)
