"""NEW_S2: deterministic patcher — producer feature code with D4/D5/D6/D7/D8/D9/D14 fixed.

D11 / D13 moved to the data/state layer on 2026-09-23 (DESIGN A5). Their patch bodies are kept in
handover_D11_D13/ so A5 has the exact text that was tested here; they are NOT applied by this file.

PREREG docs/PREREG_new_servable_v2_features_2026-09-23.md §1.1. Same shape as the researcher's
derive_f8_candidate.py: every edit is a (old, new) pair whose `old` must occur EXACTLY ONCE in the
source; sources are sha-pinned; the output shas and the hit line numbers go into the receipt.

Base:
  shadow_loop_v3.py      = ed11d731 (6080073b + R10-B01 fetch/holdable split), NOT the raw producer file
  fea171/combo_stage.py  = fb5a9407 (production)
  fea171/dlw_features.py = 29ae6a98 (production)
  fea171/f8_higher_order_features.py = 2c500c7a (production)
  fea171/stable_trend_reference.py   = 01bf8b3d (researcher; copied in, needed by the D7 patch)

NOT applied (out of scope this round, PREREG §1.2): D3's PatchedMarket routing, D10's official
intervals, D2's per-anchor history, D12's funding rank base; and the researcher's CHUNK/threading/
ThreadPoolExecutor/receipt-binding/savez_compressed edits, which are scheduling and I/O, not features.

D5 policy (one sentence, because it is the only edit with a free choice in it): accumulate in float64,
then round the result back to the dtype the production code already produced (float32). Bitwise equality
with the researcher's build is NOT a goal and is not attainable — the producer sums a 40-day rolling
window directly while the researcher differences a whole-axis cumsum. What is adopted is the POLICY
(float64 accumulator, NaN on an empty window, stable tie-break), on the producer's own code shape.

usage: python news2_derive_producer.py <out_dir> [--member-screen-f64 yes|no]
"""
import argparse, ast, hashlib, json, os, pathlib, shutil, sys, time

# Paths are env-overridable so the SAME device runs on the production Mac and on pod2; every file is
# sha-pinned below, so a wrong path fails loudly instead of quietly patching something else.
WIDE = pathlib.Path(os.environ.get("NEWS2_WIDE", os.path.expanduser("~/wide_shadow")))
_p = pathlib.Path(__file__).resolve().parents
REPO = _p[5] if len(_p) > 5 else pathlib.Path("/nonexistent-repo")   # pod2 has no repo checkout; env vars supply the paths
BASE_SHADOW = pathlib.Path(os.environ.get(
    "NEWS2_BASE_SHADOW", str(REPO / "multi_asset/exports/research/news_2026-09-23/deploy/producer_patch/shadow_loop_v3.patched.py")))
RESEARCH_TREE = pathlib.Path(os.environ.get(
    "NEWS2_RESEARCH_TREE", str(REPO / ".claude/worktrees/codex-strategy-uplift-20260920/multi_asset/experiments/codex_combo_20260923/devices")))

SRC_SHA = {
    "shadow_loop_v3.py": "ed11d731ffc13ef1333c3fabe044bc209485ba237fd9b8ae11aeccb014be1ec9",
    "fea171/combo_stage.py": "fb5a94074583b328b949cd08767c031d9eb705fbdc23d6a371d9bd657b3ca4a8",
    "fea171/dlw_features.py": "29ae6a985d891e56340378bb432c0370e914b93709eec44f54592472e4d20a76",
    "fea171/f8_higher_order_features.py": "2c500c7ad2bb0f5ddccf431021df50a106a39f4d228bd6cf2d074c5c12f66a5f",
    "fea171/stable_trend_reference.py": "01bf8b3d35a23b6599ceddcc849dbbbbb85eff5eceebfe1a5a045fe9ca8b79ae",
}
# the raw producer file, kept only so the receipt records what ed11d731 was derived from
RAW_SHADOW_SHA = "6080073964bffc621c893915b16f71ecafe093194f0b99a66a4463ee12c74e61"


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


class Patcher:
    """One source file. Every replace() is recorded with the line the `old` text started on.

    `enabled` selects a subset of fix tags (for the per-fix arms of the global gate). A tag that is
    not enabled is still located and its anchor uniqueness still asserted, so a subset arm cannot
    silently skip a patch whose anchor has drifted; it is recorded with applied=False.
    """

    def __init__(self, name, text, enabled=None):
        self.name = name
        self.text = text
        self.orig = text
        self.edits = []
        self.enabled = enabled          # None = all

    def _on(self, tag):
        if self.enabled is None:
            return True
        fam = tag.split(":")[0]
        return tag in self.enabled or any(f in self.enabled for f in fam.split("+"))

    def replace(self, tag, old, new):
        n = self.text.count(old)
        if n != 1:
            raise AssertionError(f"{self.name}: anchor for {tag} occurs {n} times, expected 1: {old[:80]!r}")
        i = self.text.index(old)
        line = self.text[:i].count("\n") + 1
        applied = self._on(tag)
        if applied:
            self.text = self.text.replace(old, new, 1)
        self.edits.append({"tag": tag, "line_in_source": line, "applied": applied, "old": old, "new": new})

    def replace_region(self, tag, begin_text, end_text, new):
        """Block edit located by boundary text; the measured start/end lines go into the receipt."""
        assert self.text.count(begin_text) == 1, (self.name, tag, "begin", self.text.count(begin_text))
        b = self.text.index(begin_text)
        assert self.text.count(end_text) == 1, (self.name, tag, "end", self.text.count(end_text))
        e = self.text.index(end_text, b)
        region = self.text[b:e]
        first = self.text[:b].count("\n") + 1
        last = self.text[:e].count("\n")
        self.replace(tag, region, new)
        self.edits[-1].update({"region_first_line": first, "region_last_line": last})


# ---------------------------------------------------------------- shadow_loop_v3.py (King block)
# D5 and D6 touch the SAME three kernels (wstat, the vol block, the member screen), so each kernel's
# replacement text is generated from the two flags. That keeps the per-fix arms of the global gate
# genuinely separable instead of collapsing D5 and D6 into one indivisible edit.
def _wstat_new(d5, d6):
    acc = "np.where(fin, seg, 0).sum(0, dtype=np.float64)" if d5 else "np.where(fin, seg, 0).sum(0)"
    cast = ".astype(np.float32)" if d5 else ""
    mean = ('np.where(cnt > 0, s_ / nf, np.nan)' + cast) if d6 else ("s_ / nf" + cast)
    return f"""    def wstat(ch, w, kind):
        # NEW_S2{' D5: float64 accumulator (feature_contract.window_stats policy), rounded back to the' if d5 else ''}
        # {'float32 this function already returned.' if d5 else ''}{' NEW_S2 D6: an empty window has no mean - NaN, so the' if d6 else ''}
        # {'existing np.isfinite(x) guard below keeps it out of the cross-sectional rank.' if d6 else ''}
        seg = CDf[max(ai + 1 - w, 0):ai + 1, :, ch]
        fin = np.isfinite(seg)
        cnt = fin.sum(0)
        nf = np.maximum(cnt, 1)
        s_ = {acc}
        if kind == "sum": return s_{cast}
        return {mean}
"""


def _vol_new(d5, d6):
    if d5:
        body = """        z64 = np.where(fin, seg, 0).astype(np.float64)      # NEW_S2 D5: square in float64, not float32
        mm = z64.sum(0) / nf
        vv = np.sqrt(np.maximum((z64 * z64).sum(0) / nf - mm**2, 0))
        del z64
"""
    else:
        body = """        mm = np.where(fin, seg, 0).sum(0) / nf
        vv = np.sqrt(np.maximum(np.where(fin, seg**2, 0).sum(0) / nf - mm**2, 0))
"""
    tail = "        vv = np.where(cnt > 0, vv, np.nan).astype(np.float32)   # NEW_S2 D6\n" if d6 else (
           "        vv = vv.astype(np.float32)\n" if d5 else "")
    return f"""        seg = CDf[max(ai + 1 - w, 0):ai + 1, :, 0]
        fin = np.isfinite(seg)
        cnt = fin.sum(0)
        nf = np.maximum(cnt, 1)
{body}{tail}        vals.append(vv[m]); names_order.append(f"vol_{{w}}")
"""


def _screen_new(d5, d6):
    if d5:
        stats = """    z5 = np.where(fin5, r5seg, 0).astype(np.float64)        # NEW_S2 D5
    m7 = z5.sum(0)
    v7 = np.sqrt(np.maximum((z5 * z5).sum(0) / n7 - (m7 / n7) ** 2, 0))
    del z5
"""
        qv = "    qvm = np.where(finq, qseg, 0).sum(0, dtype=np.float64) / np.maximum(cq, 1)\n"
    else:
        stats = """    m7 = np.where(fin5, r5seg, 0).sum(0)
    v7 = np.sqrt(np.maximum(np.where(fin5, r5seg**2, 0).sum(0) / n7 - (m7 / n7) ** 2, 0))
"""
        qv = "    qvm = np.where(finq, qseg, 0).sum(0) / np.maximum(cq, 1)\n"
    v7tail = "    v7 = np.where(c7 > 0, v7, np.nan).astype(np.float32)   # NEW_S2 D6\n" if d6 else (
             "    v7 = v7.astype(np.float32)\n" if d5 else "")
    qvtail = "    qvm = np.where(cq > 0, qvm, np.nan).astype(np.float32)   # NEW_S2 D6\n" if d6 else (
             "    qvm = qvm.astype(np.float32)\n" if d5 else "")
    return f"""    r5seg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 0]
    fin5 = np.isfinite(r5seg)
    covr = fin5.sum(0) / 2016
    c7 = fin5.sum(0)
    n7 = np.maximum(c7, 1)
{stats}{v7tail}    qseg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 3]
    finq = np.isfinite(qseg)
    cq = finq.sum(0)
{qv}{qvtail}"""


def patch_shadow(P, member_screen_f64):
    d5 = P._on("D5:x"); d6 = P._on("D6:x")
    P.replace("D5+D6:wstat", ORIG_WSTAT, _wstat_new(d5, d6))
    P.replace("D5+D6:vol", ORIG_VOL, _vol_new(d5, d6))
    if member_screen_f64:
        P.replace("D5+D6:member_screen", ORIG_SCREEN, _screen_new(d5, d6))
        if d6:
            P.replace("D6:qvm_population_assert", ORIG_OK, NEW_OK)
    # D14 - stable tie-break on the liquidity sort.
    P.replace(
        "D14:stable_argsort",
        '        m = np.sort(m[np.argsort(-qvm[m])[:P["NTOP"]]])',
        '        m = np.sort(m[np.argsort(-qvm[m], kind="stable")[:P["NTOP"]]])   # NEW_S2 D14 (feature_contract.select_members)',
    )


ORIG_WSTAT = """    def wstat(ch, w, kind):
        seg = CDf[max(ai + 1 - w, 0):ai + 1, :, ch]
        fin = np.isfinite(seg)
        nf = np.maximum(fin.sum(0), 1)
        s_ = np.where(fin, seg, 0).sum(0)
        if kind == "sum": return s_
        return s_ / nf
"""
ORIG_VOL = """        seg = CDf[max(ai + 1 - w, 0):ai + 1, :, 0]
        fin = np.isfinite(seg)
        nf = np.maximum(fin.sum(0), 1)
        mm = np.where(fin, seg, 0).sum(0) / nf
        vv = np.sqrt(np.maximum(np.where(fin, seg**2, 0).sum(0) / nf - mm**2, 0))
        vals.append(vv[m]); names_order.append(f"vol_{w}")
"""
ORIG_SCREEN = """    r5seg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 0]
    fin5 = np.isfinite(r5seg)
    covr = fin5.sum(0) / 2016
    m7 = np.where(fin5, r5seg, 0).sum(0)
    n7 = np.maximum(fin5.sum(0), 1)
    v7 = np.sqrt(np.maximum(np.where(fin5, r5seg**2, 0).sum(0) / n7 - (m7 / n7) ** 2, 0))
    qseg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 3]
    finq = np.isfinite(qseg)
    qvm = np.where(finq, qseg, 0).sum(0) / np.maximum(finq.sum(0), 1)
"""
ORIG_OK = """    ok = (covr >= P["cov_min"]) & (v7 >= P["vol_min"])
    m = np.where(ok)[0]
"""
NEW_OK = """    ok = (covr >= P["cov_min"]) & (v7 >= P["vol_min"])
    # NEW_S2 D6: no member rule is added this round, so a screened-in name with NO liquidity measurement
    # would reach argsort as NaN. Declared to be an empty population; stop rather than sort NaN silently.
    assert not np.any(ok & ~np.isfinite(qvm)), "NEW_S2 D6: member passes cov/vol but qvm window is empty"
    m = np.where(ok)[0]
"""


# ---------------------------------------------------------------- fea171/dlw_features.py (F10 82 cols)
def patch_dlw(P):
    d6 = P._on("D6:x")
    # D4 — 82-column storage precision.
    P.replace(
        "D4:x82_dtype",
        "    X = np.zeros((n_pairs, NF), np.float16); pair_a = np.zeros(n_pairs, np.int32); pair_s = np.zeros(n_pairs, np.int16)",
        "    X = np.zeros((n_pairs, NF), np.float32); pair_a = np.zeros(n_pairs, np.int32); pair_s = np.zeros(n_pairs, np.int16)   # NEW_S2 D4 (build_combo_inputs.py:147)",
    )
    # D6 — empty window -> NaN mean/std. (The ret5 SUM column stays a finite 0, as in the researcher's
    # build_combo_inputs.py:113, which takes st['sum'] for channel 0.) The rank exclusion needs no edit:
    # the existing ok = np.isfinite(xv) below already drops NaN from the rank and writes 0 for the value.
    if d6:
        P.replace(
            "D6:dlw_windows",
            """        for w in WINS:
            lo = np.maximum(hi - w, 0)
            nf = np.maximum(CSf[hi] - CSf[lo], 1)
            if c == 0:
                VAL.append((CSx[hi] - CSx[lo]).astype(np.float32)); val_names.append(f"{nm}_sum_{w}")
            else:
                VAL.append(((CSx[hi] - CSx[lo]) / nf).astype(np.float32)); val_names.append(f"{nm}_mean_{w}")
        if c == 0:
            VOLS = []
            for w in WINS:
                lo = np.maximum(hi - w, 0); nf = np.maximum(CSf[hi] - CSf[lo], 1)
                mm = (CSx[hi] - CSx[lo]) / nf
                VOLS.append(np.sqrt(np.maximum((CS2[hi] - CS2[lo]) / nf - mm ** 2, 0)).astype(np.float32))
""",
            """        for w in WINS:
            lo = np.maximum(hi - w, 0)
            cnt = CSf[hi] - CSf[lo]                      # NEW_S2 D6
            nf = np.maximum(cnt, 1)
            if c == 0:
                VAL.append((CSx[hi] - CSx[lo]).astype(np.float32)); val_names.append(f"{nm}_sum_{w}")
            else:
                VAL.append(np.where(cnt > 0, (CSx[hi] - CSx[lo]) / nf, np.nan).astype(np.float32)); val_names.append(f"{nm}_mean_{w}")
        if c == 0:
            VOLS = []
            for w in WINS:
                lo = np.maximum(hi - w, 0); cnt = CSf[hi] - CSf[lo]; nf = np.maximum(cnt, 1)
                mm = (CSx[hi] - CSx[lo]) / nf
                vv = np.sqrt(np.maximum((CS2[hi] - CS2[lo]) / nf - mm ** 2, 0))
                VOLS.append(np.where(cnt > 0, vv, np.nan).astype(np.float32))   # NEW_S2 D6
""",
        )


# ---------------------------------------------------------------- fea171/combo_stage.py (btcv, fund panel, rn8)
def patch_combo(P, trend_rows="last"):
    # D9 — btcv window [E-2015, E] including the closing bar; coverage gate; no backfill.
    P.replace(
        "D9:btcv_window",
        """    _r5 = RD[:, _jb, 0].astype(np.float64)
    W = 2016
    _v = np.full(len(_r5), np.nan)
    for i in range(W, len(_r5)):
        _v[i] = np.nanstd(_r5[i - W:i])          # 只用满窗(短窗值与配方不符, 自检会拦)
    _full = np.isfinite(_v)
    if _full.any():
        _v[:np.argmax(_full)] = _v[_full][0]      # 早期不足 7 天的行: 显式回填首个满窗值(近似, 只影响 causal_z 的早期统计)
""",
        """    _r5 = RD[:, _jb, 0].astype(np.float64)
    W = 2016
    # NEW_S2 D9 (build_combo_inputs.py:156): window [i-W+1, i] INCLUDES the bar closing at i; finite
    # coverage < 95% -> NaN; the early rows are NOT backfilled with the first full-window value.
    _fin = np.isfinite(_r5)
    _z = np.where(_fin, _r5, 0.0)
    _csn = np.concatenate([[0.0], np.cumsum(_fin.astype(np.float64))])
    _csx = np.concatenate([[0.0], np.cumsum(_z)])
    _csx2 = np.concatenate([[0.0], np.cumsum(_z * _z)])
    _hi = np.arange(len(_r5)) + 1
    _lo = np.maximum(_hi - W, 0)
    _n = _csn[_hi] - _csn[_lo]
    _nn = np.maximum(_n, 1.0)
    _mu = (_csx[_hi] - _csx[_lo]) / _nn
    _v = np.sqrt(np.maximum((_csx2[_hi] - _csx2[_lo]) / _nn - _mu * _mu, 0.0))
    _v[_n < W * 0.95] = np.nan
""",
    )
    # D9 — the two self-checks have to survive a legitimately NaN btcv. The correlation guard against
    # xfer_ref is kept (it is a real guard); only its population is made explicit.
    P.replace(
        "D9:selfcheck",
        """    if len(_pairs) >= 30:
        _a = np.array([p[0] for p in _pairs]); _b = np.array([p[1] for p in _pairs])
        _ok = np.isfinite(_a) & np.isfinite(_b) & (_b > 0)
        _c = float(np.corrcoef(_a[_ok], _b[_ok])[0, 1]); _ratio = float(np.median(_a[_ok] / _b[_ok]))
        assert _c > 0.999 and 0.99 < _ratio < 1.01, f"btcv 重建自检失败 corr={_c:.5f} ratio={_ratio:.4f}"
    assert np.isfinite(out).all() and out.std() > 0, "btcv 序列退化(恒定或含 NaN)"
""",
        """    if len(_pairs) >= 30:
        _a = np.array([p[0] for p in _pairs]); _b = np.array([p[1] for p in _pairs])
        _ok = np.isfinite(_a) & np.isfinite(_b) & (_b > 0)
        # NEW_S2 D9: btcv may now be NaN by design, so the overlap is counted AFTER the finite filter.
        if int(_ok.sum()) >= 30:
            _c = float(np.corrcoef(_a[_ok], _b[_ok])[0, 1]); _ratio = float(np.median(_a[_ok] / _b[_ok]))
            assert _c > 0.999 and 0.99 < _ratio < 1.01, f"btcv 重建自检失败 corr={_c:.5f} ratio={_ratio:.4f}"
    assert np.isfinite(out).any() and float(np.nanstd(out)) > 0, "btcv 序列退化(恒定或全 NaN)"
""",
    )
    # D7 wiring — the mini pipeline is the ONLY place where "compute the trend for the extracted row
    # only" is valid, because it is the code that discards every other row. So the mini pipeline
    # DECLARES the value instead of inheriting it from whatever the producer process happens to have
    # in its environment: a setting that lives in a plist is a setting nobody notices is missing.
    # news2_hist_features.py reads this same literal out of this file, so training and serving cannot
    # disagree about it.
    P.replace(
        "D7:mini_pipeline_declares_trend_rows",
        """    env = dict(os.environ)
    env.update({"F171_CACHE": f"{MINI}/cache.npz", "F171_TARGETS": f"{MINI}/data/dlw_targets.npz", "F171_OUT": MINI,
                "F171_FEA82": f"{MINI}/data/dlw_fea82.npz", "F171_PANEL": f"{_feature_workspace.name}/xfer_panel_live.npz"})
""",
        """    env = dict(os.environ)
    env.update({"F171_CACHE": f"{MINI}/cache.npz", "F171_TARGETS": f"{MINI}/data/dlw_targets.npz", "F171_OUT": MINI,
                "F171_FEA82": f"{MINI}/data/dlw_fea82.npz", "F171_PANEL": f"{_feature_workspace.name}/xfer_panel_live.npz",
                "F8_TREND_ROWS": "%s"})   # NEW_S2 D7: declared here, not inherited from the environment
""" % trend_rows,
    )


# ---------------------------------------------------------------- fea171/f8_higher_order_features.py
# D7 + D8, verbatim from the researcher's derive_f8_candidate.py L20-L46. The other edits in that file
# (CHUNK, PatchedMarket, threading, ThreadPoolExecutor, receipt binding, savez_compressed) are NOT applied.
D8_PATCHES = [
    ("D8:BS_support", "BS = wsum(CSr, b_hi, b_lo)", "BS = wsum(CSr, b_hi, b_lo); BS[wsum(CSf, b_hi, b_lo) != bw] = np.nan"),
    ("D8:upblk", "up = (BS > 0).mean(0); up[~b_ok.all(0), :] = np.nan;", "up = (BS > 0).mean(0); up[~np.isfinite(BS).all(0)] = np.nan; up[~b_ok.all(0), :] = np.nan;"),
    ("D8:dhi", 'put(f"D:dhi_{w}", pE - mx, chunk)', 'v = pE - mx; v[wsum(CSf, hi, lo_of(w)) != w] = np.nan; put(f"D:dhi_{w}", v, chunk)'),
    ("D8:dlo", 'put(f"D:dlo_{w}", pE - mn, chunk)', 'v = pE - mn; v[wsum(CSf, hi, lo_of(w)) != w] = np.nan; put(f"D:dlo_{w}", v, chunk)'),
    ("D8:ppct", 'put(f"D:ppct_{w}", rk, chunk)', 'rk[wsum(CSf, hi, lo_of(w)) != w] = np.nan; put(f"D:ppct_{w}", rk, chunk)'),
    ("D8:SR30", "SR30 = CSr[sp_hi_c] - CSr[sp_lo_c];", "SR30 = CSr[sp_hi_c] - CSr[sp_lo_c]; SR30[(CSf[sp_hi_c] - CSf[sp_lo_c]) != 48] = np.nan;"),
    ("D8:r4lag", "v[wsum(CSf, b_hi, b_lo) < 12] = np.nan;", "v[wsum(CSf, b_hi, b_lo) != 48] = np.nan;"),
    ("D8:r24lag", "v[wsum(CSf, b_hi, b_lo) < 72] = np.nan;", "v[wsum(CSf, b_hi, b_lo) != 288] = np.nan;"),
    ("D8:RVj", "okj = (hi - 288 * 7 >= 0)", "RVn = np.stack([wsum(CSf, np.maximum(hi - 288*j, 0), np.maximum(hi - 288*(j+1), 0)) for j in range(7)]); RVj[RVn != 288] = np.nan; okj = (hi - 288 * 7 >= 0)"),
    ("D8:jump", "jp = 1 - bv / np.maximum(rv, 1e-18)", "jp = 1 - bv / np.maximum(rv, 1e-18); jp[wsum(CSf, hi, lo) != w] = np.nan"),
    ("D8:bv_lo", "bv = (np.pi / 2) * wsum(CSbv, hi, lo);", "bv = (np.pi / 2) * wsum(CSbv, hi, lo + 1);"),
    ("D8:ac1", "ac[wsum(CSboth, hi, lo + 1) < w // 4] = np.nan;", "ac[wsum(CSf, hi, lo) != w] = np.nan;"),
    ("D8:qv_populations", 'qv = np.where(finq, np.exp(lqz), 0.0); CSqv = cs(qv)', 'qv = np.where(finq, np.exp(lqz), 0.0); CSqv = cs(qv); rq = fin & finq; flowok = finq & fint; kyleok = fin & flowok; CSqv_r = cs(qv*rq); CSn_r = cs(rq.astype(float)); CSqv_flow = cs(qv*flowok); CSn_flow = cs(flowok.astype(float)); CSn_kyle = cs(kyleok.astype(float))'),
    ("D8:kyle_inputs", "CSs2 = cs(s ** 2); CSrs = cs(rz * s)", "CSs2 = cs(s ** 2 * kyleok); CSrs = cs(rz * s * kyleok)"),
    ("D8:amihud", 'a = wsum(CSabs, hi, lo) / np.maximum(wsum(CSqv, hi, lo), 1e-12); a[wsum(CSf, hi, lo) < w // 4]', 'a = wsum(CSabs_q, hi, lo) / np.maximum(wsum(CSqv_r, hi, lo), 1e-12); a[wsum(CSn_r, hi, lo) < w // 4]'),
    ("D8:kyle_gate", "k[wsum(CSf, hi, lo) < w // 4]", "k[wsum(CSn_kyle, hi, lo) < w // 4]"),
    ("D8:tbvw", 'v = wsum(CSs, hi, lo) / np.maximum(wsum(CSqv, hi, lo), 1e-12); v[wsum(CSft, hi, lo) < w // 4]', 'v = wsum(CSs, hi, lo) / np.maximum(wsum(CSqv_flow, hi, lo), 1e-12); v[wsum(CSn_flow, hi, lo) < w // 4]'),
    ("D8:tbac1", "ac[wsum(CSft, hi, lo) < 72] = np.nan;", "ac[wsum(CSft, hi, lo) != 288] = np.nan;"),
]

# NEW_S2 DEVIATION from derive_f8_candidate.py L21-L28, on lead's ruling DESIGN §E4(a)
# (2026-09-23, after the 24-anchor probe showed 2/24 anchors DO differ at the served row):
# the researcher's text computes the stable trend for every anchor row of the panel. The producer's
# mini pipeline throws all rows but the current anchor away (combo_stage extracts pair_a == a_i), and
# computing all ~240 rows costs +132% wall clock, which DESIGN §E makes the first deployment risk.
# So WHICH rows to compute becomes an explicit parameter, F8_TREND_ROWS:
#   "all"  (default) - the researcher's text, verbatim numerics, every row
#   "last"           - only the row the mini pipeline extracts
# Training replay and serving must pass the SAME value. Default is "all", so forgetting to set it is
# slow, never wrong. "last" is admissible only after news2_d7_rows_gate.py shows the extracted row is
# BITWISE equal between the two settings on the declared anchors (DESIGN §E4(a) admission gate).
D7_NEW = '''        from stable_trend_reference import stable_trend_block
        trend_lr = np.log1p(rz)
        _tr_rows = os.environ.get("F8_TREND_ROWS", "all")
        assert _tr_rows in ("all", "last"), f"F8_TREND_ROWS must be all|last, got {_tr_rows!r}"
        _ridx = np.arange(len(hi)) if _tr_rows == "all" else np.array([len(hi) - 1])
        for w in (288, 2016):
            tr = np.full((len(hi), nc), np.nan, np.float32)
            tr[_ridx] = np.concatenate([stable_trend_block(trend_lr, pm, hi[_ridx][k:k+128], w, chunk_syms=2) for k in range(0, len(_ridx), 128)], axis=0)
            tr[wsum(CSf, hi, lo_of(w)) != w] = np.nan
            put(f"C:trend_{w}", tr, chunk)
        del trend_lr
'''


def patch_f8(P):
    P.replace_region("D7:stable_trend", "        CSpm = cs(pmf);", '        touch("C", 0)', D7_NEW)
    for tag, old, new in D8_PATCHES:
        P.replace(tag, old, new)


# ----------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--member-screen-f64", choices=("yes", "no"), default="yes",
                    help="PREREG §1.4(a): whether D5/D6 also cover the member screen (L499-L507)")
    ap.add_argument("--shadow-base", choices=("ed11d731", "raw"), default="ed11d731",
                    help="raw = the unpatched producer file 6080073b, for the 'base swap is a no-op' gate")
    ap.add_argument("--trend-rows", choices=("all", "last"), default="last",
                    help="the F8_TREND_ROWS value the mini pipeline DECLARES (DESIGN E4(a)); the arms of "
                         "news2_d7_rows_gate.py differ in this literal, not in an environment variable")
    ap.add_argument("--only", default="",
                    help="comma-separated fix families to APPLY (D4,D5,D6,D7,D8,D9,D14); empty = all")
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    assert not out.exists(), f"refusing to overwrite {out}"

    srcs = {
        "shadow_loop_v3.py": BASE_SHADOW if args.shadow_base == "ed11d731" else (WIDE / "shadow_loop_v3.py"),
        "fea171/combo_stage.py": WIDE / "fea171/combo_stage.py",
        "fea171/dlw_features.py": WIDE / "fea171/dlw_features.py",
        "fea171/f8_higher_order_features.py": WIDE / "fea171/f8_higher_order_features.py",
        "fea171/stable_trend_reference.py": RESEARCH_TREE / "stable_trend_reference.py",
    }
    got = {k: sha_file(p) for k, p in srcs.items()}
    want = dict(SRC_SHA)
    if args.shadow_base == "raw":
        want["shadow_loop_v3.py"] = RAW_SHADOW_SHA
    for k, h in want.items():
        assert got[k] == h, ("source changed", k, got[k], h)
    assert sha_file(WIDE / "shadow_loop_v3.py") == RAW_SHADOW_SHA, "raw producer shadow_loop_v3.py changed"

    enabled = None
    if args.only.strip():
        enabled = set()
        for t in args.only.split(","):
            t = t.strip()
            if t:
                for fam in t.split("+"):
                    enabled.add(fam.strip())
        # the D5/D6 kernel edits are written as one text each, so D5 and D6 cannot be separated in
        # wstat / vol / member_screen; a subset naming either applies those shared cells.
    patchers = {}
    for name in ("shadow_loop_v3.py", "fea171/combo_stage.py", "fea171/dlw_features.py", "fea171/f8_higher_order_features.py"):
        patchers[name] = Patcher(name, srcs[name].read_text(), enabled)
    patch_shadow(patchers["shadow_loop_v3.py"], args.member_screen_f64 == "yes")
    patch_dlw(patchers["fea171/dlw_features.py"])
    patch_combo(patchers["fea171/combo_stage.py"], args.trend_rows)
    patch_f8(patchers["fea171/f8_higher_order_features.py"])

    (out / "fea171").mkdir(parents=True)
    written = {}
    for name, P in patchers.items():
        ast.parse(P.text, filename=name)           # combo_stage.py is a script, but it must still parse
        (out / name).write_text(P.text)
        written[name] = sha_bytes(P.text.encode())
    # stable_trend_reference.py is copied unchanged next to f8 (the D7 patch imports it from cwd)
    shutil.copyfile(srcs["fea171/stable_trend_reference.py"], out / "fea171/stable_trend_reference.py")
    written["fea171/stable_trend_reference.py"] = got["fea171/stable_trend_reference.py"]
    # every other file the producer's fea171 needs at run time, byte-copied
    copied = {}
    for extra in sorted(os.listdir(WIDE / "fea171")):
        src = WIDE / "fea171" / extra
        if src.is_file() and extra not in ("combo_stage.py", "dlw_features.py", "f8_higher_order_features.py"):
            shutil.copyfile(src, out / "fea171" / extra)
            copied[f"fea171/{extra}"] = sha_file(src)

    rec = {
        "device": "news2_derive_producer.py",
        "self_sha256": sha_file(os.path.abspath(__file__)),
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prereg": "docs/PREREG_new_servable_v2_features_2026-09-23.md",
        "config": {"out": str(out), "member_screen_f64": args.member_screen_f64,
                   "only": sorted(enabled) if enabled else "ALL", "shadow_base": args.shadow_base,
                   "trend_rows_declared": args.trend_rows},
        "sources": {k: {"path": str(v), "sha256": got[k]} for k, v in srcs.items()},
        "raw_producer_shadow_loop_v3_sha256": RAW_SHADOW_SHA,
        "outputs": written,
        "copied_unchanged": copied,
        "edits": {name: P.edits for name, P in patchers.items()},
        "n_edits": {name: len(P.edits) for name, P in patchers.items()},
        "n_applied": {name: sum(1 for e in P.edits if e["applied"]) for name, P in patchers.items()},
        "unchanged_vs_source": {name: (P.text == P.orig) for name, P in patchers.items()},
        "not_applied": ["D3 PatchedMarket routing", "D10 official intervals", "D2 per-anchor historical members",
                        "D12 funding rank base", "researcher CHUNK/threading/ThreadPoolExecutor/receipt-binding/savez_compressed"],
    }
    (out / "PATCH_RECEIPT.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
    print("PATCH_OK", json.dumps({"only": rec["config"]["only"], "n_applied": rec["n_applied"], "outputs": written}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
