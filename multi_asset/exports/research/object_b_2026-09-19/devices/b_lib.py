#!/usr/bin/env python3
"""Object B shared library (PREREG_object_B_recipe_oof_and_object_A_paper_2026-09-19 §1–§3, AMENDMENT 1).
Used by the history driver (b_driver.py), the F10 scorer pool (b_scorer.py) and the parity gate (gate_f.py) — the SAME functions serve the
gate and the history, so the gate certifies the history path.

  LiveEquiv        live-equivalent cache rule + base list (S4): a cell is NaN when the venue had no such contract (before the first traded bar;
                   after the last traded bar of a dead contract); base(A) = alive COIN names ∪ symbols_live(A)
  FoldBooster      king scorer passed as the producer's `booster` argument: predict(X) on the producer's OWN serving features; per anchor the
                   latest fold whose label_end < A − 30 d (mode 'folds'), or one booster for every anchor (mode 'live', gate only)
  f10_fold_for     F10 fold rule: latest fold whose label_end < first second of A's month
  combo sandbox helpers   write_combo_inputs / write_f10_injection / write_identity_model / run_device / read_target
No function here reads or writes a production file; callers pass explicit paths."""
import os, sys, json, time, hashlib, calendar, shutil, subprocess
import numpy as np

H4 = 14400; DAY = 86400


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 24), b""): h.update(ch)
    return h.hexdigest()


def iso(t): return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t)))
def month_start(t): g = time.gmtime(int(t)); return calendar.timegm((g.tm_year, g.tm_mon, 1, 0, 0, 0))


# ─────────────────────────── S4 live-equivalent cache and base list ───────────────────────────
class LiveEquiv:
    """tradability_v1 (54d409d0…): first_traded_ts / last_traded_ts per name (bar close times on the cache axis), data_end_ts.
    dead(s) <=> last_traded_ts[s] < data_end − 3 d. Non-COIN(s) <=> exists t: UPIT[t, s] and not UPIT_CRYPTO[t, s] (never-in-UPIT => kept)."""
    def __init__(self, trd_path, upit_path, crypto_path, syms):
        T = np.load(trd_path, allow_pickle=True)
        assert [str(s) for s in T["symbols"]] == list(syms), "tradability symbol axis"
        self.first = T["first_traded_ts"].astype(np.int64); self.last = T["last_traded_ts"].astype(np.int64)
        self.data_end = int(T["data_end_ts"])
        self.never = (self.first <= 0) | (self.last <= 0)
        self.dead = (~self.never) & (self.last < self.data_end - 3 * DAY)
        U = np.load(upit_path, allow_pickle=True); C = np.load(crypto_path, allow_pickle=True)
        assert [str(s) for s in U["symbols"]] == list(syms) and [str(s) for s in C["symbols"]] == list(syms)
        assert np.array_equal(U["ts"], C["ts"])
        Um = np.asarray(U["mask"], bool); Cm = np.asarray(C["mask"], bool)
        assert not (Cm & ~Um).any(), "UPIT_CRYPTO must be a subset of UPIT"
        self.noncoin = (Um & ~Cm).any(0)
        self.syms = list(syms)

    def nan_ranges(self, ts):
        """[(j, lo, hi)] row ranges [lo, hi) on the ts axis to be set NaN."""
        out = []
        for j in range(len(self.syms)):
            if self.never[j]:
                out.append((j, 0, len(ts))); continue
            lo = int(np.searchsorted(ts, self.first[j], side="left"))
            if lo > 0: out.append((j, 0, lo))
            if self.dead[j]:
                hi = int(np.searchsorted(ts, self.last[j], side="right"))
                if hi < len(ts): out.append((j, hi, len(ts)))
        return out

    def apply_inplace(self, data, ts):
        """data[T, 829, C] (float16) in place; returns per-year counts of cells that were finite (any channel) and became NaN."""
        years = np.array([time.gmtime(int(t)).tm_year for t in ts[::288]]); yr_of_row = np.repeat(years, 288)[:len(ts)]
        changed = {}
        for j, lo, hi in self.nan_ranges(ts):
            seg = data[lo:hi, j, :]
            fin = np.isfinite(seg.astype(np.float32)).any(1)
            if fin.any():
                for y, c in zip(*np.unique(yr_of_row[lo:hi][fin], return_counts=True)): changed[int(y)] = changed.get(int(y), 0) + int(c)
            data[lo:hi, j, :] = np.nan
        return changed

    def alive(self, A):
        A = int(A)
        return (~self.never) & (self.first <= A) & ~(self.dead & (A > self.last))

    def base(self, A):
        m = self.alive(A) & ~self.noncoin
        return [self.syms[j] for j in np.where(m)[0]]


# ─────────────────────────── king ───────────────────────────
def king_label_ends(meta_path, years=(2023, 2024, 2025, 2026)):
    """fold Y trains on rows with anchor-year < Y; its last training anchor = last year<Y anchor with >= 50 finite labels among members;
    label_end = that anchor + 4h (the exporter's own row filter, pod_export_bundle_v3.py L39–42)."""
    M = np.load(meta_path, allow_pickle=True); E = M["E_ts"].astype(np.int64); mem = M["members"]; y4 = M["y4"]
    yrs = np.array([time.gmtime(int(t)).tm_year for t in E]); out = {}
    for Y in years:
        idx = [i for i in np.where(yrs < Y)[0] if np.isfinite(y4[i, np.asarray(mem[i], np.int64)]).sum() >= 50]
        out[int(Y)] = int(E[max(idx)]) + H4
    return out


class FoldBooster:
    """`booster` argument of the producer's run_anchor. predict(X): X = FE_ANCH[:, keep] computed by the producer for its members m.
    mode 'folds': latest fold Y with label_end[Y] < anchor − 30 d; none ⇒ all-NaN (king leg neutral, production xz semantics).
    mode 'live' : the single in-service booster for every anchor (parity gate only; NEVER used for object-B history)."""
    def __init__(self, mode, files, label_ends=None):
        import lightgbm as lgb
        assert mode in ("folds", "live")
        self.mode = mode; self.files = dict(files); self.shas = {k: sha(v) for k, v in self.files.items()}
        self.b = {k: lgb.Booster(model_file=v) for k, v in self.files.items()}
        self.label_ends = dict(label_ends or {}); self.last = None
        if mode == "live": assert list(self.files) == ["live"]
        else: assert set(self.files) <= set(self.label_ends)

    def select(self, A):
        if self.mode == "live": return "live", None
        adm = [Y for Y in sorted(self.b) if self.label_ends[Y] < int(A) - 30 * DAY]
        return (adm[-1], self.label_ends[adm[-1]]) if adm else (None, None)

    def predict(self, X):
        f = sys._getframe(1)
        assert f.f_code.co_name == "run_anchor", f.f_code.co_name
        A = int(f.f_locals["anchor"]); m = np.asarray(f.f_locals["m"], np.int64)
        assert X.shape[0] == len(m), (X.shape, len(m))
        Y, le = self.select(A)
        out = np.full(len(m), np.nan) if Y is None else self.b[Y].predict(X)
        self.last = {"anchor": A, "n_members": int(len(m)), "fold": Y, "label_end": le, "n_finite": int(np.isfinite(out).sum()),
                     "model_sha": self.shas.get(Y) if Y is not None else None}
        return out


# ─────────────────────────── F10 ───────────────────────────
def f10_fold_for(A, folds):
    """folds: {Y: {"np": path, "label_end": ts}}; latest Y with label_end < month_start(A); None if none."""
    ms = month_start(A); adm = [Y for Y in sorted(folds) if int(folds[Y]["label_end"]) < ms]
    return adm[-1] if adm else None


# ─────────────────────────── combo sandbox helpers ───────────────────────────
def write_f10_injection(fea_dir, A, pm, scores):
    """S2 I2 injection (G2-C′ exact): one row per member with a finite score; column 0 = its average rank / 128; identity model elsewhere.
    The combo stage uses f10 only through rankdata(f10_pm[okf]) (L175–176) ⇒ zf is bitwise the production zf of `scores`."""
    from scipy.stats import rankdata
    v = np.asarray(scores, np.float64); ok = np.isfinite(v); n = int(ok.sum())
    x = np.zeros(n, np.float32)
    if n:
        rk = rankdata(v[ok]); x = (rk / 128.0).astype(np.float32)
        assert np.all(x * 128.0 == rk) and x.max() <= 4.0, "rank encoding not exact"
    md = f"{fea_dir}/mini/data"; os.makedirs(md, exist_ok=True)
    X82 = np.zeros((n, 82), np.float32); X82[:, 0] = x
    np.savez(f"{md}/dlw_targets.npz", E_ts=np.array([int(A)], np.int64))
    np.savez(f"{md}/dlw_fea82.npz", pair_a=np.zeros(n, np.int64), pair_s=np.asarray(pm, np.int64)[ok], X=X82)
    np.savez(f"{md}/f8_fea89.npz", X=np.zeros((n, 89), np.float32))
    return n


def write_identity_model(path):
    w0 = np.zeros((1, 171)); w0[0, 0] = 1.0
    np.savez(path, mu=np.zeros(171), sd_=np.ones(171), w0=w0, b0=np.array([13.0]), w1=np.array([[1.0]]), b1=np.array([0.0]), w2=np.array([[1.0]]), b2=np.array([-13.0]))
    return sha(path)


def clear_mini(fea_dir):
    """★ the parity lesson of 2026-09-18: a sandbox must never carry a mini cache from another anchor (need=False would reuse later features)."""
    for sub in ("mini", ):
        p = f"{fea_dir}/{sub}"
        if os.path.isdir(p): shutil.rmtree(p)
    for f in ("xfer_panel_live.npz",):
        if os.path.exists(f"{fea_dir}/{f}"): os.remove(f"{fea_dir}/{f}")


def make_sandbox(root, fea171_src, bundle_cfg, venv_python, reader_src=None):
    """root/{wide_shadow/{state,fea171,shadow_bundle,venv/bin/python}, dl_quant_live/live}. fea171_src: dict name -> path (pipeline scripts, xfer files)."""
    ws = f"{root}/wide_shadow"
    for d in (f"{ws}/state/weights", f"{ws}/state/target_live", f"{ws}/fea171", f"{ws}/shadow_bundle", f"{ws}/venv/bin", f"{root}/dl_quant_live/live"):
        os.makedirs(d, exist_ok=True)
    for name, src in fea171_src.items():
        dst = f"{ws}/fea171/{name}"
        if not os.path.exists(dst): shutil.copy2(src, dst)
    if not os.path.exists(f"{ws}/shadow_bundle/config.json"): shutil.copy2(bundle_cfg, f"{ws}/shadow_bundle/config.json")
    if not os.path.lexists(f"{ws}/venv/bin/python"): os.symlink(venv_python, f"{ws}/venv/bin/python")
    for name, src in (reader_src or {}).items():
        dst = f"{root}/dl_quant_live/live/{name}"
        if not os.path.exists(dst): shutil.copy2(src, dst)
    return ws


def run_device(script, cwd, env, log_path, timeout=900):
    t0 = time.time()
    with open(log_path, "w") as lf:
        p = subprocess.run([env.get("_PY", sys.executable), "-B", script], cwd=cwd, env={k: v for k, v in env.items() if not k.startswith("_")},
                           stdout=lf, stderr=subprocess.STDOUT, timeout=timeout)
    lines = open(log_path, errors="replace").read().strip().splitlines()
    return p.returncode, lines, round(time.time() - t0, 2)


def target_weights(path):
    d = json.load(open(path)); return d, {k: float(v) for k, v in d["weights"].items()}


def compare_targets(arch_path, rep_path, allow_missing_f10_sha_before=None):
    """combo_parity_compare.py semantics: every key equal except written_utc; weights name by name as exact floats; f10_sha absent in an archive
    written before `allow_missing_f10_sha_before` (the FP2-6b producer patch) is a recorded version delta, not a mismatch."""
    a, wa = target_weights(arch_path); b, wb = target_weights(rep_path)
    why = []; names = sorted(set(wa) | set(wb)); nd = 0; mx = 0.0
    for n in names:
        if n not in wa or n not in wb or wa[n] != wb[n]:
            nd += 1; mx = max(mx, abs(wa.get(n, 0.0) - wb.get(n, 0.0)))
    if nd: why.append(f"weights: {nd} names differ, max|dw| {mx:.3e}")
    vd = []
    for k in sorted(set(a) | set(b)):
        if k in ("written_utc", "weights"): continue
        if k not in a or k not in b:
            if k == "f10_sha" and k in b and allow_missing_f10_sha_before and str(a.get("written_utc", "")) < allow_missing_f10_sha_before:
                vd.append("f10_sha added by the FP2-6b producer patch after this archive was written"); continue
            why.append(f"{k}: present only in {'archived' if k in a else 'replay'}"); continue
        if a[k] != b[k]: why.append(f"{k}: archived {str(a[k])[:24]} != replay {str(b[k])[:24]}")
    return {"n_archived": len(wa), "n_replay": len(wb), "n_differing": nd, "max_abs_dw": mx, "why": why, "version_delta": vd,
            "archived_sha": sha(arch_path), "replayed_sha": sha(rep_path), "PARITY": not why}


# ─────────────────────────── GATE F comparator, AMENDMENT 2 (A2.1) ───────────────────────────
def _naive_sum(xs):
    s = 0.0
    for x in xs: s += x
    return s


def _neumaier_sum(xs):          # CPython >= 3.12 builtin sum() over floats (gh-100425)
    s = 0.0; c = 0.0
    for x in xs:
        t = s + x
        if abs(s) >= abs(x): c += (s - t) + x
        else: c += (x - t) + s
        s = t
    return s + c


def compare_targets_a2(arch_path, rep_path, col, mode, allow_missing_f10_sha_before=None):
    """PREREG AMENDMENT 2 A2.1. mode: 'inject' | 'pipeline' | 'kingfile'. Weights must be name-by-name bitwise (never relaxed)."""
    a, wa = target_weights(arch_path); b, wb = target_weights(rep_path)
    names = sorted(set(wa) | set(wb)); nd = 0; mx = 0.0
    for n in names:
        if n not in wa or n not in wb or wa[n] != wb[n]:
            nd += 1; mx = max(mx, abs(wa.get(n, 0.0) - wb.get(n, 0.0)))
    why = [f"weights: {nd} names differ, max|dw| {mx:.3e}"] if nd else []
    req = ["schema", "anchor_ts", "n_names", "universe", "universe_sha", "n_universe", "booster_sha", "producer", "weights_sha"]
    for k in req:
        if a.get(k) != b.get(k): why.append(f"{k}: archived {str(a.get(k))[:24]} != replay {str(b.get(k))[:24]}")
    f10 = {"archived": a.get("f10_sha"), "replay": b.get("f10_sha")}
    if mode == "pipeline":
        if "f10_sha" in a and a.get("f10_sha") != b.get("f10_sha"): why.append("f10_sha differs (pipeline mode)")
        if "f10_sha" not in a and not (allow_missing_f10_sha_before and str(a.get("written_utc", "")) < allow_missing_f10_sha_before) and "f10_sha" in b:
            why.append("f10_sha absent in archive written after the FP2-6b patch")
    order = sorted(wb, key=lambda s: col[s]); xs = [abs(float(wb[s])) for s in order]
    g = {"archived": a.get("gross_norm"), "replay": b.get("gross_norm"), "naive": _naive_sum(xs), "neumaier": _neumaier_sum(xs)}
    if a.get("gross_norm") == b.get("gross_norm"): g["rule"] = "equal"
    elif (not nd) and b.get("gross_norm") == g["naive"] and a.get("gross_norm") == g["neumaier"]: g["rule"] = "explained_cpython_sum_D13"
    else:
        g["rule"] = "UNEXPLAINED"; why.append("gross_norm differs and is not the CPython naive-vs-Neumaier sum of the same |w|")
    literal = [k for k in sorted(set(a) | set(b)) if k != "written_utc" and a.get(k) != b.get(k)]
    return {"n_archived": len(wa), "n_replay": len(wb), "n_differing": nd, "max_abs_dw": mx, "weights_bitwise": nd == 0 and len(wa) == len(wb),
            "why": why, "f10_sha": f10, "gross_norm": g, "literal_all_keys_equal": not literal, "literal_differing_keys": literal,
            "archived_sha": sha(arch_path), "replayed_sha": sha(rep_path), "PARITY": not why}
