"""NEWS P5-0 (Mac, production venv, read-only): does the extracted producer King block (news_hist_features._king_block = shadow_loop_v3.py
L486-L553 compiled verbatim) reproduce what production ACTUALLY computed at the archived anchors? Inputs = the producer's own snapshot
state/snap/<A>/ (rolling.npz, aux.json written after anchor A): st.live = production symbols_live (450), base = aux base_syms, ledger/ema = aux.
Checks, bitwise: members == aux prev_rec members; legz king == xz(OLD booster.predict(X78)); legz rev24 == xz(-wstat(0,288,sum)[m]);
legz fund == xz_in_base(fe_v[m], names, base_vals) — all compared as float64 bit patterns with prev_rec's stored nan_to_num'd lists."""
import os, sys, json, time, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import news_hist_features as H
import news_legs as NL
P = os.path.expanduser("~/cc_tmp/news_20260923"); WS = os.path.expanduser("~/wide_shadow")
H.PROD = f"{P}/producer_copy"; H.SHADOW_SRC = f"{H.PROD}/shadow_loop_v3.py"
ANCH = [1789660800 + 14400 * k for k in range(9)]


def main():
    assert H.sha(H.SHADOW_SRC) == H.SHADOW_SHA
    kb = H._king_block(); xz_in_base, xz = NL.prod_funcs()
    cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]
    import lightgbm as lgb
    bpath = f"{WS}/shadow_bundle/slow2026.txt"; assert H.sha(bpath) == "8d79186b6380132cb67684acf1ebfcdb2c53261c850f46a4908b06bfa7a81282"
    booster = lgb.Booster(model_file=bpath)
    res = []
    for A in ANCH:
        d = f"{WS}/state/snap/{A}"
        z = np.load(f"{d}/rolling.npz", allow_pickle=True); aux = json.load(open(f"{d}/aux.json"))
        assert int(z["ts"][-1]) == A and aux["last_anchor"] == A and aux["prev_rec"]["anchor_ts"] == A
        st = H._St(); st.cd = z["data"].astype(np.float16); st.live = list(cfg["symbols_live"]); st.sym_idx = {s: j for j, s in enumerate(syms)}
        st.ledger = aux["ledger_tail"]; st.ema = aux["ema"]; st.NW = len(syms)
        rts = z["ts"].astype(np.int64); row_of = {int(t): i for i, t in enumerate(rts)}
        out = kb(st, A, cfg["params"], cfg, row_of, list(aux["base_syms"]), H._Diag(), lambda r: None)
        m = out["m"]; pr = aux["prev_rec"]
        pred = booster.predict(out["X"])
        legz = {"king": xz(pred), "rev24": xz(-out["wstat"](0, 288, "sum")[m]), "fund": xz_in_base(out["fe_v"][m], [syms[int(j)] for j in m], out["base_vals"])}
        r = {"anchor": A, "members_equal": [int(x) for x in m] == pr["members"]}
        for k in ("king", "rev24", "fund"):
            a = np.nan_to_num(legz[k]).astype(np.float64); b = np.array(pr["legz"][k], np.float64)
            r[f"legz_{k}_bitwise"] = bool(len(a) == len(b) and np.array_equal(a.view(np.uint64), b.view(np.uint64)))
            if not r[f"legz_{k}_bitwise"] and len(a) == len(b): r[f"legz_{k}_maxabs"] = float(np.abs(a - b).max())
        res.append(r); print(json.dumps(r), flush=True)
    ok = all(all(v for k, v in r.items() if k.endswith("_equal") or k.endswith("_bitwise")) for r in res)
    json.dump({"device": os.path.abspath(__file__), "device_sha256": H.sha(os.path.abspath(__file__)), "king_block_source": H.SHADOW_SRC, "king_block_source_sha256": H.SHADOW_SHA,
               "python": sys.version, "numpy": np.__version__, "lightgbm": lgb.__version__, "results": res, "VERDICT": "REPRODUCED" if ok else "NOT_REPRODUCED"},
              open(f"{P}/parity/P5_0_PRODUCTION_REPRODUCTION.json", "w"), indent=1)
    print("P5_0 VERDICT", "REPRODUCED" if ok else "NOT_REPRODUCED", flush=True)


if __name__ == "__main__":
    main()
