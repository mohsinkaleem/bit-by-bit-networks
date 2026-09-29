#!/usr/bin/env python3
"""Build the "Bit by Bit" site.

    python3 build.py          # writes ./site
    python3 build.py --watch  # rebuild whenever something in src/, assets/ or labs/ changes

Chapter sources live in src/chapters/NN.html. They are plain HTML plus a few
shorthand tags that this script expands:

    <terminal>...</terminal>      a terminal session; lines starting with "$ " are commands
    <pycode>...</pycode>          an inline Python snippet (syntax highlighted)
    <!-- @code labs/x.py -->      include a lab file (optionally  labs/x.py#region)
    <msg title="..">a | b</msg>   a protocol message, one "label | content" row per line
    <dialogue>A: hi</dialogue>    a conversation (A=Alice, B=Bob, C=Carol, D=Dave, E=Eve, G=Grandpa Otto, note=narration)
    <realworld>...</realworld>    a "Meanwhile, in the real world" aside
    <think>...</think>            a "Stop and think" aside
    <lab>...</lab>                the "Try it yourself" section
    <codebook5/>                  the 5-bit alphabet table from chapter 1
    ⟦2:text⟧ inside <terminal>    highlight part of the output with a numbered callout (⟦2⟧ = badge only)
    <callouts>2 | ...</callouts>  the list explaining those numbered callouts
    <os>...</os>                  a macOS-vs-Linux command table (see src/field-guide.html)
    <cmd id=.. ch="5,10">..</cmd> a Field Guide entry; chapters listed in ch= get an automatic
                                  "At the command line" box linking to it
    <!-- @include path -->        paste a generated SVG fragment (generators live in src/figs/)
"""
import builtins
import hashlib
import html
import io
import keyword
import re
import shutil
import sys
import time
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
SITE = ROOT / "site"

BOOK = "Bit by Bit"
TAGLINE = "Computer networks, built from scratch"
AUTHOR = "Mohsin Kaleem"
YEAR = 2026
SITE_URL = "https://mohsinkaleem.github.io/bit-by-bit-networks/"
REPO_URL = "https://github.com/mohsinkaleem/bit-by-bit-networks"
SHARE_DESCRIPTION = ("A free, story-driven book on how computer networks work, from a flashlight between two "
                     "bedroom windows to TLS 1.3, QUIC, BGP and satellite internet. Interactive diagrams and "
                     "pure-Python labs in every chapter.")

PARTS = {
    "I": ("Networks as They Might Have Been",
          "We invent a computer network from nothing, one problem at a time."),
    "II": ("Networks as They Are",
           "The real protocols, taken apart and captured live on your own machine."),
    "III": ("Networks as They May Be",
            "Where networking is heading next."),
}

# (number, part, title, subtitle)
CHAPTERS = [
    (1, "I", "Blinking Bits Between Bedroom Windows", "Sending information with a flashlight"),
    (2, "I", "Wired and Wonderful, or the Flashlight Gets Fired", "Replacing light with electricity, and keeping time"),
    (3, "I", "Over and Out", "Two-way communication and our first real protocol"),
    (4, "I", "The Chatterbox Gets a Brain", "Computers, programs, files, and requests"),
    (5, "I", "Eight Bits Walk Into a Byte", "Bytes, pictures, and saying what kind of data you're sending"),
    (6, "I", "Tangled Up in Links", "Browsers, directories, and a web of documents"),
    (7, "I", "Documents That Write Themselves", "Dynamic pages, forms, and remembering visitors"),
    (8, "I", "Three's a Crowd", "Sharing one wire: addresses, collisions, and good manners"),
    (9, "I", "Switching Things Up", "Hubs, switches, and a box that learns who lives where"),
    (10, "I", "Chop It Up and Check It Twice", "Packets, and catching errors before they catch you"),
    (11, "I", "A Network of Networks", "Routers, network addresses, and finding your way across town"),
    (12, "I", "Which Program Gets the Mail?", "Ports, and fire-and-forget messages between programs"),
    (13, "I", "Did You Get That? Did You Get That?", "Building reliable delivery on an unreliable network"),
    (14, "I", "What's in a Name?", "Swapping hard-to-remember numbers for easy names"),
    (15, "I", "The Map and the Territory", "Everything we invented, and what the real world calls it"),
    (16, "II", "Eavesdropping on Yourself", "Your packet-capture toolkit: tcpdump, filters, and tshark"),
    (17, "II", "Wires, Light, and Thin Air", "The physical layer for real: copper, fiber, and radio"),
    (18, "II", "Ethernet, Honestly", "Frames, MAC addresses, switches, and VLANs"),
    (19, "II", "Shouting Politely Through the Air", "Wi-Fi: 802.11, CSMA/CA, and joining a network"),
    (20, "II", "Four Numbers and a Slash", "IPv4 addresses, subnets, and the IP header"),
    (21, "II", "Ping, Pong, and Other Small Talk", "ARP and ICMP; ping and traceroute from the inside"),
    (22, "II", "Home Sweet Router", "DHCP and NAT: how your laptop gets online"),
    (23, "II", "Pathfinders", "Routing inside a network: longest-prefix match, RIP, and OSPF"),
    (24, "II", "The Treaty of the Internet", "BGP: how tens of thousands of networks agree to carry each other's traffic"),
    (25, "II", "Room for Everyone", "IPv6"),
    (26, "II", "Sockets and Datagrams", "UDP and the sockets API"),
    (27, "II", "Shake Hands, Count Bytes", "TCP, part 1: connections, sequence numbers, and reliability"),
    (28, "II", "Don't Flood the Pipes", "TCP, part 2: flow control and congestion control"),
    (29, "II", "The Internet's Phone Book, For Real", "DNS in depth"),
    (30, "II", "Hypertext in the Wild", "Real-world HTTP/1.1: keep-alive, caching, compression, redirects, and APIs"),
    (31, "II", "Secrets in Plain Sight", "A cryptography crash course for networking"),
    (32, "II", "The Padlock Icon", "TLS 1.3 and HTTPS, with a client built from scratch"),
    (33, "II", "Faster, Fewer, Multiplexed", "HTTP/2, HTTP/3, and QUIC"),
    (34, "II", "Middlemen", "Proxies, load balancers, CDNs, and firewalls"),
    (35, "II", "Tunnels All the Way Down", "VPNs, IPsec, WireGuard, and overlay networks"),
    (36, "II", "Networks in a Box", "Namespaces, virtual cables, bridges, and how containers get online"),
    (37, "II", "What Happens When You Press Enter", "One URL, every layer, start to finish"),
    (38, "II", "Network Detective", "A troubleshooting toolkit"),
    (39, "III", "Networks That Program Themselves", "SDN, P4, and eBPF"),
    (40, "III", "The Internet in Orbit", "Low-Earth-orbit satellite constellations"),
    (41, "III", "Mail Across the Solar System", "Delay-tolerant and interplanetary networking"),
    (42, "III", "Locks the Quantum Can't Pick", "Post-quantum cryptography on the wire"),
    (43, "III", "Ask for What, Not Where", "Named-data and content-centric networking"),
    (44, "III", "Mesh, 5G, and the Edge", "Where the last mile is going"),
]

# The 32-symbol alphabet from chapter 1. Index = 5-bit code.
CODEBOOK5 = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ["␣", ".", ",", "?", "!", "~"]

FONTS = ("https://fonts.googleapis.com/css2?family=Roboto+Slab:wght@400;700"
         "&family=Patrick+Hand&display=swap")


def chapter_path(num):
    return SRC / "chapters" / f"{num:02d}.html"


EPILOGUE = SRC / "epilogue.html"
EPILOGUE_TITLE = ("Two Windows, Again", "Where Alice and Bob end up, and where to go next")


def is_ready(num):
    return chapter_path(num).exists()


# ---------------------------------------------------------------- page shell

def page(title, body, body_class="", description="", path=""):
    desc = html.escape(description or TAGLINE)
    share = html.escape(description or SHARE_DESCRIPTION)
    url = SITE_URL + path
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{desc}">
  <meta name="author" content="{AUTHOR}">
  <link rel="canonical" href="{url}">
  <meta property="og:type" content="book">
  <meta property="og:site_name" content="{BOOK}">
  <meta property="og:title" content="{html.escape(title)}">
  <meta property="og:description" content="{share}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{SITE_URL}assets/og-cover.png">
  <meta property="og:image:width" content="1280">
  <meta property="og:image:height" content="640">
  <meta property="og:image:alt" content="Alice and Bob signalling between their bedroom windows with a flashlight">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{FONTS}" rel="stylesheet">
  <link rel="stylesheet" href="assets/main.css?v={asset_version()}">
  <script>document.documentElement.classList.add('js')</script>
</head>
<body class="{body_class}">
{sprites()}
{body}
<footer class="site-footer">
  <span>{BOOK} · {TAGLINE.lower()} · by {AUTHOR}</span>
  <span class="credit">© {YEAR} {AUTHOR}. Text and figures under <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>, code under the <a href="{REPO_URL}/blob/main/LICENSE">MIT license</a>. <a href="{REPO_URL}">Source and corrections on GitHub</a></span>
  <span class="credit">Style inspired by <a href="https://www.networksfromscratch.com/">Computer Networks From Scratch</a> by Seth Archer Brown</span>
</footer>
<script src="assets/widgets.js?v={asset_version()}"></script>
</body>
</html>
"""


_sprites_cache = None
_version_cache = None


def asset_version():
    """A short fingerprint of the CSS and JS, so browsers fetch fresh copies after every change."""
    global _version_cache
    if _version_cache is None:
        digest = hashlib.sha256()
        for name in ("main.css", "widgets.js"):
            digest.update((ROOT / "assets" / name).read_bytes())
        _version_cache = digest.hexdigest()[:10]
    return _version_cache


def sprites():
    global _sprites_cache
    if _sprites_cache is None:
        _sprites_cache = (SRC / "sprites.svg").read_text()
    return _sprites_cache


def nav(prev_href, next_href):
    def arrow(href, cls):
        if href:
            return f'<a class="arrow {cls}" href="{href}" aria-label="{cls} chapter">⮕</a>'
        return f'<span class="arrow {cls} disabled" aria-hidden="true">⮕</span>'
    return f"""<nav class="top">
  {arrow(prev_href, "prev")}
  <div class="brand">
    <a href="index.html"><span>{BOOK}</span></a>
    <span class="nav-links"><a class="toc-link" href="table_of_contents.html">Contents</a><a class="toc-link" href="field-guide.html">Field Guide</a></span>
  </div>
  {arrow(next_href, "next")}
</nav>"""


# ---------------------------------------------------------------- shorthand tags

def highlight_python(src):
    """Return HTML for src with tokens wrapped in spans. Falls back to plain text."""
    lines = src.splitlines(keepends=True)
    starts = [0]
    for line in lines:
        starts.append(starts[-1] + len(line))
    out = []
    row, col = 1, 0

    def offset(r, c):
        return min(starts[r - 1] + c, len(src)) if r - 1 < len(starts) else len(src)

    def text_between(r1, c1, r2, c2):
        return src[offset(r1, c1):offset(r2, c2)]

    builtin_names = set(dir(builtins))
    string_types = {tokenize.STRING}
    for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END",
                 "TSTRING_START", "TSTRING_MIDDLE", "TSTRING_END"):
        if hasattr(tokenize, name):
            string_types.add(getattr(tokenize, name))
    prev_name = None
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            (sr, sc), (er, ec) = tok.start, tok.end
            if tok.type == tokenize.ENDMARKER:
                break
            if (sr, sc) < (row, col):
                continue
            out.append(html.escape(text_between(row, col, sr, sc)))
            raw = text_between(sr, sc, er, ec)
            cls = None
            if tok.type == tokenize.COMMENT:
                cls = "c"
            elif tok.type in string_types:
                cls = "s"
            elif tok.type == tokenize.NUMBER:
                cls = "n"
            elif tok.type == tokenize.NAME:
                if keyword.iskeyword(raw) or raw in ("self", "match", "case"):
                    cls = "k"
                elif prev_name in ("def", "class"):
                    cls = "f"
                elif raw in builtin_names:
                    cls = "b"
                prev_name = raw
            elif tok.type == tokenize.OP and raw == "@":
                cls = "k"
            out.append(f'<span class="{cls}">{html.escape(raw)}</span>' if cls else html.escape(raw))
            row, col = er, ec
        out.append(html.escape(src[offset(row, col):]))
        return "".join(out)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return html.escape(src)


def code_block(src, filename=None, href=None, lang="python"):
    src = src.strip("\n")
    body = highlight_python(src) if lang == "python" else html.escape(src)
    head = ""
    if filename:
        link = f' <a class="dl" href="{href}" download>download</a>' if href else ""
        head = f'<div class="code-head"><span>{html.escape(filename)}</span>{link}</div>'
    return f'<div class="code">{head}<pre><code class="{lang}">{body}</code></pre></div>'


def extract_region(text, region):
    start = re.search(rf"^[ \t]*# --8<-- \[start:{re.escape(region)}\][^\n]*\n", text, re.M)
    end = re.search(rf"^[ \t]*# --8<-- \[end:{re.escape(region)}\][^\n]*$", text, re.M)
    if not start or not end:
        raise SystemExit(f"region {region!r} not found")
    chunk = text[start.end():end.start()]
    # dedent
    lines = chunk.splitlines()
    indents = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
    cut = min(indents) if indents else 0
    return "\n".join(l[cut:] for l in lines)


def strip_region_markers(text):
    return re.sub(r"^[ \t]*# --8<-- \[(start|end):[^\]]+\][^\n]*\n", "", text, flags=re.M)


def expand_code_includes(src):
    def repl(m):
        target = m.group(1)
        path, _, region = target.partition("#")
        full = ROOT / path
        if not full.exists():
            raise SystemExit(f"@code: missing {path}")
        text = full.read_text()
        lang = "python" if path.endswith(".py") else "text"
        if region:
            snippet = extract_region(text, region)
        else:
            snippet = strip_region_markers(text)
        return code_block(snippet, filename=path, href=path, lang=lang)
    return re.sub(r"<!--\s*@code\s+(\S+)\s*-->", repl, src)


def expand_terminal(src):
    def repl(m):
        title = m.group(1)
        lines = m.group(2).strip("\n").splitlines()
        rows = []
        prev = ""
        for line in lines:
            if line.startswith("    ") and prev.startswith("$ ") and prev.rstrip().endswith(("\\", "{")):
                rows.append(f'<span class="cmd cont">{callout_marks(html.escape(line))}</span>')   # a long command, continued
                prev = "$ " + line
                continue
            prev = line
            if line.startswith("$ "):
                rows.append(f'<span class="cmd">{callout_marks(html.escape(line[2:]))}</span>')
            elif line.startswith("# "):
                rows.append(f'<span class="note"># {html.escape(line[2:])}</span>')
            else:
                rows.append(f'<span class="out">{callout_marks(html.escape(line)) or " "}</span>')
        head = f'<div class="term-head"><i></i><i></i><i></i><span>{html.escape(title)}</span></div>' if title else \
            '<div class="term-head"><i></i><i></i><i></i></div>'
        cls = "terminal has-callouts" if "⟦" in m.group(2) else "terminal"
        return f'<div class="{cls}">{head}<pre>' + "\n".join(rows) + "</pre></div>"
    return re.sub(r'<terminal(?:\s+title="([^"]*)")?>(.*?)</terminal>', repl, src, flags=re.S)


def callout_marks(escaped):
    """⟦2:text⟧ highlights text and adds badge 2; ⟦2⟧ is just the badge."""
    escaped = re.sub(r"⟦(\d+):(.*?)⟧", r'<span class="co-hl">\2</span><span class="co-n" data-n="\1"></span>', escaped)
    return re.sub(r"⟦(\d+)⟧", r'<span class="co-n" data-n="\1"></span>', escaped)


def expand_callouts(src):
    def repl(m):
        items = []
        for line in m.group(1).strip("\n").splitlines():
            if not line.strip():
                continue
            num, _, text = line.partition(" | ")
            items.append(f'<li data-n="{num.strip()}">{text.strip()}</li>')
        return '<ol class="callouts">' + "".join(items) + "</ol>"
    return re.sub(r"<callouts>(.*?)</callouts>", repl, src, flags=re.S)


def expand_os(src):
    """<os> blocks: '== task' starts a row; 'mac:', 'linux:' or 'both:' lines give the commands
    (repeat a key for several commands); 'note:' adds a small note to the row, 'tip:' a line under the table."""
    def words(cmd):
        # break lines only between words, so "-listallhardwareports" never splits at its hyphen
        return " ".join(html.escape(w) if len(w) > 24 else f'<span class="w">{html.escape(w)}</span>' for w in cmd.split(" "))

    def cell(cmds):
        return "<br>".join(f"<code>{words(c)}</code>" for c in cmds) or '<span class="none">—</span>'

    def repl(m):
        rows, cur, tips = [], None, []
        for raw in m.group(1).strip("\n").splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("tip:"):
                tips.append(line[4:].strip())
                continue
            if line.startswith("== "):
                cur = {"task": line[3:], "mac": [], "linux": [], "both": [], "note": ""}
                rows.append(cur)
                continue
            key, _, val = line.partition(":")
            if key in ("mac", "linux", "both"):
                cur[key].append(val.strip())
            elif key == "note":
                cur["note"] = val.strip()
        out = ['<div class="os-wrap"><table class="os"><thead><tr><th>To…</th><th class="mac">macOS</th>'
               '<th class="linux">Linux</th></tr></thead><tbody>']
        for r in rows:
            note = f'<span class="os-note">{r["note"]}</span>' if r["note"] else ""
            task = f'<td class="task">{r["task"]}{note}</td>'
            if r["both"]:
                out.append(f'<tr>{task}<td class="both" colspan="2" data-label="macOS &amp; Linux">{cell(r["both"])}</td></tr>')
            else:
                out.append(f'<tr>{task}<td data-label="macOS">{cell(r["mac"])}</td><td data-label="Linux">{cell(r["linux"])}</td></tr>')
        out.append("</tbody></table>")
        out.extend(f'<p class="os-tip">{t}</p>' for t in tips)
        out.append("</div>")
        return "".join(out)
    return re.sub(r"<os>(.*?)</os>", repl, src, flags=re.S)


def expand_pycode(src):
    def repl(m):
        return code_block(m.group(1))
    return re.sub(r"<pycode>(.*?)</pycode>", repl, src, flags=re.S)


def expand_msg(src):
    def repl(m):
        attrs, body = m.group(1) or "", m.group(2)
        title = re.search(r'title="([^"]*)"', attrs)
        cls = re.search(r'class="([^"]*)"', attrs)
        rows = []
        for line in body.strip("\n").splitlines():
            if not line.strip():
                continue
            if " | " in line:
                label, content = line.split(" | ", 1)
            else:
                label, content = "", line
            label = label.strip()
            # content is HTML-escaped except for <b>, <i>, <em>, <mark> and span.hl which we allow through
            content = html.escape(content.strip(), quote=False)
            content = re.sub(r"&lt;(/?)(b|i|em|mark|u)&gt;", r"<\1\2>", content)
            content = re.sub(r"&lt;span class=&quot;([\w -]+)&quot;&gt;|&lt;span class=\"([\w -]+)\"&gt;",
                             lambda mm: f'<span class="{mm.group(1) or mm.group(2)}">', content)
            content = content.replace("&lt;/span&gt;", "</span>")
            lab_cls = f' class="k-{re.sub(r"[^a-z]", "", label.lower())}"' if label else ""
            rows.append(f"<tr><th{lab_cls}>{html.escape(label)}</th><td>{content}</td></tr>")
        cap = f"<caption>{html.escape(title.group(1))}</caption>" if title else ""
        extra = f" {cls.group(1)}" if cls else ""
        return f'<table class="msg{extra}">{cap}' + "".join(rows) + "</table>"
    return re.sub(r"<msg(\s[^>]*)?>(.*?)</msg>", repl, src, flags=re.S)


SPEAKERS = {"A": ("alice", "Alice", "left"), "B": ("bob", "Bob", "right"),
            "C": ("carol", "Carol", "left"), "D": ("dave", "Dave", "right"),
            "E": ("eve", "Eve", "left"), "G": ("otto", "Grandpa Otto", "left")}


def expand_dialogue(src):
    def repl(m):
        items = []
        for line in m.group(1).strip("\n").splitlines():
            line = line.strip()
            if not line:
                continue
            who, _, text = line.partition(":")
            text = text.strip()
            if who == "note":
                items.append(f'<div class="d-note">{text}</div>')
                continue
            sid, name, side = SPEAKERS[who]
            items.append(
                f'<div class="d-line {side}">'
                f'<svg class="avatar" viewBox="0 0 60 60" aria-hidden="true"><use href="#{sid}-head"/></svg>'
                f'<div class="bubble {sid}"><span class="who">{name}</span>{text}</div></div>')
        return '<div class="dialogue">' + "".join(items) + "</div>"
    return re.sub(r"<dialogue>(.*?)</dialogue>", repl, src, flags=re.S)


def expand_asides(src):
    src = re.sub(r"<realworld>(.*?)</realworld>",
                 r'<aside class="real-world"><div class="aside-tag"><svg aria-hidden="true"><use href="#icon-globe"/></svg>'
                 r'Meanwhile, in the real world</div>\1</aside>', src, flags=re.S)
    src = re.sub(r"<think>(.*?)</think>",
                 r'<aside class="think"><div class="aside-tag"><svg aria-hidden="true"><use href="#icon-bulb"/></svg>'
                 r'Stop and think</div>\1</aside>', src, flags=re.S)
    src = re.sub(r"<lab>(.*?)</lab>",
                 r'<section class="lab"><h3 id="try-it-yourself"><svg class="lab-icon" aria-hidden="true">'
                 r'<use href="#icon-flask"/></svg>Try it yourself</h3>\1</section>', src, flags=re.S)
    return src


def expand_codebook(src):
    if "<codebook5/>" not in src:
        return src
    cells = []
    for i, ch in enumerate(CODEBOOK5):
        bits = format(i, "05b")
        marbles = "".join(f'<i class="dot b{b}"></i>' for b in bits)
        label = {"␣": "space", "~": "~ (special)"}.get(ch, ch)
        cells.append(f'<div class="cb-cell"><span class="cb-ch">{html.escape(ch)}</span>'
                     f'<span class="cb-bits">{bits}</span><span class="cb-dots">{marbles}</span>'
                     f'<span class="cb-num">{i}</span><span class="sr-only">{html.escape(label)}</span></div>')
    table = '<div class="codebook" role="table" aria-label="5-bit alphabet">' + "".join(cells) + "</div>"
    return src.replace("<codebook5/>", table)


def slugify(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).lower()
    text = re.sub(r"[’']", "", text)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def add_heading_ids(src):
    seen = set()

    def repl(m):
        attrs, inner = m.group(1), m.group(2)
        if "id=" in attrs:
            ident = re.search(r'id="([^"]+)"', attrs).group(1)
            seen.add(ident)
            return m.group(0)
        ident = slugify(inner)
        base, n = ident, 2
        while ident in seen:
            ident, n = f"{base}-{n}", n + 1
        seen.add(ident)
        return f'<h3{attrs} id="{ident}">{inner}</h3>'
    return re.sub(r"<h3([^>]*)>(.*?)</h3>", repl, src, flags=re.S)


def mini_toc(src):
    items = []
    for m in re.finditer(r'<h3[^>]*id="([^"]+)"[^>]*>(.*?)</h3>', src, flags=re.S):
        label = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        items.append(f'<li><a href="#{m.group(1)}">{label}</a></li>')
    if not items:
        return ""
    return ('<details class="on-this-page"><summary>In this chapter</summary><ol>'
            + "".join(items) + "</ol></details>")


def expand_includes(src):
    """<!-- @include src/figs/x.svg --> pastes a generated fragment in place (see src/figs/*.py)."""
    def repl(m):
        path = ROOT / m.group(1)
        if not path.exists():
            raise SystemExit(f"@include: missing {m.group(1)} (run the generator in src/figs/)")
        return path.read_text()
    return re.sub(r"<!--\s*@include\s+(\S+)\s*-->", repl, src)


def expand(src):
    for fn in (expand_includes, expand_cmds, expand_code_includes, expand_terminal, expand_pycode, expand_msg,
               expand_dialogue, expand_asides, expand_codebook, expand_callouts, expand_os, add_heading_ids):
        src = fn(src)
    return src


# ---------------------------------------------------------------- command-line field guide

FIELD_GUIDE = SRC / "field-guide.html"
CMD_RE = re.compile(r'<cmd\s+id="([^"]+)"\s+name="([^"]+)"\s+title="([^"]+)"(?:\s+ch="([^"]*)")?\s*>(.*?)</cmd>', re.S)


def field_guide_entries():
    """[(id, name, title, [chapter numbers])] in the order they appear in the guide."""
    if not FIELD_GUIDE.exists():
        return []
    return [(m.group(1), m.group(2), m.group(3), [int(c) for c in (m.group(4) or "").split(",") if c.strip()])
            for m in CMD_RE.finditer(FIELD_GUIDE.read_text())]


def cmd_names(name):
    return ' <span class="sep">/</span> '.join(f"<code>{html.escape(n.strip())}</code>" for n in name.split(" / "))


def expand_cmds(src):
    def repl(m):
        ident, name, title, chs, body = m.groups()
        links = []
        for c in [int(x) for x in (chs or "").split(",") if x.strip()]:
            links.append(f'<a href="{c}.html">Ch. {c}</a>' if is_ready(c) else f"<span>Ch. {c}</span>")
        used = f'<span class="cmd-ch">{" ".join(links)}</span>' if links else ""
        return (f'<section class="cmd" id="cmd-{ident}"><header><h4 class="cmd-name">{cmd_names(name)}</h4>'
                f'<span class="cmd-title">{title}</span>{used}</header>{body}</section>')
    return CMD_RE.sub(repl, src)


def commands_box(num):
    entries = [e for e in field_guide_entries() if num in e[3]]
    if not entries:
        return ""
    items = "".join(f'<li><a href="field-guide.html#cmd-{ident}">{cmd_names(name)}</a><span>{title}</span></li>'
                    for ident, name, title, _ in entries)
    return ('<aside class="commands"><div class="aside-tag"><svg aria-hidden="true"><use href="#icon-terminal"/></svg>'
            'At the command line</div><p>Real commands that show this chapter’s ideas on your own computer. '
            'The <a href="field-guide.html">Command-Line Field Guide</a> explains each one, with examples for macOS and Linux.</p>'
            f'<ul class="cmd-list">{items}</ul></aside>')


def build_field_guide():
    body = expand(FIELD_GUIDE.read_text())
    index = "".join(f'<a href="#cmd-{ident}">{cmd_names(name)}</a>' for ident, name, _, _ in field_guide_entries())
    content = f"""<div class="chapter fg-page">
{nav("table_of_contents.html", None)}
<main class="chapter-main">
  <header class="chapter-head">
    <div class="part-label">Reference</div>
    <h2><span>Command-Line Field Guide</span></h2>
    <p class="subtitle">Networking commands for macOS and Linux, with real output explained</p>
    {mini_toc(body).replace("In this chapter", "Sections")}
  </header>
  <nav class="cmd-index" aria-label="All commands">{index}</nav>
{body}
</main>
</div>"""
    return page(f"Command-Line Field Guide · {BOOK}", content, "chapter-page", "Networking commands for macOS and Linux", "field-guide.html")


# ---------------------------------------------------------------- pages

def build_chapter(num, part, title, subtitle):
    body = expand(chapter_path(num).read_text())
    box = commands_box(num)
    if box:
        body = body.replace('<section class="lab">', box + '<section class="lab">', 1) if '<section class="lab">' in body else body + box
    ready = [c[0] for c in CHAPTERS if is_ready(c[0])]
    idx = ready.index(num)
    prev_href = f"{ready[idx - 1]}.html" if idx > 0 else None
    next_num = ready[idx + 1] if idx + 1 < len(ready) else None
    next_href = f"{next_num}.html" if next_num else ("epilogue.html" if EPILOGUE.exists() else None)
    part_name = PARTS[part][0]
    if next_num:
        nxt = next(c for c in CHAPTERS if c[0] == next_num)
        onward = (f'<div class="next-chapter"><a href="{next_href}">Onward to Chapter {next_num}: '
                  f'{html.escape(nxt[2])} ⮕</a></div>')
    elif EPILOGUE.exists():
        onward = (f'<div class="next-chapter"><a href="epilogue.html">Onward to the Epilogue: '
                  f'{html.escape(EPILOGUE_TITLE[0])} ⮕</a></div>')
    else:
        onward = ('<div class="next-chapter"><a href="table_of_contents.html">'
                  'That\'s everything written so far. Back to the Table of Contents ⮕</a></div>')
    content = f"""<div class="chapter">
{nav(prev_href, next_href)}
<main class="chapter-main">
  <header class="chapter-head">
    <div class="part-label">Part {part} · {html.escape(part_name)}</div>
    <h2><span>{html.escape(title)}</span><span class="ch-num">Ch. {num}</span></h2>
    <p class="subtitle">{html.escape(subtitle)}</p>
    {mini_toc(body)}
  </header>
{body}
</main>
{onward}
</div>"""
    return page(f"{num}. {title} · {BOOK}", content, "chapter-page", subtitle, f"{num}.html")


def build_epilogue():
    body = expand(EPILOGUE.read_text())
    last = max(c[0] for c in CHAPTERS if is_ready(c[0]))
    content = f"""<div class="chapter">
{nav(f"{last}.html", "table_of_contents.html")}
<main class="chapter-main">
  <header class="chapter-head">
    <div class="part-label">Epilogue</div>
    <h2><span>{html.escape(EPILOGUE_TITLE[0])}</span></h2>
    <p class="subtitle">{html.escape(EPILOGUE_TITLE[1])}</p>
    {mini_toc(body)}
  </header>
{body}
</main>
<div class="next-chapter"><a href="table_of_contents.html">The end. Back to the Table of Contents ⮕</a></div>
</div>"""
    return page(f"Epilogue: {EPILOGUE_TITLE[0]} · {BOOK}", content, "chapter-page", EPILOGUE_TITLE[1], "epilogue.html")


def epilogue_toc():
    if not EPILOGUE.exists():
        return ""
    return (f'<section class="toc-ref"><h2><span>✱</span>Epilogue</h2><ol class="toc-list"><li><span class="num"></span>'
            f'<a href="epilogue.html">{html.escape(EPILOGUE_TITLE[0])}<span>{html.escape(EPILOGUE_TITLE[1])}</span></a></li></ol></section>')


def build_toc():
    parts_html = []
    for key, (name, blurb) in PARTS.items():
        rows = []
        for num, part, title, subtitle in CHAPTERS:
            if part != key:
                continue
            if is_ready(num):
                rows.append(f'<li><span class="num">{num}.</span><a href="{num}.html">{html.escape(title)}'
                            f'<span>{html.escape(subtitle)}</span></a></li>')
            else:
                rows.append(f'<li class="not-yet"><span class="num">{num}.</span><span class="t">{html.escape(title)}'
                            f'<span>{html.escape(subtitle)}</span></span><em>coming soon</em></li>')
        any_ready = any(is_ready(c[0]) for c in CHAPTERS if c[1] == key)
        cls = "" if any_ready else ' class="not-yet-part"'
        parts_html.append(f'<section{cls}><h2><span>{key}.</span>{html.escape(name)}</h2>'
                          f'<p class="part-blurb">{html.escape(blurb)}</p><ol class="toc-list">{"".join(rows)}</ol></section>')
    first = next(c[0] for c in CHAPTERS if is_ready(c[0]))
    content = f"""<div class="chapter toc-page">
{nav(None, f"{first}.html")}
<main class="chapter-main toc">
  <h1>Table of Contents</h1>
  {"".join(parts_html)}
  {epilogue_toc()}
  <section class="toc-ref"><h2><span>✱</span>Reference</h2>
  <ol class="toc-list"><li><span class="num"></span><a href="field-guide.html">Command-Line Field Guide<span>Networking commands for macOS and Linux, with real output explained</span></a></li></ol></section>
</main>
</div>"""
    return page(f"Table of Contents · {BOOK}", content, "toc-body", path="table_of_contents.html")


def build_index():
    body = (SRC / "index.html").read_text()
    return page(f"{BOOK} · {TAGLINE}", expand(body), "index-page", SHARE_DESCRIPTION)


def build_404():
    content = f"""<div class="chapter">
{nav(None, None)}
<main class="chapter-main">
  <h1>404: this packet got lost</h1>
  <p>No page lives at this address. It may have been renamed, or the link has a typo.</p>
  <p><a href="{SITE_URL}">Back to the start</a> · <a href="{SITE_URL}table_of_contents.html">Table of Contents</a></p>
</main>
</div>"""
    # GitHub Pages serves this file from any path, so its relative links would break: make them absolute
    content = content.replace('href="index.html"', f'href="{SITE_URL}"').replace(
        'href="table_of_contents.html"', f'href="{SITE_URL}table_of_contents.html"').replace(
        'href="field-guide.html"', f'href="{SITE_URL}field-guide.html"')
    out = page(f"Page not found · {BOOK}", content, "chapter-page")
    return (out.replace('href="assets/', f'href="{SITE_URL}assets/')
               .replace('src="assets/', f'src="{SITE_URL}assets/'))


# ---------------------------------------------------------------- checks

def check_links():
    problems = []
    ids_by_file = {}
    for f in SITE.glob("*.html"):
        ids_by_file[f.name] = set(re.findall(r'\sid="([^"]+)"', f.read_text()))
    for f in SITE.glob("*.html"):
        if f.name == "404.html":
            continue
        text = f.read_text()
        for href in re.findall(r'<[a-zA-Z][^<>]*?\s(?:href|src)="([^"]+)"', text):
            if href.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            path, _, frag = href.partition("#")
            path = path.partition("?")[0]
            if not path:  # same-page anchor, or sprite reference
                if frag and frag not in ids_by_file[f.name]:
                    problems.append(f"{f.name}: missing anchor #{frag}")
                continue
            target = SITE / path
            if not target.exists():
                problems.append(f"{f.name}: broken link {href}")
            elif frag and target.suffix == ".html" and frag not in ids_by_file.get(target.name, set()):
                problems.append(f"{f.name}: missing anchor {href}")
    return problems


def build():
    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()
    shutil.copytree(ROOT / "assets", SITE / "assets")
    shutil.copytree(ROOT / "labs", SITE / "labs",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "_out*", "*.key", "*.tle"))
    global _sprites_cache, _version_cache
    _sprites_cache = None
    _version_cache = None
    (SITE / "index.html").write_text(build_index())
    (SITE / "table_of_contents.html").write_text(build_toc())
    (SITE / "404.html").write_text(build_404())
    (SITE / ".nojekyll").write_text("")
    if FIELD_GUIDE.exists():
        (SITE / "field-guide.html").write_text(build_field_guide())
    if EPILOGUE.exists():
        (SITE / "epilogue.html").write_text(build_epilogue())
    count = 0
    for num, part, title, subtitle in CHAPTERS:
        if is_ready(num):
            (SITE / f"{num}.html").write_text(build_chapter(num, part, title, subtitle))
            count += 1
    problems = check_links()
    for p in problems:
        print("  !", p)
    print(f"built {count} chapters into {SITE.relative_to(ROOT)}/"
          + (f" with {len(problems)} link problem(s)" if problems else ""))
    return not problems


def watch():
    def snapshot():
        return {
            p: p.stat().st_mtime
            for d in ("src", "assets", "labs")
            for p in (ROOT / d).rglob("*") if p.is_file() and "__pycache__" not in p.parts
        }
    last = None
    while True:
        snap = snapshot()
        if snap != last:
            try:
                build()
            except SystemExit as e:
                print("build failed:", e)
            last = snap
        time.sleep(0.5)


if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch()
    else:
        sys.exit(0 if build() else 1)
