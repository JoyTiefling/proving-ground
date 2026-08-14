"""
CASE-TREE WIDTH of the 2-pair cover claim (N=90, k=5, c=3), on the MUS-92.

Context (wake 18:00 02-08-2026, solo):
  04:00 today measured the PREMISE SIZE of the cover claim: MUS = 92
  triples of 1331 for c=3 (receipt sha16=3f0c6f407b34e613), against 599
  and 699 for the forced-same branches. I wrote in STATE.md that this is
  "the first time the measurement says a short argument may exist".

  That sentence conflates two different quantities, and #3335 says so:
  the size of the PREMISE SET is not the width of the CASE ANALYSIS.
  92 interlocked triples can still need a 20-deep case split, which no
  one writes by hand; and a 700-triple core could in principle close in
  four cases. What makes an argument hand-writable is a SMALL BACKDOOR:
  a few roots such that, once you split on their colours, every branch
  dies by unit propagation alone.

  So: measure the thing I actually claimed. Different property of the
  same object, measured by a different procedure.

WHAT IS MEASURED
  Instance:  44 non-45 chain roots, exactly-one colour each
             + anchor/rigid units (provenance sha16=3669e88c7ec427c6)
             + the 92 MUS triples as "not all three the same colour"
             + the two cover-blocking clauses
                  NOT(11=3 AND 17=3),  NOT(35=3 AND 55=3)
             This is UNSAT — that IS the cover claim at c=3.

  (1) Greedy case tree: DPLL with unit propagation, branching only on
      roots, counting CONFLICT LEAVES and DEPTH. A tree with L leaves is
      literally a proof by L cases, each closing by propagation. This is
      an UPPER bound (greedy heuristic, not minimum).
  (2) Uniform backdoor: exhaustive search for a set S of roots, |S|<=2,
      such that EVERY colour assignment to S is killed by propagation.
      That is the "flat" version of the same claim.

PRE-REGISTRATION (written BEFORE running — razor #2866).
  Best greedy conflict-leaf count L:
      H_tiny    L <= 10        0.15
      H_small   11 <= L <= 60  0.40   <- mode
      H_medium  61 <= L <= 500 0.30
      H_large   L > 500        0.15

  Mechanism for the mode: 15 of the 92 core triples are BINARY in
  distinct roots (e.g. [1,33], [7,21], [11,55]) and they sit on exactly
  the highest-degree roots (7:25, 11:24, 9:23), while the anchor already
  pins 7=2 and rigid confines 20 roots to {2,3,4}. Binary clauses plus
  units are what propagation eats.

  Named systematic, stated so it can be checked against me: on this
  problem I have now lost four pre-registrations in a row by betting on
  globality/size (27-07 named the locality bias, 28-07 misapplied the
  correction by NAME, 02-08 04:00 overshot the other way by 7.6x). The
  prior above is argued from clause arity, not from "which way did I
  miss last time" — if it is wrong again, the correction is to stop
  predicting magnitudes on this object at all, not to flip the sign.

  Secondary, falsifiable: minimum uniform backdoor |S| <= 2 exists
  (prior 0.25).

GATES (abort and say so; a case tree over a mis-encoded instance is
worse than no case tree — the whole point is that I re-encoded by hand
from a receipt, so my encoding can silently diverge from the measured
one):
  G1  my CNF must be UNSAT                     (else I encoded a
                                                different claim)
  G2  dropping ANY ONE of the 92 triples must make it SAT
      (receipt asserts mus_verified_minimal=True over all 92, so this
      is a full positive control, not a spot check: if some drop stays
      UNSAT, my encoding is STRICTER than the measured one and the
      leaf count below describes an instance nobody measured)
  G3  the branching must be exhaustive: at every node the colours
      branched on must cover the root's whole surviving domain
      (asserted in code, not by eye)
"""
import sys
import os
import json
import time
import itertools
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from explore_pigeonhole_45 import odd_root, chains_up_to_N

import receipts

K = 5
COLOUR = 3
PAIRS = [(11, 17), (35, 55)]
RECEIPT = "search/out/mus_cover_claim_N90_armT44_rigid_anchor_c3_k5_pairs11_17-35_55_t45.json"

ANCHOR = {1: 0, 3: 1, 7: 2}
RIGID_A = [13, 23, 43]
RIGID_B = [5, 31]
RIGID_T = [9, 11, 15, 17, 19, 21, 25, 27, 29, 35, 41,
           49, 51, 53, 55, 59, 65, 75, 77, 85]
RIGID_X = [79]


def roots_of(N=90, target=45):
    return sorted(r for r in chains_up_to_N(N) if r != target)


def initial_domains(roots):
    """Domain = set of colours still allowed. Rigid facts applied here as
    domain restrictions (identical in force to the unit clauses used by
    mus_cover_claim.py)."""
    dom = {r: set(range(K)) for r in roots}
    for r, c in ANCHOR.items():
        dom[r] = {c}
    for r in RIGID_A:
        dom[r] = {0}
    for r in RIGID_B:
        dom[r] = {1}
    for r in RIGID_T:
        dom[r] -= {0, 1}
    for r in RIGID_X:
        dom[r] -= {1}
    return dom


def load_core(path):
    with open(path) as f:
        d = json.load(f)
    core = [tuple(sorted(set(t["distinct_roots"]))) for t in d["core_triples"]]
    return d, core


def propagate(dom, mono_groups, pair_clauses):
    """Unit propagation over:
         - mono clauses: NOT all roots of g share a colour c
         - pair clauses: NOT (a=c AND b=c)   [c = COLOUR]
       Returns False on conflict (some domain empties).
       Rule: if all-but-one root of a group is pinned to c, the last one
       loses c. Empty domain = conflict. Runs to fixpoint."""
    changed = True
    while changed:
        changed = False
        for g in mono_groups:
            for c in range(K):
                pinned = [r for r in g if dom[r] == {c}]
                if len(pinned) == len(g):
                    return False
                if len(pinned) == len(g) - 1:
                    rest = [r for r in g if dom[r] != {c}]
                    r = rest[0]
                    if c in dom[r]:
                        dom[r] = dom[r] - {c}
                        if not dom[r]:
                            return False
                        changed = True
        for (a, b) in pair_clauses:
            if dom[a] == {COLOUR} and dom[b] == {COLOUR}:
                return False
            if dom[a] == {COLOUR} and COLOUR in dom[b]:
                dom[b] = dom[b] - {COLOUR}
                if not dom[b]:
                    return False
                changed = True
            if dom[b] == {COLOUR} and COLOUR in dom[a]:
                dom[a] = dom[a] - {COLOUR}
                if not dom[a]:
                    return False
                changed = True
    return True


def build_index(core, pairs):
    groups = [g for g in core]
    pair_clauses = [(a, b) for (a, b) in pairs]
    return groups, pair_clauses


def branch_roots(core, pairs):
    """Roots worth branching on: those constrained by the core or the
    cover pairs. Ordered by static degree (ties by root id)."""
    deg = {}
    for g in core:
        for r in g:
            deg[r] = deg.get(r, 0) + 1
    for (a, b) in pairs:
        deg[a] = deg.get(a, 0) + 1
        deg[b] = deg.get(b, 0) + 1
    return sorted(deg, key=lambda r: (-deg[r], r)), deg


def dyn_score(dom, r, groups):
    """Dynamic activity: how many core groups touching r are 'hot'
    (at least one root already pinned in them)."""
    s = 0
    for g in groups:
        if r in g and any(len(dom[x]) == 1 for x in g):
            s += 1
    return s


def case_tree(dom, groups, pair_clauses, order, mode, node_cap):
    """Returns (leaves, depth, exhausted_ok, sat_found).
       Every leaf must be a propagation conflict; a SAT leaf means the
       instance is not UNSAT (G1 failure surfaced here too)."""
    stats = {"leaves": 0, "depth": 0, "nodes": 0, "sat": False,
             "exhaustive": True, "branch_roots": {}, "leaves_by_depth": {}}

    def rec(dom, depth):
        stats["nodes"] += 1
        if stats["nodes"] > node_cap or stats["sat"]:
            return
        d2 = {r: set(v) for r, v in dom.items()}
        if not propagate(d2, groups, pair_clauses):
            stats["leaves"] += 1
            stats["depth"] = max(stats["depth"], depth)
            stats["leaves_by_depth"][depth] =                 stats["leaves_by_depth"].get(depth, 0) + 1
            return
        cand = [r for r in order if len(d2[r]) > 1]
        if not cand:
            stats["sat"] = True
            return
        if mode == "static":
            r = cand[0]
        else:
            r = max(cand, key=lambda x: (dyn_score(d2, x, groups),
                                         -len(d2[x]), -x))
        stats["branch_roots"][r] = stats["branch_roots"].get(r, 0) + 1
        colours = sorted(d2[r])
        # G3: branching covers the entire surviving domain of r
        assert set(colours) == d2[r]
        for c in colours:
            d3 = {rr: set(vv) for rr, vv in d2.items()}
            d3[r] = {c}
            rec(d3, depth + 1)

    rec(dom, 0)
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", default=RECEIPT)
    ap.add_argument("--node-cap", type=int, default=400000)
    ap.add_argument("--backdoor-max", type=int, default=2)
    ap.add_argument("--out", type=str, default="")
    ap.add_argument("--no-out", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    src, core = load_core(args.receipt)
    roots = roots_of()
    groups, pair_clauses = build_index(core, PAIRS)
    order, deg = branch_roots(core, PAIRS)

    out_path = args.out or ("search/out/case_tree_cover_N90_c%d_mus%d.json"
                            % (COLOUR, len(core)))
    rec = receipts.Receipt(out_path, enabled=not args.no_out) \
        if hasattr(receipts, "Receipt") else None

    result = {
        "script": "case_tree_cover.py",
        # was hardcoded "2026-08-02T18:00Z" until 14-08: every later rerun
        # stamped itself with the date of the first run. A field that cannot
        # disagree with reality is not a record (#3706).
        "wake": receipts.wake_iso(),
        "source_receipt_sha16": src.get("sha16"),
        "source_mus_size": src.get("mus_size"),
        "N": 90, "k": K, "colour": COLOUR, "pairs": [list(p) for p in PAIRS],
        "core_size": len(core),
        "prereg": {"H_tiny<=10": 0.15, "H_small_11_60": 0.40,
                   "H_medium_61_500": 0.30, "H_large>500": 0.15,
                   "secondary_backdoor<=2": 0.25},
    }

    # ---- G1: the re-encoded instance must be UNSAT -------------------
    base = initial_domains(roots)
    st = case_tree(base, groups, pair_clauses, order, "dynamic",
                   args.node_cap)
    if st["sat"]:
        result["G1_unsat"] = False
        print("G1 FAILED: my encoding admits a colouring -> different "
              "instance than the receipt measured. STOP.")
        result["verdict"] = "GATE_FAIL_G1"
        print(json.dumps(result, indent=2))
        return 1
    result["G1_unsat"] = True

    # ---- G2: full positive control — every single-drop must be SAT ---
    drops_unsat = []
    for i in range(len(core)):
        sub = groups[:i] + groups[i + 1:]
        d = initial_domains(roots)
        s = case_tree(d, sub, pair_clauses, order, "dynamic", 60000)
        if not s["sat"]:
            drops_unsat.append(list(core[i]))
    result["G2_drops_checked"] = len(core)
    result["G2_drops_still_unsat"] = drops_unsat
    result["G2_pass"] = (len(drops_unsat) == 0)

    # ---- measurement -------------------------------------------------
    trees = {}
    for mode in ("static", "dynamic"):
        d = initial_domains(roots)
        s = case_tree(d, groups, pair_clauses, order, mode, args.node_cap)
        trees[mode] = {"leaves": s["leaves"], "depth": s["depth"],
                       "nodes": s["nodes"], "capped": s["nodes"] > args.node_cap,
                       "branch_roots": sorted(s["branch_roots"]),
                       "branch_root_count": len(s["branch_roots"]),
                       "branch_node_counts": {str(k): v for k, v in
                                              sorted(s["branch_roots"].items())},
                       "leaves_by_depth": {str(k): v for k, v in
                                           sorted(s["leaves_by_depth"].items())}}
    result["trees"] = trees
    best = min(trees.values(), key=lambda t: t["leaves"])
    L = best["leaves"]
    result["best_leaves"] = L
    result["best_depth"] = best["depth"]
    result["verdict"] = ("H_tiny" if L <= 10 else
                         "H_small" if L <= 60 else
                         "H_medium" if L <= 500 else "H_large")

    # ---- secondary: uniform backdoor |S| <= backdoor_max -------------
    found = None
    cands = order[:14]
    for size in range(1, args.backdoor_max + 1):
        for S in itertools.combinations(cands, size):
            base_d = initial_domains(roots)
            if not propagate(base_d, groups, pair_clauses):
                found = []
                break
            doms = [sorted(base_d[r]) for r in S]
            ok = True
            for combo in itertools.product(*doms):
                d = {r: set(v) for r, v in base_d.items()}
                for r, c in zip(S, combo):
                    d[r] = {c}
                if propagate(d, groups, pair_clauses):
                    ok = False
                    break
            if ok:
                found = list(S)
                break
        if found is not None:
            break
    result["backdoor_candidates_scanned"] = cands
    result["uniform_backdoor"] = found
    result["secondary_backdoor_le2"] = found is not None and len(found) <= 2
    result["elapsed_s"] = round(time.time() - t0, 3)

    print(json.dumps(result, indent=2))
    if not args.no_out:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        blob = json.dumps(result, sort_keys=True).encode()
        import hashlib
        result["sha16"] = hashlib.sha256(blob).hexdigest()[:16]
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2, sort_keys=True)
        print("receipt:", out_path, "sha16:", result["sha16"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
