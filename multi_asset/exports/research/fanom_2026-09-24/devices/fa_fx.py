"""fa_fx.py — build the FX1/FX2/FX3 variant combos (08-30 FTRIM, same-caliber re-judgement).

PREREG docs/PREREG_FX1_FX3_same_caliber_2026-09-25.md + 修订 1 (lead: field = `last_rate`, two stages).
STAGE 1 (provisional): the rate comes from the LOCAL ledger `last_rate`. Two local sources are already KNOWN to
disagree on 5,613 cells (common/FUNDING_SOURCE_DISAGREEMENT_CELLS_2026-09-25.csv); the final verdict is stage 2's.

SPEC, verbatim from eda/w10_ftrim_63feb2f7193f_2026-08-30.py L178-187:
    if FTRIM_MODE != "off":
        _hit = (sm < 0) & (_fnf <= FTRIM_TH)
        if _hit.any():
            _g_orig = np.abs(sm).sum()
            sm[_hit] = 0.0 if FTRIM_MODE == "zero" else sm[_hit] * 0.5
            _g_new = np.abs(sm).sum()
            if _g_new > 1e-9: sm = sm * (_g_orig / _g_new)
  FX1 = zero @ -0.0030 | FX2 = half @ -0.0030 | FX3 = zero @ -0.0010

WHY THIS IS POST-PROCESSING AND NOT A KERNEL EDIT: `continuous_combo.evolve` writes `raw` UNCONDITIONALLY
(`if result['raw'] is not None`), so the pre-gate book exists for every ready anchor. FTRIM acts on that book and
RESTORES gross exactly, so of the kernel's three gates (combo_target.py L41-43) only `names` can change:
  L41 F10 coverage -> depends on f10_score, untouched by FTRIM  => carried from the BASE's own reason string
  L42 gross        -> FTRIM restores gross exactly              => asserted unchanged, not recomputed from scratch
  L43 names        -> zeroing names REDUCES the count           => the one gate that must be re-evaluated

★ The gate re-evaluation is CERTIFIED, not trusted: run on the UNMODIFIED raw it must reproduce the stored
  `trade_mask` AND the stored `reason` strings BITWISE. If it does not, the device stops and builds nothing --
  a reimplemented gate that cannot reproduce the kernel's own output is not a gate, it is a guess.
  (Same discipline as the C3m recovery expression, which was certified on 6,483/6,203 anchors.)

usage: ... fa_fx.py WL <arm> <seed> <base_combo_dir> <features.npz> <fund_replay.npz> <out_dir>
       arm in {FX1,FX2,FX3,FXNULL}; FXNULL = threshold -inf, the G0 degeneracy control (must be bitwise base)
"""
import os, sys, json, hashlib, time
import numpy as np

WL_ = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WL_); assert not _x, f"env outside whitelist: {_x}"
ARM, SEED, BASE, FEAT, REPLAY, OUT = sys.argv[2:8]
MODES = ["scaled_diagnostic", "literal"]
SPEC = {"FX1": ("zero", -0.0030), "FX2": ("half", -0.0030), "FX3": ("zero", -0.0010),
        "FXNULL": ("zero", -float("inf"))}
assert ARM in SPEC, f"unknown arm {ARM}"
FTRIM_MODE, FTRIM_TH = SPEC[ARM]
REASON_ORDER = ["F10 coverage", "gross", "names"]      # combo_target.py L41,L42,L43 append in this order


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def write_json_verified(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=float); f.flush(); os.fsync(f.fileno())
    with open(tmp) as f:
        assert json.load(f) == json.loads(json.dumps(obj, default=float)), "receipt did not read back equal"
    s = sha(tmp); os.replace(tmp, path); return s


def gates(raw, n_members, coverage_failed, policy):
    """combo_target.py L38-L43, applied to a given raw. Returns (trade_mask, reason strings)."""
    gross = np.abs(raw).sum(1)
    names = (np.abs(raw) > 1e-9).sum(1)
    names_gate = np.full(len(raw), 150) if policy == "literal" else np.ceil(.375 * n_members).astype(np.int64)
    tm = np.ones(len(raw), bool); reasons = []
    for i in range(len(raw)):
        r = []
        if coverage_failed[i]: r.append("F10 coverage")
        if not (.4 <= gross[i] <= 1.2): r.append("gross")
        if names[i] < names_gate[i]: r.append("names")
        reasons.append(",".join(r) if r else "publish"); tm[i] = not r
    return tm, np.asarray(reasons), gross, names


os.makedirs(OUT, exist_ok=True)
F = np.load(FEAT, allow_pickle=True); R = np.load(REPLAY, allow_pickle=False)
rec = {"device": "fa_fx.py", "self_sha256": sha(os.path.abspath(__file__)), "arm": ARM, "seed": SEED,
       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "prereg": "docs/PREREG_FX1_FX3_same_caliber_2026-09-25.md + 修订 1",
       "stage": "1 (PROVISIONAL) — rate from the LOCAL ledger last_rate; 5,613 cells already known to disagree "
                "between two local sources; the final verdict belongs to stage 2 (exchange-archive truth)",
       "spec": {"FTRIM_MODE": FTRIM_MODE, "FTRIM_TH": FTRIM_TH,
                "source": "eda/w10_ftrim_63feb2f7193f_2026-08-30.py L178-187 (verbatim)"},
       "rate_field": {"name": "last_rate", "file": REPLAY, "sha256": sha(REPLAY),
                      "why": "08-30 applied the threshold to f_fund_now = the RAW settlement rate "
                             "(r6_panel_splice.py L92 keeps the normalised rate as a SEPARATE variable rate_nf)"},
       "modes": {}}

for pol in MODES:
    zb = np.load(os.path.join(BASE, pol + ".npz"), allow_pickle=False)
    E = zb["E_ts"].astype(np.int64); syms = zb["symbols"]; raw_b = zb["raw"]
    tm_b, reason_b = zb["trade_mask"], zb["reason"]
    # member counts, aligned by anchor
    fa = F["anchors"].astype(np.int64); fcnt = F["count"].astype(np.int64)
    fi = {t: i for i, t in enumerate(fa)}
    assert all(int(t) in fi for t in E), "combo anchors not covered by the features axis"
    n_mem = np.array([fcnt[fi[int(t)]] for t in E], np.int64)
    coverage_failed = np.array(["F10 coverage" in str(x) for x in reason_b], bool)

    # ---- POSITIVE CONTROL: the re-evaluated gates must reproduce the kernel's own output BITWISE ----
    tm0, rs0, gross0, names0 = gates(raw_b, n_mem, coverage_failed, pol)
    ok_tm = bool(np.array_equal(tm0, tm_b))
    ok_rs = bool(np.array_equal(rs0, reason_b.astype(rs0.dtype)))
    assert ok_tm and ok_rs, (f"{pol}: gate re-evaluation does NOT reproduce the kernel's stored output "
                             f"(trade_mask ok={ok_tm}, reason ok={ok_rs}) — refusing to build the arm")

    # ---- the arm: FTRIM on raw, then restore gross (08-30 L178-187) ----
    rate = R["last_rate"]; ra = R["anchors"].astype(np.int64); rsy = [str(s) for s in R["symbols"]]
    assert rsy == [str(s) for s in syms], "replay symbol axis differs from the combo's"
    ri = {t: i for i, t in enumerate(ra)}
    assert all(int(t) in ri for t in E), "combo anchors not covered by the replay axis"
    rate_a = np.stack([rate[ri[int(t)]] for t in E])
    fnf = np.nan_to_num(rate_a, nan=0.0)                       # 08-30 L179: nan -> 0.0
    hit = (raw_b < 0) & (fnf <= FTRIM_TH)                      # 08-30 L180
    raw_v = raw_b.copy()
    g_orig = np.abs(raw_b).sum(1)
    if FTRIM_MODE == "zero": raw_v[hit] = 0.0                  # 08-30 L184
    else: raw_v[hit] = raw_v[hit] * 0.5
    g_new = np.abs(raw_v).sum(1)
    scale = np.where(g_new > 1e-9, g_orig / np.where(g_new > 1e-9, g_new, 1.0), 1.0)   # 08-30 L186-187
    raw_v = raw_v * scale[:, None]

    tm_v, rs_v, gross_v, names_v = gates(raw_v, n_mem, coverage_failed, pol)
    w_v = np.where(tm_v[:, None], np.where(np.abs(raw_v) > 1e-9, raw_v, 0.0), 0.0)     # evolve L40-42

    # ---- assertions the prereg requires ----
    anch_hit = hit.any(1)
    gross_dev = np.abs(gross_v - g_orig)[anch_hit & (g_new > 1e-9)]
    c = {"gross_conserved_on_hit_anchors_max_dev": float(gross_dev.max()) if gross_dev.size else 0.0,
         "gross_gate_verdict_unchanged": bool(np.array_equal((~((.4 <= gross_v) & (gross_v <= 1.2))),
                                                             (~((.4 <= g_orig) & (g_orig <= 1.2))))),
         "publish_only_base": int((tm_b & ~tm_v).sum()), "publish_only_variant": int((tm_v & ~tm_b).sum()),
         "publish_net": int(tm_v.sum() - tm_b.sum()),
         "trade_mask_bitwise_equal_base": bool(np.array_equal(tm_v, tm_b)),
         "hit_cells": int(hit.sum()), "hit_anchors": int(anch_hit.sum()),
         "weight_cells_differing": int((w_v != zb["weights"]).sum())}
    if ARM == "FXNULL":
        # G0 degeneracy control: threshold -inf can never fire => every array bitwise identical to base
        for k, a, b in (("raw", raw_v, raw_b), ("weights", w_v, zb["weights"]), ("trade_mask", tm_v, tm_b)):
            c["G0_" + k + "_bitwise_base"] = bool(np.array_equal(a, b))
        assert all(c["G0_" + k + "_bitwise_base"] for k in ("raw", "weights", "trade_mask")), \
            "G0 FAILED: threshold -inf changed the product"
        assert c["hit_cells"] == 0, "G0 FAILED: -inf threshold produced hits"
    else:
        assert c["hit_cells"] > 0, f"{pol}: arm is empty (no hits) — it degenerates to the baseline"
        assert c["gross_conserved_on_hit_anchors_max_dev"] < 1e-9, \
            f"{pol}: gross NOT conserved (max dev {c['gross_conserved_on_hit_anchors_max_dev']:.3e}) — L186-187 did not take"

    out = {"E_ts": E, "symbols": syms, "kc": zb["kc"], "fc": zb["fc"], "raw": raw_v,
           "weights": w_v, "trade_mask": tm_v, "reason": rs_v}
    p = os.path.join(OUT, pol + ".npz")
    np.savez(p + ".tmp.npz", **out); os.replace(p + ".tmp.npz", p)
    zr = np.load(p, allow_pickle=False)
    assert all(np.array_equal(zr[k], out[k]) for k in out), f"{pol}: written npz does not read back bitwise"
    rec["modes"][pol] = dict(c, npz=p, npz_sha256=sha(p),
                             positive_control_gates_reproduce_kernel={"trade_mask": ok_tm, "reason": ok_rs})
    print("FA_FX %-4s %-18s hits=%7d/%5d anchors  publish base=%d var=%d (only_base=%d only_var=%d)  wcells=%d  gross_dev=%.2e"
          % (ARM, pol, c["hit_cells"], c["hit_anchors"], int(tm_b.sum()), int(tm_v.sum()),
             c["publish_only_base"], c["publish_only_variant"], c["weight_cells_differing"],
             c["gross_conserved_on_hit_anchors_max_dev"]), flush=True)

s = write_json_verified(rec, os.path.join(OUT, "FA_FX_RECEIPT.json"))
print("FA_FX %s receipt sha=%s" % (ARM, s[:16]), flush=True)
