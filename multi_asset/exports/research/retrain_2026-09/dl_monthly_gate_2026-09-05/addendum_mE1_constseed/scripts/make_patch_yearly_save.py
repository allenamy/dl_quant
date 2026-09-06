"""make_patch_yearly_save.py — diagnostic-only patch of the VERBATIM yearly trainer (sha 93cc2cdf…): after best-epoch reload, save the fold model state dict and
its raw scores for EVERY anchor >= first_te (cross-year agreement, addendum §11 diagnostic). No RNG is consumed (eval, no_grad), the test pass is untouched,
so preds must stay bitwise equal to the 09-01 gate run (asserted afterwards by identity). Needs {OUT}/models and {OUT}/preds_fold. usage: <verbatim> <out>"""
import sys, hashlib
src, dst = sys.argv[1], sys.argv[2]; S = open(src, encoding="utf-8").read()
assert hashlib.sha256(S.encode("utf-8")).hexdigest() == "93cc2cdf925a1dada9190a5d86664d28c811d9ba0ecf3eaf377d54fc554f2598"
old = "    mdl.load_state_dict(best_state); mdl.eval()\n"; assert S.count(old) == 1
new = old + ('    torch.save(best_state, f"{OUT}/models/f10_{ARM}_s{SEED}_{YV}.pt")   # yearly_save (diagnostic): fold model state dict\n'
             '    with torch.no_grad():   # yearly_save (diagnostic): raw scores for EVERY anchor >= first_te; eval/no_grad, no RNG, CTXA==0 asserted\n'
             '        assert CTXA == 0 and REC == 0 and PLEON == 0\n'
             '        _PA = np.full((nA - first_te, NW), np.nan, np.float32)\n'
             '        for _i in range(first_te, nA):\n'
             '            _a0, _b0 = int(ST[_i]), int(ST[_i + 1])\n'
             '            if _b0 - _a0 < 50:\n'
             '                continue\n'
             '            _x = torch.clamp((XT[_a0:_b0] - mu) / sd, -5, 5)\n'
             '            _PA[_i - first_te, PST[_a0:_b0].cpu().numpy()] = mdl.f(torch.nan_to_num(_x)).squeeze(-1).cpu().numpy()\n'
             '        np.savez_compressed(f"{OUT}/preds_fold/f10_{ARM}_s{SEED}_{YV}.npz", first_te=first_te, P=_PA)\n')
S = S.replace(old, new); open(dst, "w", encoding="utf-8").write(S); print("wrote", dst, hashlib.sha256(S.encode("utf-8")).hexdigest())
