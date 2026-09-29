#!/usr/bin/env python3
"""Chapter 3 lab: two Chatterboxes sharing ONE wire (half duplex).

Time moves in ticks, and one symbol crosses the wire per tick. Each Chatterbox follows
the protocol from the chapter:

  1. Listen before you talk: only start once the line has been quiet for a moment.
  2. Keep listening while you talk. If the line doesn't carry what you sent, that's a
     collision: stop, wait a random time, then try again.
  3. When a complete message arrives, answer ~A ("got it").
  4. If no ~A comes back in time, send the message again (up to MAX_TRIES times).

    python3 chatterbox.py                    Alice and Bob both start talking at t=0
    python3 chatterbox.py --noise 0.03       3% of symbols get garbled on the wire
    python3 chatterbox.py --seed 5           make different random choices
    python3 chatterbox.py --no-backoff       everyone waits the same fixed time after a collision
"""
import argparse
import random

from framing import ACK, END, NAK, frame, parse

SYMBOLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ .,?!~"
GAP = 2              # quiet ticks required before starting to talk
ACK_TIMEOUT = 10     # ticks to wait for ~A before trying again
MAX_TRIES = 5
COLLISION = "#"


class Chatterbox:
    def __init__(self, name, outbox, rng, log, backoff=True):
        self.name, self.rng, self.backoff = name, rng, backoff
        self.outbox = list(outbox)            # [(ready_at_tick, text), ...]
        self.state = "idle"                   # idle | sending | waiting | backoff | gave-up
        self.tx, self.tx_pos, self.tx_kind = "", 0, None
        self.return_state = "idle"
        self.tries = 0
        self.wake_at = 0
        self.quiet = GAP
        self.rx = ""
        self.need_ack = False
        self.paper = []                       # what got printed on this Chatterbox's roll
        self.log = log                        # shared by both boxes, in the order things happen
        self.originals = set()                # what was really sent (only the simulation knows this)

    def say(self, t, what):
        self.log.append((t, self.name, what))

    # ------------------------------------------------ deciding what to put on the wire
    def begin(self, t, text, kind):
        if kind == "msg":
            self.tries += 1
            self.say(t, f"starts sending {text!r} (try {self.tries})")
            self.tx = frame(text)
        else:
            self.return_state = self.state
            self.tx = ACK
        self.tx_pos, self.tx_kind, self.state = 0, kind, "sending"

    def drive(self, t):
        """Return the symbol this box puts on the wire this tick, or None."""
        if self.state == "waiting" and t >= self.wake_at:
            if self.tries >= MAX_TRIES:
                self.say(t, f"gives up on {self.outbox[0][1]!r} after {self.tries} tries")
                self.outbox.pop(0)
                self.tries, self.state = 0, "idle"
            else:
                self.say(t, "heard no ~A in time: will send again")
                self.state, self.wake_at = "backoff", t
        can_start = self.quiet >= GAP and self.state in ("idle", "waiting", "backoff")
        if can_start and self.need_ack:
            self.need_ack = False
            self.begin(t, None, "ack")
        elif can_start and self.state == "idle" and self.outbox and self.outbox[0][0] <= t:
            self.begin(t, self.outbox[0][1], "msg")
        elif can_start and self.state == "backoff" and t >= self.wake_at:
            self.begin(t, self.outbox[0][1], "msg")
        return self.tx[self.tx_pos] if self.state == "sending" else None

    # ------------------------------------------------ reacting to what was on the wire
    def observe(self, t, line, sent):
        self.quiet = self.quiet + 1 if line is None else 0
        if sent is not None:
            if line != sent:                          # I didn't hear my own symbol back
                wait = self.pick_backoff()
                self.say(t, f"collision! backs off {wait} ticks")
                if self.tx_kind == "ack":
                    self.need_ack, self.state = True, self.return_state
                elif self.tries >= MAX_TRIES:
                    self.say(t, f"gives up on {self.outbox[0][1]!r} after {self.tries} tries")
                    self.outbox.pop(0)
                    self.tries, self.state = 0, "idle"
                else:
                    self.state = "backoff"
                self.wake_at = t + wait
                self.rx = ""
                return
            self.tx_pos += 1
            if self.tx_pos == len(self.tx):
                if self.tx_kind == "msg":
                    self.state, self.wake_at = "waiting", t + ACK_TIMEOUT
                else:
                    self.state = self.return_state
            return
        if line is None:
            return
        if line == COLLISION:
            self.rx = ""                              # whatever we had is ruined
            return
        self.rx += line
        if self.rx.endswith(END) or self.rx.endswith(ACK):
            messages, errors = parse(self.rx)
            self.rx = ""
            for e in errors:
                self.say(t, f"threw away a garbled message ({e})")
            for m in messages:
                self.receive(t, m)

    def receive(self, t, message):
        if message == NAK:
            if self.state == "waiting":
                self.say(t, "got ~N: will send again")
                self.state, self.wake_at = "backoff", t
            return
        if message == ACK:
            if self.state in ("waiting", "backoff") and self.outbox:
                self.say(t, f"got ~A: {self.outbox[0][1]!r} delivered")
                self.outbox.pop(0)
                self.tries, self.state = 0, "idle"
            return
        note = ""
        if message in self.paper:
            note = "   <- a DUPLICATE!"
        elif message not in self.originals:
            note = "   <- CORRUPTED, and nobody noticed!"
        self.paper.append(message)
        self.say(t, f"prints {message!r}{note}")
        self.need_ack = True

    def pick_backoff(self):
        if not self.backoff:
            return 4
        return self.rng.randint(1, 4 * 2 ** min(self.tries, 5))


def run(alice_msgs, bob_msgs, noise=0.0, seed=1, backoff=True, ticks=400):
    rng = random.Random(seed)
    log = []
    boxes = [Chatterbox("Alice", alice_msgs, rng, log, backoff), Chatterbox("Bob", bob_msgs, rng, log, backoff)]
    for box in boxes:
        box.originals = {text for _, text in alice_msgs + bob_msgs}
    trace = []
    for t in range(ticks):
        sent = [box.drive(t) for box in boxes]
        drivers = [s for s in sent if s is not None]
        if not drivers:
            line = None
        elif len(drivers) > 1:
            line = COLLISION
        else:
            line = drivers[0]
        trace.append(line)
        for box, s in zip(boxes, sent):
            heard = line
            if s is None and line not in (None, COLLISION) and rng.random() < noise:
                heard = rng.choice(SYMBOLS.replace(line, ""))   # noise near the listener's end
            box.observe(t, heard, s)
        if all(not b.outbox and b.state == "idle" and not b.need_ack for b in boxes):
            break
    return boxes, trace, log


def show(boxes, trace, log, width=64):
    for t, who, what in log:
        print(f"t={t:4}  {who:5}  {what}")
    print("\nThe wire, one symbol per tick  ( . = quiet,  # = collision ):")
    line = "".join("." if s is None else s for s in trace)
    for i in range(0, len(line), width):
        print(f"  {i:4} │{line[i:i + width]}")
    for b in boxes:
        print(f"\n{b.name}'s paper roll: {b.paper}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--noise", type=float, default=0.0, help="chance each symbol arrives garbled (0 to 1)")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--no-backoff", action="store_true", help="always wait exactly 4 ticks after a collision")
    args = p.parse_args()
    alice = [(0, "HI BOB"), (40, "WANT TO PLAY CHESS?")]
    bob = [(0, "HEY ALICE"), (70, "SURE! ~ BOB")]
    show(*run(alice, bob, args.noise, args.seed, not args.no_backoff))


if __name__ == "__main__":
    main()
