#!/usr/bin/env python3
"""Chapter 33 lab: AES-128 and AES-GCM in pure Python. quic.py imports this.

    python3 aesgcm.py --test     check against the standard test vectors

QUIC's very first packets are always sealed with AES-128-GCM, so a QUIC client needs it even
if it prefers ChaCha20 afterwards. AES scrambles 16-byte blocks; GCM turns it into a stream
cipher (by encrypting a counter) and adds a tag (GHASH, a polynomial like Poly1305's).
For learning only: it's slow, and its timing depends on the data.
"""
import sys


# ---------------------------------------------------------------- the S-box, computed rather than copied

def _xtime(a):
    return ((a << 1) ^ 0x1B) & 0xFF if a & 0x80 else a << 1


def _gmul(a, b):
    out = 0
    while b:
        if b & 1:
            out ^= a
        a, b = _xtime(a), b >> 1
    return out


def _sbox():
    box = []
    for x in range(256):
        inv = next((y for y in range(1, 256) if _gmul(x, y) == 1), 0)      # the inverse in GF(2^8)
        s = inv
        for k in range(1, 5):
            s ^= ((inv << k) | (inv >> (8 - k))) & 0xFF                   # the affine step
        box.append(s ^ 0x63)
    return box


SBOX = _sbox()


# ---------------------------------------------------------------- AES-128, encryption only (all GCM needs)

# --8<-- [start:aes]
def expand_key(key):
    words = [list(key[i:i + 4]) for i in range(0, 16, 4)]
    rcon = 1
    for i in range(4, 44):
        w = list(words[i - 1])
        if i % 4 == 0:
            w = [SBOX[b] for b in w[1:] + w[:1]]
            w[0] ^= rcon
            rcon = _xtime(rcon)
        words.append([a ^ b for a, b in zip(words[i - 4], w)])
    return [sum(words[r * 4:r * 4 + 4], []) for r in range(11)]


def encrypt_block(round_keys, block):
    s = [a ^ b for a, b in zip(block, round_keys[0])]
    for r in range(1, 11):
        s = [SBOX[b] for b in s]                                           # SubBytes
        s = [s[(i + 4 * (i % 4)) % 16] for i in range(16)]                 # ShiftRows (column-major state)
        if r < 10:                                                         # MixColumns
            t = []
            for c in range(4):
                a = s[4 * c:4 * c + 4]
                t += [_xtime(a[0]) ^ _xtime(a[1]) ^ a[1] ^ a[2] ^ a[3],
                      a[0] ^ _xtime(a[1]) ^ _xtime(a[2]) ^ a[2] ^ a[3],
                      a[0] ^ a[1] ^ _xtime(a[2]) ^ _xtime(a[3]) ^ a[3],
                      _xtime(a[0]) ^ a[0] ^ a[1] ^ a[2] ^ _xtime(a[3])]
            s = t
        s = [a ^ b for a, b in zip(s, round_keys[r])]                     # AddRoundKey
    return bytes(s)
# --8<-- [end:aes]


def aes_ecb(key, block):
    return encrypt_block(expand_key(key), block)


# ---------------------------------------------------------------- GCM

def _gf_mult(x, y):
    """Multiply in GF(2^128), GCM's bit order (the first bit is the highest power)."""
    z, v = 0, y
    for i in range(127, -1, -1):
        if x >> i & 1:
            z ^= v
        v = (v >> 1) ^ (0xE1 << 120) if v & 1 else v >> 1
    return z


def _ghash(h, aad, ct):
    def blocks(data):
        data += bytes(-len(data) % 16)
        return [int.from_bytes(data[i:i + 16], "big") for i in range(0, len(data), 16)]
    y = 0
    for b in blocks(aad) + blocks(ct) + [(len(aad) * 8) << 64 | len(ct) * 8]:
        y = _gf_mult(y ^ b, h)
    return y


def _ctr(rk, j0, data):
    out = bytearray()
    counter = int.from_bytes(j0[12:], "big")
    for i in range(0, len(data), 16):
        counter = (counter + 1) & 0xFFFFFFFF
        stream = encrypt_block(rk, j0[:12] + counter.to_bytes(4, "big"))
        out += bytes(a ^ b for a, b in zip(data[i:i + 16], stream))
    return bytes(out)


# --8<-- [start:gcm]
def seal(key, nonce, plaintext, aad=b""):
    rk = expand_key(key)
    h = int.from_bytes(encrypt_block(rk, bytes(16)), "big")
    j0 = nonce + b"\x00\x00\x00\x01"
    ct = _ctr(rk, j0, plaintext)
    tag = _ghash(h, aad, ct) ^ int.from_bytes(encrypt_block(rk, j0), "big")
    return ct + tag.to_bytes(16, "big")


def open_(key, nonce, sealed, aad=b""):
    rk = expand_key(key)
    ct, tag = sealed[:-16], sealed[-16:]
    h = int.from_bytes(encrypt_block(rk, bytes(16)), "big")
    j0 = nonce + b"\x00\x00\x00\x01"
    expected = _ghash(h, aad, ct) ^ int.from_bytes(encrypt_block(rk, j0), "big")
    if expected.to_bytes(16, "big") != tag:
        raise ValueError("authentication failed")
    return _ctr(rk, j0, ct)
# --8<-- [end:gcm]


def test():
    ok = aes_ecb(bytes(range(16)), bytes.fromhex("00112233445566778899aabbccddeeff")).hex() == "69c4e0d86a7b0430d8cdb78070b4c55a"
    ok &= seal(bytes(16), bytes(12), b"").hex() == "58e2fccefa7e3061367f1d57a4e7455a"
    ok &= seal(bytes(16), bytes(12), bytes(16)).hex() == "0388dace60b6a392f328c2b971b2fe78" "ab6e47d42cec13bdf53a67b21257bddf"
    k = bytes.fromhex("feffe9928665731c6d6a8f9467308308")
    iv = bytes.fromhex("cafebabefacedbaddecaf888")
    p = bytes.fromhex("d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a721c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b39")
    a = bytes.fromhex("feedfacedeadbeeffeedfacedeadbeefabaddad2")
    ok &= seal(k, iv, p, a)[-16:].hex() == "5bc94fbc3221a5db94fae95ae7121a47"
    ok &= open_(k, iv, seal(k, iv, p, a), a) == p
    print("AES and GCM test vectors: all match" if ok else "MISMATCH")


if __name__ == "__main__":
    test()
