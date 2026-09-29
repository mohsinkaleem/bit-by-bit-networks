#!/usr/bin/env python3
"""Chapter 30 lab: JSON APIs, the way apps talk to servers.

    python3 api.py weather                 ask a real public API about the weather at Grandpa's garden
    python3 api.py serve                   run a tiny garden API on 127.0.0.1:7132…
    python3 api.py demo                    …and, in another window, use every method on it

The weather comes from Open-Meteo (open-meteo.com), which is free and needs no key.
"""
import http.server
import json
import sys
import urllib.error
import urllib.request

GARDEN = (51.5, -0.12)          # latitude and longitude: London, near enough


# --8<-- [start:weather]
def weather():
    lat, lon = GARDEN
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           "&current=temperature_2m,precipitation&daily=precipitation_sum&forecast_days=3&timezone=Europe%2FLondon")
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "bitbybit-lab/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        print(f"GET {url}\n→ {r.status} {r.reason}, Content-Type: {r.headers['Content-Type']}\n")
        data = json.load(r)                       # JSON text → Python dicts and lists
    now = data["current"]
    print(f"in the garden now: {now['temperature_2m']} °C, {now['precipitation']} mm of rain")
    for day, rain in zip(data["daily"]["time"], data["daily"]["precipitation_sum"]):
        print(f"  {day}: {rain} mm of rain" + ("  (water the beans!)" if rain < 1 else ""))
# --8<-- [end:weather]


# --8<-- [start:server]
PLANTS = {1: {"id": 1, "name": "runner beans", "planted": "2026-05-02"}}


class GardenAPI(http.server.BaseHTTPRequestHandler):
    def reply(self, code, obj=None, extra=None):
        body = json.dumps(obj, indent=1).encode() if obj is not None else b""
        self.send_response(code)
        if body:
            self.send_header("Content-Type", "application/json")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def plant_id(self):
        parts = self.path.strip("/").split("/")
        if parts[0] != "plants":
            return None, False
        return (int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None), True

    def do_GET(self):                             # read: safe, changes nothing
        pid, ok = self.plant_id()
        if not ok:
            return self.reply(404, {"error": "no such thing"})
        if pid is None:
            return self.reply(200, list(PLANTS.values()))
        if pid not in PLANTS:
            return self.reply(404, {"error": f"no plant {pid}"})
        self.reply(200, PLANTS[pid])

    def do_POST(self):                            # create: the server picks the new plant's number
        try:
            new = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            name = new["name"]
        except (ValueError, KeyError):
            return self.reply(400, {"error": "send JSON with a name"})
        pid = max(PLANTS, default=0) + 1
        PLANTS[pid] = {"id": pid, "name": name, "planted": new.get("planted")}
        self.reply(201, PLANTS[pid], {"Location": f"/plants/{pid}"})

    def do_DELETE(self):                          # delete: doing it twice has the same effect as once
        pid, ok = self.plant_id()
        if pid in PLANTS:
            del PLANTS[pid]
        self.reply(204)

    def log_message(self, fmt, *args):
        print(f"server: {self.command} {self.path} → {args[1]}")
# --8<-- [end:server]


def call(method, path, obj=None):
    data = json.dumps(obj).encode() if obj is not None else None
    req = urllib.request.Request(f"http://127.0.0.1:7132{path}", data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req) as r:
            code, body, loc = r.status, r.read(), r.headers.get("Location")
    except urllib.error.HTTPError as e:
        code, body, loc = e.code, e.read(), None
    shown = json.dumps(json.loads(body)) if body else "(no body)"
    print(f"{method:<6} {path:<11} → {code}" + (f"  Location: {loc}" if loc else "") + f"   {shown}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "weather":
        weather()
    elif cmd == "serve":
        print("garden API on http://127.0.0.1:7132/plants (Ctrl-C to stop)")
        try:
            http.server.ThreadingHTTPServer(("127.0.0.1", 7132), GardenAPI).serve_forever()
        except KeyboardInterrupt:
            print()
    elif cmd == "demo":
        call("GET", "/plants")
        call("POST", "/plants", {"name": "courgettes", "planted": "2026-06-01"})
        call("GET", "/plants/2")
        call("POST", "/plants", {"colour": "green"})
        call("DELETE", "/plants/1")
        call("DELETE", "/plants/1")
        call("GET", "/plants/1")
        call("GET", "/plants")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
