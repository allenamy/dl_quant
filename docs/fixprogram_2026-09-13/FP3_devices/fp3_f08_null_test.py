#!/usr/bin/env python3
"""FP3 item G (F08 economic impact, 2026-09-17): does the model information on generation-straddling windows move the BOOK? Intervention on the
replay arm's inputs (the arm consumes SCORES: king SLOW file + DL FPRED file; NaN scores are z-scored to 0 = model-neutral): for every OPEN
transition (symbol s, time o) in the lifecycle calendar, the member cells (anchor i, symbol s) with o ≤ E_ts[i] < o + H (H = 30 d, the widest
feature window) get NaN in BOTH score files; the A0 dyn s42 arm (formal profile: tradable umask, RAW, msharpe seat) is run on (a) unperturbed
files = baseline, (b) the exposed cells NaN = treatment, (c) K random member-cell sets of the same size = null. Δ = mean g over the frozen
windows (bps/anchor/gross) treatment − baseline, ranked against the null Δs. Reads only; writes perturbed score copies under F08_OUT and pred
copies (removed afterwards) beside the arm's preds; records go to the tree's probe_artifacts under F08 tags."""
import json, os, subprocess, sys, time, hashlib, numpy as np
R = "/workspace/fp2_2026-09"; H = f"{R}/health_check"; D = f"{R}/devices_v4chain"; KD = f"{R}/king_v4"; PY = "/workspace/venv/bin/python"
UP = "/workspace/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz"; CAL = "/workspace/codex_research/QNT-2026-0907/causal_fullchain_20260914/book/full_axis_calendar_review_20260914/evidence1/calendar_candidate2/CONTRACT_LIFECYCLE.json"
OUT = f"{R}/f08_null"; os.makedirs(OUT, exist_ok=True); PREDS = f"{H}/dev_v4/f8_2026-08-22/preds"; K = int(os.environ.get("F08_K", "20")); HZ = int(os.environ.get("F08_H", "2592000")); SEED = 7
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
WA0, UB, KL0 = 1656547200, 1788120000, 1704067200
T0 = time.time(); log = lambda *a: print(f"[{time.time()-T0:6.0f}s]", *a, flush=True)
z = np.load(f"{R}/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True); E = z["E_ts"].astype(np.int64); M = z["members"]; syms = [str(s) for s in z["symbols"]]; pos = {s: j for j, s in enumerate(syms)}
cal = json.load(open(CAL)); opens = [(int(t["effective_ms"]) // 1000, s) for s, v in cal["symbols"].items() for t in v.get("transitions", []) if t["kind"] == "OPEN"]
cells = []; per_event = []
for o, s in sorted(opens):
    j = pos.get(s); assert j is not None, s
    idx = [i for i in np.where((E >= o) & (E < o + HZ))[0] if j in set(np.asarray(M[i]).tolist())]
    per_event.append({"symbol": s, "open_ts": o, "member_anchors_in_H": len(idx)}); cells += [(int(i), j) for i in idx]
log(f"OPEN events {len(opens)} exposed member cells (H={HZ}s) {len(cells)}")
SLOW0 = f"{KD}/SLOW_v3_on_v4axis.npy"; FP0 = f"{PREDS}/f10_A0_s42.npy"; S = np.load(SLOW0); F = np.load(FP0); assert S.shape == F.shape == (len(E), len(syms)), (S.shape, F.shape)
def write_variant(tag, cl):
    s2 = S.copy(); f2 = F.copy()
    for i, j in cl: s2[i, j] = np.nan; f2[i, j] = np.nan
    sp = f"{OUT}/SLOW_{tag}.npy"; fp = f"{PREDS}/f10_A0_s42_{tag}.npy"; np.save(sp, s2); np.save(fp, f2); return sp, os.path.basename(fp)
def run_arm(tag, sp, fpname):
    cmd = ["bash", f"{D}/run_arm.sh", f"V4_A0_dyn_s42_{tag}", "v4", "w10_health.py", "LEGS=101", "CAL=log", "WRULE=msharpe", "LOOK=900", "MEMBERS_TOPN=829", "FTRIM=zero", "PHI=0.45", "UMASK_SCOPE=m1", f"UMASK_NPZ={UP}", f"COSTB_JSON={H}/calib/costb_fee_steady.json", f"SLOW_NPY={sp}", "FSEED=42", f"FPRED={fpname}"]
    r = subprocess.run(cmd, env={"PATH": os.environ["PATH"], "HOME": os.environ.get("HOME", "/root"), "RUN_ARM_ROOT": H, "RUN_ARM_PY": PY}, capture_output=True, text=True)
    p = f"{H}/dev_v4/probe_artifacts/w10_ablation_series_V4_A0_dyn_s42_{tag}.npz"
    if r.returncode != 0 or not os.path.isfile(p): raise SystemExit(f"arm {tag} rc {r.returncode}: {r.stdout[-400:]} {r.stderr[-400:]}")
    zz = np.load(p, allow_pickle=True); C = [str(c) for c in zz["cols"]]; rec = np.asarray(zz["d30_n2_c42_rec"], float); ts = rec[:, C.index("ts")].astype(np.int64); g = rec[:, C.index("net_ex")] / np.where(rec[:, C.index("gross_total")] > 0, rec[:, C.index("gross_total")], np.nan)
    return ts, g, sha(p)
def stats(ts, g):
    wa = (ts >= WA0) & (ts <= UB); kl = (ts >= KL0) & (ts <= UB); return {"W_ALPHA": float(np.nanmean(g[wa])), "KING_LIVE": float(np.nanmean(g[kl])), "n_WA": int(wa.sum()), "n_KL": int(kl.sum())}
sp, fpn = write_variant("F08base", []); ts0, g0, rs0 = run_arm("F08base", sp, fpn); st0 = stats(ts0, g0); log("baseline", st0)
sp, fpn = write_variant("F08x", cells); ts1, g1, rs1 = run_arm("F08x", sp, fpn); assert np.array_equal(ts0, ts1); st1 = stats(ts1, g1)
d_anchor = g1 - g0; treat = {"dW": st1["W_ALPHA"] - st0["W_ALPHA"], "dKL": st1["KING_LIVE"] - st0["KING_LIVE"], "anchors_changed": int(np.sum(np.abs(np.nan_to_num(d_anchor)) > 1e-12)), "max_abs_d_anchor": float(np.nanmax(np.abs(d_anchor)))}; log("treatment", treat)
rng = np.random.default_rng(SEED); pool = [(int(i), int(j)) for i in range(len(E)) for j in np.asarray(M[i]).tolist()]; nulls = []
for k in range(K):
    pick = [pool[t] for t in rng.choice(len(pool), size=len(cells), replace=False)]; sp, fpn = write_variant(f"F08n{k}", pick); tsk, gk, rsk = run_arm(f"F08n{k}", sp, fpn); stk = stats(tsk, gk)
    nulls.append({"k": k, "dW": stk["W_ALPHA"] - st0["W_ALPHA"], "dKL": stk["KING_LIVE"] - st0["KING_LIVE"], "anchors_changed": int(np.sum(np.abs(np.nan_to_num(gk - g0)) > 1e-12)), "max_abs_d_anchor": float(np.nanmax(np.abs(gk - g0))), "record_sha": rsk[:16]}); log(f"null {k}", nulls[-1])
    os.remove(f"{PREDS}/f10_A0_s42_F08n{k}.npy")
for t in ("F08base", "F08x"): os.remove(f"{PREDS}/f10_A0_s42_{t}.npy")
nd = np.array([n["dW"] for n in nulls]); rank = int(np.sum(np.abs(nd) >= abs(treat["dW"])))
rec = {"device": "fp3_f08_null_test.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%FT%TZ", time.gmtime()), "H_s": HZ, "K": K, "seed": SEED, "inputs": {"calendar": sha(CAL), "dlw_targets": sha(f"{R}/dlw_v4raw/data/dlw_targets.npz"), "SLOW": sha(SLOW0), "FPRED": sha(FP0), "umask": sha(UP), "run_arm": sha(f"{D}/run_arm.sh"), "w10_health": sha(f"{H}/w10_health.py")},
       "events": per_event, "n_exposed_cells": len(cells), "n_member_cells_total": len(pool), "baseline": st0, "baseline_record_sha": rs0[:16], "treatment": dict(treat, record_sha=rs1[:16]), "nulls": nulls, "null_dW_abs_ge_treatment": rank, "null_dW_mean": float(nd.mean()), "null_dW_sd": float(nd.std(ddof=1)) if K > 1 else None,
       "reads": "Δ = treatment − baseline mean g (bps/anchor/gross) over the frozen windows; the null is the same number of member cells chosen at random; a treatment |Δ| inside the null distribution means the straddling windows carry no book-level information beyond what any equally-sized cell removal does"}
json.dump(rec, open(f"{OUT}/F08_NULL_TEST.json", "w"), indent=1); log("F08_NULL_TEST_DONE", {"dW": treat["dW"], "null_mean": rec["null_dW_mean"], "null_sd": rec["null_dW_sd"], "rank": rank, "of": K})
