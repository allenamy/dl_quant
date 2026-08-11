"""#48 书状态特征构建 — PREREG_bookstate_pregate_2026-08-05.md 的 §1, 逐字实现。

只算预注册的 7 个特征; add/del 族按预注册【排除】(实盘 snapshot 流不可复现)。
share bar_data 只读(bar_loader 自身 mode='r')。输出 minute 级原料 + panel 对齐特征。
"""
import sys, os, json, time
import numpy as np

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA)
sys.path.insert(0, os.path.dirname(MA))
from multi_asset.data import bar_loader as BL

PANEL = os.path.join(MA, "exports/wide_dl_full_corrfund_causal_0731.npz")
OUT = os.path.join(MA, "exports/eda/bookstate14_features.npz")
MARK = "/tmp/bookstate14.DONE"

SYM_MAP = {"BTCUSDT": "bnfbtc", "ETHUSDT": "bnfeth", "SOLUSDT": "bnfsol", "BNBUSDT": "bnfbnb",
           "XRPUSDT": "bnfxrp", "DOGEUSDT": "bnfdog", "ADAUSDT": "bnfada", "LINKUSDT": "bnflink",
           "BCHUSDT": "bnfbch", "TRXUSDT": "bnftrx", "LTCUSDT": "bnfltc", "DOTUSDT": "bnfdot",
           "FILUSDT": "bnffil", "ETCUSDT": "bnfetc"}
PSY = sorted(SYM_MAP)                       # 14 panel symbols, fixed order
C = BL.FEATURE_COLUMNS
ix = {c: i for i, c in enumerate(C)}
BID_SZ = [ix[c] for c in ("bidsz", "bidsz_1", "bidsz_2", "bidsz_3", "bidsz_4")]
ASK_SZ = [ix[c] for c in ("asksz", "asksz_1", "asksz_2", "asksz_3", "asksz_4")]
BID_PX = [ix[c] for c in ("bid", "bid_1", "bid_2", "bid_3", "bid_4")]
ASK_PX = [ix[c] for c in ("ask", "ask_1", "ask_2", "ask_3", "ask_4")]
CB_N = [ix[f"cumu_bidsz_dep_{b}"] for b in ("0.1", "0.3", "1.0")]
CA_N = [ix[f"cumu_asksz_dep_{b}"] for b in ("0.1", "0.3", "1.0")]
CB_F = [ix[f"cumu_bidsz_dep_{b}"] for b in ("100.0", "300.0", "1000.0")]
CA_F = [ix[f"cumu_asksz_dep_{b}"] for b in ("100.0", "300.0", "1000.0")]
MID, BID0, ASK0 = ix["mid"], ix["bid"], ix["ask"]
TQB, TQS = ix["tdQtyBuy"], ix["tdQtySell"]
NRAW = 8      # 7 特征的分子/分母原料: obi5, nearA, farA, spread, ldepth, tfb, tfs, microdev

def day_minutes(date, syms_int):
    """(1430, 14, NRAW) minute aggregates for one day; NaN where absent."""
    out = np.full((1430, len(PSY), NRAW), np.nan, np.float32)
    try:
        pan = BL.load_day_panel(date, syms_int)
    except Exception:
        return out, 0
    n_ok = 0
    for j, ps in enumerate(PSY):
        s = SYM_MAP[ps]
        if s not in pan.data:
            continue
        a = np.asarray(pan.data[s], np.float32)
        if a.shape[0] < 85800:
            pad = np.full((85800 - a.shape[0], a.shape[1]), np.nan, np.float32)
            a = np.vstack([a, pad])
        a = a[:85800].reshape(1430, 60, -1)
        with np.errstate(all="ignore"):
            bs = np.nansum(a[:, :, BID_SZ], axis=2)
            as_ = np.nansum(a[:, :, ASK_SZ], axis=2)
            obi = np.nanmean((bs - as_) / np.where(bs + as_ > 0, bs + as_, np.nan), axis=1)
            cbn = np.nansum(a[:, :, CB_N], axis=2); can = np.nansum(a[:, :, CA_N], axis=2)
            nearA = np.nanmean((cbn - can) / np.where(cbn + can > 0, cbn + can, np.nan), axis=1)
            cbf = np.nansum(a[:, :, CB_F], axis=2); caf = np.nansum(a[:, :, CA_F], axis=2)
            farA = np.nanmean((cbf - caf) / np.where(cbf + caf > 0, cbf + caf, np.nan), axis=1)
            mid = a[:, :, MID]; bid = a[:, :, BID0]; ask = a[:, :, ASK0]
            spr = np.nanmean((ask - bid) / np.where(mid > 0, mid, np.nan), axis=1)
            ntl = (np.nansum(a[:, :, BID_SZ] * a[:, :, BID_PX], axis=2)
                   + np.nansum(a[:, :, ASK_SZ] * a[:, :, ASK_PX], axis=2))
            ldep = np.nanmean(np.log(np.where(ntl > 0, ntl, np.nan)), axis=1)
            tfb = np.nansum(a[:, :, TQB] * mid, axis=1)      # 名义化, 可比
            tfs = np.nansum(a[:, :, TQS] * mid, axis=1)
            bsz0 = a[:, :, ix["bidsz"]]; asz0 = a[:, :, ix["asksz"]]
            micro = (bid * asz0 + ask * bsz0) / np.where(bsz0 + asz0 > 0, bsz0 + asz0, np.nan)
            mdev = np.nanmean((micro - mid) / np.where(mid > 0, mid, np.nan), axis=1)
        out[:, j, 0] = obi; out[:, j, 1] = nearA; out[:, j, 2] = farA; out[:, j, 3] = spr
        out[:, j, 4] = ldep; out[:, j, 5] = tfb; out[:, j, 6] = tfs; out[:, j, 7] = mdev
        n_ok += 1
    return out, n_ok


def main():
    z = np.load(PANEL, allow_pickle=True)
    pts = z["ts"].astype(np.int64)
    # 单位探测: 面板 ts 为 ms(实测 1.78e12 量级); 内部一律用秒, 输出保留原 ts 供 panel 对齐
    pts_s = pts // 1000 if int(pts[0]) > 10**11 else pts
    psyms = [str(x) for x in z["symbols"]]
    keep = [psyms.index(s) for s in PSY if s in psyms]
    assert len(keep) == 14, f"panel 缺 14 大币之一: {[s for s in PSY if s not in psyms]}"
    # bar_data 覆盖: 2022-01-01 .. 2025-11-30 (README); 取 panel span 的交集
    import datetime as dt
    d0 = dt.datetime.utcfromtimestamp(int(pts_s[0])).date()
    d0 = max(d0, dt.date(2022, 1, 1))
    d1 = min(dt.datetime.utcfromtimestamp(int(pts_s[-1])).date(), dt.date(2025, 11, 30))
    days = []
    d = d0
    while d <= d1:
        days.append(int(d.strftime("%Y%m%d")))
        d += dt.timedelta(days=1)
    syms_int = [SYM_MAP[s] for s in PSY]
    M = np.full((len(days) * 1430, 14, NRAW), np.nan, np.float32)
    mts = np.zeros(len(days) * 1430, np.int64)
    t0 = time.time()
    n_ok_days = 0
    for di, date in enumerate(days):
        day_ep = int(dt.datetime.strptime(str(date), "%Y%m%d")
                     .replace(tzinfo=dt.timezone.utc).timestamp())
        mts[di * 1430:(di + 1) * 1430] = day_ep + np.arange(1430) * 60 + 60   # 分钟【右端】ts
        blk, n_ok = day_minutes(date, syms_int)
        M[di * 1430:(di + 1) * 1430] = blk
        n_ok_days += (n_ok > 0)
        if di % 50 == 0:
            el = time.time() - t0
            print(f"  {di}/{len(days)} days ({el:.0f}s, ok={n_ok_days})", flush=True)
    # panel 对齐: 拖尾 1h(60 分钟), 分钟右端 ≤ panel ts —— 严格因果
    F = np.full((len(pts), 14, 7), np.nan, np.float32)
    idx = np.searchsorted(mts, pts_s, side="right")        # 第一个 > ts 的位置(秒口径)
    for ti, e in enumerate(idx):
        s = e - 60
        # ★★ 2026-08-06 缺陷修复: 当面板 ts 超出分钟网格右端时 searchsorted 恒返回 len(mts),
        # 于是【其后每一个锚都拿到同一个常向量】—— 实测 2025-12 / 2026-02 / 2026-05 逐位相同。
        # 这不是前视(是陈旧), 但它违反本轨预注册 v2 §6-① 亲自写下的"NaN 不得当 0 混入", 且它的
        # 症状是【覆盖率 1.000】—— 一个坏仪器的读数恰好长得像好消息。缺数据就是缺, 必须留 NaN。
        if s < 0 or e <= 0 or pts_s[ti] > mts[-1]:
            continue
        w = M[max(s, 0):e]                                  # (≤60, 14, NRAW)
        if not np.isfinite(w).any():
            continue
        with np.errstate(all="ignore"):
            mean = np.nanmean(w, axis=0)                    # (14, NRAW)
            tfb, tfs = np.nansum(w[:, :, 5], axis=0), np.nansum(w[:, :, 6], axis=0)
            tfimb = (tfb - tfs) / np.where(tfb + tfs > 0, tfb + tfs, np.nan)
        F[ti, :, 0] = mean[:, 0]; F[ti, :, 1] = mean[:, 1]; F[ti, :, 2] = mean[:, 2]
        F[ti, :, 3] = mean[:, 3]; F[ti, :, 4] = mean[:, 4]; F[ti, :, 5] = tfimb
        F[ti, :, 6] = mean[:, 7]
    # 14 币内 xsec-z(逐行逐特征)
    with np.errstate(all="ignore"):
        mu = np.nanmean(F, axis=1, keepdims=True)
        sd = np.nanstd(F, axis=1, keepdims=True)
        Fz = (F - mu) / np.where(sd > 1e-12, sd, np.nan)
    names = ["obi5", "cumdep_near_asym", "cumdep_far_asym", "spread_bps",
             "ldepth", "tfimb", "micro_dev"]
    np.savez_compressed(OUT, ts=pts, symbols=np.array(PSY, dtype=object),
                        F_raw=F, F_z=Fz, feat_names=np.array(names, dtype=object),
                        prereg="PREREG_bookstate_pregate_2026-08-05.md")
    fin = float(np.isfinite(Fz).mean())
    print(f"saved -> {OUT}  T={len(pts)} finite={fin:.3f} days_ok={n_ok_days}/{len(days)}", flush=True)
    open(MARK, "w").write(json.dumps({"finite": fin, "days_ok": n_ok_days, "n_days": len(days)}))


if __name__ == "__main__":
    main()
