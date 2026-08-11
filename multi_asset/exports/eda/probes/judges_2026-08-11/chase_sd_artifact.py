"""§7-4 产物 `chase_sd_artifact.json` —— 机会成本 H 口径的 sd, 供冻结 N*。

预注册: PREREG_chase_opportunity_cost_2026-08-03.md (裁定版-A, frozen)
几何(§3-1, 逐字):
    H_i = q_i × (P_next − P_w)/P_w    [USDT]   报告 = H_i/|q_i| × 1e4  [bps]
    q_i = 扣下时刻带符号残差 = 补单行 intended_notional (topup_source=="from_partial")
    P_w = 该锚 mid_at_anchor (§3-2 裁定, 两臂同一个价)
    P_next = 下一锚 anchors.jsonl 的 mid_at_anchor_vector[symbol] (冻结口径: 用 mid 不用成交价)
总体(§5-1/§5-2): 越地板名字 = {chase+filled} ∪ {no_chase+skipped_no_chase_arm}
    ★ chase_forced 永不并入(冻结条款); skipped_min_notional 是地板以下, 不属随机化总体。

★★ 内建方向屏障: 本脚本【只】输出 sd 与计数。任何均值 / ATE / 臂间差一律不计算不打印
   —— 预注册的整个顺序门就是"方差步先于方向步", 自己印一个均值就等于自己破门。
"""
import json, glob, math, statistics as st, datetime as dt
import numpy as np

LIVE = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
OUT = "/Users/haosiyu/dl_quant_live/state/live/chase_sd_artifact.json"
MDE_BPS = 37.0                      # ★ team-lead 裁定 Q1 冻结, 不是本脚本选的
Z2 = 7.8489                         # (Φ⁻¹(.975)+Φ⁻¹(.80))²

anch = {}
for f in sorted(glob.glob(f"{LIVE}/2026*/anchors.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        rid = d.get("rebalance_id")
        if rid:
            anch[rid] = d
seq = sorted(anch.values(), key=lambda d: d.get("anchor_ts") or 0)
nxt = {}
for a, b in zip(seq[:-1], seq[1:]):
    nxt[a["rebalance_id"]] = b
print(f"锚点 {len(seq)}  可取下一锚的 {len(nxt)}")

POP = []
for f in sorted(glob.glob(f"{LIVE}/2026*/orders.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        if d.get("topup_source") != "from_partial":
            continue
        arm = d.get("chase_arm") or d.get("chase_arm_assigned")
        tr = d.get("terminal_reason")
        if arm == "chase" and tr == "filled":
            POP.append((d, "chase"))
        elif arm == "no_chase" and tr == "skipped_no_chase_arm":
            POP.append((d, "no_chase"))
print(f"随机化总体行 {len(POP)}  (chase {sum(1 for _,a in POP if a=='chase')} / "
      f"no_chase {sum(1 for _,a in POP if a=='no_chase')})")

rows = []
miss = {"no_next": 0, "no_mid_next": 0, "bad_pw": 0}
for d, arm in POP:
    rid = d.get("rebalance_id"); nb = nxt.get(rid)
    if nb is None:
        miss["no_next"] += 1; continue
    mv = nb.get("mid_at_anchor_vector") or {}
    if isinstance(mv, str):                       # 落盘为 JSON 字符串, 需再解一层
        try: mv = json.loads(mv)
        except Exception: mv = {}
    pn = mv.get(d["symbol"])
    if pn is None or not np.isfinite(float(pn)) or float(pn) <= 0:
        miss["no_mid_next"] += 1; continue
    pw = d.get("mid_at_anchor")
    if pw is None or not np.isfinite(float(pw)) or float(pw) <= 0:
        miss["bad_pw"] += 1; continue
    q = float(d.get("intended_notional") or 0.0)
    if abs(q) < 1e-12:
        continue
    h_bps = math.copysign(1.0, q) * (float(pn) - float(pw)) / float(pw) * 1e4
    rows.append({"rid": rid, "ts": d.get("anchor_ts") or nb.get("anchor_ts"),
                 "sym": d["symbol"], "arm": arm, "q": q, "H_bps": h_bps,
                 "regime": (anch.get(rid) or {}).get("regime_at_anchor")})
print(f"可算 H 的行 {len(rows)}   丢弃 {miss}")

by = {}
for r in rows:
    by.setdefault(r["rid"], []).append(r)
per_anchor = []
for rid, g in sorted(by.items(), key=lambda x: x[1][0]["ts"] or 0):
    w = np.array([abs(r["q"]) for r in g]); h = np.array([r["H_bps"] for r in g])
    per_anchor.append({
        "rebalance_id": rid,
        "anchor_ts": g[0]["ts"],
        "n_pop_restricted": len(g),
        "n_chase": sum(1 for r in g if r["arm"] == "chase"),
        "n_no_chase": sum(1 for r in g if r["arm"] == "no_chase"),
        "H_anchor_bps": float(np.sum(w*h)/max(w.sum(), 1e-12)),   # 名义加权(§7-3 假设)
        "regime_at_anchor": g[0]["regime"],
    })

Ha = np.array([a["H_anchor_bps"] for a in per_anchor])
sd_between = float(np.std(Ha, ddof=1)) if len(Ha) > 2 else float("nan")
resid = []
for rid, g in by.items():
    for arm in ("chase", "no_chase"):
        v = [r["H_bps"] for r in g if r["arm"] == arm]
        if len(v) >= 2:
            m = float(np.mean(v)); resid += [x - m for x in v]
sd_within = float(np.std(resid, ddof=1)) if len(resid) > 2 else float("nan")

nc = float(np.mean([a["n_chase"] for a in per_anchor]))
nn = float(np.mean([a["n_no_chase"] for a in per_anchor]))
var_d = (sd_within**2) * (1.0/max(nc, 1e-9) + 1.0/max(nn, 1e-9)) + sd_between**2
n_star = int(math.ceil(Z2 * var_d / MDE_BPS**2))

reg = {}
for a in per_anchor:
    reg[str(a["regime_at_anchor"])] = reg.get(str(a["regime_at_anchor"]), 0) + 1

ART = {
    "caliber": "opportunity_cost_H_bps",      # ★ §7-4 必填, 存在的唯一理由是防止填成本侧 sd
    "produced_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    "prereg": "PREREG_chase_opportunity_cost_2026-08-03.md (裁定版-A)",
    "population_rule": "from_partial ∩ ({chase,filled} ∪ {no_chase,skipped_no_chase_arm}); "
                       "chase_forced 永不并入; skipped_min_notional 属地板以下不入总体",
    "n_anchors": len(per_anchor),
    "n_rows": len(rows),
    "mean_n_chase_per_anchor": round(nc, 2),
    "mean_n_no_chase_per_anchor": round(nn, 2),
    "sd_within_name_bps": round(sd_within, 3),
    "sd_between_anchor_bps": round(sd_between, 3),
    "MDE_bps": MDE_BPS,
    "MDE_source": "team-lead 裁定 Q1 (§7-2), 冻结; 本脚本不选择 MDE",
    "n_star": n_star,
    "n_star_formula": "ceil(7.8489 × [sd_within²(1/n_c+1/n_nc) + sd_between²] / MDE²)",
    "assumed_regime_mix": reg,     # ★ 无此字段则 readout 会拒绝 N*
    "regime_mix_note": "观测到的逐锚 regime 计数。N* 只在这个 mix 下成立; mix 移动须重算。",
    "per_anchor": per_anchor,
    "NOT_PRODUCED_vs_spec": ["terminal_case_mix (§4-2 情形分类未实现)",
                             "carry_frac (§4-4 对称定义未实现)",
                             "密封份 (§7-4 要求公开/密封两份, 本次只产公开份)"],
    "direction_barrier": "本产物【不含】任何均值/ATE/臂间差 —— 方差步先于方向步是预注册的门本身。",
}
json.dump(ART, open(OUT, "w"), indent=1, ensure_ascii=False)

print("\n" + "="*70)
print(f"caliber              = {ART['caliber']}")
print(f"n_anchors            = {ART['n_anchors']}   n_rows = {ART['n_rows']}")
print(f"每锚 chase / no_chase = {nc:.2f} / {nn:.2f}")
print(f"sd_within_name_bps   = {sd_within:.3f}")
print(f"sd_between_anchor_bps= {sd_between:.3f}   ← N* 主输入")
print(f"MDE (冻结)           = {MDE_BPS}")
print(f"★ N*                 = {n_star} 锚   ({n_star/6.0:.1f} 天 @6锚/日)")
print(f"  现有样本内锚        = {len(per_anchor)}")
gap = max(n_star - len(per_anchor), 0)
print(f"  还差                = {gap} 锚 ≈ {gap/6.0:.1f} 天")
print(f"regime mix           = {reg}")
print("="*70)
print("★ 方向仍被屏蔽: 本产物不含任何均值。冻结 N* 后由 chase_readout.py 出方向。")
print(f"-> {OUT}\nSDART_DONE")
