#!/bin/bash
# Chapter 35 lab (Linux only, needs sudo, and tshark for the capture): two tunnels you can watch.
#
#   sudo ./tunnel_box.sh gre      an IP packet inside another IP packet (GRE)
#   sudo ./tunnel_box.sh vxlan    a whole Ethernet frame inside UDP (VXLAN), as data centres do
#
# Two network namespaces, "alice" and "grandpa", stand in for two houses. They're joined by a veth
# cable (Chapter 36) playing the internet: 192.0.2.1 and 192.0.2.2. The tunnel gives them a private
# network of their own on top, 10.99.0.0/24, and we capture on the "internet" to see the wrapping.
set -e
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
PATH=$PATH:/usr/sbin
MODE=${1:-vxlan}
A="ip netns exec alice"
G="ip netns exec grandpa"

cleanup() {
    ip netns del alice 2>/dev/null || true
    ip netns del grandpa 2>/dev/null || true
    sleep 0.5
}
trap cleanup EXIT
cleanup

# the "internet" between the two houses
ip netns add alice
ip netns add grandpa
ip link add net-a type veth peer name net-g
ip link set net-a netns alice
ip link set net-g netns grandpa
$A ip addr add 192.0.2.1/24 dev net-a && $A ip link set net-a up && $A ip link set lo up
$G ip addr add 192.0.2.2/24 dev net-g && $G ip link set net-g up && $G ip link set lo up

if [ "$MODE" = gre ]; then
    # --8<-- [start:gre]
    $A ip tunnel add tun0 mode gre local 192.0.2.1 remote 192.0.2.2
    $G ip tunnel add tun0 mode gre local 192.0.2.2 remote 192.0.2.1
    # --8<-- [end:gre]
else
    # --8<-- [start:vxlan]
    $A ip link add tun0 type vxlan id 42 local 192.0.2.1 remote 192.0.2.2 dstport 4789 dev net-a
    $G ip link add tun0 type vxlan id 42 local 192.0.2.2 remote 192.0.2.1 dstport 4789 dev net-g
    # --8<-- [end:vxlan]
fi
$A ip addr add 10.99.0.1/24 dev tun0 && $A ip link set tun0 up
$G ip addr add 10.99.0.2/24 dev tun0 && $G ip link set tun0 up
sleep 1

echo "== the tunnel interface in Alice's house"
$A ip -d link show tun0 | sed 's/^/   /'
echo "== ping Grandpa's private address, through the tunnel, while capturing on the \"internet\""
$A tshark -q -i net-a -f "ip" -w /tmp/tunnel_box.pcap -a duration:4 >/dev/null 2>&1 &
sleep 1.5
$A ping -c 2 10.99.0.2 | grep -E "bytes from|packets" | sed 's/^/   /'
wait
echo "== what crossed the internet"
tshark -r /tmp/tunnel_box.pcap -Y "not icmpv6" 2>/dev/null | sed 's/^/   /'
echo "== one of those packets, layer by layer"
tshark -r /tmp/tunnel_box.pcap -Y "icmp.type == 8" -O ip,gre,udp,vxlan,eth,icmp 2>/dev/null | awk 'NR==1,/^$/' \
    | grep -E "^[A-Z]|Source Address|Destination Address|Source Port|Destination Port|VXLAN Network Identifier|Protocol Type|Protocol:|Type:" \
    | grep -v "\[" | sed 's/^/   /'
if [ "$MODE" = vxlan ]; then
    echo "== Grandpa's end has learned where Alice's MAC address lives, like a switch (Chapter 9)"
    $G bridge fdb show dev tun0 | sed 's/^/   /'
fi
rm -f /tmp/tunnel_box.pcap
