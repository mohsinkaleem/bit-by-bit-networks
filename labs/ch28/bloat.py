#!/usr/bin/env python3
"""Chapter 28 lab: does your internet connection get laggy when it's busy? (No sudo needed.)

    python3 bloat.py                    ping 1.1.1.1 while idle, while downloading, and while uploading
    python3 bloat.py --target 8.8.8.8 --seconds 8

It downloads and uploads as fast as it can for a few seconds each, to and from speed.cloudflare.com
(that can be hundreds of megabytes), so don't run it on a metered connection. The pings use an unprivileged ICMP socket, like Chapter 21's pyping.
"""
import argparse
import socket
import ssl
import statistics
import struct
import threading
import time

HOST = "speed.cloudflare.com"


# --8<-- [start:ping]
class Pinger(threading.Thread):
    """Send a ping every 100 ms and remember each round trip, or None for a lost one."""

    def __init__(self, target):
        super().__init__(daemon=True)
        self.target, self.results, self.stop = target, [], False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_ICMP)
        self.sock.settimeout(1.0)

    def run(self):
        seq = 0
        while not self.stop:
            seq += 1
            t = time.perf_counter()
            self.sock.sendto(struct.pack("!BBHHH", 8, 0, 0, 0, seq) + b"bloat?", (self.target, 0))
            try:
                while True:
                    data, _ = self.sock.recvfrom(1500)
                    icmp = data[20:] if data[0] >> 4 == 4 else data   # macOS includes the IP header
                    if icmp[0] == 0 and struct.unpack("!H", icmp[6:8])[0] == seq:
                        self.results.append((time.perf_counter(), (time.perf_counter() - t) * 1000))
                        break
            except socket.timeout:
                self.results.append((time.perf_counter(), None))
            time.sleep(max(0, 0.1 - (time.perf_counter() - t)))
# --8<-- [end:ping]


def https(request, upload=False, seconds=8):
    """Keep an HTTPS connection to the speed test server busy for a few seconds. Returns bytes moved."""
    ctx = ssl.create_default_context()
    end, moved = time.time() + seconds, 0
    while time.time() < end:                      # the server sends at most ~99 MB per request: ask again
        with ctx.wrap_socket(socket.create_connection((HOST, 443)), server_hostname=HOST) as s:
            s.sendall(request.encode())
            chunk = bytes(65536)
            while time.time() < end:
                if upload:
                    s.sendall(chunk)              # as fast as TCP will let us
                    n = len(chunk)
                else:
                    n = len(s.recv(262144))
                    if not n:
                        break
                moved += n
    return moved


def phase(pinger, name, work, seconds):
    start = time.perf_counter()
    t0 = time.time()
    moved = work() if work else (time.sleep(seconds) or 0)
    elapsed = time.time() - t0
    rtts = [r for t, r in pinger.results if t >= start and r is not None]
    lost = sum(1 for t, r in pinger.results if t >= start and r is None)
    speed = f"{moved * 8 / elapsed / 1e6:6.1f} Mbit/s" if moved else "            "
    if rtts:
        print(f"{name:<12} {speed}   ping median {statistics.median(rtts):6.1f} ms, "
              f"worst {max(rtts):6.1f} ms, {lost} lost of {len(rtts) + lost}")
    return statistics.median(rtts) if rtts else None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target", default="1.1.1.1")
    p.add_argument("--seconds", type=float, default=8)
    args = p.parse_args()
    pinger = Pinger(args.target)
    pinger.start()
    secs = args.seconds
    idle = phase(pinger, "idle", None, secs / 2)
    down = phase(pinger, "downloading", lambda: https(
        f"GET /__down?bytes=99000000 HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: bitbybit\r\nConnection: close\r\n\r\n",
        seconds=secs), secs)
    up = phase(pinger, "uploading", lambda: https(
        f"POST /__up HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: bitbybit\r\nContent-Length: 1000000000\r\n\r\n",
        upload=True, seconds=secs), secs)
    pinger.stop = True
    if idle and down and up:
        print(f"\nBusy, your pings took {down - idle:+.0f} ms longer downloading and {up - idle:+.0f} ms longer uploading.")
        print("That extra time is packets waiting in a queue somewhere: bufferbloat. For a game, anything over")
        print("about 30 ms is noticeable, and over 100 ms is painful.")


if __name__ == "__main__":
    main()
