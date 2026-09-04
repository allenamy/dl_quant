"""给 w10_universe.py 加 KSVOL 开关(king 空头凸性修正): KSVOL=0 关(默认路径逐字不变); KSVOL=20/30: king 的 xz 中, 空头(xz<0)里 σ 处于空头 σ 分布顶 KSVOL% 的名置零; KSVOL_INV=1: 改为空头按 1/σ 缩放(乘空头 σ 中位数). σ_i = 该名过去 KSVOL_WIN(默认 42)行 y4 的 nanstd(只用锚 i 之前已实现的行)。应用点: legs()(席位用腿收益)与 run() 的 kc 链 king 项。"""
import sys, re
p = sys.argv[1]; s = open(p).read()
assert "KSVOL" not in s, "already patched"
# 1) 开关声明: 插在 KMOD_L 行之后
anchor = 'KMOD_L = float(os.environ.get("KMOD_L", "0.5"))'
i = s.index(anchor); j = s.index("\n", i)
decl = '''
KSVOL = int(os.environ.get("KSVOL", "0")); assert KSVOL in (0, 20, 30)          # KC1: king 空头凸性修正 — 空头中 σ 顶 KSVOL% 的名置零(0=关)
KSVOL_INV = int(os.environ.get("KSVOL_INV", "0")); assert KSVOL_INV in (0, 1)     # KC2: 空头按 1/σ 缩放(乘空头 σ 中位数), 与 KSVOL 互斥
KSVOL_WIN = int(os.environ.get("KSVOL_WIN", "42")); assert KSVOL_WIN in (42, 84)
assert not (KSVOL and KSVOL_INV), "KSVOL 与 KSVOL_INV 互斥"'''
s = s[:j] + decl + s[j:]
# 2) _CFG 自报
s = s.replace('_CFG = {"KMOD_F10": KMOD_F10,', '_CFG = {"KSVOL": KSVOL, "KSVOL_INV": KSVOL_INV, "KSVOL_WIN": KSVOL_WIN, "KMOD_F10": KMOD_F10,', 1)
# 3) helper: 放在 def legs 之前
helper = '''
def _ksig(i, m):
    """点时 σ_i: y4 行 i-KSVOL_WIN..i-1(在锚 i 全部已实现)的 nanstd; 有限行 <20 或 σ 无效 → 用中位数补."""
    lo = max(0, i - KSVOL_WIN)
    if i - lo < 20: return None
    h = y4[lo:i, m]; n = np.isfinite(h).sum(0)
    with np.errstate(all="ignore"):
        sg = np.nanstd(h, axis=0)
    sg = np.where((n >= 20) & np.isfinite(sg) & (sg > 1e-4), sg, np.nan)
    if not np.isfinite(sg).any(): return None
    return np.where(np.isfinite(sg), sg, np.nanmedian(sg))
def kfix(zk, i, m):
    """king xz 的空头凸性修正(KSVOL/KSVOL_INV); 关时原样返回."""
    if not (KSVOL or KSVOL_INV): return zk
    sg = _ksig(i, m)
    if sg is None: return zk
    sh = zk < 0
    if sh.sum() < 10: return zk
    if KSVOL:
        thr = np.percentile(sg[sh], 100 - KSVOL)
        return np.where(sh & (sg >= thr), 0.0, zk)
    return np.where(sh, zk / sg * np.median(sg[sh]), zk)
'''
k = s.index("def legs(SLOW):"); s = s[:k] + helper.lstrip("\n") + s[k:]
# 4) legs(): king 腿的 z 经 kfix
a = '            z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0\n            g = np.abs(z).sum()\n            _yy = np.nan_to_num(y4[i, m], nan=0.0)'
assert s.count(a) == 1
b = '            z = np.nan_to_num(xz(sc[leg]))\n            if leg == "king": z = kfix(z, i, m)   # KC: king 空头凸性修正(席位用腿收益同口径)\n            z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0\n            g = np.abs(z).sum()\n            _yy = np.nan_to_num(y4[i, m], nan=0.0)'
s = s.replace(a, b)
# 5) run(): kc 链的 king 项
a2 = 'z = w3[0]*np.nan_to_num(xz(sc["king"])) + w3[1]*np.nan_to_num(xz(sc["rev24"])) + w3[2]*_fs*np.nan_to_num(xz(sc["fund"]))'
assert s.count(a2) == 1
b2 = 'z = w3[0]*kfix(np.nan_to_num(xz(sc["king"])), i, m) + w3[1]*np.nan_to_num(xz(sc["rev24"])) + w3[2]*_fs*np.nan_to_num(xz(sc["fund"]))   # KC: king 项经 kfix(关时恒等)'
s = s.replace(a2, b2)
open(p, "w").write(s); print("patched", p)
