"""Turn the five rigid facts from SAT verdicts into auditable triple-sets.

Wake 16-08 12:00 solo.

WHY. `mus_cover_claim` (14-08) measured the three-step ladder and found the
6.7x/7.4x jump between "rigid free" and "rigid unavailable" is carried by FIVE
positive colour assignments, shared by both colours:

    13 -> 0,  23 -> 0,  43 -> 0   (class A)
    5  -> 1,  31 -> 1              (class B)

Their current status is a SAT verdict: `sat_verify_partition` reported UNSAT for
every wrong colour under T_44 + anchor {1:0, 3:1, 7:2}. An UNSAT verdict is a
proof only if you trust the solver; it is not something a reader of this repo
can audit. The next measurable piece has an address (log/weak-schur.md, 14-08):
"cover costs 130 + 119 triples plus a single proof of those five facts."

WHAT THIS DOES. For each fact (R -> c*) and each wrong colour c != c*, extract an
irreducible subset of T_44 that already forces UNSAT. Two stages:
  1. selector-assumption core: one selector s_t per triple, all triples assumed
     on; Minisat's get_core() returns an over-approximation of the needed set.
  2. deletion-based minimisation inside that core, TWO deletion orders (forward,
     reverse) as two hands -- a size that depends on the order is a property of
     the procedure, not of the object (#3335), and must ride with the number.

If the sets come out small, each of the five stops being an oracle verdict and
becomes a finite combinatorial argument a human can check.

PRE-REGISTERED PREDICTIONS (structure, not magnitude -- the thing that has
actually won on this object before). Written before the first run:

  P1  Locality. Every MUS is a small fraction of T_other (1331 triples): the
      forcing of a single root is local, not global. Falsified if any MUS
      exceeds 200 triples.
  P2  Colour symmetry of the certificate. The anchor pins colours 0,1,2 (via
      1,3,7) and leaves 3,4 interchangeable. So for a fixed fact, the MUS for
      wrong colour 3 and the MUS for wrong colour 4 are EQUAL AS SETS.
      Falsified if they differ for any fact.
  P3  Shared root-1 spine. The class-A facts 13,23,43 are exactly the partners
      of 1 in the forced_same list. So every class-A MUS contains at least one
      triple whose entries meet chain-root 1. Falsified if any class-A MUS is
      free of root 1.

P2 and P3 are cheap to refute, which is the point.

RESULT OF THE FIRST RUN (fact 13 -> 0, receipt `01b9c00621e97385`, 80s):
  P1 REFUTED, and it is the finding. MUS = 319..584 of 1331 triples depending on
  wrong colour. The forcing of a single root is NOT local: proving 13 -> 0 costs
  the same order of magnitude as the 616/633-triple unconditional cover it was
  supposed to undercut. "Prove the five once and share them" buys much less than
  the ladder suggested -- unless the five MUS overlap heavily with each other,
  which this run does not measure.
  P2 was NOT TESTABLE as written -- see the comment at the check. The minimiser
  disagrees with ITSELF by 40-92 triples across two orders on the SAME instance,
  so a set difference between colours 3 and 4 says nothing about the symmetry.
  Sizes: colour 3 -> 579/487, colour 4 -> 584/493: the cross-colour gap (5,6) is
  an order of magnitude below the procedure's self-noise, i.e. entirely
  consistent with the symmetry the prediction claimed. I wrote a prediction
  about the object and a test that could only see my procedure.
  P3 SUPPORTED: every class-A MUS meets root 1.
"""
import sys, os, time, json, argparse
sys.path.insert(0, os.path.dirname(__file__))

from explore_pigeonhole_45 import (
    chains_up_to_N, forbidden_triples, split_triples_by_root,
)
import receipts

N, K, TARGET = 90, 5, 45
ANCHOR = {1: 0, 3: 1, 7: 2}

# The five facts carrying the 6.7x/7.4x jump (mus_cover_claim, 14-08).
FIVE = [(13, 0), (23, 0), (43, 0), (5, 1), (31, 1)]


def build():
    """CNF over roots != 45 with one selector per triple.

    Returns (base_clauses, V, sel, triples, roots).
      base_clauses: exactly-one-colour clauses only.
      sel[t] -> selector var for triple index t; triple clauses are
      [-sel, -V(r1,c), -V(r2,c), -V(r3,c)] so assuming sel turns the triple on.
    """
    chain_by_root = chains_up_to_N(N)
    roots = [r for r in sorted(chain_by_root.keys()) if r != TARGET]
    _, T_other = split_triples_by_root(forbidden_triples(N), TARGET)
    triples = sorted({tuple(sorted(set(t))) for t in T_other
                      if TARGET not in set(t)})

    idx = {r: i for i, r in enumerate(roots)}
    nvar_colour = len(roots) * K

    def V(r, c):
        return idx[r] * K + c + 1

    clauses = []
    for r in roots:
        lits = [V(r, c) for c in range(K)]
        clauses.append(lits)
        for i in range(K):
            for j in range(i + 1, K):
                clauses.append([-lits[i], -lits[j]])

    sel = {}
    for t, tri in enumerate(triples):
        s = nvar_colour + 1 + t
        sel[t] = s
        for c in range(K):
            clauses.append([-s] + [-V(r, c) for r in tri])
    return clauses, V, sel, triples, roots


def unsat_with(clauses, assumptions):
    from pysat.solvers import Minisat22
    with Minisat22(bootstrap_with=clauses) as s:
        ok = s.solve(assumptions=assumptions)
        core = None if ok else list(s.get_core() or [])
        return (not ok), core


def minimise(clauses, fixed, sel, candidates, order):
    """Deletion-based irreducible subset of `candidates` (triple indices)."""
    keep = set(candidates)
    calls = 0
    for t in order:
        if t not in keep:
            continue
        trial = keep - {t}
        unsat, _ = unsat_with(clauses, fixed + [sel[i] for i in sorted(trial)])
        calls += 1
        if unsat:
            keep = trial
    return sorted(keep), calls


def run_fact(clauses, V, sel, triples, root, right_colour, verbose=True):
    out = {}
    anchor_lits = [V(r, c) for r, c in ANCHOR.items()]
    all_sel = [sel[t] for t in range(len(triples))]
    for wrong in range(K):
        if wrong == right_colour:
            continue
        fixed = anchor_lits + [V(root, wrong)]
        unsat, core = unsat_with(clauses, fixed + all_sel)
        if not unsat:
            out[wrong] = {"verdict": "ESCAPES"}
            if verbose:
                print(f"  {root}->{wrong}: SAT -- fact {root}->{right_colour} "
                      f"is NOT forced. Prediction chain broken.")
            continue
        sel_inv = {v: t for t, v in sel.items()}
        core_t = sorted({sel_inv[abs(l)] for l in core if abs(l) in sel_inv})
        fwd, c1 = minimise(clauses, fixed, sel, core_t, list(core_t))
        rev, c2 = minimise(clauses, fixed, sel, core_t, list(reversed(core_t)))
        out[wrong] = {
            "verdict": "UNSAT",
            "core_size": len(core_t),
            "mus_forward": [list(triples[t]) for t in fwd],
            "mus_reverse": [list(triples[t]) for t in rev],
            "size_forward": len(fwd),
            "size_reverse": len(rev),
            "same_set": sorted(fwd) == sorted(rev),
            "sat_calls": c1 + c2,
        }
        if verbose:
            print(f"  {root}->{wrong}: UNSAT, core {len(core_t)} -> "
                  f"MUS {len(fwd)} / {len(rev)} "
                  f"({'same set' if sorted(fwd)==sorted(rev) else 'ORDER-DEPENDENT'})")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--facts", default="all",
                    help="comma list of roots, or 'all'")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    facts = FIVE if args.facts == "all" else [
        f for f in FIVE if str(f[0]) in args.facts.split(",")]

    out_path = receipts.resolve_out(args, __file__,
                                    facts="-".join(str(r) for r, _ in facts))
    receipts.probe_writable(out_path)

    t0 = time.time()
    clauses, V, sel, triples, roots = build()
    print(f"N={N} k={K} target={TARGET}: {len(roots)} roots, "
          f"{len(triples)} triples, {len(clauses)} clauses.")

    results = {}
    for root, colour in facts:
        print(f"fact {root} -> {colour}:")
        results[f"{root}->{colour}"] = run_fact(clauses, V, sel, triples,
                                                root, colour)

    # Pre-registered checks.
    checks = {}
    sizes = [d["size_forward"] for f in results.values()
             for d in f.values() if d["verdict"] == "UNSAT"]
    checks["P1_locality"] = {
        "max_mus": max(sizes) if sizes else None,
        "of_total": len(triples),
        "verdict": "SUPPORTED" if sizes and max(sizes) <= 200 else "REFUTED",
    }
    # P2 as pre-registered is NOT TESTABLE by this procedure: the minimiser is
    # order-dependent (it disagrees with ITSELF across two orders on the same
    # instance), so set-inequality between colours 3 and 4 cannot separate "the
    # symmetry is broken" from "the deletion order wandered". Reporting it as
    # REFUTED would be a statement about my procedure worn as a statement about
    # the object (#3468). What IS comparable: the solver-deterministic core, and
    # the spread of sizes relative to the procedure's own self-disagreement.
    p2 = {}
    for name, f in results.items():
        a, b = f.get(3), f.get(4)
        if not (a and b and a["verdict"] == b["verdict"] == "UNSAT"):
            continue
        self_spread = max(abs(d["size_forward"] - d["size_reverse"])
                          for d in (a, b))
        cross_spread = abs(a["size_forward"] - b["size_forward"])
        p2[name] = {
            "core_equal": a["core_size"] == b["core_size"],
            "self_disagreement": self_spread,
            "cross_colour_gap": cross_spread,
            "sets_equal": sorted(map(tuple, a["mus_forward"]))
                          == sorted(map(tuple, b["mus_forward"])),
            "reading": ("consistent with symmetry (cross gap within the "
                        "procedure's own noise)" if cross_spread <= self_spread
                        else "cross gap EXCEEDS self-noise -- worth a look"),
        }
    checks["P2_colour34_identical"] = {
        "per_fact": p2,
        "verdict": "NOT TESTABLE BY THIS PROCEDURE",
        "note": "order-dependent minimiser; see comment in source",
    }
    p3 = {}
    for name, f in results.items():
        if not name.startswith(("13", "23", "43")):
            continue
        p3[name] = all(
            any(1 in tri for tri in d["mus_forward"])
            for d in f.values() if d["verdict"] == "UNSAT")
    checks["P3_root1_spine"] = {
        "per_fact": p3,
        "verdict": "SUPPORTED" if p3 and all(p3.values()) else "REFUTED",
    }

    print("\nPre-registered:")
    for k, v in checks.items():
        print(f"  {k}: {v['verdict']}  {({kk: vv for kk, vv in v.items() if kk != 'verdict'})}")

    receipt = {
        "script": os.path.basename(__file__),
        "wake": receipts.wake_iso(),
        "config": {"N": N, "k": K, "target": TARGET,
                   "anchor": {str(r): c for r, c in ANCHOR.items()}},
        "facts": [list(f) for f in facts],
        "source_of_facts": "mus_cover_claim 14-08; rigid verdicts from "
                           "sat_verify_partition_run1.json sha16=3669e88c7ec427c6",
        "preregistered": {
            "P1": "every MUS <= 200 of 1331 triples (forcing is local)",
            "P2": "MUS for wrong colour 3 == MUS for wrong colour 4 (anchor "
                  "leaves 3,4 interchangeable)",
            "P3": "every class-A MUS contains a triple meeting root 1",
        },
        "results": results,
        "checks": checks,
        "elapsed_s": round(time.time() - t0, 1),
    }
    receipts.write_receipt(out_path, receipt)
    print(f"\n{time.time()-t0:.1f}s -> {out_path}")


if __name__ == "__main__":
    main()
