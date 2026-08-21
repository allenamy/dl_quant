"""★★ 书级组合审计仪器 (2026-08-09, 用户转向书级) —— 不用代理, 直接算多空组合的毛/净/换手。

为什么必须换仪器: 今天全天问的是"X 能否打败冠军"(增量门), 而书的问题是"X 能否补充组合"。
一个 IC=0.02 但【与现有书不相关且换手极低】的因子, 在成本受限的书里可以净正贡献,
却会被增量门判负。⇒ 需要一台按【净夏普】而非【增量 IC】说话的仪器。

装置(真实构造, 非代理):
  w_i(t) = 横截面 z-rank 分数, 归一到 Σ|w|=1 (gross 1, 市场中性)
  ret_t  = Σ w_i · y_i          (raw 4h 收益 —— 书兑现的就是它)
  turn_t = Σ|w(t) − w(t−1)|/2   (单边换手占 gross 的比例)
  net_t  = ret_t − turn_t · cost_bps/1e4
  Sharpe = mean/std × √(锚/年)
成本用实测 3.63bps(CI 1.5-5.8), 三档都报。
输出: 逐腿 IC / 换手 / 毛夏普 / 净夏普 + 腿间相关矩阵 ⇒ 为组合优化提供全部输入。
"""
import numpy as np, glob, json, datetime as dt, itertools
d = np.load("/workspace/data/wide_dl_pm32_hz.npz", allow_pickle=True)
MEM = d["MEMBER110"]; CH = d["CH"]; C = d["CL4"]; ts = d["ts"].astype(np.int64)
Yraw = d["Y4"]; YR = d["YR4"]
nm = [str(v) for v in d["ch_names"]]
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in ts])
T, N = Yraw.shape

def zr_row(v, m):
    o = np.full(N, np.nan)
    x = np.where(m, v, np.nan); f = np.isfinite(x)
    if f.sum() < 25: return o
    r = np.argsort(np.argsort(x[f])).astype(float)
    o[f] = (r - r.mean()) / (r.std() + 1e-12); return o

# ---------- 候选腿 ----------
LEGS = {}
for c in ("funding_ema", "rev_1h", "mom_24h", "mom_72h", "rvol_24h", "max_ret_24h", "size_dvol", "beta_24h"):
    LEGS["ch:" + c] = ("chan", nm.index(c))
for tag in ("rb32_lam0_yr4_s42", "rb32_lam0_yr8_s42", "rb32_lam0_yr12_s42", "rb32_lam0_s3037",
            "volt_ref", "zoo56_yr24_s42", "f2t_lam0_s42", "roll8_yr4"):
    if glob.glob(f"/workspace/exports_train/{tag}/fold_*_head_scores.npz"):
        LEGS["dl:" + tag] = ("dl", tag)
print("候选腿 %d: %s" % (len(LEGS), list(LEGS)), flush=True)

def dl_scores(tag):
    out = {}
    for f in sorted(glob.glob(f"/workspace/exports_train/{tag}/fold_*_head_scores.npz")):
        z = np.load(f); te = z["te_rows"]; SC = z["scores"]
        for i in te: out[int(i)] = SC[int(i)].mean(1)      # 头均
        del SC
    return out

RAW = {}
for name, (kind, ref) in LEGS.items():
    RAW[name] = dl_scores(ref) if kind == "dl" else None
rows_all = None
for name, (kind, ref) in LEGS.items():
    if kind == "dl":
        s = set(RAW[name]); rows_all = s if rows_all is None else (rows_all & s)
rows = np.array(sorted(rows_all))
print("共同锚 %d  (%s ~ %s)" % (len(rows),
      dt.datetime.fromtimestamp(int(ts[rows[0]])/1000, dt.timezone.utc).date(),
      dt.datetime.fromtimestamp(int(ts[rows[-1]])/1000, dt.timezone.utc).date()), flush=True)

# ---------- 逐腿权重矩阵 ----------
W = {}
for name, (kind, ref) in LEGS.items():
    A = np.full((len(rows), N), np.nan)
    for j, i in enumerate(rows):
        m = MEM[i] & C[i] & np.isfinite(Yraw[i])
        v = CH[i, :, ref] if kind == "chan" else RAW[name][i]
        z = zr_row(v, m)
        if np.isfinite(z).sum() >= 25:
            z = z - np.nanmean(z)
            g = np.nansum(np.abs(z))
            if g > 0: A[j] = z / g
    W[name] = A
print("权重矩阵已建", flush=True)

ANCHORS_PER_YEAR = 2190.0   # 4h 锚的【真实】交易频率; 不可用共同锚子集的密度代替

def stats(A, cost_bps):
    """2026-08-09 修两处口径:
    (1) 年化基数用真实 2190/年, 而非共同锚子集密度(原实现低估夏普 sqrt(2190/366)=2.45x);
    (2) 换手【只在真正相邻的锚(行距==4)上测】—— 跨了几天的两个共同锚之间的漂移不是一次调仓。
    """
    ret, turn = [], []
    for j in range(len(rows)):
        w = A[j]
        if not np.isfinite(w).any():
            continue
        y = Yraw[rows[j]]
        ok = np.isfinite(w) & np.isfinite(y)
        if ok.sum() < 25:
            continue
        ret.append(float(np.nansum(w[ok] * y[ok])))
        if j > 0 and (rows[j] - rows[j - 1]) == 4 and np.isfinite(A[j - 1]).any():
            turn.append(float(np.nansum(np.abs(np.nan_to_num(w) - np.nan_to_num(A[j - 1]))) / 2.0))
    ret = np.array(ret)
    tm = float(np.mean(turn)) if turn else float("nan")
    drag = (tm if tm == tm else 0.0) * cost_bps / 1e4
    f = lambda mu, sd: mu / (sd + 1e-12) * np.sqrt(ANCHORS_PER_YEAR)
    return dict(n=len(ret), n_turn=len(turn), ret=ret.mean(), turn=tm,
                gross=f(ret.mean(), ret.std()), net=f(ret.mean() - drag, ret.std()))

print("\n%-26s %7s %6s %8s %8s %8s %8s" % ("腿", "换手", "n换", "毛均值", "毛Sharpe", "净@3.63", "净@5.8"), flush=True)
S = {}
for name, A in W.items():
    a = stats(A, 3.63); b = stats(A, 5.8)
    S[name] = a
    print("%-26s %7.4f %6d %8.2e %8.2f %8.2f %8.2f" % (name, a["turn"], a["n_turn"], a["ret"], a["gross"], a["net"], b["net"]), flush=True)

# ---------- 腿间相关(逐锚权重向量的相关, 再平均) ----------
names = list(W)
print("\n腿间相关(权重向量逐锚相关的均值):", flush=True)
Cm = np.eye(len(names))
for a, b in itertools.combinations(range(len(names)), 2):
    cs = []
    for j in range(0, len(rows), 7):
        x, y = W[names[a]][j], W[names[b]][j]
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() >= 25 and x[ok].std() > 0 and y[ok].std() > 0:
            cs.append(float(np.corrcoef(x[ok], y[ok])[0, 1]))
    Cm[a, b] = Cm[b, a] = float(np.mean(cs)) if cs else np.nan
hdr = "".join("%7s" % n.split(":")[-1][:6] for n in names)
print("%-26s%s" % ("", hdr), flush=True)
for i, n in enumerate(names):
    print("%-26s%s" % (n, "".join("%7.2f" % Cm[i, k] for k in range(len(names)))), flush=True)
np.savez("/workspace/data/book_audit.npz", names=np.array(names), corr=Cm,
         turn=np.array([S[n]["turn"] for n in names]), gross=np.array([S[n]["gross"] for n in names]),
         net=np.array([S[n]["net"] for n in names]), rows=rows)
print("\nBOOK_AUDIT_DONE -> /workspace/data/book_audit.npz", flush=True)
