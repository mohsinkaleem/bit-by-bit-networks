#!/usr/bin/env python3
"""Chapter 31 lab: the ideas behind every padlock icon, one at a time.

    python3 crypto_lab.py pad        a one-time pad, and what goes wrong if you use it twice
    python3 crypto_lab.py hash       fingerprints: change one character, change everything
    python3 crypto_lab.py collide    why fingerprints must be long: find a collision in a short one
    python3 crypto_lab.py mac        a tag that proves who sent a message (HMAC)
    python3 crypto_lab.py dh         agree on a secret in public, with small numbers, then big ones
    python3 crypto_lab.py rsa        sign with a private key, check with a public one (tiny RSA)
    python3 crypto_lab.py cert       the certificate a real website sends you

Toy versions use tiny numbers so you can follow the arithmetic; never use them for real secrets.
"""
import hashlib
import hmac
import os
import secrets
import socket
import ssl
import sys
import time


def xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


# --8<-- [start:pad]
def pad():
    m1, m2 = b"MEET AT THE OAK AT NOON", b"THE KEY IS UNDER THE MAT"[:23]
    key = os.urandom(len(m1))                      # truly random, as long as the message, used ONCE
    c1, c2 = xor(m1, key), xor(m2, key)
    print(f"message 1: {m1.decode()}")
    print(f"key:       {key.hex()}")
    print(f"encrypted: {c1.hex()}   (without the key, every message of this length is equally likely)")
    print(f"\nNow Alice lazily uses the same key again, for message 2. Eve has both ciphertexts:")
    both = xor(c1, c2)                             # the key cancels out: (m1^k) ^ (m2^k) = m1 ^ m2
    print(f"c1 XOR c2: {both.hex()}   = message 1 XOR message 2: no key involved at all!")
    guess = b"THE "
    for pos in range(len(both) - len(guess) + 1):   # "crib dragging": guess a word, slide it along
        piece = xor(both[pos:pos + len(guess)], guess)
        if all(65 <= ch <= 90 or ch == 32 for ch in piece):
            print(f"  if one message has {guess.decode()!r} at position {pos:>2}, the other one there reads {piece.decode()!r}")
# --8<-- [end:pad]


def bits_differ(a, b):
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b))


def hash_demo():
    for text in ("Meet me at noon", "Meet me at noon.", "Meet me at noom"):
        print(f"SHA-256({text!r:<19}) = {hashlib.sha256(text.encode()).hexdigest()}")
    a, b = hashlib.sha256(b"Meet me at noon").digest(), hashlib.sha256(b"Meet me at noon.").digest()
    print(f"\nadding one full stop changed {bits_differ(a, b)} of the 256 bits (about half, as it should)")
    big = os.urandom(10_000_000)
    t = time.perf_counter()
    h = hashlib.sha256(big).hexdigest()
    print(f"10 MB of random data → {h[:16]}…  in {(time.perf_counter() - t) * 1000:.0f} ms: fingerprints are fast")


# --8<-- [start:collide]
def collide(bits=32):
    """Two different messages with the same first `bits` bits of SHA-256. The birthday paradox says
    it takes about 2^(bits/2) tries, not 2^bits: 65,536-ish for 32 bits."""
    seen = {}
    t = time.perf_counter()
    for i in range(1 << 30):
        msg = f"Pay Bob £{i}".encode()
        fp = hashlib.sha256(msg).digest()[: bits // 8]
        if fp in seen:
            print(f"{seen[fp].decode()!r} and {msg.decode()!r} share the fingerprint {fp.hex()}")
            print(f"found after {i:,} tries in {time.perf_counter() - t:.2f} s")
            return
        seen[fp] = msg
# --8<-- [end:collide]


def mac():
    key = secrets.token_bytes(32)                  # shared by Alice and Bob, nobody else
    msg = b"Transfer 10 pounds to Bob"
    tag = hmac.new(key, msg, hashlib.sha256).hexdigest()
    print(f"message: {msg.decode()}\ntag:     {tag}")
    fake = b"Transfer 99 pounds to Eve"
    fake_tag = hashlib.sha256(fake).hexdigest()    # Eve can make a hash; she can't make an HMAC without the key
    for m, t in ((msg, tag), (fake, fake_tag)):
        good = hmac.compare_digest(hmac.new(key, m, hashlib.sha256).hexdigest(), t)
        print(f"Bob checks {m.decode()!r}: {'genuine' if good else 'FORGED: the tag is wrong'}")


# --8<-- [start:dh]
def dh():
    p, g = 23, 5                                   # public: a prime, and a starting number
    a, b = 6, 15                                   # private: Alice's and Bob's secret numbers
    A, B = pow(g, a, p), pow(g, b, p)              # public: 5^6 mod 23 = 8, 5^15 mod 23 = 19
    print(f"everyone knows p = {p}, g = {g}")
    print(f"Alice picks a = {a} (secret), sends A = g^a mod p = {A}")
    print(f"Bob picks   b = {b} (secret), sends B = g^b mod p = {B}")
    print(f"Alice computes B^a mod p = {pow(B, a, p)};  Bob computes A^b mod p = {pow(A, b, p)}: the same!")
    guess = next(x for x in range(p) if pow(g, x, p) == A)
    print(f"Eve, with tiny numbers, just tries every a: a = {guess} works, so she can work it out too.\n")
    p = 2 ** 255 - 19                              # the size real TLS uses (Chapter 32 uses X25519)
    a, b = secrets.randbelow(p), secrets.randbelow(p)
    A, B = pow(2, a, p), pow(2, b, p)
    print(f"with a 255-bit prime, A = {A % 10 ** 12:,}… ({A.bit_length()} bits)")
    print(f"shared secret agrees: {pow(B, a, p) == pow(A, b, p)}. Trying every a would take longer than the")
    print("universe has existed, even with every computer on Earth.")
# --8<-- [end:dh]


def rsa():
    p, q = 61, 53                                  # two secret primes (real ones have ~300 digits)
    n, phi = p * q, (p - 1) * (q - 1)              # n = 3233 is public; phi stays secret
    e = 17                                         # public exponent
    d = pow(e, -1, phi)                            # private exponent: 2753 (easy only if you know p and q)
    print(f"public key (n, e) = ({n}, {e});  private key d = {d}")
    msg = b"I owe Bob 5 pounds"
    h = int.from_bytes(hashlib.sha256(msg).digest(), "big") % n       # sign the fingerprint, not the message
    sig = pow(h, d, n)
    print(f"Alice signs {msg.decode()!r}: fingerprint mod n = {h}, signature = {h}^{d} mod {n} = {sig}")
    print(f"anyone checks: {sig}^{e} mod {n} = {pow(sig, e, n)}, which matches the fingerprint: genuine")
    h2 = int.from_bytes(hashlib.sha256(b"I owe Bob 500 pounds").digest(), "big") % n
    print(f"change the message, and the signature checks out to {pow(sig, e, n)}, not {h2}: forged")


def cert(host="example.org"):
    ctx = ssl.create_default_context()
    with ctx.wrap_socket(socket.create_connection((host, 443)), server_hostname=host) as s:
        c = s.getpeercert()
        print(f"{host} sent a certificate that says:")
        print(f"  subject:  {dict(x[0] for x in c['subject']).get('commonName')}")
        print(f"  also for: {', '.join(v for k, v in c.get('subjectAltName', []))}")
        print(f"  issuer:   {', '.join('='.join(x[0]) for x in c['issuer'])}")
        print(f"  valid:    {c['notBefore']} to {c['notAfter']}")
        print(f"  (and Python checked it: the signature chain leads to a certificate authority this computer trusts,")
        print(f"   and the name matches. Otherwise wrap_socket would have raised an error.)")
        if hasattr(s, "get_verified_chain"):          # Python 3.13 and later
            chain = s.get_verified_chain()
            print(f"  the chain, from the site up to the trusted root: {len(chain)} certificates")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    table = {"pad": pad, "hash": hash_demo, "collide": collide, "mac": mac, "dh": dh, "rsa": rsa, "cert": cert}
    if cmd in table:
        table[cmd](*sys.argv[2:])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
