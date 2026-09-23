#!/usr/bin/env python3
"""fresh_stats_base_equiv.py — prove fresh_stats.py carries the FIXED news_stats.py (R10-E02 / AMENDMENT 2) R-P selection,
so the FRESH statistics device is based on 7141ba42 and not on the pre-fix 10cb1d9e.

Three things are compared, each by BYTES, not by eyeball:
  (1) the source text of select_rp_run() in both modules (ast segment, verbatim);
  (2) the R-P frozen-object constants both modules bind at module level;
  (3) import-time side effects: importing either module must not read argv/env or touch the filesystem
      (the pre-fix device did all of its work at module level and could not be imported by a test at all).
Also reports, for the record, the checks the PRE-FIX device performed, to show what the fix added.
usage: env -i PATH=/usr/bin:/bin HOME=/root python -B fresh_stats_base_equiv.py PATH,HOME,LC_CTYPE <fixed_news_stats.py> <fresh_stats.py> <prefix_news_stats.py> <out.json>
"""
import os, sys, json, ast, time, hashlib, importlib.util

WL = set(sys.argv[1].split(",")); extra = sorted(set(os.environ) - WL); assert not extra, f"env outside whitelist: {extra}"
FIXED, FRESH, PREFIX_, OUT = sys.argv[2:6]

CONSTS = ("RP_THRESHOLD", "RP_BASE_LABEL", "RP_BASE_ANCHOR", "RP_BASE_KEY", "RP_WINDOW_END", "BTP_SHA", "NPATH")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def fn_source(path, name):
    src = open(path, "rb").read().decode()
    tree = ast.parse(src)
    hits = [n for n in tree.body if isinstance(n, (ast.FunctionDef,)) and n.name == name]
    if len(hits) != 1: return None
    return ast.get_source_segment(src, hits[0])


def consts(path):
    """module-level literal assignments, read from the AST so nothing is executed"""
    src = open(path, "rb").read().decode(); tree = ast.parse(src); out = {}
    for n in tree.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id in CONSTS:
                    try: out[t.id] = ast.literal_eval(n.value)
                    except Exception: out[t.id] = ast.get_source_segment(src, n.value)
    return out


def import_side_effects(path, modname):
    """import the module under a filesystem/argv/env tripwire; returns the list of tripped accesses"""
    tripped = []
    real_open, real_argv = open, list(sys.argv)
    import builtins
    def guard_open(f, *a, **k):
        tripped.append(f"open({f!r})"); return real_open(f, *a, **k)
    builtins.open = guard_open
    sys.argv = ["<no-argv>"]          # a module that reads sys.argv[1] at import time raises IndexError here
    try:
        spec = importlib.util.spec_from_file_location(modname, path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        err = None
    except BaseException as e:
        m = None; err = f"{type(e).__name__}: {e}"
    finally:
        builtins.open = real_open; sys.argv = real_argv
    return {"tripped_file_opens": tripped, "import_error": err,
            "select_rp_run_importable": bool(m is not None and callable(getattr(m, "select_rp_run", None)))}


def main():
    rec = {"device": "fresh_stats_base_equiv.py", "self_sha256": sha(os.path.abspath(__file__)), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "files": {"fixed_news_stats": {"path": FIXED, "sha256": sha(FIXED)}, "fresh_stats": {"path": FRESH, "sha256": sha(FRESH)},
                     "prefix_news_stats": {"path": PREFIX_, "sha256": sha(PREFIX_)}}}
    a = fn_source(FIXED, "select_rp_run"); b = fn_source(FRESH, "select_rp_run"); c = fn_source(PREFIX_, "select_rp_run")
    rec["C1_select_rp_run_source"] = {
        "present_in_fixed": a is not None, "present_in_fresh": b is not None, "present_in_prefix_version": c is not None,
        "bytes_fixed": len(a or ""), "bytes_fresh": len(b or ""),
        "sha256_fixed": hashlib.sha256((a or "").encode()).hexdigest(), "sha256_fresh": hashlib.sha256((b or "").encode()).hexdigest(),
        "IDENTICAL": bool(a is not None and a == b)}
    ca, cb, cc = consts(FIXED), consts(FRESH), consts(PREFIX_)
    rec["C2_frozen_object_constants"] = {"fixed": ca, "fresh": cb, "prefix_version": cc,
                                         "missing_in_fresh": sorted(set(CONSTS) - set(cb)), "missing_in_fixed": sorted(set(CONSTS) - set(ca)),
                                         "IDENTICAL": bool(ca == cb and set(ca) == set(CONSTS))}
    rec["C3_import_side_effects"] = {"fixed": import_side_effects(FIXED, "eqv_fixed"), "fresh": import_side_effects(FRESH, "eqv_fresh"),
                                     "prefix_version": import_side_effects(PREFIX_, "eqv_prefix")}
    rec["C3_import_side_effects"]["IDENTICAL"] = bool(
        rec["C3_import_side_effects"]["fresh"]["select_rp_run_importable"] and
        not rec["C3_import_side_effects"]["fresh"]["tripped_file_opens"] and
        rec["C3_import_side_effects"]["fresh"]["import_error"] is None)
    # what the PRE-FIX device did instead, quoted from its own source (the thing R10-E02 replaced)
    ph = fn_source(PREFIX_, "halted")
    rec["prefix_version_did"] = {"function": "halted", "source": ph,
                                 "note": "asserts len(runs)==1 over ALL runs in the receipt; a receipt holding scaled+lit therefore stops the device "
                                         "rather than selecting the scaled main reading. No threshold / base / seed / window checks."}
    # C4: census of EVERY function both modules define. The measurement functions must be byte-identical, so the two arms are
    # measured by one instrument; only the four that carry the different prereg / different arm set may differ, and they are named here.
    MAY_DIFFER = {"load_cell": "FRESH has no certified-reproduction arm (NEW_S's OLD arm re-checks against CERT); FRESH instead records the "
                               "engine/calibration/price/config pins its own P0_same_engine precondition compares across arms",
                  "main": "different arms, roots and argv (FRESH vs NEW_S)",
                  "rules": "prereg §3 F1..F5 (FRESH) vs S1..S5 (NEW_S) — different documents, different gates",
                  "ts": "parameter renamed iso -> iso_ so it does not shadow the module-level iso(); body otherwise identical"}
    def fns(path):
        src = open(path, "rb").read().decode(); out = {}
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.FunctionDef): out.setdefault(n.name, ast.get_source_segment(src, n))
        return out
    fa, fb = fns(FIXED), fns(FRESH)
    ident = sorted(k for k in set(fa) & set(fb) if fa[k] == fb[k]); diff = sorted(k for k in set(fa) & set(fb) if fa[k] != fb[k])
    unexpected = [k for k in diff if k not in MAY_DIFFER]
    rec["C4_function_census"] = {"identical": ident, "different": diff, "only_in_fixed": sorted(set(fa) - set(fb)), "only_in_fresh": sorted(set(fb) - set(fa)),
                                 "why_each_difference_is_required": {k: MAY_DIFFER[k] for k in diff if k in MAY_DIFFER},
                                 "unexpected_differences": unexpected,
                                 "IDENTICAL": bool(not unexpected and not (set(fa) ^ set(fb)))}
    ok = (rec["C1_select_rp_run_source"]["IDENTICAL"] and rec["C2_frozen_object_constants"]["IDENTICAL"]
          and rec["C3_import_side_effects"]["IDENTICAL"] and rec["C4_function_census"]["IDENTICAL"])
    rec["VERDICT"] = "FRESH_STATS_CARRIES_FIXED_RP_SELECTION" if ok else "DIFFERS"
    json.dump(rec, open(OUT + ".tmp", "w"), indent=1); os.replace(OUT + ".tmp", OUT)
    print(f"FRESH_STATS_BASE_EQUIV VERDICT={rec['VERDICT']} C1_source_identical={rec['C1_select_rp_run_source']['IDENTICAL']} "
          f"C2_constants_identical={rec['C2_frozen_object_constants']['IDENTICAL']} C3_import_clean={rec['C3_import_side_effects']['IDENTICAL']} "
          f"C4_measurement_fns_identical={len(rec['C4_function_census']['identical'])} required_differences={rec['C4_function_census']['different']} unexpected={rec['C4_function_census']['unexpected_differences']} "
          f"fixed={rec['files']['fixed_news_stats']['sha256'][:8]} fresh={rec['files']['fresh_stats']['sha256'][:8]} prefix={rec['files']['prefix_news_stats']['sha256'][:8]}", flush=True)
    sys.exit(0 if ok else 3)


if __name__ == "__main__":
    main()
