#!/bin/bash
# Chapter 36 lab (Linux only, needs sudo): container networking by hand, the way Docker and Podman do it.
#
#   sudo ./box.sh           build three "containers", test them, show everything, and clean up
#   sudo ./box.sh keep      …and leave them running (then: sudo ./box.sh down)
#   sudo ./box.sh down      remove everything
#
# Three network namespaces, web, db and bot, each with its own eth0, plugged into a software switch
# (a bridge, br36, 10.36.0.1) by virtual cables (veth pairs). NAT lets them out to the internet, and
# port 8036 on this computer is "published" to the web box's port 80. Needs curl; tshark is optional.
set -e
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
PATH=$PATH:/usr/sbin
BOXES="web:2 db:3 bot:4"
STATE=/run/box36.forward

down() {
    for b in $BOXES; do
        n=${b%%:*}
        ip netns pids "$n" 2>/dev/null | xargs -r kill 2>/dev/null || true
        ip netns del "$n" 2>/dev/null || true
    done
    ip link del br36 2>/dev/null || true
    rm -rf /run/box36-web /run/box36-bot
    nft delete table ip box36 2>/dev/null || true
    [ -f $STATE ] && cat $STATE > /proc/sys/net/ipv4/ip_forward && rm -f $STATE
    true
}

if [ "$1" = down ]; then down; echo "removed"; exit 0; fi
down

# --8<-- [start:bridge]
ip link add br36 type bridge                       # a switch, in software (Chapter 9)
ip addr add 10.36.0.1/24 dev br36                  # the host's address on it: the boxes' router
ip link set br36 up
# --8<-- [end:bridge]

# --8<-- [start:boxes]
for b in $BOXES; do
    n=${b%%:*}; i=${b##*:}
    ip netns add "$n"                                                  # a new, empty network stack
    ip link add "veth-$n" type veth peer name eth0 netns "$n"            # a virtual cable, one end inside
    ip link set "veth-$n" master br36 up                                # plug the outside end into the switch
    ip netns exec "$n" ip addr add "10.36.0.$i/24" dev eth0
    ip netns exec "$n" ip link set eth0 up
    ip netns exec "$n" ip link set lo up
    ip netns exec "$n" ip route add default via 10.36.0.1               # everything else: ask the host
done
# --8<-- [end:boxes]

# --8<-- [start:nat]
cat /proc/sys/net/ipv4/ip_forward > $STATE
echo 1 > /proc/sys/net/ipv4/ip_forward             # let the host route between br36 and the real network
nft -f - <<'EOF'
table ip box36 {
    chain post {
        type nat hook postrouting priority srcnat;
        ip saddr 10.36.0.0/24 oifname != "br36" masquerade      # going out: borrow the host's address (Chapter 22)
    }
    chain pre {
        type nat hook prerouting priority dstnat;
        tcp dport 8036 dnat to 10.36.0.2:80                      # "publish" port 8036 → web:80
    }
}
EOF
# --8<-- [end:nat]

# two web servers, both on port 80, in different boxes: no conflict
for n in web bot; do
    mkdir -p /run/box36-$n && echo "Hello from the $n box" > /run/box36-$n/index.html
    ip netns exec $n python3 -m http.server 80 --directory /run/box36-$n >/dev/null 2>&1 &
done
sleep 2

echo "== inside the db box: its own interfaces, addresses and routes"
ip netns exec db ip -br addr | sed 's/^/   /'
ip netns exec db ip route | sed 's/^/   /'
echo "== box to box, across the bridge"
ip netns exec db ping -c 2 -q 10.36.0.2 | tail -1 | sed 's/^/   db → web ping: /'
ip netns exec db curl -s -o /dev/null -w "   db → web http: %{http_code}\n" http://10.36.0.2/
echo "== both web and bot are listening on port 80, in their own namespaces"
for n in web bot; do ip netns exec $n ss -ltnH | sed "s/^/   $n: /"; done
echo "== out to the internet, through the host's NAT"
ip netns exec bot curl -s -o /dev/null -w "   bot → https://example.org: HTTP %{http_code}, from %{local_ip} to %{remote_ip}\n" https://example.org/
echo "== the host's switch: which MAC address is on which cable"
bridge link show master br36 | sed 's/^/   /'
bridge fdb show br br36 | grep -v permanent | sed 's/^/   /'
if command -v conntrack >/dev/null; then
    echo "== the NAT, remembered by conntrack"
    conntrack -L -s 10.36.0.4 2>/dev/null | sed 's/^/   /'
fi
echo "== network namespaces on this computer"
lsns -t net | sed 's/^/   /'

if [ "$1" = keep ]; then
    echo; echo "left running. From another computer: curl http://THIS-COMPUTER:8036/   Remove: sudo $0 down"
else
    down
fi
