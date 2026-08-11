"""恒真扫描 v2: 区分 try/except 惯用法 (合法) 与真正的空断言。"""
import ast, glob, os

ROOT = os.path.expanduser("~/dl_quant_live/live")

def in_try(tree, target):
    """target 是否位于某个 Try 的 body 或 handler 内 (那样字面 True/False 的真正条件是'能否走到这一行')"""
    for n in ast.walk(tree):
        if isinstance(n, ast.Try):
            for sub in n.body:
                for x in ast.walk(sub):
                    if x is target: return "try-body"
            for h in n.handlers:
                for sub in h.body:
                    for x in ast.walk(sub):
                        if x is target: return "except-handler"
    return None

legit, vacuous, other = [], [], []
for path in sorted(glob.glob(os.path.join(ROOT, "tests_*.py"))):
    src = open(path).read(); tree = ast.parse(src, path); lines = src.splitlines()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "check" and len(node.args) >= 2):
            continue
        cond = node.args[1]
        if not isinstance(cond, ast.Constant):
            # 两个常量比较也算
            if isinstance(cond, ast.Compare) and len(cond.comparators)==1 \
               and isinstance(cond.left, ast.Constant) and isinstance(cond.comparators[0], ast.Constant):
                other.append((os.path.basename(path), node.lineno, ast.unparse(cond)))
            continue
        loc = in_try(tree, node)
        rec = (os.path.basename(path), node.lineno, repr(cond.value), lines[node.lineno-1].strip()[:90])
        (legit if loc else vacuous).append(rec + (loc,))
print("=== 合法 (try/except 惯用法: 真正条件是'能否走到这一行') ===")
print(f"  共 {len(legit)} 处 —— 不是缺陷")
print("\n=== ★ 真正的空断言 (不在 try/except 内的字面常量) ===")
for r in vacuous: print(f"  {r[0]}:{r[1]}  值={r[2]}\n      {r[3]}")
print(f"  共 {len(vacuous)} 处")
print("\n=== 两个常量比较 ===")
for r in other: print(f"  {r[0]}:{r[1]}  {r[2]}")
print(f"  共 {len(other)} 处")
