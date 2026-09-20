#!/usr/bin/env python3
"""cf_arms.py — CF3 step 2: the eight coalitions of {FUND, KING, F10}, each a FULL re-chain of the
combo stage over the whole window from the same seeded start (PREREG §5 + addendum A1).

Entry gate (re-asserted here, not inherited): the BASE arm reproduces the archived kc / fc / written
target BITWISE. If it does not, VERDICT=REFUSED and no arm file is written.

Per arm and anchor the ONLY thing that changes is which of the three signal vectors enters L234/L235;
seats (w3m), sel, LIVE_MASK, cap/alpha/band and the FTRIM rule are the production ones. FTRIM is
recomputed on the arm's own z (faithful to L251/L252). The B-scaled trade decision is recomputed on
the arm's own combo_raw (b_driver.combo_outcome judgement, verbatim).

C-DEGEN / C-DEGEN-STATE (PREREG §5.1 + addendum A1): a component whose z is identically zero on `sel`
(chain's `Sum|w| < 1e-9` branch) contributes the ZERO book and carries the ZERO EMA state.

usage: env -i ... /workspace/venv/bin/python -B cf_arms.py <ENV_WHITELIST_CSV> <OUT_DIR>
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
chk = L.Checks(T0)
rec = L.rec_head("cf_arms.py", sys.argv)
rec["addendum"] = "PREREG addendum A1 C-DEGEN-STATE (committed before this device ran)"
extra = sorted(set(rec["env"]) - ENV_OK)
chk("env.whitelist", not extra, {"extra": extra})


def log(*a):
    print("[%7.1fs]" % (time.time() - T0), *a, flush=True)


def fail(msg):
    L.write_receipt(rec, chk, f"{OUT}/CF_ARMS.json", "REFUSED")
    print("CF_ARMS VERDICT=REFUSED failed=%s note=%s" % (chk.fails, msg), flush=True)
    sys.exit(3)


# ── inputs ──────────────────────────────────────────────────────────────────
STATE_P = f"{L.ROOT}/work/CF_STATE.npz"
REB_P = f"{OUT}/CF_REBUILD.json"
rec["inputs"] = {}
for k, (p, want) in L.PINS.items():
    got = L.sha(p)
    rec["inputs"][k] = {"path": p, "sha256": got}
    if want is not None:
        chk(f"input.{k}.sha256", got == want, {"got": got, "want": want})
REB = json.load(open(REB_P))
rec["inputs"]["CF_REBUILD.json"] = {"path": REB_P, "sha256": L.sha(REB_P)}
rec["inputs"]["CF_STATE.npz"] = {"path": STATE_P, "sha256": L.sha(STATE_P)}
chk("upstream.CF_REBUILD_PASS", REB["verdict"] == "PASS" and not REB["failed"],
    {"verdict": REB["verdict"], "failed": REB["failed"]})
chk("upstream.CF_STATE_sha_matches_receipt",
    REB["outputs"]["CF_STATE.npz"]["sha256"] == L.sha(STATE_P), None)
if chk.fails:
    fail("inputs")


def _load(path, keys=None):
    z = np.load(path, allow_pickle=True)
    return {k: np.asarray(z[k]) for k in (keys or z.files)}


S = _load(STATE_P)
P1 = _load(L.PINS["P1VEC"][0], ["anchor", "pm_off", "pm", "legz_off", "legz"])
P3 = _load(L.PINS["P3VEC"][0], ["anchor", "king_off", "king_idx", "king_val",
                                "kc_off", "kc_idx", "kc_val", "fc_off", "fc_idx", "fc_val",
                                "king_file_off", "king_file_idx", "king_file_val"])
TG = _load(L.PINS["TARGETS"][0], ["anchor", "scaled_kind", "scaled_off", "scaled_idx", "scaled_val"])
CFGJ = json.load(open("/workspace/shadow_bundle_v3/config.json"))
SYMS = list(CFGJ["symbols_panel"])
P = CFGJ["params"]
rec["params"] = dict(P)

A_all = S["anchor"].astype(np.int64)
N = len(A_all)
FTRIM_HI = -0.0010

# ── per-arm re-chain ────────────────────────────────────────────────────────
ARMS = L.ARMS
res = {a: {"kind": np.zeros(N, np.int8), "idx": [], "val": [], "off": [0],
           "kind_gf": np.zeros(N, np.int8), "idx_gf": [], "val_gf": [], "off_gf": [0],
           "degen_kc": np.zeros(N, bool), "degen_fc": np.zeros(N, bool),
           "gross": np.zeros(N), "n_names": np.zeros(N, np.int32)} for a in ARMS}
base_bad = []

log("re-chaining %d arms over %d anchors ..." % (len(ARMS), N))
for arm in L.ARM_ORDER:
    use_fund, use_king, use_f10 = ARMS[arm]
    prev_kc = prev_fc = None
    t_arm = time.time()
    R = res[arm]
    for k in range(N):
        A = int(A_all[k])
        a0, b0 = int(S["pm_off"][k]), int(S["pm_off"][k + 1])
        pm = S["pm"][a0:b0].astype(np.int64)
        n_mem = len(pm)
        sel = np.zeros(n_mem, bool)
        s0, s1 = int(S["sel_off"][k]), int(S["sel_off"][k + 1])
        sel[S["sel_idx"][s0:s1].astype(np.int64)] = True
        rn8_m = S["rn8"][a0:b0]
        zf = S["zf"][a0:b0]
        lmask = S["lmask"][k]
        w3m = S["w3m"][k]
        okf_n = int(S["okf"][k])
        lz = P1["legz"][int(P1["legz_off"][k]):int(P1["legz_off"][k + 1])].reshape(3, -1)
        z_king_leg, z_fund_leg = lz[0], lz[2]

        CH = L.Chain(sel, pm, P, lmask.copy())

        # warm-start seeds (arm-invariant; used only where a component has no own state)
        king_prev = L.csr_dense(P3, "king", k - 1) if k >= 1 else np.zeros(L.NW)
        Hfile = L.h_from_weights_file(king_prev)
        smf10_prev = None
        if k >= 1:
            g0, g1 = int(S["smf10_off"][k - 1]), int(S["smf10_off"][k])
            if g1 > g0 or not S["smf10_none"][k - 1]:
                v = np.zeros(L.NW)
                v[S["smf10_idx"][g0:g1].astype(np.int64)] = S["smf10_val"][g0:g1]
                smf10_prev = v
        H_f10_prev = smf10_prev if smf10_prev is not None else Hfile

        zk = z_king_leg if use_king else np.zeros(n_mem)
        zfu = z_fund_leg if use_fund else np.zeros(n_mem)
        zfa = zf if use_f10 else np.zeros(n_mem)
        z_kc = w3m[0] * np.nan_to_num(zk) + w3m[2] * np.nan_to_num(zfu)
        z_fc = w3m[0] * np.nan_to_num(zfa) + w3m[2] * np.nan_to_num(zfu)
        _band_kc = (z_kc < 0) & np.isfinite(rn8_m) & (rn8_m <= FTRIM_HI)
        _band_fc = (z_fc < 0) & np.isfinite(rn8_m) & (rn8_m <= FTRIM_HI)
        z_kc = np.where(_band_kc, 0.0, z_kc)
        z_fc = np.where(_band_fc, 0.0, z_fc)

        H_kc_prev = prev_kc if prev_kc is not None else Hfile
        H_fc_prev = prev_fc if prev_fc is not None else H_f10_prev
        sm_kc = CH.run(z_kc, H_kc_prev)
        sm_fc = CH.run(z_fc, H_fc_prev)

        # BASE entry gate: bitwise against the archive
        if arm == "BASE":
            if k >= 1:
                ok1, n1 = L.bitwise_equal(sm_kc if sm_kc is not None else np.zeros(L.NW),
                                          L.csr_dense(P3, "kc", k))
                ok2, n2 = L.bitwise_equal(sm_fc if sm_fc is not None else np.zeros(L.NW),
                                          L.csr_dense(P3, "fc", k))
                if not (ok1 and ok2):
                    base_bad.append({"k": k, "utc": L.iso(A), "kc_cells": n1, "fc_cells": n2})

        # C-DEGEN / C-DEGEN-STATE (PREREG addendum A1) with the A2 carve-out:
        # a degeneracy that PRODUCTION ALSO HAD at this anchor (BASE has no states) is not
        # arm-induced, so production semantics apply there (no state file -> warm start next anchor).
        d_kc = sm_kc is None
        d_fc = sm_fc is None
        R["degen_kc"][k] = d_kc
        R["degen_fc"][k] = d_fc
        prod_degen = not bool(S["has_states"][k])
        sm_kc_e = np.zeros(L.NW) if d_kc else sm_kc
        sm_fc_e = np.zeros(L.NW) if d_fc else sm_fc
        combo_raw = 0.55 * sm_kc_e + 0.45 * sm_fc_e
        if prod_degen:
            prev_kc = None if d_kc else sm_kc
            prev_fc = None if d_fc else sm_fc
        else:
            prev_kc, prev_fc = sm_kc_e, sm_fc_e

        # B-scaled decision on this arm's own book (b_driver.combo_outcome judgement)
        nz = np.where(np.abs(combo_raw) > 1e-9)[0]
        gg = float(np.abs(combo_raw[nz]).sum())
        nn = int(len(nz))
        live_cols = lmask
        inside = bool(live_cols[nz].all()) if nn else True
        g_in = float(np.abs(combo_raw[nz][live_cols[nz]]).sum()) if nn else 0.0
        n_in = int(live_cols[nz].sum()) if nn else 0
        f380 = math.ceil(380 * n_mem / 400)
        f150 = math.ceil(150 * n_mem / 400)
        scaled = bool((okf_n >= f380) and (0.4 <= gg <= 1.2) and (nn >= f150) and inside
                      and (n_in >= f150) and (g_in > 0.4))
        R["gross"][k] = gg
        R["n_names"][k] = nn
        kf_i, kf_v = L.csr(P3, "king_file", k)
        kf_i = kf_i.astype(np.int16)
        cb_i, cb_v = nz.astype(np.int16), combo_raw[nz]
        # G-FAITHFUL (PREREG 5.2): the arm's own B-scaled preflight decides
        if scaled:
            R["kind"][k] = 2
            i_, v_ = cb_i, cb_v
        else:
            R["kind"][k] = 1
            i_, v_ = kf_i, kf_v
        R["idx"].append(i_)
        R["val"].append(v_)
        R["off"].append(R["off"][-1] + len(i_))
        # G-FROZEN (PREREG addendum A3): BASE's kind decides; preflight floors waived on BASE-combo
        # anchors whenever this arm's book is non-empty
        if int(res["BASE"]["kind"][k]) == 2 and nn > 0:
            R["kind_gf"][k] = 2
            gi_, gv_ = cb_i, cb_v
        else:
            R["kind_gf"][k] = 1
            gi_, gv_ = kf_i, kf_v
        R["idx_gf"].append(gi_)
        R["val_gf"].append(gv_)
        R["off_gf"].append(R["off_gf"][-1] + len(gi_))
    log("arm %-9s done in %5.1fs  GF-AITH kind2=%5d kind1=%5d | GFROZEN kind2=%5d kind1=%5d | degen_kc=%5d degen_fc=%5d"
        % (arm, time.time() - t_arm, int((R["kind"] == 2).sum()), int((R["kind"] == 1).sum()),
           int((R["kind_gf"] == 2).sum()), int((R["kind_gf"] == 1).sum()),
           int(R["degen_kc"].sum()), int(R["degen_fc"].sum())))

chk("GATE_ENTRY.base_arm_bitwise_vs_archive", not base_bad,
    {"n_bad": len(base_bad), "first": base_bad[:3], "n_checked": N - 1})

# BASE must also reproduce the archived kind and the archived written target exactly
kb = res["BASE"]
kind_bad = int((kb["kind"] != TG["scaled_kind"]).sum())
chk("GATE_ENTRY.base_kind_equals_archive", kind_bad == 0, {"n_differ": kind_bad})
tgt_bad = []
for k in range(N):
    a, b = int(kb["off"][k]), int(kb["off"][k + 1])
    mine = np.zeros(L.NW)
    mine[kb["idx"][k].astype(np.int64)] = kb["val"][k]
    ok, nc = L.bitwise_equal(mine, L.csr_dense(TG, "scaled", k))
    if not ok:
        tgt_bad.append({"k": k, "utc": L.iso(int(A_all[k])), "n_cells": nc})
chk("GATE_ENTRY.base_written_target_bitwise_vs_archive", not tgt_bad,
    {"n_bad": len(tgt_bad), "first": tgt_bad[:3], "n_checked": N})

chk("GATE_ENTRY.base_GF_equals_base_FAITHFUL",
    bool(np.array_equal(res["BASE"]["kind"], res["BASE"]["kind_gf"]))
    and all(np.array_equal(a, b) for a, b in zip(res["BASE"]["idx"], res["BASE"]["idx_gf"])), None)
if chk.fails:
    fail("entry gate failed — no arm file written")

# ── write one TARGETS npz + receipt per arm ─────────────────────────────────
rec["arms"] = {}
VARIANTS = [(a, "G-FAITHFUL", "kind", "off", "idx", "val") for a in L.ARM_ORDER] + \
           [(a, "G-FROZEN", "kind_gf", "off_gf", "idx_gf", "val_gf") for a in L.ARM_ORDER if a != "BASE"]
for arm, gate, kk, ok, ik, vk in VARIANTS:
    R = res[arm]
    tag = arm if gate == "G-FAITHFUL" else arm + "_GF"
    npz = f"{L.ROOT}/work/TARGETS_CF_{tag}.npz"
    np.savez_compressed(
        npz,
        anchor=A_all,
        scaled_kind=R[kk],
        scaled_off=np.array(R[ok], np.int64),
        scaled_idx=np.concatenate(R[ik]).astype(np.int16),
        scaled_val=np.concatenate(R[vk]).astype(np.float64),
    )
    nsha = L.sha(npz)
    doc = {"tag": f"CF_{tag}", "arm": "A0", "data": "holefix2",
           "comparison_type": "(1) historical recipe — object B A0_main, CF3 counterfactual re-chain",
           "counterfactual": {"arm": arm, "coalition": {"FUND": bool(L.ARMS[arm][0]), "KING": bool(L.ARMS[arm][1]),
                                                        "F10": bool(L.ARMS[arm][2])},
                              "convention": "C-DEGEN + C-DEGEN-STATE (PREREG 5.1 + addendum A1/A2)",
                              "gate_convention": gate},
           "prereg": "docs/PREREG_three_signal_counterfactual_2026-09-20.md",
           "source_targets": {"path": L.PINS["TARGETS"][0], "sha256": L.sha(L.PINS["TARGETS"][0])},
           "n_anchors": int(N), "axis": [L.iso(A_all[0]), L.iso(A_all[-1])],
           "B_CORE_start": "2023-06-30T04:00:00Z",
           "B_CORE_rule": "object-B receipts TARGETS_A0_main.json B_CORE_start, carried over unchanged",
           "PRE_window": ["2022-06-30T00:00:00Z", "2023-06-30T00:00:00Z",
                          "PARTIAL_RECIPE — seat warm-up / missing legs; not the production strategy"],
           "counts_by_kind": {"combo": int((R[kk] == 2).sum()), "king": int((R[kk] == 1).sum()),
                              "hold": int((R[kk] == 0).sum())},
           "degenerate_anchors": {"DEGEN_BOTH": int((R["degen_kc"] & R["degen_fc"]).sum()),
                                  "DEGEN_ONE": int((R["degen_kc"] ^ R["degen_fc"]).sum()),
                                  "degen_kc": int(R["degen_kc"].sum()), "degen_fc": int(R["degen_fc"].sum())},
           "kind_flip_vs_BASE": int((R[kk] != res["BASE"]["kind"]).sum()),
           "targets_npz_sha256": nsha,
           "self_sha256": L.sha(os.path.abspath(sys.argv[0])), "lib_sha256": L.sha(f"{HERE}/cf_lib.py"),
           "utc": L.iso(time.time())}
    rp = f"{OUT}/TARGETS_CF_{tag}.json"
    tmp = rp + ".tmp"
    with open(tmp, "w") as f:
        json.dump(doc, f, indent=1)
    os.replace(tmp, rp)
    rec["arms"][tag] = {"npz": npz, "gate_convention": gate, "npz_sha256": nsha, "receipt": rp, "receipt_sha256": L.sha(rp),
                        "counts_by_kind": doc["counts_by_kind"], "degenerate_anchors": doc["degenerate_anchors"],
                        "kind_flip_vs_BASE": doc["kind_flip_vs_BASE"]}

# per-period named subsets (PREREG §7.3) — counts only, no outcome quantity yet
rec["named_subsets_by_period"] = {}
for per in ("HIST", "2026", "FULL_RECIPE", "PRE", "ALL_2022_06"):
    m = L.period_mask(A_all, per)
    d = {"n_anchors": int(m.sum())}
    for arm in L.ARM_ORDER:
        R = res[arm]
        d[arm] = {"kind2": int((R["kind"][m] == 2).sum()), "kind1": int((R["kind"][m] == 1).sum()),
                  "GF_kind2": int((R["kind_gf"][m] == 2).sum()), "GF_kind1": int((R["kind_gf"][m] == 1).sum()),
                  "GF_EMPTY_to_king": int(((R["kind_gf"][m] == 1) & (res["BASE"]["kind"][m] == 2)).sum()),
                  "DEGEN_BOTH": int((R["degen_kc"][m] & R["degen_fc"][m]).sum()),
                  "DEGEN_ONE": int((R["degen_kc"][m] ^ R["degen_fc"][m]).sum()),
                  "KIND_FLIP_vs_BASE": int((R["kind"][m] != res["BASE"]["kind"][m]).sum())}
    rec["named_subsets_by_period"][per] = d

np.savez_compressed(f"{L.ROOT}/work/CF_ARM_FLAGS.npz", anchor=A_all,
                    **{f"{a}_kind": res[a]["kind"] for a in L.ARM_ORDER},
                    **{f"{a}_kind_gf": res[a]["kind_gf"] for a in L.ARM_ORDER},
                    **{f"{a}_degen_kc": res[a]["degen_kc"] for a in L.ARM_ORDER},
                    **{f"{a}_degen_fc": res[a]["degen_fc"] for a in L.ARM_ORDER},
                    **{f"{a}_gross": res[a]["gross"] for a in L.ARM_ORDER},
                    **{f"{a}_n_names": res[a]["n_names"] for a in L.ARM_ORDER})
rec["outputs"] = {"CF_ARM_FLAGS.npz": {"path": f"{L.ROOT}/work/CF_ARM_FLAGS.npz",
                                       "sha256": L.sha(f"{L.ROOT}/work/CF_ARM_FLAGS.npz")}}
rsha = L.write_receipt(rec, chk, f"{OUT}/CF_ARMS.json", "PASS")
print("CF_ARMS VERDICT=PASS checks=%d failed=[] arm_files=%d receipt_sha256=%s"
      % (len(chk.items), len(VARIANTS), rsha), flush=True)
