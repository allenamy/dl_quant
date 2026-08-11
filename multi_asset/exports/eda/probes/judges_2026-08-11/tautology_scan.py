"""恒真断言扫描: 找出在任何输入下都为真的 check(...) 第二参数。"""
import ast, glob, os, sys

ROOT = os.path.expanduser("~/dl_quant_live/live")
CONST = (ast.Constant,)

def const_truthy(n):
    return isinstance(n, ast.Constant) and bool(n.value) and n.value is not None

def both_const(n):
    """比较两侧都是字面量 ⇒ 结果与输入无关"""
    if isinstance(n, ast.Compare) and len(n.comparators) == 1:
        return isinstance(n.left, CONST) and isinstance(n.comparators[0], CONST)
    return False

def is_len_of_literal(n):
    """len([...]) == 3 之类: 对字面容器取长度"""
    if isinstance(n, ast.Compare) and isinstance(n.left, ast.Call):
        f = n.left.func
        if isinstance(f, ast.Name) and f.id == "len" and n.left.args \
           and isinstance(n.left.args[0], (ast.List, ast.Tuple, ast.Dict, ast.Set)):
            return True
    return False

rows = []
for path in sorted(glob.glob(os.path.join(ROOT, "tests_*.py"))):
    src = open(path).read()
    tree = ast.parse(src, path)
    lines = src.splitlines()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "check" and len(node.args) >= 2):
            continue
        cond = node.args[1]
        why = None
        if const_truthy(cond):
            why = f"字面常量 {ast.unparse(cond)}"
        elif both_const(cond):
            why = f"两个常量比较 {ast.unparse(cond)}"
        elif is_len_of_literal(cond):
            why = f"对字面容器取长度 {ast.unparse(cond)}"
        elif isinstance(cond, ast.Constant) and cond.value is False:
            why = "字面 False (恒假)"
        if why:
            rows.append((os.path.basename(path), node.lineno, why,
                         lines[node.lineno-1].strip()[:100]))
print("=== 恒真/恒假 断言 ===")
for f, ln, why, txt in rows:
    print(f"  {f}:{ln}  [{why}]")
    print(f"      {txt}")
print(f"\n共 {len(rows)} 处")
