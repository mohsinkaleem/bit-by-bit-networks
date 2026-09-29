#!/usr/bin/env python3
"""Chapter 40 lab: where are the internet's satellites, right now?

    python3 sky.py                       Starlink, seen from Greenwich, in London
    python3 sky.py --at 40.71,-74.01     …seen from somewhere else (latitude,longitude)
    python3 sky.py --group geo           another group: oneweb, kuiper, geo (geostationary), gps-ops
    python3 sky.py --watch 120           follow the highest satellite for two minutes, and count the changes

It downloads every satellite's orbit from CelesTrak (at most once every two hours, to be polite)
and works out where each one is: Kepler's laws, plus the biggest correction, for the Earth's bulge.
Professional tracking software (SGP4) also models the air's drag and more; for orbits a day or two
old, this lab’s positions agree with it to within about 20 km. Python 3.9+, no packages.
"""
import argparse
import math
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone

MU = 398600.4418               # the Earth's gravity: km³/s²
RE = 6378.137                  # the Earth's radius at the equator, km
J2 = 1.08262668e-3             # how much the Earth bulges at the equator
C = 299792.458                 # the speed of light, km/s
HOME = (51.4779, -0.0015)      # the Royal Observatory, Greenwich
HERE = os.path.dirname(os.path.abspath(__file__))


def download(group):
    path = os.path.join(HERE, f"{group}.tle")
    if not os.path.exists(path) or time.time() - os.path.getmtime(path) > 7200:
        url = f"https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"
        with urllib.request.urlopen(url, timeout=60) as r, open(path, "wb") as f:
            f.write(r.read())
    lines = [l.rstrip() for l in open(path) if l.strip()]
    return [Satellite(*lines[i:i + 3]) for i in range(0, len(lines) - 2, 3)]


# --8<-- [start:orbit]
class Satellite:
    """One satellite's orbit, from a two-line element set (TLE): six numbers, and when they were true."""

    def __init__(self, name, line1, line2):
        self.name = name.strip()
        yy, day = int(line1[18:20]), float(line1[20:32])
        self.epoch = datetime(2000 + yy if yy < 57 else 1900 + yy, 1, 1, tzinfo=timezone.utc) + timedelta(days=day - 1)
        self.ndot = float(line1[33:43])                      # how fast the orbit is speeding up (air drag)
        self.i = math.radians(float(line2[8:16]))            # inclination: the tilt against the equator
        self.raan = math.radians(float(line2[17:25]))        # where it crosses the equator, going north
        self.e = float("0." + line2[26:33])                  # eccentricity: 0 is a perfect circle
        self.argp = math.radians(float(line2[34:42]))        # where in the orbit it comes closest
        self.m = math.radians(float(line2[43:51]))           # where it was, at the epoch
        n = float(line2[52:63]) * 2 * math.pi / 86400        # revolutions per day → radians per second
        cos_i = math.cos(self.i)
        # TLEs store a mean motion with part of the bulge's effect folded in; take it out again, as SGP4 does
        bulge = 0.75 * J2 * (3 * cos_i ** 2 - 1) / (1 - self.e ** 2) ** 1.5
        a1 = (MU / n ** 2) ** (1 / 3) / RE
        d1 = bulge / a1 ** 2
        a0 = a1 * (1 - d1 / 3 - d1 ** 2 - 134 / 81 * d1 ** 3)
        self.n = n / (1 + bulge / a0 ** 2)
        self.a = (MU / self.n ** 2) ** (1 / 3)               # Kepler's third law: the orbit's size
        k = 1.5 * J2 * (RE / (self.a * (1 - self.e ** 2))) ** 2
        # The bulge slowly turns the orbit around the Earth's axis, and turns it within its own plane
        self.raan_rate = -k * self.n * cos_i
        self.argp_rate = 0.5 * k * self.n * (5 * cos_i ** 2 - 1)
        self.m_rate = self.n * (1 + 0.5 * k * math.sqrt(1 - self.e ** 2) * (3 * cos_i ** 2 - 1))

    def position(self, when):
        """Where it is at `when`: x, y, z in km, from the Earth's centre, not turning with the Earth."""
        t = (when - self.epoch).total_seconds()
        m = self.m + self.m_rate * t + 2 * math.pi * self.ndot * (t / 86400) ** 2
        raan, argp = self.raan + self.raan_rate * t, self.argp + self.argp_rate * t
        ecc = m
        for _ in range(8):                                   # Kepler's equation: E − e·sin E = M
            ecc -= (ecc - self.e * math.sin(ecc) - m) / (1 - self.e * math.cos(ecc))
        xp, yp = self.a * (math.cos(ecc) - self.e), self.a * math.sqrt(1 - self.e ** 2) * math.sin(ecc)
        co, so, cw, sw, ci, si = (math.cos(raan), math.sin(raan), math.cos(argp), math.sin(argp),
                                  math.cos(self.i), math.sin(self.i))
        return ((co * cw - so * sw * ci) * xp - (co * sw + so * cw * ci) * yp,
                (so * cw + co * sw * ci) * xp + (co * cw * ci - so * sw) * yp,
                sw * si * xp + cw * si * yp)
# --8<-- [end:orbit]


# --8<-- [start:look]
def sidereal(when):
    """How far the Earth has turned (radians), measured against the stars."""
    t = ((when - datetime(2000, 1, 1, 12, tzinfo=timezone.utc)).total_seconds() / 86400) / 36525
    seconds = 67310.54841 + (876600 * 3600 + 8640184.812866) * t + 0.093104 * t * t
    return math.radians((seconds % 86400) / 240)


def look(sat, place, when):
    """From `place` (latitude, longitude), where is `sat` in the sky? (elevation°, azimuth°, distance km)"""
    x, y, z = sat.position(when)
    g = sidereal(when)
    x, y = math.cos(g) * x + math.sin(g) * y, -math.sin(g) * x + math.cos(g) * y     # turn with the Earth
    lat, lon = math.radians(place[0]), math.radians(place[1])
    f = 1 / 298.257223563                                    # the Earth is slightly squashed
    n = RE / math.sqrt(1 - f * (2 - f) * math.sin(lat) ** 2)
    ox, oy, oz = n * math.cos(lat) * math.cos(lon), n * math.cos(lat) * math.sin(lon), n * (1 - f) ** 2 * math.sin(lat)
    dx, dy, dz = x - ox, y - oy, z - oz
    east = -math.sin(lon) * dx + math.cos(lon) * dy
    north = -math.sin(lat) * math.cos(lon) * dx - math.sin(lat) * math.sin(lon) * dy + math.cos(lat) * dz
    up = math.cos(lat) * math.cos(lon) * dx + math.cos(lat) * math.sin(lon) * dy + math.sin(lat) * dz
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    return math.degrees(math.asin(up / dist)), math.degrees(math.atan2(east, north)) % 360, dist
# --8<-- [end:look]


def compass(az):
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int((az + 22.5) // 45) % 8]


def snapshot(sats, place, group):
    now = datetime.now(timezone.utc)
    seen = sorted(((look(s, place, now), s) for s in sats), key=lambda v: -v[0][0])
    up = [v for v in seen if v[0][0] > 0]
    usable = [v for v in seen if v[0][0] > 25]
    heights = sorted(s.a - RE for s in sats)
    print(f"{len(sats)} {group} satellites, most of them {heights[len(heights) // 2]:.0f} km up "
          f"(orbits downloaded from CelesTrak, the newest from {max(s.epoch for s in sats):%d %b %H:%M} UTC)")
    print(f"seen from {place[0]:.2f}°, {place[1]:.2f}° at {now:%H:%M:%S} UTC:")
    print(f"  above the horizon:        {len(up)}")
    print(f"  higher than 25° (usable): {len(usable)}")
    print("  the highest:")
    for (el, az, dist), s in seen[:5]:
        print(f"    {s.name:<22} {el:4.0f}° up, towards the {compass(az):<2}  {dist:7,.0f} km away: "
              f"light takes {dist / C * 1000:5.1f} ms")
    best = seen[0][0][2]
    print(f"  a round trip through the highest, down to a ground station and back, takes at least "
          f"{4 * best / C * 1000:.1f} ms")


# --8<-- [start:watch]
def watch(sats, place, seconds):
    start = datetime.now(timezone.utc)
    near = [s for s in sats if look(s, place, start)[2] < 4000]      # only these could come overhead soon
    print(f"the highest satellite, second by second, for the next {seconds} s ({len(near)} are near enough to matter):")
    current, changes = None, 0
    for t in range(seconds + 1):
        when = start + timedelta(seconds=t)
        el, s = max((look(s, place, when)[0], s) for s in near)
        if s is not current:
            if current is not None:
                changes += 1
                old = look(current, place, when)[0]
                print(f"  {when:%H:%M:%S}  → {s.name:<22} {el:4.1f}° up   (the last one, {current.name}, is at {old:.1f}°)")
            else:
                print(f"  {when:%H:%M:%S}    {s.name:<22} {el:4.1f}° up")
            current = s
    print(f"{changes} changes in {seconds} s" + (f": one every {seconds / changes:.0f} s on average" if changes else ""))
# --8<-- [end:watch]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--at", default=f"{HOME[0]},{HOME[1]}", help="latitude,longitude")
    ap.add_argument("--group", default="starlink")
    ap.add_argument("--watch", type=int, metavar="SECONDS")
    args = ap.parse_args()
    place = tuple(float(v) for v in args.at.split(","))
    sats = [s for s in download(args.group) if s.a - RE > 150]      # skip any that are falling back to Earth
    if args.watch:
        watch(sats, place, args.watch)
    else:
        snapshot(sats, place, args.group)


if __name__ == "__main__":
    main()
