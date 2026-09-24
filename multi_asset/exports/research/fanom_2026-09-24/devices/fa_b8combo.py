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

usage: env -i PATH=/usr/bin:/bin HOME=/root python -B fa_combo.py PATH,HOME,LC_CTYPE \
         --legs-root <root> --f10-root <root> --seed 42 --out <dir> [--compare <existing combo dir>] [--allow-crossed]
"""
import os, sys, json, argparse, collections, datetime, pathlib, hashlib, zipfile, io
import numpy as np

WLIST = set(sys.argv[1].split(",")); _x = sorted(set(os.environ) - WLIST); assert not _x, f"env outside whitelist: {_x}"
sys.argv = [sys.argv[0]] + sys.argv[2:]
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from continuous_combo import evolve, verify_training
from book_universe import align as align_universe, PATH as UNIVERSE_PATH, SHA as UNIVERSE_SHA
import combo_target

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
    args = ap.parse_args()
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
                                        W / 'vendor_live/fea171/combo_stage.py']}
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)
    mem_u = [members[i] for i in np.flatnonzero(use)]
    outside = int(sum(int((~book_legal[k][m]).sum()) for k, m in enumerate(mem_u)))
    summary = {}
    for policy in ('literal', 'scaled_diagnostic'):
        seats_in = leg['WL'][use].astype(np.float64)
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
        result = evolve(au, leg['KZ'][use].astype(np.float64), score['P'][use].astype(np.float64), leg['ZFD'][use].astype(np.float64),
                        seats_in, leg['RN8'][use].astype(np.float64), mem_u, leg['QV'][use].astype(np.float64),
                        book_legal, leg['ready'][use], config['params'], policy)
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
    if args.compare:
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

    receipt = {'status': 'FA_COMBO_PHASE2', 'prereg': PREREG, 'seed': args.seed,
               'pairing': {'legs_root': str(LR_ROOT), 'f10_root': str(F10_ROOT), 'crossed': bool(crossed)},
               'changes_vs_fresh_combo': ['axis from legs.npz', 'members from isfinite(KING_OOF.P), verified vs panel parity9 + fingerprint',
                                          'training-input drift skipped-and-named for deleted files',
                                          'legs<->F10 binding asserted or deliberately bypassed'],
               'inputs': ident, 'sources': sources, 'policies': summary,
               'member_substitution': memsub, 'unverifiable_provenance': unverifiable, 'legs_f10_binding': binding,
               'member_cells_outside_book_universe': outside, 'G0': g0,
               'B2': (B2INFO if args.const_seat else None), 'B8': B8INFO}
    (out / 'FA_COMBO_RECEIPT.json').write_text(json.dumps(receipt, indent=2, allow_nan=False))
    print("FA_COMBO", json.dumps({"look": (B8INFO or {}).get("look", 900),
                                  "seat_rows_differing_from_look900": (B8INFO or {}).get("ready_anchors_with_seat_differing_from_look900"),
                                  "legs": LR_ROOT.name, "f10": F10_ROOT.name, "crossed": crossed,
                                  "outside": outside, "unverifiable": len(unverifiable),
                                  "G0_arrays_bitwise_equal": (g0 or {}).get("ARRAYS_BITWISE_EQUAL_ALL"),
                                  "G0_container_sha_equal": {k: v["container_sha_equal"] for k, v in (g0 or {}).get("policies", {}).items()}}),
          flush=True)
    if args.compare and not g0["ARRAYS_BITWISE_EQUAL_ALL"]: sys.exit(3)


if __name__ == '__main__':
    main()
