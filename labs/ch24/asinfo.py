#!/usr/bin/env python3
"""Chapter 24 lab: ask the internet's route collectors about any address.

    python3 asinfo.py 188.184.67.127      who announces it, is that allowed (RPKI), and which AS paths lead there
    python3 asinfo.py 1.1.1.1 --paths 20  show more of the paths the collectors saw
    python3 asinfo.py --table             how big is the internet's routing table today?

It uses RIPEstat (stat.ripe.net), a free service from RIPE NCC, which runs about two dozen
"route collectors" around the world. Each one has BGP sessions with hundreds of networks,
and records every route they announce.
"""
import argparse
import collections
import json
import urllib.parse
import urllib.request

API = "https://stat.ripe.net/data/{}/data.json?"


# --8<-- [start:ask]
def ask(call, **params):
    """One RIPEstat 'data call'. Every answer is JSON, with the interesting part under 'data'."""
    url = API.format(call) + urllib.parse.urlencode(params | {"sourceapp": "bitbybit-book"})
    with urllib.request.urlopen(url, timeout=60) as reply:
        return json.load(reply)["data"]
# --8<-- [end:ask]


def squash(path):
    """Remove repeats of the same AS next to each other (prepending)."""
    out = []
    for asn in path:
        if not out or out[-1] != asn:
            out.append(asn)
    return out


_names = {}


def as_name(asn):
    if asn not in _names:
        try:
            _names[asn] = ask("as-overview", resource=asn)["holder"] or "?"
        except OSError:
            _names[asn] = "?"
    return _names[asn]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("address", nargs="?")
    p.add_argument("--paths", type=int, default=8, help="how many AS paths to print")
    p.add_argument("--table", action="store_true")
    args = p.parse_args()

    if args.table or not args.address:
        t = ask("ris-full-table-threshold")
        n = ask("ris-asns", list_asns="false")["counts"]["total"]
        print(f"a full IPv4 routing table: about {t['v4']:,} prefixes")
        print(f"a full IPv6 routing table: about {t['v6']:,} prefixes")
        print(f"autonomous systems seen by RIPE's collectors: {n:,}")
        if not args.address:
            return

    over = ask("prefix-overview", resource=args.address)
    prefix = over["resource"]
    origins = [a["asn"] for a in over["asns"]]
    print(f"{args.address} is inside {prefix}")
    for a in over["asns"]:
        print(f"  announced by AS{a['asn']}: {a['holder']}")
    for asn in origins:
        rpki = ask("rpki-validation", resource=asn, prefix=prefix)
        roas = ", ".join(f"{r['prefix']} max /{r['max_length']} by AS{r['origin']}" for r in rpki.get("validating_roas", []))
        print(f"  RPKI: {rpki['status']}" + (f"  (ROA: {roas})" if roas else ""))

    # --8<-- [start:paths]
    glass = ask("looking-glass", resource=prefix)
    paths = []
    for rrc in glass["rrcs"]:
        for peer in rrc["peers"]:
            paths.append((rrc["location"], peer["as_path"].split()))
    print(f"\n{len(paths)} routes to {prefix}, seen from {len(glass['rrcs'])} collectors. A few of them:")
    for where, path in paths[:args.paths]:
        print(f"  from {where[:24]:<24} {' '.join(path)}")
    squashed = [squash(path) for _, path in paths]      # "174 513 513" → "174 513"
    lengths = collections.Counter(len(path) for path in squashed)
    upstream = collections.Counter(path[-2] for path in squashed if len(path) > 1)
    prepended = sum(1 for _, path in paths if len(path) > 1 and path[-1] == path[-2])
    # --8<-- [end:paths]
    print("\nhow many networks away (not counting repeats):",
          ", ".join(f"{k}: {v}" for k, v in sorted(lengths.items())))
    print("the origin's neighbours on those paths (its providers and peers):")
    for asn, count in upstream.most_common(6):
        print(f"  AS{asn:<7} {count:>3} routes   {as_name(asn)}")
    if prepended:
        print(f"{prepended} of the routes have the origin's number more than once: it's prepending, "
              f"to make those paths look longer.")


if __name__ == "__main__":
    main()
