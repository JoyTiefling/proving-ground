"""
STRICT TEST v2 via pysat/Minisat: is pair (35, 55) forced same-color under
T_44 in N=90, k=5?

v1 (test_forced_pair_35_55.py) used a home-grown DPLL and timed out at 300s
after 41M decisions with no verdict. Not a hardware wall — an instrument wall.
Same test in real CDCL SAT solver: ~seconds.

SAT encoding:
  Variables: x[r,c] = "chain root r has color c", for r in 44 non-target roots
             and c in [0..k-1]. Total 44*5=220 variables.
  Clauses:
    (a) exactly-one color per root: at-least-one + pairwise at-most-one.
    (b) for each triple (a,b,c) in T_44 and each color k:
        NOT (x[a,k] AND x[b,k] AND x[c,k]).
        Duplicates in triple naturally collapse to shorter clause.
    (c) unit color(35) = 0:                x[35, 0].
    (d) unit color(55) != 0 (opposite):    NOT x[55, 0].

Solver: Minisat22 (pysat.solvers).
  SAT   -> witness -> H_forced refuted (H_partial/H_correlation alive).
  UNSAT -> H_forced proven for T_44.

Pre-registration (unchanged from v1): H_forced 0.55 / H_partial 0.30 /
H_correlation 0.15.

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
PAIR = (35, 55)
FIXED_ROOT = 35
FIXED_COLOR = 0
FORBID_ROOT = 55
FORBID_COLOR = 0


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
    """Return (cnf, var_map) where var_map[(r, c)] = DIMACS var index."""
    cnf = CNF()
    # var index starts at 1
    var = {}
    n = 0
    for r in other_roots:
        for c in range(k):
            n += 1
            var[(r, c)] = n

    # (a) exactly-one color per root
    for r in other_roots:
        # at-least-one
        cnf.append([var[(r, c)] for c in range(k)])
        # at-most-one: pairwise
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                cnf.append([-var[(r, c1)], -var[(r, c2)]])

    # (b) no monochromatic triple in T_other under any color
    for tri in T_other:
        # tri may have repeated roots; collect unique roots present
        roots_in_tri = set(tri)
        # ensure they are actually chain roots we track
        if not roots_in_tri.issubset(set(other_roots)):
            # triple references target root or beyond — skip (belongs to T_target)
            continue
        for c in range(k):
            clause = [-var[(r, c)] for r in roots_in_tri]
            cnf.append(clause)

    return cnf, var


def _cli():
    ap = argparse.ArgumentParser(
        description="Strict SAT test (Minisat22): is pair (35,55) forced "
                    "same-color under T_44 at N=90 k=5?")
    ap.add_argument("--N", type=int, default=90)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--time-cap", type=float, default=300.0)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    N, k = args.N, args.k
    t_start = time.time()

    print(f"STRICT TEST v2 forced-pair (35,55): N={N} k={k}, solver=Minisat22")

    chain_by_root = chains_up_to_N(N)
    all_roots = sorted(chain_by_root.keys())
    if TARGET not in all_roots:
        print(f"  ERR: target {TARGET} not a chain root at N={N}.")
        return
    if FIXED_ROOT not in all_roots or FORBID_ROOT not in all_roots:
        print(f"  ERR: pair {PAIR} not both roots at N={N}.")
        return

    other_roots = [r for r in all_roots if r != TARGET]
    triples = forbidden_triples(N)
    T_target, T_other = split_triples_by_root(triples, TARGET)
    print(f"  chains: {len(all_roots)} ({len(other_roots)} non-target)")
    print(f"  triples total: {len(triples)}  T_44: {len(T_other)}  "
          f"T_45: {len(T_target)}")

    cnf, var = build_cnf(other_roots, T_other, k)
    n_vars = max(var.values())
    n_clauses = len(cnf.clauses)
    print(f"  CNF: vars={n_vars} clauses={n_clauses}")

    # === RUN 1: pair constrained (color(35)=0, color(55) != 0) ===
    print(f"\n  RUN A (forced-different): color[{FIXED_ROOT}]={FIXED_COLOR}, "
          f"color[{FORBID_ROOT}] != {FORBID_COLOR}")
    with Minisat22(bootstrap_with=cnf.clauses) as solver:
        # unit assumptions
        solver.add_clause([var[(FIXED_ROOT, FIXED_COLOR)]])
        solver.add_clause([-var[(FORBID_ROOT, FORBID_COLOR)]])
        t0 = time.time()
        sat_a = solver.solve()
        t_a = time.time() - t0
        model_a = solver.get_model() if sat_a else None
    print(f"    result: {'SAT' if sat_a else 'UNSAT'}  ({t_a:.3f}s)")

    witness_a = None
    if sat_a and model_a is not None:
        witness_a = {}
        pos = set(m for m in model_a if m > 0)
        for r in other_roots:
            for c in range(k):
                if var[(r, c)] in pos:
                    witness_a[r] = c
                    break
        c35 = witness_a.get(FIXED_ROOT)
        c55 = witness_a.get(FORBID_ROOT)
        print(f"    witness: color(35)={c35}, color(55)={c55}")

    # === RUN 2: control — sanity, unconstrained pair should be SAT ===
    print(f"\n  RUN B (baseline control): only color[{FIXED_ROOT}]={FIXED_COLOR}")
    with Minisat22(bootstrap_with=cnf.clauses) as solver:
        solver.add_clause([var[(FIXED_ROOT, FIXED_COLOR)]])
        t0 = time.time()
        sat_b = solver.solve()
        t_b = time.time() - t0
        model_b = solver.get_model() if sat_b else None
    print(f"    result: {'SAT' if sat_b else 'UNSAT'}  ({t_b:.3f}s)")
    witness_b = None
    if sat_b and model_b is not None:
        witness_b = {}
        pos = set(m for m in model_b if m > 0)
        for r in other_roots:
            for c in range(k):
                if var[(r, c)] in pos:
                    witness_b[r] = c
                    break
        c35b = witness_b.get(FIXED_ROOT)
        c55b = witness_b.get(FORBID_ROOT)
        print(f"    witness: color(35)={c35b}, color(55)={c55b}")

    # === RUN 3: NEGATIVE CONTROL — force color(55)=0 too. Must be SAT.
    #     (from run1 we know all 20 diverse colorings had color(35)==color(55).)
    print(f"\n  RUN C (negative control): color[{FIXED_ROOT}]=0 and "
          f"color[{FORBID_ROOT}]=0. Must be SAT if v1-experiment sane.")
    with Minisat22(bootstrap_with=cnf.clauses) as solver:
        solver.add_clause([var[(FIXED_ROOT, FIXED_COLOR)]])
        solver.add_clause([var[(FORBID_ROOT, FIXED_COLOR)]])
        t0 = time.time()
        sat_c = solver.solve()
        t_c = time.time() - t0
    print(f"    result: {'SAT' if sat_c else 'UNSAT'}  ({t_c:.3f}s)")

    # === Verdict for pre-registered H_forced ===
    elapsed = time.time() - t_start
    verdict = None
    if sat_a:
        # sanity: verify witness respects T_44
        ok = True
        for tri in T_other:
            roots_in_tri = set(tri)
            if not roots_in_tri.issubset(set(other_roots)):
                continue
            cs = [witness_a.get(r) for r in roots_in_tri]
            if all(c == cs[0] and c is not None for c in cs):
                ok = False
                break
        c35 = witness_a[FIXED_ROOT]
        c55 = witness_a[FORBID_ROOT]
        if c35 != FIXED_COLOR or c55 == FORBID_COLOR:
            ok = False
        if ok:
            verdict = "H_forced_REFUTED"
            print(f"\n=== VERDICT: H_forced REFUTED ===")
            print(f"  Under T_44 alone (weaker than full T at N=90), pair "
                  f"(35,55) is NOT forced same-color.")
            print(f"  The 20/20 alignment seen in run1 is a coincidence-of-"
                  f"sample / statistical bias, not a structural forcing.")
            print(f"  Consequence for structure hunt: forcing must invoke "
                  f"T_45 as well, which is trivially true (all N=90 UNSAT).")
        else:
            verdict = "BUG_WITNESS_INVALID"
    else:
        verdict = "H_forced_PROVEN"
        print(f"\n=== VERDICT: H_forced PROVEN ===")
        print(f"  Under T_44 alone, no valid coloring exists with "
              f"color(35) != color(55).")
        print(f"  Pair (35,55) is a T_44-level forced-same-color pair.")

    if not sat_b:
        print("\n  ! UNEXPECTED: baseline control UNSAT — bug or new fact.")
        verdict = verdict + "_but_baseline_UNSAT"
    if not sat_c:
        print("\n  ! UNEXPECTED: negative control (color35=color55=0) UNSAT — "
              "contradicts run1 finding.")
        verdict = verdict + "_but_negctl_UNSAT"

    print(f"\n  total_elapsed_s: {elapsed:.2f}")

    if args.out:
        receipt = {
            "meta": {
                "method": "strict SAT test of forced-pair via Minisat22 "
                          "CDCL solver (pysat)",
                "N": N, "k": k,
                "target_root": TARGET,
                "pair": list(PAIR),
                "wake": _wake_iso(),
                "tool": "test_forced_pair_35_55_sat.py",
                "tool_version": "23-07-2026 wake 02:00 (v2 pysat)",
                "predecessor_tool_v1_result": (
                    "TIMEOUT@300s home-grown DPLL 41M decisions"),
                "chains": len(all_roots),
                "other_chains": len(other_roots),
                "triples_total": len(triples),
                "triples_T_target": len(T_target),
                "triples_T_44": len(T_other),
                "cnf": {"n_vars": n_vars, "n_clauses": n_clauses},
                "pre_registration": {
                    "H_forced": 0.55,
                    "H_partial": 0.30,
                    "H_correlation": 0.15,
                },
            },
            "result": {
                "verdict": verdict,
                "runs": {
                    "A_forced_different": {
                        "constraint": "color(35)=0 AND color(55)!=0",
                        "sat": bool(sat_a),
                        "time_s": round(t_a, 4),
                        "witness_pair": (
                            [witness_a[FIXED_ROOT], witness_a[FORBID_ROOT]]
                            if witness_a else None),
                    },
                    "B_baseline_control": {
                        "constraint": "color(35)=0",
                        "sat": bool(sat_b),
                        "time_s": round(t_b, 4),
                    },
                    "C_negative_control": {
                        "constraint": "color(35)=0 AND color(55)=0",
                        "sat": bool(sat_c),
                        "time_s": round(t_c, 4),
                    },
                },
                "total_elapsed_s": round(elapsed, 3),
                "witness_A_full": witness_a,
            },
        }
        _write_receipt(args.out, receipt)


if __name__ == "__main__":
    _cli()
