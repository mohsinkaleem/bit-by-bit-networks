#!/usr/bin/env python3
"""Generate the epilogue's figure.  python3 src/figs/epilogue.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


def stack():
    rows = [("running the network", "middleboxes, tunnels, containers, programmable networks, troubleshooting", "34–36, 38, 39", "f-card", "var(--line)"),
            ("keeping secrets", "cryptography, TLS, post-quantum locks", "31, 32, 42", "t-purple", "var(--purple)"),
            ("names and applications", "names, the web, DNS, HTTP, a page load from end to end", "6, 7, 14, 29, 30, 37", "t-green", "var(--green)"),
            ("between programs", "ports, retries, TCP, UDP, QUIC, bundles for Mars", "12, 13, 26–28, 33, 41", "t-teal", "var(--teal)"),
            ("between networks", "routers, IP, routing, BGP, IPv6, named data", "11, 20–25, 43", "t-blue", "var(--blue)"),
            ("on one link", "frames, addresses, switches, Ethernet, Wi-Fi, meshes", "5, 8–10, 18, 19, 44", "t-orange", "var(--orange)"),
            ("signals", "a flashlight, wires, glass, radio, satellites", "1–3, 17, 40", "t-yellow", "var(--yellow)")]
    b = []
    for i, (layer, what, chs, cls, stroke) in enumerate(rows):
        y = 14 + i * 44
        w = 560 + i * 20
        x = (720 - w) / 2
        b.append(f'<rect x="{x:g}" y="{y}" width="{w:g}" height="38" rx="7" class="{cls}" stroke="{stroke}" stroke-width="1.5"/>')
        b.append(text(x + 14, y + 17, layer, "xs b"))
        b.append(text(x + 14, y + 31, what, "xs"))
        b.append(text(x + w - 14, y + 24, f"ch. {chs}", "end xs muted"))
    b.append(text(360, 14 + 7 * 44 + 14, "…and the lamp still says HI.", "mid sm hand"))
    svg = fig("".join(b), 720, 14 + 7 * 44 + 24, "The layers built in this book, from signals at the bottom to running the network at the top, with the chapters for each",
              "Everything this book built, from the flashlight up. Each layer only has to trust the one beneath it to do its job, which is the whole trick.")
    (OUT / "epilogue-stack.svg").write_text(svg)


if __name__ == "__main__":
    stack()
    print("wrote epilogue figure")
