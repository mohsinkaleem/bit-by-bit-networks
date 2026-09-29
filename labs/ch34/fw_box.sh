#!/bin/bash
# Chapter 34 lab (Linux only, needs sudo): a real stateful firewall, with nftables, in a network namespace.
#
#   sudo ./fw_box.sh          build it, test it, show the rules' counters and the connection table, clean up
#
# A namespace called "garden" (10.34.0.2) plays Grandpa's Pi, joined to this computer (10.34.0.1) by a
# virtual cable (Chapter 36 explains both). Inside, a web server on port 8000 is public; port 2222 isn't.
# Optional: sudo apt install conntrack   (to list the connection-tracking table)
set -e
[ "$(id -u)" = 0 ] || { echo "run with sudo"; exit 1; }
PATH=$PATH:/usr/sbin
NS="ip netns exec garden"

cleanup() {
    ip netns pids garden 2>/dev/null | xargs -r kill 2>/dev/null || true
    [ -n "$HOSTSRV" ] && kill "$HOSTSRV" 2>/dev/null || true
    sleep 0.5
    ip netns del garden 2>/dev/null || true
    ip link del veth-host 2>/dev/null || true
    for i in 1 2 3 4 5 6 7 8 9 10; do          # the kernel removes old namespaces in the background
        ip link show veth-host >/dev/null 2>&1 || break
        sleep 0.5
    done
    true
}
trap cleanup EXIT
cleanup

# --8<-- [start:build]
ip netns add garden
ip link add veth-host type veth peer name veth-garden
ip link set veth-garden netns garden
ip addr add 10.34.0.1/24 dev veth-host && ip link set veth-host up
$NS ip addr add 10.34.0.2/24 dev veth-garden && $NS ip link set veth-garden up && $NS ip link set lo up
$NS python3 -m http.server 8000 --bind 10.34.0.2 >/dev/null 2>&1 &     # the public web server
$NS python3 -m http.server 2222 --bind 10.34.0.2 >/dev/null 2>&1 &     # something that shouldn't be reachable
python3 -m http.server 8001 --bind 10.34.0.1 >/dev/null 2>&1 &         # a server outside, for the Pi to visit
HOSTSRV=$!
sleep 2
ping -c 1 -W 2 10.34.0.2 >/dev/null     # let the new link settle (and learn each other's MAC addresses)
# --8<-- [end:build]

# --8<-- [start:rules]
$NS nft -f - <<'EOF'
table inet garden {
    chain input {
        type filter hook input priority 0; policy drop;
        ct state established,related counter accept    # answers to what we started
        iif lo accept                                     # the Pi talking to itself
        tcp dport 8000 counter accept                     # the web server is public
        counter drop                                      # everything else: silently dropped
    }
}
EOF
# --8<-- [end:rules]

echo "== from outside: the web server (allowed)"
curl -s -m 5 -o /dev/null -w "   port 8000: HTTP %{http_code} in %{time_total} s\n" http://10.34.0.2:8000/
echo "== from outside: port 2222 (dropped: no answer at all, so curl gives up after 3 s)"
curl -s -o /dev/null -m 3 http://10.34.0.2:2222/ && echo "   port 2222: answered?!" || echo "   port 2222: no answer; curl gave up after 3 s"
echo "== from outside: ping (dropped too)"
ping -c 2 -W 1 10.34.0.2 | grep -E "packets" | sed 's/^/   /'
echo "== from inside: the Pi visits a server outside (the answers come back in: ct state established)"
$NS curl -s -m 5 -o /dev/null -w "   10.34.0.1:8001: HTTP %{http_code}\n" http://10.34.0.1:8001/
echo
echo "== the rules, with their counters"
$NS nft list ruleset | sed 's/^/   /'
if command -v conntrack >/dev/null; then
    echo "== the connection-tracking table inside the namespace"
    $NS conntrack -L 2>/dev/null | sed 's/^/   /'
fi
