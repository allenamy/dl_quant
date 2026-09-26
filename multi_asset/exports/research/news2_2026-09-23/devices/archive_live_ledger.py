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
  archive_live_ledger.py --root <archive dir> --runs <receipt dir>   one archiving pass (+ runs/RUN_<utc>.json always)
  archive_live_ledger.py --selftest --root <tmp dir>                 design 7b (2 positive + 9 red) + rev-1 R10-R12

rev 1 (2026-09-26, deployment package): guard = installed sibling copy (R10); every run leaves a receipt in a runs dir
outside the archive (R11); the producer's state dir is ENUMERATED in-run (R12); derived liveness thresholds in every
receipt (design s5); MANIFEST.last_update_utc (design s5 name); conflicts.jsonl rewritten atomically, not appended;
no json.dump(x, open(p,'w')) anywhere.
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
# rev 1 (2026-09-26, deployment package): the guard is the INSTALLED SIBLING copy, never the repo under ~/Desktop.
# Rev 0 called ~/Desktop/quant_research/.../venue_quiet_window.py, which a launchd job may be unable to read (the
# TCC wall on record for ~/Desktop); a missing sibling is an error, there is no fallback path to drift to.
QW = os.path.join(os.path.dirname(os.path.realpath(__file__)), "venue_quiet_window.py")
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
    return durable_write_bytes(path, json.dumps(obj, sort_keys=True).encode("utf-8"))


TAIL_ROWS = 400      # shadow_loop_v3.py L421: ledger_tail keeps the last 400 rows per symbol


def derive_thresholds(tail):
    """Design s5: the longest tolerable gap is the shortest coverage among TRUNCATED names (exactly TAIL_ROWS rows;
    a newly listed name is short because it is new, not because rows were dropped). Recomputed every run."""
    cov = {s: (int(r[-1][0]) - int(r[0][0])) / 3600.0 for s, r in tail.items() if len(r) >= 2}
    trunc = {s: h for s, h in cov.items() if len(tail[s]) >= TAIL_ROWS}
    if not trunc:
        return {"basis": "no truncated name", "hard_fail_h": None, "warn_h": None}
    s_min = min(trunc, key=trunc.get)
    return {"basis": f"min coverage over {len(trunc)} names with {TAIL_ROWS} rows", "shortest_name": s_min,
            "hard_fail_h": round(trunc[s_min], 2), "warn_h": round(trunc[s_min] / 2.0, 2)}


def durable_write_bytes(path, payload):
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".json")
    try:
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
        if not os.path.isfile(QW):                                   # R10: no guard is not an open window
            raise ArchiveError(f"quiet-window guard {QW} not installed next to this file -- unknown is not open (R10)")
        rec["window"] = {"guard": QW, "guard_sha256": sha_file(QW)}
        try:
            out = subprocess.run([sys.executable, "-B", QW, "--json"], capture_output=True, text=True,
                                 timeout=60)
            ok = out.returncode == 0
            st = json.loads(out.stdout) if out.stdout else {}
            rec["window"].update({"exit": out.returncode, "open": ok, "reason": st.get("reason"),
                                  "now_utc": st.get("now_utc"), "remaining_min": st.get("remaining_min")})
        except Exception as e:
            raise ArchiveError(f"quiet-window guard could not be run: {e!r} -- unknown is not open")
        if out.returncode not in (0, 3):
            # R13 (rev 1): the guard's CLI contract is 0 = open, 3 = closed. Rev 0 read ANY non-zero as "closed", so a
            # guard that cannot even be opened (exit 2) produced SKIPPED_WINDOW_CLOSED forever -- measured on rev 0.
            raise ArchiveError(f"quiet-window guard exited {out.returncode} (contract: 0 open / 3 closed): "
                               f"{(out.stderr or '')[-200:]!r} -- a broken guard is not a closed window (R13)")
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

    # R12 (design s7 "must be measured in the launchd context, not assumed"): ENUMERATE the producer's state dir.
    # Opening aux.json by path can succeed where listdir fails (the ~/Desktop TCC shape), so this is its own check.
    try:
        rec["aux"]["dir_enumerated_n"] = len(os.listdir(os.path.dirname(os.path.realpath(aux_path))))
    except OSError as e:
        raise ArchiveError(f"cannot enumerate {os.path.dirname(aux_path)}: {e!r} -- measured, not assumed (R12)")
    aux, aux_sha, attempts = read_aux_twice(aux_path)                # R8
    rec["aux"].update({"sha256": aux_sha, "read_attempts": attempts})
    tail = aux.get("ledger_tail") or {}
    rec["liveness_thresholds"] = derive_thresholds(tail)
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
        # rev 1: whole rewrite + os.replace like the shards (rev 0 appended, which can leave a half line)
        cj = os.path.join(rec["root"], "conflicts.jsonl")
        old = open(cj, "rb").read() if os.path.exists(cj) else b""
        durable_write_bytes(cj, old + b"".join(json.dumps(c, sort_keys=True).encode() + b"\n" for c in conflicts))
        rec["conflicts"] = len(conflicts)
    manifest["runs"] = manifest.get("runs", 0) + 1
    manifest["last_update_utc"] = utc()                              # rev 1: the design's s5 field name (rev 0: last_utc)
    manifest.pop("last_utc", None)
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

    # rev 1: the guard must exist as a sibling file; the stubbed-guard controls get a dummy one
    global QW
    real_qw = QW
    QW = os.path.join(base, "venue_quiet_window.py")
    open(QW, "w").write("# selftest dummy guard; subprocess.run is stubbed in every control that reaches it\n")

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

    # ---- rev 1 R10: guard not installed next to the device -> error, archive root untouched (no fallback path)
    def r10():
        global QW
        probe = os.path.join(base, "arch_r10"); os.makedirs(probe, exist_ok=True)
        saved, QW = QW, os.path.join(base, "no_such_dir", "venue_quiet_window.py")
        try:
            archive_pass(probe, aux, check_window=True)
            return False, "ran without a guard"
        except ArchiveError as e:
            return "not installed" in str(e) and os.listdir(probe) == [], str(e)[:120]
        finally:
            QW = saved
    check("R10 guard missing next to the device -> error, nothing written", "RED", r10)

    # ---- rev 1 R11: every exit path leaves a run receipt; a skip still writes nothing into the archive
    def r11():
        real = subprocess.run
        class _Closed:
            returncode = 3; stdout = json.dumps({"reason": "test: forced closed"}); stderr = ""
        arch, runs = os.path.join(base, "arch_r11"), os.path.join(base, "runs_r11")
        os.makedirs(arch, exist_ok=True)
        subprocess.run = lambda *a, **k: _Closed()
        try:
            rc_skip = run_with_receipt(arch, runs, aux, check_window=True)
        finally:
            subprocess.run = real
        skip_recs = [json.load(open(os.path.join(runs, n))) for n in sorted(os.listdir(runs))]
        arch_after_skip = os.listdir(arch)
        bad = os.path.join(base, "aux_trunc_r11.json"); open(bad, "w").write('{"ledger_tail": {')
        import time as _t; _t.sleep(1.1)                             # receipt names are per-second
        rc_fail = run_with_receipt(arch, runs, bad, check_window=False)
        recs = [json.load(open(os.path.join(runs, n))) for n in sorted(os.listdir(runs))]
        try:
            run_with_receipt(arch, os.path.join(arch, "runs"), aux, check_window=False)
            inside_refused = False
        except ArchiveError:
            inside_refused = True
        ok = (rc_skip == 0 and [r["status"] for r in skip_recs] == ["SKIPPED_WINDOW_CLOSED"] and arch_after_skip == []
              and rc_fail == 2 and [r["status"] for r in recs] == ["SKIPPED_WINDOW_CLOSED", "FAILED"]
              and "does not parse" in recs[-1]["error"] and inside_refused)
        return ok, (f"rc_skip={rc_skip} rc_fail={rc_fail} statuses={[r['status'] for r in recs]} "
                    f"arch_after_skip={arch_after_skip} runs_inside_root_refused={inside_refused}")
    check("R11 skip and failure each leave a run receipt; the archive gets nothing on a skip", "RED", r11)

    # ---- rev 1 R12: producer state dir openable by path but NOT enumerable (the TCC shape) -> error
    def r12():
        d = os.path.join(base, "state_x"); os.makedirs(d, exist_ok=True)
        ax = _fake_aux(os.path.join(d, "aux.json"), {"AUSDT": [[1777000000, 0.0001, 4.0]]})
        probe = os.path.join(base, "arch_r12"); os.makedirs(probe, exist_ok=True)
        os.chmod(d, 0o100)                                           # execute only: open() by path works, listdir fails
        try:
            opened = len(open(ax, "rb").read()) > 0
            archive_pass(probe, ax, check_window=False)
            return False, f"not detected (open by path works={opened})"
        except ArchiveError as e:
            return opened and "cannot enumerate" in str(e) and "R12" in str(e), f"open_by_path={opened} {str(e)[:100]}"
        finally:
            os.chmod(d, 0o755)
    check("R12 producer state dir not enumerable (open by path still works) -> error", "RED", r12)

    # ---- rev 1 R13: a guard that exits outside its 0/3 contract is an error, never a closed window
    def r13():
        real = subprocess.run
        class _Broken:
            returncode = 2; stdout = ""; stderr = "python3: can't open file 'venue_quiet_window.py': [Errno 1] Operation not permitted"
        probe = os.path.join(base, "arch_r13"); os.makedirs(probe, exist_ok=True)
        subprocess.run = lambda *a, **k: _Broken()
        try:
            r = archive_pass(probe, aux, check_window=True)
            return False, f"status={r['status']} (a broken guard read as a closed window)"
        except ArchiveError as e:
            return "R13" in str(e) and os.listdir(probe) == [], str(e)[:120]
        finally:
            subprocess.run = real
    check("R13 guard exit outside 0/3 (e.g. 2 = cannot open, the TCC shape) -> error, not SKIPPED", "RED", r13)

    # ---- rev 1 positive 3: derived thresholds come from the truncated names only
    def p3():
        t = {"OLD": [[1777000000 + 3600 * i, 0.0, 1.0] for i in range(TAIL_ROWS)],
             "NEW": [[1777000000, 0.0, 8.0], [1777003600, 0.0, 8.0]]}
        th = derive_thresholds(t)
        return th["shortest_name"] == "OLD" and th["hard_fail_h"] == TAIL_ROWS - 1, str(th)
    check("derived liveness thresholds use truncated names only (a new short name is not truncation)", "POSITIVE", p3)

    QW = real_qw
    npass = sum(1 for r in res if r["pass"])
    print(f"\n7b CONTROLS {npass}/{len(res)} pass "
          f"({sum(1 for r in res if r['kind'] == 'POSITIVE')} positive, "
          f"{sum(1 for r in res if r['kind'] == 'RED')} red)")
    return res, npass == len(res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--runs", default=None, help="receipt dir, outside --root (required for a pass)")
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
                got = durable_write_json(a.out, rec)                  # rev 1: sha from the verified write
                print(f"receipt -> {a.out}  sha256={got}")
            return 0 if ok else 1
        finally:
            shutil.rmtree(base, ignore_errors=True)
    if not a.runs:
        print("--runs is required for an archiving pass (design s6: every run leaves a receipt)", file=sys.stderr)
        return 2
    return run_with_receipt(a.root, a.runs, a.aux, check_window=not a.no_window)


def run_with_receipt(root, runs, aux_path, check_window=True):
    """rev 1 (design s5/s6): EVERY invocation leaves runs/RUN_<utc>.json -- OK, SKIPPED_WINDOW_CLOSED and FAILED alike --
    so the per-anchor liveness check can tell 'skipped' and 'failed' from 'never started' (no receipt at all). The runs
    dir is separate from the archive root, so R4's 'not one byte in the archive' still holds on a skip."""
    runs_r = check_root(runs)
    if os.path.realpath(root) == runs_r or runs_r.startswith(os.path.realpath(root) + os.sep):
        raise ArchiveError(f"runs dir {runs_r} must not be inside the archive root (R11)")
    try:
        rec = archive_pass(root, aux_path, check_window=check_window)
        rc = 0
    except Exception as e:                                            # ArchiveError, OSError (disk full), anything
        rec = {"utc": utc(), "root": root, "aux": {"path": aux_path}, "status": "FAILED", "error": repr(e)[:500]}
        rc = 2
    rec["device_sha256"] = sha_file(os.path.realpath(__file__))
    os.makedirs(runs_r, exist_ok=True)
    p = os.path.join(runs_r, f"RUN_{rec['utc'].replace(':', '')}.json")
    got = durable_write_json(p, rec)                                  # a failure here raises -> launchd.err, rc != 0
    print(json.dumps({"receipt": p, "sha256": got, "status": rec["status"]}))
    return rc


if __name__ == "__main__":
    sys.exit(main())
