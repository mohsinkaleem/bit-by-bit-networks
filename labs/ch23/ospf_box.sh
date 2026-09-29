#!/bin/sh
# Chapter 23 lab (Linux only, needs sudo and the BIRD routing daemon: sudo apt install bird2).
# Builds three real OSPF routers inside one computer, wired in a triangle:
#
#                library  10.1.1.0/24
#               /        \
#      10.0.12.0/30    10.0.31.0/30
#             /            \
#          main ---------- lab
#   10.1.3.0/24  10.0.23.0/30  10.1.2.0/24
#
#   sudo sh ospf_box.sh up                 build it and start BIRD in each router
#   sudo sh ospf_box.sh show library       neighbours, the map, and the routing table of one router
#   sudo sh ospf_box.sh cut library main   pull the cable out (both ends go down at once)
#   sudo sh ospf_box.sh quiet library main the cable stays plugged in, but nothing gets through
#   sudo sh ospf_box.sh mend library main  put it back
#   sudo sh ospf_box.sh down               take everything away again
#
# Each router is a Linux network namespace (Chapter 36 explains them); the cables are "veth" pairs.
set -e
DIR=/tmp/ospfbox
ROUTERS="library main lab"
BIRD=$(command -v bird || echo /usr/sbin/bird)
BIRDC=$(command -v birdc || echo /usr/sbin/birdc)

num() { case $1 in library) echo 1;; lab) echo 2;; main) echo 3;; *) echo "unknown router $1" >&2; exit 1;; esac; }

# a cable between routers $1 and $2, on network 10.0.$3.0/30
cable() {
  ip link add "$1-$2" type veth peer name "$2-$1"
  ip link set "$1-$2" netns "$1"; ip -n "$1" link set "$1-$2" name "to-$2"
  ip link set "$2-$1" netns "$2"; ip -n "$2" link set "$2-$1" name "to-$1"
  ip -n "$1" addr add "10.0.$3.1/30" dev "to-$2"; ip -n "$1" link set "to-$2" up
  ip -n "$2" addr add "10.0.$3.2/30" dev "to-$1"; ip -n "$2" link set "to-$1" up
}

config() {  # BIRD's configuration for router $1
  cat <<CONF
router id 10.255.0.$(num "$1");
protocol device { scan time 5; }
protocol kernel { ipv4 { export where source = RTS_OSPF; }; }   # put what OSPF learns into Linux's table
protocol ospf v2 campus {
  ipv4 { import all; };
  area 0 {
    interface "lan" { stub yes; };                               # the building's own network
    interface "to-*" { type ptp; cost 10; hello 10; dead 40; };  # the cables to other routers
  };
}
CONF
}

case "$1" in
up)
  mkdir -p $DIR
  for r in $ROUTERS; do
    ip netns add "$r"
    ip -n "$r" link set lo up
    ip -n "$r" link add lan type dummy
    ip -n "$r" addr add "10.1.$(num "$r").1/24" dev lan
    ip -n "$r" link set lan up
    ip netns exec "$r" sysctl -qw net.ipv4.ip_forward=1
  done
  cable library main 12
  cable main lab 23
  cable lab library 31
  for r in $ROUTERS; do
    config "$r" > "$DIR/$r.conf"
    ip netns exec "$r" "$BIRD" -c "$DIR/$r.conf" -s "$DIR/$r.ctl" -P "$DIR/$r.pid"
  done
  echo "three routers are up; give them a few seconds to meet, then try: sudo sh $0 show library"
  ;;
show)
  r=${2:-library}
  "$BIRDC" -s "$DIR/$r.ctl" show ospf neighbors
  "$BIRDC" -s "$DIR/$r.ctl" show ospf state
  echo "--- $r's routing table (ip route):"
  ip -n "$r" route
  ;;
cut)  ip -n "$2" link set "to-$3" down; ip -n "$3" link set "to-$2" down; echo "cable $2-$3 pulled out";;
quiet) ip netns exec "$2" tc qdisc add dev "to-$3" root netem loss 100%
       ip netns exec "$3" tc qdisc add dev "to-$2" root netem loss 100%; echo "cable $2-$3 is silent (but still plugged in)";;
mend)
  ip -n "$2" link set "to-$3" up; ip -n "$3" link set "to-$2" up
  ip netns exec "$2" tc qdisc del dev "to-$3" root 2>/dev/null || true
  ip netns exec "$3" tc qdisc del dev "to-$2" root 2>/dev/null || true
  echo "cable $2-$3 mended";;
down)
  for r in $ROUTERS; do
    [ -f "$DIR/$r.pid" ] && kill "$(cat "$DIR/$r.pid")" 2>/dev/null || true
    ip netns del "$r" 2>/dev/null || true
  done
  rm -rf $DIR; echo "all gone";;
*) sed -n '2,20p' "$0"; exit 1;;
esac
