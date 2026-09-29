#!/usr/bin/env python3
"""Chapter 12 lab: send datagrams to the programs on Otto's computer (start otto.py first).

    python3 dgram.py 7123                          ask the clock the time
    python3 dgram.py 7064 e4                       make a chess move
    python3 dgram.py 7064 d4 --from-port 50001     ...from a port of your choosing
    python3 dgram.py 7012 "hello grandpa"          chat (chat never replies)
    python3 dgram.py 7055 hello                    send to a port where nobody is home
    python3 dgram.py 7099 --blast 5000             fire 5,000 numbered datagrams at slowpoke, as fast as possible
    python3 dgram.py 7123 --host 192.168.1.250     try an address on your network where there's no computer at all
"""
import argparse
import socket

OTTO = "127.0.0.1"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("port", type=int)
    p.add_argument("message", nargs="?", default="what time is it?")
    p.add_argument("--from-port", type=int, default=0, help="our own port (0 = let the operating system pick one)")
    p.add_argument("--blast", type=int, metavar="N", help="send N numbered datagrams without stopping")
    p.add_argument("--host", default=OTTO, help="where Otto's computer is (default 127.0.0.1, this computer)")
    args = p.parse_args()
    if args.blast:
        return blast(args)

    # --8<-- [start:send]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", args.from_port))                 # port 0 means "any free port, you choose"
    sock.connect((args.host, args.port))            # UDP "connect" just remembers where to send
    me = sock.getsockname()
    sock.send(args.message.encode())
    print(f"sent {len(args.message)} bytes from {me[0]}:{me[1]} to {args.host}:{args.port}")
    sock.settimeout(1.0)
    try:
        data, sender = sock.recvfrom(2048)
        print(f"reply from {sender[0]}:{sender[1]}: {data.decode().strip()}")
    except socket.timeout:
        print("no reply within a second. (UDP promises nothing: maybe there's no reply, maybe it got lost.)")
    except ConnectionRefusedError:
        print("nobody home! Otto's operating system says no program is using that port.")
    # --8<-- [end:send]


def blast(args):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", args.from_port))
    sock.connect((args.host, args.port))
    for i in range(args.blast):
        sock.send(f"{i}/{args.blast}".encode())
    print(f"fired {args.blast:,} datagrams from port {sock.getsockname()[1]} without waiting for anything")
    sock.settimeout(3.0)
    try:
        print("reply:", sock.recv(2048).decode())
    except (socket.timeout, ConnectionRefusedError):
        print("no report came back. Is otto.py running?")


if __name__ == "__main__":
    main()
