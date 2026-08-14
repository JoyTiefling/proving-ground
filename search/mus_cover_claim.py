"""
MUS-EXTRACTION for the *cover claim* itself (N=90, k=5, T_44).

Context (wake 04:00 02-08-2026, solo):
  28-07 sqeezed the universal-cover argument from 10 forced-same pairs
  down to 2: for c in {3,4} — the only colours where cover is needed at
  all — {(11,17),(35,55)} suffices (receipt sha16=62bda6b81b534a22).
  The reduced form of the N=90 UNSAT argument is now:
      c in {0,1,2} : analytic direct-forcing lemma (26-07)
      c in {3,4}   : universal cover on TWO pairs
  The named next step in STATE.md was: run the MUS probe on the 2-pair
  cover — a cheap measurement of "does a short analytic argument exist"
  BEFORE spending wakes hunting for one.

What is measured here (NOT the same object as mus_forced_pair.py):
  mus_forced_pair.py minimised the premises of "f(a) = f(b) is forced".
  This script minimises the premises of the COVER claim itself:

      T_44  AND  NOT mono_c(11,17)  AND  NOT mono_c(35,55)      is UNSAT

  i.e. no valid T_44 colouring keeps colour c off both pairs. Same
  mechanism as the earlier probes (deletion-MUS over triple-groups of
  T_44), different claim.

WHICH ARM (corrected mid-wake, 02-08 — the first run measured the wrong
  query and the sanity gate caught it):
  The 2-pair cover was measured under arm "T_44 + anchor + rigid" at
  c in {3,4}. Under T_44 ALONE the colours are symmetric and the
  irreducible cover is 5 pairs, not 2 — so a 2-pair claim on T_44 alone
  is SAT by construction, not a defect. That first run is kept as a
  positive control of this encoding: it reproduced the 28-07 control
  arm (receipt sha16=a77f82518da029ee, S3 SAT at c=0 without rigid).
  Default here is therefore --rigid (anchor + rigid hard) and c=3.
  Anchor/rigid provenance: sat_verify_partition_run1.json
  sha16=3669e88c7ec427c6 (26 rigid roots, 24-07).

PRE-REGISTRATION (written BEFORE running, razor #2866):
  H_small   (<=15 triples)   0.05
  H_medium  (16-60)          0.15
  H_large   (>60)            0.80

  This is NOT the "I bet on locality where structure is global"
  systematic being transferred by NAME (that mistake was made on
  28-07 and corrected: the systematic was measured on MUS-over-triples
  and misapplied to a kernel-over-cover-pairs). Here the mechanism is
  the same one it was measured on — MUS over triples — and there is an
  independent structural reason:

    MECHANISM CLAIM (M1, checked separately below): any colouring that
    never uses colour c AT ALL trivially keeps c off both pairs. So the
    cover claim ENTAILS "colour c cannot be dispensed with" as a
    sub-fact — i.e. the instance is not (k-1)-colourable. That is a
    global Schur-type certificate (WS(4)=66 < 90), which alone cannot
    be small. Hence the core should be at least as large as the
    forced-pair cores (599 and 699 of 1331).

  Secondary, falsifiable: mus_size > 699 (prior 0.50).
  M1 is a real gate, not decoration: if dropping colour c comes back
  SAT, the structural reason above is WRONG and I must say so in the
  log regardless of what the core size turns out to be.

SANITY GATES (abort if any fails — a core from a broken encoding is
worse than no core):
  S1  T_44 alone                        -> expect SAT
  S2  T_44 + one pair excluded (each)   -> expect SAT   [this is what
      "the 2-pair cover is irreducible" MEANS; if it comes back UNSAT,
      either cover_minimal_pairs is wrong or this encoding diverges
      from it — either way, stop.]
  S3  T_44 + both pairs excluded        -> expect UNSAT (the claim)

Receipt: persist-by-default via receipts.py (a3a5c1c).
"""
import sys
import os
import json
import time
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from explore_pigeonhole_45 import (
    odd_root, chains_up_to_N, forbidden_triples, split_triples_by_root,
)

from pysat.solvers import Minisat22

import receipts

TARGET = 45
DEFAULT_PAIRS = "11,17;35,55"

# Anchor + rigid claims — sat_verify_partition_run1.json sha16=3669e88c7ec427c6
# (copied verbatim from cover_minimal_pairs.py; same provenance line)
ANCHOR = {1: 0, 3: 1, 7: 2}
RIGID_A = [13, 23, 43]                                     # colour 0
RIGID_B = [5, 31]                                          # colour 1
RIGID_T = [9, 11, 15, 17, 19, 21, 25, 27, 29, 35, 41,      # colour in {2,3,4}
           49, 51, 53, 55, 59, 65, 75, 77, 85]
RIGID_X = [79]                                             # colour != 1


def anchor_clauses(var):
    """WLOG symmetry-breaking labels. FREE — not a derived fact, so these
    stay hard in every arm that keeps them (colours are interchangeable
    until three of them are named)."""
    return [[var[(r, c)]] for r, c in ANCHOR.items()]


def rigid_units(var):
    """The 26 rigid facts as (label, unit-clause) pairs.

    These are NOT free: they were themselves established by SAT under
    T_44 + anchor (sat_verify_partition, 24-07). Every MUS measured with
    them HARD is therefore conditional — it prices the cover claim at a
    premise front that already contains paid-for work. See --rigid-mode."""
    out = []
    for r in RIGID_A:
        out.append((f"rigid_A:{r}=0", [var[(r, 0)]]))
    for r in RIGID_B:
        out.append((f"rigid_B:{r}=1", [var[(r, 1)]]))
    for r in RIGID_T:
        out.append((f"rigid_T:{r}!=0", [-var[(r, 0)]]))
        out.append((f"rigid_T:{r}!=1", [-var[(r, 1)]]))
    for r in RIGID_X:
        out.append((f"rigid_X:{r}!=1", [-var[(r, 1)]]))
    return out


def rigid_clauses(var):
    """Anchor + rigid facts as hard unit clauses (legacy shape, kept so the
    default arm encodes byte-for-byte the same instance as on 02-08)."""
    return anchor_clauses(var) + [cl for _, cl in rigid_units(var)]


def witnesses_for_triple(tri, N):
    """Integer witnesses x + y = z whose odd-root multiset equals tri."""
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
    """Hard exactly-one clauses + per-triple soft groups with selectors."""
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

    groups = {}
    soft = []
    for tri in sorted(T_other):
        if not set(tri).issubset(set(other_roots)):
            continue
        n += 1
        sel = n
        groups[sel] = tri
        for c in range(k):
            soft.append([-sel] + [-var[(r, c)] for r in sorted(set(tri))])

    return var, hard, soft, groups, n


def block_pair(var, pair, c):
    """Clause forbidding both members of `pair` from taking colour c."""
    a, b = pair
    if a == b:
        return [-var[(a, c)]]
    return [-var[(a, c)], -var[(b, c)]]


def solve(hard, soft, extra, assumptions):
    with Minisat22(bootstrap_with=hard + soft + list(extra)) as s:
        sat = s.solve(assumptions=assumptions)
        core = None if sat else (s.get_core() or [])
        return sat, core


def colour_dispensable(hard, soft, sels, var, other_roots, c):
    """M1 (mechanism check): can colour c be dropped from the instance
    ENTIRELY? Any such colouring keeps c off both pairs for free, so the
    cover claim entails this being impossible. If this comes back SAT the
    structural reason in the docstring is wrong — say so, don't bury it."""
    extra = [[-var[(r, c)]] for r in other_roots]
    sat, _ = solve(hard, soft, extra, sels)
    return bool(sat)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--N", type=int, default=90)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--target", type=int, default=TARGET)
    ap.add_argument("--pairs", type=str, default=DEFAULT_PAIRS,
                    help="semicolon-separated cover pairs, e.g. '11,17;35,55'")
    ap.add_argument("--colour", type=int, default=3,
                    help="colour to keep off the pairs; the 2-pair cover was "
                         "measured for c in {3,4} under anchor+rigid")
    ap.add_argument("--no-rigid", action="store_true",
                    help="control arm: T_44 alone, no anchor/rigid facts")
    ap.add_argument("--rigid-mode", choices=["hard", "off", "soft"],
                    default="hard",
                    help="hard (default, 02-08 arm: rigid unminimisable) | "
                         "off (anchor kept, rigid REMOVED — unconditional "
                         "price of the cover claim) | soft (rigid facts "
                         "become minimisable premises alongside triples, so "
                         "the core reports how many of them it actually "
                         "needs). Ignored when --no-rigid.")
    ap.add_argument("--order",
                    choices=["core", "sorted", "reverse", "rigid-first"],
                    default="core",
                    help="deletion order — an MUS is irreducible, not "
                         "minimum, so it is order-dependent; run two hands "
                         "before believing a size")
    ap.add_argument("--out", type=str, default="")
    ap.add_argument("--no-out", action="store_true")
    args = ap.parse_args()

    pairs = [tuple(int(x) for x in p.split(",")) for p in args.pairs.split(";")]
    N, k, c = args.N, args.k, args.colour

    tag = "-".join(f"{a}_{b}" for a, b in pairs)
    if args.no_rigid:
        arm = "T44_only"
    else:
        arm = {"hard": "T44_rigid_anchor",
               "off": "T44_anchor_norigid",
               "soft": "T44_rigid_soft"}[args.rigid_mode]
    if args.order != "core":
        arm = f"{arm}_{args.order}"
    out_path = receipts.resolve_out(args, __file__, arm=arm,
                                    pairs=tag, N=N, k=k, t=args.target, c=c)
    receipts.probe_writable(out_path)

    t0 = time.time()

    chain_by_root = chains_up_to_N(N)
    all_roots = sorted(chain_by_root)
    triples = forbidden_triples(N)
    T_target, T_other = split_triples_by_root(triples, args.target)
    other_roots = [r for r in all_roots if r != args.target]

    print(f"N={N} k={k} target={args.target} colour={c} arm={arm}")
    print(f"  cover pairs: {pairs}")
    print(f"  roots={len(all_roots)}  T_target={len(T_target)}  "
          f"T_other={len(T_other)}")

    var, hard, soft, groups, nvars = build(other_roots, T_other, k)
    kind = {s: "triple" for s in groups}
    rigid_label = {}

    if args.no_rigid:
        pass
    elif args.rigid_mode == "hard":
        rc = rigid_clauses(var)
        hard = hard + rc
        print(f"  + anchor/rigid hard clauses: {len(rc)}")
    elif args.rigid_mode == "off":
        ac = anchor_clauses(var)
        hard = hard + ac
        print(f"  + anchor hard clauses: {len(ac)}  (rigid REMOVED — "
              f"unconditional front)")
    elif args.rigid_mode == "soft":
        ac = anchor_clauses(var)
        hard = hard + ac
        ru = rigid_units(var)
        for label, cl in ru:
            nvars += 1
            sel = nvars
            groups[sel] = tuple(cl)
            kind[sel] = "rigid"
            rigid_label[sel] = label
            soft.append([-sel] + cl)
        print(f"  + anchor hard clauses: {len(ac)}  + rigid as SOFT groups: "
              f"{len(ru)}  (minimisable alongside triples)")

    sels = sorted(groups)
    print(f"  vars={nvars} hard={len(hard)} soft={len(soft)} groups={len(sels)}"
          f"  (triples={sum(1 for s in sels if kind[s] == 'triple')}, "
          f"rigid={sum(1 for s in sels if kind[s] == 'rigid')})"
          f"  deletion order={args.order}")

    blocks = [block_pair(var, p, c) for p in pairs]

    # --- M1: mechanism check (does the claim entail non-4-colourability?)
    m1_sat = colour_dispensable(hard, soft, sels, var, other_roots, c)
    print(f"\n  M1  colour {c} dropped entirely : "
          f"{'SAT' if m1_sat else 'UNSAT'}  (expect UNSAT; SAT => the "
          f"structural reason in the docstring is wrong)")

    # --- sanity gates
    s1_sat, _ = solve(hard, soft, [], sels)
    print(f"  S1  T_44 alone         : {'SAT' if s1_sat else 'UNSAT'} (expect SAT)")

    s2 = {}
    for i, p in enumerate(pairs):
        sat, _ = solve(hard, soft, [blocks[i]], sels)
        s2[f"{p[0]},{p[1]}"] = bool(sat)
        print(f"  S2  only pair {str(p):>10} : {'SAT' if sat else 'UNSAT'} "
              f"(expect SAT — irreducibility of the 2-pair cover)")

    s3_sat, core0 = solve(hard, soft, blocks, sels)
    print(f"  S3  all pairs blocked  : {'SAT' if s3_sat else 'UNSAT'} "
          f"(expect UNSAT — the claim)")

    if s3_sat:
        print("  !! claim is SAT — the 2-pair cover does NOT hold here. Abort.")
        receipts.write_receipt(out_path, {
            "script": "mus_cover_claim.py", "wake": receipts.wake_iso(),
            "aborted": "claim_SAT", "N": N, "k": k, "colour": c, "arm": arm,
            "pairs": [list(p) for p in pairs],
            "sanity": {"S1_baseline_SAT": bool(s1_sat), "S2_single_pair_SAT": s2,
                       "S3_claim_SAT": True},
            "M1_colour_dispensable_SAT": m1_sat,
        })
        return
    if not s1_sat or not all(s2.values()):
        print("  !! sanity failed — encoding diverges. Core not trustworthy.")
        receipts.write_receipt(out_path, {
            "script": "mus_cover_claim.py", "wake": receipts.wake_iso(),
            "aborted": "sanity_failed", "N": N, "k": k, "colour": c, "arm": arm,
            "pairs": [list(p) for p in pairs],
            "sanity": {"S1_baseline_SAT": bool(s1_sat), "S2_single_pair_SAT": s2,
                       "S3_claim_SAT": False},
            "M1_colour_dispensable_SAT": m1_sat,
        })
        return

    core_sels = [s for s in core0 if s in groups]
    print(f"\n  solver core (over-approx): {len(core_sels)} of {len(sels)}")

    # An MUS is IRREDUCIBLE, not minimum — the subset you land on depends on
    # the order you try deletions in. "core" is the legacy order (whatever
    # order the solver handed the core back in) and reproduces the published
    # 02-08 numbers; the others are second hands on the same instance.
    if args.order == "reverse":
        del_order = sorted(core_sels, reverse=True)
    elif args.order == "rigid-first":
        del_order = ([s for s in core_sels if kind[s] == "rigid"]
                     + [s for s in core_sels if kind[s] != "rigid"])
    elif args.order == "sorted":
        del_order = sorted(core_sels)
    else:
        del_order = list(core_sels)

    cand = list(core_sels)
    removed = 0
    t_del = time.time()
    for s in del_order:
        trial = [x for x in cand if x != s]
        sat, _ = solve(hard, soft, blocks, trial)
        if not sat:
            cand = trial
            removed += 1
    mus = sorted(cand)
    print(f"  MUS after deletion: {len(mus)} triples (dropped {removed}, "
          f"{time.time() - t_del:.1f}s)")

    sat_mus, _ = solve(hard, soft, blocks, mus)
    each_drop_sat = True
    for s in mus:
        sat, _ = solve(hard, soft, blocks, [x for x in mus if x != s])
        if not sat:
            each_drop_sat = False
            break
    print(f"  verify: MUS UNSAT = {not sat_mus}; every 1-drop SAT = {each_drop_sat}")

    mus_triples = [s for s in mus if kind[s] == "triple"]
    mus_rigid = [s for s in mus if kind[s] == "rigid"]
    roots_in_mus = sorted({r for s in mus_triples for r in set(groups[s])})
    print(f"  roots touched (by triples): {len(roots_in_mus)} of "
          f"{len(other_roots)}")
    if args.rigid_mode == "soft" and not args.no_rigid:
        print(f"  MUS composition: {len(mus_triples)} triples + "
              f"{len(mus_rigid)} rigid facts of {len(rigid_label)} offered")
        for s in mus_rigid:
            print(f"      kept: {rigid_label[s]}")

    core_detail = []
    for s in mus_triples:
        tri = groups[s]
        w = witnesses_for_triple(tri, N)
        core_detail.append({"triple": list(tri),
                            "distinct_roots": sorted(set(tri)),
                            "n_witnesses": len(w),
                            "witness": w[0] if w else None})

    elapsed = time.time() - t0
    print(f"\n  elapsed {elapsed:.2f}s")

    verdict = ("H_small" if len(mus) <= 15
               else "H_medium" if len(mus) <= 60 else "H_large")
    print(f"  pre-registered verdict: {verdict} (mus_size={len(mus)})")
    print(f"  secondary (mus_size > 699): "
          f"{'SUPPORTED' if len(mus) > 699 else 'REFUTED'}")

    receipts.write_receipt(out_path, {
        "script": "mus_cover_claim.py",
        "wake": receipts.wake_iso(),
        "claim": "T_44 AND no pair takes colour c  is UNSAT "
                 "(universal cover on the reduced pair set)",
        "N": N, "k": k, "target_root": args.target, "colour": c, "arm": arm,
        "pairs": [list(p) for p in pairs],
        "prereg": {"H_small<=15": 0.05, "H_medium_16_60": 0.15,
                   "H_large>60": 0.80,
                   "secondary_mus_gt_699": 0.50},
        "counts": {"roots": len(all_roots), "T_target": len(T_target),
                   "T_other": len(T_other), "groups": len(sels)},
        "M1_colour_dispensable_SAT": m1_sat,
        "sanity": {"S1_baseline_SAT": bool(s1_sat),
                   "S2_single_pair_SAT": s2,
                   "S3_claim_SAT": bool(s3_sat)},
        "rigid_mode": "absent" if args.no_rigid else args.rigid_mode,
        "deletion_order": args.order,
        "solver_core_size": len(core_sels),
        "mus_size": len(mus),
        "mus_size_triples": len(mus_triples),
        "mus_size_rigid": len(mus_rigid),
        "rigid_offered": len(rigid_label),
        "rigid_kept": [rigid_label[s] for s in mus_rigid],
        "mus_verified_unsat": bool(not sat_mus),
        "mus_verified_minimal": bool(each_drop_sat),
        "verdict": verdict,
        "secondary_mus_gt_699": bool(len(mus) > 699),
        "roots_in_mus": roots_in_mus,
        "core_triples": core_detail,
        "elapsed_s": round(elapsed, 3),
    })


if __name__ == "__main__":
    main()
