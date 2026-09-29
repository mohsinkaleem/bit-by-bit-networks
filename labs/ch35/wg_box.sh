#!/bin/bash
# Chapter 35 lab (Linux only, needs sudo and `sudo apt install wireguard-tools`): a real WireGuard server,
# for wg_peer.py to talk to.
#
#   sudo ./wg_box.sh up PEER_PUBLIC_KEY    start wg0 (10.35.0.1) on UDP port 51820; print its public key
#   sudo ./wg_box.sh show                  what the kernel knows about the tunnel
#   sudo ./wg_box.sh down                  remove it again
set -e
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
PATH=$PATH:/usr/sbin
KEY=/run/wg_box.key

case "$1" in
up)
    # --8<-- [start:up]
    ip link add wg0 type wireguard                         # a network interface that encrypts
    (umask 077; wg genkey > $KEY)                           # this server's permanent private key
    wg set wg0 listen-port 51820 private-key $KEY \
        peer "$2" allowed-ips 10.35.0.2/32                  # the one peer we accept, and what it may send
    ip addr add 10.35.0.1/24 dev wg0
    ip link set wg0 up
    # --8<-- [end:up]
    echo "wg0 is up. Its public key: $(wg show wg0 public-key)"
    ;;
show)
    wg show wg0
    ip -br addr show wg0
    ;;
down)
    ip link del wg0 2>/dev/null || true
    rm -f $KEY
    echo "wg0 removed"
    ;;
*)
    echo "usage: sudo $0 up PEER_PUBLIC_KEY | show | down"
    ;;
esac
