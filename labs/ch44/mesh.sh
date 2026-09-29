#!/bin/bash
# Chapter 44 lab (Linux only, needs sudo and batctl): a village mesh network, built in namespaces.
#
#   sudo ./mesh.sh          build it, look at the routes, break a house's radio, watch the mesh heal, tidy up
#   sudo ./mesh.sh keep     …and leave it running (then: sudo ./mesh.sh down)
#   sudo ./mesh.sh down     remove everything
#
# Five houses round the village green, each with one rooftop radio. The "air" is a software switch, and
# a few firewall rules decide who can hear whom: neighbours hear each other, and house 1 can just about
# hear house 3 across the green, losing 30% of what it sends. Each house runs batman-adv, the mesh
# protocol in the Linux kernel. The pub, house 5, has the only way out (its 5G router): a cable to this
# computer, which NATs everyone to the internet.
#
#        house 1 ─────── house 2
#        │   ╲ (weak)        │
#        │     ╲             │
#     house 5    ╲────── house 3
#   (the pub)╲              │
#             ╲──────── house 4
#
# Install batctl with: sudo apt install batctl
set -e
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
PATH=$PATH:/usr/sbin
cd "$(dirname "$0")"
HOUSES="1 2 3 4 5"
DEAF="1-4 2-4 2-5 3-5"          # these pairs are too far apart to hear each other at all
STATE=/run/mesh44.forward
H() { ip netns exec house$1 "${@:2}"; }

down() {
    for h in $HOUSES; do ip netns del house$h 2>/dev/null || true; done
    ip link del air 2>/dev/null || true
    ip link del to-pub 2>/dev/null || true
    ip route del 10.44.0.0/24 2>/dev/null || true
    nft delete table ip mesh44 2>/dev/null || true
    nft delete table bridge air44 2>/dev/null || true
    [ -f $STATE ] && cat $STATE > /proc/sys/net/ipv4/ip_forward && rm -f $STATE
    rm -f bat-hosts ping.log
    true
}
if [ "$1" = down ]; then down; echo "removed"; exit 0; fi
down
trap down EXIT

# --8<-- [start:air]
ip link add air type bridge && ip link set air up         # the air: every radio is plugged into it
nft add table bridge air44
nft add chain bridge air44 hear '{ type filter hook forward priority 0; }'
for pair in $DEAF; do                                      # too far apart: never hear each other
    a=${pair%-*}; b=${pair#*-}
    nft add rule bridge air44 hear iifname air$a oifname air$b drop
    nft add rule bridge air44 hear iifname air$b oifname air$a drop
done
nft add rule bridge air44 hear iifname air1 oifname air3 numgen random mod 100 '<' 30 drop   # across the green:
nft add rule bridge air44 hear iifname air3 oifname air1 numgen random mod 100 '<' 30 drop   # 30% lost
# --8<-- [end:air]

# --8<-- [start:houses]
modprobe batman-adv
for h in $HOUSES; do
    ip netns add house$h
    H $h ip link set lo up
    ip link add wlan0 netns house$h address 02:44:00:00:00:0$h mtu 1560 type veth peer name air$h
    ip link set air$h master air up                        # the radio's antenna, in the air
    H $h ip link add bat0 type batadv                      # the mesh: one virtual Ethernet for the whole village
    H $h ip link set wlan0 master bat0 up                  # batman-adv takes over the radio
    H $h ip addr add 10.44.0.$h/24 dev bat0
    H $h ip link set bat0 up
    [ $h != 5 ] && H $h ip route add default via 10.44.0.5    # everyone reaches the internet through the pub
    echo "02:44:00:00:00:0$h house$h" >> bat-hosts          # names, for batctl's output
done
# --8<-- [end:houses]
ip link add to-pub type veth peer name wan netns house5
ip addr add 10.44.9.1/24 dev to-pub && ip link set to-pub up
H 5 ip addr add 10.44.9.2/24 dev wan && H 5 ip link set wan up
H 5 ip route add default via 10.44.9.1
H 5 sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'
ip route add 10.44.0.0/24 via 10.44.9.2
cat /proc/sys/net/ipv4/ip_forward > $STATE && echo 1 > /proc/sys/net/ipv4/ip_forward
nft add table ip mesh44
nft add chain ip mesh44 post '{ type nat hook postrouting priority srcnat; }'
nft add rule ip mesh44 post ip saddr 10.44.0.0/16 oifname != "to-pub" masquerade
echo "built five houses; batman-adv needs about a minute to learn how good each link is…"
sleep 60

# --8<-- [start:look]
echo "=== house 1's table: every other house, through which neighbour, and how good the path is (out of 255)"
H 1 batctl originators
echo "=== the path from house 1 to house 3"
H 1 batctl traceroute house3
echo "=== and out to the internet, through the pub"
H 1 ping -c 3 -W 2 1.1.1.1 | grep -E "bytes from|packets"
# --8<-- [end:look]

if [ "$1" = keep ]; then echo "left running: try sudo ip netns exec house1 bash"; trap - EXIT; exit 0; fi

# --8<-- [start:break]
echo "=== house 2's radio breaks. House 1 keeps pinging house 3, five times a second, for 30 seconds:"
H 1 ping -i 0.2 -c 150 -W 1 10.44.0.3 > ping.log &
sleep 3
H 2 ip link set wlan0 down
wait
grep -E "packets|rtt" ping.log | sed 's/^/   /'
awk '/icmp_seq/ { split($5, s, "="); seen[s[2]] = 1 } END { for (i = 1; i <= 150; i++) if (!seen[i]) printf "%d ", i; print "" }' ping.log \
    | sed 's/^/   no answer to: /'
echo "=== house 1's path to house 3, now"
H 1 batctl traceroute house3
H 1 batctl originators | grep -E "Originator|\*"
# --8<-- [end:break]
