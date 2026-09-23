#!/usr/bin/env python3
"""NC deploy live pack (DESIGN §A7-1, FREEZE amendment 1 §2.2-2.3): the K-line rows after the research-axis end that the production state
does not hold under the new contract, fetched live in a quiet window. Consumed by nc_seed_state.py --live-pack. Exchange: PUBLIC klines
only; never writes ~/wide_shadow.
  (1) names in the dynamic fetch list that production did not fetch (not in symbols_live): every row in (axis_end, last_anchor], paged
      (limit 1000, weight 5), starting one bar before the axis end so the first row's ret5 has its adjacent previous close;
  (2) every bound cell after the axis end in the production rolling cache (|ch0| = the f16 bound): the two bars (previous, bound) to get
      the exact raw return c/pc - 1.
Rows are built with the NC producer's own bars_to_channels / clipch and the no-cross-gap rule; bound bars go to the sparse table.
Guards (identical to nc_fetch_test.py): require_quiet_window(>= 30 min), wait_for_quiet_window(5) before each request, IP used weight
> 1200 aborts, any HTTP 429 / 418 aborts (no retry; headers recorded), deadline N+3:10, every request logged.
usage: ~/wide_shadow/venv/bin/python nc_deploy_fetch.py <patched tree> <prod state dir (copy)> <fetch list json> <axis_end> <out npz>"""
import os, sys, json, time, importlib.util, hashlib, urllib.error, concurrent.futures
import numpy as np

HOME = os.path.expanduser("~")
sys.path.insert(0, f"{HOME}/Desktop/quant_research/multi_asset/exports/research/common")
from venue_quiet_window import require_quiet_window, wait_for_quiet_window

HARD = 1200


class Abort(BaseException):
    pass


def main():
    tree, prod, fl, E, out = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
    require_quiet_window(min_remaining_min=30)
    N = int(time.time()) // 14400 * 14400; deadline = N + 3 * 3600 + 600
    os.environ["WIDE_SHADOW_HOME"] = os.path.dirname(os.path.abspath(out)); os.environ["WIDE_SHADOW_BUNDLE"] = f"{HOME}/wide_shadow/shadow_bundle"
    spec = importlib.util.spec_from_file_location("nc_shadow_loop", f"{tree}/shadow_loop_v3.py"); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    sys.path.insert(0, f"{tree}/fea171"); import nc_contract as NC
    log = open(out + ".requests.jsonl", "a"); aborted = {}; real = M.urllib.request.urlopen

    def guarded(url, *a, **k):
        try:
            return real(url, *a, **k)
        except urllib.error.HTTPError as e:
            if e.code in (429, 418):
                aborted.update({"code": e.code, "headers": dict(e.headers.items()), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}); raise Abort(f"HTTP {e.code}")
            raise
    M.urllib.request.urlopen = guarded

    class TF(M.Fetcher):
        def get(self, path, params, weight):
            if time.time() > deadline: raise Abort("deadline N+3:10")
            wait_for_quiet_window(min_remaining_min=5)
            r = super().get(path, params, weight); used = self._diag.get("used_weight_1m_last", 0)
            log.write(json.dumps({"utc": time.strftime("%H:%M:%S", time.gmtime()), "path": path, "symbol": params.get("symbol"), "startTime": params.get("startTime"),
                                  "rows": (len(r) if isinstance(r, list) else None), "used_weight_1m": used}) + "\n"); log.flush()
            if used > HARD: raise Abort(f"used weight {used} > {HARD}")
            return r

    cfg = json.load(open(f"{HOME}/wide_shadow/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; sidx = {s: j for j, s in enumerate(syms)}; live = set(cfg["symbols_live"])
    fetch = json.load(open(fl))
    Z = np.load(f"{prod}/rolling.npz", allow_pickle=True); ts = Z["ts"].astype(np.int64); D = Z["data"]; last = int(ts[-1]); rowpos = {int(t): i for i, t in enumerate(ts)}
    M.FETCH_WORKERS, M.FETCH_BUDGET = 6, 600
    fx = TF(); rec = {"device_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(), "axis_end": E, "last_anchor": last}
    new = [s for s in fetch if s not in live]
    rows_ts, rows_col, rows_val, b_ts, b_col, b_raw, pc_s, pc_c, pc_t = [], [], [], [], [], [], [], [], []
    try:
        def page(s):
            got = []; start = (E - 300) * 1000 - 300000       # the bar closing at E-300 .. so the bar closing at E gives the first adjacent close
            while True:
                r = fx.get("/fapi/v1/klines", {"symbol": s, "interval": "5m", "startTime": start, "endTime": last * 1000 - 1, "limit": 1000}, weight=5)
                if not isinstance(r, list): return s, None
                got += r
                if len(r) < 1000: return s, got
                start = int(r[-1][0]) + 300000
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            res = list(ex.map(page, new))
        failed = []
        for s, kl in res:
            if kl is None: failed.append(s); continue
            j = sidx[s]; pc = pts = None
            for k in kl:
                close_s = (int(k[0]) + 300000) // 1000
                if close_s > last: continue
                c, ch = M.bars_to_channels(k)
                ret5 = (c / pc - 1) if (pc and pc > 0 and pts == close_s - 300) else np.nan
                if close_s > E and close_s in rowpos:
                    ch[0] = ret5; rows_ts.append(close_s); rows_col.append(j); rows_val.append(np.array(M.clipch(ch), np.float16))
                    if NC.needs_boundary_raw(ret5): b_ts.append(close_s); b_col.append(j); b_raw.append(np.float32(ret5))
                pc = c; pts = close_s
            if kl: pc_s.append(s); pc_c.append(float(kl[-1][4])); pc_t.append((int(kl[-1][0]) + 300000) // 1000)
        # bound cells after the axis end in the production rows of names production fetches
        B16 = np.float32(NC.BOUND16); bound = []
        for i in np.flatnonzero(ts > E):
            for j in np.flatnonzero(np.isfinite(D[i, :, 0].astype(np.float32)) & (np.abs(D[i, :, 0].astype(np.float32)) == B16)):
                if syms[j] in live: bound.append((int(ts[i]), int(j)))
        for t, j in bound:
            r = fx.get("/fapi/v1/klines", {"symbol": syms[j], "interval": "5m", "startTime": (t - 600) * 1000, "endTime": t * 1000 - 1, "limit": 2}, weight=1)
            if isinstance(r, list) and len(r) == 2 and (int(r[1][0]) + 300000) // 1000 == t and (int(r[0][0]) + 300000) // 1000 == t - 300:
                raw = float(r[1][4]) / float(r[0][4]) - 1
                b_ts.append(t); b_col.append(j); b_raw.append(np.float32(raw))
            else:
                failed.append(f"bound:{syms[j]}@{t}")
        rec.update({"new_names": len(new), "rows": len(rows_ts), "bound_cells_after_axis": len(bound), "boundary_entries": len(b_ts), "failed": failed,
                    "own_weight": fx.weight_used, "used_weight_1m_max": fx.diagnostics().get("used_weight_1m_max")})
        np.savez(out, row_ts=np.array(rows_ts, np.int64), row_col=np.array(rows_col, np.int64),
                 row_val=(np.stack(rows_val) if rows_val else np.zeros((0, 7), np.float16)), bnd_ts=np.array(b_ts, np.int64), bnd_col=np.array(b_col, np.int32),
                 bnd_raw=np.array(b_raw, np.float32), pc_sym=np.array(pc_s), pc_close=np.array(pc_c), pc_ts=np.array(pc_t, np.int64))
        rec["VERDICT"] = "PACKED" if not failed else "PACKED_WITH_FAILURES"
    except Abort as e:
        rec["VERDICT"] = f"ABORTED: {e}"; rec["abort_http"] = aborted or None
    json.dump(rec, open(out + ".json", "w"), indent=1)
    print("NC_DEPLOY_FETCH", json.dumps(rec)[:600], flush=True)
    sys.exit(0 if rec["VERDICT"] == "PACKED" else 3)


if __name__ == "__main__":
    main()
