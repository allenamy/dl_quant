#!/usr/bin/env python3
"""FTRIM 首锚/逐锚验收(只读; PREREG_deploy_ftrim_2026-09-02 §3 修正版): 用法 python3 check_ftrim_anchor.py <anchor_ts>
断言: ① target_combo 记录含 ftrim, 规则串/覆盖率 ≥0.95, 3 ≤ n_kc ≤ 60; ② 每个排除名 rn8 ≤ −0.0010;
③ 排除名在 target_live 中: 未持仓者权重为 0/缺席(不新开空头); 已持仓者 |w_new| ≤ |w_prev|(EMA 衰减, 不加仓);
④ gross_norm 与上锚差 ≤ 10%; ⑤ 无频带外名被误置零: 记录里所有名都满足 ②(闭合)。exit 0 = PASS."""
import json, sys, os, numpy as np
WS='/Users/haosiyu/wide_shadow'; A=int(sys.argv[1]); prev=A-14400
fails=[]; ok=lambda c,m: (None if c else fails.append(m))
tc=f'{WS}/state/target_combo/{A}.json'; ok(os.path.exists(tc), f"no target_combo {A}")
rec=json.load(open(tc)) if os.path.exists(tc) else {}
ft=rec.get('ftrim') or {}; ok(bool(ft), "record has no ftrim block")
if ft:
    ok(ft.get('rule')=='pre_zero_rn8_le_-10bp_8h', f"rule {ft.get('rule')}")
    ok(float(ft.get('rn8_coverage',0))>=0.95, f"rn8 coverage {ft.get('rn8_coverage')}")
    ok(3<=int(ft.get('n_kc',0))<=60, f"n_kc {ft.get('n_kc')} outside [3,60]")
    for side in ('names_kc','names_fc'):
        for nm,v in (ft.get(side) or {}).items(): ok(float(v)<=-0.0010, f"{side} {nm} rn8 {v} > -10bp")
def wts(ts):
    p=f'{WS}/state/target_live/{ts}.json'
    if not os.path.exists(p): return None
    d=json.load(open(p)); w=d.get('weights',{}); return {k:float(v) for k,v in w.items()}, d
cur=wts(A); prv=wts(prev); ok(cur is not None, f"no target_live {A}")
if cur and ft:
    wc,dc=cur; wp=prv[0] if prv else {}
    excl=set((ft.get('names_kc') or {}))|set((ft.get('names_fc') or {}))
    for nm in excl:
        wn=wc.get(nm,0.0); wo=wp.get(nm,0.0)
        if abs(wo)<1e-12: ok(abs(wn)<1e-12 or wn>0, f"{nm} newly opened short {wn:.5f}")
        else: ok(abs(wn)<=abs(wo)+1e-9, f"{nm} |w| increased {wo:.5f}->{wn:.5f}")
    gn=float(dc.get('gross_norm', np.nan)); gp=float((prv[1] if prv else {}).get('gross_norm', np.nan))
    if np.isfinite(gn) and np.isfinite(gp): ok(abs(gn/gp-1)<=0.10, f"gross_norm jump {gp:.4f}->{gn:.4f}")
    print(f"anchor {A}: excluded kc {ft.get('n_kc')} fc {ft.get('n_fc')} | 排除名当前 |w| 合计 {sum(abs(wc.get(n,0)) for n in excl):.4f} (上锚 {sum(abs(wp.get(n,0)) for n in excl):.4f}) | gross_norm {gn:.4f} (上锚 {gp:.4f})")
print("PASS" if not fails else "FAIL: "+"; ".join(fails)); sys.exit(0 if not fails else 1)
