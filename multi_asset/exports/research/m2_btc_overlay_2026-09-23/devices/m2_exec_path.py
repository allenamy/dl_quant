#!/usr/bin/env python3
"""m2_exec_path.py — DIAGNOSTIC (no NAV, no fills): what does the certified executor path do to an M2 target file?

Why this exists: the pinned executor (tree 409ea16, imported unchanged from the replay mirror exactly as exec_sim.ExecutorCode does) turns a
target file into orders via external_book.parse_target → target_vector (w / Σ|w_in-universe|) → to_notional(·, NAV × gross_mult) →
anchor_loop.apply_withhold_and_reshape (POP unheld untradables → RESHAPE: w − mean(w), then w / Σ|w| (RESHAPE_REDEMEAN = RESHAPE_RESCALE =
True) → CLAMP held untradables). A BTC overlay written INTO the target file is a NET position; the reshape's re-demean spreads −hedge/N over
every name and the rescale puts the book back at the sizing gross. This device measures, per anchor, the executed-book beta
Σ_s target_s · β_s / Gs for the base file and for the M2 file, on the certified executor code, for a FLAT book (no holdings ⇒ every
untradable name is popped, none clamped; no per-name stop / cooldown; min-notional dust at Gs = NAV0 × gm = 200,000 USDT).
It is a mechanism measurement, not a result: the simulator's realised beta (H2.1) is the criterion.
Inputs are the same pinned files the certified runner reads (RUN_CONFIG_main_A0_2026-09-19 pins + the objb universe), sha-checked.
usage: env -i PATH=/usr/bin:/bin HOME=/root nice -n 10 /workspace/venv/bin/python -B m2_exec_path.py PATH,HOME,LC_CTYPE <run_config.json> <base_run_tag>
         <m2_run_tag> <beta_npz> <diag_npz> <out_npz> <out_json>
"""
import os, sys, json, time
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[_k] = "1"
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import m2_lib as M
DEV = "/workspace/baseline_tables_2026-09-19/devices_v3"
sys.path.insert(0, DEV)
import bt_driver_lib as DL
import bt_objb_targets as OT

T0 = time.time()
cfg_p, base_tag, m2_tag, beta_p, diag_p, out_npz, out_json = sys.argv[2:9]
CFG = json.load(open(cfg_p)); runs = {r["tag"]: r for r in CFG["runs"]}
rec = dict(device="m2_exec_path.py", self_sha256=M.sha_file(os.path.abspath(__file__)), argv=sys.argv, config={"path": cfg_p, "sha256": M.sha_file(cfg_p)},
           utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), checks=[])
FAILS = []


def check(name, ok, detail=None):
    rec["checks"].append(dict(check=name, ok=bool(ok), detail=detail)); print("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:300], flush=True)
    if not ok: FAILS.append(name)


for k in ("exec_sim", "simlib", "input_manifest", "price_full_meta", "tradability"):
    got = M.sha_file(CFG["pins"][k]["path"]); check(f"pin.{k}", got == CFG["pins"][k]["sha256"], got[:16])
ES, SL, BH, L2 = DL.import_modules(CFG, DEV)
M0 = BH.HistMirror(CFG["paths"]["exec_mirror"], "/dev/shm/m2_ep_%d" % os.getpid()); X = ES.ExecutorCode(M0)
check("executor.redemean_rescale_switches", X.AL.RESHAPE_REDEMEAN is True and X.AL.RESHAPE_RESCALE is True, [X.AL.RESHAPE_REDEMEAN, X.AL.RESHAPE_RESCALE])
PM = np.load(CFG["pins"]["price_full_meta"]["path"], allow_pickle=True); SY = [str(s) for s in PM["symbols"]]; nS = len(SY); bj = SY.index(M.BTC)
anchors = np.arange(DL.ts(CFG["window"]["first_anchor"]), DL.ts(CFG["window"]["last_anchor"]) + 1, 14400, dtype=np.int64)
TRZ = np.load(CFG["pins"]["tradability"]["path"], allow_pickle=True); TRS = np.asarray(TRZ["state_W24H"]); trow = {int(t): i for i, t in enumerate(TRZ["anchor_ts"].astype(np.int64))}
SYa = np.array(SY)
books = {}
for tag in (base_tag, m2_tag):
    tg = runs[tag]["targets"]
    T = OT.load_targets(tg["sources"], reading=tg["reading"], arm=tg["arm"], n_sym=nS)
    W, fresh, kind, cnt = OT.book_for_window(T, anchors, nS)
    PIT = OT.universe_rows(tg["universe"]["path"], tg["universe"]["sha256"], anchors, SY)
    books[tag] = (W, fresh, PIT); check(f"targets.{tag}.loaded", True, cnt)
check("universe_rows_equal", np.array_equal(books[base_tag][2], books[m2_tag][2]))
BZ = np.load(beta_p); BA = BZ["anchor"].astype(np.int64); pos = {int(a): i for i, a in enumerate(BA)}
check("beta_axis_covers_window", all(int(a) in pos for a in anchors))
Bw = BZ["beta"][np.array([pos[int(a)] for a in anchors])]
D = np.load(diag_p); dpos = {int(a): i for i, a in enumerate(D["anchor"].astype(np.int64))}; di = np.array([dpos[int(a)] for a in anchors])
bb_file = D["beta_book"][di]; L1b = D["L1_base"][di]; hedge_file = D["hedge"][di]
GS = float(CFG["nav0_usdt"]) * float(CFG["current_production_config"]["gross_mult"])
floors = {s: float((X.filters.f.get(s) or {}).get("min_notional", 5.0) or 5.0) for s in SY}
n = len(anchors)
out = {k: np.full(n, np.nan) for k in ("beta_exec_base", "beta_exec_m2", "net_exec_base", "net_exec_m2", "btc_exec_base", "btc_exec_m2",
                                       "gross_exec_base", "gross_exec_m2", "beta_file_base_over_gross_in", "n_names_base", "n_names_m2")}
nbad = 0
for i, A in enumerate(anchors.tolist()):
    tr = set(SYa[TRS[trow[A]] == 2].tolist())
    for tag, sfx in ((base_tag, "base"), (m2_tag, "m2")):
        W, fresh, PIT = books[tag]
        if not fresh[i]: continue
        uni = [SY[j] for j in np.nonzero(PIT[i])[0]]
        doc = BH.target_doc(A, W[i], SY, uni, "m2_exec_path", X.EXT)
        ext = X.EXT.parse_target(json.dumps(doc).encode(), X.ext_cfg, A, A + 1440.0)
        if not ext.get("ok"): nbad += 1; continue
        symbols = sorted(set(ext["symbols"]))
        untr = set(symbols) - tr
        target = X.LG.to_notional(X.EXT.target_vector(ext, symbols), symbols, GS)
        dust = X.EXT.below_min_notional(target, {s: floors[s] for s in target}, X.ext_cfg["min_notional_mult"])
        untr |= set(dust["names"])
        X.AL.apply_withhold_and_reshape(target, {}, sorted(untr), GS, floors_usdt=None, force_flat=())
        bvec = np.array([Bw[i, SY.index(s)] for s in target]); vv = np.array([target[s] for s in target]) / GS
        out["beta_exec_" + sfx][i] = float(np.dot(vv, bvec)); out["net_exec_" + sfx][i] = float(vv.sum())
        out["btc_exec_" + sfx][i] = float(target.get(M.BTC, 0.0) / GS); out["gross_exec_" + sfx][i] = float(np.abs(vv).sum()); out["n_names_" + sfx][i] = len(target)
        if sfx == "base":
            wi = np.array([ext["w"][s] for s in ext["w"]]); bi = np.array([Bw[i, SY.index(s)] for s in ext["w"]])
            out["beta_file_base_over_gross_in"][i] = float(np.dot(wi, bi) / ext["gross_in"])
check("parse_target_ok_everywhere", nbad == 0, nbad)
intended = -bb_file / L1b                                       # the formula's hedge in gross units of the published book
survive = (out["beta_exec_m2"] - out["beta_exec_base"]) / intended
np.savez(out_npz, anchor=anchors, intended_hedge_gross_units=intended, beta_book_file=bb_file, L1_base=L1b, **out)
yr = np.array([time.gmtime(int(a)).tm_year for a in anchors])


def q(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) == 0: raise M.M2Error("empty series")
    return {"n": int(len(x)), "mean": float(x.mean()), "p05": float(np.percentile(x, 5)), "p50": float(np.percentile(x, 50)), "p95": float(np.percentile(x, 95))}


summ = {}
for y in sorted(set(yr.tolist())):
    m = yr == y
    ok = m & np.isfinite(survive) & (np.abs(intended) > 0.01)
    summ[str(y)] = {"beta_file_base_over_L1": q(bb_file[m] / L1b[m]), "beta_exec_base": q(out["beta_exec_base"][m]), "beta_exec_m2": q(out["beta_exec_m2"][m]),
                    "intended_hedge": q(intended[m]), "btc_exec_m2_minus_base": q(out["btc_exec_m2"][m] - out["btc_exec_base"][m]),
                    "net_exec_base": q(out["net_exec_base"][m]), "net_exec_m2": q(out["net_exec_m2"][m]),
                    "beta_change_exec_over_intended (|intended|>0.01)": q(survive[ok])}
rec["summary_by_year"] = summ; rec["out_npz"] = {"path": out_npz, "sha256": M.sha_file(out_npz)}
rec["runtime_s"] = round(time.time() - T0, 1); rec["VERDICT"] = "DONE" if not FAILS else "RED"
json.dump(rec, open(out_json, "w"), indent=1, default=str)
print("M2_EXEC_PATH", rec["VERDICT"], json.dumps(summ, default=str)[:3000], flush=True)
