"""Probe the Garmin MCP server over stdio and report the tools it registers.

Run with: uv run python scripts/probe_mcp.py
Requires no Garmin credentials: tools/list is answered from the MCP handshake
even though the background Garmin login in this environment has nothing to
authenticate with.
"""

import json
import os
import subprocess
import sys

BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".venv", "bin", "garmin-mcp")


def send(proc, payload):
    proc.stdin.write(json.dumps(payload) + "\n")
    proc.stdin.flush()


def read_until(proc, want_id, limit=200):
    for _ in range(limit):
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == want_id:
            return msg
    return None


def main():
    proc = subprocess.Popen(
        [BIN],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env={**os.environ, "GARMIN_EMAIL": "", "GARMIN_PASSWORD": ""},
    )
    try:
        send(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "probe", "version": "1.0"},
            },
        })
        init = read_until(proc, 1)
        if not init:
            print("FAILED: no initialize response", file=sys.stderr)
            return 1
        server = init["result"]["serverInfo"]
        print(f"server: {server['name']} {server.get('version', '')}")

        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

        listing = read_until(proc, 2)
        if not listing:
            print("FAILED: no tools/list response", file=sys.stderr)
            return 1
        tools = listing["result"]["tools"]
        names = sorted(t["name"] for t in tools)
        print(f"tools registered: {len(names)}")

        bidirectional = {
            "download": ["get_activities", "get_activity", "download_activity_file"],
            "upload": ["upload_workout", "upload_workouts"],
            "schedule": ["schedule_workout", "schedule_workouts", "schedule_week"],
        }
        print("\nbidirectional capability check:")
        ok = True
        for kind, wanted in bidirectional.items():
            for name in wanted:
                found = name in names
                ok = ok and found
                print(f"  [{'x' if found else ' '}] {kind:9} {name}")
        print(f"\ntotal tools: {len(names)}")
        print("sample:", ", ".join(names[:12]))
        return 0 if ok else 2
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
