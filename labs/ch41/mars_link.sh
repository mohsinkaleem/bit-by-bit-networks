#!/bin/bash
# Chapter 41 lab (Linux only, needs sudo): a link as slow as the one to Mars. Takes about 12 minutes.
#
#   sudo ./mars_link.sh          5 min 38 s each way: Mars at its nearest, in February 2027 (mars.py --year)
#   sudo ./mars_link.sh 60       …or any number of seconds
#
# A namespace called "mars" (10.41.0.2), joined to this computer (10.41.0.1) by a virtual cable whose
# both ends hold every packet for that long (tc's netem, "network emulator"). Then it tries TCP, and ping.
set -e
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
PATH=$PATH:/usr/sbin
DELAY=${1:-338}

down() {
    ip netns pids mars 2>/dev/null | xargs -r kill 2>/dev/null || true
    ip netns del mars 2>/dev/null || true
    ip link del to-mars 2>/dev/null || true
}
trap down EXIT
down

# --8<-- [start:link]
ip netns add mars
ip link add to-mars type veth peer name eth0 netns mars
ip addr add 10.41.0.1/24 dev to-mars && ip link set to-mars up
ip netns exec mars ip addr add 10.41.0.2/24 dev eth0
ip netns exec mars ip link set eth0 up
ip neigh add 10.41.0.2 lladdr "$(ip netns exec mars cat /sys/class/net/eth0/address)" dev to-mars   # skip ARP
ip netns exec mars ip neigh add 10.41.0.1 lladdr "$(cat /sys/class/net/to-mars/address)" dev eth0
tc qdisc add dev to-mars root netem delay ${DELAY}s limit 100000                 # Earth → Mars
ip netns exec mars tc qdisc add dev eth0 root netem delay ${DELAY}s limit 100000 # Mars → Earth
ip netns exec mars python3 -m http.server 80 --bind 10.41.0.2 >/dev/null 2>&1 &   # a web server on Mars
# --8<-- [end:link]

echo "one way to Mars: ${DELAY} s"
(
    start=$(date +%s)
    curl -sS -o /dev/null -m $((4 * DELAY)) http://10.41.0.2/ 2>&1 || true
    echo "  …after $(( $(date +%s) - start )) s"
) &
TRY=$!
ping -c 1 -W $((3 * DELAY)) 10.41.0.2 | grep -E "bytes from|transmitted"
wait $TRY
