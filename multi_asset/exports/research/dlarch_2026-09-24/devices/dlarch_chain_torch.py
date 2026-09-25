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
anchor. Then a deliberately perturbed coefficient must make that parity go RED. Both are asserted.

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
                clamp_mode="clamp", _perturb=None):
    """Differentiable `chain`. zc, sel: member-length. H, live: NW-length. Returns NW-length smv or None.

    _perturb: for the G3 RED control only -- a multiplicative nudge on `alpha`, which MUST break parity.
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
    smv = H + gate * (smv - H)
    keep_liq = torch.zeros(NW, dtype=torch.bool, device=zc.device)
    keep_liq[pm[sel]] = True
    mem = torch.zeros(NW, dtype=torch.bool, device=zc.device); mem[pm] = True
    keep = live & mem & keep_liq
    leave = (~keep) & (smv.abs() > 1e-12)
    return torch.where(leave, zero, smv)


def main():
    assert not sorted(set(os.environ) - set(sys.argv[1].split(","))), "env outside whitelist"
    outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
    nmax = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    sys.path.insert(0, f"{W}/devices")
    import combo_target
    from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA
    from scipy.stats import rankdata

    src = f"{W}/vendor_live/fea171/combo_stage.py"
    assert sha(src) == combo_target.EXPECTED, "producer source sha"
    assert sha(UNIVERSE_PATH) == UNIVERSE_SHA
    rec = {"device": "dlarch_chain_torch.py", "self_sha256": sha(os.path.abspath(__file__)),
           "prereg": {"path": "docs/PREREG_dlarch_T3_leg_gate_2026-09-25.md", "commit": "fd04f242f"},
           "producer_source": {src: combo_target.EXPECTED}, "utc_start": iso(time.time()),
           "torch": torch.__version__, "device": "cpu", "inputs": {}}

    F = np.load(f"{W}/work/NEWS_FEATURES.npz"); leg = np.load(f"{W}/work/legs.npz")
    fsha = sha(f"{W}/work/NEWS_FEATURES.npz"); lsha = sha(f"{W}/work/legs.npz")
    assert json.load(open(f"{W}/receipts/P2B_FEATURES.json"))["sha256"] == fsha
    assert json.load(open(f"{W}/receipts/P3_LEGS.json"))["sha256"] == lsha
    rec["inputs"].update({f"{W}/work/NEWS_FEATURES.npz": fsha, f"{W}/work/legs.npz": lsha})
    a = F["anchors"].astype(np.int64); syms = F["symbols"]; NW = len(syms)
    off = F["off"]; mm = F["m"].astype(np.int64)
    # ★ materialise ONCE. np.load on an .npz returns a lazy loader: `leg["QV"]` inside a per-anchor loop
    # re-reads and re-decompresses the whole (10333, 829) array every single iteration. The first run of
    # this device did exactly that and had to be killed. Correctness was never at risk; speed was.
    QV = leg["QV"]; WLa = leg["WL"]; KZ = leg["KZ"]; ZFD = leg["ZFD"]; RN8 = leg["RN8"]; READY = leg["ready"]
    params = json.loads(open(f"{W}/inputs/bundle_config.json").read())["params"]
    mk = np.load(MASK_PATH); assert np.array_equal(mk["ts"].astype(np.int64), a)
    crypto = np.load(f"{W}/receipts/P1_members_2025H2on.npz")["crypto"]
    cand = mk["mask"] & crypto[None, :]
    universe = np.load(UNIVERSE_PATH)
    use = (a >= 1672531200) & (a <= universe["ts"][-1]); au = a[use]
    book_legal = align_universe(au, syms, universe) & cand[use]
    rec["inputs"][MASK_PATH] = sha(MASK_PATH); rec["inputs"][UNIVERSE_PATH] = UNIVERSE_SHA

    results = {}
    for seed in (42, 2027):
        cp = f"{W}/work/combo_s{seed}/scaled_diagnostic.npz"
        tr = json.load(open(f"{W}/work/combo_s{seed}/TARGET_RECEIPT.json"))
        assert tr["policies"]["scaled_diagnostic"]["sha"] == sha(cp)
        rec["inputs"][cp] = sha(cp)
        C = np.load(cp); ca = C["E_ts"].astype(np.int64)
        assert np.array_equal(ca, au), "combo axis != use-axis"
        FC = C["fc"]; KC = C["kc"]
        P10 = np.load(f"{W}/work/f10_s{seed}/F10_OOF.npz")["P"]
        ci = np.searchsorted(a, ca)
        m_pre = (ca >= ts(SEG_PRE[0])) & (ca <= ts(SEG_PRE[1]))
        rows = np.flatnonzero(m_pre & READY[ci])
        if nmax: rows = rows[:nmax]
        worst_fc = worst_kc = 0.0; nfc = nkc = 0; skipped = 0; none_cnt = 0
        for j in rows:
            if j == 0: continue
            i = ci[j]; pmv = mm[off[i]:off[i + 1]]
            qv = QV[i][pmv].astype(np.float64)
            sel_np = np.isfinite(qv) & (qv >= params["qv4h_min"])
            if sel_np.sum() < params["sel_min"]: skipped += 1; continue
            wl = WLa[i].astype(np.float64)
            w3 = np.array([wl[0], 0.0, wl[2]]); w3 = w3 / w3.sum() if w3.sum() > 1e-12 else np.array([.5, 0., .5])
            kr = np.nan_to_num(KZ[i][pmv].astype(np.float64))
            fr = np.nan_to_num(ZFD[i][pmv].astype(np.float64))
            p = P10[i][pmv].astype(np.float64); okf = np.isfinite(p)
            zf = np.zeros(len(pmv))
            if okf.sum(): zf[okf] = rankdata(p[okf]) / max(int(okf.sum()) - 1, 1) - .5
            rn = RN8[i][pmv].astype(np.float64); bad = np.isfinite(rn) & (rn <= -.001)
            for nm, zpre, arch in (("fc", w3[0] * zf + w3[2] * fr, FC), ("kc", w3[0] * kr + w3[2] * fr, KC)):
                zc = np.where((zpre < 0) & bad, 0.0, zpre)
                out = chain_torch(torch.from_numpy(zc), torch.from_numpy(sel_np),
                                  torch.from_numpy(arch[j - 1].astype(np.float64)),
                                  torch.from_numpy(pmv), NW, torch.from_numpy(book_legal[j]),
                                  params["cap_mult"], params["alpha"], params["band"], 0.0, "clamp")
                if out is None: none_cnt += 1; continue
                d = float(np.max(np.abs(out.numpy() - arch[j])))
                if nm == "fc": worst_fc = max(worst_fc, d); nfc += 1
                else: worst_kc = max(worst_kc, d); nkc += 1
        results[f"s{seed}"] = {"anchors_tested": int(len(rows)), "fc_compared": nfc, "kc_compared": nkc,
                              "max_abs_dw_fc": worst_fc, "max_abs_dw_kc": worst_kc,
                              "skipped_sel_min": skipped, "chain_returned_none": none_cnt}
        log("G3", seed, json.dumps(results[f"s{seed}"]))

    # ── G3 RED control: perturb alpha by 1+1e-9; parity MUST break ──
    seed = 42
    C = np.load(f"{W}/work/combo_s{seed}/scaled_diagnostic.npz"); FC = C["fc"]
    P10 = np.load(f"{W}/work/f10_s{seed}/F10_OOF.npz")["P"]
    ci = np.searchsorted(a, au)
    m_pre = (au >= ts(SEG_PRE[0])) & (au <= ts(SEG_PRE[1]))
    red_worst = 0.0; red_n = 0
    for j in np.flatnonzero(m_pre & READY[ci])[:200]:
        if j == 0: continue
        i = ci[j]; pmv = mm[off[i]:off[i + 1]]
        qv = QV[i][pmv].astype(np.float64)
        sel_np = np.isfinite(qv) & (qv >= params["qv4h_min"])
        if sel_np.sum() < params["sel_min"]: continue
        wl = WLa[i].astype(np.float64)
        w3 = np.array([wl[0], 0.0, wl[2]]); w3 = w3 / w3.sum() if w3.sum() > 1e-12 else np.array([.5, 0., .5])
        fr = np.nan_to_num(ZFD[i][pmv].astype(np.float64))
        p = P10[i][pmv].astype(np.float64); okf = np.isfinite(p)
        zf = np.zeros(len(pmv))
        if okf.sum(): zf[okf] = rankdata(p[okf]) / max(int(okf.sum()) - 1, 1) - .5
        rn = RN8[i][pmv].astype(np.float64); bad = np.isfinite(rn) & (rn <= -.001)
        zpre = w3[0] * zf + w3[2] * fr
        zc = np.where((zpre < 0) & bad, 0.0, zpre)
        out = chain_torch(torch.from_numpy(zc), torch.from_numpy(sel_np),
                          torch.from_numpy(FC[j - 1].astype(np.float64)), torch.from_numpy(pmv), NW,
                          torch.from_numpy(book_legal[j]), params["cap_mult"], params["alpha"],
                          params["band"], 0.0, "clamp", _perturb=1.0 + 1e-9)
        if out is None: continue
        red_worst = max(red_worst, float(np.max(np.abs(out.numpy() - FC[j])))); red_n += 1
    green = max(results["s42"]["max_abs_dw_fc"], results["s42"]["max_abs_dw_kc"],
                results["s2027"]["max_abs_dw_fc"], results["s2027"]["max_abs_dw_kc"])
    rec["G3"] = {"results": results, "green_max_abs_dw": green, "tolerance": 1e-12,
                 "GREEN": bool(green <= 1e-12),
                 "red_control": {"perturb": "alpha *= 1+1e-9", "anchors": red_n,
                                 "max_abs_dw": red_worst, "RED": bool(red_worst > 1e-12)}}
    rec["utc_end"] = iso(time.time())
    op = os.path.join(outdir, "G3_CHAIN_PARITY.json")
    tmp = op + ".tmp"; open(tmp, "w").write(json.dumps(rec, indent=1, allow_nan=False)); os.replace(tmp, op)
    print(f"G3_CHAIN_PARITY green_max_abs_dw={green:.3e} GREEN={rec['G3']['GREEN']} "
          f"red_max_abs_dw={red_worst:.3e} RED={rec['G3']['red_control']['RED']} json={sha(op)[:16]}", flush=True)
    assert rec["G3"]["GREEN"], f"G3 parity FAILED: max|dw| = {green:.3e}"
    assert rec["G3"]["red_control"]["RED"], "G3 red control vacuous: perturbing alpha did not break parity"


if __name__ == "__main__":
    main()
