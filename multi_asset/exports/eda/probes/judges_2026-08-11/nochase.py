"""停 chase 到底省多少 —— 用实盘一手记录直接算, 不跨口径。
预注册: 本测量无自由参数, 判据即算术恒等式; 结论只报点估计 + 锚级 bootstrap CI。
口径: 全部以【书毛额 target_gross】为分母, 与净额 bps 同尺。
"""
import json, glob, numpy as np
LOG = "/Users/haosiyu/dl_quant_live/state/live/pilot_log"
A = {}
for f in sorted(glob.glob(f"{LOG}/2026*/anchors.jsonl")):
    for L in open(f):
        try: d = json.loads(L)
        except: continue
        if d.get("anchor_ts"): A[int(float(d["anchor_ts"])//14400)] = d
per = []
for k, a in sorted(A.items()):
    ce = a.get("chase_experiment") or {}
    if isinstance(ce, str):
        try: ce = json.loads(ce)
        except: ce = {}
    if not ce.get("in_sample"): continue
    g = float(a.get("target_gross") or 0)
    if g <= 0: continue
    fee = adv = 0.0; note = 0.0
    for f in sorted(glob.glob(f"{LOG}/2026*/orders.jsonl")):
        pass
    per.append((k, g))
print("(骨架已就位; 需与 orders.jsonl 的 topup 行连接后出数 —— 见 chase_H.py 的读取逻辑)")
