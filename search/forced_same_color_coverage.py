"""
Follow-up to cycle_forced_pairs (wake 04:00 23-07):

For each of the 10 forced_same partner-pairs of chain 45, test which of the
5 colors they can jointly occupy under T_44. That is, for pair (a, b) and
color c: add unit clauses color(a)=c AND color(b)=c to CNF(T_44), solve.

If SAT for c: this pair CAN be color c in some T_44 coloring.
If UNSAT for c: this pair CANNOT be color c under any T_44 coloring.

Then aggregate across the 10 forced_same pairs: which color-classes are
covered by at least one pair being satisfiable at that color?

Critical for structural argument N=90 UNSAT:
  - If EVERY color c in 0..4 has AT LEAST ONE forced_same partner-pair (a,b)
    with (color(a)=color(b)=c) achievable under T_44 — then for any color
    assigned to chain 45, there's a forced-same partner-pair matching that
    color, which makes triple (a,b,45) mono. ⇒ N=90 UNSAT structurally
    proved via T_44 forcing + pigeonhole on colors.
  - If some color c is not achievable by any forced_same pair, the argument
    incomplete for that c — need free/forced_different pairs to fill gaps,
    which is more delicate.

Pre-registration (before running):
  H_full_cover (0.55): all 5 colors covered by some forced_same pair.
  H_partial_cover (0.35): 3-4 colors covered; the missing color(s) need
    other machinery to close the UNSAT argument.
  H_thin_cover (0.10): 1-2 colors covered only; forced_same alone doesn't
    close the structural argument.

Method:
  1. Load cnf as before (via cycle_forced_pairs.build_cnf).
  2. For each pair in forced_same list, for c in 0..4:
       add color(a)=c ∧ color(b)=c, solve. Record SAT/UNSAT.
  3. Aggregate: colors_covered = {c | at least one forced_same pair SAT at c}.
  4. Emit receipt with sha16.
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
from cycle_forced_pairs import build_cnf, partner_pairs, _wake_iso

from pysat.solvers import Minisat22


TARGET = 45

# From cycle_forced_pairs run1 (sha16=5fa65016a6417fb8), the 10 forced_same
# pairs. Hard-coded to keep this script self-contained; re-derive via
# cycle_forced_pairs.py if graph changes.
FORCED_SAME = [
    (1, 13), (1, 23), (1, 43),
    (3, 3), (5, 5), (7, 19),
    (9, 9), (11, 17), (15, 15),
    (35, 55),
]


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


def color_coverage(clauses, var, pair, k):
    """For pair (a, b), test SAT of color(a)=color(b)=c for each c in [0..k).

    Returns dict c -> {sat: bool, time_s: float}."""
    a, b = pair
    out = {}
    for c in range(k):
        # For intra-chain pair (a, a), just fix color(a)=c once.
        with Minisat22(bootstrap_with=clauses) as solver:
            solver.add_clause([var[(a, c)]])
            if a != b:
                solver.add_clause([var[(b, c)]])
            t0 = time.time()
            sat = solver.solve()
            t = time.time() - t0
        out[c] = {"sat": bool(sat), "time_s": round(t, 4)}
    return out


def _cli():
    ap = argparse.ArgumentParser(
        description="Test color-coverage of 10 forced-same partner-pairs "
                    "of chain 45 under T_44.")
    ap.add_argument("--N", type=int, default=90)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    N, k = args.N, args.k
    t_start = time.time()

    print(f"COLOR-COVERAGE of forced-same pairs of chain {TARGET}, N={N} k={k}")

    chain_by_root = chains_up_to_N(N)
    all_roots = sorted(chain_by_root.keys())
    other_roots = [r for r in all_roots if r != TARGET]
    triples = forbidden_triples(N)
    T_target, T_other = split_triples_by_root(triples, TARGET)

    # sanity: FORCED_SAME still matches the graph
    known_pairs, _ = partner_pairs(T_target, TARGET)
    for p in FORCED_SAME:
        # intra-chain pair (r, r) present in triples with tri==(r, r, target)
        if p[0] == p[1]:
            self_tri = tuple(sorted([p[0], p[0], TARGET]))
            if self_tri not in T_target:
                print(f"  WARN: intra-chain pair {p} not in T_45 anymore.")
        elif p not in known_pairs:
            print(f"  WARN: pair {p} no longer in partner set.")

    clauses, var = build_cnf(other_roots, T_other, k)
    n_vars = max(var.values())
    n_clauses = len(clauses)
    print(f"  CNF: vars={n_vars} clauses={n_clauses}")

    print(f"\n=== COLOR COVERAGE PER PAIR ===")
    per_pair = {}
    colors_covered = set()
    color_supporters = {c: [] for c in range(k)}
    for p in FORCED_SAME:
        cov = color_coverage(clauses, var, p, k)
        per_pair[f"{p[0]}_{p[1]}"] = cov
        line = f"  pair ({p[0]:2}, {p[1]:2}): "
        row = []
        for c in range(k):
            marker = "SAT" if cov[c]["sat"] else "unsat"
            row.append(f"c{c}={marker}")
            if cov[c]["sat"]:
                colors_covered.add(c)
                color_supporters[c].append(p)
        print(line + "  ".join(row))

    print(f"\n=== AGGREGATE COVERAGE ===")
    print(f"  colors covered by at least one forced-same pair: "
          f"{sorted(colors_covered)} ({len(colors_covered)}/{k})")
    for c in range(k):
        print(f"  color {c}: supporters = {color_supporters[c]}")

    # Hypothesis verdict
    if len(colors_covered) == k:
        hypothesis = "H_full_cover"
        print(f"\n  === HYPOTHESIS SUPPORTED: H_full_cover ({k}/{k}) ===")
        print(f"  For any color c in [0..{k-1}], SOME forced-same partner-pair")
        print(f"  (a, b) can jointly take color c under T_44. Therefore:")
        print(f"    - assign color(45) = c",)
        print(f"    - pick a forced-same partner-pair supporting color c")
        print(f"    - triple (a, b, 45) is mono-c")
        print(f"  => N=90 UNSAT structurally, via T_44 forcing + color pigeon.")
        print(f"  !! NOTE: this shows EXISTENCE per color, not FORALL colorings.")
        print(f"     Universal cover test needed (see universal_cover.py).")
    elif len(colors_covered) >= 3:
        hypothesis = "H_partial_cover"
        missing = set(range(k)) - colors_covered
        print(f"\n  === HYPOTHESIS SUPPORTED: H_partial_cover "
              f"({len(colors_covered)}/{k}) ===")
        print(f"  Colors missing: {sorted(missing)}. Structural argument")
        print(f"  incomplete for those colors — need free / forced_different")
        print(f"  pair machinery for gap-filling.")
    else:
        hypothesis = "H_thin_cover"
        print(f"\n  === HYPOTHESIS SUPPORTED: H_thin_cover "
              f"({len(colors_covered)}/{k}) ===")
        print(f"  Too few colors covered; forced-same alone insufficient.")

    elapsed = time.time() - t_start
    print(f"\n  total_elapsed_s: {elapsed:.2f}")

    if args.out:
        receipt = {
            "meta": {
                "method": "color-coverage of 10 forced-same partner-pairs of "
                          "chain 45 via Minisat22",
                "N": N, "k": k,
                "target_root": TARGET,
                "n_forced_same_pairs": len(FORCED_SAME),
                "wake": _wake_iso(),
                "tool": "forced_same_color_coverage.py",
                "tool_version": "23-07-2026 wake 04:00",
                "predecessor": "cycle_forced_pairs.py run1 sha16=5fa65016a6417fb8",
                "cnf": {"n_vars": n_vars, "n_clauses": n_clauses},
                "pre_registration": {
                    "H_full_cover": 0.55,
                    "H_partial_cover": 0.35,
                    "H_thin_cover": 0.10,
                },
            },
            "result": {
                "per_pair": per_pair,
                "colors_covered": sorted(colors_covered),
                "n_colors_covered": len(colors_covered),
                "color_supporters": {str(c): [list(p) for p in ps]
                                     for c, ps in color_supporters.items()},
                "hypothesis_supported": hypothesis,
                "total_elapsed_s": round(elapsed, 3),
            },
        }
        _write_receipt(args.out, receipt)


if __name__ == "__main__":
    _cli()
