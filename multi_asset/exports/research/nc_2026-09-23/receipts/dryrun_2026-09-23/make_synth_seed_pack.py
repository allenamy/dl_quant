"""MACHINERY TEST ONLY: a seed pack in nc_export_seed.py's format built from PRODUCTION data (snap/<E>), not the training replay.
rows = snap/<E> rolling crypto columns; no boundary cells; no member history; funding = production ledger rows <= E re-ingested from
scratch with nc_contract (NC intervals, NC EMA). Its only use is to run nc_seed_state.py end to end on the Mac."""
import sys, json, numpy as np, os
tree, E, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
sys.path.insert(0, f"{tree}/fea171"); import nc_contract as NC
HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"
cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]
cr = np.load(f"{HOME}/cc_tmp/news_20260923/package_NEW_S/crypto_P1_members_2025H2on.npz", allow_pickle=True)["crypto"].astype(bool)
cols = np.flatnonzero(cr)
z = np.load(f"{WS}/state/snap/{E}/rolling.npz", allow_pickle=True); ts = z["ts"].astype(np.int64); d = np.array(z["data"], np.float16)
assert int(ts[-1]) == E
aux = json.load(open(f"{WS}/state/snap/{E}/aux.json"))
fe = {"sym": [], "n": [], "ft": [], "rate": [], "iv": [], "acc": [], "prev": []}
for j in cols:
    rows = [(int(r[0]), float(r[1])) for r in aux["ledger_tail"].get(syms[j], []) if int(r[0]) <= E][-400:]
    led, st, n = NC.ingest_settlements([], None, rows)
    fe["sym"].append(j); fe["n"].append(len(led))
    fe["ft"].append(np.array([r[0] for r in led], np.int64)); fe["rate"].append(np.array([r[1] for r in led], np.float64))
    fe["iv"].append(np.array([np.nan if r[2] is None else r[2] for r in led], np.float64))
    fe["acc"].append(np.nan if (st is None or st.get("acc") is None) else st["acc"]); fe["prev"].append(-1 if (st is None or st.get("last_ts") is None) else st["last_ts"])
np.savez(out, rts=ts, rows=d[:, cols, :], crypto_cols=cols, symbols=np.array(syms), axis_end=np.int64(E),
         bnd_ts=np.zeros(0, np.int64), bnd_col=np.zeros(0, np.int32), bnd_raw=np.zeros(0, np.float32),
         m_anchors=np.zeros(0, np.int64), m_off=np.zeros(1, np.int64), m_idx=np.zeros(0, np.int16),
         f_sym=np.array(fe["sym"], np.int64), f_n=np.array(fe["n"], np.int64), f_ft=np.concatenate(fe["ft"]), f_rate=np.concatenate(fe["rate"]),
         f_iv=np.concatenate(fe["iv"]), f_acc=np.array(fe["acc"], np.float64), f_prev=np.array(fe["prev"], np.int64))
print("SYNTH_SEED_PACK", out, len(cols), sum(fe["n"]))
