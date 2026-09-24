#!/usr/bin/env python3
"""Cross-check news2's s42 handoff against the files that will be packaged (lead 2026-09-24: shas are taken FROM THE HANDOFF, never typed).
Read-only. Asserts, each a named refusal (exit 3):
  sha(manifest) == handoff.manifest.sha256
  handoff FROZEN_VERDICT == manifest VERDICT; handoff USER_OVERRIDE == manifest USER_OVERRIDE == sha(ruling) == handoff.override_ruling.sha256_measured
  handoff seed == manifest seed == 's42'
  handoff executor_pins == manifest deploy.executor_pins == {sha(king), sha(f10)}
  handoff exported_files (name, sha256) == manifest exported_files (name, sha256) == the local files
Prints one line HANDOFF_CHECK OK {...} (the shas the downstream steps must use) and, with --out, writes it as JSON.
usage: python3 nc_handoff_check.py <HANDOFF_deploy_s42.json> <P5_DEPLOY_MANIFEST.json> <slow2026.txt> <f10_live_s42_np.npz> <ruling.md> [--out F]"""
import argparse, hashlib, json, os, sys, time


def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    for k in ("handoff", "manifest", "king", "f10", "ruling"): ap.add_argument(k)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    H = json.load(open(a.handoff)); M = json.load(open(a.manifest))
    s = {"handoff": sha(a.handoff), "manifest": sha(a.manifest), "king": sha(a.king), "f10": sha(a.f10), "ruling": sha(a.ruling)}
    fails = []
    def need(ok, msg):
        if not ok: fails.append(msg)
    need(s["manifest"] == (H.get("manifest") or {}).get("sha256"), f"sha(manifest) {s['manifest']} != handoff.manifest.sha256 {(H.get('manifest') or {}).get('sha256')}")
    need(H.get("FROZEN_VERDICT") == M.get("VERDICT") and isinstance(H.get("FROZEN_VERDICT"), str), f"handoff FROZEN_VERDICT {H.get('FROZEN_VERDICT')} != manifest VERDICT {M.get('VERDICT')}")
    if M.get("VERDICT") != "DEPLOY":
        need(H.get("USER_OVERRIDE") == M.get("USER_OVERRIDE") == s["ruling"] == (H.get("override_ruling") or {}).get("sha256_measured"),
             f"USER_OVERRIDE disagree: handoff {H.get('USER_OVERRIDE')} manifest {M.get('USER_OVERRIDE')} sha(ruling) {s['ruling']}")
        need((H.get("override_ruling") or {}).get("verified") is True, "handoff override_ruling.verified is not true")
    need(H.get("seed") == M.get("seed") == "s42", f"seed handoff {H.get('seed')} manifest {M.get('seed')} (want s42)")
    want = {"booster_sha_pin": s["king"], "f10_sha_pin": s["f10"]}
    need(H.get("executor_pins") == want, f"handoff executor_pins {H.get('executor_pins')} != local files {want}")
    need((M.get("deploy") or {}).get("executor_pins") == want, f"manifest deploy.executor_pins != local files {want}")
    ex = lambda D: sorted((e.get("name"), e.get("sha256")) for e in D.get("exported_files") or [])
    need(ex(H) == ex(M) == sorted([("slow2026.txt", s["king"]), ("f10_live_s42_np.npz", s["f10"])]), f"exported_files disagree: handoff {ex(H)} manifest {ex(M)}")
    need(M.get("lineage_bound") is True, "manifest lineage_bound is not true")
    rec = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "device_sha256": sha(os.path.abspath(__file__)),
           "paths": {k: os.path.abspath(getattr(a, k)) for k in ("handoff", "manifest", "king", "f10", "ruling")}, "sha256": s,
           "FROZEN_VERDICT": H.get("FROZEN_VERDICT"), "USER_OVERRIDE": H.get("USER_OVERRIDE"), "seed": H.get("seed"), "executor_pins": H.get("executor_pins"),
           "V1_gate_note": "handoff V1_gate.PASS is the numpy == torch numerical equivalence gate (spearman >= 0.99999, maxabs <= 1e-5), not a book-level admission",
           "failures": fails, "result": "OK" if not fails else "REFUSED"}
    if a.out:
        json.dump(rec, open(a.out, "w"), indent=1)
    if fails:
        print("HANDOFF_CHECK REFUSED " + " | ".join(fails), flush=True); return 3
    print("HANDOFF_CHECK OK " + json.dumps({"FROZEN_VERDICT": rec["FROZEN_VERDICT"], "USER_OVERRIDE": rec["USER_OVERRIDE"], "executor_pins": rec["executor_pins"],
                                            "handoff_sha256": s["handoff"], "manifest_sha256": s["manifest"]}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
