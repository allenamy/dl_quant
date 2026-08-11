import json, torch
from multi_asset.eval.swa_eval import swa_average
from multi_asset.train.train_dual_lob import build_dual_lob_model
fd="experiments/d1gate/d1_2026_01_run1/fold_0"; cfg=json.load(open("configs/d1gate/d1_2026_01_run1.json"))
mj=json.load(open(f"{fd}/metrics.json")); vh=mj["val_hist"]
raw=sorted([(e["epoch"],e["raw"]["composite"]) for e in vh if e.get("raw")], key=lambda x:x[1], reverse=True)[:3]
eps=[e for e,_ in raw]; print("top-3 raw epochs by valC:", eps)
paths=[f"{fd}/epoch_ckpts/raw_ep{e:03d}.pt" for e in eps]
avg=swa_average(paths, torch.device("cpu"))
one=torch.load(paths[0], map_location="cpu", weights_only=False)["state"]
print("avg keys == single ckpt keys:", set(avg)==set(one))
k=[n for n in avg if torch.is_floating_point(avg[n]) and avg[n].numel()>10][0]
print("averaged differs from ckpt0:", not torch.equal(avg[k], one[k]))
m=build_dual_lob_model(cfg["model"], 88, 20)
m.load_state_dict(avg); print("load_state_dict(avg) into fresh model: OK")
print("SWA LOGIC OK")
