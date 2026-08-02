"""
LEAF WITNESSES for the 76-leaf case tree of the 2-pair cover claim
(N=90, k=5, c=3, MUS-92).   Wake 20:00 02-08-2026, solo.

WHY THIS SCRIPT EXISTS
  18:00 today measured the WIDTH of the argument: 76 conflict leaves,
  depth 6, branching on seven roots (receipt sha16=7f094ff660e8b2a3).
  STATE.md then recorded the next step as "write the 76 cases out in
  prose -- finite work of known size".

  It is not writable from that receipt. The receipt holds COUNTS only:
  leaves, depth, leaves_by_depth, branch_node_counts. No branch paths,
  no conflicting clauses. Prose written from counts would be invented
  case-by-case detail dressed as a measurement. So the actual next step
  is to EMIT the leaves, with enough per-leaf structure that a reader
  can check each case without re-running my search.

WHAT A LEAF MUST CARRY (and why not less)
  The whole instance is UNSAT. Therefore "assert this leaf's path into
  the CNF and the solver says UNSAT" is true of EVERY path, including
  wrong ones, truncated ones and invented ones. That check cannot fail,
  so it certifies nothing -- it would only look like verification.

  What is actually claimed about a leaf is stronger and falsifiable:
  the path closes BY UNIT PROPAGATION ALONE. So each leaf carries a
  DERIVATION: an ordered list of steps, each naming the clause used and
  the already-pinned roots that make it fire, ending in a conflict step.

  Finder and checker are then different acts on different code:
    - the tree walk SEARCHES for the steps,
    - check_derivation() only VALIDATES a step it is handed
      (is this clause in the instance? are these roots pinned as
      claimed? does the rule licence exactly this removal?)
  A checker that cannot search cannot inherit the search's blind spot.

GATES
  G1  re-encoded instance UNSAT and leaf/depth profile reproduces the
      18:00 receipt exactly (76 / 6 / 7 roots, leaves_by_depth).
      Divergence = I am emitting witnesses for a different instance.
  W1  every emitted derivation validates step-by-step.
  W2  the 76 paths COVER the case space: every total assignment of the
      branch roots over their surviving domains is compatible with at
      least one leaf (exhaustive) and at most one (disjoint).
      This is combinatorial and does not consult the tree walk.
  M   mutation / positive control, because W1 and W2 are worthless if
      they cannot go red:
        M1 corrupt one derivation step  -> W1 must FAIL
        M2 drop one leaf                -> W2 exhaustiveness must FAIL
        M3 duplicate-and-relax one leaf -> W2 disjointness must FAIL
      All three are reported; a green M is a failed script, not a pass.
"""
import sys
import os
import json
import time
import itertools
import argparse

sys.path.insert(0, os.path.dirname(__file__))
import receipts
from case_tree_cover import (K, COLOUR, PAIRS, RECEIPT, roots_of,
                             initial_domains, load_core, branch_roots)


# ---------------------------------------------------------------- finder

def propagate_traced(dom, groups, pair_clauses):
    """Unit propagation identical in rule to case_tree_cover.propagate,
    but recording every deduction as a checkable step.

    Step kinds:
      'mono_prune'  clause g, colour c: all but one root of g pinned to c
                    -> the remaining root loses c
      'mono_conflict'  every root of g pinned to the same colour c
      'pair_prune'  clause (a,b): a pinned to COLOUR -> b loses COLOUR
      'pair_conflict'  both pinned to COLOUR
      'empty'       a domain went empty as a result of the last removal
    Returns (ok, steps)."""
    steps = []
    changed = True
    while changed:
        changed = False
        for g in groups:
            for c in range(K):
                pinned = [r for r in g if dom[r] == {c}]
                if len(pinned) == len(g):
                    steps.append({"kind": "mono_conflict", "clause": list(g),
                                  "colour": c, "because": list(g)})
                    return False, steps
                if len(pinned) == len(g) - 1:
                    rest = [r for r in g if dom[r] != {c}]
                    r = rest[0]
                    if c in dom[r]:
                        dom[r] = dom[r] - {c}
                        steps.append({"kind": "mono_prune", "clause": list(g),
                                      "colour": c, "because": pinned,
                                      "root": r, "removed": c,
                                      "left": sorted(dom[r])})
                        if not dom[r]:
                            steps.append({"kind": "empty", "root": r})
                            return False, steps
                        changed = True
        for (a, b) in pair_clauses:
            if dom[a] == {COLOUR} and dom[b] == {COLOUR}:
                steps.append({"kind": "pair_conflict", "clause": [a, b],
                              "colour": COLOUR, "because": [a, b]})
                return False, steps
            for (x, y) in ((a, b), (b, a)):
                if dom[x] == {COLOUR} and COLOUR in dom[y]:
                    dom[y] = dom[y] - {COLOUR}
                    steps.append({"kind": "pair_prune", "clause": [a, b],
                                  "colour": COLOUR, "because": [x],
                                  "root": y, "removed": COLOUR,
                                  "left": sorted(dom[y])})
                    if not dom[y]:
                        steps.append({"kind": "empty", "root": y})
                        return False, steps
                    changed = True
    return True, steps


def walk(dom0, groups, pair_clauses, order):
    """Static-degree case tree (the 18:00 'static' arm), emitting leaves."""
    leaves = []
    branch_counts = {}
    state = {"sat": False, "nodes": 0, "depth": 0}

    def rec(dom, path, trace):
        """trace = the FULL derivation from the initial domains down to
        here: propagation steps and 'pin' steps interleaved in the order
        a reader would replay them. A leaf that carried only its own
        node's propagation would be a fragment -- the first version of
        this script did exactly that and all 76 checks failed, because
        the deductions inherited from ancestors were missing."""
        state["nodes"] += 1
        d2 = {r: set(v) for r, v in dom.items()}
        ok, steps = propagate_traced(d2, groups, pair_clauses)
        trace = trace + steps
        if not ok:
            leaves.append({"path": [list(p) for p in path],
                           "depth": len(path), "steps": trace})
            state["depth"] = max(state["depth"], len(path))
            return
        cand = [r for r in order if len(d2[r]) > 1]
        if not cand:
            state["sat"] = True
            return
        r = cand[0]
        branch_counts[r] = branch_counts.get(r, 0) + 1
        colours = sorted(d2[r])
        assert set(colours) == d2[r]          # G3, as at 18:00
        # the split is exhaustive only relative to what propagation has
        # already removed; record that so the checker can re-derive it
        nodes_out.append({"depth": len(path), "root": r,
                          "branched": colours,
                          "removed": sorted(set(range(K)) - set(colours)),
                          "path": [list(p) for p in path],
                          "steps": trace})
        for c in colours:
            d3 = {rr: set(vv) for rr, vv in d2.items()}
            d3[r] = {c}
            rec(d3, path + [(r, c)],
                trace + [{"kind": "pin", "root": r, "colour": c}])

    nodes_out = []
    rec(dom0, [], [])
    return leaves, branch_counts, state, nodes_out


# --------------------------------------------------------------- checker

def _ok(pins, leaf):
    """A derivation that closes but whose pins do not match the stated
    path is describing a different case than the one it is labelled."""
    if [list(p) for p in pins] != [list(p) for p in leaf["path"]]:
        return False, "stated path does not match the pins in the derivation"
    return True, "ok"


def check_derivation(leaf, dom0, group_set, pair_set,
                     require_conflict=True, out=None):
    """VALIDATE a handed-in derivation. Never searches: replays the path,
    then applies exactly the steps as written and checks each is licensed.
    Returns (ok, reason)."""
    dom = {r: set(v) for r, v in dom0.items()}
    steps = leaf["steps"]
    if not steps:
        return False, "empty derivation"
    pins = []
    for i, s in enumerate(steps):
        kind = s["kind"]
        if kind == "pin":
            r, c = s["root"], s["colour"]
            if c not in dom[r]:
                return False, ("step %d: pin %d=%d outside surviving "
                               "domain %s" % (i, r, c, sorted(dom[r])))
            dom[r] = {c}
            pins.append([r, c])
            continue
        if kind in ("mono_prune", "mono_conflict"):
            g = tuple(sorted(s["clause"]))
            if g not in group_set:
                return False, "step %d: clause %s not in the core" % (i, g)
        elif kind in ("pair_prune", "pair_conflict"):
            p = tuple(sorted(s["clause"]))
            if p not in pair_set:
                return False, "step %d: %s not a cover pair" % (i, p)
        elif kind == "empty":
            if dom[s["root"]]:
                return False, "step %d: root %d not empty" % (i, s["root"])
            if i != len(steps) - 1:
                return False, "step %d: 'empty' before the end" % i
            return _ok(pins, leaf)
        else:
            return False, "step %d: unknown kind %r" % (i, kind)

        c = s["colour"]
        because = s["because"]
        for r in because:
            if dom[r] != {c}:
                return False, ("step %d: root %d claimed pinned to %d, "
                               "domain is %s" % (i, r, c, sorted(dom[r])))
        if kind == "mono_conflict":
            if set(because) != set(s["clause"]):
                return False, "step %d: conflict needs the whole clause" % i
            if i != len(steps) - 1:
                return False, "step %d: conflict before the end" % i
            return _ok(pins, leaf)
        if kind == "pair_conflict":
            if set(because) != set(s["clause"]):
                return False, "step %d: pair conflict needs both roots" % i
            if i != len(steps) - 1:
                return False, "step %d: conflict before the end" % i
            return _ok(pins, leaf)
        if kind == "mono_prune":
            g = s["clause"]
            rest = [r for r in g if r not in because]
            if len(rest) != 1 or rest[0] != s["root"]:
                return False, ("step %d: mono rule needs all-but-one pinned, "
                               "got %d free" % (i, len(rest)))
            if len(because) != len(g) - 1:
                return False, "step %d: wrong number of pinned roots" % i
        if kind == "pair_prune":
            a, b = s["clause"]
            other = b if s["root"] == a else a
            if s["root"] not in (a, b) or because != [other]:
                return False, "step %d: pair rule not licensed" % i
            if c != COLOUR:
                return False, "step %d: pair rule only fires on c=%d" % (
                    i, COLOUR)
        r, rem = s["root"], s["removed"]
        if rem not in dom[r]:
            return False, "step %d: %d already lacks colour %d" % (i, r, rem)
        dom[r] = dom[r] - {rem}
        if sorted(dom[r]) != s["left"]:
            return False, "step %d: stated leftover domain is wrong" % i
    if out is not None:
        out["dom"] = dom
        out["pins"] = pins
    if require_conflict:
        return False, "derivation ended without a conflict"
    return True, "ok"


def check_node_splits(nodes, dom0, gset, pset):
    """W2 (corrected). The first version of this gate asked whether the
    76 paths cover the PRODUCT of the branch roots' initial domains.
    That is the wrong claim and it went red for the right reason: 999 of
    2187 assignments are refuted by propagation before any split, so they
    are covered by a DERIVATION, not by a case. Exhaustiveness of a case
    tree is a LOCAL property -- at every internal node the split must
    cover the root's whole SURVIVING domain, and every colour missing
    from the split must have been removed by a validated step.

    The checker replays each node's derivation and recomputes the
    surviving domain itself; it never asks the tree walk what it was."""
    bad = []
    for i, nd in enumerate(nodes):
        out = {}
        ok, why = check_derivation(nd, dom0, gset, pset,
                                   require_conflict=False, out=out)
        if not ok:
            bad.append({"node": i, "why": "derivation: " + why})
            continue
        surviving = out["dom"][nd["root"]]
        if set(nd["branched"]) != surviving:
            bad.append({"node": i, "root": nd["root"],
                        "why": "split %s != surviving domain %s"
                        % (nd["branched"], sorted(surviving))})
    return bad


def check_cover(leaves, dom0, branch_roots_used):
    """Exhaustive + disjoint, computed from the PATHS ONLY -- no tree,
    no propagation. Every total assignment of the branched roots over
    their initial domains must be compatible with exactly one leaf."""
    rs = sorted(branch_roots_used)
    doms = [sorted(dom0[r]) for r in rs]
    uncovered, multi = [], []
    paths = [dict((int(a), int(b)) for a, b in lf["path"]) for lf in leaves]
    for combo in itertools.product(*doms):
        asg = dict(zip(rs, combo))
        hits = sum(1 for p in paths
                   if all(asg[r] == c for r, c in p.items() if r in asg))
        if hits == 0:
            uncovered.append(asg)
        elif hits > 1:
            multi.append(asg)
    return {"space": len(list(itertools.product(*doms))),
            "roots": rs,
            "uncovered": len(uncovered),
            "overlapping": len(multi),
            "uncovered_sample": uncovered[:3],
            "overlapping_sample": multi[:3]}


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt", default=RECEIPT)
    ap.add_argument("--prior", default="search/out/"
                    "case_tree_cover_N90_c3_mus92.json")
    ap.add_argument("--out", default="")
    ap.add_argument("--no-out", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    src, core = load_core(args.receipt)
    roots = roots_of()
    dom0 = initial_domains(roots)
    groups = [tuple(sorted(g)) for g in core]
    pair_clauses = [tuple(sorted(p)) for p in PAIRS]
    order, _deg = branch_roots(core, PAIRS)

    leaves, branch_counts, state, nodes = walk(
        dom0, groups, pair_clauses, order)
    by_depth = {}
    for lf in leaves:
        by_depth[lf["depth"]] = by_depth.get(lf["depth"], 0) + 1

    res = {
        "script": "case_tree_witnesses.py",
        "wake": "2026-08-02T20:00Z",
        "source_receipt_sha16": src.get("sha16"),
        "N": 90, "k": K, "colour": COLOUR, "core_size": len(core),
        "leaves": len(leaves), "depth": state["depth"],
        "sat_leaf_found": state["sat"],
        "branch_roots": sorted(branch_counts),
        "leaves_by_depth": {str(k): v for k, v in sorted(by_depth.items())},
    }

    # ---- G1: must reproduce the 18:00 static arm exactly --------------
    with open(args.prior) as f:
        prior = json.load(f)["trees"]["static"]
    res["G1_matches_prior"] = (
        len(leaves) == prior["leaves"]
        and state["depth"] == prior["depth"]
        and sorted(branch_counts) == sorted(int(r) for r in
                                            prior["branch_roots"])
        and {str(k): v for k, v in sorted(by_depth.items())}
        == {str(k): v for k, v in sorted(
            (int(a), b) for a, b in prior["leaves_by_depth"].items())})
    res["G1_prior_sha16"] = json.load(open(args.prior)).get("sha16")

    # ---- W1: every derivation validates ------------------------------
    gset, pset = set(groups), set(pair_clauses)
    bad = []
    for i, lf in enumerate(leaves):
        ok, why = check_derivation(lf, dom0, gset, pset)
        if not ok:
            bad.append({"leaf": i, "why": why})
    res["W1_checked"] = len(leaves)
    res["W1_failed"] = len(bad)
    res["W1_failures"] = bad[:5]
    res["W1_pass"] = not bad

    # ---- W2: every split covers its root's surviving domain ---------
    nd_bad = check_node_splits(nodes, dom0, gset, pset)
    res["W2_nodes_checked"] = len(nodes)
    res["W2_failed"] = len(nd_bad)
    res["W2_failures"] = nd_bad[:5]
    res["W2_pass"] = not nd_bad

    # ---- W3: leaves pairwise disjoint (kept from the first version,
    #          it was the half of the old W2 that tested a real claim)
    res["W3"] = check_cover(leaves, dom0, set(branch_counts))
    res["W3_disjoint_pass"] = res["W3"]["overlapping"] == 0
    res["W3_note"] = ("uncovered counts assignments killed by propagation "
                      "before any split -- covered by derivation, not by a "
                      "case; exhaustiveness is W2, not this")

    # ---- M: the checks must be able to go red ------------------------
    m = {}
    victim = json.loads(json.dumps(leaves[0]))
    for st in victim["steps"]:
        if st["kind"] == "mono_prune":
            st["removed"] = (st["removed"] + 1) % K
            break
    ok, why = check_derivation(victim, dom0, gset, pset)
    m["M1_corrupt_step_rejected"] = (not ok)
    m["M1_reason"] = why

    # M2: drop an inherited (ancestor) segment from a deep leaf -- this
    # is exactly the defect the first version of this script shipped
    deep = max(leaves, key=lambda l: l["depth"])
    trunc = json.loads(json.dumps(deep))
    first_pin = next(i for i, st in enumerate(trunc["steps"])
                     if st["kind"] == "pin")
    trunc["steps"] = trunc["steps"][first_pin:]
    ok2, why2 = check_derivation(trunc, dom0, gset, pset)
    m["M2_fragment_rejected"] = (not ok2)
    m["M2_reason"] = why2

    # M3: widen one split by a colour propagation had removed
    nd_bad_m = None
    for i, nd in enumerate(nodes):
        if nd["removed"]:
            mut = json.loads(json.dumps(nd))
            mut["branched"] = sorted(mut["branched"] + [mut["removed"][0]])
            nd_bad_m = check_node_splits([mut], dom0, gset, pset)
            break
    m["M3_widened_split_rejected"] = bool(nd_bad_m)
    m["M3_reason"] = (nd_bad_m or [{}])[0].get("why", "no node had a "
                                               "removed colour to widen")

    # M4: mislabel a path -- derivation closes but says it is another case
    mis = json.loads(json.dumps(leaves[0]))
    mis["path"] = [[mis["path"][0][0], (mis["path"][0][1] + 1) % K]]         + mis["path"][1:]
    ok4, why4 = check_derivation(mis, dom0, gset, pset)
    m["M4_mislabelled_path_rejected"] = (not ok4)
    m["M4_reason"] = why4

    m["pass"] = all([m["M1_corrupt_step_rejected"], m["M2_fragment_rejected"],
                     m["M3_widened_split_rejected"],
                     m["M4_mislabelled_path_rejected"]])
    res["M"] = m

    res["all_gates_pass"] = (res["G1_matches_prior"] and res["W1_pass"]
                             and res["W2_pass"]
                             and res["W3_disjoint_pass"] and m["pass"])
    res["elapsed_s"] = round(time.time() - t0, 3)
    res["cases"] = leaves
    res["nodes"] = nodes

    out = args.out or "search/out/case_tree_witnesses_N90_c3_mus92.json"
    if not args.no_out:
        if hasattr(receipts, "write_receipt"):
            receipts.write_receipt(out, res)
        else:
            with open(out, "w") as f:
                json.dump(res, f, indent=1)
    slim = {k: v for k, v in res.items() if k != "cases"}
    print(json.dumps(slim, indent=1))


if __name__ == "__main__":
    main()
