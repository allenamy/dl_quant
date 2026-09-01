"""f10v2_legs 延伸 @pod(2026-09-01, V2MAIN 重训输入): 旧行逐字保留 + 新锚同公式拼接。
政策(MANIFEST 记档): 历史行 = 实盘经历过的旧值原样(不重写历史); 新锚 = 同构造 + v3 pinned king PRED。
构造(= pod_export_shadow_bundle.py §② 同族, meta 自述 "rank-z legs + C3r msharpe WL on dlw grid"):
  Z24[i] = xz(−f_rev_24h[j, members]) 散射; ZFD[i] = xz(f_fund_ema_v1[j, members]) 散射;
  WL[i] = trailing-900 msharpe(king/rev24/fund 三腿 L1 归一 z·y4 收益), <900 锚 = 1/3。
自验证(公式收据): 在重叠段末尾 120 锚重算 Z24/ZFD 对旧值 exact≥0.999 断言(与 PRED 无关, 必须逐位);
  WL 重算 vs 旧 WL 报 corr(依赖 king PRED 代际, 允许偏差, 只记录不 gate)。
用法: python3 pod_legs_ext.py
"""
import json, time
import numpy as np
from scipy.stats import rankdata

OLD = np.load("/workspace/data/f10v2_legs.npz", allow_pickle=True)
TG = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True)
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
PRED = np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy")

E_ts = TG["E_ts"].astype(np.int64); members = TG["members"]; y4s = TG["y4s"]
nA = len(E_ts); NW = y4s.shape[1]
old_ts = OLD["E_ts"].astype(np.int64)
old_row = {int(t): i for i, t in enumerate(old_ts)}
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
fe_row = {int(t): i for i, t in enumerate(MT["E_ts"].astype(np.int64))}
R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]

def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out

def build_row(i):
    j = pw_row.get(int(E_ts[i]))
    m = members[i]
    z24 = np.full(NW, np.nan, np.float32); zfd = np.full(NW, np.nan, np.float32)
    if j is not None:
        z24[m] = xz(-R24[j, m]).astype(np.float32)
        zfd[m] = xz(FE[j, m]).astype(np.float32)
    return z24, zfd

# ---- 腿收益全序列(WL 用; king 分数 = v3 pinned PRED 按 ts 对齐) ----
def leg_ret(i):
    j = pw_row.get(int(E_ts[i])); fi = fe_row.get(int(E_ts[i]))
    m = members[i]
    if j is None: return None
    kp = PRED[fi, m] if fi is not None else np.full(len(m), np.nan)
    sc = {"king": kp, "rev24": -R24[j, m], "fund": FE[j, m]}
    ok = np.isfinite(y4s[i, m])
    out = []
    for leg in ("king", "rev24", "fund"):
        z = np.nan_to_num(xz(sc[leg]))
        z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0
        g = np.abs(z).sum()
        out.append(float((z / g * np.nan_to_num(y4s[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
    return out

LRs = []; lr_idx = []
for i in range(nA):
    r = leg_ret(i)
    if r is not None: LRs.append(r); lr_idx.append(i)
LRs = np.array(LRs); pos = {int(i): p for p, i in enumerate(lr_idx)}

def msharpe_w(i):
    p = pos.get(int(i), 0)
    if p < 900: return np.array([1/3, 1/3, 1/3])
    r = LRs[p-900:p].T
    shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
    return shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3)

Z24o = np.full((nA, NW), np.nan, np.float32); ZFDo = np.full((nA, NW), np.nan, np.float32)
WLo = np.full((nA, 3), 1/3, np.float32)
n_copy = n_new = 0
for i in range(nA):
    oi = old_row.get(int(E_ts[i]))
    if oi is not None:
        Z24o[i] = OLD["Z24"][oi]; ZFDo[i] = OLD["ZFD"][oi]; WLo[i] = OLD["WL"][oi]; n_copy += 1
    else:
        z24, zfd = build_row(i)
        Z24o[i] = z24; ZFDo[i] = zfd; WLo[i] = msharpe_w(i).astype(np.float32); n_new += 1

# ---- 自验证: 重叠段末 120 锚公式重算 vs 旧值 ----
chk = [i for i in range(nA) if int(E_ts[i]) in old_row][-120:]
ex24 = []; exfd = []; wl_d = []
for i in chk:
    z24, zfd = build_row(i)
    o24 = Z24o[i]; ofd = ZFDo[i]
    for new, old, acc in ((z24, o24, ex24), (zfd, ofd, exfd)):
        ok = np.isfinite(new) & np.isfinite(old)
        acc.append(float(np.mean(np.abs(new[ok] - old[ok]) < 1e-6)) if ok.sum() else np.nan)
    wl_d.append(float(np.abs(msharpe_w(i) - WLo[i]).max()))
e24 = float(np.nanmean(ex24)); efd = float(np.nanmean(exfd)); wmax = float(np.max(wl_d))
print(f"selfcheck Z24 exact {e24:.4f} ZFD exact {efd:.4f} WL max|Δ| {wmax:.4f} (WL 允差: PRED 代际)", flush=True)
assert e24 >= 0.999 and efd >= 0.999, "legs 公式自验证 FAIL"

meta = {"note": "splice: old rows verbatim + new rows same formula with v3 pinned PRED",
        "n_copy": n_copy, "n_new": n_new, "selfcheck": {"z24_exact": e24, "zfd_exact": efd, "wl_maxdiff": wmax},
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
import os
os.makedirs("/workspace/f8_ext/data", exist_ok=True)
np.savez("/workspace/f8_ext/data/f10v2_legs.npz", Z24=Z24o, ZFD=ZFDo, WL=WLo, E_ts=E_ts, meta_json=json.dumps(meta))
print(f"LEGS_EXT_DONE copy {n_copy} new {n_new}", flush=True)
