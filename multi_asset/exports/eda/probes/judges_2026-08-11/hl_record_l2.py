"""Hyperliquid L2 order-book recorder — one snapshot per coin per minute, via websocket.

WHY: maker-fill feasibility (queue position + adverse selection) is the single largest unknown in
the HL deployment case, and it CANNOT be answered from a point-in-time snapshot -- it needs a
time series of books. This data does not exist anywhere retroactively, so recording has to start
before it can ever be analysed.

Design: subscribe to l2Book for the top-N coins by 24h notional, keep the latest book per coin in
memory, and flush a snapshot of all coins once per minute to a per-day file. Websocket (not REST
polling) because polling 60 coins x 1440 min/day would consume the entire /info rate budget.

Storage: exports/hl_archive/l2/<YYYYMMDD>.npz, appended each flush
    ts    (M,)        snapshot epoch ms
    coin  (M,)        coin index into `coins`
    bid/ask (M,L,2)   float32 [price, size] for the top L levels of each side

READ-ONLY public websocket. No trading/auth subscriptions.

Usage (cron, restarts hourly under flock -- if it dies it is back within the hour):
    python engine/hl_archive/record_l2.py --minutes 1440 --top 60
"""
import argparse, json, os, threading, time
import urllib.request
import numpy as np
import websocket                                   # websocket-client 1.8.0

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
ARC = MA + "/exports/hl_archive/l2"
INFO = "https://api.hyperliquid.xyz/info"
WS = "wss://api.hyperliquid.xyz/ws"
UA = "Mozilla/5.0 (research archive; read-only public market data)"
LEVELS = 10


class Recorder:
    def __init__(self, coins, levels=LEVELS):
        self.coins = coins
        self.idx = {c: i for i, c in enumerate(coins)}
        self.levels = levels
        self.latest = {}
        self.lock = threading.Lock()
        self.n_msg = 0
        self.ws = None
        self.stop = False

    def on_message(self, _ws, msg):
        try:
            d = json.loads(msg)
        except Exception:
            return
        if d.get("channel") != "l2Book":
            return
        data = d.get("data") or {}
        c = data.get("coin")
        if c is None or c not in self.idx:
            return
        lv = data.get("levels") or [[], []]
        with self.lock:
            self.latest[c] = (int(data.get("time", time.time() * 1000)), lv[0], lv[1])
            self.n_msg += 1

    def on_error(self, _ws, err):
        print(f"[l2rec] ws error: {type(err).__name__}: {str(err)[:120]}", flush=True)

    def on_close(self, _ws, code, msg):
        print(f"[l2rec] ws closed code={code} msg={msg}", flush=True)

    def on_open(self, ws):
        for c in self.coins:
            ws.send(json.dumps({"method": "subscribe",
                                "subscription": {"type": "l2Book", "coin": c}}))
            time.sleep(0.02)
        print(f"[l2rec] subscribed to {len(self.coins)} books", flush=True)

    def run_ws(self):
        while not self.stop:
            try:
                self.ws = websocket.WebSocketApp(
                    WS, on_open=self.on_open, on_message=self.on_message,
                    on_error=self.on_error, on_close=self.on_close)
                self.ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                print(f"[l2rec] run_forever crashed: {type(e).__name__}", flush=True)
            if not self.stop:
                time.sleep(5)                       # reconnect loop

    def snapshot(self):
        L = self.levels
        with self.lock:
            items = list(self.latest.items())
        if not items:
            return None
        ts = np.empty(len(items), np.int64)
        cn = np.empty(len(items), dtype=object)          # coin NAME per row, not an index
        bid = np.zeros((len(items), L, 2), np.float32)
        ask = np.zeros((len(items), L, 2), np.float32)
        for k, (c, (t, b, a)) in enumerate(items):
            ts[k] = t; cn[k] = c
            for s, side in ((bid, b), (ask, a)):
                for j, lv in enumerate(side[:L]):
                    s[k, j, 0] = float(lv["px"]); s[k, j, 1] = float(lv["sz"])
        return ts, cn, bid, ask


def append_day(path, coins, snap):
    """Rows carry the coin NAME, deliberately: the recorder's subscribed set can change between
    restarts (top-N is re-ranked each launch), so an index into a per-file coin list would silently
    re-point previously written rows at the wrong coin."""
    ts, cn, bid, ask = snap
    if os.path.exists(path):
        z = np.load(path, allow_pickle=True)
        ts = np.concatenate([z["ts"], ts]); cn = np.concatenate([z["coin"], cn])
        bid = np.concatenate([z["bid"], bid]); ask = np.concatenate([z["ask"], ask])
    np.savez_compressed(path, ts=ts, coin=cn.astype(object), bid=bid, ask=ask,
                        coins=np.array(sorted(set(map(str, cn))), dtype=object))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=int, default=1440)
    ap.add_argument("--top", type=int, default=60)
    ap.add_argument("--levels", type=int, default=LEVELS)
    a = ap.parse_args()
    os.makedirs(ARC, exist_ok=True)

    req = urllib.request.Request(INFO, data=json.dumps({"type": "metaAndAssetCtxs"}).encode(),
                                 method="POST",
                                 headers={"User-Agent": UA, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        mc = json.loads(r.read())
    rows = [(u["name"], float(c.get("dayNtlVlm") or 0))
            for u, c in zip(mc[0]["universe"], mc[1]) if not u.get("isDelisted", False)]
    rows.sort(key=lambda x: -x[1])
    coins = [c for c, _ in rows[:a.top]]
    print(f"[l2rec] recording top-{len(coins)} by 24h notional, {a.levels} levels, "
          f"{a.minutes} min", flush=True)

    rec = Recorder(coins, a.levels)
    th = threading.Thread(target=rec.run_ws, daemon=True)
    th.start()
    time.sleep(8)                                   # let the subscriptions fill

    # Buffer in memory and rewrite the day file every FLUSH_EVERY minutes. Rewriting a growing npz
    # once per minute would be ~20 GB of I/O per day for no benefit; a day of buffer is ~14 MB.
    # 10 min is the durability/IO trade-off: a crash loses at most 10 minutes of books (cron
    # relaunches within 30), at ~1 GB/day of rewrite I/O, which is cheap. This data cannot be
    # recovered retroactively, so bounding the loss window matters more than the I/O.
    FLUSH_EVERY = 10
    t_end = time.time() + a.minutes * 60
    n_snap = 0
    buf, buf_day = [], time.strftime("%Y%m%d", time.gmtime())

    def flush():
        nonlocal buf
        if not buf:
            return
        try:
            append_day(f"{ARC}/{buf_day}.npz", coins,
                       tuple(np.concatenate([b[k] for b in buf]) for k in range(4)))
            buf = []
        except Exception as e:
            print(f"[l2rec] flush failed: {type(e).__name__}: {str(e)[:120]}", flush=True)

    while time.time() < t_end:
        time.sleep(max(0.0, 60 - (time.time() % 60)))
        snap = rec.snapshot()
        if snap is None:
            print("[l2rec] no books yet", flush=True)
            continue
        day = time.strftime("%Y%m%d", time.gmtime())
        if day != buf_day:                          # UTC day rollover: close the old file first
            flush()
            buf_day = day
        buf.append(snap)
        n_snap += 1
        if n_snap % FLUSH_EVERY == 0:
            flush()
            print(f"[l2rec] {n_snap} snapshots, {len(snap[0])} coins live, "
                  f"{rec.n_msg} ws msgs", flush=True)
    flush()
    rec.stop = True
    if rec.ws:
        rec.ws.close()
    print(f"[l2rec] done: {n_snap} snapshots", flush=True)


if __name__ == "__main__":
    main()
