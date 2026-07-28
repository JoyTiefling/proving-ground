"""
CYCLE-SAT: are ALL partner-pairs of chain 45 forced same-color under T_44
at N=90, k=5?

Context (wake 04:00 23-07-2026, 9th consecutive frontier wake):
  - Wake 02:00 proved: pair (35,55) is forced same-color under T_44 alone.
    (Minisat22 UNSAT for color(35)=0 ∧ color(55)!=0 in 0.44s.)
  - Chain 45 has ~22 distinct partner-pairs at N=90 (roots (a,b) with
    triple (a,b,45) forbidden, i.e. a+b congruent to 0 mod odd-root of
    something that lands on 45's chain).
  - Question: is (35,55) special, or is EVERY partner-pair forced?

Pre-registration (from state.md wake 02:00 close):
  - H_all_forced (0.35): every partner-pair (a, 90-a-etc) is T_44-forced
    same-color. Structural argument N=90 UNSAT becomes clean: T_44 forces
    a chain of same-color pairs incident to 45, then any color(45)
    completes a mono-triple.
  - H_35_55_special (0.45): (35,55) is unique — likely because at N=89 the
    chain 45 alone had degree 60 already, and (35,55) sits at a spectral
    "corner" of the partner-graph. Prior favors this because 20/20 diverse
    T_44 colorings all had color(35)==color(55), which is stronger evidence
    for local structure than for uniform forcing.
  - H_broad_not_universal (0.20): some subset (>1, <all) is forced; the
    rest can vary.

Method:
  1. Compute chain roots and forbidden triples for N=90, k=5.
  2. Split triples into T_45 (containing root 45) and T_44 (rest).
  3. Enumerate distinct partner-pairs (a, b) — pairs (a, b) sorted with
     (a, b, 45) in T_45. If duplicates (e.g., (a, 45, 45)), collapse.
  4. Build CNF once from T_44 constraints on the 44 non-target roots.
  5. For each partner-pair (a, b):
     - Run A: add unit clauses color(a)=0 and color(b)!=0. If UNSAT ->
       pair is T_44-forced same-color.
     - Run B (sanity): only color(a)=0. Must be SAT (T_44 satisfiable).
     - Run C (sanity): color(a)=0 AND color(b)=0. If negation of Run A
       (both same color), this must be SAT for forced pairs; otherwise
       we know the pair is trivially forced-different (weird).
  6. Aggregate: count forced-same, forced-different (Run C UNSAT), or
     free. Compare against pre-registration.

Receipt: JSON with sort_keys + sha16 self-hash (rule 18-07).
"""
import sys
import os
import time
import json
import argparse
import hashlib
import datetime

sys.path.insert(0, os.path.dirname(__file__))
from explore_pigeonhole_45 import (
    chains_up_to_N, forbidden_triples, split_triples_by_root,
)

from pysat.solvers import Minisat22
from pysat.formula import CNF


TARGET = 45


def _wake_iso():
    return (datetime.datetime.now(datetime.timezone.utc)
            .isoformat(timespec="seconds").replace("+00:00", "Z"))


def _write_receipt(out_path, receipt):
    if not out_path:
        sys.stderr.write("  [warn] --out not given; result NOT persisted.\n")
        return
    payload = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True)
    sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    receipt["sha16"] = sha
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"  receipt -> {out_path}  sha16={sha}")


def build_cnf(other_roots, T_other, k):
    """Return (cnf_clauses_list, var_map). cnf as list of clauses to be
    re-bootstrapped per solver instance (Minisat22 doesn't reset)."""
    clauses = []
    var = {}
    n = 0
    for r in other_roots:
        for c in range(k):
            n += 1
            var[(r, c)] = n

    for r in other_roots:
        clauses.append([var[(r, c)] for c in range(k)])
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                clauses.append([-var[(r, c1)], -var[(r, c2)]])

    for tri in T_other:
        roots_in_tri = set(tri)
        if not roots_in_tri.issubset(set(other_roots)):
            continue
        for c in range(k):
            clause = [-var[(r, c)] for r in roots_in_tri]
            clauses.append(clause)

    return clauses, var


def partner_pairs(T_target, target_root):
    """Enumerate distinct sorted partner-pairs (a, b) in T_target excluding
    duplicates (e.g., (target, target, x) collapses to (x, target)).

    Returns list of (a, b) tuples sorted lexicographically, a <= b, both != target.
    Pairs where one leg is target itself (i.e. triple (a, target, target)) are
    kept as (a, target) but marked with target-included flag: we skip those in
    Run A (can't fix color(target) as it's the whole point)."""
    pairs = set()
    self_pairs = set()  # (a, target_root) — target repeated
    for tri in T_target:
        rest = [r for r in tri if r != target_root]
        if len(rest) == 2:
            a, b = sorted(rest)
            pairs.add((a, b))
        elif len(rest) == 1:
            # triple (a, target_root, target_root) — target's chain has both
            # v and 2v both roots resolve to target itself. Rare.
            self_pairs.add((rest[0], target_root))
    return sorted(pairs), sorted(self_pairs)


def solve_forced(clauses, var, a, b, k):
    """Test if pair (a, b) is forced same-color under given CNF.

    Returns dict with runA/runB/runC results (SAT bool, time, witness pair).
    """
    result = {}
    # Run A: color(a)=0 AND color(b) != 0.
    with Minisat22(bootstrap_with=clauses) as solver:
        solver.add_clause([var[(a, 0)]])
        solver.add_clause([-var[(b, 0)]])
        t0 = time.time()
        sat_a = solver.solve()
        t_a = time.time() - t0
        model = solver.get_model() if sat_a else None
    witness_a = None
    if sat_a and model is not None:
        pos = set(m for m in model if m > 0)
        c_a = c_b = None
        for c in range(k):
            if var[(a, c)] in pos and c_a is None:
                c_a = c
            if var[(b, c)] in pos and c_b is None:
                c_b = c
        witness_a = [c_a, c_b]
    result["A"] = {"sat": bool(sat_a), "time_s": round(t_a, 4),
                   "witness_pair": witness_a}

    # Run B: only color(a)=0. Sanity.
    with Minisat22(bootstrap_with=clauses) as solver:
        solver.add_clause([var[(a, 0)]])
        t0 = time.time()
        sat_b = solver.solve()
        t_b = time.time() - t0
    result["B"] = {"sat": bool(sat_b), "time_s": round(t_b, 4)}

    # Run C: color(a)=0 AND color(b)=0. Same-color feasibility.
    with Minisat22(bootstrap_with=clauses) as solver:
        solver.add_clause([var[(a, 0)]])
        solver.add_clause([var[(b, 0)]])
        t0 = time.time()
        sat_c = solver.solve()
        t_c = time.time() - t0
    result["C"] = {"sat": bool(sat_c), "time_s": round(t_c, 4)}

    # Verdict per pair:
    if not sat_b:
        result["verdict"] = "BUG_baseline_UNSAT"
    elif sat_a and sat_c:
        result["verdict"] = "free"
    elif sat_a and not sat_c:
        result["verdict"] = "forced_different"  # weird
    elif (not sat_a) and sat_c:
        result["verdict"] = "forced_same"
    elif (not sat_a) and (not sat_c):
        result["verdict"] = "BUG_both_UNSAT"
    return result


def _cli():
    ap = argparse.ArgumentParser(
        description="Cycle SAT: is every partner-pair of chain 45 forced "
                    "same-color under T_44 at N=90 k=5?")
    ap.add_argument("--N", type=int, default=90)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    N, k = args.N, args.k
    t_start = time.time()

    print(f"CYCLE-SAT partner-pairs: target={TARGET} N={N} k={k}, "
          f"solver=Minisat22")

    chain_by_root = chains_up_to_N(N)
    all_roots = sorted(chain_by_root.keys())
    if TARGET not in all_roots:
        print(f"  ERR: target {TARGET} not a chain root at N={N}.")
        return

    other_roots = [r for r in all_roots if r != TARGET]
    triples = forbidden_triples(N)
    T_target, T_other = split_triples_by_root(triples, TARGET)
    print(f"  chains: {len(all_roots)} ({len(other_roots)} non-target)")
    print(f"  triples total: {len(triples)}  T_44: {len(T_other)}  "
          f"T_45: {len(T_target)}")

    pairs, self_pairs = partner_pairs(T_target, TARGET)
    print(f"  distinct partner-pairs (both roots != target): {len(pairs)}")
    print(f"  self-partner-pairs (a, target, target): {len(self_pairs)} "
          f"(skipped in Run A — no free variable to constrain)")

    clauses, var = build_cnf(other_roots, T_other, k)
    n_vars = max(var.values())
    n_clauses = len(clauses)
    print(f"  CNF: vars={n_vars} clauses={n_clauses}")

    print(f"\n=== CYCLE OVER {len(pairs)} PAIRS ===")
    results = {}
    forced_same = []
    free = []
    weird = []
    for i, (a, b) in enumerate(pairs, 1):
        r = solve_forced(clauses, var, a, b, k)
        v = r["verdict"]
        results[f"{a}_{b}"] = r
        marker = {"forced_same": "===",
                  "free": "   ",
                  "forced_different": "*!*",
                  "BUG_baseline_UNSAT": "!!!",
                  "BUG_both_UNSAT": "!!!"}.get(v, "???")
        tA = r["A"]["time_s"]
        tC = r["C"]["time_s"]
        print(f"  [{i:2}/{len(pairs)}] {marker} pair ({a:2}, {b:2}) -> "
              f"{v}   (A: {'SAT' if r['A']['sat'] else 'UNSAT'} {tA:.3f}s, "
              f"C: {'SAT' if r['C']['sat'] else 'UNSAT'} {tC:.3f}s)")
        if v == "forced_same":
            forced_same.append((a, b))
        elif v == "free":
            free.append((a, b))
        else:
            weird.append(((a, b), v))

    elapsed = time.time() - t_start

    # === Hypothesis check ===
    n_pairs = len(pairs)
    print(f"\n=== AGGREGATE ===")
    print(f"  forced_same: {len(forced_same)}/{n_pairs}")
    print(f"  free       : {len(free)}/{n_pairs}")
    print(f"  weird      : {len(weird)}/{n_pairs} : {weird}")

    if len(forced_same) == n_pairs and n_pairs > 0:
        hypothesis = "H_all_forced"
        print(f"\n  === HYPOTHESIS SUPPORTED: H_all_forced ===")
        print(f"  Every one of the {n_pairs} partner-pairs of chain 45 is "
              f"T_44-forced same-color.")
        print(f"  Structural corollary: T_44 partitions all partners of 45 "
              f"into color-equivalence classes; whichever color assigned to")
        print(f"  chain 45 collides with at least one class (pigeonhole 5<C+1"
              f" for C classes). ⇒ N=90 UNSAT structurally.")
    elif (35, 55) in forced_same and len(forced_same) == 1:
        hypothesis = "H_35_55_special"
        print(f"\n  === HYPOTHESIS SUPPORTED: H_35_55_special ===")
        print(f"  Only (35, 55) is forced. The 20/20 alignment seen in "
              f"pigeonhole run was local structure.")
        print(f"  N=90 UNSAT proof needs a different completion — (35,55) "
              f"alone doesn't cover all colors.")
    elif len(forced_same) > 1 and len(forced_same) < n_pairs:
        hypothesis = "H_broad_not_universal"
        print(f"\n  === HYPOTHESIS SUPPORTED: H_broad_not_universal ===")
        print(f"  {len(forced_same)} pairs forced, {len(free)} free. "
              f"Look at which pairs are forced — subgroup structure?")
    else:
        hypothesis = "unclear"
        print(f"\n  === Result doesn't match any pre-registered hypothesis "
              f"cleanly ===")

    print(f"\n  total_elapsed_s: {elapsed:.2f}")

    if args.out:
        receipt = {
            "meta": {
                "method": "cycle SAT over all partner-pairs of chain 45 "
                          "via Minisat22 CDCL (pysat)",
                "N": N, "k": k,
                "target_root": TARGET,
                "wake": _wake_iso(),
                "tool": "cycle_forced_pairs.py",
                "tool_version": "23-07-2026 wake 04:00",
                "chains": len(all_roots),
                "other_chains": len(other_roots),
                "triples_total": len(triples),
                "triples_T_44": len(T_other),
                "triples_T_45": len(T_target),
                "n_partner_pairs": n_pairs,
                "n_self_pairs_skipped": len(self_pairs),
                "cnf": {"n_vars": n_vars, "n_clauses": n_clauses},
                "pre_registration": {
                    "H_all_forced": 0.35,
                    "H_35_55_special": 0.45,
                    "H_broad_not_universal": 0.20,
                },
            },
            "result": {
                "per_pair": results,
                "forced_same": [list(p) for p in forced_same],
                "free": [list(p) for p in free],
                "weird": [{"pair": list(w[0]), "verdict": w[1]} for w in weird],
                "hypothesis_supported": hypothesis,
                "total_elapsed_s": round(elapsed, 3),
            },
        }
        _write_receipt(args.out, receipt)


if __name__ == "__main__":
    _cli()
