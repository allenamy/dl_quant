#!/usr/bin/env python3
"""r17_selection_channel.py — EXPLORATORY (NOT pre-registered; PREREG §2.5 only asked for the conditional's direction).
Bounds the one channel the unconditional fill model cannot price: unfilled legs are where the price moved the intended way.
penalty (bps/anchor/unit gross) = unfilled matched turnover x [E(adv | unfilled, notional-weighted) - E(adv | all sent, intent-weighted)]
adv = signed mid move to the NEXT anchor (~4h), from the ledger only (r17_fill_groups.npz). Day-block bootstrap on the difference.
Reads no environment variable."""
import os, json, hashlib, time, numpy as np
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Z = np.load(R + "/receipts/r17_fill_groups.npz", allow_pickle=True); J = json.load(open(R + "/receipts/RECEIPT_r17_judge.json"))
adv = Z["adv"]; I = Z["I"]; F = Z["F"]; E = Z["E"]; ok = np.isfinite(adv); adv, I, F, E = adv[ok], I[ok], F[ok], E[ok]; U = np.maximum(I - F, 0.0)
days = np.array([time.strftime("%Y%m%d", time.gmtime(int(t))) for t in E]); ud = sorted(set(days)); idx = {d: np.where(days == d)[0] for d in ud}
def stat(sel):
    return float((adv[sel] * U[sel]).sum() / U[sel].sum() - (adv[sel] * I[sel]).sum() / I[sel].sum())
pt = stat(np.arange(len(adv))); rng = np.random.default_rng([20260905, 901]); o = np.empty(2000)
for b in range(2000):
    p = rng.integers(0, len(ud), len(ud)); sel = np.concatenate([idx[ud[q]] for q in p]); o[b] = stat(sel)
ci = [float(np.percentile(o, 2.5)), float(np.percentile(o, 97.5))]
out = dict(self_sha256=hashlib.sha256(open(__file__, "rb").read()).hexdigest(), status="EXPLORATORY, not pre-registered", n_groups=int(len(adv)), n_days=len(ud),
           adv_unfilled_weighted=float((adv * U).sum() / U.sum()), adv_intent_weighted=float((adv * I).sum() / I.sum()), excess_bps_per_unit_unfilled=pt, excess_ci95_dayblock=ci, unfilled_share_of_sent_intent=float(U.sum() / I.sum()))
for s in ("42", "2027"):
    ii = J["A0DET"][s]["instr_WA"]; un = ii["tau_intent_matched"] - ii["tau_exec_matched"]; un_sent = un - ii["dust_notional_over_intent"] * ii["tau_intent_matched"]
    out["seed_" + s] = dict(unfilled_matched_turnover_total=un, unfilled_matched_turnover_excl_dust=un_sent,
                            penalty_bps_per_anchor_excl_dust=dict(point=un_sent * pt, ci95=[un_sent * ci[0], un_sent * ci[1]]), penalty_bps_per_anchor_incl_dust=dict(point=un * pt, ci95=[un * ci[0], un * ci[1]]))
json.dump(out, open(R + "/receipts/RECEIPT_r17_selection_channel_EXPLORATORY.json", "w"), indent=1)
print(json.dumps(out, indent=1))
