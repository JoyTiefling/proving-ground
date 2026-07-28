"""
ANALYZE forced-same partner pairs of chain 45 as color-orbits under T_44.

Wake 23-07 14:00 (solo, angle-for-forcing-analytical).

Question: 10 forced-same pairs are known computationally (SAT).
  self-pairs (trivial): (3,3), (5,5), (9,9), (15,15)
  real (6):             (1,13), (1,23), (1,43), (7,19), (11,17), (35,55)

If forced-same holds under T_44 alone, then ANY valid T_44 coloring must
have color(a) = color(b) for every forced-same pair (a,b). So the 6 real
pairs define an equivalence relation on chain-roots that is invariant of
which coloring we pick. Follow transitivity:
  {1,13,23,43}  (via 1↔13, 1↔23, 1↔43)
  {7,19}
  {11,17}
  {35,55}
plus 40 singletons for the other roots.

Test 1 — verify empirically: on K diverse valid T_44 colorings, does
color(1)=color(13)=color(23)=color(43) hold ALWAYS? Same for the others?

Test 2 — extract additional forcings from data: within the 40 "singleton"
roots, do any two ALSO always share color across all colorings we sampled?
(would extend the equivalence, or fail to — either way, data.)

Test 3 — inspect ORBIT-color distribution: for each orbit, count how many
of K colorings assign it color 0, 1, ..., 4. If distributions are highly
skewed, the orbits are "channeled" — a step toward analytic why-story.

Method:
  Reuse find_valid_colorings from explore_pigeonhole_45. Run many orders
  and candidate permutations to get diverse T_44 colorings.

Ceilings: MAX_COLORINGS ≤ 200 total; MAX_ORDERS ≤ 20; MAX_PER_ORDER ≤ 10.
Should run in ~30s at most given single-coloring DPLL is <1s.
"""
import sys, os, time, json, hashlib
sys.path.insert(0, os.path.dirname(__file__))
from explore_pigeonhole_45 import (
    chains_up_to_N, forbidden_triples, split_triples_by_root,
    find_valid_colorings,
)

N, k, TARGET = 90, 5, 45

# 6 real forced-same pairs (self-pairs are trivial → skip in per-coloring check;
# self forcing means chain(x)={x,2x,...} with x+x=2x collinear in same chain
# → same color trivially).
FORCED_SAME_REAL = [(1,13), (1,23), (1,43), (7,19), (11,17), (35,55)]
FORCED_SAME_SELF = [(3,3), (5,5), (9,9), (15,15)]  # sanity

# Derived orbits under transitivity of FORCED_SAME_REAL:
ORBITS_KNOWN = [
    {1, 13, 23, 43},
    {7, 19},
    {11, 17},
    {35, 55},
]


def orbit_of(root, orbits):
    for orb in orbits:
        if root in orb:
            return orb
    return {root}


def main():
    t0 = time.time()
    chain_by_root = chains_up_to_N(N)
    all_roots = sorted(chain_by_root.keys())
    assert TARGET in all_roots
    roots_no_target = [r for r in all_roots if r != TARGET]
    print(f"N={N} k={k} target={TARGET}: {len(all_roots)} chain-roots, "
          f"{len(roots_no_target)} without target.")

    all_tri = forbidden_triples(N)
    T_target, T_other = split_triples_by_root(all_tri, TARGET)
    print(f"|T_44| (no root {TARGET}) = {len(T_other)}, "
          f"|T_45| (contains {TARGET}) = {len(T_target)}")

    # === Receipt collector — structured, JSON-hashable, sha16 in stdout. ===
    # Урок 18-07: SAT witness |D|=36 потерян stdout-only. Правило: json + hash.
    # Что receipt даёт: артефакт для (a) SAT-verify на следующем ходе —
    # 4-class partition (A/B/T/X) становится верифицируемым входом.
    receipt = {
        "script": os.path.basename(__file__),
        "wake": "24-07 06:00 solo",
        "config": {
            "N": N, "k": k, "target": TARGET,
            "num_chain_roots": len(all_roots),
            "num_roots_no_target": len(roots_no_target),
            "T_44_size": len(T_other),
            "T_45_size": len(T_target),
        },
        "sampling": {
            "perms_tried": None,     # filled after perms slice
            "max_sols_per_perm": 3,
        },
        "colorings": {
            "total_before_dedup": None,
            "unique_after_dedup": None,
        },
        "test_1_forced_same_real": [],
        "test_2_extended_always_same": {
            "known_orbit_pairs": None,
            "always_same_count": None,
            "novel_count": None,
            "novel_pairs": [],
        },
        "test_3_orbit_distributions": [],
        "test_4_permutation_triples": {
            "distinct_count": None,
            "triples": [],
        },
        "test_5_signature_partition": {
            "num_signatures": None,
            "groups": [],
        },
    }

    # Collect diverse colorings via a handful of candidate permutations.
    # DPLL with degree-desc ordering + symmetry break is fast for a few
    # solutions; enumerating many can blow up, so keep counts modest and
    # print per-perm timing so we know if any blows up.
    from itertools import permutations
    perms = list(permutations(range(k)))
    # 8 permutations × 3 solutions = 24 candidates — enough for pattern check
    perms = perms[:8]
    receipt["sampling"]["perms_tried"] = [list(cp) for cp in perms]

    all_colorings = []
    for i, cp in enumerate(perms):
        ts = time.time()
        sols, _ = find_valid_colorings(
            roots_no_target, T_other, k,
            max_solutions=3, candidate_perm=list(cp),
        )
        print(f"  perm {i} {cp}: {len(sols)} sols in {time.time()-ts:.2f}s")
        all_colorings.extend(sols)
    print(f"Collected {len(all_colorings)} candidate colorings before dedup.")
    receipt["colorings"]["total_before_dedup"] = len(all_colorings)

    # Dedup by fingerprint
    seen = set()
    uniq = []
    for c in all_colorings:
        fp = hashlib.sha256(
            ",".join(f"{r}:{c[r]}" for r in sorted(c)).encode()
        ).hexdigest()[:16]
        if fp not in seen:
            seen.add(fp)
            uniq.append(c)
    print(f"Deduped: {len(uniq)} distinct colorings.")
    receipt["colorings"]["unique_after_dedup"] = len(uniq)
    if not uniq:
        print("NO colorings found — abort.")
        _write_receipt(receipt, aborted=True)
        return

    # ================================
    # TEST 1 — verify real forced-same holds across all colorings
    # ================================
    print("\n=== TEST 1: forced-same holds under T_44 alone ===")
    for a, b in FORCED_SAME_REAL:
        match = sum(1 for c in uniq if c[a] == c[b])
        status = "OK" if match == len(uniq) else "FAIL"
        print(f"  ({a},{b}): match {match}/{len(uniq)}  [{status}]")
        receipt["test_1_forced_same_real"].append({
            "pair": [a, b], "match": match, "total": len(uniq), "status": status,
        })

    # ================================
    # TEST 2 — extended: find ALL pairs of roots that always share color
    # ================================
    print("\n=== TEST 2: extended empirical forcing (pairs always same across sample) ===")
    always_same = []
    for i, a in enumerate(roots_no_target):
        for b in roots_no_target[i+1:]:
            if all(c[a] == c[b] for c in uniq):
                always_same.append((a, b))
    print(f"  Total 'always-same' pairs in sample: {len(always_same)}")
    known_set = set()
    for orb in ORBITS_KNOWN:
        for x in orb:
            for y in orb:
                if x < y:
                    known_set.add((x, y))
    novel = [p for p in always_same if p not in known_set]
    print(f"  Known-orbit pairs covered: "
          f"{len(known_set & set(always_same))}/{len(known_set)}")
    if novel:
        print(f"  NOVEL always-same pairs (candidates for stronger forcing):")
        for p in novel[:30]:
            print(f"    {p}")
        if len(novel) > 30:
            print(f"    ...(+{len(novel)-30} more)")
    else:
        print("  No novel always-same pairs — sample confirms exactly the "
              "known SAT orbits (no extensions).")
    receipt["test_2_extended_always_same"] = {
        "known_orbit_pairs": len(known_set),
        "known_orbit_pairs_covered": len(known_set & set(always_same)),
        "always_same_count": len(always_same),
        "novel_count": len(novel),
        "novel_pairs": [list(p) for p in novel],  # full list — cheap
    }

    # ================================
    # TEST 3 — orbit color distribution across colorings
    # ================================
    print("\n=== TEST 3: per-orbit color distributions ===")
    for orb in ORBITS_KNOWN:
        rep = min(orb)  # representative
        dist = [0] * k
        for c in uniq:
            dist[c[rep]] += 1
        print(f"  orbit {sorted(orb)}: color-dist = {dist}  (over {len(uniq)} colorings)")
        receipt["test_3_orbit_distributions"].append({
            "orbit": sorted(orb), "representative": rep, "color_dist": dist,
        })

    # Sanity: distribution for a random singleton
    print("  (singletons for comparison):")
    for r in [1, 3, 5, 7, 21, 45]:
        if r not in roots_no_target:
            continue
        dist = [0] * k
        for c in uniq:
            dist[c[r]] += 1
        print(f"    root {r}: color-dist = {dist}")

    # ================================
    # TEST 4 — permutation-orbit hypothesis
    #   The three orbits {7,19}, {11,17}, {35,55} have identical
    #   color-distribution [0,0,6,6,6]. Hypothesis: they form a single
    #   "permutation cell" that bijects onto colors {2,3,4} in each
    #   coloring. Predicts: (c7, c11, c35) takes each of 6 permutations
    #   of {2,3,4} equally often, and never repeats within a coloring.
    # ================================
    print("\n=== TEST 4: permutation-orbit hypothesis on {7,19}/{11,17}/{35,55} ===")
    triples_seen = {}
    for c in uniq:
        t = (c[7], c[11], c[35])
        triples_seen[t] = triples_seen.get(t, 0) + 1
    print(f"  distinct (c7, c11, c35) triples: {len(triples_seen)}")
    receipt["test_4_permutation_triples"]["distinct_count"] = len(triples_seen)
    for t, cnt in sorted(triples_seen.items()):
        distinct = len(set(t)) == 3
        marker = "bij" if distinct else "COLLIDE"
        print(f"    {t}: {cnt}  [{marker}]")
        receipt["test_4_permutation_triples"]["triples"].append({
            "triple": list(t), "count": cnt, "bijection": distinct,
        })

    # ================================
    # TEST 5 — full partition sketch
    #   Group chain-roots by their color-distribution signature.
    #   Roots with the same signature belong (empirically) to the same
    #   "role" in the T_44 quotient.
    # ================================
    print("\n=== TEST 5: chain-root color-signatures under T_44 ===")
    sig_by_root = {}
    for r in roots_no_target:
        dist = [0] * k
        for c in uniq:
            dist[c[r]] += 1
        sig_by_root[r] = tuple(dist)
    groups = {}
    for r, sig in sig_by_root.items():
        groups.setdefault(sig, []).append(r)
    print(f"  distinct signatures: {len(groups)}")
    receipt["test_5_signature_partition"]["num_signatures"] = len(groups)
    for sig, rs in sorted(groups.items(), key=lambda kv: -sum(kv[0])):
        print(f"    {sig} : {sorted(rs)}")
        receipt["test_5_signature_partition"]["groups"].append({
            "signature": list(sig), "roots": sorted(rs), "size": len(rs),
        })

    receipt["elapsed_s"] = round(time.time() - t0, 2)
    _write_receipt(receipt)
    print(f"\nElapsed: {receipt['elapsed_s']}s")


def _write_receipt(receipt, aborted=False):
    """Write structured JSON receipt with sha16 fingerprint.

    Fingerprint = sha256 over receipt with 'sha16' key removed, first 16 hex.
    Deterministic: sort_keys=True. Verifier reproduces by same script + params.
    """
    out_dir = os.path.join(os.path.dirname(__file__), "out")
    os.makedirs(out_dir, exist_ok=True)
    if aborted:
        receipt["status"] = "aborted"
    # Pick next run number to avoid overwriting prior receipts.
    base = "orbit_partition_run"
    existing = [f for f in os.listdir(out_dir) if f.startswith(base) and f.endswith(".json")]
    run_no = len(existing) + 1
    path = os.path.join(out_dir, f"{base}{run_no}.json")
    # Hash without sha16 field
    payload = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    sha16 = hashlib.sha256(payload).hexdigest()[:16]
    receipt["sha16"] = sha16
    with open(path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
    print(f"\nReceipt: {path}  sha16={sha16}")


def sat_check_pair_forced(a, b, verbose=False):
    """Quick SAT check: is (a, b) forced-same, forced-different, or free
    under T_44? Uses pysat if available."""
    try:
        from pysat.solvers import Minisat22
        from pysat.card import CardEnc, EncType
        from pysat.formula import CNF
    except ImportError:
        print("  pysat not available for SAT check.")
        return None
    chain_by_root = chains_up_to_N(N)
    all_roots = sorted(chain_by_root.keys())
    roots_no_target = [r for r in all_roots if r != TARGET]
    all_tri = forbidden_triples(N)
    _, T_other = split_triples_by_root(all_tri, TARGET)
    # var(root, color) = index; 1-based; layout: (roots_no_target index)*k + color + 1
    idx = {r: i for i, r in enumerate(roots_no_target)}
    def V(r, c):
        return idx[r] * k + c + 1
    cnf = CNF()
    # each root exactly one color: exactly-one encoding
    for r in roots_no_target:
        lits = [V(r, c) for c in range(k)]
        cnf.append(lits)  # at-least-one
        for i in range(k):
            for j in range(i+1, k):
                cnf.append([-lits[i], -lits[j]])  # at-most-one
    # no-mono constraints for T_44 (only include triples whose roots are all in roots_no_target)
    for tri in T_other:
        rs = list(set(tri))
        if any(r == TARGET for r in rs):
            continue
        for c in range(k):
            cnf.append([-V(r, c) for r in rs])
    # Test A: color(a)=0, color(b) in {1..k-1}
    # Test C: color(a)=color(b)=0
    def test(assumptions):
        with Minisat22(bootstrap_with=cnf.clauses) as s:
            return s.solve(assumptions=assumptions)
    A = test([V(a, 0)] + [-V(b, 0)])   # a=0, b != 0
    if a == b:
        # self pair — degenerate
        return "self"
    C = test([V(a, 0), V(b, 0)])       # a=0, b=0
    if A and C:
        return "free"
    if not A and C:
        return "forced_same"
    if A and not C:
        return "forced_different"
    return "unsat_baseline"


if __name__ == "__main__":
    main()
