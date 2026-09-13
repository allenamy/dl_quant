#!/usr/bin/env python3
"""t1_h2.py — Mac, READ-ONLY copies (PREREG_T1 §6 H2: E2a / E2b; GATE H2; §7(4) descriptive shares from REAL).
E2a: for each of the 15 stale-span names, every stored producer ledger row k>=1: gap_k = (ft_k - ft_{k-1})/3600 snapped exactly as
     shadow_loop_v3.py L342 (nearest of {1,2,4,6,8}, gap outside (0,24] -> 8); compare with the recorded iv_k. Count mismatches on LIVE rows
     (ft in [2026-08-26 04Z, 2026-09-12 00Z]) and on all rows; LIVE gap mode.
E2b: recompute the producer EMA (shadow_loop_v3.py L344-349: rn = rate*8/iv, a = 1-0.5**(max(dt,1)/3d)) over the stored rows with (i) the
     recorded iv and (ii) the snapped-gap iv; relative difference to the stored ema acc.
Independent venue cross-check: the executor income ledger funding.jsonl rows carry funding_interval_h "from /fapi/v1/fundingInfo on the venue
that charged it" (read-only copy) — compare with the producer's recorded iv at the same settlement timestamps.
Descriptive (all names): count of producer ledger rows where recorded iv != snapped gap.
Descriptive (REAL): the 15 names' share of realized gross and of realized price / funding in LIVE_REAL.
"""
import os, sys, json, time, hashlib, collections
T1 = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
PREREG_SHA = "9548214267b5a44900ba90fee6b2fb2bbeb77964d562628b77678b16c56777f6"; AMEND_SHA = "a7628a7268cad50976470e5b6334c9086af9805bf786dac0ed51f496374da373"; AMEND2_SHA = "12b262fd5b5ec47b7741c10b500baa9bc726cfc873ef7c5b07edf39b897e7207"
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
assert sha(T1 + "/PREREG_T1_edge_diagnosis_2026-09-13.md") == PREREG_SHA and sha(T1 + "/PREREG_AMENDMENT_1_T1_2026-09-13.md") == AMEND_SHA and sha(T1 + "/PREREG_AMENDMENT_2_T1_2026-09-13.md") == AMEND2_SHA
AUX = T1 + "/private/aux_20260913.json"; EPI = T1 + "/private/funding_span_episode_live.json"; SPAN = T1 + "/private/funding_span_table.json"
BASE = T1 + "/private/pilot_log"; REALN = T1 + "/receipts/T1_real_names.npz"
L0 = 1787716800; L1 = 1789214400   # 2026-08-26 04Z .. 2026-09-12 00Z (ledger rows)
LR0 = 1787716800; LR1 = 1789156800 # LIVE_REAL anchors
aux = json.load(open(AUX)); LED = aux["ledger_tail"]; EMA = aux["ema"]
epi = json.load(open(EPI)); STALE = sorted(x.split(":")[0] for x in epi["findings"]); assert len(STALE) == 15
span = json.load(open(SPAN))["table"]
def snap(gap):
    return float(min([1.0, 2.0, 4.0, 6.0, 8.0], key=lambda a: abs(a - (gap if 0 < gap <= 24 else 8.0))))
GH2 = dict(in_ledger=[s for s in STALE if LED.get(s)], in_ema=[s for s in STALE if s in EMA])
GH2["PASS"] = bool(len(GH2["in_ledger"]) == 15 and len(GH2["in_ema"]) == 15)
E2 = {}
for s in STALE:
    rows = LED.get(s) or []
    ft = np.array([float(r[0]) for r in rows]); rate = np.array([float(r[1]) for r in rows]); iv = np.array([float(r[2]) if (len(r) > 2 and r[2]) else np.nan for r in rows])
    gaps = np.diff(ft) / 3600.0; sg = np.array([snap(g) for g in gaps])
    mis_all = int(np.sum(iv[1:] != sg)); live = (ft[1:] >= L0) & (ft[1:] <= L1)
    mis_live = int(np.sum((iv[1:] != sg) & live))
    live_ivs = collections.Counter(iv[1:][live].tolist()); live_gaps = collections.Counter(sg[live].tolist())
    def ema(ivarr):
        acc = None; last = None
        for k in range(len(ft)):
            v = rate[k] * (8.0 / ivarr[k]) if np.isfinite(ivarr[k]) and ivarr[k] > 0 else rate[k]
            if acc is None: acc = v; last = ft[k]
            else:
                a = 1 - 0.5 ** (max(ft[k] - last, 1) / (3 * 86400.0)); acc = acc + a * (v - acc); last = ft[k]
        return acc
    acc_st = float(EMA[s]["acc"]) if s in EMA else np.nan
    ivsnap = np.concatenate([[iv[0]], sg]) if len(ft) else iv
    acc_rec = ema(iv); acc_snap = ema(ivsnap)
    rel = lambda a: float(abs(a - acc_st) / max(abs(acc_st), 1e-6))
    first_4h_row = None
    for k in range(1, len(ft)):
        if sg[k - 1] == 4.0: first_4h_row = dict(ft_utc=time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(ft[k]))), recorded_iv=float(iv[k])); break
    E2[s] = dict(n_rows=int(len(ft)), first_row_utc=time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(ft[0]))) if len(ft) else None, last_row_utc=time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(ft[-1]))) if len(ft) else None,
                 span_table_interval_h=float(span[s]["median_interval_h"]) if s in span else None,
                 mismatch_all=mis_all, mismatch_live=mis_live, n_live_rows=int(live.sum()), live_recorded_iv_counts={str(k): v for k, v in live_ivs.items()}, live_snapped_gap_counts={str(k): v for k, v in live_gaps.items()},
                 all_recorded_iv_counts={str(k): v for k, v in collections.Counter(iv.tolist()).items()}, first_stored_row_with_4h_gap=first_4h_row,
                 ema_stored=acc_st, ema_recomputed_recorded_iv=acc_rec, ema_recomputed_snapped_iv=acc_snap, rel_diff_recorded_iv=rel(acc_rec), rel_diff_snapped_iv=rel(acc_snap))
# venue cross-check from the executor income ledger
VEN = collections.defaultdict(dict)
for d in sorted(x for x in os.listdir(BASE) if x.isdigit()):
    p = f"{BASE}/{d}/funding.jsonl"
    if not os.path.exists(p): continue
    for ln in open(p):
        try: r = json.loads(ln)
        except Exception: continue
        if r.get("funding_interval_h") is None: continue
        VEN[r["symbol"]][int(float(r["settlement_ts"]))] = float(r["funding_interval_h"])
venue_cmp = {}; allv = dict(n=0, mismatch=0, examples=[])
for s, rows in LED.items():
    if s not in VEN: continue
    for r in rows:
        t = int(float(r[0])); vi = VEN[s].get(t)
        if vi is None: continue
        rec = float(r[2]) if (len(r) > 2 and r[2]) else np.nan
        allv["n"] += 1
        if rec != vi:
            allv["mismatch"] += 1
            if len(allv["examples"]) < 15: allv["examples"].append(dict(symbol=s, settlement_utc=time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(t)), producer_iv=rec, venue_iv=vi))
        if s in STALE:
            c = venue_cmp.setdefault(s, dict(n=0, mismatch=0, venue_iv_counts=collections.Counter()))
            c["n"] += 1; c["mismatch"] += int(rec != vi); c["venue_iv_counts"][str(vi)] += 1
for s in venue_cmp: venue_cmp[s]["venue_iv_counts"] = dict(venue_cmp[s]["venue_iv_counts"])
# all-names inferred-interval inconsistency (descriptive)
alln = dict(n_rows=0, mismatch=0, by_symbol={})
for s, rows in LED.items():
    if len(rows) < 2: continue
    ft = np.array([float(r[0]) for r in rows]); iv = np.array([float(r[2]) if (len(r) > 2 and r[2]) else np.nan for r in rows])
    sg = np.array([snap(g) for g in np.diff(ft) / 3600.0]); mm = int(np.sum(iv[1:] != sg))
    alln["n_rows"] += int(len(rows) - 1); alln["mismatch"] += mm
    if mm: alln["by_symbol"][s] = mm
# REAL descriptive shares
Z = np.load(REALN, allow_pickle=True); names = Z["names"]; cols = [str(c) for c in Z["cols"]]; X = Z["rows"]; ci = {c: i for i, c in enumerate(cols)}
AN = Z["anchors"]; acols = [str(c) for c in Z["anchor_cols"]]; ai = {c: i for i, c in enumerate(acols)}
la = (AN[:, ai["A"]] >= LR0) & (AN[:, ai["A"]] <= LR1); live_A = set(AN[la, ai["A"]].astype(np.int64).tolist())
rl = np.array([int(a) in live_A for a in X[:, ci["A"]]]); st = np.isin(names, STALE)
held = X[:, ci["held"]] > 0
g_all = np.nansum(np.abs(X[rl & held, ci["notional_at_mid"]])); g_st = np.nansum(np.abs(X[rl & held & st, ci["notional_at_mid"]]))
REALS = dict(live_anchors=int(la.sum()), gross_share_stale15=float(g_st / g_all) if g_all > 0 else None,
             price_usd_stale15=float(X[rl & st, ci["price_usd"]].sum()), price_usd_all=float(X[rl, ci["price_usd"]].sum()),
             funding_usd_stale15=float(X[rl & st, ci["funding_usd"]].sum()), funding_usd_all=float(X[rl, ci["funding_usd"]].sum()),
             note="gross share = sum |q*mid(E)| over held rows; price/funding in USD over LIVE_REAL anchors; book layer, not fund-leg layer")
H2 = dict(falsified_rule="all 15: mismatch_live == 0 and rel_diff_recorded_iv <= 1e-3", survives_rule="any: LIVE row recorded iv 8 where gap 4, or rel_diff_snapped_iv > 5%")
H2["all_mismatch_live_zero"] = all(E2[s]["mismatch_live"] == 0 for s in STALE)
H2["all_rel_diff_recorded_le_1e-3"] = all(E2[s]["rel_diff_recorded_iv"] <= 1e-3 for s in STALE)
H2["any_live_iv8_where_gap4"] = any(any((ft_iv == "8.0") for ft_iv in E2[s]["live_recorded_iv_counts"]) and E2[s]["live_snapped_gap_counts"].get("4.0", 0) > 0 and E2[s]["mismatch_live"] > 0 for s in STALE)
H2["any_rel_diff_snapped_gt_5pct"] = any(E2[s]["rel_diff_snapped_iv"] > 0.05 for s in STALE)
H2["all_live_rows_present"] = all(E2[s]["n_live_rows"] > 0 for s in STALE)
H2["VERDICT"] = ("NOT DECIDABLE" if not (GH2["PASS"] and H2["all_live_rows_present"]) else
                 "FALSIFIED" if (H2["all_mismatch_live_zero"] and H2["all_rel_diff_recorded_le_1e-3"]) else
                 "SURVIVES" if (H2["any_live_iv8_where_gap4"] or H2["any_rel_diff_snapped_gt_5pct"]) else "NOT DECIDABLE")
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, amendment1_sha256=AMEND_SHA, amendment2_sha256=AMEND2_SHA,
          inputs={AUX: sha(AUX), EPI: sha(EPI), SPAN: sha(SPAN), REALN: sha(REALN)}, stale15=STALE, gate_H2=GH2, E2=E2, venue_crosscheck_stale15=venue_cmp, venue_crosscheck_all_names=allv,
          producer_ledger_all_names_iv_vs_gap=alln, real_shares=REALS, H2=H2, env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}),
          built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
json.dump(RC, open(T1 + "/receipts/RECEIPT_T1_h2.json", "w"), indent=1, default=str)
print(json.dumps(dict(gate_H2=GH2["PASS"], H2=H2, venue_all=dict(n=allv["n"], mismatch=allv["mismatch"]), alln=dict(n_rows=alln["n_rows"], mismatch=alln["mismatch"])), indent=1))
