#!/usr/bin/env python3
"""t5d_posthoc_dk_carry.py — Mac, READ-ONLY. POST-HOC description: where the deployed books' fixed-weight carry correction (Δ_fixed, +0.25 bps/anchor) comes from.
Per name and per period (before / after the producer FTRIM start 09-02 12Z), Σ_k w_k,n (C4corr − C4x0910)_k,n · 1e4 / 61 for the deployed king chain (archived kc) and
the deployed book (target_live), with the interval change of the in-force cell. Sums must equal the bridge components per anchor.
Launch: env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5d_posthoc_dk_carry.py "$PWD" CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING
"""
import os, sys, json, time, hashlib, stat
T = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
def sha(p):
    st = os.stat(p)
    if st.st_flags & getattr(stat, "SF_DATALESS", 0x40000000): raise SystemExit("REFUSE dataless %s" % p)
    h = hashlib.sha256(); n = 0
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b); n += len(b)
    if n != st.st_size: raise SystemExit("REFUSE short read %s" % p)
    return h.hexdigest()
assert sha(T + "/PREREG_T5d_iv_corrected_replay_2026-09-13.md") == "a1ef16cdba5e95def27f77b180cba3f1ac954ad04c7b0a17f59c24e1a0c85a4f"
BR = json.load(open(T + "/receipts/pod2/RECEIPT_T5d_bridge.json")); CMPP = "/Users/haosiyu/cc_tmp/t5d_2026-09-13/T5d_bridge_components.npz"; assert sha(CMPP) == BR["components_npz_sha256"]
INGP = os.path.dirname(T) + "/T5c/receipts/T5c_live_ingredients.npz"; assert sha(INGP) == BR["inputs"]["/workspace/uplift_r2_2026-09-13/T5c/receipts/T5c_live_ingredients.npz"]
Z = np.load(CMPP, allow_pickle=True); ING = np.load(INGP, allow_pickle=True)
SYM = [str(s) for s in ING["symbols"]]; CAL = [int(x) for x in ING["cal"]]; WIN = [int(x) for x in ING["win"]]; FTRIM_ON = int(ING["FTRIM_ON"])
assert [int(x) for x in Z["CAL"]] == CAL
kW = [k for k, A in enumerate(CAL) if A in WIN]; C4X = Z["C4X"]; C4C = Z["C4C"]
U = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
OUT = {}
for nm, W, key in (("D_K", ING["KC"], "DK"), ("D_B", ING["WTL"], "DB")):
    contrib = np.zeros((len(CAL), len(SYM))); maxres = 0.0
    for k in range(len(CAL)):
        w = W[k] / np.abs(W[k]).sum(); contrib[k] = w * (C4C[k] - C4X[k]) * 1e4
        if key == "DK": maxres = max(maxres, abs(contrib[k].sum() - (Z["DK_FIX_C"][k] - Z["DK_T5C_C"][k])))
    pre = np.array([CAL[k] < FTRIM_ON for k in kW]); kw = np.array(kW)
    tot = contrib[kw].sum(0) / len(kW); tpre = contrib[kw[pre]].sum(0) / len(kW); tpost = contrib[kw[~pre]].sum(0) / len(kW)
    ratio = np.where((C4X != 0), C4C / np.where(C4X != 0, C4X, 1.0), np.nan)
    rows = []
    for n in np.argsort(-np.abs(tot))[:12]:
        held = [k for k in kW if abs(W[k][n]) > 0 and C4X[k][n] != C4C[k][n]]
        rows.append(dict(symbol=SYM[n], total=float(tot[n]), before_ftrim=float(tpre[n]), after_ftrim=float(tpost[n]), mean_weight_when_changed=(float(np.mean([W[k][n] / np.abs(W[k]).sum() for k in held])) if held else 0.0),
                         anchors_changed_and_held=len(held), first=(U(CAL[held[0]]) if held else None), last=(U(CAL[held[-1]]) if held else None),
                         carry_ratio_corr_over_x0910=sorted({round(float(ratio[k][n]), 3) for k in held if np.isfinite(ratio[k][n])})))
    OUT[nm] = dict(total=float(tot.sum()), before_ftrim=float(tpre.sum()), after_ftrim=float(tpost.sum()), n_before=int(pre.sum()), n_after=int((~pre).sum()), names=rows,
                   share_top3=float(np.sort(np.abs(tot))[::-1][:3].sum() / max(np.abs(tot).sum(), 1e-12)), max_abs_residual_vs_components=(maxres if key == "DK" else None))
assert OUT["D_K"]["max_abs_residual_vs_components"] <= 1e-9 and abs(OUT["D_K"]["total"] - BR["deltas"]["D_K"]["C"]["delta_fixed"][0]) <= 1e-9 and abs(OUT["D_B"]["total"] - BR["deltas"]["D_B"]["C"]["delta_fixed"][0]) <= 1e-9
RC = dict(label="POST-HOC descriptive; not a gate, not a reading", self_sha256=sha(os.path.abspath(__file__)), inputs={CMPP: sha(CMPP), INGP: sha(INGP)}, ftrim_on=U(FTRIM_ON), result=OUT,
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T + "/receipts/RECEIPT_T5d_posthoc_dk_carry.json", "w"), indent=1)
print(json.dumps({nm: dict(total=round(v["total"], 4), before=round(v["before_ftrim"], 4), after=round(v["after_ftrim"], 4), top=[(r["symbol"], round(r["total"], 4), round(r["before_ftrim"], 4), r["anchors_changed_and_held"], r["first"], r["last"], round(1e3 * r["mean_weight_when_changed"], 2), r["carry_ratio_corr_over_x0910"]) for r in v["names"][:8]]) for nm, v in OUT.items()}, indent=1))
