#!/usr/bin/env python3
"""真实成本回放(在役形态 A0, 动态席位, 可交易掩码, RAW 记账, 实测成本档)的【窗口分布】与【regime 持续性】。只读。
在 pod2 上跑(臂文件在 /workspace/fp2_2026-09/realcost/arms/); 输出 JSON 到 stdout。

g 的定义与判官 fp2_per_year_table.py L33/L72 相同: 逐锚 g = net_ex / gross_total(bps / 锚 / 单位 gross), 窗口 g = 窗内逐锚 g 的均值。
另报「比值的和」Σnet_ex / Σgross_total, 仅作对照(实盘有入金, 两个定义差很多)。
窗口 = W_ALPHA 口径(ts ≤ UB 去掉前 900 锚), 与判官同。
① 143 锚(≈24 天)滚动窗的分位数, 以及实盘读数在其中的分位(实盘读数由调用参数给, 来自 LIVE_G_DECOMPOSITION 收据)
② 持续性: 以一天为步, 前 143 锚窗 g 与其后 H 锚(143 / 540 / 1095)的均值 g 的关系; 条件于前窗 ≤ −1.0 与 ≤ 下四分位
usage (pod): python backtest_window_stats.py <live_g_time_weighted> <live_g_dollar_weighted> <live_price_time_weighted> <live_nav_return>"""
import datetime as dt, hashlib, json, sys
import numpy as np

ARMS = "/workspace/fp2_2026-09/realcost/arms/w10_ablation_series_V4_A0_dyn_s{}.npz"
VARIANT = "d30_n2_c42_rec"
UB = dt.datetime(2026, 8, 30, 20, tzinfo=dt.timezone.utc).timestamp()
W = 143


def main():
    live_g_tw, live_g_dw, live_price_tw, live_nav = map(float, sys.argv[1:5])
    out = {"device_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "window_anchors": W, "variant": VARIANT,
           "live_inputs": {"g_time_weighted": live_g_tw, "g_dollar_weighted": live_g_dw, "price_time_weighted": live_price_tw, "nav_return": live_nav},
           "seeds": {}}
    for s in ("42", "2027"):
        p = ARMS.format(s); z = np.load(p, allow_pickle=True)
        cols = [str(c) for c in z["cols"]]; r = z[VARIANT]; C = {c: r[:, i] for i, c in enumerate(cols)}
        ts = C["ts"]; idx = np.where(ts <= UB)[0][900:]
        gt = C["gross_total"][idx]
        if not (np.isfinite(r[idx]).all() and (gt > 0).all()): raise SystemExit("non-finite or non-positive gross in arm " + s)
        g = C["net_ex"][idx] / gt; pr = C["pnl_ex"][idx] / gt; t = ts[idx]
        cs = lambda a: np.concatenate([[0.0], np.cumsum(a)])
        Sg, Sp, Sne, Sgt = cs(g), cs(pr), cs(C["net_ex"][idx]), cs(gt)
        gw = (Sg[W:] - Sg[:-W]) / W; pw = (Sp[W:] - Sp[:-W]) / W; gw_rs = (Sne[W:] - Sne[:-W]) / (Sgt[W:] - Sgt[:-W])
        lr = np.log1p(2.0 * g * 1e-4); Sl = cs(lr); navw = np.expm1(Sl[W:] - Sl[:-W])
        t_end = t[W - 1:]; y26 = t_end >= dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc).timestamp()
        q = lambda a, qs: {str(x): round(float(np.quantile(a, x)), 4) for x in qs}
        pct = lambda a, x: round(float((a <= x).mean()), 4)
        seed = {"arm": p, "arm_sha256": hashlib.sha256(open(p, "rb").read()).hexdigest(), "n_anchors_W_ALPHA": int(len(g)),
                "g_W_ALPHA_mean_of_ratios": round(float(g.mean()), 4), "g_W_ALPHA_ratio_of_sums": round(float(Sne[-1] / Sgt[-1]), 4),
                "n_windows": int(len(gw)),
                "window_g_quantiles": q(gw, (0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9)),
                "window_price_quantiles": q(pw, (0.05, 0.1, 0.25, 0.5)),
                "window_nav2x_quantiles": q(navw, (0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9)),
                "live_percentiles": {"g_time_weighted": pct(gw, live_g_tw), "g_dollar_weighted_vs_ratio_of_sums_windows": pct(gw_rs, live_g_dw),
                                     "price_time_weighted": pct(pw, live_price_tw), "nav_return_2x": pct(navw, live_nav),
                                     "g_time_weighted_2026_windows_only": pct(gw[y26], live_g_tw)},
                "last_window_to_UB": {"end_utc": dt.datetime.fromtimestamp(t_end[-1], dt.timezone.utc).isoformat(),
                                      "g": round(float(gw[-1]), 4), "price": round(float(pw[-1]), 4)},
                "persistence": {}}
        for H in (143, 540, 1095):
            tr, nx = [], []
            for i in range(W, len(g) - H + 1, 6):
                tr.append((Sg[i] - Sg[i - W]) / W); nx.append((Sg[i + H] - Sg[i]) / H)
            tr, nx = np.array(tr), np.array(nx); q25 = np.quantile(tr, 0.25); ve = tr <= -1.0; lo = tr <= q25
            seed["persistence"][str(H)] = {"n_starts_daily_step": int(len(tr)), "uncond_mean_next": round(float(nx.mean()), 4),
                                           "next_mean_given_trailing_le_q25": round(float(nx[lo].mean()), 4),
                                           "next_mean_given_trailing_le_minus1": round(float(nx[ve].mean()), 4), "n_trailing_le_minus1": int(ve.sum()),
                                           "corr_trailing_next": round(float(np.corrcoef(tr, nx)[0, 1]), 4),
                                           "p_next_negative_given_le_minus1": round(float((nx[ve] < 0).mean()), 4),
                                           "p_next_negative_uncond": round(float((nx < 0).mean()), 4),
                                           "note": "overlapping windows (daily step) — observations are NOT independent; read as descriptive"}
        out["seeds"][s] = seed
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
