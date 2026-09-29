#!/usr/bin/env python3
"""Generate chapter 36 figures.  python3 src/figs/ch36.py"""
from pathlib import Path

from svgkit import fig, text

OUT = Path(__file__).parent


def box(x, y, w, h, cls="f-card", stroke="var(--line)", rx=8, dash=False):
    d = ' stroke-dasharray="6 4"' if dash else ""
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx}" class="{cls}" stroke="{stroke}" stroke-width="1.6"{d}/>'


def line(x1, y1, x2, y2, cls="s-ink", w=2.2, arrow=False, dash=False):
    mk = f' marker-end="url(#ah-{"ink" if cls == "s-ink" else cls[2:]})"' if arrow else ""
    d = ' stroke-dasharray="5 4"' if dash else ""
    return f'<path d="M{x1:g},{y1:g} L{x2:g},{y2:g}" class="line {cls}" stroke-width="{w}"{mk}{d}/>'


# ---------------------------------------------------------------- what a network namespace holds

def netns():
    b = [box(10, 10, 700, 230, "f-surface", "var(--line)", 14),
         text(24, 32, "one Linux kernel", "sm b"),
         text(24, 50, "(the Pi)", "xs muted")]
    spaces = [("the host", ["lo", "wlan0 192.168.1.4", "eth0 (no cable)"], "routes: default via 192.168.1.1", "ports: 22 (ssh), …", "t-blue", "var(--blue)"),
              ("“web”", ["lo", "eth0 10.36.0.2"], "routes: default via 10.36.0.1", "ports: 80", "t-green", "var(--green)"),
              ("“bot”", ["lo", "eth0 10.36.0.4"], "routes: default via 10.36.0.1", "ports: 80 (as well!)", "t-orange", "var(--orange)")]
    for i, (name, devs, routes, ports, cls, stroke) in enumerate(spaces):
        x = 30 + i * 226
        b.append(box(x, 64, 206, 160, cls, stroke))
        b.append(text(x + 12, 86, name, "sm b"))
        for k, d in enumerate(devs):
            b.append(text(x + 12, 108 + k * 16, "▸ " + d, "xs mono"))
        b.append(text(x + 12, 170, routes, "xs"))
        b.append(text(x + 12, 188, ports, "xs"))
        b.append(text(x + 12, 206, "its own firewall, ARP table…", "xs muted"))
    svg = fig("".join(b), 720, 250, "One kernel holding three network namespaces, each with its own devices, addresses, routes and ports",
              "Network <strong>namespaces</strong>: one kernel, several complete, separate network stacks. A process in “web” sees only web’s devices, routes, firewall and ports. Nothing is copied: the kernel just gives each group of processes a different view.")
    (OUT / "ch36-netns.svg").write_text(svg)


# ---------------------------------------------------------------- container networking by hand (box.sh)

def byhand():
    b = []
    # the host
    b.append(box(10, 10, 700, 300, "f-surface", "var(--line)", 14))
    b.append(text(24, 30, "Grandpa’s Pi: the host", "sm b"))
    b.append(box(520, 40, 170, 50, "t-blue", "var(--blue)"))
    b.append(text(605, 60, "wlan0", "mid sm b"))
    b.append(text(605, 78, "192.168.1.4", "mid xs mono"))
    b.append(line(690, 65, 712, 65, "s-blue", 3))
    b.append(box(300, 40, 190, 50, "t-purple", "var(--purple)"))
    b.append(text(395, 60, "routing + NAT (nftables)", "mid xs b"))
    b.append(text(395, 78, "masquerade · 8036 → web:80", "mid xs mono"))
    b.append(line(490, 65, 520, 65, "s-ink", 2))
    b.append(box(40, 110, 640, 40, "t-teal", "var(--teal)"))
    b.append(text(360, 134, "br36: a software switch · the host is 10.36.0.1 on it", "mid sm b"))
    b.append(line(395, 90, 395, 110, "s-ink", 2))
    for i, (name, ip, cls, stroke) in enumerate([("web", "10.36.0.2", "t-green", "var(--green)"), ("db", "10.36.0.3", "t-yellow", "var(--yellow)"),
                                                  ("bot", "10.36.0.4", "t-orange", "var(--orange)")]):
        x = 70 + i * 210
        b.append(line(x + 70, 150, x + 70, 212, "s-muted", 3))
        b.append(text(x + 78, 186, f"veth-{name}", "xs mono muted"))
        b.append(box(x, 212, 150, 84, cls, stroke))
        b.append(text(x + 75, 234, f"namespace “{name}”", "mid xs b"))
        b.append(text(x + 75, 256, f"eth0 {ip}", "mid xs mono"))
        b.append(text(x + 75, 274, "default via 10.36.0.1", "mid xs mono muted"))
    svg = fig("".join(b), 720, 318, "The box.sh layout: three namespaces with veth cables into a bridge, the host routing and NATing to wlan0",
              "Chapter 36’s <code>box.sh</code>: three “containers” plugged into a software switch, with the host as their router and NAT. Docker’s default network is the same picture, with the bridge called <code>docker0</code> and addresses from 172.17.0.0/16.")
    (OUT / "ch36-byhand.svg").write_text(svg)


# ---------------------------------------------------------------- the real Podman layers on a Mac

def podman():
    b = []
    b.append(box(10, 10, 700, 316, "t-blue", "var(--blue)", 14))
    b.append(text(24, 32, "Bob’s MacBook (macOS)", "sm b"))
    b.append(text(24, 50, "gvproxy listens on :8036, and passes connections into the VM", "xs"))
    b.append(box(40, 64, 650, 250, "f-surface", "var(--line)", 12))
    b.append(text(54, 86, "a Linux virtual machine: enp0s1 192.168.127.2, gateway 192.168.127.1 (gvproxy again)", "xs b"))
    b.append(box(70, 100, 600, 200, "t-purple", "var(--purple)", 12, dash=True))
    b.append(text(84, 122, "Podman’s rootless network namespace (pasta gives it a copy of enp0s1)", "xs b"))
    b.append(box(100, 136, 540, 34, "t-teal", "var(--teal)"))
    b.append(text(370, 158, "podman1: a bridge · 10.89.0.1 · aardvark-dns answers names here", "mid xs b"))
    for i, (name, ip, cls, stroke) in enumerate([("web", "10.89.0.4", "t-green", "var(--green)"), ("db", "10.89.0.5", "t-yellow", "var(--yellow)"),
                                                  ("pub", "port 80 ⇐ Mac’s 8036", "t-orange", "var(--orange)")]):
        x = 120 + i * 180
        b.append(line(x + 70, 170, x + 70, 218, "s-muted", 3))
        b.append(text(x + 78, 198, f"veth{i}", "xs mono muted"))
        b.append(box(x, 218, 140, 64, cls, stroke))
        b.append(text(x + 70, 242, f"container “{name}”", "mid xs b"))
        b.append(text(x + 70, 262, ip, "mid xs mono"))
    svg = fig("".join(b), 720, 336, "Nested layers on a Mac: macOS, a Linux VM, Podman's rootless network namespace, a bridge, and containers on veth cables",
              "The real layers behind <code>podman run</code> on Bob’s MacBook. Containers need a Linux kernel, so on a Mac they run inside a small Linux VM, and inside that, in namespaces, the same bridge-and-veth picture as the Pi.")
    (OUT / "ch36-podman.svg").write_text(svg)


# ---------------------------------------------------------------- Kubernetes networking

def k8s():
    b = []
    for n, (x, subnet, pods) in enumerate([(10, "10.244.1.0/24", [("garden-7d9f", "10.244.1.5"), ("weather-2c1a", "10.244.1.6")]),
                                           (370, "10.244.2.0/24", [("garden-4b8e", "10.244.2.7"), ("db-0", "10.244.2.8")])]):
        b.append(box(x, 40, 340, 190, "f-surface", "var(--line)", 12))
        b.append(text(x + 14, 60, f"node {n + 1}: a computer · pods get {subnet}", "xs b"))
        b.append(box(x + 20, 150, 300, 30, "t-teal", "var(--teal)"))
        b.append(text(x + 170, 170, "a bridge (or routes), set up by the CNI plugin", "mid xs"))
        for k, (pod, ip) in enumerate(pods):
            px = x + 30 + k * 150
            b.append(box(px, 72, 130, 56, "t-green", "var(--green)"))
            b.append(text(px + 65, 94, f"pod {pod}", "mid xs b"))
            b.append(text(px + 65, 114, ip, "mid xs mono"))
            b.append(line(px + 65, 128, px + 65, 150, "s-muted", 2.5))
        b.append(text(x + 170, 212, "kube-proxy: Service addresses → pods", "mid xs muted"))
    b.append('<g data-show="2">' + line(350, 165, 370, 165, "s-orange", 3) + text(360, 250, "between nodes: an overlay (VXLAN, Chapter 35) or plain routes (often BGP, Chapter 24)", "mid xs b f-orange") + "</g>")
    b.append('<g data-show="3">' + box(220, 270, 280, 44, "t-purple", "var(--purple)")
             + text(360, 290, "Service “garden”: 10.96.0.20:80", "mid xs b")
             + text(360, 306, "garden.default.svc.cluster.local", "mid xs mono") + "</g>")
    b.append(text(360, 24, "a Kubernetes cluster", "mid sm b"))
    steps = ["Every <strong>pod</strong> (one or more containers that share a network namespace) gets its own IP address, from a range belonging to its node. On one node, pods are connected much like <code>box.sh</code>’s boxes.",
             "Kubernetes’ one rule: every pod can reach every other pod’s address directly, with no NAT, whichever node it’s on. A <strong>CNI plugin</strong> makes that true, either by tunnelling between nodes (VXLAN), or by telling the network routes to each node’s pod range.",
             "Pods come and go, and their addresses change, so clients use a <strong>Service</strong>: a stable virtual address, and a DNS name. No computer actually has 10.96.0.20: on every node, kube-proxy (or an eBPF program, Chapter 39) rewrites packets for it with DNAT to one of the garden pods, a load balancer (Chapter 34) built into every node."]
    svg = fig("".join(b), 720, 322, "A Kubernetes cluster with two nodes, pods with their own IP addresses, connections between nodes, and a Service with a virtual IP and DNS name",
              "How Kubernetes networking fits together.", steps)
    (OUT / "ch36-k8s.svg").write_text(svg)


if __name__ == "__main__":
    netns()
    byhand()
    podman()
    k8s()
    print("wrote ch36 figures")
