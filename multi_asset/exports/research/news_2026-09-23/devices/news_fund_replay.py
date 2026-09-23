"""NEWS P2a: the producer's funding update loop (shadow_loop_v3.py L451-L484, source lines compiled
verbatim, sha + boundary asserted) replayed over the historical funding ledger, anchor by anchor.

Replay fetcher = the fundingRate endpoint semantics the loop relies on: rows with
startTime <= fundingTime <= endTime, ascending, at most `limit`; historical fundingTime is stored in whole
seconds, so fundingTime(ms) = ft*1000 and the loop's `int(row["fundingTime"]) // 1000` recovers ft.
base(A) = candidates(A) = legal mask ∧ crypto (AMENDMENT 1 §3.8). State starts empty (cold start).
Output per anchor, all 829 names: EMA acc (NaN = no state), last ledger row (ft, rate, iv) (ft=-1 none).
"""
import os, sys, json, time, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from news_hist_features import SHADOW_SRC, SHADOW_SHA, W, sha

LEDGER = "/workspace/baseline_tables_2026-09-19/funding/ledger_spliced_p2_to_20260901T0200_streamD_after.npz"
MASK = "/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"


def fund_block():
    src = open(SHADOW_SRC, "rb").read(); assert hashlib.sha256(src).hexdigest() == SHADOW_SHA
    lines = src.decode().split("\n")
    assert lines[450].strip() == "fund_updates = 0; fund_updates_base = 0" and lines[483].strip() == "if est: st.ema[s] = est", (lines[450], lines[483])
    code = "def fund_block(st, fx, anchor, base, _live_set):\n" + "\n".join(lines[450:484]) + "\n    return fund_updates, fund_updates_base\n"
    ns = {"np": np}
    exec(compile(code, SHADOW_SRC + ":L451-L484", "exec"), ns)
    return ns["fund_block"]


class ReplayFetcher:
    def __init__(self, sym_rows):
        self.rows = sym_rows; self.calls = 0; self.truncated = 0
    def get(self, path, params, weight=1):
        assert path == "/fapi/v1/fundingRate"
        self.calls += 1
        ft, rate = self.rows.get(params["symbol"], (np.zeros(0, np.int64), np.zeros(0)))
        lo = int(np.searchsorted(ft * 1000, params["startTime"], side="left"))
        hi = int(np.searchsorted(ft * 1000, params["endTime"], side="right"))
        if hi - lo > params["limit"]: self.truncated += 1
        hi = min(hi, lo + params["limit"])
        return [{"fundingTime": int(ft[k]) * 1000, "fundingRate": float(rate[k])} for k in range(lo, hi)]


class _St: pass


def main():
    t0 = time.time()
    ident = {LEDGER: sha(LEDGER), MASK: sha(MASK), SHADOW_SRC: sha(SHADOW_SRC), __file__: sha(os.path.abspath(__file__))}
    z = np.load(LEDGER); syms = [str(s) for s in z["symbols"]]; off = z["off"]; FT = z["ft"].astype(np.int64); RT = z["rate"].astype(np.float64)
    sym_rows = {}
    for j, s in enumerate(syms):
        a, b = int(off[j]), int(off[j + 1]); ft = FT[a:b]
        assert np.all(np.diff(ft) > 0), ("ledger order", s)
        sym_rows[s] = (ft, RT[a:b])
    mk = np.load(MASK); A = mk["ts"].astype(np.int64); assert [str(s) for s in mk["symbols"]] == syms
    crypto = np.load(f"{W}/receipts/P1_members_2025H2on.npz")["crypto"]
    cand = mk["mask"] & crypto[None, :]
    fb = fund_block(); st = _St(); st.ledger = {}; st.ema = {}; fx = ReplayFetcher(sym_rows)
    n = len(A); NW = len(syms)
    ema_acc = np.full((n, NW), np.nan); last_ft = np.full((n, NW), -1, np.int64); last_rate = np.full((n, NW), np.nan); last_iv = np.full((n, NW), np.nan)
    upd = np.zeros(n, np.int64); sidx = {s_: j for j, s_ in enumerate(syms)}
    for i, a in enumerate(A):
        base = [syms[j] for j in np.flatnonzero(cand[i])]
        u, ub = fb(st, fx, int(a), base, set(base)); upd[i] = u + ub
        for s, e in st.ema.items(): ema_acc[i, sidx[s]] = e["acc"]
        for s, led in st.ledger.items():
            if led:
                j = sidx[s]; last_ft[i, j] = led[-1][0]; last_rate[i, j] = led[-1][1]; last_iv[i, j] = led[-1][2]
        if i % 1000 == 0: print(time.strftime("%H:%M:%S", time.gmtime()), i, n, flush=True)
    out = f"{W}/work/fund_replay.npz"
    np.savez_compressed(out, anchors=A, symbols=np.array(syms), ema_acc=ema_acc, last_ft=last_ft, last_rate=last_rate, last_iv=last_iv, updates=upd)
    rec = {"device": os.path.abspath(__file__), "inputs_sha256": ident, "anchors": int(n), "first": int(A[0]), "last": int(A[-1]),
           "fetch_calls": fx.calls, "fetch_truncated_at_limit_100": fx.truncated, "updates_total": int(upd.sum()),
           "output": out, "output_sha256": sha(out), "seconds": round(time.time() - t0, 1),
           "semantics": "producer funding loop verbatim; base = legal∧crypto; cold start at first mask anchor"}
    json.dump(rec, open(f"{W}/receipts/P2A_FUND_REPLAY.json", "w"), indent=1)
    print("FUND_REPLAY_DONE", json.dumps({k: rec[k] for k in ("anchors", "fetch_calls", "fetch_truncated_at_limit_100", "updates_total", "seconds")}), flush=True)


if __name__ == "__main__":
    main()
