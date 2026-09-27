#!/usr/bin/env python3
"""Live per-leg momentum loadings x seats, 09-19 00Z .. 09-27 (dlarch spec, message 2026-09-27 ~00:4xZ, written before any reading; the research
axis to 09-18 used the same caliber, 1b6baf38f). READ-ONLY, per-anchor CROSS-SECTIONAL statistics only (no per-name output, no arm split).
Sign convention: loading > 0 = the leg/book leans long recent winners (with momentum); < 0 = long recent losers (contrarian).
Per anchor A the producer actually computed:
  members pm, King rank KZ = legz["king"], fund rank ZFD = legz["fund"]   <- state/snap/<A>/aux.json prev_rec (anchor_ts == A asserted)
  F10 uniform rank zf (combo_stage L232-L233)                              <- cf_legs rev 5 --dump-f10 base-arm replay (base == production target
                                                                               bitwise, cf_legs' STOP rule), dumps/<A>.npz; pm in the dump == pm
  seats w0, w2 = target_combo/<A>.json w3_masked[0], [2]
  p_k (k = 1/3/7 d) = sum log1p(rr) over the 288k 5-minute bars closing at or before A (latest snapshot's rr, causal slice asserted),
      defined when >= 80% of those bars are finite; zp = standardised over the members with a defined p_k
  L(x) = mean over those members of (x - mean x) * zp;  T_K = w0*0.55*L(KZ), T_F10 = w0*0.45*L(zf), T_FUND = w2*L(ZFD), S = T_K+T_F10+T_FUND
  control: L(combo_z) with combo_z = w0*(0.55*KZ + 0.45*zf) + w2*ZFD equals S within 1e-12 (asserted per anchor and k)
  E = sum w_pub*zp / sum|w_pub| over published names that are members with a defined p_k (w_pub = target_live/<A>.json; a name outside the
      members is excluded and counted) — reference only
Anchors the producer never ran (09-26 12Z / 16Z) are rows marked MISSING, never interpolated. The 09-26 09:00Z seat reseed is flagged.
usage: ~/wide_shadow/venv/bin/python momentum_loadings_live.py <cf_legs dump dir>[,<dir>...] <out json>"""
import glob, hashlib, json, os, sys, time
import numpy as np
HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"
sys.path.insert(0, f"{WS}/fea171"); import nc_contract as NC
fmt = lambda t: time.strftime("%m-%dT%HZ", time.gmtime(t))
dump_dirs, outp = sys.argv[1].split(","), sys.argv[2]
RESEED = 1790413200                    # 2026-09-26 09:00Z, the seat reseed went live (6f0ec7557)
T_FROM, T_TO = 1789776000, 1790481600  # 09-19 00Z .. 09-27 04Z
snaps = sorted(int(d) for d in os.listdir(f"{WS}/state/snap") if d.isdigit() and os.path.exists(f"{WS}/state/snap/{d}/rolling.npz"))
last = snaps[-1]
Z = np.load(f"{WS}/state/snap/{last}/rolling.npz"); Bd = np.load(f"{WS}/state/snap/{last}/boundary_raw.npz"); ts = Z["ts"].astype(np.int64)
RR = NC.rr_from_ch0(ts, Z["data"][:, :, 0], Bd["ts"], Bd["col"], Bd["raw"]).astype(np.float64)
syms = json.load(open(f"{WS}/shadow_bundle/config.json"))["symbols_panel"]; col = {s: j for j, s in enumerate(syms)}
LOG = np.log1p(np.where(np.isfinite(RR), RR, 0.0)); FIN = np.isfinite(RR)
CS = np.vstack([np.zeros((1, RR.shape[1])), np.cumsum(LOG, axis=0)]); CF = np.vstack([np.zeros((1, RR.shape[1]), int), np.cumsum(FIN, axis=0)])
dumps = {}
for d in dump_dirs:
    for p in glob.glob(f"{d}/dumps/*.npz"):
        dumps[int(os.path.basename(p)[:-4])] = p

def pk(pm, A, k):
    i1 = int(np.searchsorted(ts, A, side="right")) - 1
    assert ts[i1] <= A, "p_k used a bar after A"
    n = 288 * k; i0 = i1 - n
    if i0 < 0: return np.full(len(pm), np.nan)
    v = CS[i1 + 1, pm] - CS[i0 + 1, pm]; f = (CF[i1 + 1, pm] - CF[i0 + 1, pm]) / n
    return np.where(f >= 0.8, v, np.nan)

def L(x, zp, ok):
    xx = x[ok]; return float(np.mean((xx - xx.mean()) * zp[ok]))

rows, missing = [], []
for A in range(T_FROM, T_TO + 1, 14400):
    snap = f"{WS}/state/snap/{A}"
    if not os.path.exists(f"{snap}/aux.json"):
        missing.append({"A": fmt(A), "why": "the producer never ran this anchor (no snapshot)"}); continue
    pr = json.load(open(f"{snap}/aux.json"))["prev_rec"]; assert int(pr["anchor_ts"]) == A
    pm = np.array(pr["members"], int); KZ = np.array(pr["legz"]["king"], float); ZFD = np.array(pr["legz"]["fund"], float)
    tc = f"{WS}/state/target_combo/{A}.json"
    if A not in dumps or not os.path.exists(tc):
        missing.append({"A": fmt(A), "why": ("no F10 dump (replay missing)" if A not in dumps else "no target_combo")}); continue
    dz = np.load(dumps[A]); assert int(dz["anchor"]) == A and np.array_equal(np.asarray(dz["pm"], int), pm), "dump pm != snapshot members"
    zf = np.nan_to_num(np.asarray(dz["zf"], float))            # combo uses nan_to_num(zf) in z_fc (L288)
    w3m = json.load(open(tc))["w3_masked"]; w0, w2 = float(w3m[0]), float(w3m[2])
    tl = json.load(open(f"{WS}/state/target_live/{A}.json"))["weights"]
    row = {"A": fmt(A), "reseed": "after" if A >= RESEED else "before", "w0": round(w0, 6), "w2": round(w2, 6), "n_members": int(len(pm))}
    for k in (1, 3, 7):
        p = pk(pm, A, k); ok = np.isfinite(p)
        zp = np.full(len(pm), np.nan); zp[ok] = (p[ok] - p[ok].mean()) / p[ok].std()
        lk, lf, lz = L(KZ, zp, ok), L(zf, zp, ok), L(ZFD, zp, ok)
        tk, tf, tz = w0 * 0.55 * lk, w0 * 0.45 * lf, w2 * lz
        S = tk + tf + tz
        combo_z = w0 * (0.55 * KZ + 0.45 * zf) + w2 * ZFD
        assert abs(L(combo_z, zp, ok) - S) <= 1e-12, f"identity failed at {fmt(A)} k={k}"
        pos = {int(j): i for i, j in enumerate(pm)}
        num = den = 0.0; n_out = 0
        for s_, w in tl.items():
            j = col.get(s_); i = pos.get(j) if j is not None else None
            if i is None or not ok[i]: n_out += 1; continue
            num += w * zp[i]; den += abs(w)
        row[f"k{k}"] = {"n_defined": int(ok.sum()), "L_KZ": round(lk, 5), "L_zf": round(lf, 5), "L_ZFD": round(lz, 5),
                        "T_K": round(tk, 5), "T_F10": round(tf, 5), "T_FUND": round(tz, 5), "S": round(S, 5),
                        "E": round(num / den, 5) if den > 0 else None, "E_names_excluded": n_out}
    rows.append(row)
def mean_over(rs):
    out = {}
    for k in (1, 3, 7):
        out[f"k{k}"] = {q: round(float(np.mean([r[f"k{k}"][q] for r in rs if r[f"k{k}"][q] is not None])), 5)
                        for q in ("L_KZ", "L_zf", "L_ZFD", "T_K", "T_F10", "T_FUND", "S", "E")} if rs else None
    out["w0"] = round(float(np.mean([r["w0"] for r in rs])), 5) if rs else None; out["n"] = len(rs)
    return out
pre = [r for r in rows if r["A"] <= "09-26T23Z"]
res = {"device": "momentum_loadings_live.py", "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
       "price_snapshot": last, "dump_dirs": dump_dirs, "n_rows": len(rows), "missing": missing,
       "identity_L_combo_z_equals_S": "asserted per anchor and k (1e-12)",
       "mean_0919_0926": mean_over(pre), "mean_before_reseed": mean_over([r for r in rows if r["reseed"] == "before"]),
       "mean_after_reseed": mean_over([r for r in rows if r["reseed"] == "after"]), "rows": rows}
json.dump(res, open(outp, "w"), indent=1)
print(json.dumps({k: res[k] for k in ("n_rows", "missing", "mean_0919_0926", "mean_after_reseed")}, indent=1))
