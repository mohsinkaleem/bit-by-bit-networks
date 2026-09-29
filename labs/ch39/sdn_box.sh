#!/bin/bash
# Chapter 39 lab (Linux only, needs sudo and Open vSwitch): two software switches with no brains of their own.
#
#   sudo ./sdn_box.sh up       build them, and point them at a controller on 127.0.0.1:6653
#   sudo ./sdn_box.sh test     ping between the hosts, and show both switches' flow tables
#   sudo ./sdn_box.sh down     remove everything
#
# Start the controller first, in another terminal: python3 controller.py
# Three hosts, h1 and h2 on switch s1 and h3 on switch s2, with a cable between the switches:
#
#     h1 (10.39.0.1) ──┐                 ┌── h3 (10.39.0.3)
#                      s1 ───────────── s2
#     h2 (10.39.0.2) ──┘
#
# Install Open vSwitch with: sudo apt install openvswitch-switch
set -e
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
PATH=$PATH:/usr/sbin

down() {
    for h in h1 h2 h3; do ip netns del $h 2>/dev/null || true; done
    ovs-vsctl --if-exists del-br s1 -- --if-exists del-br s2
    ip link del s1-s2 2>/dev/null || true
}

case "$1" in
up)
    down
    # --8<-- [start:up]
    for n in 1 2; do                                    # two switches, each told: no controller, no forwarding
        ovs-vsctl add-br s$n -- set bridge s$n protocols=OpenFlow13 fail-mode=secure \
            other-config:datapath-id=000000000000000$n
        ovs-vsctl set-controller s$n tcp:127.0.0.1:6653
    done
    for h in 1 2 3; do                                  # three hosts, each in its own namespace (Chapter 36)
        sw=s1; [ $h = 3 ] && sw=s2
        ip netns add h$h
        ip link add eth0 netns h$h address 0a:39:00:00:00:0$h type veth peer name h$h
        ip netns exec h$h sysctl -qw net.ipv6.conf.eth0.disable_ipv6=1   # IPv4 only, to keep things quiet
        ip netns exec h$h ip addr add 10.39.0.$h/24 dev eth0
        ip netns exec h$h ip link set eth0 up
        ip link set h$h up
        ovs-vsctl add-port $sw h$h -- set interface h$h ofport_request=$h
    done
    ip link add s1-s2 type veth peer name s2-s1         # the cable between the switches
    ip link set s1-s2 up && ip link set s2-s1 up
    ovs-vsctl add-port s1 s1-s2 -- set interface s1-s2 ofport_request=9
    ovs-vsctl add-port s2 s2-s1 -- set interface s2-s1 ofport_request=9
    # --8<-- [end:up]
    echo "built s1 and s2; they're looking for a controller on 127.0.0.1:6653" ;;
test)
    for pair in "h1 10.39.0.2" "h1 10.39.0.3" "h2 10.39.0.3" "h3 10.39.0.1"; do
        set -- $pair
        printf "%s → %-10s " $1 $2
        ip netns exec $1 ping -c 3 -i 0.2 -W 1 $2 | grep -E "packets" || true
    done
    for s in s1 s2; do
        echo "--- the flow table in $s"
        ovs-ofctl -O OpenFlow13 dump-flows $s | sed -E 's/^ *//; s/(cookie|duration|table|n_bytes)=[^ ]* //g' | grep -v OFPST
    done ;;
down)
    down; echo "removed" ;;
*)
    echo "usage: sudo $0 up|test|down"; exit 1 ;;
esac
