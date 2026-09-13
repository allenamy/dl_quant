#!/usr/bin/env python3
"""t5_live_ingredients.py — Mac, READ-ONLY copies under T5/private/live (PREREG_T5 §4.4 D versions, §6 G-ING-V / G-ING-S / G-ARCH-D).
Builds the deployed-book (D) ingredients on the 30-anchor simulation calendar 2026-08-26 00Z..08-30 20Z (+ states entering from 08-25 20Z):
  pm (members, weights/<A>.npz), LIVE (universe list of the king file), w3m (target_combo w3_masked), qv4h_D / sel_D (producer rolling cache,
  same float32 ops as shadow_loop_v3 pre-M1 L376-379 / combo_stage L41-44), feD (producer fund EMA acc at A by exact backward inversion of
  shadow_loop_v3 L344-349 from the 2026-09-04 00Z aux snapshot; live names with last settlement <= 12h, else NaN), warm-start states,
  archived chain states sm_kc / sm_fc, target_live weights (also 08-31 00Z..09-10 00Z for TC2).
Launch: env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5_live_ingredients.py <T5 dir> PATH,HOME
"""
import os, sys, json, time, hashlib
T5 = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import rankdata
PREREG_SHA = "33b20fa10109b95d9b4f0ff480619d82cd9bd1b7d2def7cf0a38c7938e83660f"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(T5 + "/PREREG_T5_deployed_carry_gap_2026-09-13.md") == PREREG_SHA, "prereg sha"
L = T5 + "/private/live"; t0 = time.time()
u = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
cfg = json.load(open(L + "/bundle_aug_backup/config.json")); SP = [str(s) for s in cfg["symbols_panel"]]; LV = [str(s) for s in cfg["symbols_live"]]; P = cfg["params"]
assert [str(s) for s in np.load(L + "/xfer_ref.npz", allow_pickle=True)["symbols"]] == SP
NW = len(SP); sidx = {s: i for i, s in enumerate(SP)}
CAL = [1787702400 + 14400 * k for k in range(30)]          # 08-26 00Z .. 08-30 20Z
PRE = 1787688000                                           # 08-25 20Z
AT5 = [a for a in CAL if a not in (1787702400, 1788033600, 1788048000)]
assert len(AT5) == 27
E2A = [a for a in range(1788134400, 1788998400 + 1, 14400)]  # 08-31 00Z .. 09-10 00Z
def load_state(p):
    z = np.load(p); v = np.zeros(NW); v[z["idx"].astype(np.int64)] = z["val"].astype(np.float64); return int(z["anchor"]) if "anchor" in z.files else None, v
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
# ---------------------------------------------------------------- per-anchor metadata, members, seats, chain states, target_live
nC = len(CAL)
meta = []; PM = np.zeros((nC, NW), bool); W3M = np.full((nC, 3), np.nan); KC = np.full((nC, NW), np.nan); FC = np.full((nC, NW), np.nan)
WTL = np.full((nC, NW), np.nan); LIVE = None; is_combo = np.zeros(nC, bool); has_w = np.zeros(nC, bool); KING_NZ = np.zeros((nC, NW), bool)
for k, A in enumerate(CAL):
    m = dict(A=A, utc=u(A))
    pw = f"{L}/weights/{A}.npz"
    if os.path.exists(pw):
        z = np.load(pw); PM[k, z["members"].astype(np.int64)] = True; has_w[k] = True
        KING_NZ[k, z["idx"].astype(np.int64)] = z["val"] != 0
        m["n_members"] = int(len(z["members"]))
    ptl = f"{L}/target_live/{A}.json"
    if os.path.exists(ptl):
        d = json.load(open(ptl)); m["producer"] = d.get("producer"); m["booster_sha"] = d.get("booster_sha")
        is_combo[k] = "combo_stage" in str(d.get("producer"))
        w = np.zeros(NW)
        for s, x in d["weights"].items(): w[sidx[s]] += float(x)
        WTL[k] = w
        lv = [str(s) for s in d["universe"]]
        if LIVE is None: LIVE = lv
        assert lv == LIVE, ("universe changed", u(A))
    ptc = f"{L}/target_combo/{A}.json"
    if os.path.exists(ptc):
        d = json.load(open(ptc)); W3M[k] = d["w3_masked"]; m["kc_src"] = d["kc_state_source"]; m["fc_src"] = d["fc_state_source"]; m["ftrim_key"] = "ftrim" in d
    for nm, arr in (("kc", KC), ("fc", FC)):
        p = f"{L}/fea171_states/state_H_{nm}_{A}.npz"
        if os.path.exists(p):
            an, v = load_state(p); assert an == A, (p, an); arr[k] = v
    meta.append(m)
assert LIVE == LV, "universe list != config symbols_live"
LIVE_MASK = np.array([s in set(LIVE) for s in SP])
for k, A in enumerate(CAL): assert (A in AT5) == bool(is_combo[k] and np.isfinite(W3M[k]).all() and np.isfinite(KC[k]).all() and np.isfinite(FC[k]).all()), ("A_T5 rule", u(A))
# warm-start states (combo_stage L95-97 H = weights/<A-4h>; L186-196 H_f10_prev = state_H_f10_<A-4h>)
WARM = {}
for A in (1787702400, 1788062400):
    zw = np.load(f"{L}/weights/{A - 14400}.npz"); hk = np.zeros(NW); hk[zw["idx"].astype(np.int64)] = zw["val"].astype(np.float64)
    an, hf = load_state(f"{L}/fea171_states/state_H_f10_{A - 14400}.npz"); assert an == A - 14400
    WARM[A] = (hk, hf)
# G-ARCH-D: target_live == 0.55 kc + 0.45 fc on A_T5; own-state continuity
arch = {}
for k, A in enumerate(CAL):
    if A not in AT5: continue
    arch[u(A)] = float(np.abs(WTL[k] - (0.55 * KC[k] + 0.45 * FC[k])).max())
own_ok = all((meta[k].get("kc_src") == "own") == (CAL[k] not in (1787702400, 1788062400)) for k in range(nC) if CAL[k] in AT5 or CAL[k] == 1787702400)
G_ARCH_D = dict(max_abs_per_anchor=arch, max_abs=max(arch.values()), own_source_rule_ok=bool(own_ok), PASS=bool(max(arch.values()) <= 1e-9 and own_ok))
print("G-ARCH-D", G_ARCH_D["max_abs"], G_ARCH_D["PASS"], flush=True)
# ---------------------------------------------------------------- qv4h_D / sel_D from the producer rolling cache
RZ = np.load(L + "/rolling.npz", allow_pickle=True); rts = RZ["ts"].astype(np.int64); RD = RZ["data"]
QV = np.full((nC, NW), np.nan)
for k, A in enumerate(CAL):
    ai = int(np.searchsorted(rts, A, side="right")) - 1
    assert rts[ai] <= A < rts[ai] + 300 and rts[ai] == A, ("anchor row", u(A))
    CDf = RD[max(ai + 1 - 2016, 0):ai + 1, :, 3].astype(np.float32)
    finq = np.isfinite(CDf)
    qvm = np.where(finq, CDf, 0).sum(0) / np.maximum(finq.sum(0), 1)
    QV[k] = np.expm1(np.clip(qvm, 0, 30)) * 48
SEL = QV >= P["qv4h_min"]
# G-ING-S
siglog = {}
for ln in open(L + "/shadow_log.jsonl"):
    try: r = json.loads(ln)
    except Exception: continue
    if r.get("e") == "signal" and PRE <= int(r["anchor_ts"]) <= CAL[-1]: siglog[int(r["anchor_ts"])] = r
GS = {}
for k, A in enumerate(CAL):
    if not has_w[k]: continue
    viol = KING_NZ[k] & ~(PM[k] & SEL[k] & LIVE_MASK)
    nsel = int((PM[k] & SEL[k]).sum()); logged = siglog.get(A, {}).get("sel")
    GS[u(A)] = dict(nonzero_outside_pm_sel_live=int(viol.sum()), names=[SP[j] for j in np.where(viol)[0]][:10], sel_recon=nsel, sel_logged=logged, match=bool(logged == nsel))
G_ING_S = dict(per_anchor=GS, total_violations=int(sum(v["nonzero_outside_pm_sel_live"] for v in GS.values())), anchors_sel_count_mismatch=[a for a, v in GS.items() if not v["match"]])
G_ING_S["PASS"] = bool(G_ING_S["total_violations"] == 0 and not G_ING_S["anchors_sel_count_mismatch"])
print("G-ING-S", G_ING_S["total_violations"], G_ING_S["anchors_sel_count_mismatch"], G_ING_S["PASS"], flush=True)
# ---------------------------------------------------------------- producer fund EMA by backward inversion
def ema_back(aux, targets, names):
    """acc at each target anchor (after all settlements with ft <= target), exact inverse of acc_k = acc_{k-1} + a_k (rn_k - acc_{k-1});
    returns dict target -> (acc array over names, last settlement ft array)."""
    led = aux["ledger_tail"]; ema = aux["ema"]
    out = {T: (np.full(len(names), np.nan), np.full(len(names), np.nan)) for T in targets}
    info = dict(n_names=0, n_no_rows=0, n_rows_too_short=0)
    for q, s in enumerate(names):
        rows = led.get(s) or []; est = ema.get(s)
        if not rows or not est: info["n_no_rows"] += 1; continue
        ft = np.array([float(r[0]) for r in rows]); rate = np.array([float(r[1]) for r in rows]); iv = np.array([float(r[2]) for r in rows])
        assert np.all(np.diff(ft) > 0), s
        assert abs(float(est["last_ts"]) - ft[-1]) < 1e-6, (s, est["last_ts"], ft[-1])
        acc = float(est["acc"]); kk = len(ft) - 1
        for T in sorted(targets, reverse=True):
            while kk >= 1 and ft[kk] > T:
                a = 1 - 0.5 ** (max(ft[kk] - ft[kk - 1], 1) / (3 * 86400.0)); rn = rate[kk] * (8.0 / iv[kk])
                acc = (acc - a * rn) / (1 - a); kk -= 1
            if ft[kk] > T: info["n_rows_too_short"] += 1; continue
            out[T][0][q] = acc; out[T][1][q] = ft[kk]
        info["n_names"] += 1
    return out, info
AUX04 = json.load(open(L + "/aux_pre_m1_20260904.json")); AUX13 = json.load(open(L + "/aux.json"))
assert int(AUX04["prev_rec"]["anchor_ts"]) == 1788480000
# G-ING-V: 09-13 snapshot -> 09-04 00Z, compare legz["fund"] = nan_to_num(xz(fe_v[m])) stored at 09-04 00Z
T04 = 1788480000
back, infoV = ema_back(AUX13, [T04], SP)
acc_rec, ftl = back[T04]
fe_rec = np.where(np.isfinite(ftl) & (T04 - ftl <= 12 * 3600) & LIVE_MASK, acc_rec, np.nan)
m04 = np.array(AUX04["prev_rec"]["members"], np.int64); z_st = np.array(AUX04["prev_rec"]["legz"]["fund"], np.float64)
z_rec = np.nan_to_num(xz(fe_rec[m04]))
acc_true = np.array([float(AUX04["ema"][s]["acc"]) if s in AUX04["ema"] else np.nan for s in SP])
rel = np.abs(acc_rec - acc_true) / np.maximum(np.abs(acc_true), 1e-12); relm = rel[LIVE_MASK & np.isfinite(rel)]
G_ING_V = dict(max_abs_dz_members=float(np.abs(z_rec - z_st).max()), n_members_dz_gt_1e9=int((np.abs(z_rec - z_st) > 1e-9).sum()), acc_rel_err_max=float(relm.max()), acc_rel_err_p99=float(np.percentile(relm, 99)),
               acc_exact_equal_share=float(np.mean(acc_rec[LIVE_MASK] == acc_true[LIVE_MASK])), info=infoV)
G_ING_V["PASS"] = bool(G_ING_V["max_abs_dz_members"] <= 1e-9)
print("G-ING-V", json.dumps({k: v for k, v in G_ING_V.items() if k != "info"}), flush=True)
# feD on the calendar from the 09-04 00Z snapshot
backC, infoC = ema_back(AUX04, CAL, SP)
FED = np.full((nC, NW), np.nan); FTLAST = np.full((nC, NW), np.nan)
for k, A in enumerate(CAL):
    acc, ftl_ = backC[A]; FTLAST[k] = ftl_
    FED[k] = np.where(np.isfinite(ftl_) & (A - ftl_ <= 12 * 3600) & LIVE_MASK, acc, np.nan)
# TC2 deployed weights on E2a
WE2 = []; E2_ok = []; E2_prod = []
for A in E2A:
    p = f"{L}/target_live/{A}.json"
    if not os.path.exists(p): continue
    d = json.load(open(p)); w = np.zeros(NW)
    for s, x in d["weights"].items(): w[sidx[s]] += float(x)
    WE2.append(w); E2_ok.append(A); E2_prod.append(str(d.get("producer")))
out = T5 + "/receipts/T5_live_ingredients.npz"
np.savez_compressed(out, symbols=np.array(SP), cal=np.array(CAL, np.int64), at5=np.array(AT5, np.int64), is_combo=is_combo, has_weights=has_w, PM=PM, LIVE=LIVE_MASK, W3M=W3M,
                    QV=QV, SEL=SEL, FED=FED, FTLAST=FTLAST, KC=KC, FC=FC, WTL=WTL, WARM_0826_kc=WARM[1787702400][0], WARM_0826_fc=WARM[1787702400][1], WARM_0830_kc=WARM[1788062400][0], WARM_0830_fc=WARM[1788062400][1],
                    E2A=np.array(E2_ok, np.int64), WE2=np.array(WE2), E2A_producer=np.array(E2_prod), KING_NZ=KING_NZ)
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, meta=meta, G_ARCH_D=G_ARCH_D, G_ING_S=G_ING_S, G_ING_V=G_ING_V, feD_info=infoC,
          n_E2a_files=len(E2_ok), E2a_first=u(E2_ok[0]), E2a_last=u(E2_ok[-1]), inputs={os.path.relpath(p, T5): sha(p) for p in (L + "/bundle_aug_backup/config.json", L + "/rolling.npz", L + "/aux_pre_m1_20260904.json", L + "/aux.json", L + "/shadow_log.jsonl")},
          copy_manifest_sha256=sha(T5 + "/private/COPY_SHA256.txt"), out=os.path.relpath(out, T5), out_sha256=sha(out),
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), python=sys.version.split()[0], numpy=np.__version__, built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(T5 + "/receipts/RECEIPT_T5_live_ingredients.json", "w"), indent=1, default=str)
print("DONE t5_live_ingredients", RC["wall_s"], "s; E2a files", len(E2_ok))
