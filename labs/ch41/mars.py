#!/usr/bin/env python3
"""Chapter 41 lab: how far away is Mars today, and how long does a message take?

    python3 mars.py                  today
    python3 mars.py 2027-02-19       another day
    python3 mars.py --year           the next two years: nearest, furthest, and when the Sun is in the way

Uses NASA JPL's "approximate positions of the planets" (Standish): each planet's orbit as six numbers
and how they slowly change, good to a small fraction of a degree between 1800 and 2050. Python 3.9+.
"""
import math
import sys
from datetime import date, datetime, timedelta, timezone

AU = 149_597_870.7          # km
C = 299_792.458             # km/s
# (a in AU, e, inclination, mean longitude, longitude of perihelion, longitude of ascending node),
# at 1 January 2000, and how much each changes per century. Angles in degrees.
ORBITS = {
    "Earth": ((1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0),
              (0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0)),
    "Mars": ((1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891),
             (0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343)),
}


# --8<-- [start:where]
def where(planet, when):
    """The planet's position (x, y, z, in AU) around the Sun, at `when`."""
    t = (when - datetime(2000, 1, 1, 12, tzinfo=timezone.utc)).total_seconds() / 86400 / 36525   # centuries
    a, e, inc, mean_lon, peri, node = (v + dv * t for v, dv in zip(*ORBITS[planet]))
    m = math.radians((mean_lon - peri + 180) % 360 - 180)        # how far round, from its closest point
    w, node, inc = math.radians(peri - node), math.radians(node), math.radians(inc)
    ecc = m + e * math.sin(m)
    for _ in range(10):                                           # Kepler's equation, as in Chapter 40
        ecc -= (ecc - e * math.sin(ecc) - m) / (1 - e * math.cos(ecc))
    xp, yp = a * (math.cos(ecc) - e), a * math.sqrt(1 - e * e) * math.sin(ecc)
    cw, sw, cn, sn, ci, si = math.cos(w), math.sin(w), math.cos(node), math.sin(node), math.cos(inc), math.sin(inc)
    return ((cw * cn - sw * sn * ci) * xp + (-sw * cn - cw * sn * ci) * yp,
            (cw * sn + sw * cn * ci) * xp + (-sw * sn + cw * cn * ci) * yp,
            sw * si * xp + cw * si * yp)


def mars_from_earth(when):
    """Distance (km), and the angle between Mars and the Sun as seen from Earth (degrees)."""
    e, m = where("Earth", when), where("Mars", when)
    d = [mi - ei for mi, ei in zip(m, e)]
    dist = math.sqrt(sum(v * v for v in d))
    sun = [-v for v in e]
    cos_angle = sum(a * b for a, b in zip(d, sun)) / (dist * math.sqrt(sum(v * v for v in sun)))
    return dist * AU, math.degrees(math.acos(cos_angle))
# --8<-- [end:where]


def minutes(km):
    s = km / C
    return f"{int(s // 60)} min {s % 60:02.0f} s"


def day(d):
    when = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    km, angle = mars_from_earth(when)
    print(f"{d:%d %B %Y}: Mars is {km / 1e6:,.0f} million km from Earth ({km / AU:.3f} AU)")
    print(f"  a radio message takes {minutes(km)} to get there, and as long again for any answer:")
    print(f"  {2 * km / C / 60:.0f} minutes for a single question and reply")
    print(f"  Mars is {angle:.0f}° from the Sun in our sky" +
          ("; that’s too close to talk through the Sun’s noise" if angle < 3 else ""))


# --8<-- [start:year]
def year(start):
    days = [start + timedelta(days=k) for k in range(800)]
    info = [(d, *mars_from_earth(datetime(d.year, d.month, d.day, tzinfo=timezone.utc))) for d in days]
    near = min(info, key=lambda v: v[1])
    far = max(info, key=lambda v: v[1])
    print(f"over the next two years, from {start:%d %b %Y}:")
    print(f"  nearest:  {near[0]:%d %b %Y}, {near[1] / 1e6:4.0f} million km: {minutes(near[1])} one way")
    print(f"  furthest: {far[0]:%d %b %Y}, {far[1] / 1e6:4.0f} million km: {minutes(far[1])} one way")
    quiet = [d for d, _, angle in info if angle < 3]
    if quiet:
        print(f"  the Sun is in the way (Mars within 3° of it) from {quiet[0]:%d %b %Y} to {quiet[-1]:%d %b %Y}: "
              f"{len(quiet)} days of near silence")
# --8<-- [end:year]


if __name__ == "__main__":
    today = datetime.now(timezone.utc).date()
    if "--year" in sys.argv:
        year(today)
    else:
        day(date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else today)
