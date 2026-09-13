#!/usr/bin/env python3
"""t5d_posthoc.py — pod2, CPU (nice, single process), READ-ONLY. POST-HOC and descriptive: written after the T5d bridge numbers were seen.
Nothing here is a gate of PREREG_T5d or changes a reading.
 A. Per-settlement interval sources for every settlement after 2026-08-30 00Z (the 24 h before the cut and the whole tail): x0910 iv (r6 iv_full), producer
    ledger iv, snapped timestamp gap, executor funding_interval_h, iv_true and its source. Re-deriving the corrected tail cells from this list must equal
    the T5d panel bitwise (A-REPRO). Settlements with neither a ledger record nor a usable gap are listed with where they are in force.
    Executor mismatches are classified: at an interval change of iv_true (the executor read the new interval) or not.
 B. Incumbent rows (<= 2026-08-31 00Z) against the producer ledger over the whole ledger coverage (from 2026-08-28 00Z): the panel f_fund_iv of the
    in-force settlement, and the r6 event-stream iv of every pre-cut settlement. For pre-cut settlements whose stream iv differs from the ledger, the
    linear effect on the v1 EMA at the cut if the base panel used the stream iv (INFERRED bound; the base builder's own iv vector is not available).
 C. Where the regenerated weights moved the replay (KA, both seeds): REG − T5c per UTC day and per name, for price, carry (weight part and repricing
    part), cost and net; sums must equal the bridge components per anchor.
 D. Construction-only part of the D_K − R_K gap = the nine group Shapley values = total − REM, per outcome, both calibers, k = 90.
Launch: bash devices/launch_pod2.sh t5d_posthoc.py
"""
import os, io, csv, sys, json, glob, gzip, zipfile, time, hashlib, subprocess
WHITE = set(x for x in sys.argv[1].split(",") if x) if len(sys.argv) > 1 else None
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
R = "/workspace/uplift_r2_2026-09-13/T5d"; T5C = "/workspace/uplift_r2_2026-09-13/T5c"; PREREG_SHA = "a1ef16cdba5e95def27f77b180cba3f1ac954ad04c7b0a17f59c24e1a0c85a4f"
def sha(p):
    h = hashlib.sha256()
    with open(os.path.realpath(p), "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()
def sh(cmd):
    try: return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as e: return "ERR %s" % e
U = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
assert sha(R + "/PREREG_T5d_iv_corrected_replay_2026-09-13.md") == PREREG_SHA
GPU0 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID0 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2"); assert GPU0.replace(" ", "") == "0%,2MiB", GPU0
t0 = time.time()
PRC = json.load(open(R + "/receipts/RECEIPT_T5d_ivfix_panel.json")); BRC = json.load(open(R + "/receipts/RECEIPT_T5d_bridge.json")); DRV = json.load(open(R + "/receipts/RECEIPT_T5d_drive.json"))
T5CD = json.load(open(T5C + "/receipts/RECEIPT_T5c_drive.json")); T5CB = json.load(open(T5C + "/receipts/RECEIPT_T5c_bridge.json"))
R6 = "/workspace/uplift_2026-09-11/r6"; SPLICE = R6 + "/r6_panel_splice.py"; BASEP = "/workspace/data/wide_panel_4h_v2ext.npz"; XP = R6 + "/out/wide_panel_4h_v2ext_x0910.npz"
XRC = json.load(open(R6 + "/out/wide_panel_4h_v2ext_x0910_RECEIPT.json")); FSEP = XRC["fund_sep"]; AUGP = "/workspace/fund_aug.json.gz"; FDIR = "/workspace/wide_multisrc/funding"
SRCJ = R + "/inputs/t5d_interval_sources.json"; PXC = PRC["out"]; MX = R6 + "/out/meta_newprod_v4_x0910.npz"; COSTB = "/workspace/uplift_2026-09-11/r3k/costb_PWR_G230k.json"
INGP = T5C + "/receipts/T5c_live_ingredients.npz"; CMPD = R + "/receipts/T5d_bridge_components.npz"; CMPC = T5C + "/receipts/T5c_bridge_components.npz"
TAGS = ("KA_s42", "KA_s2027"); ARM_D = {t: DRV["runs"][t]["out"] for t in TAGS}; ARM_C = {t: T5CD["runs"][t]["out"] for t in TAGS}
EXP = {SPLICE: PRC["inputs"][SPLICE], BASEP: PRC["inputs"][BASEP], XP: PRC["inputs"][XP], FSEP: PRC["inputs"][FSEP], SRCJ: PRC["inputs"][SRCJ], AUGP: PRC["inputs"][AUGP], PXC: PRC["out_sha256"],
       MX: BRC["inputs"][MX], COSTB: BRC["inputs"][COSTB], INGP: BRC["inputs"][INGP], CMPD: BRC["components_npz_sha256"], CMPC: T5CB["components_npz_sha256"]}
EXP.update({ARM_D[t]: DRV["runs"][t]["out_sha256"] for t in TAGS}); EXP.update({ARM_C[t]: T5CD["runs"][t]["out_sha256"] for t in TAGS})
INPUTS = {p: sha(p) for p in EXP}
for p, h in EXP.items(): assert INPUTS[p] == h, ("INPUT SHA", p)
HL = 3 * 86400.0; ALLOWED = np.array([1.0, 2.0, 4.0, 6.0, 8.0])
CAN = np.load(BASEP, allow_pickle=True); X = np.load(XP, allow_pickle=True); XF = np.load(PXC, allow_pickle=True)
CANA = {k: CAN[k] for k in ("ts", "symbols", "f_fund_now", "f_fund_iv", "f_fund_ema", "f_fund_ema_v1", "f_fund_ema_v2")}   # materialise once (NpzFile re-reads on every access)
syms = [str(s) for s in X["symbols"]]; assert syms == [str(s) for s in CANA["symbols"]] == [str(s) for s in XF["symbols"]]
ct = CANA["ts"].astype(np.int64); xt = X["ts"].astype(np.int64); nC0 = len(ct); cut = int(ct[-1]); tail_ts = xt[nC0:]
assert np.array_equal(xt[:nC0], ct) and len(tail_ts) == 60 and U(cut) == "2026-08-31 00:00Z"
KEYS = ("f_fund_now", "f_fund_iv", "f_fund_ema", "f_fund_ema_v1", "f_fund_ema_v2"); XFA = {k: XF[k] for k in KEYS}
AUG = json.loads(gzip.open(AUGP, "rt").read()); AUG_IV = {k: float(v) for k, v in (AUG.get("intervals") or {}).items() if v}
SEP = json.loads(gzip.open(FSEP, "rt").read()); SEP_IV = {k: float(v) for k, v in (SEP.get("intervals") or {}).items() if v}
SRC = json.load(open(SRCJ)); LED = {s: {int(r[0]): r[1] for r in rows} for s, rows in SRC["ledger"].items()}; EXE = {s: {int(r[0]): r[1] for r in rows} for s, rows in SRC["executor"].items()}
LO = 1787875200   # 2026-08-28 00:00Z = the lower bound t5d_interval_sources.py applied to ledger rows (its comment says 08-20; the constant is 08-28)
def tail_cells(ft, fr, ivv, seeds):
    """identical to t5d_ivfix_panel.py tail_cells (r6_panel_splice.py L102-L128 algebra)."""
    rate_nf = fr * (8.0 / ivv); sel = ft > cut
    pos = np.searchsorted(ft, tail_ts, side="right") - 1; okp = pos >= 0
    fn = np.full(len(tail_ts), np.nan); fi = np.full(len(tail_ts), np.nan)
    fn[okp] = fr[pos[okp]]; fi[okp] = ivv[pos[okp]]
    stale = okp & ((tail_ts - np.where(okp, ft[np.maximum(pos, 0)], 0)) > 12*3600)
    fn[stale] = np.nan; fi[stale] = np.nan
    out = dict(f_fund_now=fn.astype(np.float32), f_fund_iv=fi.astype(np.float32), inforce=np.where(okp & ~stale, pos, -1))
    if seeds["v1"] is None: return out
    e0, e1, e2 = seeds["v0"], seeds["v1"], seeds["v2"]; prev_t = cut
    ivm = np.median(ivv[sel]) if sel.any() else 8.0
    span = max(2, round(24 / ivm)); al2 = 2.0 / (span + 1.0)
    ptr = np.where(sel)[0]; k2 = 0; E0 = np.full(len(tail_ts), np.nan, np.float32); E1 = E0.copy(); E2 = E0.copy()
    for r_row, t_anchor in enumerate(tail_ts):
        while k2 < len(ptr) and ft[ptr[k2]] <= t_anchor:
            i_ = ptr[k2]
            a = 1 - 0.5 ** (max(ft[i_] - prev_t, 1) / HL)
            e0 = e0 + a * (fr[i_] - e0); e1 = e1 + a * (rate_nf[i_] - e1)
            e2 = e2 + al2 * (rate_nf[i_] - e2) if e2 is not None else rate_nf[i_]
            prev_t = ft[i_]; k2 += 1
        E0[r_row] = np.float32(e0); E1[r_row] = np.float32(e1)
        if e2 is not None: E2[r_row] = np.float32(e2)
    out.update(f_fund_ema=E0, f_fund_ema_v1=E1, f_fund_ema_v2=E2, has_v2=e2 is not None or seeds["v2"] is not None)
    return out
def eqf(a, b): return bool(np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(a[~np.isnan(a)], b[~np.isnan(b)]))
# ---------------------------------------------------------------- C
ING = np.load(INGP, allow_pickle=True); SYM = [str(x) for x in ING["symbols"]]; CAL = [int(x) for x in ING["cal"]]; WIN = [int(x) for x in ING["win"]]; kW = [k for k, A in enumerate(CAL) if A in WIN]
P_ = lambda path: np.load(path, allow_pickle=True)
def carry_rows(path):
    P = P_(path); prow = {int(t): q for q, t in enumerate(P["ts"].astype(np.int64))}; FN = P["f_fund_now"].astype(np.float64); IV = P["f_fund_iv"].astype(np.float64); IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0)
    return np.stack([np.nan_to_num(FN[prow[A]], nan=0.0) * (4.0 / IVf[prow[A]]) for A in CAL])
C4X = carry_rows(XP); C4C = carry_rows(PXC)
MXz = P_(MX); emap = {int(t): i for i, t in enumerate(MXz["E_ts"].astype(np.int64))}; Y4c = np.nan_to_num(np.stack([MXz["y4"][emap[A]].astype(np.float64) for A in CAL]), nan=0.0); QVKx = np.stack([MXz["qvk"][emap[A]].astype(np.float64) for A in CAL])
CB = json.load(open(COSTB)); tiers = CB["tiers"] if isinstance(CB, dict) else CB
COST_B = [(float(t["maker_bps"]), float(t["taker_bps"]), float(t["maker_share"])) if isinstance(t, dict) else (float(t[0]), float(t[1]), float(t[2])) for t in tiers]
QV4H = np.expm1(np.clip(QVKx, 0, 30)) * 48; TIER = np.where(QV4H >= 5e6, 0, np.where(QV4H >= 1e6, 1, 2)); RATES = np.array([fr_ * mk + (1 - fr_) * tk for (mk, tk, fr_) in COST_B]); RATE = RATES[TIER]
CMP = P_(CMPD); CMP5 = P_(CMPC)
days = np.array([CAL[k] // 86400 for k in kW]); one = np.ones(len(kW)); B = 2000
def boot(num, den, k):
    u, inv = np.unique(days, return_inverse=True); nd = len(u)
    sn = np.bincount(inv, weights=num, minlength=nd); sdn = np.bincount(inv, weights=den, minlength=nd)
    rng = np.random.default_rng([20260905, k]); dr = rng.integers(0, nd, size=(B, nd)); rep = sn[dr].sum(1) / sdn[dr].sum(1)
    return [float(sn.sum() / sdn.sum()), float(np.percentile(rep, 2.5)), float(np.percentile(rep, 97.5))]
SWITCH = {x["symbol"] for t in TAGS for x in BRC["ftrim_and_weights"][t]["switches"]}; CHG23 = set(PRC["gate_G_IV_LEDGER"]["changed_symbols"])
CPART = {}
for t in TAGS:
    dR = P_(ARM_D[t]); dC = P_(ARM_C[t]); pre = "d30_n2_c42_T5_"; smR = dR[pre + "smk"].astype(np.float64); smC = dC[pre + "smk"].astype(np.float64)
    assert [int(x) for x in dR[pre + "ts"]][1:] == CAL
    nP = np.zeros((nC := len(CAL), len(SYM))); nCw = nP.copy(); nCr = nP.copy(); nK = nP.copy(); maxres = 0.0
    for k in range(nC):
        gR = np.abs(smR[k + 1]).sum(); gC = np.abs(smC[k + 1]).sum(); wR = smR[k + 1] / gR; wC = smC[k + 1] / gC
        nP[k] = (wR - wC) * Y4c[k] * 1e4; nCw[k] = (wR - wC) * C4C[k] * 1e4; nCr[k] = wC * (C4C[k] - C4X[k]) * 1e4
        nK[k] = np.abs(smR[k + 1] - smR[k]) * RATE[k] / gR - np.abs(smC[k + 1] - smC[k]) * RATE[k] / gC
        for q, arr in (("P", nP[k]), ("C", nCw[k] + nCr[k]), ("K", nK[k])):
            maxres = max(maxres, abs(arr.sum() - (CMP[f"R_REG_{t}_{q}"][k] - CMP[f"R_T5C_{t}_{q}"][k])))
    nN = nP - nCw - nCr - nK; kw = np.array(kW)
    per_day = {}
    for d in np.unique(days):
        sel = np.array(kW)[days == d]
        per_day[time.strftime("%m-%d", time.gmtime(int(d) * 86400))] = dict(n=int(len(sel)), P=float(nP[sel].sum(1).mean()), C=float((nCw[sel] + nCr[sel]).sum(1).mean()), C_weight=float(nCw[sel].sum(1).mean()), C_reprice=float(nCr[sel].sum(1).mean()), K=float(nK[sel].sum(1).mean()), N=float(nN[sel].sum(1).mean()),
                                                                          contribution_to_window_mean_N=float(nN[sel].sum() / len(kW)), contribution_to_window_mean_P=float(nP[sel].sum() / len(kW)))
    mP = nP[kw].sum(0) / len(kW); mCw = nCw[kw].sum(0) / len(kW); mCr = nCr[kw].sum(0) / len(kW); mK = nK[kw].sum(0) / len(kW); mN = nN[kw].sum(0) / len(kW)
    rowf = lambda n: dict(symbol=SYM[n], P=float(mP[n]), C_weight=float(mCw[n]), C_reprice=float(mCr[n]), K=float(mK[n]), N=float(mN[n]), iv_changed=SYM[n] in CHG23, ftrim_switch=SYM[n] in SWITCH)
    grp = lambda S_: {q: float(v[[SYM.index(x) for x in S_ if x in SYM]].sum()) for q, v in (("P", mP), ("C_weight", mCw), ("C_reprice", mCr), ("K", mK), ("N", mN))}
    CPART[t] = dict(max_abs_residual_vs_components=maxres, totals={q: float(v.sum()) for q, v in (("P", mP), ("C_weight", mCw), ("C_reprice", mCr), ("K", mK), ("N", mN))},
                    ftrim_switch_names=sorted(SWITCH), subtotal_ftrim_switch_names=grp(SWITCH), subtotal_other_iv_changed_names=grp(CHG23 - SWITCH), subtotal_rest=grp(set(SYM) - CHG23 - SWITCH),
                    per_day=per_day, names_most_negative_N=[rowf(n) for n in np.argsort(mN)[:12]], names_most_positive_N=[rowf(n) for n in np.argsort(-mN)[:8]], names_abs_P=[rowf(n) for n in np.argsort(-np.abs(mP))[:12]])
    assert maxres <= 1e-9, ("C residual", t, maxres)
print("C done", {t: CPART[t]["totals"] for t in TAGS}, flush=True)
# ---------------------------------------------------------------- D
DELTA_EQ = 0.25
def rd(ci):
    return "detected" if (ci[1] > 0 or ci[2] < 0) else ("economically negligible: excluded beyond ±0.25" if (-DELTA_EQ <= ci[1] and ci[2] <= DELTA_EQ) else "not detected, not excluded: below %+.2f or above %+.2f excluded (95%%, descriptive)" % (ci[1], ci[2]))
DPART = {}
for t in TAGS:
    DPART[t] = {}
    for cal, Z in (("REG", CMP), ("T5C", CMP5)):
        DPART[t][cal] = {}
        for q in ("P", "C", "K", "N"):
            con = Z[f"{t}_{q}_DEL"] - Z[f"{t}_{q}_REM"]; ci = boot(con, one, 90); DPART[t][cal][q] = dict(construction=ci, reading=rd(ci), total=boot(Z[f"{t}_{q}_DEL"], one, 90), REM=boot(Z[f"{t}_{q}_REM"], one, 90))
print("D done", json.dumps({t: {c: {q: [round(x, 2) for x in DPART[t][c][q]["construction"]] for q in "PCN"} for c in DPART[t]} for t in TAGS}), flush=True)
# ---------------------------------------------------------------- A and B
LIST_P = R + "/posthoc/iv_sources_per_settlement.csv.gz"; os.makedirs(R + "/posthoc", exist_ok=True)
lw = gzip.open(LIST_P, "wt", newline=""); cw = csv.writer(lw)
cw.writerow(["symbol", "settlement_utc", "settlement_ts", "tail", "rate", "iv_x0910", "iv_ledger", "iv_gap", "iv_executor", "iv_true", "source"])
A_REPRO = dict(mismatch={k: [] for k in KEYS}); A_CNT = dict(tail={}, pre24={}); CHANGED = []; FALLBACK = []; EXEC_CLS = []
B_ROWS = dict(checked=0, not_in_ledger=0, rate_mismatch=0, iv_mismatch=[]); B_EVENTS = dict(checked=0, iv_mismatch=[]); SEEDERR = []
canrows = np.nonzero((ct >= LO) & (ct <= cut))[0]
for j, s in enumerate(syms):
    rows = []
    for zp in sorted(glob.glob(f"{FDIR}/{s}/*.zip")):           # verbatim r6_panel_splice.py L63-L77 (as t5d_ivfix_panel.py)
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
    seeds = {nm: (float(CANA[col][-1, j]) if np.isfinite(CANA[col][-1, j]) else None) for nm, col in (("v0", "f_fund_ema"), ("v1", "f_fund_ema_v1"), ("v2", "f_fund_ema_v2"))}
    gap = np.where(np.isfinite(dv), ALLOWED[np.argmin(np.abs(np.nan_to_num(dv, nan=8.0)[:, None] - ALLOWED[None, :]), axis=1)], np.nan)
    iv_true = iv_full.copy(); led = LED.get(s, {}); ex = EXE.get(s, {}); src = np.array(["pre"] * len(ft), dtype=object)
    relevant = ft > cut - 24 * 3600
    for i in np.nonzero(relevant)[0]:
        lv = led.get(int(ft[i]))
        if lv is not None and lv is not False: iv_true[i] = float(lv); src[i] = "ledger"
        elif np.isfinite(gap[i]): iv_true[i] = float(gap[i]); src[i] = "gap"
        else: src[i] = "fallback_x0910"
    c2 = tail_cells(ft, fr, iv_true, seeds)
    for k in ("f_fund_now", "f_fund_iv"):
        if not eqf(c2[k], XFA[k][nC0:, j]): A_REPRO["mismatch"][k].append(s)
    if seeds["v1"] is not None:
        for k in ("f_fund_ema", "f_fund_ema_v1", "f_fund_ema_v2"):
            if k == "f_fund_ema_v2" and not c2["has_v2"]: continue
            if not eqf(c2[k], XFA[k][nC0:, j]): A_REPRO["mismatch"][k].append(s)
    inforce_rows = {}
    for r_row, p_ in enumerate(c2["inforce"]):
        if p_ >= 0: inforce_rows.setdefault(int(p_), []).append(U(tail_ts[r_row]))
    for i in np.nonzero(relevant)[0]:
        tl = bool(ft[i] > cut); key = "tail" if tl else "pre24"; A_CNT[key][src[i]] = A_CNT[key].get(src[i], 0) + 1
        eiv = ex.get(int(ft[i])); lv = led.get(int(ft[i]))
        cw.writerow([s, U(ft[i]), int(ft[i]), int(tl), repr(float(fr[i])), float(iv_full[i]), (float(lv) if lv is not None else ""), (float(gap[i]) if np.isfinite(gap[i]) else ""), (float(eiv) if eiv is not None else ""), float(iv_true[i]), src[i]])
        if iv_true[i] != iv_full[i]: CHANGED.append([s, U(ft[i]), float(iv_full[i]), float(iv_true[i]), src[i], (float(eiv) if eiv is not None else None), inforce_rows.get(int(i), [])[:1] + (inforce_rows.get(int(i), [])[-1:] if len(inforce_rows.get(int(i), [])) > 1 else [])])
        if src[i] == "fallback_x0910":
            nxt = float(np.round((ft[i + 1] - ft[i]) / 3600.0)) if i + 1 < len(ft) else None; prv = float(np.round((ft[i] - ft[i - 1]) / 3600.0)) if i > 0 else None
            FALLBACK.append(dict(symbol=s, settlement=U(ft[i]), tail=tl, iv_used=float(iv_full[i]), hours_since_previous=prv, hours_to_next=nxt, executor=(float(eiv) if eiv is not None else None), in_force_at=inforce_rows.get(int(i), []), sep_iv=SEP_IV.get(s), aug_iv=AUG_IV.get(s), has_tail_ema=seeds["v1"] is not None))
        if eiv is not None and float(iv_true[i]) != float(eiv):
            nxt8 = [float(iv_true[m]) for m in range(i + 1, len(ft)) if ft[m] - ft[i] <= 8 * 3600]; prv8 = [float(iv_true[m]) for m in range(0, i) if ft[i] - ft[m] <= 8 * 3600 and relevant[m]]
            EXEC_CLS.append(dict(symbol=s, settlement=U(ft[i]), iv_true=float(iv_true[i]), executor=float(eiv), source=src[i], gap=(float(gap[i]) if np.isfinite(gap[i]) else None), iv_true_next_8h=nxt8, iv_true_prev_8h=prv8,
                                 executor_shows_upcoming_interval=bool(float(eiv) in nxt8), executor_shows_previous_interval=bool(float(eiv) in prv8)))
    # executor settlements before the 24 h window (not recomputed by T5d): compare with ledger and stream
    for t_, eiv in ex.items():
        if t_ > cut - 24 * 3600: continue
        i = int(np.searchsorted(ft, t_))
        if i < len(ft) and ft[i] == t_ and float(iv_full[i]) != float(eiv):
            lv = led.get(int(t_)); EXEC_CLS.append(dict(symbol=s, settlement=U(t_), iv_true=None, iv_stream=float(iv_full[i]), executor=float(eiv), ledger=(float(lv) if lv is not None else None), gap=(float(gap[i]) if np.isfinite(gap[i]) else None), pre_window=True))
    # B: pre-cut events and incumbent rows vs ledger
    if led:
        pre = np.nonzero((ft >= LO) & (ft <= cut))[0]; mis_ev = []
        for i in pre:
            lv = led.get(int(ft[i]))
            if lv is None: continue
            B_EVENTS["checked"] += 1
            if float(lv) != float(iv_full[i]): mis_ev.append(i); B_EVENTS["iv_mismatch"].append([s, U(ft[i]), float(iv_full[i]), float(lv), (float(gap[i]) if np.isfinite(gap[i]) else None)])
        for r_ in canrows:
            A_ = int(ct[r_]); p_ = int(np.searchsorted(ft, A_, side="right")) - 1
            if p_ < 0 or A_ - ft[p_] > 12 * 3600 or not np.isfinite(CANA["f_fund_iv"][r_, j]): continue
            lv = led.get(int(ft[p_]))
            if lv is None: B_ROWS["not_in_ledger"] += 1; continue
            B_ROWS["checked"] += 1
            if np.float32(fr[p_]) != CANA["f_fund_now"][r_, j]: B_ROWS["rate_mismatch"] += 1
            if float(CANA["f_fund_iv"][r_, j]) != float(lv): B_ROWS["iv_mismatch"].append([s, U(A_), float(CANA["f_fund_iv"][r_, j]), float(lv), U(ft[p_]), float(iv_full[p_])])
        if mis_ev and seeds["v1"] is not None:
            # linear response of the v1 EMA at the cut to replacing the stream iv by the ledger iv on the mismatching pre-cut events (a_j from the stream)
            idx = np.nonzero(ft <= cut)[0]; a_all = np.ones(len(ft)); a_all[1:] = 1 - 0.5 ** (np.maximum(np.diff(ft), 1) / HL)
            de = 0.0
            for i in mis_ev:
                decay = float(np.prod(1 - a_all[i + 1: idx[-1] + 1])) if i < idx[-1] else 1.0
                de += decay * a_all[i] * fr[i] * (8.0 / float(led[int(ft[i])]) - 8.0 / float(iv_full[i]))
            SEEDERR.append(dict(symbol=s, n_events=len(mis_ev), v1_seed=seeds["v1"], v1_seed_correction_if_base_used_stream_iv=float(de), events=[U(ft[i]) for i in mis_ev][:6]))
    if j % 100 == 0: print("sym", j, round(time.time() - t0, 1), flush=True)
lw.close()
A_REPRO["n_mismatch"] = {k: len(v) for k, v in A_REPRO["mismatch"].items()}; A_REPRO["PASS"] = all(v == 0 for v in A_REPRO["n_mismatch"].values())
print("A-REPRO", A_REPRO["n_mismatch"], A_REPRO["PASS"], "counts", A_CNT, "changed", len(CHANGED), "fallback", len(FALLBACK), flush=True); assert A_REPRO["PASS"], "A-REPRO failed"
# seed errors in cross-sectional context (v1 at the cut, all finite names)
v1cut = CANA["f_fund_ema_v1"][-1].astype(np.float64); fin = np.isfinite(v1cut)
for e in SEEDERR:
    jj = syms.index(e["symbol"]); v = v1cut[jj]; nv = v + e["v1_seed_correction_if_base_used_stream_iv"]
    e["rank_of_seed"] = int((v1cut[fin] < v).sum()); e["rank_if_changed"] = int((v1cut[fin] < nv).sum()); e["names_finite"] = int(fin.sum())
    e["decay_factor_at_window_end"] = float(0.5 ** ((int(tail_ts[-1]) - cut) / HL)); e["decay_factor_at_09_02_00Z"] = float(0.5 ** (2 * 86400 / HL))
GPU1 = sh("nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader"); PID1 = sh("ps -o pid,stat -p 333197,339489 | tail -n +2")
RC = dict(label="POST-HOC descriptive (after the T5d bridge numbers were seen); not a gate, not a reading", self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, inputs=INPUTS,
          A=dict(repro=A_REPRO, source_counts=A_CNT, changed_settlements=CHANGED, n_changed=len(CHANGED), fallback_settlements=FALLBACK, executor_mismatches=EXEC_CLS,
                 per_settlement_list=LIST_P, per_settlement_list_sha256=sha(LIST_P)),
          B=dict(incumbent_rows=dict(checked=B_ROWS["checked"], not_in_ledger=B_ROWS["not_in_ledger"], rate_mismatch=B_ROWS["rate_mismatch"], n_iv_mismatch=len(B_ROWS["iv_mismatch"]), iv_mismatch=B_ROWS["iv_mismatch"][:200],
                                    iv_mismatch_names=sorted({x[0] for x in B_ROWS["iv_mismatch"]}), first_anchor=U(ct[canrows[0]]), last_anchor=U(ct[canrows[-1]])),
                 stream_events=dict(checked=B_EVENTS["checked"], n_iv_mismatch=len(B_EVENTS["iv_mismatch"]), iv_mismatch=B_EVENTS["iv_mismatch"][:300], names=sorted({x[0] for x in B_EVENTS["iv_mismatch"]})),
                 v1_seed_linear_response=SEEDERR),
          C=CPART, D=DPART, gpu_before=GPU0, gpu_after=GPU1, pids_before=PID0, pids_after=PID1, env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}),
          built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(R + "/receipts/RECEIPT_T5d_posthoc.json", "w"), indent=1, default=lambda o: (o.tolist() if isinstance(o, np.ndarray) else float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else bool(o) if isinstance(o, np.bool_) else str(o)))
print("DONE_t5d_posthoc", RC["wall_s"])
