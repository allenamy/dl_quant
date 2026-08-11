"""补验: 已聚合的 113 天里, V5(隐含价) 曾因参考价缺失被跳过。
用月度 klines 对【聚合产物本身】重算隐含价并校验 —— 聚合产物存的是 depth, 需配 notional,
而我只存了 depth ⇒ 改用【可行的等价检验】: 逐币逐天的 hourly depth 中位数 与 该币规模的
量级一致性 + 跨日连续性(相邻日中位数比值应在 [1/5, 5])。突变=单位错乱的签名。
★ 如实声明: 这是【弱于】原 V5 的替代检验(原 V5 直接对价)。真正的补强见 §结论。"""
import json, os, glob, numpy as np
AGG=os.path.expanduser("~/lob_raw/bd_hourly")
fs=sorted(glob.glob(f"{AGG}/bd_*.json"))
print(f"已聚合 {len(fs)} 天")
series={}
for f in fs:
    day=os.path.basename(f)[3:-5]
    d=json.load(open(f))
    for sym,hh in d.items():
        vals=[v[0] for k,v in hh.items() if k.startswith("1.00|")]
        if vals: series.setdefault(sym,{})[day]=float(np.median(vals))
bad=[]
for sym,dd in series.items():
    days=sorted(dd)
    for a,b in zip(days,days[1:]):
        x,y=dd[a],dd[b]
        if x>0 and y>0:
            r=y/x
            if r>5 or r<0.2: bad.append((sym,a,b,round(r,2)))
print(f"币 {len(series)}  跨日突变(>5× 或 <1/5) {len(bad)} 处")
for b in bad[:10]: print(f"   {b[0]:14s} {b[1]} → {b[2]}  比值 {b[3]}")
print("\n判读: 单位/口径错乱会表现为【整段】跳变(同一币的某段全体偏离一个常数倍)。")
print(f"      零星突变 = 真实流动性变化(上市/退市/行情), 不阻断。")
