"""Tiny helpers shared by the figure generators in src/figs/."""
from html import escape


def fig(svg_body, width, height, label, caption=None, stepper_steps=None, extra_class=""):
    """Wrap SVG content in a <figure>. stepper_steps: list of caption strings (HTML)."""
    cls = "fig" + (" stepper" if stepper_steps else "") + (f" {extra_class}" if extra_class else "")
    widget = ' data-widget="stepper"' if stepper_steps else ""
    out = [f'<figure class="{cls}"{widget}>',
           f'<svg class="dia" viewBox="0 0 {width:g} {height:g}" role="img" aria-label="{escape(label)}">',
           svg_body, "</svg>"]
    if stepper_steps:
        out.append('<ol class="steps">' + "".join(f"<li>{s}</li>" for s in stepper_steps) + "</ol>")
    if caption:
        out.append(f"<figcaption>{caption}</figcaption>")
    out.append("</figure>\n")
    return "\n".join(out)


def text(x, y, s, cls="", **attrs):
    extra = "".join(f' {k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<text x="{x:g}" y="{y:g}" class="{cls}"{extra}>{s}</text>'


def wave_path(levels, x0, y_mid, seg_w, amp):
    """levels: list of numbers in [-1, 1], each lasting seg_w. Returns an SVG path d string."""
    d = []
    x = x0
    prev = None
    for lv in levels:
        y = y_mid - lv * amp
        if prev is None:
            d.append(f"M{x:g},{y:g}")
        elif lv != prev:
            d.append(f"L{x:g},{y:g}")
        x += seg_w
        d.append(f"L{x:g},{y:g}")
        prev = lv
    return " ".join(d)


def curve_path(values, x0, y_mid, dx, amp):
    """values: list of floats in volts-ish units (scaled by amp). Smooth polyline."""
    pts = [f"{x0 + i * dx:.1f},{y_mid - v * amp:.1f}" for i, v in enumerate(values)]
    return "M" + " L".join(pts)


def level_axes(x0, x1, y_mid, amp, labels=("+5 V", "0 V", "−5 V")):
    """Faint horizontal guides at +amp, 0 and -amp with labels on the left."""
    out = []
    for i, (dy, lab) in enumerate(zip((-amp, 0, amp), labels)):
        y = y_mid + dy
        out.append(f'<line x1="{x0}" y1="{y:g}" x2="{x1}" y2="{y:g}" class="grid"'
                   + (' stroke-dasharray="4 4"' if dy else "") + "/>")
        if lab:
            out.append(text(x0 - 8, y + 4, lab, "end xs muted"))
    return "".join(out)


# ---------------------------------------------------------------- sequence diagrams
# Time runs downward. Each item may carry step="3" (stepper data-show spec).

class Seq:
    def __init__(self, actors, top=86, scale=30, width=720, head=True):
        """actors: list of (name, x, sprite_id or None)."""
        self.actors = {name: x for name, x, _ in actors}
        self.sprites = actors
        self.top, self.scale, self.width = top, scale, width
        self.items = []
        self.max_t = 0
        self.head = head

    def y(self, t):
        self.max_t = max(self.max_t, t)
        return self.top + t * self.scale

    def _wrap(self, body, step):
        return f'<g data-show="{step}">{body}</g>' if step else body

    def msg(self, a, b, t0, t1, label, cls="navy", step=None, lost=None, label_at=0.5, sub=None):
        x0, x1 = self.actors[a], self.actors[b]
        y0, y1 = self.y(t0), self.y(t1)
        if lost is not None:
            xe, ye = x0 + (x1 - x0) * lost, y0 + (y1 - y0) * lost
            body = (f'<line x1="{x0}" y1="{y0:g}" x2="{xe:g}" y2="{ye:g}" class="line s-red dash" stroke-width="2.5"/>'
                    f'<path d="M{xe - 9:g},{ye - 9:g} l18,18 M{xe + 9:g},{ye - 9:g} l-18,18" class="line s-red" stroke-width="3.5"/>')
            lx, ly = x0 + (x1 - x0) * lost * 0.5, y0 + (y1 - y0) * lost * 0.5
        else:
            body = (f'<line x1="{x0}" y1="{y0:g}" x2="{x1}" y2="{y1:g}" class="line s-{cls}" stroke-width="2.5" '
                    f'marker-end="url(#ah-{"ink" if cls == "navy" else cls})"/>')
            lx, ly = x0 + (x1 - x0) * label_at, y0 + (y1 - y0) * label_at
        body += f'<text x="{lx:g}" y="{ly - 7:g}" class="mid mono sm b halo">{label}</text>'
        if sub:
            body += f'<text x="{lx:g}" y="{ly + 16:g}" class="mid xs muted halo">{sub}</text>'
        self.items.append(self._wrap(body, step))

    def note(self, actor, t, label, step=None, cls="", side=None):
        x = self.actors[actor]
        center = sum(self.actors.values()) / len(self.actors)
        side = side or ("right" if x < center else "left")
        anchor, dx = ("start", 14) if side == "right" else ("end", -14)
        y = self.y(t)
        body = (f'<circle cx="{x}" cy="{y:g}" r="5" class="f-ink"/>'
                f'<text x="{x + dx}" y="{y + 5:g}" class="hand {cls} halo" text-anchor="{anchor}">{label}</text>')
        self.items.append(self._wrap(body, step))

    def timer(self, actor, t0, t1, label, step=None, side="left"):
        x = self.actors[actor]
        dx = -22 if side == "left" else 22
        y0, y1 = self.y(t0), self.y(t1)
        body = (f'<path d="M{x + dx * 0.4:g},{y0:g} L{x + dx:g},{y0:g} L{x + dx:g},{y1:g} L{x + dx * 0.4:g},{y1:g}" '
                f'class="line s-orange" stroke-width="2.5"/>'
                f'<text x="{x + dx * 1.4:g}" y="{(y0 + y1) / 2 + 5:g}" class="hand f-orange halo" '
                f'text-anchor="{"end" if side == "left" else "start"}">{label}</text>')
        self.items.append(self._wrap(body, step))

    def render(self, extra_bottom=30):
        bottom = self.top + self.max_t * self.scale + extra_bottom
        out = []
        for name, x, sprite in self.sprites:
            if self.head and sprite:
                out.append(f'<use href="#{sprite}-head" x="{x - 26}" y="4" width="52" height="52"/>')
            out.append(f'<text x="{x}" y="{self.top - 12}" class="mid slab b">{name}</text>')
            out.append(f'<line x1="{x}" y1="{self.top - 4}" x2="{x}" y2="{bottom}" class="line s-muted" stroke-width="2" stroke-dasharray="2 5"/>')
        out.append(f'<text x="14" y="{bottom - 4}" class="xs muted">time ↓</text>')
        return "".join(out + self.items), bottom + 6
