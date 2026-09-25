"""fa_rn8extract.py — extract the FULL channel decomposition from an engine cell, for PREREG_step1_rn8_clamp_2026-09-25.md
(commit 1624526af). fa_bextract.py saved only price/daily_r/g; the rn8 question needs the funding channel, because the
whole point is that the clamp trades price alpha for funding paid.

Channels, exactly as bt_tables.series_from_path defines them (bt_tables.py L65-71) -- FOUR, not three:
    pnl = 1e4*price_trade/den     price channel
    car = -1e4*funding/den        carry; NOTE THE SIGN -- car > 0 means funding RECEIVED
    cst = 1e4*fee/den             fees
    unk = 1e4*unk_excluded*(unk_price+unk_funding)/den    unknown-position channel
    g   = 1e4*r/gm                the total

CLOSURE (asserted, per-anchor): g must equal pnl+car+cst+unk to within TOL. The prereg forbids dropping `unk` to make
the count three: a decomposition that does not close is not a decomposition, and silently omitting a term is the
"encode no-measurement as a benign value" family. If unk is identically zero here, that is REPORTED as measured-zero,
not omitted.

usage: ... fa_rn8extract.py WL <cell_dir> <ARM> <seed> <out.npz>
"""
import os, sys, json, hashlib, time
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
CELL, ARM, SEED, OUT = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
sys.path.insert(0, "/dev/shm/fresh_2026-09-23/engine")
import bt_tables as BT, bt_driver_lib as DL

TOL = 1e-6          # bps per anchor; closure is an arithmetic identity, so this is tight on purpose


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


tag = os.path.basename(CELL)
P = []
for k in range(32):
    s = f"{CELL}/PATH_{tag}_seed_{k:02d}"
    J = json.load(open(s + ".json"))
    assert J["npz_sha256"] == sha(s + ".npz"), f"path npz sha mismatch at seed {k}"
    assert DL.audits_clean(J["audits"]) and int(J["seed"]) == k
    P.append(BT.series_from_path(np.load(s + ".npz")))
ax = P[0]["A"]
for p in P:
    assert np.array_equal(p["A"], ax), "path anchor axes differ"

ch = {}
for k in ("g", "pnl", "car", "cst", "unk", "tau", "r", "hold", "halt"):
    ch[k] = np.mean([p[k] for p in P], axis=0)

# ---- closure, per anchor ----
resid = ch["g"] - (ch["pnl"] + ch["car"] + ch["cst"] + ch["unk"])
max_abs = float(np.nanmax(np.abs(resid)))
closes = bool(max_abs <= TOL)
unk_all_zero = bool(np.all(ch["unk"] == 0.0))

rec = {"device": "fa_rn8extract.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "prereg": {"path": "docs/PREREG_step1_rn8_clamp_2026-09-25.md", "commit": "1624526af"},
       "cell": CELL, "arm": ARM, "seed": SEED, "anchors": int(len(ax)), "paths": len(P),
       "channel_definitions": "bt_tables.series_from_path L65-71; car = -funding so car>0 means funding RECEIVED",
       "closure": {"identity": "g == pnl + car + cst + unk", "max_abs_residual_bps": max_abs,
                   "tolerance_bps": TOL, "CLOSES": closes},
       "unk_channel": {"identically_zero": unk_all_zero,
                       "status": ("MEASURED_ZERO -- reported, not omitted" if unk_all_zero else "nonzero, carried"),
                       "sum_bps": float(np.nansum(ch["unk"]))},
       "window_totals_bps": {k: float(np.nansum(ch[k])) for k in ("g", "pnl", "car", "cst", "unk")}}

assert closes, f"channel decomposition does not close: max|g-(pnl+car+cst+unk)| = {max_abs} bps > {TOL}"

np.savez_compressed(OUT + ".tmp.npz", anchors=ax, **{k: v for k, v in ch.items()})
os.replace(OUT + ".tmp.npz", OUT)
rec["out"] = OUT; rec["out_sha256"] = sha(OUT)
json.dump(rec, open(OUT.replace(".npz", ".json"), "w"), indent=1)
assert os.path.exists(OUT.replace(".npz", ".json")), "receipt not written"
print("FA_RN8EXTRACT %s s%s CLOSES=%s max_resid=%.3e unk_zero=%s | totals bps g=%+.1f pnl=%+.1f car=%+.1f cst=%+.1f unk=%+.1f"
      % (ARM, SEED, closes, max_abs, unk_all_zero, rec["window_totals_bps"]["g"], rec["window_totals_bps"]["pnl"],
         rec["window_totals_bps"]["car"], rec["window_totals_bps"]["cst"], rec["window_totals_bps"]["unk"]), flush=True)
