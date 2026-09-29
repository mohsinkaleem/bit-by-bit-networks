#!/usr/bin/env python3
"""Generate chapter 26 figures.  python3 src/figs/ch26.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


# ---------------------------------------------------------------- a socket, inside the kernel

def socket_fig():
    b = ['<rect x="10" y="10" width="700" height="90" rx="10" class="t-blue" stroke="var(--blue)" stroke-width="1.5"/>',
         text(24, 30, "your program", "sm b", style="fill:var(--blue)"),
         '<rect x="10" y="118" width="700" height="190" rx="10" class="f-card" stroke="var(--line)" stroke-width="1.5"/>',
         text(24, 138, "the operating system’s kernel", "sm b muted"),
         '<line x1="10" y1="109" x2="710" y2="109" class="line s-muted dash" stroke-width="1.5"/>',
         text(706, 106, "system calls cross here", "end xs muted")]
    # the calls
    calls = [("s = socket(AF_INET, SOCK_DGRAM)", "1"), ("s.bind((\"0.0.0.0\", 7123))", "2"), ("data, who = s.recvfrom(512)", "4"),
             ("s.sendto(reply, who)", "4")]
    for i, (c, step) in enumerate(calls):
        x = 30 + (i % 2) * 340
        y = 52 + (i // 2) * 26
        b.append(f'<g data-show="{step}">' + text(x, y, c, "mono sm b") + "</g>")
    # socket table
    b.append('<g data-show="1">'
             '<rect x="30" y="152" width="300" height="140" rx="8" class="f-surface" stroke="var(--line)"/>'
             + text(180, 172, "the socket table", "mid xs b")
             + text(44, 196, "UDP  *:5353       (mDNS, Chapter 22)", "mono xs")
             + text(44, 216, "UDP  127.0.0.1:53 (a name server)", "mono xs") + "</g>")
    b.append('<g data-show="2"><rect x="38" y="228" width="284" height="22" rx="4" class="t-yellow" stroke="var(--yellow)"/>'
             + text(44, 243, "UDP  *:7123       ← our socket", "mono xs b") + "</g>")
    b.append('<g data-show="=1">' + text(44, 243, "UDP  *:7123 ?     not yet: no port", "mono xs muted") + "</g>")
    # buffer
    b.append('<g data-show="2">' + text(380, 172, "our socket’s receive buffer", "xs b")
             + "".join(f'<rect x="{380 + i * 38}" y="182" width="32" height="30" rx="4" class="f-surface" stroke="var(--line)"/>' for i in range(8))
             + "</g>")
    b.append('<g data-show="3"><rect x="380" y="182" width="32" height="30" rx="4" class="t-green" stroke="var(--green)"/>'
             '<rect x="418" y="182" width="32" height="30" rx="4" class="t-green" stroke="var(--green)"/></g>')
    b.append('<g data-show="3-4"><path d="M680,280 C640,250 520,240 440,216" class="line s-green" stroke-width="2.5" marker-end="url(#ah-green)"/>'
             + text(600, 296, "a datagram for port 7123 arrives", "mid xs b f-green") + "</g>")
    b.append('<g data-show="=4"><path d="M396,180 C396,150 380,120 300,70" class="line s-blue" stroke-width="2.5" marker-end="url(#ah-blue)"/>'
             + text(460, 150, "recvfrom() takes the oldest one", "xs b", style="fill:var(--blue)") + "</g>")
    b.append('<g data-show="5"><path d="M690,250 C660,245 640,245 620,250" class="line s-red" stroke-width="2.5"/>'
             + text(700, 240, "one for port 7777: no such socket", "end xs b f-red")
             + text(700, 262, "→ drop it, send back ICMP “port unreachable”", "end xs b f-red") + "</g>")
    steps = ["<code>socket()</code> asks the kernel for a new socket: an entry in its table, and a number (a “file descriptor”) the program uses to refer to it. It has no port yet.",
             "<code>bind()</code> claims a port. From now on, the kernel will deliver datagrams for UDP port 7123 to this socket, and it gets a <strong>receive buffer</strong> to keep them in until the program asks. (A program that just calls <code>sendto()</code> without binding gets a random port, as Chapter 12’s clients did.)",
             "Datagrams arrive whenever they like, whether the program is ready or not. The kernel looks up the destination port in its table, finds our socket, and puts the datagram at the end of its buffer.",
             "<code>recvfrom()</code> takes the oldest datagram out of the buffer, with the address and port it came from, so the program knows where to send the reply. If the buffer is empty, it waits.",
             "A datagram for a port with no socket has nowhere to go. The kernel throws it away, and sends back an ICMP “port unreachable” (Chapter 21), which is what Chapter 12’s “nobody home” was."]
    svg = fig("".join(b), 720, 318, "A program's socket calls, the kernel's socket table, and a receive buffer filling with datagrams",
              "What a UDP socket really is: an entry in the kernel’s table, and a queue.", steps)
    (OUT / "ch26-socket.svg").write_text(svg)


# ---------------------------------------------------------------- four timestamps

def ntp():
    # real numbers from `ntp.py time.apple.com --explain`, relative to t1 (ms)
    t1, t2, t3, t4 = 0.0, 93.638, 93.647, 51.657
    offset = ((t2 - t1) + (t3 - t4)) / 2
    xc, xs = 150, 570
    y0, sc = 70, 2.6
    b = [text(xc, 30, "Bob’s MacBook", "mid slab b"), text(xc, 48, "(its clock)", "mid xs muted"),
         text(xs, 30, "time.apple.com", "mid slab b"), text(xs, 48, "(its clock, which is right)", "mid xs muted")]
    b.append(f'<line x1="{xc}" y1="{y0 - 6}" x2="{xc}" y2="{y0 + 170 * sc / 2.6 * 1.3:g}" class="line s-muted" stroke-width="2" stroke-dasharray="2 5"/>')
    b.append(f'<line x1="{xs}" y1="{y0 - 6}" x2="{xs}" y2="{y0 + 170 * sc / 2.6 * 1.3:g}" class="line s-muted" stroke-width="2" stroke-dasharray="2 5"/>')
    # draw in "true time": the server's clock is right, the Mac's reads 67.8 ms low
    def yt(true_ms):
        return y0 + 10 + true_ms * 2.1
    true1 = t1 + offset            # when the Mac read t1, the true time was later
    true4 = t4 + offset
    b.append(f'<g data-show="1"><circle cx="{xc}" cy="{yt(true1):g}" r="5" class="f-blue"/>'
             + text(xc - 12, yt(true1) + 5, "t1 = 20.689401", "end mono xs b", style="fill:var(--blue)") + "</g>")
    b.append(f'<g data-show="1"><line x1="{xc}" y1="{yt(true1):g}" x2="{xs - 6}" y2="{yt(t2) - 2:g}" class="line s-navy" stroke-width="2.5" marker-end="url(#ah-ink)"/>'
             + text((xc + xs) / 2, (yt(true1) + yt(t2)) / 2 - 8, "request", "mid xs b halo") + "</g>")
    b.append(f'<g data-show="2"><circle cx="{xs}" cy="{yt(t2):g}" r="5" class="f-purple"/>'
             + text(xs + 12, yt(t2) - 2, "t2 = 20.783039", "mono xs b", style="fill:var(--purple)")
             + f'<circle cx="{xs}" cy="{yt(t3) + 8:g}" r="5" class="f-purple"/>'
             + text(xs + 12, yt(t3) + 14, "t3 = 20.783048", "mono xs b", style="fill:var(--purple)") + "</g>")
    b.append(f'<g data-show="3"><line x1="{xs}" y1="{yt(t3) + 8:g}" x2="{xc + 6}" y2="{yt(true4) - 2:g}" class="line s-purple" stroke-width="2.5" marker-end="url(#ah-purple)"/>'
             + text((xc + xs) / 2, (yt(t3) + yt(true4)) / 2 + 22, "reply, carrying t2 and t3", "mid xs b halo")
             + f'<circle cx="{xc}" cy="{yt(true4):g}" r="5" class="f-blue"/>'
             + text(xc - 12, yt(true4) + 5, "t4 = 20.741058", "end mono xs b", style="fill:var(--blue)") + "</g>")
    b.append('<g data-show="4">' + text(360, 316, "delay = (t4 − t1) − (t3 − t2) = 51.66 − 0.01 = 51.65 ms on the network", "mid sm b")
             + text(360, 338, "offset = ((t2 − t1) + (t3 − t4)) / 2 = (93.64 + 41.99) / 2 = +67.81 ms: the MacBook is behind", "mid sm b f-orange") + "</g>")
    steps = ["The MacBook notes the time by its own clock, <strong>t1</strong>, and sends a 48-byte request. (All times are seconds past 16:55, from this chapter’s lab.)",
             "The server notes when the request arrived, <strong>t2</strong>, and when its reply leaves, <strong>t3</strong>, by its own clock. They’re nine microseconds apart.",
             "The MacBook notes when the reply arrives, <strong>t4</strong>. Look: by the MacBook’s clock, the reply arrived before the server sent it! That’s because the two clocks disagree.",
             "Four timestamps are enough to separate the two unknowns. The time spent travelling is the whole round trip, minus the server’s thinking time. And if the journey took as long each way, the difference between the clocks is the average of the two “gaps”. Bob’s MacBook is about 68 milliseconds slow."]
    svg = fig("".join(b), 720, 350, "An NTP exchange with four real timestamps, t1 to t4, and the formulas for network delay and clock offset",
              "How NTP measures a clock it can’t see, across a network it can’t measure.", steps)
    (OUT / "ch26-ntp.svg").write_text(svg)


# ---------------------------------------------------------------- the whole UDP header

def header():
    fields = [("source port", "50123", "which socket it came from"), ("destination port", "123", "which socket it’s for"),
              ("length", "56", "header + data, in bytes"), ("checksum", "0x0862", "covers the header, data and addresses")]
    b = []
    for i, (name, value, note) in enumerate(fields):
        x = 40 + (i % 2) * 320
        y = 20 + (i // 2) * 60
        b.append(f'<rect x="{x}" y="{y}" width="310" height="44" rx="4" class="t-yellow" stroke="var(--yellow)" stroke-width="1.5"/>')
        b.append(text(x + 12, y + 18, name, "xs b"))
        b.append(text(x + 12, y + 35, note, "xs muted"))
        b.append(text(x + 298, y + 28, value, "end mono sm b"))
    b.append('<rect x="40" y="140" width="630" height="44" rx="4" class="t-green" stroke="var(--green)" stroke-width="1.5"/>')
    b.append(text(355, 167, "the data: 48 bytes of NTP request", "mid xs b"))
    b.append(text(355, 206, "That’s all of it: 8 bytes. Everything else is up to the program.", "mid sm"))
    svg = fig("".join(b), 720, 218, "The four fields of a UDP header: source port, destination port, length and checksum, followed by the data",
              "A simple NTP request from Bob’s MacBook (192.168.1.3) to time.apple.com, with its real checksum. Compare TCP’s header in Chapter 27.")
    (OUT / "ch26-header.svg").write_text(svg)


if __name__ == "__main__":
    socket_fig()
    ntp()
    header()
    print("wrote ch26 figures")
