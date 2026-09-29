#!/usr/bin/env python3
"""Chapter 31 lab: ChaCha20-Poly1305, the cipher your phone probably uses for HTTPS, in pure Python.

    python3 chacha.py           encrypt a message, tamper with it, and watch decryption refuse
    python3 chacha.py --test    check against the test vectors in RFC 8439

ChaCha20 turns a 32-byte key and a 12-byte nonce into an endless stream of random-looking bytes,
which are XORed with the message (a stream cipher, like a one-time pad, but with a short key).
Poly1305 adds a 16-byte tag that proves nobody changed a single bit. Chapter 32's TLS client imports this.
"""
import os
import struct
import sys


# --8<-- [start:chacha]
def quarter_round(s, a, b, c, d):
    """Add, rotate, XOR: four simple steps, repeated until the bits are thoroughly mixed."""
    rot = lambda v, n: ((v << n) & 0xFFFFFFFF) | (v >> (32 - n))
    s[a] = (s[a] + s[b]) & 0xFFFFFFFF; s[d] = rot(s[d] ^ s[a], 16)
    s[c] = (s[c] + s[d]) & 0xFFFFFFFF; s[b] = rot(s[b] ^ s[c], 12)
    s[a] = (s[a] + s[b]) & 0xFFFFFFFF; s[d] = rot(s[d] ^ s[a], 8)
    s[c] = (s[c] + s[d]) & 0xFFFFFFFF; s[b] = rot(s[b] ^ s[c], 7)


def chacha20_block(key, counter, nonce):
    """64 bytes of keystream: the block for this key, nonce and counter."""
    state = [0x61707865, 0x3320646E, 0x79622D32, 0x6B206574]         # "expand 32-byte k"
    state += list(struct.unpack("<8I", key)) + [counter] + list(struct.unpack("<3I", nonce))
    s = state[:]
    for _ in range(10):                                               # 20 rounds: columns, then diagonals
        quarter_round(s, 0, 4, 8, 12); quarter_round(s, 1, 5, 9, 13)
        quarter_round(s, 2, 6, 10, 14); quarter_round(s, 3, 7, 11, 15)
        quarter_round(s, 0, 5, 10, 15); quarter_round(s, 1, 6, 11, 12)
        quarter_round(s, 2, 7, 8, 13); quarter_round(s, 3, 4, 9, 14)
    return struct.pack("<16I", *((x + y) & 0xFFFFFFFF for x, y in zip(s, state)))


def chacha20(key, counter, nonce, data):
    out = bytearray()
    for i in range(0, len(data), 64):
        block = chacha20_block(key, counter + i // 64, nonce)
        out += bytes(a ^ b for a, b in zip(data[i:i + 64], block))  # XOR, exactly like a one-time pad
    return bytes(out)
# --8<-- [end:chacha]


# --8<-- [start:poly]
def poly1305(key, msg):
    """A 16-byte tag: evaluate a polynomial made of the message, at a secret point, modulo 2^130 - 5."""
    r = int.from_bytes(key[:16], "little") & 0x0FFFFFFC0FFFFFFC0FFFFFFC0FFFFFFF
    s = int.from_bytes(key[16:], "little")
    p, acc = (1 << 130) - 5, 0
    for i in range(0, len(msg), 16):
        n = int.from_bytes(msg[i:i + 16] + b"\x01", "little")        # each 16 bytes, plus a 1 on top
        acc = (acc + n) * r % p
    return ((acc + s) & ((1 << 128) - 1)).to_bytes(16, "little")
# --8<-- [end:poly]


# --8<-- [start:aead]
def pad16(b):
    return b"\0" * (-len(b) % 16)


def seal(key, nonce, plaintext, aad=b""):
    """Encrypt and authenticate. aad is data that isn't secret but mustn't be changed (like a header)."""
    otk = chacha20_block(key, 0, nonce)[:32]                          # block 0 makes the one-time Poly1305 key
    ciphertext = chacha20(key, 1, nonce, plaintext)                   # blocks 1, 2, 3… encrypt the message
    mac_data = aad + pad16(aad) + ciphertext + pad16(ciphertext) + struct.pack("<QQ", len(aad), len(ciphertext))
    return ciphertext + poly1305(otk, mac_data)


def open_(key, nonce, sealed, aad=b""):
    ciphertext, tag = sealed[:-16], sealed[-16:]
    otk = chacha20_block(key, 0, nonce)[:32]
    mac_data = aad + pad16(aad) + ciphertext + pad16(ciphertext) + struct.pack("<QQ", len(aad), len(ciphertext))
    if poly1305(otk, mac_data) != tag:                                # (real code compares in constant time)
        raise ValueError("authentication failed: this message was changed, or the key is wrong")
    return chacha20(key, 1, nonce, ciphertext)
# --8<-- [end:aead]


def test():
    # RFC 8439 section 2.4.2 (ChaCha20) and 2.8.2 (the AEAD)
    key = bytes(range(32))
    nonce = bytes.fromhex("000000000000004a00000000")
    text = (b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, "
            b"sunscreen would be it.")
    ok1 = chacha20(key, 1, nonce, text)[:16].hex() == "6e2e359a2568f98041ba0728dd0d6981"
    akey = bytes(range(0x80, 0xA0))
    anonce = bytes.fromhex("070000004041424344454647")
    aad = bytes.fromhex("50515253c0c1c2c3c4c5c6c7")
    sealed = seal(akey, anonce, text, aad)
    ok2 = sealed[-16:].hex() == "1ae10b594f09e26a7e902ecbd0600691" and open_(akey, anonce, sealed, aad) == text
    print("RFC 8439 test vectors:", "all match" if ok1 and ok2 else "FAILED")
    return ok1 and ok2


def main():
    if "--test" in sys.argv:
        sys.exit(0 if test() else 1)
    key, nonce = os.urandom(32), os.urandom(12)
    msg = b"Meet me at the old oak at midnight. -A"
    sealed = seal(key, nonce, msg)
    print(f"message:    {msg.decode()}")
    print(f"sealed:     {sealed[:-16].hex()}  (the same length as the message)")
    print(f"            + tag {sealed[-16:].hex()}")
    print(f"opened:     {open_(key, nonce, sealed).decode()}")
    tampered = bytearray(sealed)
    tampered[0] ^= 1                                                  # Eve flips one bit
    try:
        open_(key, nonce, bytes(tampered))
    except ValueError as e:
        print(f"one bit flipped: {e}")


if __name__ == "__main__":
    main()
