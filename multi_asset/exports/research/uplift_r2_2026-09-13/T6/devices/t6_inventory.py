#!/usr/bin/env python3
"""t6_inventory.py -- T6 step 1 (inventory, NO statistics). Read-only scan of npz artifacts.
For every *.npz under the given roots (minus declared input-only subtrees) record: path, size, mtime,
keys, and for files that carry a per-anchor record (a 2-D float array whose column names are in a
'cols'-like key and include 'ts','net_ex','gross_total') the record shape, ts grid (first/last/n/sha256 of
the int64 ts bytes), column list, config_json caliber fields, source_sha256 and the file sha256.
It never reads a return column except to hash the ts column; it computes no mean/std/Sharpe of anything.
Usage: python3 t6_inventory.py <env_whitelist_csv> <out_json> <root1> [<root2> ...]
"""
import os, sys, json, time, hashlib, zipfile
WHITE = set(x for x in sys.argv[1].split(",") if x)
assert WHITE, "launch with a non-empty env whitelist as argv[1]"
EXTRA = sorted(k for k in os.environ if k not in WHITE); assert EXTRA == [], ("ENV WHITELIST VIOLATION", EXTRA)
OUT = sys.argv[2]; ROOTS = sys.argv[3:]; assert ROOTS
import numpy as np
SKIP_PARTS = ("/r5_oi/parts/", "/r5_oi/raw/", "/sig/", "/feat/", "/pod_backup_", "/data/", "/masks/", "/ckpt_np/", "/lob2/", "/__pycache__/")
CAL_FIELDS = ("CAL", "PHI", "LEGS", "WRULE", "W3FIX", "UMASK_SCOPE", "UMASK_NPZ", "LOOK", "FTRIM", "FTRIM_TH", "MEMBERS_TOPN", "TRADE_TOPN",
              "COSTB_JSON", "COST_B", "SLOW_NPY", "FPRED", "FSEED", "SLEEVE", "KMOD", "KMOD_F10", "KMOD_L", "KMOD_AGREE", "SEATF10", "SEATNET", "KTAIL",
              "FUNDSCALE", "FEMAT_NPZ", "RNSM", "FTPOS", "LTRIM_TH", "CDAMP", "REF_SKIP")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def selfsha(): return sha(os.path.abspath(__file__))
t0 = time.time(); rows = []; n_seen = 0; n_skipped_path = 0
for root in ROOTS:
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for f in sorted(fn):
            if not f.endswith(".npz"): continue
            p = os.path.join(dp, f); n_seen += 1
            if any(s in p + ("/" if False else "") for s in SKIP_PARTS): n_skipped_path += 1; continue
            st = os.stat(p); r = dict(path=p, size=st.st_size, mtime_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(st.st_mtime)))
            try:
                Z = np.load(p, allow_pickle=False); keys = list(Z.files); r["keys"] = keys
                colkeys = [k for k in keys if k == "cols" or k.endswith("_cols") or k.endswith("cols")]
                recs = []
                for ck in colkeys:
                    try: C = [str(c) for c in Z[ck]]
                    except Exception as e: continue
                    if not ("ts" in C and "net_ex" in C and "gross_total" in C): continue
                    base = ck[:-4] if ck.endswith("cols") else ""
                    cand = [k for k in keys if k != ck and (k == base + "rec" or k == base.rstrip("_") + "_rec" or (base == "" and k.endswith("rec")))]
                    for rk in cand:
                        a = Z[rk]
                        if a.ndim != 2 or a.shape[1] != len(C): continue
                        ts = np.asarray(a[:, C.index("ts")], np.float64)
                        tsi = ts.astype(np.int64)
                        recs.append(dict(rec_key=rk, cols_key=ck, shape=list(a.shape), cols=C, dtype=str(a.dtype), ts_first=int(tsi[0]), ts_last=int(tsi[-1]),
                                         ts_first_utc=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(tsi[0]))), ts_last_utc=time.strftime("%Y-%m-%d %HZ", time.gmtime(int(tsi[-1]))),
                                         ts_sha256=hashlib.sha256(tsi.tobytes()).hexdigest(), ts_integral=bool(np.all(ts == tsi))))
                r["records"] = recs
                if recs:
                    r["sha256"] = sha(p)
                    if "config_json" in keys:
                        cfg = json.loads(str(Z["config_json"])); r["config_top_keys"] = sorted(cfg.keys())
                        r["cal"] = {k: cfg.get(k, "<absent>") for k in CAL_FIELDS}
                        r["config_nested"] = {k: v for k, v in cfg.items() if isinstance(v, dict)}
                        r["config_scalar_other"] = {k: v for k, v in cfg.items() if not isinstance(v, dict) and k not in CAL_FIELDS}
                    if "source_sha256" in keys: r["source_sha256"] = str(Z["source_sha256"])
                    r["other_keys_shapes"] = {k: list(Z[k].shape) for k in keys if k not in [x["rec_key"] for x in recs] and k not in ("config_json",) and Z[k].size < 50_000_000}
            except Exception as e:
                r["error"] = "%s: %s" % (type(e).__name__, str(e)[:300])
            rows.append(r)
out = dict(device="t6_inventory.py", self_sha256=selfsha(), argv=sys.argv, env_whitelist=sorted(WHITE), env_actual={k: os.environ[k] for k in sorted(os.environ)},
           python=sys.version.split()[0], numpy=np.__version__, host=os.uname().nodename, roots=ROOTS, skip_parts=SKIP_PARTS,
           n_npz_seen=n_seen, n_skipped_by_path=n_skipped_path, n_scanned=len(rows), n_with_record=sum(1 for r in rows if r.get("records")),
           n_errors=sum(1 for r in rows if "error" in r), wall_s=round(time.time() - t0, 1), rows=rows)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f: json.dump(out, f, indent=1, default=str)
print("SUMMARY t6_inventory host=%s seen=%d skipped_by_path=%d scanned=%d with_record=%d errors=%d wall=%.1fs self_sha256=%s"
      % (out["host"], n_seen, n_skipped_path, len(rows), out["n_with_record"], out["n_errors"], out["wall_s"], out["self_sha256"][:16]))
