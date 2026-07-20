"""Before/after diagnostic for the xsec-universe fix (0C, 2026-07-20). Toggles ctx['__universe__'] to
compute OLD (all-finite=140) vs NEW (member&CL=109) for each batch_001 candidate, and reports the
scored inc-IC under each + per-anchor rank preservation. Proves 0C's expectations:
  (a) id101 (mul of two xsec_z) collapses under the fix;
  (b) single-xsec candidates rank-invariant (inc-IC identical, per-anchor Spearman 1.0);
  (c) leg-router candidates (gt of two xsec_z) shift (branch threshold now on the trading universe).
"""
import sys
import numpy as np

FAC = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory"
sys.path.insert(0, FAC)
import dsl
import pipeline as P
from pipeline import _xsec_ranks, _rowwise_rankcorr

CANDIDATES = [
    ("B06/id?", "neg(mul(xsec_z(lturnover_24h), xsec_z(max_ret_24h)))", "non-monotone: product of 2 xsec_z"),
    ("B20", "neg(xsec_z(ts_max(abs(ret_1h), 24)))", "single outer xsec_z (monotone)"),
    ("C10", "neg(xsec_z(power(ret_24h, 3)))", "single outer xsec_z (monotone)"),
    ("D01", "where(gt(xsec_z(rvol_24h), xsec_z(rvol_72h)), s2, king)", "leg router: gt of 2 xsec_z"),
    ("D11", "where(gt(xsec_z(mom_72h), xsec_z(mom_24h)), s2, king)", "leg router: gt of 2 xsec_z"),
    ("D16", "where(gt(xsec_z(dvol_24h), xsec_z(dvol_72h)), king, s2)", "leg router: gt of 2 xsec_z"),
    ("E12", "neg(xsec_z(ts_max(rvol_6h, 42)))", "single outer xsec_z (monotone)"),
]


def scored_inc_ic(factor, C, tr):
    ic = _rowwise_rankcorr(_xsec_ranks(factor, C), tr)
    return float(np.nanmean(ic)) if np.isfinite(ic).any() else np.nan


def per_anchor_rank_spearman(fac_old, fac_new, C):
    """mean over anchors of the within-anchor Spearman(fac_old, fac_new) over member&CL&both-finite."""
    ro = _xsec_ranks(fac_old, C); rn = _xsec_ranks(fac_new, C)
    sp = _rowwise_rankcorr(ro, rn)
    return float(np.nanmean(sp)) if np.isfinite(sp).any() else np.nan


def main():
    C = P.load_context(4, subsample=1)
    assert "__universe__" in C["ctx"], "pipeline not patched: __universe__ missing"
    ctx_new = C["ctx"]                                        # fixed (has __universe__)
    ctx_old = {k: v for k, v in C["ctx"].items() if k != "__universe__"}   # buggy (all-finite)
    tr = _xsec_ranks(C["target"], C)
    print(f"[diag] {len(C['rows'])} anchors | universe cells/anchor (member&CL) "
          f"median={int(np.median((C['member'] & C['CL'])[C['rows']].sum(1)))} vs all-finite=140", flush=True)
    print(f"{'id':10s} {'inc_ic_OLD':>11s} {'inc_ic_NEW':>11s} {'Δ':>9s} {'perAnchorSpear':>15s}  note", flush=True)
    rows = []
    for cid, f, note in CANDIDATES:
        root = dsl.parse(f)
        fo = dsl.evaluate(root, ctx_old)
        fn = dsl.evaluate(root, ctx_new)
        io = scored_inc_ic(fo, C, tr); inn = scored_inc_ic(fn, C, tr)
        sp = per_anchor_rank_spearman(fo, fn, C)
        rows.append((cid, io, inn, sp, note))
        print(f"{cid:10s} {io:>11.5f} {inn:>11.5f} {inn-io:>+9.5f} {sp:>15.5f}  {note}", flush=True)
    print("\n[diag] interpretation:")
    print("  single-xsec (B20/C10/E12): perAnchorSpear=1.0 & Δinc_ic≈0  -> rank-invariant (0C (b))")
    print("  id101 (B06): inc_ic collapses & perAnchorSpear<1            -> artifact removed (0C (a))")
    print("  routers (D01/D11/D16): perAnchorSpear<1 & inc_ic shifts     -> threshold on trading universe (0C (c))")


if __name__ == "__main__":
    main()
