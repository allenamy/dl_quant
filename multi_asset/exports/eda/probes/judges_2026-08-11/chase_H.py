"""chase 主判据补全: E[H] − E[X] (PREREG_chase_opportunity_cost 裁定版-A, 全冻结条款)
§2 追 iff E[H]>E[X], 同单位=残差名义 bps · §3-1 H=q×(P_next−P_w)/P_w, P_w=补单行 mid_at_anchor,
P_next=下一锚 mid_at_anchor_vector · §5-2 总体=越地板(terminal_reason≠skipped_min_notional),
处理=skipped_no_chase_arm, chase_forced 永不入样 · §5-2bis 平衡检验 D, cluster bootstrap B=20000 seed 0,
CI 排 0 ⇒ 自动切 ITT · §4-3 情形占比+次级判据(E[S] 的 c_{a+1} 用下一锚实测费率, 无 adverse ⇒ 低估, 明标)
"""
import json, glob, math
import numpy as np

LOG = "state/live/pilot_log"
A, O = {}, {}                                   # nominal4h -> anchors row / [order rows]
for f in sorted(glob.glob(f"{LOG}/2026*/anchors.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        if d.get("anchor_ts"): A[int(float(d["anchor_ts"])//14400)] = d
for f in sorted(glob.glob(f"{LOG}/2026*/orders.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        if d.get("anchor_ts"): O.setdefault(int(float(d["anchor_ts"])//14400), []).append(d)

def mids(k):
    v = A.get(k, {}).get("mid_at_anchor_vector")
    if isinstance(v, str):
        try: v = json.loads(v)
        except: v = None
    return v or {}

# in-sample 锚 = chase_experiment.in_sample(运行时记录, 与 readout 同源)
ins = []
for k, a in sorted(A.items()):
    ce = a.get("chase_experiment") or {}
    if isinstance(ce, str):
        try: ce = json.loads(ce)
        except: ce = {}
    if ce and ce.get("in_sample"): ins.append(k)
print(f"in-sample 锚 {len(ins)}  (最后一锚若无下一锚 mid 则从 H 侧剔除, 明标)")

rows_H, rows_X, bal = [], [], {}
case_i = case_ii = 0; S_usd = 0.0; S_q = 0.0
for k in ins:
    gross = float(A[k].get("target_gross") or 0) or 1.0
    m1 = mids(k+1)
    nx = {r["symbol"]: r for r in O.get(k+1, []) if r.get("target_w") is not None}
    cf = [r for r in O.get(k+1, []) if r.get("fee_all_usdt")]
    fee_n = sum(float(r["fee_all_usdt"]) for r in cf)
    fee_d = sum(abs(float(r.get("filled_notional") or 0))*gross for r in cf)
    c_next = fee_n/fee_d if fee_d > 0 else float("nan")
    for r in O.get(k, []):
        if r.get("topup_source") != "from_partial": continue
        arm = r.get("chase_arm")
        if arm not in ("chase", "no_chase"): continue
        crossed = r.get("terminal_reason") != "skipped_min_notional"
        bal.setdefault(k, {"chase": [0, 0], "no_chase": [0, 0]})[arm][0] += 1
        if crossed: bal[k][arm][1] += 1
        if not crossed: continue
        q = float(r.get("intended_notional") or 0); Pw = r.get("mid_at_anchor")
        if not q or not Pw: continue
        sym = r["symbol"]
        if arm == "no_chase" and r.get("terminal_reason") == "skipped_no_chase_arm":
            Pn = m1.get(sym)
            if Pn:
                rows_H.append((k, q*gross, q*gross*(float(Pn)-float(Pw))/float(Pw)))
                d = 0.0
                if sym in nx:
                    d = (float(nx[sym]["target_w"]) - float(nx[sym].get("prev_w") or 0))
                    d = d/abs(d)*abs(float(nx[sym].get("intended_notional") or d)) if d else 0.0
                opp = (abs(d) < 1e-9) or (d*q < 0)
                case_i += opp; case_ii += (not opp)
                if not math.isnan(c_next):
                    S_usd += (abs(d)-abs(d-q))*gross*c_next; S_q += abs(q)*gross
        elif arm == "chase":
            F = r.get("avg_fill_px"); fee = float(r.get("fee_all_usdt") or 0)
            adv = q*gross*(float(F)-float(Pw))/float(Pw) if F else 0.0
            if F or fee: rows_X.append((k, q*gross, adv+fee))

qH = sum(abs(q) for _, q, _ in rows_H); H = sum(h for _, _, h in rows_H)
qX = sum(abs(q) for _, q, _ in rows_X); X = sum(x for _, _, x in rows_X)
EH, EX = H/qH*1e4, X/qX*1e4
print(f"\nE[H] 持有价值(no_chase 扣下, n={len(rows_H)} 名, |q| {qH:,.0f} USDT) = {EH:+.2f} bps")
print(f"E[X] 支付成本(chase 成交,  n={len(rows_X)} 名, |q| {qX:,.0f} USDT) = {EX:+.2f} bps")
print(f"主判据 ATE = E[H] − E[X] = {EH-EX:+.2f} bps   ⇒ {'追价值得' if EH>EX else '【不追】更好'}")

# 锚级 cluster bootstrap (B=20000, seed 0 —— §5-2bis 同参)
rng = np.random.default_rng(0)
ks = sorted(set(k for k, _, _ in rows_H) | set(k for k, _, _ in rows_X))
hk = {k: [0., 0.] for k in ks}; xk = {k: [0., 0.] for k in ks}
for k, q, h in rows_H: hk[k][0] += h; hk[k][1] += abs(q)
for k, q, x in rows_X: xk[k][0] += x; xk[k][1] += abs(q)
bs = []
for _ in range(20000):
    pick = rng.choice(ks, len(ks), replace=True)
    hn = sum(hk[k][0] for k in pick); hd = sum(hk[k][1] for k in pick)
    xn = sum(xk[k][0] for k in pick); xd = sum(xk[k][1] for k in pick)
    if hd > 0 and xd > 0: bs.append((hn/hd - xn/xd)*1e4)
lo, hi = np.percentile(bs, [2.5, 97.5])
print(f"  锚级 cluster bootstrap CI95 [{lo:+.2f}, {hi:+.2f}]  " +
      ("排除 0" if lo > 0 or hi < 0 else "含 0 ⇒ 方向不显著"))

# §4-3 情形占比 + 次级判据
tot = case_i + case_ii
print(f"\n§4-3 情形占比: (i) 残差消失/反号 {case_i}/{tot} = {case_i/max(tot,1):.0%}   "
      f"(ii) 同向延续 {case_ii}/{tot} = {case_ii/max(tot,1):.0%}")
ES = S_usd/S_q*1e4 if S_q else float("nan")
print(f"E[S](二阶差, c_next=下一锚实测费率【无 adverse ⇒ 低估】) = {ES:+.2f} bps")
print(f"次级判据 E[H]−E[X]+E[S] = {EH-EX+ES:+.2f} bps")

# §5-2bis 平衡检验
D = []
for k, v in bal.items():
    rn = v["no_chase"][1]/v["no_chase"][0] if v["no_chase"][0] else None
    rc = v["chase"][1]/v["chase"][0] if v["chase"][0] else None
    if rn is not None and rc is not None: D.append(rn-rc)
D = np.array(D); rng2 = np.random.default_rng(0)
bsD = [D[rng2.integers(0, len(D), len(D))].mean() for _ in range(20000)]
l2, h2 = np.percentile(bsD, [2.5, 97.5])
print(f"\n§5-2bis 平衡检验 D = {D.mean():+.4f}  CI95[{l2:+.4f},{h2:+.4f}]  " +
      ("★排除 0 ⇒ 主判据自动切 ITT(本读数作废, 须按 ITT 重出)" if l2 > 0 or h2 < 0 else "含 0 ⇒ per-protocol 有效"))
print("\nCHASE_H_DONE")
