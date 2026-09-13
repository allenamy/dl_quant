#!/usr/bin/env python3
"""ad_cache_members.py -- AUDIT_DATA 2026-09-13, device C (pod2, CPU, READ-ONLY). One load of the canonical 5m cache, five checks.

C1  ret5 clip bound vs raw patches: every cache cell whose ret5 sits exactly on the float16 +-0.30 bound, vs raw_patch.npz (holefix2)
    and, for the x0910 extension, the tail rows (> 490,752) vs raw_patch_x0910.npz (tail read by streaming the npy inside the npz,
    prefix bytes discarded, so only 2,880 rows are held). A bound cell absent from the patch = a place where RAW targets silently
    fall back to the clipped value (E-0908-B).
C2  survivorship of the 829-symbol axis: first / last finite ret5 bar per symbol (delisted names present? names with no data?).
C3  forward-looking member predicates. Re-derive the member lists of
      K: king feature meta   (pod_fea_ext_clamp.py L24-L41: covr/v7/qvm over 2016 rows, ok &= isfinite(y4 rows [E, E+47]))
      D: DL targets          (pod_dlw_targets_raw.py L86-L113: rows [max(E-2016,0), E), ok &= y4s finite rows [E+1, E+48])
    with the builders' own cumulative-sum arithmetic (float64 cumsum of float32 values, numpy negative-index semantics kept),
    POSITIVE CONTROL = bitwise equality of axis and every member list with the stored files (wide_fea_v4_meta.npz, dlw_v4raw
    dlw_targets.npz) -- if it fails, no C3/C4 number is read. Then drop ONLY the forward predicate and count, per year:
    pairs removed because the forward 4h return was not finite, pairs back-filled into the top-400, anchors that exist only without it,
    whether the removed name ever trades again (permanent end vs gap), and how many removed pairs sit inside the CRYPTO mask.
C4  the archived reference book A0 (r3k A0_PWR230k_s{42,2027}; its config MEMBERS_TOPN=829 so its universe is every name with finite qvk,
    and its eligibility is the replay's own ok = isfinite(accounting y4 at E)): positions held at E-4h in names whose (E, E+4h] accounting
    return is NOT finite -- the replay forces them to 0 at E because their future data stops, and books a 0 return for them.
C5  OOF availability masks: king OOF (SLOW_v4, SLOW_v3_on_v4axis) and F10 OOF (f10_v4RAW, f10_A0) finite cells vs member lists and vs
    forward-return finiteness.
C6  universe class inside TRAINING members: (anchor, member) pairs whose venue underlyingType is not COIN/INDEX (tokenized stocks,
    commodities ...) per year, for K and D (venue_class_20260908.json = git multi_asset/exports/research/retrain_2026-09/universe_crypto_2026-09-08/).
Usage: python3 ad_cache_members.py <out_receipt.json> <venue_class_json>
"""
import os, sys, json, time, hashlib, zipfile, calendar
import numpy as np

ENV_WHITELIST = set()
os.nice(19)
OUT, VENUE = sys.argv[1], sys.argv[2]
W = "/workspace"
CACHE = f"{W}/data/dlnative_5m_wide829_f16_holefix2.npz"; CACHE_X = f"{W}/data/dlnative_5m_wide829_f16_holefix2_x0910.npz"
PATCH = f"{W}/review_scratch/raw_patch.npz"; PATCH_X = f"{W}/uplift_2026-09-11/r6/out/raw_patch_x0910.npz"
KMETA = f"{W}/data/wide_fea_v4_meta.npz"; DTG = f"{W}/dlw_v4raw/data/dlw_targets.npz"; AMETA = f"{W}/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"
UMASK = f"{W}/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"
A0 = {s: f"{W}/uplift_2026-09-11/r3k/arms/A0_PWR230k_s{s}.npz" for s in (42, 2027)}
OOF_K = {"SLOW_v4": f"{W}/review_scratch/king_v4/SLOW_v4.npy", "SLOW_v3_on_v4axis": f"{W}/review_scratch/king_v4/SLOW_v3_on_v4axis.npy"}
OOF_D = {f"f10_{a}_s{s}": f"{W}/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_{a}_s{s}.npy" for a in ("v4RAW", "A0") for s in (42, 2027)}

T0 = time.time()
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def yr(t): return time.gmtime(int(t)).tm_year
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)

assert not (ENV_WHITELIST - set(os.environ))
rec = {"device": "ad_cache_members.py", "self_sha256": sha(os.path.abspath(__file__)), "numpy": np.__version__,
       "inputs": {p: sha(p) for p in [CACHE, PATCH, PATCH_X, KMETA, DTG, AMETA, UMASK, VENUE] + list(A0.values()) + list(OOF_K.values()) + list(OOF_D.values())}}
log("input shas done")

# ---------------- load cache once ----------------
Z = np.load(CACHE, allow_pickle=True)
CTS = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; NW = len(syms); ch = [str(c) for c in Z["ch"]]
assert ch[0] == "ret5" and ch[3] == "log_qv", ch
DATA = Z["data"]; TT = DATA.shape[0]
R5 = np.ascontiguousarray(DATA[:, :, 0]); Q3 = np.ascontiguousarray(DATA[:, :, 3]); del DATA, Z
log("cache loaded", TT, NW, "ts", utc(CTS[0]), utc(CTS[-1]))

# ---------------- C1 clip bound vs patch ----------------
B16 = np.float16(0.3)
cand = (R5 == B16) | (R5 == -B16); beyond = int((np.abs(R5.astype(np.float32)) > np.float32(B16)).sum())
cr, cc = np.where(cand)
P = np.load(PATCH, allow_pickle=True); pset = set(zip(P["row"].astype(np.int64).tolist(), P["col"].astype(np.int64).tolist()))
cset = set(zip(cr.tolist(), cc.tolist()))
unpatched = sorted(cset - pset)
c1 = {"bound_value": float(B16), "bound_cells": int(len(cset)), "cells_beyond_bound": beyond, "patch_rows": int(len(P["row"])),
      "bound_cells_in_patch": int(len(cset & pset)), "bound_cells_NOT_in_patch": int(len(unpatched)), "patch_cells_not_on_bound": int(len(pset - cset)),
      "not_in_patch_list": [{"ts": utc(CTS[r]), "symbol": syms[c], "clip16": float(R5[r, c])} for r, c in unpatched[:50]],
      "bound_cells_by_year": {str(y): int(sum(1 for r, _ in cset if yr(CTS[r]) == y)) for y in range(2022, 2027)}}
# x0910 tail by streaming
def stream_tail(path, first_row):
    zf = zipfile.ZipFile(path)
    with zf.open("ts.npy") as fh: pass
    ts = np.load(path, allow_pickle=True)["ts"].astype(np.int64); sy = [str(s) for s in np.load(path, allow_pickle=True)["symbols"]]
    with zf.open("data.npy") as fh:
        ver = np.lib.format.read_magic(fh)
        shape, fort, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
        assert not fort and dt == np.float16, (fort, dt)
        rowb = int(np.prod(shape[1:])) * dt.itemsize; skip = first_row * rowb
        while skip > 0:
            n = min(skip, 1 << 28); got = fh.read(n); assert len(got) == n; skip -= n
        tail = np.frombuffer(fh.read((shape[0] - first_row) * rowb), dtype=np.float16).reshape((shape[0] - first_row,) + tuple(shape[1:]))
    return ts, sy, shape, tail
tsx, syx, shx, tailx = stream_tail(CACHE_X, TT)
assert syx == syms and np.array_equal(tsx[:TT], CTS), "x0910 prefix axis differs from holefix2"
t0r = tailx[:, :, 0]; xr, xc = np.where((t0r == B16) | (t0r == -B16)); xset = set(zip((xr + TT).tolist(), xc.tolist()))
PX = np.load(PATCH_X, allow_pickle=True); pxr = PX["row"].astype(np.int64); pxc = PX["col"].astype(np.int64)
prefix_equal = bool(np.array_equal(pxr[:len(P["row"])], P["row"].astype(np.int64)) and np.array_equal(pxc[:len(P["row"])], P["col"].astype(np.int64))
                    and np.array_equal(PX["raw32"][:len(P["row"])], P["raw32"]))
pxtail = set(zip(pxr[pxr >= TT].tolist(), pxc[pxr >= TT].tolist()))
c1["x0910"] = {"cache_shape": list(shx), "tail_rows": int(shx[0] - TT), "tail_first": utc(tsx[TT]), "tail_last": utc(tsx[-1]),
               "tail_bound_cells": int(len(xset)), "patch_x0910_rows": int(len(pxr)), "patch_x0910_prefix_equals_incumbent_patch": prefix_equal,
               "tail_bound_cells_in_patch": int(len(xset & pxtail)), "tail_bound_cells_NOT_in_patch": int(len(xset - pxtail)),
               "tail_bound_list": [{"ts": utc(tsx[r]), "symbol": syms[c], "in_patch": (r, c) in pxtail} for r, c in sorted(xset)]}
del tailx, t0r
rec["C1_clip_bound_vs_patch"] = c1; log("C1", json.dumps({k: v for k, v in c1.items() if k not in ("not_in_patch_list", "x0910")}), "x0910 tail", len(xset), len(xset & pxtail))

# ---------------- C2 survivorship ----------------
fin = np.isfinite(R5)
has = fin.any(0); first = np.argmax(fin, 0); last = TT - 1 - np.argmax(fin[::-1], 0)
aug1 = calendar.timegm((2026, 8, 1, 0, 0, 0))
ended = [(syms[j], utc(CTS[last[j]])) for j in range(NW) if has[j] and CTS[last[j]] < aug1]
rec["C2_axis_survivorship"] = {"n_symbols": NW, "no_finite_bar": [syms[j] for j in range(NW) if not has[j]],
                               "last_bar_before_2026-08-01_n": len(ended), "last_bar_before_2026-08-01_by_year": {str(y): sum(1 for _, d in ended if d.startswith(str(y))) for y in range(2022, 2027)},
                               "last_bar_before_2026-08-01_head": sorted(ended, key=lambda x: x[1])[:40],
                               "first_bar_after_2022-01-02_n": int(sum(1 for j in range(NW) if has[j] and CTS[first[j]] > calendar.timegm((2022, 1, 2, 0, 0, 0))))}
log("C2 ended", len(ended))

# ---------------- C3 member predicates ----------------
def cumsum_rows(vals_f64_or_int, idx_sets, dtype):
    out = np.empty((TT + 1, NW), dtype); out[0] = 0
    np.cumsum(vals_f64_or_int, axis=0, dtype=dtype, out=out[1:])
    got = {k: out[v] for k, v in idx_sets.items()}; del out
    return got
grid = np.where(CTS % 14400 == 0)[0]
EK = grid[(grid >= 576) & (grid + 48 <= TT)]            # king: E + 48 <= TT
ED = grid[(grid >= 576) & (grid + 48 <= TT - 1)]        # DL:   E + FWD <= TT - 1
SD = np.maximum(ED - 2016, 0)
IDX = {"KE": EK, "KEm": EK - 2016, "KEc": np.maximum(EK - 2016, 0), "KE48": EK + 48, "DE": ED, "DS": SD, "DE1": ED + 1, "DE49": ED + 49}
r5f = np.where(fin, R5.astype(np.float32), np.float32(0))
C_ret = cumsum_rows(r5f, IDX, np.float64); log("cumsum ret")
C_cnt = cumsum_rows(fin, IDX, np.int32); log("cumsum cnt")
C_r2 = cumsum_rows(r5f.astype(np.float64) ** 2, IDX, np.float64); del r5f; log("cumsum r2")
finq = np.isfinite(Q3); q3f = np.where(finq, Q3.astype(np.float32), np.float32(0))
C_q = cumsum_rows(q3f, IDX, np.float64); del q3f
C_qc = cumsum_rows(finq, IDX, np.int32); del finq; log("cumsum qv")
# king arithmetic (pod_fea_ext_clamp.py L27-L34; CS arrays of length TT+1, python/numpy negative-index semantics for E-2016)
n7 = np.maximum(C_qc["KE"] - C_qc["KEm"], 1)
covrK = (C_cnt["KE"] - C_cnt["KEc"]) / 2016
qvmK = (C_q["KE"] - C_q["KEm"]) / n7
m7 = (C_ret["KE"] - C_ret["KEm"])
v7 = np.sqrt(np.maximum((C_r2["KE"] - C_r2["KEm"]) / n7 - (m7 / n7) ** 2, 0))
y4nK = C_cnt["KE48"] - C_cnt["KE"]; y4K = (C_ret["KE48"] - C_ret["KE"]).astype(np.float32); y4K[y4nK < 46] = np.nan
# DL arithmetic (pod_dlw_targets_raw.py L88-L101)
nfin = np.maximum(C_cnt["DE"] - C_cnt["DS"], 1)
covrD = (C_cnt["DE"] - C_cnt["DS"]) / np.maximum(ED - SD, 1)[:, None]
qvmD = (C_q["DE"] - C_q["DS"]) / nfin
rsD = C_ret["DE"] - C_ret["DS"]
vstd = np.sqrt(np.maximum((C_r2["DE"] - C_r2["DS"]) / nfin - (rsD / nfin) ** 2, 0))
y4nD = C_cnt["DE49"] - C_cnt["DE1"]; finD = y4nD >= 46
del C_ret, C_r2, C_q, C_qc
def members(covr, vol, finy, qvm, ntop=400, mn=50, vol_th=1e-4):
    M, keep = [], []
    for i in range(covr.shape[0]):
        ok = (covr[i] >= 0.95) & (vol[i] >= vol_th)
        if finy is not None: ok = ok & finy[i]
        m = np.where(ok)[0]
        if len(m) > ntop: m = np.sort(m[np.argsort(-qvm[i, m])[:ntop]])
        if len(m) >= mn: M.append(m); keep.append(i)
    return M, np.array(keep, np.int64)
MK, kK = members(covrK, v7, np.isfinite(y4K), qvmK); MK0, kK0 = members(covrK, v7, None, qvmK)
MD, kD = members(covrD, vstd, finD, qvmD); MD0, kD0 = members(covrD, vstd, None, qvmD)
log("members derived", len(kK), len(kK0), len(kD), len(kD0))
KM = np.load(KMETA, allow_pickle=True); DT = np.load(DTG, allow_pickle=True)
kE = KM["E_ts"].astype(np.int64); kMem = KM["members"]; kY4 = KM["y4"]
dE = DT["E_ts"].astype(np.int64); dMem = DT["members"]; dY4s = DT["y4s"]
pcK = {"axis_equal": bool(np.array_equal(CTS[EK[kK]], kE)), "n_derived": int(len(kK)), "n_file": int(len(kE))}
if pcK["axis_equal"]:
    neq = [i for i in range(len(kE)) if not np.array_equal(MK[i], np.asarray(kMem[i], np.int64))]
    y4d = np.abs(y4K[kK] - kY4.astype(np.float32)); fp = np.isfinite(y4K[kK]) == np.isfinite(kY4)
    pcK.update({"member_lists_unequal": len(neq), "unequal_first": [utc(kE[i]) for i in neq[:10]], "y4_finite_pattern_equal": bool(fp.all()),
                "y4_maxabs_window_rows_E_to_E+47": float(np.nanmax(np.where(np.isfinite(y4d), y4d, np.nan)))})
pcD = {"axis_equal": bool(np.array_equal(CTS[ED[kD]], dE)), "n_derived": int(len(kD)), "n_file": int(len(dE))}
if pcD["axis_equal"]:
    neq = [i for i in range(len(dE)) if not np.array_equal(MD[i], np.asarray(dMem[i], np.int64))]
    pcD.update({"member_lists_unequal": len(neq), "unequal_first": [utc(dE[i]) for i in neq[:10]],
                "y4s_finite_pattern_equal_rule_count_ge_46": bool(np.array_equal(finD[kD], np.isfinite(dY4s)))})
PC = bool(pcK["axis_equal"] and pcK.get("member_lists_unequal", 1) == 0 and pcD["axis_equal"] and pcD.get("member_lists_unequal", 1) == 0)
rec["C3_positive_control"] = {"king": pcK, "dl": pcD, "PASS": PC}
log("PC", json.dumps(rec["C3_positive_control"]))

UZ = np.load(UMASK, allow_pickle=True); UTS = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"]); assert [str(s) for s in UZ["symbols"]] == syms
permanent_end = np.array([CTS[last[j]] if has[j] else -1 for j in range(NW)])
def diff_stats(E_rows, M_pred, k_pred, M_np, k_np, finy_rows, y4n_rows, tag):
    ts_pred = CTS[E_rows[k_pred]]; ts_np = CTS[E_rows[k_np]]; pos_pred = {int(t): i for i, t in enumerate(ts_pred)}
    by = {}; removed = {}
    for ii, i in enumerate(k_np):
        t = int(CTS[E_rows[i]]); y = str(yr(t)); b = by.setdefault(y, {"anchors_no_predicate": 0, "anchors_with_predicate": 0, "anchors_only_without_predicate": 0,
                                                                       "pairs_no_predicate": 0, "pairs_removed_forward_nonfinite": 0, "pairs_backfilled": 0,
                                                                       "removed_y4n_zero": 0, "removed_y4n_partial": 0, "removed_name_never_trades_again": 0,
                                                                       "removed_inside_crypto_mask": 0})
        b["anchors_no_predicate"] += 1; m0 = M_np[ii]; b["pairs_no_predicate"] += int(len(m0))
        rem = m0[~finy_rows[i][m0]]
        b["pairs_removed_forward_nonfinite"] += int(len(rem))
        j = pos_pred.get(t)
        if j is None: b["anchors_only_without_predicate"] += 1
        else:
            b["anchors_with_predicate"] += 1; b["pairs_backfilled"] += int(len(np.setdiff1d(M_pred[j], m0)))
        if len(rem):
            yn = y4n_rows[i][rem]; b["removed_y4n_zero"] += int((yn == 0).sum()); b["removed_y4n_partial"] += int(((yn > 0) & (yn < 46)).sum())
            b["removed_name_never_trades_again"] += int((permanent_end[rem] <= t + 48 * 300).sum())
            ur = UTS.get(t)
            if ur is not None: b["removed_inside_crypto_mask"] += int(UM[ur, rem].sum())
            removed[t] = rem
    for y, b in by.items(): b["share_removed_of_no_predicate_pairs"] = round(b["pairs_removed_forward_nonfinite"] / max(b["pairs_no_predicate"], 1), 6)
    return by, removed
if PC:
    finK_rows = np.isfinite(y4K); byK, remK = diff_stats(EK, MK, kK, MK0, kK0, finK_rows, y4nK, "king")
    byD, remD = diff_stats(ED, MD, kD, MD0, kD0, finD, y4nD, "dl")
    rec["C3_forward_predicate"] = {"king_meta_rule": byK, "dl_targets_rule": byD,
                                   "note": "removed = in the top-400 without the predicate but excluded because < 46 finite bars in the forward 4h window; backfilled = entered the top-400 because of the vacancy"}
    log("C3 king", json.dumps({y: b["pairs_removed_forward_nonfinite"] for y, b in byK.items()}))
    # ---------------- C4 A0: positions the replay dumps because the NEXT 4h accounting return is not finite ----------------
    # w10_sleeve (A0 config MEMBERS_TOPN=829, R18_ELIG=0): ok = isfinite(y4[i, m]) with y4 = meta_newprod_v4 (RAW accounting), sel = ok & liquid,
    # names outside sel are forced to 0 at anchor i (`_nonsel`), and pnl uses nan_to_num(y4) = 0. So a name held at i-1 whose (E_i, E_i+4h] return is
    # not finite is exited at E_i BECAUSE its future data stops; the loss of holding it through a halt/delisting never enters any replay number.
    AM = np.load(AMETA, allow_pickle=True); aE = AM["E_ts"].astype(np.int64); aY4 = AM["y4"]; apos = {int(t): i for i, t in enumerate(aE)}
    c4 = {}
    for s, pth in A0.items():
        Az = np.load(pth, allow_pickle=True); cols = [str(c) for c in Az["cols"]]; Wb = Az["W"].astype(np.float64); R = Az["rec"]
        cfg = json.loads(str(Az["config_json"]))
        ats = R[:, cols.index("ts")].astype(np.int64); posA = {int(t): k for k, t in enumerate(ats)}
        by = {}; examples = []
        for k in range(1, len(ats)):
            t = int(ats[k]); kp = posA.get(t - 14400); ia = apos.get(t)
            if kp is None or ia is None: continue
            held = np.abs(Wb[kp]) > 1e-12
            dump = held & ~np.isfinite(aY4[ia])
            y = str(yr(t)); b = by.setdefault(y, {"anchors": 0, "anchors_with_dump": 0, "dumped_pairs": 0, "dumped_abs_weight_prev": 0.0, "dumped_pairs_name_never_trades_again": 0,
                                                 "dumped_abs_weight_never_trades_again": 0.0, "abs_weight_at_anchor_on_dumped": 0.0, "gross_prev_sum": 0.0})
            b["anchors"] += 1; b["gross_prev_sum"] += float(np.abs(Wb[kp]).sum())
            if dump.any():
                idx = np.where(dump)[0]; wp = np.abs(Wb[kp, idx]); perm = permanent_end[idx] <= t + 48 * 300
                b["anchors_with_dump"] += 1; b["dumped_pairs"] += int(len(idx)); b["dumped_abs_weight_prev"] += float(wp.sum())
                b["dumped_pairs_name_never_trades_again"] += int(perm.sum()); b["dumped_abs_weight_never_trades_again"] += float(wp[perm].sum())
                b["abs_weight_at_anchor_on_dumped"] += float(np.abs(Wb[k, idx]).sum())
                if len(examples) < 25:
                    for n in idx[np.argsort(-wp)][:2]: examples.append({"anchor": utc(t), "symbol": syms[n], "w_prev": float(Wb[kp, n]), "never_trades_again": bool(permanent_end[n] <= t + 48 * 300)})
        for b in by.values(): b["dumped_share_of_gross_prev_sum"] = b["dumped_abs_weight_prev"] / max(b["gross_prev_sum"], 1e-12)
        c4[s] = {"config": {k: cfg.get(k) for k in ("MEMBERS_TOPN", "UMASK_SCOPE", "SLOW_NPY", "PHI", "CAL", "LEGS", "FTRIM")}, "R18_ELIG_in_config": cfg.get("R18_ELIG"),
                 "axis_n": int(len(ats)), "axis_first": utc(ats[0]), "axis_last": utc(ats[-1]), "by_year": by, "largest_examples": examples}
    rec["C4_A0_forward_nonfinite_exits"] = c4
    log("C4 done")
    # ---------------- C5 OOF masks ----------------
    c5 = {}
    kpos = {int(t): i for i, t in enumerate(kE)}
    for nm, p in OOF_K.items():
        A = np.load(p); assert A.shape == (len(kE), NW), (nm, A.shape)
        fa = np.isfinite(A); rows = np.where(fa.any(1))[0]
        outside = 0; members_without = 0; fwd_nonfinite_pred = 0
        for i in rows:
            mset = np.zeros(NW, bool); mset[np.asarray(kMem[i], np.int64)] = True
            outside += int((fa[i] & ~mset).sum()); members_without += int((mset & ~fa[i]).sum()); fwd_nonfinite_pred += int((fa[i] & ~np.isfinite(kY4[i])).sum())
        c5[nm] = {"axis": "king meta (10182)", "anchors_with_any_pred": int(len(rows)), "first_pred_anchor": (utc(kE[rows[0]]) if len(rows) else None),
                  "pred_cells_outside_members": outside, "member_cells_without_pred_on_pred_anchors": members_without,
                  "pred_cells_with_nonfinite_forward_y4": fwd_nonfinite_pred}
    for nm, p in OOF_D.items():
        A = np.load(p); assert A.shape == (len(dE), NW), (nm, A.shape)
        fa = np.isfinite(A); rows = np.where(fa.any(1))[0]
        outside = 0; members_without = 0; fwd_nonfinite_pred = 0
        for i in rows:
            mset = np.zeros(NW, bool); mset[np.asarray(dMem[i], np.int64)] = True
            outside += int((fa[i] & ~mset).sum()); members_without += int((mset & ~fa[i]).sum()); fwd_nonfinite_pred += int((fa[i] & ~np.isfinite(dY4s[i])).sum())
        c5[nm] = {"axis": "dlw_v4raw targets (10212)", "anchors_with_any_pred": int(len(rows)), "first_pred_anchor": (utc(dE[rows[0]]) if len(rows) else None),
                  "last_pred_anchor": (utc(dE[rows[-1]]) if len(rows) else None), "pred_cells_outside_dlw_v4raw_members": outside,
                  "dlw_v4raw_member_cells_without_pred_on_pred_anchors": members_without, "pred_cells_with_nonfinite_forward_y4s": fwd_nonfinite_pred}
    rec["C5_oof_masks"] = c5; log("C5", json.dumps(c5))
    # ---------------- C6 universe class inside training members ----------------
    VC = json.load(open(VENUE)); cls = {}
    for s in syms:
        v = VC.get(s); u = (v.get("underlyingType") if isinstance(v, dict) else v) if v is not None else None
        cls[s] = "UNKNOWN" if u is None else ("CRYPTO" if u in ("COIN", "INDEX") else "NONCRYPTO:" + str(u))
    ncr = np.array([cls[s].startswith("NONCRYPTO") for s in syms]); unk = np.array([cls[s] == "UNKNOWN" for s in syms])
    def cls_stats(E_ts, MEM):
        by = {}
        for i, t in enumerate(E_ts):
            y = str(yr(t)); m = np.asarray(MEM[i], np.int64); b = by.setdefault(y, {"pairs": 0, "noncrypto_pairs": 0, "unknown_class_pairs": 0, "anchors_with_noncrypto": 0})
            b["pairs"] += int(len(m)); nn = int(ncr[m].sum()); b["noncrypto_pairs"] += nn; b["unknown_class_pairs"] += int(unk[m].sum()); b["anchors_with_noncrypto"] += int(nn > 0)
        for b in by.values(): b["noncrypto_share"] = round(b["noncrypto_pairs"] / max(b["pairs"], 1), 6)
        return by
    rec["C6_universe_class_in_training_members"] = {"venue_class_symbols": len(VC), "noncrypto_symbols_on_axis": int(ncr.sum()), "unknown_symbols_on_axis": int(unk.sum()),
                                                     "noncrypto_examples": [s for s in syms if cls[s].startswith("NONCRYPTO")][:30],
                                                     "king_meta_members": cls_stats(kE, kMem), "dl_targets_members": cls_stats(dE, dMem)}
    log("C6 done")
else:
    rec["C3_forward_predicate"] = "NOT READ: positive control failed"
rec["elapsed_s"] = round(time.time() - T0, 1)
json.dump(rec, open(OUT, "w"), indent=1)
print("AD_CACHE_MEMBERS_DONE PC=%s out=%s" % (PC, OUT), flush=True)
