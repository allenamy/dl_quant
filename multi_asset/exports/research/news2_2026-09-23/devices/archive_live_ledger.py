#!/usr/bin/env python3
"""archive_live_ledger.py -- append-only monthly archive of the live producer's funding ledger.

Design: docs/DESIGN_live_funding_ledger_archive_2026-09-25.md (lead approved deployment; criteria
docs/DECISION_RULE_D10_stage2_2026-09-26.md §3). Deployed as its own launchd job, NOT hung off the per-anchor
acceptance chain -- lead's reason, which corrected me: a session-driven chain cannot be the sole executor,
because on the days there is no session it simply does not run, and does so silently. Execution belongs to
something that does not depend on a session; supervision belongs to something a person looks at.

WHY IT EXISTS: `ledger_tail` keeps only the last 400 rows per symbol (shadow_loop_v3.py:421), so a name in a
1h spike regime is truncated after ~17 days, and per-anchor snapshots only start 2026-09-17T12:00Z. Without a
durable archive, "did the live ledger miss a settlement" is permanently unanswerable for anything older than
the rolling tail.

SAFETY PROPERTIES, each with a red control in --selftest:
  * READ-ONLY on the producer. It opens ~/wide_shadow/state/aux.json and never writes inside that tree.
  * The quiet-window guard runs FIRST; outside the window it writes nothing at all.
  * Enumeration failure is an ERROR, never "the directory is empty, so this is a first run" -- the launchd TCC
    case is on record for ~/Desktop, and "not under Desktop" does not imply "enumerable", so this is measured
    in the launchd context rather than assumed.
  * aux.json is read TWICE and the two sha256 compared; a mismatch retries once, and only a second mismatch
    is an error. A truncated file is an error with nothing written.
  * Writes go to a temp file, fsync, read back, then os.replace, so a failure cannot leave a half-written
    shard under the real name. json.dump(x, open(p,"w")) is deliberately NOT used: it does not raise when the
    disk is full, which is the executor defect already on record.
  * Same key with a different value never overwrites: both are kept and the key goes to conflicts.jsonl.
  * The archive root is refused if it resolves under ~/Desktop or ~/wide_shadow.

Usage:
  archive_live_ledger.py --root <archive dir>            one archiving pass
  archive_live_ledger.py --selftest --root <tmp dir>     the 2 positive + 9 red controls of design 7b
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

AUX = os.path.expanduser("~/wide_shadow/state/aux.json")
QW = os.path.expanduser(
    "~/Desktop/quant_research/multi_asset/exports/research/common/venue_quiet_window.py")
FORBIDDEN_ROOTS = (os.path.expanduser("~/Desktop"), os.path.expanduser("~/wide_shadow"))


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ArchiveError(RuntimeError):
    pass


def check_root(root):
    r = os.path.realpath(root)
    for bad in FORBIDDEN_ROOTS:
        if r == os.path.realpath(bad) or r.startswith(os.path.realpath(bad) + os.sep):
            raise ArchiveError(f"archive root {r} is inside {bad}; refusing to start (R7)")
    return r


def enumerate_root(root):
    """os.listdir, so a permission or TCC failure RAISES. An empty list from an existing directory and an
    unreadable directory must never collapse into the same 'first run' branch (R1)."""
    try:
        names = os.listdir(root)
    except FileNotFoundError:
        return None, "absent"
    except OSError as e:
        raise ArchiveError(f"cannot enumerate archive root {root}: {e!r} -- unknown is not empty (R1)")
    return names, "present"


def read_aux_twice(path):
    """Read, hash, read again, compare; retry once on mismatch. A truncated file raises (R8a); a file swapped
    between reads retries and only a second disagreement raises (R8b)."""
    attempts = []
    for attempt in (1, 2):
        b1 = open(path, "rb").read()
        b2 = open(path, "rb").read()
        s1, s2 = sha_bytes(b1), sha_bytes(b2)
        attempts.append({"attempt": attempt, "sha_read1": s1, "sha_read2": s2, "stable": s1 == s2})
        if s1 == s2:
            try:
                return json.loads(b1.decode("utf-8")), s1, attempts
            except Exception as e:
                raise ArchiveError(f"aux.json does not parse: {e!r} -- nothing written (R8a)")
    raise ArchiveError(f"aux.json changed between reads twice in a row; refusing (R8b): {attempts}")


def durable_write_json(path, obj):
    """temp -> fsync -> read back -> compare -> os.replace. Never json.dump(x, open(p,'w')): that does not
    raise on a full disk, which is the recorded executor defect (R9)."""
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".json")
    try:
        payload = json.dumps(obj, sort_keys=True).encode("utf-8")
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        back = open(tmp, "rb").read()
        if back != payload:
            raise ArchiveError(f"read-back differs from what was written for {path} (R9)")
        got = sha_bytes(back)
        os.replace(tmp, path)
        tmp = None
        return got
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def month_of(ts):
    return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime("%Y-%m")


def load_shard(root, month):
    p = os.path.join(root, f"ledger_{month}.json")
    if not os.path.exists(p):
        return {}, None
    return json.load(open(p)), sha_file(p)


def key_of(sym, ft):
    return f"{sym}|{int(ft)}"


def archive_pass(root, aux_path=AUX, check_window=True, manifest_selfcheck=True):
    rec = {"utc": utc(), "root": None, "aux": {"path": aux_path}, "window": None,
           "events_seen": 0, "events_new": 0, "conflicts": 0, "shards_written": {},
           "status": None}
    rec["root"] = check_root(root)                                   # R7 before anything else
    if check_window:
        try:
            out = subprocess.run([sys.executable, "-B", QW, "--json"], capture_output=True, text=True,
                                 timeout=60)
            ok = out.returncode == 0
            rec["window"] = {"exit": out.returncode, "open": ok,
                             "reason": (json.loads(out.stdout).get("reason") if out.stdout else None)}
        except Exception as e:
            raise ArchiveError(f"quiet-window guard could not be run: {e!r} -- unknown is not open")
        if not ok:
            rec["status"] = "SKIPPED_WINDOW_CLOSED"                  # R4: not one byte written
            return rec
    names, state = enumerate_root(rec["root"])                       # R1
    if state == "absent":
        os.makedirs(rec["root"], exist_ok=True)
        names = []
    mpath = os.path.join(rec["root"], "MANIFEST.json")
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {"shards": {}, "runs": 0}
    shard_names = [n for n in names if n.startswith("ledger_") and n.endswith(".json")]
    # R6: a manifest that has seen runs, but an archive with no shards, is a red -- not a first run
    if manifest.get("runs", 0) > 0 and manifest.get("shards") and not shard_names:
        raise ArchiveError("MANIFEST records shards but none are on disk: the archive lost data (R6)")
    if manifest_selfcheck:                                           # R5
        for m, meta in sorted(manifest.get("shards", {}).items()):
            p = os.path.join(rec["root"], f"ledger_{m}.json")
            if not os.path.exists(p):
                raise ArchiveError(f"shard {m} in MANIFEST is missing on disk (R6)")
            got = sha_file(p)
            if got != meta.get("sha256"):
                raise ArchiveError(f"shard {m} sha mismatch: manifest {meta.get('sha256')} disk {got} (R5)")

    aux, aux_sha, attempts = read_aux_twice(aux_path)                # R8
    rec["aux"].update({"sha256": aux_sha, "read_attempts": attempts})
    tail = aux.get("ledger_tail") or {}
    by_month = collections.defaultdict(dict)
    for sym, rows in tail.items():
        for r in rows:
            ft = int(r[0])
            by_month[month_of(ft)][key_of(sym, ft)] = r
            rec["events_seen"] += 1

    conflicts = []
    for month, incoming in sorted(by_month.items()):
        shard, _ = load_shard(rec["root"], month)
        before = len(shard)
        for k, r in incoming.items():
            if k in shard:
                if json.dumps(shard[k], sort_keys=True) != json.dumps(r, sort_keys=True):
                    conflicts.append({"key": k, "archived": shard[k], "incoming": r, "utc": utc()})
                    shard[k + "|conflict|" + utc()] = r              # R3: keep BOTH, never overwrite
                continue
            shard[k] = r
        added = len(shard) - before
        if added or conflicts:
            got = durable_write_json(os.path.join(rec["root"], f"ledger_{month}.json"), shard)
            manifest.setdefault("shards", {})[month] = {"sha256": got, "keys": len(shard), "utc": utc()}
            rec["shards_written"][month] = {"added": added, "keys": len(shard), "sha256": got}
            rec["events_new"] += added
    if conflicts:
        with open(os.path.join(rec["root"], "conflicts.jsonl"), "a") as fh:
            for c in conflicts:
                fh.write(json.dumps(c, sort_keys=True) + "\n")
        rec["conflicts"] = len(conflicts)
    manifest["runs"] = manifest.get("runs", 0) + 1
    manifest["last_utc"] = utc()
    durable_write_json(mpath, manifest)
    rec["status"] = "OK"
    return rec


# ------------------------------------------------------------------ 7b controls
def _fake_aux(path, rows):
    obj = {"ledger_tail": rows, "last_anchor": 1789704000}
    open(path, "w").write(json.dumps(obj))
    return path


def selftest(base):
    res = []

    def check(name, kind, fn):
        try:
            out = fn()
            ok, detail = out if isinstance(out, tuple) else (out, "")
        except Exception as e:
            ok, detail = False, f"unexpected exception: {e!r}"
        res.append({"control": name, "kind": kind, "pass": bool(ok), "detail": str(detail)[:300]})
        print(f"  [{'PASS' if ok else 'FAIL'}] {kind:8s} {name}")
        if not ok:
            print(f"          {detail}")

    root = os.path.join(base, "arch")
    aux = _fake_aux(os.path.join(base, "aux.json"),
                    {"AUSDT": [[1777000000, 0.0001, 4.0], [1777014400, 0.0002, 4.0]],
                     "BUSDT": [[1777000000, -0.0003, 8.0]]})

    # ---- positive 1: archive == union by (symbol, funding_time), compared KEY BY KEY
    def p1():
        r = archive_pass(root, aux, check_window=False)
        shard, _ = load_shard(root, month_of(1777000000))
        want = {key_of("AUSDT", 1777000000), key_of("AUSDT", 1777014400), key_of("BUSDT", 1777000000)}
        return set(shard) == want, f"keys={sorted(shard)} status={r['status']} new={r['events_new']}"
    check("archive equals the union by (symbol, funding_time), key by key", "POSITIVE", p1)

    # ---- positive 2: every written shard sha comes from the read-back and matches MANIFEST
    def p2():
        man = json.load(open(os.path.join(root, "MANIFEST.json")))
        bad = []
        for m, meta in man["shards"].items():
            if sha_file(os.path.join(root, f"ledger_{m}.json")) != meta["sha256"]:
                bad.append(m)
        return not bad, f"shards={list(man['shards'])} mismatched={bad}"
    check("shard sha returned by the read-back equals MANIFEST", "POSITIVE", p2)

    # ---- R1 unenumerable directory -> error, never "empty, so first run"
    def r1():
        blocked = os.path.join(base, "blocked")
        os.makedirs(blocked, exist_ok=True)
        os.makedirs(os.path.join(blocked, "arch"), exist_ok=True)
        os.chmod(blocked, 0o000)
        try:
            archive_pass(os.path.join(blocked, "arch"), aux, check_window=False)
            return False, "no error raised"
        except ArchiveError as e:
            return "cannot enumerate" in str(e), str(e)
        finally:
            os.chmod(blocked, 0o755)
    check("R1 unenumerable root raises, not treated as empty", "RED", r1)

    # ---- R2 idempotent: second run over the same aux adds exactly 0
    def r2():
        r = archive_pass(root, aux, check_window=False)
        return r["events_new"] == 0, f"events_new={r['events_new']}"
    check("R2 re-running the same aux adds exactly 0 events", "RED", r2)

    # ---- R3 same key, different value -> both kept, conflict recorded, no overwrite
    def r3():
        m = month_of(1777000000)
        p = os.path.join(root, f"ledger_{m}.json")
        shard = json.load(open(p))
        k = key_of("AUSDT", 1777000000)
        original = list(shard[k])
        shard[k] = [1777000000, 0.9999, 4.0]
        durable_write_json(p, shard)
        man = json.load(open(os.path.join(root, "MANIFEST.json")))
        man["shards"][m]["sha256"] = sha_file(p)
        durable_write_json(os.path.join(root, "MANIFEST.json"), man)
        r = archive_pass(root, aux, check_window=False)
        after = json.load(open(p))
        kept_tampered = after.get(k) == [1777000000, 0.9999, 4.0]
        has_conflict_key = any(x.startswith(k + "|conflict|") for x in after)
        incoming_present = any(after[x] == original for x in after if x.startswith(k + "|conflict|"))
        cj = os.path.join(root, "conflicts.jsonl")
        logged = os.path.exists(cj) and len(open(cj).read().strip().split("\n")) >= 1
        return (r["conflicts"] >= 1 and kept_tampered and has_conflict_key and incoming_present and logged,
                f"conflicts={r['conflicts']} kept_existing={kept_tampered} "
                f"both_kept={has_conflict_key and incoming_present} logged={logged}")
    check("R3 conflicting key keeps BOTH and logs it, never overwrites", "RED", r3)

    # ---- R4 window closed -> SKIPPED and not one byte written
    def r4():
        probe = os.path.join(base, "arch_win")
        os.makedirs(probe, exist_ok=True)
        before = sorted(os.listdir(probe))
        class _Closed:
            returncode = 3
            stdout = json.dumps({"reason": "test: forced closed"})
            stderr = ""
        real = subprocess.run
        subprocess.run = lambda *a, **k: _Closed()
        try:
            r = archive_pass(probe, aux, check_window=True)
        finally:
            subprocess.run = real
        return (r["status"] == "SKIPPED_WINDOW_CLOSED" and sorted(os.listdir(probe)) == before,
                f"status={r['status']} dir_before={before} dir_after={sorted(os.listdir(probe))}")
    check("R4 window closed -> SKIPPED_WINDOW_CLOSED and zero bytes written", "RED", r4)

    # ---- R5 corrupted shard -> sha self-check reds on the next start
    def r5():
        m = month_of(1777000000)
        p = os.path.join(root, f"ledger_{m}.json")
        d = json.load(open(p))
        d["AUSDT|9999999999"] = [9999999999, 0.5, 4.0]
        open(p, "w").write(json.dumps(d))          # write WITHOUT updating MANIFEST
        try:
            archive_pass(root, aux, check_window=False)
            return False, "corruption not detected"
        except ArchiveError as e:
            return "sha mismatch" in str(e), str(e)
    check("R5 shard edited behind the manifest -> sha self-check reds", "RED", r5)

    # ---- R6 archive emptied but manifest remembers -> red, not a first run
    def r6():
        probe = os.path.join(base, "arch_r6")
        os.makedirs(probe, exist_ok=True)
        archive_pass(probe, aux, check_window=False)
        for n in os.listdir(probe):
            if n.startswith("ledger_"):
                os.unlink(os.path.join(probe, n))
        try:
            archive_pass(probe, aux, check_window=False)
            return False, "emptied archive accepted as a first run"
        except ArchiveError as e:
            return ("lost data" in str(e)) or ("missing on disk" in str(e)), str(e)
    check("R6 emptied archive with a non-empty manifest -> red", "RED", r6)

    # ---- R7 forbidden root -> refuses to start
    def r7():
        outs = []
        for bad in (os.path.expanduser("~/Desktop/zz_archive_probe"),
                    os.path.expanduser("~/wide_shadow/zz_archive_probe")):
            try:
                archive_pass(bad, aux, check_window=False)
                outs.append((bad, False, "no refusal"))
            except ArchiveError as e:
                outs.append((bad, "refusing to start" in str(e), str(e)[:80]))
        return all(o[1] for o in outs), str(outs)
    check("R7 root under ~/Desktop or ~/wide_shadow -> refuses to start", "RED", r7)

    # ---- R8a truncated aux -> error, nothing written
    def r8a():
        probe = os.path.join(base, "arch_r8a")
        os.makedirs(probe, exist_ok=True)
        before = sorted(os.listdir(probe))
        bad = os.path.join(base, "aux_trunc.json")
        open(bad, "w").write('{"ledger_tail": {"AUSDT": [[177700')
        try:
            archive_pass(probe, bad, check_window=False)
            return False, "truncated aux accepted"
        except ArchiveError as e:
            return ("does not parse" in str(e)) and sorted(os.listdir(probe)) == before, str(e)[:120]
    check("R8a truncated aux.json -> error and zero bytes written", "RED", r8a)

    # ---- R8b aux swapped between reads -> retry once; a second disagreement is red
    def r8b():
        swap = os.path.join(base, "aux_swap.json")
        _fake_aux(swap, {"AUSDT": [[1777000000, 0.0001, 4.0]]})
        state = {"n": 0}
        real_open = open

        def flaky(p, *a, **k):
            if os.path.realpath(str(p)) == os.path.realpath(swap) and "b" in (a[0] if a else k.get("mode", "r")):
                state["n"] += 1
                payload = json.dumps({"ledger_tail": {"AUSDT": [[1777000000, state["n"] * 1.0, 4.0]]}}).encode()
                import io
                return io.BytesIO(payload)
            return real_open(p, *a, **k)
        import builtins
        builtins.open = flaky
        try:
            probe = os.path.join(base, "arch_r8b")
            os.makedirs(probe, exist_ok=True)
            try:
                archive_pass(probe, swap, check_window=False)
                return False, f"unstable aux accepted after {state['n']} reads"
            except ArchiveError as e:
                # 4 reads = two attempts of (read, read): the retry was actually taken
                return ("changed between reads twice" in str(e)) and state["n"] == 4, \
                       f"{str(e)[:90]} reads={state['n']}"
        finally:
            builtins.open = real_open
    check("R8b aux unstable across reads -> retries ONCE then reds (retry proven taken)", "RED", r8b)

    # ---- R9 write failure -> error AND the real shard is byte-identical to before
    def r9():
        probe = os.path.join(base, "arch_r9")
        os.makedirs(probe, exist_ok=True)
        archive_pass(probe, aux, check_window=False)
        m = month_of(1777000000)
        p = os.path.join(probe, f"ledger_{m}.json")
        before_bytes = open(p, "rb").read()
        aux2 = _fake_aux(os.path.join(base, "aux_more.json"),
                         {"AUSDT": [[1777000000, 0.0001, 4.0], [1777028800, 0.0007, 4.0]]})
        real_fsync = os.fsync
        os.fsync = lambda fd: (_ for _ in ()).throw(OSError(28, "No space left on device"))
        try:
            archive_pass(probe, aux2, check_window=False)
            ok_raised = False
        except OSError:
            ok_raised = True
        except ArchiveError:
            ok_raised = True
        finally:
            os.fsync = real_fsync
        after_bytes = open(p, "rb").read()
        leftovers = [n for n in os.listdir(probe) if n.startswith(".tmp_")]
        return (ok_raised and after_bytes == before_bytes and not leftovers,
                f"raised={ok_raised} shard_unchanged={after_bytes == before_bytes} tmp_leftovers={leftovers}")
    check("R9 write failure -> raises, shard byte-identical, no temp left behind", "RED", r9)

    npass = sum(1 for r in res if r["pass"])
    print(f"\n7b CONTROLS {npass}/{len(res)} pass "
          f"({sum(1 for r in res if r['kind'] == 'POSITIVE')} positive, "
          f"{sum(1 for r in res if r['kind'] == 'RED')} red)")
    return res, npass == len(res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--aux", default=AUX)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-window", action="store_true", help="only for --selftest")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.selftest:
        base = tempfile.mkdtemp(prefix="archsel_", dir=a.root)
        try:
            res, ok = selftest(base)
            rec = {"device": os.path.basename(__file__), "self_sha256": sha_file(os.path.realpath(__file__)),
                   "utc": utc(), "design": "docs/DESIGN_live_funding_ledger_archive_2026-09-25.md 7b",
                   "controls": res, "all_pass": ok,
                   "n_positive": sum(1 for r in res if r["kind"] == "POSITIVE"),
                   "n_red": sum(1 for r in res if r["kind"] == "RED")}
            if a.out:
                json.dump(rec, open(a.out, "w"), indent=1)
                print(f"receipt -> {a.out}  sha256={sha_file(a.out)}")
            return 0 if ok else 1
        finally:
            shutil.rmtree(base, ignore_errors=True)
    rec = archive_pass(a.root, a.aux, check_window=not a.no_window)
    print(json.dumps(rec, indent=1))
    if a.out:
        json.dump(rec, open(a.out, "w"), indent=1)
    return 0 if rec["status"] in ("OK", "SKIPPED_WINDOW_CLOSED") else 2


if __name__ == "__main__":
    sys.exit(main())
