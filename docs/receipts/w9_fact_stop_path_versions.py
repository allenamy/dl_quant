"""W9 fact F-VERSIONS: hash each piece of the per-name-stop code path in every executor version since the stop went live.
Reads git objects of ~/dl_quant_live (read-only: git log / git show). Prints one row per version."""
import ast, hashlib, subprocess, sys
REPO = "/Users/haosiyu/dl_quant_live"
def sh(*a): return subprocess.check_output(["git", "-C", REPO, *a]).decode()
def show(rev, path):
    try: return sh("show", f"{rev}:{path}")
    except subprocess.CalledProcessError: return None
def func_src(src, name):
    if src is None: return None
    t = ast.parse(src)
    for n in t.body:
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return ast.get_source_segment(src, n)
    return None
def block(src, start, end_marker):
    if src is None or start not in src: return None
    i = src.index(start); j = src.index(end_marker, i) + len(end_marker)
    return src[i:j]
def h(x): return "-" if x is None else hashlib.sha256(x.encode()).hexdigest()[:8]
revs = sh("log", "--reverse", "--format=%h %cI", "0bcc089^..918559f", "--", "scheduler/anchor_loop.py", "signal/legs.py", "live/per_name_stop.py", "live/external_book.py").split("\n")
revs = [r for r in revs if r.strip()]
pre = sh("rev-parse", "--short", "0bcc089^").strip()
rows = [(pre, "(parent of 0bcc089)")] + [tuple(r.split(" ", 1)) for r in revs]
cols = ["zero_loop+call", "stop_into_untradable", "apply_withhold", "clamp_held", "withhold_pop", "reshape_after", "to_notional", "active_sets", "ext.target_vector", "ext.held_not_in_target"]
print("version  commit_time               " + "  ".join(c[:14].ljust(14) for c in cols))
prev = None
for rev, t in rows:
    al = show(rev, "scheduler/anchor_loop.py"); lg = show(rev, "signal/legs.py"); pn = show(rev, "live/per_name_stop.py"); ex = show(rev, "live/external_book.py")
    vals = [h(block(al, "for _s in getattr(self, \"_pns_sets\"", "floors_usdt=_fl, floors_source=_fl_src)")),
            h(block(al, "self._pns_sets = PNS.active_sets(", "self._untradable = set(self._untradable) | _pns_all")),
            h(func_src(al, "apply_withhold_and_reshape")), h(func_src(al, "clamp_held_untradable")), h(func_src(al, "withhold_pop")),
            h(func_src(lg, "reshape_after_withhold")), h(func_src(lg, "to_notional")), h(func_src(pn, "active_sets")),
            h(func_src(ex, "target_vector")), h(func_src(ex, "held_not_in_target"))]
    mark = "" if prev is None else ("  (changed: " + ",".join(c for c, a, b in zip(cols, prev, vals) if a != b) + ")" if vals != prev else "")
    print(f"{rev:8} {t[:25]:25} " + "  ".join(v.ljust(14) for v in vals) + mark)
    prev = vals
