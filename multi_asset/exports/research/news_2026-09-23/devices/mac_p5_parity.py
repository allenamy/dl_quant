"""NEWS P5 parity (Mac, production venv; read-only on the producer tree): the PRODUCER'S CODE on the archived live inputs of
2026-09-17T16Z .. 09-19T00Z (state/snap/<A>/), made post-deploy-equivalent, versus the training build at the same anchors.
Serving inputs at A (what the producer would hold after deploy steps A1-A3):
  rolling  = snapshot rolling.npz (live data of the 450 in-service names) + the 72 added names' columns taken from the research cache
             x0918r (stand-in for the A2 backfill; x0918r hole cells NaN) — the 450 live columns are FIRST checked bitwise against x0918r;
  ledger   = snapshot aux ledger_tail (live); ema = snapshot ema re-seeded to the training replay at A (step A3 emulated);
  fetch list = 450 + 72 (step A1); fund-leg base = snapshot base_syms (production M1 base, unchanged by the swap).
Serving computation = news_hist_features.replay_anchor with cand = the 522 fetch list and NO hole mask (= the producer's King block L486-L553
and the combo_stage mini with dlw_features.py / f8 build, all sha-asserted), so the only thing that can differ from the training build is INPUT.
Compared bitwise with the training build (pod2 NEWS_FEATURES rows, and the Mac recompute of P5-a): members, X78, X82, X89, fe_v, rev24, qvm;
then scores (NEWS King booster on the Mac vs pod2 OOF; NEWS F10 s42 numpy export vs the GPU OOF the evaluation used), leg z and the
combo target (combo_target.step = combo_stage chain/exec_reshape source) with kc/fc state taken from the evaluation at A-4h.
Every difference is located and named; nothing is toleranced away."""
import os, sys, json, time, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import news_hist_features as H
import news_legs as NL
P = os.path.expanduser("~/cc_tmp/news_20260923"); WS = os.path.expanduser("~/wide_shadow"); PAR = f"{P}/parity"
H.W = PAR; H.PROD = f"{P}/producer_copy"; H.SHADOW_SRC = f"{H.PROD}/shadow_loop_v3.py"; H.COMBO_SRC = f"{H.PROD}/fea171/combo_stage.py"
H.DLW_SRC = f"{H.PROD}/fea171/dlw_features.py"; H.F8_SRC = f"{H.PROD}/fea171/f8_higher_order_features.py"
H.XSYMS = f"{H.PROD}/fea171/xfer_syms.npz"; H.XREF = f"{H.PROD}/fea171/xfer_ref.npz"
ANCH = [1789660800 + 14400 * k for k in range(9)]


def bits(a, dt):
    return np.ascontiguousarray(np.asarray(a, dt)).view({np.float16: np.uint16, np.float32: np.uint32, np.float64: np.uint64}[dt])


def cmp(a, b, dt):
    a = np.asarray(a); b = np.asarray(b)
    if a.shape != b.shape: return {"bitwise": False, "why": f"shape {a.shape} vs {b.shape}"}
    ne = bits(a, dt) != bits(b, dt)
    both_nan = ~np.isfinite(np.asarray(a, np.float64)) & ~np.isfinite(np.asarray(b, np.float64))
    ne &= ~both_nan
    r = {"bitwise": bool(not ne.any()), "n_diff": int(ne.sum()), "n": int(ne.size)}
    if ne.any(): r["max_abs"] = float(np.nanmax(np.abs(np.asarray(a, np.float64)[ne] - np.asarray(b, np.float64)[ne])))
    return r


def main():
    t0 = time.time()
    import lightgbm as lgb
    sys.path.insert(0, f"{P}/devices"); import combo_target as CT
    CT.ROOT = __import__("pathlib").Path(f"{P}/parity/ct_root")          # combo_target.source_kernels reads ROOT/vendor_live/fea171/combo_stage.py (sha-pinned)
    os.makedirs(f"{PAR}/ct_root/vendor_live/fea171", exist_ok=True)
    import shutil; shutil.copy2(H.COMBO_SRC, f"{PAR}/ct_root/vendor_live/fea171/combo_stage.py")
    for f, s in ((H.SHADOW_SRC, H.SHADOW_SHA), (H.COMBO_SRC, H.COMBO_SHA), (H.DLW_SRC, H.DLW_SHA), (H.F8_SRC, H.F8_SHA)): assert H.sha(f) == s, f
    xz_in_base, xz = NL.prod_funcs()
    cfg = json.load(open(f"{P}/producer_copy/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; sidx = {s: j for j, s in enumerate(syms)}
    added = json.load(open(f"{PAR}/added_names.json")); live522 = list(cfg["symbols_live"]) + sorted(added)
    F522 = np.zeros(len(syms), bool); F522[[sidx[s] for s in live522]] = True
    X = np.load(f"{PAR}/parity_cache_slice.npz", allow_pickle=True); xts = X["ts"].astype(np.int64); xd = X["data"]; row0 = int(X["row0"])
    HZ = np.load(f"{PAR}/parity_holes_slice.npz")
    FR = np.load(f"{PAR}/parity_fund_slice.npz"); fa = FR["anchors"].astype(np.int64)
    T = np.load(f"{PAR}/NEWS_TRAIN_PARITY_ROWS.npz", allow_pickle=True)     # pod2 training build rows + OOF + legs + combo at the parity anchors
    MAC = np.load(f"{PAR}/MAC_TRAINBUILD_FEATURES.npz", allow_pickle=True)
    booster = lgb.Booster(model_file=f"{PAR}/deploy/slow2026.txt"); M10 = np.load(f"{PAR}/deploy/f10_live_s42_np.npz")
    from scipy.special import erf
    def gelu(x): return 0.5 * x * (1 + erf(x / np.sqrt(2)))
    res = []
    for A in ANCH:
        r = {"anchor": A, "utc": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(A))}
        d = f"{WS}/state/snap/{A}"; z = np.load(f"{d}/rolling.npz", allow_pickle=True); aux = json.load(open(f"{d}/aux.json"))
        rts = z["ts"].astype(np.int64); RD = np.array(z["data"], np.float16); assert int(rts[-1]) == A
        xi = np.searchsorted(xts, rts); assert np.array_equal(xts[xi], rts)
        L450 = [sidx[s] for s in cfg["symbols_live"]]
        r["data_450_live_vs_x0918r"] = cmp(RD[:, L450, :], xd[xi][:, L450, :], np.float16)
        hole = np.zeros((len(rts), len(syms)), bool); hs = (HZ["row"] - row0); m_ = np.isin(hs, xi)
        pos = {int(v): k for k, v in enumerate(xi)}
        for rr, cc in zip(hs[m_], HZ["col"][m_]): hole[pos[int(rr)], int(cc)] = True
        for s in added:
            j = sidx[s]; col = np.array(xd[xi, j, :], np.float16); col[hole[:, j]] = np.nan; RD[:, j, :] = col
        ia = int(np.searchsorted(fa, A)); assert fa[ia] == A
        ema = dict(aux["ema"]); n_reseed = 0
        for j in np.flatnonzero(np.isfinite(FR["ema_acc"][ia])):
            ema[syms[j]] = {"acc": float(FR["ema_acc"][ia, j]), "last_ts": int(FR["last_ft"][ia, j])}; n_reseed += 1
        r["ema_reseeded_names"] = n_reseed
        led = aux["ledger_tail"]
        # serving computation: producer code on the post-deploy inputs (fetch list = 522, no hole mask, no candidate mask beyond the fetch list)
        S = H.replay_anchor(A, RD, rts, syms, [str(c) for c in z["ch"]] if "ch" in z.files else ["ret5", "range", "cpos", "log_qv", "log_cnt", "log_avgsz", "tbf"],
                            F522, ema, led, cfg["params"], cfg, f"{PAR}/work", holes=None, cols="members")
        tm = T[f"m_{A}"]
        r["members"] = {"equal": bool(np.array_equal(S["m"], tm)), "serving_not_train": [syms[j] for j in sorted(set(S["m"]) - set(tm))], "train_not_serving": [syms[j] for j in sorted(set(tm) - set(S["m"]))]}
        if r["members"]["equal"]:
            for key, dt in (("X78", np.float32), ("X82", np.float16), ("X89", np.float32)):
                src = {"X78": "king_X78"}.get(key, key)
                r[key] = cmp(S[src], T[f"{key}_{A}"], dt); r[key + "_vs_mac_trainbuild"] = cmp(S[src], MAC[f"{key}_{A}"], dt)
            for key in ("fe_v", "fn_v", "rev24", "qvm"): r[key] = cmp(S[key], T[f"{key}_{A}"], np.float64)
            # scores
            pk = booster.predict(S["king_X78"]); r["king_score_vs_pod2_oof"] = cmp(pk, T[f"king_oof_{A}"], np.float64)
            X171 = np.concatenate([S["X82"].astype(np.float32), S["X89"]], 1)
            xz_in = np.nan_to_num(np.clip((X171 - M10["mu"]) / M10["sd_"], -5, 5)); h = gelu(xz_in @ M10["w0"].T + M10["b0"]); h = gelu(h @ M10["w1"].T + M10["b1"])
            f10 = (h @ M10["w2"].T + M10["b2"]).squeeze(-1); g = T[f"f10_oof_{A}"]
            r["f10_numpy_vs_gpu_oof"] = {"max_abs": float(np.abs(f10.astype(np.float64) - g).max()), "rank_mismatch": int((np.argsort(np.argsort(f10)) != np.argsort(np.argsort(g))).sum())}
            # legs
            bv = {s: v for s, v in S["base_vals"].items()}
            prod_base = {s: float(aux["ema"].get(s, {}).get("acc", np.nan)) for s in aux["base_syms"]}
            base_serv = {}
            for s in aux["base_syms"]:
                l_ = led.get(s); e_ = ema.get(s)
                if l_ and e_ and A - l_[-1][0] <= 12 * 3600: base_serv[s] = float(e_["acc"])
            names_m = [syms[int(j)] for j in S["m"]]
            lz = {"king": xz(pk), "rev24": xz(-S["rev24"]), "fund": xz_in_base(S["fe_v"], names_m, base_serv)}
            r["base_serving_minus_train"] = sorted(set(base_serv) - set(syms[j] for j in np.flatnonzero(np.isfinite(T[f"base_val_{A}"]))))
            r["base_train_minus_serving"] = sorted(set(syms[j] for j in np.flatnonzero(np.isfinite(T[f"base_val_{A}"]))) - set(base_serv))
            for k, tk in (("king", "KZ"), ("rev24", "Z24"), ("fund", "ZFD")): r[f"legz_{k}"] = cmp(lz[k], T[f"{tk}_{A}"], np.float64)
            # combo (step = combo_stage chain/exec_reshape source), state from the evaluation at A-4h
            m = S["m"]; qv = np.expm1(np.clip(S["qvm"], 0, 30)) * 48
            rn8 = np.array([(float(led[syms[j]][-1][1]) * (8.0 / (float(led[syms[j]][-1][2]) if float(led[syms[j]][-1][2]) > 0 else 8.0))) if led.get(syms[j]) else np.nan for j in m])
            for tag, legal in (("serving_LIVE_MASK_522", F522), ("evaluation_LIVE_MASK", T[f"book_legal_{A}"])):
                out = CT.step(lz["king"], f10, lz["fund"], T[f"WL_{A}"], rn8, m, qv, legal, cfg["params"], T[f"kc_prev_{A}"], T[f"fc_prev_{A}"], "scaled_diagnostic")
                r[f"combo_{tag}"] = {"accepted": bool(out["accepted"]), "eval_trade_mask": bool(T[f"trade_mask_{A}"]),
                                     "raw_vs_eval": cmp(out["raw"], T[f"raw_{A}"], np.float64) if out["raw"] is not None else "no raw"}
        res.append(r); print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk in ("bitwise", "equal", "n_diff", "max_abs", "rank_mismatch", "accepted")}) for k, v in r.items()}), flush=True)
    json.dump({"device": os.path.abspath(__file__), "device_sha256": H.sha(os.path.abspath(__file__)), "python": sys.version, "numpy": np.__version__,
               "lightgbm": lgb.__version__, "results": res, "seconds": round(time.time() - t0, 1)}, open(f"{PAR}/P5_PARITY.json", "w"), indent=1, default=str)
    print("P5_PARITY_DONE", round(time.time() - t0, 1), flush=True)


if __name__ == "__main__":
    main()
