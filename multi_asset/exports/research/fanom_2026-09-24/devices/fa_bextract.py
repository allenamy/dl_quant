"""fa_bextract.py — extract a B-arm's per-anchor series against the SURVIVING NEWS original, then derive the
difference against the arm's own original. PREREG 56c0177aa readout 1.
  r_B4FRESH - r_FRESH = (r_B4FRESH - r_NEWS) - (r_FRESH - r_NEWS)   <- both terms available, no regeneration needed
usage: ... fa_bextract.py WL <variant_cell_dir> <base_arm FRESH|NEWS> <seed> <out.npz>
"""
import os, sys, json, hashlib
import numpy as np
WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x
CELL, BASEARM, SEED, OUT = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
ENG = "/dev/shm/fresh_2026-09-23/engine"; sys.path.insert(0, ENG)
import bt_tables as BT, bt_driver_lib as DL
N = "/dev/shm/news_2026-09-23"; R = "/dev/shm/fanom_2026-09-24/receipts"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def load(cell):
    tag = os.path.basename(cell); out = []
    for k in range(32):
        s = f"{cell}/PATH_{tag}_seed_{k:02d}"
        J = json.load(open(s + ".json")); assert J["npz_sha256"] == sha(s + ".npz")
        assert DL.audits_clean(J["audits"]) and int(J["seed"]) == k
        out.append(BT.series_from_path(np.load(s + ".npz")))
    return out
V = load(CELL); A = load(f"{N}/runs/NEWS_s{SEED}_scaled_rule_raw_UAFE")
ax = V[0]["A"]
for p in V + A: assert np.array_equal(p["A"], ax)
v_minus_news = np.mean([p["pnl"] for p in V], axis=0) - np.mean([p["pnl"] for p in A], axis=0)
v_r = np.mean([p["r"] for p in V], axis=0); a_r = np.mean([p["r"] for p in A], axis=0)
if BASEARM == "FRESH":
    S = np.load(f"{R}/FA_ANCHOR_SERIES.npz" if SEED == "42" else f"{R}/FA_ANCHOR_SERIES_s2027.npz")
    assert np.array_equal(S["anchors"].astype(np.int64), ax)
    vs_own = v_minus_news - S["price_diff_D_minus_A_bps"]
    pre = S["in_pre2026"].astype(bool); seat = S["seat_king_FRESH"]
else:
    S = np.load(f"{R}/FA_ANCHOR_SERIES.npz" if SEED == "42" else f"{R}/FA_ANCHOR_SERIES_s2027.npz")
    assert np.array_equal(S["anchors"].astype(np.int64), ax)
    vs_own = v_minus_news
    pre = S["in_pre2026"].astype(bool); seat = S["seat_king_FRESH"]
np.savez_compressed(OUT, anchors=ax, price_vs_NEWS_bps=v_minus_news, price_vs_own_original_bps=vs_own,
                    daily_r_variant=v_r, daily_r_news=a_r, in_pre2026=pre, seat_king_FRESH=seat)
print("FA_BEXTRACT %s base=%s s%s vs_own_mean=%+.4f bps/anchor (pre2026) vs_news_mean=%+.4f n=%d out=%s"
      % (os.path.basename(CELL), BASEARM, SEED, float(np.nanmean(vs_own[pre])), float(np.nanmean(v_minus_news[pre])),
         int(pre.sum()), sha(OUT)[:16]), flush=True)
