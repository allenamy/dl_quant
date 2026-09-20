#!/usr/bin/env python3
"""fcf_f4bp_vs_kc.py — AMENDMENT 3 §4 condition 2: prove, don't assert, what separates F4a (= the archived kc component) from F4b′.

THE RULING (docs/AMENDMENT_3_fallback_counterfactual_2026-09-20.md, 32c4ff43e §4-2), verbatim in substance:
  "「F4a − F4b′ = FTRIM 单独贡献」必须被证明, 不得声称。先断言 z(F4b′) 与 z_kc 逐位相同; 若书仍有差, 残差来自链状态路径
   (F4b′ 背的是 king 链从 2022-01 冷启动的 H, kc 背的是 combo 阶段起点的 H_kc), 必须具名并单独量化, 不得并进 FTRIM。
   lead 预期这两条状态路径不同。"

THE TWO PRODUCTION DEFINITION LINES THIS COMPARES (E-0920-B: file:line + code):
  combo_stage_replay_3520d363.py
    L232: w3m = np.array([w3[0], 0.0, w3[2]])
    L233: w3m = w3m / w3m.sum() if w3m.sum() > 1e-12 else np.array([0.5, 0.0, 0.5])
    L234: z_kc = w3m[0] * np.nan_to_num(legz["king"]) + w3m[2] * np.nan_to_num(legz["fund"])
    L245: z_kc = np.where(_band_kc, 0.0, z_kc)          # FTRIM: (z_kc < 0) & rn8 <= -0.0010
  shadow_loop_v3_replay_F4bp.py (the F4b′ producer, lines 449-450, gated by fcf_mk_producer_F4bp.py G1-G5)
    L449: w3m = np.array([w3[0], 0.0, w3[2]]); w3m = w3m / w3m.sum() if w3m.sum() > 1e-12 else np.array([0.5, 0.0, 0.5])
    L450: z    = w3m[0]*np.nan_to_num(legz["king"]) + w3m[1]*np.nan_to_num(legz["rev24"]) + w3m[2]*np.nan_to_num(legz["fund"])

WHAT IS PROVED HERE, IN THREE PARTS:
  A  z(F4b′) == z_kc BEFORE FTRIM, bitwise, on every anchor. (`w3m[1]` is exactly +0.0 and `nan_to_num` leaves no NaN/inf, so the middle
     term is exactly +0.0 and `x + 0.0 == x`; the ruling asks for this measured, not argued, so it is measured.)
     w3m is NOT re-derived: it is read from the archive's own `combo_meta.w3_masked`, i.e. the vector combo_stage actually used.
  B  FTRIM's footprint: the anchors where FTRIM zeroed NOTHING (`ftrim.n_kc == 0`). On those, z_kc == z_kc-before-FTRIM, hence
     z(F4b′) == z_kc bitwise, hence ANY book difference there is NOT FTRIM.
  C  THE RESIDUAL, SEPARATED. On the simulated fallback anchors, compare the F4b′ king book with the kc book, split by whether FTRIM
     fired. On the FTRIM-fired-nothing subset the difference is the CHAIN-STATE PATH alone (F4b′ carries the king chain's H from the
     2022-01 cold start; kc carries H_kc from the combo stage's own start). On the other subset it is FTRIM + chain state. The two are
     reported separately and are never added together into one "FTRIM" number.

E-0920-C: every cell prints its n; a subset with no members prints as no-measurement, never as 0.
usage: fcf_f4bp_vs_kc.py <out.json>
"""
import hashlib, json, os, sys, time

import numpy as np

OBJB = "/workspace/object_b_2026-09-19/work/A0_main"
OUT = "/workspace/fallback_cf_2026-09-20"
JUDGE_FIRST, JUDGE_LAST = 1656547200, 1788480000


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))


def load(p):
    z = np.load(p); return {k: z[k] for k in z.files}


def main():
    OUTP = sys.argv[1]
    V1 = load(f"{OBJB}/P1.vec.npz"); V3 = load(f"{OBJB}/P3.vec.npz")
    K = load(f"{OUT}/work/F4bp_KING.npz")
    D = json.load(open(f"{OBJB}/P3.json"))["records"]
    A1 = V1["anchor"].astype(np.int64); A3 = V3["anchor"].astype(np.int64)
    p1 = {int(a): i for i, a in enumerate(A1)}
    kpos = {int(a): i for i, a in enumerate(K["anchor"].astype(np.int64))}
    meta = {int(r["anchor"]): ((r.get("combo") or {}).get("combo_meta"), (r.get("combo") or {}).get("ftrim")) for r in D}
    kind = load(f"{OBJB}/TARGETS_A0_main.npz")["scaled_kind"]
    doc = {"device": "fcf_f4bp_vs_kc.py", "self_sha256": sha(os.path.abspath(__file__)),
           "ruling": "docs/AMENDMENT_3_fallback_counterfactual_2026-09-20.md (32c4ff43e) §4 condition 2",
           "inputs": {k: sha(v) for k, v in (("P1.vec", f"{OBJB}/P1.vec.npz"), ("P3.vec", f"{OBJB}/P3.vec.npz"),
                                             ("P3.json", f"{OBJB}/P3.json"), ("F4bp_KING", f"{OUT}/work/F4bp_KING.npz"))},
           "utc": iso(time.time()), "checks": []}
    FAILS = []

    def check(n, ok, d=None):
        doc["checks"].append(dict(check=n, ok=bool(ok), detail=d))
        print(("PASS " if ok else "FAIL ") + n, json.dumps(d, default=str)[:250] if d is not None else "", flush=True)
        if not ok: FAILS.append(n)

    def row(V, name, k):
        a, b = V[name + "_off"][k], V[name + "_off"][k + 1]; return V[name][a:b]

    def vec(V, name, k):
        a, b = V[name + "_off"][k], V[name + "_off"][k + 1]
        return V[name + "_idx"][a:b].astype(np.int64), V[name + "_val"][a:b]

    # ── A: z(F4b') == z_kc BEFORE FTRIM, bitwise ──
    nA = eqA = 0; badA = []
    ft0 = []                       # anchors where FTRIM zeroed nothing
    for k3, A in enumerate(A3):
        cm, ft = meta.get(int(A), (None, None))
        if cm is None or cm.get("w3_masked") is None: continue
        i1 = p1.get(int(A))
        if i1 is None: continue
        pm = row(V1, "pm", i1).astype(np.int64); n = len(pm)
        lz = row(V1, "legz", i1)
        if len(lz) != 3 * n: continue
        king, rev24, fund = lz[:n], lz[n:2 * n], lz[2 * n:]
        w = np.asarray(cm["w3_masked"], np.float64)
        z_f4bp = w[0] * np.nan_to_num(king) + w[1] * np.nan_to_num(rev24) + w[2] * np.nan_to_num(fund)
        z_kc_pre = w[0] * np.nan_to_num(king) + w[2] * np.nan_to_num(fund)
        nA += 1
        if z_f4bp.tobytes() == z_kc_pre.tobytes(): eqA += 1
        elif len(badA) < 3: badA.append(iso(A))
        if ft is not None and int(ft.get("n_kc") or 0) == 0: ft0.append(int(A))
    check("A.z_F4bprime_equals_z_kc_before_FTRIM_bitwise_on_every_anchor", eqA == nA and nA > 0,
          dict(equal=eqA, compared=nA, first_mismatch=badA,
               note="w3m read from the archive's own combo_meta.w3_masked, not re-derived"))

    # ── B: FTRIM footprint ──
    ft0s = set(ft0)
    check("B.FTRIM_footprint_named", True,
          dict(anchors_with_an_ftrim_record=sum(1 for a in A3 if meta.get(int(a), (None, None))[1] is not None),
               anchors_where_FTRIM_zeroed_nothing=len(ft0), share=round(len(ft0) / max(len(A3), 1), 4),
               meaning="on these, z_kc == z_kc-before-FTRIM, so z(F4b′) == z_kc bitwise and any book difference is NOT FTRIM"))

    # ── C: the residual, split ──
    res = {}
    for lab, sel in (("FTRIM_fired_nothing__residual_is_CHAIN_STATE_ALONE", lambda a: int(a) in ft0s),
                     ("FTRIM_fired__residual_is_FTRIM_PLUS_CHAIN_STATE", lambda a: int(a) not in ft0s)):
        mx = []; l1 = []; dg = []; anchors = []
        for k3, A in enumerate(A3):
            if kind[k3] != 1 or not (JUDGE_FIRST <= int(A) <= JUDGE_LAST) or not sel(A): continue
            kk = kpos.get(int(A))
            if kk is None: continue
            a_, b_ = K["king_file_off"][kk], K["king_file_off"][kk + 1]
            bi, bv = K["king_file_idx"][a_:b_].astype(np.int64), K["king_file_val"][a_:b_]
            ci, cv = vec(V3, "kc", k3)
            x = np.zeros(829); y = np.zeros(829); x[bi] = bv; y[ci] = cv
            d = np.abs(x - y)
            mx.append(float(d.max())); l1.append(float(d.sum()))
            dg.append(float(np.abs(x).sum() - np.abs(y).sum())); anchors.append(int(A))
        res[lab] = ({"n": 0, "note": "no member — no measurement, not 0"} if not mx else
                    {"n": len(mx),
                     "max_abs_dw": {"median": float(np.median(mx)), "p95": float(np.percentile(mx, 95)), "max": float(np.max(mx))},
                     "sum_abs_dw_L1": {"median": float(np.median(l1)), "p95": float(np.percentile(l1, 95)), "max": float(np.max(l1))},
                     "gross_difference_F4bprime_minus_kc": {"median": float(np.median(dg)), "p05": float(np.percentile(dg, 5)),
                                                            "p95": float(np.percentile(dg, 95))},
                     "first": iso(anchors[0]), "last": iso(anchors[-1])})
    doc["C_residual_on_simulated_fallback_anchors"] = res
    a = res["FTRIM_fired_nothing__residual_is_CHAIN_STATE_ALONE"]; b = res["FTRIM_fired__residual_is_FTRIM_PLUS_CHAIN_STATE"]
    check("C.chain_state_residual_is_measured_and_named", a.get("n", 0) > 0,
          dict(n_chain_state_only=a.get("n"), n_ftrim_plus_chain=b.get("n")))
    if a.get("n") and b.get("n"):
        doc["C_verdict"] = {
            "chain_state_alone_L1_median": a["sum_abs_dw_L1"]["median"],
            "ftrim_plus_chain_state_L1_median": b["sum_abs_dw_L1"]["median"],
            "ratio_ftrim_plus_chain_over_chain_alone": round(b["sum_abs_dw_L1"]["median"] / a["sum_abs_dw_L1"]["median"], 4),
            "reading": ("if the two are the same order, the chain-state path is NOT negligible and 'F4a - F4b′ = FTRIM alone' is FALSE; "
                        "AMENDMENT 3 §4-3 then forces (C) and no point estimate for rev24")}
    doc["VERDICT"] = "PASS" if not FAILS else "REFUSED"; doc["failed"] = FAILS
    json.dump(doc, open(OUTP + ".tmp", "w"), indent=1); os.replace(OUTP + ".tmp", OUTP)
    print(json.dumps(res, indent=1)[:1500], flush=True)
    if doc.get("C_verdict"): print("C_verdict:", json.dumps(doc["C_verdict"]), flush=True)
    print(f"FCF_F4BP_VS_KC VERDICT={doc['VERDICT']} checks={len(doc['checks'])} receipt_sha256={sha(OUTP)}", flush=True)
    sys.exit(0 if not FAILS else 3)


if __name__ == "__main__":
    main()
