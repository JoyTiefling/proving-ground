"""
SAT-verify 4-signature partition from orbit_partition_run1.json (sha16=d694c168...).

Wake 24-07 06:00 solo, angle (a) from щель №2 open next-angles.

Hypothesis (from analyze_forced_same_orbits.py sample): under T_44, every non-45
chain-root falls into one of 4 signature-classes:
  A = {1,13,23,37,43,57,67}   — always color 0 (dist [18,0,0,0,0])
  B = {3,5,31,39,61,69}       — always color 1 (dist [0,18,0,0,0])
  T = {7,9,11,15,17,19,21,25,27,29,33,35,41,47,49,51,53,55,59,63,65,71,73,75,77,83,85,87,89}
                              — uniform in {2,3,4} (dist [0,0,6,6,6])
  X = {79,81}                 — dist [6,0,4,4,4] (color 0 OR {2,3,4}, never 1)

Razor from state: sample 18 colorings, sym-break fixes labels — is this really
rigid, or is it a sample artifact (sample-correlation ≠ forcing)?

Verification protocol — SAT with pysat/Minisat22 for each root separately:
  Symmetry-break anchor: color(1)=0, color(3)=1, color(7)=2.
  For each R in A: is [color(R) != 0] UNSAT under T_44? UNSAT = R forced to 0.
  For each R in B: is [color(R) != 1] UNSAT under T_44? UNSAT = R forced to 1.
  For each R in T: is [color(R) in {0,1}] UNSAT under T_44?
    (encoded as SAT with color(R)=0 OR color(R)=1 — either sat = escape from T)
  For each R in X: is [color(R) = 1] UNSAT under T_44? UNSAT = R never in 1.

Predictions under H_rigid (Bayes prior 0.5, from state 24-07):
  H_rigid holds: all 44 checks return the expected verdict → partition SAT-verified.
  H_sample_artifact: some root R escapes → single counter-example flips the map.

Full escape witness saved when SAT. JSON receipt with sha16 for reproducibility.
"""
import sys, os, time, json, hashlib
sys.path.insert(0, os.path.dirname(__file__))
from explore_pigeonhole_45 import (
    chains_up_to_N, forbidden_triples, split_triples_by_root,
)

N, k, TARGET = 90, 5, 45

# Partition from orbit_partition_run1.json (sha16=d694c168a4142180).
CLASS_A = [1, 13, 23, 37, 43, 57, 67]
CLASS_B = [3, 5, 31, 39, 61, 69]
CLASS_T = [7, 9, 11, 15, 17, 19, 21, 25, 27, 29, 33, 35, 41, 47, 49, 51, 53, 55,
           59, 63, 65, 71, 73, 75, 77, 83, 85, 87, 89]
CLASS_X = [79, 81]

# Symmetry anchor: representative of each of A, B, T.
ANCHOR = {1: 0, 3: 1, 7: 2}


def build_cnf():
    """Build T_44 no-mono CNF + exactly-one color per root."""
    from pysat.formula import CNF
    chain_by_root = chains_up_to_N(N)
    all_roots = sorted(chain_by_root.keys())
    roots_no_target = [r for r in all_roots if r != TARGET]
    all_tri = forbidden_triples(N)
    _, T_other = split_triples_by_root(all_tri, TARGET)

    idx = {r: i for i, r in enumerate(roots_no_target)}
    def V(r, c):
        return idx[r] * k + c + 1

    cnf = CNF()
    for r in roots_no_target:
        lits = [V(r, c) for c in range(k)]
        cnf.append(lits)  # at-least-one
        for i in range(k):
            for j in range(i+1, k):
                cnf.append([-lits[i], -lits[j]])  # at-most-one
    for tri in T_other:
        rs = list(set(tri))
        if any(r == TARGET for r in rs):
            continue
        for c in range(k):
            cnf.append([-V(r, c) for r in rs])
    return cnf, V, roots_no_target


def anchor_assumptions(V):
    """Fix color(1)=0, color(3)=1, color(7)=2 as symmetry break."""
    return [V(r, c) for r, c in ANCHOR.items()]


def extract_coloring(model_set, V, roots_no_target):
    """Given a satisfying model (set of positive literals), extract coloring."""
    out = {}
    for r in roots_no_target:
        for c in range(k):
            if V(r, c) in model_set:
                out[r] = c
                break
    return out


def verify_class(cnf, V, roots_no_target, root, forbidden_colors):
    """Check UNSAT of [color(root) ∈ forbidden_colors] under T_44 + anchor.

    forbidden_colors: list of ints. If ANY of these is satisfiable — root escapes.
    Return: (verdict, witness_dict_or_None).
      verdict = "rigid" if all forbidden colors UNSAT.
      verdict = "escapes" with witness for the first satisfied color.
    """
    from pysat.solvers import Minisat22
    assumptions = anchor_assumptions(V)
    for c in forbidden_colors:
        with Minisat22(bootstrap_with=cnf.clauses) as s:
            ok = s.solve(assumptions=assumptions + [V(root, c)])
            if ok:
                model = set(s.get_model())
                witness = extract_coloring(model, V, roots_no_target)
                return "escapes", {"color": c, "witness": witness}
    return "rigid", None


def main():
    t0 = time.time()
    print(f"N={N} k={k} target={TARGET}. Verifying 4-signature partition under T_44.")
    print(f"Anchor: color(1)=0, color(3)=1, color(7)=2.")
    print(f"Referencing partition sha16=d694c168a4142180 (orbit_partition_run1.json).")

    cnf, V, roots_no_target = build_cnf()
    print(f"CNF built: {len(cnf.clauses)} clauses over {len(roots_no_target)*k} vars.")

    receipt = {
        "script": os.path.basename(__file__),
        "wake": "24-07 06:00 solo",
        "config": {"N": N, "k": k, "target": TARGET},
        "anchor": {str(r): c for r, c in ANCHOR.items()},
        "partition_source": {
            "file": "orbit_partition_run1.json",
            "sha16": "d694c168a4142180",
        },
        "partition_claim": {
            "A_always_0": CLASS_A,
            "B_always_1": CLASS_B,
            "T_in_234": CLASS_T,
            "X_never_1": CLASS_X,
        },
        "results": {
            "A": [], "B": [], "T": [], "X": [],
        },
        "summary": {},
    }

    # Sanity: anchor consistency — anchors themselves obey signature claims.
    print("\n=== SANITY: anchor consistency with partition ===")
    for r in ANCHOR:
        cls = "A" if r in CLASS_A else "B" if r in CLASS_B else "T" if r in CLASS_T else "X" if r in CLASS_X else "?"
        print(f"  root {r}: anchor color {ANCHOR[r]}, in class {cls}  "
              f"({'consistent' if (cls, ANCHOR[r]) in [('A', 0), ('B', 1), ('T', 2), ('T', 3), ('T', 4)] else 'INCONSISTENT'})")

    # === Class A: forbid color != 0 ===
    print("\n=== CLASS A (always color 0): check each root ===")
    for r in CLASS_A:
        forbidden = [1, 2, 3, 4]
        if r in ANCHOR:  # skip anchor itself, trivially in claimed color
            print(f"  root {r}: (anchor, skipped)")
            receipt["results"]["A"].append({"root": r, "verdict": "anchor", "witness": None})
            continue
        verdict, witness = verify_class(cnf, V, roots_no_target, r, forbidden)
        print(f"  root {r}: {verdict}" + (f" — escape to color {witness['color']}" if witness else ""))
        receipt["results"]["A"].append({"root": r, "verdict": verdict, "witness": witness})

    # === Class B: forbid color != 1 ===
    print("\n=== CLASS B (always color 1): check each root ===")
    for r in CLASS_B:
        forbidden = [0, 2, 3, 4]
        if r in ANCHOR:
            print(f"  root {r}: (anchor, skipped)")
            receipt["results"]["B"].append({"root": r, "verdict": "anchor", "witness": None})
            continue
        verdict, witness = verify_class(cnf, V, roots_no_target, r, forbidden)
        print(f"  root {r}: {verdict}" + (f" — escape to color {witness['color']}" if witness else ""))
        receipt["results"]["B"].append({"root": r, "verdict": verdict, "witness": witness})

    # === Class T: forbid color 0 and color 1 ===
    print("\n=== CLASS T (in {2,3,4}): check each root ===")
    for r in CLASS_T:
        forbidden = [0, 1]
        if r in ANCHOR:
            print(f"  root {r}: (anchor, skipped)")
            receipt["results"]["T"].append({"root": r, "verdict": "anchor", "witness": None})
            continue
        verdict, witness = verify_class(cnf, V, roots_no_target, r, forbidden)
        print(f"  root {r}: {verdict}" + (f" — escape to color {witness['color']}" if witness else ""))
        receipt["results"]["T"].append({"root": r, "verdict": verdict, "witness": witness})

    # === Class X: forbid color 1 only ===
    print("\n=== CLASS X (never color 1): check each root ===")
    for r in CLASS_X:
        forbidden = [1]
        verdict, witness = verify_class(cnf, V, roots_no_target, r, forbidden)
        print(f"  root {r}: {verdict}" + (f" — escape to color {witness['color']}" if witness else ""))
        receipt["results"]["X"].append({"root": r, "verdict": verdict, "witness": witness})

    # Summary
    total_checked = sum(1 for cls in ["A", "B", "T", "X"]
                        for entry in receipt["results"][cls]
                        if entry["verdict"] != "anchor")
    rigid = sum(1 for cls in ["A", "B", "T", "X"]
                for entry in receipt["results"][cls]
                if entry["verdict"] == "rigid")
    escapes = sum(1 for cls in ["A", "B", "T", "X"]
                  for entry in receipt["results"][cls]
                  if entry["verdict"] == "escapes")
    receipt["summary"] = {
        "total_checked": total_checked,
        "rigid": rigid,
        "escapes": escapes,
        "H_rigid_supported": escapes == 0,
    }
    print(f"\n=== SUMMARY ===")
    print(f"  Checked: {total_checked} non-anchor roots.")
    print(f"  Rigid:   {rigid}   (forced to signature color)")
    print(f"  Escapes: {escapes}  (sample artifact)")
    if escapes == 0:
        print(f"  H_rigid SUPPORTED — 4-signature partition SAT-verified.")
    else:
        print(f"  H_sample_artifact SUPPORTED — partition breaks in {escapes} places.")

    receipt["elapsed_s"] = round(time.time() - t0, 2)
    _write_receipt(receipt)
    print(f"\nElapsed: {receipt['elapsed_s']}s")


def _write_receipt(receipt):
    out_dir = os.path.join(os.path.dirname(__file__), "out")
    os.makedirs(out_dir, exist_ok=True)
    base = "sat_verify_partition_run"
    existing = [f for f in os.listdir(out_dir) if f.startswith(base) and f.endswith(".json")]
    run_no = len(existing) + 1
    path = os.path.join(out_dir, f"{base}{run_no}.json")
    payload = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    sha16 = hashlib.sha256(payload).hexdigest()[:16]
    receipt["sha16"] = sha16
    with open(path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
    print(f"\nReceipt: {path}  sha16={sha16}")


if __name__ == "__main__":
    main()
