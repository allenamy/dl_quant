#!/usr/bin/env python3
"""FP2 member-rule check (independent review round 2, R09 — 2026-09-17): the masked builds must contain EXACTLY the members the builders' rule
selects, not merely "a subset whose removals are mask-False and whose additions sit at truncated rows". That weaker rule (AMENDMENT 8 + F06)
passes a masked build that misses a replacement name (399), swaps it for a lower-ranked one (400), adds an extra one (401), or drops an anchor
whose masked pool still has ≥ MIN_MEM names (the reviewer's 79-eligible case).

Method — recompute from the CACHE, per builder, with that builder's own formulas (pod_fea_ext_clamp_v2.py L52-66; pod_dlw_targets_raw_v2.py
L128-158), then:
  (1) the UNMASKED replica must reproduce the control build EXACTLY (anchor axis + members per anchor) — this binds the replica to the real
      builder on every anchor (a replica that drifted from the builder cannot PASS here);
  (2) the MASKED replica (rule ∧ mask, then top-NTOP by qvm, keep iff ≥ MIN_MEM) must equal the masked build EXACTLY — axis and members.
Any mismatch ⇒ FAIL with the first rows named. Both builders (king meta; DL targets) are checked with their own rule (they differ: the king rule
normalises qvm/vol by the log_qv finite count and takes y4 on rows [E, E+48); the targets rule uses the ret5 finite count, y4s = expm1(Σ log1p)
on rows [E+1, E+48] with the raw patch applied to the target channel).
env: CACHE MEMBER_MASK CONTROL_KING_META MASKED_KING_META CONTROL_DL_TARGETS MASKED_DL_TARGETS OUT_JSON [RAW_PATCH] [SKIP_KING=1|SKIP_DL=1]
Constants are the builders' (NTOP 400, MIN_MEM 50, W 576, FWD 48, TRAIL 2016, MIN_FIN 46, COVR 0.95, VOL 1e-4)."""
import hashlib, json, os, sys, time
import numpy as np
NTOP, MIN_MEM, W, FWD, TRAIL, MIN_FIN, COVR_MIN, VOL_MIN = 400, 50, 576, 48, 2016, 46, 0.95, 1e-4
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def log(*a): print("[mrc]", *a, flush=True)

def cumsums(CD):
    """the builders' cumulative sums, materialised once: (finite count of ret5, Σret5, Σret5², Σlog_qv, count log_qv finite)"""
    r5 = CD[:, :, 0].astype(np.float32); fin = np.isfinite(r5); r5z = np.where(fin, r5, 0).astype(np.float32)
    NW = r5.shape[1]; z1 = np.zeros((1, NW))
    CS_f = np.concatenate([z1.astype(np.int32), np.cumsum(fin, 0, dtype=np.int32)])
    CS_r = np.concatenate([z1, np.cumsum(r5z, 0, dtype=np.float64)])
    CS_r2 = np.concatenate([z1, np.cumsum(r5z.astype(np.float64) ** 2, 0)])
    qv = CD[:, :, 3].astype(np.float32); qfin = np.isfinite(qv); qvz = np.where(qfin, qv, 0).astype(np.float32)
    CS_q = np.concatenate([z1, np.cumsum(qvz, 0, dtype=np.float64)])
    CS_qf = np.concatenate([z1.astype(np.int32), np.cumsum(qfin, 0, dtype=np.int32)])
    return CS_f, CS_r, CS_r2, CS_q, CS_qf, r5z, fin

def select(ok_rows, qvm_rows, E):
    """the shared tail of both rules: top-NTOP by qvm among ok, keep iff ≥ MIN_MEM. Returns (kept anchor rows, members list)."""
    MS, keep = [], []
    for i in range(len(E)):
        m = np.where(ok_rows[i])[0]
        if len(m) > NTOP: m = np.sort(m[np.argsort(-qvm_rows[i, m])[:NTOP]])
        if len(m) >= MIN_MEM: MS.append(m); keep.append(i)
    return np.array(keep, dtype=np.int64), MS

def king_rule(CS, CTS, TT):
    """pod_fea_ext_clamp_v2.py L52-66 verbatim in meaning (S7 clamp; n7 = log_qv finite count; covr on ret5 count; y4 rows [E, E+48))"""
    CS_f, CS_r, CS_r2, CS_q, CS_qf = CS
    grid = np.where(CTS % 14400 == 0)[0]; grid = grid[(grid >= 576) & (grid + 48 <= TT)]; E = grid
    S7 = np.maximum(E - 2016, 0); n7 = np.maximum(CS_qf[E] - CS_qf[S7], 1)
    covr = (CS_f[E] - CS_f[S7]) / np.maximum(E - S7, 1)[:, None]
    qvm = (CS_q[E] - CS_q[S7]) / n7
    m7 = CS_r[E] - CS_r[S7]; v7 = np.sqrt(np.maximum((CS_r2[E] - CS_r2[S7]) / n7 - (m7 / n7) ** 2, 0))
    y4n = CS_f[E + 48] - CS_f[E]; y4 = (CS_r[E + 48] - CS_r[E]).astype(np.float32); y4[y4n < 46] = np.nan
    ok = (covr >= COVR_MIN) & (v7 >= VOL_MIN) & np.isfinite(y4)
    return E, ok, qvm

def targets_rule(CS, CTS, TT, CS_L):
    """pod_dlw_targets_raw_v2.py L128-158 verbatim in meaning (nfin = ret5 finite count; y4s = expm1(Σ log1p) rows [E+1, E+48], MIN_FIN)"""
    CS_f, CS_r, CS_r2, CS_q, CS_qf = CS
    grid = np.where(CTS % 14400 == 0)[0]; grid = grid[(grid >= W) & (grid + FWD <= TT - 1)]; E = grid; S = np.maximum(E - TRAIL, 0)
    nfin = np.maximum(CS_f[E] - CS_f[S], 1); covr = (CS_f[E] - CS_f[S]) / np.maximum(E - S, 1)[:, None]
    qvm = (CS_q[E] - CS_q[S]) / nfin; rs_ = CS_r[E] - CS_r[S]
    vstd = np.sqrt(np.maximum((CS_r2[E] - CS_r2[S]) / nfin - (rs_ / nfin) ** 2, 0))
    lo_t = E + 1; hi_t = E + FWD + 1; y4n = CS_f[hi_t] - CS_f[lo_t]
    y4s = np.expm1(CS_L[hi_t] - CS_L[lo_t]).astype(np.float32); y4s[y4n < MIN_FIN] = np.nan
    ok = (covr >= COVR_MIN) & (vstd >= VOL_MIN) & np.isfinite(y4s)
    return E, ok, qvm

def compare(E_exp, MS_exp, E_got, MS_got, label):
    """exact axis + members comparison; first mismatches named"""
    E_got = np.asarray(E_got, np.int64); out = {"n_expected": int(len(E_exp)), "n_build": int(len(E_got)), "axis_equal": bool(np.array_equal(E_exp, E_got)),
                                              "anchors_only_expected": [], "anchors_only_build": [], "rows_members_differ": 0, "first_differences": [], "n_truncated_rows": int(sum(1 for m in MS_exp if len(m) == NTOP))}
    se, sg = set(E_exp.tolist()), set(E_got.tolist())
    out["anchors_only_expected"] = sorted(se - sg)[:10]; out["n_anchors_only_expected"] = len(se - sg)
    out["anchors_only_build"] = sorted(sg - se)[:10]; out["n_anchors_only_build"] = len(sg - se)
    ie = {int(t): i for i, t in enumerate(E_exp)}; ig = {int(t): i for i, t in enumerate(E_got)}
    for t in sorted(se & sg):
        a = np.asarray(MS_exp[ie[t]], np.int64); b = np.asarray(MS_got[ig[t]], np.int64)
        if not np.array_equal(a, b):
            out["rows_members_differ"] += 1
            if len(out["first_differences"]) < 5:
                sa, sb = set(a.tolist()), set(b.tolist())
                out["first_differences"].append({"ts": int(t), "n_expected": int(len(a)), "n_build": int(len(b)), "missing_in_build": sorted(sa - sb)[:8], "extra_in_build": sorted(sb - sa)[:8]})
    out["PASS"] = bool(out["axis_equal"] and out["rows_members_differ"] == 0); out["label"] = label
    return out

def mask_rows(mask_path, ts_rows, syms):
    Mz = np.load(mask_path, allow_pickle=True); msy = [str(s) for s in Mz["symbols"]]
    if msy != list(syms): return None, "mask symbols != cache symbols"
    mts = Mz["ts"].astype(np.int64); row = {int(t): i for i, t in enumerate(mts)}; miss = [int(t) for t in ts_rows if int(t) not in row]
    if miss: return None, f"{len(miss)} grid anchors have no mask row (first {miss[:3]})"
    M = np.asarray(Mz["mask"]); return M[[row[int(t)] for t in ts_rows]], None

def main():
    E = {k: os.environ.get(k, "") for k in ("CACHE", "MEMBER_MASK", "CONTROL_KING_META", "MASKED_KING_META", "CONTROL_DL_TARGETS", "MASKED_DL_TARGETS", "OUT_JSON", "RAW_PATCH", "SKIP_KING", "SKIP_DL")}
    rec = {"gate": "FP2_MEMBER_RULE_CHECK", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%FT%TZ", time.gmtime()), "constants": dict(NTOP=NTOP, MIN_MEM=MIN_MEM, W=W, FWD=FWD, TRAIL=TRAIL, MIN_FIN=MIN_FIN, COVR=COVR_MIN, VOL=VOL_MIN),
           "inputs": {}, "UNAVAILABLE": [], "king": None, "dl": None}
    def write(v):
        rec["VERDICT"] = v; rec["PASS"] = v == "PASS"; os.makedirs(os.path.dirname(os.path.abspath(E["OUT_JSON"] or "MEMBER_RULE_CHECK.json")), exist_ok=True)
        json.dump(rec, open(E["OUT_JSON"] or "MEMBER_RULE_CHECK.json", "w"), indent=1, default=str); print("MEMBER_RULE_CHECK", v, json.dumps({k: (rec[k] or {}).get("summary") for k in ("king", "dl")})); return 0 if v == "PASS" else 3
    need = ["CACHE", "MEMBER_MASK", "OUT_JSON"] + ([] if E["SKIP_KING"] else ["CONTROL_KING_META", "MASKED_KING_META"]) + ([] if E["SKIP_DL"] else ["CONTROL_DL_TARGETS", "MASKED_DL_TARGETS"])
    for k in need:
        if k == "OUT_JSON": continue
        if not E[k] or not os.path.isfile(E[k]): rec["UNAVAILABLE"].append(f"{k} missing: {E[k]!r}")
        else: rec["inputs"][k] = {"path": E[k], "sha256": sha(E[k])}
    if E["RAW_PATCH"]:
        if os.path.isfile(E["RAW_PATCH"]): rec["inputs"]["RAW_PATCH"] = {"path": E["RAW_PATCH"], "sha256": sha(E["RAW_PATCH"])}
        else: rec["UNAVAILABLE"].append(f"RAW_PATCH missing: {E['RAW_PATCH']!r}")
    if rec["UNAVAILABLE"]: return write("UNAVAILABLE")
    t0 = time.time(); Z = np.load(E["CACHE"], allow_pickle=True); CTS = Z["ts"].astype(np.int64); CD = Z["data"]; syms = [str(s) for s in Z["symbols"]]; TT = CD.shape[0]
    if (np.diff(CTS) != 300).any(): rec["UNAVAILABLE"].append("cache ts not a 300 s grid"); return write("UNAVAILABLE")
    CS_f, CS_r, CS_r2, CS_q, CS_qf, r5z, fin = cumsums(CD); log(f"cumsums {time.time()-t0:.0f}s TT={TT} NW={len(syms)}")
    grid_all = np.where(CTS % 14400 == 0)[0]
    MM_all, why = mask_rows(E["MEMBER_MASK"], CTS[grid_all], syms)
    if why: rec["UNAVAILABLE"].append("member mask: " + why); return write("UNAVAILABLE")
    mm_row = {int(g): i for i, g in enumerate(grid_all)}
    def mm_for(Eg): return MM_all[[mm_row[int(g)] for g in Eg]]
    CS = (CS_f, CS_r, CS_r2, CS_q, CS_qf); verdicts = []
    if not E["SKIP_KING"]:
        Ek, ok, qvm = king_rule(CS, CTS, TT); MMk = mm_for(Ek)
        kc, MSc = select(ok, qvm, Ek); km, MSm = select(ok & MMk, qvm, Ek)
        Mc = np.load(E["CONTROL_KING_META"], allow_pickle=True); Mm = np.load(E["MASKED_KING_META"], allow_pickle=True)
        c = compare(CTS[Ek[kc]], MSc, Mc["E_ts"], Mc["members"], "king: unmasked replica vs CONTROL build (binds the replica to the builder)")
        m = compare(CTS[Ek[km]], MSm, Mm["E_ts"], Mm["members"], "king: masked replica (rule ∧ mask → top-NTOP → ≥ MIN_MEM) vs MASKED build")
        rec["king"] = {"control": c, "masked": m, "summary": {"control_reproduced": c["PASS"], "masked_exact": m["PASS"], "n_grid": int(len(Ek)), "n_control": int(len(kc)), "n_masked_expected": int(len(km)), "n_truncated_masked_rows": m["n_truncated_rows"],
                                                         "expected_dropped_by_mask": int(len(set(kc.tolist()) - set(km.tolist()))), "min_masked_pool_over_kept": int(min((int((ok[i] & MMk[i]).sum()) for i in km), default=0))}}
        verdicts += [c["PASS"], m["PASS"]]; log("king", json.dumps(rec["king"]["summary"]))
    if not E["SKIP_DL"]:
        rt = r5z.astype(np.float32).copy()
        if E["RAW_PATCH"]:
            P = np.load(E["RAW_PATCH"]); rt[P["row"], P["col"]] = P["raw32"].astype(np.float32)   # the builder applies the exact raw returns on the clipped bars (target channel only)
        CS_L = np.concatenate([np.zeros((1, rt.shape[1])), np.cumsum(np.log1p(rt.astype(np.float64)), 0)]); del rt
        Ed, okd, qvmd = targets_rule(CS, CTS, TT, CS_L); MMd = mm_for(Ed)
        dc, DSc = select(okd, qvmd, Ed); dm, DSm = select(okd & MMd, qvmd, Ed)
        Tc = np.load(E["CONTROL_DL_TARGETS"], allow_pickle=True); Tm = np.load(E["MASKED_DL_TARGETS"], allow_pickle=True)
        c = compare(CTS[Ed[dc]], DSc, Tc["E_ts"], Tc["members"], "dl: unmasked replica vs CONTROL build (binds the replica to the builder)")
        m = compare(CTS[Ed[dm]], DSm, Tm["E_ts"], Tm["members"], "dl: masked replica (rule ∧ mask → top-NTOP → ≥ MIN_MEM) vs MASKED build")
        rec["dl"] = {"control": c, "masked": m, "summary": {"control_reproduced": c["PASS"], "masked_exact": m["PASS"], "n_grid": int(len(Ed)), "n_control": int(len(dc)), "n_masked_expected": int(len(dm)), "n_truncated_masked_rows": m["n_truncated_rows"],
                                                       "expected_dropped_by_mask": int(len(set(dc.tolist()) - set(dm.tolist()))), "min_masked_pool_over_kept": int(min((int((okd[i] & MMd[i]).sum()) for i in dm), default=0))}}
        verdicts += [c["PASS"], m["PASS"]]; log("dl", json.dumps(rec["dl"]["summary"]))
    rec["runtime_s"] = round(time.time() - t0, 1)
    return write("PASS" if verdicts and all(verdicts) else "FAIL")
if __name__ == "__main__": sys.exit(main())
