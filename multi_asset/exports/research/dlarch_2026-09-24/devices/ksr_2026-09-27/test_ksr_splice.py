"""selftest for dlarch_ksr_splice.py on synthetic arrays (known answers; red cases must fail)."""
import numpy as np, subprocess, sys, os, tempfile, json
D = os.path.dirname(os.path.abspath(__file__)); S = os.path.join(D, 'dlarch_ksr_splice.py'); PY = sys.executable
t = tempfile.mkdtemp(); NA, NW = 40, 5; E = (np.arange(NA) * 14400 + 1_700_000_000 // 14400 * 14400).astype(np.int64)
rng = np.random.default_rng(1); sym = np.array([f'S{i}' for i in range(NW)])
def oof(p, P, ms): np.savez(p, P=P.astype(np.float32), E_ts=E, symbols=sym, model_sha256=ms)
P0 = rng.standard_normal((NA, NW)); ms0 = np.array(['a' * 64] * NA, dtype='U64'); oof(f'{t}/s0.npz', P0, ms0)
PA = np.full((NA, NW), np.nan); PA[10:15] = rng.standard_normal((5, NW)); msA = np.array([''] * NA, dtype='U64'); msA[10:15] = 'b' * 64; oof(f'{t}/w1.npz', PA, msA)
PB = np.full((NA, NW), np.nan); PB[25:30] = rng.standard_normal((5, NW)); msB = np.array([''] * NA, dtype='U64'); msB[25:30] = 'c' * 64; oof(f'{t}/w2.npz', PB, msB)
run = lambda *a: subprocess.run([PY, S, *a], capture_output=True, text=True)
res = {}
r = run('build', f'{t}/s0.npz', f'{t}/out', f'{t}/w1.npz', f'{t}/w2.npz'); res['build_green'] = r.returncode == 0 and 'PASS=True' in r.stdout
z = np.load(f'{t}/out/KING_OOF.npz'); exp = P0.astype(np.float32).copy(); exp[10:15] = PA[10:15]; exp[25:30] = PB[25:30]
res['build_known_answer'] = z['P'].tobytes() == exp.astype(np.float32).tobytes() and (z['model_sha256'][10:15] == 'b' * 64).all() and (z['model_sha256'][:10] == 'a' * 64).all()
PC = np.full((NA, NW), np.nan); PC[12:18] = 1.0; oof(f'{t}/w3.npz', PC, msA)
r = run('build', f'{t}/s0.npz', f'{t}/out_red', f'{t}/w1.npz', f'{t}/w3.npz'); res['red_overlap_refused'] = r.returncode != 0
# legs: arrays per anchor; spliced differs from row 10 on (green), from row 9 (red: pre-window change), and not at all (red: not reached)
L0 = {'E_ts': E, 'LR': rng.standard_normal((NA, 3)), 'WL': rng.standard_normal((NA, 3)), 'syms': sym}
np.savez(f'{t}/l0.npz', **L0)
L1 = {k: v.copy() for k, v in L0.items()}; L1['LR'][10:] += 1; L1['WL'][11:] += 1; np.savez(f'{t}/l1.npz', **L1)
L2 = {k: v.copy() for k, v in L0.items()}; L2['WL'][9:] += 1; np.savez(f'{t}/l2.npz', **L2)
np.savez(f'{t}/l3.npz', **L0)
rp = f'{t}/out/SPLICE_RECEIPT.json'
r = run('legs', f'{t}/l0.npz', f'{t}/l1.npz', rp, f'{t}/g.json'); g = json.load(open(f'{t}/g.json'))
res['legs_green'] = r.returncode == 0 and g['PASS'] and g['arrays']['LR']['first_differing_anchor'] == int(E[10]) and g['arrays']['WL']['first_differing_anchor'] == int(E[11])
r = run('legs', f'{t}/l0.npz', f'{t}/l2.npz', rp, f'{t}/r1.json'); res['legs_red_prewindow'] = r.returncode == 2 and not json.load(open(f'{t}/r1.json'))['PASS']
r = run('legs', f'{t}/l0.npz', f'{t}/l3.npz', rp, f'{t}/r2.json'); res['legs_red_not_reached'] = r.returncode == 2 and not json.load(open(f'{t}/r2.json'))['splice_reached_the_legs']
import time as _t
st = _t.strftime('%Y-%m-%d', _t.gmtime(int(E[0]) + 86400)); en = _t.strftime('%Y-%m-%d', _t.gmtime(int(E[0]) + 3 * 86400))
r = run('red', f'{t}/s0.npz', f'{t}/red', st, en, '7'); zr = np.load(f'{t}/red/KING_OOF.npz')
import calendar as _c
lo, hi = _c.timegm(_t.strptime(st, '%Y-%m-%d')), _c.timegm(_t.strptime(en, '%Y-%m-%d')); inw = (E >= lo) & (E < hi)
res['red_known_answer'] = r.returncode == 0 and np.isnan(zr['P'][~inw]).all() and all(np.array_equal(np.sort(zr['P'][i]), np.sort(P0.astype(np.float32)[i])) for i in np.flatnonzero(inw)) and not np.array_equal(zr['P'][inw], P0.astype(np.float32)[inw])
res = {k: bool(v) for k, v in res.items()}; print(json.dumps(res)); print('KSR_SPLICE_SELFTEST', 'PASS' if all(res.values()) else 'FAIL', '%d/%d' % (sum(res.values()), len(res)))
