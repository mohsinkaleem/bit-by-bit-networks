#!/usr/bin/env python3
"""Chapter 31 lab: X25519, the key exchange behind almost every TLS connection today, in pure Python.

    python3 x25519.py           Alice and Bob agree on a secret, in public
    python3 x25519.py --test    check against the test vectors in RFC 7748

Diffie-Hellman on an elliptic curve (Curve25519). Private keys are 32 random bytes; public keys
are 32 bytes too. Chapter 32's TLS client imports this file.
"""
import os
import sys

P = 2 ** 255 - 19                  # every number here is "modulo this prime": the curve's name
A24 = 121665                       # (486662 - 2) / 4, a constant of the curve


def clamp(k):
    """The standard tweaks to a private key: clear 3 low bits, clear the top bit, set bit 254."""
    k = bytearray(k)
    k[0] &= 248
    k[31] &= 127
    k[31] |= 64
    return int.from_bytes(k, "little")


# --8<-- [start:ladder]
def x25519(scalar, u_bytes):
    """Multiply the point u by the number scalar, using only its x-coordinate (the Montgomery ladder)."""
    k = clamp(scalar)
    u = int.from_bytes(u_bytes, "little") & ((1 << 255) - 1)
    x2, z2, x3, z3, swap = 1, 0, u, 1, 0
    for t in reversed(range(255)):             # one step per bit of the private key, always the same work
        bit = (k >> t) & 1
        swap ^= bit
        if swap:
            x2, x3, z2, z3 = x3, x2, z3, z2
        swap = bit
        a, b = (x2 + z2) % P, (x2 - z2) % P
        aa, bb = a * a % P, b * b % P
        e = (aa - bb) % P
        c, d = (x3 + z3) % P, (x3 - z3) % P
        da, cb = d * a % P, c * b % P
        x3, z3 = (da + cb) ** 2 % P, u * (da - cb) ** 2 % P
        x2, z2 = aa * bb % P, e * (aa + A24 * e) % P
    if swap:
        x2, z2 = x3, z3
    return (x2 * pow(z2, P - 2, P) % P).to_bytes(32, "little")   # divide: multiply by the inverse
# --8<-- [end:ladder]


BASE = (9).to_bytes(32, "little")     # the agreed starting point on the curve


def keypair():
    private = os.urandom(32)
    return private, x25519(private, BASE)


def test():
    # RFC 7748 section 6.1
    a_priv = bytes.fromhex("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a")
    b_priv = bytes.fromhex("5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb")
    a_pub = x25519(a_priv, BASE)
    b_pub = x25519(b_priv, BASE)
    ok = (a_pub.hex() == "8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a"
          and b_pub.hex() == "de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f"
          and x25519(a_priv, b_pub) == x25519(b_priv, a_pub)
          and x25519(a_priv, b_pub).hex() == "4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742")
    print("RFC 7748 test vectors:", "all match" if ok else "FAILED")
    return ok


def main():
    if "--test" in sys.argv:
        sys.exit(0 if test() else 1)
    a_priv, a_pub = keypair()
    b_priv, b_pub = keypair()
    print(f"Alice's private key (never sent): {a_priv.hex()}")
    print(f"Alice's public key  (sent):       {a_pub.hex()}")
    print(f"Bob's private key   (never sent): {b_priv.hex()}")
    print(f"Bob's public key    (sent):       {b_pub.hex()}")
    print()
    print(f"Alice works out:  x25519(her private, his public) = {x25519(a_priv, b_pub).hex()}")
    print(f"Bob works out:    x25519(his private, her public) = {x25519(b_priv, a_pub).hex()}")
    print("The same 32 bytes. Eve saw both public keys, and can't compute them.")


if __name__ == "__main__":
    main()
