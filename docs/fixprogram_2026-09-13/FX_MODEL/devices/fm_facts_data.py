#!/usr/bin/env python3
"""fm_facts_data.py — FIXPROGRAM 2026-09-13, FX-MODEL, §0.1 fact table part 2 (data). pod2, READ-ONLY on every input.

Measures the SIZE of the training-input defects, never a model or book outcome: no label enters any statistic except as a
finiteness pattern; no IC, no P&L, no return is computed.

  F1  funding name coverage of the v1 canonical / v2ext / v3splice panels (f_fund_ema, f_fund_ema_v1, f_fund_now); v1 set vs live_pins;
      splice rows <= cut bitwise equal to v1 (positive control for C-FEA-3)
  F2  fea82 cols 80/81 on DL member pairs (dlw_v4raw = v4 chain, dlw_ext = in-service): per year, pairs whose feature is exactly 0 while
      v2ext has a finite value at (anchor, name); positive control: the stored columns equal float16(nan_to_num(splice value))
  F3  legs ZFD (f8_v4 = v4 chain legs, f8_ext = in-service legs) on DL member cells: per year, NaN while v2ext f_fund_ema_v1 is finite
  F4  on the 450 v1 names before the cut: v1 vs v2ext cell agreement for the three funding columns (needed for the fill rule)
  U1  non-crypto share (venue class snapshot, non-crypto = known underlyingType not in {COIN, INDEX}) of king v4 meta and dlw_v4raw
      member pairs per year; live_pins class counts
  T1  king score skew from the clock: boosters (v4 bundle slow2026, in-service v3 bundle slow2026) scored on wide_fea_v4 (rows [E-w, E-1])
      and on wide_fea_v4e (rows [E-w+1, E]) on common members per anchor, 2024-01-01 .. axis end: per-anchor Spearman, top/bottom
      decile overlap, max|dpred|/sd; member-set differences between the two metas

Usage (pod2): env -i PATH=... HOME=... LC_CTYPE=C.UTF-8 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 FM_VENUE=<venue_class json>
              FM_OUT=<receipt.json> /workspace/venv/bin/python -B fm_facts_data.py
"""
import os, sys, json, time, hashlib, calendar
import numpy as np

ALLOWED_ENV = {"PATH", "HOME", "LC_CTYPE", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "FM_VENUE", "FM_OUT", "PWD", "SHLVL", "_"}
_extra = sorted(set(os.environ) - ALLOWED_ENV)
assert not _extra, f"env whitelist violated: {_extra}"
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    assert os.environ.get(_k) == "4", f"{_k} must be 4"
OUT = os.environ["FM_OUT"]; VENUE = os.environ["FM_VENUE"]
T0 = time.time()
P_V1 = "/workspace/data/wide_panel_4h_v1.npz"; P_V2 = "/workspace/data/wide_panel_4h_v2ext.npz"; P_SP = "/workspace/data/wide_panel_4h_v3splice.npz"
PINS = "/workspace/live_pins.json"
DLW = {"v4raw": "/workspace/dlw_v4raw", "ext_inservice": "/workspace/dlw_ext"}
LEGS = {"f8_v4": ("/workspace/f8_v4/data/f10v2_legs.npz", "/workspace/dlw_v4raw"), "f8_ext_inservice": ("/workspace/f8_ext/data/f10v2_legs.npz", "/workspace/dlw_ext")}
KFEA = {"v4": ("/workspace/data/wide_fea_v4.npy", "/workspace/data/wide_fea_v4_meta.npz"), "v4e": ("/workspace/data/wide_fea_v4e.npy", "/workspace/data/wide_fea_v4e_meta.npz")}
BOOST = {"v4_bundle": ("/workspace/shadow_bundle_v4/slow2026.txt", "/workspace/shadow_bundle_v4/config.json"),
         "v3_bundle_inservice_8d79186b": ("/workspace/shadow_bundle_v3/slow2026.txt", "/workspace/live_pins.json")}
FUNDCOLS = ("f_fund_ema", "f_fund_ema_v1", "f_fund_now")


def log(*a):
    print(f"[{time.time()-T0:7.1f}s]", *a, flush=True)


def sha(p):
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""):
            h.update(ch); n += len(ch)
    assert n == os.stat(p).st_size, f"short read {p}"
    return h.hexdigest()


def yr(t):
    return time.gmtime(int(t)).tm_year


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))


rec = {"device": "fm_facts_data.py", "self_sha256": sha(os.path.abspath(__file__)), "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "env": {k: os.environ.get(k) for k in sorted(os.environ)}, "inputs": {}}
for p in [P_V1, P_V2, P_SP, PINS, VENUE] + [f"{d}/data/{f}" for d in DLW.values() for f in ("dlw_targets.npz", "dlw_fea82.npz")] + \
         [v[0] for v in LEGS.values()] + [x for v in KFEA.values() for x in v] + [x for v in BOOST.values() for x in v]:
    if p not in rec["inputs"]:
        rec["inputs"][p] = sha(p)
log("input shas done", len(rec["inputs"]))

# ───────────── F1 panel funding coverage ─────────────
V1 = np.load(P_V1, allow_pickle=True); V2 = np.load(P_V2, allow_pickle=True); SP = np.load(P_SP, allow_pickle=True)
syms = [str(s) for s in V1["symbols"]]
assert syms == [str(s) for s in V2["symbols"]] == [str(s) for s in SP["symbols"]]
NW = len(syms)
t1 = V1["ts"].astype(np.int64); t2 = V2["ts"].astype(np.int64); tsp = SP["ts"].astype(np.int64)
cut = int(t1[-1])
pins = json.load(open(PINS)); live = set(pins["symbols_live"])
F1 = {"cut_utc": iso(cut), "v1_axis": [iso(t1[0]), iso(t1[-1]), int(len(t1))], "v2ext_axis": [iso(t2[0]), iso(t2[-1]), int(len(t2))],
      "splice_axis": [iso(tsp[0]), iso(tsp[-1]), int(len(tsp))], "cols": {}}
nsp_pre = int((tsp <= cut).sum()); assert np.array_equal(tsp[:nsp_pre], t1)
for c in FUNDCOLS:
    a1 = V1[c]; a2 = V2[c]; asp = SP[c]
    s1 = {syms[j] for j in np.where(np.isfinite(a1).any(0))[0]}
    s2 = {syms[j] for j in np.where(np.isfinite(a2).any(0))[0]}
    F1["cols"][c] = {"v1_symbols_with_any_finite": len(s1), "v2ext_symbols_with_any_finite": len(s2),
                     "v1_set_equals_live_pins": s1 == live, "live_minus_v1": sorted(live - s1)[:20], "v1_minus_live": sorted(s1 - live)[:20],
                     "splice_rows_le_cut_bitwise_equal_v1": bool(np.array_equal(asp[:nsp_pre], a1, equal_nan=True))}
    del a1, a2, asp
log("F1", json.dumps({c: {k: v for k, v in F1["cols"][c].items() if not isinstance(v, list)} for c in FUNDCOLS}))
rec["F1"] = F1

# ───────────── F2 fea82 cols 80/81 on member pairs ─────────────
r2 = {int(t): j for j, t in enumerate(t2)}; rsp = {int(t): j for j, t in enumerate(tsp)}
V2E = V2["f_fund_ema"]; V2N = V2["f_fund_now"]; V2E1 = V2["f_fund_ema_v1"]; SPE = SP["f_fund_ema"]; SPN = SP["f_fund_now"]
rec["F2"] = {}
for tag, d in DLW.items():
    TG = np.load(f"{d}/data/dlw_targets.npz", allow_pickle=True); FE = np.load(f"{d}/data/dlw_fea82.npz", allow_pickle=True)
    E_ts = TG["E_ts"].astype(np.int64); MS = TG["members"]; names = [str(n) for n in FE["names"]]
    assert names[80] == "fund_ema" and names[81] == "fund_now", names[78:]
    rep = json.loads(str(FE["meta_json"])) if "meta_json" in FE.files else {}
    X = FE["X"]; x80 = X[:, 80].astype(np.float32); x81 = X[:, 81].astype(np.float32); del X
    pa = FE["pair_a"].astype(np.int64); ps = FE["pair_s"].astype(np.int64)
    by = {}; pc_bad = 0; pc_n = 0
    for i in range(len(E_ts)):
        a0, b0 = np.searchsorted(pa, [i, i + 1]); m = ps[a0:b0]
        assert np.array_equal(m, np.asarray(MS[i], np.int64)), (tag, i)
        y = yr(E_ts[i]); B = by.setdefault(y, {"anchors": 0, "pairs": 0, "anchors_no_v2ext_row": 0, "pairs_no_v2ext_row": 0,
                                               "c80_zero_v2ext_finite": 0, "c80_nonzero_v2ext_finite": 0, "c80_zero_v2ext_nan": 0, "v2ext_finite_c80": 0,
                                               "c81_zero_v2ext_finite": 0, "v2ext_finite_c81": 0})
        B["anchors"] += 1; B["pairs"] += len(m)
        js = rsp.get(int(E_ts[i]))
        # positive control: stored cols == float16(nan_to_num(splice value)) (0 when no splice row)
        e_sp = np.zeros(len(m), np.float32) if js is None else np.nan_to_num(SPE[js, m], nan=0.0).astype(np.float32)
        n_sp = np.zeros(len(m), np.float32) if js is None else np.nan_to_num(SPN[js, m], nan=0.0).astype(np.float32)
        pc_bad += int((x80[a0:b0] != e_sp.astype(np.float16).astype(np.float32)).sum() + (x81[a0:b0] != n_sp.astype(np.float16).astype(np.float32)).sum()); pc_n += 2 * len(m)
        j2 = r2.get(int(E_ts[i]))
        if j2 is None:
            B["anchors_no_v2ext_row"] += 1; B["pairs_no_v2ext_row"] += len(m); continue
        f80 = np.isfinite(V2E[j2, m]); f81 = np.isfinite(V2N[j2, m]); z80 = x80[a0:b0] == 0; z81 = x81[a0:b0] == 0
        B["v2ext_finite_c80"] += int(f80.sum()); B["c80_zero_v2ext_finite"] += int((z80 & f80).sum()); B["c80_nonzero_v2ext_finite"] += int((~z80 & f80).sum())
        B["c80_zero_v2ext_nan"] += int((z80 & ~f80).sum()); B["v2ext_finite_c81"] += int(f81.sum()); B["c81_zero_v2ext_finite"] += int((z81 & f81).sum())
    for y, B in by.items():
        B["share_c80_zero_among_v2ext_finite"] = round(B["c80_zero_v2ext_finite"] / max(B["v2ext_finite_c80"], 1), 4)
        B["share_c81_zero_among_v2ext_finite"] = round(B["c81_zero_v2ext_finite"] / max(B["v2ext_finite_c81"], 1), 4)
    rec["F2"][tag] = {"by_year": {str(k): v for k, v in sorted(by.items())}, "positive_control_stored_eq_f16_splice": {"cells": pc_n, "mismatch": pc_bad},
                      "builder_report_panel_sha256": rep.get("panel_sha256"), "n_pairs": int(len(pa))}
    log("F2", tag, json.dumps({k: (v["share_c80_zero_among_v2ext_finite"], v["pairs"]) for k, v in sorted(by.items())}), "pc mismatch", pc_bad)
    del x80, x81, pa, ps, TG, FE

# ───────────── F3 legs ZFD on DL member cells ─────────────
rec["F3"] = {}
for tag, (lp, d) in LEGS.items():
    L = np.load(lp, allow_pickle=True); TG = np.load(f"{d}/data/dlw_targets.npz", allow_pickle=True)
    LE = L["E_ts"].astype(np.int64); ZFD = L["ZFD"]; E_ts = TG["E_ts"].astype(np.int64); MS = TG["members"]
    assert np.array_equal(LE, E_ts), f"legs axis != targets axis ({tag})"
    by = {}
    for i in range(len(E_ts)):
        m = np.asarray(MS[i], np.int64); y = yr(E_ts[i])
        B = by.setdefault(y, {"cells": 0, "zfd_finite": 0, "zfd_nan_v2ext_v1_finite": 0, "v2ext_v1_finite": 0, "no_v2ext_row": 0})
        B["cells"] += len(m); fz = np.isfinite(ZFD[i, m]); B["zfd_finite"] += int(fz.sum())
        j2 = r2.get(int(E_ts[i]))
        if j2 is None:
            B["no_v2ext_row"] += len(m); continue
        f1 = np.isfinite(V2E1[j2, m]); B["v2ext_v1_finite"] += int(f1.sum()); B["zfd_nan_v2ext_v1_finite"] += int((~fz & f1).sum())
    for B in by.values():
        B["share_zfd_nan_among_v2ext_v1_finite"] = round(B["zfd_nan_v2ext_v1_finite"] / max(B["v2ext_v1_finite"], 1), 4)
    rec["F3"][tag] = {"by_year": {str(k): v for k, v in sorted(by.items())}}
    log("F3", tag, json.dumps({k: v["share_zfd_nan_among_v2ext_v1_finite"] for k, v in sorted(by.items())}))
    del L, ZFD

# ───────────── F4 v1 vs v2ext on common anchors <= cut ─────────────
com = np.intersect1d(t1, t2); i1 = np.searchsorted(t1, com); i2 = np.searchsorted(t2, com)
live_idx = np.array([j for j, s in enumerate(syms) if s in live])
rec["F4"] = {"common_anchors": int(len(com)), "range": [iso(com[0]), iso(com[-1])], "cols": {}}
for c in FUNDCOLS:
    a = V1[c][i1][:, live_idx].astype(np.float64); b = V2[c][i2][:, live_idx].astype(np.float64)
    fa, fb = np.isfinite(a), np.isfinite(b); both = fa & fb
    d = np.abs(a[both] - b[both]); scale = np.maximum(np.abs(a[both]), 1e-12)
    rec["F4"]["cols"][c] = {"cells_live450": int(a.size), "finite_v1": int(fa.sum()), "finite_v2ext": int(fb.sum()), "finite_both": int(both.sum()),
                            "v1_only": int((fa & ~fb).sum()), "v2ext_only": int((~fa & fb).sum()), "exact_equal_share": round(float((d == 0).mean()), 6),
                            "maxabs": float(d.max()), "median_abs": float(np.median(d)), "p99_rel": float(np.percentile(d / scale, 99)),
                            "corr": float(np.corrcoef(a[both], b[both])[0, 1])}
    log("F4", c, json.dumps(rec["F4"]["cols"][c]))
del V2E, V2N, V2E1, SPE, SPN

# ───────────── U1 non-crypto share of training members ─────────────
CLS = json.load(open(VENUE))
known = np.array([s in CLS for s in syms]); ut = [CLS[s].get("underlyingType") if s in CLS else None for s in syms]
nonc = np.array([(u is not None) and (u not in ("COIN", "INDEX")) for u in ut])
rec["U1"] = {"venue_file_sha256": rec["inputs"][VENUE], "axis_noncrypto_symbols": int(nonc.sum()), "axis_unknown_symbols": int((~known).sum()),
             "live_pins_class_counts": {}, "sets": {}}
for s in pins["symbols_live"]:
    u = CLS[s].get("underlyingType") if s in CLS else "UNKNOWN"
    rec["U1"]["live_pins_class_counts"][u] = rec["U1"]["live_pins_class_counts"].get(u, 0) + 1
for tag, (Ep, Mp) in {"king_v4_meta": ("/workspace/data/wide_fea_v4_meta.npz", "E_ts"), "dlw_v4raw_targets": ("/workspace/dlw_v4raw/data/dlw_targets.npz", "E_ts")}.items():
    Z = np.load(Ep, allow_pickle=True); E_ts = Z[Mp].astype(np.int64); MS = Z["members"]
    by = {}; seen = set()
    for i in range(len(E_ts)):
        m = np.asarray(MS[i], np.int64); y = yr(E_ts[i]); B = by.setdefault(y, {"pairs": 0, "noncrypto_pairs": 0, "unknown_pairs": 0, "anchors_with_noncrypto": 0})
        nc = nonc[m]; B["pairs"] += len(m); B["noncrypto_pairs"] += int(nc.sum()); B["unknown_pairs"] += int((~known[m]).sum()); B["anchors_with_noncrypto"] += int(nc.any())
        seen.update(syms[j] for j in m[nc])
    for B in by.values():
        B["noncrypto_share"] = round(B["noncrypto_pairs"] / max(B["pairs"], 1), 6)
    rec["U1"]["sets"][tag] = {"by_year": {str(k): v for k, v in sorted(by.items())}, "noncrypto_symbols_seen": sorted(seen)}
    log("U1", tag, json.dumps({k: v["noncrypto_share"] for k, v in sorted(by.items())}), "symbols", len(seen))

# ───────────── T1 king clock skew (score layer, no label) ─────────────
import lightgbm as lgb
from scipy.stats import spearmanr
MO = np.load(KFEA["v4"][1], allow_pickle=True); ME = np.load(KFEA["v4e"][1], allow_pickle=True)
EO = MO["E_ts"].astype(np.int64); EE = ME["E_ts"].astype(np.int64); MMO = MO["members"]; MME = ME["members"]
assert [str(n) for n in MO["names"]] == [str(n) for n in ME["names"]]
names = [str(n) for n in MO["names"]]
FO = np.load(KFEA["v4"][0], mmap_mode="r"); FEe = np.load(KFEA["v4e"][0], mmap_mode="r")
assert FO.shape[0] == len(EO) and FEe.shape[0] == len(EE)
re_ = {int(t): i for i, t in enumerate(EE)}
comA = [(i, re_[int(t)]) for i, t in enumerate(EO) if int(t) in re_]
memdiff = {"common_anchors": len(comA), "anchors_member_set_differs": 0, "pairs_only_old": 0, "pairs_only_new": 0,
           "new_minus_old_anchors": [iso(t) for t in sorted(set(EE.tolist()) - set(EO.tolist()))][:10],
           "old_minus_new_anchors": [iso(t) for t in sorted(set(EO.tolist()) - set(EE.tolist()))][:10]}
for io, ie in comA:
    a = set(np.asarray(MMO[io]).tolist()); b = set(np.asarray(MME[ie]).tolist())
    if a != b:
        memdiff["anchors_member_set_differs"] += 1; memdiff["pairs_only_old"] += len(a - b); memdiff["pairs_only_new"] += len(b - a)
rec["T1"] = {"member_sets": memdiff, "boosters": {}}
log("T1 members", json.dumps({k: v for k, v in memdiff.items() if not isinstance(v, list)}))
T24 = calendar.timegm((2024, 1, 1, 0, 0, 0))
for btag, (bp, cfgp) in BOOST.items():
    cfg = json.load(open(cfgp)); keep = [int(k) for k in cfg["keep_idx"]]
    assert [names[k] for k in keep] == list(cfg["keep_names"]), btag
    bst = lgb.Booster(model_file=bp)
    per = {}
    sel = [(io, ie) for io, ie in comA if EO[io] >= T24]
    for k0 in range(0, len(sel), 400):
        chunk = sel[k0:k0 + 400]; rowsO, rowsE, spans = [], [], []
        for io, ie in chunk:
            m = np.intersect1d(np.asarray(MMO[io], np.int64), np.asarray(MME[ie], np.int64))
            rowsO.append(np.asarray(FO[io][m][:, keep], np.float32)); rowsE.append(np.asarray(FEe[ie][m][:, keep], np.float32)); spans.append(len(m))
        pO = bst.predict(np.concatenate(rowsO), num_threads=4); pE = bst.predict(np.concatenate(rowsE), num_threads=4)
        off = 0
        for (io, ie), n in zip(chunk, spans):
            a = pO[off:off + n]; b = pE[off:off + n]; off += n
            q = max(1, int(round(0.1 * n)))
            topa = set(np.argsort(-a)[:q]); topb = set(np.argsort(-b)[:q]); bota = set(np.argsort(a)[:q]); botb = set(np.argsort(b)[:q])
            y = str(yr(EO[io])); P = per.setdefault(y, {"sp": [], "top": [], "bot": [], "maxd": [], "n": []})
            P["sp"].append(float(spearmanr(a, b).correlation)); P["top"].append(len(topa & topb) / q); P["bot"].append(len(bota & botb) / q)
            P["maxd"].append(float(np.max(np.abs(a - b)) / (np.std(a) + 1e-12))); P["n"].append(n)
    out = {}
    allv = {k: [] for k in ("sp", "top", "bot", "maxd")}
    for y, P in sorted(per.items()):
        out[y] = {"anchors": len(P["sp"]), "mean_members": round(float(np.mean(P["n"])), 1)}
        for k in ("sp", "top", "bot", "maxd"):
            v = np.array(P[k]); allv[k].extend(P[k])
            out[y][k] = {"min": round(float(v.min()), 4), "p5": round(float(np.percentile(v, 5)), 4), "p25": round(float(np.percentile(v, 25)), 4),
                         "median": round(float(np.median(v)), 4), "p75": round(float(np.percentile(v, 75)), 4), "p95": round(float(np.percentile(v, 95)), 4), "max": round(float(v.max()), 4)}
    out["all"] = {k: {"median": round(float(np.median(v)), 4), "p5": round(float(np.percentile(v, 5)), 4), "min": round(float(np.min(v)), 4)} for k, v in allv.items()}
    out["booster_sha256"] = rec["inputs"][bp]
    rec["T1"]["boosters"][btag] = out
    log("T1", btag, json.dumps(out["all"]))
rec["legend"] = {"sp": "per-anchor Spearman(pred on [E-w,E-1] features, pred on [E-w+1,E] features), common members",
                 "top/bot": "share of the top/bottom 10% (by each scoring) that is shared", "maxd": "max|dpred| / sd(pred old clock) per anchor"}
rec["utc_end"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); rec["wall_s"] = round(time.time() - T0, 1)
json.dump(rec, open(OUT, "w"), indent=1)
print(f"FM_FACTS_DATA_DONE out={OUT} wall={rec['wall_s']}s", flush=True)
