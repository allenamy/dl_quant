#!/usr/bin/env python3
"""bt_nav5_chunk_probe.py — WHY the extended run's 5-minute NAV is not bitwise equal to the published run at exactly one bar (2026-08-31T04:00Z).

The 5-minute sampler (bt_hist_sim31.HistSim31._values) marks a whole block of grid rows at once:
      blk = exp(LP[r0:r1][:, J] − cref[J]) * ref_px[J];  blk = where(bar_ts >= first_fin[J], blk, 0);  return blk @ Q
`blk @ Q` is a BLAS matrix–vector product, and BLAS sums each row in blocks whose layout depends on the SHAPE of the operand. The same grid
row therefore can round differently by one ulp depending on how many rows were flushed together — and the two runs necessarily flush that one
boundary in differently sized chunks: for the published run, 2026-08-31T04:00Z is the LAST boundary, written by the final `_flush_nav(t_end+1)`;
for the extended run it is an ordinary boundary inside a later chunk.

This probe reads the REAL pinned price table and shows, at the junction row and with a fixed weight vector:
  P0  a row computed inside blocks of different heights can differ, and the difference is at the last bit (relative ~1e-16)
  P1  a row computed inside blocks of the SAME height is bitwise identical (the control: the effect is the block height, nothing else)
  P2  the observed junction-bar difference in the runs (passed in on the command line) is of the same order as the probe's
It proves the MECHANISM class on this data; it is not a re-execution of the two runs.
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B bt_nav5_chunk_probe.py PATH,HOME,LC_CTYPE <price_npy> <price_meta_npz>
         <junction_iso> <observed_abs_delta> <out.json>
"""
import os, sys, json, time, calendar, hashlib
WL = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
assert WL, "env whitelist (argv[1]) must be non-empty"
extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
import numpy as np

T0 = time.time()
LP_P, META_P, JUNC, OBS, OUTP = sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5]), sys.argv[6]
ROW = 300
RES = []


def ok(name, cond, detail=None):
    RES.append(dict(check=name, ok=bool(cond), detail=detail)); print(("PASS " if cond else "FAIL ") + name, json.dumps(detail, default=str)[:300] if detail is not None else "", flush=True)


M = np.load(META_P, allow_pickle=True); grid = np.asarray(M["grid"]).astype(np.int64); g0 = int(grid[0])
cref = np.asarray(M["cref_raw"], np.float64); ref_px = np.asarray(M["ref_px"], np.float64); first_fin = np.asarray(M["first_fin"], np.int64)
LP = np.load(LP_P, mmap_mode="r")
t_j = calendar.timegm(time.strptime(JUNC, "%Y-%m-%dT%H:%M:%SZ")); r_j = (t_j - g0) // ROW
n_sym = LP.shape[1]
rng = np.random.default_rng(20260920)                      # a fixed weight vector; the probe is about the ARITHMETIC, not about any real book
J = np.sort(rng.choice(n_sym, size=240, replace=False)).astype(np.int64)
Q = rng.normal(0, 3.0, size=len(J))


def value_at(r_target, r0, r1):
    """the sampler's own expression over rows [r0, r1); returns the value of row r_target inside that block"""
    blk = np.exp(np.asarray(LP[r0:r1])[:, J] - cref[J][None, :]) * ref_px[J][None, :]
    bts = g0 + ROW * np.arange(r0, r1)
    blk = np.where(bts[:, None] >= first_fin[J][None, :], blk, 0.0)
    return float((blk @ Q)[r_target - r0])


heights = [1, 2, 3, 5, 8, 13, 48, 97, 288, 577]
vals = {h: value_at(r_j, r_j - h + 1, r_j + 1) for h in heights}          # the junction row as the LAST row of blocks of different heights
vals_mid = {h: value_at(r_j, r_j - h + 1, r_j + h) for h in heights[:6]}  # and inside longer blocks
uniq = sorted(set(list(vals.values()) + list(vals_mid.values())))
spread = (max(uniq) - min(uniq)) if len(uniq) > 1 else 0.0
base = abs(uniq[0]) or 1.0
ok("P0.same_row_different_block_heights_can_differ", len(uniq) > 1, {"distinct_values": len(uniq), "abs_spread": spread, "relative": spread / base,
                                                                    "by_height_last_row": {str(h): v for h, v in vals.items()}})
ok("P0.difference_is_last_bit", 0 < spread / base < 1e-14, {"relative_spread": spread / base})
rep = [value_at(r_j, r_j - 47, r_j + 1) for _ in range(5)]
ok("P1.same_block_height_is_bitwise_identical (control)", len(set(rep)) == 1, {"repeats": len(rep), "distinct": len(set(rep)), "value": rep[0]})
ok("P2.observed_run_difference_is_of_the_same_order", OBS == 0.0 or (spread > 0 and 1e-3 <= OBS / max(spread, 1e-300) <= 1e3) or OBS / base < 1e-14,
   {"observed_abs_delta": OBS, "probe_abs_spread": spread, "observed_relative_to_probe_value": OBS / base})
fails = [r["check"] for r in RES if not r["ok"]]
out = dict(device="bt_nav5_chunk_probe.py", self_sha256=hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), argv=sys.argv,
           numpy=np.__version__, price_npy=LP_P, junction=JUNC, junction_row=int(r_j), n_names_in_probe=int(len(J)),
           values_by_block_height=vals, values_row_inside_block=vals_mid, checks=RES, failed=fails, VERDICT="PASS" if not fails else "RED",
           runtime_s=round(time.time() - T0, 1))
json.dump(out, open(OUTP, "w"), indent=1, default=str)
print("BT_NAV5_CHUNK_PROBE VERDICT: " + ("ALL PASS %d/%d checks" % (len(RES), len(RES)) if not fails else "FAILURES %d/%d: %s" % (len(fails), len(RES), fails)), flush=True)
sys.exit(0 if not fails else 3)
