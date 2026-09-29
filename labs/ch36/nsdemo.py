#!/usr/bin/env python3
"""Chapter 36 lab: network namespaces from Python (Linux only, run with sudo; Python 3.12 or newer).

    sudo python3 nsdemo.py         a process in a new network namespace: what can it see?
    sudo python3 nsdemo.py web     step into the namespace called "web" (made by box.sh keep) and look around

A container is an ordinary process that the kernel shows a different view of the computer:
its own network devices, addresses, routes, firewall and ports (a network namespace), and usually
its own process list, files and hostname too. os.unshare() asks for a new one; os.setns() joins one.
"""
import os
import socket
import sys


def look(label):
    names = [name for _, name in socket.if_nameindex()]           # the network devices this process can see
    s = socket.socket()
    try:
        s.bind(("0.0.0.0", 8080))
        port = "port 8080 is free"
    except OSError as e:
        port = f"port 8080: {e.strerror}"
    finally:
        s.close()
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=2).close()
        out = "can reach 1.1.1.1"
    except OSError as e:
        out = f"can't reach 1.1.1.1 ({e.strerror or e})"
    print(f"{label:<34} devices: {', '.join(names):<24} {port};  {out}", flush=True)


# --8<-- [start:unshare]
def new_namespace():
    hold = socket.socket()
    hold.bind(("0.0.0.0", 8080))                                  # the host's port 8080 is now taken
    look("this process, on the host:")
    child = os.fork()
    if child == 0:
        os.unshare(os.CLONE_NEWNET)                               # from here on, a brand-new network stack
        look("a child, after unshare(NEWNET):")
        os.system("ip link set lo up")
        look("…after switching on its loopback:")
        os._exit(0)
    os.waitpid(child, 0)
    look("the host again (unchanged):")
# --8<-- [end:unshare]


# --8<-- [start:setns]
def enter(name):
    """`ip netns add web` makes /run/netns/web; opening it and calling setns() moves this process inside."""
    look("this process, on the host:")
    with open(f"/run/netns/{name}") as f:
        os.setns(f.fileno(), os.CLONE_NEWNET)
    look(f"after setns() into “{name}”:")
    print("\nand its addresses and routes, from inside:", flush=True)
    os.system("ip -br addr; ip route")
# --8<-- [end:setns]


if __name__ == "__main__":
    if sys.platform != "linux" or os.geteuid() != 0 or not hasattr(os, "unshare"):
        sys.exit("needs Linux, sudo, and Python 3.12 or newer")
    enter(sys.argv[1]) if len(sys.argv) > 1 else new_namespace()
