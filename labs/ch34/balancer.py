#!/usr/bin/env python3
"""Chapter 34 lab: a load balancer (a reverse proxy) in front of three web servers, all on this computer.

    python3 balancer.py demo                 try each way of choosing a server, and a server failing
    python3 balancer.py serve round-robin    run it, then: curl -s http://127.0.0.1:7150/  (also least-conn, hash)

Three "garden" servers listen on ports 7151-7153; bean-2 is slow. The balancer on 7150 passes each
request to one of them, adds X-Forwarded-For, checks their health every second, and answers
502 or 504 itself when a server fails.
"""
import hashlib
import http.client
import http.server
import itertools
import socket
import sys
import threading
import time
import urllib.request

BACKENDS = {"bean-1": (7151, 0.01), "bean-2": (7152, 0.20), "bean-3": (7153, 0.01)}   # name: (port, seconds per request)
PORT = 7150


# ---------------------------------------------------------------- the servers behind it

def start_backend(name, port, delay, state):
    class Garden(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if state.get(name) == "hang":
                time.sleep(30)                                   # alive, but stuck
            time.sleep(delay)
            body = (f"Hello from {name}. You are {self.headers.get('X-Forwarded-For', '?')}, "
                    f"and the balancer is {self.client_address[0]}.\n").encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Served-By", name)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Garden)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ---------------------------------------------------------------- the balancer

class Balancer:
    def __init__(self, strategy):
        self.strategy = strategy
        self.names = list(BACKENDS)
        self.healthy = set(self.names)
        self.active = {n: 0 for n in self.names}                 # requests in progress, per server
        self.rr = itertools.cycle(self.names)
        self.lock = threading.Lock()

    # --8<-- [start:choose]
    def choose(self, client):
        with self.lock:
            live = [n for n in self.names if n in self.healthy]
            if not live:
                return None
            if self.strategy == "round-robin":                   # take turns
                while True:
                    n = next(self.rr)
                    if n in live:
                        return n
            if self.strategy == "least-conn":                    # whoever is least busy right now
                return min(live, key=lambda n: self.active[n])
            if self.strategy == "hash":                          # the same client always goes to the same server
                h = int.from_bytes(hashlib.sha256(client.encode()).digest()[:4], "big")
                return live[h % len(live)]
            raise ValueError(self.strategy)
    # --8<-- [end:choose]

    # --8<-- [start:health]
    def health_checks(self):
        """Every second, ask each server for /health. Take it out of rotation if it doesn't answer quickly."""
        while True:
            for n in self.names:
                try:
                    c = http.client.HTTPConnection("127.0.0.1", BACKENDS[n][0], timeout=1)
                    c.request("GET", "/health")
                    ok = c.getresponse().status == 200
                except OSError:
                    ok = False
                with self.lock:
                    if ok and n not in self.healthy:
                        print(f"   [health] {n} is back")
                    if not ok and n in self.healthy:
                        print(f"   [health] {n} failed its check: out of rotation")
                    (self.healthy.add if ok else self.healthy.discard)(n)
            time.sleep(1)
    # --8<-- [end:health]

    def handler(self):
        lb = self

        class Proxy(http.server.BaseHTTPRequestHandler):
            # --8<-- [start:proxy]
            def do_GET(self):
                client = self.client_address[0] + ":" + self.headers.get("X-Test-Client", "")
                name = lb.choose(client)
                if name is None:
                    return self.reply(503, "no healthy servers\n", "none")
                with lb.lock:
                    lb.active[name] += 1
                try:
                    c = http.client.HTTPConnection("127.0.0.1", BACKENDS[name][0], timeout=2)
                    c.request("GET", self.path, headers={"Host": self.headers.get("Host", ""),
                                                         "X-Forwarded-For": self.client_address[0]})
                    r = c.getresponse()
                    self.reply(r.status, r.read().decode(), name)
                except ConnectionRefusedError:                  # nobody there: a "bad gateway"
                    self.reply(502, f"502 Bad Gateway: {name} refused the connection\n", name)
                except socket.timeout:                          # there, but no answer in time
                    self.reply(504, f"504 Gateway Timeout: {name} didn't answer within 2 s\n", name)
                finally:
                    with lb.lock:
                        lb.active[name] -= 1
            # --8<-- [end:proxy]

            def reply(self, status, body, name):
                data = body.encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Served-By", name)
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass
        return Proxy


def start(strategy, checks=True):
    lb = Balancer(strategy)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), lb.handler())
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if checks:
        threading.Thread(target=lb.health_checks, daemon=True).start()
    return lb, server


def fetch(client="alice"):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/", headers={"X-Test-Client": client})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.headers["X-Served-By"], time.monotonic() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.headers["X-Served-By"], time.monotonic() - t0


def burst(n=30, clients=("alice", "bob", "carol", "dave", "eve")):
    """n requests, 6 at a time, like a browser. Returns [(status, server, seconds)]."""
    results, lock = [], threading.Lock()
    todo = list(range(n))

    def worker():
        while True:
            with lock:
                if not todo:
                    return
                i = todo.pop()
            r = fetch(clients[i % len(clients)])
            with lock:
                results.append((clients[i % len(clients)],) + r)
    threads = [threading.Thread(target=worker) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def report(results):
    counts = {n: sum(1 for _, _, s, _ in results if s == n) for n in BACKENDS}
    avg = sum(t for *_, t in results) / len(results)
    worst = max(t for *_, t in results)
    print("   " + "   ".join(f"{n}: {c:>2}" for n, c in counts.items()) + f"    average {avg * 1000:4.0f} ms, slowest {worst * 1000:4.0f} ms")


def demo():
    state = {}
    backends = {n: start_backend(n, port, delay, state) for n, (port, delay) in BACKENDS.items()}
    print("three servers: bean-1 and bean-3 answer in 10 ms, bean-2 takes 200 ms\n")
    for strategy in ("round-robin", "least-conn", "hash"):
        lb, server = start(strategy, checks=False)
        results = burst()
        print(f"{strategy}: 30 requests, 6 at a time")
        report(results)
        if strategy == "hash":
            for who in ("alice", "bob", "carol"):
                print(f"   {who} always went to: {sorted({s for c, _, s, _ in results if c == who})}")
        server.shutdown()
        server.server_close()
        print()
    lb, server = start("round-robin")
    time.sleep(0.5)
    print("now bean-3 crashes (its port closes):")
    backends["bean-3"].shutdown()
    backends["bean-3"].server_close()
    for _ in range(3):
        status, name, t = fetch()
        print(f"   {status} from {name}")
    time.sleep(2.2)
    print("after the next health check:")
    report(burst(9))
    print("\nnow bean-1 hangs: its port is open, but it never answers:")
    state["bean-1"] = "hang"
    for _ in range(3):
        status, name, t = fetch()
        print(f"   {status} from {name} after {t:.1f} s")
    time.sleep(1.5)
    print("after the next health check:")
    report(burst(6))


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        strategy = sys.argv[2] if len(sys.argv) > 2 else "round-robin"
        state = {}
        for n, (port, delay) in BACKENDS.items():
            start_backend(n, port, delay, state)
        start(strategy)
        print(f"load balancer ({strategy}) on 127.0.0.1:{PORT}, servers on 7151-7153. Ctrl-C to stop.")
        print(f"try:  for i in 1 2 3 4 5 6; do curl -s http://127.0.0.1:{PORT}/; done")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        demo()


if __name__ == "__main__":
    main()
