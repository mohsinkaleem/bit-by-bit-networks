#!/usr/bin/env python3
"""Chapter 32 lab: a TLS 1.3 client from scratch. It fetches a real web page over HTTPS.

    python3 tls13.py example.org                 connect, shake hands, check the certificate, GET /
    python3 tls13.py www.google.com /robots.txt  another site, another path
    python3 tls13.py example.org --hex           show the bytes of every handshake message
    python3 tls13.py example.org --keylog keys.txt   save the secrets, so Wireshark can decrypt a capture

Everything is here except the lowest-level building blocks, which come from Chapter 31:
x25519.py (the key exchange) and chacha.py (the cipher). It only speaks one cipher suite,
TLS_CHACHA20_POLY1305_SHA256, which almost every server supports. It checks the server's
signature and name itself; checking that the certificate chain leads to a trusted root is left
to Python's own ssl module, at the end, for comparison.
"""
import argparse
import hashlib
import hmac
import os
import socket
import ssl
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ch31"))
from chacha import open_ as aead_open, seal as aead_seal   # noqa: E402  (Chapter 31)
from x25519 import keypair, x25519                          # noqa: E402

import certs                                                 # noqa: E402  (this folder: certificates and signatures)

GROUP, KEX_NAME = 0x001D, "X25519"      # the one key exchange we offer (Chapter 42 swaps in a post-quantum one)

HS_NAMES = {1: "ClientHello", 2: "ServerHello", 4: "NewSessionTicket", 8: "EncryptedExtensions", 11: "Certificate",
            13: "CertificateRequest", 15: "CertificateVerify", 20: "Finished"}
REC_NAMES = {20: "change_cipher_spec", 21: "alert", 22: "handshake", 23: "application_data"}


# ---------------------------------------------------------------- the key schedule (RFC 8446 section 7)

# --8<-- [start:hkdf]
def hkdf_extract(salt, ikm):
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def hkdf_expand_label(secret, label, context, length):
    """Stretch a secret into a key of any length, labelled with what it's for ("tls13 key", "tls13 iv", …)."""
    full = b"tls13 " + label.encode()
    info = struct.pack("!H", length) + bytes([len(full)]) + full + bytes([len(context)]) + context
    out, block, i = b"", b"", 1
    while len(out) < length:
        block = hmac.new(secret, block + info + bytes([i]), hashlib.sha256).digest()
        out += block
        i += 1
    return out[:length]


def derive_secret(secret, label, transcript):
    """A new secret, tied to everything said so far (the transcript's SHA-256 fingerprint)."""
    return hkdf_expand_label(secret, label, hashlib.sha256(transcript).digest(), 32)
# --8<-- [end:hkdf]


# ---------------------------------------------------------------- building the ClientHello

def ext(kind, data):
    return struct.pack("!HH", kind, len(data)) + data


def vec(data, n):
    """A vector with an n-byte length in front: TLS's way of writing a list."""
    return len(data).to_bytes(n, "big") + data


# --8<-- [start:hello]
def client_hello(host, public_key):
    random = os.urandom(32)
    extensions = b"".join([
        ext(0, vec(b"\x00" + vec(host.encode(), 2), 2)),         # server_name (SNI): which site we want
        ext(10, vec(struct.pack("!H", GROUP), 2)),                # supported_groups: x25519
        ext(13, vec(struct.pack("!7H", 0x0403, 0x0503, 0x0804, 0x0805, 0x0807, 0x0401, 0x0501), 2)),  # signatures we can check
        ext(43, vec(struct.pack("!H", 0x0304), 1)),               # supported_versions: TLS 1.3 only
        ext(51, vec(struct.pack("!HH", GROUP, len(public_key)) + public_key, 2)),  # key_share: our X25519 public key
        ext(16, vec(vec(b"http/1.1", 1), 2)),                     # ALPN: we'll speak HTTP/1.1
    ])
    body = (struct.pack("!H", 0x0303) + random                    # "TLS 1.2", for old middleboxes' sake
            + vec(os.urandom(32), 1)                              # a fake session ID, for the same reason
            + vec(struct.pack("!H", 0x1303), 2)                   # cipher suites: CHACHA20_POLY1305_SHA256
            + vec(b"\x00", 1)                                     # compression: none
            + vec(extensions, 2))
    return random, b"\x01" + vec(body, 3)                         # handshake type 1 = ClientHello
# --8<-- [end:hello]


def parse_extensions(data):
    out, i = {}, 0
    while i < len(data):
        kind, n = struct.unpack("!HH", data[i:i + 4])
        out[kind] = data[i + 4:i + 4 + n]
        i += 4 + n
    return out


# ---------------------------------------------------------------- the record layer

class Records:
    def __init__(self, sock, verbose):
        self.sock, self.buf, self.verbose = sock, b"", verbose
        self.read_key = self.write_key = None
        self.read_seq = self.write_seq = 0

    def _read(self, n):
        while len(self.buf) < n:
            more = self.sock.recv(65536)
            if not more:
                raise ConnectionError("the server closed the connection")
            self.buf += more
        data, self.buf = self.buf[:n], self.buf[n:]
        return data

    def set_keys(self, read_secret=None, write_secret=None):
        if read_secret:
            self.read_key = (hkdf_expand_label(read_secret, "key", b"", 32), hkdf_expand_label(read_secret, "iv", b"", 12))
            self.read_seq = 0
        if write_secret:
            self.write_key = (hkdf_expand_label(write_secret, "key", b"", 32), hkdf_expand_label(write_secret, "iv", b"", 12))
            self.write_seq = 0

    @staticmethod
    def nonce(iv, seq):
        return bytes(a ^ b for a, b in zip(iv, seq.to_bytes(12, "big")))   # a new nonce for every record

    # --8<-- [start:records]
    def read(self):
        """One record. Encrypted ones are decrypted: the real type is hidden inside."""
        header = self._read(5)
        rtype, _, length = struct.unpack("!BHH", header)
        body = self._read(length)
        if rtype == 23 and self.read_key:
            key, iv = self.read_key
            inner = aead_open(key, self.nonce(iv, self.read_seq), body, aad=header)
            self.read_seq += 1
            inner = inner.rstrip(b"\0")                 # remove padding
            return inner[-1], inner[:-1], length       # the last byte is the real content type
        return rtype, body, length

    def write(self, rtype, data):
        if self.write_key:
            key, iv = self.write_key
            inner = data + bytes([rtype])
            header = struct.pack("!BHH", 23, 0x0303, len(inner) + 16)   # everything looks like app data
            self.sock.sendall(header + aead_seal(key, self.nonce(iv, self.write_seq), inner, aad=header))
            self.write_seq += 1
        else:   # unencrypted: only the ClientHello says "TLS 1.0" (0x0301), for very old middleboxes
            version = 0x0301 if data[:1] == b"\x01" and rtype == 22 else 0x0303
            self.sock.sendall(struct.pack("!BHH", rtype, version, len(data)) + data)
    # --8<-- [end:records]


def handshake_messages(buf):
    """Split handshake bytes into messages; returns ([(type, whole message)], leftover)."""
    out, i = [], 0
    while i + 4 <= len(buf):
        n = int.from_bytes(buf[i + 1:i + 4], "big")
        if i + 4 + n > len(buf):
            break
        out.append((buf[i], buf[i:i + 4 + n]))
        i += 4 + n
    return out, buf[i:]


def show(verbose, direction, what, data=b"", note=""):
    print(f"{direction} {what:<22} {len(data):>5} bytes  {note}")
    if verbose and data:
        print("        " + data[:64].hex(" ") + (" …" if len(data) > 64 else ""))


# ---------------------------------------------------------------- the handshake

def connect(host, path="/", verbose=False, keylog=None):
    sock = socket.create_connection((host, 443), timeout=10)
    rec = Records(sock, verbose)
    print(f"TCP connected to {host} ({sock.getpeername()[0]}) port 443\n")

    # --8<-- [start:flight1]
    private, public = keypair()                                   # a fresh X25519 key pair, just for this connection
    client_random, ch = client_hello(host, public)
    rec.write(22, ch)
    show(verbose, "→", "ClientHello", ch, f"offers TLS 1.3, ChaCha20-Poly1305, {KEX_NAME}; SNI {host}")
    transcript = ch

    rtype, body, _ = rec.read()
    if rtype == 21:
        raise SystemExit(f"the server refused: alert {body.hex()}")
    sh = body
    transcript += sh
    legacy, server_random = struct.unpack("!H", sh[4:6])[0], sh[6:38]
    sid_len = sh[38]
    suite = struct.unpack("!H", sh[39 + sid_len:41 + sid_len])[0]
    exts = parse_extensions(sh[44 + sid_len:])
    if server_random == hashlib.sha256(b"HelloRetryRequest").digest():
        raise SystemExit("the server sent HelloRetryRequest (it wants a different key share); this lab stops here")
    group, klen = struct.unpack("!HH", exts[51][:4])
    server_public = exts[51][4:4 + klen]
    show(verbose, "←", "ServerHello", sh, f"suite 0x{suite:04x}, version 0x{struct.unpack('!H', exts[43])[0]:04x}, "
         f"server's {KEX_NAME} key {server_public[:6].hex()}…")

    shared = x25519(private, server_public)                       # Chapter 31: the same secret on both sides
    print(f"\n  shared secret ({KEX_NAME}): {shared.hex()}")
    zero = bytes(32)
    early = hkdf_extract(zero, zero)
    handshake_secret = hkdf_extract(derive_secret(early, "derived", b""), shared)
    c_hs = derive_secret(handshake_secret, "c hs traffic", transcript)
    s_hs = derive_secret(handshake_secret, "s hs traffic", transcript)
    rec.set_keys(read_secret=s_hs, write_secret=None)
    print(f"  handshake keys derived. From now on, everything the server sends is encrypted.\n")
    # --8<-- [end:flight1]

    # --8<-- [start:flight2]
    pending, cert_chain, done = b"", [], False
    while not done:
        rtype, body, wire_len = rec.read()
        if rtype == 20:
            show(verbose, "←", "(change_cipher_spec)", body, "meaningless: only there to calm old middleboxes")
            continue
        if rtype == 21:
            raise SystemExit(f"alert from server: {body.hex()}")
        pending += body
        messages, pending = handshake_messages(pending)
        for mtype, msg in messages:
            name = HS_NAMES.get(mtype, f"type {mtype}")
            if mtype == 8:
                alpn = parse_extensions(msg[6:]).get(16, b"")
                show(verbose, "←", name, msg, f"(decrypted) ALPN: {alpn[3:].decode() or 'none'}")
            elif mtype == 11:
                cert_chain = certs.parse_certificate_message(msg[4:])
                show(verbose, "←", name, msg, f"(decrypted) a chain of {len(cert_chain)} certificates")
                for i, der in enumerate(cert_chain):
                    info = certs.describe(der)
                    print(f"        #{i} {info['subject']}  (issued by {info['issuer']}, {info['key']}, until {info['not_after']})")
            elif mtype == 15:
                scheme, sig = struct.unpack("!H", msg[4:6])[0], msg[8:]
                signed = b" " * 64 + b"TLS 1.3, server CertificateVerify\x00" + hashlib.sha256(transcript).digest()
                ok = certs.verify(cert_chain[0], scheme, signed, sig)
                show(verbose, "←", name, msg, f"(decrypted) signature scheme 0x{scheme:04x}: "
                     + ("VALID: the server has the private key for that certificate" if ok else "INVALID!"))
                if not ok:
                    raise SystemExit("the signature doesn't check out: someone is pretending to be the server")
            elif mtype == 20:
                finished_key = hkdf_expand_label(s_hs, "finished", b"", 32)
                expected = hmac.new(finished_key, hashlib.sha256(transcript).digest(), hashlib.sha256).digest()
                ok = hmac.compare_digest(expected, msg[4:])
                show(verbose, "←", name, msg, "(decrypted) " + ("matches: nobody tampered with the handshake" if ok else "WRONG!"))
                if not ok:
                    raise SystemExit("the Finished message is wrong: the handshake was tampered with")
                done = True
            transcript += msg
    # --8<-- [end:flight2]

    names = certs.describe(cert_chain[0])["names"]
    ok_name = any(n == host or (n.startswith("*.") and host.split(".", 1)[-1] == n[2:]) for n in names)
    print(f"\n  the certificate is for {', '.join(names[:4])}{'…' if len(names) > 4 else ''}: "
          + ("it includes " + host if ok_name else f"NOT {host}!"))

    # --8<-- [start:finish]
    master = hkdf_extract(derive_secret(handshake_secret, "derived", b""), zero)
    c_ap = derive_secret(master, "c ap traffic", transcript)      # application keys cover the whole handshake
    s_ap = derive_secret(master, "s ap traffic", transcript)
    rec.write(20, b"\x01")                                        # our own (meaningless) change_cipher_spec
    rec.set_keys(write_secret=c_hs)
    finished_key = hkdf_expand_label(c_hs, "finished", b"", 32)
    fin = b"\x14" + vec(hmac.new(finished_key, hashlib.sha256(transcript).digest(), hashlib.sha256).digest(), 3)
    rec.write(22, fin)
    show(verbose, "→", "Finished", fin, "(encrypted) proves we saw the same handshake")
    rec.set_keys(read_secret=s_ap, write_secret=c_ap)
    print("\n  handshake complete: application keys in place.\n")
    # --8<-- [end:finish]

    if keylog:
        with open(keylog, "a") as f:
            cr = client_random.hex()
            f.write(f"CLIENT_HANDSHAKE_TRAFFIC_SECRET {cr} {c_hs.hex()}\nSERVER_HANDSHAKE_TRAFFIC_SECRET {cr} {s_hs.hex()}\n"
                    f"CLIENT_TRAFFIC_SECRET_0 {cr} {c_ap.hex()}\nSERVER_TRAFFIC_SECRET_0 {cr} {s_ap.hex()}\n")
        print(f"  (secrets appended to {keylog}: Wireshark can use them to decrypt a capture of this connection)\n")

    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: bitbybit-tls13/1.0\r\nConnection: close\r\n\r\n".encode()
    rec.write(23, request)
    show(verbose, "→", "application_data", request, f"(encrypted) GET {path}")
    response, records = b"", 0
    while True:
        try:
            rtype, body, wire_len = rec.read()
        except ConnectionError:
            break
        if rtype == 22:
            show(verbose, "←", HS_NAMES.get(body[0], "handshake"), body, "(decrypted) for resuming later; ignored")
        elif rtype == 23:
            response += body
            records += 1
            if records == 1:
                show(verbose, "←", "application_data", body, "(decrypted) the start of the response")
        elif rtype == 21:
            if records > 1:
                print(f"← application_data × {records - 1} more records, {len(response):,} bytes decrypted in all")
            show(verbose, "←", "alert", body, "close_notify: the server is done" if body[1:2] == b"\x00" else body.hex())
            records = 0
            break
    if records > 1:
        print(f"← application_data × {records - 1} more records, {len(response):,} bytes decrypted in all")
    sock.close()
    head, _, content = response.partition(b"\r\n\r\n")
    print("\n" + head.decode("latin-1"))
    print(f"\n({len(content)} bytes of body)")
    return response


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("host")
    p.add_argument("path", nargs="?", default="/")
    p.add_argument("--hex", action="store_true")
    p.add_argument("--keylog")
    a = p.parse_args()
    connect(a.host, a.path, a.hex, a.keylog)
    # for comparison: does Python's ssl module, with its trusted roots, accept the same server?
    try:
        with ssl.create_default_context().wrap_socket(socket.create_connection((a.host, 443), timeout=10), server_hostname=a.host) as s:
            print(f"(Python's ssl module agrees: the chain leads to a trusted root, and it chose {s.version()} with {s.cipher()[0]})")
    except ssl.SSLError as e:
        print(f"(Python's ssl module does NOT trust this server: {e})")


if __name__ == "__main__":
    main()
