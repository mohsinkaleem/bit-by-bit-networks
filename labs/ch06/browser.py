#!/usr/bin/env python3
"""Chapter 6 lab: a text-mode web browser for the Tangled Text Protocol.

    python3 browser.py                          start at ttp://bob/index.mu
    python3 browser.py ttp://carol/index.mu     start somewhere else
    python3 browser.py -v                       also show every request and response

At the prompt:  a number = follow that link    b = back    g <url> = go to a URL
                r = reload                      q = quit
(Start webserver.py in another terminal first.)
"""
import re
import socket
import sys

SERVER = ("127.0.0.1", 7006)       # every "computer" lives on the same server for now
BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
VERBOSE = "-v" in sys.argv


# --8<-- [start:url]
def split_url(url):
    """'ttp://bob/school/homework.mu' -> ('bob', '/school/homework.mu')"""
    assert url.startswith("ttp://"), f"not a ttp:// URL: {url}"
    host, _, path = url[len("ttp://"):].partition("/")
    return host, "/" + path


def resolve(base, link):
    """Turn a link found on the page at `base` into a full URL."""
    if link.startswith("ttp://"):
        return link                                        # absolute: another computer
    host, path = split_url(base)
    if link.startswith("/"):
        return f"ttp://{host}{link}"                       # same computer, from the top
    folder = path.rsplit("/", 1)[0]
    return f"ttp://{host}{folder}/{link}"                  # relative to this page's folder
# --8<-- [end:url]


# --8<-- [start:fetch]
def fetch(url, log):
    """GET a URL, following redirects. Returns (final url, status, headers, body)."""
    for _ in range(5):
        host, path = split_url(url)
        request = (f"GET {path} TTP/1\n"
                   f"Host: {host}\n"
                   f"Accept: text/markup, image/png\n"
                   f"User-Agent: browser.py/1.0\n\n")
        with socket.create_connection(SERVER) as sock:
            sock.sendall(request.encode())
            reply = b""
            while chunk := sock.recv(65536):
                reply += chunk
        head, _, body = reply.partition(b"\n\n")
        status_line, *header_lines = head.decode().split("\n")
        headers = dict(line.split(": ", 1) for line in header_lines)
        status = int(status_line.split(" ")[1])
        log.append((request, head.decode()))
        if status == 301:
            url = resolve(url, headers["Location"])        # moved: ask again at the new place
            continue
        return url, status, headers, body
    raise RuntimeError("too many redirects")
# --8<-- [end:fetch]


def render(url, markup, log):
    """Print a page. Returns the list of link URLs, numbered from 1."""
    links = []

    def link(m):
        links.append(resolve(url, m[1]))
        return f"{BOLD}\033[4m{m[2]}{RESET}{DIM}[{len(links)}]{RESET}"

    def image(m):
        img_url = resolve(url, m[1])
        _, status, headers, body = fetch(img_url, log)     # a picture is a whole separate request!
        if status != 200:
            return f"{DIM}[broken image: {m[1]}]{RESET}"
        return f"{DIM}[picture: {m[1]}, {headers.get('Type')}, {len(body)} bytes]{RESET}"

    title = re.search(r"<title>(.*?)</title>", markup)
    text = re.sub(r"<title>.*?</title>\n?", "", markup)
    text = re.sub(r"<h>(.*?)</h>", lambda m: f"{BOLD}{m[1].upper()}{RESET}", text)
    text = re.sub(r"<b>(.*?)</b>", lambda m: f"{BOLD}{m[1]}{RESET}", text)
    text = re.sub(r'<link to="(.*?)">(.*?)</link>', link, text)
    text = re.sub(r'<image src="(.*?)">', image, text)
    print("\n" + "═" * 64)
    print(f" {BOLD}{title[1] if title else url}{RESET}   {DIM}{url}{RESET}")
    print("═" * 64)
    print(text.rstrip())
    return links


def visit(url):
    log = []
    try:
        url, status, headers, body = fetch(url, log)
    except (ConnectionError, OSError) as e:
        print(f"\ncan't reach the server: {e}. Is webserver.py running?")
        return url, []
    if status != 200:
        print(f"\n{BOLD}{status}{RESET}: {body.decode().strip()}")
        links = []
    elif headers.get("Type", "").startswith("text/markup"):
        links = render(url, body.decode(), log)
    else:
        print(f"\n[{headers.get('Type')}, {len(body)} bytes: this browser can't show those]")
        links = []
    print(f"{DIM}{'─' * 64}\n{len(log)} request(s) for this page{RESET}")
    if VERBOSE:
        for request, reply in log:
            print(DIM + request.rstrip().replace("\n", "\n  > ").join(["  > ", ""]) + RESET)
            print(DIM + reply.replace("\n", "\n  < ").join(["  < ", ""]) + RESET)
    return url, links


def main():
    args = [a for a in sys.argv[1:] if a != "-v"]
    url = args[0] if args else "ttp://bob/index.mu"
    history = []
    url, links = visit(url)
    while True:
        try:
            cmd = input("\nlink number, b(ack), g <url>, r(eload), q(uit)> ").strip()
        except EOFError:
            return
        if cmd == "q":
            return
        if cmd == "b" and history:
            url = history.pop()
        elif cmd.isdigit() and 1 <= int(cmd) <= len(links):
            history.append(url)
            url = links[int(cmd) - 1]
        elif cmd.startswith("g "):
            history.append(url)
            url = cmd[2:].strip()
        elif cmd != "r":
            continue
        url, links = visit(url)


if __name__ == "__main__":
    main()
