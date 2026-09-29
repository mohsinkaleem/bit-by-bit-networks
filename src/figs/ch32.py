#!/usr/bin/env python3
"""Generate chapter 32 figures.  python3 src/figs/ch32.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- the TLS 1.3 handshake, from the lab's real run

def handshake():
    B, S = "Bob’s laptop", "example.org"
    seq = Seq([(B, 200, "bob"), (S, 600, None)], top=86, scale=30)
    seq.msg(B, S, 0.3, 1.5, "ClientHello", "navy", step="1", sub="191 bytes · key share · SNI example.org")
    seq.msg(S, B, 2.0, 3.2, "ServerHello", "purple", step="2", sub="122 bytes · its key share")
    seq.note(B, 3.7, "X25519 → shared secret → handshake keys", step="2", cls="f-green")
    seq.msg(S, B, 4.3, 5.5, "🔒 EncryptedExtensions, Certificate,", "purple", step="3", label_at=0.42,
            sub="🔒 CertificateVerify, Finished · 3,829 bytes")
    seq.note(B, 6.1, "check the chain, the name, the signature, the MAC", step="4", cls="f-green")
    seq.msg(B, S, 6.8, 8.0, "🔒 Finished + 🔒 GET /", "navy", step="5", sub="the request goes straight after")
    seq.msg(S, B, 8.5, 9.7, "🔒 HTTP/1.1 200 OK …", "green", step="6", sub="and a 🔒 NewSessionTicket, for next time")
    body, bottom = seq.render(18)
    body += ('<g data-show="5">'
             + f'<path d="M{130},{seq.y(0.3):g} L{120},{seq.y(0.3):g} L{120},{seq.y(6.8):g} L{130},{seq.y(6.8):g}" class="line s-orange" stroke-width="2.5"/>'
             + text(110, (seq.y(0.3) + seq.y(6.8)) / 2, "one", "end hand f-orange")
             + text(110, (seq.y(0.3) + seq.y(6.8)) / 2 + 20, "round trip", "end hand f-orange") + "</g>")
    steps = ["Bob’s laptop sends a <strong>ClientHello</strong>: “I speak TLS 1.3, here are the ciphers I know, I want example.org (the <strong>SNI</strong>, server name indication), and here’s my half of a Diffie–Hellman exchange (the <strong>key share</strong>)”. It’s not encrypted: there’s no key yet.",
             "The server answers with a <strong>ServerHello</strong>: its choice of cipher, and its own key share. Now both sides do Chapter 31’s X25519, and get the same secret, which never crossed the network. From it, they derive <strong>handshake keys</strong>.",
             "Everything else the server says is encrypted (🔒) with those keys: its settings, its certificate chain, a <strong>signature</strong> over the whole conversation so far, made with the private key that belongs to the certificate, and a <strong>Finished</strong> message: a MAC over everything, proving nothing was changed on the way.",
             "Bob’s laptop checks all of it. Does the chain lead to a root it trusts? Is the certificate for example.org? Does the signature check out with the certificate’s public key? Is the MAC right? If anything fails, it hangs up.",
             "Its own Finished goes back, and in the same breath, the actual HTTP request, encrypted with fresh <strong>application keys</strong>. The whole handshake cost one round trip before the request could leave. (TLS 1.2 took two.)",
             "The answer comes back encrypted. The server often adds a <strong>session ticket</strong>: a note Bob can show next time, to skip most of this."]
    svg = fig(body, 720, bottom, "The TLS 1.3 handshake between Bob's laptop and example.org: ClientHello, ServerHello, the encrypted server messages, the client's Finished and the request",
              "The TLS 1.3 handshake. The sizes are real, from this chapter’s lab talking to example.org. 🔒 means encrypted.", steps)
    (OUT / "ch32-handshake.svg").write_text(svg)


# ---------------------------------------------------------------- Eve's attempts

def eve():
    b = []
    xs = {"bob": 90, "eve": 360, "srv": 630}
    b.append(f'<use href="#bob" x="{xs["bob"] - 26}" y="16" width="52" height="86"/>')
    b.append(f'<use href="#eve" x="{xs["eve"] - 26}" y="16" width="52" height="86"/>')
    b.append(f'<use href="#server" x="{xs["srv"] - 20}" y="22" width="40" height="66"/>')
    b.append(text(xs["bob"], 118, "Bob", "mid sm b"))
    b.append(text(xs["eve"], 118, "Eve, in the middle", "mid sm b f-purple"))
    b.append(text(xs["srv"], 118, "the bank", "mid sm b"))
    b.append(text(xs["eve"], 134, "(ARP spoofing, Chapter 21)", "mid xs muted"))

    def panel(step, y, lines, verdict):
        out = [f'<g data-show="={step}">']
        for i, s in enumerate(lines):
            out.append(text(360, y + i * 20, s, "mid xs"))
        yb = y + len(lines) * 20 - 4
        out.append(f'<rect x="110" y="{yb}" width="500" height="30" rx="8" class="t-green" stroke="var(--green)" stroke-width="1.5"/>')
        out.append(text(360, yb + 20, verdict, "mid sm b"))
        return "".join(out) + "</g>"

    def arrows(step, left, right, lcls, rcls):
        out = [f'<g data-show="={step}">']
        out.append(f'<path d="M{xs["bob"] + 34},62 L{xs["eve"] - 34},62" class="line {lcls}" stroke-width="2.5" marker-end="url(#ah-{lcls[2:]})"/>')
        if right:
            out.append(f'<path d="M{xs["eve"] + 34},62 L{xs["srv"] - 30},62" class="line {rcls}" stroke-width="2.5" marker-end="url(#ah-{rcls[2:]})"/>')
        out.append(text((xs["bob"] + xs["eve"]) / 2, 52, left, "mid xs b halo"))
        out.append(text((xs["eve"] + xs["srv"]) / 2, 52, right, "mid xs b halo"))
        return "".join(out) + "</g>"
    b.append(arrows(1, "Bob’s key share", "passed on, untouched", "s-blue", "s-blue"))
    b.append(panel(1, 166, ["She sees both key shares go past. To get the secret she needs one of the private keys,",
                            "which never leave Bob’s laptop or the bank. Everything after the hellos is noise to her."],
                   "She learns the site’s name (the SNI), and sizes. Nothing else."))
    b.append(arrows(2, "Bob’s key share", "Eve’s key share!", "s-blue", "s-purple"))
    b.append(panel(2, 166, ["She swaps in her own key shares, to share one secret with Bob and another with the bank.",
                            "But the bank’s CertificateVerify signs the whole conversation, which now has her key share",
                            "in it, and she can’t make a new signature without the bank’s private key."],
                   "Bob’s laptop: “signature invalid”. It hangs up."))
    b.append(arrows(3, "Eve’s own certificate", "", "s-purple", "s-muted"))
    b.append(panel(3, 166, ["She answers Bob herself, with a certificate and a key of her own, which she can sign with.",
                            "But no certificate authority will sign a certificate saying her key belongs to the bank,",
                            "so the chain doesn’t lead to any root Bob’s laptop trusts."],
                   "“Your connection is not private.” Bob stops."))
    b.append(arrows(4, "http://bank… ?", "https://bank…", "s-orange", "s-blue"))
    b.append(panel(4, 166, ["Her last trick: catch Bob’s very first, unencrypted http:// request, and never pass on",
                            "the redirect to https://. She talks HTTPS to the bank, and plain HTTP to Bob,",
                            "and hopes he doesn’t notice the missing padlock."],
                   "HSTS (Chapter 30): the browser never sends that http:// request."))
    steps = ["<strong>Listening.</strong> Eve can see every packet, as she could in Chapters 19 and 21. The Diffie–Hellman exchange is designed for exactly this.",
             "<strong>Swapping the keys.</strong> A plain Diffie–Hellman exchange can be hijacked like this: it’s the attack from the end of Chapter 31. TLS stops it with the signature.",
             "<strong>Her own certificate.</strong> This is why certificate authorities matter: they’re the only thing that ties a name to a key.",
             "<strong>No TLS at all.</strong> “SSL stripping” is the attack HTTPS can’t prevent by itself, because it happens before HTTPS starts. HSTS, and browsers that try https:// first, close the gap."]
    svg = fig("".join(b), 720, 262, "Eve in the middle of Bob's connection to his bank: four attacks and how TLS or HSTS defeats each",
              "Eve’s four tricks, and why each one fails.", steps)
    (OUT / "ch32-eve.svg").write_text(svg)


# ---------------------------------------------------------------- the key schedule

def keys():
    b = []

    def node(x, y, w, label, sub, cls, stroke):
        return (f'<rect x="{x - w / 2:g}" y="{y}" width="{w}" height="40" rx="8" class="{cls}" stroke="{stroke}" stroke-width="1.6"/>'
                + text(x, y + 17, label, "mid xs b") + text(x, y + 32, sub, "mid xs muted"))

    def arrow(x1, y1, x2, y2, cls="s-muted"):
        return f'<path d="M{x1:g},{y1:g} L{x2:g},{y2:g}" class="line {cls}" stroke-width="1.8" marker-end="url(#ah-{cls[2:]})"/>'
    b.append(node(150, 16, 190, "zero", "(no pre-shared key)", "f-card", "var(--line)"))
    b.append(arrow(150, 56, 150, 80))
    b.append(node(150, 82, 190, "early secret", "HKDF-Extract", "f-card", "var(--line)"))
    b.append(arrow(150, 122, 150, 156))
    b.append(node(410, 96, 200, "X25519 shared secret", "from the two key shares", "t-green", "var(--green)"))
    b.append(arrow(330, 136, 248, 164, "s-green"))
    b.append(node(150, 158, 190, "handshake secret", "HKDF-Extract", "t-orange", "var(--orange)"))
    b.append(arrow(150, 198, 150, 250))
    b.append(node(150, 252, 190, "master secret", "HKDF-Extract", "t-purple", "var(--purple)"))
    b.append(arrow(246, 172, 452, 172, "s-orange"))
    b.append(arrow(246, 186, 452, 212, "s-orange"))
    b.append(node(560, 152, 210, "client handshake secret", "“c hs traffic” + transcript", "t-orange", "var(--orange)"))
    b.append(node(560, 196, 210, "server handshake secret", "“s hs traffic” + transcript", "t-orange", "var(--orange)"))
    b.append(arrow(246, 266, 452, 266, "s-purple"))
    b.append(arrow(246, 280, 452, 306, "s-purple"))
    b.append(node(560, 246, 210, "client application secret", "“c ap traffic” + transcript", "t-purple", "var(--purple)"))
    b.append(node(560, 290, 210, "server application secret", "“s ap traffic” + transcript", "t-purple", "var(--purple)"))
    b.append(text(560, 352, "each secret → a 32-byte key (“key”) and a 12-byte IV (“iv”),", "mid xs b"))
    b.append(text(560, 368, "and a Finished key (“finished”) for the MACs", "mid xs"))
    b.append(text(150, 318, "“transcript” = SHA-256 of every", "mid xs muted"))
    b.append(text(150, 332, "handshake message so far", "mid xs muted"))
    svg = fig("".join(b), 720, 380, "The TLS 1.3 key schedule: early, handshake and master secrets, and the handshake and application traffic secrets derived from them",
              "TLS 1.3’s key schedule. Every arrow is HKDF, a way of stretching and mixing secrets with HMAC (Chapter 31). Each key is labelled with what it’s for, and tied to the conversation so far, so a key for one job is useless for any other. In the lab, it’s twenty lines.")
    (OUT / "ch32-keys.svg").write_text(svg)


# ---------------------------------------------------------------- an encrypted record

def record():
    b = []
    y = 40
    parts = [(20, 110, "17 03 03 03 7e", "header: “application data, 894 bytes”", "t-yellow", "var(--yellow)"),
             (130, 420, "HTTP/1.1 200 OK …  17  00 00 …", "encrypted: the data, its real type, and padding", "t-green", "var(--green)"),
             (550, 150, "tag (16 bytes)", "Poly1305", "t-purple", "var(--purple)")]
    for x, w, label, sub, cls, stroke in parts:
        b.append(f'<rect x="{x}" y="{y}" width="{w}" height="42" rx="6" class="{cls}" stroke="{stroke}" stroke-width="1.6"/>')
        b.append(text(x + w / 2, y + 26, label, "mid mono xs b"))
        b.append(text(x + w / 2, y + 60, sub, "mid xs"))
    b.append(text(20, 26, "What travels, and what Eve sees:", "xs b"))
    b.append(text(20, 140, "The header is readable, but always says the same thing: “application data, version 1.2”. The real type (handshake,", "xs"))
    b.append(text(20, 157, "alert or data) is hidden inside, and padding can hide the true length. The header is still protected: it’s the AEAD’s", "xs"))
    b.append(text(20, 174, "“additional data” (Chapter 31), so changing it breaks the tag.", "xs"))
    b.append(text(20, 206, "nonce for record n  =  the 12-byte IV  XOR  n", "mono sm b"))
    b.append(text(20, 226, "Each side counts its records from 0, so every record gets a fresh nonce without sending one, and a record", "xs"))
    b.append(text(20, 243, "that’s dropped, repeated or reordered fails to decrypt: TCP delivers them in order, so anything else is an attack.", "xs"))
    svg = fig("".join(b), 720, 256, "A TLS 1.3 record: a fixed-looking header, the encrypted content with its real type and padding, and a 16-byte tag",
              "One encrypted TLS record, as the lab receives it from example.org.")
    (OUT / "ch32-record.svg").write_text(svg)


if __name__ == "__main__":
    handshake()
    eve()
    keys()
    record()
    print("wrote ch32 figures")
