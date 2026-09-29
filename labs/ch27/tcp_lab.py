#!/usr/bin/env python3
"""Chapter 27 lab: a TCP connection's life, watched from the outside with netstat.

    python3 tcp_lab.py states             connect, talk, close, and see each state the kernel reports
    python3 tcp_lab.py refused            connect to a port nobody's listening on: meet RST
    python3 tcp_lab.py handshake          how long does connect() take? (one round trip)
    python3 tcp_lab.py stream             three writes, one read: TCP carries bytes, not messages

Everything except "handshake" stays on 127.0.0.1, port 7127.
"""
import os
import socket
import subprocess
import sys
import time

PORT = 7127


def states_now(label):
    """Ask the operating system which state each end of our connection is in."""
    if sys.platform == "darwin":
        out = subprocess.run(["netstat", "-an", "-p", "tcp"], capture_output=True, text=True).stdout
        lines = [l for l in out.splitlines() if f".{PORT} " in l]
        lines = [" ".join(l.split()[3:6]) for l in lines]
    else:
        out = subprocess.run(["ss", "-tan", f"( sport = :{PORT} or dport = :{PORT} )"], capture_output=True, text=True).stdout
        lines = [" ".join(l.split()[3:5] + l.split()[:1]) for l in out.splitlines()[1:]]
    print(f"\n{label}")
    for l in sorted(lines):
        print("   ", l)


# --8<-- [start:states]
def states():
    server = socket.create_server(("127.0.0.1", PORT))            # socket, bind, listen
    states_now("1. the server is listening:")
    client = socket.create_connection(("127.0.0.1", PORT))        # SYN, SYN-ACK, ACK
    conn, _ = server.accept()
    states_now("2. after the handshake, both ends are ESTABLISHED:")
    client.sendall(b"GET / please\n")
    conn.recv(100)
    client.close()                                                # the client sends FIN
    time.sleep(0.2)
    states_now("3. the client closed first (sent FIN); the server hasn't yet:")
    conn.close()                                                  # the server sends its own FIN
    time.sleep(0.2)
    states_now("4. both closed. The side that closed first waits in TIME_WAIT:")
    server.close()
# --8<-- [end:states]


def refused():
    s = socket.socket()
    t = time.perf_counter()
    try:
        s.connect(("127.0.0.1", PORT + 1))
    except ConnectionRefusedError as e:
        ms = (time.perf_counter() - t) * 1000
        print(f"{e!r} after {ms:.2f} ms")
        print("The other end's kernel answered our SYN with RST (“reset”): nobody is listening on that port.")


def handshake(hosts=(("example.org", 443), ("info.cern.ch", 80), ("1.1.1.1", 443))):
    for host, port in hosts:
        addr = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)[0][4]
        times = []
        for _ in range(3):
            t = time.perf_counter()
            with socket.create_connection(addr, timeout=5):       # returns when the SYN-ACK arrives
                times.append((time.perf_counter() - t) * 1000)
        print(f"{host:<14} {addr[0]:<16} connect() took " + ", ".join(f"{x:.1f}" for x in times) + " ms")
    print("Each connect() waits for exactly one round trip: our SYN there, their SYN-ACK back.")


# --8<-- [start:stream]
def stream():
    server = socket.create_server(("127.0.0.1", PORT))
    client = socket.create_connection(("127.0.0.1", PORT))
    conn, _ = server.accept()
    for word in (b"one ", b"two ", b"three"):
        client.send(word)                    # three separate sends…
    time.sleep(0.1)
    print("three sends of 4, 4 and 5 bytes; the other end's first recv() got:", conn.recv(100))
    client.close(), conn.close(), server.close()
# --8<-- [end:stream]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"states": states, "refused": refused, "handshake": handshake, "stream": stream}.get(cmd, lambda: print(__doc__))()


if __name__ == "__main__":
    main()
