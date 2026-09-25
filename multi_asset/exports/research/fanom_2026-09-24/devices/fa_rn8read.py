"""fa_rn8read.py — rn8 readout. PREREG docs/PREREG_step1_rn8_clamp_2026-09-25.md, AMENDMENT 1 (commit 64f0ebb27).

AMENDMENT 1 §C requires the FROZEN news_stats.py caliber, so this device IMPORTS news_stats and calls its own
dbar / boot / daily_on / seg_mask / full_days / path_metrics / SEG / JUDGE. It does NOT reimplement them: writing my
own version from the description is what produced the drifting second instrument behind correction W-1
(mine averaged across paths first; the canonical dbar takes per-path daily differences THEN averages).

Two traps this device is built around, both measured rather than assumed:
  * news_stats sets `BT = DL = None` at module level and wires them inside main(). Importing it and calling daily_on
    without wiring them raises on None. This device wires them exactly as main() does, and asserts it.
  * the canonical channel identity is  g = pnl - car - cst - unk  (news_stats.py L134), and `car` is named
    funding_paid there (L131), i.e. car > 0 means funding PAID. My earlier draft had both the sign and the identity
    backwards; see AMENDMENT 1 §B. The identity is checked by the canonical path_metrics itself
    (g_identity_max_err), which is reported here rather than re-derived.

usage: ... fa_rn8read.py WL <variant_cell> <baseline_cell> <seed> <out.json>
"""
import os, sys, json, hashlib, time
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
VCELL, BCELL, SEED, OUT = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]

ENG = "/dev/shm/news2_2026-09-23/engine"
NS_SHA = "7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c"
NC = "/dev/shm/news2_2026-09-23"
sys.path.insert(0, ENG)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


assert sha(os.path.join(ENG, "news_stats.py")) == NS_SHA, "news_stats.py is not the frozen caliber"
import news_stats as NS
import bt_tables as BT, bt_driver_lib as DL
NS.BT, NS.DL = BT, DL                                   # exactly what NS.main() does
assert NS.BT is not None and NS.DL is not None, "canonical globals not wired; daily_on would raise on None"


def load_cell(cell):
    tag = os.path.basename(cell); P = []
    for k in range(32):
        s = f"{cell}/PATH_{tag}_seed_{k:02d}"
        J = json.load(open(s + ".json"))
        assert J["npz_sha256"] == sha(s + ".npz"), f"{tag} seed {k}: npz sha mismatch"
        assert DL.audits_clean(J["audits"]) and int(J["seed"]) == k, f"{tag} seed {k}: audit/seed"
        P.append(BT.series_from_path(np.load(s + ".npz")))
    return P


V, B_ = load_cell(VCELL), load_cell(BCELL)              # seed order 0..31 => common random numbers pair by index
A = V[0]["A"]
for p in V + B_:
    assert np.array_equal(p["A"], A), "path anchor axes differ across paths/arms"

masks = {s: NS.seg_mask(A, a, b) for s, (a, b) in NS.SEG.items()}
days = {s: NS.full_days(A, masks[s]) for s in NS.SEG}

rec = {"device": "fa_rn8read.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "prereg": {"path": "docs/PREREG_step1_rn8_clamp_2026-09-25.md", "amendment_1": "64f0ebb27"},
       "caliber": {"news_stats.py": NS_SHA, "functions_used": "dbar, boot, daily_on, seg_mask, full_days, path_metrics",
                   "reimplemented": "nothing -- AMENDMENT 1 section C"},
       "variant_cell": VCELL, "baseline_cell": BCELL, "seed": SEED,
       "SENTENCE_verbatim": NS.SENTENCE,
       "channel_identity": "g = pnl - car - cst - unk ; car == funding_paid (positive = PAID)",
       "segments": {}, "channels": {}, "behavioural": {}}

# ---- main reading: canonical dbar on the pre-2026 judge window, plus every segment separately ----
for s in ("pre2026", "2023H2", "2024", "2025", "2026"):
    db, D = NS.dbar(V, B_, masks[s], days[s])
    est = float(1e4 * db.mean())
    e = {"mean_bps_per_day": est, "n_days": int(len(db)), "n_windows": int(masks[s].sum())}
    if s == "pre2026":
        e["boot"] = NS.boot(db, 30)
    rec["segments"][s] = e

# ---- channels, via the canonical path_metrics (which also checks the g identity) ----
for s in ("pre2026", "2026"):
    mv = [NS.path_metrics(p, masks[s], days[s]) for p in V]
    mb = [NS.path_metrics(p, masks[s], days[s]) for p in B_]
    ch = {}
    for k in ("g", "price", "funding_paid", "fee", "unknown_excluded", "turnover_over_gross"):
        a_ = float(np.mean([x[k] for x in mv])); b_ = float(np.mean([x[k] for x in mb]))
        ch[k] = {"variant": a_, "baseline": b_, "delta": a_ - b_}
    ch["NET_price_minus_funding_paid"] = ch["price"]["delta"] - ch["funding_paid"]["delta"]
    ch["g_identity_max_err"] = {"variant": float(max(x["g_identity_max_err"] for x in mv)),
                                "baseline": float(max(x["g_identity_max_err"] for x in mb))}
    rec["channels"][s] = ch

# ---- behavioural difference + mandatory cancellation ratio (no shares) ----
dpnl = np.mean([p["pnl"] for p in V], 0) - np.mean([p["pnl"] for p in B_], 0)
pop = masks["pre2026"]
tot = float(np.nansum(dpnl[pop]))
L = np.load(f"{NC}/work/legs.npz"); le = L["E_ts"].astype(np.int64); WL = L["WL"].astype(np.float64)
pos = {int(t): i for i, t in enumerate(le)}
si = np.array([pos[int(t)] for t in A])
s0, s2 = WL[si, 0], WL[si, 2]
w0 = np.where((s0 + s2) > 1e-12, s0 / (s0 + s2), 0.5)
bang = (w0 == 0.0) | (w0 == 1.0)
parts = {"bang_bang_seat": float(np.nansum(dpnl[pop & bang])), "interior_seat": float(np.nansum(dpnl[pop & ~bang]))}
gross = sum(abs(v) for v in parts.values())
rec["behavioural"] = {"anchors_with_price_difference": int((np.abs(dpnl[pop]) > 0).sum()),
                      "total_price_delta_bps_pre2026": tot,
                      "bang_bang_segmentation": {"parts_absolute_bps": parts,
                                                 "n_bang_bang": int((pop & bang).sum()), "n_interior": int((pop & ~bang).sum()),
                                                 "bang_bang_fraction": float((pop & bang).sum() / max(1, pop.sum())),
                                                 "note": "absolute contributions only; shares deliberately not reported"},
                      "cancellation_ratio": (abs(tot) / gross if gross else None)}
assert rec["behavioural"]["anchors_with_price_difference"] > 0, \
    "variant and baseline price channels are identical on every anchor -- the clamp switch is not wired"

json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
assert os.path.exists(OUT), "receipt not written"
p26 = rec["segments"]["pre2026"]; c = rec["channels"]["pre2026"]
print("FA_RN8READ s%s | pre2026 dbar=%+.4f bps/d ci95=%s | 2026 dbar=%+.4f | dPrice=%+.4f dFundPaid=%+.4f NET=%+.4f | g_id_err=%.2e | cancel=%.3f"
      % (SEED, p26["mean_bps_per_day"], [round(x, 3) for x in p26["boot"]["ci95_bps"]],
         rec["segments"]["2026"]["mean_bps_per_day"], c["price"]["delta"], c["funding_paid"]["delta"],
         c["NET_price_minus_funding_paid"], max(c["g_identity_max_err"].values()),
         rec["behavioural"]["cancellation_ratio"] or 0.0), flush=True)
for s in ("2023H2", "2024", "2025", "2026"):
    print("    seg %-7s dbar=%+8.4f bps/d over %d days" % (s, rec["segments"][s]["mean_bps_per_day"], rec["segments"][s]["n_days"]), flush=True)
