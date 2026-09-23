"""Adapter: let the news2 B-part gates drive the INTEGRATOR'S replay core (nc_hist_features.py).

Why an adapter and not a fix to news2_hist_features: the nc King block calls `NC` (nc_contract) and
`TR` (tradability), which the producer imports at module level. Injecting those into news2's own core
would create a second replay core for the same tree -- the same shape as the D11 twin this round
removed. So the gates change what they drive, and nc_hist_features stays the single replay core.

It exposes one call, `Replay.at(A)`, returning the dict shape the news2 gates already expect
(`m`, `king_X78`, `X82`, `X89`, `qvm`, `rev24`, `fe_v`, `fn_v`, `f89_names`, `f89_finite_share_raw`,
`btcv_anchor`), assembled from pass1_anchor + pass2_anchor.

Two things it refuses rather than papers over:
  * pass2 needs the as-of member history (merge1's members_hist_all.npz). If it is absent, `at()`
    returns pass1 only and marks `X82`/`X89` as UNAVAILABLE with the reason -- it does not substitute
    the current anchor's members, which is exactly the D2 defect this release exists to remove.
  * every tree it opens must carry a PATCH_RECEIPT whose shas match; nc_hist_features.set_tree does
    that check and this adapter does not weaken it.

usage: imported by the news2 gates; see Replay.__init__ for the paths it takes.
"""
import json, os, sys

import numpy as np


class Replay:
    def __init__(self, nc_devices, tree, cfg_path, work, members_hist_npz=None):
        sys.path.insert(0, nc_devices)
        import nc_hist_features as H
        self.H = H
        self.rec = H.set_tree(tree)
        self.I = H.Inputs()
        self.king = H._king_block()
        self.mini = H._mini_block()
        self.cf = H._combo_funcs()
        self.cfg = json.load(open(cfg_path))
        self.P = self.cfg["params"]
        self.work = work
        os.makedirs(work, exist_ok=True)
        self.MH = None
        self.mh_why = "members_hist not supplied"
        if members_hist_npz and os.path.exists(members_hist_npz):
            z = np.load(members_hist_npz)
            self.MH = {int(a): z["idx"][z["off"][i]:z["off"][i + 1]].astype(np.int64)
                       for i, a in enumerate(z["anchors"])}
            self.mh_why = None
        elif members_hist_npz:
            self.mh_why = f"members_hist absent at {members_hist_npz} (merge1 not finished?)"

    def tree_outputs(self):
        return self.rec["outputs"]

    def at(self, A, cols="members"):
        r1 = self.H.pass1_anchor(self.I, int(A), self.P, self.cfg, self.king)
        out = dict(r1)
        if "m" not in r1:
            out["X82"] = out["X89"] = None
            out["unavailable"] = "pass1 produced no King features (producer would have skipped this anchor)"
            return out
        if self.MH is None:
            out["X82"] = out["X89"] = None
            out["unavailable"] = f"pass2 not run: {self.mh_why}"
            return out
        if int(A) not in self.MH:
            out["X82"] = out["X89"] = None
            out["unavailable"] = f"pass2 not run: anchor {A} absent from members_hist"
            return out
        r2 = self.H.pass2_anchor(self.I, int(A), self.MH, self.work, self.mini, self.cf, cols=cols)
        out.update(r2)
        return out


def main():
    """Smoke test: open a tree and replay the given anchors, printing what is and is not available."""
    nc_dev, tree, cfg, work, out_path = sys.argv[1:6]
    mh = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] != "-" else None
    anchors = [int(x) for x in sys.argv[7:]]
    import hashlib, time
    R = Replay(nc_dev, tree, cfg, work, mh)
    rows = []
    for A in anchors:
        t = time.time()
        r = R.at(A)
        row = {"anchor": A, "seconds": round(time.time() - t, 2),
               "n_members": int(len(r["m"])) if r.get("m") is not None else None,
               "king_X78": list(r["king_X78"].shape) if r.get("king_X78") is not None else None,
               "X82": list(r["X82"].shape) if r.get("X82") is not None else None,
               "X89": list(r["X89"].shape) if r.get("X89") is not None else None,
               "n_legal": r.get("n_legal"), "n_cand": r.get("n_cand"),
               "unavailable": r.get("unavailable")}
        rows.append(row)
        print(json.dumps(row), flush=True)
    rec = {"device": "news2_nc_adapter.py",
           "self_sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "tree": tree, "tree_outputs": R.tree_outputs(), "members_hist": mh, "members_hist_why": R.mh_why,
           "rows": rows,
           "PASS1_OK": all(r["king_X78"] is not None for r in rows),
           "PASS2_OK": all(r["X89"] is not None for r in rows)}
    json.dump(rec, open(out_path, "w"), indent=1)
    print(f"NEWS2_NC_ADAPTER pass1_ok={rec['PASS1_OK']} pass2_ok={rec['PASS2_OK']} anchors={len(rows)} "
          f"receipt_sha256={hashlib.sha256(open(out_path,'rb').read()).hexdigest()}", flush=True)


if __name__ == "__main__":
    main()
