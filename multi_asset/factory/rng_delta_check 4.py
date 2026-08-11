"""Validation (d) (factory_rng_signoff.md Q3): the shift from the OLD serial-shared-rng bootstrap to
the NEW per-formula (ast_md5-keyed) bootstrap must move CI/z only at bootstrap Monte-Carlo-noise level
(~1% at nboot=3000), and RANDOMLY (mean signed delta ~0), never systematically. A systematic bias would
be a red flag. Full-window (subsample=1) so z magnitudes match the real regime (batch_001 z ~10-17)."""
import sys
import numpy as np

FAC = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/factory"
sys.path.insert(0, FAC)
import dsl
import pipeline as P
from pipeline import _xsec_ranks, _rowwise_rankcorr, stats, RNG_BASE_SEED, BOOT
from run_campaign import parse_batch

BATCH = FAC + "/proposals/batch_001.txt"


def main():
    C = P.load_context(4, 1)
    tr = _xsec_ranks(C["target"], C)
    day_w = C["day"][C["rows"]]; year_w = C["year"][C["rows"]]
    formulas = [f for _, _, f in parse_batch(BATCH)]
    # precompute each formula's ic series (deterministic, rng-free)
    per = []
    for f in formulas:
        try:
            root = dsl.parse(f); fac = dsl.evaluate(root, C["ctx"])
            ic = _rowwise_rankcorr(_xsec_ranks(fac, C), tr); ok = np.isfinite(ic)
            if ok.sum() >= 5:
                per.append((f, root.value["md5"], ic[ok], day_w[ok], year_w[ok]))
        except Exception:
            pass
    print(f"[d] nboot={BOOT} | {len(per)} scored formulas | comparing shared-sequential vs per-formula rng", flush=True)

    shared_rng = np.random.default_rng(0)                  # OLD behaviour: one rng threaded across formulas
    rows = []
    for (f, md5, ics, days, yrs) in per:
        z_sh = stats(ics, days, yrs, shared_rng)["z"]
        z_pf = stats(ics, days, yrs, np.random.default_rng([RNG_BASE_SEED, int(md5, 16)]))["z"]
        if z_sh and z_pf and np.isfinite(z_sh) and np.isfinite(z_pf):
            rows.append((z_sh, z_pf))
    zsh = np.array([r[0] for r in rows]); zpf = np.array([r[1] for r in rows])
    d = zpf - zsh
    rel = np.abs(d) / np.abs(zsh)
    # expected bootstrap MC noise on z at this nboot (rough): z * (SE-of-SE) ~ z / sqrt(2*nboot)
    mc_pct = 1.0 / np.sqrt(2 * BOOT) * 100
    print(f"[d] n={len(rows)} | signed delta mean={d.mean():+.4f} std={d.std():.4f} "
          f"(mean≈0 => unbiased)", flush=True)
    print(f"[d] |delta|/|z|: median={np.median(rel)*100:.2f}%  p90={np.percentile(rel,90)*100:.2f}%  "
          f"max={rel.max()*100:.2f}%  | expected MC ~{mc_pct:.2f}%", flush=True)
    print(f"[d] z range shared=[{zsh.min():.1f},{zsh.max():.1f}] | any verdict-flip near z*=4.42? "
          f"{'YES(!)' if ((np.sign(zsh-4.42) != np.sign(zpf-4.42)).any()) else 'no'}", flush=True)


if __name__ == "__main__":
    main()
