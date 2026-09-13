#!/usr/bin/env python3
"""t6_posthoc.py -- T6 POST-HOC decomposition (written AFTER reading RECEIPT_T6_compute.json; NOT part of the frozen spec; no verdict
may rest on it). Reuses the frozen machinery of t6_compute.py by import-free copy of its definitions via exec of the frozen file
up to the GATE section, so the estimators are bitwise the frozen ones.
PH1  F1 minus the XIB_LAG50 family {XIB_PWR230k, IB_LAG50_PWR230k} (both seeds, W_FULL and FROZEN): PBO, nested, SEL DSR.
PH2  training-window Sharpe and rank of H* and of A0 at each nested selection point (F1, both seeds, both windows).
PH3  nested selection minus A0 on the nested span (paired UTC-day block bootstrap, same draws as the frozen device).
Usage: python3 t6_posthoc.py <env_whitelist_csv> <receipts_dir>
"""
import os, sys, json, hashlib
WHITE = set(x for x in sys.argv[1].split(",") if x); assert WHITE
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
RD = sys.argv[2]; HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN = os.path.join(HERE, "t6_compute.py")
def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()
FROZEN_SHA = "103974f3d7958a4e506bb3b38208d188e0c9f692a106999ab7deb57404f134fc"
assert sha(FROZEN) == FROZEN_SHA, "t6_compute.py changed since the frozen run"
src = open(FROZEN).read(); cut = src.index("# ------------------------------------------------------------------ GATE-I on the real F1 s42 matrix")
g = {"__file__": FROZEN}; sys_argv = sys.argv; sys.argv = [FROZEN, sys.argv[1], RD]
exec(compile(src[:cut], FROZEN, "exec"), g); sys.argv = sys_argv
np = g["np"]; TS = g["TS"]; WF, FR = g["WF"], g["FR"]; DATA = g["DATA"]; SRcols = g["SRcols"]; SR = g["SR"]
cscv, dsr, nested, boot_sr_pair, DAY = g["cscv"], g["dsr"], g["nested"], g["boot_sr_pair"], g["DAY"]
SEG_WF, SEG_FR = g["SEG_WF"], g["SEG_FR"]
OUT = dict(device="t6_posthoc.py", self_sha256=sha(os.path.abspath(__file__)), frozen_device_sha256=FROZEN_SHA, label="POST-HOC (after reading RECEIPT_T6_compute.json); descriptive only",
           env_actual={k: os.environ[k] for k in sorted(os.environ)}, PH1={}, PH2={}, PH3={})
XIBFAM = ("XIB_PWR230k_s42", "IB_LAG50_PWR230k_s42", "XIB_PWR230k_s2027", "IB_LAG50_PWR230k_s2027")
for s in ("42", "2027"):
    D = DATA[s]; F1 = D["F1"].astype(bool); stems = D["stem"].astype(str); ids = D["member_id"].astype(str)
    for tag, m in (("F1", F1), ("F1_minus_XIBfam", F1 & ~np.isin(stems, XIBFAM))):
        X = D["G"][:, m]; lab = np.array(["%s:%s" % (a, b) for a, b in zip(ids[m], stems[m])])
        a0 = int(np.nonzero(np.isin(stems[m], ("A0_PWR230k_s42", "A0_PWR230k_s2027")))[0][0])
        for w, mask, segs in (("W_FULL", WF, SEG_WF), ("FROZEN", FR, SEG_FR)):
            ne = nested(X, lab, a0, segs, mask)
            if tag == "F1_minus_XIBfam":
                pb, _ = cscv(X[mask], lab); ds = dsr(X[mask], lab, a0)
                OUT["PH1"]["s%s_%s" % (s, w)] = dict(N=int(m.sum()), PBO=pb["PBO"], P_oos_loss=pb["P_oos_loss"], slope=pb["slope"], top=pb["top_selected"][:3], N_eff=ds["N_eff"],
                                                      SEL=ds["SEL"]["member"], SEL_SR=ds["SEL"]["SR_annual"], SEL_P_gt0_Neff=ds["SEL"]["P_true_SR_gt_0_N_eff"],
                                                      SR_nested=ne["SR_nested"], Hstar=ne["Hstar"], SR_Hstar_span=ne["SR_Hstar_span"], haircut=ne["haircut_primary"], ci95_haircut=ne["ci95_haircut_primary"],
                                                      picks=[r["selected"] for r in ne["segments"]])
            else:
                H = int(np.nonzero(lab == ne["Hstar"])[0][0]); rows = []
                for (lo, hi), seg in zip(segs, ne["segments"]):
                    tr = TS < lo; srt = SRcols(X[tr]); order = np.argsort(-srt)
                    rows.append(dict(segment=seg["segment"], selected=seg["selected"], SR_train_selected=float(srt.max()), Hstar_SR_train=float(srt[H]), Hstar_rank_train=int(np.nonzero(order == H)[0][0] + 1),
                                     A0_SR_train=float(srt[a0]), A0_rank_train=int(np.nonzero(order == a0)[0][0] + 1), N=int(len(srt))))
                OUT["PH2"]["s%s_%s" % (s, w)] = dict(Hstar=ne["Hstar"], rows=rows)
                span = np.zeros(len(TS), bool)
                for lo, hi in segs: span |= (TS >= lo) & (TS < hi)
                parts = [((TS >= lo) & (TS < hi), int(np.nonzero(lab == r["selected"])[0][0])) for (lo, hi), r in zip(segs, ne["segments"])]
                xn = np.concatenate([X[sg, k] for sg, k in parts]); xa = X[span, a0]; dn = DAY[span]
                bt = boot_sr_pair(xn, xa, dn)
                OUT["PH3"]["s%s_%s" % (s, w)] = dict(SR_nested=SR(xn), SR_A0_span=SR(xa), diff=SR(xn) - SR(xa), ci95_diff=bt["ci95_diff"], n_days=bt["n_days"])
json.dump(OUT, open(os.path.join(RD, "POSTHOC_T6_decomposition.json"), "w"), indent=1, default=float)
p = OUT["PH1"]
print("SUMMARY t6_posthoc (POST-HOC) F1-minus-XIBfam s42 WFULL PBO=%.4f nested=%.3f H*=%s %.3f haircut=%.3f | FROZEN PBO=%.4f nested=%.3f H*=%s %.3f haircut=%.3f | nested-A0 s42 WFULL %.3f %s FROZEN %.3f %s self_sha256=%s" % (
    p["s42_W_FULL"]["PBO"], p["s42_W_FULL"]["SR_nested"], p["s42_W_FULL"]["Hstar"], p["s42_W_FULL"]["SR_Hstar_span"], p["s42_W_FULL"]["haircut"],
    p["s42_FROZEN"]["PBO"], p["s42_FROZEN"]["SR_nested"], p["s42_FROZEN"]["Hstar"], p["s42_FROZEN"]["SR_Hstar_span"], p["s42_FROZEN"]["haircut"],
    OUT["PH3"]["s42_W_FULL"]["diff"], [round(v, 3) for v in OUT["PH3"]["s42_W_FULL"]["ci95_diff"]], OUT["PH3"]["s42_FROZEN"]["diff"], [round(v, 3) for v in OUT["PH3"]["s42_FROZEN"]["ci95_diff"]], OUT["self_sha256"][:16]))
