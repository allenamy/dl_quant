#!/usr/bin/env python3
"""Wire NEW's real rn8 / qv / members / legal sources into the ladder driver.

The positive control refused with KeyError 'RN8 is not a file in the archive'. That refusal is the
finding, not a bug: NEW's f10v2_legs.npz holds only E_ts/symbols/KZ/Z24/ZFD/WL/ready/LR/
seat_priced_fraction. The researcher's own call site is continuous_combo.py:78, and the loads that
feed it are continuous_combo.py:49 (paths) and :61 (handles):

    paths = [data/dlw_targets.npz, data/f10v2_legs.npz, data/LEGS_RECEIPT.json,
             data/funding_state.npz, BUILD_RECEIPT.json, f10_s42/F10_OOF.npz, ...]
    t=np.load(paths[0]); leg=np.load(paths[1]); fund=np.load(paths[3]); score=np.load(paths[5])
    book_legal = align_universe(a,syms,universe) & fund['legal'][use]          # :69
    evolve(a, leg['KZ'], score['P'], leg['ZFD'], leg['WL'], fund['rn8'],
           list(t['members']), t['qvk'], book_legal, leg['ready'], params, policy)   # :78

So four of evolve's arguments come from files OUTSIDE the legs npz: rn8 and legal from
funding_state.npz, qv and members from dlw_targets.npz. Read off the consuming line, not off names.

MEASURED, not assumed:
  * dlw_targets / f10v2_legs / funding_state / F10_OOF all share one E_ts axis (asserted below too).
  * NEW axis = NC axis restricted to [1641168000, 1789776000], bitwise; the 12 NC anchors NEW lacks
    are 2022-01-01/02, i.e. BEFORE use>=1672531200 -> the evolve state path is identical. No gap.
  * config params byte-identical (3a8422f3...), so params are not a ladder input.
  * legal DIFFERS: NC 2822237 True cells vs NEW 2916291, 94054 disagreeing cells over 1628/8143
    anchors. legal and members are therefore NEW-vs-NC input differences that NONE of lead's five
    single-swap arms covers (lead's FUND_res is written as ZFD+ready+QV+RN8). Lead's arm list is
    copied verbatim and is NOT edited here; the coverage hole is reported to lead instead.
"""
p = "/dev/shm/pnoise_2026-09-24/devices/pnoise_ladder_combo.py"
s = open(p).read()
n_before = len(s)

s = s.replace(
    '    ap.add_argument("--new-f10", required=True)',
    '    ap.add_argument("--new-f10", required=True)\n'
    '    ap.add_argument("--new-funding", required=True,\n'
    '                    help="funding_state.npz -- NEW\'s rn8 AND legal live here (continuous_combo.py:69,78)")\n'
    '    ap.add_argument("--new-targets", required=True,\n'
    '                    help="dlw_targets.npz -- NEW\'s qvk and members live here (continuous_combo.py:78)")',
    1)

s = s.replace(
    '                       ("new_f10", a.new_f10), ("mask", a.mask), ("crypto_axis", a.crypto_axis))}}',
    '                       ("new_f10", a.new_f10), ("new_funding", a.new_funding),\n'
    '                       ("new_targets", a.new_targets),\n'
    '                       ("mask", a.mask), ("crypto_axis", a.crypto_axis))}}\n'
    '    rec["new_input_provenance"] = {\n'
    '        "read_off": "continuous_combo.py:49 (paths), :61 (handles), :69 (book_legal), :78 (evolve call)",\n'
    '        "KZ/ZFD/WL/ready": "data/f10v2_legs.npz",\n'
    '        "P": "f10_s42/F10_OOF.npz",\n'
    '        "rn8": "data/funding_state.npz[rn8]",\n'
    '        "legal": "data/funding_state.npz[legal]  -- NEW book_legal = align_universe & fund[legal]",\n'
    '        "qv": "data/dlw_targets.npz[qvk]",\n'
    '        "members": "data/dlw_targets.npz[members]",\n'
    '        "not_in_the_legs_file": ["rn8", "legal", "qv", "members"],\n'
    '        "caliber_note": ("NC book_legal = align_universe & tradable_mask & crypto (production); NEW = "\n'
    '                         "align_universe & funding_state[legal]. legal and members are NEW-vs-NC input "\n'
    '                         "differences that none of lead\'s five single-swap arms covers; lead\'s arm list "\n'
    '                         "is not edited here, the coverage hole is reported to lead.")}',
    1)

s = s.replace(
    '    nwf = np.load(a.new_f10, allow_pickle=False)',
    '    nwf = np.load(a.new_f10, allow_pickle=False)\n'
    '    nwfund = np.load(a.new_funding, allow_pickle=False)\n'
    '    nwt = np.load(a.new_targets, allow_pickle=True)',
    1)

# One NEW axis for all four NEW files -- asserted, never assumed (the researcher asserts the same at :62).
s = s.replace(
    '    rows_newf = np.array([newf_pos.get(int(t), -1) for t in anchors])',
    '    rows_newf = np.array([newf_pos.get(int(t), -1) for t in anchors])\n'
    '    for _nm, _z in (("new_funding", nwfund), ("new_targets", nwt), ("new_f10", nwf)):\n'
    '        assert np.array_equal(_z["E_ts"].astype(np.int64), nwl["E_ts"].astype(np.int64)), \\\n'
    '            ("NEW files not on one anchor axis", _nm)\n'
    '        assert np.array_equal(_z["symbols"], syms), ("NEW symbol axis differs", _nm)\n'
    '    assert np.array_equal(rows_newf, rows_new), "NEW F10 axis must equal NEW legs axis"',
    1)

# FUND_res: lead's definition verbatim = ZFD + ready + QV + RN8. legal is NOT in it.
s = s.replace(
    '''    elif ARM == "FUND_res":
        for nm in ("ZFD", "RN8", "QV"):
            sub(nm, nwl[nm], rows_new)''',
    '''    elif ARM == "FUND_res":
        # lead's arm is written "FUND_res(ZFD+ready+QV+RN8)" -- copied verbatim, legal deliberately NOT here
        sub("ZFD", nwl["ZFD"], rows_new)
        sub("RN8", nwfund["rn8"], rows_new)
        sub("QV", nwt["qvk"], rows_new)''',
    1)

s = s.replace(
    '''    elif ARM == "all_new":
        for nm in ("KZ", "ZFD", "WL", "RN8", "QV"):
            sub(nm, nwl[nm], rows_new)
        sub("P", nwf["P"], rows_newf)''',
    '''    elif ARM == "all_new":
        for nm in ("KZ", "ZFD", "WL"):
            sub(nm, nwl[nm], rows_new)
        sub("RN8", nwfund["rn8"], rows_new)
        sub("QV", nwt["qvk"], rows_new)
        sub("P", nwf["P"], rows_new)
        # members and legal too: "全部数组换成 NEW 的" means both ends of the ladder really are NC and NEW
        nm_new = list(nwt["members"]); n_sw = 0
        for i in range(len(anchors)):
            if rows_new[i] >= 0:
                members[i] = np.asarray(nm_new[rows_new[i]], np.int64); n_sw += 1
        swapped.append("members"); kept_nc["members"] = int(len(anchors) - n_sw)
        NEW_LEGAL[0] = True''',
    1)

# legal is consumed where book_legal is built, after the arm switch -> a flag carries the arm's intent
s = s.replace(
    '    swapped, kept_nc = [], {}',
    '    swapped, kept_nc, NEW_LEGAL = [], {}, [False]',
    1)

s = s.replace(
    '    cand = mk["mask"] & crypto[None, :]',
    '''    cand = mk["mask"] & crypto[None, :]
    rec["legal_source"] = "NC: align_universe & tradable_mask & crypto"
    if NEW_LEGAL[0]:
        nwlegal = np.asarray(nwfund["legal"], bool)
        c2 = cand.copy(); ok = rows_new >= 0
        c2[ok] = nwlegal[rows_new[ok]]
        rec["legal_swap"] = {"nc_true_cells": int(cand.sum()), "new_true_cells": int(c2.sum()),
                             "disagreeing_cells": int((cand != c2).sum()),
                             "anchors_with_any_disagreement": int((cand != c2).any(1).sum())}
        cand = c2
        swapped.append("legal(funding_state)"); kept_nc["legal"] = int((~ok).sum())
        rec["legal_source"] = "NEW: align_universe & funding_state[legal]"''',
    1)

open(p, "w").write(s)
ok = all(k in s for k in ('new_funding', 'nwt["qvk"]', 'new_input_provenance', 'NEW_LEGAL[0] = True',
                          'legal_swap', 'not_in_the_legs_file'))
print("patched:", ok, "bytes", n_before, "->", len(s))
