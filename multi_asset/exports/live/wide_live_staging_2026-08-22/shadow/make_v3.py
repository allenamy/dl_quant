#!/usr/bin/env python3
"""shadow_loop_v3 generator (2026-08-22, lead's ruling): v3 = running v2 (SHA 019049584b…)
  -> WA (b) exit-on-leave  (EXIT_ON_LEAVE; v3 sets EXIT_NON_MEMBERS=True; keep = universe ∧ members — see NOTE)
  -> WA (a) tail scoring   (score rows gain tail_* fields; original fields byte-identical)
  -> universe LIST in the signed target file (same recipe as universe_sha; the reader recomputes it and refuses a mismatch)
Writes shadow_loop_v3.py + shadow_loop_v3.diff (vs v2). Every hunk is exact-match; drift => refusal.
NOTE (deviation from WA's (b) hunk, documented): WA wrote `keep[:] = False; keep[m] = True` under EXIT_NON_MEMBERS —
  the member mask REPLACES the universe mask, so a member outside symbols_live (possible while the 40d bootstrap
  cache still gives non-live names coverage, until ~08-23) would be KEPT. The lead's intent is 纸面书 ≡ 可执行书
  => keep = live_mask ∧ member_mask. v3 intersects.
Cross-check: every '+' line of WA's a_tail_scoring.diff / b_exit_on_leave.diff must appear in v3 except the two
  lines v3 deliberately changes (EXIT_NON_MEMBERS value; the keep-mask replacement) — asserted below.
"""
import difflib
import hashlib
import os

D = os.path.dirname(os.path.abspath(__file__))
v2 = open(f"{D}/shadow_loop_v2.py", encoding="utf-8").read()
assert hashlib.sha256(v2.encode()).hexdigest().startswith("019049584b"), \
    "v2 drifted — regenerate from the running file and re-review"


def must_replace(s, old, new, label):
    assert s.count(old) == 1, f"{label}: anchor text count {s.count(old)} != 1: {old[:70]!r}"
    return s.replace(old, new, 1)


V = v2
# ── WA (b): constants + pure function ─────────────────────────────────────────────────────────────
V = must_replace(V, '''CHN_CLIPS = [(-0.3, 0.3), (0.0, 0.5), (0.0, 1.0), (0.0, 25.0), (0.0, 20.0), (-5.0, 15.0), (0.0, 1.0)]''',
'''CHN_CLIPS = [(-0.3, 0.3), (0.0, 0.5), (0.0, 1.0), (0.0, 25.0), (0.0, 20.0), (-5.0, 15.0), (0.0, 1.0)]
EXIT_ON_LEAVE = True       # (b) 出宇宙即平: 数据宇宙(symbols_live)之外的名权重归零, 强制交易不受带约束, 计入换手/成本
EXIT_NON_MEMBERS = True    # v3 (lead 2026-08-22): 离开 K400 成员集的名也即平 ⇒ 纸面书 ≡ 可执行书(目标文件只含宇宙内成员); WA 提案默认 False
FORCED_EXIT_COST_BPS = 4.7 # 强制平仓按最差档(tier2)成本计: 0.55×2.0 + 0.45×8.0

def exit_out_of_universe(sm, H, keep_mask):
    """把 keep_mask 为 False 的名的目标持仓置 0(强制, 不受带约束). 返回 (sm_new, forced_trade_abs_sum, n_forced)."""
    leave = (~keep_mask) & (np.abs(sm) > 1e-12)
    forced = float(np.abs(sm[leave]).sum()); sm2 = np.where(leave, 0.0, sm)
    return sm2, forced, int(leave.sum())''', "b constants")
V = must_replace(V, '''                aux["H"] = {k: v for k, v in sig[last_t]["w"].items()}''',
'''                live_set = set(cfg["symbols_live"])
                aux["H"] = {k: v for k, v in sig[last_t]["w"].items() if (not EXIT_ON_LEAVE) or cfg["symbols_panel"][int(k)] in live_set}   # (b) 引导时即清掉数据宇宙外的名''', "b bootstrap")
V = must_replace(V, '''        self.sym_idx = {s: j for j, s in enumerate(self.syms)}
        p = f"{STATE_DIR}/rolling.npz"''',
'''        self.sym_idx = {s: j for j, s in enumerate(self.syms)}
        self.live_mask = np.zeros(self.NW, bool); self.live_mask[[self.sym_idx[s] for s in self.live if s in self.sym_idx]] = True
        p = f"{STATE_DIR}/rolling.npz"''', "b live_mask")
V = must_replace(V, '''    sm = np.where(np.abs(trade) < P["band"], st.H, sm)
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
            _mm = np.zeros(st.NW, bool); _mm[m] = True
            keep &= _mm          # v3: 宇宙内 ∧ 成员 (WA 原 hunk 用成员集替换宇宙掩码, 会保留宇宙外成员; 改为相交 — 见 make_v3.py NOTE)
        sm, forced_abs, forced_n = exit_out_of_universe(sm, st.H, keep)   # 强制平仓, 不受带约束
    trade = sm - st.H
    # 成本(情景b) + carry(修正口径)
    tiers = np.full(len(m), 2, np.int8); tiers[qv4h >= 1e6] = 1; tiers[qv4h >= 5e6] = 0
    tabs = np.abs(trade[m])
    COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
    cost = float(sum(tabs[tiers == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B)))
    if EXIT_ON_LEAVE:
        nm_mask = np.ones(st.NW, bool); nm_mask[m] = False
        cost += float(np.abs(trade[nm_mask]).sum()) * FORCED_EXIT_COST_BPS   # 成员集外的强制交易按最差档计成本''', "b step 8")
V = must_replace(V, '''                "turnover": round(float(np.abs(trade).sum()), 5), "gross_pos": round(float(np.abs(sm).sum()), 4),''',
'''                "turnover": round(float(np.abs(trade).sum()), 5), "gross_pos": round(float(np.abs(sm).sum()), 4),
                "forced_exit_n": forced_n, "forced_exit_gross": round(forced_abs, 4),''', "b signal row")
# ── WA (a): tail scoring ─────────────────────────────────────────────────────────────────────────
V = must_replace(V, '''CHN_CLIPS = [(-0.3, 0.3), (0.0, 0.5), (0.0, 1.0), (0.0, 25.0), (0.0, 20.0), (-5.0, 15.0), (0.0, 1.0)]''',
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
    return {"tail_gross_bps": round(gross, 3), "tail_carry_bps": round(carry, 3), "tail_n": n, "tail_unknown_gross": round(unknown, 4), "tail_weight_used": wt}''', "a constants")
V = must_replace(V, '''            smp = np.array(prev["sm"]); pmi = np.array(prev["sm_idx"])
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
            append_log(row)''', "a score row")
# ── v3: universe LIST in the signed target file + producer stamp + header ─────────────────────────
V = must_replace(V, '''           "universe_sha": universe_sha(live), "n_universe": len(live),''',
'''           "universe": live, "universe_sha": universe_sha(live), "n_universe": len(live),''', "v3 universe list")
V = must_replace(V, '''           "producer": "shadow_loop_v2",''', '''           "producer": "shadow_loop_v3",''', "v3 producer")
V = must_replace(V, '''# ── v2 (2026-08-22, DESIGN_wide_live_deployment §1/§3.1): signed target file for the live adapter ──''',
'''# ── v2 (2026-08-22, DESIGN_wide_live_deployment §1/§3.1): signed target file for the live adapter ──
# ── v3 (2026-08-22 lead): + WA (b) exit-on-leave [EXIT_NON_MEMBERS=True, keep = universe ∧ members] + WA (a) tail
#    scoring + `universe` LIST in the target file (same recipe as universe_sha; the reader recomputes it and refuses
#    a mismatch; names outside it are never live targets) ⇒ the target file IS the in-universe member book.''', "v3 header")
open(f"{D}/shadow_loop_v3.py", "w", encoding="utf-8").write(V)
open(f"{D}/shadow_loop_v3.diff", "w", encoding="utf-8").write("".join(difflib.unified_diff(
    v2.splitlines(True), V.splitlines(True), fromfile="a/shadow_loop_v2.py", tofile="b/shadow_loop_v3.py", n=3)))
# ── cross-check against WA's diff artefacts ─────────────────────────────────────────────────────
changed_by_v3 = ("EXIT_NON_MEMBERS = False", "keep[:] = False; keep[m] = True")
missing = []
for nm in ("a_tail_scoring.diff", "b_exit_on_leave.diff"):
    for line in open(f"{D}/{nm}", encoding="utf-8"):
        if line.startswith("+") and not line.startswith("+++"):
            body = line[1:].rstrip("\n")
            if any(c in body for c in changed_by_v3):
                continue
            if body.strip() and body not in V:
                missing.append((nm, body[:80]))
assert not missing, f"WA '+' lines absent from v3: {missing}"
print("shadow_loop_v3.py written; sha256", hashlib.sha256(V.encode()).hexdigest()[:12],
      "| diff lines", sum(1 for _ in open(f"{D}/shadow_loop_v3.diff")), "| WA cross-check OK")
