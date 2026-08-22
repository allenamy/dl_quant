"""L0 阶段0 数据件: BTC Tardis 25 档 perp 书 + trades → 1-min 右端聚合(严格 ≤t).
列: spread_bps, ldepth5, obi5, near_asym(1-8), mid_asym(9-16), far_asym(17-25), micro_dev, tf_imb, l_tnot
幂等: 逐日 npy 缓存, 重跑跳过; 全部完成后组装 npz。
env: SRC(dl-tardis 根) OUT_DIR WORKERS
"""
import os, sys, glob, gzip
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd

SRC = os.environ.get("SRC", "/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis")
OUT = os.environ.get("OUT_DIR", "/mnt/storage/private/work_hsy/w3lane/s30/lob_btc")
os.makedirs(OUT + "/daily", exist_ok=True)
COLS = ["spread_bps", "ldepth5", "obi5", "near_asym", "mid_asym", "far_asym", "micro_dev", "tf_imb", "l_tnot"]

def one_day(day):
    out = f"{OUT}/daily/{day}.npy"
    if os.path.exists(out):
        return day, "cached"
    bf = f"{SRC}/book_snapshot_25/{day}/binance-futures/BTCUSDT.csv.gz"
    tf = f"{SRC}/trades/{day}/binance-futures/BTCUSDT.csv.gz"
    if not os.path.exists(bf):
        return day, "missing_book"
    try:
        b = pd.read_csv(bf)
        ts = b["timestamp"].values // 60_000_000  # μs → 分钟槽
        ap = b[[f"asks[{i}].price" for i in range(25)]].values
        aa = b[[f"asks[{i}].amount" for i in range(25)]].values
        bp = b[[f"bids[{i}].price" for i in range(25)]].values
        ba = b[[f"bids[{i}].amount" for i in range(25)]].values
        del b
        mid = (ap[:, 0] + bp[:, 0]) / 2
        an, bn = ap * aa, bp * ba  # 名义
        F = np.empty((len(ts), 9), np.float32)
        F[:, 0] = (ap[:, 0] - bp[:, 0]) / mid * 1e4
        F[:, 1] = np.log1p(an[:, :5].sum(1) + bn[:, :5].sum(1))
        F[:, 2] = (ba[:, :5].sum(1) - aa[:, :5].sum(1)) / (ba[:, :5].sum(1) + aa[:, :5].sum(1) + 1e-12)
        for j, (lo, hi) in enumerate(((0, 8), (8, 16), (16, 25))):
            bs, as_ = bn[:, lo:hi].sum(1), an[:, lo:hi].sum(1)
            F[:, 3 + j] = (bs - as_) / (bs + as_ + 1e-12)
        micro = (ap[:, 0] * ba[:, 0] + bp[:, 0] * aa[:, 0]) / (aa[:, 0] + ba[:, 0] + 1e-12)
        F[:, 6] = (micro - mid) / mid * 1e4
        # 分钟右端 = 槽内最后一帧
        last = np.r_[ts[1:] != ts[:-1], True]
        M = pd.DataFrame(F[last], index=ts[last], columns=COLS)
        # trades → 分钟 taker 流
        if os.path.exists(tf):
            t = pd.read_csv(tf, usecols=["timestamp", "side", "price", "amount"])
            t["m"] = t["timestamp"] // 60_000_000
            t["not"] = t["price"] * t["amount"]
            g = t.groupby(["m", "side"])["not"].sum().unstack(fill_value=0.0)
            buy = g.get("buy", pd.Series(0.0, index=g.index))
            sell = g.get("sell", pd.Series(0.0, index=g.index))
            M["tf_imb"] = ((buy - sell) / (buy + sell + 1e-9)).reindex(M.index).astype(np.float32)
            M["l_tnot"] = np.log1p((buy + sell).reindex(M.index)).astype(np.float32)
        else:
            M["tf_imb"] = np.nan; M["l_tnot"] = np.nan
        arr = np.column_stack([M.index.values.astype(np.int64), M.values.astype(np.float32)])
        np.save(out + ".tmp.npy", arr); os.replace(out + ".tmp.npy", out)
        return day, f"ok {len(M)}"
    except Exception as e:
        return day, f"ERR {type(e).__name__}: {str(e)[:80]}"

if __name__ == "__main__":
    days = sorted(os.listdir(f"{SRC}/book_snapshot_25"))
    print(f"days {len(days)} {days[0]}..{days[-1]}", flush=True)
    nerr = 0
    with ProcessPoolExecutor(max_workers=int(os.environ.get("WORKERS", "10"))) as ex:
        for i, (d, st) in enumerate(ex.map(one_day, days)):
            if st.startswith("ERR"): nerr += 1
            if st.startswith("ERR") or (i + 1) % 50 == 0:
                print(f"[{i+1}/{len(days)}] {d} {st}", flush=True)
    # 组装
    files = sorted(glob.glob(f"{OUT}/daily/*.npy"))
    big = np.concatenate([np.load(f) for f in files])
    np.savez_compressed(f"{OUT}/lob_btc_1min.tmp.npz", ts_min=big[:, 0].astype(np.int64),
                        feat=big[:, 1:].astype(np.float32), cols=np.array(COLS),
                        provenance=np.array([f"jp_lob_agg.py days={len(files)} err={nerr} src={SRC}"]))
    os.replace(f"{OUT}/lob_btc_1min.tmp.npz", f"{OUT}/lob_btc_1min.npz")
    print(f"LOB_AGG_DONE rows {len(big)} days {len(files)} err {nerr}", flush=True)
