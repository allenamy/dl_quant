#!/usr/bin/env python3
"""NC release (DESIGN_producer_new_contract §A7 addendum, lead 2026-09-23): regime_dash must survive the new-contract aux.json, where a
name's funding EMA can be {"acc": None, "last_ts": None} (reset / unknown interval / first event). Runs the ORIGINAL and the PATCHED
regime_dash.py end to end on a fake HOME built from one archived production snapshot (read-only copies; the executor pilot_log is an
EMPTY directory, so no live execution data is read; regime_dash_ext.py is NOT copied, so nothing is sent).
  T0 baseline green: original script, unmodified aux ⇒ rc 0, row for the snapshot anchor, name X has a transient score.
  T1 fixture reproduces the defect: original script, aux with X.acc = None ⇒ rc != 0 with TypeError (red on the old code).
  T2 fix: patched script, same aux ⇒ rc 0; X has no transient score (unknown ⇒ NaN ⇒ excluded, not zero); every other baseline name still scored.
  T3 no change on the old contract: patched script, unmodified aux ⇒ the row equals the baseline row exactly.
usage: python3 tests_regime_dash_acc_none.py <original regime_dash.py> <patched regime_dash.py> [snapshot anchor]"""
import json, os, shutil, subprocess, sys, tempfile

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"
USERBASE = subprocess.run([sys.executable, "-m", "site", "--user-base"], capture_output=True, text=True).stdout.strip()   # the launchd job's numpy lives in the real user site
FAILS, N = [], [0]


def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:300]) if detail is not None else ""), flush=True)


def world(t, A, aux):
    h = f"{t}/home"; st = f"{h}/wide_shadow/state"
    for d in ("target_live", "target_combo"): os.makedirs(f"{st}/{d}", exist_ok=True)
    os.makedirs(f"{h}/wide_shadow/fea171", exist_ok=True); os.makedirs(f"{h}/dl_quant_live/state/live/pilot_log", exist_ok=True)
    json.dump(aux, open(f"{st}/aux.json", "w"))
    shutil.copy(f"{WS}/fea171/xfer_ref.npz", f"{h}/wide_shadow/fea171/xfer_ref.npz")
    for a in (A, A - 14400):
        for d in ("target_live", "target_combo"):
            p = f"{WS}/state/{d}/{a}.json"
            if os.path.exists(p): shutil.copy(p, f"{st}/{d}/{a}.json")
    shutil.copy(f"{WS}/shadow_log.jsonl", f"{h}/wide_shadow/shadow_log.jsonl")
    return h


def run(t, script, home):
    rd = f"{t}/rd"; os.makedirs(rd, exist_ok=True)
    shutil.copy(script, f"{rd}/regime_dash.py"); shutil.copy(f"{HOME}/regime_dash/regime_hist_pct.json", f"{rd}/regime_hist_pct.json")
    assert not os.path.exists(f"{rd}/regime_dash_ext.py")
    r = subprocess.run([sys.executable, f"{rd}/regime_dash.py"], env={"HOME": home, "PATH": "/usr/bin:/bin", "PYTHONUSERBASE": USERBASE}, capture_output=True, text=True, cwd=rd)
    rows = [json.loads(l) for l in open(f"{rd}/regime_dash.jsonl")] if os.path.exists(f"{rd}/regime_dash.jsonl") else []
    return r, rows


def main():
    orig, patched = sys.argv[1], sys.argv[2]
    snaps = sorted(int(x) for x in os.listdir(f"{WS}/state/snap") if x.isdigit() and os.path.exists(f"{WS}/state/snap/{x}/COMPLETE"))
    A = int(sys.argv[3]) if len(sys.argv) > 3 else snaps[-1]
    aux0 = json.load(open(f"{WS}/state/snap/{A}/aux.json")); assert int(aux0["prev_rec"]["anchor_ts"]) == A
    print(f"snapshot anchor {A}; original {orig}; patched {patched}")
    with tempfile.TemporaryDirectory() as t:
        r0, rows0 = run(t, orig, world(t, A, aux0))
        row0 = [x for x in rows0 if x.get("anchor_ts") == A]
        check("T0 baseline green: original script, unmodified aux ⇒ rc 0 and one row for A", r0.returncode == 0 and len(row0) == 1, (r0.returncode, r0.stderr[-300:]))
        if not row0:
            print("baseline not green; stop"); sys.exit(1)
        row0 = row0[0]; ts0 = row0["tr_score"]
        X = sorted(n for n in ts0 if n in aux0["ema"])[0]
        print(f"  name X = {X} (baseline tr_score {ts0[X]:.6f}, acc {aux0['ema'][X].get('acc')}), {len(ts0)} names scored")
    aux1 = json.loads(json.dumps(aux0)); aux1["ema"][X] = {"acc": None, "last_ts": None}
    with tempfile.TemporaryDirectory() as t:
        r1, _ = run(t, orig, world(t, A, aux1))
        check("T1 fixture reproduces the defect: original script with X.acc = None ⇒ rc != 0, TypeError", r1.returncode != 0 and "TypeError" in r1.stderr, (r1.returncode, r1.stderr.strip().splitlines()[-1:] if r1.stderr else ""))
    with tempfile.TemporaryDirectory() as t:
        r2, rows2 = run(t, patched, world(t, A, aux1)); row2 = [x for x in rows2 if x.get("anchor_ts") == A]
        ok = r2.returncode == 0 and len(row2) == 1
        ts2 = row2[0]["tr_score"] if ok else {}
        check("T2 patched script with X.acc = None ⇒ rc 0, X unscored (NaN, not zero), every other baseline name still scored",
              ok and X not in ts2 and set(ts2) == set(ts0) - {X}, (r2.returncode, r2.stderr[-300:], len(ts2)))
    with tempfile.TemporaryDirectory() as t:
        r3, rows3 = run(t, patched, world(t, A, aux0)); row3 = [x for x in rows3 if x.get("anchor_ts") == A]
        check("T3 patched script, unmodified aux ⇒ row identical to the baseline row", r3.returncode == 0 and len(row3) == 1 and row3[0] == row0,
              (r3.returncode, sorted(k for k in row0 if row3 and row3[0].get(k) != row0.get(k))[:8]))
    print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
    if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
    print("ALL PASS")


if __name__ == "__main__":
    main()
