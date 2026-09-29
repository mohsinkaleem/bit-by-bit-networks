#!/usr/bin/env python3
"""Chapter 3 lab: framing messages with control codes and escaping.

The Chatterbox Protocol marks messages with two-symbol control codes that start with "~":

    ~S   start of a message
    ~E   end of a message
    ~A   "got it" (acknowledgement)
    ~N   "that was garbled, send it again"
    ~~   a real "~" that is part of the message text

    python3 framing.py demo      frame a few tricky messages and parse them back
    python3 framing.py test      run the self-checks
    python3 framing.py naive     see what goes wrong WITHOUT escaping
"""
import sys

ESC = "~"
START, END, ACK, NAK = "~S", "~E", "~A", "~N"


# --8<-- [start:frame]
def frame(text):
    """Wrap text in start/end codes, escaping any "~" inside it."""
    escaped = text.replace(ESC, ESC + ESC)        # every real ~ becomes ~~
    return START + escaped + END


def parse(stream):
    """Pull complete messages out of a stream of symbols.

    Returns (messages, errors). Anything outside ~S ... ~E is ignored,
    which lets the receiver skip over line noise between messages.
    """
    messages, errors = [], []
    inside, current, i = False, "", 0
    while i < len(stream):
        ch = stream[i]
        if ch != ESC:
            if inside:
                current += ch
            i += 1
            continue
        code = stream[i:i + 2]                    # an escape: look at the next symbol
        if code == START:
            if inside:
                errors.append(f"new start before end; dropped {current!r}")
            inside, current = True, ""
        elif code == END and inside:
            messages.append(current)
            inside = False
        elif code == ESC + ESC and inside:
            current += ESC                        # ~~ is a real ~
        elif code in (ACK, NAK):
            if inside:
                errors.append(f"message cut off by {code}; dropped {current!r}")
                inside = False
            messages.append(code)                 # tiny control-only messages
        else:
            errors.append(f"unexpected {code!r} at position {i}")
            inside = False                        # give up on this message
        i += 2
    return messages, errors
# --8<-- [end:frame]


def naive_frame(text):
    """The first attempt: end every message with the word OVER."""
    return "START " + text + " OVER"


def naive_parse(stream):
    messages = []
    for chunk in stream.split(" OVER"):
        chunk = chunk.strip()
        if chunk.startswith("START "):
            messages.append(chunk[len("START "):])
        elif chunk:
            messages.append("(garbage: " + chunk + ")")
    return messages


TRICKY = ["HI BOB", "GAME OVER", "SEE YOU ~ SOON", "~~~", "~E IS THE END CODE", ""]


def demo():
    for text in TRICKY:
        framed = frame(text)
        got, errs = parse(framed)
        print(f"{text!r:24} -> {framed!r:32} -> {got}")
    print("\nTwo messages, an ACK and some line noise in one stream:")
    stream = "##" + frame("HI BOB") + "#x#" + ACK + frame("GAME OVER") + "##"
    print(" ", repr(stream))
    print(" ", parse(stream))


def naive():
    for text in ["HI BOB", "GAME OVER LOL", "HANDS OVER THE COOKIES"]:
        sent = naive_frame(text)
        print(f"Alice sends {sent!r}")
        print(f"   Bob gets {naive_parse(sent)}\n")


def test():
    for text in TRICKY:
        assert parse(frame(text)) == ([text], []), text
    assert parse(frame("A") + frame("B")) == (["A", "B"], [])
    assert parse("noise" + frame("A")) == (["A"], [])
    msgs, errs = parse("~SHI~XBOB~E")
    assert msgs == [] and errs, "a bad escape must be reported"
    msgs, errs = parse("~SHALF~SFULL~E")
    assert msgs == ["FULL"] and errs, "a restart drops the half message"
    print("all framing tests passed")


if __name__ == "__main__":
    {"demo": demo, "test": test, "naive": naive}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
