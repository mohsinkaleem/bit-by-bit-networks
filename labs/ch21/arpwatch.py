#!/usr/bin/env python3
"""Chapter 21 lab: read your computer's "who has?" memory (the ARP cache), and watch it for lies.

    python3 arpwatch.py              what your computer remembers right now
    python3 arpwatch.py --watch      keep checking every 2 seconds, and warn about anything suspicious
    python3 arpwatch.py --demo       feed it a made-up attack, to see what the warnings look like
"""
import argparse
import re
import subprocess
import sys
import time

VENDORS = {"2c:cf:67": "Raspberry Pi", "d8:3a:dd": "Raspberry Pi", "b8:27:eb": "Raspberry Pi",
           "84:2f:57": "Apple", "3c:22:fb": "Apple", "a4:83:e7": "Apple", "f0:18:98": "Apple",
           "00:1b:21": "Intel", "3c:7c:3f": "ASUS", "00:50:56": "VMware"}


def normalise(mac):
    return ":".join(part.zfill(2) for part in mac.lower().split(":"))


# --8<-- [start:read]
def read_cache():
    """{IP address: card address}, from `arp -an` on macOS or `ip neigh` on Linux."""
    if sys.platform == "darwin":
        out = subprocess.run(["arp", "-an"], capture_output=True, text=True).stdout
        pairs = re.findall(r"\((\d+\.\d+\.\d+\.\d+)\) at ([0-9a-f:]+) on", out)
    else:
        out = subprocess.run(["ip", "-4", "neigh"], capture_output=True, text=True).stdout
        pairs = re.findall(r"^(\d+\.\d+\.\d+\.\d+) .*lladdr ([0-9a-f:]+)", out, re.M)
    return {ip: normalise(mac) for ip, mac in pairs if not ip.startswith(("224.", "239.", "255."))}
# --8<-- [end:read]


def who(mac):
    if int(mac[:2], 16) & 2:
        return "a made-up (private) address"
    return VENDORS.get(mac[:8], "maker not in this lab's list")


# --8<-- [start:check]
def suspicious(old, new):
    """Compare two readings of the cache, and say what looks wrong."""
    warnings = []
    for ip, mac in new.items():
        if ip in old and old[ip] != mac:
            warnings.append(f"{ip} moved from {old[ip]} to {mac}. A new device, or someone lying?")
    owners = {}
    for ip, mac in new.items():
        owners.setdefault(mac, []).append(ip)
    for mac, ips in owners.items():
        if len(ips) > 1:
            warnings.append(f"{mac} claims {len(ips)} addresses: {', '.join(sorted(ips))}. "
                            "If one of them is your router, someone may be in the middle.")
    return warnings
# --8<-- [end:check]


def show(cache):
    for ip, mac in sorted(cache.items(), key=lambda kv: tuple(map(int, kv[0].split(".")))):
        print(f"  {ip:<16} is at {mac}   ({who(mac)})")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--watch", action="store_true")
    p.add_argument("--demo", action="store_true")
    args = p.parse_args()
    if args.demo:
        before = {"192.168.1.1": "14:c3:5e:40:0b:32", "192.168.1.4": "2c:cf:67:5e:10:c2", "192.168.1.9": "3c:7c:3f:44:55:66"}
        after = dict(before, **{"192.168.1.1": "3c:7c:3f:44:55:66"})
        print("Before:")
        show(before)
        print("After Eve's lies:")
        show(after)
        for w in suspicious(before, after):
            print("  ! " + w)
        return
    cache = read_cache()
    print("Your computer remembers:")
    show(cache)
    for w in suspicious({}, cache):
        print("  ! " + w)
    if not args.watch:
        return
    print("\nWatching (Ctrl-C to stop)…")
    try:
        while True:
            time.sleep(2)
            new = read_cache()
            for w in suspicious(cache, new):
                print(time.strftime("%H:%M:%S") + "  ! " + w)
            for ip in new.keys() - cache.keys():
                print(time.strftime("%H:%M:%S") + f"  new: {ip} is at {new[ip]} ({who(new[ip])})")
            cache = {**cache, **new}
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
