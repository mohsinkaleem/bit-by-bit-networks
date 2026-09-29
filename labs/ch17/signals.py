#!/usr/bin/env python3
"""Chapter 17 lab: more levels means more bits per symbol, and more mistakes. Then, your own Wi-Fi.

    python3 signals.py levels                  2, 4, 8 and 16 voltage levels through growing noise
    python3 signals.py qam --snr 25            which Wi-Fi constellations survive this much noise?
    python3 signals.py shannon 80 36           the most an 80 MHz channel can carry at 36 dB signal-to-noise
    python3 signals.py wifi                    your own Wi-Fi's signal, noise and speed (macOS or Linux)
"""
import argparse
import json
import math
import random
import re
import subprocess
import sys


# --8<-- [start:levels]
def pam_errors(levels, noise, symbols=20000, rng=random.Random(1)):
    """Send random symbols as one of `levels` evenly spaced voltages between -1 and +1, add random noise,
    and let the receiver pick the nearest level. Returns the fraction it gets wrong."""
    volts = [-1 + 2 * i / (levels - 1) for i in range(levels)]
    wrong = 0
    for _ in range(symbols):
        sent = rng.randrange(levels)
        heard = volts[sent] + rng.gauss(0, noise)
        guess = min(range(levels), key=lambda i: abs(volts[i] - heard))
        wrong += guess != sent
    return wrong / symbols
# --8<-- [end:levels]


# --8<-- [start:qam]
def qam_errors(points, snr_db, symbols=20000, rng=random.Random(2)):
    """Like pam_errors, in two dimensions: each symbol is one dot on a square grid (QAM).
    The grid is scaled so the average signal power is 1; noise power is 1 / SNR."""
    if points == 2:                                  # BPSK: just two dots, +1 and -1
        xs, ys, scale = [-1, 1], [0], 1.0
    else:                                            # a square grid, side × side, at odd numbers ±1, ±3, ±5…
        side = math.isqrt(points)
        xs = ys = [2 * i - (side - 1) for i in range(side)]
        scale = math.sqrt(2 * sum(v * v for v in xs) / side)
    sigma = math.sqrt(1 / (2 * 10 ** (snr_db / 10))) * scale
    wrong = 0
    for _ in range(symbols):
        x, y = rng.choice(xs), rng.choice(ys)
        hx, hy = x + rng.gauss(0, sigma), y + rng.gauss(0, sigma)
        nearest_x = min(xs, key=lambda v: abs(v - hx))      # the grid is square, so each
        nearest_y = min(ys, key=lambda v: abs(v - hy))      # direction can be decided on its own
        wrong += (nearest_x, nearest_y) != (x, y)
    return wrong / symbols
# --8<-- [end:qam]


def shannon_mbps(mhz, snr_db):
    return mhz * math.log2(1 + 10 ** (snr_db / 10))


def show_levels(noises):
    print("Fraction of symbols the receiver gets wrong:\n")
    print(f"{'levels':>8} {'bits each':>10}" + "".join(f"{'noise ' + str(n):>12}" for n in noises))
    for levels in (2, 4, 8, 16):
        row = "".join(f"{pam_errors(levels, n):>12.1%}" for n in noises)
        print(f"{levels:>8} {int(math.log2(levels)):>10}{row}")
    print("\nThe levels always span -1 to +1 volt, so more levels means they're closer together.")


def show_qam(snr_db):
    names = [(2, "BPSK"), (4, "QPSK"), (16, "16-QAM"), (64, "64-QAM"), (256, "256-QAM"), (1024, "1024-QAM"), (4096, "4096-QAM")]
    print(f"At a signal-to-noise ratio of {snr_db} dB:\n")
    print(f"{'name':>10} {'dots':>6} {'bits each':>10} {'wrong':>8}")
    best = None
    for points, name in names:
        err = qam_errors(points, snr_db, symbols=6000 if points > 256 else 20000)
        ok = err < 0.01
        if ok:
            best = name
        print(f"{name:>10} {points:>6} {int(math.log2(points)):>10} {err:>8.1%}" + ("   fine" if ok else ""))
    print(f"\nWith under 1% of symbols wrong, error-correcting codes can fix the rest, so Wi-Fi would pick {best or 'nothing'}.")
    print(f"Shannon's limit for a 20 MHz channel at this SNR: {shannon_mbps(20, snr_db):.0f} Mb/s.")


# --8<-- [start:wifi]
def read_wifi():
    """Returns a dict with whatever the operating system will tell us about the current Wi-Fi link."""
    if sys.platform == "darwin":
        out = subprocess.run(["system_profiler", "SPAirPortDataType", "-json"], capture_output=True, text=True).stdout
        for itf in json.loads(out)["SPAirPortDataType"][0].get("spairport_airport_interfaces", []):
            cur = itf.get("spairport_current_network_information")
            if cur and "spairport_signal_noise" in cur:
                signal, noise = map(int, re.findall(r"-\d+", cur["spairport_signal_noise"]))
                chan = cur.get("spairport_network_channel", "")
                width = re.search(r"(\d+)MHz", chan)
                return {"interface": itf["_name"], "signal": signal, "noise": noise, "channel": chan,
                        "width": int(width.group(1)) if width else 20, "rate": cur.get("spairport_network_rate"),
                        "standard": cur.get("spairport_network_phymode"), "mcs": cur.get("spairport_network_mcs")}
    else:
        for iface in ("wlan0", "wlp2s0", "wlp3s0", "wlo1"):
            link = subprocess.run(["iw", "dev", iface, "link"], capture_output=True, text=True).stdout
            if "signal" not in link:
                continue
            info = subprocess.run(["iw", "dev", iface, "info"], capture_output=True, text=True).stdout
            width = re.search(r"width: (\d+) MHz", info)
            chan = re.search(r"channel (\d+) \((\d+) MHz\)", info)
            return {"interface": iface, "signal": int(re.search(r"signal: (-\d+)", link).group(1)), "noise": None,
                    "channel": f"{chan.group(1)} ({chan.group(2)} MHz)" if chan else "?",
                    "width": int(width.group(1)) if width else 20,
                    "rate": float(re.search(r"tx bitrate: ([\d.]+)", link).group(1)), "standard": None, "mcs": None}
    return None
# --8<-- [end:wifi]


def show_wifi():
    try:
        w = read_wifi()
    except (OSError, ValueError, KeyError) as e:
        raise SystemExit(f"couldn't read the Wi-Fi details: {e}")
    if not w:
        raise SystemExit("No Wi-Fi connection found. (On Linux this needs the 'iw' command: sudo apt install iw)")
    guessed = w["noise"] is None
    noise = -95 if guessed else w["noise"]
    snr = w["signal"] - noise
    print(f"interface {w['interface']}, channel {w['channel']}" + (f", {w['standard']}" if w["standard"] else ""))
    print(f"  signal   {w['signal']} dBm   ({signal_words(w['signal'])})")
    print(f"  noise    {noise} dBm" + ("   (your system doesn't report noise; -95 is typical)" if guessed else ""))
    print(f"  SNR      {snr} dB: the signal is {10 ** (snr / 10):,.0f} times stronger than the noise")
    print(f"  Shannon's limit for {w['width']} MHz at {snr} dB: {shannon_mbps(w['width'], snr):,.0f} Mb/s per antenna pair")
    print(f"  link rate right now: {w['rate']} Mb/s" + (f" (MCS {w['mcs']})" if w["mcs"] is not None else ""))


def signal_words(dbm):
    for limit, words in ((-50, "excellent"), (-60, "very good"), (-67, "good enough for video calls"),
                         (-75, "patchy"), (-85, "barely usable")):
        if dbm >= limit:
            return words
    return "lost in the noise"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")
    lv = sub.add_parser("levels")
    lv.add_argument("--noise", type=float, nargs="*", default=[0.05, 0.1, 0.2, 0.3])
    q = sub.add_parser("qam")
    q.add_argument("--snr", type=float, default=25)
    sh = sub.add_parser("shannon")
    sh.add_argument("mhz", type=float)
    sh.add_argument("snr", type=float)
    sub.add_parser("wifi")
    args = p.parse_args()
    if args.cmd == "levels":
        show_levels(args.noise)
    elif args.cmd == "qam":
        show_qam(args.snr)
    elif args.cmd == "shannon":
        print(f"{args.mhz:g} MHz at {args.snr:g} dB SNR: at most {shannon_mbps(args.mhz, args.snr):,.0f} Mb/s")
    elif args.cmd == "wifi":
        show_wifi()
    else:
        p.print_help()


if __name__ == "__main__":
    main()
