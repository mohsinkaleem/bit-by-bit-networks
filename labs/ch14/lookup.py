#!/usr/bin/env python3
"""Chapter 14 lab: look up a name, by asking the resolver on your street (start names.py first).

    python3 lookup.py otto.seaside                ask the resolver
    python3 lookup.py otto.seaside --trace        do the resolver's job yourself, one server at a time
    python3 lookup.py --update otto.seaside 4.9   Otto's town renumbers him (tell seaside's name server)
"""
import argparse
import socket
import time

HOST, RESOLVER, ROOT = "127.0.0.1", 7050, 7053


def ask(port, message, timeout=2.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    sock.sendto(message.encode(), (HOST, port))
    try:
        return sock.recvfrom(2048)[0].decode()
    except (socket.timeout, ConnectionRefusedError):
        raise SystemExit("no answer: is names.py running?")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("name", nargs="?")
    p.add_argument("address", nargs="?")
    p.add_argument("--trace", action="store_true")
    p.add_argument("--update", action="store_true")
    args = p.parse_args()
    if not args.name:
        p.error("give me a name, like otto.seaside")

    if args.update:
        zone_port = {"seaside": 7054, "school": 7055, "library": 7056, "street": 7057}[args.name.split(".")[-1]]
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(f"U {args.name} {args.address}".encode(), (HOST, zone_port))
        print(f"told the {args.name.split('.')[-1]} name server: {args.name} is now {args.address}")
        return

    if args.trace:
        # --8<-- [start:trace]
        port = ROOT
        for step in range(1, 6):
            reply = ask(port, f"Q {step} {args.name}").split()
            if reply[0] == "R":
                print(f"{step}. port {port} says: I don't know {args.name}, but port {reply[3]} is in charge of “{reply[2]}”")
                port = int(reply[3])
            elif reply[0] == "A":
                print(f"{step}. port {port} says: {args.name} is {reply[3]} (good for {reply[4]} seconds)")
                return
            else:
                print(f"{step}. port {port} says: there's no such name as {args.name}")
                return
        # --8<-- [end:trace]
        return

    start = time.monotonic()
    lines = ask(RESOLVER, f"Q {args.name}").split("\n")
    took = (time.monotonic() - start) * 1000
    answer = lines[0].split()
    if answer[0] == "A":
        print(f"{args.name} is {answer[2]}   ({' '.join(answer[3:])}; answered in {took:.1f} ms)")
    else:
        print(f"{args.name}: no such name   ({took:.1f} ms)")
    for s in lines[1:]:
        print(f"   the resolver {s}")


if __name__ == "__main__":
    main()
