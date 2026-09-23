"""Red/green tests of nc_derive_producer's two guards (lead 2026-09-23, found by news2):
  G-skip: the news2 families skipped are exactly {D11, D13} (an empty skipped set must be refused);
  G-A5:   the §A5 as-of call appears at the three consumers and no old ledger-tail read survives (dropping an A5 edit must be refused).
  G-screen (lead 2026-09-23, news2 ARM_VIABILITY.json): an arm must enable D5 or D6 (empty set included), because only their member-screen
          rewrite defines c7, which the replay's King-block capture reads. The hole is shown to be real: with the guard switched off a D4
          arm builds and its shadow_loop_v3.py stores no c7 (AST); a D5+D4 arm stores it.
Each cell runs the real derive main() into a scratch dir."""
import ast
import importlib.util, sys, os, json, shutil, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
def load():
    spec = importlib.util.spec_from_file_location("ncd", os.path.join(HERE, "nc_derive_producer.py")); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M); return M
def stores_c7(out):
    t = ast.parse(open(os.path.join(out, "shadow_loop_v3.py")).read())
    return any(isinstance(n, ast.Name) and n.id == "c7" and isinstance(n.ctx, ast.Store) for n in ast.walk(t))
def run(mut, release=False, probe=None):
    M = load(); mut(M); d = tempfile.mkdtemp(); out = os.path.join(d, "t")
    sys.argv = ["x", out] + (["--release"] if release else [])
    try:
        M.main()
        return "PASS" + (f" c7_stored={stores_c7(out)}" if probe else "")
    except AssertionError as e:
        return "REFUSED: " + str(e)[:160]
    finally:
        shutil.rmtree(d, ignore_errors=True)
cells = {}
cells["baseline_green"] = run(lambda M: None)
def empty_skip(M):
    M.NEWS2_FAMILIES = {"D4", "D5", "D6", "D7", "D8", "D9", "D11", "D13", "D14"}     # news2 applies D11/D13 itself -> skipped set empty
cells["R_empty_skip_refused"] = run(empty_skip)
def drop_king_a5(M):
    M.SH = [e for e in M.SH if e[0] != "A5+A6:fund_asof_and_base"]
cells["R_drop_king_A5_refused"] = run(drop_king_a5)
def drop_panel_a5(M):
    M.CS = [e for e in M.CS if e[0] != "A5:fund_panel_asof"]
cells["R_drop_panel_A5_refused"] = run(drop_panel_a5)
def drop_ftrim_a5(M):
    M.CS = [e for e in M.CS if e[0] != "A5:ftrim_rn8_asof"]
cells["R_drop_ftrim_A5_refused"] = run(drop_ftrim_a5)
cells["release_default_green"] = run(lambda M: None, release=True)
def arm_trend_all(M):
    M.TREND_ROWS = "all"
cells["arm_trend_all_nonrelease_green"] = run(arm_trend_all)
cells["R_arm_trend_all_release_refused"] = run(arm_trend_all, release=True)
def fams(*f):
    def m(M): M.NEWS2_FAMILIES = set(f)
    return m
cells["R_arm_only_D4_refused"] = run(fams("D4"))
cells["R_arm_only_D4_release_refused"] = run(fams("D4"), release=True)
cells["R_arm_empty_refused"] = run(fams())
for f in ("D7", "D8", "D9", "D14"):
    cells[f"R_arm_only_{f}_refused"] = run(fams(f))
cells["arm_D5_D4_nonrelease_green"] = run(fams("D4", "D5"), probe=True)
cells["arm_only_D6_nonrelease_green"] = run(fams("D6"), probe=True)
def d4_guard_off(M):
    M.NEWS2_FAMILIES = {"D4"}; M.REQUIRE_SCREEN_FAMILY = False
cells["hole_D4_guard_off_builds_without_c7"] = run(d4_guard_off, probe=True)
def m3_undoes_a5(M):     # a later replacement-type edit (after M3) that removes an A5 call must be caught: the check runs after every edit
    M.POST_EDITS = [("fea171/combo_stage.py", "TEST:late_edit", '_fe, _fn, _iv, _r8 = NC.funding_asof(aux["ema"].get(s_), rows_[-1], A)', '_fe, _fn, _iv, _r8 = (np.nan,) * 4')]
cells["R_late_edit_undoing_A5_refused"] = run(m3_undoes_a5)
ok = (cells["baseline_green"] == "PASS" and cells["release_default_green"] == "PASS" and cells["arm_trend_all_nonrelease_green"] == "PASS"
      and cells["arm_D5_D4_nonrelease_green"] == "PASS c7_stored=True" and cells["arm_only_D6_nonrelease_green"] == "PASS c7_stored=True"
      and cells["hole_D4_guard_off_builds_without_c7"] == "PASS c7_stored=False"
      and all(v.startswith("REFUSED") for k, v in cells.items() if k.startswith("R_"))
      and all("D5 or D6" in cells[k] for k in cells if k.startswith("R_arm_") and "release" not in k))
print(json.dumps(cells, indent=1)); print("TEST_NC_DERIVE_GUARDS", "PASS" if ok else "FAIL")
json.dump({"cells": cells, "PASS": ok}, open(os.path.join(HERE, "TEST_NC_DERIVE_GUARDS.json"), "w"), indent=1)
sys.exit(0 if ok else 3)
