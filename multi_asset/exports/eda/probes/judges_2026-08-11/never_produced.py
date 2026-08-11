"""静态扫描: 哪些 schema 字段"只被测试赋值, 生产代码从不赋值"。
判据: 字段出现在 pilot_log.SCHEMA 里, 但生产代码 (非 tests_*) 中找不到任何一处对它的赋值 ——
      dict 字面量 "field": <expr> / kwarg field= / obj["field"] = / setdefault("field"
      且若行构造用的是 p.get("field", CONST) 而 p["field"] 从未被赋值 ⇒ 该字段恒为 CONST。
"""
import ast, glob, json, os, re, sys

REPO = os.path.expanduser("~/dl_quant_live")
sys.path.insert(0, os.path.join(REPO, "live"))
import pilot_log as PL

prod = [p for p in glob.glob(os.path.join(REPO, "*", "*.py")) + glob.glob(os.path.join(REPO, "*.py"))
        if "/tests_" not in p and not os.path.basename(p).startswith("tests_")]
tests = [p for p in glob.glob(os.path.join(REPO, "*", "*.py")) if os.path.basename(p).startswith("tests_")]

def read(paths):
    return {p: open(p, encoding="utf-8").read() for p in paths}
PROD, TEST = read(prod), read(tests)

def assigned_in(blobs, field):
    pats = [rf'\["{field}"\]\s*=', rf"\['{field}'\]\s*=", rf'\b{field}\s*=\s*[^=]',
            rf'setdefault\(\s*["\']{field}["\']']
    hits = []
    for path, src in blobs.items():
        for ln, line in enumerate(src.splitlines(), 1):
            if re.search(rf'["\']{field}["\']\s*:', line) and ".get(" not in line:
                hits.append((path, ln, "dict-literal", line.strip()[:90])); continue
            for pat in pats:
                if re.search(pat, line):
                    hits.append((path, ln, "assign", line.strip()[:90])); break
    return hits

rows = []
for table, spec in PL.SCHEMA.items():
    cols = spec["required"] if isinstance(spec, dict) else spec
    for c in cols:
        ph, th = assigned_in(PROD, c), assigned_in(TEST, c)
        if not ph:
            rows.append((table, c, len(th), th[:1]))
print("=== schema 字段: 生产代码从不赋值 (但测试可能赋值) ===")
print(f"{'表':<20}{'字段':<32}{'测试中赋值处':>10}")
for t, c, n, ex in rows:
    star = " ★" if n else ""
    print(f"{t:<20}{c:<32}{n:>10}{star}")
    if ex:
        print(f"      测试样例: {os.path.basename(ex[0][0])}:{ex[0][1]}  {ex[0][3]}")
print(f"\n共 {len(rows)} 个字段生产代码从不赋值; 其中 {sum(1 for r in rows if r[2])} 个在测试里被赋了真值 ★")
