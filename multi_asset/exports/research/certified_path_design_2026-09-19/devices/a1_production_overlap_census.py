#!/usr/bin/env python3
"""A1 — object (A) census: which target file the real production chain wrote AND the executor actually read, anchor by anchor,
2026-08-26 00Z .. 2026-09-18 20Z (144 anchors). READ-ONLY on the production host (Mac); design doc DESIGN_certified_production_path_2026-09-19 §2.

Reads (never writes):
  ~/wide_shadow/state/target_live/{A}.json(.sha256)   file the executor reads (combo writer overwrites the king file; rollback restores it)
  ~/wide_shadow/state/target_live_king/{A}.json       king backup (combo_stage L339-342, written only after the preflight passed)
  ~/wide_shadow/state/target_combo/{A}.json           combo stage record (n_f10_scored, w3_masked, gross)
  ~/wide_shadow/fea171/combo_live.log                 combo writer stdout (members line, ⑤ success / ABORT, '=== combo_live anchor=.. rc=..')
  ~/dl_quant_live/state/anchor_runs.log               executor phase_A JSON per attempt (external_book ok/reason/json_sha/producer, action)
  ~/dl_quant_live/state/live/pilot_log/*/anchors.jsonl executor anchor rows (external_book.json_sha, opening_halted)
Writes only (research repo receipts folder):
  receipts/A1_PRODUCTION_OVERLAP_CENSUS.json
  receipts/production_overlap_archive_20260826_20260918.tar.gz + receipts/production_overlap_archive_MANIFEST.json
    (byte copies of target_live / target_live_king / target_combo for the window; per-file sha256 = source sha256 at copy time)
"""
import os, sys, re, json, time, glob, hashlib, tarfile, io, collections

HOME = os.path.expanduser("~"); WS = f"{HOME}/wide_shadow"; DQ = f"{HOME}/dl_quant_live"
HERE = os.path.dirname(os.path.abspath(__file__)); RCPT = os.path.join(os.path.dirname(HERE), "receipts")
LO, HI, H4 = 1787702400, 1789768800, 14400      # 2026-08-26 00Z .. 2026-09-18 20Z
OUT = f"{RCPT}/A1_PRODUCTION_OVERLAP_CENSUS.json"
TAR = f"{RCPT}/production_overlap_archive_20260826_20260918.tar.gz"; MAN = f"{RCPT}/production_overlap_archive_MANIFEST.json"


def shab(b): return hashlib.sha256(b).hexdigest()
def shaf(p): return shab(open(p, "rb").read())
def iso(t): return time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(t)))


def combo_log_blocks():
    """Blocks end with '=== combo_live anchor=<A> rc=<rc> ...'; lines since the previous block end belong to it."""
    out = {}; buf = []
    for l in open(f"{WS}/fea171/combo_live.log", errors="replace"):
        m = re.match(r"^=== combo_live anchor=(\d+) rc=(-?\d+)", l)
        if m:
            A = int(m.group(1)); mem = [int(x) for x in re.findall(r"members (\d+)", "".join(buf))]
            out.setdefault(A, []).append({"rc": int(m.group(2)), "members": mem[-1] if mem else None,
                                          "writer_done": any("⑤ COMBO_LIVE 写者完成 rehearsal=False" in x for x in buf),
                                          "abort": next((x.strip()[:200] for x in buf if "COMBO_LIVE ABORT" in x), None)})
            buf = []
        else:
            buf.append(l)
    return out


def executor_phaseA():
    pat = re.compile(r"^(\S+) phase_A: (\{.*\})\s*$"); out = collections.defaultdict(list)
    for l in open(f"{DQ}/state/anchor_runs.log", errors="replace"):
        m = pat.match(l)
        if not m: continue
        try: d = json.loads(m.group(2))
        except Exception: continue
        eb = d.get("external_book") or {}; n = eb.get("nominal_ts")
        if n is None: continue
        out[int(n)].append({"log_utc": m.group(1), "ok": eb.get("ok"), "reason": eb.get("reason"), "json_sha": eb.get("json_sha"),
                            "producer": (eb.get("producer") or "")[:40], "attempts": eb.get("attempts"), "action": d.get("action"),
                            "on_schedule": (d.get("schedule") or {}).get("on_schedule")})
    return out


def executor_rows():
    out = collections.defaultdict(list)
    for p in sorted(glob.glob(f"{DQ}/state/live/pilot_log/2026*/anchors.jsonl")):
        for l in open(p):
            try: r = json.loads(l)
            except Exception: continue
            eb = r.get("external_book") or {}; n = eb.get("nominal_ts")
            if n is None: continue
            out[int(n)].append({"day": os.path.basename(os.path.dirname(p)), "ok": eb.get("ok"), "json_sha": eb.get("json_sha"), "opening_halted": r.get("opening_halted")})
    return out


def main():
    t0 = time.time(); CL = combo_log_blocks(); PA = executor_phaseA(); ER = executor_rows()
    import gzip
    rows = []; man = []; tbuf = io.BytesIO(); gz = gzip.GzipFile(fileobj=tbuf, mode="wb", mtime=0)   # mtime 0 => byte-reproducible archive
    tf = tarfile.open(fileobj=gz, mode="w", format=tarfile.USTAR_FORMAT)
    for A in range(LO, HI + 1, H4):
        r = {"anchor": A, "utc": iso(A)}
        tl = f"{WS}/state/target_live/{A}.json"
        if os.path.exists(tl):
            b = open(tl, "rb").read(); s = shab(b); d = json.loads(b)
            sc = tl + ".sha256"; r["tl_sha256"] = s
            r["tl_sidecar_ok"] = (open(sc).read().split()[0] == s) if os.path.exists(sc) else None
            prod = d.get("producer", ""); r["tl_kind"] = "combo" if "combo_stage" in prod else ("king" if prod else "?")
            r["tl_producer"] = prod[:60]; r["tl_has_f10_sha"] = "f10_sha" in d; r["tl_n_names"] = len(d.get("weights", {}))
        else:
            r["tl_kind"] = "MISSING"
        kb = f"{WS}/state/target_live_king/{A}.json"; r["king_backup"] = os.path.exists(kb)
        tc = f"{WS}/state/target_combo/{A}.json"
        if os.path.exists(tc):
            d = json.load(open(tc)); r["tc_n_f10_scored"] = d.get("n_f10_scored"); r["tc_w3_masked"] = d.get("w3_masked"); r["tc_gross"] = d.get("gross")
        blocks = CL.get(A, []); r["combo_log"] = blocks[-1] if blocks else None; r["combo_log_n_runs"] = len(blocks)
        pa = PA.get(A, []); r["exec_phaseA_n"] = len(pa)
        if pa:
            # an anchor can have one on-schedule attempt plus later off-schedule re-runs that HOLD on a stale file; the traded attempt is the TRADE one
            tr = [x for x in pa if x["action"] == "TRADE"]
            r["exec_trade_attempts"] = len(tr); r["exec_on_schedule_attempts"] = sum(1 for x in pa if x["on_schedule"] is True)
            r["exec_off_schedule_attempts"] = sum(1 for x in pa if x["on_schedule"] is False)
            f = tr[0] if tr else pa[-1]
            r["exec_final_action"] = "TRADE" if tr else f["action"]; r["exec_final_ok"] = f["ok"]; r["exec_final_reason"] = f["reason"]
            r["exec_json_sha"] = f["json_sha"]; r["exec_producer"] = f["producer"]
            r["exec_json_sha_eq_archive"] = (f["json_sha"] == r.get("tl_sha256")) if f["ok"] else None
            r["exec_reasons_all_attempts"] = sorted(set(str(x["reason"]) for x in pa))
        er = ER.get(A, []); r["exec_anchor_rows"] = len(er)
        if er: r["exec_opening_halted"] = er[-1]["opening_halted"]; r["exec_row_sha_eq_archive"] = (er[-1]["json_sha"] == r.get("tl_sha256")) if er[-1]["ok"] else None
        rows.append(r)
        for sub in ("target_live", "target_live_king", "target_combo"):
            for suf in (".json", ".json.sha256"):
                p = f"{WS}/state/{sub}/{A}{suf}"
                if os.path.exists(p):
                    b = open(p, "rb").read(); ti = tarfile.TarInfo(f"{sub}/{A}{suf}"); ti.size = len(b); ti.mtime = int(os.path.getmtime(p))
                    tf.addfile(ti, io.BytesIO(b)); man.append({"path": f"{sub}/{A}{suf}", "sha256": shab(b), "bytes": len(b), "src_mtime_utc": iso(os.path.getmtime(p))})
    tf.close(); gz.close(); open(TAR, "wb").write(tbuf.getvalue())
    json.dump({"source_root": f"{WS}/state", "window": [iso(LO), iso(HI)], "n_files": len(man), "tar_sha256": shaf(TAR), "files": man}, open(MAN, "w"), indent=1)
    c = collections.Counter()
    for r in rows:
        c["tl:" + r["tl_kind"]] += 1
        c["exec_action:" + str(r.get("exec_final_action"))] += 1
        if r.get("exec_json_sha_eq_archive") is True: c["exec_traded_file_sha_eq_archive"] += 1
        if r.get("exec_json_sha_eq_archive") is False: c["exec_traded_file_sha_NE_archive"] += 1
        if r.get("exec_opening_halted"): c["exec_opening_halted"] += 1
        if r.get("exec_off_schedule_attempts"): c["anchors_with_off_schedule_reruns"] += 1
        if r.get("exec_trade_attempts", 0) > 1: c["anchors_with_gt1_TRADE_attempts"] += 1
        if r.get("tc_n_f10_scored") is not None: c["tc_n_f10_scored_eq_400"] += int(r["tc_n_f10_scored"] == 400)
        cl = r.get("combo_log")
        if cl: c["combo_writer_done"] += int(cl["writer_done"]); c["combo_abort"] += int(bool(cl["abort"])); c["combo_members_400"] += int(cl["members"] == 400)
    exc = [{k: r.get(k) for k in ("utc", "tl_kind", "king_backup", "combo_log", "exec_final_action", "exec_final_reason", "exec_reasons_all_attempts", "exec_phaseA_n")}
           for r in rows if r["tl_kind"] != "combo" or r.get("exec_final_action") != "TRADE"]
    doc = {"device": os.path.abspath(__file__), "self_sha256": shaf(os.path.abspath(__file__)), "python": sys.version.split()[0],
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "window": [iso(LO), iso(HI)], "n_anchors": len(rows),
           "sources": {"combo_live_log_sha256": shaf(f"{WS}/fea171/combo_live.log"), "anchor_runs_log_bytes_read": os.path.getsize(f"{DQ}/state/anchor_runs.log")},
           "summary": dict(c), "exceptions": exc, "archive": {"tar": os.path.basename(TAR), "tar_sha256": shaf(TAR), "manifest": os.path.basename(MAN), "n_files": len(man)},
           "rows": rows, "runtime_s": round(time.time() - t0, 1)}
    json.dump(doc, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(json.dumps(doc["summary"], ensure_ascii=False)); print(json.dumps(exc, ensure_ascii=False, indent=1)); print("WROTE", OUT, shaf(OUT), TAR, shaf(TAR))


if __name__ == "__main__":
    main()
