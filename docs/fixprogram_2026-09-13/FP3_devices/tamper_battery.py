#!/usr/bin/env python3
"""Tamper red-battery for seal_manifest.py — proves each round-16 fix REFUSES on incomplete
verification. Runs against a scratch root that symlinks the real (large) artefacts but uses
tamperable COPIES of the small witness JSONs, so the real pod artefacts are never modified.
Establishes a GREEN baseline first (else the refusals would be vacuous), then applies each
tamper and requires: exit!=0, verdict NOT SEALED, and the SPECIFIC expected refusal present."""
import json, subprocess, os, shutil, sys

S = "/workspace/_sealtest/R"
PY = "/workspace/venv/bin/python"
SEAL = "/workspace/fp3_live_2026-09/seal_manifest.py"
ENV = dict(os.environ, FP3_ROOT=S, FP3_WS="/workspace")

def run():
    r = subprocess.run([PY, SEAL], env=ENV, capture_output=True, text=True)
    verdict = next((l for l in r.stdout.splitlines() if l.startswith("SEALED") or l.startswith("NOT SEALED")), "?")
    refs = [l.strip() for l in r.stdout.splitlines() if "[REFUSED]" in l or "[UNPROVEN]" in l]
    return r.returncode, verdict, refs

def load(p): return json.load(open(p))
def dump(p, d): json.dump(d, open(p, "w"), indent=1)

merge42 = f"{S}/f8_v4/mwf_v4b/RAW_s42/results/merge.json"
refit42 = f"{S}/f8_v4/models/f10_live_s42.json"
npx42   = f"{S}/np_export/NP_EXPORT_s42.json"
COPIES = (merge42, refit42, npx42)
for p in COPIES: shutil.copy(p, p + ".pristine")
def restore():
    for p in COPIES: shutil.copy(p + ".pristine", p)

results = []
restore()
rc, v, refs = run()
baseline_green = (rc == 0 and v.startswith("SEALED"))
results.append(("BASELINE (untampered scratch)", rc, v, "GREEN" if baseline_green else "NOT GREEN — tests below are vacuous", []))

def test(name, tamper, expect_item):
    restore(); tamper()
    rc, v, refs = run()
    hit = [r for r in refs if expect_item in r]
    ok = (rc != 0) and v.startswith("NOT SEALED") and bool(hit)
    results.append((name, rc, v, "REFUSED as required" if ok else "*** DID NOT REFUSE ***", hit[:1]))

def tA():
    d = load(merge42); del d["merged"]["folds"]["202503"]; dump(merge42, d)
test("A  delete fold s42:202503 registration (was: 39/40 SEALED)", tA, "fold.s42:202503")

def tB():
    d = load(merge42); d["merged"]["folds"]["202501"].pop("pt_sha256", None); dump(merge42, d)
test("B  delete pt_sha256 of fold s42:202501 (was: tampered model passes)", tB, "fold.s42:202501")

def tC():
    d = load(refit42); d.get("inputs_sha256", {}).pop("targets", None); dump(refit42, d)
test("C  delete artefact witness refit.inputs_sha256.targets (was: downgrade to present-only)", tC, "artefact.dlw_raw_targets")

def tD():
    d = load(refit42); d.pop("self_sha256", None); dump(refit42, d)
test("D  delete device witness refit.self_sha256 (was: downgrade to present-only)", tD, "device.pod_f10_refit_v4.py")

def tE():
    d = load(npx42); d.pop("pt_sha256", None); dump(npx42, d)
test("E  delete NP_EXPORT_s42.pt_sha256 (was: None==None bind passes)", tE, "np_export.s42")

def tF():
    d = load(npx42); d.get("V1", {}).pop("criterion_rho", None); dump(npx42, d)
test("F  delete NP_EXPORT_s42.V1.criterion_rho (was: None comparison / skip)", tF, "np_export.s42")

restore()
for p in COPIES:
    try: os.remove(p + ".pristine")
    except OSError: pass

print("=" * 78)
print("TAMPER RED-BATTERY for seal_manifest.py")
print(f"BASELINE green (untampered scratch SEALS): {baseline_green}")
print("=" * 78)
for name, rc, v, status, hit in results:
    print(f"\n### {name}\n    exit={rc}  verdict={v[:34]}  => {status}")
    for h in hit: print(f"    {h}")
tests = results[1:]
ok_all = baseline_green and all(t[3].startswith("REFUSED") for t in tests)
print("\n" + "=" * 78)
print(f"RESULT: {'PASS' if ok_all else 'FAIL'} — baseline green={baseline_green}, {sum(t[3].startswith('REFUSED') for t in tests)}/{len(tests)} tamper cases refused")
print("=" * 78)
sys.exit(0 if ok_all else 1)
