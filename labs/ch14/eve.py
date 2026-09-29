#!/usr/bin/env python3
"""Chapter 14 lab: Eve tries to poison the resolver's memory.

While someone looks up a name that the resolver doesn't have yet, Eve floods the port the
resolver asks its questions from with fake answers, guessing the question number.

    terminal 1:  python3 names.py --naive
    terminal 2:  python3 eve.py harbor.seaside 6.66
    terminal 3:  (within a few seconds) python3 lookup.py harbor.seaside

Then try it again with plain `python3 names.py`.
"""
import socket
import sys
import time

name = sys.argv[1] if len(sys.argv) > 1 else "harbor.seaside"
fake = sys.argv[2] if len(sys.argv) > 2 else "6.66"

# --8<-- [start:eve]
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"Eve is sending fake answers “{name} is {fake}” to port 7051 for 10 seconds...")
end = time.monotonic() + 10
sent = 0
while time.monotonic() < end:
    for guess in range(1, 50):                       # the naive resolver counts 1, 2, 3...
        forged = f"A {guess} {name} {fake} 3600"      # ...and good for a whole hour!
        sock.sendto(forged.encode(), ("127.0.0.1", 7051))
        sent += 1
    time.sleep(0.001)
print(f"Eve sent {sent:,} fake answers.")
# --8<-- [end:eve]
