"""Red/green tests of nc_derive_producer's two guards (lead 2026-09-23, found by news2):
  G-skip: the news2 families skipped are exactly {D11, D13} (an empty skipped set must be refused);
  G-A5:   the §A5 as-of call appears at the three consumers and no old ledger-tail read survives (dropping an A5 edit must be refused).
Each cell runs the real derive main() into a scratch dir."""
import importlib.util, sys, os, json, shutil, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
def load():
    spec = importlib.util.spec_from_file_location("ncd", os.path.join(HERE, "nc_derive_producer.py")); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M); return M
def run(mut):
    M = load(); mut(M); d = tempfile.mkdtemp(); out = os.path.join(d, "t")
    sys.argv = ["x", out]
    try:
        M.main(); return "PASS"
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
ok = cells["baseline_green"] == "PASS" and all(v.startswith("REFUSED") for k, v in cells.items() if k.startswith("R_"))
print(json.dumps(cells, indent=1)); print("TEST_NC_DERIVE_GUARDS", "PASS" if ok else "FAIL")
json.dump({"cells": cells, "PASS": ok}, open(os.path.join(HERE, "TEST_NC_DERIVE_GUARDS.json"), "w"), indent=1)
sys.exit(0 if ok else 3)
