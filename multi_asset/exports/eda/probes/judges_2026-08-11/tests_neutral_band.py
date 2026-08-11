"""tests_neutral_band — 中性保持型免交易带(PROPOSAL 8e499dac, 用户裁定 2026-08-10)

覆盖: [T1] 配置钉 [T2] 函数语义(中性精确/带内保持/零仓不开新) [T3] 豁免名原样且不参与摊派
[T4] band=0 恒等(保真门) [T5] 接线次序(reshape 之后, plan 之前) [T6] 豁免集接线
设计依据: 回放 9821 锚 Δ净 vs 实盘现状 +0.0583 / vs 入金后 +0.0972, 5/5 年, 中性 1e-16。
"""
import json
import os
import re
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "signal"))
import legs as LG  # noqa: E402

FAIL = []


def check(name, cond, detail=""):
    print(("  PASS " if cond else "★ FAIL ") + name + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(name)


# [T1] 配置钉: 值与 provenance 同在 —— 只有值没有出处 = 下一个读者无从判断它能不能动
cfg = json.load(open(os.path.join(_REPO, "config", "book.json")))
check("T1a no_trade_band_w == 0.002", cfg.get("no_trade_band_w") == 0.002,
      f"got {cfg.get('no_trade_band_w')}")
check("T1b provenance key present", "8e499dac" in str(cfg.get("_no_trade_band_basis", "")),
      "basis must cite the frozen proposal SHA")

# [T2] 函数语义
tgt = {"A": 100.0, "B": -100.0, "C": 3.0, "D": -3.0, "E": 0.5}
pos = {"A": 60.0, "B": -58.0, "C": 1.0, "D": -1.5, "E": 0.0}
out, st = LG.apply_no_trade_band(tgt, pos, band_notional=5.0)
check("T2a in-band names hold current", out["C"] == 1.0 and out["D"] == -1.5,
      f"C={out['C']} D={out['D']}")
check("T2b zero-position small target stays flat (no dust open)", out["E"] == 0.0,
      f"E={out['E']}")
check("T2c neutrality exact over traded set", abs(sum(out.values())) < 1e-9,
      f"net={sum(out.values()):.2e}")
check("T2d traded names moved by common constant only",
      abs((tgt["A"] - out["A"]) - (tgt["B"] - out["B"])) < 1e-9,
      "spread must be a single constant, not proportional")
check("T2e stats coherent", st["n_held"] == 3 and st["n_traded"] == 2 and st["applied"],
      f"held={st['n_held']} traded={st['n_traded']}")

# [T3] 豁免名: 原样通过, 不参与摊派 —— 对 clamp 约束名加常数会重新打开被禁方向
out3, st3 = LG.apply_no_trade_band(tgt, pos, band_notional=5.0, exempt={"A"})
check("T3a exempt name untouched", out3["A"] == tgt["A"], f"A={out3['A']}")
check("T3b exempt excluded from spread set", st3["n_exempt"] == 1 and st3["n_traded"] == 1,
      f"exempt={st3['n_exempt']} traded={st3['n_traded']}")
check("T3c neutrality still exact with exemptions", abs(sum(out3.values())) < 1e-9,
      f"net={sum(out3.values()):.2e}")

# [T4] band=0 恒等 —— 回放 b=0 保真门用的就是这条直通
out4, st4 = LG.apply_no_trade_band(tgt, pos, band_notional=0.0)
check("T4 band<=0 is identity", out4 == {k: float(v) for k, v in tgt.items()}
      and not st4["applied"])

# [T5] 接线次序: 带必须在 withhold+reshape 之后(reshape 的 re-demean 会移动带住的名字),
#      在 executor.plan 之前(plan 消费的必须是带后目标)
src = open(os.path.join(_REPO, "scheduler", "anchor_loop.py")).read()
i_reshape = src.find("apply_withhold_and_reshape(")
i_band = src.find("apply_no_trade_band(")
i_plan = src.find("self.executor.plan(")
check("T5a band wired", i_band > 0)
check("T5b order reshape -> band -> plan", 0 < i_reshape < i_band < i_plan,
      f"idx reshape={i_reshape} band={i_band} plan={i_plan}")

# [T6] 豁免集接线: 三类场所约束名都必须进 exempt
seg = src[i_band - 600:i_band + 200] if i_band > 0 else ""
for key in ("reduced", "add_blocked", "flatten_only"):
    check(f"T6 exempt includes _clamp[{key}]", key in seg,
          "venue-constrained names must not receive the spread constant")

# [T7] 单位陷阱三连(尺子审计 #61 最高风险第2条): 仓里另有一条休眠的 bps 口径带
#      (binance_executor.DEFAULT_BAND_BPS, |delta|/gross*1e4 < band_bps)。0.002 填错口径
#      = 10,000× 偏小的静默无操作, 且没有任何读数会红 —— 与 funding 4h/8h 单位 bug 同形。
exe = open(os.path.join(_REPO, "live", "binance_executor.py")).read()
check("T7a executor band stays dormant (DEFAULT_BAND_BPS = 0.0)",
      "DEFAULT_BAND_BPS = 0.0" in exe,
      "exactly ONE band mechanism may be live; activating band_bps = double-banding")
check("T7b config does not set band_bps", "band_bps" not in json.dumps(cfg),
      "no_trade_band_w is the ONLY band key; band_bps would be a unit trap")
check("T7c wiring multiplies by gross (notional caliber)",
      "_bw * float(self.gross" in src,
      "no_trade_band_w is WEIGHT units; must scale by gross before comparing to notional delta")

n = len(FAIL)
print(f"\ntests_neutral_band: {'ALL PASS' if n == 0 else f'{n} FAIL: {FAIL}'}")
sys.exit(1 if n else 0)
