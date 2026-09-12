#!/usr/bin/env python3
"""r13 · DEPLOYABILITY of T1: can the live chain express FORM A / FORM B?

READ-ONLY. Imports the DEPLOYED function ~/dl_quant_live/signal/legs.py::reshape_after_withhold
(a pure module: numpy + typing only, no side effects, verified by reading it). Opens
~/wide_shadow/state/target_live/*.json and ~/dl_quant_live/state/live/pilot_log/*/anchors.jsonl
read-only. No venue API. No writes outside exports/research/uplift_2026-09-11/r13_deploy/.

PREREG: PREREG_r13_deployability_2026-09-12.md sha256 asserted below before anything runs.
"""
import os, sys, json, glob, time, hashlib, calendar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import assert_env
ENV = assert_env()
import numpy as np

R13 = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
PREREG = os.path.join(R13, "PREREG_r13_deployability_2026-09-12.md")
PREREG_SHA = "fcbedd4aae571dcbe8c550348981e08baf594dc2d270aaefb41c72b43c96c8a4"
_got = hashlib.sha256(open(PREREG, 'rb').read()).hexdigest()
assert _got == PREREG_SHA, ("PREREG HASH MISMATCH", _got, PREREG_SHA)

LIVEROOT = os.path.expanduser("~/dl_quant_live")
WS = os.path.expanduser("~/wide_shadow")
sys.path.insert(0, os.path.join(LIVEROOT, "signal"))
import legs as LG                                   # the DEPLOYED module
LEGS_SHA = hashlib.sha256(open(os.path.join(LIVEROOT, "signal", "legs.py"), 'rb').read()).hexdigest()
AL_SRC = open(os.path.join(LIVEROOT, "scheduler", "anchor_loop.py"), errors="ignore").read()
AL_SHA = hashlib.sha256(AL_SRC.encode()).hexdigest()
CS_PATH = os.path.join(WS, "fea171", "combo_stage.py")
CS_SRC = open(CS_PATH, errors="ignore").read()
CS_SHA = hashlib.sha256(CS_SRC.encode()).hexdigest()
H = 14400
OUT = os.path.join(R13, "receipts")

# ══ S5 · ORDER, from the deployed source text ════════════════════════════════════════════════
i_pop     = AL_SRC.find("clamp[\"popped\"] = withhold_pop(")
i_reshape = AL_SRC.find("rs = LG.reshape_after_withhold(")
i_clamp   = AL_SRC.find("clamp.update(clamp_held_untradable(")
i_call    = AL_SRC.find("apply_withhold_and_reshape(\n")
i_band    = AL_SRC.find("LG.apply_no_trade_band(")
i_plan    = AL_SRC.find("self.executor.capture_anchor(symbols)")
S5 = dict(i_pop=i_pop, i_reshape=i_reshape, i_clamp=i_clamp, i_band=i_band, i_plan=i_plan,
          order_pop_reshape_clamp=bool(0 < i_pop < i_reshape < i_clamp),
          order_reshape_band_plan=bool(0 < i_reshape < i_band < i_plan),
          external_book_skips_band=("\"skipped\": \"external_book\"" in AL_SRC),
          switches_are_module_constants=bool("RESHAPE_REDEMEAN = True" in AL_SRC
                                             and "RESHAPE_RESCALE = True" in AL_SRC),
          reshape_call_is_ungated=bool("if target and g > 0:" in AL_SRC),
          n_call_sites=AL_SRC.count("apply_withhold_and_reshape("))
# producer's own reshape and WHICH vector it writes
S6_src = dict(producer_has_exec_reshape=bool("def exec_reshape(w):" in CS_SRC),
              producer_writes_combo_raw=bool(
                  '_weights = {syms[int(j)]: float(combo_raw[j]) for j in _nz}' in CS_SRC),
              producer_writes_combo_reshaped=bool(
                  '_weights = {syms[int(j)]: float(combo[j]) for j in _nz}' in CS_SRC))

# ══ ledger ═══════════════════════════════════════════════════════════════════════════════════
def jl(p):
    for l in open(p, errors="ignore"):
        l = l.strip()
        if not l: continue
        try: yield json.loads(l)
        except Exception: pass

LO = calendar.timegm((2026, 8, 26, 8, 0, 0))
# ★ E-0908 NAME COLLISION (anchor_loop.py L1826-1834, the code's own receipt): from 2026-09-05
#   12:00Z to 2026-09-08 04Z the ledger's `reshape` field silently carried the REJECT-RATE report
#   (`_rr`) instead of the withhold report (`_rs`) — same local name. Zero book impact; the loss
#   was the record. The STABLE selector is structural, not by date: a genuine withhold report
#   carries `sizing_gross` and `popped_names`. Contaminated rows are enumerated, not silently
#   dropped (never infer semantics from a filename or a date range).
rows = {}; CONTAM = {}
for p in sorted(glob.glob(f"{LIVEROOT}/state/live/pilot_log/2026*/anchors.jsonl")):
    for r in jl(p):
        rs = r.get("reshape")
        if not rs: continue
        a = int(round(float(r["anchor_ts"]) / H) * H)
        if a < LO: continue
        if "sizing_gross" in rs and "popped_names" in rs:
            rows[a] = r                              # last row for the anchor wins
        else:
            CONTAM[a] = sorted(rs.keys())[:6]
ANCH = sorted(rows)
CONTAM_REC = dict(n=len(CONTAM),
                  anchors_utc=[time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t)) for t in sorted(CONTAM)],
                  sample_keys=CONTAM[sorted(CONTAM)[0]] if CONTAM else None,
                  cause="E-0908 `_rs` name collision with the reject-rate summariser; "
                        "anchor_loop.py L1826-1834 is the code's own receipt. Book unaffected.")

# ══ S1..S4, S6 empirical ═════════════════════════════════════════════════════════════════════
S = []
for a in ANCH:
    rs = rows[a]["reshape"]; g = float(rs["sizing_gross"])
    S.append(dict(ts=a, net_before=float(rs["net_before"]), net_after=float(rs["net_after"]),
                  gross_before=float(rs["gross_before"]), gross_after=float(rs["gross_after"]),
                  sizing_gross=g, mxdpp=float(rs["max_name_delta_pp"]),
                  n_popped=int(rs.get("n_popped", 0)),
                  n_clamped=len((rs.get("clamped_after_reshape") or {}).get("names", [])),
                  book_net=float((rs.get("clamped_after_reshape") or {}).get("book_net_usdt", 0.0)),
                  nog=float(rows[a].get("net_over_gross") or np.nan),
                  gross_in=float((rows[a].get("external_book") or {}).get("gross_in") or np.nan)))
A_ = {k: np.array([s[k] for s in S], float) for k in S[0]}
S1 = dict(max_abs_net_after_over_gross=float(np.abs(A_["net_after"] / A_["sizing_gross"]).max()),
          threshold=1e-12, n=len(S))
S1["PASS"] = bool(S1["max_abs_net_after_over_gross"] <= 1e-12)
S2 = dict(max_rel_gross_err=float(np.abs(A_["gross_after"] / A_["sizing_gross"] - 1.0).max()),
          threshold=1e-9)
S2["PASS"] = bool(S2["max_rel_gross_err"] <= 1e-9)
_nb = A_["net_before"] / A_["sizing_gross"]
S4_nopop = A_["n_popped"] == 0
S4 = dict(n_anchors_with_zero_pops=int(S4_nopop.sum()),
          n_zero_pop_anchors_still_corrected=int((S4_nopop & (np.abs(_nb) > 1e-9)).sum()),
          verdict="unconditional" if (S4_nopop.sum() == 0 or (S4_nopop & (np.abs(_nb) > 1e-9)).any())
                  else "pop_gated")
NETB = dict(mean_pct=float(_nb.mean() * 100), median_pct=float(np.median(_nb) * 100),
            p05_pct=float(np.percentile(_nb, 5) * 100), p95_pct=float(np.percentile(_nb, 95) * 100),
            max_abs_pct=float(np.abs(_nb).max() * 100), n_negative=int((_nb < 0).sum()), n=len(S))
GROSSB = dict(mean_ratio_before_over_sizing=float((A_["gross_before"] / A_["sizing_gross"]).mean()),
              min_ratio=float((A_["gross_before"] / A_["sizing_gross"]).min()),
              max_ratio=float((A_["gross_before"] / A_["sizing_gross"]).max()))
MXD = dict(mean_pp=float(A_["mxdpp"].mean()), median_pp=float(np.median(A_["mxdpp"])),
           max_pp=float(A_["mxdpp"].max()), min_pp=float(A_["mxdpp"].min()))
POPS = dict(mean_n_popped=float(A_["n_popped"].mean()), max_n_popped=int(A_["n_popped"].max()),
            min_n_popped=int(A_["n_popped"].min()),
            mean_n_clamped=float(A_["n_clamped"].mean()))
CLAMPRES = dict(mean_book_net_over_gross=float((A_["book_net"] / A_["sizing_gross"]).mean()),
                max_abs_book_net_over_gross=float(np.abs(A_["book_net"] / A_["sizing_gross"]).max()),
                note="net AFTER the venue clamps, i.e. what actually reached the venue as a dollar tilt")

# ══ P0 · reconstruct the pre-reshape book from the producer file ══════════════════════════════
def prod_file(a):
    p = f"{WS}/state/target_live/{a}.json"
    if not os.path.exists(p): return None
    try: return json.load(open(p))
    except Exception: return None

P0 = []; REC = {}
for a in ANCH:
    d = prod_file(a)
    if d is None: continue
    rs = rows[a]["reshape"]; g = float(rs["sizing_gross"])
    uni = set(d["universe"]); w = {s: float(v) for s, v in d["weights"].items() if s in uni}
    gin = sum(abs(v) for v in w.values())
    if gin <= 0: continue
    tgt = {s: v / gin * g for s, v in w.items() if abs(v / gin) > 1e-12}
    for s in rs.get("popped_names", ()): tgt.pop(s, None)
    nb, gb = sum(tgt.values()), sum(abs(v) for v in tgt.values())
    P0.append(dict(ts=a, nb_rec=nb, nb_led=float(rs["net_before"]),
                   gb_rec=gb, gb_led=float(rs["gross_before"]),
                   rel_nb=abs(nb - float(rs["net_before"])) / max(abs(float(rs["net_before"])), 1e-9),
                   rel_gb=abs(gb - float(rs["gross_before"])) / max(float(rs["gross_before"]), 1e-9),
                   n=len(tgt)))
    REC[a] = tgt
P0ok = [r for r in P0 if r["rel_nb"] <= 1e-6 and r["rel_gb"] <= 1e-6]
P0PASS = {r["ts"] for r in P0ok}
P0S = dict(n_files=len(P0), n_parity_pass=len(P0ok), threshold_rel=1e-6, required_n=30,
           PASS=bool(len(P0ok) >= 30),
           median_rel_nb=float(np.median([r["rel_nb"] for r in P0])) if P0 else None,
           median_rel_gb=float(np.median([r["rel_gb"] for r in P0])) if P0 else None,
           max_rel_nb=float(max(r["rel_nb"] for r in P0)) if P0 else None,
           max_rel_gb=float(max(r["rel_gb"] for r in P0)) if P0 else None)
PANCH = sorted(r["ts"] for r in P0ok)
PALL = sorted(REC)

# ══ the deployed reshape, called on a name->usdt dict, exactly as anchor_loop does ════════════
def deployed_reshape(tgt, g):
    syms = sorted(tgt)
    vec = np.array([tgt[s] / g for s in syms], float)
    rs = LG.reshape_after_withhold(vec, sizing_gross=g, redemean=True, rescale=True,
                                   floors_usdt=None, strict=True)
    return syms, np.asarray(rs["w"], float), rs

def my_reshape(vec):                                  # S3 independent re-implementation
    w = np.asarray(vec, float) - np.mean(vec)
    s = np.abs(w).sum()
    return w / s if s > 0 else w

S3max = 0.0
for a in PALL:
    g = float(rows[a]["reshape"]["sizing_gross"])
    syms, wo, _ = deployed_reshape(REC[a], g)
    vin = np.array([REC[a][s] / g for s in syms], float)
    S3max = max(S3max, float(np.abs(wo - my_reshape(vin)).max()))
S3 = dict(max_abs_delta=S3max, threshold=1e-15, PASS=bool(S3max <= 1e-15),
          semantics="w -> (w - mean(w)) / L1(w - mean(w)); global affine, per-name only through "
                    "the one shared mean and the one shared scale")

# ══ betas from the local 5m panel (for FORM B construction and B3 turnover) ═══════════════════
Z = np.load(f"{WS}/state/rolling.npz", allow_pickle=True)
PTS = Z["ts"].astype(np.int64); R5 = Z["data"][:, :, 0].astype(np.float32)
CFG = json.load(open(f"{WS}/shadow_bundle/config.json"))
SP = [str(s) for s in CFG["symbols_panel"]]; PIDX = {s: i for i, s in enumerate(SP)}
TPOS = {int(t): i for i, t in enumerate(PTS)}
OFF = 6                                               # verified in beta_neutrality_2026-09-11.py
def pret(a):
    i0 = TPOS.get(a + OFF * 300); i1 = TPOS.get(a + H + OFF * 300 - 300)
    if i0 is None or i1 is None: return None
    b = R5[i0:i1 + 1]
    bad = np.isnan(b).any(axis=0)
    r = np.nansum(b, axis=0).astype(np.float64); r[bad] = np.nan
    return r
RET = {}
_t = int(PTS[0]) - int(PTS[0]) % H
while _t <= int(PTS[-1]):
    v = pret(_t)
    if v is not None: RET[_t] = v
    _t += H
RTS = sorted(RET)
RMAT = np.array([RET[t] for t in RTS])                # (T, 829)
AEW = np.nanmean(RMAT, axis=1)                        # equal-weight cross-section, panel caliber
WBETA = 60
def betas_at(a):
    """trailing WBETA anchors STRICTLY BEFORE a; cov(y_i, A)/var(A). NaN where <0.8W obs."""
    js = [j for j, t in enumerate(RTS) if t < a][-WBETA:]
    if len(js) < int(0.8 * WBETA): return None
    Y = RMAT[js]; A = AEW[js]
    ok = np.isfinite(A); Y = Y[ok]; A = A[ok]
    Am = A - A.mean(); va = float((Am * Am).sum())
    if va <= 0: return None
    n_ok = np.isfinite(Y).sum(axis=0)
    Yf = np.where(np.isfinite(Y), Y, np.nan)
    Ym = Yf - np.nanmean(Yf, axis=0)
    cov = np.nansum(Ym * Am[:, None], axis=0)
    b = cov / va
    b[n_ok < int(0.8 * len(A))] = np.nan
    return b

# ══ FORM A and FORM B ════════════════════════════════════════════════════════════════════════
def halves(w):
    L = w > 0; Sh = w < 0
    return L, Sh
def bstats(w, bt):
    L, Sh = halves(w)
    ok = np.isfinite(bt)
    gL = w[L].sum(); gS = -w[Sh].sum()
    bL = float((w[L & ok] * bt[L & ok]).sum() / max(w[L & ok].sum(), 1e-12))
    bS = float((-w[Sh & ok] * bt[Sh & ok]).sum() / max(-w[Sh & ok].sum(), 1e-12))
    return float(gL), float(gS), bL, bS, float(np.nansum(w[ok] * bt[ok]))

def form_A(w, d):
    o = w.copy(); L, Sh = halves(w)
    o[L] *= (1.0 + d); o[Sh] *= (1.0 - d)
    return o

def form_B(w, bt, frac=1.0, kmax=0.95):
    """within-half re-weighting, each half's dollar sum EXACTLY fixed, closing frac of the gap."""
    o = w.copy(); L, Sh = halves(w); ok = np.isfinite(bt)
    Lo = L & ok; So = Sh & ok
    gL = w[Lo].sum(); gS = -w[So].sum()
    if gL <= 0 or gS <= 0: return o, None
    bL = (w[Lo] * bt[Lo]).sum() / gL; bS = (-w[So] * bt[So]).sum() / gS
    vL = (w[Lo] * (bt[Lo] - bL) ** 2).sum() / gL
    vS = (-w[So] * (bt[So] - bS) ** 2).sum() / gS
    if vL <= 0 or vS <= 0: return o, None
    delta = (bL - bS) * frac
    kL = -delta / (2.0 * vL); kS = +delta / (2.0 * vS)
    tL = kL * (bt[Lo] - bL); tS = kS * (bt[So] - bS)
    cap = max(np.abs(tL).max(), np.abs(tS).max())
    sc = 1.0 if cap <= kmax else kmax / cap
    o[Lo] = w[Lo] * (1.0 + sc * tL)
    o[So] = w[So] * (1.0 + sc * tS)                   # w<0; |a_j| scaled identically
    return o, dict(kL=float(kL), kS=float(kS), scale=float(sc), bL=float(bL), bS=float(bS),
                   varL=float(vL), varS=float(vS), gap=float(bL - bS), capped=bool(sc < 1.0))

DS = [0.01, 0.05, 0.10, 0.20]
LAD = []
Arows = {d: [] for d in DS}; Brows = []; Brows_pre = []; A2rows = []; A3rows = []
RESHAPE_BETA = []
for a in PALL:
    g = float(rows[a]["reshape"]["sizing_gross"])
    syms = sorted(REC[a]); vin = np.array([REC[a][s] / g for s in syms], float)
    bt = betas_at(a)
    if bt is None: continue
    bv = np.array([bt[PIDX[s]] if s in PIDX else np.nan for s in syms], float)
    if np.isfinite(bv).sum() < 100: continue
    w0 = my_reshape(vin)                              # the book the executor actually deploys
    # --- what the CURRENT reshape does to the book's beta (uncontrolled, new fact) ---
    _, _, bL0, bS0, bb0 = bstats(vin / np.abs(vin).sum(), bv)
    _, _, bL1, bS1, bb1 = bstats(w0, bv)
    _bbar = float(np.nanmean(bv)); _netg = float(vin.sum() / np.abs(vin).sum())
    RESHAPE_BETA.append(dict(ts=a, pred_d_beta=-_netg * _bbar * float(np.isfinite(bv).sum()) / len(bv) * len(bv) / max(np.isfinite(bv).sum(), 1),
                             beta_bar=_bbar,
                             identity_resid=abs((bb1 - bb0) - (-_netg * _bbar)),
                             book_beta_before=bb0, book_beta_after=bb1,
                             d_book_beta=bb1 - bb0, gap_before=bL0 - bS0, gap_after=bL1 - bS1,
                             d_gap=(bL1 - bS1) - (bL0 - bS0),
                             net_over_gross_before=float(vin.sum() / np.abs(vin).sum())))
    # --- FORM A: inject into the producer-shaped (net-tilted) book AND into the self-reshaped one
    for d in DS:
        for tag, base in (("on_combo_raw", vin / np.abs(vin).sum()), ("on_selfreshaped", w0)):
            wa = form_A(base, d)
            gLa, gSa, _, _, _ = bstats(wa, bv)
            _ta = {s_: float(wa[m_] * g) for m_, s_ in enumerate(syms) if abs(wa[m_]) > 1e-12}
            _sa, _wa_out, _ = deployed_reshape(_ta, g)      # THE DEPLOYED FUNCTION
            wout = np.zeros_like(wa); _pm = {s_: m_ for m_, s_ in enumerate(syms)}
            for _m2, s_ in enumerate(_sa): wout[_pm[s_]] = _wa_out[_m2]
            gLo, gSo, _, _, _ = bstats(wout, bv)
            Arows[d].append(dict(ts=a, tag=tag, p0=a in P0PASS, tilt_in=gLa - gSa,
                                 tilt_out=gLo - gSo, S_A=(gLo - gSo) / d))
    # --- A2: what actually survives a FORM A injection
    wa = form_A(w0, 0.05); wao = my_reshape(wa)
    A2rows.append(dict(ts=a, max_abs_delta_pp=float(np.abs(wao - w0).max() * 100),
                       typ_name_pp=float(np.median(np.abs(w0[np.abs(w0) > 1e-9])) * 100),
                       corr_with_absw=float(np.corrcoef(wao - w0, np.abs(w0))[0, 1])))
    # --- A3: affine invariance of ratios of differences
    nzi = np.where(np.abs(w0) > 1e-9)[0][:4]
    if len(nzi) == 4:
        i, j, k, l = nzi
        r_in = (vin[i] - vin[j]) / (vin[k] - vin[l])
        r_out = (w0[i] - w0[j]) / (w0[k] - w0[l])
        A3rows.append(dict(ts=a, rel=abs(r_out - r_in) / max(abs(r_in), 1e-12)))
    # --- FORM B DOSE LADDER: incremental turnover vs fraction of the gap closed
    for _f in (0.25, 0.50, 0.75, 1.00):
        _wbf, _inf = form_B(w0, bv, _f)
        if _inf is not None:
            LAD.append(dict(ts=a, frac=_f, turn_delta=float(np.abs(_wbf - w0).sum()),
                            capped=_inf["capped"]))
    # --- FORM B on the self-reshaped book (the shape a producer can emit)
    wb, info = form_B(w0, bv, 1.0)
    if info is None: continue
    syms_b = syms
    tb = {s: float(wb[m] * g) for m, s in enumerate(syms_b) if abs(wb[m]) > 1e-12}
    _sy, wbo, rsb = deployed_reshape(tb, g)
    wbo_full = np.zeros_like(wb)
    _pos = {s: m for m, s in enumerate(syms_b)}
    for m2, s in enumerate(_sy): wbo_full[_pos[s]] = wbo[m2]
    SB = float(np.abs(wbo_full - wb).max() * g)
    gLb, gSb, bLb, bSb, bbb = bstats(wb, bv)
    gLo, gSo, bLo, bSo, bbo = bstats(wbo_full, bv)
    Brows.append(dict(ts=a, p0=a in P0PASS, S_B_usdt=SB, gap_in=bLb - bSb, gap_out=bLo - bSo,
                      gap_base=bL1 - bS1,
                      rel_gap_err=abs((bLo - bSo) - (bLb - bSb)) / max(abs(bL1 - bS1), 1e-12),
                      net_in=float(wb.sum()), gross_in=float(np.abs(wb).sum()),
                      turn_delta=float(np.abs(wb - w0).sum()), capped=info["capped"],
                      scale=info["scale"], varL=info["varL"], varS=info["varS"]))
    # --- FORM B applied to the CURRENT producer shape (net-tilted) -> reshape is NOT identity
    wbp, info2 = form_B(vin / np.abs(vin).sum(), bv, 1.0)
    if info2 is not None:
        wbpo = my_reshape(wbp)
        _, _, bLp, bSp, _ = bstats(wbp, bv)
        _, _, bLpo, bSpo, _ = bstats(wbpo, bv)
        Brows_pre.append(dict(ts=a, S_B_usdt=float(np.abs(wbpo - wbp).max() * g),
                              gap_in=bLp - bSp, gap_out=bLpo - bSpo))

def agg(rs, k):
    v = np.array([r[k] for r in rs], float); v = v[np.isfinite(v)]
    return dict(n=int(v.size), mean=float(v.mean()), median=float(np.median(v)),
                p05=float(np.percentile(v, 5)), p95=float(np.percentile(v, 95)),
                min=float(v.min()), max=float(v.max())) if v.size else None

A1 = {}
for d in DS:
    for tag in ("on_combo_raw", "on_selfreshaped"):
        sub = [r for r in Arows[d] if r["tag"] == tag]
        s0 = [r for r in sub if r["p0"]]
        A1[f"d={d}|{tag}"] = dict(S_A=agg(sub, "S_A"), tilt_out=agg(sub, "tilt_out"),
                                  S_A_p0_only=agg(s0, "S_A"), n_all=len(sub), n_p0=len(s0))
mA = A1.get("d=0.05|on_selfreshaped", {}).get("S_A", {}) or {}
A1V = dict(median_S_A_at_0p05=mA.get("median"),
           verdict=("YES" if (mA.get("median") or 0) >= 0.50 else
                    "NO" if abs(mA.get("median") or 0) <= 0.01 else "ONLY_WITH_EXECUTOR_CHANGE"))
B1 = agg(Brows, "S_B_usdt")
B1_p0 = agg([r for r in Brows if r["p0"]], "S_B_usdt")
B1V = dict(max_S_B_usdt=B1["max"] if B1 else None, threshold_usdt=1e-6,
           verdict=("YES" if (B1 and B1["max"] <= 1e-6) else "NO"))
B2 = agg(Brows, "rel_gap_err")
B3turn = agg(Brows, "turn_delta")
COSTB = json.load(open(os.path.join(R13, "..", "r3k_impact", "costb_PWR_G230k.json")))
BPS = float(COSTB["book_avg_bps_per_unit_turnover"])
B3 = dict(delta_turnover_matched=B3turn,
          A0_matched_turnover_reference=0.0540270,
          bps_per_unit_turnover_fitted=BPS,
          delta_cost_bps_fitted=(B3turn["mean"] * BPS) if B3turn else None,
          delta_cost_bps_repriced_3p2167=(B3turn["mean"] * BPS * 3.2167) if B3turn else None,
          dose_ladder={str(f): dict(turn_delta=agg([r for r in LAD if r["frac"] == f], "turn_delta"),
                                    n_capped=sum(1 for r in LAD if r["frac"] == f and r["capped"]),
                                    cost_bps_fitted=(agg([r for r in LAD if r["frac"] == f], "turn_delta") or {}).get("mean", 0) * BPS,
                                    cost_bps_x3p2167=(agg([r for r in LAD if r["frac"] == f], "turn_delta") or {}).get("mean", 0) * BPS * 3.2167)
                       for f in (0.25, 0.50, 0.75, 1.00)},
          costb_sha256=hashlib.sha256(open(os.path.join(R13, "..", "r3k_impact",
                                                        "costb_PWR_G230k.json"), 'rb').read()).hexdigest(),
          note="turnover caliber = sum|dw| with sum|w|=1, i.e. turnover/gross_total, the MATCHED "
               "caliber (A0 = 0.0540270). The un-normalised receipt field 0.03032 is NOT this.")
RB = dict(identity_resid=agg(RESHAPE_BETA, "identity_resid"), beta_bar=agg(RESHAPE_BETA, "beta_bar"),
          identity="d(book beta) = -(net/gross) x mean_i(beta_i) exactly, because redemean is a "
                   "UNIFORM additive shift of -mean(w) applied to every name",
          d_book_beta=agg(RESHAPE_BETA, "d_book_beta"), d_gap=agg(RESHAPE_BETA, "d_gap"),
          net_over_gross_before=agg(RESHAPE_BETA, "net_over_gross_before"),
          book_beta_before=agg(RESHAPE_BETA, "book_beta_before"),
          book_beta_after=agg(RESHAPE_BETA, "book_beta_after"),
          gap_before=agg(RESHAPE_BETA, "gap_before"), gap_after=agg(RESHAPE_BETA, "gap_after"))

RCP = dict(
    device=os.path.basename(__file__),
    device_sha256=hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest(),
    prereg_sha256=PREREG_SHA, prereg_asserted=True,
    deployed_legs_sha256=LEGS_SHA, deployed_anchor_loop_sha256=AL_SHA, producer_combo_stage_sha256=CS_SHA,
    window="W_LIVE_DEPLOY", window_lo_utc="2026-08-26T08:00:00Z",
    n_anchors_with_reshape=len(ANCH),
    first_anchor=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ANCH[0])),
    last_anchor=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ANCH[-1])),
    contaminated_reshape_rows=CONTAM_REC,
    S1=S1, S2=S2, S3=S3, S4=S4, S5=S5, S6_src=S6_src, P0=P0S, n_P0_anchors=len(PANCH), n_injection_anchors=len(PALL),
    net_before_over_gross_pct=NETB, gross_before_ratio=GROSSB, max_name_delta_pp=MXD,
    pops=POPS, clamp_residual=CLAMPRES,
    A1=A1, A1_VERDICT=A1V, A2=dict(max_abs_delta_pp=agg(A2rows, "max_abs_delta_pp"),
                                   typical_name_pp=agg(A2rows, "typ_name_pp"),
                                   corr_delta_vs_absw=agg(A2rows, "corr_with_absw")),
    A3=dict(rel_change_of_difference_ratio=agg(A3rows, "rel")),
    B1=B1, B1_p0_only=B1_p0, B1_VERDICT=B1V, B2_rel_gap_err=B2, B3_cost=B3,
    B_on_current_producer_shape=dict(S_B_usdt=agg(Brows_pre, "S_B_usdt"),
                                     gap_in=agg(Brows_pre, "gap_in"), gap_out=agg(Brows_pre, "gap_out")),
    reshape_moves_book_beta=RB,
    beta_window_anchors=WBETA, beta_panel="wide_shadow/state/rolling.npz ch0 5m simple return, "
                                          "sum over the +30min-shifted 4h window (E-0904-F: no expm1)",
    env=ENV, built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
os.makedirs(OUT, exist_ok=True)
json.dump(RCP, open(f"{OUT}/RECEIPT_r13_reshape.json", "w"), indent=1, default=float)
json.dump(dict(per_anchor_S=S, P0=P0, B=Brows, RB=RESHAPE_BETA),
          open(f"{OUT}/r13_reshape_rows.json", "w"), indent=0, default=float)
print(json.dumps({k: v for k, v in RCP.items() if k != "env"}, indent=1, default=float))
