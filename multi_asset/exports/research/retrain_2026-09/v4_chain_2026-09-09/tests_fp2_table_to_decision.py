#!/usr/bin/env python3
"""tests_fp2_table_to_decision.py — FP3 item J (2026-09-17; independent review round 3 §1 / round 4 §5): the ORIGINAL table feeds the ORIGINAL decision.
Until now the per-year suite and the decision suite each had their own fixture on the two sides of the receipt; the real runner's per_year → decision
link was exercised only by the real run. Here the REAL fp2_per_year_table.py runs on synthetic arms laid on the FORMAL axis (ts[900] = 2022-06-30 00Z,
axis to 2026-08-31 00Z ⇒ 9,138 W_ALPHA / 5,838 KING_LIVE anchors, values known by construction) inside the decision fixture's root, and its receipt
— unedited — is what the REAL fp2_decision.py binds (books re-hashed and equal to the export's inputs, window re-derived from the book axes).
  I1 A1 = A0 + 0.5 bps/anchor/gross everywhere ⇒ table PASS, all four Δ cells [0.5, 0.5] ⇒ G1′ BETTER, G2 True, G3 True ⇒ SWAP_RECOMMENDED rc 0
  I2 A1 = A0 − 1.0 ⇒ G1′ WORSE ⇒ NO_SWAP
  I3 A1 raw axis + 0.5 s (round-4 P2-3) ⇒ the table refuses before integer conversion ⇒ the decision has no PASS table ⇒ UNAVAILABLE
  I4 every book's axis ends 2026-03-01 ⇒ the table's coverage does not reach the frozen UB ⇒ the decision refuses (no recommendation)
  I5 the table is built from OTHER files (same names, different bytes) than the export receipt's books ⇒ arms identity refused ⇒ UNAVAILABLE"""
import calendar, json, os, subprocess, sys, tempfile, hashlib, shutil
import numpy as np
from fp2_decision_fixture import Root, sha, SEEDS, TS, WA0, UB, KL0, N_WA, N_KL, HERE, PY
FAILS, N = [], [0]
def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:300]) if detail is not None else ""), flush=True)
COLS = ['ts', 'net', 'pnl', 'carry', 'cost', 'gross_total', 'gross_member', 'gross_sel', 'nsel', 'nmember', 'fires', 'leg_king', 'leg_rev24', 'leg_fund', 'w3_king', 'w3_rev24', 'w3_fund', 'turnover', 'net_ex', 'pnl_ex', 'carry_ex', 'cost_ex', 'netlong']
SYMS = ["AUSDT", "BUSDT", "CUSDT"]
def g0(ts):   # A0 per-anchor RAW return, bps/anchor/gross: 0.3 + a deterministic wobble (std > 0 so Sharpe is finite; day blocks vary)
    i = np.arange(len(ts)); return 0.3 + 0.2 * np.sin(i * 0.37) + 0.05 * np.cos(i * 0.011)
def umask_file(path, ts):
    np.savez(path, ts=ts, symbols=np.array(SYMS), mask=np.ones((len(ts), len(SYMS)), bool), definition=np.array("integration fixture: all tradable")); return path
def arm(path, ts, g, seed, umask, ts_shift=0.0):
    rec = np.zeros((len(ts), len(COLS))); rec[:, 0] = ts + ts_shift; gt = 2.0
    rec[:, COLS.index("gross_total")] = gt; rec[:, COLS.index("net_ex")] = g * gt; rec[:, COLS.index("pnl_ex")] = (g + 0.1) * gt; rec[:, COLS.index("carry_ex")] = 0.1 * gt; rec[:, COLS.index("cost_ex")] = 0.0; rec[:, COLS.index("turnover")] = 0.05 * gt
    cfg = {"CAL": "log", "PHI": 0.45, "LEGS": "101", "WRULE": "msharpe", "UMASK_SCOPE": "m1", "LOOK": 900, "FTRIM": "zero", "MEMBERS_TOPN": 829, "W3FIX": None, "UMASK_NPZ": umask, "COSTB_JSON": "/x/c.json", "SLOW_NPY": "/x/SLOW.npy", "FPRED": "f.npy", "FSEED": str(seed)}
    np.savez(path, cols=np.array(COLS), d30_n2_c42_rec=rec, config_json=np.array(json.dumps(cfg)), symbols=np.array(SYMS))
def lay_books(X, ts, delta, a1_shift=0.0, into=None):
    """overwrite the fixture's dyn books (A0 and A1, both seeds) with formal-axis arms; returns the umask path used by every arm"""
    um = umask_file(f"{X.R}/data/umask_formal.npz", ts); g = g0(ts)
    for s in SEEDS:
        for a, gg, sh in (("A0", g, 0.0), ("A1", g + delta, a1_shift)):
            p = X.books[f"{a}/dyn/s{s}"] if into is None else f"{into}/w10_ablation_series_V4_{a}_dyn_s{s}.npz"
            arm(p, ts, gg, s, um, ts_shift=sh)
    X.f["umask"] = um; return um
def run_table(X, arms_dir=None):
    e = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "ARMS_DIR": arms_dir or f"{X.R}/hc/probe_artifacts", "OUT_JSON": f"{X.R}/v4_gates/PER_YEAR_TABLE.json", "OUT_MD": f"{X.R}/v4_gates/PER_YEAR_TABLE.md",
         "UMASK_NPZ": X.f["umask"], "ARMS": "A0,A1", "SEATS": "dyn", "SEEDS": "42,2027", "LEV": "2.0", "UB": "2026-08-30T20:00:00Z", "WA_START": "2022-06-30T00:00:00Z"}
    r = subprocess.run([PY, f"{HERE}/fp2_per_year_table.py"], env=e, capture_output=True, text=True); p = e["OUT_JSON"]
    j = json.load(open(p)) if os.path.isfile(p) else None
    return r.returncode, r.stdout + r.stderr, j, p
# ── I1 positive control ──
X = Root(); um = lay_books(X, TS, +0.5)
rc_t, out_t, T, tp = run_table(X)
cells = {k: T["delta"][f"A1-A0/dyn/s{s}"][k] for s in SEEDS for k in ("W_ALPHA", "KING_LIVE")} if T and T.get("VERDICT") == "PASS" else {}
check("I1a the REAL table on formal-axis arms: rc 0, VERDICT PASS, n = 9,138 / 5,838, every Δ cell [0.5, 0.5] with n_days > 0",
      rc_t == 0 and T and T["VERDICT"] == "PASS" and T["delta"]["A1-A0/dyn/s42"]["W_ALPHA"]["n"] == 9138 == N_WA and T["delta"]["A1-A0/dyn/s42"]["KING_LIVE"]["n"] == 5838 == N_KL
      and all(abs(c["dg"] - 0.5) < 1e-9 and abs(c["ci95"][0] - 0.5) < 1e-9 and abs(c["ci95"][1] - 0.5) < 1e-9 and c["n_days"] > 0 for c in cells.values()), (rc_t, T and T.get("VERDICT"), {k: (c.get("dg"), c.get("ci95"), c.get("n")) for k, c in cells.items()} or out_t[-300:]))
rc, o, j = X.run(tp, X.export(), umask=um)
check("★★★ I1b the UNEDITED table receipt into the REAL decision: books re-hashed = export inputs, window re-derived from the book axes ⇒ G1′ BETTER, G2 True, G3 True ⇒ SWAP_RECOMMENDED rc 0",
      rc == 0 and j["RECOMMENDATION"] == "SWAP_RECOMMENDED" and j["G1"]["verdict"] == "BETTER" and j["G2"]["ok"] is True and j["G3"]["ok"] is True and not j["UNAVAILABLE"] and all(v.get("same_sha") is True for v in j["binding"]["same_books"].values()) and j["binding"]["umask"]["table_sha256"] == sha(um) == j["binding"]["umask"]["export_umask_sha256"], (rc, j.get("RECOMMENDATION"), j.get("G1", {}).get("verdict"), j.get("UNAVAILABLE", [])[:3], o[-300:] if rc else ""))
# ── I2 WORSE ──
X = Root(); um = lay_books(X, TS, -1.0); rc_t, out_t, T, tp = run_table(X); rc, o, j = X.run(tp, X.export(), umask=um)
check("I2 A1 = A0 − 1.0 through both real devices ⇒ G1′ WORSE ⇒ NO_SWAP", rc_t == 0 and T["VERDICT"] == "PASS" and j["RECOMMENDATION"] == "NO_SWAP" and j["G1"]["verdict"] == "WORSE", (rc_t, j.get("RECOMMENDATION"), j.get("G1", {}).get("verdict")))
# ── I3 the round-4 axis counterexample, end to end ──
X = Root(); um = lay_books(X, TS, +0.5, a1_shift=0.5); rc_t, out_t, T, tp = run_table(X); rc, o, j = X.run(tp, X.export(), umask=um)
check("★★★ I3 A1 raw axis + 0.5 s: the table refuses (no PASS receipt) and the decision lands on UNAVAILABLE, never a recommendation",
      (T is None or T.get("VERDICT") != "PASS") and j["RECOMMENDATION"] != "SWAP_RECOMMENDED" and j["UNAVAILABLE"], (rc_t, T and T.get("VERDICT"), j.get("RECOMMENDATION"), j.get("UNAVAILABLE", [])[:2]))
# ── I4 books that stop before the frozen upper bound ──
X = Root(); short = TS[TS <= calendar.timegm((2026, 3, 1, 0, 0, 0))]; um = lay_books(X, short, +0.5); rc_t, out_t, T, tp = run_table(X); rc, o, j = X.run(tp, X.export(), umask=um)
check("★★★ I4 every book's axis ends 2026-03-01: the table cannot reach UB 2026-08-30 20Z and the decision refuses (no recommendation; coverage / anchor count named)",
      j["RECOMMENDATION"] != "SWAP_RECOMMENDED" and (j["UNAVAILABLE"] or j["RECOMMENDATION"] == "REFUSED_PROFILE"), (rc_t, T and (T.get("VERDICT"), T.get("coverage", {}).get("reaches_UB")), j.get("RECOMMENDATION"), j.get("UNAVAILABLE", [])[:2]))
# ── I5 the table was built from other files than the export's books ──
X = Root(); um = lay_books(X, TS, +0.5); other = f"{X.R}/other"; os.makedirs(other); lay_books(X, TS, +0.7, into=other)   # export binds X.books (+0.5); the table reads `other` (+0.7): same names, different bytes
rc_t, out_t, T, tp = run_table(X, arms_dir=other); rc, o, j = X.run(tp, X.export(), umask=um)
check("★★★ I5 table from OTHER files (same names, different bytes) than the export receipt's books ⇒ arms identity refused ⇒ UNAVAILABLE",
      rc_t == 0 and T["VERDICT"] == "PASS" and j["RECOMMENDATION"] != "SWAP_RECOMMENDED" and any("arm" in u.lower() or "book" in u.lower() for u in j["UNAVAILABLE"]), (rc_t, j.get("RECOMMENDATION"), j.get("UNAVAILABLE", [])[:2]))
print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
print("ALL PASS")
