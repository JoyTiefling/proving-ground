"""
MUS-EXTRACTION for forced-same pairs under T_44 (N=90, k=5).

Context (wake 20:00 26-07-2026, solo):
  Wake 18:00 today closed the analytic direct-forcing lemma for
  color(45) in {0,1,2} — EXCEPT one step. The c=2 branch leans on
  forced-same(7,19) under T_44, which so far is only "SAT said UNSAT".
  That is the single computer-assisted debt inside an otherwise
  paper-checkable lemma.

Idea (angle, not force):
  Do not ask SAT for a *verdict*. Ask it for the *reason*.
  Extract a Minimal Unsatisfiable Subset over the triple-constraints:
  which forbidden root-triples are actually needed to derive
  f(7) = f(19)? If the core is small (say < 20 triples), the forcing
  can be written out by hand as a case-split and the debt closes.

Pre-registration (written BEFORE running, razor #2866):
  H_small     (0.30): core <= 15 triples — hand-writable derivation, debt
                      closable this wake.
  H_medium    (0.45): core 16-60 triples — structure visible, derivation
                      needs a case-tree; closable over 1-2 wakes.
  H_large     (0.25): core > 60 triples — forcing is genuinely global,
                      no short analytic proof; honest negative, record it
                      and stop claiming "analytic version is near".
  Secondary prediction: core is NOT localized around 7 and 19; it will
  pull in the dense small roots (1,3,5,9,11,...) because the earlier
  degree analysis showed the backbone is the small numbers. (prior 0.7)

Method:
  1. Rebuild T_44 exactly as cycle_forced_pairs.py does (shared imports —
     no re-derivation, no drift).
  2. Hard clauses: exactly-one colour per root.
     Soft (selector-guarded) clauses: one group per forbidden triple,
     5 clauses (one per colour) sharing a single selector s_t.
  3. Assume all selectors + f(a)=0 + f(b)=1. Must be UNSAT.
     (WLOG: the system is fully colour-symmetric, so fixing f(a)=0 and
     then f(b)=1 among the remaining 4 colours loses no generality.)
  4. Take solver.get_core() as a first over-approximation, then
     deletion-based minimization to a true MUS (each removal re-tested).
  5. Report core triples with integer witnesses (x + y = z, x != y,
     x,y,z <= N) so each constraint is human-checkable without the code.

Receipt: JSON with sort_keys + sha16 self-hash (rule 18-07).
"""
import sys
import os
import json
import time
import argparse
import hashlib
import datetime

sys.path.insert(0, os.path.dirname(__file__))
from explore_pigeonhole_45 import (
    odd_root, chains_up_to_N, forbidden_triples, split_triples_by_root,
)

from pysat.solvers import Minisat22


def _wake_iso():
    return (datetime.datetime.now(datetime.timezone.utc)
            .isoformat(timespec="seconds").replace("+00:00", "Z"))


import receipts

_write_receipt = receipts.write_receipt


def witnesses_for_triple(tri, N):
    """All integer witnesses x + y = z (x < y, all <= N) whose odd-root
    multiset equals tri. Lets a reader verify the constraint by hand."""
    out = []
    for x in range(1, N + 1):
        for y in range(x + 1, N + 1):
            z = x + y
            if z > N:
                break
            if tuple(sorted([odd_root(x), odd_root(y), odd_root(z)])) == tri:
                out.append([x, y, z])
    return out


def build(other_roots, T_other, k):
    """Hard clauses (exactly-one) + per-triple soft groups with selectors."""
    var = {}
    n = 0
    for r in other_roots:
        for c in range(k):
            n += 1
            var[(r, c)] = n

    hard = []
    for r in other_roots:
        hard.append([var[(r, c)] for c in range(k)])
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                hard.append([-var[(r, c1)], -var[(r, c2)]])

    groups = {}   # selector var -> triple
    soft = []
    for tri in sorted(T_other):
        roots_in_tri = sorted(set(tri))
        if not set(roots_in_tri).issubset(set(other_roots)):
            continue
        n += 1
        sel = n
        groups[sel] = tri
        for c in range(k):
            soft.append([-sel] + [-var[(r, c)] for r in roots_in_tri])

    return var, hard, soft, groups, n


def solve(hard, soft, assumptions):
    with Minisat22(bootstrap_with=hard + soft) as s:
        sat = s.solve(assumptions=assumptions)
        core = None if sat else (s.get_core() or [])
        return sat, core


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=90)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--target", type=int, default=45,
                    help="root whose triples are excluded (T_44 = rest)")
    ap.add_argument("--pair", type=str, default="7,19")
    ap.add_argument("--out", type=str, default="",
                    help="receipt path; default = auto under search/out/")
    ap.add_argument("--no-out", action="store_true",
                    help="explicitly discard the receipt (default is to keep it)")
    args = ap.parse_args()

    a, b = (int(x) for x in args.pair.split(","))
    N, k = args.N, args.k

    out_path = receipts.resolve_out(args, __file__,
                                    pair=f"{a}-{b}", N=N, k=k, t=args.target)
    receipts.probe_writable(out_path)

    t0 = time.time()

    chain_by_root = chains_up_to_N(N)
    all_roots = sorted(chain_by_root)
    triples = forbidden_triples(N)
    T_target, T_other = split_triples_by_root(triples, args.target)
    other_roots = [r for r in all_roots if r != args.target]

    print(f"N={N} k={k} target={args.target}")
    print(f"  roots: {len(all_roots)} (T_other over {len(other_roots)})")
    print(f"  triples total={len(triples)}  T_target={len(T_target)}  T_other={len(T_other)}")

    var, hard, soft, groups, nvars = build(other_roots, T_other, k)
    sels = sorted(groups)
    print(f"  vars={nvars}  hard={len(hard)}  soft={len(soft)}  groups={len(sels)}")

    fix = [var[(a, 0)], var[(b, 1)]]

    # sanity 1: same colour must be SAT (pair is forced-SAME, not -DIFFERENT)
    sat_same, _ = solve(hard, soft, sels + [var[(a, 0)], var[(b, 0)]])
    # sanity 2: baseline T_44 satisfiable
    sat_base, _ = solve(hard, soft, sels + [var[(a, 0)]])
    # the claim itself
    sat_diff, core0 = solve(hard, soft, sels + fix)

    print(f"  sanity same-colour  f({a})=f({b})=0 : {'SAT' if sat_same else 'UNSAT'} (expect SAT)")
    print(f"  sanity baseline     f({a})=0        : {'SAT' if sat_base else 'UNSAT'} (expect SAT)")
    print(f"  claim   f({a})=0, f({b})=1          : {'SAT' if sat_diff else 'UNSAT'} (expect UNSAT)")

    if sat_diff:
        print("  !! pair is NOT forced-same under these constraints — abort.")
        return
    if not (sat_same and sat_base):
        print("  !! sanity failed — encoding is wrong, do not trust the core.")
        return

    core_sels = [s for s in core0 if s in groups]
    print(f"\n  solver core (over-approx): {len(core_sels)} triples "
          f"(of {len(sels)})")

    # deletion-based minimization to a true MUS over triple-groups
    cand = list(core_sels)
    removed = 0
    for s in list(cand):
        trial = [x for x in cand if x != s]
        sat, _ = solve(hard, soft, trial + fix)
        if not sat:
            cand = trial
            removed += 1
    mus = sorted(cand)
    print(f"  MUS after deletion pass: {len(mus)} triples (dropped {removed})")

    # final verification of minimality claim: MUS unsat, and each 1-drop sat
    sat_mus, _ = solve(hard, soft, mus + fix)
    each_drop_sat = True
    for s in mus:
        sat, _ = solve(hard, soft, [x for x in mus if x != s] + fix)
        if not sat:
            each_drop_sat = False
            break
    print(f"  verify: MUS is UNSAT = {not sat_mus}; every 1-drop SAT = {each_drop_sat}")

    roots_in_mus = sorted({r for s in mus for r in set(groups[s])})
    print(f"  roots touched by MUS: {len(roots_in_mus)} -> {roots_in_mus}")

    print("\n  CORE TRIPLES (root-multiset  ->  one integer witness):")
    core_detail = []
    for s in mus:
        tri = groups[s]
        w = witnesses_for_triple(tri, N)
        core_detail.append({"triple": list(tri),
                            "distinct_roots": sorted(set(tri)),
                            "n_witnesses": len(w),
                            "witness": w[0] if w else None})
        wit = w[0] if w else None
        wstr = f"{wit[0]}+{wit[1]}={wit[2]}" if wit else "??"
        print(f"    {str(list(tri)):>18}  {wstr:>14}   ({len(w)} witnesses)")

    elapsed = time.time() - t0
    print(f"\n  elapsed {elapsed:.2f}s")

    receipt = {
        "script": "mus_forced_pair.py",
        "wake": _wake_iso(),
        "N": N, "k": k, "target_root": args.target,
        "pair": [a, b],
        "prereg": {"H_small<=15": 0.30, "H_medium_16_60": 0.45, "H_large>60": 0.25},
        "counts": {"roots": len(all_roots), "T_target": len(T_target),
                   "T_other": len(T_other), "groups": len(sels)},
        "sanity": {"same_colour_SAT": bool(sat_same),
                   "baseline_SAT": bool(sat_base),
                   "diff_colour_SAT": bool(sat_diff)},
        "solver_core_size": len(core_sels),
        "mus_size": len(mus),
        "mus_verified_unsat": bool(not sat_mus),
        "mus_verified_minimal": bool(each_drop_sat),
        "roots_in_mus": roots_in_mus,
        "core_triples": core_detail,
        "elapsed_s": round(elapsed, 3),
    }
    _write_receipt(out_path, receipt)


if __name__ == "__main__":
    main()
