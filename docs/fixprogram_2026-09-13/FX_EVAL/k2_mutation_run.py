#!/usr/bin/env python3
"""k2_mutation_run.py — FIXPROGRAM 2026-09-13 item K2: do the module-mode tests have teeth? Each mutant is one exact text substitution in a
COPY of equivalence_labels.py or k2_rules.py placed with a copy of the test file in a scratch directory (the committed files are never
touched). A mutant is KILLED when the test run exits non-zero; a SURVIVOR names a missing test. A control copy with no substitution must
pass. Usage: python3 k2_mutation_run.py <scratch_dir>
"""
import os, sys, shutil, subprocess, json, hashlib, time
REPO = "/Users/haosiyu/Desktop/quant_research"
MOD = REPO + "/multi_asset/exports/research/common/equivalence_labels.py"; TST = REPO + "/multi_asset/exports/research/common/tests_equivalence_labels.py"
RUL = REPO + "/docs/fixprogram_2026-09-13/FX_EVAL/k2_rules.py"
MUTANTS = [
    ("M-a_equivalence_closed_boundary", MOD, "if -d < ci.lo and ci.hi < d: label = EQUIVALENT", "if -d <= ci.lo and ci.hi <= d: label = EQUIVALENT"),
    ("M-b_equivalence_ignores_lo", MOD, "if -d < ci.lo and ci.hi < d: label = EQUIVALENT", "if ci.hi < d: label = EQUIVALENT"),
    ("M-c_not_equivalent_against_zero", MOD, "elif ci.lo >= d or ci.hi <= -d: label = NOT_EQUIVALENT", "elif ci.lo > 0 or ci.hi < 0: label = NOT_EQUIVALENT"),
    ("M-d_one_sided_upper_reads_point", MOD, "label = WITHIN_MARGIN if ci.hi < line else", "label = WITHIN_MARGIN if ci.point < line else"),
    ("M-e_aggregate_takes_first_member", MOD, "label = labels[0] if len(set(labels)) == 1 else INCONCLUSIVE", "label = labels[0]"),
    ("M-f_shared_loss_ignores_sign", MOD, "lost_d, lost_r = all(dep), all(rep)", "lost_d, lost_r = True, True"),
    ("M-g_direction_drops_point_condition", MOD, "if all(c.point > 0 and c.lo > 0 for c in cells): return \"(A)\"", "if all(c.lo > 0 for c in cells): return \"(A)\""),
    ("M-h_short_justification_accepted", MOD, "MIN_JUSTIFICATION_CHARS = 20", "MIN_JUSTIFICATION_CHARS = 1"),
    ("M-i_interval_level_defaults", MOD, "    level: float\n", "    level: float = 0.95\n"),
    ("M-j_equivalence_overrides_direction", MOD, "label=(d if d != \"(C)\" else \"(C) \" + eq[\"label\"])", "label=(\"(C) EQUIVALENT\" if eq[\"label\"] == EQUIVALENT else (d if d != \"(C)\" else \"(C) \" + eq[\"label\"]))"),
    ("M-k_loss_guard_always_true", MOD, "try: return len(means) > 0 and all(_finite(\"mean\", m) < 0.0 for m in means)", "try: return True"),
    ("R-a_t4_material_needs_both_legs", RUL, "elif b[\"label\"] == EL.NOT_EQUIVALENT or i[\"label\"] == EL.NOT_EQUIVALENT:", "elif b[\"label\"] == EL.NOT_EQUIVALENT and i[\"label\"] == EL.NOT_EQUIVALENT:"),
    ("R-b_t1h1_band_from_point_not_least_extreme_drop", RUL, "m = EL.Margin(delta=fraction * abs(D[2]),", "m = EL.Margin(delta=fraction * abs(D[0]),"),
    ("R-c_t8_usefulness_k0_only", RUL, "excluded.append(r0 == EL.WITHIN_MARGIN and r9 == EL.WITHIN_MARGIN)", "excluded.append(r0 == EL.WITHIN_MARGIN)"),
    ("R-d_t5b_absent_reads_below_line", RUL, "if mean is None or ci is None or any(x is None for x in ci): return \"NOT RE-LABELLABLE (statistic absent)\"",
     "if mean is None or ci is None or any(x is None for x in ci): return \"NOT MATERIAL (established below line)\""),
    ("R-e_t1h5_band_from_reference_point", RUL, "return None if (ref[1] <= 0 <= ref[2]) else fraction * min(abs(ref[1]), abs(ref[2]))", "return fraction * abs(ref[0])"),
    ("R-f_t5addendum_not_negligible_single_seed", RUL, "if all(v.lo >= not_negligible_line or v.hi <= -not_negligible_line for v in ivs):", "if any(v.lo >= not_negligible_line or v.hi <= -not_negligible_line for v in ivs):"),
]


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def run_case(root, name, target=None, old=None, new=None):
    d = os.path.join(root, name); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    shutil.copy(TST, d); shutil.copy(MOD, d); shutil.copy(RUL, d)
    if target is not None:
        p = os.path.join(d, os.path.basename(target)); s = open(p).read()
        assert s.count(old) == 1, (name, "substitution anchor count", s.count(old)); open(p, "w").write(s.replace(old, new))
    r = subprocess.run([sys.executable, "-B", os.path.join(d, "tests_equivalence_labels.py"), "--impl", "module"], capture_output=True, text=True, cwd=d)
    lines = r.stdout.strip().split("\n"); summ = next((l for l in lines if l.startswith("SUMMARY")), "NO SUMMARY LINE")
    failing = [l.split()[1] for l in lines if l.startswith("FAIL ") or l.startswith("ERROR ")]
    return dict(name=name, rc=r.returncode, summary=summ, failing=failing, stderr_tail=r.stderr.strip()[-300:])


def main():
    root = sys.argv[1]; os.makedirs(root, exist_ok=True)
    out = dict(tool="k2_mutation_run.py", utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), inputs={MOD: sha(MOD), TST: sha(TST), RUL: sha(RUL)})
    ctl = run_case(root, "CONTROL_no_mutation"); out["control"] = ctl
    res = [run_case(root, n, t, o, w) for n, t, o, w in MUTANTS]; out["mutants"] = res
    killed = [x for x in res if x["rc"] != 0]; surv = [x for x in res if x["rc"] == 0]
    for x in [ctl] + res: print("%-52s rc=%d %s | failing: %s" % (x["name"], x["rc"], x["summary"], ",".join(x["failing"][:6])))
    out.update(killed=len(killed), survivors=[x["name"] for x in surv], control_pass=(ctl["rc"] == 0))
    json.dump(out, open(os.path.join(root, "MUTATION_RESULT.json"), "w"), indent=1)
    print("SUMMARY k2_mutation_run control_pass=%s mutants=%d killed=%d survivors=%s" % (ctl["rc"] == 0, len(res), len(killed), [x["name"] for x in surv]))
    sys.exit(0 if ctl["rc"] == 0 and not surv else 1)


if __name__ == "__main__":
    main()
