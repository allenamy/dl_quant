"""fa_combo.py — fresh_combo.py with the deleted feature panel replaced, for PREREG 427d76f34 phase 2
(AMENDMENT 2 953df1489 + correction dfdcf9ba8). Parameterised over which arm supplies legs and which supplies F10.

WHAT IS CHANGED vs fresh_combo.py, and nothing else:
  1. axis    : a / syms come from legs.npz (E_ts / symbols) instead of NEWS_FEATURES.npz (deleted).
  2. members : per-anchor member lists come from isfinite(KING_OOF.P) instead of F['off']/F['m'] (deleted).
               dlw_targets['members'] was tried first and refuted (panel members are all crypto; dlw's include
               68 TradFi; crypto-filtered dlw is 332 not 400). The definition is verified AT RUNTIME two ways:
               bitwise against the 9 surviving real panel member lists in NEWS_FEATURES_parity9.npz, and by
               asserting the two arms' finite-cell masks are bitwise identical so members stay arm-independent.
  3. the drift assertion over the F10 training receipt's recorded inputs SKIPS entries whose file no longer
     exists, and records each one BY NAME as UNVERIFIABLE. It does not pretend to have checked them.
  4. the legs<->F10 provenance binding is asserted for an uncrossed pairing and, for a crossed pairing, is
     recorded BY NAME as deliberately bypassed. Crossed pairings are not run in this round.
  6. rn8 (PREREG_step1_rn8_clamp_2026-09-25.md, commit 1624526af): --no-rn8-clamp removes the funding clamp
     (combo_target.py L33-34) WITHOUT TOUCHING ANY SOURCE FILE, by passing an all-NaN rn8 array.
     Why that is exactly equivalent to deleting the two lines: inside step(), rn8 appears ONLY at L20 (signature),
     L23 (shape check), L33 and L34 (the clamp). The clamp condition is
         (zkc < 0) & np.isfinite(rn8) & (rn8 <= -.001)
     so an rn8 that is NaN everywhere makes np.isfinite(rn8) False in every cell and the clamp can never fire, while
     the L23 shape check still passes because NaN preserves shape and dtype. Editing the kernel would change the
     source sha that this device asserts; substituting the input does not. The grep that establishes rn8 has no other
     consumer in the kernel is RE-RUN INTO THE RECEIPT at run time rather than cited from memory.
  5. B8 (PREREG_fresh_rootcause_B8_2026-09-24.md, commit 38f4c0fbd): --seat-npz substitutes a seat series recomputed
     for a different msharpe_look, produced by fa_b8seat.py whose G1 gate proved that the same recomputation
     reproduces legs.npz's WL BITWISE at look=900. The substitution is a drop-in for seats_in and touches nothing
     else. A behavioural assertion requires the substituted seat to actually differ from look=900 inside the
     window on ready anchors, so a silently unwired switch cannot pass as a full re-run.

G0 (the reason this device exists): run it on each arm's OWN pairing and require it to reproduce that arm's
existing combo. Reported two ways, because np.savez_compressed embeds zip member timestamps and therefore the
CONTAINER bytes are not reproducible across runs by construction:
    container_sha_equal   -- the literal file-byte comparison (may be False purely from zip metadata)
    arrays_bitwise_equal  -- every key present, same dtype, same shape, and identical RAW ARRAY BYTES
The substantive requirement is arrays_bitwise_equal; container_sha_equal is reported so the distinction is on the
record rather than hidden. This is a named deviation from AMENDMENT 2's wording "逐字节相同", decided and written
here BEFORE any comparison was run.

LADDER (PREREG_fresh_gap_carrier_ladder_2026-09-25.md, amendment 1 a9a5fe8a5): --donor-root plus --swap replaces
named arrays with the donor root's, one item at a time, so each arm measures what that input carries. Provenance is
recorded PER ARRAY with its sha, because "which arrays came from where" is the whole content of a ladder arm and a
directory name is not evidence of it.

usage: env -i PATH=/usr/bin:/bin HOME=/root python -B fa_combo.py PATH,HOME,LC_CTYPE \
         --legs-root <root> --f10-root <root> --seed 42 --out <dir> [--compare <existing combo dir>] [--allow-crossed]
"""
import os, sys, json, argparse, collections, datetime, pathlib, hashlib, zipfile, io, importlib
import numpy as np

WLIST = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WLIST); assert not _x, f"env outside whitelist: {_x}"
sys.argv = [sys.argv[0]] + sys.argv[2:]
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from continuous_combo import evolve, verify_training
from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA
import combo_target

# Declared hunk per variant kernel. The device re-derives at RUNTIME that the variant differs from combo_target.py
# ONLY by this hunk: every line before it identical, every line after it identical, and the line count exactly +delta.
# A variant kernel is a second copy of the mixing kernel; without this check "only one line changed" is my word for it.
KERNEL_HUNK = {
    "combo_target_c3": {
        "orig_line_1based": 33,
        "orig_text": "    zkc=np.where((zkc<0)&np.isfinite(rn8)&(rn8<=-.001),0.,zkc)",
        "n_new_lines": 1,
        "why": "C3: rn8 clamp threshold -0.001 -> 0 (refuse to short ANY name whose funding is negative)",
        "second_line": {"orig_line_1based": 34,
                        "orig_text": "    zfc=np.where((zfc<0)&np.isfinite(rn8)&(rn8<=-.001),0.,zfc)"},
    },
    "combo_target_b1": {
        "orig_line_1based": 38,
        "orig_text": "    raw=.55*kc+.45*fc;gross=float(np.abs(raw).sum());names=int((np.abs(raw)>1e-9).sum())",
        "n_new_lines": 3,
        "why": "B1: per-leg L1 normalisation before mixing (raw = .55*kc/||kc||1 + .45*fc/||fc||1)",
    },
}

W = pathlib.Path('/dev/shm/fresh_2026-09-23')
N = pathlib.Path('/dev/shm/news_2026-09-23')
PREREG = {'path': 'docs/PREREG_fresh_book_anomaly_2026-09-24.md', 'commit': '427d76f34',
          'amendment_2': '953df1489', 'correction': 'dfdcf9ba8'}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(16 << 20), b''): h.update(b)
    return h.hexdigest()


def arrays_equal(p1, p2):
    """compare two npz by ARRAY CONTENT, bit for bit, independent of zip container metadata"""
    A = np.load(p1, allow_pickle=True); B = np.load(p2, allow_pickle=True)
    ka, kb = sorted(A.files), sorted(B.files)
    if ka != kb: return False, {"keys_differ": {"only_a": sorted(set(ka) - set(kb)), "only_b": sorted(set(kb) - set(ka))}}
    per = {}
    ok = True
    for k in ka:
        a, b = A[k], B[k]
        same = (a.dtype == b.dtype and a.shape == b.shape and a.tobytes() == b.tobytes())
        per[k] = {"dtype": str(a.dtype), "shape": list(a.shape), "identical_bytes": bool(same)}
        ok = ok and same
    return ok, per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--legs-root', required=True); ap.add_argument('--f10-root', required=True)
    ap.add_argument('--seed', type=int, choices=(42, 2027), required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--compare', default=None)
    ap.add_argument('--allow-crossed', action='store_true')
    ap.add_argument('--const-seat', action='store_true', help='B2: replace seats by their judge-window mean, per component')
    ap.add_argument('--seat-npz', default=None, help='B8: seat series recomputed for a different msharpe_look (fa_b8seat.py output)')
    ap.add_argument('--no-rn8-clamp', action='store_true', help='rn8: disable the funding clamp by passing an all-NaN rn8')
    ap.add_argument('--donor-root', default=None, help='ladder: root supplying the swapped arrays')
    ap.add_argument('--swap', default='', help='ladder: comma list from KZ,WL,ZFD,ready,QV,RN8,F10 taken from --donor-root')
    ap.add_argument('--negate', default='', help='ladder mutation control: comma list of swapped arrays to negate')
    ap.add_argument('--compare-tol', type=float, default=None,
                    help='ladder positive control: compare weights against --compare with max|dw| <= tol instead of bitwise')
    ap.add_argument('--kernel', default='combo_target', help='mixing kernel module to run (default: the production one). '
                                                            'A variant must appear in KERNEL_HUNK and its diff vs '
                                                            'combo_target.py is re-derived at runtime.')
    ap.add_argument('--compare-state', default=None, help='assert kc/fc are BITWISE IDENTICAL to this baseline combo '
                                                          'and that raw DIFFERS -- the invariant of a raw-only change')
    ap.add_argument('--compare-publish', default=None,
                    help='mutation control: assert the PUBLISH DECISION differs from this baseline combo on >=1 anchor. '
                         'Use this, not --compare-state: a mutation is meant to change the state chain, so the '
                         'raw-only invariant can never hold for it.')
    ap.add_argument('--panel', default=None, help="rn8: derive members from THIS panel's own off/m instead of "
                                                 "substituting isfinite(KING_OOF.P). Use it whenever the arm's panel "
                                                 "still exists -- the substitution was only ever a workaround for "
                                                 "FRESH's DELETED panel, and it drags in two validations (arm "
                                                 "independence, parity9) that are about the substitution, not about "
                                                 "the book.")
    args = ap.parse_args()
    RN8INFO = None
    LADDER = None
    SWAP = [x.strip() for x in args.swap.split(',') if x.strip()]
    NEG = [x.strip() for x in args.negate.split(',') if x.strip()]
    VALID = ('KZ', 'WL', 'ZFD', 'ready', 'QV', 'RN8', 'F10')
    for x in SWAP + NEG:
        assert x in VALID, f"unknown swap item {x}; valid: {VALID}"
    assert not (SWAP and args.donor_root is None), "--swap requires --donor-root"
    assert all(x in SWAP for x in NEG), "--negate items must also be swapped"
    # ---- kernel selection, with the only-difference check done at runtime ----
    KINFO = {"kernel_module": args.kernel}
    korig = (pathlib.Path(HERE) / 'combo_target.py')
    KINFO["combo_target_sha256"] = sha(korig)
    if args.kernel != 'combo_target':
        assert args.kernel in KERNEL_HUNK, f"variant kernel {args.kernel} has no declared hunk"
        spec = KERNEL_HUNK[args.kernel]
        kvar = pathlib.Path(HERE) / (args.kernel + '.py')
        KINFO["variant_sha256"] = sha(kvar); KINFO["declared_hunk"] = spec
        A_ = korig.read_text().split('\n'); B_ = kvar.read_text().split('\n')
        i0 = spec["orig_line_1based"] - 1
        assert A_[i0] == spec["orig_text"], f"declared hunk text not at line {spec['orig_line_1based']} of combo_target.py"
        if "second_line" in spec:
            # a two-line hunk (C3 changes the same threshold on both clamp lines). Declared explicitly rather than
            # loosening the single-hunk check, and the differing line set must equal EXACTLY the declared lines.
            j0 = spec["second_line"]["orig_line_1based"] - 1
            assert A_[j0] == spec["second_line"]["orig_text"], "declared second hunk text not where stated"
            assert len(A_) == len(B_), "variant kernel line count changed"
            got = [i for i in range(len(A_)) if A_[i] != B_[i]]
            assert got == sorted([i0, j0]), f"variant kernel differs on unexpected lines: {[g+1 for g in got]}"
        else:
            assert A_[:i0] == B_[:i0], "variant kernel differs BEFORE the declared hunk"
            assert A_[i0 + 1:] == B_[i0 + spec["n_new_lines"]:], "variant kernel differs AFTER the declared hunk"
            assert len(B_) == len(A_) + spec["n_new_lines"] - 1, "variant kernel line count off"
        KINFO["only_declared_hunk_differs"] = True
        KMOD = importlib.import_module(args.kernel)
        import continuous_combo as _CC
        _CC.step = KMOD.step          # continuous_combo.py L10 binds `step` by name; this is the injection point
        assert _CC.step is KMOD.step, "kernel injection did not take"
        KINFO["injected_into"] = "continuous_combo.step"
    else:
        KINFO["only_declared_hunk_differs"] = "N/A (production kernel)"
        KINFO["variant_sha256"] = None
    assert not (args.const_seat and args.seat_npz), 'B2 and B8 are different interventions; do not combine them'
    B8INFO = None
    LR_ROOT = pathlib.Path(args.legs_root); F10_ROOT = pathlib.Path(args.f10_root)
    crossed = (LR_ROOT != F10_ROOT)
    froot = F10_ROOT / f'work/f10_s{args.seed}'
    if crossed and not args.allow_crossed:
        raise SystemExit("crossed pairing requires --allow-crossed (AMENDMENT 2 correction: the legs<->F10 "
                         "provenance binding must be bypassed deliberately, and crossed arms are contaminated "
                         "because F10's loss reads WL, which is King-dependent)")

    legs_p = LR_ROOT / 'work/legs.npz'; legs_rcpt = LR_ROOT / 'receipts/P3_LEGS.json'
    paths = [legs_p, legs_rcpt, froot / 'F10_OOF.npz', froot / 'TRAIN_RECEIPT.json', N / 'inputs/bundle_config.json',
             N / 'receipts/P1_members_2025H2on.npz',
             pathlib.Path('/workspace/axis_0919/x0918r/masks/member_mask_tradable_AND_live_W24H_cachegrid.npz')]
    ident = {str(p): sha(p) for p in paths}
    rec = json.loads((froot / 'TRAIN_RECEIPT.json').read_text()); lr = json.loads(legs_rcpt.read_text())
    assert rec['status'] == 'ALL_DECLARED_FOLDS_SCORED_NOT_COMBO_CERTIFIED' and rec['pred_sha256'] == ident[str(froot / 'F10_OOF.npz')]
    verify_training(froot, rec, args.seed, sha)
    assert set(rec['folds']) == set(rec['expected_folds'])

    # change 3: drift over the training receipt's recorded inputs -- skip-and-NAME what no longer exists
    unverifiable = []
    for p, h in rec['inputs'].items():
        if not os.path.exists(p):
            unverifiable.append({"path": p, "recorded_sha256": h, "why": "file no longer on disk; drift NOT checked"}); continue
        assert sha(p) == h, ('training input drift', p)
    for p, h in rec['sources'].items():
        if not os.path.exists(p):
            unverifiable.append({"path": p, "recorded_sha256": h, "why": "file no longer on disk; drift NOT checked"}); continue
        assert sha(p) == h, ('training source drift', p)

    # change 4: legs<->F10 provenance binding
    binding = {"legs_used": str(legs_p), "legs_sha256": ident[str(legs_p)], "legs_receipt_sha256": lr['sha256'],
               "f10_training_legs": [p for p in rec['inputs'] if p.endswith('legs.npz')]}
    if not crossed:
        assert ident[str(legs_p)] == lr['sha256'], 'legs sha != P3_LEGS receipt'
        binding["status"] = "ASSERTED (uncrossed pairing)"
    else:
        binding["status"] = ("DELIBERATELY BYPASSED (crossed pairing): the F10 was trained with the other arm's legs, "
                             "so its recorded provenance cannot match the legs it is being run with")

    leg = np.load(legs_p); score = np.load(froot / 'F10_OOF.npz')
    a = leg['E_ts'].astype(np.int64); syms = leg['symbols']                      # change 1
    assert np.array_equal(score['E_ts'], a) and np.array_equal(score['symbols'], syms)
    mk = np.load(paths[6]); assert np.array_equal(mk['ts'].astype(np.int64), a)
    crypto = np.load(paths[5])['crypto']; cand = mk['mask'] & crypto[None, :]

    # change 2 (lead-approved 2026-09-24): members := isfinite(KING_OOF.P).
    # dlw_targets['members'] was tried first and REFUTED: the panel's 400 members are all crypto, dlw's 400
    # include 68 TradFi, and filtering dlw to crypto leaves only 332 -- the panel fills those slots with the next
    # crypto names down the liquidity ranking, which no filter can reproduce.
    # This definition is verified HERE, at runtime, two independent ways before it is used.
    king_oof = LR_ROOT / 'work/king/KING_OOF.npz'
    K = np.load(king_oof); ident[str(king_oof)] = sha(king_oof)
    assert np.array_equal(K['E_ts'].astype(np.int64), a) and np.array_equal(K['symbols'], syms)
    if args.panel:
        # ---- real members, no substitution ----
        PN = pathlib.Path(args.panel); ident[str(PN)] = sha(PN)
        F_ = np.load(PN, allow_pickle=True)
        assert np.array_equal(F_['anchors'].astype(np.int64), a), 'panel anchor axis != legs axis'
        assert np.array_equal(F_['symbols'], syms), 'panel symbol axis != legs axis'
        off_ = F_['off'].astype(np.int64); m_ = F_['m']
        members = [m_[off_[i]:off_[i + 1]].astype(np.int64) for i in range(len(a))]
        assert min(len(x) for x in members) >= 0
        memmask = np.zeros((len(a), len(syms)), bool)
        for i, mm in enumerate(members):
            memmask[i, mm] = True
        memsub = {"definition": "members := the panel's OWN off/m (no substitution)",
                  "source": str(PN), "sha256": ident[str(PN)],
                  "why_no_substitution": ("isfinite(KING_OOF.P) was a workaround for FRESH's DELETED panel. This arm's "
                                          "panel is on disk, so the real member lists are used and the two validations "
                                          "that exist to justify the substitution (arm-independence, parity9) do not "
                                          "apply -- they validate the substitute, not the book."),
                  "member_cells": int(memmask.sum()),
                  "arm_independence_asserted": "N/A (no substitution)",
                  "validated_by": "the G0 bitwise reproduction of this arm's own combo (run with --compare)"}
        arm_indep = None
    else:
        memmask = np.isfinite(K['P'])
    # (2a) arm-independence: both arms' finite-cell masks must be bitwise identical, otherwise deriving members
    #      from King's OOF WOULD smuggle King information into the comparison. Asserted, not assumed.
        other = (N if LR_ROOT == W else W) / 'work/king/KING_OOF.npz'
        KO = np.load(other)
        arm_indep = bool(np.array_equal(np.isfinite(KO['P']), memmask))
        assert arm_indep, 'the two arms\' King finite-cell masks differ; members would not be arm-independent'
    # (2b) bitwise against the surviving real panel member lists (9 anchors)
        PAR = N / 'work/NEWS_FEATURES_parity9.npz'
        Pp = np.load(PAR, allow_pickle=True); ident[str(PAR)] = sha(PAR)
        pos = {int(v): i for i, v in enumerate(a)}
        par = {}
        for tt in Pp['anchors'].astype(np.int64):
            pm = np.sort(np.asarray(Pp[f'm_{int(tt)}']).astype(np.int64))
            km = np.sort(np.flatnonzero(memmask[pos[int(tt)]]).astype(np.int64))
            par[int(tt)] = bool(len(pm) == len(km) and np.array_equal(pm, km))
        assert all(par.values()), f'panel-member parity failed at {[k for k, v in par.items() if not v]}'
        members = [np.flatnonzero(memmask[i]).astype(np.int64) for i in range(len(a))]
        memsub = {"definition": "members := isfinite(KING_OOF.P)",
                  "source": str(king_oof), "sha256": ident[str(king_oof)],
                  "refuted_alternative": ("dlw_targets['members'] -- panel members are all crypto (400), dlw's 400 include "
                                          "68 TradFi, crypto-filtered dlw is only 332; no filter reproduces the panel"),
                  "confirmation_1_panel_parity_9_anchors": {"file": str(PAR), "sha256": ident[str(PAR)],
                                                            "anchors": {str(k): v for k, v in par.items()},
                                                            "ALL_IDENTICAL": bool(all(par.values()))},
                  "confirmation_2_fingerprint": "member_cells_outside_book_universe must equal the arm's recorded value; see G0 and the printed value",
                  "arm_independence_asserted": arm_indep,
                  "scope_limit": ("this is the member rule of the NEW_S / FRESH panel, which is the panel both arms read. "
                                  "The researcher NEW's member rule is NOT verifiable -- its panel is not on disk."),
                  "lead_approval": "2026-09-24, after both confirmations were reported"}

    assert sha(UNIVERSE_PATH) == UNIVERSE_SHA, 'universe content identity'
    universe = np.load(UNIVERSE_PATH)
    use = (a >= 1672531200) & (a <= universe['ts'][-1]); au = a[use]
    assert memmask[use].sum(1).min() > 0, 'an anchor inside the use-window has no members'
    book_legal = align_universe(au, syms, universe) & cand[use]
    ident[UNIVERSE_PATH] = UNIVERSE_SHA
    config = json.loads(paths[4].read_text())
    sources = {str(p): sha(p) for p in [pathlib.Path(__file__), pathlib.Path(HERE) / 'continuous_combo.py',
                                        pathlib.Path(HERE) / 'combo_target.py', pathlib.Path(HERE) / 'book_universe.py',
                                        *( [pathlib.Path(HERE) / (args.kernel + '.py')] if args.kernel != 'combo_target' else [] ),
                                        W / 'vendor_live/fea171/combo_stage.py']}
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)
    mem_u = [members[i] for i in np.flatnonzero(use)]
    outside = int(sum(int((~book_legal[k][m]).sum()) for k, m in enumerate(mem_u)))
    summary = {}
    for policy in ('literal', 'scaled_diagnostic'):
        # ---- ladder: per-array source selection, recorded with shas ----
        SRC = {k: 'base' for k in VALID}
        arr = {'KZ': leg['KZ'], 'WL': leg['WL'], 'ZFD': leg['ZFD'], 'ready': leg['ready'],
               'QV': leg['QV'], 'RN8': leg['RN8'], 'F10': score['P']}
        if SWAP:
            DR = pathlib.Path(args.donor_root)
            dleg_p = DR / 'work/legs.npz'; dsc_p = DR / f'work/f10_s{args.seed}/F10_OOF.npz'
            dleg = np.load(dleg_p); dsc = np.load(dsc_p)
            ident[str(dleg_p)] = sha(dleg_p); ident[str(dsc_p)] = sha(dsc_p)
            assert np.array_equal(dleg['E_ts'].astype(np.int64), a), 'donor legs axis != base axis'
            assert np.array_equal(dleg['symbols'], syms), 'donor legs symbols != base symbols'
            assert np.array_equal(dsc['E_ts'].astype(np.int64), a), 'donor F10 axis != base axis'
            dmap = {'KZ': dleg['KZ'], 'WL': dleg['WL'], 'ZFD': dleg['ZFD'], 'ready': dleg['ready'],
                    'QV': dleg['QV'], 'RN8': dleg['RN8'], 'F10': dsc['P']}
            for k in SWAP:
                arr[k] = dmap[k]; SRC[k] = 'donor'
            for k in NEG:
                arr[k] = -np.asarray(arr[k]) if k != 'ready' else ~np.asarray(arr[k]).astype(bool)
                SRC[k] += '+negated'
            # behavioural, not textual: a swapped array must actually differ from the base one, else the arm is a
            # relabelled baseline. `ready` is bool and may legitimately coincide, so it is reported not asserted.
            diffs = {}
            for k in SWAP:
                b_ = np.asarray({'KZ': leg['KZ'], 'WL': leg['WL'], 'ZFD': leg['ZFD'], 'ready': leg['ready'],
                                 'QV': leg['QV'], 'RN8': leg['RN8'], 'F10': score['P']}[k])
                v_ = np.asarray(arr[k])
                diffs[k] = int((~np.isclose(np.nan_to_num(b_, nan=-9e9).astype(np.float64),
                                            np.nan_to_num(v_, nan=-9e9).astype(np.float64), rtol=0, atol=0)).sum())
            LADDER = {'donor_root': str(args.donor_root), 'swapped': SWAP, 'negated': NEG,
                      'per_array_source': SRC, 'donor_legs_sha256': ident[str(dleg_p)],
                      'donor_f10_sha256': ident[str(dsc_p)], 'cells_differing_vs_base': diffs,
                      'note': 'a configuration the pipeline cannot produce; this arm is a measuring instrument only'}
            # The non-vacuity assertion applies only to a REAL swap. The red control deliberately swaps the base
            # root's own arrays into itself, so identity is exactly what it is testing for; asserting non-identity
            # there would make the control impossible to run. Which case we are in is recorded, not inferred.
            self_swap = (str(DR) == str(LR_ROOT))
            LADDER['self_swap'] = bool(self_swap)
            if not self_swap:
                for k in SWAP:
                    if k != 'ready':
                        assert diffs[k] > 0, f"swapped {k} is identical to the base array -- this arm is a relabelled baseline"
            else:
                assert all(v == 0 for k, v in diffs.items()), \
                    f"self-swap must be identical on every array, got {diffs}"
        seats_in = np.asarray(arr['WL'])[use].astype(np.float64)
        if args.seat_npz:
            SZ = np.load(args.seat_npz); ident[args.seat_npz] = sha(args.seat_npz)
            assert np.array_equal(SZ['E_ts'].astype(np.int64), a), 'seat npz axis != legs axis'
            assert np.array_equal(SZ['ready'].astype(bool), leg['ready'].astype(bool)), 'seat npz ready != legs ready'
            lk = int(SZ['look'])
            assert lk != 900, 'seat npz is the look=900 baseline, not a variant'
            rdy = leg['ready'][use].astype(bool)
            new = SZ['WL'][use]; old = leg['WL'][use]
            assert new.dtype == old.dtype == np.float32, (new.dtype, old.dtype)
            nd = int((~(new[rdy].view(np.uint32) == old[rdy].view(np.uint32)).all(1)).sum())
            # behavioural, not textual: if the switch were unwired this count would be 0 and the run would be a
            # byte-identical re-run of the baseline masquerading as an arm.
            assert nd > 0, f'B8 look={lk}: seat bitwise identical to look=900 on every ready anchor in the window'
            seats_in = new.astype(np.float64)
            B8INFO = {'seat_npz': args.seat_npz, 'seat_npz_sha256': ident[args.seat_npz], 'look': lk,
                      'ready_anchors_in_window': int(rdy.sum()),
                      'ready_anchors_with_seat_differing_from_look900': nd,
                      'mean_seat_look900': [float(x) for x in np.nanmean(old[rdy], 0)],
                      'mean_seat_this_look': [float(x) for x in np.nanmean(new[rdy], 0)]}
        if args.const_seat:
            import calendar as _cal, time as _tm
            _ts = lambda s: _cal.timegm(_tm.strptime(s, '%Y-%m-%dT%H:%M:%SZ'))
            jw = (au >= _ts('2023-06-30T04:00:00Z')) & (au <= _ts('2025-12-31T20:00:00Z'))
            const = np.nanmean(seats_in[jw], axis=0)
            assert np.isfinite(const).all() and const.shape == (3,), const
            seats_in = np.tile(const, (len(au), 1))
            # Contract = âthe seat is constantâ. Test it as ROW-WISE BITWISE EQUALITY, not as variance == 0.0:
            # nanvar of identical float64 values is ~1e-32, not exactly zero, because the mean itself rounds.
            # Welding the contract to an exact float identity is the brittle-assertion family; the rows being
            # bit-identical is the thing actually required.
            rows_identical = bool(np.all(seats_in == seats_in[0]))
            assert rows_identical, 'B2 contract: seat rows are not bitwise identical'
            seat_variance = [float(np.nanvar(seats_in[:, j])) for j in range(3)]   # reported, not gated
            B2INFO = {'const_seat': [float(x) for x in const], 'rows_bitwise_identical': rows_identical,
                      'seat_variance_reported_not_gated': seat_variance,
                      'judge_window_anchors': int(jw.sum())}
        rn8_in = np.asarray(arr['RN8'])[use].astype(np.float64)
        if args.no_rn8_clamp:
            # The clamp's ELIGIBLE population on the real rn8, member cells only. This is an UPPER BOUND on the cells
            # the clamp actually zeroed: it does not condition on zkc < 0, which is internal to step(). Reported as an
            # upper bound, never as a hit count.
            elig = 0; elig_anch = 0
            for k, mm in enumerate(mem_u):
                v = rn8_in[k][mm]
                c = int((np.isfinite(v) & (v <= -0.001)).sum())
                elig += c; elig_anch += int(c > 0)
            nan_rn8 = np.full_like(rn8_in, np.nan)
            assert nan_rn8.shape == rn8_in.shape and nan_rn8.dtype == rn8_in.dtype, 'NaN rn8 must preserve shape/dtype'
            assert not np.isfinite(nan_rn8).any(), 'NaN rn8 must be non-finite everywhere so the clamp cannot fire'
            assert elig > 0, ('the clamp has an empty eligible population on this arm -- removing it could not change '
                              'anything, so the switch would be unwired')
            RN8INFO = {'intervention': 'all-NaN rn8 passed to evolve; combo_target.py L33-34 can never fire',
                       'source_files_modified': 'none (the kernel sha assertions still hold)',
                       'clamp_eligible_member_cells_UPPER_BOUND': elig,
                       'clamp_eligible_anchors_UPPER_BOUND': elig_anch,
                       'upper_bound_note': 'does not condition on zkc<0 (internal to step); true hit count <= this'}
            rn8_in = nan_rn8
        result = evolve(au, np.asarray(arr['KZ'])[use].astype(np.float64), np.asarray(arr['F10'])[use].astype(np.float64),
                        np.asarray(arr['ZFD'])[use].astype(np.float64),
                        seats_in, rn8_in, mem_u, np.asarray(arr['QV'])[use].astype(np.float64),
                        book_legal, np.asarray(arr['ready'])[use], config['params'], policy)
        p = out / (policy + '.npz'); tmp = out / (policy + '.tmp.npz')
        np.savez_compressed(tmp, E_ts=au, symbols=syms, **result); tmp.replace(p)
        counts = dict(collections.Counter(result['reason'])); years = {}
        yr = np.array([datetime.datetime.fromtimestamp(int(x), datetime.timezone.utc).year for x in au])
        for y in np.unique(yr):
            m = yr == y; years[str(y)] = {'anchors': int(m.sum()), 'publish': int(result['trade_mask'][m].sum()),
                                          'mean_producer_gross': float(np.abs(result['raw'][m]).sum(1).mean())}
        summary[policy] = {'path': str(p), 'sha': sha(p), 'reasons': counts, 'years': years}
    for p, h in ident.items(): assert sha(p) == h
    for p, h in sources.items(): assert sha(p) == h

    g0 = None
    if args.compare and args.compare_tol is not None:
        cmp_dir = pathlib.Path(args.compare); g0 = {"compare_dir": str(cmp_dir), "mode": "tolerance", "tol": args.compare_tol, "policies": {}}
        allok = True
        for policy in ('literal', 'scaled_diagnostic'):
            A_ = np.load(out / (policy + '.npz'), allow_pickle=True); B_ = np.load(cmp_dir / (policy + '.npz'), allow_pickle=True)
            dw = np.abs(np.nan_to_num(A_['weights'], nan=0.0) - np.nan_to_num(B_['weights'], nan=0.0))
            mx = float(dw.max()); ncell = int((dw > args.compare_tol).sum())
            tm = int((np.asarray(A_['trade_mask']).astype(bool) != np.asarray(B_['trade_mask']).astype(bool)).sum())
            g0["policies"][policy] = {"max_abs_dw": mx, "cells_over_tol": ncell, "anchors_trade_mask_differing": tm,
                                      "within_tol": bool(mx <= args.compare_tol)}
            allok = allok and mx <= args.compare_tol
        g0["WITHIN_TOL_ALL"] = bool(allok)
        g0["per_array_hint"] = ("if this fails, the ladder's input list is INCOMPLETE -- something the donor book uses is "
                               "still coming from the base root. The failing quantity is named by cells_over_tol.")
    elif args.compare:
        cmp_dir = pathlib.Path(args.compare); g0 = {"compare_dir": str(cmp_dir), "policies": {}}
        allok = True
        for policy in ('literal', 'scaled_diagnostic'):
            mine = out / (policy + '.npz'); theirs = cmp_dir / (policy + '.npz')
            csha = (sha(mine) == sha(theirs))
            aok, per = arrays_equal(mine, theirs)
            g0["policies"][policy] = {"container_sha_equal": bool(csha), "container_sha_mine": sha(mine),
                                      "container_sha_theirs": sha(theirs), "arrays_bitwise_equal": bool(aok), "per_key": per}
            allok = allok and aok
        g0["ARRAYS_BITWISE_EQUAL_ALL"] = bool(allok)
        g0["note"] = ("np.savez_compressed embeds zip member timestamps, so container_sha_equal can be False with "
                      "identical contents. The substantive gate is ARRAYS_BITWISE_EQUAL_ALL.")

    if args.no_rn8_clamp:
        ksrc = (pathlib.Path(HERE) / 'combo_target.py').read_text().split('\n')
        hits = [{'line': i + 1, 'text': l.strip()} for i, l in enumerate(ksrc) if 'rn8' in l]
        RN8INFO['grep_rn8_in_combo_target'] = hits
        RN8INFO['grep_line_numbers'] = [h['line'] for h in hits]
        # the equivalence claim is sound only if the sole rn8 uses that change values are the two clamp lines
        clampish = [h for h in hits if 'np.where' in h['text']]
        assert len(clampish) == 2, f'expected exactly 2 clamp lines using rn8, found {len(clampish)}'
        RN8INFO['equivalence_sound'] = True
    PUB_CHK = None
    if args.compare_publish:
        base = pathlib.Path(args.compare_publish)
        PUB_CHK = {"baseline": str(base), "policies": {}}
        anyflip = False
        for policy in ('literal', 'scaled_diagnostic'):
            B_ = np.load(base / (policy + '.npz'), allow_pickle=True)
            V_ = np.load(out / (policy + '.npz'), allow_pickle=True)
            tb = np.asarray(B_['trade_mask']).astype(bool); tv = np.asarray(V_['trade_mask']).astype(bool)
            nflip = int((tb != tv).sum())
            PUB_CHK["policies"][policy] = {"anchors_publish_differing": nflip,
                                           "publish_base": int(tb.sum()), "publish_variant": int(tv.sum())}
            anyflip = anyflip or nflip > 0
        PUB_CHK["PUBLISH_DECISION_CHANGED"] = bool(anyflip)
        assert anyflip, "mutation control: the publish decision did not change on any anchor -- the device is not driving the book"
    STATE_CHK = None
    if args.compare_state:
        base = pathlib.Path(args.compare_state)
        STATE_CHK = {"baseline": str(base), "policies": {}}
        okall = True
        for policy in ('literal', 'scaled_diagnostic'):
            Bn = np.load(base / (policy + '.npz'), allow_pickle=True)
            Vn = np.load(out / (policy + '.npz'), allow_pickle=True)
            same = {k: bool(Bn[k].dtype == Vn[k].dtype and Bn[k].shape == Vn[k].shape
                            and Bn[k].tobytes() == Vn[k].tobytes()) for k in ('kc', 'fc', 'E_ts', 'symbols')}
            rawdiff = int((~np.isclose(np.nan_to_num(Bn['raw'], nan=-9e9), np.nan_to_num(Vn['raw'], nan=-9e9),
                                       rtol=0, atol=0)).any(1).sum())
            tmdiff = int((np.asarray(Bn['trade_mask']).astype(bool) != np.asarray(Vn['trade_mask']).astype(bool)).sum())
            STATE_CHK["policies"][policy] = {"state_bitwise_identical": same, "anchors_raw_differing": rawdiff,
                                             "anchors_trade_mask_differing": tmdiff}
            # a raw-only change MUST leave the state chain untouched ...
            assert all(same.values()), f"{policy}: state chain changed -- this is not a raw-only intervention"
            # ... and MUST actually change raw, or the kernel injection silently did nothing
            assert rawdiff > 0, f"{policy}: raw identical on every anchor -- the variant kernel did not take effect"
            okall = okall and all(same.values()) and rawdiff > 0
        STATE_CHK["VERDICT"] = "STATE_INVARIANT_AND_RAW_CHANGED" if okall else "FAILED"
    receipt = {'status': 'FA_COMBO_PHASE2', 'prereg': PREREG, 'seed': args.seed,
               'pairing': {'legs_root': str(LR_ROOT), 'f10_root': str(F10_ROOT), 'crossed': bool(crossed)},
               'changes_vs_fresh_combo': ['axis from legs.npz', 'members from isfinite(KING_OOF.P), verified vs panel parity9 + fingerprint',
                                          'training-input drift skipped-and-named for deleted files',
                                          'legs<->F10 binding asserted or deliberately bypassed'],
               'inputs': ident, 'sources': sources, 'policies': summary,
               'member_substitution': memsub, 'unverifiable_provenance': unverifiable, 'legs_f10_binding': binding,
               'member_cells_outside_book_universe': outside, 'G0': g0,
               'B2': (B2INFO if args.const_seat else None), 'B8': B8INFO, 'RN8': RN8INFO,
               'KERNEL': KINFO, 'STATE_CHECK': STATE_CHK, 'LADDER': LADDER, 'PUBLISH_CHECK': PUB_CHK}
    (out / 'FA_COMBO_RECEIPT.json').write_text(json.dumps(receipt, indent=2, allow_nan=False))
    print("FA_COMBO", json.dumps({"swapped": SWAP, "negated": NEG,
                                  "swap_diff_cells": (LADDER or {}).get("cells_differing_vs_base"),
                                  "tol_compare": (g0 or {}).get("WITHIN_TOL_ALL"),
                                  "publish_changed": (PUB_CHK or {}).get("PUBLISH_DECISION_CHANGED"),
                                  "kernel": args.kernel,
                                  "only_declared_hunk_differs": KINFO["only_declared_hunk_differs"],
                                  "state_check": (STATE_CHK or {}).get("VERDICT"),
                                  "raw_differing_anchors": {k: v["anchors_raw_differing"] for k, v in (STATE_CHK or {}).get("policies", {}).items()},
                                  "no_rn8_clamp": bool(args.no_rn8_clamp),
                                  "clamp_eligible_cells_upper_bound": (RN8INFO or {}).get("clamp_eligible_member_cells_UPPER_BOUND"),
                                  "look": (B8INFO or {}).get("look", 900),
                                  "seat_rows_differing_from_look900": (B8INFO or {}).get("ready_anchors_with_seat_differing_from_look900"),
                                  "legs": LR_ROOT.name, "f10": F10_ROOT.name, "crossed": crossed,
                                  "outside": outside, "unverifiable": len(unverifiable),
                                  "G0_arrays_bitwise_equal": (g0 or {}).get("ARRAYS_BITWISE_EQUAL_ALL"),
                                  "G0_container_sha_equal": {k: v.get("container_sha_equal") for k, v in (g0 or {}).get("policies", {}).items()}}),
          flush=True)
    if args.compare and args.compare_tol is not None and not g0["WITHIN_TOL_ALL"]: sys.exit(3)
    if args.compare and args.compare_tol is None and not g0["ARRAYS_BITWISE_EQUAL_ALL"]: sys.exit(3)


if __name__ == '__main__':
    main()
