"""Build the single-family test arms of nc_derive_producer.py with the screen-family guard OFF (arm viability test only; lead 2026-09-23).
usage: python nc_build_arms.py <out root> name=FAMS ...   (FAMS comma list; empty = base)"""
import importlib.util, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
root = sys.argv[1]
for spec_ in sys.argv[2:]:
    name, fams = spec_.split("=", 1)
    spec = importlib.util.spec_from_file_location(f"ncd_{name}", os.path.join(HERE, "nc_derive_producer.py")); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    M.NEWS2_FAMILIES = {f for f in fams.split(",") if f}; M.REQUIRE_SCREEN_FAMILY = False
    sys.argv = ["x", os.path.join(root, name)]
    M.main(); print("BUILT", name, sorted(M.NEWS2_FAMILIES), flush=True)
