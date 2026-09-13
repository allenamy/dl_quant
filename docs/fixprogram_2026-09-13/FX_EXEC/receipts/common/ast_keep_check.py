"""ast_keep_check.py <old_file> <new_file> [call_names=check]
Every assertion site of the OLD file must survive VERBATIM, IN ORDER, in the NEW file:
  · every call to a checker function (default `check`; comma-separated list allowed) — compared as the exact source
    segment of the whole call (label, condition, detail), whitespace-normalised only;
  · every `assert` statement — exact source segment.
Prints counts, the first lost site if any, and exits 1 when any old site is missing or out of order."""
import ast, sys, re

def sites(path, names):
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            nm = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if nm in names:
                out.append((n.lineno, n.col_offset, "call:" + nm, ast.get_source_segment(src, n)))
        elif isinstance(n, ast.Assert):
            out.append((n.lineno, n.col_offset, "assert", ast.get_source_segment(src, n)))
    out.sort()
    norm = lambda s: re.sub(r"\s+", " ", s or "").strip()
    return [(ln, kind, norm(seg)) for ln, _c, kind, seg in out]

old, new = sys.argv[1], sys.argv[2]
names = set((sys.argv[3] if len(sys.argv) > 3 else "check").split(","))
so, sn = sites(old, names), sites(new, names)
j, lost = 0, []
for ln, kind, seg in so:
    while j < len(sn) and sn[j][2] != seg:
        j += 1
    if j == len(sn):
        lost.append((ln, kind, seg[:200]))
        j = 0  # keep scanning for the others to report every loss, order-insensitive after a loss
        continue
    j += 1
new_only = len(sn) - (len(so) - len(lost))
print(f"old sites {len(so)} | new sites {len(sn)} | lost {len(lost)} | added {new_only} | names {sorted(names)}")
for l in lost[:5]:
    print("  LOST", l)
sys.exit(1 if lost else 0)
