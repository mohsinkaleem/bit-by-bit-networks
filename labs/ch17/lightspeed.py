#!/usr/bin/env python3
"""Chapter 17 lab: how fast can a packet possibly go? Distance, the speed of light, and real pings.

    python3 lightspeed.py                                   list the cities it knows
    python3 lightspeed.py London "New York"                 the fastest possible round trip between two places
    python3 lightspeed.py Mumbai Geneva --ping info.cern.ch ...and compare it with a real ping
    python3 lightspeed.py 51.5,-0.13 40.71,-74.0            use latitude,longitude instead of a name
    python3 lightspeed.py --wire                            how long it takes just to put a packet on the wire
"""
import argparse
import math
import re
import subprocess

C_VACUUM = 299_792.458          # km per second
C_FIBER = C_VACUUM / 1.47       # glass slows light down by its refractive index, about 1.47

CITIES = {                      # latitude, longitude
    "London": (51.51, -0.13), "New York": (40.71, -74.01), "San Francisco": (37.77, -122.42),
    "Geneva": (46.23, 6.05), "Frankfurt": (50.11, 8.68), "Stockholm": (59.33, 18.07),
    "Mumbai": (19.08, 72.88), "Delhi": (28.61, 77.21), "Bengaluru": (12.97, 77.59),
    "Chennai": (13.08, 80.27), "Hyderabad": (17.39, 78.49), "Kolkata": (22.57, 88.36),
    "Singapore": (1.35, 103.82), "Tokyo": (35.68, 139.69), "Sydney": (-33.87, 151.21),
    "Johannesburg": (-26.20, 28.05), "Sao Paulo": (-23.55, -46.63), "Dubai": (25.20, 55.27),
}


# --8<-- [start:distance]
def great_circle_km(a, b):
    """The shortest distance between two points on a sphere the size of the Earth (the haversine formula)."""
    (lat1, lon1), (lat2, lon2) = [(math.radians(lat), math.radians(lon)) for lat, lon in (a, b)]
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def best_round_trip_ms(km, speed=C_FIBER):
    return 2 * km / speed * 1000
# --8<-- [end:distance]


def place(text):
    if re.fullmatch(r"-?\d+(\.\d+)?,-?\d+(\.\d+)?", text):
        lat, lon = map(float, text.split(","))
        return text, (lat, lon)
    for name, where in CITIES.items():
        if name.lower() == text.lower():
            return name, where
    raise SystemExit(f"I don't know {text!r}. Use latitude,longitude, or one of: {', '.join(CITIES)}")


def ping_min_ms(host, count=5):
    try:
        out = subprocess.run(["ping", "-c", str(count), host], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"= ([\d.]+)/", out)          # "min/avg/max… = 150.6/163.4/…" on both macOS and Linux
    return float(m.group(1)) if m else None


def wire_table():
    speeds = [("10 Mb/s", 10e6), ("100 Mb/s", 100e6), ("1 Gb/s", 1e9), ("10 Gb/s", 10e9), ("400 Gb/s", 400e9)]
    print("Time just to put one packet onto the wire (serialization delay):\n")
    print(f"{'packet':>14}" + "".join(f"{name:>12}" for name, _ in speeds))
    for label, size in (("64 bytes", 64), ("1,500 bytes", 1500), ("9,000 bytes", 9000)):
        cells = []
        for _, bps in speeds:
            us = size * 8 / bps * 1e6
            if us >= 1000:
                cells.append(f"{us / 1000:.2f} ms")
            elif us >= 10:
                cells.append(f"{us:.0f} µs")
            else:
                cells.append(f"{us:.2f} µs" if us >= 1 else f"{us * 1000:.0f} ns")
        print(f"{label:>14}" + "".join(f"{c:>12}" for c in cells))
    km = 1000
    print(f"\nMeanwhile, light takes {km / C_FIBER * 1000:.1f} ms to travel {km:,} km of fiber, whatever the speed.")
    for name, bps in speeds[2:]:
        print(f"  at {name:>8}, {bps * km / C_FIBER / 8 / 1e6:,.1f} MB are inside those {km:,} km of glass at any moment")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("places", nargs="*", help="two city names, or latitude,longitude pairs")
    p.add_argument("--ping", metavar="HOST", help="also ping this host (near the second place) and compare")
    p.add_argument("--wire", action="store_true", help="show serialization delays")
    args = p.parse_args()
    if args.wire:
        return wire_table()
    if len(args.places) != 2:
        print("Cities I know:", ", ".join(sorted(CITIES)))
        print('Try: python3 lightspeed.py London "New York"')
        return
    (name1, a), (name2, b) = place(args.places[0]), place(args.places[1])
    km = great_circle_km(a, b)
    print(f"{name1} → {name2}: {km:,.0f} km as the crow flies")
    print(f"  light in a vacuum: {km / C_VACUUM * 1000:6.1f} ms one way, {best_round_trip_ms(km, C_VACUUM):6.1f} ms there and back")
    print(f"  light in fiber:    {km / C_FIBER * 1000:6.1f} ms one way, {best_round_trip_ms(km):6.1f} ms there and back"
          "   ← no network can beat this")
    if args.ping:
        best = ping_min_ms(args.ping)
        if best is None:
            print(f"  ping {args.ping}: no answer (some servers ignore pings)")
        else:
            ratio = best / best_round_trip_ms(km)
            print(f"  ping {args.ping}: fastest of 5 was {best:.1f} ms, {ratio:.1f}× the fiber limit.")
            print("  The rest is detours: cables don't follow great circles, and every router and queue adds a little.")


if __name__ == "__main__":
    main()
