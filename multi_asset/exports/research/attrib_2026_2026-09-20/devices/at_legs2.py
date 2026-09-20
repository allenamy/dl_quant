#!/usr/bin/env python3
"""at_legs2.py — the CORRECTED §2-A decomposition. Replaces the withdrawn A1 / A2 / A2b of at_attrib.py,
which modelled the book as `φ_king · king-leg + φ_fund · fund-leg` and was wrong about what the two stored
vectors and the two seats ARE (error ledger E-0920-B).

════════ THE PRODUCTION DEFINITION, COPIED VERBATIM (file:line + code), NOT PARAPHRASED ════════
Producer `~/wide_shadow/fea171/combo_stage.py` (sha256 3520d36394fbe7b9); the object-B replay copy
`/workspace/object_b_2026-09-19/devices/combo_stage_replay_3520d363.py` is structurally identical, the
same statements at +3 lines. Production line numbers are quoted; the replay's are given in brackets.

  L229 [232]  w3m = np.array([w3[0], 0.0, w3[2]])
  L230 [233]  w3m = w3m / w3m.sum() if w3m.sum() > 1e-12 else np.array([0.5, 0.0, 0.5])
  L231 [234]  z_kc = w3m[0] * np.nan_to_num(legz["king"]) + w3m[2] * np.nan_to_num(legz["fund"])
  L232 [235]  z_fc = w3m[0] * np.nan_to_num(zf)           + w3m[2] * np.nan_to_num(legz["fund"])
  L248 [251]  z_kc = np.where(_band_kc, 0.0, z_kc)          # FTRIM, per component
  L249 [252]  z_fc = np.where(_band_fc, 0.0, z_fc)
  L265 [268]  H = H_kc_prev; sm_kc = chain(z_kc)
  L266 [269]  H = H_fc_prev; sm_fc = chain(z_fc)
  L271 [274]  combo_raw = 0.55 * sm_kc + 0.45 * sm_fc
  L272 [275]  combo     = exec_reshape(combo_raw)
  L352 [340]  _weights = {syms[int(j)]: float(combo_raw[j]) for j in _nz}     # ← what is ARCHIVED / traded
  L78  [81]   def chain(zc):  mask → demean over `sel` → /Σ|·| → clip(±cap_mult/n) → /Σ|·| →
              smv = H + alpha*(tgt − H) → dead-band: where |smv−H| < band keep H → liquidity-exit zeroing

WHAT THIS MEANS, AND WHAT THE PREVIOUS VERSION GOT WRONG.
  * The two seats w3m[0] / w3m[2] are NOT weights between the two stored books. They are the weights of the
    MODEL signal vs the FUNDING signal INSIDE EACH component's z, and BOTH components carry the funding
    signal at the SAME seat w3m[2]. The previous version used them as book-level leg weights.
  * The two stored vectors `kc` / `fc` are not "the king leg" and "the fund leg": `kc` is the KING COMPONENT
    (king model + funding) and `fc` is the F10 COMPONENT (F10 model + funding).
  * The weights BETWEEN the two components are the fixed 0.55 / 0.45 of L271, not the seats.
  * What is archived and traded is `combo_raw` (L352), i.e. BEFORE `exec_reshape`; the executor applies its
    own reshape at trade time, which is what the paper book W of at_build already does.

════════ ASSERTION A0 — RUNS FIRST, AND NO NUMBER IS EMITTED UNLESS IT PASSES ════════
  A0a  every kind-2 (combo) anchor:      written target == 0.55 * kc + 0.45 * fc     BITWISE (uint64 view)
  A0b  every kind-1 (king-file) anchor:  written target == king_file                 BITWISE
  A0c  the traded paper book W of at_build is reproduced exactly by the parts below (≤ 1e-12 per weight)
A failed assertion ⇒ VERDICT REFUSED, no output file. This is the gate the previous version did not have:
it had arithmetic gates (things add up) and a reproduction gate (the published table reproduces), but
nothing that tied the decomposed quantity to the producer's own definition of it.

════════ THE CORRECTED, EXACTLY ADDITIVE BOOK-LEVEL SPLIT ════════
With raw = the written target, nz = its non-zero set, μ = mean(raw[nz]), G' = Σ|raw[nz] − μ|:
    W_i = 0.55·kc_i/G'  +  0.45·fc_i/G'  −  μ/G'          (i ∈ nz; 0 elsewhere)
            └ KC part ┘    └ FC part ┘     └ RESHAPE part ┘
On a kind-1 anchor the traded book is the producer's ORIGINAL 3-leg king file — z_king = w3[0]·king +
w3[1]·rev24 + w3[2]·fund with the UNMASKED w3, i.e. it still carries the rev24 leg that the combo form
removes. It is a different book, not a component of the combo form, so it goes in its own bucket
KING_FILE and is never merged into KC / FC.

════════ WHAT IS *NOT* IDENTIFIABLE, STATED RATHER THAN MANUFACTURED ════════
A book-level split into "funding signal / king signal / F10 signal" DOES NOT EXIST in the archived
artefacts. At the z level the algebra is clean:
    0.55·z_kc + 0.45·z_fc = w3m[0]·(0.55·z_king + 0.45·z_f10) + w3m[2]·z_fund
— so there is no 55/45 interaction term at z level either; the blend is exactly linear. But the book is
`0.55·chain(z_kc) + 0.45·chain(z_fc)`, and `chain` is NOT linear: it clips at ±cap, it has a dead-band
that can return the previous state unchanged, and it carries a path-dependent EMA state that DIFFERS
between the two components (H_kc vs H_fc). chain(a·x + b·y) ≠ a·chain(x) + b·chain(y). The archive stores
only sm_kc, sm_fc, the king book and the combo — never z_king, z_f10 or z_fund. Recovering the three-signal
split therefore needs a producer re-run that dumps those three z vectors per anchor; this device does not
guess one, and the result document says so.

Two things ARE identified and are reported instead:
  (1) SEATS AS THEY ACTUALLY ARE: w3m[2] is the funding signal's z-weight inside BOTH components, w3m[0]
      the model composite's. Reported as a z-level weight, never as a book-level contribution.
  (2) SEAT-EXTREME SUBSAMPLES, exact by identity, not by estimate:
        w3m[2] == 0  ⇒  z_kc = w3m[0]·z_king, z_fc = w3m[0]·z_f10, and `chain` is invariant to a positive
                        scale (it divides by Σ|·| before the clip) ⇒ the book IS the pure 0.55/0.45 MODEL
                        composite, with no funding signal in it at all.
        w3m[0] == 0  ⇒  z_kc = z_fc = w3m[2]·z_fund ⇒ both components are built from the SAME z ⇒ the book
                        IS the pure FUNDING book (the two component books can still differ only through
                        their separate EMA states).
      ⚠ These subsamples are chosen by the producer's msharpe seat rule, which selects on trailing Sharpe.
      They are NOT a random sample of history and the device prints that next to the numbers.
  (3) The component-return DIFFERENCE r(kc) − r(fc) is driven only by w3m[0]·(z_king − z_f10): the funding
      term is bit-identical in both z's (L231/L232) and cancels. So the difference isolates MODEL
      DISAGREEMENT — up to the chain, which is why it is reported as a difference and not as two levels.

usage: python at_legs2.py <ENV_WHITELIST_CSV> <OUT_DIR>
"""
import json, os, sys, time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import at_lib as L

T0 = time.time()
ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{L.ROOT}/receipts"
chk = L.Checks(T0)
rec = L.rec_head("at_legs2.py", sys.argv)
rec["replaces"] = "at_attrib.py block_A_legs (A1 / A2 / A2b) — withdrawn, error ledger E-0920-B"
rec["production_source"] = {"producer": "~/wide_shadow/fea171/combo_stage.py", "sha256_16": "3520d36394fbe7b9",
                            "replay_copy": "/workspace/object_b_2026-09-19/devices/combo_stage_replay_3520d363.py"}
chk("env.whitelist", not sorted(set(rec["env"]) - ENV_OK), {"extra": sorted(set(rec["env"]) - ENV_OK)})
rec["inputs"] = L.verify_pins(chk, ["TARGETS_A0_MAIN", "P3VEC_A0_MAIN", "P3JSON_A0_EXT", "AGG_A0"])
PANP = f"{L.ROOT}/work/AT_PANEL.npz"
L1P = f"{L.ROOT}/work/AT_L1_mean.npz"
rec["upstream"] = {"panel": {"path": PANP, "sha256": L.sha(PANP)}, "L1_mean": {"path": L1P, "sha256": L.sha(L1P)}}
if chk.fails:
    L.write_receipt(rec, chk, f"{OUT}/AT_LEGS2_RECEIPT.json")
    print("AT_LEGS2 VERDICT=REFUSED failed=%s" % chk.fails, flush=True)
    sys.exit(3)

NW = L.NW
TX = np.load(L.PINS["TARGETS_A0_MAIN"][0], allow_pickle=True)
PX = np.load(L.PINS["P3VEC_A0_MAIN"][0], allow_pickle=True)
P3J = json.load(open(L.PINS["P3JSON_A0_EXT"][0]))["records"]
CS = {k: np.asarray(TX[k]) for k in ("scaled_off", "scaled_idx", "scaled_val", "scaled_kind")}
for pref in ("kc", "fc", "king_file"):
    for suf in ("_off", "_idx", "_val"):
        CS[pref + suf] = np.asarray(PX[pref + suf])
anch_all = np.asarray(TX["anchor"]).astype(np.int64)

Z = np.load(PANP, allow_pickle=True)
L1 = np.load(L1P)
in_run = Z["in_run"]
A = Z["A"].astype(np.int64)[in_run]
sel_all = np.nonzero((anch_all >= A[0]) & (anch_all <= A[-1]))[0]
chk("axis.aligned", len(sel_all) == len(A) and np.array_equal(anch_all[sel_all], A), {"n": len(A)})
SY = [str(s) for s in Z["symbols"]]
W = np.asarray(Z["W"], np.float64)[in_run]
RET = np.asarray(Z["RET"], np.float64)[in_run]
FUND = np.asarray(Z["FUND"], np.float64)[in_run]
KIND = Z["KIND"][in_run]
NA = len(A)


def dense(pref, a):
    o = CS[pref + "_off"]
    x = np.zeros(NW)
    i0, i1 = int(o[a]), int(o[a + 1])
    if i1 > i0:
        x[CS[pref + "_idx"][i0:i1]] = CS[pref + "_val"][i0:i1]
    return x


# ───────── ASSERTION A0 (first; nothing is emitted unless it passes) ─────────
bad_a, bad_b = 0, 0
n2 = n1 = 0
KCW = np.zeros((NA, NW))
FCW = np.zeros((NA, NW))
RSW = np.zeros((NA, NW))
KFW = np.zeros((NA, NW))
WEX = np.zeros((NA, NW))          # the paper book recomputed in float64 from the written target
PHI = np.zeros((NA, 2))
for i, a in enumerate(sel_all):
    o = CS["scaled_off"]
    i0, i1 = int(o[a]), int(o[a + 1])
    ii = CS["scaled_idx"][i0:i1]
    raw = np.zeros(NW)
    raw[ii] = CS["scaled_val"][i0:i1]
    kind = int(CS["scaled_kind"][a])
    nz = np.zeros(NW, bool)
    nz[ii] = True
    WEX[i, nz] = L.reshape_pop(raw[nz])
    if kind == 2:
        n2 += 1
        kc = dense("kc", a)
        fc = dense("fc", a)
        if not np.array_equal((0.55 * kc + 0.45 * fc).view(np.uint64), raw.view(np.uint64)):
            bad_a += 1
        cm = (P3J[a]["combo"].get("combo_meta") or {})
        w3 = cm.get("w3_masked") or [np.nan, np.nan, np.nan]
        PHI[i] = (float(w3[0]), float(w3[2]))
        v = raw[nz]
        mu = v.mean()
        Gp = np.abs(v - mu).sum()
        if Gp > 0:
            KCW[i, nz] = 0.55 * kc[nz] / Gp
            FCW[i, nz] = 0.45 * fc[nz] / Gp
            RSW[i, nz] = -mu / Gp
    else:
        n1 += 1
        kf = dense("king_file", a)
        if not np.array_equal(kf.view(np.uint64), raw.view(np.uint64)):
            bad_b += 1
        PHI[i] = (np.nan, np.nan)
        KFW[i] = WEX[i]
chk("A0a.combo_target_is_0.55kc_plus_0.45fc_BITWISE", bad_a == 0, {"n_combo_anchors": n2, "n_bad": bad_a})
chk("A0b.kingfile_target_is_the_king_file_BITWISE", bad_b == 0, {"n_kingfile_anchors": n1, "n_bad": bad_b})
resid = np.abs(KCW + FCW + RSW + KFW - WEX).max()
chk("A0c.parts_reproduce_the_traded_paper_book", float(resid) <= 1e-12, {"max_abs_weight_resid": float(resid)})
# the panel stores W as float32 (at_build), so the stored copy differs from the float64 reconstruction by
# storage round-off only. Checked and bounded here rather than silently absorbed into the tolerance above.
stor = np.abs(WEX - W).max()
chk("A0d.float32_storage_deviation_is_round_off_only", float(stor) <= 5e-9,
    {"max_abs": float(stor), "float32_eps_times_typical_weight": 6e-8 * float(np.abs(WEX).max()),
     "note": "contributions below use the float64 reconstruction WEX, not the float32 panel copy"})
W = WEX
if chk.fails:
    L.write_receipt(rec, chk, f"{OUT}/AT_LEGS2_RECEIPT.json", {"note": "REFUSED before any attribution number"})
    print("AT_LEGS2 VERDICT=REFUSED failed=%s" % chk.fails, flush=True)
    sys.exit(3)

# ───────── contributions (exactly additive) ─────────
def contrib(Wpart, x):
    return 1e4 * (Wpart * x).sum(1)


PARTS = {"KC_king_component": KCW, "FC_f10_component": FCW, "reshape_shift": RSW, "KING_FILE_3leg": KFW}
px = {k: contrib(v, RET) for k, v in PARTS.items()}
fd = {k: contrib(v, FUND) for k, v in PARTS.items()}
# fee: the simulator emits it per anchor only. Allocated across the parts in proportion to each part's own
# weight turnover, normalised so the parts sum to the realised anchor fee EXACTLY (a declared allocation,
# not an identity — Σ_p |ΔW_p| ≠ |ΔW| by the triangle inequality, so no allocation can be both).
tdw = {k: np.abs(np.vstack([v[:1], np.diff(v, axis=0)])).sum(1) for k, v in PARTS.items()}
tsum = sum(tdw.values())
fe = {k: np.where(tsum > 0, L1["fee"] * tdw[k] / np.maximum(tsum, 1e-300), 0.0) for k in PARTS}
chk("additivity.fee_allocation_sums_to_realised", float(np.abs(sum(fe.values()) - L1["fee"]).max()) <= 1e-9,
    {"max_abs_bps": float(np.abs(sum(fe.values()) - L1["fee"]).max())})
px_tot = sum(px.values())
fd_tot = sum(fd.values())
chk("additivity.price", float(np.abs(px_tot - 1e4 * (W * RET).sum(1)).max()) <= 1e-9,
    {"max_abs_bps": float(np.abs(px_tot - 1e4 * (W * RET).sum(1)).max())})
chk("additivity.funding", float(np.abs(fd_tot - 1e4 * (W * FUND).sum(1)).max()) <= 1e-9,
    {"max_abs_bps": float(np.abs(fd_tot - 1e4 * (W * FUND).sum(1)).max())})

# component own-gross returns (kind-2 anchors only) and their difference
r_kc = np.full(NA, np.nan)
r_fc = np.full(NA, np.nan)
for i, a in enumerate(sel_all):
    if int(CS["scaled_kind"][a]) != 2:
        continue
    kc = dense("kc", a)
    fc = dense("fc", a)
    gk, gf = np.abs(kc).sum(), np.abs(fc).sum()
    if gk > 0:
        r_kc[i] = 1e4 * (kc / gk * RET[i]).sum()
    if gf > 0:
        r_fc[i] = 1e4 * (fc / gf * RET[i]).sum()

PERMASK = {n: L.period_mask(A, lo, hi) for n, lo, hi, _ in L.PERIODS}
PERMASK = {k: v for k, v in PERMASK.items() if v.any()}
OUTJ = {"status": "CORRECTED §2-A; replaces the withdrawn A1/A2/A2b (E-0920-B)",
        "structure": {
            "book_level": "written target = 0.55 · kc (KING component) + 0.45 · fc (F10 component), FIXED; bitwise on all %d combo anchors" % n2,
            "kind1": "on %d anchors the producer wrote its ORIGINAL 3-leg king file (king + rev24 + fund, unmasked w3) — a different book, own bucket" % n1,
            "seats": "w3m[0] / w3m[2] weight the MODEL vs the FUNDING signal INSIDE each component's z (L231/L232); BOTH components carry the funding signal at the same seat; they are NOT book-level leg weights",
            "not_identifiable": "a book-level funding/king/F10 split does not exist in the archive: the book is 0.55·chain(z_kc)+0.45·chain(z_fc) and chain (L78) clips, dead-bands and carries a per-component EMA state ⇒ non-linear; z_king / z_f10 / z_fund are never stored",
            "no_blend_interaction": "the 0.55/0.45 blend is exactly linear at both z and book level ⇒ there is no interaction term"},
        "per_period": {}}
for k, m in PERMASK.items():
    d = {"n_anchors": int(m.sum()),
         "share_anchors_combo": float((KIND[m] == 2).mean()),
         "share_anchors_king_file": float((KIND[m] == 1).mean()),
         "price": {p: float(px[p][m].mean()) for p in PARTS},
         "funding_paid": {p: float(fd[p][m].mean()) for p in PARTS},
         "fee": {p: float(fe[p][m].mean()) for p in PARTS},
         "price_total": float(px_tot[m].mean()),
         "component_own_gross_return": {"kc_king_component": float(np.nanmean(r_kc[m])) if np.isfinite(r_kc[m]).any() else None,
                                        "fc_f10_component": float(np.nanmean(r_fc[m])) if np.isfinite(r_fc[m]).any() else None,
                                        "difference_kc_minus_fc_isolates_model_disagreement":
                                            float(np.nanmean((r_kc - r_fc)[m])) if np.isfinite((r_kc - r_fc)[m]).any() else None},
         "seats_z_level": {"funding_signal_z_weight_mean": float(np.nanmean(PHI[m, 1])) if np.isfinite(PHI[m, 1]).any() else None,
                           "model_composite_z_weight_mean": float(np.nanmean(PHI[m, 0])) if np.isfinite(PHI[m, 0]).any() else None}}
    d["net"] = {p: d["price"][p] - d["funding_paid"][p] - d["fee"][p] for p in PARTS}
    OUTJ["per_period"][k] = d

# ───────── seat-extreme subsamples: exact by identity ─────────
f0 = np.isfinite(PHI[:, 1]) & (PHI[:, 1] == 0.0)
m0 = np.isfinite(PHI[:, 0]) & (PHI[:, 0] == 0.0)
SX = {"caveat": "these subsamples are selected by the producer's msharpe seat rule (trailing-Sharpe driven); they are NOT a random sample of history, and no causal reading is available from them",
      "pure_model_composite_funding_seat_exactly_zero": {}, "pure_funding_book_model_seat_exactly_zero": {}}
for tag, mm in (("pure_model_composite_funding_seat_exactly_zero", f0), ("pure_funding_book_model_seat_exactly_zero", m0)):
    for k, m in PERMASK.items():
        s = m & mm
        if s.sum() == 0:
            continue
        _, ss, cc = L.day_aggregate(A, L1["g"], s)
        SX[tag][k] = {"n_anchors": int(s.sum()), "share_of_period": float(s.sum() / m.sum()),
                      "g": float(ss.sum() / cc.sum()),
                      "price": float(L1["price"][s].mean()), "funding_paid": float(L1["funding_paid"][s].mean()),
                      "fee": float(L1["fee"][s].mean())}
SX["identity"] = {"funding_seat_0": "z_kc = w3m[0]·z_king and z_fc = w3m[0]·z_f10; chain is invariant to a positive scale ⇒ the book IS the pure 0.55/0.45 model composite",
                  "model_seat_0": "z_kc = z_fc = w3m[2]·z_fund ⇒ both components are built from the same z ⇒ the book IS the pure funding book (the two can differ only through their separate EMA states)"}
OUTJ["seat_extreme_subsamples"] = SX

# monthly series of the corrected parts (for the 2023 narrative)
mon = np.array([time.strftime("%Y-%m", time.gmtime(int(t))) for t in A])
OUTJ["monthly"] = {}
for m_ in sorted(set(mon.tolist())):
    k = mon == m_
    OUTJ["monthly"][m_] = {"n": int(k.sum()), "g": float(L1["g"][k].mean()),
                           "price_KC": float(px["KC_king_component"][k].mean()),
                           "price_FC": float(px["FC_f10_component"][k].mean()),
                           "price_reshape": float(px["reshape_shift"][k].mean()),
                           "price_KING_FILE": float(px["KING_FILE_3leg"][k].mean()),
                           "r_kc": float(np.nanmean(r_kc[k])) if np.isfinite(r_kc[k]).any() else None,
                           "r_fc": float(np.nanmean(r_fc[k])) if np.isfinite(r_fc[k]).any() else None,
                           "funding_seat_z": float(np.nanmean(PHI[k, 1])) if np.isfinite(PHI[k, 1]).any() else None,
                           "share_combo": float((KIND[k] == 2).mean())}

# the FULL_RECIPE condition cells and the extreme anchors, with the corrected leg columns
COND = Z["COND"][in_run]
CONDN = [str(s) for s in Z["COND_NAMES"]]
G0L = Z["G0L"][in_run]
GVARS = [str(s) for s in Z["G0_VARS"]]
mfull = PERMASK["FULL_RECIPE"]
cells = {}
for cn in L.COND_NAMES:
    if cn not in L.COND_FROM_G0:
        continue
    lab = G0L[:, GVARS.index(L.COND_FROM_G0[cn])]
    cells[cn] = {b_: ({"n_anchors": int((mfull & (lab == bi)).sum()),
                       "price_KC": float(px["KC_king_component"][mfull & (lab == bi)].mean()),
                       "price_FC": float(px["FC_f10_component"][mfull & (lab == bi)].mean()),
                       "price_KING_FILE": float(px["KING_FILE_3leg"][mfull & (lab == bi)].mean())}
                      if (mfull & (lab == bi)).sum() >= 2 else {"n_anchors": int((mfull & (lab == bi)).sum())})
                 for bi, b_ in ((0, "low"), (1, "mid"), (2, "high"))}
OUTJ["condition_cells_FULL_RECIPE_corrected_legs"] = cells

gr = L1["g"]
idx_full = np.nonzero(mfull)[0]
n1p = max(1, int(round(0.01 * len(idx_full))))
ordr = np.argsort(gr[idx_full])
ext = {"bottom": idx_full[ordr[:n1p]].tolist(), "top": idx_full[ordr[-n1p:]][::-1].tolist()}
OUTJ["extreme_anchors_corrected_legs"] = {
    tag: [{"anchor": L.utc(A[i]), "kind": ("combo" if KIND[i] == 2 else "king_file"),
           "g": float(gr[i]), "price_KC": float(px["KC_king_component"][i]),
           "price_FC": float(px["FC_f10_component"][i]), "price_reshape": float(px["reshape_shift"][i]),
           "price_KING_FILE": float(px["KING_FILE_3leg"][i]),
           "funding_seat_z": (float(PHI[i, 1]) if np.isfinite(PHI[i, 1]) else None)}
          for i in ext[tag][:15]] for tag in ("top", "bottom")}

# the 2023 window, with CI on the corrected parts
m23 = PERMASK["2023full"]
mref = PERMASK["2024"] | PERMASK["2025"] | PERMASK["2026"]
F = {}
for j, (nm, x) in enumerate(sorted({"price_KC": px["KC_king_component"], "price_FC": px["FC_f10_component"],
                                    "price_reshape": px["reshape_shift"], "price_KING_FILE": px["KING_FILE_3leg"],
                                    "r_kc_own_gross": np.nan_to_num(r_kc), "r_fc_own_gross": np.nan_to_num(r_fc),
                                    "r_kc_minus_r_fc": np.nan_to_num(r_kc - r_fc)}.items())):
    def ci(mask, k):
        _, s, c = L.day_aggregate(A, x, mask)
        return L.ci_p(float(s.sum() / c.sum()), L.boot_mean_ratio(s, c, seed_k=k))
    F[nm] = {"2023H2": ci(m23, 600 + j), "2024_2026_reference": ci(mref, 700 + j)}
OUTJ["block_F_2023_corrected_legs"] = F
# the KING_FILE bucket unpacked: what the 3-leg king file did ON THE ANCHORS WHERE IT WAS TRADED
k1 = KIND == 1
OUTJ["king_file_anchors_conditional"] = {}
for k, m in PERMASK.items():
    s_ = m & k1
    if s_.sum() < 2:
        continue
    _, ss, cc = L.day_aggregate(A, L1["g"], s_)
    OUTJ["king_file_anchors_conditional"][k] = {
        "n_king_file_anchors": int(s_.sum()), "share_of_period": float(s_.sum() / m.sum()),
        "g_on_those_anchors": float(ss.sum() / cc.sum()),
        "paper_price_on_those_anchors": float(px_tot[s_].mean()),
        "contribution_to_the_period_price": float(px["KING_FILE_3leg"][m].mean()),
        "note": "the producer's ORIGINAL 3-leg king file (king + rev24 + fund, unmasked w3) — not a component of the combo form"}
# and the combo-form anchors on their own
OUTJ["combo_anchors_conditional"] = {}
for k, m in PERMASK.items():
    s_ = m & (KIND == 2)
    if s_.sum() < 2:
        continue
    _, ss, cc = L.day_aggregate(A, L1["g"], s_)
    OUTJ["combo_anchors_conditional"][k] = {
        "n_combo_anchors": int(s_.sum()), "g_on_those_anchors": float(ss.sum() / cc.sum()),
        "paper_price_on_those_anchors": float(px_tot[s_].mean()),
        "price_KC_on_those_anchors": float(px["KC_king_component"][s_].mean()),
        "price_FC_on_those_anchors": float(px["FC_f10_component"][s_].mean())}

p = f"{OUT}/AT_LEGS2.json"
with open(p + ".tmp", "w") as f:
    json.dump(OUTJ, f, indent=1, default=str)
os.replace(p + ".tmp", p)
rec["outputs"] = {"legs2": {"path": p, "sha256": L.sha(p)}}
v = L.write_receipt(rec, chk, f"{OUT}/AT_LEGS2_RECEIPT.json", {"peak_rss_gb": L.rss_gb(), "runtime_s": round(time.time() - T0, 1)})
print("AT_LEGS2 VERDICT=%s checks=%d failed=%s" % (v, len(chk.rows), chk.fails), flush=True)
sys.exit(0 if v == "PASS" else 3)
