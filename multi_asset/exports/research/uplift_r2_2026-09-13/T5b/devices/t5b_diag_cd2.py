#!/usr/bin/env python3
"""t5b_diag_cd2.py — POST-HOC diagnostic (not in SPEC_T5b; written after G-CARRY-CD2 came back red). Does not change any frozen reading.
Localises the T1-D2-panel vs producer-ledger carry disagreement on CD2 anchors:
 (1) per-anchor decomposition vs T1 D2 columns carry_L / carry_S / non8h_carry / non8h_gross / st15_carry / coh_gross;
 (2) ledger interval field vs observed settlement spacing (last two settlement times <= A) for every name with |w| > 1e-6;
 (3) worst anchors: top |w*c4| names with ledger iv, observed spacing, age of last settlement, and c4 under spacing-derived iv.
Launch: env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5b_diag_cd2.py <T5b dir> CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING
"""
import os, sys, json, time
T5B = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
sys.path.insert(0, T5B + "/devices")
import numpy as np
import t5b_common as TC
SPEC_SHA = "92d901034b14eea09fea221fe4ca88b96b649d81e9955caf1dfa0aea570e5b87"; assert TC.sha(T5B + "/SPEC_T5b.md") == SPEC_SHA
P = T5B + "/private/ws"; utc = TC.utc
SYM = [str(s) for s in np.load(P + "/xfer_ref.npz", allow_pickle=True)["symbols"]]; sidx = {s: j for j, s in enumerate(SYM)}; NW = len(SYM)
LED = TC.Ledger([P + "/aux.json", P + "/aux_pre_m1_20260904.json"])
D2 = np.load(T5B + "/../T1/receipts/pod2/T1_d2.npz", allow_pickle=True); DC = [str(c) for c in D2["cols"]]; DD = D2["D"]
STALE15 = ["ANKRUSDT", "AXSUSDT", "ENJUSDT", "FLOWUSDT", "GMTUSDT", "IOSTUSDT", "KAVAUSDT", "MASKUSDT", "ONTUSDT", "RVNUSDT", "SKLUSDT", "STGUSDT", "XTZUSDT", "ZILUSDT", "ZRXUSDT"]
st = np.zeros(NW, bool); st[[sidx[s] for s in STALE15]] = True
ALLOWED = np.array([1.0, 2.0, 4.0, 6.0, 8.0])
def load_tl(A):
    d = json.load(open(f"{P}/target_live/{A}.json")); w = np.zeros(NW)
    for s, x in d["weights"].items(): w[sidx[s]] += float(x)
    return w
out = dict(per_anchor=[], interval_flags={}, worst={})
for rw in DD:
    A = int(rw[DC.index("A")])
    if not (1788350400 <= A <= 1788998400): continue
    w = load_tl(A); g = np.abs(w).sum(); c4, rn8, rn8f, ivv, ftv = LED.vectors(SYM, A)
    n8 = np.isfinite(ivv) & (ivv != 8.0) & np.isfinite(rn8)
    L = w > 0; S = w < 0
    mine = dict(carry_L=float((w[L] * c4[L]).sum() / g * 1e4), carry_S=float((w[S] * c4[S]).sum() / g * 1e4), non8h_carry=float((w[n8] * c4[n8]).sum() / g * 1e4), non8h_gross=float(np.abs(w[n8]).sum() / g),
                st15_carry=float((w[st] * c4[st]).sum() / g * 1e4), coh_gross=float(np.abs(w[S & np.isfinite(rn8) & (rn8 <= -0.0010)]).sum() / g))
    t1 = {k: float(rw[DC.index(k)]) for k in mine}
    # interval check on held names
    flags = []
    c4_sp = c4.copy()
    for j in np.where(np.abs(w) > 1e-6)[0]:
        s = SYM[j]; ft = LED.ft.get(s)
        if not ft: continue
        import bisect
        k = bisect.bisect_right(ft, A) - 1
        if k < 1 or not np.isfinite(ivv[j]): continue
        sp = (ft[k] - ft[k - 1]) / 3600.0; sp_snap = float(ALLOWED[np.argmin(np.abs(ALLOWED - sp))]) if 0 < sp <= 24 else None
        if sp_snap is not None and sp_snap != ivv[j]:
            age_h = (A - ft[k]) / 3600.0
            if A - ft[k] <= 12 * 3600: c4_sp[j] = LED.rate[s][k] * (4.0 / sp_snap)
            flags.append(dict(symbol=s, w_unit=float(w[j] / g), ledger_iv=float(ivv[j]), spacing_h=sp, spacing_snap=sp_snap, age_last_h=age_h, rate=LED.rate[s][k], contrib_mine=float(w[j] * c4[j] / g * 1e4), contrib_spacing_iv=float(w[j] * c4_sp[j] / g * 1e4)))
    carry_mine = float((w * c4).sum() / g * 1e4); carry_sp = float((w * c4_sp).sum() / g * 1e4)
    rec = dict(utc=utc(A), t1_carry=float(rw[DC.index("carry")]), mine_carry=carry_mine, mine_carry_spacing_iv=carry_sp, d_mine=carry_mine - float(rw[DC.index("carry")]), d_spacing_iv=carry_sp - float(rw[DC.index("carry")]),
               d_components={k: mine[k] - t1[k] for k in mine}, n_interval_flags=len(flags))
    out["per_anchor"].append(rec); out["interval_flags"][utc(A)] = sorted(flags, key=lambda x: -abs(x["contrib_mine"] - x["contrib_spacing_iv"]))[:10]
    if abs(rec["d_mine"]) > 0.2:
        top = np.argsort(-np.abs(w * c4))[:8]
        out["worst"][utc(A)] = [dict(symbol=SYM[j], w_unit=float(w[j] / g), c4_bps=float(c4[j] * 1e4), ledger_iv=(float(ivv[j]) if np.isfinite(ivv[j]) else None),
                                     last_ft_age_h=(float((A - ftv[j]) / 3600.0) if np.isfinite(ftv[j]) else None), rn8_bp=(float(rn8f[j] * 1e4) if np.isfinite(rn8f[j]) else None)) for j in top]
for rec in out["per_anchor"]:
    dc = rec["d_components"]
    print(rec["utc"], "d_mine %+.4f  d_if_spacing_iv %+.4f | dL %+.4f dS %+.4f d_non8h %+.4f d_non8h_gross %+.5f d_st15 %+.4f d_coh_gross %+.5f | iv_flags %d" % (rec["d_mine"], rec["d_spacing_iv"], dc["carry_L"], dc["carry_S"], dc["non8h_carry"], dc["non8h_gross"], dc["st15_carry"], dc["coh_gross"], rec["n_interval_flags"]))
for a, v in out["worst"].items():
    print("WORST", a, json.dumps(v)[:1500])
for a in ("2026-09-02 20:00Z", "2026-09-03 00:00Z", "2026-09-08 16:00Z", "2026-09-09 16:00Z", "2026-09-10 00:00Z"):
    print("IVFLAGS", a, json.dumps(out["interval_flags"].get(a))[:1500])
out["self_sha256"] = TC.sha(os.path.abspath(__file__)); out["label"] = "POST-HOC diagnostic, not pre-registered; does not alter SPEC readings"
json.dump(out, open(T5B + "/receipts/RECEIPT_T5b_diag_cd2.json", "w"), indent=1)
print("DONE_t5b_diag_cd2", len(out["per_anchor"]))
