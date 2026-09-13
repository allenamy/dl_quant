"""红能力跑手: 把测试文件里每一处 check(...) 调用包进 try/except(崩溃也算 FAIL, 不中断),
然后以【指定的树】为 _REPO 跑整套 —— 用来证明每个新格在修前源上就是红的。只读: 不改克隆任何文件。"""
import ast, io, os, sys, contextlib

TESTS = "/Users/haosiyu/cc_tmp/exec_w1/live/tests_ic_monitor.py"
tree_root = sys.argv[1]


class Wrap(ast.NodeTransformer):
    def visit_Expr(self, node):
        v = node.value
        if isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == "check":
            name = ""
            if v.args and isinstance(v.args[0], (ast.Constant, ast.JoinedStr)):
                try:
                    name = ast.literal_eval(v.args[0])
                except Exception:
                    name = "<dynamic>"
            handler = ast.parse(
                "except BaseException as _e:\n"
                f"    print('\u2605 FAIL ' + {name[:110]!r} + ' \u2014 CRASHED: ' + type(_e).__name__ + ': ' + str(_e)[:160])\n"
                "    FAIL.append('CRASH')\n".replace("except", "try:\n    pass\n" + "except", 1)).body[0].handlers[0]
            return ast.copy_location(ast.Try(body=[node], handlers=[handler], orelse=[], finalbody=[]), node)
        return node


src = open(TESTS, encoding="utf-8").read()
mod = Wrap().visit(ast.parse(src))
ast.fix_missing_locations(mod)
fake = os.path.join(tree_root, "live", "tests_ic_monitor.py")
ns = {"__name__": "__redprobe__", "__file__": fake}
code = compile(mod, fake, "exec")
try:
    exec(code, ns)
except SystemExit as e:
    print(f"[runner] suite exit={e.code}")
