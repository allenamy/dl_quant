#!/usr/bin/env python3
"""cf_rebuild.py — CF3 step 1: rebuild every per-anchor input of the combo stage's `chain` from the
archive, re-chain the BASELINE arm over the whole window from a seeded start, and run the STRUCTURAL
ASSERTION (PREREG §4.2, gates S1-S8). Writes CF_STATE.npz ONLY if every gate passes.

What is rebuilt per anchor (nothing is read from the archive that the arms would need to differ on):
  sel        producer L348-350 + L450-451 on the object-B cache tail (G.cache_tail semantics)
  LIVE_MASK  the PIT live set at A (= the universe written into state/target_live/<A>.json)
  rn8        the funding-ledger tail state, simulated with the producer's own section-4 loop
  w3 / w3m   the msharpe seats, from a leg-return series recomputed from P1 legz + the cache
  zf         rankdata of the archived P2 F10 scores (bitwise the production zf, b_lib L135)
  legz       archived (P1.vec)
  H          per-component EMA state, CARRIED FROM MY OWN RE-CHAIN, never taken from the archive

usage: env -i PATH=... HOME=... /workspace/venv/bin/python -B cf_rebuild.py <ENV_WHITELIST_CSV> <OUT_DIR>
"""
import json
import math
import os
import sys
import time

import numpy as np

T0 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/workspace/object_b_2026-09-19/devices")
import cf_lib as L                                     # noqa: E402

ENV_OK = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else set()
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{L.ROOT}/receipts"
LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else 0        # smoke: first N anchors only (never writes CF_STATE)
chk = L.Checks(T0)
rec = L.rec_head("cf_rebuild.py", sys.argv)
extra = sorted(set(rec["env"]) - ENV_OK)
chk("env.whitelist", not extra, {"extra": extra})


def log(*a):
    print("[%7.1fs]" % (time.time() - T0), *a, flush=True)


def fail(msg):
    L.write_receipt(rec, chk, f"{OUT}/CF_REBUILD.json", "REFUSED")
    print("CF_REBUILD VERDICT=REFUSED failed=%s note=%s" % (chk.fails, msg), flush=True)
    sys.exit(3)


# ── inputs ──────────────────────────────────────────────────────────────────
rec["inputs"] = {}
for k, (p, want) in L.PINS.items():
    got = L.sha(p)
    rec["inputs"][k] = {"path": p, "sha256": got}
    if want is not None:
        chk(f"input.{k}.sha256", got == want, {"got": got, "want": want})
if chk.fails:
    fail("pinned input sha mismatch")

import b_driver as BD                                  # noqa: E402

log("loading Globals (cache ~5.7 GB) ...")
G = BD.Globals(load_cache=True)
rec["objb_input_shas"] = G.shas
rec["objb_arm_data"] = {"arm": BD.ARM, "data": BD.DATA}
chk("objb.arm_A0_data_holefix2", BD.ARM == "A0" and BD.DATA == "holefix2", {"arm": BD.ARM, "data": BD.DATA})
SYMS = G.SYMS
COL = G.col
P = G.cfg_raw["params"]
rec["params"] = dict(P)
log("Globals loaded in %.1fs" % G.load_s)

# ★ NpzFile re-decompresses the WHOLE array on every key access (the at_build.py 20 min -> 39 s trap).
#   Materialise every array once.
def _load(path, keys=None):
    z = np.load(path, allow_pickle=True)
    return {k: np.asarray(z[k]) for k in (keys or z.files)}


P1 = _load(L.PINS["P1VEC"][0], ["anchor", "pm_off", "pm", "legz_off", "legz"])
P2 = _load(L.PINS["P2SCORES"][0], ["anchor", "pm_off", "pm", "f10"])
P3 = _load(L.PINS["P3VEC"][0], ["anchor", "king_off", "king_idx", "king_val",
                                "kc_off", "kc_idx", "kc_val", "fc_off", "fc_idx", "fc_val",
                                "king_file_off", "king_file_idx", "king_file_val"])
TG = _load(L.PINS["TARGETS"][0], ["anchor", "scaled_kind", "scaled_off", "scaled_idx", "scaled_val"])
RECS = json.load(open(L.PINS["P3JSON"][0]))["records"]
LRLIVE = json.load(open(L.PINS["LRLIVE"][0]))

A_all = P3["anchor"].astype(np.int64)
N = len(A_all)
chk("axis.aligned", N == len(P1["anchor"]) == len(TG["anchor"]) == len(RECS)
    and np.array_equal(A_all, P1["anchor"].astype(np.int64))
    and np.array_equal(A_all, TG["anchor"].astype(np.int64))
    and all(int(r["anchor"]) == int(a) for r, a in zip(RECS, A_all)), {"n": int(N)})
chk("axis.contiguous_4h", bool(np.all(np.diff(A_all) == L.H4)), {"first": L.iso(A_all[0]), "last": L.iso(A_all[-1])})
if chk.fails:
    fail("axis")

# P2 scores keyed by anchor
P2_off = P2["pm_off"]
P2_idx = {int(a): i for i, a in enumerate(P2["anchor"].astype(np.int64))}

# ── per-anchor state carried by the loop ────────────────────────────────────
LED = {}                                   # col -> list of [ft, rate, iv]  (producer's st.ledger, last 400)
rn8_full = np.full(L.NW, np.nan)
LR = {"king": [], "rev24": [], "fund": []}
look = int(P["msharpe_look"])

prev_sm_kc = prev_sm_fc = prev_sm_f10 = None      # my own carried EMA states (None = state file absent)
prev_king_dense = None                            # producer H at the previous anchor (archived)

# ── outputs ─────────────────────────────────────────────────────────────────
o_sel_idx, o_sel_off = [], [0]
o_rn8 = []                                 # rn8 restricted to pm (float64, NaN where absent)
o_zf = []                                  # zf on pm
o_okf = np.zeros(N, np.int64)
o_w3 = np.zeros((N, 3))
o_w3m = np.zeros((N, 3))
o_lmask = np.zeros((N, L.NW), bool)
o_smf10_idx, o_smf10_val, o_smf10_off = [], [], [0]   # sidecar F10 book (arm-invariant EMA seed at warm starts)
o_has_states = np.zeros(N, bool)
o_kc_src = np.zeros(N, np.int8)            # 0 own, 1 warmstart
o_fc_src = np.zeros(N, np.int8)
o_scaled = np.zeros(N, np.int8)

s1_bad, s2_bad, s3_bad, s4_bad = [], [], [], []
s5_w3_bad, s5_w3m_bad, s6_bad, s7_bad, s8_bad = [], [], [], [], []
n_states = 0

IV_SET = [1.0, 2.0, 4.0, 6.0, 8.0]
FTRIM_HI = -0.0010
DAY = 86400

NRUN = LIMIT if LIMIT else N
log("main loop over %d anchors (LIMIT=%d) ..." % (NRUN, LIMIT))
for k in range(NRUN):
    A = int(A_all[k])
    live = G.live_names(A)
    lmask = np.zeros(L.NW, bool)
    lmask[[COL[s] for s in live]] = True
    o_lmask[k] = lmask
    live_set = set(live)
    base = sorted(set(G.base_names(A)) | live_set)

    # ── producer section 4: funding ledger increment (verbatim loop shape) ──
    for s in base:
        j = COL[s]
        led = LED.get(j)
        last_ts = led[-1][0] if led else A - 40 * DAY
        exp_iv = led[-1][2] if led else 8.0
        if A - last_ts < exp_iv * 3600 * 0.9:
            continue
        a, b = int(G.L_off[j]), int(G.L_off[j + 1])
        ftv = G.L_ft[a:b]
        lo = int(np.searchsorted(ftv, last_ts, side="right"))
        hi = int(np.searchsorted(ftv, A, side="right"))
        hi = min(hi, lo + 100)
        if hi <= lo:
            continue
        if led is None:
            led = []
        for kk in range(lo, hi):
            ft = int(ftv[kk])
            rate = float(G.L_rate[a + kk])
            iv = (ft - led[-1][0]) / 3600.0 if led else 8.0
            iv = float(min(IV_SET, key=lambda x: abs(x - (iv if 0 < iv <= 24 else 8.0))))
            led.append([ft, rate, iv])
        LED[j] = led[-400:]
        r_ = LED[j][-1]
        rn8_full[j] = r_[1] * (8.0 / (r_[2] if r_[2] else 8.0))

    # ── cache slice (producer L332 / L348 / L405 semantics) ─────────────────
    ai = G.row_of_ts[A]
    q0 = max(0, ai + 1 - 2016)
    # producer L332/L348: CDf = st.cd.astype(np.float32); qseg = CDf[.., :, 3].
    # Only channels 3 and 0 are needed; float16 -> float32 is exact elementwise and
    # np.where(...) materialises a fresh C-contiguous (rows, 829) float32 array in either
    # layout, so the axis-0 reduction below is bit-identical to slicing the full 7-channel block.
    sub3 = np.array(G.DATA[q0:ai + 1, :, 3])
    sub3[:, ~lmask] = np.nan
    qseg = sub3.astype(np.float32)
    finq = np.isfinite(qseg)
    qvm = np.where(finq, qseg, 0).sum(0) / np.maximum(finq.sum(0), 1)

    pm = L.pm_of(P1, k)
    qv4h = np.expm1(np.clip(qvm[pm], 0, 30)) * 48
    sel = qv4h >= P["qv4h_min"]

    legz_flat = P1["legz"][int(P1["legz_off"][k]):int(P1["legz_off"][k + 1])]
    legz = legz_flat.reshape(3, -1)          # king, rev24, fund
    z_king_leg, z_rev24_leg, z_fund_leg = legz[0], legz[1], legz[2]

    # ── producer section 6: leg returns for the PREVIOUS anchor ────────────
    if k >= 1:
        pi = G.row_of_ts.get(A - L.H4)
        assert pi is not None and pi >= q0, ("previous anchor row outside the slice", L.iso(A))
        sub0 = np.array(G.DATA[pi + 1:ai + 1, :, 0])
        sub0[:, ~lmask] = np.nan
        seg = sub0.astype(np.float32)
        fin = np.isfinite(seg)
        y4v = np.where(fin, seg, 0).sum(0)
        y4v[fin.sum(0) < 46] = np.nan
        pm_p = L.pm_of(P1, k - 1)
        lz_p = P1["legz"][int(P1["legz_off"][k - 1]):int(P1["legz_off"][k])].reshape(3, -1)
        okl = np.isfinite(y4v[pm_p])
        for li, leg in enumerate(("king", "rev24", "fund")):
            z = lz_p[li]
            zz = np.where(okl, z, 0.0)
            zz = zz - (zz[okl].mean() if okl.sum() else 0)
            g = np.abs(zz).sum()
            LR[leg].append(float((zz / g * np.nan_to_num(y4v[pm_p], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)

    # ── producer section 7: msharpe seats ──────────────────────────────────
    if len(LR["king"]) >= look:
        r = np.stack([np.array(LR[leg][-look:], np.float64) for leg in ("king", "rev24", "fund")])
        shp = r.mean(1) / (r.std(1) + 1e-9)
        shp = np.maximum(shp, 0.0)
        w3 = shp / shp.sum() if shp.sum() > 0 else np.array([1 / 3] * 3)
    else:
        w3 = np.array([1 / 3] * 3)
    o_w3[k] = w3
    w3m = np.array([w3[0], 0.0, w3[2]])
    w3m = w3m / w3m.sum() if w3m.sum() > 1e-12 else np.array([0.5, 0.0, 0.5])
    o_w3m[k] = w3m

    # ── zf from the archived P2 scores ─────────────────────────────────────
    zf = np.full(len(pm), np.nan)
    okf = np.zeros(len(pm), bool)
    pk = P2_idx.get(A)
    if pk is not None:
        a2, b2 = int(P2_off[pk]), int(P2_off[pk + 1])
        pm2 = P2["pm"][a2:b2].astype(np.int64)
        assert np.array_equal(pm2, pm), ("P2 member set differs", L.iso(A))
        zf, okf = L.zf_from_scores(P2["f10"][a2:b2])
    o_okf[k] = int(okf.sum())

    # ── the combo stage ────────────────────────────────────────────────────
    LIVE_MASK = lmask.copy()                                   # = set(target_live universe) over SYMS
    CH = L.Chain(sel, pm, P, LIVE_MASK)

    king_dense = L.csr_dense(P3, "king", k)
    Hfile = L.h_from_weights_file(prev_king_dense) if prev_king_dense is not None else np.zeros(L.NW)

    # sidecar F10 book (needed only to seed H_fc at a warm start; arm-invariant)
    H_f10_prev = prev_sm_f10 if prev_sm_f10 is not None else Hfile
    z_f10book = w3[0] * np.nan_to_num(zf) + w3[1] * np.nan_to_num(z_rev24_leg) + w3[2] * np.nan_to_num(z_fund_leg)
    sm_f10 = CH.run(z_f10book, H_f10_prev)

    z_kc = w3m[0] * np.nan_to_num(z_king_leg) + w3m[2] * np.nan_to_num(z_fund_leg)
    z_fc = w3m[0] * np.nan_to_num(zf) + w3m[2] * np.nan_to_num(z_fund_leg)
    rn8_m = rn8_full[pm]
    _band_kc = (z_kc < 0) & np.isfinite(rn8_m) & (rn8_m <= FTRIM_HI)
    _band_fc = (z_fc < 0) & np.isfinite(rn8_m) & (rn8_m <= FTRIM_HI)
    z_kc = np.where(_band_kc, 0.0, z_kc)
    z_fc = np.where(_band_fc, 0.0, z_fc)

    H_kc_prev = prev_sm_kc if prev_sm_kc is not None else Hfile
    H_fc_prev = prev_sm_fc if prev_sm_fc is not None else H_f10_prev
    o_kc_src[k] = 0 if prev_sm_kc is not None else 1
    o_fc_src[k] = 0 if prev_sm_fc is not None else 1
    sm_kc = CH.run(z_kc, H_kc_prev)
    sm_fc = CH.run(z_fc, H_fc_prev)

    # state files: written in one loop, crashing on the first None (b_driver combo_outcome known_crash)
    has_states = (sm_kc is not None) and (sm_fc is not None)
    o_has_states[k] = has_states

    # ── gates S1 / S2 / S3 / S7 / S8 on this anchor ────────────────────────
    r_ = RECS[k]
    cb = r_.get("combo") or {}
    arch_has = bool(cb.get("has_states"))
    if arch_has != has_states:
        s1_bad.append({"k": k, "utc": L.iso(A), "why": "has_states mismatch", "mine": has_states, "arch": arch_has})
    elif has_states:
        n_states += 1
        ok1, n1 = L.bitwise_equal(sm_kc, L.csr_dense(P3, "kc", k))
        ok2, n2 = L.bitwise_equal(sm_fc, L.csr_dense(P3, "fc", k))
        if not ok1:
            s1_bad.append({"k": k, "utc": L.iso(A), "n_cells": n1})
        if not ok2:
            s2_bad.append({"k": k, "utc": L.iso(A), "n_cells": n2})
        mt = cb.get("ftrim") or {}
        if int(mt.get("n_kc", -1)) != int(_band_kc.sum()) or int(mt.get("n_fc", -1)) != int(_band_fc.sum()):
            s7_bad.append({"k": k, "utc": L.iso(A), "mine": [int(_band_kc.sum()), int(_band_fc.sum())],
                           "arch": [mt.get("n_kc"), mt.get("n_fc")],
                           "rn8_cov_mine": round(float(np.isfinite(rn8_m).mean()), 4), "rn8_cov_arch": mt.get("rn8_coverage")})

    # B-scaled trade decision (b_driver.combo_outcome, verbatim judgement)
    scaled = False
    combo_raw = None
    if has_states:
        combo_raw = 0.55 * sm_kc + 0.45 * sm_fc
        nz = np.where(np.abs(combo_raw) > 1e-9)[0]
        n_mem = len(pm)
        gg = float(np.abs(combo_raw[nz]).sum())
        nn = int(len(nz))
        inside = all(SYMS[int(j)] in live_set for j in nz)
        g_in = float(sum(abs(combo_raw[j]) for j in nz if SYMS[int(j)] in live_set))
        n_in = int(sum(1 for j in nz if SYMS[int(j)] in live_set))
        f380 = math.ceil(380 * n_mem / 400)
        f150 = math.ceil(150 * n_mem / 400)
        scaled = bool((int(okf.sum()) >= f380) and (0.4 <= gg <= 1.2) and (nn >= f150) and inside
                      and (n_in >= f150) and (g_in > 0.4))
    o_scaled[k] = int(scaled)
    arch_traded = r_.get("traded_scaled")
    mine_traded = "combo" if scaled else "king"
    if arch_traded != mine_traded:
        s8_bad.append({"k": k, "utc": L.iso(A), "mine": mine_traded, "arch": arch_traded})

    # S3: the written target == 0.55*kc + 0.45*fc, bitwise, on every kind-2 anchor
    kind = int(TG["scaled_kind"][k])
    tgt_dense = L.csr_dense(TG, "scaled", k)
    if kind == 2:
        if combo_raw is None:
            s3_bad.append({"k": k, "utc": L.iso(A), "why": "kind 2 without states"})
        else:
            cr = np.where(np.abs(combo_raw) > 1e-9, combo_raw, 0.0)
            ok3, n3 = L.bitwise_equal(cr, tgt_dense)
            if not ok3:
                s3_bad.append({"k": k, "utc": L.iso(A), "n_cells": n3})
    elif kind == 1:
        ok4, n4 = L.bitwise_equal(L.csr_dense(P3, "king_file", k), tgt_dense)
        if not ok4:
            s4_bad.append({"k": k, "utc": L.iso(A), "n_cells": n4})

    # S5 / S6 cross-checks against the producer's own recorded scalars
    sig = r_.get("signal") or {}
    if sig.get("w3") is not None and [round(float(x), 4) for x in w3] != list(sig["w3"]):
        s5_w3_bad.append({"k": k, "utc": L.iso(A), "mine": [round(float(x), 4) for x in w3], "arch": sig["w3"]})
    cm = cb.get("combo_meta") or {}
    if cm.get("w3_masked") is not None and [round(float(x), 6) for x in w3m] != list(cm["w3_masked"]):
        s5_w3m_bad.append({"k": k, "utc": L.iso(A), "mine": [round(float(x), 6) for x in w3m], "arch": cm["w3_masked"]})
    if sig.get("sel") is not None and int(sel.sum()) != int(sig["sel"]):
        s6_bad.append({"k": k, "utc": L.iso(A), "mine": int(sel.sum()), "arch": int(sig["sel"])})

    # ── carry ──────────────────────────────────────────────────────────────
    prev_sm_kc = sm_kc if has_states else None
    prev_sm_fc = sm_fc if has_states else None
    prev_sm_f10 = sm_f10                              # None if the sidecar chain degenerated
    prev_king_dense = king_dense
    _fi = np.where(np.abs(sm_f10) > 1e-9)[0] if sm_f10 is not None else np.zeros(0, np.int64)
    o_smf10_idx.append(_fi.astype(np.int16))
    o_smf10_val.append((sm_f10[_fi] if sm_f10 is not None else np.zeros(0)))
    o_smf10_off.append(o_smf10_off[-1] + len(_fi))

    si = np.where(sel)[0].astype(np.int16)
    o_sel_idx.append(si)
    o_sel_off.append(o_sel_off[-1] + len(si))
    o_rn8.append(rn8_m.copy())
    o_zf.append(zf.copy())

    if k % 500 == 0 or k == N - 1:
        log("k=%5d %s states=%d S1bad=%d S3bad=%d S5bad=%d S6bad=%d S7bad=%d S8bad=%d"
            % (k, L.iso(A), n_states, len(s1_bad), len(s3_bad), len(s5_w3_bad) + len(s5_w3m_bad),
               len(s6_bad), len(s7_bad), len(s8_bad)))

# ── S5 bitwise check of the leg-return tail ────────────────────────────────
lr_tail_ok = True
lr_tail_detail = {"skipped_on_smoke": bool(LIMIT)}
for leg in (() if LIMIT else ("king", "rev24", "fund")):
    mine = np.array(LR[leg][-950:], np.float64)
    arch = np.array(LRLIVE[leg], np.float64)
    ok, nbad = L.bitwise_equal(mine, arch) if mine.shape == arch.shape else (False, -1)
    lr_tail_detail[leg] = {"n_mine": len(mine), "n_arch": len(arch), "bitwise": bool(ok), "n_cells_differ": nbad}
    lr_tail_ok &= bool(ok)

# ── verdict ────────────────────────────────────────────────────────────────
chk("S1.sm_kc_bitwise", not s1_bad, {"n_bad": len(s1_bad), "first": s1_bad[:3], "n_state_anchors": n_states})
chk("S2.sm_fc_bitwise", not s2_bad, {"n_bad": len(s2_bad), "first": s2_bad[:3]})
chk("S3.written_target_is_0.55kc+0.45fc_bitwise", not s3_bad,
    {"n_bad": len(s3_bad), "first": s3_bad[:3], "n_kind2": int((TG["scaled_kind"][:NRUN] == 2).sum())})
chk("S4.kind1_target_is_king_file_bitwise", not s4_bad,
    {"n_bad": len(s4_bad), "first": s4_bad[:3], "n_kind1": int((TG["scaled_kind"][:NRUN] == 1).sum())})
chk("S5a.leg_return_tail_bitwise", lr_tail_ok, lr_tail_detail)
chk("S5b.w3_matches_recorded_4dp", not s5_w3_bad, {"n_bad": len(s5_w3_bad), "first": s5_w3_bad[:3]})
chk("S5c.w3_masked_matches_recorded_6dp", not s5_w3m_bad, {"n_bad": len(s5_w3m_bad), "first": s5_w3m_bad[:3]})
chk("S6.sel_count_matches_recorded", not s6_bad, {"n_bad": len(s6_bad), "first": s6_bad[:3]})
chk("S7.ftrim_counts_match_recorded", not s7_bad, {"n_bad": len(s7_bad), "first": s7_bad[:3]})
chk("S8.scaled_trade_decision_matches_recorded", not s8_bad, {"n_bad": len(s8_bad), "first": s8_bad[:3]})

rec["census"] = {"n_anchors": int(NRUN), "n_state_anchors": int(n_states),
                 "n_kind2": int((TG["scaled_kind"][:NRUN] == 2).sum()), "n_kind1": int((TG["scaled_kind"][:NRUN] == 1).sum()),
                 "n_kind0": int((TG["scaled_kind"][:NRUN] == 0).sum()),
                 "n_kc_warmstart": int(o_kc_src[:NRUN].sum()), "n_fc_warmstart": int(o_fc_src[:NRUN].sum())}

if chk.fails:
    fail("structural assertion failed")
if LIMIT:
    L.write_receipt(rec, chk, f"{OUT}/CF_REBUILD_smoke.json", "SMOKE_PASS")
    print("CF_REBUILD VERDICT=SMOKE_PASS (LIMIT=%d, no CF_STATE written) failed=[]" % LIMIT, flush=True)
    sys.exit(0)

np.savez_compressed(
    f"{L.ROOT}/work/CF_STATE.npz",
    anchor=A_all,
    sel_off=np.array(o_sel_off, np.int64), sel_idx=np.concatenate(o_sel_idx).astype(np.int16),
    rn8=np.concatenate(o_rn8), zf=np.concatenate(o_zf),
    pm_off=P1["pm_off"], pm=P1["pm"],
    okf=o_okf, w3=o_w3, w3m=o_w3m, lmask=o_lmask,
    has_states=o_has_states, kc_src=o_kc_src, fc_src=o_fc_src, scaled=o_scaled,
    smf10_off=np.array(o_smf10_off, np.int64),
    smf10_idx=np.concatenate(o_smf10_idx).astype(np.int16) if o_smf10_off[-1] else np.zeros(0, np.int16),
    smf10_val=np.concatenate(o_smf10_val) if o_smf10_off[-1] else np.zeros(0),
    smf10_none=np.array([1 if len(x) == 0 else 0 for x in o_smf10_idx], np.int8),
)
rec["outputs"] = {"CF_STATE.npz": {"path": f"{L.ROOT}/work/CF_STATE.npz", "sha256": L.sha(f"{L.ROOT}/work/CF_STATE.npz")}}
rsha = L.write_receipt(rec, chk, f"{OUT}/CF_REBUILD.json", "PASS")
print("CF_REBUILD VERDICT=PASS checks=%d failed=[] state_anchors=%d receipt_sha256=%s"
      % (len(chk.items), n_states, rsha), flush=True)
