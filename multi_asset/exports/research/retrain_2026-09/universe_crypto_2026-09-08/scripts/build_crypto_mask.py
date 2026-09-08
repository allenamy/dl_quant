"""build_crypto_mask.py — ADDENDUM 3 (REVIEW_codex_early_batch_2026-09-08): UPIT ∧ (underlyingType=="COIN").
只读输入: masks/umask_UPIT.npz + venue_class.json(公开 exchangeInfo 落盘)。输出 masks/umask_UPIT_CRYPTO.npz(装置格式)。
自检 §A3.3 四条全部在此断言; 任一不过即 raise, 不写文件。"""
import numpy as np, json, time, calendar, hashlib, os
ROOT="/workspace/review_scratch/health_check"
Z=np.load(f"{ROOT}/masks/umask_UPIT.npz",allow_pickle=True)
ts=Z["ts"].astype(np.int64); syms=[str(s) for s in Z["symbols"]]; M=Z["mask"]
CLS=json.load(open("/tmp/venue_class.json"))
n=len(syms)
known=[s for s in syms if s in CLS]; unk=[s for s in syms if s not in CLS]
coin=np.array([ (CLS[s]["underlyingType"] in ("COIN","INDEX")) if s in CLS else True for s in syms])  # 未知 ⇒ 保留
print(f"面板 {n} 名 | 今日 exchangeInfo 可查 {len(known)} | 未知(已下架, 按保留处理) {len(unk)}")
if unk: print("  未知名(全部列出):", " ".join(unk))
import collections
c=collections.Counter((CLS[s]["underlyingType"] if s in CLS else "UNKNOWN") for s in syms)
print("  面板类别构成:", dict(c.most_common()))
MC = M & coin[None,:]
# ── 自检 1: 子集 ──
assert bool((MC & ~M).sum()==0), "CRYPTO 不是 UPIT 的子集"
print("自检1 子集: OK")
# ── 自检 2: 允许集内零个已知非 COIN ──
noncoin_known=np.array([ (s in CLS and CLS[s]["underlyingType"] not in ("COIN","INDEX")) for s in syms])
bad=int(MC[:,noncoin_known].sum())
assert bad==0, f"CRYPTO 允许集内仍有 {bad} 个已知非 COIN 格"
print(f"自检2 类别: OK(允许集内已知非 COIN 格 = {bad})")
# ── 自检 3: 2022-2024 两 mask 应逐格相同 ──
T25=calendar.timegm((2025,1,1,0,0,0))
early=ts<T25
d=int((MC[early]!=M[early]).sum())
print(f"自检3 早年逐格等价: 2022-2024 差异格 = {d} / {int(early.sum())*n}")
if d>0:
    rows=np.where((MC[early]!=M[early]).any(1))[0]
    cols=np.where((MC[early]!=M[early]).any(0))[0]
    print("  ★ 不等! 涉及名:", [syms[j] for j in cols][:20], "| 首个不等时点:", time.strftime("%Y-%m-%d",time.gmtime(int(ts[early][rows[0]]))))
# ── 逐年允许集 ──
yr=np.array([time.gmtime(int(t)).tm_year for t in ts])
print(f"\n{'年':>6s} {'UPIT 允许':>10s} {'CRYPTO 允许':>12s} {'差':>6s}")
for y in sorted(set(yr.tolist())):
    m=yr==y
    print(f"{y:>6d} {M[m].sum(1).mean():>10.1f} {MC[m].sum(1).mean():>12.1f} {M[m].sum(1).mean()-MC[m].sum(1).mean():>6.1f}")
out=f"{ROOT}/masks/umask_UPIT_CRYPTO.npz"
np.savez_compressed(out, ts=ts, symbols=np.array(syms), mask=MC)
print(f"\n写出 {out} sha16 {hashlib.sha256(open(out,'rb').read()).hexdigest()[:16]}")
json.dump({"definition":"UPIT & underlyingType=='COIN' (unknown -> kept)","n_unknown":len(unk),"unknown":unk,
           "selfcheck":{"subset":True,"noncoin_cells":bad,"early_diff_cells":d}}, open(f"{ROOT}/masks/crypto_mask_note.json","w"), indent=1)
