"""§4.4 二审 · 本地评估器(2026-08-21, Session 6737834a-P2): 读 jpline 装置产物(event_preshrink_booklevel_server.json + .npz),
补算: ① 事件后逐锚轨迹(gross 比值 / 累计 Δ净额 vs 事件后偏移 k, 各臂) ② 纸面 vs 书级相对差(作废线 30%) ③ 通道分解表
(事件锚 / 下1锚 / 下2-6 / 其余; S1 底座 vs S0 底座 vs restore) ④ 逐年表 ⑤ 判据汇总; 写 results/event_preshrink_booklevel_2026-08-21.json。
输入 SHA256 记录在输出 meta。口径同装置头(net_pg=(pnl−trn×C−carry)/S0_gross×2)。"""
import json, hashlib, os, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, "results")
SRV = os.path.join(RES, "event_preshrink_booklevel_server.json"); NPZ = os.path.join(RES, "event_preshrink_booklevel.npz")
OUT = os.path.join(RES, "event_preshrink_booklevel_2026-08-21.json")
PAPER = json.load(open(os.path.join(RES, "event_preshrink_2026-08-21.json")))
S = json.load(open(SRV)); z = np.load(NPZ); ANN = np.sqrt(6 * 365); G = 2.0; C1 = 4.137
ts = z["ts"]; yr = z["yr"]; ev = z["ev_idx"]; g0 = z["S0_gross"]; n = len(ts)
assert list(map(int, S["meta"]["event_ts"])) == [int(ts[i]) for i in ev], "event set mismatch"
paper_ev = [int(__import__("calendar").timegm(__import__("time").strptime(e["date"] + " 16:00", "%Y-%m-%d %H:%M"))) for e in PAPER["redteam_main"]["per_event"]]
assert paper_ev == [int(ts[i]) for i in ev], "一审/二审 event set differ"


def net_pg(tag, C=C1):
    return (z[f"{tag}_pnl"] - z[f"{tag}_trn"] * C - np.nan_to_num(z[f"{tag}_carry"])) / g0 * G


def sharpe(x): return float(x.mean() / x.std(ddof=1) * ANN)


base1, base0 = net_pg("S1"), net_pg("S0")
ARMS = {k: (k, "S1") for k in z.files if k.startswith("fomc_") and k.endswith("_pnl")}
traj = {}; decomp = {}; yearly = {}
for key in sorted({k[:-4] for k in z.files if k.startswith("fomc_") and k.endswith("_pnl")}):
    b = base0 if "S0base" in key else base1; btag = "S0" if "S0base" in key else "S1"
    x = net_pg(key); d = x - b; gr = z[f"{key}_gross"] / z[f"{btag}_gross"]
    K = 120; cum = np.zeros(K + 1); grk = np.zeros(K + 1); cnt = np.zeros(K + 1)
    for e in ev:
        for k in range(0, K + 1):
            i = e + k
            if i < n:
                cum[k] += d[i]; grk[k] += gr[i]; cnt[k] += 1
    c = np.cumsum(cum)  # cumulative Δ (summed over events) by offset
    traj[key] = {"offset_0_1_2_6_12_24_48_120_cumsum_bps": [float(c[k]) for k in (0, 1, 2, 6, 12, 24, 48, 120)],
                 "gross_ratio_mean_by_offset_0_1_2_6_12_24_48_120": [float(grk[k] / cnt[k]) for k in (0, 1, 2, 6, 12, 24, 48, 120)],
                 "total_d_net_bps": float(d.sum()), "d_mean": float(d.mean()), "d_sharpe": sharpe(x) - sharpe(b),
                 "fires": int(z[f"{key}_fires"].sum()), "fires_base": int(z[f"{btag}_fires"].sum())}
    # decomposition: event anchor / next1 / next2-6 / rest
    at0 = float(d[ev].sum()); at1 = float(d[np.minimum(ev + 1, n - 1)].sum()); idx26 = np.unique(np.concatenate([np.minimum(ev + k, n - 1) for k in range(2, 7)])); at26 = float(d[idx26].sum())
    decomp[key] = {"event_anchor": at0, "next1": at1, "next2_6": at26, "rest": float(d.sum() - at0 - at1 - at26), "total": float(d.sum())}
    yearly[key] = {int(y): {"d_mean": float(d[yr == y].mean()), "base_sharpe": sharpe(b[yr == y]), "alt_sharpe": sharpe(x[yr == y]), "event_mean_base": float(b[ev[yr[ev] == y]].mean()) if (yr[ev] == y).any() else None} for y in sorted(set(yr.tolist()))}
# channel split for main arm m0.75: stop channel = rest(S1) - rest(S0base); band drag = rest(S0base); with restore
main = S["arms"]["fomc_m0.75"]["C4.137"]; paper_dm = PAPER["arms"]["primary_S1_carry"]["k1_m0.75"]["d_mean"]; paper_ds = PAPER["arms"]["primary_S1_carry"]["k1_m0.75"]["d_sharpe"]
rel = abs(main["d_mean"] - paper_dm) / abs(paper_dm)
summary = {"paper_vs_book": {"paper_d_mean": paper_dm, "book_d_mean": main["d_mean"], "rel_diff": rel, "paper_void": bool(rel > 0.30), "paper_d_sharpe": paper_ds, "book_d_sharpe": main["d_sharpe"]},
           "channels_m0.75_bps": {"event_anchor_S1": decomp["fomc_m0.75"]["event_anchor"], "event_anchor_S0base": decomp["fomc_S0base_m0.75"]["event_anchor"],
                                   "path_after_event_S1(next1+next2_6+rest)": decomp["fomc_m0.75"]["next1"] + decomp["fomc_m0.75"]["next2_6"] + decomp["fomc_m0.75"]["rest"],
                                   "path_after_event_S0base": decomp["fomc_S0base_m0.75"]["next1"] + decomp["fomc_S0base_m0.75"]["next2_6"] + decomp["fomc_S0base_m0.75"]["rest"],
                                   "stop_channel_est(S1_rest - S0base_rest)": decomp["fomc_m0.75"]["rest"] - decomp["fomc_S0base_m0.75"]["rest"],
                                   "band_drag_est(S0base rest)": decomp["fomc_S0base_m0.75"]["rest"]}}
for k in ("fomc_m0.75_restore", "fomc_S0base_m0.75_restore"):
    if k in decomp: summary["channels_m0.75_bps"][k] = decomp[k]
crit = {}
for arm in ("fomc_m0.75", "fomc_m0.75_restore", "fomc_S0base_m0.75", "fomc_S0base_m0.75_restore", "fomc_m0.5", "fomc_m0.5_restore", "fomc_m0.9"):
    if arm in S["arms"]:
        c = S["arms"][arm]["C4.137"]; c2 = S["arms"][arm]["C3.52"]
        e1 = c["d_mean"] >= 0; e2 = c["event_var_reduction"] >= 0.2; e3 = c["d_sharpe"] >= 0.03; e4 = (c["cost_share_of_pretax_gain"] is not None) and (0 <= c["cost_share_of_pretax_gain"] <= 1 / 3)
        crit[arm] = {"d_mean": c["d_mean"], "d_mean_per_year_bps": c["d_mean_per_year_bps"], "d_sharpe": c["d_sharpe"], "event_var_reduction": c["event_var_reduction"], "cost_share": c["cost_share_of_pretax_gain"],
                     "sum_d_cost_bps": c["sum_d_cost_turnover_bps"], "d_turnover_units_per_event": c["d_turnover_units_per_event"], "fires": S["arms"][arm]["fires"], "fires_base": S["arms"][arm].get("fires_base"),
                     "E1": bool(e1), "E2": bool(e2), "E3": bool(e3), "E4": bool(e4), "PASS": bool(e1 and e2 and e3 and e4),
                     "C3.52": {"d_mean": c2["d_mean"], "d_sharpe": c2["d_sharpe"], "cost_share": c2["cost_share_of_pretax_gain"]}}
out = {"meta": {"server_json_sha256": hashlib.sha256(open(SRV, "rb").read()).hexdigest(), "npz_sha256": hashlib.sha256(open(NPZ, "rb").read()).hexdigest(), "server_meta": S["meta"], "paper_json": "event_preshrink_2026-08-21.json"},
       "receipts": S["receipts"], "base": S["base"], "base_S0": S.get("base_S0"), "criteria_by_arm": crit, "summary": summary, "decomposition_bps": decomp, "trajectory": traj, "yearly": yearly,
       "shifted_placebo": S["shifted_placebo"], "event_block_bootstrap": S["event_block_bootstrap_main"], "random_placebo": {k: v for k, v in S["random_placebo_main"].items()},
       "arms_full": S["arms"]}
json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=False)
print("paper_vs_book", summary["paper_vs_book"]); print("channels", json.dumps(summary["channels_m0.75_bps"], indent=0))
for k, v in crit.items(): print(k, {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "C3.52"})
for k, v in traj.items(): print("TRAJ", k, "cum", [round(u, 0) for u in v["offset_0_1_2_6_12_24_48_120_cumsum_bps"]], "gross", [round(u, 3) for u in v["gross_ratio_mean_by_offset_0_1_2_6_12_24_48_120"]], "fires", v["fires"], "/", v["fires_base"])
print("WROTE", OUT)
