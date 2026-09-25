"""fa_window_legs.py — put the BACKTEST's 2026-08 drawdown and the LIVE 2026-09 drawdown side by side, decomposed the
same way by the same code path (lead 2026-09-25). Read-only; no engine, no GPU.

Two windows:
  BT_AUG  2026-08-14 .. 2026-08-28   (the cluster where every historical <=-9% 9-day book window sits)
  LIVE_SEP 2026-09-16 12:45Z .. end of the legs axis (2026-09-19T00:00Z)

WHY per-anchor means are reported next to the sums: the two windows are NOT the same length (90 vs 15 anchors at 4h).
Comparing sums across windows of different length would attribute a length difference to a mechanism difference, so
every quantity is given as both a sum and a per-anchor mean, and the anchor count is printed beside each.

Leg decomposition uses legs.npz's own stored LR columns (king / rev24 / fund) -- these are the SIGNAL LEG returns, not
the book. The book is the combo of them, so leg sums do not have to add up to a book return and are not presented as if
they did.

The per-name short-side decomposition is PANEL-CALIBER (panel Y4, not the 5-minute cache that fresh_legs.py uses);
the reproduction control against the stored LR is re-run here and printed, exactly as in fa_fundleg_envelope.py.

usage: ... fa_window_legs.py WL <out.json>
"""
import os, sys, json, hashlib, time, datetime, calendar
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT = sys.argv[2]
NC = "/dev/shm/news2_2026-09-23"
PANEL = "/workspace/axis_0919/x0918r/panels/wide_panel_4h_rawbuild_x0918r.npz"
LEGS = ("king", "rev24", "fund")
QB = 5


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%d %H:%MZ")


L = np.load(f"{NC}/work/legs.npz", allow_pickle=True)
lt = L["E_ts"].astype(np.int64); LR = np.asarray(L["LR"], float)
ZFD = L["ZFD"]; RN8 = L["RN8"]; lsym = [str(s) for s in L["symbols"]]
P = np.load(PANEL, allow_pickle=True)
pt = P["ts"].astype(np.int64); Y4 = P["Y4"]; psym = [str(s) for s in P["symbols"]]
assert lsym == psym, "legs and panel symbol axes differ"
pl = {int(t): i for i, t in enumerate(pt)}

WINDOWS = {"BT_AUG": ("2026-08-14T00:00:00Z", "2026-08-28T20:00:00Z"),
           "LIVE_SEP": ("2026-09-16T12:45:00Z", "2026-09-19T00:00:00Z")}

rec = {"device": "fa_window_legs.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "inputs": {f"{NC}/work/legs.npz": sha(f"{NC}/work/legs.npz"), PANEL: sha(PANEL)},
       "legs_axis": {"first": iso(lt[0]), "last": iso(lt[-1]), "n": int(len(lt))},
       "caveats": {"legs_are_signal_legs_not_the_book":
                   "LR columns are the signal legs; the book is their combo, so leg sums need not add to a book return",
                   "window_lengths_differ": "sums AND per-anchor means are both reported; anchor counts printed",
                   "per_name_caliber": "panel Y4 (PANEL_CALIBER); reproduction control against stored LR printed"},
       "windows": {}}

# ---- reproduction control, once, over the whole overlap ----
mine = np.full(len(lt), np.nan)
percell = {}
for j, t in enumerate(lt):
    i = pl.get(int(t))
    if i is None: continue
    z = ZFD[j]; y = Y4[i]
    m = np.isfinite(z)
    if m.sum() < 50: continue
    okl = m & np.isfinite(y)
    if okl.sum() == 0: continue
    zz = np.where(okl, z, 0.0); zz = zz - zz[okl].mean(); zz = np.where(okl, zz, 0.0)
    g = np.abs(zz).sum()
    if g <= 1e-9: continue
    c = (zz / g) * np.nan_to_num(y, nan=0.0) * 1e4
    mine[j] = float(c.sum()); percell[j] = (c, zz, RN8[j], okl)
both = np.isfinite(mine) & np.isfinite(LR[:, 2])
rc = {"n_anchors": int(both.sum()), "corr": float(np.corrcoef(mine[both], LR[both, 2])[0, 1]),
      "mean_abs_diff_bps": float(np.abs(mine[both] - LR[both, 2]).mean())}
rc["label"] = ("FAITHFUL" if (rc["corr"] > 0.98 and rc["mean_abs_diff_bps"] < 1.0) else "PANEL_CALIBER_ONLY")
rec["reproduction_control"] = rc

for name, (a, b) in WINDOWS.items():
    t0, t1 = ts(a), ts(b)
    sel = np.flatnonzero((lt >= t0) & (lt <= t1))
    o = {"requested": [a, b], "n_anchors": int(len(sel))}
    if len(sel) == 0:
        o["status"] = "NO ANCHORS IN LEGS AXIS"; rec["windows"][name] = o; continue
    o["first_anchor"] = iso(lt[sel[0]]); o["last_anchor"] = iso(lt[sel[-1]])
    o["legs"] = {}
    for li, leg in enumerate(LEGS):
        v = LR[sel, li]
        f = np.isfinite(v)
        o["legs"][leg] = {"n_finite": int(f.sum()),
                          "sum_bps": float(np.nansum(v)) if f.any() else None,
                          "mean_bps_per_anchor": float(np.nanmean(v)) if f.any() else None}
    # short side by funding quintile, same code path for both windows
    agg = {q: {"n": 0, "sum": 0.0, "npos": 0, "worst": 0.0} for q in range(QB)}
    n_used = 0
    for j in sel:
        if j not in percell: continue
        c, zz, r8, okl = percell[j]
        shm_ = okl & (zz < 0) & np.isfinite(r8)
        if shm_.sum() < QB: continue
        n_used += 1
        rr = r8[shm_]; cc = c[shm_]
        q = np.argsort(np.argsort(rr)) * QB // max(1, shm_.sum())
        for qq in range(QB):
            s_ = q == qq
            if not s_.any(): continue
            A_ = agg[qq]
            A_["n"] += int(s_.sum()); A_["sum"] += float(cc[s_].sum())
            A_["npos"] += int((cc[s_] > 0).sum()); A_["worst"] = min(A_["worst"], float(cc[s_].min()))
    o["short_side_by_funding_quintile"] = {
        "anchors_used": n_used, "note": "q0 = most negative funding rate (crowded shorts); PANEL_CALIBER",
        "buckets": {str(q): ({"n_obs": agg[q]["n"], "sum_bps": agg[q]["sum"],
                              "mean_bps": agg[q]["sum"] / agg[q]["n"], "frac_positive": agg[q]["npos"] / agg[q]["n"],
                              "worst_single_bps": agg[q]["worst"]} if agg[q]["n"] else {"n_obs": 0})
                    for q in range(QB)}}
    rec["windows"][name] = o

json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
assert os.path.exists(OUT), "receipt not written"
print("FA_WINDOW_LEGS reproduction=%s corr=%.4f mad=%.3f bps" % (rc["label"], rc["corr"], rc["mean_abs_diff_bps"]), flush=True)
for name, o in rec["windows"].items():
    if o.get("status"): print("  %-9s %s" % (name, o["status"])); continue
    print("  %-9s %s .. %s  n_anchors=%d" % (name, o["first_anchor"], o["last_anchor"], o["n_anchors"]), flush=True)
    for leg in LEGS:
        g = o["legs"][leg]
        print("      %-6s sum %+10.1f bps   mean %+8.3f bps/anchor  (n_finite %d)" % (
            leg, g["sum_bps"] if g["sum_bps"] is not None else float("nan"),
            g["mean_bps_per_anchor"] if g["mean_bps_per_anchor"] is not None else float("nan"), g["n_finite"]), flush=True)
    bb = o["short_side_by_funding_quintile"]["buckets"]
    print("      short side by funding quintile (anchors used %d):" % o["short_side_by_funding_quintile"]["anchors_used"], flush=True)
    for q in range(QB):
        v = bb[str(q)]
        if not v.get("n_obs"): continue
        print("        q%d n=%6d sum %+9.1f  mean %+8.4f  frac>0 %.3f  worst %+8.2f" % (
            q, v["n_obs"], v["sum_bps"], v["mean_bps"], v["frac_positive"], v["worst_single_bps"]), flush=True)
