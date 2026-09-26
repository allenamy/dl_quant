"""test_pinned_sources_intact.py — no training-pinned source file may be edited in place.

WHY THIS EXISTS. I broke the same thing twice in one session, and both times a run discovered it for me:
  * I added a deprecation raise to `fresh_legs.py` -> `fa_ladder.py` L206 `('training source drift', ...)`
    refused the FRESH ladder end;
  * after restoring that, I had ALSO wired fund_replay_guard into `news_p2_build.py` -> the SAME assertion
    refused the SAME end again, one file later.
Both files are pinned by FRESH/NEW_S `work/f10_s*/TRAIN_RECEIPT.json`. Lead's diagnosis (2026-09-26):
**a source file pinned by a training receipt must not be edited in place** -- the pin exists so that editing it
is visible. Fixing the two instances is an instance-shaped fix; this test is the class-shaped one: it enumerates
EVERY pinned .py across the receipts and fails if any has drifted, so the NEXT in-place edit is caught before it
costs an engine run.

RED CONTROL (--red): appends a byte to a scratch copy of a pinned file, points the checker at it, and requires a
failure; then restores. A drift detector that has never seen drift is not known to detect it.

usage: ... test_pinned_sources_intact.py WL [--red]
"""
import os, sys, json, glob, hashlib, time

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
RED = "--red" in sys.argv[2:]
RECEIPT_GLOBS = ("/dev/shm/fresh_2026-09-23/work/f10_s*/TRAIN_RECEIPT.json",
                 "/dev/shm/news_2026-09-23/work/f10_s*/TRAIN_RECEIPT.json",
                 "/dev/shm/news2_2026-09-23/work/f10_s*/TRAIN_RECEIPT.json")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TEST_PINNED_SOURCES_INTACT.json")


def sha(p):
    if not os.path.exists(p): return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def collect():
    """{source_path: {(pinned_sha, receipt_path), ...}} over every reachable training receipt"""
    pins = {}
    for g in RECEIPT_GLOBS:
        for rp in sorted(glob.glob(g)):
            try: d = json.load(open(rp))
            except Exception: continue
            for key in ("sources", "inputs"):
                for p, h in (d.get(key) or {}).items():
                    if p.endswith(".py"):
                        pins.setdefault(p, set()).add((h, rp))
    return pins


def check(pins, override=None):
    """returns (n_entries, drifted, missing). `override` maps path -> path-to-hash-instead (red control)."""
    n = 0; drift = []; missing = []
    for p, vals in sorted(pins.items()):
        target = (override or {}).get(p, p)
        cur = sha(target)
        for h, rp in sorted(vals):
            n += 1
            if cur is None:
                missing.append({"source": p, "receipt": rp}); continue
            if cur != h:
                drift.append({"source": p, "current_sha256": cur, "pinned_sha256": h, "receipt": rp})
    return n, drift, missing


pins = collect()
n, drift, missing = check(pins)
rec = {"device": "test_pinned_sources_intact.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "rule": "a source file pinned by a training receipt must not be edited in place (lead 2026-09-26)",
       "receipt_globs": list(RECEIPT_GLOBS),
       "distinct_pinned_sources": len(pins), "pinned_entries_checked": n,
       "drifted": drift, "missing": missing,
       "history": ("broken twice on 2026-09-25/26 -- fresh_legs.py (deprecation raise) and news_p2_build.py "
                   "(fund_replay_guard wiring). Both were discovered by fa_ladder.py L206 at run time, which is "
                   "one engine run too late; this test moves the detection earlier.")}

if RED:
    # plant drift on a scratch COPY -- never touch the real pinned file
    victim = sorted(pins)[0] if pins else None
    red = {"attempted": bool(victim)}
    if victim:
        scratch = "/tmp/_RED_pinned_probe.py"
        with open(victim, "rb") as f: body = f.read()
        with open(scratch, "wb") as f: f.write(body + b"\n# planted drift\n")
        _, d2, _ = check({victim: pins[victim]}, override={victim: scratch})
        os.remove(scratch)
        red.update({"victim": victim, "drift_detected": bool(d2)})
    rec["red_control"] = red
    rec["red_control_fired"] = bool(red.get("drift_detected"))

tmp = OUT + ".tmp"
with open(tmp, "w") as f:
    json.dump(rec, f, indent=1); f.flush(); os.fsync(f.fileno())
with open(tmp) as f:
    assert json.load(f) == json.loads(json.dumps(rec)), "receipt did not read back equal"
os.replace(tmp, OUT)

print("TEST_PINNED_SOURCES_INTACT sources=%d entries=%d drifted=%d missing=%d"
      % (len(pins), n, len(drift), len(missing)), flush=True)
for d in drift:
    print("  DRIFT %-26s current %s != pinned %s  (%s)"
          % (os.path.basename(d["source"]), d["current_sha256"][:16], d["pinned_sha256"][:16],
             d["receipt"].split("/")[-2]), flush=True)
for m in missing:
    print("  MISSING %s (pinned by %s)" % (m["source"], m["receipt"].split("/")[-2]), flush=True)
if RED:
    print("  red control: planted drift on a scratch copy of %s -> detected=%s"
          % (os.path.basename(rec["red_control"].get("victim", "?")), rec.get("red_control_fired")), flush=True)
    assert rec["red_control_fired"], "RED CONTROL FAILED: planted drift was not detected -- this test is decorative"
assert not drift, f"{len(drift)} pinned source(s) edited in place"
print("  PASS: every pinned training source still matches its receipt", flush=True)
