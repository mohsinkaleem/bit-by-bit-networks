#!/usr/bin/env python3
"""Chapter 4 lab: a tiny "computer" with an operating system, programs, a disk and a wire.

Run two of them in two terminal windows. The first one waits for the wire to be plugged in,
the second one plugs it in:

    python3 computer.py alice --disk alice_disk --listen 7000
    python3 computer.py bob   --disk bob_disk   --connect 7000

Then type commands at either prompt:

    START SERVE        run the file server in the background
    STOP SERVE         stop it again
    FETCH REPORT       ask the other computer for the file REPORT
    STORE NOTES        send your file NOTES to the other computer's INBOX
    CHAT hello there   send a chat message
    PS                 list running programs
    LS                 list files on this computer's disk
    SHOW REPORT        print a file from this disk
    QUIT

(We use a real network connection on your own machine as a stand-in for the copper wire.
It's "cheating": this wire works in both directions at once and never loses anything.
We'll build that reliability ourselves in Chapter 13.)
"""
import argparse
import itertools
import os
import queue
import socket
import sys
import threading
import time

TIMEOUT = 3.0     # seconds FETCH/STORE wait for an answer


# ------------------------------------------------------------------ framing (from Chapter 3)
# A message is a list of lines. On the wire: ~S line ~L line ~L line ~E, with ~ escaped as ~~.

# --8<-- [start:wire-format]
def encode(lines):
    body = "~L".join(line.replace("~", "~~") for line in lines)
    return "~S" + body + "~E"


def decode_stream(buffer):
    """Pull complete frames out of buffer. Returns (list of messages, leftover text)."""
    messages = []
    while True:
        start = buffer.find("~S")
        if start < 0:
            return messages, ""
        lines, current, i = [], "", start + 2
        while i < len(buffer) - 1:
            pair = buffer[i:i + 2]
            if pair == "~~":
                current += "~"
            elif pair == "~L":
                lines.append(current)
                current = ""
            elif pair == "~E":
                lines.append(current)
                messages.append(lines)
                buffer = buffer[i + 2:]
                break
            else:
                current += buffer[i]
                i += 1
                continue
            i += 2
        else:
            return messages, buffer[start:]     # frame not finished yet: keep it for later
# --8<-- [end:wire-format]


# ------------------------------------------------------------------ the operating system

class OS:
    def __init__(self, name, disk):
        self.name, self.disk = name, disk
        self.wire = None
        self.mailboxes = {}                      # program id -> queue of incoming messages
        self.threads = {}
        self.counter = itertools.count(1)
        self.lock = threading.Lock()
        os.makedirs(os.path.join(disk, "INBOX"), exist_ok=True)

    def log(self, text):
        sys.stdout.write(f"\r[{self.name} OS] {text}\n{self.name}> ")
        sys.stdout.flush()

    # --8<-- [start:dispatch]
    def send(self, to, sender, lines):
        """A program asks the OS to send a message to a program on the other computer."""
        frame = encode([f"TO: {to}", f"FROM: {sender}"] + lines)
        self.wire.sendall(frame.encode())

    def deliver(self, message):
        """A message arrived on the wire: read the TO line and hand it to that program."""
        headers = {}
        while message and ": " in message[0] and message[0].split(": ")[0] in ("TO", "FROM"):
            key, value = message.pop(0).split(": ", 1)
            headers[key] = value
        to = headers.get("TO")
        box = self.mailboxes.get(to)
        if box is None:
            self.log(f"dropped a message for {to!r}: no program by that name is running")
            return
        box.put((headers.get("FROM"), message))
    # --8<-- [end:dispatch]

    def start(self, kind, target, *args):
        pid = kind if kind in ("SERVE", "CHAT") else f"{kind}#{next(self.counter)}"
        with self.lock:
            if pid in self.mailboxes:
                return self.log(f"{pid} is already running")
            self.mailboxes[pid] = queue.Queue()
        t = threading.Thread(target=self._run, args=(pid, target, args), daemon=True)
        self.threads[pid] = t
        t.start()
        return pid

    def _run(self, pid, target, args):
        try:
            target(self, pid, *args)
        finally:
            with self.lock:
                self.mailboxes.pop(pid, None)

    def stop(self, pid):
        box = self.mailboxes.get(pid)
        if box:
            box.put(None)                          # a "please exit" note

    def receive(self, pid, timeout=None):
        try:
            return self.mailboxes[pid].get(timeout=timeout)
        except queue.Empty:
            return "timeout"

    def read_file(self, name):
        path = os.path.join(self.disk, name)
        if not os.path.isfile(path):
            return None
        with open(path) as f:
            return f.read().splitlines()

    def write_file(self, name, lines):
        with open(os.path.join(self.disk, name), "w") as f:
            f.write("\n".join(lines) + "\n")


# ------------------------------------------------------------------ programs

# --8<-- [start:programs]
def serve(os_, me):
    """The file server: answer GET and PUT requests until told to stop."""
    os_.log("SERVE is running and waiting for requests")
    while True:
        item = os_.receive(me)
        if item is None:
            return os_.log("SERVE stopped")
        sender, lines = item
        command = lines[0] if lines else ""
        if command == "GET" and len(lines) >= 2:
            body = os_.read_file(lines[1])
            if body is None:
                os_.send(sender, me, ["NOT FOUND", lines[1]])
            else:
                os_.send(sender, me, ["OK", lines[1]] + body)
            os_.log(f"{sender} asked for {lines[1]!r}: {'sent it' if body is not None else 'not found'}")
        elif command == "PUT" and len(lines) >= 2:
            name = os.path.basename(lines[1])          # only ever write inside INBOX
            os_.write_file(os.path.join("INBOX", name), lines[2:])
            os_.send(sender, me, ["OK", name])
            os_.log(f"{sender} stored {name!r} in INBOX")
        else:
            os_.send(sender, me, ["BAD REQUEST"])


def fetch(os_, me, name):
    os_.send("SERVE", me, ["GET", name])
    reply = os_.receive(me, timeout=TIMEOUT)
    if reply == "timeout":
        return os_.log(f"{me}: no answer from the other computer (is SERVE running there?)")
    _, lines = reply
    if lines[0] == "OK":
        name = os.path.basename(name)              # always save inside our own disk folder
        os_.write_file(name, lines[2:])
        os_.log(f"{me}: saved {name!r} ({len(lines) - 2} lines)")
    else:
        os_.log(f"{me}: the other computer says {lines[0]}")
# --8<-- [end:programs]


def store(os_, me, name):
    body = os_.read_file(name)
    if body is None:
        return os_.log(f"{me}: there is no file called {name!r} on this disk")
    os_.send("SERVE", me, ["PUT", name] + body)
    reply = os_.receive(me, timeout=TIMEOUT)
    if reply == "timeout":
        return os_.log(f"{me}: no answer (is SERVE running on the other computer?)")
    os_.log(f"{me}: the other computer says {' '.join(reply[1])}")


def chat(os_, me):
    """Always running: prints chat messages that arrive."""
    while True:
        item = os_.receive(me)
        if item is None:
            return
        sender, lines = item
        os_.log(f"💬 {' / '.join(lines)}")


# ------------------------------------------------------------------ the wire + the shell

def plug_in(args):
    if args.listen:
        server = socket.socket()
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", args.listen))
        server.listen(1)
        print(f"waiting for the other computer to plug into port {args.listen}...")
        conn, _ = server.accept()
        return conn
    for _ in range(50):
        try:
            return socket.create_connection(("127.0.0.1", args.connect))
        except ConnectionRefusedError:
            time.sleep(0.2)
    sys.exit("nobody is listening on the other end of the wire")


def listen_to_wire(os_):
    buffer = ""
    while True:
        data = os_.wire.recv(4096)
        if not data:
            os_.log("the wire went dead (the other computer quit)")
            os._exit(0)
        buffer += data.decode()
        messages, buffer = decode_stream(buffer)
        for m in messages:
            os_.deliver(m)


def shell(os_):
    while True:
        try:
            line = input(f"{os_.name}> ").strip()
        except EOFError:
            line = "QUIT"
        if not line:
            continue
        cmd, _, rest = line.partition(" ")
        cmd = cmd.upper()
        if cmd == "START" and rest.upper() == "SERVE":
            os_.start("SERVE", serve)
        elif cmd == "STOP":
            os_.stop(rest.upper())
        elif cmd == "FETCH" and rest:
            os_.start("FETCH", fetch, rest)
        elif cmd == "STORE" and rest:
            os_.start("STORE", store, rest)
        elif cmd == "CHAT" and rest:
            os_.send("CHAT", "CHAT", [rest])
        elif cmd == "PS":
            print("running:", ", ".join(sorted(os_.mailboxes)) or "(nothing)")
        elif cmd == "LS":
            for root, _, files in os.walk(os_.disk):
                for f in sorted(files):
                    print(" ", os.path.relpath(os.path.join(root, f), os_.disk))
        elif cmd == "SHOW" and rest:
            print("\n".join(os_.read_file(rest) or ["(no such file)"]))
        elif cmd == "QUIT":
            os._exit(0)
        else:
            print("commands: START SERVE, STOP SERVE, FETCH name, STORE name, CHAT text, PS, LS, SHOW name, QUIT")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("name")
    p.add_argument("--disk", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--listen", type=int)
    g.add_argument("--connect", type=int)
    args = p.parse_args()
    os_ = OS(args.name, args.disk)
    os_.wire = plug_in(args)
    print(f"wire connected. type HELP for commands.")
    os_.start("CHAT", chat)
    threading.Thread(target=listen_to_wire, args=(os_,), daemon=True).start()
    shell(os_)


if __name__ == "__main__":
    main()
