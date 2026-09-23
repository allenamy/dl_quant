"""NEW_S deploy step A2 — 40-day 5m history for the names added to the producer's fetch list (DEPLOY_new_servable_models_2026-09-23.md §A).
NOT RUN BY THE BUILD AGENT (it calls the exchange). Lead constraints 2026-09-23: fapi only inside the quiet window [N+1:00, N+3:40] AFTER
venue_quiet_window.py opens it (require_quiet_window at start, wait_for_quiet_window between requests); the per-minute log records the IP's
used weight (X-MBX-USED-WEIGHT-1M = every client on this IP, i.e. the external weight); the command text and the request estimate go to the
lead BEFORE running. Two separate modes:
  fetch   (exchange; writes ONLY an isolated copy <out_dir>/isolated_state/{rolling.npz,aux.json,generation.json}; ~/wide_shadow untouched)
  install (no exchange; DEPLOY STEP, user-confirmed, producer STOPPED: copies the isolated copy's added columns + prev_close into
           ~/wide_shadow/state after re-checking that the production state has not advanced since the fetch, re-signs generation.json)
  rollback(no exchange; producer STOPPED: sets the added columns of ~/wide_shadow/state/rolling.npz to NaN, drops their prev_close, re-signs)

Why: shadow_loop_v3 only fetches the last `gap_bars` (52) bars per name per anchor and never backfills; a newly listed fetch name
would carry ~40 days of NaN rows in state/rolling.npz ⇒ fails the 7-day coverage screen for 7 days and its 30-day windows stay
incomplete for 30 days ⇒ features ≠ the training build. This script fills exactly the rows a producer that had always fetched the
name would hold, with the producer's own channel code:
  * channel math = shadow_loop_v3.py `bars_to_channels` + `clipch` (compiled from the file, sha asserted); ret5 = c/prev_close − 1 chained
    bar to bar exactly as L413-L427 (prev_close = the close of the bar before the window, fetched as the first row);
  * only rows that are NaN in the rolling cache are written (same rule as L423-426), f16;
  * aux.json prev_close[name] = close of the last bar; generation.json re-signed with the producer's build_generation_record.
Rate limit (E-0919-V; lead 2026-09-23): endpoint GET /fapi/v1/klines interval=5m limit=1000 (request weight 5). Budget = 300 weight/min
(12.5 % of the published 2400/min IP limit; hard ceiling 50 % = 1200 incl. every other client on this IP): before every request the
script reads the last seen X-MBX-USED-WEIGHT-1M; if > 600 it sleeps to the next minute; if any response header > 1200 it ABORTS.
Every request is logged (utc, symbol, startTime, endTime, rows, used_weight_1m); a per-minute summary line is written.
Acceptance (printed, exit 0 only if all pass):
  (1) each added name: every row of the window after its first listed bar is finite in log_qv (gaps listed by name and row time);
  (2) rows <= 2026-09-19T00Z are BITWISE equal (f16, 7 channels) to the research cache x0918r (parity_cache_slice.npz) wherever x0918r is
      not a hole cell — the same equality already measured for the 450 in-service names (0 differing cells, 08-10→09-19);
  (3) the rolling axis/shape and the other 450 columns are byte-identical to before (only the added columns changed).
usage: news_backfill.py fetch <added_names.json> <x0918r_slice.npz> <x0918r_holes_slice.npz> <out_dir> [--dry-run]
       news_backfill.py install <added_names.json> <out_dir>
       news_backfill.py rollback <added_names.json> <out_dir>
"""
import os, sys, json, time, math, hashlib, ast, urllib.request, shutil
import numpy as np
sys.path.insert(0, os.path.expanduser("~/Desktop/quant_research/multi_asset/exports/research/common"))

WS = os.environ.get("WIDE_SHADOW_HOME", os.path.expanduser("~/wide_shadow")); STATE = f"{WS}/state"   # rehearsal: WIDE_SHADOW_HOME=<state copy>
SRC = os.environ.get("NEWS_PRODUCER_SRC", os.path.expanduser("~/wide_shadow/shadow_loop_v3.py"))
SRC_SHA = "6080073964bffc621c893915b16f71ecafe093194f0b99a66a4463ee12c74e61"
BASE = "https://fapi.binance.com"; BUDGET_PER_MIN = 300; SOFT = 600; HARD = 1200


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def producer_funcs():
    raw = open(SRC, "rb").read(); assert hashlib.sha256(raw).hexdigest() == SRC_SHA, "producer source changed"
    t = ast.parse(raw); keep = {"bars_to_channels", "clipch", "build_generation_record", "_state_file_hashes", "atomic_write", "atomic_json"}
    body = [x for x in t.body if (isinstance(x, ast.FunctionDef) and x.name in keep) or
            (isinstance(x, ast.Assign) and any(getattr(tg, "id", None) in ("CHN_CLIPS", "STATE_FILES") for tg in x.targets))]
    t.body = body; ns = {"np": np, "math": math, "os": os, "json": json, "hashlib": hashlib}
    exec(compile(t, SRC, "exec"), ns); assert keep <= set(ns), keep - set(ns)
    return ns


class Limiter:
    def __init__(self, logp):
        self.log = open(logp, "a"); self.min0 = int(time.time() // 60); self.w = 0; self.last_used = 0
    def before(self, weight):
        now = int(time.time() // 60)
        if now != self.min0:
            self.log.write(json.dumps({"minute_utc": time.strftime("%H:%M", time.gmtime(self.min0 * 60)), "weight_sent": self.w, "last_used_1m": self.last_used}) + "\n"); self.log.flush()
            self.min0, self.w = now, 0
        if self.w + weight > BUDGET_PER_MIN or self.last_used > SOFT:
            time.sleep(60 - time.time() % 60 + 1); self.before(weight); return
        self.w += weight
    def after(self, used):
        self.last_used = used
        if used > HARD: raise SystemExit(f"ABORT: X-MBX-USED-WEIGHT-1M = {used} > {HARD}")


def klines(sym, start_ms, end_ms, lim):
    from venue_quiet_window import wait_for_quiet_window
    wait_for_quiet_window(min_remaining_min=5)
    lim.before(5)
    url = f"{BASE}/fapi/v1/klines?symbol={sym}&interval=5m&startTime={start_ms}&endTime={end_ms}&limit=1000"
    with urllib.request.urlopen(url, timeout=15) as r:
        used = int(r.headers.get("X-MBX-USED-WEIGHT-1M", "0")); body = json.loads(r.read())
    lim.after(used)
    lim.log.write(json.dumps({"utc": time.strftime("%H:%M:%S", time.gmtime()), "symbol": sym, "start": start_ms, "end": end_ms, "rows": len(body), "used_1m": used}) + "\n"); lim.log.flush()
    return body


def fetch():
    names = json.load(open(sys.argv[2])); X = np.load(sys.argv[3], allow_pickle=True); HZ = np.load(sys.argv[4]); out = sys.argv[5]; dry = "--dry-run" in sys.argv
    os.makedirs(out, exist_ok=True); P = producer_funcs()
    if not dry:
        from venue_quiet_window import require_quiet_window
        require_quiet_window(min_remaining_min=25)
    cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); syms = cfg["symbols_panel"]; sidx = {s: j for j, s in enumerate(syms)}
    assert all(n in sidx for n in names), [n for n in names if n not in sidx]
    z = np.load(f"{STATE}/rolling.npz", allow_pickle=True); rts = z["ts"].astype(np.int64); RD = z["data"].astype(np.float16); RD0 = RD.copy()
    aux = json.load(open(f"{STATE}/aux.json")); row_of = {int(t): i for i, t in enumerate(rts)}
    lim = Limiter(f"{out}/requests.log"); report = {"names": {}, "window": [int(rts[0]), int(rts[-1])]}
    for s in names:
        j = sidx[s]; t0 = int(rts[0]) - 300; t1 = int(rts[-1])      # one extra bar before the window gives prev_close for the first row
        rows = []; st = (t0 - 300) * 1000                            # kline open time = close − 300 s
        while True:
            if dry: break
            b = klines(s, st, t1 * 1000 - 1, lim); rows += b
            if len(b) < 1000: break
            st = int(b[-1][0]) + 300000
        pc = None; filled = 0
        for k in rows:
            close_s = (int(k[0]) + 300000) // 1000
            if close_s > t1: continue
            c, ch = P["bars_to_channels"](k)
            ret5 = (c / pc - 1) if (pc and pc > 0) else np.nan
            i = row_of.get(close_s)
            if i is not None and not np.isfinite(float(RD[i, j, 3])):
                ch[0] = ret5; RD[i, j] = np.array(P["clipch"](ch), np.float16); filled += 1
            pc = c
        if rows: aux["prev_close"][s] = float(rows[-1][4])
        fin = np.isfinite(RD[:, j, 3].astype(np.float32)); first = int(np.argmax(fin)) if fin.any() else None
        gaps = [int(rts[i]) for i in np.flatnonzero(~fin) if first is not None and i > first]
        report["names"][s] = {"rows_fetched": len(rows), "rows_filled": filled, "first_finite_row_ts": int(rts[first]) if first is not None else None, "gaps_after_first": gaps[:50], "n_gaps": len(gaps)}
    # acceptance (2): bitwise vs x0918r where not a hole cell
    xts = X["ts"].astype(np.int64); xd = X["data"]; xs = [str(x) for x in X["symbols"]]; holes = set()
    holes = set(zip(HZ["row"].tolist(), HZ["col"].tolist()))      # absolute x0918r rows of synthetic hole cells
    common = np.intersect1d(rts, xts); ri = np.searchsorted(rts, common); xi = np.searchsorted(xts, common); diff = {}
    for s in names:
        j = sidx[s]; jx = xs.index(s); a = RD[ri, j, :]; b = xd[xi, jx, :]
        eq = (a.view(np.uint16) == b.view(np.uint16)) | (~np.isfinite(a.astype(np.float32)) & ~np.isfinite(b.astype(np.float32)))
        bad = [int(common[r]) for r in np.flatnonzero(~eq.all(1)) if (int(xi[r]) + int(X["row0"]), jx) not in holes]
        diff[s] = {"rows_compared": int(len(common)), "rows_differing_nonhole": len(bad), "first": bad[:5]}
    others = [sidx[s] for s in syms if s not in names]
    untouched = bool(np.array_equal(RD[:, others, :].view(np.uint16), RD0[:, others, :].view(np.uint16)))
    ok = untouched and all(v["rows_differing_nonhole"] == 0 for v in diff.values()) and all(v["n_gaps"] == 0 for v in report["names"].values())
    report.update({"vs_x0918r": diff, "other_columns_byte_identical": untouched, "ACCEPT": bool(ok), "dry_run": dry})
    json.dump(report, open(f"{out}/BACKFILL_REPORT.json", "w"), indent=1)
    if ok and not dry:                                       # isolated copy only; production state is never written by `fetch`
        iso = f"{out}/isolated_state"; os.makedirs(iso, exist_ok=True)
        np.savez_compressed(f"{iso}/.rolling_tmp.npz", ts=rts, data=RD); os.replace(f"{iso}/.rolling_tmp.npz", f"{iso}/rolling.npz")
        P["atomic_json"](f"{iso}/aux.json", aux)
        shutil.copy2(f"{STATE}/leg_returns_live.json", f"{iso}/leg_returns_live.json")
        P["atomic_json"](f"{iso}/generation.json", P["build_generation_record"](iso, int(aux["last_anchor"])))
        json.dump({"source_generation_sha256": sha(f"{STATE}/generation.json"), "source_last_anchor": int(aux["last_anchor"])}, open(f"{iso}/SOURCE.json", "w"))
    print("BACKFILL", "ACCEPT" if ok else "REJECT", "(isolated copy written)" if ok and not dry else "(not written)", flush=True)
    sys.exit(0 if ok else 3)


def install():
    """DEPLOY STEP (user-confirmed; producer stopped): the production state must still be the generation the fetch started from."""
    names = json.load(open(sys.argv[2])); out = sys.argv[3]; iso = f"{out}/isolated_state"; P = producer_funcs()
    src = json.load(open(f"{iso}/SOURCE.json"))
    assert sha(f"{STATE}/generation.json") == src["source_generation_sha256"], "REFUSE: production state advanced since the fetch — re-run fetch"
    cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); sidx = {s: j for j, s in enumerate(cfg["symbols_panel"])}; J = [sidx[s] for s in names]
    z = np.load(f"{STATE}/rolling.npz", allow_pickle=True); zi = np.load(f"{iso}/rolling.npz", allow_pickle=True)
    assert np.array_equal(z["ts"], zi["ts"]); RD = z["data"].astype(np.float16); RD[:, J, :] = zi["data"][:, J, :]
    aux = json.load(open(f"{STATE}/aux.json")); auxi = json.load(open(f"{iso}/aux.json"))
    for s in names:
        if s in auxi["prev_close"]: aux["prev_close"][s] = auxi["prev_close"][s]
    np.savez_compressed(f"{STATE}/.rolling_tmp.npz", ts=z["ts"], data=RD); os.replace(f"{STATE}/.rolling_tmp.npz", f"{STATE}/rolling.npz")
    P["atomic_json"](f"{STATE}/aux.json", aux)
    P["atomic_json"](f"{STATE}/generation.json", P["build_generation_record"](STATE, int(aux["last_anchor"])))
    print("INSTALL done; generation", sha(f"{STATE}/generation.json"))


def rollback():
    names = json.load(open(sys.argv[2])); P = producer_funcs()
    cfg = json.load(open(f"{WS}/shadow_bundle/config.json")); sidx = {s: j for j, s in enumerate(cfg["symbols_panel"])}; J = [sidx[s] for s in names]
    z = np.load(f"{STATE}/rolling.npz", allow_pickle=True); RD = z["data"].astype(np.float16); RD[:, J, :] = np.nan
    aux = json.load(open(f"{STATE}/aux.json"))
    for s in names: aux["prev_close"].pop(s, None)
    np.savez_compressed(f"{STATE}/.rolling_tmp.npz", ts=z["ts"], data=RD); os.replace(f"{STATE}/.rolling_tmp.npz", f"{STATE}/rolling.npz")
    P["atomic_json"](f"{STATE}/aux.json", aux)
    P["atomic_json"](f"{STATE}/generation.json", P["build_generation_record"](STATE, int(aux["last_anchor"])))
    print("ROLLBACK done; generation", sha(f"{STATE}/generation.json"))


def main():
    {"fetch": fetch, "install": install, "rollback": rollback}[sys.argv[1]]()


if __name__ == "__main__":
    main()
