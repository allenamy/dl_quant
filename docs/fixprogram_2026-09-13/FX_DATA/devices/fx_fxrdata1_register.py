#!/usr/bin/env python3
"""fx_fxrdata1_register.py — FXR-DATA-1 Object B instantiated on the real book (pod2, CPU, read-only). Committed before it is run.

SPEC v2 section 2 defines the unresolved-holdings register. This device fills it in from the A0 C0 arm, so the thing
`AUDIT_DATA TRD-03` called VERIFIED_IMMATERIAL finally has the bound it never had: **how much exit P&L the book left unidentified.**

An episode enters the register at the anchor where the name stops being ACTIVE while the book still holds it. `w10_sleeve` does not
force-exit such names — their weight decays by EMA — so the exposure that would have needed an exit is the weight AT THAT ANCHOR.

UNITS, stated rather than switched silently. The register is written in price space. The book has no price series (and the cache's
`ret5` is clipped, so prices may not be rebuilt from it — SPEC v2 section 3.1). The instantiation therefore uses the exactly
equivalent return-space mapping: `entry_price = last_reliable_price = 1.0`, so an exit price of `1 + r` is an exit return of `r`.
  * `TO_ZERO`      exit price 0  <=>  exit return -100%  (a long loses the position, a short gains it)
  * `VOL_MULTIPLE_k` exit price 1 +/- k*sigma24, k = 3, sigma24 = std of the name's own y4 over its last 6 anchors while ACTIVE
P&L is reported in the book's own unit, bps per unit gross, i.e. `w * r * 1e4 / gross_total` — the same unit as `pnl_ex` and as the
D1 delta, so it is directly comparable to delta = 0.05.

A one-off exit loss is NOT a per-anchor rate. Both forms are reported and labelled: the total over the window, and that total
divided by the number of anchors in the window, which is an **amortisation** and is named as one.

Usage: python3 fx_fxrdata1_register.py <artifact.npz> <artifact_sha256> <arms_dir> <out_receipt.json> <out_csv>
Exit 0 only if every control passed.
"""
import os, sys, csv, json, time
import numpy as np

ENV_WHITELIST = {"PATH", "HOME", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONPATH"}
EXTRA = sorted(k for k in os.environ if k not in ENV_WHITELIST and k not in ("PWD", "SHLVL", "_", "OLDPWD", "LC_CTYPE"))
assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
os.nice(19)
ART, ART_SHA, ARMS, OUT, OUTCSV = sys.argv[1:6]
for p in os.environ["PYTHONPATH"].split(":"): sys.path.insert(0, p)
import tradability as T
import holdings_register as H

W = "/workspace"
PANEL = f"{W}/data/wide_panel_4h_v2ext.npz"
META = f"{W}/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
META_OFF = 138
T0 = time.time()
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
FAILS = []; CHECKS = []
def check(n, ok, d=None):
    CHECKS.append({"check": n, "ok": bool(ok), **({"detail": d} if d is not None else {})})
    if not ok: FAILS.append(n)

rec = {"device": "fx_fxrdata1_register.py", "self_sha256": T.guarded_sha256(os.path.abspath(__file__)),
       "tradability_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "tradability.py")),
       "register_module_sha256": T.guarded_sha256(os.path.join(os.environ["PYTHONPATH"].split(":")[0], "holdings_register.py")),
       "spec_v2": H.SPEC_V2, "numpy": np.__version__, "argv": sys.argv,
       "env": {k: os.environ[k] for k in sorted(os.environ)},
       "inputs": {p: T.guarded_sha256(p) for p in (PANEL, META)},
       "units": "bps per unit gross, i.e. w * r * 1e4 / gross_total; same unit as pnl_ex and as the D1 delta 0.05",
       "k_vol": H.K_VOL, "utc_start": utc(time.time())}
A = T.Artifact.load(ART, expected_sha256=ART_SHA); rec["artifact_sha256"] = A.sha256

P = np.load(PANEL, allow_pickle=True); pts = P["ts"].astype(np.int64); syms = [str(s) for s in P["symbols"]]
assert syms == A.symbols
M = np.load(META, allow_pickle=True); Y = np.asarray(M["y4"], np.float64)
ets = M["E_ts"].astype(np.int64)
assert np.array_equal(ets[META_OFF:META_OFF + len(pts)], pts)
Yp = Y[META_OFF:META_OFF + len(pts)]
STATE = A._z["state_W24H"][A.rows(pts)]
ACT = STATE == T.TRADABLE
dead = A.dead_after(pts, syms)                   # descriptive only: used to COUNT, never to drive a transition
yrs = np.array([time.gmtime(int(t)).tm_year for t in pts])

rows = []; per_seed = {}
for seed in ("42", "2027"):
    Z = np.load(os.path.join(ARMS, "C0_PWR230k_s%s.npz" % seed), allow_pickle=False)
    cols = [str(c) for c in Z["cols"]]; R = np.asarray(Z["rec"], np.float64)
    Wm = np.asarray(Z["W"], np.float64); gt = R[:, cols.index("gross_total")]
    assert np.array_equal(R[:, cols.index("ts")].astype(np.int64), pts)
    held = np.abs(Wm) > 1e-12
    # an episode opens at the anchor where ACTIVE ends while the book still holds the name
    ends = held & ~ACT & np.vstack([np.zeros((1, len(syms)), bool), ACT[:-1]])
    ri, rj = np.where(ends)
    reg = H.HoldingsRegister()
    n_unpriceable = 0
    for k in range(len(ri)):
        i, j = int(ri[k]), int(rj[k])
        w = float(Wm[i, j])
        lo6 = max(0, i - 6)
        win = Yp[lo6:i, j]; win = win[np.isfinite(win)]
        sig = float(win.std(ddof=1)) if len(win) >= 3 else None
        e = reg.open(syms[j], int(pts[i]), w, 1.0)
        # the last reliable price is the last one with a trade behind it; in return space that is 1.0 at the last ACTIVE anchor
        reg.mark(e, int(pts[i]), activity=H.QUIET, price=1.0, price_evidence="TRADE",
                 sigma24=(sig if sig is not None and np.isfinite(sig) else None))
        if sig is None: n_unpriceable += 1
        lo0, hi0 = e.stress_pnl(stress_basis="TO_ZERO")
        lov, hiv = (e.stress_pnl(stress_basis="VOL_MULTIPLE_k") if sig is not None else (None, None))
        g = gt[i] if gt[i] > 1e-12 else np.nan
        rows.append({"seed": seed, "symbol": syms[j], "anchor": utc(pts[i]), "year": int(yrs[i]),
                     "state": e.state, "qty_w": w, "exit_price": e.exit_price, "unknown_flag": e.unknown_flag,
                     "never_trades_again": bool(dead[i, j]),
                     "pnl_bps_TO_ZERO_lo": (lo0 * 1e4 / g if lo0 is not None else None),
                     "pnl_bps_TO_ZERO_hi": (hi0 * 1e4 / g if hi0 is not None else None),
                     "pnl_bps_VOL3_lo": (lov * 1e4 / g if lov is not None else None),
                     "pnl_bps_VOL3_hi": (hiv * 1e4 / g if hiv is not None else None),
                     "sigma24": sig, "gross_total": float(gt[i])})
    check("C.s%s.no_episode_was_closed_without_evidence" % seed,
          all(e.state not in H.TERMINAL for e in reg.episodes.values()), {"episodes": len(reg.episodes)})
    check("C.s%s.every_episode_has_a_null_exit_price" % seed,
          all(e.exit_price is None for e in reg.episodes.values()), None)
    per_seed[seed] = {"episodes": len(reg.episodes), "episodes_without_sigma": n_unpriceable}
    log("seed", seed, "episodes", len(reg.episodes))

def agg(sel, key_lo, key_hi):
    lo = sum(r[key_lo] for r in sel if r[key_lo] is not None)
    hi = sum(r[key_hi] for r in sel if r[key_hi] is not None)
    n = sum(1 for r in sel if r[key_lo] is not None)
    return {"n_episodes_counted": n, "total_bps_lo": lo, "total_bps_hi": hi}

out = {}
for seed in ("42", "2027"):
    S = [r for r in rows if r["seed"] == seed]
    D = [r for r in S if r["never_trades_again"]]
    nA = int(len(pts))
    o = {"episodes": len(S), "episodes_on_names_that_never_trade_again": len(D),
         "all_episodes": {"TO_ZERO": agg(S, "pnl_bps_TO_ZERO_lo", "pnl_bps_TO_ZERO_hi"),
                          "VOL_MULTIPLE_3": agg(S, "pnl_bps_VOL3_lo", "pnl_bps_VOL3_hi")},
         "never_trades_again_only": {"TO_ZERO": agg(D, "pnl_bps_TO_ZERO_lo", "pnl_bps_TO_ZERO_hi"),
                                     "VOL_MULTIPLE_3": agg(D, "pnl_bps_VOL3_lo", "pnl_bps_VOL3_hi")},
         "by_year_TO_ZERO_never_trades_again": {}}
    for y in sorted(set(yrs.tolist())):
        Dy = [r for r in D if r["year"] == y]
        o["by_year_TO_ZERO_never_trades_again"][str(y)] = agg(Dy, "pnl_bps_TO_ZERO_lo", "pnl_bps_TO_ZERO_hi")
    for tag in ("all_episodes", "never_trades_again_only"):
        for basis in ("TO_ZERO", "VOL_MULTIPLE_3"):
            b = o[tag][basis]
            b["amortised_bps_per_anchor_lo"] = b["total_bps_lo"] / nA
            b["amortised_bps_per_anchor_hi"] = b["total_bps_hi"] / nA
            b["amortisation_note"] = ("a one-off exit loss is not a rate; this is the total divided by the %d anchors of the "
                                      "window, given only so it can be set beside a per-anchor delta" % nA)
    out[seed] = o
    log("seed", seed, "TO_ZERO dead-only total bps", round(o["never_trades_again_only"]["TO_ZERO"]["total_bps_lo"], 2),
        "..", round(o["never_trades_again_only"]["TO_ZERO"]["total_bps_hi"], 2))
rec["register"] = out; rec["per_seed"] = per_seed
rec["worst_episodes_TO_ZERO_s42"] = sorted([r for r in rows if r["seed"] == "42" and r["pnl_bps_TO_ZERO_lo"] is not None],
                                           key=lambda r: r["pnl_bps_TO_ZERO_lo"])[:15]
with open(OUTCSV, "w", newline="") as fh:
    wtr = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); wtr.writeheader()
    for r in rows: wtr.writerow(r)
rec["register_csv"] = {"path": OUTCSV, "sha256": T.guarded_sha256(OUTCSV), "rows": len(rows)}
rec["checks"] = CHECKS; rec["n_failed"] = len(FAILS); rec["failed"] = FAILS
rec["runtime_s"] = round(time.time() - T0, 1); rec["utc_end"] = utc(time.time())
json.dump(rec, open(OUT, "w"), indent=1, default=str)
print("FX_FXRDATA1_REGISTER_DONE", json.dumps({"failed": len(FAILS), "rows": len(rows),
      "s42_dead_TO_ZERO_total_bps": [round(out["42"]["never_trades_again_only"]["TO_ZERO"]["total_bps_lo"], 2),
                                     round(out["42"]["never_trades_again_only"]["TO_ZERO"]["total_bps_hi"], 2)]}), flush=True)
sys.exit(1 if FAILS else 0)
