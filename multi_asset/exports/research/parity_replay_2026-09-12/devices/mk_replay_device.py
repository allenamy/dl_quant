#!/usr/bin/env python3
"""Generate shadow_loop_v3_replay.py from the PRODUCTION file by exact, once-only string replacements
(PREREG_producer_parity_replay_2026-09-12 §1). Nothing in ~/wide_shadow is touched. Each replacement asserts
count == 1 on the production source; the device self-reports the production sha and the replacement list."""
import hashlib, io, json, os, sys, time
SRC = os.path.expanduser("~/wide_shadow/shadow_loop_v3.py"); OUT = sys.argv[1] if len(sys.argv) > 1 else "shadow_loop_v3_replay.py"
src = io.open(SRC, encoding="utf-8").read(); sha = hashlib.sha256(src.encode()).hexdigest()
REPL = [
 # 1. klines step -> channel rows already in the cache (the producer's own rows; later anchors only fill NaN rows).
 ("""    for s in st.live:
        j = st.sym_idx.get(s)
        if j is None: continue
        r = fx.get("/fapi/v1/klines", {"symbol": s, "interval": "5m", "limit": gap_bars,
                                       "endTime": anchor * 1000 - 1}, weight=kw)
        if isinstance(r, dict):
            missing += 1; continue
        pc = st.prev_close.get(s)
        for k in r:
            close_s = (int(k[0]) + 300000) // 1000
            if close_s > anchor:  # V1 因果硬断言
                future_dropped += 1; continue
            if close_s > data_max_ts: data_max_ts = close_s
            i = row_of.get(close_s)
            if i is None: continue
            c, ch = bars_to_channels(k)
            ret5 = (c / pc - 1) if (pc and pc > 0) else np.nan
            # 若该行已有数(重叠窗), 保持原值以免 f16 抖动 — 只填 NaN 行
            if not np.isfinite(float(st.cd[i, j, 3])):
                ch[0] = ret5
                st.cd[i, j] = np.array(clipch(ch), np.float16)
            pc = c
        if r:
            st.prev_close[s] = float(r[-1][4])
        fetched += 1
""",
  """    # REPLAY: channel rows come from the producer's own cache (rolling.npz snapshot); no fetch, no fill.
    fetched, missing, future_dropped, data_max_ts = REPLAY_KLINES(st, anchor, row_of)
"""),
 # 2. tail scoring off (score rows only; never touches weights)
 ("TAIL_SCORE = True          # (a) 对数据宇宙外的持仓名按真实价格/资金费补记分(只加字段, 不改书)",
  "TAIL_SCORE = False         # REPLAY: no venue calls"),
]
out = src
for a, b in REPL:
    n = out.count(a); assert n == 1, (n, a[:60]); out = out.replace(a, b)
hook = '''
# ══ REPLAY HOOKS (generated) ══
REPLAY_META = {"production_sha256": "%s", "generated_utc": "%s", "n_replacements": %d}
def REPLAY_KLINES(st, anchor, row_of):
    """No network: the cache already holds the producer's own channel rows. Report counts like the producer would."""
    ai = row_of.get(anchor)
    fetched = len(st.live); missing = 0; future_dropped = 0
    data_max_ts = int(st.cts[ai]) if ai is not None else 0
    return fetched, missing, future_dropped, data_max_ts
class ReplayFetcher:
    """Serves exchangeInfo (recorded base list) and fundingRate (recorded ledger rows); refuses everything else."""
    def __init__(self, base_syms, ledger_full):
        self.weight_used = 0; self.base = list(base_syms); self.ledger = ledger_full; self.calls = {}
    def get(self, path, params, weight):
        self.calls[path] = self.calls.get(path, 0) + 1
        if path == "/fapi/v1/exchangeInfo":
            return {"symbols": [{"symbol": s, "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING"} for s in self.base]}
        if path == "/fapi/v1/fundingRate":
            s = params["symbol"]; lo = int(params["startTime"]); hi = int(params["endTime"])
            rows = [r for r in self.ledger.get(s, []) if lo <= int(r[0]) * 1000 <= hi]
            return [{"fundingTime": int(r[0]) * 1000, "fundingRate": str(r[1])} for r in rows][: int(params.get("limit", 100))]
        raise RuntimeError("REPLAY: network path refused: " + path)
''' % (sha, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), len(REPL))
marker = "\ndef next_slot(offset_min=6):"
assert out.count(marker) == 1
out = out.replace(marker, hook + marker)
io.open(OUT, "w", encoding="utf-8").write(out)
print(json.dumps({"production_sha256": sha, "device": OUT, "device_sha256": hashlib.sha256(out.encode()).hexdigest(), "n_replacements": len(REPL)}))
