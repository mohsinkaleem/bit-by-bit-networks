#!/usr/bin/env python3
"""Chapter 10 lab: send Bob's video over a noisy line, in one piece or in packets.

    python3 packets.py whole                  one giant message with one check; resend it until it arrives intact
    python3 packets.py packets                chop it into 1000-byte packets, each with its own check
    python3 packets.py packets --size 100     ...or any other packet size
    python3 packets.py sweep                  try lots of packet sizes and compare the cost

Options:
    --noise 1e-6     the chance that any one bit gets flipped (the "bit error rate")
    --file PATH      send a real file instead of the pretend video
"""
import argparse
import hashlib
import random
import struct
import zlib

VIDEO_SIZE = 2_000_000          # bytes. A real two-hour video would be a thousand times bigger.


class NoisyLine:
    """A wire that flips each bit with probability `noise`. Rather than rolling a die for
    every single bit (millions of them), it works out how many bits to wait until the next flip."""

    def __init__(self, noise, rng):
        self.noise, self.rng = noise, rng
        self.bits_carried = 0
        self.next_flip = self._gap()

    def _gap(self):
        return int(self.rng.expovariate(self.noise)) if self.noise > 0 else float("inf")

    def carry(self, data):
        n = len(data) * 8
        self.bits_carried += n
        if self.next_flip >= n:                     # the usual case: this message gets through untouched
            self.next_flip -= n
            return data
        data = bytearray(data)
        pos = self.next_flip
        while pos < n:
            data[pos // 8] ^= 0x80 >> (pos % 8)
            pos += 1 + self._gap()
        self.next_flip = pos - n
        return bytes(data)


def crc(data):
    return zlib.crc32(data).to_bytes(4, "big")      # the same CRC-32 we wrote in checks.py, but fast


# ------------------------------------------------------------------ plan A: one giant message

def send_whole(data, line, max_tries=40):
    message = data + crc(data)
    for attempt in range(1, max_tries + 1):
        arrived = line.carry(message)
        body, check = arrived[:-4], arrived[-4:]
        if crc(body) == check:
            print(f"  try {attempt}: the check matches. Carol has the video!")
            return body
        if attempt <= 3:
            print(f"  try {attempt}: {len(message) * 8:,} bits sent... the check doesn't match. Throw it all away, send it again.")
        else:
            print(f"  try {attempt}: ✗", end="\n" if (attempt - 3) % 8 == 0 else "   ", flush=True)
    print(f"\n  Bob gives up after {max_tries} tries. Carol still has nothing.")
    return None


# ------------------------------------------------------------------ plan B: packets

# --8<-- [start:packetize]
HEADER = struct.Struct("!III")        # three 4-byte numbers: piece number, total pieces, data length


def packetize(data, size):
    total = (len(data) + size - 1) // size
    packets = []
    for seq in range(total):
        chunk = data[seq * size:(seq + 1) * size]
        body = HEADER.pack(seq, total, len(chunk)) + chunk
        packets.append(body + crc(body))              # the check covers the header too
    return packets


def unpack(packet):
    body, check = packet[:-4], packet[-4:]
    if crc(body) != check:
        return None                                   # damaged somewhere: throw the whole packet away
    seq, total, length = HEADER.unpack(body[:HEADER.size])
    return seq, total, body[HEADER.size:HEADER.size + length]
# --8<-- [end:packetize]


# --8<-- [start:reassemble]
def send_packets(data, size, line, rng, quiet=False):
    packets = packetize(data, size)
    shelf = {}                                        # Carol files each good piece by its number
    to_send = list(range(len(packets)))
    rounds = 0
    while to_send:
        rounds += 1
        rng.shuffle(to_send)                          # arrival order doesn't matter, thanks to the numbers
        sent, damaged = len(to_send), 0
        for seq in to_send:
            got = unpack(line.carry(packets[seq]))
            if got is None:
                damaged += 1
            else:
                shelf[got[0]] = got[2]
        # Carol replies with the numbers of the pieces she's still missing
        to_send = [seq for seq in range(len(packets)) if seq not in shelf]
        if not quiet:
            print(f"  round {rounds}: sent {sent:,} packets, {damaged} damaged. Carol asks again for: "
                  f"{short_list(sorted(to_send)) if to_send else 'nothing, she has them all!'}")
    return b"".join(shelf[seq] for seq in range(len(packets))), rounds
# --8<-- [end:reassemble]


def short_list(nums, n=8):
    return ", ".join(map(str, nums[:n])) + (f" … ({len(nums)} in all)" if len(nums) > n else "")


def report(data, received, line):
    useful = len(data) * 8
    print(f"\n  bits on the wire: {line.bits_carried:,} for a {useful:,}-bit video "
          f"({line.bits_carried / useful:.2f}× the video's size)")
    if received is not None:
        same = hashlib.sha256(received).digest() == hashlib.sha256(data).digest()
        print("  Carol's copy is " + ("identical to Bob's ✓" if same else "DIFFERENT from Bob's ✗"))


def sweep(data, noise, seed):
    print(f"Sending a {len(data):,}-byte video over a line that flips 1 bit in {1 / noise:,.0f}.\n")
    print(f"{'packet size':>12} {'packets':>9} {'header cost':>12} {'resent':>8} {'rounds':>7} {'total sent':>11}")
    for size in (16, 64, 256, 1000, 4000, 16000, 64000, 256000):
        rng = random.Random(seed)
        line = NoisyLine(noise, rng)
        received, rounds = send_packets(data, size, line, rng, quiet=True)
        assert received == data
        n = (len(data) + size - 1) // size
        first_round = n * (HEADER.size + 4) * 8 + len(data) * 8
        cost = line.bits_carried / (len(data) * 8)
        bar = "█" * min(40, round((cost - 1) * 40))
        print(f"{size:>12,} {n:>9,} {100 * (first_round / (len(data) * 8) - 1):>11.1f}% "
              f"{100 * (line.bits_carried / first_round - 1):>7.1f}% {rounds:>7} {cost:>10.2f}×  {bar}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["whole", "packets", "sweep"])
    p.add_argument("--size", type=int, default=1000, help="bytes of video per packet")
    p.add_argument("--noise", type=float, default=1e-6, help="chance of any one bit being flipped")
    p.add_argument("--file", help="send this file instead of the pretend video")
    p.add_argument("--seed", type=int, default=10)
    args = p.parse_args()

    rng = random.Random(args.seed)
    if args.file:
        with open(args.file, "rb") as f:
            data = f.read()
    else:
        data = random.Random(0).randbytes(VIDEO_SIZE) if hasattr(random.Random, "randbytes") else \
            bytes(random.Random(0).getrandbits(8) for _ in range(VIDEO_SIZE))
    if args.mode == "sweep":
        sweep(data, args.noise, args.seed)
        return
    line = NoisyLine(args.noise, rng)
    print(f"Bob sends {len(data):,} bytes to Carol. The line flips about 1 bit in {1 / args.noise:,.0f}.\n")
    if args.mode == "whole":
        received = send_whole(data, line)
    else:
        received, _ = send_packets(data, args.size, line, rng)
    report(data, received, line)


if __name__ == "__main__":
    main()
