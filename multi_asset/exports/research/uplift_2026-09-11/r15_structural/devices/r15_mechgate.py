#!/usr/bin/env python3
"""r15_mechgate.py — PREREG_r15 §4 mechanism gate for ARM-F, read BEFORE any P&L number.
Inputs: instrumented derived-device runs D_A0I_s{42,2027} (FTPOS=0) and D_FI_s{42,2027} (FTPOS=1), whose rec/W were
proven bitwise equal to the pinned device (GATE P2/P3, RECEIPT_r15_drive_gateP.json, asserted here).
Also emits the per-anchor FTPOS kill counts of ARM-F (null firing target, §8).  CPU only, read-only.
"""
import os, sys, json, time, hashlib, calendar
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
BANNED = ('CAL','JUDGE','UPLIFT','PANEL','LOOK','WRULE','LEGS','PHI','FSEED','W3FIX','FTRIM','UMASK','SLOW','FPRED','MEMBERS_TOPN','COSTB','SLEEVE','KMOD','SEAT','RNSM','LTRIM','CDAMP','FUNDSCALE','FEMAT','TRADE_TOPN','REF_SKIP','PYTHON','OMP','MKL','R15','FTPOS','OUT_TAG')
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
BAN = sorted(k for k in os.environ if k.startswith(BANNED)); assert BAN == [], ("CALIBER FLAG PRESENT", BAN)
ENV = dict(env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)}, launch_cmdline=" ".join(sys.argv))
import numpy as np
R = "/workspace/uplift_2026-09-11/r15_structural"
PREREG_SHA = "097769b087fa0834fb780062bf710134d7e3a67555174de5c26c1668c455f6fc"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(R + "/PREREG_r15_structural_2026-09-12.md") == PREREG_SHA
G = json.load(open(R + "/receipts/RECEIPT_r15_drive_gateP.json"))
assert G["gate"]["P1"]["PASS"] and G["gate"]["P2"]["PASS"] and G["gate"]["P3"]["PASS"], G["gate"]
UB = calendar.timegm((2026, 8, 30, 20, 0, 0)); K24 = calendar.timegm((2024, 1, 1, 0, 0, 0)); Y26 = calendar.timegm((2026, 1, 1, 0, 0, 0))
OUT = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, env=ENV, arms={}, kill_counts={})
def stats(tag, expect_zero):
    p = R + "/arms/%s.npz" % tag; assert sha(p) == G["runs"][tag]["out_sha256"], tag
    Z = np.load(p, allow_pickle=True); C = [str(c) for c in Z["cols"]]; rec = Z["d30_n2_c42_rec"]
    ts = rec[:, 0].astype(np.int64); gt = rec[:, C.index("gross_total")]
    fk, ff, dp, kl, mm, smr, c4 = (Z["d30_n2_c42_R15_" + k] for k in ("flagK", "flagF", "deep", "kill", "member", "smr", "c4"))
    assert fk.shape == smr.shape == (len(ts), 829)
    W = Z["d30_n2_c42_W"].astype(np.float64)
    # smr is the executor redemean of W (device L314-320); parity of gross: |smr|_1 == |W|_1 (rescaled)  and carry_ex == sum(smr*c4)
    gs = np.abs(smr.astype(np.float64)).sum(1); par_g = float(np.abs(gs - gt).max())
    car_ex = rec[:, C.index("carry_ex")]; car_chk = (smr.astype(np.float64) * c4.astype(np.float64)).sum(1) * 1e4; par_c = float(np.abs(car_chk - car_ex).max())
    WT = ts <= UB; WA = WT.copy(); WA[:900] = False; assert WA.sum() == 9138 and WT.sum() == 10038
    both = fk & ff; either = fk | ff; neg = smr < 0
    def block(mask_names, win, label):
        n_flag = mask_names[win].sum(1); leak = mask_names & neg
        n_leak = leak[win].sum(1)
        lg = (np.abs(smr) * leak).sum(1)[win] / gt[win]
        lc = ((smr * c4) * leak).sum(1)[win] * 1e4 / gt[win]
        return dict(label=label, n_anchors=int(win.sum()), flagged_per_anchor=float(n_flag.mean()),
                    leaked_per_anchor=float(n_leak.mean()), frac_flagged_negative=float(n_leak.sum() / max(n_flag.sum(), 1)),
                    leaked_gross_share_mean=float(lg.mean()), leaked_gross_share_p90=float(np.percentile(lg, 90)), leaked_gross_share_max=float(lg.max()),
                    leaked_carry_paid_bps_mean=float(lc.mean()), anchors_with_any_leak=float((n_leak > 0).mean()))
    res = dict(parity_gross_maxabs=par_g, parity_carry_ex_maxabs=par_c, expect_zero=expect_zero)
    for wn, win in (("W_ALPHA", WA), ("KING_LIVE", WA & (ts >= K24)), ("Y2026", WA & (ts >= Y26))):
        res[wn] = dict(both_chains=block(both, win, "flagged in BOTH chains (production dual-arm analogue) & smr<0"),
                       either_chain=block(either, win, "flagged in EITHER chain & smr<0"),
                       deep_short=block(dp, win, "rn8<=th (any z) & smr<0  = the FTPOS kill set"),
                       kills_per_anchor=float(kl[win].sum(1).mean()), kills_total=int(kl[win].sum()),
                       carry_ex_pug_mean=float((car_ex[win] / gt[win]).mean()))
        res[wn]["leaked_carry_share_of_book_carry"] = float(res[wn]["both_chains"]["leaked_carry_paid_bps_mean"] / res[wn]["carry_ex_pug_mean"]) if res[wn]["carry_ex_pug_mean"] != 0 else None
    OUT["kill_counts"][tag] = dict(ts=ts.tolist(), kills=kl.sum(1).astype(int).tolist())
    return res
for s in ("42", "2027"):
    OUT["arms"]["D_A0I_s" + s] = stats("D_A0I_s" + s, False)
    OUT["arms"]["D_FI_s" + s] = stats("D_FI_s" + s, True)
def gate():
    g = {}
    for s in ("42", "2027"):
        a = OUT["arms"]["D_A0I_s" + s]["W_ALPHA"]["both_chains"]; f = OUT["arms"]["D_FI_s" + s]["W_ALPHA"]
        g["s" + s] = dict(A0_frac_flagged_negative=a["frac_flagged_negative"], A0_leaked_carry_bps=a["leaked_carry_paid_bps_mean"],
                         A0_gate_pass=bool(a["frac_flagged_negative"] >= 0.25 and a["leaked_carry_paid_bps_mean"] >= 0.05),
                         F_both_leaked_total=int(round(f["both_chains"]["leaked_per_anchor"] * f["both_chains"]["n_anchors"])),
                         F_deep_short_total=int(round(f["deep_short"]["leaked_per_anchor"] * f["deep_short"]["n_anchors"])),
                         F_position_zero_pass=bool(f["both_chains"]["leaked_per_anchor"] == 0.0 and f["deep_short"]["leaked_per_anchor"] == 0.0))
    g["PASS"] = all(v["A0_gate_pass"] and v["F_position_zero_pass"] for k, v in g.items() if k != "PASS")
    return g
OUT["gate"] = gate(); OUT["built_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
json.dump(OUT, open(R + "/receipts/RECEIPT_r15_mechgate.json", "w"), indent=1)
for s in ("42", "2027"):
    for tag in ("D_A0I_s" + s, "D_FI_s" + s):
        r = OUT["arms"][tag]; print("\n==", tag, "parity gross %.2e carry_ex %.2e" % (r["parity_gross_maxabs"], r["parity_carry_ex_maxabs"]))
        for wn in ("W_ALPHA", "KING_LIVE", "Y2026"):
            w = r[wn]; print("  [%s n=%d] kills/anchor %.3f | book carry_ex/gt %.4f" % (wn, w["both_chains"]["n_anchors"], w["kills_per_anchor"], w["carry_ex_pug_mean"]))
            for k in ("both_chains", "either_chain", "deep_short"):
                b = w[k]; print("     %-12s flagged/anchor %6.2f  leaked/anchor %6.2f  frac_neg %6.1f%%  leaked gross %.3f%% (p90 %.3f%% max %.3f%%)  carry paid %.4f bps" % (
                    k, b["flagged_per_anchor"], b["leaked_per_anchor"], 100 * b["frac_flagged_negative"], 100 * b["leaked_gross_share_mean"], 100 * b["leaked_gross_share_p90"], 100 * b["leaked_gross_share_max"], b["leaked_carry_paid_bps_mean"]))
print("\nGATE", json.dumps(OUT["gate"], indent=1)); print("DONE_r15_mechgate")
