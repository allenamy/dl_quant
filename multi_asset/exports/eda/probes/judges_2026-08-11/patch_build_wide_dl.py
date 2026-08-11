"""Wire assert_funding_dim.py into build_wide_dl.py as a HARD GATE (non-zero exit breaks the build)."""
import shutil, sys

P = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset/data/build_wide_dl.py"

OLD = '''    print(f"[wide_dl] T={T} N={N} C={CH.shape[2]} chans -> {outpath}", flush=True)
    print(f"  channels: {ch_names}", flush=True)'''

NEW = '''    print(f"[wide_dl] T={T} N={N} C={CH.shape[2]} chans -> {outpath}", flush=True)
    print(f"  channels: {ch_names}", flush=True)

    # ---- HARD GATE: funding settlement-interval dimension regression check ----
    # funding_ema stores a per-settlement rate; 4h- and 8h-settled coins coexist, and the engine
    # rank-centres the funding cross-section. Rank-centring removes individual scale but NOT a
    # group-level shift, so an un-normalised rate silently biases the 4h cohort to one side --
    # and xsr_fund (derived here from funding_ema) carries the identical artifact. "Fixing the
    # source fixes the derived channel" is an assumption about this build graph, so it is CHECKED,
    # not trusted. Non-zero exit deliberately breaks the build.
    import subprocess
    rc = subprocess.call([_sys.executable,
                          _p.join(_p.dirname(_p.dirname(_p.abspath(__file__))),
                                  "exports", "eda", "assert_funding_dim.py"),
                          "--panel", outpath])
    if rc != 0:
        raise SystemExit(f"[wide_dl] FUNDING DIMENSION GATE FAILED (exit {rc}) on {outpath} — "
                         "panel NOT fit for use. See exports/eda/assert_funding_dim_result.json; "
                         "fix is rate*(8/interval_h_of_that_row) BEFORE the EMA in "
                         "data/build_wide_panel.py.")
    print("[wide_dl] funding-dimension gate PASSED", flush=True)'''


def main():
    s = open(P).read()
    if "FUNDING DIMENSION GATE" in s:
        print("already patched; nothing to do")
        return 0
    if s.count(OLD) != 1:
        print(f"FAIL: anchor found {s.count(OLD)} times, expected 1")
        return 1
    shutil.copy(P, P + ".bak_pregate")
    s = s.replace(OLD, NEW)
    # the gate needs `sys` and `os.path`; the module imports them under underscore aliases
    s = s.replace("import os.path as _p\nimport sys as _sys",
                  "import os.path as _p\nimport sys as _sys")
    open(P, "w").write(s)
    print("patched build_wide_dl.py (backup: .bak_pregate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
