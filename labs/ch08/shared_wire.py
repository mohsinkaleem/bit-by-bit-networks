#!/usr/bin/env python3
"""Chapter 8 lab, part 2: one wire, many computers, and addresses on every frame.

Start the wire first, then join it from as many terminals as you like:

    python3 shared_wire.py wire                          the wire itself
    python3 shared_wire.py station alice 0a:11           join as Alice, card address 0a:11
    python3 shared_wire.py station bob 0b:22
    python3 shared_wire.py station carol 0c:33
    python3 shared_wire.py station eve 0e:99 --nosy      Eve's card keeps EVERY frame

At a station's prompt:
    to 0b:22 hello bob       send a frame to one card
    to ff:ff anyone there?   send to everyone (the broadcast address)
    who                      broadcast "who's there?" (every station answers automatically)

The wire repeats every frame to every station, just like a real shared cable, and each
network card decides for itself which frames to keep. (Collisions are simulated in bus_sim.py.)
"""
import socket
import sys
import threading

WIRE = ("127.0.0.1", 7008)
BROADCAST = "ff:ff"
DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"


def run_wire():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(WIRE)
    attached = set()
    print("the wire is up. Every frame gets copied to every station.", flush=True)
    while True:
        data, sender = sock.recvfrom(2048)
        if data == b"JOIN":
            attached.add(sender)
            print(f"a station plugged in ({len(attached)} on the wire)", flush=True)
            continue
        print(f"on the wire: {data.decode()}", flush=True)
        for station in attached:
            if station != sender:
                sock.sendto(data, station)            # everybody hears everything


# --8<-- [start:frame]
def make_frame(to, frm, data):
    return f"{to} {frm} {data}".encode()


def read_frame(raw):
    to, frm, data = raw.decode().split(" ", 2)
    return to, frm, data
# --8<-- [end:frame]


def run_station(name, mac, nosy):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 0))
    sock.sendto(b"JOIN", WIRE)

    # --8<-- [start:filter]
    def listen():
        while True:
            to, frm, data = read_frame(sock.recv(2048))
            if to == mac or to == BROADCAST:
                print(f"\r{BOLD}{frm} → {to}{RESET}: {data}\n{name}> ", end="", flush=True)
                if data == "who's there?":             # answer broadcasts automatically
                    sock.sendto(make_frame(frm, mac, f"it's {name}!"), WIRE)
            elif nosy:
                print(f"\r{DIM}(snooped) {frm} → {to}: {data}{RESET}\n{name}> ", end="", flush=True)
            else:
                print(f"\r{DIM}[my card ignored a frame for {to}]{RESET}\n{name}> ", end="", flush=True)
    # --8<-- [end:filter]

    threading.Thread(target=listen, daemon=True).start()
    print(f"{name}'s card has address {mac}{' (and is NOSY)' if nosy else ''}. Commands: to <addr> <msg>, who, quit")
    while True:
        try:
            line = input(f"{name}> ").strip()
        except EOFError:
            return
        if line == "quit":
            return
        if line == "who":
            sock.sendto(make_frame(BROADCAST, mac, "who's there?"), WIRE)
        elif line.startswith("to ") and len(line.split(" ", 2)) == 3:
            _, to, msg = line.split(" ", 2)
            sock.sendto(make_frame(to, mac, msg), WIRE)
        elif line:
            print("try: to 0b:22 hello   or   who")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["wire"]:
        run_wire()
    elif args[:1] == ["station"] and len(args) >= 3:
        run_station(args[1], args[2].lower(), "--nosy" in args)
    else:
        print(__doc__)
