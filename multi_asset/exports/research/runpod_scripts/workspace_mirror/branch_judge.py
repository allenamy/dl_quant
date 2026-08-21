import json, sys, glob
B = 0.0463
def ic(tag):
    f = glob.glob(f'/workspace/exports_train/wide_harness_{tag}.json') + glob.glob(f'/workspace/exports_train/train/wide_harness_{tag}.json') +         glob.glob('/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/exports/train/wide_harness_%s.json' % tag)
    if not f: return None
    return json.load(open(f[0])).get('mean_resid_rank_ic')
a, b = ic('ssl32_yr4_s42'), ic('ssl32_yr4_s2027')
if a is None or b is None:
    print('MISSING'); sys.exit(0)
da, db = a - B, b - B
print(f'IC s42={a:.4f} (D{da:+.4f}) s2027={b:.4f} (D{db:+.4f})')
if da >= 0.005 and db >= 0.005: print('BRANCH:PASS')
elif da > 0 and db > 0: print('BRANCH:MARGINAL')
else: print('BRANCH:FAIL')
