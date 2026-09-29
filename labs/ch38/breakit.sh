#!/bin/bash
# Chapter 38 lab (Linux only, needs sudo): break a network on purpose, then play detective.
#
#   sudo ./breakit.sh healthy      a working network, to compare with
#   sudo ./breakit.sh nodns        the DNS server it was given doesn't exist
#   sudo ./breakit.sh noroute      no default route
#   sudo ./breakit.sh blackhole    a narrow link in the middle, and the ICMP "too big" messages dropped
#   sudo ./breakit.sh noping       a server that drops ping, but serves web pages fine
#   sudo ./breakit.sh icmpv6       IPv6 with all ICMPv6 blocked
#   add "shell" at the end to get a shell inside the patient instead (exit to tidy up)
#
# The patient (10.38.0.2) sits behind two routers, r1 and r2, joined by a link that only carries
# 1,400-byte packets; r2 hands everything to this computer, which NATs it to the internet. Each
# scenario runs netdoctor.py inside the patient, then a few extra tests. Everything is removed afterwards.
set -e
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
PATH=$PATH:/usr/sbin
MODE=${1:-healthy}
HERE=$(cd "$(dirname "$0")" && pwd)
P="ip netns exec patient"
STATE=/run/breakit.forward

down() {
    for n in patient r1 r2; do
        ip netns pids $n 2>/dev/null | xargs -r kill 2>/dev/null || true
        ip netns del $n 2>/dev/null || true
    done
    ip link del to-r2 2>/dev/null || true
    ip route del 10.38.0.0/16 2>/dev/null || true
    nft delete table ip breakit 2>/dev/null || true
    rm -rf /etc/netns/patient /run/breakit
    [ -n "$SERVER" ] && kill "$SERVER" 2>/dev/null || true
    [ -f $STATE ] && cat $STATE > /proc/sys/net/ipv4/ip_forward && rm -f $STATE
    true
}
trap down EXIT
down

# --8<-- [start:build]
for n in patient r1 r2; do ip netns add $n; ip netns exec $n ip link set lo up; done
ip link add eth0 netns patient type veth peer name to-patient netns r1        # patient ↔ r1
ip link add to-r2 netns r1 mtu 1400 type veth peer name to-r1 netns r2 mtu 1400   # r1 ↔ r2: the narrow link
ip link add to-host netns r2 type veth peer name to-r2                        # r2 ↔ this computer
$P ip addr add 10.38.0.2/24 dev eth0 && $P ip link set eth0 up
ip netns exec r1 ip addr add 10.38.0.1/24 dev to-patient && ip netns exec r1 ip link set to-patient up
ip netns exec r1 ip addr add 10.38.1.1/24 dev to-r2 && ip netns exec r1 ip link set to-r2 up
ip netns exec r2 ip addr add 10.38.1.2/24 dev to-r1 && ip netns exec r2 ip link set to-r1 up
ip netns exec r2 ip addr add 10.38.2.1/24 dev to-host && ip netns exec r2 ip link set to-host up
ip addr add 10.38.2.2/24 dev to-r2 && ip link set to-r2 up
$P ip route add default via 10.38.0.1
ip netns exec r1 ip route add default via 10.38.1.2
ip netns exec r2 ip route add default via 10.38.2.2
ip netns exec r2 ip route add 10.38.0.0/24 via 10.38.1.1
ip route add 10.38.0.0/16 via 10.38.2.1
for n in r1 r2; do ip netns exec $n sh -c 'echo 1 > /proc/sys/net/ipv4/ip_forward'; done
cat /proc/sys/net/ipv4/ip_forward > $STATE && echo 1 > /proc/sys/net/ipv4/ip_forward
nft add table ip breakit
nft add chain ip breakit post '{ type nat hook postrouting priority srcnat; }'
nft add rule ip breakit post ip saddr 10.38.0.0/16 oifname != "to-r2" masquerade
mkdir -p /etc/netns/patient && echo "nameserver 1.1.1.1" > /etc/netns/patient/resolv.conf   # the patient's own DNS setting
mkdir -p /run/breakit && head -c 2000000 /dev/urandom > /run/breakit/big.bin                  # a server on this computer,
python3 -m http.server 8038 --bind 10.38.2.2 --directory /run/breakit >/dev/null 2>&1 &     # on the far side of the narrow link
SERVER=$!
# --8<-- [end:build]

# --8<-- [start:break]
case "$MODE" in
nodns)     echo "nameserver 10.38.0.53" > /etc/netns/patient/resolv.conf ;;          # nobody lives there
noroute)   $P ip route del default ;;
blackhole) for r in r1 r2; do                                                          # drop "fragmentation needed"
               ip netns exec $r nft add table ip t
               ip netns exec $r nft add chain ip t out '{ type filter hook output priority 0; }'
               ip netns exec $r nft add rule ip t out icmp type destination-unreachable icmp code frag-needed drop
           done ;;
noping)    $P nft add table ip t
           $P nft add chain ip t in '{ type filter hook input priority 0; }'
           $P nft add rule ip t in icmp type echo-request drop
           $P python3 -m http.server 80 --bind 10.38.0.2 --directory /etc/netns/patient >/dev/null 2>&1 & ;;
icmpv6)    $P ip addr add fd38::2/64 dev eth0 nodad; ip netns exec r1 ip addr add fd38::1/64 dev to-patient nodad
           $P nft add table ip6 t
           $P nft add chain ip6 t in '{ type filter hook input priority 0; }'
           $P nft add rule ip6 t in meta l4proto ipv6-icmp drop ;;
esac
# --8<-- [end:break]
sleep 1

if [ "$2" = shell ]; then
    echo "you're in the patient ($MODE). Try: python3 $HERE/netdoctor.py --big, ping, curl, tracepath… exit to tidy up."
    $P bash || true
    exit 0
fi
echo "=== the patient ($MODE): netdoctor.py --big"
$P python3 "$HERE/netdoctor.py" --big http://10.38.2.2:8038/big.bin || true
case "$MODE" in
blackhole|healthy)
    echo "=== a small file and a big one, from the server beyond the narrow link"
    echo "hello" > /run/breakit/small.txt
    $P curl -s -m 8 -o /dev/null -w "   small.txt: HTTP %{http_code}, %{size_download} bytes in %{time_total} s\n" http://10.38.2.2:8038/small.txt || true
    $P curl -s -m 8 -o /dev/null -w "   big.bin:   HTTP %{http_code}, %{size_download} bytes in %{time_total} s\n" http://10.38.2.2:8038/big.bin || echo "   big.bin: curl gave up after 8 s"
    echo "=== one big packet, with Don't Fragment set"
    $P ping -c 1 -W 2 -M do -s 1472 10.38.2.2 2>&1 | grep -E "bytes from|Frag|packets" | sed 's/^/   /' || true ;;
noping)
    echo "=== from this computer: ping the patient, and ask it for a web page"
    ping -c 2 -W 1 10.38.0.2 | grep -E "packets" | sed 's/^/   /'
    curl -s -m 3 -o /dev/null -w "   http://10.38.0.2/: HTTP %{http_code}\n" http://10.38.0.2/ ;;
icmpv6)
    echo "=== IPv6 to the router, on the same cable"
    $P ping -6 -c 2 -W 1 fd38::1 2>&1 | grep -E "Unreachable|packets" | sed 's/^/   /' | head -3
    $P ip -6 neigh show dev eth0 | sed 's/^/   neighbour table: /' ;;
esac
