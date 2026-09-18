#!/usr/bin/env python3
"""R6 decomposition v2 (review round 9 §2–§3): price P&L is computed ONLY over the anchor's MEMBER set (as the engine does: pnl_r = Σ_m smr[m]·y4[i,m]); carry_ex is a
COST (net_ex = pnl − carry − cost) and is reported as such; identity residual |net − (long + short − carry − cost)| per anchor is reported. Continuation is tested on the
FIXED basket held at the trigger anchor: the short names at anchor k (HR<0) valued with the next anchors' returns Y[k+1], Y[k+2] (same weights, no rebalance), likewise longs.
usage: r6_decomposition.py <probe_dir> <meta.npz> <out.json>"""
import sys, glob, os, json, time, hashlib, numpy as np
PD, META, OUT = sys.argv[1:4]; WA0, UB = 1656547200, 1788120000
M = np.load(META, allow_pickle=True); E = M["E_ts"].astype(np.int64); y4 = np.asarray(M["y4"], float); MEM = M["members"]; pos = {int(t): i for i, t in enumerate(E)}
def load(tag):
    z = np.load(f"{PD}/w10_ablation_series_V4_A0_dyn_s42_{tag}.npz", allow_pickle=True); C = [str(c) for c in z["cols"]]; rec = np.asarray(z["d30_n2_c42_rec"], float)
    return rec[:, C.index("ts")].astype(np.int64), rec, C, np.asarray(z["d30_n2_c42_HR"], float)
ts0, rec0, C, HR0 = load("OVLnone"); gt = rec0[:, C.index("gross_total")]; g0 = rec0[:, C.index("net_ex")] / gt; pnl0 = rec0[:, C.index("pnl_ex")] / gt
I = np.array([pos[int(t)] for t in ts0]); N = HR0.shape[1]
memmask = np.asarray(np.load(f"{PD}/w10_ablation_series_V4_A0_dyn_s42_OVLnone.npz", allow_pickle=True)["d30_n2_c42_M"], bool)   # v3: the engine's OWN pricing member set per anchor (MEMBERS_TOPN + umask), exported by the hooked engine
Y = np.where(np.isfinite(y4[I]) & memmask, y4[I], 0.0)                                   # member-only pricing, exactly the engine's population
H0 = np.nan_to_num(HR0); pl_long0 = (np.where(H0 > 0, H0, 0.0) * Y).sum(1) * 1e4 / gt; pl_short0 = (np.where(H0 < 0, H0, 0.0) * Y).sum(1) * 1e4 / gt
carry0 = rec0[:, C.index("carry_ex")] / gt; cost0 = rec0[:, C.index("cost_ex")] / gt
ident = pnl0 - (pl_long0 + pl_short0); ident_net = g0 - (pl_long0 + pl_short0 - carry0 - cost0)
WA = (ts0 >= WA0) & (ts0 <= UB)
# fixed-basket continuation: basket at k valued at k+1 and k+2 (member-only pricing of those anchors)
def fixed_next(sign, lag):
    out = np.full(len(ts0), np.nan)
    for k in range(len(ts0) - lag):
        w = np.where((H0[k] * sign) > 0, H0[k], 0.0); out[k] = float((w * Y[k + lag]).sum() * 1e4 / gt[k])
    return out
fs1, fs2, fl1, fl2 = fixed_next(-1, 1), fixed_next(-1, 2), fixed_next(+1, 1), fixed_next(+1, 2)
out = {"device": "r6_decomposition.py", "version": "v3 engine-exported pricing member set, carry as cost, fixed-basket continuation", "self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "utc": time.strftime("%FT%TZ", time.gmtime()),
       "identity_residual": {"max_abs_pnl_minus_legs": float(np.nanmax(np.abs(ident[WA]))), "max_abs_net_identity": float(np.nanmax(np.abs(ident_net[WA]))), "note": "engine pnl_ex vs long+short on the member set; net = long + short − carry − cost"},
       "baseline_all_WA": {"net": float(g0[WA].mean()), "price_long": float(pl_long0[WA].mean()), "price_short": float(pl_short0[WA].mean()), "carry_cost": float(carry0[WA].mean()), "cost": float(cost0[WA].mean()), "fixed_short_next1": float(np.nanmean(fs1[WA])), "fixed_short_next2": float(np.nanmean(fs2[WA])), "fixed_long_next1": float(np.nanmean(fl1[WA]))}, "arms": {}}
for p in sorted(glob.glob(f"{PD}/w10_ablation_series_V4_A0_dyn_s42_OVL_r6*.npz")):
    tag = os.path.basename(p).split("_OVL_")[1][:-4]
    if tag.startswith("r6c"): continue
    ts, rec, _, HR = load("OVL_" + tag); assert np.array_equal(ts, ts0)
    g = rec[:, C.index("net_ex")] / gt; d = g - g0; ratio = np.abs(HR).sum(1) / np.maximum(np.abs(HR0).sum(1), 1e-9); trig = WA & (ratio < 1 - 1e-6)
    restore = WA & np.concatenate([[False], (ratio[:-1] < 1 - 1e-6) & (ratio[1:] >= 1 - 1e-6)])
    tot = float(np.nan_to_num(d[WA]).sum()); din = float(np.nan_to_num(d[trig]).sum()); dout = float(np.nan_to_num(d[WA & ~trig]).sum())
    out["arms"][tag] = {"n_trigger": int(trig.sum()), "n_restore_events": int(restore.sum()), "sum_delta_total": tot, "sum_delta_in_trigger": din, "sum_delta_outside_trigger": dout, "share_outside": (dout / tot if tot else None), "mean_delta_restore_anchor": float(np.nan_to_num(d[restore]).mean()) if restore.sum() else None,
        "baseline_on_trigger_anchors": {"n": int(trig.sum()), "net": float(g0[trig].mean()), "price_long": float(pl_long0[trig].mean()), "price_short": float(pl_short0[trig].mean()), "carry_cost": float(carry0[trig].mean()), "cost": float(cost0[trig].mean()), "short_leg_negative_frac": float((pl_short0[trig] < 0).mean()), "identity_check_max": float(np.nanmax(np.abs(ident_net[trig])))},
        "fixed_basket_continuation": {"short_next1": float(np.nanmean(fs1[trig])), "short_next2": float(np.nanmean(fs2[trig])), "long_next1": float(np.nanmean(fl1[trig])), "long_next2": float(np.nanmean(fl2[trig])), "short_next1_negative_frac": float(np.nanmean(fs1[trig] < 0)), "n": int(trig.sum())}}
json.dump(out, open(OUT, "w"), indent=1)
print("identity residual max |pnl − legs| %.4f | max |net identity| %.4f" % (out["identity_residual"]["max_abs_pnl_minus_legs"], out["identity_residual"]["max_abs_net_identity"]))
b = out["baseline_all_WA"]; print("baseline all: net %+.2f = long %+.2f + short %+.2f − carry %.2f − cost %.2f | fixed short next1 %+.2f next2 %+.2f | fixed long next1 %+.2f" % (b["net"], b["price_long"], b["price_short"], b["carry_cost"], b["cost"], b["fixed_short_next1"], b["fixed_short_next2"], b["fixed_long_next1"]))
for tag, a in out["arms"].items():
    t = a["baseline_on_trigger_anchors"]; f = a["fixed_basket_continuation"]
    print(f"{tag:30s} trig {a['n_trigger']:4d} | baseline on trigger: net {t['net']:+.2f} = long {t['price_long']:+.2f} + short {t['price_short']:+.2f} − carry {t['carry_cost']:.2f} − cost {t['cost']:.2f} (id {t['identity_check_max']:.3f}) | FIXED basket next1: short {f['short_next1']:+.2f} (neg frac {f['short_next1_negative_frac']:.2f}) long {f['long_next1']:+.2f} | next2: short {f['short_next2']:+.2f} long {f['long_next2']:+.2f} | Δ share outside {a['share_outside']:.2f}")
