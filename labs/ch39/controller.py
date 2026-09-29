#!/usr/bin/env python3
"""Chapter 39 lab: a software-defined networking controller, from scratch.

    python3 controller.py                      a learning switch (Chapter 9), for every switch that connects
    python3 controller.py --block 10.39.0.3    …plus one rule, pushed to every switch: drop all IPv4 from 10.39.0.3
    python3 controller.py --port 6653          listen somewhere else (6653 is OpenFlow's standard port)

It speaks OpenFlow 1.3 over TCP. The switches do the forwarding; this program only decides,
and writes its decisions into their flow tables. sdn_box.sh builds two Open vSwitch switches
that connect to it (Linux, needs sudo). Runs anywhere with Python 3.9+; no packages needed.
"""
import argparse
import socket
import struct
import threading

VERSION = 4                                        # OpenFlow 1.3
HELLO, ERROR, ECHO_REQUEST, ECHO_REPLY = 0, 1, 2, 3
FEATURES_REQUEST, FEATURES_REPLY = 5, 6
PACKET_IN, PACKET_OUT, FLOW_MOD = 10, 13, 14
CONTROLLER, FLOOD, ANY = 0xFFFFFFFD, 0xFFFFFFFB, 0xFFFFFFFF
NO_BUFFER = 0xFFFFFFFF
IN_PORT, ETH_DST, ETH_SRC, ETH_TYPE, IPV4_SRC = 0, 3, 4, 5, 11     # match field numbers
lock = threading.Lock()


def log(*args):
    with lock:
        print(*args, flush=True)


def mac(b):
    return ":".join(f"{x:02x}" for x in b)


# --8<-- [start:messages]
def message(kind, body=b"", xid=0):                # every OpenFlow message: version, type, length, id
    return struct.pack("!BBHI", VERSION, kind, 8 + len(body), xid) + body


def field(number, value):                          # one thing to match on, e.g. "Ethernet destination = …"
    return struct.pack("!HBB", 0x8000, number << 1, len(value)) + value


def match(*fields):
    body = b"".join(fields)
    m = struct.pack("!HH", 1, 4 + len(body)) + body
    return m + bytes(-len(m) % 8)                  # padded to a multiple of 8 bytes


def output(port):                                  # the action "send it out of this port"
    return struct.pack("!HHIH6x", 0, 16, port, 0xFFFF)


def apply(*actions):                               # the instruction "do these actions now"
    acts = b"".join(actions)
    return struct.pack("!HH4x", 4, 8 + len(acts)) + acts


def flow_mod(priority, m, instructions=b"", idle=0):
    """Add a row to the switch's flow table. No instructions means: drop."""
    body = struct.pack("!QQBBHHHIIIH2x", 0, 0, 0, 0, idle, 0, priority, NO_BUFFER, ANY, ANY, 0)
    return message(FLOW_MOD, body + m + instructions)


def packet_out(in_port, data, *actions):           # "send this packet, like this"
    acts = b"".join(actions)
    return message(PACKET_OUT, struct.pack("!IIH6x", NO_BUFFER, in_port, len(acts)) + acts + data)
# --8<-- [end:messages]


def parse_match(m):
    fields, i = {}, 4
    while i + 4 <= len(m):
        _, f, n = struct.unpack_from("!HBB", m, i)
        fields[f >> 1] = m[i + 4:i + 4 + n]
        i += 4 + n
    return fields


def describe(frame):
    kind = int.from_bytes(frame[12:14], "big")
    if kind == 0x0806 and frame[21] == 1:
        return "ARP: who has " + socket.inet_ntoa(frame[38:42]) + "?"
    if kind == 0x0806:
        return "ARP: " + socket.inet_ntoa(frame[28:32]) + " is here"
    if kind == 0x0800:
        proto = {1: "ping", 6: "TCP", 17: "UDP"}.get(frame[23], f"protocol {frame[23]}")
        return f"{proto} {socket.inet_ntoa(frame[26:30])} → {socket.inet_ntoa(frame[30:34])}"
    if kind == 0x86DD:
        return "IPv6"
    return f"type {kind:#06x}"


class Switch(threading.Thread):
    def __init__(self, conn, block):
        super().__init__(daemon=True)
        self.conn, self.block = conn, block
        self.name = "?"
        self.macs = {}                             # MAC address → port: what this switch has learned

    def send(self, data):
        self.conn.sendall(data)

    def recv_exact(self, n):
        data = b""
        while len(data) < n:
            more = self.conn.recv(n - len(data))
            if not more:
                raise ConnectionError("switch hung up")
            data += more
        return data

    def run(self):
        self.send(message(HELLO))
        self.send(message(FEATURES_REQUEST, xid=1))
        try:
            while True:
                version, kind, length, xid = struct.unpack("!BBHI", self.recv_exact(8))
                body = self.recv_exact(length - 8)
                if kind == ECHO_REQUEST:           # "are you still there?", every few seconds
                    self.send(message(ECHO_REPLY, body, xid))
                elif kind == FEATURES_REPLY:
                    self.connected(body)
                elif kind == PACKET_IN:
                    self.packet_in(body)
                elif kind == ERROR:
                    log(f"switch {self.name}: error {struct.unpack_from('!HH', body)}")
        except (ConnectionError, OSError):
            log(f"switch {self.name} disconnected")

    # --8<-- [start:connected]
    def connected(self, body):
        dpid = struct.unpack_from("!Q", body)[0]
        self.name = str(dpid)
        # Rule 0, the lowest priority, matches everything: "if nothing else matches, ask me".
        self.send(flow_mod(0, match(), apply(output(CONTROLLER))))
        log(f"switch {self.name} connected: installed “anything you don't recognise, send to me”")
        for ip in self.block:                      # the network-wide policy, one rule per switch
            self.send(flow_mod(100, match(field(ETH_TYPE, b"\x08\x00"), field(IPV4_SRC, socket.inet_aton(ip)))))
            log(f"switch {self.name}: installed “drop every IPv4 packet from {ip}”")
    # --8<-- [end:connected]

    # --8<-- [start:packet_in]
    def packet_in(self, body):
        mlen = struct.unpack_from("!H", body, 18)[0]
        in_port = int.from_bytes(parse_match(body[16:16 + mlen])[IN_PORT], "big")
        frame = body[16 + (mlen + 7) // 8 * 8 + 2:]
        dst, src = frame[0:6], frame[6:12]
        self.macs[src] = in_port                   # learn where the sender lives (Chapter 9)
        out = self.macs.get(dst)
        what = f"switch {self.name}, port {in_port}: {mac(src)} → {mac(dst)} ({describe(frame)})"
        if out is None:                            # don't know yet: send it everywhere
            self.send(packet_out(in_port, frame, output(FLOOD)))
            log(f"{what}: flood")
        else:                                      # know it: tell the switch, so it never has to ask again
            self.send(flow_mod(10, match(field(IN_PORT, in_port.to_bytes(4, "big")), field(ETH_DST, dst)),
                               apply(output(out)), idle=60))
            self.send(packet_out(in_port, frame, output(out)))
            log(f"{what}: port {out}, and a new flow")
    # --8<-- [end:packet_in]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=6653)
    ap.add_argument("--block", action="append", default=[], metavar="IP")
    args = ap.parse_args()
    server = socket.create_server(("0.0.0.0", args.port), reuse_port=hasattr(socket, "SO_REUSEPORT"))
    log(f"controller listening on port {args.port}")
    while True:
        conn, _ = server.accept()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        Switch(conn, args.block).start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
