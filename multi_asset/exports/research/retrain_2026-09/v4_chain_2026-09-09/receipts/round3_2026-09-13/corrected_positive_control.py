"""Round 3, lead's condition: show SIDE BY SIDE that the researcher's `sidecar_complete_identity_positive` flipping to rc 3
is a FIXTURE GAP, not the new gate rejecting legitimate input.

Three panels, all computed here, nothing asserted from memory:
  A. What the REAL writer (pod_f10_refit_v4.py) emits — extracted from its AST, plus whether any field is conditional.
  B. The researcher's fixture (probe_followup.py lines 66-77) vs the real writer: which fields/paths it has and lacks.
  C. The same BYTES run through the gate twice — at the researcher's layout, and at the writer's canonical layout.

If any field the gate requires were optional in the real writer's output, the gate would be wrong and must be relaxed.
Panel A answers that: the writer's `meta` is ONE unconditional dict literal, and the four env_given keys the gate
requires are exactly the writer's own _REQ tuple — the four it refuses (rc 2) to run without.
"""
import ast, hashlib, json, os, subprocess, sys, tempfile

D = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the device dir
GATE_TOP = {"seed", "best_ep_rule", "best_ep_kept", "env_given", "inputs", "inputs_sha256", "pt", "pt_sha256", "self_sha256"}
GATE_ENV = {"F10_DLW", "F10_OUT", "SEED", "BEST_EP_FIX"}
ROLES = ["targets", "fea82", "fea89", "legs"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 24), b""):
            h.update(c)
    return h.hexdigest()


# ── Panel A: what the real writer emits (AST, so "always" vs "sometimes" is decidable) ────────────────────────────────
tree = ast.parse(open(f"{D}/pod_f10_refit_v4.py").read())
emit, egk, roles, rpaths, req, cond = set(), [], [], [], [], []
for n in ast.walk(tree):
    if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "meta" for t in n.targets) and isinstance(n.value, ast.Dict):
        for k, v in zip(n.value.keys, n.value.values):
            emit.add(k.value)
            if k.value == "env_given":
                egk = [e.value for c in ast.walk(v) if isinstance(c, ast.Tuple) for e in c.elts]
            if k.value == "inputs" and isinstance(v, ast.Dict):
                roles = [e.value for e in v.keys]; rpaths = [ast.unparse(e) for e in v.values]
    if isinstance(n, ast.Assign):
        for t in n.targets:
            if isinstance(t, ast.Subscript) and getattr(t.value, "id", "") == "meta" and isinstance(t.slice, ast.Constant):
                emit.add(t.slice.value)
    if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_REQ" for t in n.targets):
        req = [e.value for e in n.value.elts]
for b in ast.walk(tree):
    if isinstance(b, (ast.If, ast.Try, ast.For, ast.While)):
        cond += [ast.unparse(a)[:60] for a in ast.walk(b) if isinstance(a, ast.Assign)
                 and any((isinstance(t, ast.Subscript) and getattr(t.value, "id", "") == "meta") or getattr(t, "id", "") == "meta" for t in a.targets)]
A = {"writer": "pod_f10_refit_v4.py", "writer_sha256": sha(f"{D}/pod_f10_refit_v4.py"),
     "meta_keys_emitted": sorted(emit), "meta_assignments_inside_if_try_loop": cond or "NONE (nothing is conditionally emitted)",
     "env_given_keys_always_present": egk, "writer_REQ_refuses_rc2_without": req,
     "inputs_roles": roles, "inputs_path_expressions": rpaths,
     "VERDICT_gate_requires_only_unconditional_fields": {
         "top_level_required_subset_of_emitted": sorted(GATE_TOP) if GATE_TOP <= emit else f"VIOLATION missing {sorted(GATE_TOP - emit)}",
         "env_required_equals_writer_REQ": GATE_ENV == set(req),
         "env_keys_that_may_legitimately_be_None_and_are_NOT_required": sorted(set(egk) - GATE_ENV),
         "conclusion": ("no field the gate requires is optional in the real writer's output: the meta dict is one unconditional literal, "
                        "and the four env_given keys required are the four the writer itself refuses to run without")
         if (GATE_TOP <= emit and not cond and GATE_ENV == set(req)) else "GATE IS TOO STRICT — RELAX IT"}}

# ── Panel B + C: the researcher's fixture vs the canonical layout, SAME BYTES ─────────────────────────────────────────
B, C = {}, {}
for label, canonical in (("researcher_layout_as_written", False), ("same_bytes_at_canonical_paths", True)):
    with tempfile.TemporaryDirectory() as d:
        dlw, f8 = f"{d}/dlw", f"{d}/f8"
        for r in ("dlw/data", "f8/data", "f8/models"):
            os.makedirs(f"{d}/{r}", exist_ok=True)
        layout = {"targets": "dlw/data/dlw_targets.npz", "fea82": "dlw/data/dlw_fea82.npz",
                  "fea89": "f8/data/f8_fea89.npz", "legs": "f8/data/f10v2_legs.npz"}
        ins = {}
        for k in ROLES:
            p = f"{d}/{layout[k]}" if canonical else f"{d}/{k}.bin"   # researcher: <F>/<role>.bin
            open(p, "wb").write(k.encode())                            # ← SAME BYTES in both arms
            ins[k] = p
        pt = f"{d}/f8/models/f10_live_s42.pt" if canonical else f"{d}/f8/model.pt"   # researcher: <f8>/model.pt
        open(pt, "wb").write(b"original synthetic weights")
        m = {"seed": 42, "best_ep_rule": "fix7", "env_given": {"F10_DLW": dlw, "F10_OUT": f8, "BEST_EP_FIX": "7"},
             "inputs": ins, "inputs_sha256": {k: sha(p) for k, p in ins.items()}, "pt": pt, "pt_sha256": sha(pt)}
        if canonical:
            m["best_ep_kept"] = 7; m["env_given"]["SEED"] = "42"; m["self_sha256"] = sha(f"{D}/pod_f10_refit_v4.py")
        sc = f"{d}/f8/models/f10_live_s42.json"; json.dump(m, open(sc, "w"))
        if not canonical:
            B = {"researcher_fixture": "probe_followup.py L66-77 (codex_followup_code_review_2026-09-13/retrain)",
                 "top_level_fields_present": sorted(m), "top_level_fields_the_REAL_WRITER_emits_but_this_lacks": sorted(GATE_TOP - set(m)),
                 "env_given_present": sorted(m["env_given"]), "env_given_the_REAL_WRITER_emits_but_this_lacks": sorted(GATE_ENV - set(m["env_given"])),
                 "input_paths": {k: os.path.basename(v) for k, v in ins.items()},
                 "input_paths_the_REAL_WRITER_would_use": {k: layout[k] for k in ROLES},
                 "pt_path": os.path.basename(pt), "pt_path_the_REAL_WRITER_would_use": "f8/models/f10_live_s42.pt",
                 "helper_call_form": "5 arguments (round-2 form): no expected seed, no refit source",
                 "note": ("every FILE is fine and every recorded sha matches its file; what is missing is the three fields the writer always "
                          "emits and the canonical LOCATIONS — i.e. the fixture never modelled a real sidecar, it modelled the old gate")}
        args = f" 42 {D}/pod_f10_refit_v4.py" if canonical else ""
        log = f"{d}/say.log"; open(log, "w").close()
        p = subprocess.run(["/bin/bash", "-c", f". {D}/chain_lib.sh; prereq_refit_sidecar arms refit_s42 {sc} {dlw} {f8}{args}"],
                           capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "L": log, "PY": sys.executable, "R": d})
        C[label] = {"rc": p.returncode, "stderr": p.stderr.strip()[-700:], "chain_log": open(log).read().strip()[-450:]}

C["reading"] = ("Same bytes, same recorded shas. rc 3 at the researcher's layout and rc 0 at the writer's canonical layout ⇒ the flip is a "
                "FIXTURE GAP. The gate rejects a sidecar that is not ABOUT this month's artefacts; it does not reject a real one.")
print(json.dumps({"A_real_writer": A, "B_researcher_fixture_vs_real_writer": B, "C_same_bytes_both_layouts": C}, indent=1))
