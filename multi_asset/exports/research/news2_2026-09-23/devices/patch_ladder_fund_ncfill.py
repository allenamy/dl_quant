#!/usr/bin/env python3
"""Add FUND_res_ncfill, because FUND_res is silently degraded and my detector missed it.

MY DETECTOR HAD A BLIND SPOT. The reason-vocabulary detector (compare each arm's refusal reasons with
the two ends; a novel reason = artifact) caught KZ_res / KZWL_res / F10_res / MEM_res. It reported
FUND_res as clean -- no novel reason, and its combo weights contain no NaN or inf at all.

But a direct per-array non-finite census on MEMBER cells in the use window says:
    ZFD  43,233 non-finite member cells over 1,715 anchors   <- MORE anchors than the KZ footprint (1,487)
    RN8     352 non-finite member cells over   275 anchors
    QV        0
So the arm that reported "-0.004739, does not carry" was measured on an input that is missing on 43k
member cells. combo tolerates a non-finite funding rank silently -- it neither refuses the anchor nor
produces a NaN weight -- so nothing in the reason vocabulary could ever have revealed it.

LESSON, recorded in the device so it travels with it: the reason-vocabulary detector is NECESSARY but
NOT SUFFICIENT. It only sees degradation that the consumer complains about. The complete check is a
per-array non-finite census on member cells, run for EVERY arm including the quiet ones.

This arm applies lead's path-2 fill rule to the funding trio so FUND_res can be read on an input that
is not silently missing: ZFD + RN8 + QV from NEW, NC's value wherever NEW's is non-finite.
"""
p = "/dev/shm/pnoise_2026-09-24/devices/pnoise_ladder_combo.py"
s = open(p).read()
n0 = len(s)

s = s.replace(
    '''    elif ARM == "F10_res_ncfill":
        sub("P", nwf["P"], rows_new, ncfill=True)''',
    '''    elif ARM == "F10_res_ncfill":
        sub("P", nwf["P"], rows_new, ncfill=True)
    elif ARM == "FUND_res_ncfill":
        # lead's FUND_res trio, with the path-2 fill rule. FUND_res itself is silently degraded:
        # ZFD is non-finite on 43,233 member cells over 1,715 anchors and combo neither refuses the
        # anchor nor emits NaN, so the reason-vocabulary detector could not see it.
        sub("ZFD", nwl["ZFD"], rows_new, ncfill=True)
        sub("RN8", nwfund["rn8"], rows_new, ncfill=True)
        sub("QV", nwt["qvk"], rows_new, ncfill=True)''',
    1)

s = s.replace('  KZ_res_ncfill / KZWL_res_ncfill / F10_res_ncfill   revision 1: lead\'s path-2 sensitivity (NC fill)',
              '''  KZ_res_ncfill / KZWL_res_ncfill / F10_res_ncfill / FUND_res_ncfill   revision 1: path-2 (NC fill).
            FUND_res_ncfill exists because FUND_res is SILENTLY degraded (ZFD non-finite on 43,233
            member cells / 1,715 anchors) and the reason-vocabulary detector cannot see silent
            degradation -- it only sees what the consumer complains about.''', 1)

open(p, "w").write(s)
print("patched:", "FUND_res_ncfill" in s, "bytes", n0, "->", len(s))
