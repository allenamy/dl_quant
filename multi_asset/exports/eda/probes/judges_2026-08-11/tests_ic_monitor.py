"""tests_ic_monitor — #55 逐锚实现 IC 监视器(尺子审计判定的最大结构缺口的补件)

覆盖: [T1] 阈值已盖章且引标定源 [T2] IC 数学(已知符号的合成数据) [T3] 判级逻辑(OK/不足/ALERT/DECIDE)
[T4] β 严格因果(历史在计算之后推进) [T5] launchd plist 存在且指向本脚本 [T6] 幂等(known_ts 跳过)
盲区(自陈): (a) 不跑真实 position_readback —— 数据形状变化本套件不红; (b) 不测 telegram 投递
(deliver 的 import 在 try 内, 死投递只打印); (c) 阈值的【正确性】来自离线标定文档, 本套件只钉存在。
"""
import importlib.util
import json
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("ic_monitor",
                                              os.path.join(_REPO, "ops", "ic_monitor.py"))
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

FAIL = []


def check(name, cond, detail=""):
    print(("  PASS " if cond else "★ FAIL ") + name + (f" — {detail}" if detail else ""))
    if not cond:
        FAIL.append(name)


# [T1] 阈值盖章
check("T1a thresholds stamped", all(v is not None for v in (M.R24_P5, M.R24_P1, M.R48_P1)),
      f"{M.R24_P5}/{M.R24_P1}/{M.R48_P1}")
check("T1b ordering P1 < P5 < 0", M.R24_P1 < M.R24_P5 < 0,
      "DECIDE must be rarer than ALERT")
check("T1c calibration source cited", "ic_calib_a005" in M.CALIB_SRC)

# [T2] IC 数学: 完全同序 ⇒ spearman=1; 反序 ⇒ −1
check("T2a spearman +1", abs(M._spear([1, 2, 3, 4, 5], [10, 20, 30, 40, 50]) - 1.0) < 1e-9)
check("T2b spearman −1", abs(M._spear([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) + 1.0) < 1e-9)
check("T2c ties handled", M._spear([1, 1, 2], [1, 2, 3]) is not None)

# [T3] 判级: <24 锚只记不判; 越线判级正确
W = M.WINDOW_START_TS
mk = lambda i, ic: {"anchor_ts": W + i * 14400, "rank_ic": ic}
v0 = M.check([mk(i, 0.05) for i in range(10)])
check("T3a insufficient below 24", not v0["judged"] and v0["level"] == "OK", str(v0))
v1 = M.check([mk(i, 0.05) for i in range(30)])
check("T3b healthy = OK judged", v1["judged"] and v1["level"] == "OK", str(v1))
v2 = M.check([mk(i, 0.05) for i in range(10)] + [mk(10 + i, M.R24_P5 - 0.005) for i in range(24)])
check("T3c ALERT on r24 < p5", v2["level"] in ("ALERT", "DECIDE"), str(v2))
v3 = M.check([mk(i, M.R24_P1 - 0.01) for i in range(24)])
check("T3d DECIDE on r24 < p1", v3["level"] == "DECIDE", str(v3))
v4 = M.check([mk(i, 0.05) for i in range(30)] + [{"anchor_ts": W - 999999, "rank_ic": -9.9}])
check("T3e pre-window rows excluded", v4["level"] == "OK",
      "rows before WINDOW_START_TS must not be judged")

# [T4] β 严格因果: compute_rows 内 history 推进必须在 IC 计算之后(静态序检查)
src = open(os.path.join(_REPO, "ops", "ic_monitor.py")).read()
i_ic = src.find("ic = _spear(pos, ret)")
i_push = src.find("# push history AFTER computing")
check("T4 beta history pushed AFTER ic computation", 0 < i_ic < i_push,
      f"idx ic={i_ic} push={i_push}")

# [T5] launchd plist 存在且指向本脚本
_pl = os.path.expanduser("~/Library/LaunchAgents/com.dlquant.live.icmonitor.plist")
check("T5a plist exists", os.path.exists(_pl))
if os.path.exists(_pl):
    _pt = open(_pl).read()
    check("T5b plist runs ops/ic_monitor.py", "ops/ic_monitor.py" in _pt)

# [T6] 幂等: known_ts 内的锚不重复产行
rows6 = M.compute_rows({W: {"A": (100.0, 1.0), "B": (-100.0, 2.0)}}, known_ts={W})
check("T6 known anchors skipped", rows6 == [], str(rows6))

n = len(FAIL)
print(f"\ntests_ic_monitor: {'ALL PASS' if n == 0 else f'{n} FAIL: {FAIL}'}")
sys.exit(1 if n else 0)
