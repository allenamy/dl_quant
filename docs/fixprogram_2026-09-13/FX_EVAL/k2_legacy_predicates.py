#!/usr/bin/env python3
"""k2_legacy_predicates.py — FIXPROGRAM 2026-09-13 item K2: the CURRENT label predicates, extracted verbatim from the device files by AST
and executed on synthetic inputs. READ-ONLY: device files are parsed, never imported and never run as modules (their top levels open
data, assert environments and write receipts). Only the extracted statements run, in a namespace holding exactly the names they read.

Every extraction is pinned by the sha256 of its source text (PINS). A changed device file raises LegacySourceChanged instead of
silently testing different code. `python3 k2_legacy_predicates.py` prints the current segment hashes.
"""
import ast, hashlib, textwrap, types
import numpy as np

REPO = "/Users/haosiyu/Desktop/quant_research"
R2 = REPO + "/multi_asset/exports/research/uplift_r2_2026-09-13"
R3 = REPO + "/multi_asset/exports/research/uplift_r3_2026-09-13"
V4 = REPO + "/multi_asset/exports/research/retrain_2026-09/v4_chain_2026-09-09"
PR = REPO + "/multi_asset/exports/research/parity_replay_2026-09-12"
SEP = "\n#---\n"


class LegacySourceChanged(AssertionError):
    pass


class _File:
    def __init__(self, path):
        self.path = path; self.text = open(path, encoding="utf-8").read(); self.tree = ast.parse(self.text)
        self.lines = self.text.split("\n")

    def line(self, needle):
        hits = [i + 1 for i, l in enumerate(self.lines) if needle in l]
        if len(hits) != 1: raise LegacySourceChanged("%s: needle %r has %d hits" % (self.path, needle[:70], len(hits)))
        return hits[0]

    def seg(self, node):   # padded to the original column, then dedented: nested if-chains / defs execute as written
        return textwrap.dedent(ast.get_source_segment(self.text, node, padded=True))

    def outermost(self, ln, types_):
        c = [n for n in ast.walk(self.tree) if isinstance(n, types_) and getattr(n, "lineno", None) == ln]
        if not c: raise LegacySourceChanged("%s: no %s at line %d" % (self.path, types_, ln))
        return max(c, key=lambda n: n.end_lineno - n.lineno)

    def if_chain(self, needle):
        return self.seg(self.outermost(self.line(needle), (ast.If,)))

    def funcdef(self, needle):
        return self.seg(self.outermost(self.line(needle), (ast.FunctionDef,)))

    def stmt(self, needle):
        return self.seg(self.outermost(self.line(needle), (ast.Assign, ast.Expr)))

    def assign_value(self, needle):
        return ast.get_source_segment(self.text, self.outermost(self.line(needle), (ast.Assign,)).value)

    def named_assign(self, needle, name):
        ln = self.line(needle)
        c = [n for n in ast.walk(self.tree) if isinstance(n, ast.Assign) and n.lineno == ln and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
        if len(c) != 1: raise LegacySourceChanged("%s: assign %s at %d: %d" % (self.path, name, ln, len(c)))
        return self.seg(c[0])

    def subscript_assign(self, needle, key):
        ln = self.line(needle)
        c = [n for n in ast.walk(self.tree) if isinstance(n, ast.Assign) and n.lineno == ln and isinstance(n.targets[0], ast.Subscript)
             and isinstance(n.targets[0].slice, ast.Constant) and n.targets[0].slice.value == key]
        if len(c) != 1: raise LegacySourceChanged("%s: subscript assign [%r] at %d: %d" % (self.path, key, ln, len(c)))
        return self.seg(c[0])

    def subscript_assign_value(self, needle, key):
        ln = self.line(needle)
        c = [n for n in ast.walk(self.tree) if isinstance(n, ast.Assign) and n.lineno == ln and isinstance(n.targets[0], ast.Subscript)
             and isinstance(n.targets[0].slice, ast.Constant) and n.targets[0].slice.value == key]
        if len(c) != 1: raise LegacySourceChanged("%s: subscript assign [%r] at %d: %d" % (self.path, key, ln, len(c)))
        return ast.get_source_segment(self.text, c[0].value)

    def keyword_value(self, needle, arg):
        ln = self.line(needle)
        c = [n for n in ast.walk(self.tree) if isinstance(n, ast.keyword) and n.arg == arg and n.lineno == ln]
        if len(c) != 1: raise LegacySourceChanged("%s: keyword %s at %d: %d" % (self.path, arg, ln, len(c)))
        return ast.get_source_segment(self.text, c[0].value)

    def toplevel_range(self, first, last):
        a = self.line(first); b = self.line(last)
        body = [n for n in self.tree.body if n.lineno >= a and n.end_lineno <= b]
        if not body or body[0].lineno != a or body[-1].end_lineno < b: raise LegacySourceChanged("%s: range %d..%d not top-level" % (self.path, a, b))
        return [self.seg(n) for n in body]


def segments():
    t4 = _File(R2 + "/T4/devices/t4_judge.py"); t5c = _File(R2 + "/T5c/devices/t5c_bridge.py"); q1 = _File(R2 + "/T5b/devices/t5b_q1.py")
    ex = _File(R2 + "/T5b/devices/t5b_exec.py"); ad = _File(R2 + "/T5/devices/t5_addendum_h2b.py"); t2 = _File(R2 + "/T2/devices/t2_judge.py")
    p2 = _File(PR + "/phase2/devices/p2_s2_lib.py"); t1 = _File(R2 + "/T1/devices/t1_judge.py"); t8 = _File(R2 + "/T8/devices/t8_judge.py")
    l2 = _File(R3 + "/L2/devices/l2_b_common.py"); v4 = _File(V4 + "/judge_v4.py")
    return {
        "T4": t4.toplevel_range('A_c0 = [BOOK[f"K1_minus_K0|C0|s{s}"]["KING_LIVE"] for s in ("42", "2027")]', 'verdict = "MATERIAL" if (condA or condB) else "NOT MATERIAL (at this resolution)"'),
        "T5C": [t5c.funcdef("def boot(num, den, k, sel=None):"), t5c.funcdef("def readings(dk, rk, sel=None):")],
        "T5BQ1": [q1.keyword_value('reading=("FROZEN-RESIDUAL-MATERIAL" if x.mean() >= 0.05 else "NOT MATERIAL")', "reading")],
        "T5BEX": [ex.subscript_assign_value('READ3["PRIMARY_GAP_EXECFREEZE"]["reading"] = ("EXECUTOR-ADDED-FREEZE-MATERIAL"', "reading")],
        "T5ADD": [ad.assign_value('OUT[s]["reading"] = ("NEGLIGIBLE" if abs(sh_) <= 0.05')],
        "T2": [t2.named_assign("K = 3; ALPHA_K = 0.05 / K;", "RES_BPS"), t2.subscript_assign('o["below_resolution"] = bool(abs(o["dg"]) < RES_BPS)', "below_resolution"),
               t2.funcdef("def decide(RB, c2_pass, trip_state):")],
        "P2": [p2.named_assign("ANN = math.sqrt(2190.0); RES_BPS = 0.23; NB = 2000", "RES_BPS"), p2.funcdef("def verdict(cells, k):")],
        "T1H1": [t1.if_chain('if sd_["vci_hi"] < 0 and sm_["vci_hi"] < 0 and ratio >= 0.5: v = "EXPLAINS"'), t1.funcdef("def agg_h1(vars_):")],
        "T1H3": [t1.if_chain('if dE1["vci_hi"] < 0 and E0T >= 0.75 * E0H and dE0["vci_lo"] <= 0 <= dE0["vci_hi"]: v = "HALF-LIFE"'),
                 t1.stmt('H3["verdict"] = "SURVIVES" if "HALF-LIFE" in fcells else')],
        "T1H5": [t1.stmt('excl = lambda s_: s_["vci_lo"] > 0 or s_["vci_hi"] < 0'),
                 t1.if_chain('if c1d >= 0.50 and ((excl(dpD) and excl(dpR) and excl(dpRs)) or (excl(dsD) and excl(dsR) and excl(dsRs))): v = "SURVIVES (different mechanisms)"')],
        "T8": t8.toplevel_range("crit = {}", '    overall = "FAIL"'),
        "L2": [l2.stmt("TEST_YEARS = (2023, 2024, 2025, 2026)"), l2.funcdef("def reading(cell):")],
        "V4": [v4.stmt('v = "(A) PROMOTE" if all(x["delta"] > 0 and x["ci95"][0] > 0 for x in r) else ("(B) REJECT" if all(x["ci95"][1] < 0 for x in r) else "(C) UNDECIDED")')],
    }


def digest(parts):
    return hashlib.sha256(SEP.join(parts).encode()).hexdigest()


PINS = {   # sha256 of the extracted source text at FX-EVAL C2 (HEAD adeda8e7); a device edit breaks the pin on purpose
    "T4": "ffc9fd947b30bf632a2e25630008c1793d020daae3c46cf1edc38e5eebdbcc39",
    "T5C": "55451a05e7298ccd2cf6d2ae835241ada78d195ce917673e5cd71a60ba908eed",
    "T5BQ1": "cd359f84aef651dbcbbddbc42937222ed9a4494e408e2d487dde8bae3d1011d1",
    "T5BEX": "d3b6fd846439d6ad0ec62d517df18cc66f5ba4493d71d541fea8ddf72bea81ca",
    "T5ADD": "3bfc1ca10653e174f4843da14636571630126107db53a3838b17b60fa738fc37",
    "T2": "9c2cb9db111e9278f502cdce0310ec5f948d283e31a97d1baa2fdd278b46680e",
    "P2": "f9dcd208fbcc06926a9ce6e1e9d05d7f0407ca0c3fd3761783a5ff220003a4d7",
    "T1H1": "a0b2d1e634d4e433e86c3b8e2c7ba430c419a7a055f2651fb4928ee4cd71f70c",
    "T1H3": "e2e9eab7a287ece8cd66d4a19e1d0b79043a5187a70a41ba7333b3a5116fb691",
    "T1H5": "c3ee6523939bcf76ba4cb3ba146368ca2fb648f5520303ff3fafda58cede20f5",
    "T8": "def6ac1bd4ffee9d8dcaca2b9e5ea310d8a9c650898c001c1422e32de55bd39c",
    "L2": "17438f9189555be80d0551669bf877e00f8744155789c294e5569e93a2405aa0",
    "V4": "245126f41d6261d44ac62f251c3a4a6ae8f0aa0ef77c79d1bb706f51ba47a4cf",
}


class Legacy:
    """executes the pinned verbatim segments"""

    def __init__(self, pins=None):
        pins = pins or PINS; segs = segments(); self.code = {}
        for k, parts in segs.items():
            d = digest(parts)
            if pins.get(k) != d: raise LegacySourceChanged("%s: extracted segment sha %s != pinned %s" % (k, d, pins.get(k)))
            self.code[k] = parts

    def _exec(self, key, ns, parts=None):
        src = "\n".join(self.code[key] if parts is None else parts)
        exec(compile(src, "<legacy %s>" % key, "exec"), ns); return ns

    # T4 t4_judge.py L142-150
    def t4_verdict(self, BOOK, SCORE):
        return self._exec("T4", dict(np=np, BOOK=BOOK, SCORE=SCORE))["verdict"]

    # T5c t5c_bridge.py boot + readings
    def t5c_readings(self, dk, rk, days, B=2000):
        ns = self._exec("T5C", dict(np=np, days=np.asarray(days), B=B, one=np.ones(len(dk))))
        return ns["readings"](np.asarray(dk, float), np.asarray(rk, float))

    # T5b t5b_q1.py L248 / t5b_exec.py L332 / T5 t5_addendum_h2b.py L94 (expressions)
    def t5b_q1_reading(self, x):
        return eval(compile(self.code["T5BQ1"][0], "<legacy T5BQ1>", "eval"), dict(x=np.asarray(x, float)))

    def t5b_exec_reading(self, mean):
        return eval(compile(self.code["T5BEX"][0], "<legacy T5BEX>", "eval"), dict(p={"mean": mean}))

    def t5_addendum_reading(self, share_point):
        return eval(compile(self.code["T5ADD"][0], "<legacy T5ADD>", "eval"), dict(sh_=share_point))

    # T2 t2_judge.py RES_BPS / below_resolution / decide
    def t2_below_resolution(self, dg):
        ns = self._exec("T2", dict(np=np, SEEDS=("42", "2027")), parts=self.code["T2"][:1]); o = {"dg": dg}
        exec(compile(self.code["T2"][1], "<legacy T2 below_resolution>", "exec"), dict(ns, o=o)); return o["below_resolution"]

    def t2_decide(self, RB, c2_pass, trip_state):
        ns = self._exec("T2", dict(np=np, SEEDS=("42", "2027")), parts=[self.code["T2"][0], self.code["T2"][2]]); return ns["decide"](RB, c2_pass, trip_state)

    # P2 p2_s2_lib.py RES_BPS + verdict
    def p2_verdict(self, cells, k=0):
        return self._exec("P2", dict(np=np))["verdict"](cells, k)

    # T1 t1_judge.py H1 cell chain + agg_h1
    def t1_h1_cell(self, sd_, sm_, ratio):
        return self._exec("T1H1", dict(np=np, sd_=sd_, sm_=sm_, ratio=ratio, H1R={}), parts=self.code["T1H1"][:1])["v"]

    def t1_h1_agg(self, cell_verdicts, vars_=("DISP24", "BREADTH72")):
        H1R = {"%s|%s" % (s, T): {"cell_verdict": cell_verdicts[(s, T)]} for s in vars_ for T in ("T_A", "T_L")}
        return self._exec("T1H1", dict(np=np, H1R=H1R), parts=self.code["T1H1"][1:])["agg_h1"](list(vars_))

    # T1 H3 cell chain + aggregate
    def t1_h3(self, cells):
        out = [self._exec("T1H3", dict(np=np, **c), parts=self.code["T1H3"][:1])["v"] for c in cells]
        ns = self._exec("T1H3", dict(np=np, H3={}, fcells=out), parts=self.code["T1H3"][1:]); return out, ns["H3"]["verdict"]

    # T1 H5 (excl + chain); c1d is computed in the device from H5["c1_diff"] one line earlier
    def t1_h5(self, c1d, dpD, dsD, dpR, dsR, dpRs, dsRs, pi23, ss23):
        return self._exec("T1H5", dict(np=np, c1d=c1d, dpD=dpD, dsD=dsD, dpR=dpR, dsR=dsR, dpRs=dpRs, dsRs=dsRs, pi23=pi23, ss23=ss23))["v"]

    # T8 t8_judge.py crit … overall
    def t8(self, FR, M, cellnull, B, SUBST=("NET", "LONG", "SHORT"), MODELS=("R", "L"), SEEDS=("42", "2027"), NNULL=500):
        C = types.SimpleNamespace(SUBST=SUBST, MODELS=MODELS, SEEDS=SEEDS, NNULL=NNULL)
        M = np.asarray(M, float)
        ns = self._exec("T8", dict(np=np, FR=FR, M=M, q95=float(np.percentile(M, 95)), cellnull=cellnull, B=B, C=C, FIN=lambda v: v is not None and np.isfinite(v)))
        return ns["overall"], ns["tv"], ns["mt"], ns["crit"]

    # L2 l2_b_common.py reading
    def l2_reading(self, cell):
        return self._exec("L2", dict(np=np))["reading"](cell)

    # judge_v4.py verdict expression
    def v4_verdict(self, r):
        return self._exec("V4", dict(np=np, r=r))["v"]


if __name__ == "__main__":
    import json
    print(json.dumps({k: digest(v) for k, v in segments().items()}, indent=1))
