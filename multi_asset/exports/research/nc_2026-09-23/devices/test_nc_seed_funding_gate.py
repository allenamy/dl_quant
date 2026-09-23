#!/usr/bin/env python3
"""Red/green test of nc_seed_state.py's funding reconciliation (lead 2026-09-23):
  replay rows the production ledger lacks are COUNTED (not refused), split into inside / outside production's own coverage
  [first production row, axis end]; if the inside count exceeds 1% of the replay rows inside coverage, the tool stops with
  STOP_REPORT_TO_LEAD (receipt written, no state). Production rows the replay lacks are still refused.
Cells (machinery inputs: the fork's synthetic seed pack built from snap/<E> and the production snapshot snap/<E+4h>; each cell runs the
real tool as a subprocess on a throw-away copy):
  B0 baseline green:   unmodified snapshot                                  ⇒ SEEDED, in-coverage missing 0, replay rows in coverage > 0
  T1 under the gate:   drop 0.5% of in-coverage production rows (<= E)      ⇒ SEEDED, in-coverage missing = the dropped rows whose event the
                       replay pack holds (older rows are outside the pack, invisible by construction), names listed
  T2 over the gate:    drop 2% of in-coverage production rows (<= E)        ⇒ exit != 0, STOP_REPORT_TO_LEAD, receipt VERDICT, no generation.json
  T3 still refused:    add a production row <= E the replay does not have  ⇒ exit != 0 (AssertionError: events absent from the replay)
usage: ~/wide_shadow/venv/bin/python test_nc_seed_funding_gate.py <NC tree> <synth seed pack> <snapshot anchor> <work dir>"""
import json, os, random, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__)); HOME = os.path.expanduser("~")
FAILS, N = [], [0]


def check(name, ok, detail=None):
    N[0] += 1
    if not ok: FAILS.append(name)
    print(("  OK   " if ok else "  FAIL ") + name + (("  — " + str(detail)[:300]) if detail is not None else ""), flush=True)


def prod_copy(work, tag, A, mutate=None):
    d = f"{work}/{tag}/prod"; os.makedirs(d)
    for f in ("rolling.npz", "leg_returns_live.json"): os.symlink(f"{HOME}/wide_shadow/state/snap/{A}/{f}", f"{d}/{f}")
    aux = json.load(open(f"{HOME}/wide_shadow/state/snap/{A}/aux.json"))
    info = mutate(aux) if mutate else None
    json.dump(aux, open(f"{d}/aux.json", "w"))
    return d, info


def run(tree, pack, work, tag, A, mutate=None):
    prod, info = prod_copy(work, tag, A, mutate)
    out = f"{work}/{tag}/out"
    r = subprocess.run([sys.executable, f"{HERE}/nc_seed_state.py", tree, pack, prod, out], capture_output=True, text=True)
    rec = json.load(open(f"{out}/SEED_RECEIPT.json")) if os.path.exists(f"{out}/SEED_RECEIPT.json") else {}
    return r, rec, info, out


def in_cov_rows(aux, E):
    """(name, index) of production rows <= E that are not the name's first row (dropping the first row would move the coverage start)."""
    return [(s, i) for s, rows in aux["ledger_tail"].items() for i, r in enumerate(rows) if 0 < i and int(r[0]) <= E]


def replay_times(pack):
    """{name: set of replay settlement times} from the pack (the tool can only see a production gap where the replay has the event)."""
    import numpy as np
    z = np.load(pack); syms = [str(x) for x in z["symbols"]]; off = np.concatenate([[0], np.cumsum(z["f_n"])])
    return {syms[int(j)]: set(int(t) for t in z["f_ft"][off[k]:off[k + 1]]) for k, j in enumerate(z["f_sym"])}


def dropper(frac, E, seed, rep):
    def m(aux):
        cand = in_cov_rows(aux, E); rnd = random.Random(seed); pick = rnd.sample(cand, int(round(frac * len(cand))))
        by = {}
        for s, i in pick: by.setdefault(s, set()).add(i)
        seen = sum(1 for s, i in pick if int(aux["ledger_tail"][s][i][0]) in rep.get(s, ()))
        for s, idx in by.items(): aux["ledger_tail"][s] = [r for i, r in enumerate(aux["ledger_tail"][s]) if i not in idx]
        return {"dropped": len(pick), "dropped_where_replay_has_the_event": seen, "candidates": len(cand)}
    return m


def main():
    tree, pack, A, work = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    assert not os.path.exists(work), "work dir exists"; os.makedirs(work)
    import numpy as np
    E = int(np.load(pack)["axis_end"]); rep = replay_times(pack)
    r, rec, _, out = run(tree, pack, work, "B0", A)
    c = rec.get("counts", {})
    ok0 = r.returncode == 0 and c.get("replay_rows_missing_in_production_in_coverage") == 0 and c.get("replay_rows_in_production_coverage", 0) > 0
    check("B0 baseline green: unmodified snapshot ⇒ SEEDED, 0 in-coverage missing, replay rows in coverage > 0", ok0,
          (r.returncode, {k: c.get(k) for k in ("replay_rows_in_production_coverage", "replay_rows_missing_in_production_in_coverage", "replay_rows_missing_in_production_out_of_coverage")}, r.stderr[-200:]))
    if not ok0: print("baseline not green; stop"); sys.exit(1)
    cov = c["replay_rows_in_production_coverage"]
    r, rec, info, out = run(tree, pack, work, "T1", A, dropper(0.005, E, 1, rep)); c = rec.get("counts", {})
    check("T1 drop 0.5% of in-coverage production rows ⇒ SEEDED, in-coverage missing == dropped rows the replay has, names listed",
          r.returncode == 0 and c.get("replay_rows_missing_in_production_in_coverage") == info["dropped_where_replay_has_the_event"] > 0
          and sum(c.get("replay_rows_missing_in_production_in_coverage_by_name", {}).values()) == info["dropped_where_replay_has_the_event"],
          (r.returncode, info, c.get("replay_rows_missing_in_production_in_coverage"), cov))
    r, rec, info, out = run(tree, pack, work, "T2", A, dropper(0.02, E, 2, rep))
    check("T2 drop 2% ⇒ exit != 0, STOP_REPORT_TO_LEAD, receipt VERDICT, no generation.json",
          r.returncode != 0 and "STOP_REPORT_TO_LEAD" in (r.stderr + r.stdout) and rec.get("VERDICT") == "STOP_REPORT_TO_LEAD" and not os.path.exists(f"{out}/state/generation.json"),
          (r.returncode, info, rec.get("VERDICT"), (r.stderr.strip().splitlines() or [""])[-1][:200]))

    def add_row(aux):
        s = sorted(aux["ledger_tail"])[0]; rows = aux["ledger_tail"][s]
        t = [int(x[0]) for x in rows if int(x[0]) <= E]
        new_t = t[-1] - 1800                     # 30 min before the last row <= E: inside the pack's coverage, a time no settlement has
        aux["ledger_tail"][s] = sorted(rows + [[new_t, 0.0001, 8.0]], key=lambda x: int(x[0]))
        return {"name": s, "ft": new_t}
    r, rec, info, out = run(tree, pack, work, "T3", A, add_row)
    check("T3 production row <= E absent from the replay ⇒ still refused (exit != 0)", r.returncode != 0 and "absent from the replay" in r.stderr,
          (r.returncode, info, (r.stderr.strip().splitlines() or [""])[-1][:200]))
    print(f"\n{N[0] - len(FAILS)}/{N[0]} checks passed")
    if FAILS: print("FAILED:", *FAILS, sep="\n  "); sys.exit(1)
    print("ALL PASS")


if __name__ == "__main__":
    main()
