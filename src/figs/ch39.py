#!/usr/bin/env python3
"""Generate chapter 39 figures.  python3 src/figs/ch39.py"""
from pathlib import Path

from svgkit import Seq, fig, text

OUT = Path(__file__).parent


def box(x, y, w, h, cls="f-card", stroke="var(--line)", rx=8, dash=False, sw=1.6):
    d = ' stroke-dasharray="6 4"' if dash else ""
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx}" class="{cls}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def line(x1, y1, x2, y2, cls="s-ink", w=2.2, arrow=False, dash=False):
    mk = f' marker-end="url(#ah-{"ink" if cls == "s-ink" else cls[2:]})"' if arrow else ""
    d = ' stroke-dasharray="5 4"' if dash else ""
    return f'<path d="M{x1:g},{y1:g} L{x2:g},{y2:g}" class="line {cls}" stroke-width="{w}"{mk}{d}/>'


# ---------------------------------------------------------------- brains and hands

def planes():
    b = [text(180, 22, "every box thinks for itself", "mid sm b"), text(540, 22, "one brain, many hands", "mid sm b")]
    # left: four routers, each with its own control plane
    spots = [(70, 70), (290, 70), (70, 210), (290, 210)]
    for x, y in spots:
        b.append(box(x - 50, y - 26, 100, 70, "f-card"))
        b.append(box(x - 42, y - 20, 84, 24, "t-purple", "var(--purple)", 5, sw=1.2))
        b.append(text(x, y - 4, "brain: OSPF, BGP", "mid xs b"))
        b.append(box(x - 42, y + 10, 84, 26, "t-green", "var(--green)", 5, sw=1.2))
        b.append(text(x, y + 27, "hands: forwarding", "mid xs b"))
    for (x1, y1), (x2, y2) in [((120, 80), (240, 80)), ((120, 220), (240, 220)), ((70, 114), (70, 184)), ((290, 114), (290, 184))]:
        b.append(line(x1, y1, x2, y2, "s-muted", 3))
    b.append(text(180, 72, "maps, gossip", "mid xs hand muted"))
    b.append(text(180, 212, "maps, gossip", "mid xs hand muted"))
    b.append(text(180, 272, "and a person, logged in to each box, typing its settings", "mid xs"))
    b.append(line(360, 12, 360, 282, "s-line", 1.5, dash=True))
    # right: one controller, four switches
    b.append(box(460, 40, 160, 50, "t-purple", "var(--purple)"))
    b.append(text(540, 62, "the controller", "mid sm b"))
    b.append(text(540, 80, "a program, on a server", "mid xs"))
    sw = [(430, 200), (510, 200), (590, 200), (670, 200)]
    for x, y in sw:
        b.append(box(x - 32, y - 16, 64, 36, "t-green", "var(--green)", 6))
        b.append(text(x, y + 6, "switch", "mid xs b"))
        b.append(line(540, 90, x, y - 18, "s-purple", 1.6, dash=True))
    for (x1, _), (x2, _) in zip(sw, sw[1:]):
        b.append(line(x1 + 32, 202, x2 - 32, 202, "s-muted", 3))
    b.append(text(622, 116, "OpenFlow:", "xs b f-purple"))
    b.append(text(622, 131, "“here are your rules”", "xs hand f-purple"))
    b.append(text(550, 272, "the switches only match and forward", "mid xs"))
    svg = fig("".join(b), 720, 290, "Left: four routers each with their own control plane and data plane. Right: one controller programming four simple switches",
              "Every router has a <strong>control plane</strong>, the part that decides where things should go (Chapter 23’s maps, Chapter 24’s treaties), and a <strong>data plane</strong>, the part that actually moves packets. Software-defined networking takes the brains out of the boxes and puts them together, in one program.")
    (OUT / "ch39-planes.svg").write_text(svg)


# ---------------------------------------------------------------- the first packet asks; the rest don't

def reactive():
    q = Seq([("h1", 90, None), ("switch s1", 300, None), ("controller", 520, None), ("h2", 660, None)], top=40, scale=34, head=False)
    q.msg("h1", "switch s1", 0.3, 0.9, "ping to h2", "blue", step="1")
    q.note("switch s1", 1.4, "no rule matches…", step="1", side="left")
    q.msg("switch s1", "controller", 1.8, 2.6, "PACKET_IN", "purple", step="2", sub="port 1: 0a…01 → 0a…02")
    q.note("controller", 3.5, "h1: port 1, h2: port 2", step="3", side="left")
    q.msg("controller", "switch s1", 4.1, 4.9, "FLOW_MOD", "purple", step="3", sub="port 1, to 0a…02: output 2")
    q.msg("controller", "switch s1", 5.5, 6.2, "PACKET_OUT", "purple", step="3")
    q.msg("switch s1", "h2", 6.4, 7.0, "the first ping", "blue", step="3")
    q.msg("h1", "switch s1", 7.7, 8.1, "ping 2", "green", step="4")
    q.msg("switch s1", "h2", 8.1, 8.5, "", "green", step="4")
    q.msg("h1", "switch s1", 8.8, 9.2, "ping 3", "green", step="4")
    q.msg("switch s1", "h2", 9.2, 9.6, "", "green", step="4")
    q.note("switch s1", 10.2, "a rule matches: no need to ask", step="4", side="right")
    body, h = q.render(extra_bottom=16)
    steps = ["A ping from h1 arrives at the switch. Its flow table has only one row, the lowest-priority rule that matches anything: “send it to the controller”.",
             "So the switch wraps the packet in an OpenFlow <code>PACKET_IN</code> message and sends it to the controller, over an ordinary TCP connection.",
             "The controller learns where h1 is, looks up where h2 is, and answers twice: a <code>FLOW_MOD</code> adds a row to the table for next time, and a <code>PACKET_OUT</code> sends this packet on its way.",
             "Every later packet matches the new row, and the switch forwards it by itself, at full speed. The controller is only asked about the first packet of each conversation."]
    svg = fig(body, 720, h, "A sequence diagram: the first packet goes to the controller, which installs a rule; later packets are forwarded by the switch alone",
              "Reactive flow set-up: the controller is the switch’s memory and judgement, consulted once per conversation. (It could also install rules in advance, before any packet arrives: that’s <em>proactive</em>.)", steps)
    (OUT / "ch39-reactive.svg").write_text(svg)


# ---------------------------------------------------------------- P4: the pipeline

def p4():
    b = []
    stages = [("parser", "a state machine: read Ethernet, then IPv4 or IPv6, then TCP or UDP…", "t-blue", "var(--blue)", 116),
              ("ingress", "match-action tables: look up fields, run actions", "t-purple", "var(--purple)", 136),
              ("queues", "buffers, and scheduling", "f-card", "var(--line)", 96),
              ("egress", "more tables: rewrite on the way out", "t-purple", "var(--purple)", 118),
              ("deparser", "put the headers back together", "t-blue", "var(--blue)", 104)]
    x = 20
    for i, (name, what, cls, stroke, w) in enumerate(stages):
        b.append(box(x, 40, w, 64, cls, stroke))
        b.append(text(x + w / 2, 62, name, "mid sm b"))
        words, lines, cur = what.split(), [], ""
        for wd in words:
            if len(cur) + len(wd) > w // 6.3:
                lines.append(cur)
                cur = wd
            else:
                cur = (cur + " " + wd).strip()
        lines.append(cur)
        for k, ln in enumerate(lines[:3]):
            b.append(text(x + w / 2, 128 + k * 14, ln, "mid xs"))
        if i < len(stages) - 1:
            b.append(line(x + w + 2, 72, x + w + 18, 72, "s-ink", 2, arrow=True))
        x += w + 20
    b.append(text(20, 24, "packet in", "xs b muted"))
    b.append(text(700, 24, "packet out", "end xs b muted"))
    b.append(box(160, 186, 400, 60, "f-surface", "var(--line)", 8, dash=True))
    b.append(text(360, 206, "You write all five parts, in P4. The switch chip knows no protocols", "mid xs b"))
    b.append(text(360, 222, "until you teach it: not even Ethernet. Tables are filled in at run time,", "mid xs"))
    b.append(text(360, 238, "by a controller, just like OpenFlow’s.", "mid xs"))
    svg = fig("".join(b), 720, 256, "The P4 pipeline: parser, ingress match-action tables, queues, egress tables, deparser",
              "A P4 program describes a switch’s whole pipeline. OpenFlow lets you fill in tables whose shape was decided by the switch’s makers; P4 lets you decide the shape too.")
    (OUT / "ch39-p4.svg").write_text(svg)


# ---------------------------------------------------------------- eBPF: hooks in the Linux network stack

def hooks():
    b = [box(10, 10, 470, 340, "f-surface", "var(--line)", 12), text(24, 32, "inside the Linux kernel", "sm b")]
    layers = [("the network card’s driver", 290), ("sk_buff: Linux’s packet structure is built", 240),
              ("traffic control (tc)", 190), ("firewall, routing (Chapters 20, 34)", 140), ("TCP, UDP, sockets", 90)]
    for name, y in layers:
        b.append(box(30, y, 250, 34, "f-card", "var(--line)", 6))
        b.append(text(155, y + 22, name, "mid xs b"))
    b.append(line(155, 344, 155, 326, "s-ink", 2.4, arrow=True))
    for y in (290, 240, 190, 140):
        b.append(line(155, y, 155, y - 14, "s-ink", 2, arrow=True))
    b.append(text(155, 64, "↑ to the program, e.g. a web server", "mid xs muted"))
    hooks = [(307, "XDP", ["before Linux builds its packet:", "the fastest place to drop"]),
             (207, "tc", ["filter, rewrite, redirect"]),
             (157, "netfilter", ["(nftables isn’t eBPF)"]),
             (107, "sockets", ["socket filters: the old BPF", "job (Chapter 16)"])]
    for y, name, what in hooks:
        dim = name == "netfilter"
        b.append(f'<circle cx="288" cy="{y}" r="7" class="{"f-muted" if dim else "f-orange"}"/>')
        b.append(text(302, y + 4, name, "xs b" + (" muted" if dim else " f-orange")))
        for k, w in enumerate(what):
            b.append(text(302, y + 18 + k * 13, w, "xs" + (" muted" if dim else "")))
    b.append(text(24, 342, "a packet arrives ↑", "xs muted"))
    # the loading path
    b.append(box(492, 10, 218, 340, "f-card", "var(--line)", 12))
    b.append(text(506, 32, "how a program gets there", "sm b"))
    stepsx = [("your program: instructions", "t-blue", "var(--blue)"), ("the verifier: is it safe?", "t-yellow", "var(--yellow)"),
              ("JIT: compiled to machine code", "t-purple", "var(--purple)"), ("attached to a hook", "t-orange", "var(--orange)")]
    for i, (name, cls, stroke) in enumerate(stepsx):
        y = 46 + i * 66
        b.append(box(502, y, 198, 34, cls, stroke, 6))
        b.append(text(601, y + 22, name, "mid xs b"))
        if i < 3:
            b.append(line(560, y + 36, 560, y + 64, "s-ink", 2, arrow=True))
    b.append(text(572, 160, "no endless loops,", "xs hand"))
    b.append(text(572, 173, "no bad pointers", "xs hand"))
    b.append(box(502, 296, 198, 44, "t-green", "var(--green)", 6))
    b.append(text(601, 314, "maps: memory shared with", "mid xs b"))
    b.append(text(601, 329, "programs outside the kernel", "mid xs b"))
    svg = fig("".join(b), 720, 360, "The Linux receive path, with eBPF hook points at the driver (XDP), traffic control, and sockets; and the path a program takes: verifier, JIT, attach",
              "Where eBPF programs can run as a packet climbs through Linux, and how one gets there. There are many more hooks outside networking: almost every function in the kernel can have a program attached, for tracing.")
    (OUT / "ch39-hooks.svg").write_text(svg)


# ---------------------------------------------------------------- one eBPF instruction, taken apart

def insn():
    parts = [("55", "opcode", "jump if not equal,", "to a number", "t-purple", "var(--purple)", 1),
             ("00", "registers", "dst = r0,", "src = unused", "t-blue", "var(--blue)", 1),
             ("0c 00", "offset", "skip 12", "instructions", "t-orange", "var(--orange)", 2),
             ("00 08 00 00", "number", "0x0800:", "IPv4", "t-green", "var(--green)", 4)]
    b = [text(360, 22, "jne r0, 0x0800, +12  =  if r0 isn’t 0x0800, skip the next 12 instructions", "mid sm b mono")]
    x, unit = 60, 75
    for byt, name, l1, l2, cls, stroke, n in parts:
        w = n * unit
        b.append(box(x, 40, w - 4, 40, cls, stroke, 6))
        b.append(text(x + (w - 4) / 2, 66, byt, "mid sm b mono"))
        b.append(text(x + (w - 4) / 2, 100, name, "mid xs b"))
        b.append(text(x + (w - 4) / 2, 116, l1, "mid xs"))
        b.append(text(x + (w - 4) / 2, 130, l2, "mid xs"))
        x += w
    b.append(text(360, 158, "Eight bytes, little-endian. Compare Chapter 16’s classic BPF: the same idea, with more registers and more room.", "mid xs muted"))
    svg = fig("".join(b), 720, 170, "One eBPF instruction, eight bytes: opcode 55, registers 00, offset 0c 00, immediate 00 08 00 00",
              "The third instruction of this chapter’s counting program, as the kernel receives it.")
    (OUT / "ch39-insn.svg").write_text(svg)


if __name__ == "__main__":
    planes()
    reactive()
    p4()
    hooks()
    insn()
    print("wrote ch39 figures")
