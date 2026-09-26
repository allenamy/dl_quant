#!/usr/bin/env python3
"""Patch the F10_FULL copy of dlarch_train_f10.py. Six named changes, each asserted unique.

Base = the T3 copy (cf66cecb1bfd4d0a): it carries the vendored CODE path, so this arm does not
depend on news2's volatile /dev/shm for anything but bulk DATA, which is sha-pinned per fold.

Changes 1-3 are the F10_FULL arm (prereg section 1). Changes 4-6 are the R25-08 class fix: the
resume identity pinned inputs/sources/seed/arm and NOT ONE training parameter.
"""
import pathlib
import sys

P = pathlib.Path('/workspace/dlarch_2026-09-24/f10full_2026-09-26/dlarch_train_f10.py')
s = P.read_text()
orig = s


def sub(old, new, what):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit('ABORT: %s appears %d times, expected exactly 1' % (what, n))
    s = s.replace(old, new, 1)


# ---------------------------------------------------------------- 1. the new flag
A = "    ap.add_argument('--band-temp-div', type=float, default=10.0)"
sub(A,
    "    ap.add_argument('--train-frac', type=float, default=0.85,\n"
    "                    help='Fraction of the admissible training anchors to use, earliest-first. '\n"
    "                         'Default 0.85 reproduces the as-delivered recipe BYTE-FOR-BYTE; the '\n"
    "                         'F10_FULL arm passes 1.0. The discarded tail had no consumer (grep '\n"
    "                         'tr[cut:] == 0 hits) and the epoch is fixed, so it was neither trained '\n"
    "                         'on nor validated on.')\n" + A,
    'anchor for the new flag')

# ------------------------------------------------- 2. the ONE substantive line (prereg section 1)
sub("        cut = int(len(tr) * .85); tr1 = tr[:cut]; assert a[tr1[-1]] + 14400 <= cutoff",
    "        cut = int(len(tr) * args.train_frac); tr1 = tr[:cut]; "
    "assert a[tr1[-1]] + 14400 <= cutoff",
    'the .85 truncation line')

# ---------------------- 3. arm name must differ off-default, and the params hash is defined here
C = "        arm = 'G1_T0_nomask'"
sub(C, C + "\n"
    "    if args.train_frac != 0.85:\n"
    "        # WHY: at the DEFAULT the arm string must stay UNCHANGED, so H-FULL-1 can compare this copy\n"
    "        # bitwise against the delivered cells. OFF-default it must DIFFER, because the resume branch\n"
    "        # below reuses any FOLD_RECEIPT.json found at the same path -- an identical arm name would\n"
    "        # silently republish the 0.85 folds as 1.0 results. Naming carries the separation; no\n"
    "        # delivered file is deleted, overwritten or read as if it were this arm's.\n"
    "        arm = f'{arm}_frac{args.train_frac:g}'\n"
    "    # R25-08: every training parameter that can change a number, in ONE canonical form, hashed once\n"
    "    # and then asserted by the resume branch and written into both receipts. Adding a parameter to\n"
    "    # the parser and forgetting it here is the same defect again, so the tuple is built from the\n"
    "    # parser's own namespace minus the keys that are provenance rather than recipe.\n"
    "    _NOT_RECIPE = {'env_whitelist', 'out_root', 'folds'}   # folds selects WHICH folds, not HOW\n"
    "    train_params = {k: v for k, v in sorted(vars(args).items()) if k not in _NOT_RECIPE}\n"
    "    train_params_sha = hashlib.sha256(\n"
    "        json.dumps(train_params, sort_keys=True, separators=(',', ':')).encode()).hexdigest()\n"
    "    log('train params', train_params_sha[:16], json.dumps(train_params, sort_keys=True))",
    'the nomask arm assignment')

# ------------------- 4. the resume identity ignored every training parameter
sub("            old = json.load(open(result)); assert old['inputs'] == inputs and old['sources'] "
    "== sources and old['seed'] == args.seed and old['arm'] == arm, 'resume identity changed'",
    "            old = json.load(open(result))\n"
    "            assert old['inputs'] == inputs and old['sources'] == sources and old['seed'] == args.seed \\\n"
    "                and old['arm'] == arm, 'resume identity changed'\n"
    "            # R25-08, same class as --band-temp-div: the identity above pins inputs/sources/seed/arm\n"
    "            # and NOT ONE training parameter, so two runs differing only in a hyper-parameter resume\n"
    "            # each other's folds. A receipt predating this check has no key -> REFUSE, never assume a\n"
    "            # match (absence of the field is not evidence that the parameters agreed).\n"
    "            assert old.get('train_params_sha256') == train_params_sha, (\n"
    "                'resume identity: training parameters differ or were never recorded: '\n"
    "                + str(old.get('train_params_sha256')) + ' != ' + train_params_sha)",
    'the resume identity assert')

# ------------------- 5. record it in the FOLD receipt
sub("        rr = {'status': 'F10_OOF_SCORES_NOT_COMBO_PNL', 'arm': arm, "
    "'clamp_mode': args.clamp_mode if args.arm == 'T3' else None,",
    "        rr = {'status': 'F10_OOF_SCORES_NOT_COMBO_PNL', 'arm': arm, "
    "'clamp_mode': args.clamp_mode if args.arm == 'T3' else None,\n"
    "              'train_params': train_params, 'train_params_sha256': train_params_sha,",
    'the fold receipt head')

# ------------------- 6. record it in the MERGED receipt (signature + both callsites)
sub("def merge_folds(out, a, symbols, inputs, sources, seed, arm):",
    "def merge_folds(out, a, symbols, inputs, sources, seed, arm, *, train_params_sha):",
    'the merge_folds signature')
sub("          'expected_folds': [s[0] for s in fold_specs(a)], 'inputs': inputs, 'sources': sources,",
    "          'expected_folds': [s[0] for s in fold_specs(a)], 'inputs': inputs, 'sources': sources,\n"
    "          'train_params_sha256': train_params_sha,",
    'the merged receipt body')
n = s.count("merge_folds(out, a, t['symbols'], inputs, sources, args.seed, arm)")
if n != 2:
    sys.exit('ABORT: expected 2 merge_folds callsites, found %d' % n)
s = s.replace("merge_folds(out, a, t['symbols'], inputs, sources, args.seed, arm)",
              "merge_folds(out, a, t['symbols'], inputs, sources, args.seed, arm, "
              "train_params_sha=train_params_sha)")

if s == orig:
    sys.exit('ABORT: nothing changed')
P.write_text(s)
print('PATCHED_OK 6 changes')
