#!/usr/bin/env python3
"""Chapter 13 lab: reliable delivery over an unreliable network.

Alice sends her school report to Otto as UDP datagrams, through a "lossy link" that loses,
duplicates, delays and reorders them. All three run on your computer, with real UDP sockets.

    python3 reliable.py                          defaults: window of 8, go-back-N, 10% loss, 20 ms each way
    python3 reliable.py --window 1               stop-and-wait: one datagram at a time
    python3 reliable.py --window 16 --selective  a bigger window, resending only what's missing
    python3 reliable.py --loss 0.3 --dup 0.05    a truly awful network
    python3 reliable.py --file some.pdf          send a real file
    python3 reliable.py tcp                      the same report over real TCP, for comparison
"""
import argparse
import hashlib
import heapq
import random
import socket
import threading
import time

LINK, OTTO = ("127.0.0.1", 7130), ("127.0.0.1", 7132)
CHUNK = 1000                                  # bytes of data per datagram


def make_report():
    lines = [f"Page {p} of 50. The volcano report, by Alice. " + "Magma rises, cools, and becomes new rock. " * 20
             for p in range(1, 51)]
    return "\n".join(lines).encode()


# ------------------------------------------------------------------ the lossy link

def lossy_link(loss, dup, delay, reorder, stats, stop, seed):
    """Forwards datagrams between Alice and Otto, badly."""
    rng = random.Random(seed)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(LINK)
    sock.settimeout(0.002)
    queue, alice, n = [], None, 0
    while not stop.is_set():
        try:
            data, src = sock.recvfrom(65536)
            if src == OTTO:
                dest = alice
            else:
                alice, dest = src, OTTO
            if rng.random() < loss:
                stats["lost"] += 1
                continue
            copies = 2 if rng.random() < dup else 1
            stats["duplicated"] += copies - 1
            for _ in range(copies):
                late = 0.010 if rng.random() < reorder else 0         # hold a few back, so others overtake them
                due = time.monotonic() + delay + late
                heapq.heappush(queue, (due, n, data, dest))
                n += 1
        except socket.timeout:
            pass
        now = time.monotonic()
        while queue and queue[0][0] <= now:
            _, _, data, dest = heapq.heappop(queue)
            sock.sendto(data, dest)
    sock.close()


# ------------------------------------------------------------------ Otto's end

# --8<-- [start:receiver]
def receiver(selective, result, stop):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(OTTO)
    sock.settimeout(0.01)
    shelf, expected, total = {}, 0, None       # expected: the first piece Otto doesn't have yet
    while not stop.is_set():
        try:
            data, src = sock.recvfrom(65536)
        except socket.timeout:
            continue
        header, _, body = data.partition(b"\n")
        seq, total = map(int, header.split()[1:])
        if seq < expected or seq in shelf:
            result["duplicates"] += 1                    # seen it already: just acknowledge again
        elif seq > expected:
            result["early"] += 1                         # a gap: something before it is missing or late
            if selective:
                shelf[seq] = body                        # keep it for later
        else:
            shelf[seq] = body
        while expected in shelf:
            expected += 1
        extra = [s for s in shelf if s > expected] if selective else []
        ack = f"ACK {expected}" + (" " + ",".join(map(str, sorted(extra))) if extra else "")
        sock.sendto(ack.encode(), src)                   # "I have everything before <expected>"
        if expected == total and "data" not in result:
            result["data"] = b"".join(shelf[i] for i in range(total))
    sock.close()
# --8<-- [end:receiver]


# ------------------------------------------------------------------ Alice's end

class Timer:
    """Works out how long to wait for an acknowledgment, from round trips measured so far."""

    def __init__(self):
        self.average, self.wobble, self.patience = None, 0.0, 1

    # --8<-- [start:timer]
    def measured(self, rtt):
        if self.average is None:
            self.average, self.wobble = rtt, rtt / 2
        else:
            self.wobble = 0.75 * self.wobble + 0.25 * abs(rtt - self.average)
            self.average = 0.875 * self.average + 0.125 * rtt

    @property
    def timeout(self):
        if self.average is None:
            return 0.5                                   # no measurements yet: guess
        margin = max(4 * self.wobble, 0.020)            # a steady network still gets 20 ms to spare
        return min(2.0, (self.average + margin) * self.patience)
    # --8<-- [end:timer]

    def gave_up(self):
        self.patience = min(self.patience * 2, 32)      # something's wrong: be more patient next time

    def progress(self):
        self.patience = 1                                # things are moving again


# --8<-- [start:sender]
def sender(data, window, selective, stats):
    pieces = [data[i:i + CHUNK] for i in range(0, len(data), CHUNK)]
    total = len(pieces)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.002)
    base, next_seq = 0, 0                      # base: oldest unacknowledged piece
    sent_at, resent, acked_early = {}, set(), set()
    timer = Timer()

    def transmit(seq, again=False):
        sock.sendto(f"DATA {seq} {total}\n".encode() + pieces[seq], LINK)
        sent_at[seq] = time.monotonic()
        stats["sent"] += 1
        if again:
            stats["resent"] += 1
            resent.add(seq)

    while base < total:
        while next_seq < total and next_seq < base + window:      # 1. fill the window
            transmit(next_seq)
            next_seq += 1
        try:                                                       # 2. read acknowledgments
            parts = sock.recv(65536).decode().split()
            ack = int(parts[1])
            if len(parts) > 2:
                acked_early.update(int(s) for s in parts[2].split(","))
            if ack > base:
                if ack == base + 1 and base not in resent:         # time only a piece that was sent once,
                    timer.measured(time.monotonic() - sent_at[base])  # and acknowledged on its own
                timer.progress()
                base = ack                                         # the window slides forward
        except socket.timeout:
            pass
        now = time.monotonic()                                     # 3. waited too long?
        if base < next_seq and now - sent_at[base] > timer.timeout:
            stats["timeouts"] += 1
            if selective:                                          # resend only what's still missing
                late = [s for s in range(base, next_seq) if s not in acked_early and now - sent_at[s] > timer.timeout]
            else:                                                  # go back and resend everything unacknowledged
                late = range(base, next_seq)
            for seq in late:
                transmit(seq, again=True)
            timer.gave_up()
    stats["timeout"] = timer.timeout
    sock.close()
# --8<-- [end:sender]


# ------------------------------------------------------------------ run it all

def run(args):
    data = open(args.file, "rb").read() if args.file else make_report()
    stats = {"sent": 0, "resent": 0, "timeouts": 0, "lost": 0, "duplicated": 0}
    result = {"duplicates": 0, "early": 0}
    stop = threading.Event()
    threads = [threading.Thread(target=lossy_link, args=(args.loss, args.dup, args.delay / 1000, args.reorder,
                                                         stats, stop, args.seed)),
               threading.Thread(target=receiver, args=(args.selective, result, stop))]
    for t in threads:
        t.start()
    time.sleep(0.1)
    pieces = (len(data) + CHUNK - 1) // CHUNK
    mode = "stop-and-wait" if args.window == 1 else f"window of {args.window}" + (", selective" if args.selective else ", go-back-N")
    print(f"Alice sends {len(data):,} bytes as {pieces} datagrams ({mode}) through a link that takes {args.delay:g} ms each way,\n"
          f"loses {args.loss:.0%}, duplicates {args.dup:.0%} and delays {args.reorder:.0%} by an extra 10 ms.")
    start = time.monotonic()
    sender(data, args.window, args.selective, stats)
    took = time.monotonic() - start
    time.sleep(0.2)
    stop.set()
    for t in threads:
        t.join()
    print(f"\n  done in {took:.2f} s ({len(data) / took / 1000:,.0f} kB/s)")
    print(f"  Alice sent {stats['sent']} datagrams: {stats['resent']} of them were resends, after {stats['timeouts']} timeouts")
    print(f"  the link lost {stats['lost']} (data and acks) and duplicated {stats['duplicated']}")
    print(f"  Otto got {result['duplicates']} duplicates and {result['early']} that arrived ahead of a gap")
    print(f"  Alice's final timeout: {stats['timeout'] * 1000:.0f} ms")
    got = result.get("data")
    ok = got is not None and hashlib.sha256(got).digest() == hashlib.sha256(data).digest()
    print("  Otto's copy is " + ("identical to Alice's ✓" if ok else "WRONG ✗"))


# --8<-- [start:tcp]
def run_tcp():
    data = make_report()
    server = socket.create_server(("127.0.0.1", 7133))
    received = []

    def otto():
        conn, _ = server.accept()
        while chunk := conn.recv(65536):          # a stream: read until Alice hangs up
            received.append(chunk)
        conn.close()

    t = threading.Thread(target=otto)
    t.start()
    alice = socket.create_connection(("127.0.0.1", 7133))
    alice.sendall(data)                            # TCP does all of this chapter's work for us
    alice.close()
    t.join()
    server.close()
    got = b"".join(received)
    print(f"sent {len(data):,} bytes over TCP; Otto received {len(got):,} bytes in {len(received)} reads; "
          + ("identical ✓" if got == data else "different ✗"))
# --8<-- [end:tcp]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", nargs="?", default="udp", choices=["udp", "tcp"])
    p.add_argument("--window", type=int, default=8, help="how many unacknowledged datagrams may be in flight")
    p.add_argument("--selective", action="store_true", help="Otto keeps early arrivals; Alice resends only gaps")
    p.add_argument("--loss", type=float, default=0.1)
    p.add_argument("--dup", type=float, default=0.02)
    p.add_argument("--delay", type=float, default=20, help="milliseconds each way")
    p.add_argument("--reorder", type=float, default=0.03, help="chance of holding a datagram back 10 ms, so others overtake it")
    p.add_argument("--file")
    p.add_argument("--seed", type=int, default=3)
    args = p.parse_args()
    run_tcp() if args.mode == "tcp" else run(args)


if __name__ == "__main__":
    main()
