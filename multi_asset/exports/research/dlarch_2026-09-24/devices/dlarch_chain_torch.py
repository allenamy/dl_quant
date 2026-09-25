#!/usr/bin/env python3
"""dlarch_chain_torch.py — a differentiable re-expression of the PRODUCTION `chain`, plus gate G3.

PREREG docs/PREREG_dlarch_T3_leg_gate_2026-09-25.md (fd04f242f) §1.1 / §6.2 G3.

`chain` is combo_stage.py L78-L101, compiled from the sha-pinned producer source by
combo_target.source_kernels(). Its seven steps and how each is made differentiable:

  1 sel mask                  multiply by a known 0/1 vector                -> exact
  2 de-mean on sel            linear                                        -> exact
  3 L1 normalise              differentiable except g<1e-9 (anchor skipped) -> exact
  4 clip(+-cap) then renorm   torch.clamp (sub-gradient)  [MAIN ARM]        -> exact
                              cap*tanh(./cap)             [SENSITIVITY]     -> approximate by design
  5 EMA  H + alpha(tgt-H)     linear, alpha = production constant 0.1       -> exact
  6 dead band |trade|<band    hard threshold: sigmoid((|trade|-band)/s);
                              s=0 recovers the exact step                   -> exact at s=0
  7 exit mask                 multiply by a known 0/1 vector                -> exact

G3 (load-bearing,先红后绿): with s=0 and clamp, this must reproduce the ARCHIVED production book
bit-for-bit -- not "closely", bit-for-bit -- on real anchors, taking H from the archive's own previous
anchor. THREE controls are asserted (lead 2026-09-25):
  GREEN      max|dw| <= 1e-12 on both books, both seeds;
  RED-alpha  alpha *= 1+1e-6 must break parity by >= 100x the tolerance (the first version used 1e-9 and
             cleared the bar by only 1.8x -- a weak demonstration, so lead required a bigger nudge);
  RED-rn8    removing the rn8 funding clamp from the path must break parity. Under lead's ruling (a),
             T3 = rn8 clamp + chain as ONE alignment intervention, so the clamp is part of the object
             under test; this control proves it is actually wired in and not merely present in a
             reference arm. The number of cells the clamp actually zeroes is reported and must be > 0 --
             a clamp that never fires could not be detected by any parity test.

READ-ONLY. CPU only, no GPU (G3 needs none).
usage: env -i PATH=/usr/bin:/bin HOME=/root /workspace/venv/bin/python -B dlarch_chain_torch.py \
         PATH,HOME,LC_CTYPE <outdir> [n_anchors]
"""
import os, sys, json, time, hashlib, calendar

import numpy as np
import torch

W = "/dev/shm/news2_2026-09-23"
MASK_PATH = "/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz"
H4 = 14400
SEG_PRE = ("2023-06-30T04:00:00Z", "2025-12-31T20:00:00Z")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest()


def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ"))
def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def log(*a): print(time.strftime("%H:%M:%S", time.gmtime()), *a, flush=True)


def chain_torch(zc, sel, H, pm, NW, live, cap_mult, alpha, band, s_temp=0.0,
                clamp_mode="clamp", _perturb=None, census=None):
    """Differentiable `chain`. zc, sel: member-length. H, live: NW-length. Returns NW-length smv or None.

    _perturb: for the G3 RED control only -- a multiplicative nudge on `alpha`, which MUST break parity.
    census:   if a dict is passed, it is filled with the DEAD-BAND census for gate G4:
              `band_open_cells`  = cells the band let through (their value is not frozen to H)
              `book_cells`       = cells that are non-zero in either H or the pre-band smv
              This is the object G4 is about -- how much of the BOOK the band freezes. The network's
              parameter-gradient sparsity is NOT that object: the last layer's gradient is a sum over
              every pair in the span, so it is non-zero almost always regardless of the band.
    """
    dt = zc.dtype
    zero = torch.zeros((), dtype=dt, device=zc.device)
    w = torch.where(sel, zc, zero)
    if bool(sel.any()):
        w = torch.where(sel, w - w[sel].mean(), w)
    g = w.abs().sum()
    if float(g) < 1e-9:
        return None
    w = w / g
    capw = cap_mult / max(int(sel.sum()), 1)
    w = torch.clamp(w, -capw, capw) if clamp_mode == "clamp" else capw * torch.tanh(w / capw)
    g2 = w.abs().sum()
    if float(g2) > 1e-9:
        w = w / g2
    tgt = torch.zeros(NW, dtype=dt, device=zc.device).scatter(0, pm, w)
    a = alpha if _perturb is None else alpha * _perturb
    smv = H + a * (tgt - H)
    trade = smv - H
    gate = (trade.abs() >= band).to(dt) if s_temp <= 0 else torch.sigmoid((trade.abs() - band) / s_temp)
    if census is not None:
        pre = H + a * (tgt - H)
        book = ((H.abs() > 0) | (pre.abs() > 0))
        census["band_open_cells"] = int(((gate > 0) & book).sum())
        census["book_cells"] = int(book.sum())
    smv = H + gate * (smv - H)
    keep_liq = torch.zeros(NW, dtype=torch.bool, device=zc.device)
    keep_liq[pm[sel]] = True
    mem = torch.zeros(NW, dtype=torch.bool, device=zc.device); mem[pm] = True
    keep = live & mem & keep_liq
    leave = (~keep) & (smv.abs() > 1e-12)
    return torch.where(leave, zero, smv)


def recon(j, ci, mm, off, leg_arrays, P10, params, apply_rn8=True):
    """Rebuild one anchor's (zfc, zkc, sel, members) from legs + F10 OOF, exactly as the producer does.
    apply_rn8=False drops combo_target.py L33-34 (the funding-sign clamp) -- used only by RED-rn8."""
    from scipy.stats import rankdata
    QV, WLa, KZ, ZFD, RN8 = leg_arrays
    i = ci[j]; pmv = mm[off[i]:off[i + 1]]
    qv = QV[i][pmv].astype(np.float64)
    sel_np = np.isfinite(qv) & (qv >= params["qv4h_min"])
    if sel_np.sum() < params["sel_min"]:
        return None
    wl = WLa[i].astype(np.float64)
    w3 = np.array([wl[0], 0.0, wl[2]])
    w3 = w3 / w3.sum() if w3.sum() > 1e-12 else np.array([.5, 0., .5])
    kr = np.nan_to_num(KZ[i][pmv].astype(np.float64))
    fr = np.nan_to_num(ZFD[i][pmv].astype(np.float64))
    p = P10[i][pmv].astype(np.float64); okf = np.isfinite(p)
    zf = np.zeros(len(pmv))
    if okf.sum(): zf[okf] = rankdata(p[okf]) / max(int(okf.sum()) - 1, 1) - .5
    rn = RN8[i][pmv].astype(np.float64); bad = np.isfinite(rn) & (rn <= -.001)
    out = {"members": pmv, "sel": sel_np, "clamped_fc": 0, "clamped_kc": 0}
    for nm, zpre in (("fc", w3[0] * zf + w3[2] * fr), ("kc", w3[0] * kr + w3[2] * fr)):
        hit = (zpre < 0) & bad
        out["clamped_" + nm] = int(hit.sum())
        out[nm] = np.where(hit, 0.0, zpre) if apply_rn8 else zpre.copy()
    return out


def main():
    assert not sorted(set(os.environ) - set(sys.argv[1].split(","))), "env outside whitelist"
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    nmax = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    sys.path.insert(0, f"{W}/devices")
    import combo_target
    from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA

    src = f"{W}/vendor_live/fea171/combo_stage.py"
    assert sha(src) == combo_target.EXPECTED, "producer source sha"
    assert sha(UNIVERSE_PATH) == UNIVERSE_SHA
    rec = {"device": "dlarch_chain_torch.py", "self_sha256": sha(os.path.abspath(__file__)),
           "prereg": {"path": "docs/PREREG_dlarch_T3_leg_gate_2026-09-25.md", "revision": "3 (lead ruling (a))"},
           "ruling": "lead 2026-09-25: T3 = rn8 clamp + chain, ONE alignment intervention",
           "producer_source": {src: combo_target.EXPECTED}, "utc_start": iso(time.time()),
           "torch": torch.__version__, "device": "cpu", "inputs": {}}

    F = np.load(f"{W}/work/NEWS_FEATURES.npz"); leg = np.load(f"{W}/work/legs.npz")
    fsha = sha(f"{W}/work/NEWS_FEATURES.npz"); lsha = sha(f"{W}/work/legs.npz")
    assert json.load(open(f"{W}/receipts/P2B_FEATURES.json"))["sha256"] == fsha
    assert json.load(open(f"{W}/receipts/P3_LEGS.json"))["sha256"] == lsha
    rec["inputs"].update({f"{W}/work/NEWS_FEATURES.npz": fsha, f"{W}/work/legs.npz": lsha})
    a = F["anchors"].astype(np.int64); syms = F["symbols"]; NW = len(syms)
    off = F["off"]; mm = F["m"].astype(np.int64)
    # materialise ONCE: np.load on an .npz is lazy; leg["QV"] inside a loop re-decompresses (10333,829).
    legarr = (leg["QV"], leg["WL"], leg["KZ"], leg["ZFD"], leg["RN8"]); READY = leg["ready"]
    params = json.loads(open(f"{W}/inputs/bundle_config.json").read())["params"]
    mk = np.load(MASK_PATH); assert np.array_equal(mk["ts"].astype(np.int64), a)
    crypto = np.load(f"{W}/receipts/P1_members_2025H2on.npz")["crypto"]
    cand = mk["mask"] & crypto[None, :]
    universe = np.load(UNIVERSE_PATH)
    use = (a >= 1672531200) & (a <= universe["ts"][-1]); au = a[use]
    book_legal = align_universe(au, syms, universe) & cand[use]
    rec["inputs"][MASK_PATH] = sha(MASK_PATH); rec["inputs"][UNIVERSE_PATH] = UNIVERSE_SHA
    ci = np.searchsorted(a, au); assert np.all(a[ci] == au)
    m_pre = (au >= ts(SEG_PRE[0])) & (au <= ts(SEG_PRE[1]))

    def run(seed, apply_rn8=True, perturb=None, limit=0):
        cp = f"{W}/work/combo_s{seed}/scaled_diagnostic.npz"
        tr = json.load(open(f"{W}/work/combo_s{seed}/TARGET_RECEIPT.json"))
        assert tr["policies"]["scaled_diagnostic"]["sha"] == sha(cp)
        rec["inputs"][cp] = sha(cp)
        C = np.load(cp); assert np.array_equal(C["E_ts"].astype(np.int64), au)
        arch = {"fc": C["fc"], "kc": C["kc"]}
        P10 = np.load(f"{W}/work/f10_s{seed}/F10_OOF.npz")["P"]
        rows = np.flatnonzero(m_pre & READY[ci])
        if limit: rows = rows[:limit]
        st = {"anchors_tested": 0, "skipped_sel_min": 0, "chain_returned_none": 0,
              "max_abs_dw_fc": 0.0, "max_abs_dw_kc": 0.0, "compared_fc": 0, "compared_kc": 0,
              "clamped_cells_fc": 0, "clamped_cells_kc": 0, "anchors_with_any_clamp": 0}
        for j in rows:
            if j == 0: continue
            R = recon(j, ci, mm, off, legarr, P10, params, apply_rn8=apply_rn8)
            if R is None: st["skipped_sel_min"] += 1; continue
            st["anchors_tested"] += 1
            st["clamped_cells_fc"] += R["clamped_fc"]; st["clamped_cells_kc"] += R["clamped_kc"]
            if R["clamped_fc"] or R["clamped_kc"]: st["anchors_with_any_clamp"] += 1
            for nm in ("fc", "kc"):
                out = chain_torch(torch.from_numpy(R[nm]), torch.from_numpy(R["sel"]),
                                  torch.from_numpy(arch[nm][j - 1].astype(np.float64)),
                                  torch.from_numpy(R["members"]), NW,
                                  torch.from_numpy(book_legal[j]), params["cap_mult"], params["alpha"],
                                  params["band"], 0.0, "clamp", _perturb=perturb)
                if out is None: st["chain_returned_none"] += 1; continue
                d = float(np.max(np.abs(out.numpy() - arch[nm][j])))
                st["max_abs_dw_" + nm] = max(st["max_abs_dw_" + nm], d); st["compared_" + nm] += 1
        st["max_abs_dw"] = max(st["max_abs_dw_fc"], st["max_abs_dw_kc"])
        return st

    TOL = 1e-12
    green = {f"s{sd}": run(sd, limit=nmax) for sd in (42, 2027)}
    gmax = max(v["max_abs_dw"] for v in green.values())
    for k, v in green.items(): log("GREEN", k, json.dumps({q: v[q] for q in ("max_abs_dw", "compared_fc", "clamped_cells_fc", "anchors_with_any_clamp")}))
    red_a = run(42, perturb=1.0 + 1e-6, limit=min(nmax, 200) if nmax else 200)
    red_c = run(42, apply_rn8=False, limit=min(nmax, 200) if nmax else 200)
    log("RED-alpha", red_a["max_abs_dw"]); log("RED-rn8", red_c["max_abs_dw"])
    rec["G3"] = {
        "tolerance": TOL, "green": green, "green_max_abs_dw": gmax,
        "GREEN": bool(gmax <= TOL), "green_margin_x": (TOL / gmax) if gmax > 0 else None,
        "red_alpha": {"perturb": "alpha *= 1+1e-6", "max_abs_dw": red_a["max_abs_dw"],
                      "RED": bool(red_a["max_abs_dw"] > TOL),
                      "margin_x": red_a["max_abs_dw"] / TOL,
                      "meets_lead_100x": bool(red_a["max_abs_dw"] >= 100 * TOL),
                      "anchors": red_a["anchors_tested"]},
        "red_no_rn8": {"change": "rn8 funding clamp (combo_target.py L33-34) removed from the path",
                       "max_abs_dw": red_c["max_abs_dw"], "RED": bool(red_c["max_abs_dw"] > TOL),
                       "margin_x": red_c["max_abs_dw"] / TOL if TOL else None,
                       "anchors": red_c["anchors_tested"],
                       "clamped_cells_fc": green["s42"]["clamped_cells_fc"],
                       "clamped_cells_kc": green["s42"]["clamped_cells_kc"],
                       "anchors_with_any_clamp": green["s42"]["anchors_with_any_clamp"],
                       "clamp_actually_fires": bool(green["s42"]["clamped_cells_fc"] > 0)}}
    rec["utc_end"] = iso(time.time())
    op = os.path.join(outdir, "G3_CHAIN_PARITY.json")
    tmp = op + ".tmp"; open(tmp, "w").write(json.dumps(rec, indent=1, allow_nan=False)); os.replace(tmp, op)
    G = rec["G3"]
    print(f"G3_CHAIN_PARITY GREEN={G['GREEN']} green_max_abs_dw={gmax:.3e} green_margin={G['green_margin_x']:.2e}x | "
          f"RED_alpha={G['red_alpha']['RED']} {G['red_alpha']['max_abs_dw']:.3e} ({G['red_alpha']['margin_x']:.1f}x, "
          f"lead_100x={G['red_alpha']['meets_lead_100x']}) | RED_rn8={G['red_no_rn8']['RED']} "
          f"{G['red_no_rn8']['max_abs_dw']:.3e} ({G['red_no_rn8']['margin_x']:.1f}x) "
          f"clamped_cells={G['red_no_rn8']['clamped_cells_fc']} fires={G['red_no_rn8']['clamp_actually_fires']} | "
          f"json={sha(op)[:16]}", flush=True)
    assert G["GREEN"], f"G3 parity FAILED: {gmax:.3e}"
    assert G["red_alpha"]["meets_lead_100x"], "RED-alpha did not clear 100x the tolerance"
    assert G["red_no_rn8"]["RED"], "RED-rn8 vacuous: removing the rn8 clamp did not break parity"
    assert G["red_no_rn8"]["clamp_actually_fires"], "the rn8 clamp never fires -> no parity test could detect it"


if __name__ == "__main__":
    main()
