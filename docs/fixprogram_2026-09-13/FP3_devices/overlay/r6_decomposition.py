#!/usr/bin/env python3
"""R6 decomposition (independent review 8ba6d6a5 §3–§4): for each r6 arm, split the paired Δ (variant − baseline, net_ex per target gross) into the TRIGGER anchors
(accounted book differs from baseline) and the OTHER anchors; count restoration events (budget back to full after a cut); and on the trigger anchors decompose the
BASELINE book's return into long-leg price, short-leg price (HR × y4, bps per target gross), carry_ex and cost_ex from the record — does the short leg keep rising after
the trigger, or does the book earn on the longs? usage: r6_decomposition.py <probe_dir> <meta.npz> <out.json>"""
import sys, glob, os, json, time, hashlib, numpy as np
PD, META, OUT = sys.argv[1:4]; WA0, UB = 1656547200, 1788120000
M = np.load(META, allow_pickle=True); E = M["E_ts"].astype(np.int64); y4 = np.asarray(M["y4"], float); pos = {int(t): i for i, t in enumerate(E)}
def load(tag):
    z = np.load(f"{PD}/w10_ablation_series_V4_A0_dyn_s42_{tag}.npz", allow_pickle=True); C = [str(c) for c in z["cols"]]; rec = np.asarray(z["d30_n2_c42_rec"], float)
    return rec[:, C.index("ts")].astype(np.int64), rec, C, np.asarray(z["d30_n2_c42_HR"], float), np.asarray(z["d30_n2_c42_W"], float)
ts0, rec0, C, HR0, T0 = load("OVLnone"); gt = rec0[:, C.index("gross_total")]; g0 = rec0[:, C.index("net_ex")] / gt
I = np.array([pos[int(t)] for t in ts0]); Y = np.where(np.isfinite(y4[I]), y4[I], 0.0)
pl_long0 = (np.where(HR0 > 0, HR0, 0.0) * Y).sum(1) * 1e4 / gt; pl_short0 = (np.where(HR0 < 0, HR0, 0.0) * Y).sum(1) * 1e4 / gt
carry0 = rec0[:, C.index("carry_ex")] / gt; cost0 = rec0[:, C.index("cost_ex")] / gt
WA = (ts0 >= WA0) & (ts0 <= UB); out = {"device": "r6_decomposition.py", "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "utc": time.strftime("%FT%TZ", time.gmtime()), "arms": {}}
for p in sorted(glob.glob(f"{PD}/w10_ablation_series_V4_A0_dyn_s42_OVL_r6*.npz")):
    tag = os.path.basename(p).split("_OVL_")[1][:-4]
    if tag.startswith("r6c"): continue
    ts, rec, _, HR, T = load("OVL_" + tag); assert np.array_equal(ts, ts0)
    g = rec[:, C.index("net_ex")] / gt; d = g - g0; ratio = np.abs(HR).sum(1) / np.maximum(np.abs(HR0).sum(1), 1e-9); trig = WA & (ratio < 1 - 1e-6)
    restore = WA & np.concatenate([[False], (ratio[:-1] < 1 - 1e-6) & (ratio[1:] >= 1 - 1e-6)])          # first full-budget anchor after a cut
    tot = float(np.nan_to_num(d[WA]).sum()); din = float(np.nan_to_num(d[trig]).sum()); dout = float(np.nan_to_num(d[WA & ~trig]).sum())
    out["arms"][tag] = {"n_trigger": int(trig.sum()), "n_restore_events": int(restore.sum()), "sum_delta_total": tot, "sum_delta_in_trigger": din, "sum_delta_outside_trigger": dout, "share_outside": (dout / tot if tot else None),
        "mean_delta_restore_anchor": float(np.nan_to_num(d[restore]).mean()) if restore.sum() else None,
        "baseline_on_trigger_anchors": {"n": int(trig.sum()), "net": float(g0[trig].mean()), "price_long": float(pl_long0[trig].mean()), "price_short": float(pl_short0[trig].mean()), "carry": float(carry0[trig].mean()), "cost": float(cost0[trig].mean()),
                                        "short_leg_negative_frac": float((pl_short0[trig] < 0).mean()), "book_positive_frac": float((g0[trig] > 0).mean())},
        "baseline_on_all_WA": {"net": float(g0[WA].mean()), "price_long": float(pl_long0[WA].mean()), "price_short": float(pl_short0[WA].mean()), "carry": float(carry0[WA].mean()), "cost": float(cost0[WA].mean())},
        "baseline_next_anchor_after_trigger": {"net": float(g0[WA & np.concatenate([[False], trig[:-1]])].mean()), "price_short": float(pl_short0[WA & np.concatenate([[False], trig[:-1]])].mean())}}
json.dump(out, open(OUT, "w"), indent=1)
for tag, a in out["arms"].items():
    b = a["baseline_on_trigger_anchors"]; print(f"{tag:22s} trig {a['n_trigger']:4d} restores {a['n_restore_events']:4d} | Δ total {a['sum_delta_total']:+.0f} in-trigger {a['sum_delta_in_trigger']:+.0f} outside {a['sum_delta_outside_trigger']:+.0f} (share outside {a['share_outside']:.2f}) restore-anchor mean Δ {a['mean_delta_restore_anchor'] if a['mean_delta_restore_anchor'] is None else round(a['mean_delta_restore_anchor'],3)} | baseline on trigger: net {b['net']:+.2f} long {b['price_long']:+.2f} short {b['price_short']:+.2f} carry {b['carry']:+.2f} cost {b['cost']:.2f} | short<0 frac {b['short_leg_negative_frac']:.2f} | next anchor net {a['baseline_next_anchor_after_trigger']['net']:+.2f} short {a['baseline_next_anchor_after_trigger']['price_short']:+.2f}")
a = list(out["arms"].values())[0]["baseline_on_all_WA"]; print("baseline all W_ALPHA: net %+.2f long %+.2f short %+.2f carry %+.2f cost %.2f" % (a["net"], a["price_long"], a["price_short"], a["carry"], a["cost"]))
