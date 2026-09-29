#!/usr/bin/env python3
"""Chapter 1 lab: Alice and Bob's 5-bit codebook.

    python3 codebook.py encode "HI BOB"        text  -> bits
    python3 codebook.py decode 00111 01000     bits  -> text
    python3 codebook.py flash "HI BOB"         watch the flashlight blink in your terminal
    python3 codebook.py table                  print the whole codebook
"""
import sys
import time

# The 32 symbols, in order. A symbol's position IS its code: A is 0, B is 1, ... "~" is 31.
SYMBOLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ .,?!~"

GREEN = "\033[42m  \033[0m"   # a green square (bit 1)
RED = "\033[41m  \033[0m"     # a red square   (bit 0)
DARK = "  "                   # the gap between flashes


# --8<-- [start:encode]
def encode_symbol(symbol):
    """Turn one symbol into its 5-bit code, e.g. 'K' -> '01010'."""
    number = SYMBOLS.index(symbol)       # 'K' is the 10th symbol (counting from 0)
    return format(number, "05b")         # 10 written in binary, padded to 5 digits


def decode_bits(bits):
    """Turn a 5-bit code back into its symbol, e.g. '01010' -> 'K'."""
    number = int(bits, 2)                # read the string as a base-2 number
    return SYMBOLS[number]


def encode(text):
    return [encode_symbol(ch) for ch in text.upper()]


def decode(codes):
    return "".join(decode_bits(code) for code in codes)
# --8<-- [end:encode]


def lights(code):
    return " ".join(GREEN if bit == "1" else RED for bit in code)


def cmd_encode(text):
    bad = [ch for ch in text.upper() if ch not in SYMBOLS]
    if bad:
        sys.exit(f"Sorry, the codebook has no symbol for: {' '.join(sorted(set(bad)))}")
    for ch, code in zip(text.upper(), encode(text)):
        shown = "␣" if ch == " " else ch
        print(f"  {shown}   {code}   {lights(code)}")
    print("\nAll together:", " ".join(encode(text)))


def cmd_decode(codes):
    for code in codes:
        if len(code) != 5 or set(code) - {"0", "1"}:
            sys.exit(f"'{code}' is not a 5-bit code (it needs exactly five 0s and 1s)")
    print(decode(codes))


def cmd_flash(text, speed=0.35):
    """Blink each bit like Grandpa Otto would: flash, dark gap, flash, dark gap..."""
    print("Watch the square. Green = 1, red = 0.  (Ctrl+C to stop)\n")
    received = ""
    for ch, code in zip(text.upper(), encode(text)):
        for bit in code:
            sys.stdout.write("\r   " + (GREEN if bit == "1" else RED) + "  ")
            sys.stdout.flush()
            time.sleep(speed)
            sys.stdout.write("\r   " + DARK + "  ")
            sys.stdout.flush()
            time.sleep(speed / 2)
        received += ch
        sys.stdout.write(f"\r   {DARK}   {code} -> {'␣' if ch == ' ' else ch}    so far: {received}\n")
    print()


def cmd_table():
    for row in range(8):
        cells = []
        for col in range(4):
            n = row + col * 8
            ch = SYMBOLS[n]
            cells.append(f"{'␣' if ch == ' ' else ch} {n:2} {n:05b}")
        print("    ".join(cells))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return
    command, args = argv[1], argv[2:]
    if command == "encode":
        cmd_encode(" ".join(args))
    elif command == "decode":
        cmd_decode(args)
    elif command == "flash":
        cmd_encode(" ".join(args))
        print()
        cmd_flash(" ".join(args))
    elif command == "table":
        cmd_table()
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
