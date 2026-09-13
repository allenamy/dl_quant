#!/usr/bin/env python3
"""t8_judge.py — PREREG_T8 §8 reading, from receipts only (build, 500-permutation null, fit). Asserts every receipt's device / common / data sha.
Cell criteria C1 r_pool>=0.03; C2 r_f>0 in >=4/5 folds; C3 CI95 lower bound >0 under k=0 and k=9; C4 (NET) price-part r>=0.03 with CI LB>0 (k0,k9);
G1 r_pool > q95 of the family max M; G2b argmax_{k in 0..3} spectrum = 0. PC: CARRY r_pool >= 0.5 both seeds per model.
Writes receipts/RECEIPT_T8_judge.json. Launch: devices/run_t8.sh t8_judge.py"""
import os, sys, time, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t8_common as C
ENV = C.check_env(sys.argv)
import numpy as np
t0 = time.time()
SELF = C.sha256(os.path.abspath(__file__)); COMMON = C.sha256(C.__file__); PRE = C.check_prereg()
BPATH = C.T8 + "/receipts/RECEIPT_T8_build.json"; B = json.load(open(BPATH))
FPATH = C.T8 + "/receipts/RECEIPT_T8_fit.json"; FR = json.load(open(FPATH))
assert B["common_sha256"] == COMMON and B["self_sha256"] == C.sha256(C.T8 + "/devices/t8_build.py")
assert FR["common_sha256"] == COMMON and FR["self_sha256"] == C.sha256(C.T8 + "/devices/t8_fit.py") and FR["data_sha256"] == B["out"]["sha256"]
assert FR["build_receipt_sha256"] == C.sha256(BPATH) and FR["out"]["sha256"] == C.sha256(FR["out"]["path"])
NULL_SELF = C.sha256(C.T8 + "/devices/t8_null.py"); assert FR["null_device_sha256"] == NULL_SELF
rows = []; null_files = {}
for p in sorted(glob.glob(C.T8 + "/receipts/RECEIPT_T8_null_*.json")):
    N = json.load(open(p))
    assert N["self_sha256"] == NULL_SELF and N["common_sha256"] == COMMON and N["data_sha256"] == B["out"]["sha256"] and N["build_receipt_sha256"] == C.sha256(BPATH)
    rows += N["rows"]; null_files[os.path.basename(p)] = C.sha256(p)
rows.sort(key=lambda x: x["r"]); assert [x["r"] for x in rows] == list(range(C.NNULL)), "null incomplete"
M = np.array([x["M"] for x in rows]); q95 = float(np.percentile(M, 95))
cellnull = {f"{m}_{t}": np.array([x[m + "_" + t] for x in rows]) for m in C.MODELS for t in C.SUBST}
FIN = lambda v: v is not None and np.isfinite(v)

crit = {}
for key, o in FR["cells"].items():
    m, t, s = o["model"], o["target"], o["seed"]
    r = o["pool"]["r"]
    c1 = bool(FIN(r) and r >= 0.03)
    npos = sum(1 for f in o["folds"] if FIN(f["r"]) and f["r"] > 0)
    c2 = bool(npos >= 4)
    c3 = bool(o["pool"]["ci95_k0"][0] > 0 and o["pool"]["ci95_k9"][0] > 0)
    spec = {int(k): v["r"] for k, v in o["spectrum"].items()}
    fwd = {k: (spec[k] if FIN(spec[k]) else -np.inf) for k in (0, 1, 2, 3)}
    g2b = bool(max(fwd, key=lambda k: fwd[k]) == 0 and FIN(spec[0]))
    d = dict(r_pool=r, n_folds_positive=npos, C1=c1, C2=c2, C3=c3, G2b=g2b, spectrum_forward_argmax=max(fwd, key=lambda k: fwd[k]))
    if t in C.SUBST:
        g1 = bool(FIN(r) and r > q95)
        c4 = True
        if t == "NET":
            cp = o["C4_price"]; c4 = bool(FIN(cp["r"]) and cp["r"] >= 0.03 and cp["ci95_k0"][0] > 0 and cp["ci95_k9"][0] > 0)
            d["C4"] = c4; d["r_price"] = cp["r"]
        core = bool(c1 and c2 and c3 and g1 and c4)
        d.update(G1=g1, null_p_family=float((1 + int((M >= r).sum())) / (C.NNULL + 1)) if FIN(r) else None,
                 null_q95_cell=float(np.percentile(cellnull[f"{m}_{t}"], 95)), CORE=core, PASS_cell=bool(core and g2b))
    crit[key] = d

PC = {m: bool(all(FIN(FR["cells"][f"{m}_CARRY_s{s}"]["pool"]["r"]) and FR["cells"][f"{m}_CARRY_s{s}"]["pool"]["r"] >= 0.5 for s in C.SEEDS)) for m in C.MODELS}

def label(m, t):
    o = [FR["cells"][f"{m}_{t}_s{s}"]["decomp"] for s in C.SEEDS]
    if all(FIN(x["share_S"]) and x["share_S"] >= 0.5 for x in o):
        return "DOMINANCE-TIMING"
    if all(FIN(x["share_S"]) and x["share_S"] < 0.5 and x["r_e"] >= 0.03 and x["r_e_ci95_k0"][0] > 0 and x["r_e_ci95_k9"][0] > 0 for x in o):
        return "RESIDUAL"
    return "MIXED"

mt = {}
for t in C.SUBST:
    for m in C.MODELS:
        cs = [crit[f"{m}_{t}_s{s}"] for s in C.SEEDS]
        if not PC[m]:
            v = "INVALID"
        elif all(c["PASS_cell"] for c in cs):
            v = "PASS"
        elif all(c["CORE"] for c in cs) or sum(c["PASS_cell"] for c in cs) == 1:
            v = "UNDECIDED"
        else:
            v = "FAIL"
        mt[f"{m}_{t}"] = dict(verdict=v, decomposition_label=label(m, t))
tv = {}
for t in C.SUBST:
    vr, vl = mt[f"R_{t}"]["verdict"], mt[f"L_{t}"]["verdict"]
    if vr == "PASS":
        v, lab = "PASS-LINEAR", mt[f"R_{t}"]["decomposition_label"]
    elif vl == "PASS":
        v, lab = "PASS-LGBM-ONLY", mt[f"L_{t}"]["decomposition_label"]
    elif "UNDECIDED" in (vr, vl):
        v, lab = "UNDECIDED", {m: mt[f"{m}_{t}"]["decomposition_label"] for m in C.MODELS if mt[f"{m}_{t}"]["verdict"] == "UNDECIDED"}
    elif vr == "INVALID" and vl == "INVALID":
        v, lab = "INVALID", None
    else:
        v, lab = "FAIL", None
    tv[t] = dict(verdict=v, decomposition_label_attached=lab, R=vr, L=vl)
if not B["ALL_PASS"] or not any(PC.values()):
    overall = "INVALID"
elif any(tv[t]["verdict"].startswith("PASS") for t in C.SUBST):
    overall = "PASS"
elif any(tv[t]["verdict"] == "UNDECIDED" for t in C.SUBST):
    overall = "UNDECIDED"
else:
    overall = "FAIL"
R = dict(device="t8_judge.py", self_sha256=SELF, common_sha256=COMMON, prereg_sha256=PRE, env=ENV, build_receipt_sha256=C.sha256(BPATH),
         fit_receipt_sha256=C.sha256(FPATH), null_receipts=null_files, null=dict(n=len(M), q95_family_max=q95, M_quantiles={str(q): float(np.percentile(M, q)) for q in (50, 90, 95, 99)},
         M_max=float(M.max())), positive_control=PC, criteria=crit, model_target=mt, target=tv, T8=overall, build_all_pass=B["ALL_PASS"], utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
C.jdump(R, C.T8 + "/receipts/RECEIPT_T8_judge.json")
print(f"T8_JUDGE_DONE T8={overall} NET={tv['NET']['verdict']} LONG={tv['LONG']['verdict']} SHORT={tv['SHORT']['verdict']} PC={PC} q95={q95:.5f}", flush=True)
