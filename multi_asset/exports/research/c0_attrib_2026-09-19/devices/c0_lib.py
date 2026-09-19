#!/usr/bin/env python3
"""c0_lib.py — shared loaders + the exact per-name accounting of the realcost replay device, for stream C0
(docs/RESULT_c0_attribution_2026-09-19.md). pod2, CPU, read-only on every input.

The replay device is w10_health.py (sha256 8684d9a9…, run 2026-09-18 00:03Z by realcost/run_realcost.sh, cwd dev_v4/ ⇒ meta =
meta_newprod_v4.npz, panel = /workspace/data/wide_panel_4h_v2ext.npz via the dev_v4/pod_backup_2026-08-21 symlinks). Facts read from
its source (line numbers of 8684d9a9) that this module replicates verbatim — nothing here is re-derived:
  * saved W (`d30_n2_c42_W`, float32) = `sm` (L331) = the blended book (1−PHI)·king-book + PHI·F10-book after EMA / band / forced exit /
    stop-block (L278–282); signed; per unit of 1× NAV (Σ|W| = gross_total, L327).
  * the judge's `_ex` columns (fp2_per_year_table.py L33: g = net_ex/gross_total) are computed on the RESHAPED book `smr` (L284–290):
      nz = |sm| > 1e-12;  smr[nz] −= mean(sm[nz]);  smr ×= Σ|sm| / Σ|smr|
  * pnl_ex  = Σ_{k∈m} smr_k · nan→0(y4[i,k]) · 1e4                       (L322; CAL=log ⇒ y4 used as stored = RAW Π(1+r)−1)
    carry_ex= Σ_{k∈m} smr_k · nan→0(f_fund_now[j,k]) · 4/iv_k · 1e4      (L297, L323; iv = f_fund_iv if finite and > 0 else 8; + = book pays)
    cost_ex = Σ_{k∈m} |smr_k − HR_k| · (fr·maker + (1−fr)·taker)[tier_k]   (L291, L324–325; HR = previous RECORDED anchor's smr, L333)
    where m = the anchor's member set: {finite qvk} (MEMBERS_TOPN=829, L59–64) ∩ umask row (UMASK_SCOPE=m1, L140–142 / L196–198).
    ⇒ positions held on names OUTSIDE m (names that left the member set; EMA decay) count in gross_total but earn no P&L in the device.
  * leg_fund (L301–303) = w3_fund · Σ_{k∈m} (zz_k/Σ|zz|) · y4_k · 1e4 with zz = nan→0(xz(f_fund_ema_v1[j, all 829])[m]) — SEAT-WEIGHTED;
    legs_fund saved in the npz (L380) = the seat input from legs() (L143–154): z demeaned over finite-y members, not seat-weighted.
"""
import hashlib, json, time
import numpy as np
from scipy.stats import rankdata

W_ = "/workspace"
INPUTS = {   # name: (path, sha256) — pinned; any mismatch refuses
    "ARM_A0_S42": (f"{W_}/fp2_2026-09/realcost/arms/w10_ablation_series_V4_A0_dyn_s42.npz", "634f7c55ba730520371aab64b64b3b2b5c211422af6ab7b8bacb78e4d706060b"),
    "ARM_A0_S2027": (f"{W_}/fp2_2026-09/realcost/arms/w10_ablation_series_V4_A0_dyn_s2027.npz", "c1f92ec24bb45c990427840831033e6cc136cc7ba02a86b00375a6dcf1f74081"),
    "META_V4": (f"{W_}/fp2_2026-09/refute_C6_2/altrun/meta_newprod_v4.npz", "e1cf515eca46b0a1a7afe2bd6e89039cb68f4eea1a0428353e2f3aac989890a7"),
    "PANEL_ARM": (f"{W_}/data/wide_panel_4h_v2ext.npz", "5e67c0559daa904d8f0526b6e268e93dcb45aab89d82646cf79a794445481116"),
    "UMASK_ARM": (f"{W_}/fx_data_2026-09-13/out/inject/umask_UPIT_CRYPTO_tradable_W24H.npz", "3badc4b6a4fcbc5935f66f29c065ffd7ab500cb6876bdf53ce491b2d9056024c"),
    "W10_DEVICE": (f"{W_}/fp2_2026-09/health_check/w10_health.py", "8684d9a9f43a8d15beaa559cd12bd8f2977a3d088b01b93835f60f2bbf98a53d"),
    "COSTB_JSON": (f"{W_}/fp2_2026-09/realcost/costb_fee_real_0907.json", "e5ac58d57f230be73b9af31830ec48fb87229997576da52da15bd46991d434b7"),
    "JUDGE": (f"{W_}/fp2_2026-09/devices_v4chain/fp2_per_year_table.py", "230e3c793cd92ddf78abf76198e39c8cdb3657696920f0290324ff4a9e7a882f"),
}
CACHE_INPUTS = {
    "CACHE_HOLEFIX2": (f"{W_}/data/dlnative_5m_wide829_f16_holefix2.npz", "1d7f459dee434ec49e7714a2a612807f2e38e97f35c6c39471a8a4aaa7452488"),
    "HOLE_CELLS": (f"{W_}/fp2_2026-09/holefix2_cells.npz", "6156f97a0709f073147e392d5b0cb542f6b6d463cc3be2500f8791a0d1a8dfda"),
}
SEEDS = ("42", "2027")
UB = 1788120000            # 2026-08-30T20:00:00Z — the judge's frozen upper bound (realcost/run_realcost.sh UB=)
NW = 829


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def utc(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))


class Checks:
    def __init__(self, t0): self.rows = []; self.fails = []; self.t0 = t0
    def log(self, *a): print("[%6.0fs]" % (time.time() - self.t0), *a, flush=True)
    def __call__(self, name, ok, detail=None):
        self.rows.append({"check": name, "ok": bool(ok), **({"detail": detail} if detail is not None else {})})
        if not ok: self.fails.append(name)
        self.log("CHECK", name, "OK" if ok else "FAIL", json.dumps(detail, default=str)[:500] if detail is not None else "")
        return ok


def verify_inputs(chk, table):
    out = {}
    for k, (p, s) in table.items():
        got = sha(p); out[k] = {"path": p, "sha256": got}
        chk(f"input_sha.{k}", got == s, {"expected": s[:12], "got": got[:12]})
    return out


def xz(v):   # w10_health.py L122–125 verbatim
    ok = np.isfinite(v); out = np.full(len(v), np.nan)
    if ok.sum() >= 10: out[ok] = rankdata(v[ok]) / max(ok.sum() - 1, 1) - 0.5
    return out


def tier_of(q):   # L131–133 verbatim
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t


def reshape(sm):   # L284–290 verbatim
    nz = np.abs(sm) > 1e-12
    smr = sm.copy()
    if nz.any():
        smr[nz] -= smr[nz].mean()
        _g0 = np.abs(sm).sum(); _g1 = np.abs(smr).sum()
        if _g1 > 1e-9:
            smr *= _g0 / _g1
    return smr


def load_arm(seed, chk):
    p = INPUTS[f"ARM_A0_S{seed}"][0]
    z = np.load(p, allow_pickle=True)
    cols = [str(c) for c in z["cols"]]
    cfg = json.loads(str(z["config_json"]))
    exp = {"CAL": "log", "LEGS": "101", "UMASK_SCOPE": "m1", "MEMBERS_TOPN": 829, "FTRIM": "zero", "PHI": 0.45, "WRULE": "msharpe", "LOOK": 900,
           "FSEED": seed, "FPRED": f"f10_A0_s{seed}.npy", "SLOW_NPY": f"{W_}/fp2_2026-09/king_v4/SLOW_v3_on_v4axis.npy", "UMASK_NPZ": INPUTS["UMASK_ARM"][0],
           "COSTB_JSON": INPUTS["COSTB_JSON"][0], "COST_B": [[2.0, 5.0, 0.589]] * 3, "W3FIX": None, "KMOD": 0.0, "KMOD_F10": 0.0, "KMOD_AGREE": 0.0,
           "KTAIL": 0, "SEATF10": 0, "SEATNET": 0, "FUNDSCALE": 0, "FEMAT_NPZ": None, "TRADE_TOPN": 0}
    bad = {k: (cfg.get(k), v) for k, v in exp.items() if cfg.get(k) != v}
    chk(f"arm_s{seed}.config_is_the_in_role_A0_realcost_arm", not bad and cfg["HEALTH"]["device_sha256"] == INPUTS["W10_DEVICE"][1], {"mismatch": bad})
    R = np.asarray(z["d30_n2_c42_rec"], np.float64); W = np.asarray(z["d30_n2_c42_W"])
    chk(f"arm_s{seed}.shapes", R.shape[0] == W.shape[0] and W.shape[1] == NW and W.dtype == np.float32 and [str(s) for s in z["symbols"]] is not None,
        {"rec": R.shape, "W": W.shape, "W_dtype": str(W.dtype)})
    return dict(cols=cols, cfg=cfg, R=R, W=W, symbols=[str(s) for s in z["symbols"]], legs_ts=np.asarray(z["legs_ts"]).astype(np.int64),
                legs_fund=np.asarray(z["legs_fund"]), legs_king=np.asarray(z["legs_king"]), path=p)


def load_common(chk):
    MT = np.load(INPUTS["META_V4"][0], allow_pickle=True)
    ME = MT["E_ts"].astype(np.int64); y4 = MT["y4"]; qvk = MT["qvk"]
    PW = np.load(INPUTS["PANEL_ARM"][0], allow_pickle=True)
    PTS = PW["ts"].astype(np.int64); SYM = [str(s) for s in PW["symbols"]]
    FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; FE = PW["f_fund_ema_v1"]
    UZ = np.load(INPUTS["UMASK_ARM"][0], allow_pickle=True)
    chk("umask.symbols_equal_panel", [str(s) for s in UZ["symbols"]] == SYM)
    UM = np.asarray(UZ["mask"]); umap = {int(t): k for k, t in enumerate(UZ["ts"].astype(np.int64))}
    cj = json.load(open(INPUTS["COSTB_JSON"][0])); tiers = [(float(t["maker_bps"]), float(t["taker_bps"]), float(t["maker_share"])) for t in cj["tiers"]]
    return dict(ME=ME, y4=y4, qvk=qvk, mrow={int(t): i for i, t in enumerate(ME)}, PTS=PTS, prow={int(t): j for j, t in enumerate(PTS)}, SYM=SYM,
                FN=FN, IV=IV, FE=FE, UM=UM, umap=umap, COST_B=tiers)


def members(C, i, j):   # L59–64 (MEMBERS_TOPN=829) then L140–142 (umask m1)
    q = np.nan_to_num(C["qvk"][i], nan=-1.0); o = np.argsort(-q); o = o[q[o] > -0.5]
    m = np.sort(o[:829]).astype(np.int64)
    k = C["umap"].get(int(C["PTS"][j]))
    if k is not None:
        mk = C["UM"][k]; m = m[mk[m]]
    return m


def per_name(A, C, keep_rows=None):
    """dense per-(row, name) accounting on the reshaped book; returns dict of (nR, 829) float64 arrays (+ per-row sums).
    keep_rows: optional boolean over rec rows; the HR chain always runs over ALL rows (fee needs the previous recorded row)."""
    R = A["R"]; W = A["W"]; cols = A["cols"]; nR = R.shape[0]
    ts = R[:, 0].astype(np.int64)
    if keep_rows is None: keep_rows = np.ones(nR, bool)
    ridx = np.nonzero(keep_rows)[0]; pos = {int(r): p for p, r in enumerate(ridx)}; nK = len(ridx)
    out = {k: np.zeros((nK, NW)) for k in ("smr", "price", "carry", "fee")}
    inm = np.zeros((nK, NW), bool)
    sums = {k: np.zeros(nR) for k in ("pnl_ex", "carry_ex", "cost_ex", "leg_fund", "leg_fund_raw", "legs_fund_seatinput", "S_abs_price", "S_abs_carry", "S_abs_cost",
                                      "gross_W", "gross_outside_m", "nmember")}
    HR = np.zeros(NW)
    w3f = R[:, cols.index("w3_fund")]
    for r in range(nR):
        i = C["mrow"][int(ts[r])]; j = C["prow"][int(ts[r])]
        m = members(C, i, j)
        sm = W[r].astype(np.float64)
        smr = reshape(sm)
        yv = np.nan_to_num(C["y4"][i, m], nan=0.0)
        fnow = np.nan_to_num(C["FN"][j, m], nan=0.0); ivv = C["IV"][j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
        pr = smr[m] * yv * 1e4
        ca = smr[m] * fnow * (4.0 / ivv) * 1e4
        qv4h = np.expm1(np.clip(C["qvk"][i, m], 0, 30)) * 48; tr = tier_of(qv4h)
        blend = np.array([fr * mk + (1 - fr) * tk for (mk, tk, fr) in C["COST_B"]])[tr]
        trr = smr - HR
        fe = np.abs(trr[m]) * blend
        sums["pnl_ex"][r] = float((smr[m] * yv).sum() * 1e4)
        sums["carry_ex"][r] = float((smr[m] * fnow * (4.0 / ivv)).sum() * 1e4)
        sums["cost_ex"][r] = float(sum(np.abs(trr[m])[tr == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(C["COST_B"])))
        sums["S_abs_price"][r] = float(np.abs(pr).sum()); sums["S_abs_carry"][r] = float(np.abs(ca).sum())
        sums["S_abs_cost"][r] = float(((np.abs(smr[m]) + np.abs(HR[m])) * blend).sum())
        FZ = xz(C["FE"][j, :])[m]; zz = np.nan_to_num(FZ); gl = np.abs(zz).sum()
        raw = float((zz / gl * yv).sum() * 1e4) if gl > 1e-9 else 0.0
        sums["leg_fund_raw"][r] = raw; sums["leg_fund"][r] = float(w3f[r] * (zz / gl * yv).sum() * 1e4) if gl > 1e-9 else 0.0
        ok = np.isfinite(C["y4"][i, m]); z = np.where(ok, zz, 0.0); z = z - (z[ok].mean() if ok.sum() else 0); g = np.abs(z).sum()
        sums["legs_fund_seatinput"][r] = float((z / g * yv).sum() * 1e4) if g > 1e-9 else 0.0
        sums["gross_W"][r] = float(np.abs(sm).sum())
        outm = np.ones(NW, bool); outm[m] = False
        sums["gross_outside_m"][r] = float(np.abs(sm[outm]).sum()); sums["nmember"][r] = len(m)
        if keep_rows[r]:
            p = pos[r]
            out["smr"][p] = smr; out["price"][p, m] = pr; out["carry"][p, m] = ca; out["fee"][p, m] = fe; inm[p, m] = True
        HR = smr
    out["inm"] = inm; out["rows"] = ridx; out["ts"] = ts[ridx]
    return out, sums
