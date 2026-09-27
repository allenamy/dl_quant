#!/usr/bin/env python3
"""The only sanctioned way to change INFLIGHT_REGISTRY.json (class fix for 4d5cd3d79, 3696479ea, 6213fe12c):
the registry is ONE shared file, so a pathspec commit cannot separate my change from someone else's uncommitted edit,
and a hand re-dump can re-encode other agents' entries. This tool refuses to run unless the file is clean in git,
edits one entry, writes with the file's own format (indent=1, ensure_ascii=False), asserts that every OTHER entry is
byte-for-byte unchanged after a re-read, commits exactly that one path, and checks the commit touched only it.

  registry_edit.py add   --json '<entry object>'            --by <agent>
  registry_edit.py close --name <entry name> --note '<text>'  --by <agent>
  registry_edit.py note  --name <entry name> --note '<text>'  --by <agent>   (rev 1: append a dated status note, e.g.
                   paused/resumed/stale field; the entry's own fields are never rewritten, the history stays readable)
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "INFLIGHT_REGISTRY.json")
REPO = subprocess.run(["git", "-C", HERE, "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
REL = os.path.relpath(REG, REPO)
TRAILER = ("\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
           "Claude-Session: https://claude.ai/code/session_01VNPQL7t93ECz7Xkrv9rH6n")


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True)


def dump(entries):
    return json.dumps(entries, indent=1, ensure_ascii=False) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["add", "close", "note"])
    ap.add_argument("--json"); ap.add_argument("--name"); ap.add_argument("--note"); ap.add_argument("--by", required=True)
    a = ap.parse_args()
    st = git("status", "--porcelain", "--", REL)
    if st.returncode or st.stdout.strip():
        sys.exit(f"REFUSED: {REL} is not clean in git (someone has an uncommitted edit):\n{st.stdout}"
                 "Ask its owner to commit it first; never commit or overwrite another agent's pending change.")
    raw = open(REG, encoding="utf-8").read()
    entries = json.loads(raw)
    if dump(entries) != raw:
        sys.exit("REFUSED: the file is not in canonical format (indent=1, ensure_ascii=False); fix by hand with lead")
    before = {e["name"]: json.dumps(e, ensure_ascii=False, sort_keys=True) for e in entries}
    if a.cmd == "add":
        e = json.loads(a.json)
        for k in ("name", "owner", "log", "terminal"):
            if k not in e: sys.exit(f"REFUSED: entry lacks '{k}'")
        if e["name"] in before: sys.exit(f"REFUSED: name {e['name']} already registered")
        entries.append(e); target = e["name"]; msg = f"INFLIGHT: register {target} ({a.by})"
    elif a.cmd == "note":
        hit = [e for e in entries if e["name"] == a.name]
        if len(hit) != 1: sys.exit(f"REFUSED: expected exactly one entry named {a.name}, found {len(hit)}")
        if not a.note: sys.exit("REFUSED: --note is required")
        import time
        hit[0].setdefault("notes", []).append(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {a.by}: {a.note}")
        target = a.name; msg = f"INFLIGHT: note on {target} ({a.by}): {a.note[:80]}"
    else:
        hit = [e for e in entries if e["name"] == a.name]
        if len(hit) != 1: sys.exit(f"REFUSED: expected exactly one entry named {a.name}, found {len(hit)}")
        if hit[0].get("closed"): sys.exit(f"REFUSED: {a.name} is already closed")
        hit[0]["closed"] = True; hit[0]["closed_note"] = f"{a.by}: {a.note}"; target = a.name
        msg = f"INFLIGHT: close {target} ({a.by}): {a.note[:80]}"
    tmp = REG + f".tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(dump(entries)); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, REG)
    after = {e["name"]: json.dumps(e, ensure_ascii=False, sort_keys=True) for e in json.loads(open(REG, encoding="utf-8").read())}
    changed = sorted(n for n in set(before) | set(after) if before.get(n) != after.get(n))
    if changed != [target]:
        git("checkout", "--", REL)
        sys.exit(f"ABORTED and restored: entries changed {changed} != [{target}]")
    c = git("commit", "-q", "-m", msg + TRAILER, "--", REL)
    if c.returncode:
        sys.exit(f"COMMIT FAILED (file left modified, nothing else touched): {c.stderr}")
    files = git("show", "--name-only", "--format=", "HEAD").stdout.split()
    if files != [REL]:
        sys.exit(f"ALARM: HEAD touched {files}, expected only {REL}; report to lead")
    print(f"OK {git('rev-parse', '--short', 'HEAD').stdout.strip()} {msg}")


if __name__ == "__main__":
    main()
