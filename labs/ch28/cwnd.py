#!/usr/bin/env python3
"""Chapter 28 lab: watch TCP's congestion window from the inside, during a real upload.

    python3 cwnd.py                   upload to speed.cloudflare.com for 4 seconds, sampling every 10 ms
    python3 cwnd.py --seconds 8 --every 5

The kernel will tell a program about its own TCP connection: the congestion window, the
slow-start threshold, the round-trip time, how much has been resent. On macOS that's the
TCP_CONNECTION_INFO socket option; on Linux, TCP_INFO. We only upload, because the congestion
window that matters is the sender's.
"""
import argparse
import socket
import ssl
import struct
import sys
import threading
import time

HOST = "speed.cloudflare.com"


# --8<-- [start:info]
def tcp_info(sock):
    """{cwnd, ssthresh (bytes), srtt (ms), retrans (bytes)} for this socket, straight from the kernel."""
    if sys.platform == "darwin":
        raw = sock.getsockopt(socket.IPPROTO_TCP, 0x106, 112)          # TCP_CONNECTION_INFO
        (rto, mss, ssthresh, cwnd, sndwnd, inbuf, rcvwnd, rttcur, srtt) = struct.unpack_from("<9I", raw, 12)
        retrans = struct.unpack_from("<Q", raw, 72)[0]
        return dict(cwnd=cwnd, ssthresh=ssthresh, srtt=srtt, rtt=rttcur, retrans=retrans, mss=mss)
    raw = sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_INFO, 232)    # Linux's struct tcp_info
    mss = struct.unpack_from("<I", raw, 16)[0]
    rtt_us, _, ssthresh, cwnd = struct.unpack_from("<4I", raw, 68)
    total_retrans = struct.unpack_from("<I", raw, 100)[0]
    return dict(cwnd=cwnd * mss, ssthresh=min(ssthresh, 2 ** 31) * mss, srtt=rtt_us // 1000, rtt=rtt_us // 1000,
                retrans=total_retrans * mss, mss=mss)
# --8<-- [end:info]


def upload(seconds, every):
    ctx = ssl.create_default_context()
    s = ctx.wrap_socket(socket.create_connection((HOST, 443)), server_hostname=HOST)
    s.sendall(f"POST /__up HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: bitbybit\r\n"
              f"Content-Length: 1000000000\r\n\r\n".encode())
    samples, stop, t0 = [], [False], time.perf_counter()

    def sampler():
        while not stop[0]:
            samples.append((time.perf_counter() - t0, tcp_info(s)))
            time.sleep(every / 1000)
    threading.Thread(target=sampler, daemon=True).start()
    chunk, sent = bytes(65536), 0
    while time.perf_counter() - t0 < seconds:
        s.sendall(chunk)
        sent += len(chunk)
    stop[0] = True
    s.close()
    return samples, sent


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seconds", type=float, default=4)
    p.add_argument("--every", type=float, default=10, help="milliseconds between samples")
    p.add_argument("--save", help="also write the samples to this JSON file")
    args = p.parse_args()
    samples, sent = upload(args.seconds, args.every)
    if args.save:
        import json
        json.dump({"sent": sent, "seconds": args.seconds, "samples": [[round(t, 4), i] for t, i in samples]}, open(args.save, "w"))
    print(f"uploaded {sent / 1e6:.0f} MB in {args.seconds:g} s ({sent * 8 / args.seconds / 1e6:.0f} Mbit/s), "
          f"{len(samples)} samples. MSS {samples[0][1]['mss']} bytes.\n")
    top = max(i["cwnd"] for _, i in samples)
    print("   time    cwnd (KB)                                              ssthresh   RTT    resent")
    last_retx, shown = 0, 0
    for t, i in samples:
        if t < shown:
            continue
        shown = t + (0.02 if t < 0.3 else 0.1)                       # more detail at the start
        bar = "█" * max(1, round(50 * i["cwnd"] / top))
        ss = "   -   " if i["ssthresh"] > 1e9 else f"{i['ssthresh'] // 1024:>5} KB"
        new = i["retrans"] - last_retx
        last_retx = i["retrans"]
        print(f"{t:6.2f} s {i['cwnd'] // 1024:>6}  {bar:<50} {ss} {i['srtt']:>4} ms"
              + (f"  +{new // 1024} KB" if new > 0 else ""))
    bdp = max(i["cwnd"] for _, i in samples[-50:])
    print(f"\nThe window settled around {bdp // 1024} KB: that's how many bytes were in flight, unacknowledged, at once.")


if __name__ == "__main__":
    main()
