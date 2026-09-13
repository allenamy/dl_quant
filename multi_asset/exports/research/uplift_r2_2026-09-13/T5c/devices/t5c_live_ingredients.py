#!/usr/bin/env python3
"""t5c_live_ingredients.py — Mac, READ-ONLY copies under T5c/private/live (PREREG_T5c §5 D versions, §7 G-ARCH-D / G-ING-V / G-ING-B / G-ING-S / G-ING-T).
Calendar = 2026-08-30 04Z .. 2026-09-10 00Z (66 anchors; states enter from 08-30 00Z). Builds for every anchor: members pm, LIVE, w3m, sel_D (producer
rolling cache, shadow_loop_v3 L376-379 float32 ops), producer fund EMA of live names with a settlement <= 12h (exact backward inversion of L344-349;
09-04 00Z snapshot for A <= 09-04 00Z, 09-13 04Z snapshot after), the M1 base distribution (base_syms, EMA exists, settlement <= 12h; incl. names
off the 829 axis) for A >= 09-04 04Z, ledger rn8 (last settlement <= A: rate x 8/iv, combo_stage FTRIM input), archived kc / fc / f10 states,
target_live weights, the 08-30 04Z warm-start state.
Launch: env -i PATH=/usr/bin:/bin HOME=$HOME /usr/bin/python3 devices/t5c_live_ingredients.py <T5c dir> CPATH,HOME,LC_CTYPE,LIBRARY_PATH,MANPATH,PATH,SDKROOT,__CF_USER_TEXT_ENCODING
"""
import os, sys, json, time, hashlib
T = os.path.abspath(sys.argv[1]); WHITE = set(x for x in sys.argv[2].split(",") if x)
assert WHITE and sorted(k for k in os.environ if k not in WHITE) == [], ("ENV WHITELIST VIOLATION", sorted(os.environ))
import numpy as np
from scipy.stats import rankdata
PREREG_SHA = "a669c62782c58d424eed17cf3c7b2a8ad78050c059f43cb2e6496737eaf56a48"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
assert sha(T + "/PREREG_T5c_september_replay_vs_deployed_2026-09-13.md") == PREREG_SHA, "prereg sha"
L = T + "/private/live"; t0 = time.time()
u = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
cfg = json.load(open(L + "/bundle_aug_backup/config.json")); SP = [str(s) for s in cfg["symbols_panel"]]; LV = [str(s) for s in cfg["symbols_live"]]; P = cfg["params"]
cfg2 = json.load(open(L + "/bundle_current/config.json"))
assert cfg2["symbols_panel"] == cfg["symbols_panel"] and cfg2["symbols_live"] == cfg["symbols_live"] and cfg2["params"] == cfg["params"], "bundle config changed within window"
assert [str(s) for s in np.load(L + "/xfer_ref.npz", allow_pickle=True)["symbols"]] == SP
NW = len(SP); sidx = {s: i for i, s in enumerate(SP)}
PRE = 1788048000; CAL = [1788062400 + 14400 * k for k in range(66)]; assert CAL[-1] == 1788998400
WIN = [a for a in CAL if a >= 1788134400]; assert len(WIN) == 61
FTRIM_ON = 1788350400; M1_ON = 1788494400; SEED_ON = 1788624000
nC = len(CAL)
def load_state(p):
    z = np.load(p); v = np.zeros(NW); v[z["idx"].astype(np.int64)] = z["val"].astype(np.float64); return (int(z["anchor"]) if "anchor" in z.files else None), v
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out
def xz_in_base(vm, names_m, base_vals):   # shadow_loop_v3.py (M1) L100-112, verbatim semantics
    keys = list(base_vals.keys()); bv = np.array([base_vals[k] for k in keys], float); pos = {k: i for i, k in enumerate(keys)}
    out = np.full(len(vm), np.nan)
    if len(bv) >= 10:
        r = rankdata(bv) / max(len(bv) - 1, 1) - 0.5
        for i, (v, nm) in enumerate(zip(vm, names_m)):
            if np.isfinite(v) and nm in pos: out[i] = float(r[pos[nm]])
    return out
# ---------------------------------------------------------------- archived per-anchor files
PM = np.zeros((nC, NW), bool); W3M = np.full((nC, 3), np.nan); KC = np.full((nC, NW), np.nan); FC = np.full((nC, NW), np.nan); WTL = np.full((nC, NW), np.nan)
KING_NZ = np.zeros((nC, NW), bool); LIVE = None; meta = []; FTR = {}
for k, A in enumerate(CAL):
    m = dict(A=A, utc=u(A))
    z = np.load(f"{L}/weights/{A}.npz"); PM[k, z["members"].astype(np.int64)] = True; KING_NZ[k, z["idx"].astype(np.int64)] = z["val"] != 0
    d = json.load(open(f"{L}/target_live/{A}.json")); m["producer"] = d.get("producer"); m["booster_sha"] = str(d.get("booster_sha"))[:16]
    assert "combo_stage" in str(d.get("producer")), ("not combo", u(A))
    w = np.zeros(NW)
    for s, x in d["weights"].items(): w[sidx[s]] += float(x)
    WTL[k] = w; lv = [str(s) for s in d["universe"]]
    if LIVE is None: LIVE = lv
    assert lv == LIVE, ("universe changed", u(A))
    c = json.load(open(f"{L}/target_combo/{A}.json")); W3M[k] = c["w3_masked"]; m["kc_src"] = c["kc_state_source"]; m["fc_src"] = c["fc_state_source"]; m["ftrim"] = "ftrim" in c
    if "ftrim" in c: FTR[A] = c["ftrim"]
    for nm, arr in (("kc", KC), ("fc", FC)):
        an, v = load_state(f"{L}/fea171_states/state_H_{nm}_{A}.npz"); assert an == A; arr[k] = v
    meta.append(m)
assert LIVE == LV
LIVE_MASK = np.array([s in set(LIVE) for s in SP])
assert all(meta[k]["ftrim"] == (CAL[k] >= FTRIM_ON) for k in range(nC)), "FTRIM start anchor"
assert all((meta[k]["kc_src"] == "own") == (CAL[k] != 1788062400) for k in range(nC)), "state source rule"
zw = np.load(f"{L}/weights/{PRE}.npz"); WARM_kc = np.zeros(NW); WARM_kc[zw["idx"].astype(np.int64)] = zw["val"].astype(np.float64)
an, WARM_fc = load_state(f"{L}/fea171_states/state_H_f10_{PRE}.npz"); assert an == PRE
arch = {u(A): float(np.abs(WTL[k] - (0.55 * KC[k] + 0.45 * FC[k])).max()) for k, A in enumerate(CAL)}
G_ARCH_D = dict(max_abs=max(arch.values()), per_anchor_max=max(arch.values()), PASS=bool(max(arch.values()) <= 1e-9))
print("G-ARCH-D", G_ARCH_D, flush=True)
# ---------------------------------------------------------------- sel_D from the producer rolling cache
RZ = np.load(L + "/rolling.npz", allow_pickle=True); rts = RZ["ts"].astype(np.int64); RD = RZ["data"]
QV = np.full((nC, NW), np.nan)
for k, A in enumerate(CAL):
    ai = int(np.searchsorted(rts, A, side="right")) - 1; assert rts[ai] == A, ("anchor row", u(A))
    seg = RD[max(ai + 1 - 2016, 0):ai + 1, :, 3].astype(np.float32); fin = np.isfinite(seg)
    qvm = np.where(fin, seg, 0).sum(0) / np.maximum(fin.sum(0), 1); QV[k] = np.expm1(np.clip(qvm, 0, 30)) * 48
SEL = QV >= P["qv4h_min"]
siglog = {}
for ln in open(L + "/shadow_log.jsonl"):
    try: r = json.loads(ln)
    except Exception: continue
    if r.get("e") == "signal" and PRE <= int(r["anchor_ts"]) <= CAL[-1]: siglog[int(r["anchor_ts"])] = r
GS = {}
for k, A in enumerate(CAL):
    viol = KING_NZ[k] & ~(PM[k] & SEL[k] & LIVE_MASK); nsel = int((PM[k] & SEL[k]).sum())
    GS[u(A)] = dict(viol=int(viol.sum()), sel_recon=nsel, sel_logged=siglog[A]["sel"], match=bool(siglog[A]["sel"] == nsel))
G_ING_S = dict(total_violations=sum(v["viol"] for v in GS.values()), count_mismatch=[a for a, v in GS.items() if not v["match"]], per_anchor=GS)
G_ING_S["PASS"] = bool(G_ING_S["total_violations"] == 0 and not G_ING_S["count_mismatch"])
print("G-ING-S", G_ING_S["total_violations"], G_ING_S["count_mismatch"], flush=True)
# ---------------------------------------------------------------- producer EMA / ledger reconstruction
def ema_back(aux, targets, names):
    led = aux["ledger_tail"]; ema = aux["ema"]
    acc_o = {T_: np.full(len(names), np.nan) for T_ in targets}; ft_o = {T_: np.full(len(names), np.nan) for T_ in targets}
    rate_o = {T_: np.full(len(names), np.nan) for T_ in targets}; iv_o = {T_: np.full(len(names), np.nan) for T_ in targets}
    info = dict(n_names=0, n_no_rows=0, n_rows_too_short=0)
    for q, s in enumerate(names):
        rows = led.get(s) or []; est = ema.get(s)
        if not rows: info["n_no_rows"] += 1; continue
        ft = np.array([float(r[0]) for r in rows]); rate = np.array([float(r[1]) for r in rows]); iv = np.array([float(r[2]) if (len(r) > 2 and r[2]) else 8.0 for r in rows])
        assert np.all(np.diff(ft) > 0), s
        acc = float(est["acc"]) if est else np.nan
        if est: assert abs(float(est["last_ts"]) - ft[-1]) < 1e-6, (s, est["last_ts"], ft[-1])
        kk = len(ft) - 1
        for T_ in sorted(targets, reverse=True):
            while kk >= 1 and ft[kk] > T_:
                a = 1 - 0.5 ** (max(ft[kk] - ft[kk - 1], 1) / (3 * 86400.0)); rn = rate[kk] * (8.0 / iv[kk])
                acc = (acc - a * rn) / (1 - a) if np.isfinite(acc) else acc; kk -= 1
            if ft[kk] > T_: info["n_rows_too_short"] += 1; continue
            acc_o[T_][q] = acc; ft_o[T_][q] = ft[kk]; rate_o[T_][q] = rate[kk]; iv_o[T_][q] = iv[kk]
        info["n_names"] += 1
    return acc_o, ft_o, rate_o, iv_o, info
AUX04 = json.load(open(L + "/aux_pre_m1_20260904.json")); AUX13 = json.load(open(L + "/aux.json"))
assert int(AUX04["prev_rec"]["anchor_ts"]) == 1788480000 and int(AUX13["prev_rec"]["anchor_ts"]) == 1789272000
BASE = [str(s) for s in AUX13["base_syms"]]; assert len(BASE) == 530 and set(LIVE) <= set(BASE)
T_pre = [A for A in CAL if A <= 1788480000]; T_post = [A for A in CAL if A > 1788480000]
a04, f04, r04, i04, info04 = ema_back(AUX04, T_pre, SP)
a13, f13, r13, i13, info13 = ema_back(AUX13, T_post, SP)
b13, bf13, _, _, infob = ema_back(AUX13, T_post, BASE)
FED = np.full((nC, NW), np.nan); RN8L = np.full((nC, NW), np.nan); BASEV = np.full((nC, len(BASE)), np.nan); NBASE = np.zeros(nC, int)
for k, A in enumerate(CAL):
    acc, ftl, rt, iv = (a04[A], f04[A], r04[A], i04[A]) if A in a04 else (a13[A], f13[A], r13[A], i13[A])
    FED[k] = np.where(np.isfinite(ftl) & (A - ftl <= 12 * 3600) & LIVE_MASK & np.isfinite(acc), acc, np.nan)
    RN8L[k] = np.where(np.isfinite(rt), rt * (8.0 / np.where(iv > 0, iv, 8.0)), np.nan)   # combo_stage L240-243: last ledger row, rate*(8/iv)
    if A >= M1_ON:
        bv = np.where(np.isfinite(bf13[A]) & (A - bf13[A] <= 12 * 3600) & np.isfinite(b13[A]), b13[A], np.nan); BASEV[k] = bv; NBASE[k] = int(np.isfinite(bv).sum())
# G-ING-V (T5 method, 09-13 -> 09-04 00Z)
T04 = 1788480000
bk, bft, _, _, _ = ema_back(AUX13, [T04], SP)
fe04 = np.where(np.isfinite(bft[T04]) & (T04 - bft[T04] <= 12 * 3600) & LIVE_MASK, bk[T04], np.nan)
m04 = np.array(AUX04["prev_rec"]["members"], np.int64); z_st = np.array(AUX04["prev_rec"]["legz"]["fund"], np.float64)
G_ING_V = dict(max_abs_dz=float(np.abs(np.nan_to_num(xz(fe04[m04])) - z_st).max())); G_ING_V["PASS"] = bool(G_ING_V["max_abs_dz"] <= 1e-9)
# G-ING-B (i) exact M1 fund z at 09-13 04Z; (ii) fund_base_n per M1 anchor
A13 = 1789272000
acc_now = {s: float(AUX13["ema"][s]["acc"]) for s in AUX13["ema"]}
led = AUX13["ledger_tail"]
bvals13 = {s: acc_now[s] for s in BASE if led.get(s) and s in acc_now and A13 - float(led[s][-1][0]) <= 12 * 3600}
fe_v13 = np.full(NW, np.nan)
for s in LIVE:
    if led.get(s) and s in acc_now and A13 - float(led[s][-1][0]) <= 12 * 3600: fe_v13[sidx[s]] = acc_now[s]
m13 = np.array(AUX13["prev_rec"]["members"], np.int64)
z13 = np.nan_to_num(xz_in_base(fe_v13[m13], [SP[j] for j in m13], bvals13)); zold = np.nan_to_num(xz(fe_v13[m13]))
GB = dict(i_max_abs_dz_M1=float(np.abs(z13 - np.array(AUX13["prev_rec"]["legz"]["fund"])).max()), i_max_abs_dz_old=float(np.abs(zold - np.array(AUX13["prev_rec"]["fund_z_old"])).max()),
          i_fund_base_n=len(bvals13), i_logged=AUX13["prev_rec"]["fund_base_n"],
          ii={u(A): dict(recon=int(NBASE[k]), logged=siglog[A].get("fund_base_n")) for k, A in enumerate(CAL) if A >= M1_ON})
GB["ii_mismatch"] = [a for a, v in GB["ii"].items() if v["recon"] != v["logged"]]
GB["PASS"] = bool(GB["i_max_abs_dz_M1"] <= 1e-9 and GB["i_max_abs_dz_old"] <= 1e-9 and GB["i_fund_base_n"] == GB["i_logged"] and not GB["ii_mismatch"])
print("G-ING-V", G_ING_V, "G-ING-B", {k: v for k, v in GB.items() if k != "ii"}, flush=True)
# G-ING-T: recorded rn8 of FTRIM-listed names vs ledger reconstruction
GT = dict(n_checked=0, max_abs=0.0, n_missing=0, worst=None)
for k, A in enumerate(CAL):
    if A not in FTR: continue
    for nmkey in ("names_kc", "names_fc"):
        for s, v in FTR[A][nmkey].items():
            j = sidx.get(s)
            if j is None or not np.isfinite(RN8L[k, j]): GT["n_missing"] += 1; continue
            dlt = abs(round(float(RN8L[k, j]), 7) - float(v)); GT["n_checked"] += 1
            if dlt > GT["max_abs"]: GT["max_abs"] = dlt; GT["worst"] = (u(A), s, float(v), float(RN8L[k, j]))
G_ING_T = dict(GT, PASS=bool(GT["n_checked"] > 0 and GT["max_abs"] <= 1e-7 and GT["n_missing"] == 0))
print("G-ING-T", G_ING_T, flush=True)
out = T + "/receipts/T5c_live_ingredients.npz"
np.savez_compressed(out, symbols=np.array(SP), cal=np.array(CAL, np.int64), win=np.array(WIN, np.int64), pre=np.int64(PRE), PM=PM, LIVE=LIVE_MASK, W3M=W3M, QV=QV, SEL=SEL, FED=FED, RN8L=RN8L,
                    BASE=np.array(BASE), BASE_IDX=np.array([sidx.get(s, -1) for s in BASE], np.int64), BASEV=BASEV, KC=KC, FC=FC, WTL=WTL, WARM_kc=WARM_kc, WARM_fc=WARM_fc, KING_NZ=KING_NZ,
                    FTRIM_ON=np.int64(FTRIM_ON), M1_ON=np.int64(M1_ON), SEED_ON=np.int64(SEED_ON))
RC = dict(self_sha256=sha(os.path.abspath(__file__)), prereg_sha256=PREREG_SHA, meta=meta, G_ARCH_D=G_ARCH_D, G_ING_S={k: v for k, v in G_ING_S.items() if k != "per_anchor"}, G_ING_S_per_anchor=G_ING_S["per_anchor"],
          G_ING_V=G_ING_V, G_ING_B=GB, G_ING_T=G_ING_T, ema_info=dict(pre=info04, post=info13, base=infob),
          inputs={os.path.relpath(p, T): sha(p) for p in (L + "/bundle_aug_backup/config.json", L + "/rolling.npz", L + "/aux_pre_m1_20260904.json", L + "/aux.json", L + "/shadow_log.jsonl")},
          copy_manifest_sha256=sha(T + "/private/COPY_SHA256.txt"), out=os.path.relpath(out, T), out_sha256=sha(out),
          env=dict(whitelist=sorted(WHITE), actual={k: os.environ[k] for k in sorted(os.environ)}), python=sys.version.split()[0], numpy=np.__version__, built_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), wall_s=round(time.time() - t0, 1))
json.dump(RC, open(T + "/receipts/RECEIPT_T5c_live_ingredients.json", "w"), indent=1, default=str)
print("DONE t5c_live_ingredients", RC["wall_s"])
