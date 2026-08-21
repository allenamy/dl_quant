"""§4.4 事件日历方差预缩 · 纸面叠加装置(第一轮, 2026-08-22, Session 6737834a-P2)
===========================================================================================
输入(只读, SHA256 钉定; 不碰实盘仓/share/交易 API):
  results/series/w2_live_series_slim.npz  SHA256 = 502207ee7d2fc60c86d5073520118414cbb4f2dd92b033594413d803b4f11003
  docs/macro_event_calendar.md            SHA256 = 0d570ccaa6bf39a9caa0b61a47abd88271446c02589b5ea1a08ed09cfa2fb6de
  事件 = FOMC 决议日(日历表内 2022–2026 共 37 个, 决议 14:00 ET = 18:00Z 夏令/19:00Z 冬令; 07-29-2026 在序列之外 ⇒ 36 个在样本内)。
  **CPI: 日历无已核实日期 ⇒ 不做(日历纪律: 禁止凭记忆填日期)。**
口径: net_t = (S1_net − S1_carry)/S0_gross × 2 = bps of NAV @gross2(与 §4.3 装置同式); 敏感性 S1 不含 carry。年化 √(6×365)。
  锚 = 名义 4h 锚(00/04/08/12/16/20Z), net_t 为锚 t → t+4h 持仓期的净额(前向); FOMC 18/19Z 落在 16Z 锚的持仓窗内。
装置(纸面叠加):
  事件前锚 = 事件时刻之前最近的 k 个锚(k=1: 16Z; k=2: 12Z+16Z), gross ×m(m ∈ {0.5, 0.75}); 事件后恢复;
  叠加后净额: 事件前锚 net'_t = m·net_t; 每个事件扣一次 |1−m|·G·4 bps×2(减仓+加回)记在首个缩减锚; 其余锚不变。
  主臂 = m0.75 × 前 1 锚。
★ 冻结判据(看数字前写定; 主臂, 全样本 9821 锚, 主口径):
  E1 净额均值 ≥ 基线;  E2 事件锚(被缩减的锚集合)方差 ↓ ≥ 20%(注: ×0.75 机械上 −43.75%, 此关实际只检查成本不改方差);  E3 夏普 ≥ 基线 + 0.03。
  全过 ⇒ 进二审; 任一不过 ⇒ 判负。先验块(事件锚 vs 非事件锚 均值/方差/最坏 5%)先报。
先验/红队: 同时段对照(同小时非事件锚); 市场方差(|r_s|,|mkt_ew|,|btc4|)在事件锚是否抬升(兼验证前向收益口径);
  逐年 σ 比值(镜像 RESULT_event_calendar §A 的逐年下行); 安慰剂: 事件日平移 ±1/±7 天 + 随机 36 个 16Z 锚(B=2000)的 Δ均值分布。
与 RESULT_event_calendar_and_wide_stop §A 的关系: §A 用"决议日及次日"整窗(432 锚)判关闭(σ 比 1.068<1.2); 本装置是锚级窗(1-2 锚), 即 §A 留档的"活口"; 两者互链。
输出: results/event_preshrink_2026-08-21.json
"""
import sys, json, time, hashlib, os, re, datetime as dt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
NPZ = os.path.join(HERE, "results", "series", "w2_live_series_slim.npz")
CAL = os.path.join(ROOT, "docs", "macro_event_calendar.md")
NPZ_SHA = "502207ee7d2fc60c86d5073520118414cbb4f2dd92b033594413d803b4f11003"
CAL_SHA = "0d570ccaa6bf39a9caa0b61a47abd88271446c02589b5ea1a08ed09cfa2fb6de"
OUT = os.path.join(HERE, "results", "event_preshrink_2026-08-21.json")
G = 2.0; ANN = np.sqrt(6 * 365); COST_BPS = 4.0; H = 4 * 3600
FROZEN = {"E1_mean_not_worse": True, "E2_event_var_reduction_min": 0.20, "E3_sharpe_gain_min": 0.03, "main_arm": {"k": 1, "m": 0.75},
          "arms": [[1, 0.5], [1, 0.75], [2, 0.5], [2, 0.75]], "cost_per_event_bps": "(1-m)*G*4*2", "G": G, "event_time": "14:00 America/New_York (FOMC decision)"}

for p, s in ((NPZ, NPZ_SHA), (CAL, CAL_SHA)):
    h = hashlib.sha256(open(p, "rb").read()).hexdigest(); assert h == s, f"SHA mismatch {p}: {h}"
z = np.load(NPZ, allow_pickle=True)
ts = z["ts"].astype(np.int64); yr = z["yr"].astype(int); n = len(ts)
rs = (z["mkt_ew"] - z["btc4"]).astype(float); mkt = z["mkt_ew"].astype(float); btc = z["btc4"].astype(float)
SERIES = {"primary_S1_carry": (z["S1_net"] - np.nan_to_num(z["S1_carry"])) / z["S0_gross"] * G,
          "S1_nocarry": z["S1_net"] / z["S0_gross"] * G}
hour = ((ts % 86400) // 3600).astype(int)
YEARS = sorted(set(yr.tolist()))


def sharpe(x):
    s = x.std(ddof=1); return float(x.mean() / s * ANN) if s > 0 else float("nan")


def es5(x):
    k = max(1, int(round(0.05 * len(x)))); return float(np.sort(x)[:k].mean())


# ---------- parse FOMC dates from the calendar ----------
txt = open(CAL, encoding="utf-8").read()
blk = txt.split("**FOMC 决议日 2022-2026**")[1].split("**加密原生排期事件**")[0]
dates = []
for line in blk.splitlines():
    mm = re.match(r"\s*(\d{4})(?:\(已过\))?:\s*(.*)", line)
    if mm:
        y = int(mm.group(1))
        for md in re.findall(r"(\d{2})-(\d{2})", mm.group(2)):
            dates.append(dt.date(y, int(md[0]), int(md[1])))
assert len(dates) == 37, f"expected 37 FOMC dates, parsed {len(dates)}"


def us_dst(d):
    """True if US daylight time on date d (2nd Sunday March .. 1st Sunday November)."""
    mar = dt.date(d.year, 3, 1); start = mar + dt.timedelta(days=(6 - mar.weekday()) % 7 + 7)
    nov = dt.date(d.year, 11, 1); end = nov + dt.timedelta(days=(6 - nov.weekday()) % 7)
    return start <= d < end


def event_utc(d):
    off = 4 if us_dst(d) else 5  # EDT=UTC-4, EST=UTC-5
    t = dt.datetime(d.year, d.month, d.day, 14, 0) + dt.timedelta(hours=off)
    return int((t - dt.datetime(1970, 1, 1)).total_seconds())


zi_check = None
try:
    from zoneinfo import ZoneInfo
    zi_check = all(int(dt.datetime(d.year, d.month, d.day, 14, 0, tzinfo=ZoneInfo("America/New_York")).timestamp()) == event_utc(d) for d in dates)
except Exception as e:
    zi_check = f"zoneinfo unavailable ({type(e).__name__}); hand-coded DST rule used"

ev_ts = np.array([event_utc(d) for d in dates], dtype=np.int64)
in_range = (ev_ts > ts[0]) & (ev_ts < ts[-1] + H)
EV = ev_ts[in_range]; EVD = [d for d, ok in zip(dates, in_range) if ok]
pos = np.searchsorted(ts, EV, side="left")  # first anchor index with ts >= event  ⇒ pre1 = pos-1
pre1 = pos - 1; pre2 = pos - 2; post1 = pos; post2 = pos + 1
ok_pre = np.array([0 <= i < n and (EV[j] - ts[i]) < H for j, i in enumerate(pre1)])  # pre1 anchor's holding window contains the event
assert ok_pre.all(), "some FOMC decisions have no anchor whose 4h window contains them"
assert all(hour[i] == 16 for i in pre1), f"pre1 hours {sorted(set(hour[pre1].tolist()))}"
assert all(hour[i] == 12 for i in pre2)
n_ev = len(EV)

RES = {"meta": {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "session": "6737834a-P2", "python": sys.version.split()[0], "numpy": np.__version__,
                "inputs": {"npz": os.path.relpath(NPZ, HERE), "npz_sha256": NPZ_SHA, "calendar": os.path.relpath(CAL, ROOT), "calendar_sha256": CAL_SHA},
                "n_anchors": int(n), "fomc_dates_parsed": len(dates), "fomc_in_sample": int(n_ev), "first_event": str(EVD[0]), "last_event": str(EVD[-1]),
                "dst_rule_zoneinfo_crosscheck": zi_check, "cpi": "not run: calendar has no verified CPI dates (calendar discipline forbids memory-filled dates)",
                "frozen_criteria": FROZEN, "caliber": "net=(S1_net−S1_carry)/S0_gross×2 bps of NAV @gross2; event anchor = last nominal anchor before 14:00 ET decision (16Z)"}}

# ---------- 1. prior: event anchors vs controls ----------
def desc(x):
    return {"n": int(len(x)), "mean": float(x.mean()), "sd": float(x.std(ddof=1)), "var": float(x.var(ddof=1)), "p5": float(np.percentile(x, 5)), "ES5": es5(x), "min": float(x.min()),
            "median": float(np.median(x)), "frac_neg": float((x < 0).mean())}


def tstat(a, b):
    return float((a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)))


ev_day = np.zeros(n, bool)
for j in range(n_ev):
    d0 = (EV[j] // 86400) * 86400; ev_day |= (ts >= d0) & (ts < d0 + 86400)
prior = {}
for tag, net in SERIES.items():
    P = {}
    for gname, idx in (("pre2_12Z", pre2), ("pre1_16Z", pre1), ("post1_20Z", post1), ("post2_00Z", post2)):
        hh = int(hour[idx[0]]); ctl = (hour == hh) & (~ev_day)
        x = net[idx]; c = net[ctl]
        P[gname] = {"event": desc(x), "control_same_hour_nonevent": desc(c), "t_mean_diff": tstat(x, c), "sd_ratio": float(x.std(ddof=1) / c.std(ddof=1)),
                    "mkt_abs_ratio": {"abs_rs": float(np.abs(rs[idx]).mean() / np.abs(rs[ctl]).mean()), "abs_mkt_ew": float(np.abs(mkt[idx]).mean() / np.abs(mkt[ctl]).mean()),
                                      "abs_btc4": float(np.abs(btc[idx]).mean() / np.abs(btc[ctl]).mean()), "sd_btc4_ratio": float(btc[idx].std(ddof=1) / btc[ctl].std(ddof=1)),
                                      "sd_rs_ratio": float(rs[idx].std(ddof=1) / rs[ctl].std(ddof=1))},
                    "by_year": {int(y): {"n": int((yr[idx] == y).sum()), "mean": float(x[yr[idx] == y].mean()), "sd": float(x[yr[idx] == y].std(ddof=1)) if (yr[idx] == y).sum() > 1 else None,
                                         "ctl_sd": float(c[yr[ctl] == y].std(ddof=1)), "sd_ratio": float(x[yr[idx] == y].std(ddof=1) / c[yr[ctl] == y].std(ddof=1)) if (yr[idx] == y).sum() > 1 else None}
                                for y in YEARS}}
    P["event_day_all6"] = {"event": desc(net[ev_day]), "control_nonevent": desc(net[~ev_day]), "t_mean_diff": tstat(net[ev_day], net[~ev_day]), "sd_ratio": float(net[ev_day].std(ddof=1) / net[~ev_day].std(ddof=1))}
    # all hours profile on event days vs non-event (mean & sd by hour) for the timing sanity check
    P["hour_profile"] = {int(h): {"event_mean": float(net[ev_day & (hour == h)].mean()), "event_sd": float(net[ev_day & (hour == h)].std(ddof=1)),
                                  "ctl_mean": float(net[~ev_day & (hour == h)].mean()), "ctl_sd": float(net[~ev_day & (hour == h)].std(ddof=1)),
                                  "sd_btc_event": float(btc[ev_day & (hour == h)].std(ddof=1)), "sd_btc_ctl": float(btc[~ev_day & (hour == h)].std(ddof=1))} for h in (0, 4, 8, 12, 16, 20)}
    prior[tag] = P
RES["prior"] = prior
p1 = prior["primary_S1_carry"]["pre1_16Z"]
print(f"PRIOR pre1(16Z) n={p1['event']['n']} mean {p1['event']['mean']:.2f} sd {p1['event']['sd']:.1f} ES5 {p1['event']['ES5']:.1f} | ctl mean {p1['control_same_hour_nonevent']['mean']:.2f} sd {p1['control_same_hour_nonevent']['sd']:.1f} ES5 {p1['control_same_hour_nonevent']['ES5']:.1f} | t {p1['t_mean_diff']:.2f} sd_ratio {p1['sd_ratio']:.3f} | btc sd ratio {p1['mkt_abs_ratio']['sd_btc4_ratio']:.2f} rs sd ratio {p1['mkt_abs_ratio']['sd_rs_ratio']:.2f}", flush=True)
for gname in ("pre2_12Z", "post1_20Z", "post2_00Z"):
    q = prior["primary_S1_carry"][gname]
    print(f"      {gname} mean {q['event']['mean']:.2f} sd_ratio {q['sd_ratio']:.3f} t {q['t_mean_diff']:.2f} btc sd ratio {q['mkt_abs_ratio']['sd_btc4_ratio']:.2f}", flush=True)


# ---------- 2. overlay arms ----------
def apply_overlay(net, k, m):
    netp = net.copy(); shrunk = np.zeros(n, bool)
    cost = (1.0 - m) * G * COST_BPS * 2.0
    for j in range(n_ev):
        idxs = [pos[j] - i for i in range(1, k + 1)]
        for i in idxs:
            netp[i] = m * net[i]; shrunk[i] = True
        netp[idxs[-1]] -= cost  # charge once per event at the first shrunk anchor (earliest)
    return netp, shrunk, cost


def arm_eval(net, k, m, label):
    netp, S, cost = apply_overlay(net, k, m)
    vb, va = net[S].var(ddof=1), netp[S].var(ddof=1)
    r = {"label": label, "k": k, "m": m, "cost_per_event_bps": cost, "n_events": int(n_ev), "n_shrunk_anchors": int(S.sum()),
         "base": {"mean": float(net.mean()), "sharpe": sharpe(net), "sd": float(net.std(ddof=1))},
         "alt": {"mean": float(netp.mean()), "sharpe": sharpe(netp), "sd": float(netp.std(ddof=1))},
         "d_mean": float(netp.mean() - net.mean()), "d_mean_pct": float((netp.mean() - net.mean()) / abs(net.mean())), "d_sharpe": sharpe(netp) - sharpe(net),
         "d_mean_per_year_bps": float((netp.sum() - net.sum()) / (n / 2190)),
         "event_var": {"base": float(vb), "alt": float(va), "reduction": float(1 - va / vb)},
         "shrunk_anchor_stats": {"mean_net": float(net[S].mean()), "sum_net": float(net[S].sum()), "sd": float(net[S].std(ddof=1))},
         "decomp_bps_total": {"pnl_forgone": float(-(1 - m) * net[S].sum()), "cost": float(-cost * n_ev), "check": float(netp.sum() - net.sum())},
         "by_year": {int(y): {"d_mean": float(netp[yr == y].mean() - net[yr == y].mean()), "base_sharpe": sharpe(net[yr == y]), "alt_sharpe": sharpe(netp[yr == y]),
                              "shrunk_mean_net": float(net[S & (yr == y)].mean()) if (S & (yr == y)).sum() else None, "n_ev": int((S & (yr == y)).sum())} for y in YEARS}}
    e1 = r["alt"]["mean"] >= r["base"]["mean"]; e2 = r["event_var"]["reduction"] >= FROZEN["E2_event_var_reduction_min"]; e3 = r["d_sharpe"] >= FROZEN["E3_sharpe_gain_min"]
    r["criteria"] = {"E1_mean": bool(e1), "E2_event_var": bool(e2), "E3_sharpe": bool(e3), "PASS": bool(e1 and e2 and e3)}
    return r


def placebo(net, k, m, B=2000, seed=11):
    """Δmean distribution if the k pre-anchors were picked on random non-event days (same hour-of-day set), same cost."""
    rng = np.random.RandomState(seed); cost = (1.0 - m) * G * COST_BPS * 2.0
    cand = np.where((hour == 16) & (~ev_day) & (np.arange(n) >= k))[0]
    d = np.empty(B)
    for b in range(B):
        pk = rng.choice(cand, n_ev, replace=False); tot = 0.0
        for p in pk:
            for i in range(0, k):
                tot += -(1 - m) * net[p - i]
        d[b] = (tot - cost * n_ev) / n
    return d


ARMS = {}
for tag, net in SERIES.items():
    A = {}
    for (k, m) in FROZEN["arms"]:
        A[f"k{k}_m{m}"] = arm_eval(net, k, m, f"k{k} m{m}")
    # placebo on the main arm
    k, m = FROZEN["main_arm"]["k"], FROZEN["main_arm"]["m"]
    d = placebo(net, k, m); act = A[f"k{k}_m{m}"]["d_mean"]
    A["placebo_random_days_main"] = {"B": len(d), "d_mean_dist": {"mean": float(d.mean()), "p5": float(np.percentile(d, 5)), "p50": float(np.percentile(d, 50)), "p95": float(np.percentile(d, 95))},
                                     "actual_d_mean": float(act), "pct_rank_of_actual": float((d < act).mean()), "frac_placebo_positive": float((d > 0).mean())}
    # shifted-calendar placebos
    sh = {}
    for days in (-7, -1, 1, 7):
        EV2 = EV + days * 86400; pos2 = np.searchsorted(ts, EV2, side="left"); pos2 = pos2[(pos2 - k >= 0) & (pos2 < n)]
        netp = net.copy(); cost = (1 - m) * G * COST_BPS * 2
        for p in pos2:
            for i in range(1, k + 1): netp[p - i] = m * net[p - i]
            netp[p - k] -= cost
        sh[f"shift_{days:+d}d"] = {"d_mean": float(netp.mean() - net.mean()), "d_sharpe": sharpe(netp) - sharpe(net), "n": int(len(pos2))}
    A["placebo_shifted_calendar_main"] = sh
    ARMS[tag] = A
    mainr = A[f"k{k}_m{m}"]
    print(f"[{tag}] MAIN k{k} m{m}: base mean {mainr['base']['mean']:.4f} S {mainr['base']['sharpe']:.4f} | alt mean {mainr['alt']['mean']:.4f} S {mainr['alt']['sharpe']:.4f} "
          f"dmean {mainr['d_mean']:+.4f} ({mainr['d_mean_per_year_bps']:+.1f} bps/yr) dS {mainr['d_sharpe']:+.4f} evvar red {mainr['event_var']['reduction']:+.3f} "
          f"shrunk mean net {mainr['shrunk_anchor_stats']['mean_net']:+.2f} | criteria {mainr['criteria']} | placebo pct {A['placebo_random_days_main']['pct_rank_of_actual']:.2f}", flush=True)
    for key in ("k1_m0.5", "k2_m0.5", "k2_m0.75"):
        a = A[key]; print(f"      {key}: dmean {a['d_mean']:+.4f} dS {a['d_sharpe']:+.4f} evvar {a['event_var']['reduction']:+.3f} shrunk mean {a['shrunk_anchor_stats']['mean_net']:+.2f} PASS {a['criteria']['PASS']}", flush=True)
    print("      shifted:", {kk: (round(v["d_mean"], 4), round(v["d_sharpe"], 4)) for kk, v in sh.items()}, flush=True)
RES["arms"] = ARMS

# ---------- 3. red-team block on the main arm (primary caliber): mechanism / drift-vs-variance / stability / event bootstrap ----------
net = SERIES["primary_S1_carry"]; k, m = FROZEN["main_arm"]["k"], FROZEN["main_arm"]["m"]; cost = (1 - m) * G * COST_BPS * 2
x = net[pre1]; bfull = float(np.cov(net, rs)[0, 1] / np.var(rs, ddof=1)); sl = bfull * rs[pre1]; resid = x - sl
ctl16 = (hour == 16) & (~ev_day); ctl_mean = float(net[ctl16].mean())
netp = net.copy(); netp[pre1] = m * net[pre1] - cost
net_cf = net.copy(); net_cf[pre1] = net[pre1] - x.mean() + ctl_mean          # drift removed: event anchors re-centred on control mean, variance kept
netp_cf = net_cf.copy(); netp_cf[pre1] = m * net_cf[pre1] - cost
be_mean = -cost / (1 - m)                                                      # E1 break-even event-anchor mean
order = np.argsort(pre1); xs_ = x[order]; wf_adopt, wf_real = [], []
for i in range(8, len(xs_)):                                                   # walk-forward: adopt only if past events' mean < break-even
    a = bool(xs_[:i].mean() < be_mean); wf_adopt.append(a)
    if a: wf_real.append(float(xs_[i]))
rng = np.random.RandomState(23); B = 4000; dmb = np.empty(B); dsb = np.empty(B)
for b in range(B):                                                             # event bootstrap: resample the 36 event anchors (with replacement), others fixed
    pick = rng.choice(pre1, n_ev, replace=True); netb = net.copy(); netpb = net.copy()
    vals = net[pick]; netb_ev = vals; netpb_ev = m * vals - cost
    # replace the event slots with resampled values (keep n fixed)
    netb[pre1] = netb_ev; netpb[pre1] = netpb_ev
    dmb[b] = netpb.mean() - netb.mean(); dsb[b] = sharpe(netpb) - sharpe(netb)
try:
    from scipy import stats
    wilc = float(stats.wilcoxon(x).pvalue)
    signp = float(stats.binomtest(int((x < 0).sum()), len(x), 0.5).pvalue) if hasattr(stats, "binomtest") else float(stats.binom_test(int((x < 0).sum()), len(x), 0.5))
except Exception as e:
    wilc = signp = f"scipy unavailable: {e!r}"
RES["redteam_main"] = {
    "per_event": [{"date": time.strftime("%Y-%m-%d", time.gmtime(int(ts[j]))), "net": float(net[j]), "rs": float(rs[j]), "btc4": float(btc[j]), "mkt_ew": float(mkt[j])} for j in pre1],
    "event_anchor": {"mean": float(x.mean()), "median": float(np.median(x)), "frac_neg": float((x < 0).mean()), "se_mean": float(x.std(ddof=1) / np.sqrt(len(x))),
                     "t_vs_0": float(x.mean() / x.std(ddof=1) * np.sqrt(len(x))), "wilcoxon_p": wilc, "sign_test_p": signp,
                     "drop_worst1_mean": float(np.sort(x)[1:].mean()), "drop_worst3_mean": float(np.sort(x)[3:].mean()), "trim10_mean": float(np.sort(x)[2:-2].mean())},
    "mechanism": {"beta_full_x2caliber": bfull, "sleeve_part_mean": float(sl.mean()), "resid_part_mean": float(resid.mean()), "sleeve_share": float(sl.mean() / x.mean()),
                  "rs_mean_event": float(rs[pre1].mean()), "rs_median_event": float(np.median(rs[pre1])), "rs_mean_ctl16": float(rs[ctl16].mean()), "btc_mean_event": float(btc[pre1].mean()),
                  "frac_rs_pos_event": float((rs[pre1] > 0).mean()), "corr_net_rs_event": float(np.corrcoef(x, rs[pre1])[0, 1]),
                  "rs_given_btc_up": float(rs[pre1][btc[pre1] > 0].mean()), "rs_given_btc_down": float(rs[pre1][btc[pre1] <= 0].mean()),
                  "n_btc_up": int((btc[pre1] > 0).sum()), "note": "alts outperform BTC in the 16-20Z FOMC window mostly when BTC rallies (high-beta catch-up) ⇒ short-spread book loses asymmetrically"},
    "split_half": {"2022_23": {"n": int((yr[pre1] <= 2023).sum()), "mean": float(x[yr[pre1] <= 2023].mean()), "median": float(np.median(x[yr[pre1] <= 2023])), "frac_neg": float((x[yr[pre1] <= 2023] < 0).mean())},
                   "2024_26": {"n": int((yr[pre1] >= 2024).sum()), "mean": float(x[yr[pre1] >= 2024].mean()), "median": float(np.median(x[yr[pre1] >= 2024])), "frac_neg": float((x[yr[pre1] >= 2024] < 0).mean())}},
    "btc_sd_ratio_by_year": {int(y): float(btc[pre1][yr[pre1] == y].std(ddof=1) / btc[(hour == 16) & (yr == y) & (~ev_day)].std(ddof=1)) for y in YEARS},
    "drift_vs_variance": {"actual": {"d_mean": float(netp.mean() - net.mean()), "d_sharpe": sharpe(netp) - sharpe(net)},
                          "drift_removed_counterfactual": {"d_mean": float(netp_cf.mean() - net_cf.mean()), "d_sharpe": sharpe(netp_cf) - sharpe(net_cf)},
                          "E1_breakeven_event_mean_bps": be_mean, "interpretation": "PASS comes from the negative conditional mean at the FOMC anchor, not from variance reduction"},
    "walk_forward": {"rule": "adopt at event i only if mean(past events) < break-even", "from_event": 9, "n_adopted": int(sum(wf_adopt)), "n_decisions": len(wf_adopt),
                     "realized_mean_on_adopted": float(np.mean(wf_real)) if wf_real else None},
    "event_bootstrap": {"B": B, "d_mean_ci95": [float(np.percentile(dmb, 2.5)), float(np.percentile(dmb, 97.5))], "P_d_mean_gt_0": float((dmb > 0).mean()),
                        "d_sharpe_ci95": [float(np.percentile(dsb, 2.5)), float(np.percentile(dsb, 97.5))], "P_d_sharpe_ge_0.03": float((dsb >= 0.03).mean()), "P_d_sharpe_gt_0": float((dsb > 0).mean())}}
rt = RES["redteam_main"]
print("REDTEAM: event mean", round(rt["event_anchor"]["mean"], 2), "median", round(rt["event_anchor"]["median"], 2), "frac_neg", rt["event_anchor"]["frac_neg"], "wilcoxon", rt["event_anchor"]["wilcoxon_p"],
      "| sleeve share", round(rt["mechanism"]["sleeve_share"], 2), "rs_ev", round(rt["mechanism"]["rs_mean_event"], 1), "rs|btc_up", round(rt["mechanism"]["rs_given_btc_up"], 1), "rs|btc_dn", round(rt["mechanism"]["rs_given_btc_down"], 1),
      "| drift-removed dS", round(rt["drift_vs_variance"]["drift_removed_counterfactual"]["d_sharpe"], 4), "| WF adopted", rt["walk_forward"]["n_adopted"], "/", rt["walk_forward"]["n_decisions"], "real", rt["walk_forward"]["realized_mean_on_adopted"],
      "| boot dmean CI", [round(v, 4) for v in rt["event_bootstrap"]["d_mean_ci95"]], "dS CI", [round(v, 4) for v in rt["event_bootstrap"]["d_sharpe_ci95"]], "P(dS>=.03)", rt["event_bootstrap"]["P_d_sharpe_ge_0.03"], flush=True)
json.dump(RES, open(OUT, "w"), indent=1, ensure_ascii=False)
print("WROTE", OUT)
