import sys, json, pathlib, csv, io, zipfile, numpy as np
sys.path.insert(0, '/workspace/codex_research/QNT-2026-0907/uplift_20260922/devices')
from corrected_inputs import official_intervals, bind_intervals
fund = {k: v for k, v in np.load('/workspace/baseline_tables_2026-09-19/funding/ledger_spliced_p2_to_20260901T0200_streamD_after.npz').items()}
latest = {k: v for k, v in np.load('/workspace/axis_0919/funding/funding_ledger.npz').items()}
symbols = fund['symbols']
root = pathlib.Path('/workspace/fx_prod_p9/zips_2026-08'); archive = []
for j, s in enumerate(symbols):
    p = root / (str(s) + '-fundingRate-2026-08.zip')
    if not p.exists(): continue
    with zipfile.ZipFile(p) as zz:
        for row in csv.DictReader(io.StringIO(zz.read(zz.namelist()[0]).decode())):
            archive.append((j, int(row['calc_time']) // 1000, float(row['last_funding_rate']), float(row['funding_interval_hours'])))
ar = np.asarray(archive); official = dict(sym=ar[:, 0].astype(int), ts=ar[:, 1].astype(np.int64), rate=ar[:, 2], iv=ar[:, 3])
iv_full, audit = official_intervals(fund, latest, official)
# without the official archive: trusted latest only (same function body minus the official steps)
source = latest['iv_src']; trusted = np.isin(source, [0, 1, 2])
rev = {k: latest[k][trusted] for k in ['sym', 'ts', 'rate', 'iv']}
iv_gap, n, d = bind_intervals(fund, rev)
fa, fg = np.isfinite(iv_full), np.isfinite(iv_gap)
ft = fund['ft']; aug = (ft >= 1785542400) & (ft < 1788220800)
out = {"events": int(len(ft)), "src_counts": {int(k): int(v) for k, v in zip(*np.unique(source, return_counts=True))},
       "known_with_official": int(fa.sum()), "known_gap_only": int(fg.sum()),
       "filled_by_official(NaN->value)": int((fa & ~fg).sum()), "value_changed": int((fa & fg & (iv_full != iv_gap)).sum()),
       "removed(value->NaN)": int((~fa & fg).sum()), "changed_events_in_2026_08": int((aug & ((fa != fg) | (fa & fg & (iv_full != iv_gap)))).sum()),
       "changed_outside_2026_08": int((~aug & ((fa != fg) | (fa & fg & (iv_full != iv_gap)))).sum()),
       "unknown_after_gap_only": int((~fg).sum()), "audit": {k: (v if not isinstance(v, list) else len(v)) for k, v in audit.items()}}
print(json.dumps(out))
# gap rule on the full ledger (production formula) vs the final research intervals
off = fund['off']; gap = np.full(len(ft), np.nan)
for j in range(len(off) - 1):
    b, e = off[j], off[j + 1]
    if e - b < 2: continue
    d = np.diff(ft[b:e]) / 3600.0
    gap[b + 1:e] = [min([1.0, 2.0, 4.0, 6.0, 8.0], key=lambda a_: abs(a_ - (x if 0 < x <= 24 else 8.0))) for x in d]
fr = np.isfinite(iv_full); fgp = np.isfinite(gap)
res = {"research_final_known": int(fr.sum()), "gap_rule_known": int(fgp.sum()),
       "both_known_disagree": int((fr & fgp & (iv_full != gap)).sum()),
       "both_known_disagree_2026_08": int((aug & fr & fgp & (iv_full != gap)).sum()),
       "research_known_gap_unknown(first events)": int((fr & ~fgp).sum()), "research_unknown_gap_known": int((~fr & fgp).sum())}
import collections, time as _t
m = collections.Counter(_t.strftime('%Y-%m', _t.gmtime(int(t))) for t in ft[fr & fgp & (iv_full != gap)])
res["disagree_by_month"] = sorted(m.items())
print(json.dumps(res))
