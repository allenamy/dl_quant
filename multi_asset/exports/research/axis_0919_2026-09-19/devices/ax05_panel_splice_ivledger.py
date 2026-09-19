"""AX05 (axis_0919, stream D) = r6_panel_splice.py (sha cccc5b6b) with THREE patches, everything else byte-identical (diff recorded in receipts):
  P1 paths: the September REST pull (R6_FUND_SEP) is replaced by this round's pull AX_REST (rows with settlement second <= AX_HI_S only); receipt/state
     paths follow R6_PANEL_OUT / EMA_STATE_JSON (new root). No default points at an existing output.
  P2 interval defect (memory x0910_fund_iv_interval_mismatch): REST rows enter the event stream with iv = NaN (never the fetch-time fundingInfo value),
     and for every event with ft > cut - 24h the interval is the AX04 LEDGER interval at that settlement (T5d rule: producer ledger == snapped gap);
     an event in that range that the ledger does not hold => hard FAIL. Events <= cut - 24h keep r6's iv_full (no tail cell uses them; T5d).
  P3 the event rate must equal the ledger rate for every event in the ledger window (reported; FAIL if any differs).
Original docstring follows.
R6 EXTEND step 4a: extend a v4 4h panel forward by 60 anchors, using the ESTABLISHED v4 mechanism
(pod_panel_splice.py 'v3splice + canoncont'): prefix copied VERBATIM (so GATE BW-2 holds by construction and is
then verified on the written file), tail kline columns taken from a fresh pod_panel_ext.py build on the EXTENDED
cache, tail funding EMAs CONTINUED from the base panel's last row using the funding event stream.

Why the funding tail is recomputed instead of taken from the fresh build: pod_panel_ext.py reads its funding from
/workspace/wide_multisrc/funding/*.zip + /workspace/fund_aug.json.gz, whose coverage ends 2026-09-01 02:00Z, so its
own September rows would be >12h stale and NaN'd by its L160 staleness rule — the very defect (E-0911-B) this round
exists to stop reproducing. September funding comes from r6_fund_sep.json.gz (public REST; vision has no 2026-09
monthly and no daily fundingRate, both VERIFIED 404).

EMA algebra (v0 wall-clock HL3d raw rate / v1 wall-clock HL3d normfix / v2 settlement-space adjust=False span) is
copied VERBATIM from pod_panel_splice.py L83-L102; interval derivation from L69-L74.
"""
import os, io, csv, json, glob, gzip, zipfile, time, hashlib, sys
import numpy as np

ENV_WL = ["R6_BASE_PANEL", "R6_RAWBUILD", "R6_PANEL_OUT", "AX_REST", "AX_LEDGER", "AX_HI_S", "EMA_STATE_JSON", "EXPORT_PANEL"]
ENV_EFF = {k: os.environ.get(k) for k in ENV_WL}
BASEP = os.environ["R6_BASE_PANEL"]          # wide_panel_4h_v2ext.npz  |  wide_panel_4h_v3splice.npz
RAWB  = os.environ["R6_RAWBUILD"]            # fresh pod_panel_ext.py build on the extended cache
OUTP  = os.environ["R6_PANEL_OUT"]
FSEP  = os.environ["AX_REST"]                # P1: this round's REST pull (ax02), no default
LEDP  = os.environ["AX_LEDGER"]              # P2: per-settlement ledger (ax04)
HI_S  = int(os.environ["AX_HI_S"])           # P1: last settlement second admitted
STATE = os.environ["EMA_STATE_JSON"]
for _p in (OUTP, STATE, OUTP.replace(".npz", "_RECEIPT.json")): assert not os.path.exists(_p), f"refuse to overwrite {_p}"
AUGP  = "/workspace/fund_aug.json.gz"
FDIR  = "/workspace/wide_multisrc/funding"
RPT   = OUTP.replace(".npz", "_RECEIPT.json")
HL = 3 * 86400.0
ALLOWED = np.array([1.0, 2.0, 4.0, 6.0, 8.0])

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()
def U(t): return time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))

CAN = np.load(BASEP, allow_pickle=True); EXT = np.load(RAWB, allow_pickle=True)
syms = [str(s) for s in CAN["symbols"]]
assert syms == [str(s) for s in EXT["symbols"]], "symbol axis mismatch base vs rawbuild"
ct = CAN["ts"].astype(np.int64); et = EXT["ts"].astype(np.int64)
cut = int(ct[-1]); tail_idx = np.where(et > cut)[0]; tail_ts = et[tail_idx]; nC = len(ct)
print(f"base {os.path.basename(BASEP)} n={nC} cut={U(cut)} | rawbuild n={len(et)} end={U(et[-1])} | tail {len(tail_idx)} anchors {U(tail_ts[0])}..{U(tail_ts[-1])}", flush=True)
keys = sorted((set(CAN.files) & set(EXT.files)) - {"ts", "symbols"})
out = {"ts": np.concatenate([ct, tail_ts]), "symbols": np.array(syms)}
carried, prefix_only = [], []
for k in keys:
    a = CAN[k]; b = EXT[k]
    if a.ndim == 2 and a.shape[1] == len(syms):
        out[k] = np.concatenate([a, b[tail_idx]]); carried.append(k)
    else:
        out[k] = a; prefix_only.append(k)          # VERBATIM pod_panel_splice.py L27 policy
for k in set(CAN.files) - set(out) - {"ts", "symbols"}:
    out[k] = CAN[k]; prefix_only.append(k)
print(f"tail-extended keys {len(carried)}: {carried}\nprefix-only keys {sorted(set(prefix_only))}", flush=True)

# ---- funding event stream: zips + fund_aug + R6 September REST ----
AUG = json.loads(gzip.open(AUGP, "rt").read()); AUG_IV = {k: float(v) for k, v in (AUG.get("intervals") or {}).items() if v}
_REST = json.loads(gzip.open(FSEP, "rt").read())                       # P1: ax02 format -> r6 shape {"rates": {sym: [[t_ms, rate]]}}
SEP = {"rates": {s: [[int(r["fundingTime"]), float(r["fundingRate"])] for r in (v or []) if int(r["fundingTime"]) // 1000 <= HI_S]
                 for s, v in _REST["rates_raw"].items()}, "meta": _REST["meta"]}
SEP_IV = {}                                                              # P2: NO fetch-time interval enters the stream
_L = np.load(LEDP, allow_pickle=True); _Lsym = [str(x) for x in _L["symbols"]]; assert _Lsym == syms, "ledger symbol axis"
LED = {}
for _j, _t, _r, _iv in zip(_L["sym"].astype(int), _L["ts"].astype(np.int64), _L["rate"], _L["iv"]):
    LED.setdefault(_j, {})[int(_t)] = (float(_r), float(_iv))
LED_LO = int(_L["window"][0])
P2 = {"events_ledger_iv": 0, "events_iv_changed_vs_r6_rule": 0, "symbols_iv_changed": [], "events_missing_in_ledger": [], "rate_mismatch_vs_ledger": []}
print(f"fund_aug syms {len(AUG.get('rates') or {})} | ax02 REST syms {len(SEP.get('rates') or {})} meta {SEP.get('meta',{}).get('max_utc')} | ledger rows {len(_L['ts'])}", flush=True)
state = {}; n_cont = 0; n_noseed = 0; n_tail_events = 0
for j, s in enumerate(syms):
    rows = []
    for zp in sorted(glob.glob(f"{FDIR}/{s}/*.zip")):
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                for row in csv.reader(io.TextIOWrapper(fh)):
                    if not row or not row[0].strip().isdigit() and "time" in row[0].lower(): continue
                    try:
                        ts_ = int(row[0]); rate = float(row[-1]) if abs(float(row[-1])) < 0.2 else float(row[1])
                        iv = np.nan
                        if len(row) >= 3:
                            try:
                                cand = float(row[1])
                                if 1 <= cand <= 24 and abs(cand - round(cand)) < 1e-9 and abs(float(row[-1])) < 0.2: iv = cand
                            except Exception: pass
                        rows.append((ts_ // 1000, rate, iv))
                    except Exception: continue
        except Exception: continue
    for t_ms, rate in (AUG.get("rates") or {}).get(s, []): rows.append((int(t_ms)//1000, float(rate), AUG_IV.get(s, np.nan)))
    for t_ms, rate in (SEP.get("rates") or {}).get(s, []): rows.append((int(t_ms)//1000, float(rate), SEP_IV.get(s, np.nan)))
    if not rows: continue
    rows.sort(); ded = {}
    for t_, r_, i_ in rows:
        if t_ not in ded or np.isfinite(i_): ded[t_] = (r_, i_)
    ft = np.array(sorted(ded), np.int64); fr = np.array([ded[t][0] for t in ft]); fiv = np.array([ded[t][1] for t in ft])
    dt_h = np.round(np.diff(ft) / 3600.0)
    dv = np.full(len(ft), np.nan); dv[1:] = np.where((dt_h > 0) & (dt_h <= 24), dt_h, np.nan)
    iv_full = np.where(np.isfinite(fiv), fiv, dv); iv_full = np.where(np.isfinite(iv_full), iv_full, 8.0)
    iv_full = ALLOWED[np.argmin(np.abs(iv_full[:, None] - ALLOWED[None, :]), axis=1)]
    # ---- P2/P3: ledger interval (and rate check) for every event with ft > cut - 24h
    _led = LED.get(j, {}); _r6iv = iv_full.copy(); _chg = 0
    for _i in np.nonzero(ft > cut - 24 * 3600)[0]:
        _t = int(ft[_i])
        if _t < LED_LO: continue
        _e = _led.get(_t)
        if _e is None: P2["events_missing_in_ledger"].append((s, U(_t))); continue
        if _e[0] != float(fr[_i]): P2["rate_mismatch_vs_ledger"].append((s, U(_t), float(fr[_i]), _e[0]))
        iv_full[_i] = _e[1]; P2["events_ledger_iv"] += 1
        if _e[1] != _r6iv[_i]: _chg += 1
    if _chg: P2["events_iv_changed_vs_r6_rule"] += _chg; P2["symbols_iv_changed"].append(s)
    rate_nf = fr * (8.0 / iv_full)
    sel = ft > cut
    # f_fund_now / f_fund_iv on the tail: last event at or before the anchor, 12h staleness rule (pod_panel_ext.py L153-162)
    pos = np.searchsorted(ft, tail_ts, side="right") - 1; okp = pos >= 0
    fn = np.full(len(tail_ts), np.nan); fi = np.full(len(tail_ts), np.nan)
    fn[okp] = fr[pos[okp]]; fi[okp] = iv_full[pos[okp]]
    stale = okp & ((tail_ts - np.where(okp, ft[np.maximum(pos, 0)], 0)) > 12*3600)
    fn[stale] = np.nan; fi[stale] = np.nan
    out["f_fund_now"][nC:, j] = fn.astype(np.float32); out["f_fund_iv"][nC:, j] = fi.astype(np.float32)
    seeds = {nm: (float(CAN[col][-1, j]) if np.isfinite(CAN[col][-1, j]) else None)
             for nm, col in (("v0","f_fund_ema"), ("v1","f_fund_ema_v1"), ("v2","f_fund_ema_v2"))}
    if seeds["v1"] is None:
        n_noseed += 1; continue                        # VERBATIM L79-80: no canonical history to continue
    n_cont += 1; n_tail_events += int(sel.sum())
    e0, e1, e2 = seeds["v0"], seeds["v1"], seeds["v2"]; prev_t = cut
    ivm = np.median(iv_full[sel]) if sel.any() else 8.0
    span = max(2, round(24 / ivm)); al2 = 2.0 / (span + 1.0)
    ptr = np.where(sel)[0]; k2 = 0
    for r_row, t_anchor in enumerate(tail_ts):
        while k2 < len(ptr) and ft[ptr[k2]] <= t_anchor:
            i_ = ptr[k2]
            a = 1 - 0.5 ** (max(ft[i_] - prev_t, 1) / HL)
            e0 = e0 + a * (fr[i_] - e0); e1 = e1 + a * (rate_nf[i_] - e1)
            e2 = e2 + al2 * (rate_nf[i_] - e2) if e2 is not None else rate_nf[i_]
            prev_t = ft[i_]; k2 += 1
        r = nC + r_row
        out["f_fund_ema"][r, j] = np.float32(e0); out["f_fund_ema_v1"][r, j] = np.float32(e1)
        if e2 is not None: out["f_fund_ema_v2"][r, j] = np.float32(e2)
    state[s] = {"acc": float(e1), "last_ts": int(prev_t)}

# ---- P2/P3 hard gates ----
print("P2", json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in P2.items()}), flush=True)
assert not P2["events_missing_in_ledger"], ("P2 FAIL: tail events absent from the ledger", P2["events_missing_in_ledger"][:10])
assert not P2["rate_mismatch_vs_ledger"], ("P3 FAIL: event rate != ledger rate", P2["rate_mismatch_vs_ledger"][:10])
# ---- assertions (VERBATIM pod_panel_splice.py L106-114, plus the full-prefix BW-2 statement) ----
chk = {}
for col in ("f_fund_ema", "f_fund_ema_v1", "f_fund_ema_v2"):
    va = CAN[col][-1]; vb = out[col][nC-1]; ok = np.isfinite(va)
    assert np.array_equal(va[ok], vb[ok]), f"cut row {col} changed"
    chk[f"cut_row_{col}_equal"] = True
for col in ("f_rev_24h", "f_mom_7d", "f_vol_7d"):
    va = EXT[col][tail_idx]; vb = out[col][nC:]; ok = np.isfinite(va)
    assert np.array_equal(va[ok], vb[ok]), f"tail {col} != rawbuild"
    chk[f"tail_{col}_equals_rawbuild"] = True
bw2 = {}
for k in sorted(set(CAN.files) - {"symbols"}):
    a = CAN[k]; b = out[k][:len(a)] if (hasattr(out[k], "ndim") and out[k].ndim >= 1 and len(out[k]) >= len(a)) else out[k]
    bw2[k] = bool(np.array_equal(a, b, equal_nan=True) if a.dtype.kind == "f" else np.array_equal(a, b))
chk["BW2_prefix_all_keys_bitwise_equal"] = bool(all(bw2.values()))
chk["BW2_per_key"] = bw2
chk["BW2_prefix_rows"] = int(nC)
print("BW-2 prefix bitwise equal per key:", json.dumps(bw2), flush=True)
assert chk["BW2_prefix_all_keys_bitwise_equal"], "BW-2 RED: extension changed a pre-existing panel cell"

# X4 on the new tail: members-proxy = all symbols with a finite kline factor this anchor
x4 = []
for r_row, t_anchor in enumerate(tail_ts):
    r = nC + r_row; live = np.isfinite(out["f_rev_24h"][r])
    fe = np.isfinite(out["f_fund_ema"][r]) & live
    x4.append({"anchor": U(t_anchor), "live_names": int(live.sum()), "fund_ema_finite": int(fe.sum()),
               "frac": round(float(fe.sum()/max(live.sum(),1)), 4)})
json.dump(state, open(STATE, "w"), indent=0)
np.savez_compressed(OUTP, **out)
rep = {"self_sha256": sha(os.path.abspath(__file__)), "env_effective": ENV_EFF,
       "base_panel": BASEP, "base_sha256": sha(BASEP), "base_n": nC, "base_end": U(cut),
       "rawbuild": RAWB, "rawbuild_sha256": sha(RAWB), "rawbuild_n": int(len(et)),
       "fund_sep": FSEP, "fund_sep_sha256": sha(FSEP), "fund_sep_meta": SEP.get("meta"),
       "ledger": LEDP, "ledger_sha256": sha(LEDP), "hi_s": HI_S, "P2_P3": {k: (v if not isinstance(v, list) else {"n": len(v), "first": v[:40]}) for k, v in P2.items()},
       "out": OUTP, "out_sha256": sha(OUTP), "out_n": int(len(out["ts"])), "out_end": U(out["ts"][-1]),
       "tail_anchors": int(len(tail_ts)), "tail_first": U(tail_ts[0]), "tail_last": U(tail_ts[-1]),
       "keys_tail_extended": carried, "keys_prefix_only": sorted(set(prefix_only)),
       "ema_continued_symbols": n_cont, "ema_unseeded_symbols": n_noseed, "tail_funding_events": n_tail_events,
       "checks": chk, "X4_tail": x4, "ema_state_json": STATE,
       "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
json.dump(rep, open(RPT, "w"), indent=1)
print(f"R6_PANEL_SPLICE_DONE n={rep['out_n']} end={rep['out_end']} cont={n_cont} noseed={n_noseed} sha={rep['out_sha256'][:16]}", flush=True)
print("X4 tail frac min/median:", round(min(x["frac"] for x in x4),4), round(float(np.median([x["frac"] for x in x4])),4), flush=True)
