#!/usr/bin/env python3
"""Generate chapter 35 figures.  python3 src/figs/ch35.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


def seg(x, y, w, h, label, cls, stroke, sub=None):
    out = f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="5" class="{cls}" stroke="{stroke}" stroke-width="1.4"/>'
    out += text(x + w / 2, y + h / 2 + (-2 if sub else 4), label, "mid xs b")
    if sub:
        out += text(x + w / 2, y + h / 2 + 12, sub, "mid xs muted")
    return out


# ---------------------------------------------------------------- a packet inside a packet

def nest():
    b = []
    y1, y2 = 40, 130
    b.append(text(20, 26, "The packet Bob’s laptop wants to send, to Grandpa’s Pi’s private address:", "xs b"))
    inner = [("IP", "10.35.0.2 → 10.35.0.1", 150, "t-yellow", "var(--yellow)"), ("ICMP", "echo request", 100, "t-green", "var(--green)"),
             ("data", "“hello Grandpa 1”", 130, "t-green", "var(--green)")]
    x = 20
    for name, sub, w, cls, stroke in inner:
        b.append(seg(x, y1, w, 40, name, cls, stroke, sub))
        x += w
    b.append(text(x + 10, y1 + 25, "43 bytes", "xs b"))
    b.append('<g data-show="2">')
    b.append(text(20, y2 - 14, "What actually crosses the internet:", "xs b"))
    outer = [("IP", "Alice’s house → Grandpa’s router", 190, "t-blue", "var(--blue)"), ("UDP", "→ port 51820", 90, "t-blue", "var(--blue)"),
             ("WireGuard", "type 4, to #c612798f, #0", 110, "t-purple", "var(--purple)")]
    x = 20
    for name, sub, w, cls, stroke in outer:
        b.append(seg(x, y2, w, 40, name, cls, stroke, sub))
        x += w
    b.append(f'<rect x="{x}" y="{y2}" width="200" height="40" rx="5" class="t-green" stroke="var(--green)" stroke-width="1.4" stroke-dasharray="5 3"/>')
    b.append(text(x + 100, y2 + 17, "🔒 the whole packet above,", "mid xs b"))
    b.append(text(x + 100, y2 + 31, "padded to 48 bytes, sealed", "mid xs muted"))
    b.append(seg(x + 200, y2, 60, 40, "tag", "t-purple", "var(--purple)", "16"))
    b.append(text(20, y2 + 58, "= 108 bytes: 20 IP + 8 UDP + 16 WireGuard header + 48 sealed + 16 tag", "xs"))
    b.append("</g>")
    b.append('<g data-show="3">')
    b.append(text(20, y2 + 84, "Grandpa’s router forwards UDP port 51820 to the Pi (Chapter 22). The Pi’s WireGuard checks the tag, unwraps", "xs"))
    b.append(text(20, y2 + 100, "the packet, and hands it to its network stack as if it had arrived on a cable called wg0. The reply goes back the same way.", "xs"))
    b.append("</g>")
    steps = ["Bob wants to reach the Pi as if he were at Grandpa’s house, on its private address. But private addresses can’t cross the internet (Chapter 22), and anyone could read the packet.",
             "So his laptop wraps the whole packet up: encrypts it, and puts it inside an ordinary UDP datagram, addressed to Grandpa’s router, which the internet knows how to deliver. The sizes are from the lab’s real ping.",
             "At the other end of the <strong>tunnel</strong>, the wrapping comes off. To the Pi, Bob’s laptop is just another computer on a network called <code>wg0</code>."]
    svg = fig("".join(b), 720, 244, "An inner IP packet from Bob to the Pi's private address, wrapped in encrypted WireGuard inside UDP inside IP addressed to Grandpa's router",
              "A tunnel: a packet inside a packet.", steps)
    (OUT / "ch35-nest.svg").write_text(svg)


# ---------------------------------------------------------------- the WireGuard handshake (real sizes)

def handshake():
    B, P = "wg_peer.py (Bob)", "Linux’s WireGuard (the Pi)"
    seq = Seq([(B, 170, None), (P, 560, None)], top=40, scale=30, head=False)
    seq.msg(B, P, 0.3, 1.3, "initiation · 148 bytes", "navy", step="1", sub="temporary key · 🔒 permanent key · 🔒 time · mac1")
    seq.note(P, 1.9, "who is this? only a known key gets an answer", step="2", cls="f-purple", side="left")
    seq.msg(P, B, 2.5, 3.5, "response · 92 bytes", "purple", step="3", sub="temporary key · 🔒 nothing (a proof)")
    seq.note(B, 4.1, "four X25519s → two transport keys", step="3", cls="f-green")
    seq.msg(B, P, 4.7, 5.7, "data #0 · 80 bytes", "green", step="4", sub="🔒 ping 10.35.0.1")
    seq.msg(P, B, 6.1, 7.1, "data #0 · 80 bytes", "green", step="4", sub="🔒 pong, 3.6 ms")
    body, bottom = seq.render(20)
    steps = ["Bob’s side sends one message: a fresh temporary public key in the clear, then its <em>permanent</em> public key and the time, sealed with keys from X25519 exchanges it could do already, because it knows the Pi’s public key in advance.",
             "The Pi checks the cheap <code>mac1</code> first, then opens the sealed parts. If the permanent key isn’t on its list of peers, or the timestamp is older than one it has seen (a replayed message), it says nothing at all. A port scan can’t even tell that WireGuard is there.",
             "Its answer carries its own temporary key, and a sealed empty box: proof that it could derive the same keys, so it really holds the Pi’s private key. Both sides now mix four X25519 results into two keys, one for each direction, and throw the temporary private keys away: forward secrecy, as in TLS 1.3.",
             "Data follows at once: whole IP packets, sealed, numbered with a counter that doubles as the nonce. Every two minutes the handshake is done again, so keys never live long."]
    svg = fig(body, 720, bottom, "The real WireGuard handshake between the lab's Python peer and the Pi's kernel: a 148-byte initiation, a 92-byte response, then transport data",
              "A WireGuard handshake, with the real sizes from <code>wg_peer.py ping</code> talking to the Pi’s kernel.", steps)
    (OUT / "ch35-handshake.svg").write_text(svg)


# ---------------------------------------------------------------- four Diffie-Hellmans

def four_dh():
    b = [text(360, 20, "Each side has two key pairs: a permanent one (its identity) and a temporary one (just for this handshake)", "mid xs b")]
    cells = [("temporary × permanent", "es", "lets Bob seal his identity before hearing a word back", "t-blue", "var(--blue)"),
             ("permanent × permanent", "ss", "only Bob and the Pi, the real ones, can compute this", "t-orange", "var(--orange)"),
             ("temporary × temporary", "ee", "forward secrecy: gone for ever once the keys are deleted", "t-green", "var(--green)"),
             ("permanent × temporary", "se", "even a thief with the Pi’s private key can’t pretend to be Bob", "t-purple", "var(--purple)")]
    for i, (name, code, why, cls, stroke) in enumerate(cells):
        x, y = 20 + (i % 2) * 350, 36 + (i // 2) * 84
        b.append(f'<rect x="{x}" y="{y}" width="330" height="72" rx="10" class="{cls}" stroke="{stroke}" stroke-width="1.6"/>')
        b.append(text(x + 14, y + 24, f"{i + 1}. Bob’s {name.split(' × ')[0]} × the Pi’s {name.split(' × ')[1]}", "sm b"))
        b.append(text(x + 14, y + 44, f"(“{code}” in the Noise protocol’s language)", "xs muted"))
        b.append(text(x + 14, y + 62, why, "xs"))
    svg = fig("".join(b), 720, 212, "The four Diffie-Hellman combinations in the WireGuard handshake and what each proves",
              "The four X25519 exchanges in WireGuard’s handshake, in the order they happen. Each result is mixed into the keys, so the keys are safe as long as any one of them is.")
    (OUT / "ch35-fourdh.svg").write_text(svg)


# ---------------------------------------------------------------- crypto-key routing

def cryptokey():
    b = [text(20, 22, "The Pi’s wg0, as `wg show` described it", "xs b")]
    rows = [("peer (public key)", "allowed IPs", "endpoint (learned)"),
            ("S3s+t5hK…AMslk=  (wg_peer.py)", "10.35.0.2/32", "192.168.1.3:51857"),
            ("…Alice’s phone, say", "10.35.0.3/32", "(wherever it last was)"),
            ("…Bob’s school, say", "10.20.0.0/16", "198.51.100.20:51820")]
    for i, (a, c, d) in enumerate(rows):
        y = 32 + i * 28
        cls = "xs b" if i == 0 else "xs mono"
        b.append(f'<rect x="20" y="{y}" width="680" height="26" class="{"f-surface" if i == 0 else "f-card"}" stroke="var(--line)"/>')
        b.append(text(30, y + 17, a, cls))
        b.append(text(320, y + 17, c, cls))
        b.append(text(470, y + 17, d, cls))
    b.append(text(20, 160, "Sending: a packet for 10.35.0.2 goes out through wg0. Which peer? The one whose allowed IPs include the destination:", "xs"))
    b.append(text(20, 176, "so it’s sealed with wg_peer.py’s keys, and sent to its endpoint. The allowed IPs are a routing table.", "xs"))
    b.append(text(20, 202, "Receiving: a packet that opens with wg_peer.py’s keys is only accepted if its source is in wg_peer.py’s allowed IPs,", "xs"))
    b.append(text(20, 218, "so no peer can pretend to be another. And the endpoint just follows the last valid packet: a laptop that changes", "xs"))
    b.append(text(20, 234, "networks carries on, as QUIC’s connections did in Chapter 33.", "xs"))
    svg = fig("".join(b), 720, 246, "WireGuard crypto-key routing: a table of peers, their allowed IP ranges and endpoints, used both to choose a peer when sending and to check sources when receiving",
              "<strong>Crypto-key routing</strong>: every peer is a public key, with the addresses it may use. (The first row is real; the others show how a bigger tunnel would look.)")
    (OUT / "ch35-cryptokey.svg").write_text(svg)


# ---------------------------------------------------------------- IPsec ESP, two modes

def ipsec():
    b = []

    def row(y, label, parts):
        out = [text(20, y + 18, label, "xs b")]
        x = 170
        for name, w, cls, stroke, dashed in parts:
            dash = ' stroke-dasharray="5 3"' if dashed else ""
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="28" rx="4" class="{cls}" stroke="{stroke}" stroke-width="1.3"{dash}/>')
            out.append(text(x + w / 2, y + 18, name, "mid xs b"))
            x += w
        return "".join(out)
    Y, B, G, P, O = ("t-yellow", "var(--yellow)"), ("t-blue", "var(--blue)"), ("t-green", "var(--green)"), ("t-purple", "var(--purple)"), ("t-orange", "var(--orange)")
    b.append(row(20, "the original", [("IP", 60, *Y, False), ("TCP", 60, *G, False), ("data", 180, *G, False)]))
    b.append(row(64, "transport mode", [("IP", 60, *Y, False), ("ESP", 60, *P, False), ("🔒 TCP", 60, *G, True), ("🔒 data", 180, *G, True),
                                         ("🔒 trailer", 70, *P, True), ("ICV", 50, *P, False)]))
    b.append(row(108, "tunnel mode", [("new IP", 60, *B, False), ("ESP", 50, *P, False), ("🔒 IP", 50, *Y, True), ("🔒 TCP", 50, *G, True),
                                       ("🔒 data", 150, *G, True), ("🔒 trailer", 70, *P, True), ("ICV", 50, *P, False)]))
    b.append(row(152, "…through a NAT", [("new IP", 60, *B, False), ("UDP 4500", 70, *O, False), ("ESP", 50, *P, False), ("🔒 IP", 50, *Y, True),
                                          ("🔒 TCP + data", 170, *G, True), ("🔒 trailer", 70, *P, True), ("ICV", 40, *P, False)]))
    b.append(text(20, 206, "ESP = the SPI (which security agreement this is) and a sequence number. ICV = the integrity check value: the tag.", "xs"))
    b.append(text(20, 222, "The keys come from a separate handshake protocol, IKE, on UDP port 500, which also checks certificates or passwords.", "xs"))
    svg = fig("".join(b), 720, 234, "IPsec ESP packet layouts: transport mode, tunnel mode, and tunnel mode inside UDP port 4500 for NAT traversal",
              "IPsec’s ESP, three ways. Transport mode protects a packet between two computers; tunnel mode wraps whole packets, for VPNs. ESP has no ports, so home routers’ NAT can’t handle it, and it’s usually wrapped in UDP as well.")
    (OUT / "ch35-ipsec.svg").write_text(svg)


# ---------------------------------------------------------------- VXLAN (real capture)

def vxlan():
    parts = [("Ethernet", "outer", 14, "t-blue", "var(--blue)"), ("IP", "192.0.2.1 → .2", 20, "t-blue", "var(--blue)"),
             ("UDP", "→ 4789", 8, "t-blue", "var(--blue)"), ("VXLAN", "VNI 42", 8, "t-orange", "var(--orange)"),
             ("Ethernet", "inner MACs", 14, "t-green", "var(--green)"), ("IP", "10.99.0.1 → .2", 20, "t-green", "var(--green)"),
             ("ICMP echo request", "", 64, "t-green", "var(--green)")]
    b, x = [], 20
    for name, sub, size, cls, stroke in parts:
        w = size * 4.6
        b.append(seg(x, 34, w, 46, name, cls, stroke, sub or None))
        b.append(text(x + w / 2, 96, f"{size}", "mid xs muted"))
        x += w
    b.append(text(20, 22, "One ping through Chapter 35’s VXLAN tunnel, as tshark decoded it on the “internet” between the two namespaces: 148 bytes", "xs b"))
    b.append(f'<path d="M20,110 L{20 + 50 * 4.6:g},110" class="line s-blue" stroke-width="2"/>')
    b.append(text(20 + 25 * 4.6, 126, "the 50 bytes VXLAN adds", "mid xs b f-blue"))
    b.append(f'<path d="M{20 + 50 * 4.6:g},110 L{x:g},110" class="line s-green" stroke-width="2"/>')
    b.append(text((20 + 50 * 4.6 + x) / 2, 126, "a complete Ethernet frame: the network the machines think they’re on", "mid xs b f-green"))
    b.append(text(20, 156, "A VXLAN tunnel acts like a switch port: it learns which MAC addresses live at which far end (bridge fdb), and floods", "xs"))
    b.append(text(20, 172, "the rest, ARP included. The 24-bit network identifier allows 16 million separate networks over the same wires,", "xs"))
    b.append(text(20, 188, "where VLAN tags (Chapter 18) allowed 4,094: enough for a data centre where every customer gets their own.", "xs"))
    svg = fig("".join(b), 720, 200, "A VXLAN packet from the lab capture: outer Ethernet, IP and UDP to port 4789, an 8-byte VXLAN header with VNI 42, then an inner Ethernet frame",
              "VXLAN: a whole Ethernet frame, inside UDP. Kubernetes networks and cloud providers’ virtual networks are often built this way (Chapter 36).")
    (OUT / "ch35-vxlan.svg").write_text(svg)


if __name__ == "__main__":
    nest()
    handshake()
    four_dh()
    cryptokey()
    ipsec()
    vxlan()
    print("wrote ch35 figures")
