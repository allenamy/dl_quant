"""W2 · 宽书影子前向腿级追踪器(每次运行追加一行; 2026-08-22, Session 6737834a-W2; 08-30 判读包用它盯宽 fund 腿的前向符号)。

输入(全部只读, 不写 ~/wide_shadow 任何文件):
  ~/wide_shadow/shadow_log.jsonl             影子逐锚日志: e="signal"(anchor_ts, w3, gross_pos, carry_bps, cost_bps, ...) 与 e="score"(上一锚结账: gross_bps/net_bps/carry_bps/cost_bps)
  ~/wide_shadow/state/leg_returns_live.json   影子 LR 的最后 950 条(= 900 回看 + 50; 见 shadow_loop.py save(): n_keep=950), 三腿 king/rev24/fund
  ~/wide_shadow/shadow_bundle/leg_returns.npz 种子 LR(2022-01-31 → 2026-08-15, 9943 锚), 仅用于对齐
对齐假设(shadow_loop.py L128-131 / L142-143 / L306-328):
  · 启动时 LR = 种子 + leg_returns_live.json; 每锚落盘 LR[-950:] ⇒ json 前缀 = 种子尾部, 后缀 = 影子实盘新增; 实盘新增条数 < 950 时, 取 json 与种子尾部的最长前缀重叠 k(逐元素 allclose), live = json[k:]。
  · 腿收益在【下一锚】结账时追加(与 e="score" 同块、同条件: 连续 4h 锚), ⇒ live 条数应 = score 事件数; 两者不等时写 flag(不硬停)。
  · 若重叠 k=0(live 已 ≥950 条, 种子尾部被挤出), 退回按 score 事件数取 json 尾部, 并打 truncated 旗。
单位:
  · 三腿价格累计 = 纯价格、单位【腿 gross】(xz 秩腿, 去均值, L1=1; 无 w3 权重、无 carry、无成本)的 bps/锚累计 —— 不是书 gross, 不是 NAV。
  · score 的 gross/net/carry/cost = 影子书在其原生 gross(gross_pos≈1.38)下的 NAV bps/锚; 另给 ÷ 同锚 gross_pos 的"每单位书 gross"版本。carry 正 = 付出。
输出: 追加一行 JSON 到 results/shadow_leg_tracker.jsonl, 并打印该行。用法: python3 w2_shadow_leg_tracker.py [--no-append]
"""
import os, sys, json, time, hashlib, numpy as np
HOME = os.path.expanduser("~"); SH = os.path.join(HOME, "wide_shadow")
LOG = os.path.join(SH, "shadow_log.jsonl"); LIVE = os.path.join(SH, "state", "leg_returns_live.json"); SEED = os.path.join(SH, "shadow_bundle", "leg_returns.npz")
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "results", "shadow_leg_tracker.jsonl")
LEGS = ("king", "rev24", "fund")
def sha(p):
    h = hashlib.sha256(); h.update(open(p, "rb").read()); return h.hexdigest()[:16]
def fmt(t): return time.strftime("%Y-%m-%d %H:%M", time.gmtime(int(t)))
rows = [json.loads(l) for l in open(LOG) if l.strip()]
sig = [r for r in rows if r.get("e") == "signal" and r.get("status") == "OK"]
score = [r for r in rows if r.get("e") == "score"]
live = json.load(open(LIVE)); seed = np.load(SEED, allow_pickle=True)
flags = []
# ---- alignment: longest prefix of json == tail of seed ----
arr = {leg: np.asarray(live[leg], float) for leg in LEGS}; sd = {leg: np.asarray(seed[leg], float) for leg in LEGS}
k_found = 0
for k in range(len(arr["fund"]), 0, -1):
    if all(len(sd[l]) >= k and np.allclose(arr[l][:k], sd[l][len(sd[l]) - k:], equal_nan=True) for l in LEGS):
        k_found = k; break
if k_found > 0:
    lv = {leg: arr[leg][k_found:] for leg in LEGS}; method = f"seed_overlap(k={k_found})"
else:
    n = min(len(score), len(arr["fund"])); lv = {leg: arr[leg][len(arr[leg]) - n:] for leg in LEGS}; method = f"fallback_score_count(n={n})"; flags.append("seed_overlap_not_found_or_truncated")
n_live = len(lv["fund"])
if n_live != len(score): flags.append(f"n_live_leg({n_live})!=n_score({len(score)})")
if len(arr["fund"]) >= 950 and k_found == 0: flags.append("json_truncated_950")
# ---- per-leg stats (bps of leg gross) ----
def stats(x):
    x = np.asarray(x, float)
    if len(x) == 0: return {"cum_bps": None, "mean": None, "pos_frac": None, "t": None, "last6": []}
    return {"cum_bps": round(float(x.sum()), 1), "mean": round(float(x.mean()), 2), "pos_frac": round(float((x > 0).mean()), 3),
            "t": round(float(x.mean() / (x.std(ddof=1) + 1e-12) * np.sqrt(len(x))), 2) if len(x) > 1 else None, "last6": [round(float(v), 1) for v in x[-6:]]}
legstat = {leg: stats(lv[leg]) for leg in LEGS}
# ---- score (book realized, NAV bps at native gross) + per-unit-gross ----
gp = {int(r["anchor_ts"]): float(r.get("gross_pos", np.nan)) for r in sig}
def sc_sum(key, per_unit=False):
    v = []
    for r in score:
        x = float(r.get(key, np.nan)); g = gp.get(int(r["anchor_ts"]), np.nan)
        v.append(x / g if per_unit else x)
    v = np.array(v, float); v = v[np.isfinite(v)]
    return (round(float(v.sum()), 2), round(float(v.mean()), 3)) if len(v) else (None, None)
book = {}
for key in ("gross_bps", "net_bps", "carry_bps", "cost_bps"):
    book[key + "_cum"], book[key + "_mean"] = sc_sum(key); book[key + "_cum_per_unit_gross"], _ = sc_sum(key, True)
carry_sig = np.array([float(r.get("carry_bps", np.nan)) for r in sig]); gpos = np.array([float(r.get("gross_pos", np.nan)) for r in sig]); w3 = np.array([r.get("w3", [np.nan] * 3) for r in sig], float)
row = {"run_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "inputs_sha16": {"shadow_log.jsonl": sha(LOG), "leg_returns_live.json": sha(LIVE), "seed_leg_returns.npz": sha(SEED)},
       "n_signal_ok": len(sig), "first_signal_anchor": fmt(sig[0]["anchor_ts"]) if sig else None, "last_signal_anchor": fmt(sig[-1]["anchor_ts"]) if sig else None,
       "n_score": len(score), "last_score_anchor": fmt(score[-1]["anchor_ts"]) if score else None,
       "n_live_leg_anchors": n_live, "align_method": method, "flags": flags,
       "leg_price_bps_of_leg_gross": legstat,
       "fund_pos_frac": legstat["fund"]["pos_frac"], "fund_cum_bps": legstat["fund"]["cum_bps"], "fund_t": legstat["fund"]["t"],
       "book_score_NAVbps_at_native_gross": book,
       "signal_carry_bps_mean_per_anchor(paid)": round(float(np.nanmean(carry_sig)), 3) if len(sig) else None,
       "signal_carry_cum_bps(paid)": round(float(np.nansum(carry_sig)), 2) if len(sig) else None,
       "signal_carry_per_unit_gross_mean": round(float(np.nanmean(carry_sig / gpos)), 3) if len(sig) else None,
       "gross_pos_mean": round(float(np.nanmean(gpos)), 3) if len(sig) else None, "w3_mean[king,rev24,fund]": [round(float(v), 3) for v in np.nanmean(w3, 0)] if len(sig) else None,
       "w3_last": [round(float(v), 3) for v in w3[-1]] if len(sig) else None,
       "units": "leg cum = bps per unit LEG gross (pure price, no w3/carry/cost, realized next anchor); book score = NAV bps at native gross_pos; carry positive = paid"}
line = json.dumps(row, ensure_ascii=False)
print(line)
if "--no-append" not in sys.argv:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "a") as f: f.write(line + "\n")
    print("appended ->", OUT)
