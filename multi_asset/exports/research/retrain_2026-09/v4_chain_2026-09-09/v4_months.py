"""v4_months.py — the fold-month set of the v4 monthly chain is DERIVED from the targets axis or DECLARED by the month env; never hand-written.

Why (RUNBOOK_monthly_retrain_2026-10 §0★ 修訂 2 (a); independent review 0dfc0d87 R2, 2026-09-12): the September trainer
(pod_f10_train_monthly_v4.py L298) and merge (merge_mwf_v4b.py L13) carried `ALL_MONTHS = 202501..202608` as a source constant and the
GPU chains carried four hand-written shard lists SH0..SH3. A month past the constant (202609) was refused by the trainer, silently
absent from the merge, and never dispatched by any shard — the October retrain could not be executed without editing three programs.

Rules (all asserted, all testable without torch):
  · MONTHS_ALL default = every COMPLETE calendar month from FIRST_MONTH (202501) through the last complete month on the anchor axis.
    A month is complete iff the axis holds every one of its 4h anchors (days*6 on the regular grid the trainer asserts); the month
    containing the last anchor is complete iff last_anchor + 4h == the next month's first anchor.
  · A declared MONTHS_ALL (env, comma list of YYYYMM) must be a subset of the derivable set: a month beyond the data's last complete
    month is refused (the data cannot label it), and so is a malformed, duplicated or unsorted list.
  · MONTHS (one shard's folds) must be a subset of MONTHS_ALL.
  · Shards = round-robin over MONTHS_ALL (k, k+n, k+2n, ...). For the September constant this reproduces the hand-written
    SH0..SH3 bit for bit (tests_pipeline_gates.py [N]).

CLI:
  python v4_months.py derive <dlw_targets.npz>                 -> prints the derived MONTHS_ALL csv (rc 0) or an error (rc 3)
  python v4_months.py check  <dlw_targets.npz> <MONTHS_ALL csv> -> rc 0 iff the declared set is admissible for that axis, else 3
  python v4_months.py shards <MONTHS_ALL csv> [n=4]             -> prints SH0=..., SH1=..., ... (one line per shard)
"""
import calendar
import sys
import time

FIRST_MONTH = 202501
N_SHARDS = 4
ANCHOR_STEP = 14400
# the constant the September trainer / merge hard-coded — kept ONLY so the bit-identity test can name it; nothing derives from it
LEGACY_MONTHS_ALL_2026_09 = [202501 + k for k in range(12)] + [202601 + k for k in range(8)]
LEGACY_SHARDS_2026_09 = ["202501,202505,202509,202601,202605", "202502,202506,202510,202602,202606",
                         "202503,202507,202511,202603,202607", "202504,202508,202512,202604,202608"]


def ym_of(ts):
    g = time.gmtime(int(ts))
    return g.tm_year * 100 + g.tm_mon


def next_ym(ym):
    y, m = divmod(int(ym), 100)
    return (y + 1) * 100 + 1 if m == 12 else ym + 1


def month_start_ts(ym):
    y, m = divmod(int(ym), 100)
    return calendar.timegm((y, m, 1, 0, 0, 0))


def is_ym(x):
    try:
        x = int(x)
    except (TypeError, ValueError):
        return False
    return 200001 <= x <= 209912 and 1 <= x % 100 <= 12


def parse_months(s):
    """'202501,202502' -> [202501, 202502]; refuses anything that is not a strictly ascending list of YYYYMM."""
    if s is None or str(s).strip() == "":
        raise ValueError("empty month list")
    out = []
    for tok in str(s).split(","):
        tok = tok.strip()
        if not tok:
            continue
        if not is_ym(tok):
            raise ValueError(f"not a YYYYMM month: {tok!r}")
        out.append(int(tok))
    if not out:
        raise ValueError("empty month list")
    if any(b <= a for a, b in zip(out, out[1:])):
        raise ValueError(f"month list must be strictly ascending without duplicates: {out}")
    return out


def months_all_from_axis(E_ts, first=FIRST_MONTH, step=ANCHOR_STEP):
    """Complete calendar months from `first` through the last complete month on the anchor axis (see module doc)."""
    E = [int(t) for t in E_ts]
    if len(E) < 2:
        raise ValueError("axis too short")
    last = E[-1]
    ym_last = ym_of(last)
    last_complete = ym_last if last + step == month_start_ts(next_ym(ym_last)) else _prev_ym(ym_last)
    if last_complete < first:
        raise ValueError(f"no complete month >= {first} on the axis (last anchor {iso(last)})")
    counts = {}
    for t in E:
        y = ym_of(t)
        counts[y] = counts.get(y, 0) + 1
    months, ym = [], first
    while ym <= last_complete:
        y, m = divmod(ym, 100)
        need = calendar.monthrange(y, m)[1] * (86400 // step)
        if counts.get(ym, 0) != need:
            raise ValueError(f"month {ym} is not complete on the axis: {counts.get(ym, 0)} anchors, expected {need}")
        months.append(ym)
        ym = next_ym(ym)
    return months


def _prev_ym(ym):
    y, m = divmod(int(ym), 100)
    return (y - 1) * 100 + 12 if m == 1 else ym - 1


def months_all(declared, E_ts, first=FIRST_MONTH, step=ANCHOR_STEP):
    """MONTHS_ALL: the declared csv (env) when given, else derived. A declared month that is not derivable from the axis is refused."""
    derived = months_all_from_axis(E_ts, first=first, step=step)
    if declared is None or str(declared).strip() == "":
        return derived
    dec = parse_months(declared)
    beyond = [m for m in dec if m not in derived]
    if beyond:
        raise ValueError(f"declared MONTHS_ALL contains month(s) {beyond} that are not complete on the data axis "
                         f"(derivable set {derived[0]}..{derived[-1]}): the data cannot label them")
    return dec


def check_subset(months, months_all_list):
    bad = [m for m in months if m not in months_all_list]
    if bad:
        raise ValueError(f"MONTHS {bad} not in MONTHS_ALL {months_all_list}")
    return True


def shards(months_all_list, n=N_SHARDS):
    """Round-robin shard lists as csv strings: shard k = months_all[k::n]."""
    if n < 1:
        raise ValueError("n shards must be >= 1")
    return [",".join(str(m) for m in months_all_list[k::n]) for k in range(n)]


def iso(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(ts)))


def last_anchor_utc(ts_values):
    """ISO of the largest timestamp in `ts_values` (the last anchor of a training subset)."""
    return iso(max(int(t) for t in ts_values))


def _load_axis(path):
    import numpy as np
    return np.load(path, allow_pickle=True)["E_ts"].astype("int64")


def main(argv):
    if len(argv) >= 3 and argv[1] == "derive":
        try:
            print(",".join(str(m) for m in months_all_from_axis(_load_axis(argv[2]))))
        except Exception as e:                            # noqa: BLE001
            print(f"MONTHS_DERIVE_FAIL {type(e).__name__}: {e}")
            return 3
        return 0
    if len(argv) >= 4 and argv[1] == "check":
        try:
            dec = months_all(argv[3], _load_axis(argv[2]))
        except Exception as e:                            # noqa: BLE001
            print(f"MONTHS_CHECK_FAIL {type(e).__name__}: {e}")
            return 3
        print(f"MONTHS_CHECK_OK {dec[0]}..{dec[-1]} n={len(dec)}")
        return 0
    if len(argv) >= 3 and argv[1] == "shards":
        n = int(argv[3]) if len(argv) > 3 else N_SHARDS
        try:
            for k, s in enumerate(shards(parse_months(argv[2]), n)):
                print(f"SH{k}={s}")
        except Exception as e:                            # noqa: BLE001
            print(f"MONTHS_SHARDS_FAIL {type(e).__name__}: {e}")
            return 3
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
