"""NEW_S deploy step A3 — re-seed the producer's funding-EMA state to the TRAINING caliber (DEPLOY_new_servable_models_2026-09-23.md §A).
No exchange call. Run by the operator with the producer STOPPED, after news_backfill.py, inside the quiet window.

Why: the in-service EMA state (aux.json "ema") was seeded 2026-08-16 from the bundle (fund_ema_v1_state.json) and, for the M1 base names,
cold-started 2026-09-04 with a 40-day / 100-row look-back. The training build ran the producer's own update loop (shadow_loop_v3.py L451-L484)
over the full historical ledger from 2022. Both obey the same recursion, but from different seeds: measured at 2026-09-19T00Z on the 450
in-service names, median |Δacc|/|acc| = 6e-11 but max 1.5e-2 (receipt P5_DATA_PARITY). fund_ema is a King feature (col 80) and an F10
feature (col 80), and the fund leg rank — bitwise parity needs the same state.
What it does (no new arithmetic): starting from the training replay's state at 2026-09-19T00Z (fund_replay_tail.npz: acc, last ledger row),
it applies the producer's own EMA update (the L472-L480 lines compiled from shadow_loop_v3.py) to every ledger row the producer holds with
fundingTime > the replay's last row, in order, using the producer's stored interval for each row (asserted equal to the producer's own
inference from the previous row). Names absent from the replay (outside the 829-name axis, e.g. DOSUSDT/MARSCOINUSDT/PONSUSDT on 09-19) keep
their in-service state (they can never be members; they enter only the fund-leg rank base — named residual R3 in the RESULT).
Checks (refuse on failure): the producer ledger row at the replay's last fundingTime exists and carries the same rate; interval recomputation
equals the stored interval on every applied row.
usage: ~/wide_shadow/venv/bin/python news_ema_reseed.py <fund_replay_tail.npz> <out_dir> [--write]
"""
import os, sys, json, ast, hashlib
import numpy as np

WS = os.environ.get("WIDE_SHADOW_HOME", os.path.expanduser("~/wide_shadow")); STATE = f"{WS}/state"   # rehearsal: WIDE_SHADOW_HOME=<state copy>
SRC = os.environ.get("NEWS_PRODUCER_SRC", os.path.expanduser("~/wide_shadow/shadow_loop_v3.py"))
SRC_SHA = "6080073964bffc621c893915b16f71ecafe093194f0b99a66a4463ee12c74e61"; REPLAY_ANCHOR = 1789776000


def producer_funcs():
    raw = open(SRC, "rb").read(); assert hashlib.sha256(raw).hexdigest() == SRC_SHA, "producer source changed"
    lines = raw.decode().split("\n")
    # L472-L480 (1-based): interval inference + EMA update, verbatim, wrapped as a function of (led, est, ft, rate)
    assert lines[471].strip().startswith("iv = (ft - led[-1][0]) / 3600.0") and lines[479].strip().startswith('est = {"acc": est["acc"] + a * (rn - est["acc"])'), (lines[471], lines[479])
    body = "\n".join(l[8:] for l in lines[471:480])
    code = "def upd(led, est, ft, rate):\n" + "\n".join("    " + l for l in body.split("\n")) + "\n        return led, est, iv\n"
    ns = {"json": json, "os": os, "hashlib": hashlib, "np": np}   # R10-E01: the compiled producer helpers need these module globals
    exec(compile(code, SRC + ":L472-L480", "exec"), ns)
    t = ast.parse(raw); t.body = [x for x in t.body if isinstance(x, ast.FunctionDef) and x.name in ("build_generation_record", "_state_file_hashes", "atomic_write", "atomic_json")] + \
        [x for x in t.body if isinstance(x, ast.Assign) and any(getattr(tg, "id", None) == "STATE_FILES" for tg in x.targets)]
    exec(compile(t, SRC, "exec"), ns)
    return ns


def main():
    R = np.load(sys.argv[1], allow_pickle=True); out = sys.argv[2]; write = "--write" in sys.argv; os.makedirs(out, exist_ok=True)
    P = producer_funcs()
    ia = int(np.flatnonzero(R["anchors"].astype(np.int64) == REPLAY_ANCHOR)[0]); syms = [str(s) for s in R["symbols"]]
    aux = json.load(open(f"{STATE}/aux.json")); ema = aux["ema"]; ledger = aux["ledger_tail"]
    rep = {"applied": {}, "kept_in_service": [], "refused": {}, "max_rel_change": 0.0}
    new = dict(ema)
    for j, s in enumerate(syms):
        acc = R["ema_acc"][ia, j]; lft = int(R["last_ft"][ia, j]); lrt = R["last_rate"][ia, j]
        if not np.isfinite(acc) or lft < 0 or s not in ledger: continue
        led_p = ledger[s]; fts = [int(r[0]) for r in led_p]
        if lft not in fts: rep["refused"][s] = "replay last row not in producer ledger tail"; continue
        k = fts.index(lft)
        if float(led_p[k][1]) != float(lrt): rep["refused"][s] = "rate mismatch at replay last row"; continue
        led = [list(led_p[k])]; est = {"acc": float(acc), "last_ts": lft}; n = 0
        for row in led_p[k + 1:]:
            ft, rate, iv_stored = int(row[0]), float(row[1]), float(row[2])
            led, est, iv = P["upd"](led, est, ft, rate)
            if iv != iv_stored: rep["refused"][s] = f"interval recompute {iv} != stored {iv_stored} at {ft}"; break
            n += 1
        if s in rep["refused"]: continue
        old = ema.get(s, {}).get("acc"); new[s] = est
        rel = abs(est["acc"] - old) / max(abs(old), 1e-12) if old is not None else None
        rep["applied"][s] = {"rows_after_replay": n, "old_acc": old, "new_acc": est["acc"], "rel_change": rel}
        if rel is not None: rep["max_rel_change"] = max(rep["max_rel_change"], rel)
    rep["kept_in_service"] = sorted(set(ema) - set(rep["applied"]))
    ok = not rep["refused"]
    rep["ACCEPT"] = ok
    json.dump(rep, open(f"{out}/EMA_RESEED_REPORT.json", "w"), indent=1)
    if ok and write:
        aux["ema"] = new; P["atomic_json"](f"{STATE}/aux.json", aux)
        P["atomic_json"](f"{STATE}/generation.json", P["build_generation_record"](STATE, int(aux["last_anchor"])))
    print("EMA_RESEED", "ACCEPT" if ok else "REFUSE", "applied", len(rep["applied"]), "kept", len(rep["kept_in_service"]), "max_rel_change", rep["max_rel_change"], "(written)" if ok and write else "(not written)")
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
