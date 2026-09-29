#!/usr/bin/env python3
"""Chapter 42 lab: ML-KEM-768, the post-quantum key exchange, from scratch (NIST's FIPS 203).

    python3 mlkem.py             make a key pair, lock a random secret with it, and unlock it again
    python3 mlkem.py --openssl   check this code against OpenSSL (3.5 or newer), in both directions

A "key encapsulation mechanism": Alice publishes an encapsulation key; Bob uses it to lock up a fresh
32-byte secret, and sends the result (the ciphertext); only Alice's decapsulation key can open it.
Its security rests on "learning with errors": equations that would be easy to solve, if it weren't
for a little deliberate noise in every one. Python 3.9+, standard library only (hashlib has SHA-3).
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import time

Q, N = 3329, 256                     # arithmetic mod 3329, on polynomials with 256 coefficients
K, ETA1, ETA2, DU, DV = 3, 2, 2, 10, 4   # ML-KEM-768: 3×3 matrices, small noise, how much to compress


# --8<-- [start:ntt]
def bitrev7(i):
    return int(f"{i:07b}"[::-1], 2)


ZETAS = [pow(17, bitrev7(i), Q) for i in range(128)]           # 17 is a 256th root of 1, mod 3329
GAMMAS = [pow(17, 2 * bitrev7(i) + 1, Q) for i in range(128)]


def ntt(f):
    """Rewrite a polynomial so that multiplying two of them is quick (like a fast Fourier transform)."""
    f, i, length = list(f), 1, 128
    while length >= 2:
        for start in range(0, N, 2 * length):
            zeta, i = ZETAS[i], i + 1
            for j in range(start, start + length):
                t = zeta * f[j + length] % Q
                f[j + length], f[j] = (f[j] - t) % Q, (f[j] + t) % Q
        length //= 2
    return f


def ntt_inverse(f):
    f, i, length = list(f), 127, 2
    while length <= 128:
        for start in range(0, N, 2 * length):
            zeta, i = ZETAS[i], i - 1
            for j in range(start, start + length):
                t = f[j]
                f[j], f[j + length] = (t + f[j + length]) % Q, zeta * (f[j + length] - t) % Q
        length *= 2
    return [x * 3303 % Q for x in f]                             # 3303 × 128 = 1, mod 3329


def times(f, g):
    """Multiply two polynomials that are both in NTT form: 128 little multiplications of pairs."""
    h = [0] * N
    for i in range(128):
        a0, a1, b0, b1 = f[2 * i], f[2 * i + 1], g[2 * i], g[2 * i + 1]
        h[2 * i] = (a0 * b0 + a1 * b1 * GAMMAS[i]) % Q
        h[2 * i + 1] = (a0 * b1 + a1 * b0) % Q
    return h


def plus(f, g):
    return [(a + b) % Q for a, b in zip(f, g)]
# --8<-- [end:ntt]


# ---------------------------------------------------------------- packing numbers into bytes

def encode(f, d):
    """256 numbers of d bits each → 32·d bytes."""
    return sum(x << (i * d) for i, x in enumerate(f)).to_bytes(32 * d, "little")


def decode(b, d):
    big, mask = int.from_bytes(b, "little"), (1 << d) - 1
    return [(big >> (i * d)) & mask for i in range(N)] if d < 12 else [((big >> (i * 12)) & 4095) % Q for i in range(N)]


def compress(f, d):                 # keep only the top d bits of each number (throwing away a little accuracy)
    return [((x << d) + Q // 2) // Q % (1 << d) for x in f]


def decompress(f, d):
    return [(y * Q + (1 << (d - 1))) >> d for y in f]


# ---------------------------------------------------------------- randomness, from seeds

def sample_ntt(seed):
    """A random-looking polynomial (already in NTT form), deterministically from a 34-byte seed."""
    out, n = [], 840
    while True:
        b = hashlib.shake_128(seed).digest(n)
        out, i = [], 0
        while len(out) < N and i + 3 <= n:
            d1, d2 = b[i] + 256 * (b[i + 1] % 16), b[i + 1] // 16 + 16 * b[i + 2]
            if d1 < Q:
                out.append(d1)
            if d2 < Q and len(out) < N:
                out.append(d2)
            i += 3
        if len(out) == N:
            return out
        n *= 2


def small_noise(seed, nonce, eta):
    """A polynomial with tiny coefficients (−2 … 2): the 'errors' in learning with errors."""
    bits = int.from_bytes(hashlib.shake_256(seed + bytes([nonce])).digest(64 * eta), "little")
    f = []
    for i in range(N):
        x = bin((bits >> (2 * i * eta)) & ((1 << eta) - 1)).count("1")
        y = bin((bits >> (2 * i * eta + eta)) & ((1 << eta) - 1)).count("1")
        f.append((x - y) % Q)
    return f


def matrix(rho):
    return [[sample_ntt(rho + bytes([j, i])) for j in range(K)] for i in range(K)]


# ---------------------------------------------------------------- the public-key encryption inside

# --8<-- [start:pke]
def pke_keygen(d):
    rho, sigma = (lambda h: (h[:32], h[32:]))(hashlib.sha3_512(d + bytes([K])).digest())
    A = matrix(rho)                                                        # a public, random 3×3 matrix
    s = [ntt(small_noise(sigma, i, ETA1)) for i in range(K)]              # the secret: small numbers
    e = [ntt(small_noise(sigma, K + i, ETA1)) for i in range(K)]          # the errors: small numbers
    t = [plus([sum(x) % Q for x in zip(*(times(A[i][j], s[j]) for j in range(K)))], e[i]) for i in range(K)]
    return b"".join(encode(ti, 12) for ti in t) + rho, b"".join(encode(si, 12) for si in s)   # t = A·s + e


def pke_encrypt(ek, m, r):
    t, rho = [decode(ek[384 * i:384 * (i + 1)], 12) for i in range(K)], ek[384 * K:]
    A = matrix(rho)
    y = [ntt(small_noise(r, i, ETA1)) for i in range(K)]
    e1 = [small_noise(r, K + i, ETA2) for i in range(K)]
    e2 = small_noise(r, 2 * K, ETA2)
    u = [plus(ntt_inverse([sum(x) % Q for x in zip(*(times(A[j][i], y[j]) for j in range(K)))]), e1[i]) for i in range(K)]
    mu = decompress(decode(m, 1), 1)                                      # each bit of m becomes 0 or ≈ q/2
    v = plus(plus(ntt_inverse([sum(x) % Q for x in zip(*(times(t[j], y[j]) for j in range(K)))]), e2), mu)
    return b"".join(encode(compress(ui, DU), DU) for ui in u) + encode(compress(v, DV), DV)


def pke_decrypt(dk, c):
    u = [decompress(decode(c[320 * i:320 * (i + 1)], DU), DU) for i in range(K)]
    v = decompress(decode(c[320 * K:], DV), DV)
    s = [decode(dk[384 * i:384 * (i + 1)], 12) for i in range(K)]
    w = [(a - b) % Q for a, b in zip(v, ntt_inverse([sum(x) % Q for x in zip(*(times(s[i], ntt(u[i])) for i in range(K)))]))]
    return encode(compress(w, 1), 1)                                      # near 0 → 0, near q/2 → 1
# --8<-- [end:pke]


# ---------------------------------------------------------------- ML-KEM itself

# --8<-- [start:kem]
def keygen(d=None, z=None):
    """Returns (encapsulation key, 1,184 bytes: public; decapsulation key, 2,400 bytes: secret)."""
    d, z = d or os.urandom(32), z or os.urandom(32)
    ek, dk_pke = pke_keygen(d)
    return ek, dk_pke + ek + hashlib.sha3_256(ek).digest() + z


def encaps(ek, m=None):
    """Lock up a fresh secret. Returns (the shared secret, 32 bytes; the ciphertext, 1,088 bytes)."""
    m = m or os.urandom(32)
    g = hashlib.sha3_512(m + hashlib.sha3_256(ek).digest()).digest()
    return g[:32], pke_encrypt(ek, m, g[32:])


def decaps(dk, c):
    dk_pke, ek, h, z = dk[:384 * K], dk[384 * K:768 * K + 32], dk[768 * K + 32:768 * K + 64], dk[768 * K + 64:]
    m = pke_decrypt(dk_pke, c)
    g = hashlib.sha3_512(m + h).digest()
    if pke_encrypt(ek, m, g[32:]) != c:            # re-encrypt, and check: a tampered ciphertext gets…
        return hashlib.shake_256(z + c).digest(32)   # …a useless, random-looking secret, and no clue why
    return g[:32]
# --8<-- [end:kem]


# ---------------------------------------------------------------- checking against OpenSSL

def openssl(*args, data=None):
    return subprocess.run(["openssl", *args], input=data, capture_output=True, check=True).stdout


def check_openssl():
    with tempfile.TemporaryDirectory() as tmp:
        key, pub = f"{tmp}/key.pem", f"{tmp}/pub.pem"
        openssl("genpkey", "-algorithm", "ML-KEM-768", "-out", key)
        der = openssl("pkey", "-in", key, "-outform", "DER")
        seed = der[der.index(b"\x04\x40") + 2:][:64]                    # PKCS#8: the 64-byte seed, d and z
        their_ek = openssl("pkey", "-in", key, "-pubout", "-outform", "DER")[-1184:]
        our_ek, our_dk = keygen(seed[:32], seed[32:])
        print(f"1. the same seed gives the same encapsulation key as OpenSSL's: {our_ek == their_ek}")
        openssl("pkey", "-in", key, "-pubout", "-out", pub)
        ct, ss = f"{tmp}/ct.bin", f"{tmp}/ss.bin"
        openssl("pkeyutl", "-encap", "-pubin", "-inkey", pub, "-out", ct, "-secret", ss)
        theirs = open(ss, "rb").read()
        print(f"2. OpenSSL locks up a secret; we unlock it:  {decaps(our_dk, open(ct, 'rb').read()) == theirs}   ({theirs.hex()[:32]}…)")
        secret, c = encaps(their_ek)
        open(ct, "wb").write(c)
        openssl("pkeyutl", "-decap", "-inkey", key, "-in", ct, "-secret", ss)
        print(f"3. we lock up a secret; OpenSSL unlocks it:  {open(ss, 'rb').read() == secret}   ({secret.hex()[:32]}…)")


# --8<-- [start:demo]
def demo():
    t0 = time.perf_counter()
    ek, dk = keygen()                                        # Alice
    t1 = time.perf_counter()
    secret_bob, ciphertext = encaps(ek)                      # Bob, with Alice's public key
    t2 = time.perf_counter()
    secret_alice = decaps(dk, ciphertext)                    # Alice, with her secret key
    t3 = time.perf_counter()
    print(f"Alice's encapsulation key (public): {len(ek):,} bytes   {ek[:12].hex()}…   ({(t1 - t0) * 1000:.0f} ms)")
    print(f"Alice's decapsulation key (secret): {len(dk):,} bytes")
    print(f"Bob's ciphertext:                   {len(ciphertext):,} bytes   {ciphertext[:12].hex()}…   ({(t2 - t1) * 1000:.0f} ms)")
    print(f"the secret Bob locked up:           {secret_bob.hex()}")
    print(f"the secret Alice unlocked:          {secret_alice.hex()}   ({(t3 - t2) * 1000:.0f} ms)")
    broken = bytes([ciphertext[0] ^ 1]) + ciphertext[1:]
    print(f"…and from a ciphertext with one bit flipped: {decaps(dk, broken).hex()}")
# --8<-- [end:demo]


if __name__ == "__main__":
    check_openssl() if "--openssl" in sys.argv else demo()
