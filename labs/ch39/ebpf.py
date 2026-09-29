#!/usr/bin/env python3
"""Chapter 39 lab: eBPF programs, written one instruction at a time (Linux only, run with sudo).

    sudo python3 ebpf.py count wlan0         count packets and bytes per protocol, inside the kernel, for 10 s
    sudo python3 ebpf.py drop wlan0 [SECS]   drop every ping that arrives, at the earliest possible point (XDP)
    sudo python3 ebpf.py verifier            two unsafe programs, and what the kernel says about them

No compiler, no libraries: the programs are assembled by hand below, and handed to the kernel with
the bpf() system call, which checks they're safe (the verifier), compiles them to machine code,
and runs them for every packet. When this program exits, they're removed.
"""
import ctypes
import os
import platform
import socket
import struct
import sys
import time

libc = ctypes.CDLL(None, use_errno=True)
SYS_BPF = {"aarch64": 280, "x86_64": 321, "armv7l": 386}[platform.machine()]
MAP_CREATE, MAP_LOOKUP, PROG_LOAD, OBJ_INFO, LINK_CREATE = 0, 1, 5, 15, 28
SOCKET_FILTER, XDP = 1, 6                          # program types
XDP_ATTACH = 37


def bpf(cmd, attr):
    buf = ctypes.create_string_buffer(bytes(attr), 128)
    fd = libc.syscall(SYS_BPF, cmd, buf, 128)
    if fd < 0:
        raise OSError(ctypes.get_errno(), os.strerror(ctypes.get_errno()))
    return fd, buf


# --8<-- [start:asm]
# One eBPF instruction is 8 bytes: an opcode, two registers (4 bits each), a 16-bit jump offset,
# and a 32-bit number. There are eleven registers: r0 (results), r1–r5 (arguments), r6–r9, and
# r10, which points at the program's 512 bytes of stack. These helpers are a tiny assembler.
def insn(op, dst=0, src=0, off=0, imm=0):
    return struct.pack("<BBhi", op, src << 4 | dst, off, imm)

def mov(dst, src):        return insn(0xBF, dst, src)               # dst = src
def movi(dst, imm):       return insn(0xB7, dst, imm=imm)           # dst = number
def addi(dst, imm):       return insn(0x07, dst, imm=imm)           # dst += number
def load(size, dst, src, off):                                      # dst = *(size *)(src + off)
    return insn({1: 0x71, 2: 0x69, 4: 0x61}[size], dst, src, off)
def store_imm(dst, off, imm): return insn(0x62, dst, off=off, imm=imm)   # *(u32 *)(dst + off) = number
def store(dst, off, src): return insn(0x63, dst, src, off)          # *(u32 *)(dst + off) = src
def atomic_add(dst, off, src): return insn(0xDB, dst, src, off)     # *(u64 *)(dst + off) += src, safely
def packet_byte(off):     return insn(0x30, imm=off)                # r0 = the packet's byte at off
def packet_half(off):     return insn(0x28, imm=off)                # r0 = the 16 bits at off
def jne(dst, imm, skip):  return insn(0x55, dst, off=skip, imm=imm)  # if dst != number: skip ahead
def jeq(dst, imm, skip):  return insn(0x15, dst, off=skip, imm=imm)  # if dst == number: skip ahead
def jgt(dst, src, skip):  return insn(0x2D, dst, src, off=skip)     # if dst > src: skip ahead
def call(helper):         return insn(0x85, imm=helper)             # call a kernel helper function
def exit_():              return insn(0x95)                         # return r0
def map_fd(dst, fd):      return insn(0x18, dst, 1, 0, fd) + insn(0)  # dst = the map (16 bytes)
LOOKUP = 1                # helper 1: bpf_map_lookup_elem(map, &key) returns a pointer, or 0
# --8<-- [end:asm]


def new_map(entries, value_size):                  # an array of counters, shared with this program
    fd, _ = bpf(MAP_CREATE, struct.pack("<IIIII", 2, 4, value_size, entries, 0))
    return fd


def read_map(fd, key, value_size):
    k, v = ctypes.c_uint32(key), ctypes.create_string_buffer(value_size)
    bpf(MAP_LOOKUP, struct.pack("<IIQQQ", fd, 0, ctypes.addressof(k), ctypes.addressof(v), 0))
    return struct.unpack(f"<{value_size // 8}Q", v.raw)


def load_program(kind, code, name):
    insns = ctypes.create_string_buffer(code, len(code))
    lic = ctypes.create_string_buffer(b"GPL")
    log = ctypes.create_string_buffer(65536)
    attr = struct.pack("<IIQQIIQII16sII", kind, len(code) // 8, ctypes.addressof(insns), ctypes.addressof(lic),
                       1, len(log), ctypes.addressof(log), 0, 0, name.encode(), 0, XDP_ATTACH if kind == XDP else 0)
    try:
        fd, _ = bpf(PROG_LOAD, attr)
    except OSError as e:
        raise PermissionError(f"the verifier said no ({e.strerror}):\n" + log.value.decode().strip()) from None
    info = ctypes.create_string_buffer(64)
    bpf(OBJ_INFO, struct.pack("<IIQ", fd, 64, ctypes.addressof(info)))
    pid, tag, jited, xlated = struct.unpack_from("<I8sII", info.raw, 4)
    arch = platform.machine()
    print(f"loaded “{name}”: {len(code) // 8} instructions, passed the verifier, "
          f"compiled to {jited} bytes of {arch} machine code (program id {pid})")
    return fd


# --8<-- [start:count]
def counter_program(counts):
    """For each packet: if it's IPv4, add 1 packet and its length to counts[protocol number]."""
    return b"".join([
        mov(6, 1),                    # r6 = the packet (the kernel passes it in r1)
        packet_half(12),              # r0 = bytes 12–13, the EtherType (Chapter 18)
        jne(0, 0x0800, 12),           # not IPv4? skip to the end
        packet_byte(23),              # r0 = byte 23, the IP header's protocol field (Chapter 20)
        store(10, -4, 0),             # put it on the stack: that's our key
        map_fd(1, counts),            # r1 = the map
        mov(2, 10), addi(2, -4),      # r2 = a pointer to the key
        call(LOOKUP),                 # r0 = a pointer to counts[protocol], or 0
        jeq(0, 0, 4),                 # 0? (the verifier insists we check) skip to the end
        movi(1, 1), atomic_add(0, 0, 1),         # packets += 1
        load(4, 1, 6, 0), atomic_add(0, 8, 1),   # bytes += the packet's length
        movi(0, 0),                   # return 0: keep none of it for the socket; we only count
        exit_(),
    ])
# --8<-- [end:count]


# --8<-- [start:drop]
def drop_program(counts):
    """XDP: runs on each arriving frame before Linux has even looked at it. Drop pings."""
    def count(key):                   # counts[key] += 1
        return b"".join([store_imm(10, -4, key), map_fd(1, counts), mov(2, 10), addi(2, -4),
                         call(LOOKUP), jeq(0, 0, 2), movi(1, 1), atomic_add(0, 0, 1)])
    verdict_drop = count(0) + movi(0, 1) + exit_()          # XDP_DROP = 1
    verdict_pass = count(1) + movi(0, 2) + exit_()          # XDP_PASS = 2
    skip = len(verdict_drop) // 8
    checks = [
        load(4, 2, 1, 0),             # r2 = where the frame starts
        load(4, 3, 1, 4),             # r3 = where it ends
        mov(4, 2), addi(4, 35),       # r4 = r2 + 35: we'll read up to byte 34
        jgt(4, 3, 6 + skip),          # frame shorter than that? pass it (and the verifier knows we checked)
        load(2, 5, 2, 12),            # EtherType, as the bytes lie in memory: 08 00 read backwards
        jne(5, 0x0008, 4 + skip),     # not IPv4? pass
        load(1, 5, 2, 23),            # the IP protocol field
        jne(5, 1, 2 + skip),          # not ICMP? pass
        load(1, 5, 2, 34),            # the ICMP type (assuming a 20-byte IP header)
        jne(5, 8, skip),          # not an echo request? pass
    ]
    return b"".join(checks) + verdict_drop + verdict_pass
# --8<-- [end:drop]


PROTOCOLS = {1: "ICMP", 6: "TCP", 17: "UDP", 58: "ICMPv6"}


def count(ifname, seconds=10):
    counts = new_map(256, 16)
    prog = load_program(SOCKET_FILTER, counter_program(counts), "count")
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))   # every frame…
    s.bind((ifname, 0))                                                          # …on this interface
    s.setsockopt(socket.SOL_SOCKET, 50, prog)                                    # SO_ATTACH_BPF
    print(f"counting IPv4 packets on {ifname}, in the kernel, for {seconds} s:")
    for t in range(1, seconds + 1):
        time.sleep(1)
        parts = []
        for num, name in PROTOCOLS.items():
            pkts, octets = read_map(counts, num, 16)
            if pkts:
                parts.append(f"{name} {pkts} ({octets / 1000:.1f} kB)")
        print(f"  {t:2d} s   " + ("   ".join(parts) or "nothing yet"))


def drop(ifname, seconds=30):
    counts = new_map(2, 8)
    prog = load_program(XDP, drop_program(counts), "drop_pings")
    link, _ = bpf(LINK_CREATE, struct.pack("<IIII", prog, socket.if_nametoindex(ifname), XDP_ATTACH, 0))
    print(f"attached to {ifname}: pings arriving there are dropped, for {seconds} s")
    for t in range(1, seconds + 1):
        time.sleep(1)
        if t % 5 == 0 or t == seconds:
            print(f"  {t:2d} s   pings dropped: {read_map(counts, 0, 8)[0]:4d}    "
                  f"everything else, let through: {read_map(counts, 1, 8)[0]}")
    os.close(link)                                  # closing the link removes the program
    print("detached")


# --8<-- [start:verifier]
def verifier():
    counts = new_map(2, 8)
    unchecked = counter_program(counts).replace(jeq(0, 0, 4), movi(3, 0))         # "forget" the null check
    no_bounds = drop_program(counts)[:32] + drop_program(counts)[40:]            # "forget" the length check
    for name, kind, code in (("no_null_check", SOCKET_FILTER, unchecked), ("no_bounds_check", XDP, no_bounds)):
        try:
            load_program(kind, code, name)
        except PermissionError as e:
            lines = str(e).splitlines()
            print(f"“{name}”: {lines[0]}")
            print("   …", lines[-3], "\n   …", lines[-2] if "processed" in lines[-1] else lines[-1])
# --8<-- [end:verifier]


if __name__ == "__main__":
    if os.geteuid() != 0 or len(sys.argv) < 2:
        sys.exit(__doc__)
    mode = sys.argv[1]
    if mode == "count":
        count(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10)
    elif mode == "drop":
        drop(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 30)
    elif mode == "verifier":
        verifier()
