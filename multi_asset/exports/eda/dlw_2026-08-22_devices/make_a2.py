# -*- coding: utf-8 -*-
"""Runs ON jpline in dlw_2026-08-22: writes dlw_train_a2.py (F-8 89-col aux-conditioning arm)
and dlw_train_f26.py (ARM-overridable copy for 2026-fold reruns). Originals untouched."""
import io, re
s = io.open('dlw_train.py', encoding='utf-8').read()
arm_m = re.search(r'(?m)^ARM\s*=\s*.*$', s)
assert arm_m, 'no ARM line'
print('ARM line was:', arm_m.group(0))
# ---------- f26 copy: ARM env-first + nothing else ----------
f26 = s.replace(arm_m.group(0), 'ARM = os.environ.get("ARM") or (%s)' % arm_m.group(0).split('=',1)[1].strip(), 1)
io.open('dlw_train_f26.py','w',encoding='utf-8').write(f26)
# ---------- a2 copy ----------
a2 = s.replace(arm_m.group(0), 'ARM = os.environ.get("ARM", "A2f89")', 1)
a = 'FOLD_MIN = int(os.environ.get("FOLD_MIN", "0"))'
if a not in a2:  # dlw_train may not have FOLD_MIN yet in this copy path
    raise SystemExit('FOLD_MIN missing')
a2 = a2.replace(a, a + '\nFOLD_MAX = int(os.environ.get("FOLD_MAX", "9999"))', 1)
b = '    if YV < FOLD_MIN:\n        continue'
assert b in a2
a2 = a2.replace(b, b + '\n    if YV > FOLD_MAX:\n        continue', 1)
i = a2.find('log(f"anchors {nA} '); assert i >= 0
j = a2.find('\n', i); assert j > 0
aux_block = '''

# A2: F-8 89-col engineered ammo -> per-name conditioning (rank in-anchor over members + presence)
_F8 = np.load(f"{ROOT}/f8_2026-08-22/data/f8_fea89.npz", allow_pickle=True)
assert int(_F8["pair_a"].max()) < nA and int(_F8["pair_s"].max()) < NW
_AUXR = np.full((nA, NW, 89), np.nan, np.float32)
_AUXR[_F8["pair_a"].astype(np.int64), _F8["pair_s"].astype(np.int64)] = _F8["X"]
del _F8
AUXD = np.zeros((nA, NW, 90), np.float16)
for _i in range(nA):
    _m = np.asarray(MS[_i], dtype=np.int64)
    if _m.size == 0:
        continue
    _v = _AUXR[_i, _m]
    _ok = np.isfinite(_v)
    _rk = np.argsort(np.argsort(np.where(_ok, _v, np.inf), axis=0), axis=0).astype(np.float32)
    _n = np.maximum(_ok.sum(0, keepdims=True).astype(np.float32) - 1.0, 1.0)
    _rk = np.where(_ok, _rk / _n - 0.5, 0.0)
    AUXD[_i, _m, :89] = _rk.astype(np.float16)
    AUXD[_i, _m, 89] = _ok.mean(1).astype(np.float16)
del _AUXR
AUXT = torch.from_numpy(AUXD).to(DEV)
del AUXD
log(f"A2 aux 90d on GPU {tuple(AUXT.shape)} (f8_fea89 in-anchor member rank + presence)")


def gather_aux(i, cols_t):
    return AUXT[i].index_select(0, cols_t).float()
'''
a2 = a2[:j+1] + aux_block + a2[j+1:]
a = '        zd = ch * 2\n'; assert a in a2
a2 = a2.replace(a, '        zd = ch * 2 + 32\n        s.auxp = nn.Sequential(nn.Linear(90, 64), nn.GELU(), nn.Linear(64, 32))\n', 1)
a = '    def forward(s, x, sizes, ctx=None):'; assert a in a2
a2 = a2.replace(a, '    def forward(s, x, sizes, ctx=None, aux=None):', 1)
a = '        z = torch.cat([(hs * w_.unsqueeze(1)).sum(-1), h[:, :, -1]], -1)\n'; assert a in a2
a2 = a2.replace(a, a + '        z = torch.cat([z, s.auxp(aux)], -1)\n', 1)
a = 'xs, ys, sz, cxs = [], [], [], []'; assert a in a2
a2 = a2.replace(a, 'xs, ys, sz, cxs, axs = [], [], [], [], []', 1)
a = '                cxs.append(regime_ctx(i, MS_T[i])[okt])\n'; assert a in a2
a2 = a2.replace(a, a + '                axs.append(gather_aux(i, MS_T[i])[okt])\n', 1)
a = 'cb = torch.cat(cxs)'; assert a in a2
a2 = a2.replace(a, 'cb = torch.cat(cxs); ab = torch.cat(axs)', 1)
a = 'o = mdl(xb, sz, ctx=cb)'; assert a in a2
a2 = a2.replace(a, 'o = mdl(xb, sz, ctx=cb, aux=ab)', 1)
a = 'p = mdl(x, [x.shape[0]], ctx=regime_ctx(i, MS_T[i])).mean(-1)'; assert a in a2
a2 = a2.replace(a, 'p = mdl(x, [x.shape[0]], ctx=regime_ctx(i, MS_T[i]), aux=gather_aux(i, MS_T[i])).mean(-1)', 1)
a = 'p = mdl(x, [x.shape[0]], ctx=regime_ctx(i, MS_T[i])).cpu().numpy().mean(-1)'; assert a in a2
a2 = a2.replace(a, 'p = mdl(x, [x.shape[0]], ctx=regime_ctx(i, MS_T[i]), aux=gather_aux(i, MS_T[i])).cpu().numpy().mean(-1)', 1)
io.open('dlw_train_a2.py','w',encoding='utf-8').write(a2)
import ast
ast.parse(a2); ast.parse(f26)
print('written dlw_train_a2.py + dlw_train_f26.py; a2 diff lines:', sum(1 for x, y in zip(s.splitlines(), a2.splitlines()) if x != y))
