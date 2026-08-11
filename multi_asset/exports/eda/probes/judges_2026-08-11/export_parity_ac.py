"""Export parity fixtures (v1 + v2) for the PRODFOLD generation. Piped over stdin, output /tmp.

Derived from ~/dl_quant_live/ops/export_parity_fixture.py (ff5ed2b44b9435f6). Four differences,
each deliberate:

 1. ★ mu/sd are LOADED from each run's `NORM_PRODFOLD.npz`, never derived. The original calls
    `data.set_fold(folds[4]["tr"])`, which RECOMPUTES the normalisation from the panel. A
    production fold has no fold 4 and its `te=[]` is constructive, so it cannot be witnessed on
    its own — the certified path is the NORM_PRODFOLD export program (max|d|=0 against the
    witnessed five folds). `set_fold` is therefore NOT called at all; it only ever set
    mu/sd/resid_sigma (verified by reading it), so skipping it changes nothing else.
 2. ★ The loaded mu/sd must hash-match the four files already staged for deployment. Two
    independently produced objects compared every run — without this the fixture and the shipped
    norms could drift apart silently and each would still look internally consistent.
 3. ★ Checkpoints are `fold_0_model.pt` (production folds store fold 0). NO renaming bridge:
    if a path is wrong this must fail loudly rather than silently pick a neighbouring file.
 4. PANEL is UNCHANGED from the old fixture (`exports/live/wide_dl_live.npz`, as-trained funding
    + centered ch31) even though the deployed generation trains on corrfund+causal. Reasons, both
    required: (a) the corrfund_causal panel ENDS 2026-06-30 and every v1 anchor plus the last two
    v2 anchors fall after it — they do not exist there; (b) this test's job is CROSS-BUILD
    REPRODUCTION (server CUDA torch vs local CPU on identical raw windows), which the window
    caliber does not enter. Holding the panel fixed also leaves the model generation as the ONLY
    variable between the old fixture and this one.
    ⇒ The fixture's windows are NOT in the caliber live will serve. Recorded in meta so nobody
      reads a green parity test as "the model was checked on deployment-caliber inputs".
"""
import sys, json, hashlib
import numpy as np

REPO = "/mnt/storage/private/work_hsy/quant_research_multi_asset"
MA = REPO + "/multi_asset"
sys.path.insert(0, REPO)
sys.path.insert(0, MA)
import torch
torch.backends.mkldnn.enabled = False
import multi_asset.train.train_wide_harness as th          # noqa: F401  (kept: same import set)
th.DEV = torch.device("cpu")
from multi_asset.data.wide_panel_dataset import WidePanelData
from multi_asset.model.wide_harness import WideFactorModel, ConformerPanelEncoder

PANEL = MA + "/exports/live/wide_dl_live.npz"              # see docstring point 4
TR = MA + "/exports/train"
SPECS = {
    "king": (TR + "/wideA_lamorth0_xattn_5yr_PRODFOLD_ac/fold_0_model.pt", 4, 8,
             TR + "/wideA_lamorth0_xattn_5yr_PRODFOLD_ac/NORM_PRODFOLD.npz"),
    "s2":   (TR + "/wideA_s2_y24_PRODFOLD_ac_val30/fold_0_model.pt", 24, 10,
             TR + "/wideA_s2_y24_PRODFOLD_ac_val30/NORM_PRODFOLD.npz"),
}
# 指纹取自已 staged 的部署件(team-lead 本机, 2026-08-04): 断言两条独立产出逐位相同
# _ac 世代的 NORM_PRODFOLD 指纹(2026-08-05 由认证过的导出程序产出, 服务器端逐位读取)
EXPECT = {"king_mu": "70cc462dae9a769d", "king_sd": "596fc3910911c838",
          "s2_mu":   "6bc416619881310c", "s2_sd":   "f20a93194fb37755"}
V2_TS = [1612051200000, 1625097600000, 1636761600000, 1656633600000, 1688169600000,
         1713139200000, 1719792000000, 1751328000000, 1782864000000, 1784678400000]
V2_KIND = ["sparsest_mask", "year_2021", "migration_dense_window", "year_2022", "year_2023",
           "migration_wave", "year_2024", "year_2025", "year_2026", "recent"]
W = 168
K1 = 3
OUT1, OUT2 = "/tmp/parity_fixture_ac.npz", "/tmp/parity_fixture_v2_ac.npz"


def sha16(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()[:16]


def build_model(ckpt):
    m = WideFactorModel(ConformerPanelEncoder(32, d=64, n_blocks=2, kernel_size=15, dropout=0.2),
                        n_factor_heads=6, xattn=True, n_xattn=1, dropout=0.2)
    m.load_state_dict(torch.load(ckpt, map_location="cpu"), strict=True)
    m.eval()
    return m


def composite(scores_bnk, base):
    comp = np.zeros(base.size); nk = 0
    for k in range(scores_bnk.shape[1]):
        col = scores_bnk[base, k]
        if np.isfinite(col).all() and col.std() > 1e-12:
            comp += (col - col.mean()) / col.std(); nk += 1
    return comp / nk if nk else None


def run_anchor(model, data, t):
    widx = t + np.arange(-W + 1, 1)
    Xseq = data.CH[widx].transpose(1, 0, 2)[None]
    Xn = np.clip((np.nan_to_num(Xseq) - data.mu) / data.sd, -10, 10).astype(np.float32)
    mask = data.member[t][None].astype(np.float32)
    with torch.no_grad():
        sc = model(torch.from_numpy(Xn), torch.from_numpy(mask))["factor_scores"][0].numpy()
    base = np.where(data.member[t])[0]
    return Xseq[0].astype(np.float32), mask[0], composite(sc, base).astype(np.float64), \
        base.astype(np.int32)


out1, out2, meta = {}, {}, {}
shared_done = False
for name, (ckpt, horizon, emb, normp) in SPECS.items():
    data = WidePanelData(path=PANEL, target_horizon=horizon)
    nz = np.load(normp)
    mu, sd = np.asarray(nz[f"{name}_mu"]), np.asarray(nz[f"{name}_sd"])
    for tag, arr in ((f"{name}_mu", mu), (f"{name}_sd", sd)):
        got = sha16(arr)
        if got != EXPECT[tag]:
            raise SystemExit(f"ABORT {tag}: NORM_PRODFOLD sha {got} != staged deployment sha "
                             f"{EXPECT[tag]}. The fixture and the shipped norms would disagree.")
    print(f"[norm] {name}: mu/sd match the staged deployment files bit-for-bit", flush=True)
    # ★ set_fold NOT called — it would derive mu/sd (docstring point 1)
    data.mu, data.sd = mu.astype(np.float32), sd.astype(np.float32)
    model = build_model(ckpt)

    # ── v1: last K1 anchors, per-model windows (original format) ──────────────────────────
    anchors = np.sort(np.where((data.member & data.CL).any(1))[0])
    a1 = [int(t) for t in anchors if t >= W - 1][-K1:]
    wins, masks = [], []
    for i, t in enumerate(a1):
        w, mk, c, b = run_anchor(model, data, t)
        wins.append(w); masks.append(mk)
        out1[f"{name}_composite_{i}"] = c; out1[f"{name}_base_{i}"] = b
    out1[f"{name}_mu"] = data.mu; out1[f"{name}_sd"] = data.sd
    out1[f"{name}_windows"] = np.stack(wins); out1[f"{name}_masks"] = np.stack(masks)
    out1[f"{name}_anchors"] = np.array(a1, np.int64)
    out1[f"{name}_ts"] = data.ts[a1].astype(np.int64)

    # ── v2: the SAME 10 timestamps as the incumbent fixture, mapped by ts (breadth preserved
    #        by construction, not by re-deriving a selection rule we do not have) ───────────
    ts_all = data.ts.astype(np.int64)
    idx = []
    for t_ms in V2_TS:
        hit = np.where(ts_all == t_ms)[0]
        if hit.size != 1:
            raise SystemExit(f"ABORT v2: ts {t_ms} maps to {hit.size} rows in {PANEL}")
        idx.append(int(hit[0]))
    w2, m2 = [], []
    for i, t in enumerate(idx):
        w, mk, c, b = run_anchor(model, data, t)
        w2.append(w); m2.append(mk)
        out2[f"{name}_composite_{i}"] = c; out2[f"{name}_base_{i}"] = b
    out2[f"{name}_mu"] = data.mu; out2[f"{name}_sd"] = data.sd
    if not shared_done:
        out2["windows"] = np.stack(w2); out2["masks"] = np.stack(m2)
        out2["anchor_idx"] = np.array(idx, np.int64)
        out2["anchor_ts"] = np.array(V2_TS, np.int64)
        out2["anchor_kind"] = np.array(V2_KIND, dtype=object)
        out2["anchor_n4"] = np.array([int(m.sum()) for m in m2], np.int64)
        out2["symbols"] = np.array([str(s) for s in data.symbols], dtype=object)
        out2["ch_names"] = np.array([str(c) for c in data.ch_names], dtype=object)
        shared_done = True
    else:
        prev = out2["windows"]
        same = bool(np.array_equal(prev, np.stack(w2)))
        print(f"[v2] shared windows identical across models: {same}", flush=True)
        if not same:
            raise SystemExit("ABORT v2: the two models saw different raw windows at the same "
                             "anchors — the shared-window format would be a lie.")

    meta[name] = {"ckpt": ckpt, "norm": normp, "horizon": horizon, "embargo": emb,
                  "n_anchors_v1": len(a1), "n_anchors_v2": len(idx),
                  "mu_sha16": sha16(mu), "sd_sha16": sha16(sd),
                  "torch": torch.__version__, "numpy": np.__version__}
    print(f"[export] {name}: v1 {len(a1)} anchors, v2 {len(idx)} anchors", flush=True)
    nz.close()

hdr = {"generation": "PRODFOLD _ac (S2 generation: data to 2026-07-31, corrfund+causal, arm=xattn)",
       "panel": PANEL,
       "panel_caliber": "as_trained funding + CENTERED ch31 — deliberately UNCHANGED from the "
                        "incumbent fixture. NOT the caliber live serves. See export docstring "
                        "point 4: the corrfund_causal panel ends 2026-06-30 and every v1 anchor "
                        "falls after it; and this test measures cross-build reproduction, which "
                        "the window caliber does not enter.",
       "norms": "loaded from each run's NORM_PRODFOLD.npz and asserted bit-identical to the "
                "files staged for deployment; NOT derived via set_fold",
       "models": meta}
# ★ v1 and v2 carry DIFFERENT meta shapes and the readers are not interchangeable:
#   tests_inference_parity line 72 reads v1 as meta['king']['torch'] (FLAT), while the v2 block
#   reads meta['models'][...]. Writing v2's shape into v1 raises KeyError('king') — which is what
#   happened on the first export. Both shapes are emitted verbatim as each reader expects.
out1["meta_json"] = np.array(json.dumps({**meta, **hdr, "variant": "v1"}), dtype=object)
out2["meta_json"] = np.array(json.dumps({**hdr, "variant": "v2"}), dtype=object)
np.savez_compressed(OUT1, **out1)
np.savez_compressed(OUT2, **out2)
for p in (OUT1, OUT2):
    print(f"[out] {p}  sha256={hashlib.sha256(open(p,'rb').read()).hexdigest()}", flush=True)
