#!/usr/bin/env python3
"""Chapter 33 lab: QUIC and HTTP/3 from scratch, over a real UDP socket.

    python3 quic.py versions www.google.com        which QUIC versions does a server speak?
    python3 quic.py get www.google.com             a QUIC handshake, then an HTTP/3 request for /
    python3 quic.py get cloudflare.com / -v        …with every frame of every packet
    python3 quic.py --test                         check the packet protection against RFC 9001's examples

It builds on Chapter 32's TLS 1.3 client (the same handshake messages, carried in QUIC's CRYPTO
frames instead of TLS records), Chapter 31's X25519 and ChaCha20-Poly1305, this folder's
AES-GCM (for QUIC's first packets) and QPACK (HTTP/3's header compression).
It handles one request on a well-behaved network: lost packets are simply sent again.
"""
import argparse
import hashlib
import hmac
import os
import socket
import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "ch31"), str(HERE.parent / "ch32")]
import aesgcm                                                   # noqa: E402  (this folder)
import certs                                                    # noqa: E402  (Chapter 32)
import chacha                                                   # noqa: E402  (Chapter 31)
import hpack                                                    # noqa: E402  (this folder)
from tls13 import derive_secret, ext, handshake_messages, hkdf_expand_label, hkdf_extract, parse_extensions, vec  # noqa: E402
from x25519 import keypair, x25519                              # noqa: E402

INITIAL_SALT = bytes.fromhex("38762cf7f55934b34d179ae6a4c80cadccbb7f0a")    # RFC 9001: the same for everyone
INITIAL, HANDSHAKE, APP = "Initial", "Handshake", "1-RTT"
LONG_TYPES = {0: INITIAL, 1: "0-RTT", 2: HANDSHAKE, 3: "Retry"}
TP_NAMES = {0x00: "original_destination_connection_id", 0x01: "max_idle_timeout", 0x02: "stateless_reset_token",
            0x03: "max_udp_payload_size", 0x04: "initial_max_data", 0x05: "initial_max_stream_data_bidi_local",
            0x06: "initial_max_stream_data_bidi_remote", 0x07: "initial_max_stream_data_uni",
            0x08: "initial_max_streams_bidi", 0x09: "initial_max_streams_uni", 0x0A: "ack_delay_exponent",
            0x0B: "max_ack_delay", 0x0C: "disable_active_migration", 0x0E: "active_connection_id_limit",
            0x0F: "initial_source_connection_id", 0x10: "retry_source_connection_id", 0x20: "max_datagram_frame_size"}
H3_SETTINGS = {0x01: "QPACK_MAX_TABLE_CAPACITY", 0x06: "MAX_FIELD_SECTION_SIZE", 0x07: "QPACK_BLOCKED_STREAMS",
               0x08: "ENABLE_CONNECT_PROTOCOL", 0x33: "H3_DATAGRAM"}


# ---------------------------------------------------------------- variable-length integers

# --8<-- [start:varint]
def varint(n):
    """QUIC's numbers: the top two bits of the first byte say whether it's 1, 2, 4 or 8 bytes long."""
    for size, top in ((1, 0), (2, 1), (4, 2), (8, 3)):
        if n < 1 << (8 * size - 2):
            return ((top << (8 * size - 2)) | n).to_bytes(size, "big")
    raise ValueError("too big")


def read_varint(data, i):
    size = 1 << (data[i] >> 6)
    return int.from_bytes(bytes([data[i] & 0x3F]) + data[i + 1:i + size], "big"), i + size
# --8<-- [end:varint]


# ---------------------------------------------------------------- packet protection

# --8<-- [start:keys]
class Keys:
    """One direction's keys for one stage: a key and IV to seal packets, and a key to hide their headers."""
    def __init__(self, secret, aes=False):
        self.aes = aes                                         # Initial packets: AES-128-GCM; later: ChaCha20
        n = 16 if aes else 32
        self.key = hkdf_expand_label(secret, "quic key", b"", n)
        self.iv = hkdf_expand_label(secret, "quic iv", b"", 12)
        self.hp = hkdf_expand_label(secret, "quic hp", b"", n)

    def nonce(self, pn):
        return bytes(a ^ b for a, b in zip(self.iv, pn.to_bytes(12, "big")))

    def seal(self, pn, payload, header):
        return (aesgcm if self.aes else chacha).seal(self.key, self.nonce(pn), payload, aad=header)

    def open(self, pn, sealed, header):
        return (aesgcm.open_ if self.aes else chacha.open_)(self.key, self.nonce(pn), sealed, aad=header)

    def mask(self, sample):
        """Header protection: 5 bytes that hide the packet number and some header bits from the network."""
        if self.aes:
            return aesgcm.aes_ecb(self.hp, sample)[:5]
        return chacha.chacha20(self.hp, int.from_bytes(sample[:4], "little"), sample[4:16], bytes(5))


def initial_keys(dcid):
    """Anyone who sees the first packet can work these out: they only stop accidents and old middleboxes."""
    secret = hkdf_extract(INITIAL_SALT, dcid)
    return (Keys(hkdf_expand_label(secret, "client in", b"", 32), aes=True),
            Keys(hkdf_expand_label(secret, "server in", b"", 32), aes=True))
# --8<-- [end:keys]


# --8<-- [start:protect]
def protect(keys, first, header_rest, pn, payload, long=True):
    """Seal a packet, then hide its packet number (it's only 2 bytes here: first & 3 = 1)."""
    header = bytes([first]) + header_rest + pn.to_bytes(2, "big")
    sealed = keys.seal(pn, payload, header)
    pn_offset = len(header) - 2
    packet = bytearray(header + sealed)
    mask = keys.mask(bytes(packet[pn_offset + 4:pn_offset + 20]))   # a sample of the ciphertext
    packet[0] ^= mask[0] & (0x0F if long else 0x1F)
    for k in range(2):
        packet[pn_offset + k] ^= mask[1 + k]
    return bytes(packet)


def unprotect(keys, data, pn_offset, end, long=True):
    """Undo header protection, then open the payload. Returns (packet number, plaintext, header length)."""
    packet = bytearray(data[:end])
    mask = keys.mask(bytes(packet[pn_offset + 4:pn_offset + 20]))
    packet[0] ^= mask[0] & (0x0F if long else 0x1F)
    pn_len = (packet[0] & 3) + 1
    for k in range(pn_len):
        packet[pn_offset + k] ^= mask[1 + k]
    truncated = int.from_bytes(packet[pn_offset:pn_offset + pn_len], "big")
    header = bytes(packet[:pn_offset + pn_len])
    return truncated, pn_len, header, bytes(packet[pn_offset + pn_len:])
# --8<-- [end:protect]


def full_pn(largest, truncated, pn_len):
    """RFC 9000 A.3: rebuild the full packet number from the last 1-4 bytes, near the largest seen so far."""
    expected, win = largest + 1, 1 << (8 * pn_len)
    candidate = (expected & ~(win - 1)) | truncated
    if candidate <= expected - win // 2 and candidate < (1 << 62) - win:
        return candidate + win
    if candidate > expected + win // 2 and candidate >= win:
        return candidate - win
    return candidate


# ---------------------------------------------------------------- frames

# --8<-- [start:frames]
def parse_frames(data):
    """A packet's payload is a list of frames. Returns [(name, fields)]."""
    out, i = [], 0
    while i < len(data):
        t, i = read_varint(data, i)
        if t == 0x00:
            n = 1
            while i < len(data) and data[i] == 0:
                i, n = i + 1, n + 1
            out.append(("PADDING", {"bytes": n}))
        elif t == 0x01:
            out.append(("PING", {}))
        elif t in (0x02, 0x03):
            largest, i = read_varint(data, i)
            _, i = read_varint(data, i)                         # ack delay
            count, i = read_varint(data, i)
            first, i = read_varint(data, i)
            for _ in range(count):
                _, i = read_varint(data, i)
                _, i = read_varint(data, i)
            if t == 0x03:
                for _ in range(3):
                    _, i = read_varint(data, i)
            out.append(("ACK", {"largest": largest, "first": first}))
        elif t == 0x06:
            off, i = read_varint(data, i)
            n, i = read_varint(data, i)
            out.append(("CRYPTO", {"offset": off, "data": data[i:i + n]}))
            i += n
        elif t == 0x07:
            n, i = read_varint(data, i)
            out.append(("NEW_TOKEN", {"token": data[i:i + n]}))
            i += n
        elif 0x08 <= t <= 0x0F:                                 # STREAM: bits say if offset, length, FIN are there
            sid, i = read_varint(data, i)
            off = 0
            if t & 0x04:
                off, i = read_varint(data, i)
            if t & 0x02:
                n, i = read_varint(data, i)
            else:
                n = len(data) - i
            out.append(("STREAM", {"id": sid, "offset": off, "data": data[i:i + n], "fin": bool(t & 1)}))
            i += n
        elif t in (0x04, 0x05, 0x11, 0x15):                     # RESET_STREAM, STOP_SENDING, MAX_STREAM_DATA, …
            for _ in range(3 if t == 0x04 else 2):
                _, i = read_varint(data, i)
            out.append(({0x04: "RESET_STREAM", 0x05: "STOP_SENDING", 0x11: "MAX_STREAM_DATA",
                         0x15: "STREAM_DATA_BLOCKED"}[t], {}))
        elif t in (0x10, 0x12, 0x13, 0x14, 0x16, 0x17, 0x19):
            v, i = read_varint(data, i)
            out.append(({0x10: "MAX_DATA", 0x12: "MAX_STREAMS", 0x13: "MAX_STREAMS", 0x14: "DATA_BLOCKED",
                         0x16: "STREAMS_BLOCKED", 0x17: "STREAMS_BLOCKED", 0x19: "RETIRE_CONNECTION_ID"}[t], {"value": v}))
        elif t == 0x18:
            seq, i = read_varint(data, i)
            _, i = read_varint(data, i)
            n = data[i]
            out.append(("NEW_CONNECTION_ID", {"seq": seq, "cid": data[i + 1:i + 1 + n]}))
            i += 1 + n + 16                                     # the ID, then a 16-byte reset token
        elif t in (0x1A, 0x1B):
            out.append(("PATH_CHALLENGE" if t == 0x1A else "PATH_RESPONSE", {"data": data[i:i + 8]}))
            i += 8
        elif t in (0x1C, 0x1D):
            code, i = read_varint(data, i)
            if t == 0x1C:
                _, i = read_varint(data, i)
            n, i = read_varint(data, i)
            out.append(("CONNECTION_CLOSE", {"error": code, "reason": data[i:i + n].decode("utf-8", "replace")}))
            i += n
        elif t == 0x1E:
            out.append(("HANDSHAKE_DONE", {}))
        elif t in (0x30, 0x31):
            n = len(data) - i
            if t == 0x31:
                n, i = read_varint(data, i)
            out.append(("DATAGRAM", {}))
            i += n
        else:
            raise ValueError(f"unknown frame type 0x{t:x}")
    return out
# --8<-- [end:frames]


def ack_frame(received):
    """An ACK frame for a set of packet numbers: the largest, then ranges going down, with gaps between."""
    pns = sorted(received, reverse=True)
    ranges, hi = [], pns[0]
    lo = hi
    for pn in pns[1:]:
        if pn == lo - 1:
            lo = pn
        else:
            ranges.append((hi, lo))
            hi = lo = pn
    ranges.append((hi, lo))
    out = varint(0x02) + varint(ranges[0][0]) + varint(0) + varint(len(ranges) - 1) + varint(ranges[0][0] - ranges[0][1])
    for (_, prev_lo), (h, lo) in zip(ranges, ranges[1:]):
        out += varint(prev_lo - h - 2) + varint(h - lo)
    return out


def summary(frames):
    parts = []
    for name, f in frames:
        if name == "PADDING":
            parts.append(f"PADDING×{f['bytes']}")
        elif name == "ACK":
            parts.append(f"ACK {f['largest'] - f['first']}–{f['largest']}" if f["first"] else f"ACK {f['largest']}")
        elif name == "CRYPTO":
            parts.append(f"CRYPTO {len(f['data'])} bytes")
        elif name == "STREAM":
            parts.append(f"STREAM {f['id']}: {len(f['data'])} bytes" + (" FIN" if f["fin"] else ""))
        elif name == "CONNECTION_CLOSE":
            parts.append(f"CONNECTION_CLOSE (error 0x{f['error']:x} {f['reason']})")
        else:
            parts.append(name)
    return ", ".join(parts)


# ---------------------------------------------------------------- the TLS ClientHello, QUIC-style

def transport_parameters(scid):
    def p(k, v):
        v = varint(v) if isinstance(v, int) else v
        return varint(k) + varint(len(v)) + v
    return b"".join([p(0x01, 30000), p(0x04, 16 << 20), p(0x05, 16 << 20), p(0x06, 1 << 20), p(0x07, 1 << 20),
                     p(0x08, 0), p(0x09, 16), p(0x0F, scid)])


# --8<-- [start:hello]
def client_hello(host, public_key, scid):
    extensions = b"".join([
        ext(0, vec(b"\x00" + vec(host.encode(), 2), 2)),                   # SNI
        ext(10, vec(struct.pack("!H", 0x001D), 2)),                         # x25519
        ext(13, vec(struct.pack("!7H", 0x0403, 0x0503, 0x0804, 0x0805, 0x0807, 0x0401, 0x0501), 2)),
        ext(43, vec(struct.pack("!H", 0x0304), 1)),                         # TLS 1.3, and nothing older
        ext(51, vec(struct.pack("!HH", 0x001D, 32) + public_key, 2)),       # our key share
        ext(16, vec(vec(b"h3", 1), 2)),                                      # ALPN: HTTP/3
        ext(0x39, transport_parameters(scid)),                               # QUIC's own settings, inside TLS
    ])
    body = (struct.pack("!H", 0x0303) + os.urandom(32) + b"\x00"           # no fake session ID: no middleboxes to fool
            + vec(struct.pack("!H", 0x1303), 2) + vec(b"\x00", 1) + vec(extensions, 2))
    return b"\x01" + vec(body, 3)
# --8<-- [end:hello]


# ---------------------------------------------------------------- the connection

class Connection:
    def __init__(self, host, path, verbose=False):
        self.host, self.path, self.verbose = host, path, verbose
        self.addr = socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_DGRAM)[0][4]
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.0)
        self.dcid, self.scid = os.urandom(8), os.urandom(8)          # the server will pick its own ID for us to use
        self.odcid = self.dcid
        self.send_keys, self.recv_keys = {}, {}
        self.send_keys[INITIAL], self.recv_keys[INITIAL] = initial_keys(self.dcid)
        self.next_pn = {INITIAL: 0, HANDSHAKE: 0, APP: 0}
        self.received = {INITIAL: set(), HANDSHAKE: set(), APP: set()}
        self.largest = {INITIAL: -1, HANDSHAKE: -1, APP: -1}
        self.crypto = {INITIAL: {}, HANDSHAKE: {}, APP: {}}          # offset → bytes, per stage
        self.crypto_read = {INITIAL: 0, HANDSHAKE: 0, APP: 0}
        self.pending = b""
        self.streams, self.token, self.transcript = {}, b"", b""
        self.done, self.response_done, self.last_flight = False, False, []
        self.eliciting, self.quiet_packets, self.quiet_bytes = False, 0, 0
        self.to_send, self.closed_by_server = [], False
        self.t0 = time.monotonic()

    def ms(self):
        return f"{(time.monotonic() - self.t0) * 1000:7.1f} ms"

    # ---- sending

    def packet(self, stage, frames, pad_to=None):
        pn = self.next_pn[stage]
        self.next_pn[stage] += 1
        if stage == APP:
            first, rest = 0x41, self.dcid                           # short header: 0 1 spin(0) … pn length 2
        else:
            first = 0xC1 | ({INITIAL: 0, HANDSHAKE: 2}[stage] << 4)
            rest = struct.pack("!I", 1) + bytes([len(self.dcid)]) + self.dcid + bytes([len(self.scid)]) + self.scid
            if stage == INITIAL:
                rest += varint(len(self.token)) + self.token
        payload = b"".join(frames)
        if pad_to:
            overhead = 1 + len(rest) + 2 + 2 + 16 + (0 if stage == APP else 0)
            payload += bytes(max(0, pad_to - overhead - len(payload)))
        if stage != APP:
            rest += struct.pack("!H", 0x4000 | (2 + len(payload) + 16))  # length, always as a 2-byte varint
        return protect(self.send_keys[stage], first, rest, pn, payload, long=stage != APP), pn

    def send(self, packets, note, show=True):
        datagram = b"".join(p for p, _ in packets)
        self.sock.sendto(datagram, self.addr)
        self.last_flight = [datagram]
        if show:
            print(f"{self.ms()} → {len(datagram):>5} bytes  {note}")

    # ---- receiving

    def receive(self, datagram):
        i = 0
        while i < len(datagram):
            first = datagram[i]
            if first & 0x80:                                         # long header
                version = struct.unpack("!I", datagram[i + 1:i + 5])[0]
                j = i + 5
                dcid = datagram[j + 1:j + 1 + datagram[j]]
                j += 1 + datagram[j]
                scid = datagram[j + 1:j + 1 + datagram[j]]
                j += 1 + datagram[j]
                if version == 0:
                    raise SystemExit("the server sent Version Negotiation: it doesn't speak QUIC version 1")
                kind = LONG_TYPES[(first >> 4) & 3]
                if kind == "Retry":
                    self.retry(scid, datagram[j:len(datagram) - 16])
                    return
                if kind == INITIAL:
                    n, j = read_varint(datagram, j)
                    j += n
                length, j = read_varint(datagram, j)
                end = j + length
                stage = kind
                self.dcid = scid                                     # from now on, use the server's chosen ID
            else:
                stage, j, end = APP, i + 1 + len(self.scid), len(datagram)
            if stage not in self.recv_keys:
                print(f"{self.ms()}   ({stage} packet arrived before its keys; dropped, it'll be sent again)")
                i = end
                continue
            view = datagram[i:end]
            truncated, pn_len, header, sealed = unprotect(self.recv_keys[stage], view, j - i, end - i, long=stage != APP)
            pn = full_pn(self.largest[stage], truncated, pn_len)
            try:
                plain = self.recv_keys[stage].open(pn, sealed, header)
            except ValueError:
                print(f"{self.ms()}   ({stage} packet failed to decrypt; ignored)")
                i = end
                continue
            self.largest[stage] = max(self.largest[stage], pn)
            self.received[stage].add(pn)
            frames = parse_frames(plain)
            self.eliciting |= any(n not in ("ACK", "PADDING", "CONNECTION_CLOSE") for n, _ in frames)
            only_data = stage == APP and all(n == "STREAM" and f["id"] == 0 for n, f in frames)
            if only_data and not self.verbose:
                self.quiet_packets += 1
                self.quiet_bytes += sum(len(f["data"]) for _, f in frames)
            else:
                lead = f"{self.ms()} ← {len(datagram):>5} bytes " if i == 0 else f"{'':>10}   {'+':>5}       "
                print(f"{lead} {stage} #{pn}: {summary(frames)}")
            for name, f in frames:
                self.frame(stage, name, f)
            i = end

    def retry(self, scid, token):
        print(f"{self.ms()} ←              Retry: the server wants proof of our address first; token {len(token)} bytes")
        self.dcid, self.token = scid, token
        self.send_keys[INITIAL], self.recv_keys[INITIAL] = initial_keys(scid)
        self.send([self.packet(INITIAL, [varint(6) + varint(0) + varint(len(self.hello)) + self.hello], pad_to=1200)],
                  "Initial again, with the token")

    def frame(self, stage, name, f):
        if name == "CRYPTO":
            self.crypto[stage][f["offset"]] = f["data"]
            buf = b""
            while self.crypto_read[stage] in self.crypto[stage]:
                chunk = self.crypto[stage].pop(self.crypto_read[stage])
                buf += chunk
                self.crypto_read[stage] += len(chunk)
            if buf:
                self.pending += buf
                messages, self.pending = handshake_messages(self.pending)
                for mtype, msg in messages:
                    self.tls(stage, mtype, msg)
        elif name == "STREAM":
            s = self.streams.setdefault(f["id"], {"parts": {}, "fin": None, "shown": 0})
            if f["data"]:
                s["parts"][f["offset"]] = f["data"]
            if f["fin"]:
                s["fin"] = f["offset"] + len(f["data"])
            self.h3(f["id"], s)
        elif name == "CONNECTION_CLOSE":
            alert = f" (a TLS alert, number {f['error'] - 0x100})" if 0x100 <= f["error"] < 0x200 else ""
            print(f"          the server closed the connection: error 0x{f['error']:x}{alert}")
            self.response_done = self.closed_by_server = True

    # ---- the TLS handshake, as in Chapter 32

    def tls(self, stage, mtype, msg):
        if mtype == 2:                                               # ServerHello
            self.transcript += msg
            exts = parse_extensions(msg[44 + msg[38]:])                 # skip version, random, session ID, suite…
            server_public = exts[51][4:36]
            shared = x25519(self.private, server_public)
            zero = bytes(32)
            early = hkdf_extract(zero, zero)
            self.hs_secret = hkdf_extract(derive_secret(early, "derived", b""), shared)
            self.c_hs = derive_secret(self.hs_secret, "c hs traffic", self.transcript)
            self.s_hs = derive_secret(self.hs_secret, "s hs traffic", self.transcript)
            self.send_keys[HANDSHAKE], self.recv_keys[HANDSHAKE] = Keys(self.c_hs), Keys(self.s_hs)
            print(f"          ServerHello: X25519 key share → handshake keys (ChaCha20-Poly1305)")
            self.to_send.append("initial ack")
        elif mtype == 8:                                             # EncryptedExtensions
            self.transcript += msg
            exts = parse_extensions(msg[6:])
            alpn = exts.get(16, b"")[3:].decode()
            params, j, tp = {}, 0, exts.get(0x39, b"")
            while j < len(tp):
                k, j = read_varint(tp, j)
                n, j = read_varint(tp, j)
                v = tp[j:j + n]
                j += n
                if k in TP_NAMES:
                    params[TP_NAMES[k]] = (read_varint(v, 0)[0] if v and k not in (0x00, 0x02, 0x0F, 0x10) else v.hex())
            print(f"          EncryptedExtensions: ALPN {alpn!r}; the server’s transport parameters:")
            for k, v in sorted(params.items(), key=lambda kv: [n for n, name in TP_NAMES.items() if name == kv[0]][0]):
                print(f"             {k} = {v}")
        elif mtype == 11:                                            # Certificate
            self.transcript += msg
            self.chain = certs.parse_certificate_message(msg[4:])
            info = certs.describe(self.chain[0])
            print(f"          Certificate: {len(self.chain)} certificates; #0 is {info['subject']} ({info['key']}), from {info['issuer']}")
        elif mtype == 15:                                            # CertificateVerify
            scheme, sig = struct.unpack("!H", msg[4:6])[0], msg[8:]
            signed = b" " * 64 + b"TLS 1.3, server CertificateVerify\x00" + hashlib.sha256(self.transcript).digest()
            ok = certs.verify(self.chain[0], scheme, signed, sig)
            print(f"          CertificateVerify: {'VALID' if ok else 'INVALID!'}")
            if not ok:
                raise SystemExit("bad signature")
            self.transcript += msg
        elif mtype == 20:                                            # Finished
            key = hkdf_expand_label(self.s_hs, "finished", b"", 32)
            ok = hmac.compare_digest(hmac.new(key, hashlib.sha256(self.transcript).digest(), hashlib.sha256).digest(), msg[4:])
            print(f"          Finished: {'matches' if ok else 'WRONG!'}")
            self.transcript += msg
            self.to_send.append("finish")
        elif mtype == 4:
            print(f"          NewSessionTicket (for next time; ignored)")

    def finish(self):
        master = hkdf_extract(derive_secret(self.hs_secret, "derived", b""), bytes(32))
        c_ap = derive_secret(master, "c ap traffic", self.transcript)
        s_ap = derive_secret(master, "s ap traffic", self.transcript)
        key = hkdf_expand_label(self.c_hs, "finished", b"", 32)
        fin = b"\x14" + vec(hmac.new(key, hashlib.sha256(self.transcript).digest(), hashlib.sha256).digest(), 3)
        self.send_keys[APP], self.recv_keys[APP] = Keys(c_ap), Keys(s_ap)
        hs = self.packet(HANDSHAKE, [ack_frame(self.received[HANDSHAKE]), varint(6) + varint(0) + varint(len(fin)) + fin])
        # --8<-- [start:request]
        control = varint(0x00) + varint(0x04) + varint(0)                          # control stream: SETTINGS (all defaults)
        fields = hpack.qpack_encode([(":method", "GET"), (":scheme", "https"), (":authority", self.host),
                                     (":path", self.path), ("user-agent", "bitbybit-h3/1.0")])
        request = varint(0x01) + varint(len(fields)) + fields                        # an HTTP/3 HEADERS frame
        app = self.packet(APP, [varint(0x0A) + varint(2) + varint(len(control)) + control,   # STREAM 2 (ours, one-way)
                                varint(0x0B) + varint(0) + varint(len(request)) + request])  # STREAM 0, FIN
        # --8<-- [end:request]
        self.send([hs, app], f"{HANDSHAKE} #{hs[1]}: ACK, CRYPTO Finished  +  {APP} #{app[1]}: "
                  f"STREAM 2 (control: SETTINGS), STREAM 0 (HEADERS: GET {self.path}) FIN")
        self.done = True

    # ---- HTTP/3 on top

    def h3(self, sid, s):
        data, off = b"", 0
        while off in s["parts"]:
            data += s["parts"][off]
            off += len(s["parts"][off])
        complete = s["fin"] is not None and off == s["fin"]
        if sid % 4 == 3 and len(data) > s["shown"]:                  # a one-way stream from the server
            kind, j = read_varint(data, 0)
            if not s["shown"]:
                grease = "a GREASE stream: meaningless, to keep clients honest"
                print(f"          stream {sid} is the server’s " + {0: "control stream", 2: "QPACK encoder stream",
                                                                       3: "QPACK decoder stream"}.get(kind, grease))
            while kind == 0 and j < len(data):
                try:
                    ftype, k = read_varint(data, j)
                    n, k = read_varint(data, k)
                except IndexError:
                    break
                if k + n > len(data):
                    break
                if ftype == 0x04 and j >= s["shown"]:
                    settings, m, body = [], 0, data[k:k + n]
                    while m < len(body):
                        ident, m = read_varint(body, m)
                        v, m = read_varint(body, m)
                        grease = (ident - 0x21) % 0x1F == 0
                        settings.append(f"{H3_SETTINGS.get(ident, 'GREASE' if grease else hex(ident))}={v}")
                    print(f"          SETTINGS: {', '.join(settings)}")
                j = k + n
            s["shown"] = len(data)
        if sid == 0 and complete and not self.response_done:
            self.response_done = True
            if self.quiet_packets:
                print(f"{self.ms()} ← … and {self.quiet_packets} more 1-RTT packets of STREAM 0 data ({self.quiet_bytes:,} bytes), "
                      f"each acknowledged (-v shows them all)")
            j, body = 0, b""
            while j < len(data):
                ftype, j = read_varint(data, j)
                n, j = read_varint(data, j)
                if ftype == 0x01:
                    fields = hpack.qpack_decode(data[j:j + n])
                    print(f"\n          HTTP/3 HEADERS ({n} bytes, QPACK):")
                    for name, value, how, size in fields:
                        print(f"             {(name + ': ' + value)[:60]:<60} {size:>3} bytes, {how}")
                elif ftype == 0x00:
                    body += data[j:j + n]
                j += n
            first = body.split(b"\n", 1)[0][:70].decode("utf-8", "replace")
            print(f"          HTTP/3 DATA: {len(body):,} bytes of body, starting “{first}”\n")

    # ---- the whole thing

    def run(self):
        print(f"QUIC to {self.host} ({self.addr[0]}) UDP port 443; our connection ID {self.scid.hex()}, "
              f"theirs for now {self.dcid.hex()}\n")
        self.private, public = keypair()
        self.hello = client_hello(self.host, public, self.scid)
        self.transcript = self.hello
        self.send([self.packet(INITIAL, [varint(6) + varint(0) + varint(len(self.hello)) + self.hello], pad_to=1200)],
                  f"{INITIAL} #0: CRYPTO ClientHello ({len(self.hello)} bytes), PADDING")
        silent = 0
        while not self.response_done:
            try:
                datagram, _ = self.sock.recvfrom(65536)
            except socket.timeout:
                silent += 1
                if silent > 5:
                    raise SystemExit("no answer: UDP port 443 may be blocked on this network")
                print(f"{self.ms()}   (silence: sending our last packets again)")
                for d in self.last_flight:
                    self.sock.sendto(d, self.addr)
                continue
            silent = 0
            self.eliciting = False
            self.receive(datagram)
            for job in self.to_send:                               # answer once the whole datagram is read
                if job == "initial ack":                           # proves our address: the server may send more
                    self.send([self.packet(INITIAL, [ack_frame(self.received[INITIAL])], pad_to=1200)],
                              f"{INITIAL} #{self.next_pn[INITIAL]}: ACK (and padding)")
                else:
                    self.finish()
            self.to_send = []
            if self.done and self.received[APP] and self.eliciting and not self.response_done:
                self.send([self.packet(APP, [ack_frame(self.received[APP])])], f"{APP} #{self.next_pn[APP]}: ACK",
                          show=self.verbose)
        if self.closed_by_server:
            return
        close = varint(0x1D) + varint(0x100) + varint(0)                 # CONNECTION_CLOSE, H3_NO_ERROR
        self.send([self.packet(APP, [ack_frame(self.received[APP]), close])], f"{APP} #{self.next_pn[APP]}: ACK, CONNECTION_CLOSE (no error)")


# ---------------------------------------------------------------- versions, and tests

def versions(host):
    """Send a packet with a made-up version; a QUIC server answers with the versions it does speak."""
    dcid, scid = os.urandom(8), os.urandom(8)
    pkt = bytes([0xC0]) + struct.pack("!I", 0x1A2A3A4A) + bytes([8]) + dcid + bytes([8]) + scid
    pkt += os.urandom(1200 - len(pkt))                                  # at least 1200 bytes, as for a real first packet
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    s.sendto(pkt, (host, 443))
    print(f"→ {len(pkt)} bytes to {host} port 443, claiming to speak version 0x1a2a3a4a")
    try:
        data, addr = s.recvfrom(2000)
    except socket.timeout:
        raise SystemExit("no answer (some servers ignore versions they don't know; or UDP 443 is blocked)")
    j = 6 + data[5]
    j += 1 + data[j]
    names = {0x00000001: "QUIC version 1 (RFC 9000)", 0x6B3343CF: "QUIC version 2 (RFC 9369)"}
    print(f"← {len(data)} bytes from {addr[0]}: Version Negotiation (version field 0x00000000). The server speaks:")
    for k in range(j, len(data), 4):
        v = int.from_bytes(data[k:k + 4], "big")
        print(f"   0x{v:08x}  " + names.get(v, "a draft version" if v >> 8 == 0xFF0000 else
                                     "(reserved: a random “GREASE” value, to keep clients honest)" if v & 0x0F0F0F0F == 0x0A0A0A0A else ""))


def test():
    client, server = initial_keys(bytes.fromhex("8394c8f03e515708"))
    ok = client.key.hex() == "1f369613dd76d5467730efcbe3b1a22d" and server.hp.hex() == "c206b8d9b9f0f37644430b490eeaa314"
    # A.2: the client's Initial packet, protected
    crypto = bytes.fromhex(
        "060040f1010000ed0303ebf8fa56f12939b9584a3896472ec40bb863cfd3e86804fe3a47f06a2b69484c000004130113"
        "02010000c000000010000e00000b6578616d706c652e636f6dff01000100000a00080006001d00170018001000070005"
        "04616c706e0005000501000000000033002600 24001d00209370b2c9caa47fbabaf4559fedba753de171fa71f50f1ce1"
        "5d43e994ec74d748002b0003020304000d0010000e0403050306030203080408050806002d00020101001c00024001"
        "003900320408ffffffffffffffff05048000ffff07048000ffff0801100104800075300901100f088394c8f03e51570806048000ffff".replace(" ", ""))
    payload = crypto + bytes(1162 - len(crypto))
    header = bytes.fromhex("c300000001088394c8f03e5157080000449e00000002")
    sealed = client.seal(2, payload, header)
    mask = client.mask(sealed[:16])
    ok &= mask.hex() == "437b9aec36" and sealed[:16].hex() == "d1b1c98dd7689fb8ec11d242b123dc9b"
    ok &= sealed[-16:].hex() == "e221af44860018ab0856972e194cd934"
    # A.3: the server's Initial packet, unprotected and opened
    pkt = bytes.fromhex("cf000000010008f067a5502a4262b5004075c0d95a482cd0991cd25b0aac406a5816b6394100f37a1c69797554780bb3"
                        "8cc5a99f5ede4cf73c3ec2493a1839b3dbcba3f6ea46c5b7684df3548e7ddeb9c3bf9c73cc3f3bded74b562bfb19fb84"
                        "022f8ef4cdd93795d77d06edbb7aaf2f58891850abbdca3d20398c276456cbc42158407dd074ee")
    truncated, pn_len, hdr, body = unprotect(server, pkt, 18, len(pkt))
    plain = server.open(truncated, body, hdr)
    ok &= truncated == 1 and parse_frames(plain)[1][0] == "CRYPTO"
    # A.5: a ChaCha20 short-header packet
    k = Keys(bytes.fromhex("9ac312a7f877468ebe69422748ad00a15443f18203a07d6060f688f30f21632b"))
    ok &= k.mask(bytes.fromhex("5e5cd55c41f69080575d7999c25a5bfb")).hex() == "aefefe7d03"
    ok &= k.seal(654360564, b"\x01", bytes.fromhex("4200bff4")).hex() == "655e5cd55c41f69080575d7999c25a5bfb"
    ok &= full_pn(0xA82F30EA, 0x9B32, 2) == 0xA82F9B32
    print("RFC 9000/9001 examples: all match" if ok else "MISMATCH")


def main():
    if "--test" in sys.argv:
        return test()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["versions", "get"])
    p.add_argument("host")
    p.add_argument("path", nargs="?", default="/")
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args()
    if a.command == "versions":
        versions(a.host)
    else:
        Connection(a.host, a.path, a.verbose).run()


if __name__ == "__main__":
    main()
