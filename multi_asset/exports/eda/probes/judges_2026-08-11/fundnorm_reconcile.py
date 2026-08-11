"""0C — numerical reconciliation of the two independent normalised-funding rebuilds.

0B: fundnorm_control.py::build(normalise=True)   -- rate*(8/iv) per settlement row, then EMA
0C: funding_dim_fix.py -> funding_ema_normfix.npz -- same transform, same span rule, same ffill

Both are per-settlement pre-EMA (confirmed by reading 0B's source), so they SHOULD agree to fp noise.
Known implementation differences to quantify:
  - 0B fills a non-finite/non-positive interval_h with 8.0; 0C drops those settlement rows
  - 0B's shipped reference is wide_panel_full.npz::FUND_EMA; 0C's is wide_dl_full.npz::CH[...,funding_ema]
If the two panels agree, either can be used downstream and no re-run is needed.

Writes exports/eda/fundnorm_reconcile.json.
"""
import sys, json
import numpy as np

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
EDA = MA + "/exports/eda/"
sys.path.insert(0, MA); sys.path.insert(0, EDA)
from engine.panel_source import PanelSource
import fundnorm_control as B          # 0B's module

src = PanelSource()
FN_0B = B.build(src.ts, src.symbols, True)
Z = np.load(EDA + "funding_ema_normfix.npz", allow_pickle=True)
FN_0C = Z["FN"].astype(np.float64)
assert [str(s) for s in Z["symbols"]] == src.symbols

both = np.isfinite(FN_0B) & np.isfinite(FN_0C)
only0B = np.isfinite(FN_0B) & ~np.isfinite(FN_0C)
only0C = ~np.isfinite(FN_0B) & np.isfinite(FN_0C)
d = np.abs(FN_0B[both] - FN_0C[both])
corr = float(np.corrcoef(FN_0B[both], FN_0C[both])[0, 1])
scale = float(np.abs(FN_0C[both]).mean())
print(f"[reconcile] n_both={both.sum():,}  corr={corr:.12f}", flush=True)
print(f"            mean|diff|={d.mean():.3e}  max|diff|={d.max():.3e}  "
      f"mean|value|={scale:.3e}  rel={d.mean()/scale:.3e}", flush=True)
print(f"            coverage-only-0B={only0B.sum():,}  only-0C={only0C.sum():,}", flush=True)

# where do they differ at all, and is it confined to the migrating coins?
ctl = json.load(open(EDA + "funding_dim_fix_control.json"))
mig = {c["sym"] for c in ctl["per_coin"] if c.get("ok") and c.get("migrated")}
per_sym = []
for j, s in enumerate(src.symbols):
    m = both[:, j]
    if m.sum() == 0:
        continue
    dd = np.abs(FN_0B[m, j] - FN_0C[m, j])
    if dd.max() > 1e-12:
        per_sym.append({"sym": s, "max_abs_diff": float(dd.max()), "migrated": s in mig})
per_sym.sort(key=lambda x: -x["max_abs_diff"])
print(f"            symbols with any diff >1e-12: {len(per_sym)} "
      f"(of which migrated: {sum(1 for x in per_sym if x['migrated'])})", flush=True)
for x in per_sym[:5]:
    print(f"              {x['sym']:14s} max|diff|={x['max_abs_diff']:.3e} migrated={x['migrated']}", flush=True)

verdict = ("IDENTICAL (fp noise) -- either panel may be used downstream, no re-run needed"
           if d.mean() < 1e-9 and corr > 0.999999999 and only0B.sum() + only0C.sum() < 1000
           else "DIFFERENT -- reconcile before using downstream")
print(f"\n  VERDICT: {verdict}", flush=True)

json.dump(dict(title="0B vs 0C normalised-funding panel reconciliation", created="2026-07-25",
               auditor="0C", n_both=int(both.sum()), pearson=corr,
               mean_abs_diff=float(d.mean()), max_abs_diff=float(d.max()),
               mean_abs_value=scale, relative_mean_diff=float(d.mean() / scale),
               coverage_only_0B=int(only0B.sum()), coverage_only_0C=int(only0C.sum()),
               n_symbols_with_any_diff=len(per_sym), symbols_with_diff=per_sym[:20],
               known_impl_differences=["0B fills non-finite/non-positive interval_h with 8.0; 0C drops those rows",
                                       "0B shipped ref = wide_panel_full::FUND_EMA; 0C = wide_dl_full::CH[funding_ema]"],
               both_apply_normalisation="per settlement row, BEFORE the EMA (confirmed by reading both sources)",
               verdict=verdict),
          open(EDA + "fundnorm_reconcile.json", "w"), indent=1, default=str)
print("SAVED exports/eda/fundnorm_reconcile.json", flush=True)
