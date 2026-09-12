#!/usr/bin/env python3
"""r19 STEP 3 (T2/T3) — generate patched copies of the outside-trackF consumers. Exact string replacements, each
asserted to occur exactly once; a unified diff is saved per file. Two kinds of edit only:
  (i) T2 (read the archived labels): point the label/vars path at the CORRECTED table, and the output path at r19;
 (ii) T3 (copied the defective line): k = umap.get(j) -> k = umap.get(int(t)), and the output path at r19.
Archived directories are never written. Reads NO environment variable."""
import os, difflib, hashlib, json
U="/workspace/uplift_2026-09-11"; R19=U+"/r19_trackF_reindex"; D=R19+"/devices"; FIXTF=R19+"/fixed_trackF"
os.makedirs(FIXTF, exist_ok=True)
for a,b in (("regime_labels.npz","regime_labels_fixed.npz"),("regime_vars.npz","regime_vars_fixed.npz")):
    p=f"{FIXTF}/{a}"
    if not os.path.islink(p): os.symlink(f"{R19}/{b}", p)
for d in ("out_r3_gates","out_r4p3","out_r6j1","out_r8_inbook","out_r7f2"): os.makedirs(f"{R19}/{d}", exist_ok=True)
def sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
REC={}
def patch(src, dst, edits, expect_sha):
    s0=open(src).read(); assert sha(src)==expect_sha, (src, sha(src)); s=s0
    for old,new,n in edits:
        c=s.count(old); assert c==n, (src, old[:80], c, n); s=s.replace(old,new)
    open(dst,"w").write(s)
    diff="".join(difflib.unified_diff(s0.splitlines(True), s.splitlines(True), fromfile=os.path.relpath(src,U), tofile=os.path.relpath(dst,U)))
    open(dst.replace(".py",".diff"),"w").write(diff)
    REC[os.path.basename(dst)]={"source":src,"source_sha256":expect_sha,"patched_sha256":sha(dst),"n_edits":len(edits),"diff_sha256":sha(dst.replace(".py",".diff"))}
    print(f"patched {os.path.basename(dst)}: {len(edits)} edits\n{diff}")
# ---- T2: regcomp / p3_an / p3_b (read the archived trackF labels) ----
patch(U+"/r3_gates/regcomp.py", D+"/regcomp_r19.py",
      [('R = "/workspace/uplift_2026-09-11/trackF"', f'R = "{FIXTF}"', 1),
       ('OUT = "/workspace/uplift_2026-09-11/r3_gates"', f'OUT = "{R19}/out_r3_gates"', 1)],
      "30fee017a80a1fbcba2c9c4a196fb35dd5663ff18b98d51865bd921dfa2ebaec")
patch(U+"/r4p3_an.py", D+"/p3_an_r19.py",
      [('Z=np.load(U+"/trackF/regime_labels.npz",allow_pickle=True)', f'Z=np.load("{FIXTF}/regime_labels.npz",allow_pickle=True)', 1),
       ('json.dump(OUT,open(R+"/RESULT_P3.json","w"),indent=1)', f'json.dump(OUT,open("{R19}/out_r4p3/RESULT_P3.json","w"),indent=1)', 1)],
      "528bcb737186eb8ae46730d50890ecfa9e45b173adbaf2bc976b71831475d4dc")
patch(U+"/r4p3_b.py", D+"/p3_b_r19.py",
      [('Z=np.load(U+"/trackF/regime_labels.npz",allow_pickle=True)', f'Z=np.load("{FIXTF}/regime_labels.npz",allow_pickle=True)', 1),
       ('json.dump(O,open(R+"/RESULT_P3B.json","w"),indent=1)', f'json.dump(O,open("{R19}/out_r4p3/RESULT_P3B.json","w"),indent=1)', 1)],
      "e14042f55253549f3eef63ce79673df7c3cbec0ff3cdaa612e29c003216d03f7")
# ---- T3: copied defect line ----
patch(U+"/r6j1_regime.py", D+"/j1_regime_r19.py",
      [('m = members[i]; k = umap.get(j)', 'm = members[i]; k = umap.get(int(t))', 1),
       ('OUT = "/workspace/uplift_2026-09-11/r6j1"', f'OUT = "{R19}/out_r6j1"', 1)],
      "79c28167cc7b44072b357de3f778c87fecf310dbfb7cb7f850edc3cc33e74ac4")
patch(U+"/r8_inbook/regime_gb.py", D+"/regime_gb_r19.py",
      [('m=MEM[i]; k=umap.get(j)', 'm=MEM[i]; k=umap.get(int(t))', 1),
       ('json.dump(OUT,open(R+"/REGIME_GIVEBACK.json","w"),indent=1)', f'json.dump(OUT,open("{R19}/out_r8_inbook/REGIME_GIVEBACK.json","w"),indent=1)', 1)],
      "578c8b8437b3b1154b7c77522495361660b93cd8dc8a54e1ecdfe51035c43f0d")
patch(U+"/r7f2/r7_fuel.py", D+"/r7_fuel_r19.py",
      [('m = members[i]; k = umap.get(j)', 'm = members[i]; k = umap.get(int(t))', 1),
       ('OUT="/workspace/uplift_2026-09-11/r7f2"', f'OUT="{R19}/out_r7f2"', 1)],
      "aecc09c46e1ec9fe486769f05f490f39da8d4cd5b7b295b96f0898fb929303a2")
# r7 downstream: OUT stays (it addresses the dev arms); the FUEL input and every output are redirected to OUT19
def r7(name, expect, extra=()):
    s=open(U+f"/r7f2/{name}").read()
    n_in=s.count('np.load(OUT+"/R7_FUEL.npz"'); n_out=s.count('open(OUT+"/R7_'); assert n_in==1 and n_out>=1, (name, n_in, n_out)
    edits=[('OUT=R+"/r7f2"', f'OUT=R+"/r7f2"; OUT19="{R19}/out_r7f2"', 1),
           ('np.load(OUT+"/R7_FUEL.npz"', 'np.load(OUT19+"/R7_FUEL.npz"', 1), ('open(OUT+"/R7_', 'open(OUT19+"/R7_', n_out)]+list(extra)
    patch(U+f"/r7f2/{name}", D+f"/{name[:-3]}_r19.py", edits, expect)
    s2=open(D+f"/{name[:-3]}_r19.py").read(); assert 'open(OUT+"' not in s2, name
r7("r7_screen.py",    "8dd02d3721c04c75d69c2778e9183d4cc015a3a107d01b86cfac7b4aa44c78ce")
r7("r7_screen2.py",   "c27852347f5d0e9d56df260fa554c87740daa515c5ac4957b6606f518ce39411")
r7("r7_spec.py",      "8408f9ec866b5ef788c81d43c09484ad56ba24452d6b5111bfbdd70bf894231b")
r7("r7_withinyear.py","993e8d5905af08c6c1cf4b6708e767c8d9b05eaf9c1311ef69af22188a0bf6bd")
r7("r7_final.py",     "391a7c1545c9452212eff667ed9252b085062e621e518c23e98c10d92e05b834",
   extra=[('m=members[i]; kk=umap.get(j)', 'm=members[i]; kk=umap.get(int(t))', 1)])
json.dump(REC, open(R19+"/receipts/RECEIPT_r19_patches.json","w"), indent=1)
print("PATCH_DONE")
