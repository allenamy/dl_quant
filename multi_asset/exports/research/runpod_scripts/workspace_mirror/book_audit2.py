"""★★ 书级组合审计 v2 —— 修 v1 的锚集耦合错误。

v1 两个错都源于【把逐腿统计和相关矩阵放在同一个锚集上】:
  v1a: 换手在共同锚集上按"相邻行"算 => 那些行其实隔了几天, 换手被系统性高估
  v1b: 修成"只算行距==4的对"后 => 共同锚集里根本没有相邻对, 换手全 nan
★ 正解: 解耦。
  逐腿 IC/换手/夏普 -> 在【该腿自己的完整锚集】上算(通道腿=全部4h锚; DL腿=自己的 te_rows, 折内连续)
  相关矩阵          -> 只在共同锚集上算(横截面相关, 无时序假设, 本来就有效)
年化一律用真实 2190 锚/年。
"""
import numpy as np, glob, datetime as dt, itertools
d = np.load("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
MEM = d["MEMBER110"]; CH = d["CH"]; C = d["CL4"]; ts = d["ts"].astype(np.int64)
Yraw = d["Y4"]; nm = [str(v) for v in d["ch_names"]]
T, N = Yraw.shape
APY = 2190.0

def zr_row(v, m):
    o = np.full(N, np.nan)
    x = np.where(m, v, np.nan); f = np.isfinite(x)
    if f.sum() < 25: return o
    r = np.argsort(np.argsort(x[f])).astype(float)
    o[f] = (r - r.mean()) / (r.std() + 1e-12); return o

def wvec(v, i):
    m = MEM[i] & C[i] & np.isfinite(Yraw[i])
    if m.sum() < 25: return None
    z = zr_row(v, m)
    if np.isfinite(z).sum() < 25: return None
    z = np.nan_to_num(z - np.nanmean(z))
    g = np.abs(z).sum()
    return z / g if g > 0 else None

# 全部 4h 锚(通道腿用)
ALL = np.array([i for i in range(24, T - 8) if i % 4 == 0 and (MEM[i] & C[i] & np.isfinite(Yraw[i])).sum() >= 25])
print("全部 4h 锚 %d (%s ~ %s)" % (len(ALL),
      dt.datetime.fromtimestamp(int(ts[ALL[0]])/1000, dt.timezone.utc).date(),
      dt.datetime.fromtimestamp(int(ts[ALL[-1]])/1000, dt.timezone.utc).date()), flush=True)

def dl_scores(tag):
    out = {}
    for f in sorted(glob.glob(f"/workspace/exports_train/{tag}/fold_*_head_scores.npz")):
        z = np.load(f); te = z["te_rows"]; SC = z["scores"]
        for i in te: out[int(i)] = SC[int(i)].mean(1)
        del SC
    return out

CHANS = ["funding_ema", "rev_1h", "mom_24h", "mom_72h", "rvol_24h", "max_ret_24h", "size_dvol", "beta_24h"]
DLS = [t for t in ("rb32_lam0_yr4_s42", "rb32_lam0_yr8_s42", "rb32_lam0_yr12_s42", "rb32_lam0_s3037",
                   "volt_ref", "zoo56_yr24_s42", "f2t_lam0_s42", "roll8_yr4")
       if glob.glob(f"/workspace/exports_train/{t}/fold_*_head_scores.npz")]
LEGW = {}   # name -> {row: w}
for c in CHANS:
    k = nm.index(c); LEGW["ch:" + c] = {int(i): w for i in ALL if (w := wvec(CH[i, :, k], i)) is not None}
for t in DLS:
    sc = dl_scores(t); LEGW["dl:" + t] = {i: w for i in sc if (w := wvec(sc[i], i)) is not None}
print("腿 %d, 各自锚数: %s" % (len(LEGW), {k: len(v) for k, v in LEGW.items()}), flush=True)

def stats(WD, cost_bps):
    R = sorted(WD); ret, turn = [], []
    for j, i in enumerate(R):
        w = WD[i]; y = Yraw[i]
        ok = np.isfinite(y)
        ret.append(float(np.nansum(w[ok] * y[ok])))
        if j > 0 and (i - R[j-1]) == 4:
            turn.append(float(np.abs(w - WD[R[j-1]]).sum() / 2.0))
    ret = np.array(ret); tm = float(np.mean(turn)) if turn else float("nan")
    drag = (tm if tm == tm else 0.0) * cost_bps / 1e4
    sd = ret.std() + 1e-12
    return dict(n=len(ret), nt=len(turn), mu=ret.mean(), turn=tm,
                gross=ret.mean()/sd*np.sqrt(APY), net=(ret.mean()-drag)/sd*np.sqrt(APY))

print("\n%-24s %6s %7s %6s %10s %8s %8s %8s" % ("腿", "锚", "换手", "n换", "毛均值", "毛Sh", "净@3.63", "净@5.8"), flush=True)
ST = {}
for name, WD in LEGW.items():
    a = stats(WD, 3.63); b = stats(WD, 5.8); ST[name] = a
    print("%-24s %6d %7.4f %6d %10.2e %8.2f %8.2f %8.2f" % (
        name, a["n"], a["turn"], a["nt"], a["mu"], a["gross"], a["net"], b["net"]), flush=True)

names = list(LEGW)
common = sorted(set.intersection(*[set(v) for v in LEGW.values()]))
print("\n共同锚 %d (仅用于相关矩阵)" % len(common), flush=True)
Cm = np.eye(len(names))
for a, b in itertools.combinations(range(len(names)), 2):
    cs = []
    for i in common[::5]:
        x, y = LEGW[names[a]][i], LEGW[names[b]][i]
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() >= 25 and x[ok].std() > 0 and y[ok].std() > 0:
            cs.append(float(np.corrcoef(x[ok], y[ok])[0, 1]))
    Cm[a, b] = Cm[b, a] = float(np.mean(cs)) if cs else np.nan
np.savez("/workspace/data/book_audit2.npz", names=np.array(names), corr=Cm,
         turn=np.array([ST[n]["turn"] for n in names]),
         gross=np.array([ST[n]["gross"] for n in names]),
         net=np.array([ST[n]["net"] for n in names]),
         mu=np.array([ST[n]["mu"] for n in names]))
print("BOOK_AUDIT2_DONE", flush=True)
