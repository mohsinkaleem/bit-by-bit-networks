#!/usr/bin/env python3
"""Chapter 35 lab: a WireGuard peer in plain Python, that talks to the real WireGuard in Linux.

    python3 wg_peer.py selftest                         two Python peers, a handshake and a ping, on this computer
    python3 wg_peer.py key                              make (or show) this peer's key pair, in wg_peer.key
    python3 wg_peer.py ping 192.168.1.4:51820 SERVERKEY  handshake with a real WireGuard server, and ping through it

For `ping`, the server needs this peer's public key, and 10.35.0.2/32 in its AllowedIPs; the server
itself should be 10.35.0.1 inside the tunnel. wg_box.sh sets that up on Linux.

WireGuard's handshake is a "Noise IK" handshake: X25519 (Chapter 31) four times over, BLAKE2s for
hashing, and ChaCha20-Poly1305 (Chapter 31) for sealing, everything else is bookkeeping.
"""
import base64
import hashlib
import hmac
import os
import socket
import struct
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ch31"))
from chacha import open_ as chacha_open, seal as chacha_seal   # noqa: E402  (Chapter 31)
from x25519 import keypair, x25519                             # noqa: E402

CONSTRUCTION = b"Noise_IKpsk2_25519_ChaChaPoly_BLAKE2s"
IDENTIFIER = b"WireGuard v1 zx2c4 Jason@zx2c4.com"
LABEL_MAC1 = b"mac1----"
BASE = (9).to_bytes(32, "little")


# ---------------------------------------------------------------- the building blocks

# --8<-- [start:prims]
def HASH(*parts):
    return hashlib.blake2s(b"".join(parts)).digest()


def MAC(key, data):
    return hashlib.blake2s(data, key=key, digest_size=16).digest()


def HMAC(key, data):
    return hmac.new(key, data, hashlib.blake2s).digest()


def KDF(key, data, n):
    """Derive n new 32-byte keys from a chaining key and some input (HKDF, with BLAKE2s)."""
    t0 = HMAC(key, data)
    out, prev = [], b""
    for i in range(1, n + 1):
        prev = HMAC(t0, prev + bytes([i]))
        out.append(prev)
    return out


def AEAD(key, counter, plaintext, aad):
    return chacha_seal(key, b"\0" * 4 + struct.pack("<Q", counter), plaintext, aad)


def AEAD_open(key, counter, sealed, aad):
    return chacha_open(key, b"\0" * 4 + struct.pack("<Q", counter), sealed, aad)


def DH(private, public):
    return x25519(private, public)


def tai64n():
    now = time.time_ns()
    return struct.pack(">QI", 0x400000000000000A + now // 10**9, now % 10**9)
# --8<-- [end:prims]


def b64(key):
    return base64.b64encode(key).decode()


# ---------------------------------------------------------------- the handshake

class Peer:
    def __init__(self, private=None):
        self.private = private or os.urandom(32)
        self.public = x25519(self.private, BASE)
        self.index = int.from_bytes(os.urandom(4), "little")        # our name for this session
        self.send_counter = 0

    # --8<-- [start:initiate]
    def initiation(self, their_public):
        """Message 1 (148 bytes): our temporary key in the clear; our permanent key and the time, sealed."""
        self.their_public = their_public
        C = HASH(CONSTRUCTION)
        H = HASH(C, IDENTIFIER)
        H = HASH(H, their_public)
        self.e_private, e_public = keypair()                        # a fresh key pair, just for this handshake
        C = KDF(C, e_public, 1)[0]
        H = HASH(H, e_public)
        C, k = KDF(C, DH(self.e_private, their_public), 2)          # 1st exchange: our temporary × their permanent
        static = AEAD(k, 0, self.public, H)
        H = HASH(H, static)
        C, k = KDF(C, DH(self.private, their_public), 2)            # 2nd: our permanent × their permanent
        stamp = AEAD(k, 0, tai64n(), H)                             # stops old messages being replayed
        H = HASH(H, stamp)
        msg = struct.pack("<II", 1, self.index) + e_public + static + stamp
        msg += MAC(HASH(LABEL_MAC1, their_public), msg)             # mac1: a cheap check, before any real work
        self.C, self.H = C, H
        return msg + bytes(16)                                       # mac2: only used when the server is under attack
    # --8<-- [end:initiate]

    # --8<-- [start:response]
    def consume_response(self, msg):
        """Message 2 (92 bytes): their temporary key, and an empty box that only opens if they know every key."""
        mtype, their_index, our_index = struct.unpack("<III", msg[:12])
        assert mtype == 2 and our_index == self.index, "not a response to our handshake"
        e_r = msg[12:44]
        C, H = self.C, self.H
        C = KDF(C, e_r, 1)[0]
        H = HASH(H, e_r)
        C = KDF(C, DH(self.e_private, e_r), 1)[0]                   # 3rd: our temporary × their temporary
        C = KDF(C, DH(self.private, e_r), 1)[0]                     # 4th: our permanent × their temporary
        C, tau, k = KDF(C, bytes(32), 3)                             # (no pre-shared key: 32 zeros)
        H = HASH(H, tau)
        AEAD_open(k, 0, msg[44:60], H)                               # raises an error if anything is wrong
        self.send_key, self.recv_key = KDF(C, b"", 2)               # two transport keys, one per direction
        self.their_index = their_index
        del self.e_private                                           # forward secrecy: forget the temporary key
    # --8<-- [end:response]

    def consume_initiation(self, msg):
        """The responder's side of message 1 (used by selftest, and by real servers)."""
        C = HASH(CONSTRUCTION)
        H = HASH(C, IDENTIFIER)
        H = HASH(H, self.public)
        _, their_index = struct.unpack("<II", msg[:8])
        e_i = msg[8:40]
        C = KDF(C, e_i, 1)[0]
        H = HASH(H, e_i)
        C, k = KDF(C, DH(self.private, e_i), 2)
        their_public = AEAD_open(k, 0, msg[40:88], H)
        H = HASH(H, msg[40:88])
        C, k = KDF(C, DH(self.private, their_public), 2)
        AEAD_open(k, 0, msg[88:116], H)
        H = HASH(H, msg[88:116])
        self.C, self.H, self.e_i, self.their_public, self.their_index = C, H, e_i, their_public, their_index

    def response(self):
        C, H = self.C, self.H
        e_private, e_public = keypair()
        C = KDF(C, e_public, 1)[0]
        H = HASH(H, e_public)
        C = KDF(C, DH(e_private, self.e_i), 1)[0]
        C = KDF(C, DH(e_private, self.their_public), 1)[0]
        C, tau, k = KDF(C, bytes(32), 3)
        H = HASH(H, tau)
        empty = AEAD(k, 0, b"", H)
        msg = struct.pack("<III", 2, self.index, self.their_index) + e_public + empty
        msg += MAC(HASH(LABEL_MAC1, self.their_public), msg)
        self.recv_key, self.send_key = KDF(C, b"", 2)                # the responder's are the other way round
        return msg + bytes(16)

    # --8<-- [start:transport]
    def seal(self, packet):
        """Message 4: an IP packet, padded to a multiple of 16 bytes, sealed with a counter as the nonce."""
        padded = packet + bytes(-len(packet) % 16)
        msg = struct.pack("<IIQ", 4, self.their_index, self.send_counter) + AEAD(self.send_key, self.send_counter, padded, b"")
        self.send_counter += 1
        return msg

    def open(self, msg):
        _, _, counter = struct.unpack("<IIQ", msg[:16])
        return counter, AEAD_open(self.recv_key, counter, msg[16:], b"")
    # --8<-- [end:transport]


# ---------------------------------------------------------------- IP and ICMP, by hand (Chapters 20 and 21)

def checksum(data):
    data += bytes(len(data) % 2)
    s = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF


def ip_packet(src, dst, proto, payload, ttl=64):
    header = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(payload), 0x2B1D, 0, ttl, proto, 0,
                         socket.inet_aton(src), socket.inet_aton(dst))
    header = header[:10] + struct.pack("!H", checksum(header)) + header[12:]
    return header + payload


def echo(kind, ident, seq, data):
    body = struct.pack("!BBHHH", kind, 0, 0, ident, seq) + data
    return body[:2] + struct.pack("!H", checksum(body)) + body[4:]


def describe(packet):
    length, ttl, proto = struct.unpack("!H", packet[2:4])[0], packet[8], packet[9]
    src, dst = socket.inet_ntoa(packet[12:16]), socket.inet_ntoa(packet[16:20])
    if proto == 1:
        kind = {0: "echo reply", 8: "echo request"}.get(packet[20], f"type {packet[20]}")
        return f"ICMP {kind} {src} → {dst}, ttl {ttl}, {length} bytes: {packet[28:length]!r}"
    return f"IP protocol {proto} {src} → {dst}, {length} bytes"


# ---------------------------------------------------------------- talking to a real server

def load_key():
    path = HERE / "wg_peer.key"
    if not path.exists():
        path.write_text(b64(os.urandom(32)) + "\n")
        path.chmod(0o600)
    return base64.b64decode(path.read_text().strip())


def ping(endpoint, server_key, count=3):
    host, _, port = endpoint.rpartition(":")
    addr = (host, int(port))
    me = Peer(load_key())
    their_public = base64.b64decode(server_key)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3)
    print(f"our public key: {b64(me.public)}  (the server must know it)\n")
    t0 = time.monotonic()
    init = me.initiation(their_public)
    sock.sendto(init, addr)
    print(f"→ handshake initiation  {len(init):>4} bytes  our temporary key; our permanent key and the time, sealed; mac1")
    try:
        resp, _ = sock.recvfrom(2048)
    except socket.timeout:
        raise SystemExit("no answer. (WireGuard stays silent unless it knows our key: is it on the server's peer list?)")
    me.consume_response(resp)
    print(f"← handshake response    {len(resp):>4} bytes  its temporary key, and an empty sealed box that opened: it knows all the keys")
    print(f"   handshake done after {(time.monotonic() - t0) * 1000:.1f} ms. Two transport keys: send {me.send_key.hex()[:16]}…, receive {me.recv_key.hex()[:16]}…\n")
    for seq in range(1, count + 1):
        inner = ip_packet("10.35.0.2", "10.35.0.1", 1, echo(8, 0xB17E, seq, b"hello Grandpa " + str(seq).encode()))
        msg = me.seal(inner)
        t1 = time.monotonic()
        sock.sendto(msg, addr)
        print(f"→ transport data #{me.send_counter - 1}      {len(msg):>4} bytes  sealed inside: {describe(inner)}")
        data, _ = sock.recvfrom(2048)
        counter, packet = me.open(data)
        print(f"← transport data #{counter}      {len(data):>4} bytes  opened: {describe(packet)}   {(time.monotonic() - t1) * 1000:.1f} ms")
        time.sleep(0.5)


def selftest():
    """Both ends in Python, over UDP on this computer: a handshake, then a ping and its reply."""
    server, client = Peer(), Peer()
    s_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s_sock.bind(("127.0.0.1", 0))
    port = s_sock.getsockname()[1]

    def serve():
        msg, addr = s_sock.recvfrom(2048)
        server.consume_initiation(msg)
        print(f"   server: a valid initiation, from the peer whose permanent key is {b64(server.their_public)[:12]}…")
        s_sock.sendto(server.response(), addr)
        msg, addr = s_sock.recvfrom(2048)
        _, packet = server.open(msg)
        ident, seq = struct.unpack("!HH", packet[24:28])
        length = struct.unpack("!H", packet[2:4])[0]                # the IP header says where the padding starts
        reply = ip_packet("10.35.0.1", "10.35.0.2", 1, echo(0, ident, seq, packet[28:length]))
        s_sock.sendto(server.seal(reply), addr)
    threading.Thread(target=serve, daemon=True).start()
    c_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    c_sock.settimeout(3)
    init = client.initiation(server.public)
    c_sock.sendto(init, ("127.0.0.1", port))
    print(f"→ handshake initiation  {len(init)} bytes")
    resp, _ = c_sock.recvfrom(2048)
    client.consume_response(resp)
    print(f"← handshake response    {len(resp)} bytes")
    print(f"   both sides agree on the keys: {client.send_key == server.recv_key and client.recv_key == server.send_key}")
    c_sock.sendto(client.seal(ip_packet("10.35.0.2", "10.35.0.1", 1, echo(8, 7, 1, b"hello"))), ("127.0.0.1", port))
    _, packet = client.open(c_sock.recvfrom(2048)[0])
    print(f"← {describe(packet)}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    if cmd == "key":
        print(f"public key: {b64(x25519(load_key(), BASE))}  (the private key is in wg_peer.key)")
    elif cmd == "ping":
        ping(sys.argv[2], sys.argv[3])
    else:
        selftest()


if __name__ == "__main__":
    main()
