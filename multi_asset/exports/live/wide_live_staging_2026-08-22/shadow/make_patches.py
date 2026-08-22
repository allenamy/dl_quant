"""WA 影子记分缺陷修法提案 · 补丁生成器(提案, 不应用; 只写本目录).
从 shadow_loop.orig.py(= ~/wide_shadow/shadow_loop.py 拷贝, SHA 445a9870…)生成两个变体与两份统一 diff:
 (a) shadow_loop_a_tail_scoring.py  —— 记分修正: score 行对【数据宇宙外的冻结尾巴名】按 fapi 1h 收盘-收盘真实价格 + 窗内实际结算资金费记盈亏(新增字段, 原字段不动; 不改书).
 (b) shadow_loop_b_exit_on_leave.py —— 书行为修正: 出宇宙即平(数据宇宙 symbols_live 之外的名权重归零, 强制交易不受带约束, 计入换手/成本; bootstrap 时同样清零),
     可选 EXIT_NON_MEMBERS=True 把"离开 K400 成员集"的名也即平(与在役 forced-exit 语义一致, 换手上升).
用法: python make_patches.py  ⇒ 写出 *.py 变体 + a_tail_scoring.diff / b_exit_on_leave.diff
"""
import difflib, os, hashlib
D = os.path.dirname(os.path.abspath(__file__))
orig = open(f"{D}/shadow_loop.orig.py").read()
assert hashlib.sha256(orig.encode()).hexdigest().startswith("445a9870"), "orig drifted; regenerate from ~/wide_shadow/shadow_loop.py and re-review hunks"

def must_replace(s, old, new, n=1):
    assert s.count(old) == n, f"anchor text not unique/found ({s.count(old)}): {old[:60]!r}"
    return s.replace(old, new)

# ───────────────────────── (a) 记分修正
A = orig
A = must_replace(A, '''CHN_CLIPS = [(-0.3, 0.3), (0.0, 0.5), (0.0, 1.0), (0.0, 25.0), (0.0, 20.0), (-5.0, 15.0), (0.0, 1.0)]''',
'''CHN_CLIPS = [(-0.3, 0.3), (0.0, 0.5), (0.0, 1.0), (0.0, 25.0), (0.0, 20.0), (-5.0, 15.0), (0.0, 1.0)]
TAIL_SCORE = True          # (a) 对数据宇宙外的持仓名按真实价格/资金费补记分(只加字段, 不改书)
TAIL_SCORE_MIN_W = 0.0     # 只对 |w| ≥ 此阈值的尾巴名拉数(0 = 全部)

def score_tail_positions(fx, syms, idx_w, T, fetch=None):
    """对宇宙外持仓 {panel_idx: w} 在窗 (T, T+4h] 按 1h 收盘-收盘简单收益与窗内实际结算资金费记分.
    返回 dict(tail_gross_bps, tail_carry_bps, tail_n, tail_unknown_gross, tail_weight_used); fetch(path, params, weight) 可注入(测试用)."""
    get = fetch or fx.get
    gross = 0.0; carry = 0.0; n = 0; unknown = 0.0; wt = 0
    for j, w in idx_w.items():
        if abs(w) < TAIL_SCORE_MIN_W: continue
        s = syms[int(j)]
        r = get("/fapi/v1/klines", {"symbol": s, "interval": "1h", "startTime": (T - 3600) * 1000, "endTime": (T + 4 * 3600) * 1000 - 1, "limit": 5}, 1); wt += 1
        if not isinstance(r, list) or len(r) < 5 or int(r[0][0]) // 1000 != T - 3600 or int(r[-1][0]) // 1000 != T + 3 * 3600:
            unknown += abs(w); continue           # 退市/缺 bar: 未知, 不记 0 也不猜
        c0 = float(r[0][4]); c1 = float(r[-1][4])
        if c0 <= 0: unknown += abs(w); continue
        gross += w * (c1 / c0 - 1.0) * 1e4; n += 1
        f = get("/fapi/v1/fundingRate", {"symbol": s, "startTime": T * 1000 + 1, "endTime": (T + 4 * 3600) * 1000, "limit": 10}, 1); wt += 1
        if isinstance(f, list):
            for row in f:
                ft = int(row["fundingTime"]) // 1000
                if T < ft <= T + 4 * 3600: carry += w * float(row["fundingRate"]) * 1e4
    return {"tail_gross_bps": round(gross, 3), "tail_carry_bps": round(carry, 3), "tail_n": n, "tail_unknown_gross": round(unknown, 4), "tail_weight_used": wt}''')
A = must_replace(A, '''            smp = np.array(prev["sm"]); pmi = np.array(prev["sm_idx"])
            gross = float((smp * np.nan_to_num(y4v[pmi], nan=0.0)).sum() * 1e4)
            net = gross - prev["carry_bps"] - prev["cost_bps"]
            append_log({"e": "score", "anchor_ts": st.last_anchor, "gross_bps": round(gross, 3),
                        "net_bps": round(net, 3), "carry_bps": prev["carry_bps"], "cost_bps": prev["cost_bps"]})''',
'''            smp = np.array(prev["sm"]); pmi = np.array(prev["sm_idx"])
            gross = float((smp * np.nan_to_num(y4v[pmi], nan=0.0)).sum() * 1e4)
            net = gross - prev["carry_bps"] - prev["cost_bps"]
            row = {"e": "score", "anchor_ts": st.last_anchor, "gross_bps": round(gross, 3),
                   "net_bps": round(net, 3), "carry_bps": prev["carry_bps"], "cost_bps": prev["cost_bps"]}
            if TAIL_SCORE:
                # 数据宇宙外的持仓名(缓存无数据 ⇒ 上面 y4v 为 NaN ⇒ 记 0): 按真实价格/资金费补记, 只加字段
                live_set = set(st.live)
                tail = {int(j): float(w) for j, w in zip(pmi, smp) if st.syms[int(j)] not in live_set}
                ts_ = score_tail_positions(fx, st.syms, tail, int(st.last_anchor))
                row.update(ts_)
                row["tail_gross_pos"] = round(float(sum(abs(v) for v in tail.values())), 4)
                row["gross_bps_total"] = round(gross + ts_["tail_gross_bps"], 3)
                row["net_bps_total"] = round(net + ts_["tail_gross_bps"] - ts_["tail_carry_bps"], 3)
            append_log(row)''')
open(f"{D}/shadow_loop_a_tail_scoring.py", "w").write(A)

# ───────────────────────── (b) 出宇宙即平
Bv = orig
Bv = must_replace(Bv, '''CHN_CLIPS = [(-0.3, 0.3), (0.0, 0.5), (0.0, 1.0), (0.0, 25.0), (0.0, 20.0), (-5.0, 15.0), (0.0, 1.0)]''',
'''CHN_CLIPS = [(-0.3, 0.3), (0.0, 0.5), (0.0, 1.0), (0.0, 25.0), (0.0, 20.0), (-5.0, 15.0), (0.0, 1.0)]
EXIT_ON_LEAVE = True       # (b) 出宇宙即平: 数据宇宙(symbols_live)之外的名权重归零, 强制交易不受带约束, 计入换手/成本
EXIT_NON_MEMBERS = False   # 可选: 离开 K400 成员集的名也即平(与在役 forced-exit 同义; 换手上升, 见提案 §4)
FORCED_EXIT_COST_BPS = 4.7 # 强制平仓按最差档(tier2)成本计: 0.55×2.0 + 0.45×8.0

def exit_out_of_universe(sm, H, keep_mask):
    """把 keep_mask 为 False 的名的目标持仓置 0(强制, 不受带约束). 返回 (sm_new, forced_trade_abs_sum, n_forced)."""
    leave = (~keep_mask) & (np.abs(sm) > 1e-12)
    forced = float(np.abs(sm[leave]).sum()); sm2 = np.where(leave, 0.0, sm)
    return sm2, forced, int(leave.sum())''')
Bv = must_replace(Bv, '''                aux["H"] = {k: v for k, v in sig[last_t]["w"].items()}''',
'''                live_set = set(cfg["symbols_live"])
                aux["H"] = {k: v for k, v in sig[last_t]["w"].items() if (not EXIT_ON_LEAVE) or cfg["symbols_panel"][int(k)] in live_set}   # (b) 引导时即清掉数据宇宙外的名''')
Bv = must_replace(Bv, '''        self.sym_idx = {s: j for j, s in enumerate(self.syms)}
        p = f"{STATE_DIR}/rolling.npz"''',
'''        self.sym_idx = {s: j for j, s in enumerate(self.syms)}
        self.live_mask = np.zeros(self.NW, bool); self.live_mask[[self.sym_idx[s] for s in self.live if s in self.sym_idx]] = True
        p = f"{STATE_DIR}/rolling.npz"''')
Bv = must_replace(Bv, '''    sm = np.where(np.abs(trade) < P["band"], st.H, sm)
    trade = sm - st.H
    # 成本(情景b) + carry(修正口径)
    tiers = np.full(len(m), 2, np.int8); tiers[qv4h >= 1e6] = 1; tiers[qv4h >= 5e6] = 0
    tabs = np.abs(trade[m])
    COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
    cost = float(sum(tabs[tiers == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B)))''',
'''    sm = np.where(np.abs(trade) < P["band"], st.H, sm)
    forced_abs = 0.0; forced_n = 0
    if EXIT_ON_LEAVE:
        keep = st.live_mask.copy()
        if EXIT_NON_MEMBERS:
            keep[:] = False; keep[m] = True
        sm, forced_abs, forced_n = exit_out_of_universe(sm, st.H, keep)   # 强制平仓, 不受带约束
    trade = sm - st.H
    # 成本(情景b) + carry(修正口径)
    tiers = np.full(len(m), 2, np.int8); tiers[qv4h >= 1e6] = 1; tiers[qv4h >= 5e6] = 0
    tabs = np.abs(trade[m])
    COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
    cost = float(sum(tabs[tiers == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B)))
    if EXIT_ON_LEAVE:
        nm_mask = np.ones(st.NW, bool); nm_mask[m] = False
        cost += float(np.abs(trade[nm_mask]).sum()) * FORCED_EXIT_COST_BPS   # 成员集外的强制交易按最差档计成本''')
Bv = must_replace(Bv, '''                "turnover": round(float(np.abs(trade).sum()), 5), "gross_pos": round(float(np.abs(sm).sum()), 4),''',
'''                "turnover": round(float(np.abs(trade).sum()), 5), "gross_pos": round(float(np.abs(sm).sum()), 4),
                "forced_exit_n": forced_n, "forced_exit_gross": round(forced_abs, 4),''')
open(f"{D}/shadow_loop_b_exit_on_leave.py", "w").write(Bv)

for nm, txt in (("a_tail_scoring", A), ("b_exit_on_leave", Bv)):
    diff = difflib.unified_diff(orig.splitlines(keepends=True), txt.splitlines(keepends=True), fromfile="a/shadow_loop.py", tofile="b/shadow_loop.py", n=3)
    open(f"{D}/{nm}.diff", "w").write("".join(diff))
    print("wrote", nm, "diff lines", sum(1 for _ in open(f"{D}/{nm}.diff")))
print("orig sha256", hashlib.sha256(orig.encode()).hexdigest())
