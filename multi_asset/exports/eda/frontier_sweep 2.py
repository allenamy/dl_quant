#!/usr/bin/env python3
"""换手-成本前沿扫描器 (0C) —— 预注册见 prereg_turnover_cost_frontier.md。

★ 它**不修改** `engine/`。做法: import 之后 monkeypatch `replay_fullhist.CrossLegNetting`
  为一个子类, 只覆盖 `shaped -> net` 那一步。canonical 代码路径字节不变。

★ 加载即断言 pin 件哈希 (team-lead 2026-07-26 裁定):
  唯一权威基准 = git 里那份 pin 件。一切"相对 canonical 改善 X"的对比都以它为准, 且**基准被换会响**
  —— 不是靠没人去动它。服务器上那份是缓存, 无权威。

★ 三根轴 (全部尺度无关 —— 仓位 L1 归一, 绝对阈值会随 gross 漂移而变义)
    b      no-trade band:  |Δ| <= b * mean|target|  的名字不动
    lam    持仓惯性:        target = (1-lam)*shaped + lam*held
    c      逐名成本降权:    band_name = b * (cost_name / median_cost) ** c

  ⇒ **c 的定义与 team-lead 原话有出入, 这里说明理由**: 原话是 "仅当 |Δw|·E[ret|Δ] > c·cost_name
    才动"。`E[ret|Δ]` 是**未来收益的期望**, 在锚点当下**不可因果获得** —— 用实现收益去算它就是
    前视。⇒ 所以 c 实现为"按逐名相对成本缩放 band 宽度"的指数: c=0 退化为统一 band(即 b 轴),
    c>0 让贵的名字更难被交易。这**就是**"逐名成本降权"的因果形式, 但它不是原公式。

★ 两个已知答案控制 (都必须过, 否则该次扫描作废)
    KA-1  b=0, lam=0, c=0 必须逐字节复现 pin 件
    KA-2  我自己按年拆的 turnover, 其全期年化必须等于引擎自报的 net_turn_ann

用法 (服务器上):
    python frontier_sweep.py --axis b     --out <dir>
    python frontier_sweep.py --axis lam   --out <dir>
    python frontier_sweep.py --ka         --out <dir>      # 只跑 KA-1/KA-2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
sys.path.insert(0, os.path.join(REPO, "multi_asset"))
sys.path.insert(0, REPO)

PIN = os.path.join(REPO, "multi_asset/exports/eda/engine_fullhist_replay_CANONICAL_pinned.json")
PIN_SHA = "5f61188ba89ec4bb463eb22d9d5b89fd793de890437b973f8f71ce951835401a"

from engine import replay_fullhist as RF          # noqa: E402
from engine.netting import CrossLegNetting        # noqa: E402


def load_canonical():
    """★ 基准的权威性由哈希断言, 不由文件名或位置。基准被换 => 这里就红。"""
    if not os.path.exists(PIN):
        raise SystemExit(f"pin 件不存在: {PIN} —— 无基准即无'相对 canonical 改善'这句话")
    raw = open(PIN, "rb").read()
    got = hashlib.sha256(raw).hexdigest()
    if got != PIN_SHA:
        raise SystemExit(f"★ pin 件哈希不符!\n  期望 {PIN_SHA}\n  实得 {got}\n"
                         f"  => 基准被换过。停止, 先归因, 不带着漂移的基准做前沿。")
    return json.loads(raw)


class BandedNetting(CrossLegNetting):
    """只覆盖 `shaped -> net` 那一步; 其余逐行沿用父类。

    ★ 父类那一步的原文是:
          net = np.zeros(N); net[m] = shaped
          net_turn += np.abs(net - prev_net).sum()
      我们在 `net[m] = shaped` 与 turnover 之间插入 惯性 -> band -> 保持旧仓。
      b=lam=0 时**逐行等价于父类**, 这是 KA-1 能过的前提。
    """

    def __init__(self, *a, band=0.0, inertia=0.0, cost_exp=0.0, cost_by_name=None, **kw):
        super().__init__(*a, **kw)
        self.band = float(band); self.inertia = float(inertia)
        self.cost_exp = float(cost_exp); self.cost_by_name = cost_by_name
        self.per_anchor = []          # (ti, turnover_this_anchor) —— 给按年拆用

    def run(self, anchors, ts, calib_by_year=None, year_of=None):
        chain = self.chain; N = chain.src.N
        if chain.funding_risk is not None:
            chain.funding_risk.n_gated = 0
        held = {k: np.zeros(N) for k in self.w}
        prev_net = np.zeros(N)
        gross_turn = 0.0; net_turn = 0.0; net_positions = []
        cur_year = None
        self.per_anchor = []
        for i, t in enumerate(anchors):
            ti = int(t)
            if calib_by_year is not None and year_of is not None:
                y = int(year_of[i])
                if y != cur_year:
                    chain.calibrator = calib_by_year.get(y); cur_year = y
            legpos, m = chain.leg_positions(ti)
            for k in self.w:
                if i == 0 or (ti % self.cad[k] == 0):
                    new = np.zeros(N); new[m] = legpos[k]
                    gross_turn += self.w[k] * np.abs(new - held[k]).sum()
                    held[k] = new
            combo_full = sum(self.w[k] * held[k] for k in self.w)
            active = combo_full[m]
            base = active - active.mean()
            gref = np.abs(base).sum()
            shaped = chain.shape_position(active)
            gsh = np.abs(shaped).sum()
            if gsh > 1e-12 and gref > 1e-12:
                shaped = shaped * (gref / gsh)
            net = np.zeros(N); net[m] = shaped

            # ── 这里是唯一的改动点 ─────────────────────────────────────────────────────────
            if self.inertia > 0.0:
                net = (1.0 - self.inertia) * net + self.inertia * prev_net
            if self.band > 0.0:
                scale = np.abs(net).mean()
                thr = np.full(N, self.band * scale)
                if self.cost_exp > 0.0 and self.cost_by_name is not None:
                    thr = thr * self.cost_by_name ** self.cost_exp
                keep = np.abs(net - prev_net) <= thr        # 动不动得起 => 不动
                net = np.where(keep, prev_net, net)
            # ──────────────────────────────────────────────────────────────────────────────

            d = float(np.abs(net - prev_net).sum())
            net_turn += d
            self.per_anchor.append((ti, d))
            prev_net = net
            net_positions.append((ti, m, net[m].copy()))
        yrs = (int(ts[anchors[-1]]) - int(ts[anchors[0]])) / (1000 * 3600 * 24 * 365.25)
        self.years_exact = yrs          # ★ 未取整 —— 见下方 KA-2 的教训
        gross_ann = gross_turn / max(yrs, 1e-9); net_ann = net_turn / max(yrs, 1e-9)
        self.net_turn_exact = net_ann
        hedge = 1 - net_ann / gross_ann if gross_ann > 0 else 0.0
        return {"net_positions": net_positions, "gross_turn_ann": gross_ann,
                "net_turn_ann": net_ann, "hedge_rate": hedge,
                "savings_bps_yr": (gross_ann - net_ann) * self.cost, "years": yrs}


_CAPTURE = {}


def run_point(band=0.0, inertia=0.0, cost_exp=0.0, cost_bps=None, cost_by_name=None):
    """跑一个工作点。返回 run_replay 的输出 + 我自己按年拆的 turnover。"""
    def _factory(chain, weights, cadence=None, cost_bps=RF.COST_BPS):
        inst = BandedNetting(chain, weights, cadence=cadence, cost_bps=cost_bps,
                             band=band, inertia=inertia, cost_exp=cost_exp,
                             cost_by_name=cost_by_name)
        _CAPTURE["inst"] = inst
        return inst
    old_cls, old_cost = RF.CrossLegNetting, RF.COST_BPS
    try:
        RF.CrossLegNetting = _factory
        if cost_bps is not None:
            RF.COST_BPS = float(cost_bps)
        out = RF.run_replay(funding_mode="rank", use_c5=True, shaping="cap", verbose=False)
    finally:
        RF.CrossLegNetting, RF.COST_BPS = old_cls, old_cost

    inst = _CAPTURE.get("inst")
    src = RF.get_src()
    tis = np.array([t for t, _ in inst.per_anchor])
    ds = np.array([d for _, d in inst.per_anchor])
    yr = pd.to_datetime(src.ts[tis], unit="ms", utc=True).year.to_numpy()
    per_year_turn = {}
    for y in sorted(set(int(v) for v in yr)):
        sel = yr == y
        span_yr = float(sel.sum()) / (365.0 * 6.0)          # 4h 锚点 => 每年 2190 (部分年按锚点数折算)
        per_year_turn[int(y)] = round(float(ds[sel].sum() / max(span_yr, 1e-9)), 2)
    out["per_year_turnover_ann"] = per_year_turn
    # ★ KA-2 第一次没过, 差 0.06 —— 原因是**我自己**拿 `netting.years` 这个**已取整到 3 位**的
    # 除数去年化 (4.492 vs 真值 4.49236), 不是引擎与我算得不同。⇒ 控制没有误报, 它抓的是我。
    # ⇒ 用未取整的 years_exact, 并直接与未取整的 net_turn_exact 比。
    out["_whole_span_turn_check"] = round(float(ds.sum() / inst.years_exact), 3)
    out["_engine_net_turn_exact"] = round(float(inst.net_turn_exact), 3)
    out["point"] = {"band": band, "inertia": inertia, "cost_exp": cost_exp,
                    "cost_bps": cost_bps if cost_bps is not None else RF.COST_BPS}
    return out


def ka_check(out, canon):
    """KA-1: 与 pin 件逐项相同; KA-2: 我按年拆的 turnover 年化回全期 == 引擎自报。"""
    fields = ["anchors", "cost_bps"]
    ka1 = all(out.get(f) == canon.get(f) for f in fields)
    for y, v in canon["per_year"].items():
        got = out["per_year"].get(int(y)) or out["per_year"].get(y)
        if got is None or any(got[k] != v[k] for k in v):
            ka1 = False
    for k, v in canon["netting"].items():
        if round(float(out["netting"][k]), 3) != round(float(v), 3):
            ka1 = False
    ka2 = abs(out["_whole_span_turn_check"] - out["_engine_net_turn_exact"]) < 0.01
    return {"KA1_matches_pinned_canonical": bool(ka1),
            "KA2_per_year_turnover_sums_to_engine": bool(ka2),
            "per_year_turnover_ann": out["per_year_turnover_ann"],
            "engine_net_turn_ann": out["netting"]["net_turn_ann"],
            "my_whole_span": out["_whole_span_turn_check"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--axis", default="", choices=["", "b", "lam", "cost", "c"])
    ap.add_argument("--ka", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    canon = load_canonical()
    print(f"[pin] canonical 哈希断言通过 ({PIN_SHA[:16]}…)  avg_net={canon['avg_net_of_cost_sharpe']}",
          flush=True)
    os.makedirs(a.out, exist_ok=True)

    if a.ka or not a.axis:
        out = run_point()                       # b=0 lam=0 c=0
        chk = ka_check(out, canon)
        json.dump({"known_answer": chk, "raw": out},
                  open(os.path.join(a.out, "ka.json"), "w"), indent=1, default=str)
        print(json.dumps(chk, ensure_ascii=False, indent=1), flush=True)
        if not (chk["KA1_matches_pinned_canonical"] and chk["KA2_per_year_turnover_sums_to_engine"]):
            raise SystemExit("★ 已知答案控制未过 —— 停, 不烧网格预算")
        print("★ 两个已知答案控制都过", flush=True)

    if a.axis == "c":
        # ★ 轴 c 用的是**代理**, 不是真实逐名成本 —— 这一点必须随结果一起走。
        #  (1) `a7_cost_tiers.json` 只覆盖**原始 14 个 symbol**, 引擎面板是 ~110 名的宽面板
        #      ⇒ 宽面板上**没有**逐名实测成本。
        #  (2) 唯一可用的面板级流动性量是 `size_dvol` —— 而它**同时是四条腿之一(size)的信号**。
        #      ⇒ 用它设 band, 等于让执行过滤器与一条腿的信号**耦合**。这是设计风险, 不只是数据缺口。
        #  ⇒ 所以本轴的读法只有一个: "**若**逐名成本与流动性同序, 重新分配 band 宽度能否救回 b 轴"。
        src = RF.get_src()
        mid = src.T // 2
        liq = np.nanmedian(src.CH[max(0, mid - 500):mid + 500, :, src.size_idx], axis=0)
        r = pd.Series(liq).rank(pct=True).to_numpy()      # 1 = 最流动
        cost_rel = np.where(np.isfinite(r), 2.0 - 1.5 * r, 1.0)   # 最不流动 2.0 -> 最流动 0.5
        for cexp in (0.5, 1.0, 2.0):
            out = run_point(band=0.20, cost_exp=cexp, cost_by_name=cost_rel)
            tag = f"c{cexp}_b0.20"
            json.dump(out, open(os.path.join(a.out, f"pt_{tag}.json"), "w"), indent=1, default=str)
            print(f"[{tag}] turn={out['netting']['net_turn_ann']:.1f} "
                  f"avg_net={out['avg_net_of_cost_sharpe']}", flush=True)
        raise SystemExit(0)

    if a.axis == "cost":
        # ★ 决定性的一轴: 真实有效成本下, λ>0 是否反超 λ=0。
        # 4.5 = Binance VIP0 最坏情形有效成本 (fee_fill_sensitivity.md)
        # 6.0 = 我按线性化估的交叉点 (待实测证实/证否)
        # 11.8 = 该文测得的盈亏平衡有效成本门
        for cb in (4.5, 6.0, 11.8):
            for lam in (0.0, 0.25, 0.50):
                out = run_point(inertia=lam, cost_bps=cb)
                tag = f"cost{cb}_lam{lam}"
                json.dump(out, open(os.path.join(a.out, f"pt_{tag}.json"), "w"),
                          indent=1, default=str)
                print(f"[{tag}] turn={out['netting']['net_turn_ann']:.1f} "
                      f"avg_net={out['avg_net_of_cost_sharpe']}", flush=True)
        raise SystemExit(0)

    grid = {"b": [0.05, 0.10, 0.15, 0.20, 0.30, 0.50],
            "lam": [0.25, 0.50, 0.75]}.get(a.axis, [])
    for v in grid:
        kw = {"band": v} if a.axis == "b" else {"inertia": v}
        out = run_point(**kw)
        tag = f"{a.axis}_{v}"
        json.dump(out, open(os.path.join(a.out, f"pt_{tag}.json"), "w"), indent=1, default=str)
        pt = out["per_year"]
        print(f"[{tag}] net_turn_ann={out['netting']['net_turn_ann']:.1f} "
              f"avg_net={out['avg_net_of_cost_sharpe']} "
              f"net={[pt[y]['net_of_cost_sharpe'] for y in sorted(pt)]}", flush=True)
