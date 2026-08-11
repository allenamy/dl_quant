"""配对世代 IC —— 【每一代在自己的家面板上】。修正 paired_gen_backfill.py 的口径混杂。

★ 为什么原仪器不成立(代码层面确证, 非推断)
`deff3bb` 在同一个提交里改了 checkpoints 和 signal/panel_build.py 两处通道构建:
  (1) 新增 `PANEL_CALIBER = "normfix"`(此前 as_trained)。代码自注: "A mismatch is silent —
      ch0 moves ~45% in sd."
  (2) ch31: np.convolve(..., "same")  →  np.convolve(..., "full")[:len]
      即 centered(含 11h 未来)→ trailing-24。代码自注: "Serving the centered form to a
      trailing-trained model is a train/serve mismatch on 155 of the model's 168 window rows."
原回填用【当前】panel_build 建一个面板给两代打分 ⇒ 新代匹配、旧代在两个轴上都失配,
而旧代实盘时看的是它自己的老面板。⇒ +0.0979 vs +0.0585 不能当模型比较读。

★ 本仪器
  臂A 新代(45f08e81/f0ca61f5) × 家面板(normfix + trailing)   = 实盘 2026-08-05 12:00Z 之后的条件
  臂B 旧代(5a7b27d9/8b1bc1ab) × 家面板(as_trained + centered) = 实盘 08-05 12:00Z 之前的条件
  同锚 · 同成员掩码(取自臂A, 强制一致) · 同 CLOSE 标的 ⇒ 差 = 【整包】差, 这是可部署单元。

★ 判据(沿用原脚本事前冻结的那一条, 一字不改):
  窗口 = anchors ≥ 2026-08-01T00:00Z(对两代都严格 OOS)
  方向性主张需 |t| ≥ 2.0 且同号 ≥ 60%; 否则报 CANNOT DISTINGUISH。
  ★ 新增只有一条【断言】不是判据: 两个面板必须真的不同(见 §断言), 否则本次作废。

★ 它仍不能分离: 干净口径 vs 多一个月数据。整包是问题的正确单元, 但不得读出"口径值 X"。
"""
import json, os, sys, types
import numpy as np

REPO = os.path.expanduser("~/dl_quant_live")
sys.path[:0] = [os.path.join(REPO, "signal"), os.path.join(REPO, "live"), REPO]
PB_PATH = os.path.join(REPO, "signal", "panel_build.py")

NEW_DIR = os.path.join(REPO, "checkpoints")
OLD_DIR = os.path.join(REPO, "rollback_batch1_20260804T145921Z", "checkpoints")
CUTOFF_MS = 1785542400000          # 2026-08-01T00:00:00Z
HOURS = 1200
FLOOR = 887
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paired_gen_homepanel.json")

NEW_SRC_MARK = 'np.convolve(np.nan_to_num(market), np.ones(24), "full")[:len(market)]'
OLD_SRC_MARK = 'np.convolve(np.nan_to_num(market), np.ones(24), "same")'


def install_panel_build(caliber, ch31_mode):
    """把 panel_build 换成指定口径的一份, 并清掉依赖它的模块以便重新导入。"""
    src = open(PB_PATH).read()
    if 'PANEL_CALIBER = "normfix"' not in src:
        raise RuntimeError("panel_build 里找不到 PANEL_CALIBER 常量 —— 代码已变, 本仪器作废")
    if NEW_SRC_MARK not in src:
        raise RuntimeError("panel_build 里找不到 ch31 的 full 卷积行 —— 代码已变, 本仪器作废")
    src = src.replace('PANEL_CALIBER = "normfix"', f'PANEL_CALIBER = "{caliber}"')
    if ch31_mode == "same":
        src = src.replace(NEW_SRC_MARK, OLD_SRC_MARK)
    for m in ("live_panel", "panel_build", "assert_funding_dim"):
        sys.modules.pop(m, None)
    mod = types.ModuleType("panel_build")
    mod.__file__ = PB_PATH
    sys.modules["panel_build"] = mod
    exec(compile(src, PB_PATH, "exec"), mod.__dict__)
    import importlib
    lp = importlib.import_module("live_panel")
    return mod, lp


def rank_ic(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 10:
        return np.nan
    x, y = a[m], b[m]
    rx = np.argsort(np.argsort(x)).astype(float); ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean(); ry -= ry.mean()
    d = np.sqrt((rx * rx).sum() * (ry * ry).sum())
    return float((rx * ry).sum() / d) if d > 0 else np.nan


def build(caliber, ch31_mode, tag):
    PB, LP = install_panel_build(caliber, ch31_mode)
    import fapi_source as FS
    src = FS.FapiSource()
    print(f"[{tag}] building panel  caliber={caliber} ch31={ch31_mode} ...", flush=True)
    b = LP.build_live_panel(src, hours=HOURS, refresh=False, progress=lambda m: None)
    tradable = None
    try:
        tradable = set(src.perp_symbols())
    except Exception:
        pass
    mem = PB.derive_member(b["DVOL30"], b["CLOSE"], symbols=b["symbols"], tradable=tradable)
    print(f"[{tag}] T={len(b['ts'])} N={len(b['symbols'])} "
          f"{np.datetime64(int(b['ts'][0]),'ms')}..{np.datetime64(int(b['ts'][-1]),'ms')}", flush=True)
    return b, mem


A, memA = build("normfix", "full", "新代家面板")
B, memB = build("as_trained", "same", "旧代家面板")

# ═══════════════ 断言: 两个面板必须真的不同, 否则"每代在自己家"是空话 ═══════════════
tsA, tsB = np.asarray(A["ts"]), np.asarray(B["ts"])
assert np.array_equal(tsA, tsB), "两面板时间轴不同 ⇒ 无法同锚比较"
assert A["symbols"] == B["symbols"], "两面板 symbol 顺序不同"
CA, CB = A["CH"], B["CH"]
names = A["ch_names"] if "ch_names" in A else None
i31 = names.index("betaadj_ret24") if names else 31
i0 = 0
d31 = float(np.nanmax(np.abs(CA[:, :, i31] - CB[:, :, i31])))
d0 = float(np.nanmax(np.abs(CA[:, :, i0] - CB[:, :, i0])))
print(f"\n断言 · 面板差异  max|Δch31|={d31:.6g}   max|Δch0|={d0:.6g}")
assert d31 > 0, "★ ch31 两面板完全相同 ⇒ 口径切换没生效(很可能被缓存吃了), 本次作废"
assert d0 > 0, "★ ch0 两面板完全相同 ⇒ funding 口径切换没生效, 本次作废"
assert np.allclose(np.asarray(A["CLOSE"], float), np.asarray(B["CLOSE"], float),
                   equal_nan=True), "CLOSE 不同 ⇒ 标的不可比"
print("断言通过: 两个面板确实不同, 标的相同\n")

import inference as INF
gens = {}
for tag, d in (("new", NEW_DIR), ("old", OLD_DIR)):
    gens[tag], _ = INF.load(stats_path=os.path.join(d, "norm_stats.npz"), ckpt_dir=d)
    print(f"loaded {tag}: {d}")

syms = A["symbols"]
CLOSE = np.asarray(A["CLOSE"], float)
idx = [i for i in range(FLOOR, len(tsA) - 4)
       if int(tsA[i]) % (4 * 3600 * 1000) == 0 and int(tsA[i]) >= CUTOFF_MS]
print(f"\n{len(idx)} anchors in the common-OOS window\n")

PAN = {"new": (CA, memA), "old": (CB, memB)}      # ★ 每代取自己的家面板
rows = []
for i in idx:
    mask = memA[i].astype(np.float32)             # ★ 掩码统一取臂A, 强制两臂成员集合相同
    if mask.sum() < 20:
        continue
    y = np.full(len(syms), np.nan)
    c0, c1 = CLOSE[i], CLOSE[i + 4]
    ok = np.isfinite(c0) & np.isfinite(c1) & (c0 > 0)
    y[ok] = c1[ok] / c0[ok] - 1.0
    y[mask < 0.5] = np.nan
    rec = {"ts": int(tsA[i]), "utc": str(np.datetime64(int(tsA[i]), "ms")),
           "n_members": int(mask.sum())}
    comp = {}
    for tag in ("new", "old"):
        CHt = PAN[tag][0]
        window = CHt[i - INF.W + 1: i + 1].transpose(1, 0, 2)
        per_leg = {}
        for leg in ("king", "s2"):
            c, base, _ = gens[tag][leg].composite(window, mask)
            v = np.full(len(syms), np.nan)
            if c is not None:
                v[np.asarray(base)] = c
            per_leg[leg] = v
            rec[f"ic_{leg}_{tag}"] = rank_ic(v, y)
        z = []
        for leg in ("king", "s2"):
            v = per_leg[leg][mask > 0.5]
            s = np.nanstd(v)
            z.append((v - np.nanmean(v)) / s if s > 0 else v * np.nan)
        cm = np.nansum(np.vstack(z), axis=0)
        full = np.full(len(syms), np.nan); full[mask > 0.5] = cm
        comp[tag] = rank_ic(full, y)
        rec[f"ic_dl_{tag}"] = comp[tag]
    rec["d_dl"] = comp["new"] - comp["old"]
    rows.append(rec)
    print(f"  {rec['utc']}  n={rec['n_members']:3d}  dl new={comp['new']:+.4f} "
          f"old={comp['old']:+.4f}  Δ={rec['d_dl']:+.4f}", flush=True)

d = np.array([r["d_dl"] for r in rows], float); d = d[np.isfinite(d)]
n = len(d)
t = float(d.mean() / (d.std(ddof=1) / np.sqrt(n))) if n > 1 and d.std(ddof=1) > 0 else np.nan
win = float((d > 0).mean())
print("\n" + "=" * 78)
print(f"配对(各自家面板)  n={n}  Δ(new−old) = {d.mean():+.5f}  t = {t:+.2f}  新胜 = {win:.0%}")
for tag in ("new", "old"):
    for leg in ("dl", "king", "s2"):
        v = np.array([r.get(f"ic_{leg}_{tag}") for r in rows], float); v = v[np.isfinite(v)]
        print(f"  {tag:3s} {leg:5s} mean IC = {v.mean():+.5f}  (n={len(v)})")
verdict = ("DIRECTIONAL" if (np.isfinite(t) and abs(t) >= 2.0 and max(win, 1 - win) >= 0.60)
           else "CANNOT DISTINGUISH")
print(f"\n事前判据(原脚本冻结, 未改): {verdict}  "
      f"(需 |t|>=2.0 且同号>=60%; 得 |t|={abs(t):.2f}, {max(win,1-win):.0%})")
print("=" * 78)
json.dump({"rows": rows, "n": n, "mean_delta": float(d.mean()), "t": t, "new_win_rate": win,
           "verdict": verdict, "panel_diff": {"max_abs_dch31": d31, "max_abs_dch0": d0},
           "design": "each generation scored on ITS OWN home panel caliber",
           "arms": {"new": "normfix + trailing ch31", "old": "as_trained + centered ch31"}},
          open(OUT, "w"), indent=1)
print(f"wrote {OUT}\nHOMEPANEL_DONE")
