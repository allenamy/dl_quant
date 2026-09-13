#!/usr/bin/env python3
"""fm_facts_code.py — FIXPROGRAM 2026-09-13, FX-MODEL, §0.1 fact table part 1 (code). READ-ONLY on every file it opens.

Items: FEA-01 (DL funding inputs = look-ahead name list), TIM-01 (king train/serve clock), UNI-01 (non-crypto training members),
TRD-05 + TRN-06 (dead / forward-finite member selection), P10 (king f16 storage vs f32 serving).
For each row: the claim, and anchors located by exact substring (never by remembered line number). Each anchor records file:line,
the verbatim line, the file's guarded sha256 (refuses APFS-dataless files and short reads, T6 guard rule) and, for repository files,
the HEAD blob id. An anchor that is absent or not unique is a hard error (rc 3). Production files (~/wide_shadow) are opened read-only.
No data file and no result receipt is opened; no number about model or book performance is computed or printed.

Usage: python3 -B fm_facts_code.py <out.json>     (prints one SUMMARY line; rc 0 only when every anchor is found exactly once)
"""
import os, sys, json, stat, hashlib, subprocess, time

REPO = "/Users/haosiyu/Desktop/quant_research"
WS = os.path.expanduser("~/wide_shadow")
RT = "multi_asset/exports/research/retrain_2026-09"
V4 = RT + "/v4_chain_2026-09-09"
SF_DATALESS = getattr(stat, "SF_DATALESS", 0x40000000)


def _abs(p):
    return p if os.path.isabs(p) else os.path.join(REPO, p)


def guarded_sha(p):
    ap = _abs(p); st = os.stat(ap)
    if st.st_flags & SF_DATALESS:
        raise SystemExit("REFUSE %s: APFS dataless (brctl download first)" % p)
    h = hashlib.sha256(); n = 0
    with open(ap, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b); n += len(b)
    if n != st.st_size:
        raise SystemExit("REFUSE %s: read %d of %d bytes" % (p, n, st.st_size))
    return h.hexdigest()


def head_blob(p):
    if os.path.isabs(p):
        return None
    r = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD:" + p], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def locate(p, needle):
    lines = open(_abs(p), encoding="utf-8").read().split("\n")
    hits = [i + 1 for i, s in enumerate(lines) if needle in s]
    if len(hits) != 1:
        raise SystemExit("ANCHOR_FAIL %r in %s: %d hits %s" % (needle[:80], p, len(hits), hits[:6]))
    return hits[0], lines[hits[0] - 1].strip()


SL = WS + "/shadow_loop_v3.py"; CB = WS + "/fea171/combo_stage.py"; DF = WS + "/fea171/dlw_features.py"

ROWS = [
    # ───────────────────────────── FEA-01: DL funding inputs ─────────────────────────────
    dict(id="C-FEA-1", item="FEA-01", claim="fea82 builder copies the panel's f_fund_ema / f_fund_now into cols 80/81 with NaN -> 0.0 and an anchor without a panel row -> 0.0; no availability column exists",
         anchors=[(RT + "/pod_dlw_features_ext.py", 'FUND = [PW["f_fund_ema"].astype(np.float32), PW["f_fund_now"].astype(np.float32)]; fund_names = ["fund_ema", "fund_now"]'),
                  (RT + "/pod_dlw_features_ext.py", "X[sl, col] = 0.0 if j is None else np.nan_to_num(fv[j, m], nan=0.0); col += 1"),
                  (RT + "/pod_dlw_features_ext.py", "assert NF == 82 and len(names) == 82, (NF, len(names))")]),
    dict(id="C-FEA-2", item="FEA-01", claim="the v4 / monthly chain builds fea82 from PANEL_SPLICE; September env = wide_panel_4h_v3splice.npz; the October template keeps a v3splice panel",
         anchors=[(V4 + "/chain_v4_monthly.sh", 'F171_CACHE=$CACHE F171_PANEL=$PANEL_SPLICE F171_OUT=$DLW_CLIP "$PY" "$BUILDER_FEA82"'),
                  (V4 + "/v4_month_2026-09.env", "PANEL_SPLICE=/workspace/data/wide_panel_4h_v3splice.npz"),
                  (V4 + "/v4_month_2026-10.env.template", "PANEL_SPLICE=/workspace/data/TODO_wide_panel_4h_v3splice_2026-10.npz")]),
    dict(id="C-FEA-3", item="FEA-01", claim="the splice panel's rows up to the cut are the v1 canonical panel verbatim (all anchor x name columns); after the cut, names without a canonical EMA seed keep ext values",
         anchors=[(RT + "/pod_panel_splice.py", 'CAN = np.load("/workspace/data/wide_panel_4h_v1.npz", allow_pickle=True)'),
                  (RT + "/pod_panel_splice.py", "out[k] = np.concatenate([a, b[tail_idx]])"),
                  (RT + "/pod_panel_splice.py", "continue  # 尾部保持 ext 原值(新上市名, 无正典口径可续)")]),
    dict(id="C-FEA-4", item="FEA-01 (same family, new site)", claim="the DL training book loss composes the model rank with fixed legs Z24/ZFD; ZFD is the member rank of the splice panel's f_fund_ema_v1 (NaN -> 0 in the trainer and in the refit), and the v4b legs copy the in-service legs rows verbatim, which were built from the same splice panel",
         anchors=[(V4 + "/pod_legs_v4b.py", 'PANP = os.environ.get("LEGS_PANEL", "/workspace/data/wide_panel_4h_v3splice.npz")'),
                  (V4 + "/pod_legs_v4b.py", 'R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]'),
                  (V4 + "/pod_legs_v4b.py", 'OLDP = os.environ.get("LEGS_OLD", "/workspace/f8_ext/data/f10v2_legs.npz")'),
                  (RT + "/pod_legs_ext.py", 'PW = np.load("/workspace/data/wide_panel_4h_v3splice.npz", allow_pickle=True)  # splice: 正典续算口径(D5)'),
                  (V4 + "/pod_f10_train_monthly_v4.py", 'LZFD = torch.from_numpy(np.nan_to_num(_L["ZFD"], nan=0.0)).to(LZ24.device)'),
                  (V4 + "/pod_f10_train_monthly_v4.py", "r = wl[0] * r + wl[1] * LZ24[i].index_select(0, cols_t) + wl[2] * LZFD[i].index_select(0, cols_t)"),
                  (V4 + "/pod_f10_refit_v4.py", 'LZFD = torch.from_numpy(np.nan_to_num(L["ZFD"], nan=0.0)).to(DEV)'),
                  (V4 + "/v4_month_2026-09.env", "LEGS_PANEL=/workspace/data/wide_panel_4h_v3splice.npz")]),
    dict(id="C-FEA-5", item="FEA-01 (serving side)", claim="production scores only the live list; the DL serving path fills fund_ema from the producer's v1 EMA state and fund_now from the ledger tail for every name that has them; the king serving path fills cols 80/81 for live names with a settlement in the last 12 h",
         anchors=[(SL, 'r = fx.get("/fapi/v1/klines", {"symbol": s, "interval": "5m", "limit": gap_bars,'),
                  (SL, "if led and anchor - led[-1][0] <= 12 * 3600:"),
                  (SL, "FE_ANCH[:, 80] = np.nan_to_num(fe_v[m], nan=0)"),
                  (SL, "FE_ANCH[:, 81] = np.nan_to_num(fn_v[m], nan=0)"),
                  (CB, 'fe[-1, j] = float(est["acc"])'),
                  (CB, "fn[-1, j] = float(rows_[-1][1])"),
                  (DF, "X[sl, col] = 0.0 if j is None else np.nan_to_num(fv[j, m], nan=0.0); col += 1")]),
    dict(id="C-FEA-6", item="FEA-01 (boundary)", claim="king features read PANEL_KING = v2ext (not the splice), so the king model is outside FEA-01; the exporter's guard/seat leg returns read EXPORT_PANEL = v3splice f_fund_ema_v1 (not a model input: noted for fx-train); the DL targets' residual target YR4s reads the splice f_fund_ema but V2MAIN trains on y4s only",
         anchors=[(V4 + "/chain_v4_monthly.sh", 'env -i "${CLEAN_ENV[@]}" CACHE_IN=$CACHE PANEL_IN=$PANEL_KING FEA_OUT=$KING_FEA META_OUT=$KING_META "$PY" "$D/pod_fea_ext_clamp.py"'),
                  (V4 + "/v4_month_2026-09.env", "PANEL_KING=/workspace/data/wide_panel_4h_v2ext.npz"),
                  (V4 + "/v4_month_2026-09.env", "EXPORT_PANEL=/workspace/data/wide_panel_4h_v3splice.npz"),
                  (V4 + "/pod_export_bundle_v4.py", 'FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]'),
                  (V4 + "/pod_dlw_targets_raw.py", 'F6_KEYS = ["f_rev_4h", "f_rev_24h", "f_vol_7d", "f_range_24h", "f_mom_7d", "f_fund_ema"]; LAM = 1e-3; MIN_RES = 60'),
                  (V4 + "/pod_f10_train_monthly_v4.py", 'E_ts = TG["E_ts"].astype(np.int64); yrs = TG["yrs"].astype(int); y4s = TG["y4s"]')]),
    # ───────────────────────────── TIM-01: king clock ─────────────────────────────
    dict(id="C-TIM-1", item="TIM-01", claim="offline king feature windows are rows [E-w, E-1] (CS[E] - CS[max(E-w,0)] with a leading zero row) and the label is rows [E, E+47]",
         anchors=[(V4 + "/pod_fea_ext_clamp.py", "Ew = np.maximum(E - w, 0)   # E-0909-A clamp (was E - w: negative index wraps to the cache tail)"),
                  (V4 + "/pod_fea_ext_clamp.py", 'VAL.append(((s_[E] - s_[Ew])).astype(np.float32)); val_names.append(f"{nm}_sum_{w}")'),
                  (V4 + "/pod_fea_ext_clamp.py", 'y4 = (CS["ret5"][0][E + 48] - CS["ret5"][0][E]).astype(np.float32); y4[y4n < 46] = np.nan')]),
    dict(id="C-TIM-2", item="TIM-01 (same family)", claim="offline king member statistics use rows [E-2016, E-1]; n7/qvm/m7/v7 use the UNCLAMPED E-2016 (negative index wraps for E < 2016), only covr is clamped",
         anchors=[(V4 + "/pod_fea_ext_clamp.py", "n7 = np.maximum(qv_f[E] - qv_f[E - 2016], 1)"),
                  (V4 + "/pod_fea_ext_clamp.py", 'covr = (CS["ret5"][1][E] - CS["ret5"][1][np.maximum(E - 2016, 0)]) / 2016'),
                  (V4 + "/pod_fea_ext_clamp.py", "v7 = np.sqrt(np.maximum((r2s[E] - r2s[E - 2016]) / n7 - (m7 / n7) ** 2, 0))"),
                  (V4 + "/pod_fea_ext_clamp.py", "grid = grid[(grid >= 576) & (grid + 48 <= TT)]")]),
    dict(id="C-TIM-3", item="TIM-01", claim="the producer serves feature windows and member statistics on rows [E-w+1, E] (ai = the row closing at the anchor)",
         anchors=[(SL, "seg = CDf[max(ai + 1 - w, 0):ai + 1, :, ch]"),
                  (SL, "r5seg = CDf[max(ai + 1 - 2016, 0):ai + 1, :, 0]"),
                  (SL, 'ok = (covr >= P["cov_min"]) & (v7 >= P["vol_min"])')]),
    dict(id="C-TIM-4", item="TIM-01", claim="the monthly chain (September contract and October template) runs pod_fea_ext_clamp.py for king features; the clock-aligned builder pod_fea_ext_e.py exists but is not wired",
         anchors=[(V4 + "/chain_v4_monthly.sh", '"$PY" "$D/pod_fea_ext_clamp.py" >> "$DL" 2>&1 || die "king_fea" 1'),
                  (V4 + "/pod_fea_ext_e.py", "HI = E + 1                                        # E版: 半开上界 => 最后一行 = E (收盘于锚时刻)"),
                  (V4 + "/pod_fea_ext_e.py", "LO7 = np.maximum(HI - 2016, 0)                    # E版: 成员统计窗 [E-2015, E]"),
                  (V4 + "/pod_fea_ext_e.py", 'y4 = (CS["ret5"][0][E + 49] - CS["ret5"][0][E + 1]).astype(np.float32); y4[y4n < 46] = np.nan')]),
    dict(id="C-TIM-5", item="TIM-01 (same family, new site)", claim="DL targets choose members on statistics over rows [E-2016, E-1] while DL features and the producer's members include row E; DL labels are rows [E+1, E+48]",
         anchors=[(V4 + "/pod_dlw_targets_raw.py", "E = grid; S = np.maximum(E - TRAIL, 0)"),
                  (V4 + "/pod_dlw_targets_raw.py", "covr = (CS_f[E] - CS_f[S]) / np.maximum(E - S, 1)[:, None]"),
                  (V4 + "/pod_dlw_targets_raw.py", "lo_t = E + 1; hi_t = E + FWD + 1          # CS 半开区间 [lo_t, hi_t) = rows E+1..E+48"),
                  (RT + "/pod_dlw_features_ext.py", "hi = E + 1                                   # CS 半开区间上界 ⇒ 最后一行 = E(收盘于 N)")]),
    dict(id="C-TIM-6", item="TIM-01", claim="the king exporter trains and pins OOF predictions on the meta label y4 (the clamp builder's rows [E, E+47])",
         anchors=[(V4 + "/pod_export_bundle_v4.py", 'E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]'),
                  (V4 + "/pod_export_bundle_v4.py", "rr = rankdata(yv[ok]) / max(ok.sum() - 1, 1) - 0.5")]),
    # ───────────────────────────── UNI-01 ─────────────────────────────
    dict(id="C-UNI-1", item="UNI-01", claim="king and DL member screens have no asset-class filter (coverage, volatility, forward-finite label, top-400 by trailing volume)",
         anchors=[(V4 + "/pod_fea_ext_clamp.py", "ok = (covr[i] >= 0.95) & (v7[i] >= 1e-4) & np.isfinite(y4[i])"),
                  (V4 + "/pod_dlw_targets_raw.py", "ok = (covr[i] >= 0.95) & (vstd[i] >= 1e-4) & np.isfinite(y4s[i])")]),
    dict(id="C-UNI-2", item="UNI-01", claim="replay / judge arms use the CRYPTO mask = U-PIT AND underlyingType in {COIN, INDEX} (unknown class kept)",
         anchors=[(RT + "/universe_crypto_2026-09-08/scripts/build_crypto_mask.py", 'coin=np.array([ (CLS[s]["underlyingType"] in ("COIN","INDEX")) if s in CLS else True for s in syms])'),
                  (V4 + "/run_v4_arms.sh", "UP=$H/masks/umask_UPIT_CRYPTO.npz")]),
    # ───────────────────────────── TRD-05 / TRN-06 ─────────────────────────────
    dict(id="C-TRD-1", item="TRD-05 / TRN-06", claim="member screens decide tradability by the share of FINITE ret5 bars (frozen post-death rows are finite 0) and require a finite forward label before the top-400 cut",
         anchors=[(V4 + "/pod_fea_ext_clamp.py", 'covr = (CS["ret5"][1][E] - CS["ret5"][1][np.maximum(E - 2016, 0)]) / 2016'),
                  (V4 + "/pod_dlw_targets_raw.py", "if len(m) > NTOP:"),
                  (V4 + "/pod_fea_ext_clamp.py", "if len(m) > 400: m = np.sort(m[np.argsort(-qvm[i, m])[:400]])")]),
    dict(id="C-TRD-2", item="TRD-05 / TRN-06", claim="the DL trainer and refit book a non-finite label as a 0 return in the book loss; the king exporter trains only on finite labels and writes OOF predictions only on finite-label members",
         anchors=[(V4 + "/pod_f10_train_monthly_v4.py", "YT = torch.from_numpy(np.nan_to_num(y4s, nan=0.0)).to(DEV)"),
                  (V4 + "/pod_f10_refit_v4.py", "YT = torch.from_numpy(np.nan_to_num(y4s, nan=0.0)).to(DEV)"),
                  (V4 + "/pod_export_bundle_v4.py", "if ok.sum() < 50: continue"),
                  (V4 + "/pod_export_bundle_v4.py", "        sel = a_te == a; m = members[a]; okm = np.isfinite(y4[a, m])"),
                  (V4 + "/pod_export_bundle_v4.py", "rows_X.append(FEA[i, m[ok]][:, keep].astype(np.float32))")]),
    dict(id="C-TRD-3", item="TRD-05 / TRN-06", claim="production members come from trailing data only (no forward term); combo_stage's DL mini-pipeline uses the producer's current members",
         anchors=[(SL, 'ok = (covr >= P["cov_min"]) & (v7 >= P["vol_min"])'),
                  (CB, "for i in range(len(e_rows)): ms_arr[i] = pm")]),
    # ───────────────────────────── P10 ─────────────────────────────
    dict(id="C-P10-1", item="P10", claim="king training features are stored float16 and cast to float32 at fit; the producer builds float32 features from a float32 view of its float16 cache",
         anchors=[(V4 + "/pod_fea_ext_clamp.py", "FEA = np.full((len(E), NW, NF), np.nan, np.float16)"),
                  (SL, "CDf = st.cd.astype(np.float32)"),
                  (SL, "FE_ANCH = np.full((len(m), 82), np.nan, np.float32)")]),
]


def main():
    out = sys.argv[1]
    t0 = time.time(); rows = []; shas = {}; n_anchor = 0
    for r in ROWS:
        rec = dict(id=r["id"], item=r["item"], claim=r["claim"], anchors=[])
        for p, needle in r["anchors"]:
            if p not in shas:
                shas[p] = dict(sha256=guarded_sha(p), head_blob=head_blob(p))
            ln, txt = locate(p, needle)
            rec["anchors"].append(dict(file=p, line=ln, text=txt, sha256=shas[p]["sha256"]))
            n_anchor += 1
        rows.append(rec)
    doc = dict(device="fm_facts_code.py", self_sha256=guarded_sha(os.path.abspath(__file__)), utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               files=shas, rows=rows, n_rows=len(rows), n_anchors=n_anchor)
    json.dump(doc, open(out, "w"), indent=1, ensure_ascii=False)
    print("SUMMARY rows=%d anchors=%d files=%d self=%s wall=%.1fs" % (len(rows), n_anchor, len(shas), doc["self_sha256"][:16], time.time() - t0))


if __name__ == "__main__":
    main()
