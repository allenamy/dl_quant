#!/usr/bin/env python3
"""G2-B funding EMA state parity (PREREG_producer_parity_phase2_oos_2026-09-12, AMENDMENT 2 §A2.5 — procedure frozen before this device ran).
Reference = Phase 1 inverted states: `ema_state_before` taken VERBATIM (AST) from devices/replay_driver.py (f2ced820…), applied to the producer snapshot
producer_state_snapshots/1789200000/aux.json (5e825c2f… = Phase 1 chain_full receipt aux_sha256) for the 41 anchors 1788624000..1789200000.
Rebuild = production recursion (shadow_loop_v3.py L341-349) cold-started at each name's earliest settlement over ledger_full.npz ∪ snapshot ledger_tail
(union by second; snapshot row kept on an unequal-rate second, counted), state after all rows with ft <= A - 14400.
Port self-checks first (i) recomputed iv == stored iv on every snapshot row with ft > 1788624000-14400; (ii) ref(1788624000) forwarded along those rows
== snapshot ema (|d| <= 1e-15, last_ts equal). Gate: every (A, s) with a valid reference: |acc_rebuild - acc_ref| <= 1e-9; reference-without-rebuild = violation.
Writes only /workspace/uplift_r2_2026-09-13/P2/receipts/G2B_funding_parity.json.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B p2_g2b_funding.py PATH,HOME,LC_CTYPE"""
import os, sys, json, time, hashlib, ast, bisect, subprocess
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np
P2 = "/workspace/uplift_r2_2026-09-13/P2"; OUT = f"{P2}/receipts/G2B_funding_parity.json"
assert os.path.realpath(OUT).startswith(P2 + "/")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
T0 = time.time()
IN = {"ledger_full": (f"{P2}/work/ledger_full.npz", "bea6f5752772d54e659a4da5571ca41945a27d1b2316ec0ae52f387074f795ad"),
      "snapshot_aux_1789200000": (f"{P2}/work/snapshots/1789200000/aux.json", "5e825c2f791bb860e9a1d6fb50817719de4acbe54594c9940392bb0640a0260e"),
      "phase1_replay_driver": (f"{P2}/work/phase1_ro/replay_driver.py", "f2ced820daa45e0fec0879b6eaeba58905109b60dc0ac09a6e5b0d7cd1bee4ec"),
      "prereg": (f"{P2}/work/prereg_ro/PREREG_producer_parity_phase2_oos_2026-09-12.md", None)}
for k, (p, s) in IN.items():
    if s is not None: got = sha(p); assert got == s, (k, got, s)
R = {"device": os.path.abspath(__file__), "self_sha256": sha(os.path.abspath(__file__)), "env": dict(os.environ), "inputs": {k: {"path": p, "sha256": sha(p)} for k, (p, s) in IN.items()},
     "python": sys.version.split()[0], "numpy": np.__version__, "utc_start": iso(T0)}
R["nvidia_smi_before"] = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()

# ── verbatim reference function ──
src = open(IN["phase1_replay_driver"][0]).read(); tree = ast.parse(src)
fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "ema_state_before"]; assert len(fn) == 1
ns = {}; exec(compile(ast.Module(body=fn, type_ignores=[]), "replay_driver.py:ema_state_before", "exec"), ns); ema_state_before = ns["ema_state_before"]
R["reference_function_source_sha256"] = hashlib.sha256(ast.get_source_segment(src, fn[0]).encode()).hexdigest()

AUX = json.load(open(IN["snapshot_aux_1789200000"][0])); assert int(AUX["last_anchor"]) == 1789200000
EMA = AUX["ema"]; LED = {s: [list(r) for r in rows] for s, rows in AUX["ledger_tail"].items()}
ANCH = [1788624000 + 14400 * k for k in range(41)]; A0 = ANCH[0]
ALLOWED = [1.0, 2.0, 4.0, 6.0, 8.0]
def snap_iv(gap_s):
    iv = gap_s / 3600.0
    return float(min(ALLOWED, key=lambda a: abs(a - (iv if 0 < iv <= 24 else 8.0))))
def step(est, ft, rate, iv):
    rn = rate * (8.0 / iv)
    if est is None: return {"acc": rn, "last_ts": ft}
    a = 1 - 0.5 ** (max(ft - est["last_ts"], 1) / (3 * 86400.0))
    return {"acc": est["acc"] + a * (rn - est["acc"]), "last_ts": ft}

# ── port self-check (i): iv recomputation on production-appended rows ──
iv_rows = 0; iv_mis = []; iv_noprev = 0
for s, rows in LED.items():
    for k, r in enumerate(rows):
        if int(r[0]) <= A0 - 14400: continue
        if k == 0: iv_noprev += 1; continue
        iv_rows += 1; ivr = snap_iv(int(r[0]) - int(rows[k - 1][0]))
        if ivr != float(r[2]): iv_mis.append([s, iso(r[0]), float(r[2]), ivr])
# ── port self-check (ii): forward the reference along snapshot rows ──
ref0 = ema_state_before(A0, EMA, LED)
fw_n = 0; fw_worst = 0.0; fw_ts_mis = []; fw_mismatch_names = 0
for s, est in ref0.items():
    if isinstance(est, tuple): fw_mismatch_names += 1; continue
    e = None if est is None else dict(est)
    rows = LED.get(s, [])
    for k, r in enumerate(rows):
        if int(r[0]) <= A0 - 14400: continue
        iv = snap_iv(int(r[0]) - int(rows[k - 1][0])) if k else 8.0
        e = step(e, int(r[0]), float(r[1]), iv)
    if e is None: continue
    fw_n += 1; fw_worst = max(fw_worst, abs(e["acc"] - float(EMA[s]["acc"])))
    if int(e["last_ts"]) != int(EMA[s]["last_ts"]): fw_ts_mis.append(s)
port_ok = (len(iv_mis) == 0 and fw_worst <= 1e-15 and not fw_ts_mis)
R["port_selfcheck"] = {"i_iv_rows_checked": iv_rows, "i_iv_mismatches": len(iv_mis), "i_iv_mismatch_examples": iv_mis[:20], "i_rows_without_previous_in_tail": iv_noprev,
                       "ii_names_forwarded": fw_n, "ii_worst_abs": fw_worst, "ii_last_ts_mismatch": fw_ts_mis[:20], "ii_mismatch_names_skipped": fw_mismatch_names, "PASS": port_ok}
print("PORT_SELFCHECK", json.dumps({k: R["port_selfcheck"][k] for k in ("i_iv_rows_checked", "i_iv_mismatches", "ii_names_forwarded", "ii_worst_abs", "PASS")}), flush=True)
if not port_ok:
    R["verdict"] = "INVALID(port self-check failed; G2-B not read)"; json.dump(R, open(OUT, "w"), indent=1); print("G2B_VERDICT INVALID port self-check failed", flush=True); sys.exit(2)

# ── rebuild ──
L = np.load(IN["ledger_full"][0], allow_pickle=True); SY = [str(s) for s in L["symbols"]]; col = {s: j for j, s in enumerate(SY)}
off = L["off"]; FT = L["ft"]; RT = L["rate"]
conflicts = 0; conflict_ex = []; rb_rows_from_snapshot_only = 0
REB = {}   # s -> (fts list, states list)
for s in EMA:
    rows = {}
    if s in col:
        j = col[s]
        for k in range(off[j], off[j + 1]): rows[int(FT[k])] = float(RT[k])
    for r in LED.get(s, []):
        t = int(r[0]); v = float(r[1])
        if t in rows and rows[t] != v:
            conflicts += 1
            if len(conflict_ex) < 20: conflict_ex.append([s, iso(t), rows[t], v])
        if t not in rows: rb_rows_from_snapshot_only += 1
        rows[t] = v
    fts = sorted(rows); states = []; e = None; prev = None
    for t in fts:
        iv = snap_iv(t - prev) if prev is not None else 8.0
        e = step(e, t, rows[t], iv); states.append((e["acc"], e["last_ts"])); prev = t
    REB[s] = (fts, states)
def rb_state(s, cut):
    fts, states = REB.get(s, ([], []))
    k = bisect.bisect_right(fts, cut) - 1
    return None if k < 0 else {"acc": states[k][0], "last_ts": states[k][1]}

# ── compare ──
viol = []; n_pairs = 0; n_none = 0; n_mism = 0; worst = 0.0; per_name = {}; per_anchor = []
for A in ANCH:
    ref = ema_state_before(A, EMA, LED); cut = A - 14400; wA = 0.0; vA = 0
    for s, est in ref.items():
        if est is None: n_none += 1; continue
        if isinstance(est, tuple): n_mism += 1; continue
        n_pairs += 1; rb = rb_state(s, cut)
        if rb is None:
            viol.append([A, s, "absent_in_rebuild"]); vA += 1; per_name.setdefault(s, {"max": float("inf"), "n": 0}); per_name[s]["n"] += 1; continue
        d = abs(rb["acc"] - float(est["acc"])); ts_eq = int(rb["last_ts"]) == int(est["last_ts"])
        wA = max(wA, d); worst = max(worst, d)
        if d > 1e-9 or not ts_eq:
            vA += 1; pn = per_name.setdefault(s, {"max": 0.0, "n": 0, "first": iso(A), "d_first": d, "last": None, "d_last": None, "ts_mismatch": 0})
            pn["max"] = max(pn["max"], d); pn["n"] += 1; pn["last"] = iso(A); pn["d_last"] = d; pn["ts_mismatch"] += (0 if ts_eq else 1)
            if len(viol) < 200: viol.append([A, s, d, ts_eq])
    per_anchor.append({"anchor": A, "utc": iso(A), "worst_abs": wA, "n_violations": vA})
nv_pairs = sum(p["n"] for p in per_name.values())
# attribution (does not change the verdict)
attr = {}
for s, pn in sorted(per_name.items(), key=lambda kv: -kv[1]["max"])[:80]:
    rows = LED.get(s, []); first_live = int(rows[0][0]) if rows else None
    fts, _ = REB[s]; first_rb = fts[0] if fts else None
    # stored live iv vs rebuild gap-iv on live rows at or before A0-4h (seed / earlier production rows)
    ivd = 0; ivd_ex = None
    for k, r in enumerate(rows):
        if int(r[0]) > A0 - 14400 or k == 0: continue
        ivr = snap_iv(int(r[0]) - int(rows[k - 1][0]))
        if ivr != float(r[2]):
            ivd += 1
            if ivd_ex is None: ivd_ex = [iso(r[0]), float(r[2]), ivr]
    attr[s] = {**pn, "live_ledger_first_row": iso(first_live) if first_live else None, "rebuild_first_row": iso(first_rb) if first_rb else None,
               "live_rows_before_A0_with_stored_iv_ne_gap_iv": ivd, "first_such_row": ivd_ex,
               "decay_ratio_last_over_first": (pn["d_last"] / pn["d_first"]) if (pn.get("d_first") and pn.get("d_last") is not None and pn["d_first"] > 0) else None,
               "hl3d_expected_ratio": 0.5 ** ((ANCH[-1] - ANCH[0]) / (3 * 86400.0))}
R.update({"n_anchors": len(ANCH), "n_pairs_compared": n_pairs, "n_reference_none": n_none, "n_reference_mismatch": n_mism, "worst_abs": worst,
          "n_violation_pairs": nv_pairs, "n_violation_names": len(per_name), "rebuild_conflicts_unequal_rate_same_second": conflicts, "conflict_examples": conflict_ex,
          "rebuild_rows_from_snapshot_only": rb_rows_from_snapshot_only, "per_anchor": per_anchor, "violations_first200": viol, "attribution_top80": attr,
          "threshold": 1e-9})
R["verdict"] = "PASS" if (nv_pairs == 0 and n_pairs > 0) else "RED"
R["runtime_s"] = round(time.time() - T0, 1)
R["nvidia_smi_after"] = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
json.dump(R, open(OUT, "w"), indent=1)
print(f"G2B_VERDICT {R['verdict']} pairs={n_pairs} worst_abs={worst:.3e} violation_pairs={nv_pairs} violation_names={len(per_name)} ref_none={n_none} ref_mismatch={n_mism} conflicts={conflicts}", flush=True)
