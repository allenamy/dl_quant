#!/usr/bin/env python3
"""ad_tradability.py -- AUDIT_DATA 2026-09-13, device H (pod2, CPU, READ-ONLY). Tradability by trades, not by closes (L4b lesson).

L4b (commit 30dc6eb2) verified on raw 1m archives: after a Binance perp stops trading the kline archive keeps writing untraded rows with one
frozen close, and fund_aug keeps funding records for some dead perps (MDT 1,197 events). A flag built from close presence or funding presence
marks dead contracts as live. This device measures the same failure mode in the research data layer.

Definitions (5m cache dlnative_5m_wide829_f16_holefix2.npz; channels ret5=0, log_qv=3, log_cnt=4 with log_cnt = log1p(number_of_trades)):
  traded bar     = finite ret5 and log_cnt > 0           untraded bar = finite ret5 and log_cnt == 0
  last_traded[s] = last traded row of symbol s in the cache
  DEAD at E      = E_row > last_traded[s] and last_traded[s] < TT-1-288   (never trades again inside the cache; descriptive, NOT causal)
  Z24 at E       = the trailing 288 rows [E-287, E] contain >= 1 finite ret5 row and 0 traded rows   (untradable at decision time; causal)
H1  cache: untraded rows after last_traded (post-death rows): count, frozen-close signature (ret5 == 0 exactly, log_qv == 0, cpos/tbf NaN),
    per year and top symbols; zero-trade runs >= 288 rows; x0910 tail rows (streamed) for names already dead before 2026-09-01.
H2  A0 population (r3k A0_PWR230k_s{42,2027}: MEMBERS_TOPN=829 => universe = finite qvk of meta_newprod_v4 ∩ CRYPTO m1 mask row; sel = isfinite(y4)
    & expm1(clip(qvk,0,30))*48 >= 2.5e5): per year, member-anchors in U that are Z24 / DEAD, of which sel, of which held (|W|>1e-12), their |W|,
    share with accounting y4 exactly 0, the price and carry the replay books on them (W*y4, W*f_fund_now*4/iv from wide_panel_4h_v2ext).
    Positive control (reported): held names outside U (smoothing carry-over) per year.
H3  fund leg rank base (w10 FZB: rank over every finite v2ext f_fund_ema_v1 on the panel row): DEAD / Z24 names inside it per anchor.
H4  training/meta rows: king meta members, DL targets members that are Z24 / DEAD; their labels exactly 0 (meta y4 / dlw y4s).
H5  funding records after death: settlement events (zips ∪ fund_aug ∪ r6_fund_sep, union by second) after ts[last_traded]+1h, per symbol / source / year;
    v2ext cells with finite f_fund_now on DEAD cells; P2 base proxy (P2 ledger_full.npz: >= 1 settlement in (A-24h, A]) names that are DEAD at A.
H6  panel `elig` (pod_panel_ext.py L40: covr & v7) True on Z24 / DEAD cells.
Usage: python3 ad_tradability.py <out_receipt.json>
"""
import os, sys, io, csv, json, glob, gzip, zipfile, time, hashlib, calendar
from multiprocessing import Pool
import numpy as np

ENV_WHITELIST = set()
os.nice(19)
OUT = sys.argv[1]
W = "/workspace"
CACHE = f"{W}/data/dlnative_5m_wide829_f16_holefix2.npz"; CACHE_X = f"{W}/data/dlnative_5m_wide829_f16_holefix2_x0910.npz"
AMETA = f"{W}/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz"; DTG = f"{W}/dlw_v4raw/data/dlw_targets.npz"
UMASK = f"{W}/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz"; PANEL = f"{W}/data/wide_panel_4h_v2ext.npz"
A0 = {s: f"{W}/uplift_2026-09-11/r3k/arms/A0_PWR230k_s{s}.npz" for s in (42, 2027)}
FDIR = f"{W}/wide_multisrc/funding"; AUGP = f"{W}/fund_aug.json.gz"; SEPP = f"{W}/uplift_2026-09-11/r6/dl/r6_fund_sep.json.gz"
LEDGER = f"{W}/uplift_r2_2026-09-13/P2/work/ledger_full.npz"
T0 = time.time()
def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))
def yr(t): return time.gmtime(int(t)).tm_year
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
def log(*a): print("[%6.0fs]" % (time.time() - T0), *a, flush=True)
assert not (ENV_WHITELIST - set(os.environ))
rec = {"device": "ad_tradability.py", "self_sha256": sha(os.path.abspath(__file__)), "numpy": np.__version__,
       "inputs": {p: sha(p) for p in [CACHE, AMETA, DTG, UMASK, PANEL, AUGP, SEPP, LEDGER] + list(A0.values())}}
log("input shas")

# ---------------- H1 cache ----------------
Z = np.load(CACHE, allow_pickle=True); CTS = Z["ts"].astype(np.int64); syms = [str(s) for s in Z["symbols"]]; ch = [str(c) for c in Z["ch"]]
assert ch[0] == "ret5" and ch[3] == "log_qv" and ch[4] == "log_cnt" and ch[2] == "cpos" and ch[6] == "tbf", ch
DATA = Z["data"]; TT, NW = DATA.shape[0], DATA.shape[1]
R0 = np.ascontiguousarray(DATA[:, :, 0]); C4 = np.ascontiguousarray(DATA[:, :, 4])
fin = np.isfinite(R0); traded = fin & (C4 > 0); untr = fin & (C4 == 0)
cnt_nan_but_ret_finite = int((fin & ~np.isfinite(C4)).sum())
has_tr = traded.any(0); last_tr = np.where(has_tr, TT - 1 - np.argmax(traded[::-1], 0), -1)
dead_sym = has_tr & (last_tr < TT - 1 - 288)
rows_idx = np.arange(TT)
post = untr & (rows_idx[:, None] > last_tr[None, :]) & dead_sym[None, :]
pr, pc = np.where(post)
sig = {"post_death_untraded_rows": int(len(pr)),
       "ret5_exactly_0": int((R0[pr, pc] == 0).sum()),
       "log_qv_exactly_0": int((DATA[pr, pc, 3] == 0).sum()),
       "cpos_nan": int((~np.isfinite(DATA[pr, pc, 2])).sum()), "tbf_nan": int((~np.isfinite(DATA[pr, pc, 6])).sum())}
del DATA, Z
by_sym = {}
cnt_by_sym = np.bincount(pc, minlength=NW)
for j in np.where(cnt_by_sym > 0)[0]:
    k = int(cnt_by_sym[j]); by_sym[syms[j]] = {"post_death_rows": k, "last_traded_bar_close": utc(CTS[last_tr[j]]), "days": round(k / 288.0, 1)}
yr_rows = {}
for y in range(2022, 2027):
    lo = np.searchsorted(CTS, calendar.timegm((y, 1, 1, 0, 0, 0))); hi = np.searchsorted(CTS, calendar.timegm((y + 1, 1, 1, 0, 0, 0)))
    s_ = (pr >= lo) & (pr < hi); yr_rows[str(y)] = {"rows": int(s_.sum()), "symbols": int(len(np.unique(pc[s_])))}
# zero-trade runs >= 288 rows (24 h), per symbol, resumed or not
runs = {"n_runs_ge_288": 0, "rows_in_runs": 0, "runs_resumed": 0, "runs_never_resumed": 0}
for j in range(NW):
    u = untr[:, j]
    if not u.any(): continue
    d = np.diff(np.concatenate([[0], u.astype(np.int8), [0]])); st = np.where(d == 1)[0]; en = np.where(d == -1)[0]
    L = en - st; big = L >= 288
    runs["n_runs_ge_288"] += int(big.sum()); runs["rows_in_runs"] += int(L[big].sum())
    for a, b in zip(st[big], en[big]):
        if traded[b:, j].any(): runs["runs_resumed"] += 1
        else: runs["runs_never_resumed"] += 1
rec["H1_cache"] = {"TT": int(TT), "cache_end": utc(CTS[-1]), "ret_finite_but_log_cnt_nan_cells": cnt_nan_but_ret_finite,
                   "symbols_with_trades": int(has_tr.sum()), "symbols_dead_inside_cache": int(dead_sym.sum()),
                   "post_death_signature": sig, "post_death_rows_by_year": yr_rows, "zero_trade_runs_ge_24h": runs,
                   "top_symbols_post_death_rows": dict(sorted(by_sym.items(), key=lambda kv: -kv[1]["post_death_rows"])[:40])}
log("H1", json.dumps(sig), json.dumps(yr_rows))
# x0910 tail streamed: ret5 / log_cnt of rows >= TT
def stream_tail(path, first_row, chans):
    zf = zipfile.ZipFile(path)
    with zf.open("data.npy") as fh:
        ver = np.lib.format.read_magic(fh)
        shape, fort, dt = (np.lib.format.read_array_header_1_0(fh) if ver == (1, 0) else np.lib.format.read_array_header_2_0(fh))
        rowb = int(np.prod(shape[1:])) * dt.itemsize; skip = first_row * rowb
        while skip > 0:
            n = min(skip, 1 << 28); got = fh.read(n); assert len(got) == n; skip -= n
        tail = np.frombuffer(fh.read((shape[0] - first_row) * rowb), dtype=dt).reshape((shape[0] - first_row,) + tuple(shape[1:]))
    return np.ascontiguousarray(tail[:, :, chans])
tail = stream_tail(CACHE_X, TT, [0, 4]); tfin = np.isfinite(tail[:, :, 0]); ttr = tfin & (tail[:, :, 1] > 0); tun = tfin & (tail[:, :, 1] == 0)
dead_before_tail = dead_sym & ~ttr.any(0)
rec["H1_x0910_tail"] = {"tail_rows": int(tail.shape[0]), "symbols_dead_before_2026-09-01_still_writing_untraded_rows": int((dead_before_tail & tun.any(0)).sum()),
                        "untraded_rows_of_those": int(tun[:, dead_before_tail].sum()), "ret5_exactly_0_of_those": int((tail[:, dead_before_tail, 0][tun[:, dead_before_tail]] == 0).sum()),
                        "names": [syms[j] for j in np.where(dead_before_tail & tun.any(0))[0]][:30]}
del tail
log("H1 tail", json.dumps(rec["H1_x0910_tail"])[:300])

# ---------------- anchor-level flags ----------------
AM = np.load(AMETA, allow_pickle=True); aE = AM["E_ts"].astype(np.int64); aMem = AM["members"]; aY4 = AM["y4"]; aQ = AM["qvk"]
arow = np.searchsorted(CTS, aE); assert np.array_equal(CTS[arow], aE)
def cs_rows(flag, idx):
    out = np.empty((TT + 1, NW), np.int32); out[0] = 0; np.cumsum(flag, axis=0, dtype=np.int32, out=out[1:]); g = out[idx]; del out; return g
hiE = arow + 1; loE = np.maximum(arow + 1 - 288, 0)
TRc = cs_rows(traded, np.concatenate([hiE, loE])); n = len(aE); tr24 = TRc[:n] - TRc[n:]; del TRc
FIc = cs_rows(fin, np.concatenate([hiE, loE])); fi24 = FIc[:n] - FIc[n:]; del FIc
Z24 = (fi24 > 0) & (tr24 == 0)
DEAD = (arow[:, None] > last_tr[None, :]) & dead_sym[None, :]
del traded, untr, fin, R0, C4
log("flags built", int(Z24.sum()), int(DEAD.sum()))
UZ = np.load(UMASK, allow_pickle=True); UTS = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}; UM = np.asarray(UZ["mask"])
P = np.load(PANEL, allow_pickle=True); pts = P["ts"].astype(np.int64); prow = {int(t): j for j, t in enumerate(pts)}
FN = np.asarray(P["f_fund_now"]).astype(np.float64); IV = np.asarray(P["f_fund_iv"]).astype(np.float64); FE1 = np.asarray(P["f_fund_ema_v1"]); ELIG = np.asarray(P["elig"])
apos = {int(t): i for i, t in enumerate(aE)}

# ---------------- H2 A0 population ----------------
h2 = {}
for s, pth in A0.items():
    Az = np.load(pth, allow_pickle=True); cols = [str(c) for c in Az["cols"]]; Wb = Az["W"].astype(np.float64); ats = Az["rec"][:, cols.index("ts")].astype(np.int64)
    by = {}
    for k, t in enumerate(ats):
        i = apos.get(int(t)); j = prow.get(int(t)); ur = UTS.get(int(t))
        if i is None or j is None: continue
        U = np.isfinite(aQ[i])
        if ur is not None: U = U & UM[ur]
        sel = np.isfinite(aY4[i]) & (np.expm1(np.clip(np.nan_to_num(aQ[i], nan=0.0), 0, 30)) * 48 >= 2.5e5)
        held = np.abs(Wb[k]) > 1e-12
        y = str(yr(t)); b = by.setdefault(y, {"anchors": 0, "U_pairs": 0, "U_Z24": 0, "U_DEAD": 0, "U_Z24_sel": 0, "U_DEAD_sel": 0, "held_pairs": 0,
                                             "held_Z24": 0, "held_DEAD": 0, "absW_total": 0.0, "absW_Z24": 0.0, "absW_DEAD": 0.0, "held_Z24_y4_exactly0": 0,
                                             "held_DEAD_y4_exactly0": 0, "price_bps_booked_on_Z24": 0.0, "carry_bps_booked_on_Z24": 0.0, "carry_bps_booked_on_DEAD": 0.0,
                                             "held_outside_U": 0, "anchors_with_held_Z24": 0})
        b["anchors"] += 1; b["U_pairs"] += int(U.sum()); b["U_Z24"] += int((U & Z24[i]).sum()); b["U_DEAD"] += int((U & DEAD[i]).sum())
        b["U_Z24_sel"] += int((U & Z24[i] & sel).sum()); b["U_DEAD_sel"] += int((U & DEAD[i] & sel).sum())
        b["held_pairs"] += int(held.sum()); b["held_outside_U"] += int((held & ~U).sum()); b["absW_total"] += float(np.abs(Wb[k]).sum())
        hz = held & Z24[i]; hd = held & DEAD[i]
        b["held_Z24"] += int(hz.sum()); b["held_DEAD"] += int(hd.sum()); b["anchors_with_held_Z24"] += int(hz.any())
        b["absW_Z24"] += float(np.abs(Wb[k, hz]).sum()); b["absW_DEAD"] += float(np.abs(Wb[k, hd]).sum())
        b["held_Z24_y4_exactly0"] += int((aY4[i, hz] == 0).sum()); b["held_DEAD_y4_exactly0"] += int((aY4[i, hd] == 0).sum())
        ivv = np.where(np.isfinite(IV[j]) & (IV[j] > 0), IV[j], 8.0); fnv = np.nan_to_num(FN[j], nan=0.0)
        b["price_bps_booked_on_Z24"] += float((Wb[k, hz] * np.nan_to_num(aY4[i, hz], nan=0.0)).sum() * 1e4)
        b["carry_bps_booked_on_Z24"] += float((Wb[k, hz] * fnv[hz] * (4.0 / ivv[hz])).sum() * 1e4)
        b["carry_bps_booked_on_DEAD"] += float((Wb[k, hd] * fnv[hd] * (4.0 / ivv[hd])).sum() * 1e4)
    for b in by.values():
        b["absW_Z24_share"] = b["absW_Z24"] / max(b["absW_total"], 1e-12); b["absW_DEAD_share"] = b["absW_DEAD"] / max(b["absW_total"], 1e-12)
    h2[s] = {"axis_n": int(len(ats)), "by_year": by}
rec["H2_A0_population"] = h2
log("H2 done")

# ---------------- H3 fund rank base / H4 training rows / H6 elig ----------------
h3 = {}; h4k = {}; h6 = {}
for i, t in enumerate(aE):
    j = prow.get(int(t)); y = str(yr(t))
    m = np.asarray(aMem[i], np.int64)
    b4 = h4k.setdefault(y, {"king_member_pairs": 0, "Z24": 0, "DEAD": 0, "DEAD_y4_exactly0": 0, "Z24_y4_exactly0": 0})
    b4["king_member_pairs"] += int(len(m)); b4["Z24"] += int(Z24[i, m].sum()); b4["DEAD"] += int(DEAD[i, m].sum())
    b4["DEAD_y4_exactly0"] += int((aY4[i, m][DEAD[i, m]] == 0).sum()); b4["Z24_y4_exactly0"] += int((aY4[i, m][Z24[i, m]] == 0).sum())
    if j is None: continue
    base = np.isfinite(FE1[j])
    b3 = h3.setdefault(y, {"anchors": 0, "base_sum": 0, "base_DEAD_sum": 0, "base_Z24_sum": 0, "base_DEAD_max": 0})
    b3["anchors"] += 1; b3["base_sum"] += int(base.sum()); nd = int((base & DEAD[i]).sum()); b3["base_DEAD_sum"] += nd; b3["base_Z24_sum"] += int((base & Z24[i]).sum()); b3["base_DEAD_max"] = max(b3["base_DEAD_max"], nd)
    b6 = h6.setdefault(y, {"elig_true": 0, "elig_true_Z24": 0, "elig_true_DEAD": 0, "fund_now_finite_on_DEAD": 0})
    e = ELIG[j].astype(bool); b6["elig_true"] += int(e.sum()); b6["elig_true_Z24"] += int((e & Z24[i]).sum()); b6["elig_true_DEAD"] += int((e & DEAD[i]).sum())
    b6["fund_now_finite_on_DEAD"] += int((np.isfinite(FN[j]) & DEAD[i]).sum())
T = np.load(DTG, allow_pickle=True); dE = T["E_ts"].astype(np.int64); dMem = T["members"]; dY = T["y4s"]; drow = np.searchsorted(CTS, dE); assert np.array_equal(CTS[drow], dE)
dpos_in_a = {int(t): i for i, t in enumerate(aE)}
h4d = {}
for i, t in enumerate(dE):
    ia = dpos_in_a.get(int(t)); y = str(yr(t)); m = np.asarray(dMem[i], np.int64)
    b = h4d.setdefault(y, {"dl_member_pairs": 0, "DEAD": 0, "DEAD_y4s_exactly0": 0, "anchors_off_king_axis": 0})
    b["dl_member_pairs"] += int(len(m))
    dead_row = (drow[i] > last_tr[m]) & dead_sym[m]
    b["DEAD"] += int(dead_row.sum()); b["DEAD_y4s_exactly0"] += int((dY[i, m][dead_row] == 0).sum())
    if ia is None: b["anchors_off_king_axis"] += 1
for b in h3.values(): b["base_mean"] = b["base_sum"] / max(b["anchors"], 1); b["base_DEAD_mean"] = b["base_DEAD_sum"] / max(b["anchors"], 1); b["base_Z24_mean"] = b["base_Z24_sum"] / max(b["anchors"], 1)
rec["H3_fund_rank_base_v2ext_f_fund_ema_v1"] = h3; rec["H4_training_rows"] = {"king_meta": h4k, "dl_targets": h4d}; rec["H6_panel_elig_and_funding_on_dead"] = h6
log("H3/H4/H6 done")

# ---------------- H5 funding records after death ----------------
AUG = json.loads(gzip.open(AUGP, "rt").read()); SEP = json.loads(gzip.open(SEPP, "rt").read())
def events(s):
    ev = {}
    for zp in sorted(glob.glob(f"{FDIR}/{s}/*.zip")):
        try:
            zf = zipfile.ZipFile(zp)
            with zf.open(zf.namelist()[0]) as fh:
                for row in csv.reader(io.TextIOWrapper(fh)):
                    if not row or not row[0].strip().isdigit(): continue
                    try: ev.setdefault(int(row[0]) // 1000, set()).add("zip")
                    except Exception: pass
        except Exception: pass
    for t, _ in (AUG.get("rates") or {}).get(s, []): ev.setdefault(int(t) // 1000, set()).add("aug")
    for t, _ in (SEP.get("rates") or {}).get(s, []): ev.setdefault(int(t) // 1000, set()).add("sep")
    return s, ev
dead_names = [syms[j] for j in np.where(dead_sym)[0]]
with Pool(6) as pool:
    EV = dict(pool.map(events, dead_names, chunksize=4))
h5 = {}; tot = {"events": 0, "zip": 0, "aug": 0, "sep": 0}; by_year = {}
for s in dead_names:
    j = syms.index(s); t_last = int(CTS[last_tr[j]]) + 3600
    after = sorted(t for t in EV[s] if t > t_last)
    if not after: continue
    srcs = {"zip": sum(1 for t in after if "zip" in EV[s][t]), "aug": sum(1 for t in after if "aug" in EV[s][t]), "sep": sum(1 for t in after if "sep" in EV[s][t])}
    h5[s] = {"last_traded_bar_close": utc(CTS[last_tr[j]]), "events_after": len(after), "first_after": utc(after[0]), "last_after": utc(after[-1]), **srcs}
    tot["events"] += len(after); [tot.__setitem__(k, tot[k] + v) for k, v in srcs.items()]
    for t in after: by_year[str(yr(t))] = by_year.get(str(yr(t)), 0) + 1
L = np.load(LEDGER, allow_pickle=True); off = L["off"].astype(np.int64); lft = L["ft"].astype(np.int64); lsy = [str(x) for x in L["symbols"]]; assert lsy == syms
p2 = {}
for i, t in enumerate(aE):
    y = str(yr(t)); b = p2.setdefault(y, {"anchors": 0, "base_proxy_sum": 0, "base_proxy_DEAD_sum": 0, "base_proxy_DEAD_max": 0})
    b["anchors"] += 1; nb = 0; nd = 0
    for jj in range(NW):
        a, c = off[jj], off[jj + 1]
        if c <= a: continue
        k = np.searchsorted(lft[a:c], t, side="right")
        if k and lft[a + k - 1] > t - 86400:
            nb += 1
            if DEAD[i, jj]: nd += 1
    b["base_proxy_sum"] += nb; b["base_proxy_DEAD_sum"] += nd; b["base_proxy_DEAD_max"] = max(b["base_proxy_DEAD_max"], nd)
for b in p2.values(): b["base_proxy_mean"] = b["base_proxy_sum"] / max(b["anchors"], 1); b["base_proxy_DEAD_mean"] = b["base_proxy_DEAD_sum"] / max(b["anchors"], 1)
rec["H5_funding_after_death"] = {"symbols_dead_inside_cache": len(dead_names), "symbols_with_events_after_death": len(h5), "totals": tot, "events_by_year": by_year,
                                 "per_symbol": dict(sorted(h5.items(), key=lambda kv: -kv[1]["events_after"])[:40]), "P2_base_proxy_on_king_axis": p2}
rec["elapsed_s"] = round(time.time() - T0, 1)
json.dump(rec, open(OUT, "w"), indent=1)
print("AD_TRADABILITY_DONE", json.dumps({"post_death_rows": sig["post_death_untraded_rows"], "dead_syms": int(dead_sym.sum()), "fund_events_after_death": tot["events"]}), flush=True)
