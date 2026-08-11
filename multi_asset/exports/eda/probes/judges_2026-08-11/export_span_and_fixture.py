"""ONE server export (piped over stdin; writes /tmp only, never the server repo).

Produces four artefacts the local live repo needs:
  1. /tmp/funding_span_table.json  per-symbol FULL-HISTORY median settlement interval -> EMA span.
     0C's ruling: ONE table, SHARED by both calibers. The dimension fix deliberately changes the
     LEVEL only, not the span -- the 3.3e-12 control rests on "everything except level unchanged".
  2. /tmp/funding_raw.npz          the raw funding archive (all symbols, full history) so the local
     side can rebuild BOTH calibers from the same rows the server used.
  3. /tmp/funding_gap_report.json  the assert_funding_dim gap on three panels -- proves WHICH file
     is as-trained (gap ~ -0.37) and which is corrected (gap ~ +0.15).
  4. /tmp/parity_fixture_v2.npz    anchors spanning every year + sparsest mask + migration windows.
     Windows are stored ONCE and shared by king/s2 (same panel, only mu/sd differ) -- halves size.
"""
import gc
import glob
import json
import os.path as p
import sys

import numpy as np
import pandas as pd

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
WIDE = REPO + "/data/wide"
sys.path.insert(0, REPO)
sys.path.insert(0, MA)

HOUR_MS = 3_600_000
W = 168


# ------------------------------------------------------------------ 1. span table + migrations
def span_table():
    tab, sym_list, fts_all, rate_all, ivh_all, offs = {}, [], [], [], [], [0]
    for f in sorted(glob.glob(WIDE + "/*_funding.csv")):
        s = p.basename(f)[:-len("_funding.csv")]
        fd = pd.read_csv(f)
        if len(fd) < 3:
            continue
        fd = fd.sort_values("fundingTime_ms")
        fts = fd["fundingTime_ms"].to_numpy().astype(np.int64)
        rate = pd.to_numeric(fd["fundingRate"], errors="coerce").to_numpy().astype(np.float64)
        has_col = "funding_interval_h" in fd.columns
        ivh_raw = (pd.to_numeric(fd["funding_interval_h"], errors="coerce").to_numpy().astype(np.float64)
                   if has_col else np.full(len(fd), np.nan))
        ivh = np.where(np.isfinite(ivh_raw) & (ivh_raw > 0), ivh_raw, 8.0)     # builder's guard
        ih = float(np.median(ivh))
        span = max(2, int(round(24.0 / max(ih, 1.0))))
        ch = np.where(ivh[1:] != ivh[:-1])[0] + 1
        tab[s] = dict(median_interval_h=ih, span=span, n_rows=int(len(fd)),
                      first_ms=int(fts[0]), last_ms=int(fts[-1]),
                      has_interval_col=bool(has_col),
                      n_nonfinite_interval=int((~(np.isfinite(ivh_raw) & (ivh_raw > 0))).sum()),
                      intervals=sorted(float(v) for v in np.unique(ivh)),
                      migrations=[dict(ts_ms=int(fts[i]), frm=float(ivh[i - 1]), to=float(ivh[i]))
                                  for i in ch])
        sym_list.append(s)
        fts_all.append(fts); rate_all.append(rate); ivh_all.append(ivh_raw)
        offs.append(offs[-1] + len(fts))
    with open("/tmp/funding_span_table.json", "w") as fh:
        json.dump(dict(source="data/wide/*_funding.csv (server, full history)",
                       rule="span = max(2, round(24 / median(interval_h over FULL history)))",
                       shared_by="funding leg (normfix) AND 32ch DL panel (as-trained)",
                       n_symbols=len(tab), table=tab), fh, indent=1, sort_keys=True)
    np.savez_compressed("/tmp/funding_raw.npz",
                        symbols=np.array(sym_list, dtype=object),
                        offsets=np.array(offs, np.int64),
                        fundingTime_ms=np.concatenate(fts_all),
                        fundingRate=np.concatenate(rate_all),
                        interval_h_raw=np.concatenate(ivh_all))
    nmig = sum(1 for v in tab.values() if v["migrations"])
    print(f"[span] {len(tab)} symbols, {nmig} with >=1 interval migration, "
          f"{sum(len(x) for x in [v['migrations'] for v in tab.values()])} migration events", flush=True)
    return tab


def interval_in_force(ts, symbols, tab, raw):
    """IH(T,N): settlement interval in force at each hourly stamp (causal ffill), assert-script rule."""
    T, N = len(ts), len(symbols)
    IH = np.full((T, N), np.nan)
    sym_idx = {s: i for i, s in enumerate(raw["symbols"])}
    offs = raw["offsets"]
    for j, s in enumerate(symbols):
        if s not in sym_idx:
            continue
        k = sym_idx[s]
        sl = slice(int(offs[k]), int(offs[k + 1]))
        iv = raw["interval_h_raw"][sl]; fts = raw["fundingTime_ms"][sl]
        ok = np.isfinite(iv) & (iv > 0)
        if ok.sum() < 3:
            continue
        idx = np.searchsorted(fts[ok], ts, side="right") - 1
        g = idx >= 0
        IH[g, j] = iv[ok][idx[g]]
    return IH


# ------------------------------------------------------------------ 2. which panel is as-trained
def rank_centred(x):
    from scipy.stats import rankdata
    r = rankdata(x); k = len(r)
    return 2.0 * (r - 1) / (k - 1) - 1.0 if k > 1 else np.zeros_like(x)


def gap_report(panels, raw):
    out = {}
    for name, path in panels.items():
        z = np.load(path, allow_pickle=True)
        ts = z["ts"].astype(np.int64); symbols = [str(s) for s in z["symbols"]]
        ch = [str(c) for c in z["ch_names"]]; mem = z["MEMBER110"]
        IH = interval_in_force(ts, symbols, None, raw)
        res = {}
        for c in ("funding_ema", "xsr_fund"):
            X = z["CH"][:, :, ch.index(c)].astype(np.float64)
            acc = []
            for t in np.where(mem.any(1))[0][::4]:
                v = np.where(mem[t] & np.isfinite(IH[t]))[0]
                if v.size < 20:
                    continue
                is4 = IH[t, v] <= 4.0
                x = X[t, v]; f = np.isfinite(x)
                if (f & is4).sum() < 3 or (f & ~is4).sum() < 3:
                    continue
                zc = np.full(len(x), np.nan); zc[f] = rank_centred(x[f])
                acc.append(float(np.nanmean(zc[is4]) - np.nanmean(zc[~is4])))
            a = np.array(acc)[np.isfinite(acc)]
            res[c] = dict(mean_gap=round(float(a.mean()), 4), n_anchors=int(a.size))
            del X
        out[name] = dict(path=path, **res)
        print(f"[gap] {name:22s} funding_ema {res['funding_ema']['mean_gap']:+.4f}  "
              f"xsr_fund {res['xsr_fund']['mean_gap']:+.4f}", flush=True)
        del z; gc.collect()
    with open("/tmp/funding_gap_report.json", "w") as fh:
        json.dump(out, fh, indent=1)
    return out


# ------------------------------------------------------------------ 3. extended parity fixture
def fixture(tab, raw):
    import torch
    torch.backends.mkldnn.enabled = False
    import multi_asset.train.train_wide_harness as th
    th.DEV = torch.device("cpu")
    from multi_asset.data.wide_panel_dataset import WidePanelData
    from multi_asset.model.wide_harness import WideFactorModel, ConformerPanelEncoder

    PANEL = MA + "/exports/live/wide_dl_live.npz"
    SPECS = {"king": (MA + "/exports/train/wideA_lamorth0_xattn_5yr/fold_4_model.pt", 4, 8),
             "s2": (MA + "/exports/train/wideA_s2_y24_5yr/fold_4_model.pt", 24, 10)}

    def build_model(ckpt):
        m = WideFactorModel(ConformerPanelEncoder(32, d=64, n_blocks=2, kernel_size=15, dropout=0.2),
                            n_factor_heads=6, xattn=True, n_xattn=1, dropout=0.2)
        m.load_state_dict(torch.load(ckpt, map_location="cpu"), strict=True)
        m.eval()
        return m

    def composite(sc, base):
        comp = np.zeros(base.size); nk = 0
        for k in range(sc.shape[1]):
            col = sc[base, k]
            if np.isfinite(col).all() and col.std() > 1e-12:
                comp += (col - col.mean()) / col.std(); nk += 1
        return comp / nk if nk else None

    # ★ the two horizons may TRIM the panel differently (Y needs h forward rows), so validity is
    # collected in TIMESTAMP space, not index space -- indices are not comparable across horizons.
    stats, valid_ts = {}, {}
    keep = None
    for name, (ckpt, horizon, emb) in SPECS.items():
        d = WidePanelData(path=PANEL, target_horizon=horizon)
        folds = th.year_folds(d, embargo_days=emb, val_days=30)
        d.set_fold(folds[4]["tr"])
        stats[name] = (d.mu.copy(), d.sd.copy())
        CL = getattr(d, "CL", np.ones_like(d.member))
        v = (d.member & CL).any(1)
        v[:W - 1] = False
        valid_ts[name] = set(int(x) for x in np.asarray(d.ts)[v])
        print(f"[fixture] {name}: T={len(d.ts)} valid_anchors={v.sum()} mu{tuple(d.mu.shape)}", flush=True)
        if keep is None:               # windows come from ONE panel; both models share them
            keep = d
        else:
            del d; gc.collect()
    data = keep
    ts = np.asarray(data.ts).astype(np.int64)
    ok = np.array([int(t) in valid_ts["king"] and int(t) in valid_ts["s2"] for t in ts])
    cand = np.where(ok)[0]
    cal = pd.to_datetime(ts, unit="ms", utc=True)

    picks = {}
    for y in sorted(set(cal.year[cand])):                       # >=1 anchor per calendar year
        inyr = cand[cal.year[cand] == y]
        mid = pd.Timestamp(f"{y}-07-01", tz="UTC").value // 1_000_000
        picks[f"year_{y}"] = int(inyr[np.argmin(np.abs(ts[inyr] - mid))])
    msum = data.member.sum(1)
    picks["sparsest_mask"] = int(cand[np.argmin(msum[cand])])

    _hdr = np.load(PANEL, allow_pickle=True)          # lazy: only the two tiny header arrays
    symbols = [str(s) for s in _hdr["symbols"]]
    ch_names = [str(c) for c in _hdr["ch_names"]]
    assert len(symbols) == data.CH.shape[1] and len(ch_names) == data.CH.shape[2]
    IH = interval_in_force(ts, symbols, tab, raw)
    is4 = (IH <= 4.0) & np.isfinite(IH)
    n4 = (is4 & data.member).sum(1)
    jump = np.abs(np.diff(n4, prepend=n4[0]))
    picks["migration_wave"] = int(cand[np.argmax(jump[cand])])
    inwin = np.array([int(((jump[max(0, t - W + 1):t + 1]) > 0).sum()) for t in cand])
    picks["migration_dense_window"] = int(cand[np.argmax(inwin)])
    picks["recent"] = int(cand[-1])

    anchors = sorted(set(picks.values()))
    kinds = {a: "+".join(sorted(k for k, v in picks.items() if v == a)) for a in anchors}
    print(f"[fixture] {len(anchors)} anchors: " +
          ", ".join(f"{kinds[a]}@{cal[a].date()}(mem={msum[a]},n4={n4[a]})" for a in anchors), flush=True)

    wins, masks = [], []
    for t in anchors:
        widx = t + np.arange(-W + 1, 1)
        wins.append(data.CH[widx].transpose(1, 0, 2).astype(np.float32))
        masks.append(data.member[t].astype(np.float32))
    Wn = np.stack(wins); Mk = np.stack(masks)

    out = dict(windows=Wn, masks=Mk,
               anchor_idx=np.array(anchors, np.int64), anchor_ts=ts[anchors],
               anchor_kind=np.array([kinds[a] for a in anchors], dtype=object),
               anchor_n4=np.array([int(n4[a]) for a in anchors], np.int64),
               symbols=np.array(symbols, dtype=object),
               ch_names=np.array(ch_names, dtype=object))
    meta = {}
    for name, (ckpt, horizon, emb) in SPECS.items():
        mu, sd = stats[name]
        model = build_model(ckpt)
        out[f"{name}_mu"] = mu; out[f"{name}_sd"] = sd
        for i, t in enumerate(anchors):
            Xn = np.clip((np.nan_to_num(Wn[i][None]) - mu) / sd, -10, 10).astype(np.float32)
            with torch.no_grad():
                sc = model(torch.from_numpy(Xn), torch.from_numpy(Mk[i][None]))["factor_scores"][0].numpy()
            base = np.where(data.member[t])[0]
            out[f"{name}_composite_{i}"] = composite(sc, base).astype(np.float64)
            out[f"{name}_base_{i}"] = base.astype(np.int32)
        meta[name] = dict(ckpt=ckpt, horizon=horizon, embargo=emb, mu_shape=list(mu.shape),
                          torch=torch.__version__, numpy=np.__version__, pandas=pd.__version__)
    out["meta_json"] = np.array(json.dumps(dict(models=meta, panel=PANEL, W=W,
                                                anchor_kinds=list(kinds.values()))), dtype=object)
    np.savez_compressed("/tmp/parity_fixture_v2.npz", **out)
    print(f"[fixture] wrote /tmp/parity_fixture_v2.npz  windows={Wn.shape}", flush=True)

    # migration-era funding slice: the two funding channels + FUND_EMA around the biggest wave
    t0 = max(0, picks["migration_wave"] - 360); t1 = min(len(ts), picks["migration_wave"] + 360)
    ci = {c: i for i, c in enumerate(ch_names)}
    np.savez_compressed("/tmp/panel_fund_slice.npz", ts=ts[t0:t1],
                        symbols=np.array(symbols, dtype=object),
                        MEMBER=data.member[t0:t1],
                        IH=IH[t0:t1].astype(np.float32),
                        CH_funding_ema=data.CH[t0:t1, :, ci["funding_ema"]].astype(np.float32),
                        CH_xsr_fund=data.CH[t0:t1, :, ci["xsr_fund"]].astype(np.float32))
    print(f"[fixture] wrote /tmp/panel_fund_slice.npz rows={t1 - t0} "
          f"({cal[t0].date()}..{cal[t1 - 1].date()})", flush=True)


tab = span_table()
raw = dict(np.load("/tmp/funding_raw.npz", allow_pickle=True))
gap_report({"live_as_trained": MA + "/exports/live/wide_dl_live.npz",
            "live_fundfix": MA + "/exports/live/wide_dl_live_fundfix.npz",
            "train_full": MA + "/exports/wide_dl_full.npz"}, raw)
fixture(tab, raw)
print("[done]", flush=True)
