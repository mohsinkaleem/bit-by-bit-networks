#!/usr/bin/env python3
"""Chapter 16 lab: a tiny tcpdump. It compiles a capture filter into a little BPF-style program,
runs that program on every packet, and prints the packets that pass, one line each.

    python3 minidump.py home.pcap                          every packet
    python3 minidump.py home.pcap "tcp port 80"            only the web page
    python3 minidump.py home.pcap "icmp or arp" -v         ...with more detail
    python3 minidump.py -d "ip and tcp dst port 80"        show the compiled program, like tcpdump -d
    python3 minidump.py home.pcap "udp port 53" --trace 3  run packet 3 through the program, step by step

Live, on your own network (tcpdump captures everything, minidump filters and prints):

    sudo tcpdump -i en0 -U -w - | python3 minidump.py - "port 443"          macOS Wi-Fi
    sudo tcpdump -i wlan0 -U -w - | python3 minidump.py - "arp or icmp"     Linux Wi-Fi

The filter language is a small part of tcpdump's own (see "man pcap-filter"):
    ip  arp  ip6  tcp  udp  icmp                 a protocol
    host 1.1.1.1   src host …   dst host …       an address (IPv4 packets and "who has?" messages)
    net 192.168.1.0/24                           a whole network
    port 53   src port …   dst port …            a port, TCP or UDP (or say "tcp port 80")
    portrange 6000-6010                          a range of ports
    ether host 2c:cf:67:5e:10:c2   broadcast     a card address, or everyone
    greater 1000   less 100                      the frame's length
    tcp[13] & 2 != 0   ip[8] < 10                any byte of a header (tcp[tcpflags] & tcp-syn != 0 works too)
    not …   … and …   … or …   ( … )             combine them. and/or have EQUAL priority, so use brackets!
Only IPv4 is looked inside: IPv6 packets never match "tcp" or "port" here (real tcpdump checks both).
"""
import argparse
import re
import struct
import sys
import time

ACCEPT, REJECT = 262144, 0
NAMES = {"tcpflags": 13, "tcp-fin": 1, "tcp-syn": 2, "tcp-rst": 4, "tcp-push": 8, "tcp-ack": 16, "tcp-urg": 32,
         "icmptype": 0, "icmpcode": 1, "icmp-echoreply": 0, "icmp-unreach": 3, "icmp-echo": 8, "icmp-timxceed": 11,
         "ssh": 22, "domain": 53, "bootps": 67, "bootpc": 68, "http": 80, "ntp": 123, "https": 443, "mdns": 5353}
PROTOS = {"tcp": 6, "udp": 17, "icmp": 1}


# ---------------------------------------------------------------- reading captures

def read_exact(f, n):
    data = b""
    while len(data) < n:
        chunk = f.read(n - len(data))
        if not chunk:
            break
        data += chunk
    return data


def read_pcap(f):
    """Yields (seconds, microseconds, frame) from a classic pcap file, as tcpdump -w writes it (also from a pipe)."""
    head = read_exact(f, 24)
    if len(head) < 24:
        return
    magic = struct.unpack("<I", head[:4])[0]
    if magic == 0x0A0D0D0A:
        raise SystemExit("That's a pcapng file. Convert it first: tcpdump -r in.pcapng -w out.pcap")
    endian = "<" if magic in (0xA1B2C3D4, 0xA1B23C4D) else ">"
    nano = magic in (0xA1B23C4D, 0x4D3CB2A1)
    linktype = struct.unpack(endian + "I", head[20:24])[0] & 0xFFFF
    if linktype != 1:
        raise SystemExit(f"This capture has link type {linktype}; minidump only reads Ethernet (1). "
                         "Capture on a single interface such as en0 or wlan0, not 'any'.")
    while True:
        rec = read_exact(f, 16)
        if len(rec) < 16:
            return
        secs, frac, caplen, _ = struct.unpack(endian + "IIII", rec)
        yield secs, frac // 1000 if nano else frac, read_exact(f, caplen)


# ---------------------------------------------------------------- parsing the filter

TOKEN = re.compile(r"\s*(\(|\)|\[|\]|!=|==|<=|>=|&&|\|\||[=<>!&|]|[A-Za-z0-9_.:/\-]+)")


def tokenize(text):
    tokens, pos = [], 0
    text = text.strip()
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise SyntaxError(f"don't understand {text[pos:]!r}")
        tokens.append(m.group(1))
        pos = m.end()
    return tokens


def number(word):
    word = str(NAMES.get(word, word))
    try:
        return int(word, 0)
    except ValueError:
        raise SyntaxError(f"expected a number, got {word!r}")


def ipv4(word):
    parts = word.split(".")
    if len(parts) != 4 or not all(p.isdigit() and int(p) < 256 for p in parts):
        raise SyntaxError(f"{word!r} isn't an IPv4 address")
    return struct.unpack("!I", bytes(int(p) for p in parts))[0]


def mac(word):
    parts = word.split(":")
    if len(parts) != 6:
        raise SyntaxError(f"{word!r} isn't a card (MAC) address")
    return bytes(int(p, 16) for p in parts)


# --8<-- [start:parse]
class Parser:
    """Turns "tcp port 80 and not host 1.1.1.1" into a tree of tuples:
    ('and', ('port', None, 80, 80, 'tcp'), ('not', ('host', None, 16843009, None)))"""

    def __init__(self, text):
        self.tokens, self.i = tokenize(text), 0

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def take(self, expected=None):
        tok = self.peek()
        if tok is None:
            raise SyntaxError("the filter stops too soon" + (f" (expected {expected!r})" if expected else ""))
        if expected and tok != expected:
            raise SyntaxError(f"expected {expected!r}, got {tok!r}")
        self.i += 1
        return tok

    def parse(self):
        tree = self.expr()
        if self.peek() is not None:
            raise SyntaxError(f"unexpected {self.peek()!r}")
        return tree

    def expr(self):                      # "and" and "or" have the same priority, left to right, like tcpdump
        left = self.unary()
        while self.peek() in ("and", "&&", "or", "||"):
            op = "and" if self.take() in ("and", "&&") else "or"
            left = (op, left, self.unary())
        return left

    def unary(self):
        tok = self.peek()
        if tok in ("not", "!"):
            self.take()
            return ("not", self.unary())
        if tok == "(":
            self.take()
            inner = self.expr()
            self.take(")")
            return inner
        return self.primitive()

    def primitive(self):
        tok = self.take()
        if tok in ("greater", "less"):
            return ("len", tok, number(self.take()))
        if tok == "broadcast":
            return ("ether", "dst", b"\xff" * 6)
        if tok == "multicast":
            return ("multicast",)
        proto = None
        if tok in ("ether", "ip", "arp", "ip6", "tcp", "udp", "icmp"):
            proto = tok
            if self.peek() == "[":
                return self.comparison(proto)
            if self.peek() not in ("src", "dst", "host", "net", "port", "portrange", "broadcast"):
                return ("proto", proto)
            tok = self.take()
        if proto == "ether" and tok == "broadcast":
            return ("ether", "dst", b"\xff" * 6)
        direction = None
        if tok in ("src", "dst"):
            direction, tok = tok, self.take()
        if tok not in ("host", "net", "port", "portrange"):   # a bare address means "host"
            self.i -= 1
            tok = "host"
        value = self.take()
        if proto == "ether":
            return ("ether", direction, mac(value))
        if tok == "host":
            return ("host", direction, ipv4(value), proto)
        if tok == "net":
            addr, _, bits = value.partition("/")
            bits = int(bits or 24)
            mask = (0xFFFFFFFF << (32 - bits)) & 0xFFFFFFFF
            return ("net", direction, ipv4(addr) & mask, mask, proto)
        low, _, high = value.partition("-") if tok == "portrange" else (value, "", value)
        return ("port", direction, number(low), number(high), proto)

    def comparison(self, proto):         # tcp[13] & 2 != 0
        self.take("[")
        where = self.take()
        offset, _, size = where.partition(":")
        self.take("]")
        mask = None
        if self.peek() == "&":
            self.take()
            mask = number(self.take())
        op = self.take()
        if op not in ("=", "==", "!=", "<", "<=", ">", ">="):
            raise SyntaxError(f"expected a comparison like = or !=, got {op!r}")
        return ("cmp", proto, number(offset), int(size or 1), mask, "=" if op == "==" else op, number(self.take()))
# --8<-- [end:parse]


# ---------------------------------------------------------------- compiling to a BPF-style program

class Label:
    at = None


class Assembler:
    """Instructions are [op, argument, jump-if-true, jump-if-false]. Jumps name Labels until the end,
    when they become instruction numbers. BPF can only jump forwards, which is all we ever need."""

    def __init__(self):
        self.code = []

    def emit(self, op, arg=None, jt=None, jf=None):
        self.code.append([op, arg, jt, jf])

    def place(self, label):
        label.at = len(self.code)

    def finish(self):
        for ins in self.code:
            for j in (2, 3):
                if isinstance(ins[j], Label):
                    ins[j] = ins[j].at
        return self.code


# --8<-- [start:compile]
def compile_filter(text):
    asm, yes, no = Assembler(), Label(), Label()
    if text.strip():
        gen(asm, Parser(text).parse(), yes, no)
    asm.place(yes)
    asm.emit("ret", ACCEPT)
    asm.place(no)
    asm.emit("ret", REJECT)
    return asm.finish()


def gen(asm, node, yes, no):
    """Emit code that ends up at `yes` if node is true for this packet, and at `no` if not."""
    kind = node[0]
    if kind == "and":                            # both: if the left fails, the answer is no
        middle = Label()
        gen(asm, node[1], middle, no)
        asm.place(middle)
        gen(asm, node[2], yes, no)
    elif kind == "or":                           # either: if the left passes, the answer is yes
        middle = Label()
        gen(asm, node[1], yes, middle)
        asm.place(middle)
        gen(asm, node[2], yes, no)
    elif kind == "not":
        gen(asm, node[1], no, yes)               # just swap the exits!
    elif kind == "proto":
        name = node[1]
        asm.emit("ldh", 12)                      # the frame's "what's inside" field
        if name in PROTOS:
            asm.emit("jeq", 0x0800, None, no)
            asm.emit("ldb", 23)                  # the IP header's "what's inside" field
            asm.emit("jeq", PROTOS[name], yes, no)
        else:
            asm.emit("jeq", {"ip": 0x0800, "arp": 0x0806, "ip6": 0x86DD, "ether": 0x0800}[name], yes, no)
    elif kind in ("host", "net"):
        gen_address(asm, node, yes, no)
    elif kind == "port":
        gen_port(asm, node, yes, no)
    elif kind == "ether":
        _, direction, addr = node
        first, last = struct.unpack("!IH", addr)
        spots = {"src": [6], "dst": [0], None: [6, 0]}[direction]
        for n, offset in enumerate(spots):
            miss = no if n == len(spots) - 1 else Label()
            asm.emit("ld", offset)
            asm.emit("jeq", first, None, miss)
            asm.emit("ldh", offset + 4)
            asm.emit("jeq", last, yes, miss)
            if miss is not no:
                asm.place(miss)
    elif kind == "multicast":
        asm.emit("ldb", 0)
        asm.emit("jset", 1, yes, no)             # the lowest bit of the first byte means "a group"
    elif kind == "len":
        asm.emit("ld", "len")
        if node[1] == "greater":
            asm.emit("jge", node[2], yes, no)
        else:
            asm.emit("jgt", node[2], no, yes)
    elif kind == "cmp":
        gen_compare(asm, node, yes, no)
# --8<-- [end:compile]


# --8<-- [start:port]
def ipv4_header(asm, protos, no):
    """Check it's IPv4 carrying one of `protos`, and not a fragment; then point X at the next header."""
    asm.emit("ldh", 12)
    asm.emit("jeq", 0x0800, None, no)
    if protos:
        asm.emit("ldb", 23)
        found = Label()
        for n, p in enumerate(protos):
            last = n == len(protos) - 1
            asm.emit("jeq", p, None if last else found, no if last else None)
        asm.place(found)
    asm.emit("ldh", 20)
    asm.emit("jset", 0x1FFF, no, None)          # a later fragment has no ports in it (Chapter 20)
    asm.emit("ldxb", 14)                         # X = the IP header's length, 4 × its low 4 bits


def gen_port(asm, node, yes, no):
    _, direction, low, high, proto = node
    ipv4_header(asm, [PROTOS[proto]] if proto else [6, 17], no)
    spots = {"src": [14], "dst": [16], None: [14, 16]}[direction]
    for n, offset in enumerate(spots):
        miss = no if n == len(spots) - 1 else Label()
        asm.emit("ldh", ("x", offset))           # the port, counted from the start of the TCP/UDP header
        if low == high:
            asm.emit("jeq", low, yes, miss)
        else:
            asm.emit("jge", low, None, miss)
            asm.emit("jgt", high, miss, yes)
        if miss is not no:
            asm.place(miss)
# --8<-- [end:port]


def gen_address(asm, node, yes, no):
    kind, direction, value = node[0], node[1], node[2]
    mask = node[3] if kind == "net" else None
    proto = node[-1]
    places = []                                  # (ethertype, where the source address is, where the destination is)
    if proto in (None, "ip"):
        places.append((0x0800, 26, 30))
    if proto in (None, "arp"):
        places.append((0x0806, 28, 38))
    asm.emit("ldh", 12)
    for n, (ethertype, src, dst) in enumerate(places):
        other = no if n == len(places) - 1 else Label()
        asm.emit("jeq", ethertype, None, other)
        spots = {"src": [src], "dst": [dst], None: [src, dst]}[direction]
        for m, offset in enumerate(spots):
            miss = other if m == len(spots) - 1 else None
            asm.emit("ld", offset)
            if mask is not None:
                asm.emit("and", mask)
            asm.emit("jeq", value, yes, miss)
        if other is not no:
            asm.place(other)                     # A still holds the ethertype here


def gen_compare(asm, node, yes, no):
    _, proto, offset, size, mask, op, value = node
    load = {1: "ldb", 2: "ldh", 4: "ld"}[size]
    if proto == "ether":
        asm.emit(load, offset)
    elif proto == "ip":
        asm.emit("ldh", 12)
        asm.emit("jeq", 0x0800, None, no)
        asm.emit(load, 14 + offset)
    else:
        ipv4_header(asm, [PROTOS[proto]], no)
        asm.emit(load, ("x", 14 + offset))
    if mask is not None and op == "!=" and value == 0:
        asm.emit("jset", mask, yes, no)          # "any of these bits set?" is one instruction
        return
    if mask is not None:
        asm.emit("and", mask)
    jump = {"=": ("jeq", yes, no), "!=": ("jeq", no, yes), ">": ("jgt", yes, no),
            ">=": ("jge", yes, no), "<": ("jge", no, yes), "<=": ("jgt", no, yes)}[op]
    asm.emit(jump[0], value, jump[1], jump[2])


# ---------------------------------------------------------------- running the program

# --8<-- [start:run]
def run(program, pkt, trace=None):
    """The virtual machine: one accumulator (A), one index register (X), and a program counter."""
    A = X = pc = 0
    while True:
        op, arg, jt, jf = program[pc]
        if trace is not None:
            trace.append((pc, A, X))
        if op == "ret":
            return arg
        if op in ("ldb", "ldh", "ld", "ldxb"):
            if arg == "len":
                A = len(pkt)
            else:
                where = X + arg[1] if isinstance(arg, tuple) else arg
                size = {"ldb": 1, "ldh": 2, "ld": 4, "ldxb": 1}[op]
                if where + size > len(pkt):
                    return REJECT                # reading past the end of the packet: no match
                value = int.from_bytes(pkt[where:where + size], "big")
                if op == "ldxb":
                    X = 4 * (value & 0xF)
                else:
                    A = value
            pc += 1
        elif op == "and":
            A &= arg
            pc += 1
        else:                                    # a conditional jump
            ok = {"jeq": A == arg, "jgt": A > arg, "jge": A >= arg, "jset": A & arg != 0}[op]
            target = jt if ok else jf
            pc = pc + 1 if target is None else target
# --8<-- [end:run]


def show(program):
    lines = []
    for n, (op, arg, jt, jf) in enumerate(program):
        if op == "ldxb":
            text = f"4*([{arg}]&0xf)"
        elif arg == "len":
            text = "#pktlen"
        elif op in ("ldb", "ldh", "ld"):
            text = f"[x + {arg[1]}]" if isinstance(arg, tuple) else f"[{arg}]"
        else:
            text = f"#{arg}" if op == "ret" else f"#0x{arg:x}"
        line = f"({n:03d}) {op:<8} {text}"
        if op.startswith("j"):
            line = f"{line:<32}jt {n + 1 if jt is None else jt}\tjf {n + 1 if jf is None else jf}"
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------- one line per packet, tcpdump style

def ip4(b):
    return ".".join(map(str, b))


def macstr(b):
    return ":".join(f"{x:02x}" for x in b)


def dns_name(msg, i):
    parts = []
    while i < len(msg) and msg[i]:
        if msg[i] & 0xC0 == 0xC0:
            parts.append(dns_name(msg, struct.unpack("!H", msg[i:i + 2])[0] & 0x3FFF)[0])
            return ".".join(parts), i + 2
        parts.append(msg[i + 1:i + 1 + msg[i]].decode(errors="replace"))
        i += 1 + msg[i]
    return ".".join(parts), i + 1


def summary(pkt, verbose=False):
    kind = struct.unpack("!H", pkt[12:14])[0]
    head = f"{macstr(pkt[6:12])} > {macstr(pkt[0:6])}, " if verbose else ""
    if kind == 0x0806:
        op, sha, spa, tha, tpa = struct.unpack("!6xH6s4s6s4s", pkt[14:42])
        if op == 1:
            return f"{head}ARP, Request who-has {ip4(tpa)} tell {ip4(spa)}"
        return f"{head}ARP, Reply {ip4(spa)} is-at {macstr(sha)}"
    if kind == 0x86DD:
        return f"{head}IP6 (minidump doesn't look inside IPv6; see Chapter 25)"
    if kind != 0x0800:
        return f"{head}ethertype 0x{kind:04x}"
    ip = pkt[14:]
    hlen, total, ttl, proto = (ip[0] & 15) * 4, struct.unpack("!H", ip[2:4])[0], ip[8], ip[9]
    src, dst = ip4(ip[12:16]), ip4(ip[16:20])
    extra = f"(ttl {ttl}, id {struct.unpack('!H', ip[4:6])[0]}, length {total}) " if verbose else ""
    body = ip[hlen:total]
    if proto == 1:
        kinds = {0: "echo reply", 8: "echo request", 3: "unreachable", 11: "time exceeded in-transit"}
        what = kinds.get(body[0], f"type {body[0]}")
        if body[0] in (0, 8):
            ident, seq = struct.unpack("!HH", body[4:8])
            what += f", id {ident}, seq {seq}"
        return f"{head}IP {extra}{src} > {dst}: ICMP {what}, length {len(body)}"
    sport, dport = struct.unpack("!HH", body[:4])
    ends = f"{src}.{sport} > {dst}.{dport}"
    if proto == 17:
        data = body[8:]
        if 53 in (sport, dport) and len(data) > 12:
            qid, flags, _, an = struct.unpack("!HHHH", data[:8])
            name, _ = dns_name(data, 12)
            if flags & 0x8000:
                return f"{head}IP {extra}{ends}: {qid} answer for {name}, {an} record(s) ({len(data)})"
            return f"{head}IP {extra}{ends}: {qid}+ question: {name}? ({len(data)})"
        return f"{head}IP {extra}{ends}: UDP, length {len(data)}"
    if proto == 6:
        seq, ack, off, fl, win = struct.unpack("!IIBBH", body[4:16])
        flags = "".join(c for bit, c in ((2, "S"), (1, "F"), (4, "R"), (8, "P")) if fl & bit) + ("." if fl & 16 else "")
        data = body[(off >> 4) * 4:]
        line = f"{head}IP {extra}{ends}: Flags [{flags}], seq {seq}" + (f", ack {ack}" if fl & 16 else "") + \
            f", win {win}, length {len(data)}"
        first = data.split(b"\r\n", 1)[0]
        if first[:4] in (b"GET ", b"POST", b"HEAD", b"HTTP"):
            line += ": HTTP: " + first.decode(errors="replace")
        return line
    return f"{head}IP {extra}{src} > {dst}: protocol {proto}"


def stamp(secs, usecs):
    return time.strftime("%H:%M:%S", time.localtime(secs)) + f".{usecs:06d}"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file", nargs="?", help="a .pcap file, or - to read from a pipe")
    p.add_argument("filter", nargs="*", help="a capture filter, like tcpdump's")
    p.add_argument("-d", metavar="FILTER", help="just show the compiled program")
    p.add_argument("-v", action="store_true", help="show card addresses and IP header details")
    p.add_argument("--trace", type=int, metavar="N", help="show packet N's trip through the program")
    args = p.parse_args()
    try:
        if args.d is not None:
            print(show(compile_filter(args.d)))
            return
        if not args.file:
            p.print_help()
            return
        program = compile_filter(" ".join(args.filter))
    except SyntaxError as e:
        raise SystemExit(f"filter problem: {e}")
    source = sys.stdin.buffer if args.file == "-" else open(args.file, "rb")
    shown = total = 0
    try:
        for number, (secs, usecs, pkt) in enumerate(read_pcap(source), start=1):
            total += 1
            trace = [] if args.trace == number else None
            if run(program, pkt, trace):
                shown += 1
                print(f"{number:>3} {stamp(secs, usecs)} {summary(pkt, args.v)}", flush=True)
            if trace is not None:
                listing = show(program).splitlines()
                print(f"\npacket {number} through the program (A and X are the registers after each step):")
                for step, (pc, _, _) in enumerate(trace):
                    _, A, X = trace[min(step + 1, len(trace) - 1)]
                    print(f"   A={A:<#10x} X={X:<3} {listing[pc]}")
                print(f"   → {'accepted' if program[trace[-1][0]][1] else 'rejected'}\n")
    except KeyboardInterrupt:
        pass
    print(f"{shown} of {total} packets matched", file=sys.stderr)


if __name__ == "__main__":
    main()
