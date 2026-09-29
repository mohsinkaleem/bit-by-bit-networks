#!/usr/bin/env python3
"""Chapter 12 lab: Grandpa Otto's computer, running four programs, each with its own port.

    python3 otto.py                 start all four programs (Ctrl-C to stop)
    python3 otto.py --no-chess      ...but not chess, so nobody is home at port 7064

    port 7012  chat      prints whatever you send it
    port 7064  chess     plays a separate game with every (address, port) that writes to it
    port 7123  clock     replies with the time
    port 7099  slowpoke  counts numbered datagrams, slowly, to show what "fire and forget" means

Talk to them with dgram.py, or with nc:  nc -u 127.0.0.1 7123   (type anything, press Enter)
"""
import argparse
import datetime
import selectors
import socket
import time

HOST = "127.0.0.1"
OTTO_MOVES = ["e5", "Nc6", "Bc5", "Nf6", "d6", "O-O", "Qe7"]


# --8<-- [start:programs]
def chat(sock, data, sender):
    print(f"[chat]     {sender[0]}:{sender[1]} says: {data.decode(errors='replace').strip()}")


games = {}                                   # (address, port) of the other player -> list of their moves


def chess(sock, data, sender):
    moves = games.setdefault(sender, [])     # a new sender (address AND port) means a new game
    moves.append(data.decode(errors="replace").strip())
    number = list(games).index(sender) + 1
    reply = OTTO_MOVES[(len(moves) - 1) % len(OTTO_MOVES)]
    print(f"[chess]    game #{number} with {sender[0]}:{sender[1]}: they played {moves[-1]}, Otto plays {reply}")
    sock.sendto(f"game #{number}, move {len(moves)}: you played {moves[-1]}, I play {reply}".encode(), sender)


def clock(sock, data, sender):
    print(f"[clock]    {sender[0]}:{sender[1]} asked the time")
    sock.sendto(f"It's {datetime.datetime.now():%H:%M:%S} at Otto's.\n".encode(), sender)
# --8<-- [end:programs]


class Slowpoke:
    """Expects datagrams like "17/5000". Handles each one slowly, then reports what arrived."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.seen, self.total, self.out_of_order, self.last, self.sender, self.when = set(), 0, 0, -1, None, 0

    def __call__(self, sock, data, sender):
        try:
            n, total = map(int, data.decode().split("/"))
        except ValueError:
            return
        if n < self.last:
            self.out_of_order += 1
        self.seen.add(n)
        self.total, self.last, self.sender, self.when = total, n, sender, time.monotonic()
        time.sleep(0.0005)                   # a slow program: half a millisecond per datagram

    def maybe_report(self, sock):
        if self.sender and time.monotonic() - self.when > 0.5:
            lost = self.total - len(self.seen)
            text = (f"slowpoke got {len(self.seen):,} of {self.total:,} datagrams; {lost:,} never arrived "
                    f"({100 * lost / self.total:.0f}%), {self.out_of_order} arrived out of order")
            print(f"[slowpoke] {text}")
            sock.sendto(text.encode(), self.sender)
            self.reset()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--no-chess", action="store_true")
    args = p.parse_args()

    slowpoke = Slowpoke()
    programs = {7012: chat, 7123: clock, 7099: slowpoke}
    if not args.no_chess:
        programs[7064] = chess
    # --8<-- [start:mailboxes]
    sel = selectors.DefaultSelector()
    for port, program in programs.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)       # DGRAM = datagrams, i.e. UDP
        if program is slowpoke:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16384)  # a small mailbox
        sock.bind((HOST, port))                                       # "please give me mailbox number <port>"
        sel.register(sock, selectors.EVENT_READ, program)
        print(f"{program.__class__.__name__.lower() if program is slowpoke else program.__name__:>8} is listening on {HOST}:{port}")
    # --8<-- [end:mailboxes]
    print("Otto's computer is ready. Ctrl-C to stop.\n")
    slow_sock = next(k.fileobj for k in sel.get_map().values() if k.data is slowpoke)
    try:
        while True:
            for key, _ in sel.select(timeout=0.2):
                data, sender = key.fileobj.recvfrom(2048)
                key.data(key.fileobj, data, sender)
            slowpoke.maybe_report(slow_sock)
    except KeyboardInterrupt:
        print("\nOtto's computer is shutting down.")


if __name__ == "__main__":
    main()
