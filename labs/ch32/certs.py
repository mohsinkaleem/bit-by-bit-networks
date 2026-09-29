#!/usr/bin/env python3
"""Chapter 32 lab: certificates and signatures, in pure Python. tls13.py imports this.

    python3 certs.py example.org       fetch a site's certificate chain, take it apart, check every signature
    python3 certs.py --test            check the signature code against keys and signatures made by openssl

A certificate is written in DER, a compact binary form of ASN.1: every item is a
tag byte, a length, and the contents (which may themselves be items). This file reads
just enough of it to find the names, dates and public key, and checks the three kinds
of signature the web uses: RSA (PKCS #1 and PSS), ECDSA (P-256 and P-384) and Ed25519.
For learning only: real implementations must also be careful about timing and malformed input.
"""
import hashlib
import socket
import ssl
import sys

# ---------------------------------------------------------------- DER: tag, length, value

# --8<-- [start:der]
def read_item(data, i=0):
    """One DER item starting at data[i]: returns (tag, contents, index just after it)."""
    tag, length = data[i], data[i + 1]
    i += 2
    if length & 0x80:                               # long form: the next (length & 0x7f) bytes are the length
        n = length & 0x7F
        length = int.from_bytes(data[i:i + n], "big")
        i += n
    return tag, data[i:i + length], i + length


def items(data):
    """All the items inside a SEQUENCE or SET."""
    out, i = [], 0
    while i < len(data):
        tag, value, nxt = read_item(data, i)
        out.append((tag, value, data[i:nxt]))       # (tag, contents, the whole item including its header)
        i = nxt
    return out


def oid(value):
    """Object identifiers, like 2.5.4.3 ('common name'), are how ASN.1 names things."""
    first, parts, n = value[0], [], 0
    parts += [first // 40, first % 40]
    for b in value[1:]:
        n = (n << 7) | (b & 0x7F)
        if not b & 0x80:
            parts.append(n)
            n = 0
    return ".".join(map(str, parts))
# --8<-- [end:der]


NAMES = {"2.5.4.3": "CN", "2.5.4.10": "O", "2.5.4.6": "C", "2.5.4.11": "OU", "2.5.4.8": "ST", "2.5.4.7": "L"}
KEY_TYPES = {"1.2.840.113549.1.1.1": "RSA", "1.2.840.10045.2.1": "EC", "1.3.101.112": "Ed25519"}
CURVES = {"1.2.840.10045.3.1.7": "P-256", "1.3.132.0.34": "P-384"}
SIG_ALGS = {"1.2.840.113549.1.1.11": ("rsa-pkcs1", "sha256"), "1.2.840.113549.1.1.12": ("rsa-pkcs1", "sha384"),
            "1.2.840.113549.1.1.13": ("rsa-pkcs1", "sha512"), "1.2.840.10045.4.3.2": ("ecdsa", "sha256"),
            "1.2.840.10045.4.3.3": ("ecdsa", "sha384"), "1.3.101.112": ("ed25519", None)}


def parse_name(value):
    out = {}
    for _, rdn, _ in items(value):                  # SET { SEQUENCE { oid, string } }
        for _, pair, _ in items(rdn):
            (_, o, _), (_, s, _) = items(pair)
            out[NAMES.get(oid(o), oid(o))] = s.decode("utf-8", "replace")
    return out


def parse_time(tag, value):
    s = value.decode()
    if tag == 0x17:                                 # UTCTime: YYMMDDhhmmssZ
        s = ("19" if int(s[:2]) >= 50 else "20") + s
    return f"{s[:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}"


# --8<-- [start:parse]
def parse(der):
    """The parts of a certificate that matter for checking it."""
    (_, tbs, tbs_whole), (_, alg, _), (_, sig_bits, _) = items(read_item(der)[1])
    fields = items(tbs)
    if fields[0][0] == 0xA0:                        # [0] version (v3 certificates have it)
        fields = fields[1:]
    serial, _, issuer, validity, subject, spki = fields[:6]
    cert = {"tbs": tbs_whole, "sig_alg": oid(items(alg)[0][1]), "signature": sig_bits[1:],   # skip BIT STRING's pad byte
            "serial": int.from_bytes(serial[1], "big"),
            "issuer": parse_name(issuer[1]), "subject": parse_name(subject[1]), "names": []}
    (t1, v1, _), (t2, v2, _) = items(validity[1])
    cert["not_before"], cert["not_after"] = parse_time(t1, v1), parse_time(t2, v2)
    (_, key_alg, _), (_, key_bits, _) = items(spki[1])
    alg_parts = items(key_alg)
    cert["key_type"] = KEY_TYPES.get(oid(alg_parts[0][1]), oid(alg_parts[0][1]))
    raw_key = key_bits[1:]
    if cert["key_type"] == "RSA":
        (_, n, _), (_, e, _) = items(read_item(raw_key)[1])
        cert["key"] = (int.from_bytes(n, "big"), int.from_bytes(e, "big"))
        cert["key_desc"] = f"RSA {cert['key'][0].bit_length()}-bit"
    elif cert["key_type"] == "EC":
        curve = CURVES.get(oid(alg_parts[1][1]), "?")
        size = (len(raw_key) - 1) // 2               # 04 || x || y
        cert["key"] = (curve, int.from_bytes(raw_key[1:1 + size], "big"), int.from_bytes(raw_key[1 + size:], "big"))
        cert["key_desc"] = f"ECDSA {curve}"
    else:
        cert["key"], cert["key_desc"] = raw_key, cert["key_type"]
    for tag, value, _ in fields[6:]:
        if tag == 0xA3:                             # [3] extensions
            for _, ext, _ in items(read_item(value)[1]):
                parts = items(ext)
                if oid(parts[0][1]) == "2.5.29.17":  # subjectAltName: the names this certificate is for
                    for gtag, gval, _ in items(read_item(parts[-1][1])[1]):
                        if gtag == 0x82:            # [2] dNSName
                            cert["names"].append(gval.decode())
    return cert
# --8<-- [end:parse]


def describe(der):
    c = parse(der)
    who = lambda n: n.get("CN") or n.get("O") or "?"
    return {"subject": who(c["subject"]), "issuer": who(c["issuer"]), "key": c["key_desc"],
            "not_after": c["not_after"][:10], "names": c["names"] or [who(c["subject"])]}


def parse_certificate_message(body):
    """TLS 1.3's Certificate message: a request context, then a list of (certificate, extensions)."""
    i = 1 + body[0]
    total = int.from_bytes(body[i:i + 3], "big")
    i += 3
    end, chain = i + total, []
    while i < end:
        n = int.from_bytes(body[i:i + 3], "big")
        chain.append(body[i + 3:i + 3 + n])
        i += 3 + n
        i += 2 + int.from_bytes(body[i:i + 2], "big")   # skip this certificate's extensions
    return chain


# ---------------------------------------------------------------- RSA

DIGEST_INFO = {"sha256": bytes.fromhex("3031300d060960864801650304020105000420"),
               "sha384": bytes.fromhex("3041300d060960864801650304020205000430"),
               "sha512": bytes.fromhex("3051300d060960864801650304020305000440")}


# --8<-- [start:rsa]
def rsa_pkcs1_verify(key, message, sig, hash_name):
    """The classic RSA signature: sig^e mod n must be 00 01 FF FF … FF 00, then the message's fingerprint."""
    n, e = key
    k = (n.bit_length() + 7) // 8
    em = pow(int.from_bytes(sig, "big"), e, n).to_bytes(k, "big")
    digest = DIGEST_INFO[hash_name] + hashlib.new(hash_name, message).digest()
    return em == b"\x00\x01" + b"\xff" * (k - 3 - len(digest)) + b"\x00" + digest


def mgf1(seed, length, hash_name):
    out, counter = b"", 0
    while len(out) < length:
        out += hashlib.new(hash_name, seed + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:length]


def rsa_pss_verify(key, message, sig, hash_name):
    """RSA-PSS, the only kind of RSA signature TLS 1.3 allows in the handshake: the fingerprint is mixed with random salt."""
    n, e = key
    em_bits = n.bit_length() - 1
    em_len = (em_bits + 7) // 8
    m = pow(int.from_bytes(sig, "big"), e, n)
    if m.bit_length() > em_bits:
        return False
    em = m.to_bytes(em_len, "big")
    h_len = hashlib.new(hash_name).digest_size
    if em[-1] != 0xBC:
        return False
    masked_db, h = em[:em_len - h_len - 1], em[em_len - h_len - 1:-1]
    db = bytearray(a ^ b for a, b in zip(masked_db, mgf1(h, len(masked_db), hash_name)))
    db[0] &= 0xFF >> (8 * em_len - em_bits)
    salt = db[-h_len:]                               # TLS uses a salt as long as the hash
    if db[:-h_len - 1].strip(b"\0") or db[-h_len - 1] != 1:
        return False
    m_hash = hashlib.new(hash_name, message).digest()
    return hashlib.new(hash_name, b"\0" * 8 + m_hash + bytes(salt)).digest() == h
# --8<-- [end:rsa]


# ---------------------------------------------------------------- ECDSA on the NIST curves

CURVE_PARAMS = {   # y² = x³ − 3x + b (mod p); G is the starting point, n the number of points it reaches
    "P-256": dict(p=0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF,
                  b=0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B,
                  G=(0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
                     0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5),
                  n=0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551),
    "P-384": dict(p=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFFFF0000000000000000FFFFFFFF,
                  b=0xB3312FA7E23EE7E4988E056BE3F82D19181D9C6EFE8141120314088F5013875AC656398D8A2ED19D2A85C8EDD3EC2AEF,
                  G=(0xAA87CA22BE8B05378EB1C71EF320AD746E1D3B628BA79B9859F741E082542A385502F25DBF55296C3A545E3872760AB7,
                     0x3617DE4A96262C6F5D9E98BF9292DC29F8F41DBD289A147CE9DA3113B5F0B8C00A60B1CE1D7E819D7A431D7C90EA0E5F),
                  n=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFC7634D81F4372DDF581A0DB248B0A77AECEC196ACCC52973),
}


# --8<-- [start:ecdsa]
def ec_add(P, Q, p):
    """Add two points on the curve (None is the 'point at infinity', which acts like zero)."""
    if P is None:
        return Q
    if Q is None:
        return P
    (x1, y1), (x2, y2) = P, Q
    if x1 == x2 and (y1 + y2) % p == 0:
        return None
    if P == Q:
        slope = (3 * x1 * x1 - 3) * pow(2 * y1, -1, p) % p        # the tangent (a = −3 on these curves)
    else:
        slope = (y2 - y1) * pow(x2 - x1, -1, p) % p               # the line through both points
    x3 = (slope * slope - x1 - x2) % p
    return x3, (slope * (x1 - x3) - y1) % p


def ec_mul(k, P, p):
    """k × P by doubling and adding, one bit of k at a time."""
    R = None
    for bit in bin(k)[2:]:
        R = ec_add(R, R, p)
        if bit == "1":
            R = ec_add(R, P, p)
    return R


def ecdsa_verify(key, message, sig, hash_name):
    curve, qx, qy = key
    c = CURVE_PARAMS[curve]
    (_, r, _), (_, s, _) = items(read_item(sig)[1])     # the signature is SEQUENCE { r, s }
    r, s = int.from_bytes(r, "big"), int.from_bytes(s, "big")
    n = c["n"]
    if not (0 < r < n and 0 < s < n):
        return False
    e = int.from_bytes(hashlib.new(hash_name, message).digest()[:(n.bit_length() + 7) // 8], "big")
    w = pow(s, -1, n)
    X = ec_add(ec_mul(e * w % n, c["G"], c["p"]), ec_mul(r * w % n, (qx, qy), c["p"]), c["p"])
    return X is not None and X[0] % n == r
# --8<-- [end:ecdsa]


# ---------------------------------------------------------------- Ed25519 (RFC 8032)

ED_P = 2 ** 255 - 19
ED_L = 2 ** 252 + 27742317777372353535851937790883648493
ED_D = -121665 * pow(121666, -1, ED_P) % ED_P
ED_I = pow(2, (ED_P - 1) // 4, ED_P)                  # a square root of −1


def ed_add(P, Q):
    (X1, Y1, Z1, T1), (X2, Y2, Z2, T2) = P, Q
    A, B = (Y1 - X1) * (Y2 - X2) % ED_P, (Y1 + X1) * (Y2 + X2) % ED_P
    C, D = T1 * 2 * ED_D * T2 % ED_P, Z1 * 2 * Z2 % ED_P
    E, F, G, H = B - A, D - C, D + C, B + A
    return E * F % ED_P, G * H % ED_P, F * G % ED_P, E * H % ED_P


def ed_mul(k, P):
    Q = (0, 1, 1, 0)
    while k:
        if k & 1:
            Q = ed_add(Q, P)
        P, k = ed_add(P, P), k >> 1
    return Q


def ed_decode(b):
    y = int.from_bytes(b, "little")
    sign, y = y >> 255, y & ((1 << 255) - 1)
    if y >= ED_P:
        return None
    x2 = (y * y - 1) * pow(ED_D * y * y + 1, -1, ED_P) % ED_P
    x = pow(x2, (ED_P + 3) // 8, ED_P)
    if (x * x - x2) % ED_P:
        x = x * ED_I % ED_P
    if (x * x - x2) % ED_P or (x == 0 and sign):
        return None
    if x & 1 != sign:
        x = ED_P - x
    return x, y, 1, x * y % ED_P


def ed_equal(P, Q):
    return (P[0] * Q[2] - Q[0] * P[2]) % ED_P == 0 and (P[1] * Q[2] - Q[1] * P[2]) % ED_P == 0


ED_G = ed_decode(bytes.fromhex("5866666666666666666666666666666666666666666666666666666666666666"))


def ed25519_verify(public, message, sig, _hash=None):
    A, R = ed_decode(public), ed_decode(sig[:32])
    s = int.from_bytes(sig[32:], "little")
    if A is None or R is None or s >= ED_L:
        return False
    h = int.from_bytes(hashlib.sha512(sig[:32] + public + message).digest(), "little") % ED_L
    return ed_equal(ed_mul(s, ED_G), ed_add(R, ed_mul(h, A)))       # s·B == R + h·A


# ---------------------------------------------------------------- putting it together

TLS_SCHEMES = {0x0401: ("rsa-pkcs1", "sha256"), 0x0501: ("rsa-pkcs1", "sha384"),
               0x0403: ("ecdsa", "sha256"), 0x0503: ("ecdsa", "sha384"),
               0x0804: ("rsa-pss", "sha256"), 0x0805: ("rsa-pss", "sha384"), 0x0807: ("ed25519", None)}
CHECKERS = {"rsa-pkcs1": rsa_pkcs1_verify, "rsa-pss": rsa_pss_verify, "ecdsa": ecdsa_verify, "ed25519": ed25519_verify}


def verify_with(cert, kind, hash_name, message, sig):
    try:
        return CHECKERS[kind](cert["key"], message, sig, hash_name)
    except (ValueError, IndexError, KeyError):
        return False


def verify(der, scheme, message, sig):
    """Check a TLS 1.3 signature (scheme = the 16-bit code from the handshake) with this certificate's public key."""
    if scheme not in TLS_SCHEMES:
        return False
    kind, hash_name = TLS_SCHEMES[scheme]
    return verify_with(parse(der), kind, hash_name, message, sig)


def check_chain(chain):
    """Is each certificate signed by the next one's key? Returns a list of (subject, issuer, ok)."""
    parsed = [parse(der) for der in chain]
    out = []
    for cert, issuer in zip(parsed, parsed[1:]):
        kind, hash_name = SIG_ALGS.get(cert["sig_alg"], (None, None))
        ok = kind is not None and verify_with(issuer, kind, hash_name, cert["tbs"], cert["signature"])
        out.append((describe_name(cert["subject"]), describe_name(issuer["subject"]), ok))
    return out


def describe_name(n):
    return n.get("CN") or n.get("O") or "?"


# ---------------------------------------------------------------- the command line

def fetch_chain(host):
    """The chain a server sends, as DER (Python 3.13+ can give us all of it; older ones just the first)."""
    ctx = ssl.create_default_context()
    with ctx.wrap_socket(socket.create_connection((host, 443), timeout=10), server_hostname=host) as s:
        if hasattr(s, "get_unverified_chain"):
            return [c if isinstance(c, bytes) else c.public_bytes(ssl._ssl.ENCODING_DER) for c in s.get_unverified_chain()]
        return [s.getpeercert(binary_form=True)]


def show(host):
    chain = fetch_chain(host)
    print(f"{host} sent {len(chain)} certificate(s):\n")
    for i, der in enumerate(chain):
        c = parse(der)
        print(f"#{i}  subject {describe_name(c['subject'])}")
        print(f"    issuer  {describe_name(c['issuer'])}")
        print(f"    valid   {c['not_before']} to {c['not_after']}")
        print(f"    key     {c['key_desc']};  signed with {SIG_ALGS.get(c['sig_alg'], (c['sig_alg'],))[0]}"
              f" {SIG_ALGS.get(c['sig_alg'], (None, ''))[1] or ''}")
        if c["names"]:
            more = f" (+{len(c['names']) - 5} more)" if len(c["names"]) > 5 else ""
            print(f"    names   {', '.join(c['names'][:5])}{more}")
    print()
    for i, (subject, issuer, ok) in enumerate(check_chain(chain)):
        print(f"{'✓' if ok else '✗'} #{i} ({subject}) {'is' if ok else 'is NOT'} signed by #{i + 1}'s private key")
    last = parse(chain[-1])
    if last["issuer"] == last["subject"]:
        print(f"  #{len(chain) - 1} signed itself: it's a root, and only worth anything if this computer already trusts it")
    else:
        print(f"  #{len(chain) - 1}'s issuer, {describe_name(last['issuer'])}, wasn't sent: this computer must already have it, as a trusted root")


def test():
    import subprocess
    import tempfile
    from pathlib import Path
    msg = b"I owe Bob 5 pounds"
    ok = True
    with tempfile.TemporaryDirectory() as d:
        Path(d, "m").write_bytes(msg)
        for name, genargs, kind, hash_name, extra in [
                ("RSA PKCS#1", ["-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048"], "rsa-pkcs1", "sha256", []),
                ("RSA-PSS", ["-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048"], "rsa-pss", "sha256",
                 ["-sigopt", "rsa_padding_mode:pss", "-sigopt", "rsa_pss_saltlen:32"]),
                ("ECDSA P-256", ["-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-256"], "ecdsa", "sha256", []),
                ("ECDSA P-384", ["-algorithm", "EC", "-pkeyopt", "ec_paramgen_curve:P-384"], "ecdsa", "sha384", []),
                ("Ed25519", ["-algorithm", "ED25519"], "ed25519", None, [])]:
            key, crt, sig = Path(d, "k.pem"), Path(d, "c.der"), Path(d, "s")
            subprocess.run(["openssl", "genpkey", *genargs, "-out", key], check=True, capture_output=True)
            subprocess.run(["openssl", "req", "-new", "-x509", "-key", key, "-subj", "/CN=test.example", "-days", "1",
                            "-outform", "DER", "-out", crt], check=True, capture_output=True)
            if kind == "ed25519":
                subprocess.run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", key, "-in", Path(d, "m"), "-out", sig],
                               check=True, capture_output=True)
            else:
                subprocess.run(["openssl", "dgst", f"-{hash_name}", "-sign", key, *extra, "-out", sig, Path(d, "m")],
                               check=True, capture_output=True)
            cert = parse(crt.read_bytes())
            good = verify_with(cert, kind, hash_name, msg, sig.read_bytes())
            bad = verify_with(cert, kind, hash_name, msg + b"0", sig.read_bytes())
            selfsig = check_chain([crt.read_bytes(), crt.read_bytes()])[0][2]
            print(f"{name:<12} genuine: {good}   tampered: {bad}   certificate's own signature: {selfsig}")
            ok &= good and not bad and selfsig
    print("all signature checks behave" if ok else "SOMETHING IS WRONG")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test()
    else:
        show(sys.argv[1] if len(sys.argv) > 1 else "example.org")
