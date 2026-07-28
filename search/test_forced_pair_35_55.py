"""
STRICT TEST: is pair (35, 55) forced to same color under T_44 in N=90, k=5?

Context (wake 00:00 23-07-2026, receipt out/pigeonhole_45_run1.json):
  - explore_pigeonhole_45 on 20 diverse T_44 colorings found: distinct
    tight-catching partner-pairs of target=45 == 1, namely (35, 55).
    In 20/20 colorings, color(35)==color(55). Live hypothesis: pair (35,55)
    is FORCED to same color by T_44 alone (weaker than full T at N=90).

Pre-registered hypotheses (state.md wake 00:00 23-07):
  H_forced        (0.55): UNSAT — pair is forced same-color under T_44.
  H_partial       (0.30): SAT — witness exists (pair not forced on T_44),
                          the 20/20 alignment is only forced by T_45 too.
  H_correlation   (0.15): SAT with rare witnesses — heavily correlated
                          (>90% same in random colorings) but not forced.

Method:
  DPLL exhaustive SAT-search over 44 chain roots [1..44 all odd] under T_44.
  Two extra constraints beyond T_44:
    (1) color(35) := 0                (WLOG by color permutation).
    (2) color(55) != 0                (opposite of the hypothesis).
  If DPLL exhausts with no solution -> UNSAT -> H_forced proven.
  If DPLL finds any witness         -> SAT   -> H_partial or H_correlation.

Symmetry break: only color(35):=0. NO "second-root <= 1" break — we want a
witness, not a canonical enumeration; duplicates are fine.

Time-cap: 300s hardware wall. Above that: inconclusive.

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


TARGET = 45
PAIR = (35, 55)
FIXED_ROOT = 35
FIXED_COLOR = 0
FORBID_ROOT = 55
FORBID_COLOR = 0  # color(55) must NOT be FORBID_COLOR (i.e. NOT 0)


def _wake_iso():
    return (datetime.datetime.now(datetime.timezone.utc)
            .isoformat(timespec="seconds").replace("+00:00", "Z"))


def _write_receipt(out_path, receipt):
    """Same pattern as construct_maxD_partial_split._write_receipt:
    sort_keys hash, embed sha16 after (self-hash chicken-and-egg avoided).
    """
    if not out_path:
        sys.stderr.write(
            "  [warn] --out not given; result NOT persisted.\n")
        return
    payload = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True)
    sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    receipt["sha16"] = sha
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"  receipt -> {out_path}  sha16={sha}")


def _dpll_witness(chain_roots, triples, k, fixed, time_budget_s):
    """DPLL exhaustive search for ANY coloring of chain_roots avoiding
    monochromatic triples, satisfying color[r]==v for (r,v) in fixed_eq,
    and color[r]!=v for (r,v) in fixed_neq.

    fixed = {"eq": {root: color, ...}, "neq": {root: set(forbidden_colors)}}

    Root order: degree-desc in the hypergraph induced by `triples`.

    Returns (result, coloring_or_None, stats):
      result: "SAT" | "UNSAT" | "TIMEOUT"
    """
    inc = {r: [] for r in chain_roots}
    for tri in triples:
        for r in set(tri):
            if r in inc:
                inc[r].append(tri)

    ordered = sorted(chain_roots, key=lambda r: (-len(inc[r]), r))

    color = {}
    stats = {"decisions": 0, "conflicts": 0, "backtracks": 0}
    t0 = time.time()
    timed_out = [False]

    eq_map = dict(fixed.get("eq", {}))
    neq_map = {r: set(cs) for r, cs in fixed.get("neq", {}).items()}

    def is_bad_partial(new_root, new_color):
        """Bad if there exists a triple incident to new_root such that ALL
        its roots have color assigned (including this one) equal to new_color.
        Partial triples (some root unassigned other than new_root) do not
        commit to badness yet."""
        for tri in inc[new_root]:
            all_match = True
            for r in tri:
                if r == new_root:
                    cv = new_color
                else:
                    cv = color.get(r)
                if cv is None:
                    all_match = False
                    break
                if cv != new_color:
                    all_match = False
                    break
            if all_match:
                return True
        return False

    def try_assign(i):
        if timed_out[0]:
            return None
        if (time.time() - t0) > time_budget_s:
            timed_out[0] = True
            return None
        if i == len(ordered):
            return dict(color)
        r = ordered[i]

        if r in eq_map:
            candidates = [eq_map[r]]
        else:
            candidates = list(range(k))
            if r in neq_map:
                candidates = [c for c in candidates if c not in neq_map[r]]

        for c in candidates:
            stats["decisions"] += 1
            if is_bad_partial(r, c):
                stats["conflicts"] += 1
                continue
            color[r] = c
            res = try_assign(i + 1)
            if res is not None:
                return res
            del color[r]
            stats["backtracks"] += 1
            if timed_out[0]:
                return None
        return None

    witness = try_assign(0)
    elapsed = time.time() - t0
    stats["elapsed_s"] = round(elapsed, 3)

    if timed_out[0]:
        return "TIMEOUT", witness, stats
    if witness is not None:
        return "SAT", witness, stats
    return "UNSAT", None, stats


def _cli():
    ap = argparse.ArgumentParser(
        description="Strict test: is pair (35,55) forced same-color under "
                    "T_44 at N=90 k=5?")
    ap.add_argument("--N", type=int, default=90)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--time-cap", type=float, default=300.0,
                    help="Hardware wall (seconds). Above -> inconclusive.")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    N, k = args.N, args.k
    t_start = time.time()

    print(f"STRICT TEST forced-pair (35,55): N={N} k={k}")
    print(f"  fix color(35)=0, forbid color(55)=0, exhaustive over T_44.")
    print(f"  time-cap = {args.time_cap:.0f}s")

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

    fixed = {
        "eq": {FIXED_ROOT: FIXED_COLOR},
        "neq": {FORBID_ROOT: {FORBID_COLOR}},
    }
    print(f"  constraints: color[{FIXED_ROOT}]={FIXED_COLOR}, "
          f"color[{FORBID_ROOT}] != {FORBID_COLOR}")

    result, witness, stats = _dpll_witness(
        other_roots, T_other, k, fixed, args.time_cap)

    elapsed = time.time() - t_start
    print(f"\n=== RESULT: {result} ===")
    print(f"  decisions: {stats['decisions']}")
    print(f"  conflicts: {stats['conflicts']}")
    print(f"  backtracks: {stats['backtracks']}")
    print(f"  dpll_elapsed_s: {stats['elapsed_s']}")
    print(f"  total_elapsed_s: {elapsed:.2f}")

    verdict = None
    if result == "UNSAT":
        verdict = "H_forced_PROVEN"
        print("\n  → H_forced PROVEN (pre-reg prior 0.55).")
        print("    Pair (35,55) is forced same-color under T_44 alone.")
    elif result == "SAT":
        # verify witness respects constraints and T_44
        c35 = witness[FIXED_ROOT]
        c55 = witness[FORBID_ROOT]
        ok = True
        for tri in T_other:
            colors = [witness.get(r) for r in tri]
            if all(c == colors[0] and c is not None for c in colors):
                ok = False
                print(f"    ! witness mono in {tri}!")
                break
        if c35 != FIXED_COLOR:
            ok = False
        if c55 == FORBID_COLOR:
            ok = False
        if ok:
            verdict = "H_forced_REFUTED"
            print(f"\n  → H_forced REFUTED (pre-reg prior 0.55).")
            print(f"    WITNESS: color(35)={c35}, color(55)={c55}.")
            print(f"    Distribution among priors: H_partial (0.30) or "
                  f"H_correlation (0.15) alive.")
        else:
            verdict = "BUG_WITNESS_INVALID"
            print("\n  ! BUG: DPLL returned invalid witness.")
    else:
        verdict = "INCONCLUSIVE_TIMEOUT"
        print(f"\n  ! TIMEOUT after {args.time_cap}s — inconclusive.")

    if args.out:
        receipt = {
            "meta": {
                "method": "strict SAT test of forced-pair via DPLL exhaustive",
                "N": N, "k": k,
                "target_root": TARGET,
                "pair": list(PAIR),
                "constraints": {
                    "eq": {str(FIXED_ROOT): FIXED_COLOR},
                    "neq_forbidden": {str(FORBID_ROOT): [FORBID_COLOR]},
                },
                "time_cap_s": args.time_cap,
                "wake": _wake_iso(),
                "tool": "test_forced_pair_35_55.py",
                "tool_version": "23-07-2026 wake 02:00",
                "chains": len(all_roots),
                "other_chains": len(other_roots),
                "triples_total": len(triples),
                "triples_T_target": len(T_target),
                "triples_T_44": len(T_other),
                "pre_registration": {
                    "H_forced": 0.55,
                    "H_partial": 0.30,
                    "H_correlation": 0.15,
                },
            },
            "result": {
                "verdict": verdict,
                "dpll_result": result,
                "witness": witness,
                "stats": stats,
                "total_elapsed_s": round(elapsed, 3),
            },
        }
        _write_receipt(args.out, receipt)


if __name__ == "__main__":
    _cli()
