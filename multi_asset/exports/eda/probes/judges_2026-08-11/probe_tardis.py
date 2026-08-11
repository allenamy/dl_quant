import time, gzip, numpy as np, pandas as pd
D = "/mnt/storage/btcusdt_copy_2023-01-01_2026-05-31/dl-tardis"
day = "2024-03-15"
bookf = f"{D}/book_snapshot_25/{day}/binance-futures/BTCUSDT.csv.gz"
tradef = f"{D}/trades/{day}/binance-futures/BTCUSDT.csv.gz"

t0 = time.time()
bk = pd.read_csv(bookf, usecols=["timestamp", "asks[0].price", "asks[0].amount", "bids[0].price", "bids[0].amount"])
print(f"book parse {time.time()-t0:.1f}s rows={len(bk)} ({len(bk)/86400:.1f}/s)")
t0 = time.time()
tr = pd.read_csv(tradef, usecols=["timestamp", "side", "price", "amount"])
print(f"trades parse {time.time()-t0:.1f}s rows={len(tr)} ({len(tr)/86400:.1f}/s)")

bts = bk["timestamp"].to_numpy()  # us
print("book ts span", (bts[-1]-bts[0])/1e6/3600, "h; median dt(ms)", np.median(np.diff(bts))/1e3)
mid = (bk["asks[0].price"].to_numpy() + bk["bids[0].price"].to_numpy()) / 2
spr = (bk["asks[0].price"].to_numpy() - bk["bids[0].price"].to_numpy()) / mid * 1e4
print("median spread bps", np.median(spr), "median bid amt", np.median(bk["bids[0].amount"]))
# trade notional/hour
notl = (tr["price"] * tr["amount"]).sum() / ((tr["timestamp"].iloc[-1]-tr["timestamp"].iloc[0])/1e6/3600)
print("hourly notional $M", notl/1e6)
sells = tr[tr["side"] == "sell"]
print("sell trades", len(sells), "sample px", sells["price"].iloc[:3].tolist())
