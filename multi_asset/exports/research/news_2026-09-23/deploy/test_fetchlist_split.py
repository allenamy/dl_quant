"""R10-B01 gate for the producer patch (fetch list separate from the holding universe). Mac, production venv, quiet window only,
no network (fake fetcher), sandboxes under ~/cc_tmp; never writes ~/wide_shadow.

Harness: for an archived anchor A, a sandbox is built from the producer's own snapshots: rolling.npz of state/snap/<A> (bars through A),
aux.json + leg_returns_live.json of state/snap/<A-4h> (prev_rec / H / ledger / EMA / prev_close as they were before A), bundle = the
production shadow_bundle. The producer's `_run_anchor(A)` is then executed exactly as in production except for the fetcher:
  klines → [] (every bar ≤ A is already in the snapshot rolling cache, and the producer only fills NaN rows),
  fundingRate → the rows of state/snap/<A>/aux.json ledger_tail inside [startTime, endTime] (limit honoured) = what production fetched,
  exchangeInfo → the TRADING base recorded in state/snap/<A>/aux.json base_syms.
Checks (VERDICT PASS only if all hold; exit 3 otherwise):
  N0 harness reproduces production: ORIGINAL shadow_loop_v3.py (6080073b) → target_live/<A>.json equals the archived
     state/target_live_king/<A>.json with `written_utc` and `weights_sha` removed (both carry the write time), and prev_rec equals state/snap/<A>/aux.json prev_rec.
  N1 negative control: PATCHED file with NO symbols_fetch → target json (minus written_utc), weights, prev_rec, leg returns, H,
     base_syms byte-identical to the ORIGINAL run.
  P1 positive control: PATCHED file with symbols_fetch = 450 + 72 (rolling cache gets the 72 names' columns from x0918r, hole cells NaN)
     → members == the training replay members at A (NEWS_FEATURES rows), and every added name holds ZERO target weight.
  R1 red control: ORIGINAL file with symbols_live = 522 (the rejected first draft) on the same inputs → at least one added name holds
     non-zero weight (proves P1's zero-holding check can fail).
usage: ~/wide_shadow/venv/bin/python test_fetchlist_split.py --neg <A> [<A> ...] --pos <A> [<A> ...]
  --neg anchors must have been produced by the CURRENT producer file (6080073b, live since 2026-09-22T13:24Z): N0 + N1 there;
  --pos anchors must be inside the training axis (<= 2026-09-19T00Z, x0918r columns + NEWS_FEATURES rows): N1 + P1 + R1 there.
"""
import os, sys, json, time, shutil, hashlib, importlib.util, copy
import numpy as np

P = os.path.expanduser("~/cc_tmp/news_20260923"); WS = os.path.expanduser("~/wide_shadow"); SB = f"{P}/deploy/sandbox_fetchsplit"
ORIG = f"{P}/deploy/producer_patch/shadow_loop_v3.orig.py"; PATCH = f"{P}/deploy/producer_patch/shadow_loop_v3.py"
ORIG_SHA = "6080073964bffc621c893915b16f71ecafe093194f0b99a66a4463ee12c74e61"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


class FakeFetcher:
    def __init__(self, aux_A):
        self.led = aux_A["ledger_tail"]; self.base = list(aux_A["base_syms"]); self.weight_used = 0; self.calls = []
    def diagnostics(self): return {"fake": True, "calls": len(self.calls)}
    def get(self, path, params, weight=1):
        self.calls.append(path)
        if path == "/fapi/v1/klines":
            return {"_err": "fake: tail scoring not replayed"} if params.get("interval") == "1h" else []
        if path == "/fapi/v1/exchangeInfo":
            return {"symbols": [{"symbol": s, "contractType": "PERPETUAL", "quoteAsset": "USDT", "status": "TRADING"} for s in self.base]}
        if path == "/fapi/v1/fundingRate":
            rows = [r for r in self.led.get(params["symbol"], []) if params["startTime"] <= int(r[0]) * 1000 + 0 <= params["endTime"]]
            return [{"fundingTime": int(r[0]) * 1000, "fundingRate": repr(float(r[1]))} for r in rows[:params["limit"]]]
        return {"_err": "fake: unsupported"}


def build_sandbox(tag, A, cfg_mod=None, add_cols=None):
    root = f"{SB}/{tag}_{A}"; shutil.rmtree(root, ignore_errors=True)
    os.makedirs(f"{root}/state"); shutil.copytree(f"{WS}/shadow_bundle", f"{root}/shadow_bundle")
    snapA = f"{WS}/state/snap/{A}"; snapP = f"{WS}/state/snap/{A - 14400}"
    z = np.load(f"{snapA}/rolling.npz", allow_pickle=True); ts, data = z["ts"], np.array(z["data"], np.float16)
    if add_cols is not None:
        for j, col in add_cols.items(): data[:, j, :] = col
    np.savez_compressed(f"{root}/state/rolling.npz", ts=ts, data=data)
    auxP = json.load(open(f"{snapP}/aux.json")); auxP["last_anchor"] = int(auxP["last_anchor"])
    # rolling now ends at A; the generation checkpoint check requires rolling ts[-1] == aux.last_anchor ⇒ load via the bootstrap-free path:
    # we hand the state object to _run_anchor directly (see run()), so aux/rolling consistency is established in memory, not via generation.json
    json.dump(auxP, open(f"{root}/state/aux.json", "w")); shutil.copy2(f"{snapP}/leg_returns_live.json", f"{root}/state/leg_returns_live.json")
    if cfg_mod:
        cfg = json.load(open(f"{root}/shadow_bundle/config.json")); cfg_mod(cfg); raw = json.dumps(cfg).encode()
        open(f"{root}/shadow_bundle/config.json", "wb").write(raw)
        man = json.load(open(f"{root}/shadow_bundle/MANIFEST.json")); man["config.json"] = hashlib.sha256(raw).hexdigest()
        json.dump(man, open(f"{root}/shadow_bundle/MANIFEST.json", "w"), indent=1)
    return root


def run(src, root, A):
    os.environ["WIDE_SHADOW_HOME"] = root; os.environ["WIDE_SHADOW_BUNDLE"] = f"{root}/shadow_bundle"
    kf = f"{WS}/state/target_live_king/{A}.json"                      # the start offset production ran with at A (plist env; 16 before 09-22, 12 after)
    os.environ["SHADOW_OFFSET_MIN"] = str(json.load(open(kf))["anchor_offset_min"]) if os.path.exists(kf) else "12"
    name = f"sl_{abs(hash((src, root)))}"; spec = importlib.util.spec_from_file_location(name, src); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    cfg, booster, man = M.load_bundle(); cfg["_booster_sha"] = man.get("slow2026.txt", "")
    # construct the state exactly as ShadowState would from (rolling through A, aux of A-4h) without the on-disk generation marker
    st = M.ShadowState.__new__(M.ShadowState)
    z = np.load(f"{root}/state/rolling.npz", allow_pickle=True); st.cts = z["ts"].astype(np.int64); st.cd = z["data"].astype(np.float16)
    aux = json.load(open(f"{root}/state/aux.json"))
    st.syms = cfg["symbols_panel"]; st.live = cfg["symbols_live"]; st.NW = len(st.syms); st.sym_idx = {s: j for j, s in enumerate(st.syms)}
    if hasattr(M.ShadowState, "__init__") and "symbols_fetch" in open(src).read():
        st.fetch = list(cfg.get("symbols_fetch") or cfg["symbols_live"])
    st.live_mask = np.zeros(st.NW, bool); st.live_mask[[st.sym_idx[s] for s in st.live if s in st.sym_idx]] = True
    st.prev_close = {k: float(v) for k, v in aux["prev_close"].items()}; st.H = np.zeros(st.NW)
    for k, v in aux["H"].items(): st.H[int(k)] = float(v)
    st.last_anchor = int(aux["last_anchor"]); st.ema = aux["ema"]; st.ledger = aux["ledger_tail"]; st.prev_rec = aux.get("prev_rec")
    st.base = list(aux.get("base_syms") or (st.fetch if hasattr(st, "fetch") else st.live))
    lr = np.load(f"{root}/shadow_bundle/leg_returns.npz"); extra = json.load(open(f"{root}/state/leg_returns_live.json"))
    st.LR = {leg: list(lr[leg]) + list(extra[leg]) for leg in ("king", "rev24", "fund")}; n_lr0 = len(st.LR["king"])
    auxA = json.load(open(f"{WS}/state/snap/{A}/aux.json")); fx = FakeFetcher(auxA)
    M.run_anchor(st, fx, cfg, booster, A)
    tl = json.load(open(f"{root}/state/target_live/{A}.json")); tl.pop("written_utc", None); tl.pop("weights_sha", None)   # weights_sha = sha of an npz whose zip header carries the write time; the weights themselves are compared
    w = np.load(f"{root}/state/weights/{A}.npz")
    return {"target": tl, "w_idx": w["idx"].tolist(), "w_val": w["val"].tolist(), "members": w["members"].tolist(), "prev_rec": st.prev_rec,
            "LR_new": {k: st.LR[k][n_lr0:] for k in st.LR}, "H": st.H.tolist(), "base": list(st.base), "cfg_live": list(cfg["symbols_live"])}


def main():
    assert sha(ORIG) == ORIG_SHA and sha(f"{WS}/shadow_loop_v3.py") == ORIG_SHA
    args = sys.argv[1:]; assert args and args[0] == "--neg" and "--pos" in args, "usage: --neg <A>... --pos <A>..."
    k = args.index("--pos"); neg = [int(a) for a in args[1:k]]; posA = [int(a) for a in args[k + 1:]]
    added = json.load(open(f"{P}/deploy/added_names.json"))
    cfg0 = json.load(open(f"{WS}/shadow_bundle/config.json")); sidx = {s: j for j, s in enumerate(cfg0["symbols_panel"])}; added_idx = {sidx[s] for s in added}
    X = np.load(f"{P}/parity/parity_cache_slice.npz", allow_pickle=True); xts = X["ts"].astype(np.int64); row0 = int(X["row0"])
    HZ = np.load(f"{P}/parity/parity_holes_slice.npz"); T = np.load(f"{P}/parity/NEWS_FEATURES_parity9.npz")
    res = []; ok_all = True
    for A in neg:
        r = {"anchor": A, "mode": "neg"}
        o = run(ORIG, build_sandbox("orig", A), A)
        kf = json.load(open(f"{WS}/state/target_live_king/{A}.json")); kf.pop("written_utc", None); kf.pop("weights_sha", None)
        prod_prev = json.load(open(f"{WS}/state/snap/{A}/aux.json"))["prev_rec"]
        r["N0_target_equals_archived_king_file"] = (json.dumps(o["target"], sort_keys=True) == json.dumps(kf, sort_keys=True))
        r["N0_prev_rec_equals_archived"] = (json.dumps(o["prev_rec"], sort_keys=True) == json.dumps(prod_prev, sort_keys=True))
        p = run(PATCH, build_sandbox("patch_nofetch", A), A)
        r["N1_patched_no_fetch_identical"] = all(json.dumps(o[k], sort_keys=True) == json.dumps(p[k], sort_keys=True) for k in o)
        r["PASS"] = bool(r["N0_target_equals_archived_king_file"] and r["N0_prev_rec_equals_archived"] and r["N1_patched_no_fetch_identical"])
        ok_all &= r["PASS"]; res.append(r); print(json.dumps(r), flush=True)
    for A in posA:
        r = {"anchor": A, "mode": "pos"}
        o = run(ORIG, build_sandbox("orig", A), A); p = run(PATCH, build_sandbox("patch_nofetch", A), A)
        r["N1_patched_no_fetch_identical"] = all(json.dumps(o[k], sort_keys=True) == json.dumps(p[k], sort_keys=True) for k in o)
        z = np.load(f"{WS}/state/snap/{A}/rolling.npz", allow_pickle=True); rts = z["ts"].astype(np.int64); xi = np.searchsorted(xts, rts); assert np.array_equal(xts[xi], rts)
        pos = {int(v): q for q, v in enumerate(xi)}; cols = {}
        for s in added:
            j = sidx[s]; col = np.array(X["data"][xi, j, :], np.float16)
            for rr in (HZ["row"][HZ["col"] == j] - row0):
                if int(rr) in pos: col[pos[int(rr)]] = np.nan
            cols[j] = col
        pp = run(PATCH, build_sandbox("patch_fetch522", A, cfg_mod=lambda c: c.__setitem__("symbols_fetch", list(c["symbols_live"]) + sorted(added)), add_cols=cols), A)
        tm = T[f"m_{A}"].astype(int).tolist()
        r["P1_members_equal_training"] = (sorted(pp["members"]) == sorted(tm))
        r["P1_added_members"] = sum(1 for j in pp["members"] if j in added_idx)
        r["P1_added_names_zero_weight"] = not any(int(j) in added_idx and float(v) != 0.0 for j, v in zip(pp["w_idx"], pp["w_val"]))
        r["P1_universe_is_450"] = (pp["target"]["universe"] == cfg0["symbols_live"])
        rr_ = run(ORIG, build_sandbox("orig_live522", A, cfg_mod=lambda c: c.__setitem__("symbols_live", list(c["symbols_live"]) + sorted(added)), add_cols=cols), A)
        r["R1_old_draft_members_equal_training"] = (sorted(rr_["members"]) == sorted(tm))
        r["R1_old_draft_holds_added_names"] = any(int(j) in added_idx and float(v) != 0.0 for j, v in zip(rr_["w_idx"], rr_["w_val"]))
        r["PASS"] = bool(r["N1_patched_no_fetch_identical"] and r["P1_members_equal_training"] and r["P1_added_names_zero_weight"] and r["P1_universe_is_450"] and r["R1_old_draft_holds_added_names"])
        ok_all &= r["PASS"]; res.append(r); print(json.dumps(r), flush=True)
    rec = {"device": os.path.abspath(__file__), "device_sha256": sha(os.path.abspath(__file__)), "orig_sha256": ORIG_SHA, "patched_sha256": sha(PATCH),
           "results": res, "VERDICT": "PASS" if ok_all else "FAIL", "python": sys.version, "numpy": np.__version__}
    json.dump(rec, open(f"{P}/deploy/TEST_FETCHLIST_SPLIT.json", "w"), indent=1)
    print(f"TEST_FETCHLIST_SPLIT VERDICT={rec['VERDICT']} anchors={len(res)}", flush=True)
    sys.exit(0 if ok_all else 3)


if __name__ == "__main__":
    main()
