"""Differential fuzz: plan_experiment at 409ea16 (old) vs the patched module (new), same inputs.
rho_pre >= 0.50 or None  => new record minus the 5 new keys must equal the old record exactly (json bytes).
rho_pre <  0.50          => old reasons kept first and unchanged, REBUILD appended; arms = old arms with
                            no_chase -> chase; every other old field unchanged except the arm-derived ones."""
import importlib.util, json, math, random, sys
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
OLD = load("cp_old", sys.argv[1]); NEW = load("cp_new", sys.argv[2])
NEWK = {"rebuild_rule", "rebuild_rho_threshold", "rho_pre", "rebuild", "rho_pre_detail"}
ARMK = {"arm", "arm_assigned", "arm_counts", "arm_notional_usdt", "no_chase_arm_net_usdt", "in_sample", "excluded_because"}
dump = lambda d: json.dumps(d, sort_keys=True, separators=(",", ":"))
rng = random.Random(20260919)
n_id = n_rb = n_rb_changed = n_insample_old = 0
bad = []
for i in range(20000):
    n = rng.choice([0, 1, 2, 3, 5, 8, 13, 30, 80])
    syms = [f"X{j:03d}USDT" for j in range(n)]
    one_sided = rng.random() < 0.4
    res = [(s, (-1 if one_sided else rng.choice([-1, 1])) * rng.uniform(0.01, 400.0)) for s in syms]
    gross = rng.choice([0.0, 500.0, 4300.0, 20000.0, 230000.0])
    net = None if rng.random() < 0.05 else rng.uniform(-0.05, 0.05) * gross - sum(r for _, r in res) * rng.random()
    w = rng.choice([{"chase": 0.5, "no_chase": 0.5}, {"chase": 1.0, "no_chase": 1.0}, {"chase": 1.0, "no_chase": 0.0}, None])
    excl = {s: "per_name_stop" for s in rng.sample(syms, min(len(syms), rng.choice([0, 0, 1, 2])))}
    kw = dict(residuals=res, seed=f"A{1788000000 + 14400 * i}", book_net_usdt=net, book_gross_usdt=gross,
              net_basis="fuzz", weights=w, exclude=excl)
    old = OLD.plan_experiment(**kw)
    n_insample_old += bool(old["in_sample"])
    rho = rng.choice([None, 0.5, math.nextafter(0.5, 1.0), rng.uniform(0.5, 1.2), 1.0, 0.0, rng.uniform(0.0, 0.5),
                      math.nextafter(0.5, 0.0), 0.257])
    new = NEW.plan_experiment(**kw, rho_pre=rho)
    if set(new) - set(old) != NEWK or set(old) - set(new):
        bad.append((i, "keyset")); continue
    nv = {k: v for k, v in new.items() if k not in NEWK}
    if rho is None or rho >= 0.5:
        n_id += 1
        if dump(nv) != dump(old) or new["rebuild"] is not False:
            bad.append((i, rho, "identity"))
    else:
        n_rb += 1
        exp_arm = {s: ("chase_forced" if a == "chase_forced" else "chase") for s, a in old["arm"].items()}
        n_rb_changed += exp_arm != old["arm"]
        ok = (new["rebuild"] is True and new["in_sample"] is False
              and new["excluded_because"][:-1] == old["excluded_because"]
              and new["excluded_before_assignment"] == old["excluded_before_assignment"]
              and new["excluded_because"][-1].startswith("REBUILD")
              and new["arm"] == exp_arm and new["arm_assigned"] == exp_arm
              and "no_chase" not in new["arm_counts"] and new["no_chase_arm_net_usdt"] == 0.0
              and dump({k: v for k, v in nv.items() if k not in ARMK}) == dump({k: v for k, v in old.items() if k not in ARMK})
              and NEW.recompute_check(new)["ok"])
        if not ok:
            bad.append((i, rho, "rebuild"))
print(f"cases=20000 identity_cases(rho>=0.5 or None)={n_id} rebuild_cases(rho<0.5)={n_rb} "
      f"rebuild_cases_where_arms_changed={n_rb_changed} old_in_sample={n_insample_old} mismatches={len(bad)}")
print("first mismatches:", bad[:5])
sys.exit(1 if bad else 0)
