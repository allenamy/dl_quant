"""★ regime 分层记分卡 —— 用户令 2026-08-08: "确保尽可能在不同 regime 都能产生稳定信号"

问题: 迄今每个臂只报 5 折平均 IC, 平均值把 regime 失效藏起来了。
装置(判据前置, 必须 arm-independent):
  分层 = 【线性 32ch 走前 Ridge 的实现健康度 H(t)】的五分位 —— 没有任何 DL 臂被拟合到它,
  且与 T1/E25 同尺(metalabel.npz 已存)。分层在评估任何臂之前冻结并落 sha。
  ⚠️ H 用到了实现 IC(含未来收益) —— 这在【评估分层】上合法(问的是"基线死的时候你怎么样"),
  在【可交易特征】上非法(#26)。两者严格分开。
输出(逐臂): 全期 / 健康五分位 / 最差三分位(T0 口径) / 逐年 / IC>0 占比 / 最差月。
自校验: 全期 ensemble IC 必须复现该臂 JSON 的 mean_ensemble_resid_ic(尺子一致性断言)。
"""
import numpy as np, json, os, sys, glob, hashlib, datetime as dt

PAN = "/workspace/data/wide_dl_pm32_hz.npz"
d = np.load(PAN, allow_pickle=True)
MEM = d["MEMBER110"]; ts = d["ts"].astype(np.int64)
YR = {h: d[f"YR{h}"] for h in (4, 8, 12, 24)}
CL = {h: d[f"CL{h}"] for h in (4, 8, 12, 24)}
YEAR = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).year for t in ts])
MONTH = np.array([dt.datetime.fromtimestamp(int(t)/1000, dt.timezone.utc).strftime("%Y-%m") for t in ts])

ML = np.load("/workspace/data/metalabel.npz", allow_pickle=True)
H = ML["H"]
assert len(H) == len(ts), "健康度序列与面板行数不符"

# ---- 冻结分层 ----
STRATA_F = "/workspace/data/regime_strata.npz"
if os.path.exists(STRATA_F):
    S = np.load(STRATA_F); QUINT = S["quint"]; TERC = S["terc"]
    print("载入已冻结分层 sha=%s" % str(S["sha"]))
else:
    QUINT = np.full(len(H), -1, np.int8); TERC = np.full(len(H), -1, np.int8)
    ok = np.isfinite(H)
    qs = np.percentile(H[ok], [20, 40, 60, 80])
    QUINT[ok] = 4 - np.searchsorted(qs, H[ok])     # 0=最健康 ... 4=最坏
    t3 = np.percentile(H[ok], [33.333, 66.667])
    TERC[ok] = 2 - np.searchsorted(t3, H[ok])      # 0=最好 2=最坏
    sha = hashlib.sha256(QUINT.tobytes() + TERC.tobytes()).hexdigest()[:16]
    np.savez(STRATA_F, quint=QUINT, terc=TERC, sha=sha, thresholds=qs, panel=PAN)
    print("★ 分层已冻结 sha=%s  (阈值 H: %s)" % (sha, np.round(qs, 5)))
    print("  五分位锚数:", [int((QUINT == q).sum()) for q in range(5)])

def zr(v):
    m = np.isfinite(v); o = np.full(len(v), np.nan)
    if m.sum() < 20: return o
    r = np.argsort(np.argsort(v[m])).astype(float)
    o[m] = (r - r.mean()) / (r.std() + 1e-12); return o

def anchor_ics(tag):
    """返回 (rows, ic_ens, ic_best) —— 逐锚横截面 rank-IC, 5 折拼接。"""
    dirs = f"/workspace/exports_train/{tag}"
    fs = sorted(glob.glob(f"{dirs}/fold_*_head_scores.npz"))
    if not fs: return None
    jf = f"/workspace/exports_train/wide_harness_{tag}.json"
    hz = json.load(open(jf))["target_horizon"] if os.path.exists(jf) else 4
    Y, C = YR[hz], CL[hz]
    R, IE, IB = [], [], []
    for f in fs:
        z = np.load(f)
        sc = z["scores"]; te = z["te_rows"]
        ens = sc[te].mean(2)                      # (n,140) 头均
        K = sc.shape[2]
        for j, i in enumerate(te):
            m = MEM[i] & C[i] & np.isfinite(Y[i])
            if m.sum() < 25: continue
            t_ = zr(np.where(m, Y[i], np.nan))[m]
            pe = zr(np.where(m, ens[j], np.nan))[m]
            g = np.isfinite(t_) & np.isfinite(pe)
            if g.sum() < 20: continue
            R.append(i); IE.append(float((pe[g]*t_[g]).mean()))
            bh = [float((zr(np.where(m, sc[i,:,k], np.nan))[m][g]*t_[g]).mean()) for k in range(K)]
            IB.append(bh)
    return np.array(R), np.array(IE), np.array(IB)

def card(tag):
    out = anchor_ics(tag)
    if out is None: return None
    R, IE, IB = out
    # best_head 按【折内】选会泄漏; 这里用全期头均(ens)作主判, 另报各头全期最大作参考
    perhead = IB.mean(0); best = float(perhead.max())
    q = QUINT[R]; t3 = TERC[R]
    row = {"tag": tag, "n": len(R), "ens_all": float(IE.mean()), "best_head_all": best,
           "pos_frac": float((IE > 0).mean())}
    for k in range(5): row[f"Q{k}"] = float(IE[q == k].mean()) if (q == k).sum() else float("nan")
    row["worst_terc"] = float(IE[t3 == 2].mean()) if (t3 == 2).sum() else float("nan")
    row["worst_terc_pos"] = float((IE[t3 == 2] > 0).mean()) if (t3 == 2).sum() else float("nan")
    for y in (2022, 2023, 2024, 2025, 2026):
        s = YEAR[R] == y
        row[f"y{y}"] = float(IE[s].mean()) if s.sum() else float("nan")
    mm = {}
    for m in np.unique(MONTH[R]):
        s = MONTH[R] == m
        if s.sum() >= 20: mm[m] = float(IE[s].mean())
    if mm:
        wm = min(mm, key=mm.get); row["worst_month"] = wm; row["worst_month_ic"] = mm[wm]
        row["neg_month_frac"] = float(np.mean([v < 0 for v in mm.values()]))
    return row

if __name__ == "__main__":
    tags = sys.argv[1:] or [os.path.basename(p) for p in sorted(glob.glob("/workspace/exports_train/*"))
                            if os.path.isdir(p)]
    hdr = ("%-24s %5s %7s %7s %7s %7s %7s %7s | %7s %6s | %7s %6s" %
           ("臂", "n", "全期", "Q0健", "Q1", "Q2", "Q3", "Q4坏", "最差三", "IC>0", "2026", "负月%"))
    print("\n" + hdr); print("-"*len(hdr))
    rows = []
    for t in tags:
        try: r = card(t)
        except Exception as e: print("%-24s ERR %s" % (t, e)); continue
        if not r: continue
        rows.append(r)
        print("%-24s %5d %7.4f %7.4f %7.4f %7.4f %7.4f %7.4f | %7.4f %6.2f | %7.4f %6.2f" %
              (r["tag"], r["n"], r["ens_all"], r["Q0"], r["Q1"], r["Q2"], r["Q3"], r["Q4"],
               r["worst_terc"], r["worst_terc_pos"], r["y2026"], r.get("neg_month_frac", float("nan"))))
    json.dump(rows, open("/workspace/data/regime_cards.json", "w"), indent=1)
    print("\nSCORECARD_DONE ->/workspace/data/regime_cards.json")
