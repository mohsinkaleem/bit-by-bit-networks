#!/bin/sh
# Chapter 24 lab (Linux only, needs sudo and BIRD: sudo apt install bird2).
# Five real BGP routers inside one computer, each its own autonomous system (AS):
#
#                  northnet (AS 65010)
#                 /                   \
#   uni (AS 65001)                     world (AS 65030) --- eve (AS 65066)
#   10.1.0.0/16   \                   /  198.51.100.0/24
#                  research (AS 65020)
#
#   sudo sh bgp_box.sh up            build it, start BIRD everywhere, uni announces 10.1.0.0/16
#   sudo sh bgp_box.sh show world    world's BGP sessions and every path it knows to 10.1.0.0/16
#   sudo sh bgp_box.sh prepend       uni makes its path through northnet look longer (and "unprepend")
#   sudo sh bgp_box.sh hijack        eve announces 10.1.1.0/24, a piece of uni's addresses
#   sudo sh bgp_box.sh rov           world checks origins against a ROA list, as RPKI does (and "norov")
#   sudo sh bgp_box.sh down          take it all away
#
# Each router is a Linux network namespace (Chapter 36); the cables are veth pairs.
set -e
DIR=/tmp/bgpbox
ROUTERS="uni northnet research world eve"
BIRD=$(command -v bird || echo /usr/sbin/bird)
BIRDC=$(command -v birdc || echo /usr/sbin/birdc)

asn() { case $1 in uni) echo 65001;; northnet) echo 65010;; research) echo 65020;; world) echo 65030;; eve) echo 65066;; esac; }

cable() {  # cable A B N: A is 10.0.N.1, B is 10.0.N.2
  ip link add "$1-$2" type veth peer name "$2-$1"
  ip link set "$1-$2" netns "$1"; ip -n "$1" link set "$1-$2" name "to-$2"
  ip link set "$2-$1" netns "$2"; ip -n "$2" link set "$2-$1" name "to-$1"
  ip -n "$1" addr add "10.0.$3.1/30" dev "to-$2"; ip -n "$1" link set "to-$2" up
  ip -n "$2" addr add "10.0.$3.2/30" dev "to-$1"; ip -n "$2" link set "to-$1" up
}

peer() {  # peer NAME MY-ADDRESS THEIR-ADDRESS THEIR-AS [export filter]
  cat <<CONF
protocol bgp $1 {
  local $2 as $ME; neighbor $3 as $4;
  ipv4 { import ${IMPORT:-all}; export ${5:-all}; };
}
CONF
}

# --8<-- [start:config]
config() {
  r=$1; ME=$(asn "$r")
  echo "router id 10.255.255.$(echo "$ROUTERS" | tr ' ' '\n' | grep -n "^$r$" | cut -d: -f1);"
  echo 'protocol device { scan time 5; }'
  echo 'protocol direct { ipv4; interface "lan"; }'
  echo 'protocol kernel { ipv4 { export where source = RTS_BGP; }; }'
  IMPORT=all
  if [ "$r" = world ] && [ -f $DIR/rov ]; then
    cat <<CONF
roa4 table roas;
protocol static { roa4 { table roas; };            # who may announce what (a ROA list, as in RPKI)
  route 10.1.0.0/16 max 16 as 65001;
  route 198.51.100.0/24 max 24 as 65030;
}
filter rov {
  if roa_check(roas, net, bgp_path.last) = ROA_INVALID then {
    print "ROV: rejecting ", net, " from AS", bgp_path.last;
    reject;
  }
  accept;
}
CONF
    IMPORT="filter rov"
  fi
  case $r in
  uni)
    if [ -f $DIR/prepend ]; then
      echo 'filter to_northnet { if source = RTS_DEVICE then { bgp_path.prepend(65001); bgp_path.prepend(65001); accept; } reject; }'
      peer northnet 10.0.1.1 10.0.1.2 65010 "filter to_northnet"
    else
      peer northnet 10.0.1.1 10.0.1.2 65010 "where source = RTS_DEVICE"
    fi
    peer research 10.0.2.1 10.0.2.2 65020 "where source = RTS_DEVICE";;
  northnet) peer uni 10.0.1.2 10.0.1.1 65001; peer world 10.0.3.1 10.0.3.2 65030;;
  research) peer uni 10.0.2.2 10.0.2.1 65001; peer world 10.0.4.1 10.0.4.2 65030;;
  world)    peer northnet 10.0.3.2 10.0.3.1 65010; peer research 10.0.4.2 10.0.4.1 65020; peer eve 10.0.5.2 10.0.5.1 65066;;
  eve)      if [ -f $DIR/hijack ]; then peer world 10.0.5.1 10.0.5.2 65030 "where source = RTS_DEVICE"
            else peer world 10.0.5.1 10.0.5.2 65030 none; fi;;
  esac
}
# --8<-- [end:config]

reload() { for r in $ROUTERS; do config "$r" > "$DIR/$r.conf"; "$BIRDC" -s "$DIR/$r.ctl" configure >/dev/null; done; }

case "$1" in
up)
  mkdir -p $DIR
  for r in $ROUTERS; do
    ip netns add "$r"; ip -n "$r" link set lo up
    ip -n "$r" link add lan type dummy; ip -n "$r" link set lan up
    ip netns exec "$r" sysctl -qw net.ipv4.ip_forward=1
  done
  ip -n uni addr add 10.1.1.1/16 dev lan              # the university's block; 10.1.1.1 is the library's server
  ip -n world addr add 198.51.100.1/24 dev lan        # somewhere out on the internet
  ip -n eve addr add 10.1.1.1/24 dev lan              # eve pretends to be the library's server
  cable uni northnet 1; cable uni research 2; cable northnet world 3; cable research world 4; cable eve world 5
  for r in $ROUTERS; do
    config "$r" > "$DIR/$r.conf"
    ip netns exec "$r" env TZ=UTC "$BIRD" -c "$DIR/$r.conf" -s "$DIR/$r.ctl" -P "$DIR/$r.pid"   # times in UTC
  done
  echo "five autonomous systems are up; in a few seconds try: sudo sh $0 show world";;
show)
  r=${2:-world}
  "$BIRDC" -s "$DIR/$r.ctl" show protocols
  "$BIRDC" -s "$DIR/$r.ctl" show route for 10.1.1.1 all;;
prepend) touch $DIR/prepend; reload; echo "uni now prepends 65001 65001 towards northnet";;
unprepend) rm -f $DIR/prepend; reload; echo "uni stopped prepending";;
hijack) touch $DIR/hijack; reload; echo "eve is announcing 10.1.1.0/24";;
unhijack) rm -f $DIR/hijack; reload; echo "eve stopped";;
rov) touch $DIR/rov; reload; echo "world now checks route origins";;
norov) rm -f $DIR/rov; reload; echo "world believes everything again";;
down)
  for r in $ROUTERS; do
    [ -f "$DIR/$r.pid" ] && kill "$(cat "$DIR/$r.pid")" 2>/dev/null || true
    ip netns del "$r" 2>/dev/null || true
  done
  rm -rf $DIR; echo "all gone";;
*) sed -n '2,20p' "$0"; exit 1;;
esac
