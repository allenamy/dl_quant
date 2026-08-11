"""PAIRED old-vs-new generation rank-IC, backfilled offline.

★ WHAT THIS ANSWERS, AND WHAT IT CANNOT
The live question is "did the 2026-08-05 checkpoint swap help?". Until now the only evidence was
UNPAIRED: the old generation's ICs come from one stretch of calendar and the new one's from
another, so every regime difference lands in the comparison. This scores BOTH generations on the
SAME anchors, the SAME panel, the SAME member mask and the SAME realised target. The only thing
that differs is the model weights ⇒ regime cancels by construction.

It still cannot separate CALIBER from FRESHNESS: the new generation is both clean-caliber and
trained on a month more data. The deployed object is the package, so the package is the right unit
for the user's question — but no claim of the form "the clean caliber is worth X" may be read out
of this table.

★ THE READ IS FIXED BEFORE THE NUMBERS ARE SEEN (written 2026-08-06 ~09:3xZ, pre-run):
  · window       = anchors at/after 2026-08-01T00:00Z. Strictly OOS for BOTH generations
                   (new trained to 07-31, old to 2026-06) — no in-sample advantage either way.
  · primary      = paired Δ = IC_new − IC_old per anchor, on the DL composite the book uses.
  · a DIRECTIONAL claim needs |t| >= 2.0 AND the sign to hold in >= 60% of anchors.
                   Anything weaker is reported as "cannot distinguish", not as a small effect.
  · per-leg (king, s2) is reported for diagnosis and is NOT a second bite at significance.
  · OBSERVATIONAL, not randomised. Paired removes regime; it does not remove selection of the
    window, which is why the window is defined by a training-data boundary and not by a result.
"""
import json
import os
import sys

import numpy as np

REPO = os.path.expanduser("~/dl_quant_live")
sys.path[:0] = [os.path.join(REPO, "signal"), os.path.join(REPO, "live"), REPO]

import fapi_source as FS          # noqa: E402
import inference as INF           # noqa: E402
import live_panel as LP           # noqa: E402
import panel_build as PB          # noqa: E402

OLD = os.path.join(REPO, "rollback_batch1_20260804T145921Z", "checkpoints")
NEW = os.path.join(REPO, "checkpoints")
CUTOFF_MS = 1785542400000         # 2026-08-01T00:00:00Z
HOURS = 1200
FLOOR = 887                       # panel_build's own warmup floor; no anchor below it


def rank_ic(a, b):
    """Spearman over the finite intersection."""
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 10:
        return np.nan
    x, y = a[m], b[m]
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean(); ry -= ry.mean()
    d = np.sqrt((rx * rx).sum() * (ry * ry).sum())
    return float((rx * ry).sum() / d) if d > 0 else np.nan


def main():
    src = FS.FapiSource()
    print(f"building {HOURS}h panel ...", flush=True)
    built = LP.build_live_panel(src, hours=HOURS, refresh=False,
                                progress=lambda m: print(f"  {m}", flush=True))
    CH, ts, syms = built["CH"], np.asarray(built["ts"]), built["symbols"]
    CLOSE = np.asarray(built["CLOSE"], float)
    print(f"panel: T={len(ts)} N={len(syms)} "
          f"{np.datetime64(int(ts[0]), 'ms')} .. {np.datetime64(int(ts[-1]), 'ms')}", flush=True)

    tradable = None
    try:
        tradable = set(src.perp_symbols())
    except Exception as e:
        print(f"  venue list unavailable ({e}); data-only eligibility", flush=True)
    member = PB.derive_member(built["DVOL30"], built["CLOSE"], symbols=syms, tradable=tradable)

    gens = {}
    for tag, d in (("new", NEW), ("old", OLD)):
        gens[tag], _man = INF.load(stats_path=os.path.join(d, "norm_stats.npz"), ckpt_dir=d)
        print(f"loaded {tag}: {d}", flush=True)

    # 4h-aligned anchors, inside the common-OOS window, with W history and a realised +4h target
    idx = [i for i in range(FLOOR, len(ts) - 4)
           if int(ts[i]) % (4 * 3600 * 1000) == 0 and int(ts[i]) >= CUTOFF_MS]
    print(f"{len(idx)} anchors in the common-OOS window\n", flush=True)

    rows = []
    for i in idx:
        mask = member[i].astype(np.float32)
        if mask.sum() < 20:
            continue
        window = CH[i - INF.W + 1: i + 1].transpose(1, 0, 2)
        y = np.full(len(syms), np.nan)
        c0, c1 = CLOSE[i], CLOSE[i + 4]
        ok = np.isfinite(c0) & np.isfinite(c1) & (c0 > 0)
        y[ok] = c1[ok] / c0[ok] - 1.0
        y[mask < 0.5] = np.nan                       # members only, as production scores

        rec = {"ts": int(ts[i]), "utc": str(np.datetime64(int(ts[i]), "ms")),
               "n_members": int(mask.sum())}
        comp = {}
        for tag in ("new", "old"):
            per_leg = {}
            for leg in ("king", "s2"):
                c, base, _ = gens[tag][leg].composite(window, mask)
                v = np.full(len(syms), np.nan)
                if c is not None:
                    v[np.asarray(base)] = c
                per_leg[leg] = v
                rec[f"ic_{leg}_{tag}"] = rank_ic(v, y)
            # the DL composite the book actually blends: equal-z of the two legs over members
            z = []
            for leg in ("king", "s2"):
                v = per_leg[leg][mask > 0.5]
                s = np.nanstd(v)
                z.append((v - np.nanmean(v)) / s if s > 0 else v * np.nan)
            cm = np.nansum(np.vstack(z), axis=0)
            full = np.full(len(syms), np.nan); full[mask > 0.5] = cm
            comp[tag] = rank_ic(full, y)
            rec[f"ic_dl_{tag}"] = comp[tag]
        rec["d_dl"] = comp["new"] - comp["old"]
        rows.append(rec)
        print(f"  {rec['utc']}  n={rec['n_members']:3d}  "
              f"dl new={comp['new']:+.4f} old={comp['old']:+.4f}  Δ={rec['d_dl']:+.4f}", flush=True)

    if not rows:
        print("no scorable anchors"); return

    d = np.array([r["d_dl"] for r in rows], float)
    d = d[np.isfinite(d)]
    n = len(d)
    t = float(d.mean() / (d.std(ddof=1) / np.sqrt(n))) if n > 1 and d.std(ddof=1) > 0 else np.nan
    win = float((d > 0).mean())
    print("\n" + "=" * 78)
    print(f"PAIRED  n={n}  mean Δ(new−old) = {d.mean():+.5f}  t = {t:+.2f}  "
          f"new-wins = {win:.0%}")
    for tag in ("new", "old"):
        for leg in ("dl", "king", "s2"):
            v = np.array([r.get(f"ic_{leg}_{tag}") for r in rows], float)
            v = v[np.isfinite(v)]
            print(f"  {tag:3s} {leg:5s} mean IC = {v.mean():+.5f}  (n={len(v)})")
    verdict = ("DIRECTIONAL" if (np.isfinite(t) and abs(t) >= 2.0
                                 and max(win, 1 - win) >= 0.60) else "CANNOT DISTINGUISH")
    print(f"\nPRE-REGISTERED READ: {verdict}  "
          f"(needs |t|>=2.0 and sign held >=60%; got |t|={abs(t):.2f}, {max(win,1-win):.0%})")
    print("=" * 78)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paired_gen_result.json")
    json.dump({"rows": rows, "n": n, "mean_delta": float(d.mean()), "t": t,
               "new_win_rate": win, "verdict": verdict,
               "window": "anchors >= 2026-08-01T00:00Z (common-OOS for both generations)",
               "caveat": "package comparison: caliber and freshness are confounded by design"},
              open(out, "w"), indent=1)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
