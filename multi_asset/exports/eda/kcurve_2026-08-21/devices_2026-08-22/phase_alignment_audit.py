"""PH · 相位对齐审计 — 本机侧装置(2026-08-22, Session 6737834a-PH)。可重跑; 只读实盘仓(~/dl_quant_live)与研究仓, 只写研究仓 results/。

回答 team-lead 派工 A/B/(C 合并)/D:
  A 事实对齐表 — 从生产代码逐位读出(本文件 FACTS 常量 + 对实盘日志的实测偏移): 面板行标 T 的含义 / 实盘名义锚 N 用哪一行 / 实盘持仓窗 / 离线 Y4[T] 的窗口。
  B 量化相位效应(实盘 2026-08-05→08-21) — 取实盘每锚【场所持仓读回】向量(position_readback, fapi/v3/account@post_anchor, ≈N+16.7min),
     用实盘仓 1h K 线缓存(state/panel_cache/klines_1h.npz, 只读)计算同一向量在
       (i) 离线族窗口 [N+1h, N+5h](= Y4[行标 N] 的窗口)   (ii) 实盘名义窗口 [N, N+4h](1h K 线)   (iii) 实盘实测窗口 [N+~1.3min, N+4h+~1.3min](锚捕获 mid 向量)
     下的毛盈亏(USDT), 并与实盘权益逐锚变化(daily_nav.nav 相邻行差, 扣出入金; 另给扣费/funding 的毛当量)比相关/回归/均绝误差。
  C 合并 jpline 装置 phase_alignment_replay_jp.py 的结果 JSON(若已存在于 results/)。
【判据冻结, 先于看数】(B): "哪个窗口更贴实盘" = 与 Δnav_gross_equiv 的 Pearson ρ 更高且均绝误差更小; 若 (ii)/(iii) 的 ρ 高于 (i) 且 (i)-(ii) 逐锚差的 sd ≥ 0.3×sd(ii)
   ⇒ 实盘持仓窗 = [N, N+4h], 与离线族 [N+1h, N+5h] 不同相位(事实成立); 若 (i) 的 ρ 反而更高 ⇒ 事实表有错, 回头重读代码。
输出: results/phase_alignment_audit_2026-08-22.json。
"""
import os, sys, json, glob, time, hashlib
import numpy as np, pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE = os.path.expanduser("~/dl_quant_live")
PLOG = f"{LIVE}/state/live/pilot_log"
KC = f"{LIVE}/state/panel_cache/klines_1h.npz"
OUT = f"{HERE}/results/phase_alignment_audit_2026-08-22.json"
JP_JSON = f"{HERE}/results/phase_alignment_jp_2026-08-22.json"
D0, D1 = "20260805", "20260822"          # anchors with nominal in [08-05 00:00Z, 08-21 20:00Z]; 08-22 00:00Z row used only as the NEXT-anchor reference
HOUR = 3600


def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()


# ------------------------------------------------------------------ A. facts (code-read, each with file:line evidence)
FACTS = {
    "panel_row_T_content": {
        "ts semantic": "行标 T = 1h K 线 open_time(训练: multi_asset/data/build_wide_panel.py:41-51 grid=openTime_ms; 实盘: signal/fapi_source.py:188 open_ms → live_panel.KlineCache.ts)",
        "price": "CLOSE[T] = bar [T, T+1h) 的收盘价 = T+1h 时刻价格 ⇒ 价格类特征截至 T+1h",
        "funding": "FUND[T] = 最后一次结算 fts ≤ T(训练 build_wide_panel.py:91 searchsorted side=right−1; 实盘 signal/funding_panel.py:176 同式, 且 live_panel.build_live_panel 传 until_ms=ts[-1]=T)⇒ funding 截至 T(比价格旧 1h; 在行标 23/03/07… 上不含 N 时刻的结算)",
        "Y4": "Y4[T] = logc[T+4] − logc[T] = log CLOSE[T+4h bar]/CLOSE[T bar] = 价格 (T+1h)→(T+5h)(build_wide_dl.py:150-151 `Y[:T-H] = logc[H:] - logc[:-H]`; data/build_yr168.py:36 fwd(H) 同式); jpline 装置另给 Y4 = Σ Y1 四段 的逐位收据",
        "CL4": "CL4 = 行索引 %4==0 & member & finite Y4(build_wide_dl.py:154-157 keep=arange(0,T,4)); 网格起点 2021-01-01 00:00Z ⇒ CL4 行 = 行标 00/04/08/12/16/20Z(实测 jpline: 六相各 1977 行)",
        "offline preds": "king/s2 newgen 预测仅在行标 00/04/…/20Z 有限(实测 1642×6 / 1636-1638×6), 由 run 目录 fold_k_head_scores(te_rows = 原生 CL 行)合成 ⇒ 离线族决策时刻 = T+1h = 01/05/09/13/17/21Z, 持仓窗 [T+1h, T+5h]",
    },
    "live_nominal_anchor_N": {
        "schedule": "launchd com.dlquant.live.anchor StartCalendarInterval 每 4h 整点(本机 UTC+8 的 08/12/16/20/00/04 = 00/04/08/12/16/20Z); book_config.schedule_check 以 4h 网格名义锚 + 容差判 on_schedule",
        "row used": "anchor = len(ts)−1(compute_preds.py:209); ts[-1] = last_closed = floor(now/1h)−1h(live_panel.py:115-116; fapi klines endTime=closed_end−1 排除成形 bar, fapi_source.py:177-182)⇒ 行标 T = N−1h; preds.anchor_ts_ms = ts[-1](compute_preds.py:348)",
        "measured": "preds_latest.json 08-22 00:00:59Z 计算: anchor_ts_ms = 2026-08-21 23:00Z(= N−1h); 记忆 king_cadence_8h_live: 16:00Z 锚携带 15:00Z 行",
        "king cadence": "相位键 = 名义锚(compute_preds.nominal_anchor_epoch, hour%8==0 ⇒ 名义 00/08/16Z 刷新)= 行标 23/07/15Z 的行; 离线族刷新 ti%8==0 = 行标 00/08/16Z(决策 01/09/17Z)",
        "s2/funding cadence": "实盘 compute_preds 每锚都重算 s2 与 funding 腿(只有 king 有 hold); 离线族 s2 ti%24==0 持 24h、funding ti%8==0 持 8h(w2_live_replay.py/cond_stop_tail.py)— 与相位无关的另一处离线≠实盘(记录, 不在本任务裁)",
    },
    "live_holding_window": {
        "orders": "run_anchor: phase_A 在名义 N 后 ~0.6-1.9 min 捕获锚价并挂 maker 单(anchors.jsonl anchor_ts 实测偏移见 B.offsets), k 窗 900s(config k_seconds), phase_B 补单 ~N+15-17 min, position_readback/daily_nav 读回 ≈N+16.7 min",
        "window": "持仓 ≈ [N+~1.3…17 min, N+4h+~1.3…17 min] ⇒ 一阶近似 [N, N+4h]; 用 1h K 线表达 = CLOSE[N+3h bar]/CLOSE[N−1h bar]",
        "offline Y4 of the row live uses": "实盘用行 T=N−1h ⇒ Y4[N−1h] = 价格 N→N+4h = 实盘窗 ✓(自洽); 离线族用行 T=N(hour%4==0)⇒ Y4[N] = 价格 N+1h→N+5h ≠ 实盘窗(差 1h 相位)",
    },
    "conclusion_A": "两套各自自洽(特征截至 τ, 收益窗 [τ, τ+4h]); 差别只在 τ 的钟点: 离线族 τ∈{01,05,09,13,17,21}Z, 实盘 τ∈{00,04,08,12,16,20}Z ⇒ W2b 发现 (a) 成立; 后果大小见 B/C",
}


# ------------------------------------------------------------------ B. live period quantification
def load_logs():
    days = sorted(d for d in os.listdir(PLOG) if d.isdigit() and D0 <= d <= D1)
    A, R, NV = [], [], []
    for d in days:
        for nm, lst in (("anchors", A), ("position_readback", R), ("daily_nav", NV)):
            f = f"{PLOG}/{d}/{nm}.jsonl"
            if os.path.exists(f):
                for line in open(f):
                    line = line.strip()
                    if line:
                        row = json.loads(line); row["_day"] = d; lst.append(row)
    return A, R, NV


def part_B():
    A, R, NV = load_logs()
    z = np.load(KC, allow_pickle=True)
    kts = z["ts"].astype(np.int64) // 1000; ksym = [str(s) for s in z["symbols"]]; C = z["close"]
    kidx = {int(t): i for i, t in enumerate(kts)}; sidx = {s: j for j, s in enumerate(ksym)}

    def px(sym, t_open):
        """CLOSE of the 1h bar opening at t_open (= price at t_open+1h); NaN if absent."""
        i = kidx.get(int(t_open)); j = sidx.get(sym)
        if i is None or j is None: return np.nan
        return float(C[i, j])

    # anchors (exclude rehearsal 'R' prefix; require on-schedule within ±20 min)
    anc = []
    for a in A:
        if str(a.get("rebalance_id", "")).startswith("R"): continue
        N = int(round(a["anchor_ts"] / 14400.0) * 14400)
        if abs(a["anchor_ts"] - N) > 20 * 60: continue
        anc.append({"N": N, "anchor_ts": float(a["anchor_ts"]), "mids": json.loads(a["mid_at_anchor_vector"]) if isinstance(a.get("mid_at_anchor_vector"), str) else (a.get("mid_at_anchor_vector") or {}),
                    "realized_gross": a.get("realized_gross"), "day": a["_day"], "opening_halted": a.get("opening_halted")})
    anc.sort(key=lambda r: r["N"]); byN = {r["N"]: r for r in anc}
    # held book per anchor from the post-anchor venue readback
    held = {}
    for r in R:
        if r.get("source") != "fapi/v3/account@post_anchor": continue
        N = int(round(float(r["anchor_ts"]) / 14400.0) * 14400)
        v = r.get("venue_position_notional")
        if v is None or not np.isfinite(float(v)) or abs(float(v)) < 1e-9: continue
        held.setdefault(N, {})[r["symbol"]] = float(v)
        byN.setdefault(N, {}).setdefault("read_ts", float(r.get("read_ts") or 0))
    # nav rows: per anchor (nav_ts ≈ N+16.7 min) with cumulative-since-00Z realised by type + external flow
    navs = []
    for n in NV:
        nt = float(n["nav_ts"]); N = int(round(nt / 14400.0) * 14400)
        if abs(nt - N) > 30 * 60: continue
        bt = n.get("realised_by_type") or {}
        navs.append({"N": N, "nav": float(n["nav"]), "nav_ts": nt, "day": n["_day"], "flow": float(n.get("external_flow_usdt") or 0.0),
                     "comm": float(bt.get("COMMISSION") or 0.0), "fund": float(bt.get("FUNDING_FEE") or 0.0), "rpnl": float(bt.get("REALIZED_PNL") or 0.0)})
    navs.sort(key=lambda r: r["N"]); navN = {r["N"]: r for r in navs}
    rows = []
    Ns = sorted(set(held) & set(byN))
    for N in Ns:
        if not (pd.Timestamp("2026-08-05", tz="UTC").timestamp() <= N <= pd.Timestamp("2026-08-21 20:00", tz="UTC").timestamp()): continue
        w = held[N]; a = byN[N]; gross = sum(abs(v) for v in w.values())
        # (i) offline window: price N+1h -> N+5h  == CLOSE[N+4h bar]/CLOSE[N bar]
        # (ii) live nominal window: price N -> N+4h == CLOSE[N+3h bar]/CLOSE[N-1h bar]
        # (iii) live measured window: anchor mids N+~1.3min -> next anchor mids
        nxt = byN.get(N + 14400)
        p_i = p_ii = p_iii = 0.0; cov_i = cov_ii = cov_iii = 0.0
        for s, v in w.items():
            c0, c4 = px(s, N), px(s, N + 4 * HOUR)
            if np.isfinite(c0) and np.isfinite(c4) and c0 > 0: p_i += v * (c4 / c0 - 1.0); cov_i += abs(v)
            b0, b4 = px(s, N - HOUR), px(s, N + 3 * HOUR)
            if np.isfinite(b0) and np.isfinite(b4) and b0 > 0: p_ii += v * (b4 / b0 - 1.0); cov_ii += abs(v)
            if nxt is not None:
                m0 = a["mids"].get(s); m1 = nxt["mids"].get(s)
                if m0 and m1 and m0 > 0: p_iii += v * (m1 / m0 - 1.0); cov_iii += abs(v)
        nv0 = navN.get(N); nv1 = navN.get(N + 14400)
        dnav = dflow = dcomm = dfund = np.nan
        if nv0 and nv1:
            dnav = nv1["nav"] - nv0["nav"]
            same_day = nv0["day"] == nv1["day"]
            dflow = (nv1["flow"] - nv0["flow"]) if same_day else nv1["flow"]      # cumulative since 00:00Z; day boundary: new day's cumulative (prev-day tail after 20:16Z assumed 0)
            dcomm = (nv1["comm"] - nv0["comm"]) if same_day else nv1["comm"]
            dfund = (nv1["fund"] - nv0["fund"]) if same_day else nv1["fund"]
        rows.append({"N": N, "N_utc": pd.Timestamp(N, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%MZ"), "day": a["day"], "n_held": len(w), "gross_held": gross,
                     "anchor_offset_min": (a["anchor_ts"] - N) / 60.0, "readback_offset_min": ((a.get("read_ts") or np.nan) - N) / 60.0,
                     "pnl_i_offline_window": p_i, "pnl_ii_live_1h": p_ii, "pnl_iii_live_mids": (p_iii if nxt is not None else np.nan),
                     "cov_i": cov_i / gross if gross else np.nan, "cov_ii": cov_ii / gross if gross else np.nan, "cov_iii": (cov_iii / gross if (gross and nxt is not None) else np.nan),
                     "dnav": dnav, "dflow": dflow, "dcomm": dcomm, "dfund": dfund,
                     "dnav_ex_flow": (dnav - dflow) if np.isfinite(dnav) else np.nan,
                     "dnav_gross_equiv": (dnav - dflow - dcomm - dfund) if np.isfinite(dnav) else np.nan,
                     "next_anchor_present": nxt is not None})
    df = pd.DataFrame(rows)
    # keep anchors with full coverage in both K-line windows (>=95% of gross priced) — edge of cache for the last anchors
    ok = df[(df.cov_i >= 0.95) & (df.cov_ii >= 0.95)].copy()

    def stats(d, tag):
        o = {"n": int(len(d))}
        if len(d) < 5: return o
        x_i, x_ii, x_iii = d.pnl_i_offline_window.values, d.pnl_ii_live_1h.values, d.pnl_iii_live_mids.values
        diff = x_i - x_ii
        o.update({"mean_pnl_i": round(float(x_i.mean()), 2), "mean_pnl_ii": round(float(x_ii.mean()), 2), "sd_pnl_i": round(float(x_i.std(ddof=1)), 2), "sd_pnl_ii": round(float(x_ii.std(ddof=1)), 2),
                  "diff_i_minus_ii": {"mean": round(float(diff.mean()), 2), "sd": round(float(diff.std(ddof=1)), 2), "mean_abs": round(float(np.abs(diff).mean()), 2),
                                      "sd_ratio_to_sd_ii": round(float(diff.std(ddof=1) / x_ii.std(ddof=1)), 3)},
                  "corr_i_ii": round(float(np.corrcoef(x_i, x_ii)[0, 1]), 4)})
        m3 = np.isfinite(x_iii)
        if m3.sum() >= 5:
            o["corr_ii_iii"] = round(float(np.corrcoef(x_ii[m3], x_iii[m3])[0, 1]), 4); o["corr_i_iii"] = round(float(np.corrcoef(x_i[m3], x_iii[m3])[0, 1]), 4)
            o["mean_pnl_iii"] = round(float(x_iii[m3].mean()), 2)
        for tgt in ("dnav_ex_flow", "dnav_gross_equiv"):
            y = d[tgt].values; m = np.isfinite(y)
            if m.sum() >= 5:
                o[f"vs_{tgt}"] = {"n": int(m.sum()), "mean_target": round(float(y[m].mean()), 2)}
                for nm, x in (("i_offline", x_i), ("ii_live_1h", x_ii), ("iii_live_mids", x_iii)):
                    mm = m & np.isfinite(x)
                    if mm.sum() >= 5:
                        slope = float(np.polyfit(x[mm], y[mm], 1)[0])
                        o[f"vs_{tgt}"][nm] = {"rho": round(float(np.corrcoef(x[mm], y[mm])[0, 1]), 4), "slope": round(slope, 3),
                                              "mae": round(float(np.abs(y[mm] - x[mm]).mean()), 2), "rmse": round(float(np.sqrt(((y[mm] - x[mm]) ** 2).mean())), 2)}
        return o
    incident_days = {"20260821"}
    res = {"inputs": {"klines_cache": KC, "klines_cache_sha256": sha(KC), "klines_span_utc": [str(pd.Timestamp(int(kts[0]), unit="s", tz="UTC")), str(pd.Timestamp(int(kts[-1]), unit="s", tz="UTC"))],
                      "pilot_log_days": [D0, D1], "n_anchor_rows": len(A), "n_readback_rows": len(R), "n_nav_rows": len(NV)},
           "offsets_min": {"anchor_capture_after_nominal": {"mean": round(float(df.anchor_offset_min.mean()), 2), "min": round(float(df.anchor_offset_min.min()), 2), "max": round(float(df.anchor_offset_min.max()), 2)},
                           "readback_after_nominal": {"mean": round(float(np.nanmean(df.readback_offset_min)), 2), "min": round(float(np.nanmin(df.readback_offset_min)), 2), "max": round(float(np.nanmax(df.readback_offset_min)), 2)}},
           "n_anchors_total": int(len(df)), "n_anchors_priced": int(len(ok)),
           "all_priced": stats(ok, "all"), "ex_incident_day_0821": stats(ok[~ok.day.isin(incident_days)], "ex0821"),
           "per_anchor": [{k: (round(float(v), 3) if isinstance(v, (float, np.floating)) else v) for k, v in r.items()} for r in ok.to_dict("records")]}
    # verdict per frozen reading
    s = res["ex_incident_day_0821"]
    try:
        r_i = s["vs_dnav_gross_equiv"]["i_offline"]["rho"]; r_ii = s["vs_dnav_gross_equiv"]["ii_live_1h"]["rho"]; r_iii = s["vs_dnav_gross_equiv"].get("iii_live_mids", {}).get("rho")
        sdr = s["diff_i_minus_ii"]["sd_ratio_to_sd_ii"]
        res["verdict_B"] = {"rho_i": r_i, "rho_ii": r_ii, "rho_iii": r_iii, "sd_ratio_diff": sdr,
                            "reading": ("实盘持仓窗 = [N, N+4h]; 离线族窗 [N+1h, N+5h] 与之不同相位(事实成立)" if (r_ii > r_i and sdr >= 0.3) else
                                        ("窗口差异小于判据阈(sd 比 <0.3)但 (ii) 更贴" if r_ii > r_i else "(i) 反而更贴实盘 — 事实表需重读"))}
    except Exception as e:
        res["verdict_B"] = {"error": str(e)}
    return res


def main():
    out = {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "session": "6737834a-PH", "script_sha256": sha(os.path.abspath(__file__)),
           "A_facts": FACTS}
    out["B_live_quantification"] = part_B()
    if os.path.exists(JP_JSON):
        jp = json.load(open(JP_JSON)); out["C_jpline_replay"] = jp; out["C_jpline_json_sha256"] = sha(JP_JSON)
    else:
        out["C_jpline_replay"] = {"status": "jpline JSON not yet present at " + JP_JSON}
    json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=False, default=str)
    b = out["B_live_quantification"]
    print(json.dumps({"offsets": b["offsets_min"], "n": [b["n_anchors_total"], b["n_anchors_priced"]], "all": b["all_priced"], "ex0821": b["ex_incident_day_0821"], "verdict_B": b.get("verdict_B")}, indent=1, ensure_ascii=False, default=str))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
