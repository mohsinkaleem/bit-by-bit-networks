#!/usr/bin/env python3
"""Generate chapter 29 figures.  python3 src/figs/ch29.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


def box(x, y, w, h, title, lines, cls="f-surface", stroke="var(--line)", extra=""):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" class="{cls}" stroke="{stroke}" stroke-width="1.6"{extra}/>',
           text(x + w / 2, y + 18, title, "mid xs b")]
    for i, l in enumerate(lines):
        out.append(text(x + w / 2, y + 34 + i * 14, l, "mid mono xs"))
    return "".join(out)


# ---------------------------------------------------------------- a real lookup, from the root down

def trace():
    b = []
    rx, ry = 70, 150
    b.append(f'<use href="#server" x="{rx - 18}" y="{ry - 30}" width="36" height="58"/>')
    b.append(text(rx, ry + 44, "a resolver", "mid xs b"))
    b.append(text(rx, ry + 58, "(empty cache)", "mid xs muted"))
    servers = [(250, 40, "a root server", ["f.root-servers.net", "one of 13 names"], "1"),
               (440, 40, "the ch servers", ["f.nic.ch", "run by SWITCH"], "2"),
               (630, 40, "the cern.ch servers", ["scsnms.switch.ch", "and 2 at CERN"], "3")]
    for x, y, title, lines, step in servers:
        b.append(box(x - 80, y, 160, 64, title, lines))
    arrows = [(250, "1", "info.cern.ch?", "“ask the ch servers:", "a.nic.ch … f.nic.ch”", "14 ms"),
              (440, "2", "info.cern.ch?", "“ask the cern.ch servers:", "ext-dns-1, -2, scsnms…”", "40 ms"),
              (630, "3", "info.cern.ch?", "“it’s an alias: webafs902.cern.ch,", "which is 188.184.67.127”", "158 ms")]
    for x, step, q, a1, a2, ms in arrows:
        b.append(f'<g data-show="={step}"><path d="M{rx + 26},{ry - 10} C{(rx + x) / 2},{ry - 50} {x - 60},{130} {x - 20},{108}" class="line s-blue" stroke-width="2.5" marker-end="url(#ah-blue)"/>'
                 + text((rx + x) / 2 + 10, 120, q, "mid xs b halo", style="fill:var(--blue)")
                 + f'<path d="M{x},{108} C{x},{190} {rx + 120},{ry + 20} {rx + 26},{ry + 4}" class="line s-green" stroke-width="2.5" marker-end="url(#ah-green)"/>'
                 + text(x - 10, 200, a1, "mid xs b halo f-green") + text(x - 10, 214, a2, "mid xs b halo f-green")
                 + text(x + 70, 150, ms, "xs b muted") + "</g>")
    b.append('<g data-show="4">' + text(360, 250, "3 questions, about 210 ms. The resolver keeps every answer for as long as its TTL says: the ch servers for 2 days,", "mid xs")
             + text(360, 266, "the cern.ch servers for an hour, the answer for 15 minutes. So the next name in cern.ch starts at step 3.", "mid xs") + "</g>")
    steps = ["The resolver knows nothing but the addresses of the root servers, which are built into it. It asks one of them about the whole name. The root doesn’t know, but it knows who looks after <code>ch</code>, and says so: a <strong>referral</strong>, with the names of Switzerland’s servers and, helpfully, their addresses (“glue”).",
             "It asks one of the <code>ch</code> servers the same question, and gets another referral, to the servers for <code>cern.ch</code>.",
             "One of CERN’s servers finally has the answer, and it’s <strong>authoritative</strong>: it comes from the people who own the name. <code>info.cern.ch</code> is an alias, and the server includes the real name’s address too.",
             "Every step was cached. These are real answers, from <code>dig +trace info.cern.ch</code>."]
    svg = fig("".join(b), 720, 278, "A resolver following referrals from a root server to the ch servers to CERN's servers, which answer with a CNAME and an address",
              "A real lookup, from the root down.", steps)
    (OUT / "ch29-trace.svg").write_text(svg)


# ---------------------------------------------------------------- TTLs and the "propagation" myth

def ttl():
    x0, x1 = 90, 690
    b = []
    rows = [("CERN’s server", 50), ("resolver A", 110), ("resolver B", 170)]
    for name, y in rows:
        b.append(text(14, y + 4, name, "xs b"))
        b.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" class="grid"/>')
    change = 300
    b.append(f'<rect x="{x0}" y="36" width="{change - x0}" height="28" rx="4" class="t-blue" stroke="var(--blue)"/>' + text((x0 + change) / 2, 54, "188.184.67.127", "mid mono xs b"))
    b.append(f'<rect x="{change}" y="36" width="{x1 - change}" height="28" rx="4" class="t-green" stroke="var(--green)"/>' + text((change + x1) / 2, 54, "the new address", "mid xs b"))
    b.append(f'<line x1="{change}" y1="26" x2="{change}" y2="200" class="line s-orange" stroke-width="2" stroke-dasharray="4 3"/>')
    b.append(text(change, 20, "CERN changes the record", "mid xs b f-orange"))
    # resolver A cached at 150, TTL 900 s (scale: 600px = 1800 s)
    s = 600 / 1800
    for y, t, label in ((110, 150, "asked at 150 s"), (170, 250, "asked at 250 s")):
        xa = t
        xe = xa + 900 * s
        b.append(f'<rect x="{xa}" y="{y - 14}" width="{xe - xa:g}" height="28" rx="4" class="t-blue" stroke="var(--blue)"/>')
        b.append(text((xa + xe) / 2, y + 4, "old address, from its cache", "mid xs b"))
        b.append(f'<rect x="{xe:g}" y="{y - 14}" width="{x1 - xe:g}" height="28" rx="4" class="t-green" stroke="var(--green)"/>')
        b.append(text(xa, y + 28, label, "xs muted"))
        b.append(text(xe, y + 28, "TTL runs out: asks again", "xs muted"))
    b.append(text(360, 224, "Each resolver keeps the old answer until its own copy’s TTL (here 900 s) runs out. Nothing “propagates”.", "mid xs"))
    svg = fig("".join(b), 720, 236, "Timeline of a DNS record changing, and two resolvers keeping the old answer until their cached copies expire",
              "When a record changes, resolvers that asked recently keep the old answer until its TTL runs out, each on its own schedule.")
    (OUT / "ch29-ttl.svg").write_text(svg)


# ---------------------------------------------------------------- DNSSEC: a chain of signatures

def dnssec():
    b = []
    levels = [(".", "the root", "the root’s key (built into every validating resolver)", "DS for net.: “net’s key has this fingerprint”", 40),
              ("net.", "the net servers", "net’s key", "DS for ripe.net.: 63758 13 2 75A473C1…", 130),
              ("ripe.net.", "RIPE’s servers", "ripe.net’s key", "A 193.0.11.51, and its RRSIG", 220)]
    for zone, who, key, signed, y in levels:
        step = {".": "1", "net.": "2", "ripe.net.": "3"}[zone]
        b.append(f'<g data-show="{step}">')
        b.append(f'<rect x="40" y="{y}" width="640" height="66" rx="10" class="f-card" stroke="var(--line)"/>')
        b.append(text(56, y + 22, f"{zone}  ({who})", "sm b"))
        b.append(f'<rect x="60" y="{y + 32}" width="220" height="24" rx="12" class="t-yellow" stroke="var(--yellow)"/>' + text(170, y + 48, "🔑 " + key, "mid xs b"))
        b.append(f'<rect x="330" y="{y + 32}" width="330" height="24" rx="5" class="t-green" stroke="var(--green)"/>' + text(495, y + 48, signed, "mid mono xs"))
        b.append(f'<path d="M280,{y + 44} L326,{y + 44}" class="line s-orange" stroke-width="2" marker-end="url(#ah-orange)"/>' + text(303, y + 38, "signs", "mid xs f-orange b"))
        b.append("</g>")
        if zone != "ripe.net.":
            b.append(f'<g data-show="{int(step) + 1}"><path d="M495,{y + 58} C495,{y + 88} 170,{y + 70} 170,{y + 118}" class="line s-green" stroke-width="2" marker-end="url(#ah-green)"/>'
                     + text(360, y + 82, "vouches for", "mid xs b f-green halo") + "</g>")
    b.append('<g data-show="4">' + text(360, 312, "Every link checks, so the resolver sets the “ad” flag: authenticated data.", "mid sm b f-green") + "</g>")
    steps = ["Every validating resolver has the root zone’s public key built in: the one thing it must trust. The root signs a record for each top-level domain that uses DNSSEC: a <strong>DS</strong> record, the fingerprint of that domain’s own key.",
             "The <code>net</code> servers publish their key, which matches the fingerprint the root signed. They sign a DS record for each signed domain under them, like <code>ripe.net</code>. (The real one, from <code>dig DS ripe.net</code>.)",
             "RIPE’s servers publish their key, which matches that fingerprint, and sign every record in their zone. With the answer comes an <strong>RRSIG</strong>: the signature.",
             "A forged answer would need a signature made with RIPE’s private key, which only RIPE has. And nobody can swap RIPE’s key for their own, because <code>net</code> vouched for the real one, and the root vouched for <code>net</code>’s."]
    svg = fig("".join(b), 720, 322, "The DNSSEC chain of trust from the root key to net's key to ripe.net's key to a signed A record",
              "DNSSEC: a chain of signatures from the root to the answer.", steps)
    (OUT / "ch29-dnssec.svg").write_text(svg)


if __name__ == "__main__":
    trace()
    ttl()
    dnssec()
    print("wrote ch29 figures")
