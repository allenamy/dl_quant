import re, hashlib
src = open("/workspace/pod_fea_ext.py").read()
assert hashlib.sha256(src.encode()).hexdigest().startswith("02157bda4fe0f6cd"), "pod_fea_ext.py identity changed"
new = src
new = new.replace('        nf = np.maximum(f_[E] - f_[E - w], 1)\n        if nm == "ret5":\n            VAL.append(((s_[E] - s_[E - w])).astype(np.float32)); val_names.append(f"{nm}_sum_{w}")\n        else:\n            VAL.append(((s_[E] - s_[E - w]) / nf).astype(np.float32)); val_names.append(f"{nm}_mean_{w}")',
                  '        Ew = np.maximum(E - w, 0)   # E-0909-A clamp (was E - w: negative index wraps to the cache tail)\n        nf = np.maximum(f_[E] - f_[Ew], 1)\n        if nm == "ret5":\n            VAL.append(((s_[E] - s_[Ew])).astype(np.float32)); val_names.append(f"{nm}_sum_{w}")\n        else:\n            VAL.append(((s_[E] - s_[Ew]) / nf).astype(np.float32)); val_names.append(f"{nm}_mean_{w}")')
new = new.replace('    nf = np.maximum(CS["ret5"][1][E] - CS["ret5"][1][E - w], 1)\n    mm = (CS["ret5"][0][E] - CS["ret5"][0][E - w]) / nf\n    vv = np.sqrt(np.maximum((r2s[E] - r2s[E - w]) / nf - mm ** 2, 0))',
                  '    Ew = np.maximum(E - w, 0)   # E-0909-A clamp\n    nf = np.maximum(CS["ret5"][1][E] - CS["ret5"][1][Ew], 1)\n    mm = (CS["ret5"][0][E] - CS["ret5"][0][Ew]) / nf\n    vv = np.sqrt(np.maximum((r2s[E] - r2s[Ew]) / nf - mm ** 2, 0))')
assert new.count("E-0909-A clamp") == 2, "patch sites not found"
open("/workspace/review_scratch/pod_fea_ext_clamp.py", "w").write(new)
import difflib
d = list(difflib.unified_diff(src.splitlines(), new.splitlines(), "pod_fea_ext.py", "pod_fea_ext_clamp.py", lineterm="", n=0))
print("\n".join(d)); print("clamp builder written; changed lines:", sum(1 for l in d if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))))
