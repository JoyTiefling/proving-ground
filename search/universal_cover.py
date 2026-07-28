"""
Follow-up to forced_same_color_coverage (wake 04:00 23-07):

The right test for the structural argument N=90 UNSAT is UNIVERSAL cover,
not existential. Question:

  Does there exist a valid T_44 coloring where NO forced-same partner-pair
  of chain 45 takes color c, for some color c in [0..k-1]?

If YES (SAT): that color is a "gap" — assigning color(45)=c avoids all
  forced-same mono-triples with 45. Then to complete N=90 UNSAT, we need
  more machinery (free / forced_different pairs, T_45 itself).

If NO (UNSAT) for every color c: then for EVERY valid T_44 coloring, and
  for EVERY color c, at least one forced-same pair (a, b) takes color c.
  Then color(45)=c always creates mono-triple (a, b, 45). ⇒ N=90 UNSAT
  proved via T_44 forcing + universal-cover argument.

Method:
  For each color c in 0..k-1:
    - Bootstrap CNF for T_44 (usual 44 non-target roots, k colors).
    - For each forced-same pair (a, b), add clause:
        NOT (color(a)=c AND color(b)=c)  →  [-x[a,c], -x[b,c]]
      (recall forced_same means color(a) always equals color(b) here,
       but the clause is written for general (a,b))
    - Solve. SAT means "c is escapable".

Pre-registration (before running):
  H_universal (0.60): all 5 colors UNSAT ⇒ N=90 UNSAT proved structurally.
  H_one_gap (0.25): exactly one color escapable ⇒ argument fixable with
    one additional forced-same pair or T_45-level fact.
  H_multi_gap (0.15): 2+ colors escapable ⇒ forced-same alone insufficient;
    forced_different / free machinery needed.
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
from cycle_forced_pairs import build_cnf, _wake_iso

from pysat.solvers import Minisat22


TARGET = 45

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


def test_color_gap(clauses, var, forced_same_pairs, c):
    """Is there a T_44 coloring where no forced-same pair takes color c?"""
    with Minisat22(bootstrap_with=clauses) as solver:
        for a, b in forced_same_pairs:
            if a == b:
                # intra-chain: forbid color(a)=c
                solver.add_clause([-var[(a, c)]])
            else:
                # forbid color(a)=c AND color(b)=c both
                solver.add_clause([-var[(a, c)], -var[(b, c)]])
        t0 = time.time()
        sat = solver.solve()
        t = time.time() - t0
    return {"sat": bool(sat), "time_s": round(t, 4)}


def _cli():
    ap = argparse.ArgumentParser(
        description="Universal cover test for forced-same pairs of chain 45.")
    ap.add_argument("--N", type=int, default=90)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    N, k = args.N, args.k
    t_start = time.time()

    print(f"UNIVERSAL COVER: N={N} k={k} target={TARGET}")
    print(f"  forced_same pairs: {len(FORCED_SAME)} : {FORCED_SAME}")

    chain_by_root = chains_up_to_N(N)
    all_roots = sorted(chain_by_root.keys())
    other_roots = [r for r in all_roots if r != TARGET]
    triples = forbidden_triples(N)
    T_target, T_other = split_triples_by_root(triples, TARGET)

    clauses, var = build_cnf(other_roots, T_other, k)
    n_vars = max(var.values())
    n_clauses = len(clauses)
    print(f"  CNF (T_44 only): vars={n_vars} clauses={n_clauses}")

    print(f"\n=== TEST COLOR GAP FOR EACH COLOR ===")
    per_color = {}
    escapable = []
    for c in range(k):
        r = test_color_gap(clauses, var, FORCED_SAME, c)
        per_color[c] = r
        marker = "ESCAPABLE" if r["sat"] else "covered  "
        print(f"  color {c}: {marker}  ({'SAT' if r['sat'] else 'UNSAT'} "
              f"{r['time_s']:.3f}s)")
        if r["sat"]:
            escapable.append(c)

    print(f"\n=== VERDICT ===")
    if not escapable:
        hypothesis = "H_universal"
        print(f"  H_universal SUPPORTED: all {k} colors covered universally.")
        print(f"  For every valid T_44 coloring, for every color c, at least")
        print(f"  one forced-same partner-pair takes color c. Therefore:")
        print(f"    - color(45)=c collides with that pair's triple in T_45")
        print(f"    - N=90 is UNSAT structurally, via T_44 + forced-same +")
        print(f"      universal cover argument.")
    elif len(escapable) == 1:
        hypothesis = "H_one_gap"
        print(f"  H_one_gap SUPPORTED: color {escapable[0]} is escapable.")
        print(f"  T_44 has a coloring where no forced-same pair takes")
        print(f"  color {escapable[0]}. Assigning color(45)={escapable[0]} in")
        print(f"  that coloring avoids forced-same mono-triples. Need extra")
        print(f"  argument (free/forced_different pair or T_45 direct) to close.")
    else:
        hypothesis = "H_multi_gap"
        print(f"  H_multi_gap SUPPORTED: {len(escapable)} colors escapable: "
              f"{escapable}.")
        print(f"  Forced-same pairs alone don't cover — richer machinery needed.")

    elapsed = time.time() - t_start
    print(f"\n  total_elapsed_s: {elapsed:.2f}")

    if args.out:
        receipt = {
            "meta": {
                "method": "universal-cover test: for each color c, is there a "
                          "T_44 coloring where no forced-same pair takes c?",
                "N": N, "k": k,
                "target_root": TARGET,
                "n_forced_same_pairs": len(FORCED_SAME),
                "forced_same_pairs": [list(p) for p in FORCED_SAME],
                "wake": _wake_iso(),
                "tool": "universal_cover.py",
                "tool_version": "23-07-2026 wake 04:00 (level 3)",
                "predecessor": "forced_same_color_coverage.py wake 04:00 "
                               "(existential coverage was 5/5 but that was "
                               "existential, not universal — this fixes it)",
                "cnf_T_44": {"n_vars": n_vars, "n_clauses": n_clauses},
                "pre_registration": {
                    "H_universal": 0.60,
                    "H_one_gap": 0.25,
                    "H_multi_gap": 0.15,
                },
            },
            "result": {
                "per_color": {str(c): per_color[c] for c in range(k)},
                "escapable_colors": escapable,
                "n_escapable": len(escapable),
                "hypothesis_supported": hypothesis,
                "total_elapsed_s": round(elapsed, 3),
            },
        }
        _write_receipt(args.out, receipt)


if __name__ == "__main__":
    _cli()
