#!/usr/bin/env python3
"""Chapter 42 lab: Chapter 32's TLS 1.3 client, with a post-quantum key exchange.

    python3 pqtls.py example.org          fetch a page, agreeing keys with X25519MLKEM768
    python3 pqtls.py www.google.com

Everything comes from ../ch32/tls13.py except the key exchange. Our key share is an ML-KEM-768
encapsulation key followed by an X25519 public key; the server's is an ML-KEM ciphertext followed by
its own X25519 public key; the shared secret is both secrets, one after the other. To learn it, an
eavesdropper would have to break both: X25519 with a quantum computer, and ML-KEM with anything.
Keep the ch31, ch32 and ch42 folders side by side.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "ch32"), str(HERE.parent / "ch31")]
import mlkem    # noqa: E402  (this folder)
import tls13    # noqa: E402  (Chapter 32)
import x25519   # noqa: E402  (Chapter 31)


# --8<-- [start:hybrid]
def hybrid_keypair():
    ek, dk = mlkem.keygen()
    x_private, x_public = x25519.keypair()
    return (dk, x_private), ek + x_public                       # our key share: 1,184 + 32 bytes


def hybrid_shared(private, server_share):
    dk, x_private = private
    ciphertext, x_public = server_share[:1088], server_share[1088:]
    return mlkem.decaps(dk, ciphertext) + x25519.x25519(x_private, x_public)   # 32 + 32 bytes


tls13.GROUP, tls13.KEX_NAME = 0x11EC, "X25519MLKEM768"          # the group's number, from IANA
tls13.keypair, tls13.x25519 = hybrid_keypair, hybrid_shared     # swap them into Chapter 32's client
# --8<-- [end:hybrid]

if __name__ == "__main__":
    tls13.main()
