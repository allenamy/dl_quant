#!/usr/bin/env python3
"""Add --shuffle-labels to the SHUFFLE-ARM copy of the trainer (control 1 of prereg section 4).

Placed in its own directory: the running f10full_2026-09-26/ trainer is pinned by
dlarch_f10full_launch.py, and changing its bytes would make seed 7's launch gate go red.

WHERE. Between the label matrix build (L208) and the point where YVALID/YT are derived from it (L215).
That ordering is what keeps the population fixed: YVALID is the FINITENESS pattern, and a permutation
inside the finite cells leaves it bit-identical.

WHAT IS PERMUTED. Within each anchor, only the cells that are BOTH a member of that anchor's book AND
finite. Not the whole row: a row also holds finite labels for non-member symbols, and permuting across
those would import non-member returns into the member population -- moving the population, which is
exactly what a null randomisation must not do (lead's ruling, null_randomisation_must_not_move_the_
population). Permuting inside members keeps each anchor's member-set marginal EXACTLY as it was.

PROOF, not assertion: the patch adds three checks that run in the shuffled run itself --
  * the finiteness pattern of y is bit-identical before and after;
  * each anchor's sorted member label vector is bit-identical before and after (a permutation cannot
    change the multiset);
  * the count of permuted cells and anchors is recorded in the receipt.
"""
import pathlib
import sys

P = pathlib.Path('/workspace/dlarch_2026-09-24/f10full_shuffle_2026-09-26/dlarch_train_f10.py')
s = P.read_text()


def sub(old, new, what):
    global s
    if s.count(old) != 1:
        sys.exit('ABORT: %s appears %d times, expected 1' % (what, s.count(old)))
    s = s.replace(old, new, 1)


# 1. the flag
sub("    ap.add_argument('--train-frac', type=float, default=0.85,",
    "    ap.add_argument('--shuffle-labels', action='store_true',\n"
    "                    help='CONTROL 1 (shuffle-future) ONLY. Permute the training labels along the '\n"
    "                         'name axis INSIDE each anchor, across the cells that are both a book '\n"
    "                         'member and finite. The finiteness pattern and every anchor\\'s member-set '\n"
    "                         'label multiset are unchanged, so the population does not move; only the '\n"
    "                         'pairing between name and return is destroyed. Never use for a real arm.')\n"
    "    ap.add_argument('--train-frac', type=float, default=0.85,",
    'the train-frac flag anchor')

# 2. the permutation itself, after `members` exists and before YVALID/YT are derived
OLD = ("    dev = 'cuda'; XT = torch.from_numpy(x).to(dev); del x\n"
       "    YVALID = torch.from_numpy(np.isfinite(y)).to(dev); "
       "YT = torch.from_numpy(np.where(np.isfinite(y), y, 0.)).to(dev)")
NEW = ("    dev = 'cuda'; XT = torch.from_numpy(x).to(dev); del x\n"
       "    shuffle_census = None\n"
       "    if args.shuffle_labels:\n"
       "        # CONTROL 1. Permute inside each anchor's (member AND finite) cells. Everything that\n"
       "        # defines the POPULATION -- which cells are finite, and each anchor's member-set label\n"
       "        # multiset -- is preserved and PROVEN so below, because a null that moves the population\n"
       "        # biases the comparison instead of nulling it.\n"
       "        _rng = np.random.default_rng(20260926 + args.seed)\n"
       "        _fin_before = np.isfinite(y).copy()\n"
       "        _sorted_before = [np.sort(y[i, members[i]][np.isfinite(y[i, members[i]])])\n"
       "                          for i in range(len(a))]\n"
       "        _cells = _anch = 0\n"
       "        for i in range(len(a)):\n"
       "            mi = members[i]\n"
       "            if mi.size == 0:\n"
       "                continue\n"
       "            idx = mi[np.isfinite(y[i, mi])]\n"
       "            if idx.size < 2:\n"
       "                continue\n"
       "            y[i, idx] = y[i, _rng.permutation(idx)]\n"
       "            _cells += int(idx.size); _anch += 1\n"
       "        assert np.array_equal(np.isfinite(y), _fin_before), \\\n"
       "            'shuffle changed the finiteness pattern: the population moved'\n"
       "        for i in range(len(a)):\n"
       "            _now = np.sort(y[i, members[i]][np.isfinite(y[i, members[i]])])\n"
       "            assert np.array_equal(_now, _sorted_before[i]), \\\n"
       "                f'shuffle changed anchor {i} label multiset: the population moved'\n"
       "        shuffle_census = {'rng': f'default_rng(20260926 + {args.seed})',\n"
       "                          'anchors_permuted': _anch, 'cells_permuted': _cells,\n"
       "                          'finiteness_pattern_identical': True,\n"
       "                          'per_anchor_member_multiset_identical': True,\n"
       "                          'scope': 'member AND finite cells, within each anchor'}\n"
       "        log('shuffle-labels census', json.dumps(shuffle_census))\n"
       "    YVALID = torch.from_numpy(np.isfinite(y)).to(dev); "
       "YT = torch.from_numpy(np.where(np.isfinite(y), y, 0.)).to(dev)")
sub(OLD, NEW, 'the YVALID derivation')

# 3. the arm name must differ, or a shuffled run could be mistaken for a real one
sub("    if args.train_frac != 0.85:",
    "    if args.shuffle_labels:\n"
    "        # A shuffled run must never share a path or a name with a real arm.\n"
    "        arm = f'{arm}_SHUFFLED'\n"
    "    if args.train_frac != 0.85:",
    'the arm-suffix block')

# 4. the census goes into the fold receipt
sub("              'train_params': train_params, 'train_params_sha256': train_params_sha,",
    "              'train_params': train_params, 'train_params_sha256': train_params_sha,\n"
    "              'shuffle_labels': bool(args.shuffle_labels), 'shuffle_census': shuffle_census,",
    'the fold receipt train_params line')

P.write_text(s)
print('PATCHED_OK 4 changes')
