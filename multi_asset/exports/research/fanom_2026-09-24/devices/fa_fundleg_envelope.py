"""fa_fundleg_envelope.py — read-only envelope for the 2026-09 live drawdown questions (lead 2026-09-25).
No engine, no GPU, writes nothing outside my own receipts dir. Every root it reads is READ-ONLY.

Answers:
  Q3  windows where the 9-day equal-weight ALT return >= +15% and 9-day BTC > 0: the backtest book's 9-day return.
  A1  in those windows, how much the funding leg loses and how long it takes to recover.
  A2  full history, funding-leg SHORT side bucketed by funding quintile: mean contribution and the right tail
      (how often and how hard the shorts get squeezed); does the lowest bucket's short side make money long-term.

CALIBER, declared rather than assumed (CLAUDE.md: the return caliber binds to the PANEL FILE, not to a variable name):
  * per-name 4h return = the panel's own `Y4` field of wide_panel_4h_rawbuild_x0918r.npz. Verified in-range for a 4h
    simple return (sd 0.0268, p1 -0.0685, p99 +0.0739, median 0). It is NOT the engine's NAV caliber, so leg numbers
    from here are never mixed with the engine's `g` in one arithmetic statement.
  * the book's 9-day return = the ENGINE's own daily series (canonical BT.daily over 32 paths), which is NAV-based.
  * equal-weight ALT = cross-sectional mean of Y4 over (eligible AND crypto AND finite). 680 of 829 columns are crypto;
    the other 149 are TradFi and are excluded, per the recorded finding that the universe carries them.

REPRODUCTION CONTROL (the reason this device can claim to decompose the funding leg at all):
  the per-name contributions are built with fresh_legs.py's own formula and their SUM is compared against the stored
  LR[:, 2] in legs.npz. fresh_legs derives y4v from the 5-minute cache while this device uses the panel's Y4, so exact
  equality is NOT expected -- what is reported is the correlation and the bias, and the decomposition is labelled
  PANEL-CALIBER unless the match is tight. Without this control, a per-name decomposition of a leg is just an assertion.

usage: ... fa_fundleg_envelope.py WL <out.json>
"""
import os, sys, json, hashlib, time, datetime
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
OUT = sys.argv[2]
NC = "/dev/shm/news2_2026-09-23"
PANEL = "/workspace/axis_0919/x0918r/panels/wide_panel_4h_rawbuild_x0918r.npz"
sys.path.insert(0, f"{NC}/engine")
import bt_tables as BT

W_ANCH = 54          # 9 days x 6 anchors
ALT_THR = 0.15


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def iso(t): return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%d %H:%MZ")
def isod(t): return datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%d")


rec = {"device": "fa_fundleg_envelope.py", "self_sha256": sha(os.path.abspath(__file__)),
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "inputs": {PANEL: sha(PANEL), f"{NC}/work/legs.npz": sha(f"{NC}/work/legs.npz"),
                  f"{NC}/receipts/P1_members_2025H2on.npz": sha(f"{NC}/receipts/P1_members_2025H2on.npz")},
       "caliber": {"per_name_4h_return": "panel Y4 (wide_panel_4h_rawbuild_x0918r.npz)",
                   "book_9day_return": "engine daily series, canonical BT.daily, 32 paths (NAV caliber)",
                   "never_mixed": "panel-caliber leg numbers are never combined with engine g in one statement"}}

P = np.load(PANEL, allow_pickle=True)
pt = P["ts"].astype(np.int64); Y4 = P["Y4"]; EL = np.asarray(P["elig"]).astype(bool); psym = [str(s) for s in P["symbols"]]
M = np.load(f"{NC}/receipts/P1_members_2025H2on.npz", allow_pickle=True)
crypto = np.asarray(M["crypto"]).astype(bool); msym = [str(s) for s in M["symbols"]]
assert psym == msym, "panel and member-file symbol axes differ"
L = np.load(f"{NC}/work/legs.npz", allow_pickle=True)
lt = L["E_ts"].astype(np.int64); ZFD = L["ZFD"]; RN8 = L["RN8"]; LR = np.asarray(L["LR"], float); lsym = [str(s) for s in L["symbols"]]
assert lsym == psym, "legs and panel symbol axes differ"

# ---- equal-weight ALT and BTC, per anchor, on the panel axis ----
ok = np.isfinite(Y4) & EL & crypto[None, :]
cnt = ok.sum(1)
altr = np.where(cnt > 0, np.where(ok, Y4, 0.0).sum(1) / np.maximum(cnt, 1), np.nan)
bi = psym.index("BTCUSDT")
btcr = np.where(np.isfinite(Y4[:, bi]), Y4[:, bi], np.nan)
rec["universe"] = {"n_symbols": len(psym), "n_crypto": int(crypto.sum()), "n_tradfi_excluded": int((~crypto).sum()),
                   "median_names_per_anchor": float(np.median(cnt))}

def roll(x, w):
    o = np.full(len(x), np.nan)
    for i in range(len(x) - w + 1):
        v = x[i:i+w]
        if np.isfinite(v).all(): o[i] = float(np.prod(1.0 + v) - 1.0)
    return o

alt9 = roll(altr, W_ANCH); btc9 = roll(btcr, W_ANCH)

# ---- the book's daily series from the engine (NAV caliber) ----
books = {}
for seed in ("42", "2027"):
    cell = f"{NC}/runs/NEWS2_s{seed}_scaled_rule_raw_UAFE"
    tag = os.path.basename(cell)
    Ps = [BT.series_from_path(np.load(f"{cell}/PATH_{tag}_seed_{k:02d}.npz")) for k in range(32)]
    A = Ps[0]["A"].astype(np.int64)
    ud = None; RD = []
    for p in Ps:
        u, rd = BT.daily(A, p["r"])
        if ud is None: ud = u
        RD.append(rd)
    books[seed] = {"days": ud, "RD": np.stack(RD), "last_anchor": int(A[-1])}
rec["engine_axis"] = {s: {"last_anchor": iso(v["last_anchor"]), "n_days": int(len(v["days"]))} for s, v in books.items()}

def book9(seed, t_start, t_end):
    """9-day book return over the calendar days spanned by [t_start, t_end], mean across paths; None if uncovered"""
    b = books[seed]; d0 = (t_start // 86400) * 86400; d1 = (t_end // 86400) * 86400
    m = (b["days"] >= d0) & (b["days"] <= d1)
    if m.sum() < 2 or b["days"][-1] < d1: return None
    r = np.prod(1.0 + b["RD"][:, m], axis=1) - 1.0
    return float(100 * r.mean())

# ---- Q3 + A1: qualifying regime windows ----
qual = np.flatnonzero(np.isfinite(alt9) & np.isfinite(btc9) & (alt9 >= ALT_THR) & (btc9 > 0))
# keep non-overlapping windows: greedily take the strongest, then skip W_ANCH
order = qual[np.argsort(-alt9[qual])]
taken = []
for i in order:
    if all(abs(int(i) - int(j)) >= W_ANCH for j in taken): taken.append(int(i))
taken = sorted(taken)

# funding-leg cumulative (bps), on the legs axis
lpos = {int(t): i for i, t in enumerate(lt)}
fund = LR[:, 2]
wins = []
for i in taken:
    t0, t1 = int(pt[i]), int(pt[i + W_ANCH - 1])
    j0, j1 = lpos.get(t0), lpos.get(t1)
    fl = None; rec_days = None; rec_status = "no measurement (funding-leg series does not cover this window)"
    if j0 is not None and j1 is not None:
        seg = fund[j0:j1+1]
        # np.nansum of an all-NaN segment returns 0.0 -- that is no-measurement dressed as a zero. The funding-leg
        # series is NaN before 2022-07-01 (1,087 anchors) and has NO genuine exact zeros, so an all-NaN segment must
        # be reported as absent, not as 0.0.
        if np.isfinite(seg).any():
            fl = float(np.nansum(seg))
            # right-censoring: the funding-leg series ends 2026-09-19, so a late window has only a few days of
            # follow-up. Saying "not recovered within 400 days" when only 28 days were observable is a false
            # statement, so the available follow-up is measured and reported instead.
            fu = int(np.isfinite(fund[j1+1:]).sum()) / 6.0
            rec_status = ("n/a (leg gained over the window)" if fl >= 0
                          else "not recovered; only %.1f days of follow-up exist (right-censored)" % fu)
        # recovery: anchors after the window until the cumulative regains its pre-window level
        c = 0.0; k = j1 + 1; steps = 0
        if fl is not None and fl < 0:
            need = -fl
            while k < len(fund) and steps < 6 * 400:
                if np.isfinite(fund[k]): c += fund[k]
                if c >= need: break
                k += 1; steps += 1
            if c >= need:
                rec_days = steps / 6.0; rec_status = "recovered in %.1f days" % rec_days
    wins.append({"start": iso(t0), "end": iso(t1), "alt9_pct": float(100 * alt9[i]), "btc9_pct": float(100 * btc9[i]),
                 "book9_s42_pct": book9("42", t0, t1), "book9_s2027_pct": book9("2027", t0, t1),
                 "fund_leg_bps_sum": fl, "fund_leg_recovery_days": rec_days, "fund_leg_recovery_status": rec_status,
                 "followup_days_available": (int(np.isfinite(fund[j1+1:]).sum()) / 6.0) if j1 is not None else None})
rec["Q3_A1_windows"] = {"threshold": {"alt9_ge_pct": 100 * ALT_THR, "btc9_gt": 0}, "n_qualifying_nonoverlapping": len(taken),
                        "windows": wins}
cov = [w for w in wins if w["book9_s42_pct"] is not None]
if cov:
    v = np.array([w["book9_s42_pct"] for w in cov])
    rec["Q3_A1_windows"]["book9_s42_pct_over_covered"] = {
        "n_covered": len(cov), "min": float(v.min()), "median": float(np.median(v)), "max": float(v.max()),
        "n_le_minus9": int((v <= -9).sum())}
rec["Q3_A1_windows"]["n_uncovered_by_engine"] = len(wins) - len(cov)

# ---- A2: funding-leg SHORT side by funding quintile, full history ----
# per-name contribution with fresh_legs.py's own formula, then SUM compared against the stored LR
pl = {int(t): i for i, t in enumerate(pt)}
contrib_rows = []
mine = np.full(len(lt), np.nan)
QB = 5
agg = {b: {"n": 0, "sum_bps": 0.0, "sq": 0.0, "n_pos": 0, "sum_pos": 0.0, "worst": 0.0} for b in range(QB)}
for j, t in enumerate(lt):
    i = pl.get(int(t))
    if i is None: continue
    z = ZFD[j]; r8 = RN8[j]; y = Y4[i]
    m = np.isfinite(z)
    if m.sum() < 50: continue
    okl = m & np.isfinite(y)
    zz = np.where(okl, z, 0.0)
    if okl.sum() == 0: continue
    zz = zz - zz[okl].mean()
    zz = np.where(okl, zz, 0.0)
    g = np.abs(zz).sum()
    if g <= 1e-9: continue
    c = (zz / g) * np.nan_to_num(y, nan=0.0) * 1e4         # per-name contribution in bps
    mine[j] = float(c.sum())
    sh = okl & (zz < 0) & np.isfinite(r8)                   # SHORT side only
    if sh.sum() >= QB:
        rr = r8[sh]; cc = c[sh]
        q = np.argsort(np.argsort(rr)) * QB // max(1, sh.sum())      # quintile of funding rate, 0 = most negative
        for b in range(QB):
            sel = q == b
            if not sel.any(): continue
            a = agg[b]
            a["n"] += int(sel.sum()); a["sum_bps"] += float(cc[sel].sum()); a["sq"] += float((cc[sel] ** 2).sum())
            a["n_pos"] += int((cc[sel] > 0).sum()); a["sum_pos"] += float(cc[sel][cc[sel] > 0].sum())
            a["worst"] = min(a["worst"], float(cc[sel].min()))
both = np.isfinite(mine) & np.isfinite(fund)
rec["A2_reproduction_control"] = {
    "n_anchors_compared": int(both.sum()),
    "corr_with_stored_LR": float(np.corrcoef(mine[both], fund[both])[0, 1]),
    "mean_mine_bps": float(mine[both].mean()), "mean_stored_bps": float(fund[both].mean()),
    "mean_abs_diff_bps": float(np.abs(mine[both] - fund[both]).mean()),
    "why_not_exact": ("fresh_legs.py builds y4v from the 5-minute cache (sum of 5-min returns, >=46 of 48 finite); "
                      "this device uses the panel's Y4. Exact equality is not expected; the label below states what "
                      "the decomposition may be used for."),
    "label": None}
c_ = rec["A2_reproduction_control"]
c_["label"] = ("FAITHFUL_TO_STORED_LEG" if (c_["corr_with_stored_LR"] > 0.98 and c_["mean_abs_diff_bps"] < 1.0)
               else "PANEL_CALIBER_ONLY -- describes the panel-caliber funding leg, not the stored LR")
buck = {}
for b in range(QB):
    a = agg[b]
    if a["n"] == 0: buck[str(b)] = {"n": 0}; continue
    mean = a["sum_bps"] / a["n"]
    buck[str(b)] = {"n_observations": a["n"], "mean_contribution_bps": mean,
                    "total_contribution_bps": a["sum_bps"],
                    "rms_bps": float((a["sq"] / a["n"]) ** 0.5),
                    "frac_positive": a["n_pos"] / a["n"],
                    "sum_of_positive_bps": a["sum_pos"], "worst_single_bps": a["worst"]}
rec["A2_short_side_by_funding_quintile"] = {
    "bucket_0_note": "bucket 0 = MOST NEGATIVE funding rate (the crowded-short names)",
    "side": "short side only (zz < 0)", "buckets": buck}

json.dump(rec, open(OUT + ".tmp", "w"), indent=1, default=float); os.replace(OUT + ".tmp", OUT)
assert os.path.exists(OUT), "receipt not written"
print("FA_FUNDLEG_ENVELOPE ok | reproduction=%s corr=%.4f mean_abs_diff=%.3f bps" % (
    c_["label"].split(" --")[0], c_["corr_with_stored_LR"], c_["mean_abs_diff_bps"]), flush=True)
print("  qualifying non-overlapping windows (alt9>=+15%% & btc9>0): %d ; engine-covered %d" % (
    len(taken), len(cov)), flush=True)
for w in wins:
    print("   %s -> %s | alt9 %+6.1f%% btc9 %+6.1f%% | book9 s42 %s s2027 %s | fund leg %s bps | recover %s d" % (
        w["start"][:10], w["end"][:10], w["alt9_pct"], w["btc9_pct"],
        ("%+7.2f%%" % w["book9_s42_pct"]) if w["book9_s42_pct"] is not None else "  n/a  ",
        ("%+7.2f%%" % w["book9_s2027_pct"]) if w["book9_s2027_pct"] is not None else "  n/a  ",
        ("%+9.1f" % w["fund_leg_bps_sum"]) if w["fund_leg_bps_sum"] is not None else "  NO MEAS",
        w["fund_leg_recovery_status"]), flush=True)
print("  SHORT side by funding quintile (0 = most negative funding):", flush=True)
for b in range(QB):
    v = buck[str(b)]
    if not v.get("n_observations"): continue
    print("   q%d n=%8d mean %+8.4f bps  total %+12.1f  rms %7.3f  frac>0 %.3f  worst %+9.2f" % (
        b, v["n_observations"], v["mean_contribution_bps"], v["total_contribution_bps"], v["rms_bps"],
        v["frac_positive"], v["worst_single_bps"]), flush=True)
