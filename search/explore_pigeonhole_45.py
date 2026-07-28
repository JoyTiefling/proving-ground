"""
PIGEONHOLE EXPLORER for chain 45 in N=90, k=5 WSF construction.

Context (wake 22:00 22-07-2026):
  - N=90, k=5 constructive UNSAT (191s DPLL). Provable: no coloring of all
    45 chain roots avoids monochromatic forbidden triples.
  - Delta 89→90 adds 19 new triples ALL with chain 45. Chain 45 has 79
    partner-triples at N=90 (deg 60 at N=89 + 19 new).
  - Baseline N=89 partition (out/n89k5_baseline.json) has chain 45 → color 4.
  - Manual check on baseline: all 5 colors give >=1 mono-triple containing 45.
  - Question: is this an INVARIANT across diverse valid [1..44 chains]
    colorings, or a peculiarity of baseline?

Method:
  1. Take triples for N=90. Split T = T_44 (no root 45) ∪ T_45 (has root 45).
  2. Find many valid colorings of the 44 non-45 roots for T_44 (which is
     itself easier than full — some SAT).
  3. For each: for each of 5 colors c, count mono-triples in T_45 induced
     by assigning color(45)=c. Record distribution.
  4. Diversity via order variation (multiple root orderings for DPLL).

Pre-registration (before running):
  - UNSAT of full N=90 implies: for EVERY valid [1..44], for EVERY color c,
    count[c] >= 1. So H_no_escape and H_full_sat are tautologically
    excluded — logging them is a sanity check on our code.
  - Real hypotheses about STRUCTURE:
    * H_uniform (0.5): count[c] distribution ~symmetric across c, avg
      count ~= (79 / 5) ≈ 16 per color; pigeonhole via sheer volume.
    * H_asymm_baseline (0.3): the baseline result "color 4 gives 1 mono,
      others give 3-5" generalizes — one color is uniquely tight (1 mono)
      and others more relaxed; distribution shape stable across colorings.
    * H_asymm_shifts (0.15): distribution shape stable per-coloring but
      the "tight color" shifts — color 4 tightness is baseline-specific.
    * H_sensitive (0.05): distributions vary wildly, no coherent pattern.

Ceilings: we cap search at MAX_SOLUTIONS colorings and MAX_ORDERS orderings.
Do not run past that in one wake — hardware-wall risk.
"""
import sys, os, time, json, argparse, random, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa


def odd_root(v: int) -> int:
    while v % 2 == 0:
        v //= 2
    return v


def chains_up_to_N(N: int):
    chain_by_root = {}
    for v in range(1, N + 1):
        r = odd_root(v)
        chain_by_root.setdefault(r, []).append(v)
    for r in chain_by_root:
        chain_by_root[r].sort()
    return chain_by_root


def forbidden_triples(N: int):
    triples = set()
    for a in range(1, N + 1):
        for b in range(a + 1, N + 1):
            z = a + b
            if z > N:
                break
            r_a, r_b, r_z = odd_root(a), odd_root(b), odd_root(z)
            key = tuple(sorted([r_a, r_b, r_z]))
            triples.add(key)
    return triples


def split_triples_by_root(triples, target_root):
    T_target = set()
    T_other = set()
    for tri in triples:
        if target_root in tri:
            T_target.add(tri)
        else:
            T_other.add(tri)
    return T_target, T_other


def find_valid_colorings(chain_roots, triples_no_target, k,
                         max_solutions=20, candidate_perm=None, rng=None):
    """DPLL enumerator returning up to max_solutions valid colorings of
    chain_roots avoiding mono-triples in triples_no_target.

    Root order: ALWAYS degree-desc (deep speed matters more than diversity
    in ordering — chain-hypergraph on 44 roots is manageable). Diversity
    via CANDIDATE PERMUTATION (order in which colors are tried at each root)
    and symmetry break (root[0]->0, root[1]<=1) to strip permutation-equiv.
    """
    inc = {r: [] for r in chain_roots}
    for tri in triples_no_target:
        for r in set(tri):
            if r in inc:
                inc[r].append(tri)

    ordered = sorted(chain_roots, key=lambda r: (-len(inc[r]), r))

    if candidate_perm is None:
        candidate_perm = list(range(k))

    solutions = []
    color = {}

    def is_bad(new_root, new_color):
        for tri in inc[new_root]:
            all_match = True
            for r in tri:
                cv = new_color if r == new_root else color.get(r)
                if cv != new_color:
                    all_match = False
                    break
            if all_match:
                return True
        return False

    def try_assign(i):
        if len(solutions) >= max_solutions:
            return
        if i == len(ordered):
            solutions.append(dict(color))
            return
        r = ordered[i]
        # Symmetry break: first root always color 0; second root in {0,1}.
        if i == 0:
            candidates = [0]
        elif i == 1:
            candidates = [c for c in candidate_perm if c in (0, 1)]
        else:
            candidates = list(candidate_perm)
        for c in candidates:
            if is_bad(r, c):
                continue
            color[r] = c
            try_assign(i + 1)
            del color[r]
            if len(solutions) >= max_solutions:
                return

    try_assign(0)
    return solutions, ordered


def count_mono_for_color(target_root, target_color, T_target, coloring):
    """Given coloring of all roots except target_root, and target_root
    assigned target_color, how many triples in T_target become mono?"""
    n_mono = 0
    conflict_triples = []
    for tri in T_target:
        colors = []
        for r in tri:
            if r == target_root:
                colors.append(target_color)
            else:
                colors.append(coloring.get(r))
        if all(c == target_color for c in colors):
            n_mono += 1
            conflict_triples.append(tri)
    return n_mono, conflict_triples


def coloring_fingerprint(coloring):
    """Stable hash of a coloring (root->color dict), invariant to iteration
    order but SENSITIVE to color labels (so symmetric-under-perm colorings
    look different — that's fine; we want to see them)."""
    items = sorted(coloring.items())
    s = ",".join(f"{r}:{c}" for r, c in items)
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def _cli():
    ap = argparse.ArgumentParser(
        description="Pigeonhole explorer for chain 45 at N=90 k=5.")
    ap.add_argument("--N", type=int, default=90)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--target", type=int, default=45,
                    help="Target chain root to analyze (default 45).")
    ap.add_argument("--n-orders", type=int, default=8,
                    help="Number of DPLL root-orderings to try.")
    ap.add_argument("--max-per-order", type=int, default=5,
                    help="Max solutions per ordering.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    N, k, target = args.N, args.k, args.target

    print(f"PIGEONHOLE EXPLORE: N={N} k={k} target_root={target}")

    t0 = time.time()
    chain_by_root = chains_up_to_N(N)
    all_roots = sorted(chain_by_root.keys())
    if target not in all_roots:
        print(f"  ERR: target root {target} not a chain root in [1..{N}].")
        return

    other_roots = [r for r in all_roots if r != target]
    triples = forbidden_triples(N)
    T_target, T_other = split_triples_by_root(triples, target)
    print(f"  chains: {len(all_roots)}  ({len(other_roots)} non-target)")
    print(f"  triples total: {len(triples)}")
    print(f"  triples containing target={target}: {len(T_target)}")
    print(f"  triples without target: {len(T_other)}")

    # Compute degree of target root in T_target for later scoring
    target_partners_pair = {}  # (r_a, r_b) sorted -> count of triples with
                               # target and this pair (usually 1)
    for tri in T_target:
        rest = [r for r in tri if r != target]
        if len(rest) == 2:
            k_pair = tuple(sorted(rest))
        elif len(rest) == 1:
            # triple has target twice — (r_a, target, target)
            k_pair = (rest[0], target)
        else:
            # (target, target, target) — impossible for doubling chains
            k_pair = (target, target)
        target_partners_pair[k_pair] = target_partners_pair.get(k_pair, 0) + 1

    print(f"  distinct partner-pairs: {len(target_partners_pair)}")

    # === Find many diverse colorings of other_roots ===
    all_solutions = []
    seen = set()
    # Diverse via candidate permutations. Identity first (fastest through
    # sym-break); then a few reshuffles of colors 2..k-1 (0 and 1 fixed
    # by sym-break so those can't rotate meaningfully).
    perms_tried = []
    perms_tried.append(tuple(range(k)))
    for _ in range(args.n_orders - 1):
        tail = list(range(2, k))
        rng.shuffle(tail)
        perms_tried.append((0, 1, *tail))
    # deduplicate perms
    perms_tried = list(dict.fromkeys(perms_tried))
    for order_idx, perm in enumerate(perms_tried):
        sols, _ = find_valid_colorings(
            other_roots, T_other, k,
            max_solutions=args.max_per_order,
            candidate_perm=list(perm),
            rng=rng,
        )
        for s in sols:
            fp = coloring_fingerprint(s)
            if fp in seen:
                continue
            seen.add(fp)
            all_solutions.append((fp, s))
        elapsed_step = time.time() - t0
        print(f"  perm#{order_idx} {perm}: found {len(sols)} sols "
              f"(total unique={len(all_solutions)}, t={elapsed_step:.1f}s)")
        if elapsed_step > 120:
            print(f"  time cap 120s hit, stopping enumeration.")
            break

    if not all_solutions:
        print("  ERR: no valid coloring of 44 chains found — logic error.")
        return

    print(f"\n=== DISTRIBUTION over {len(all_solutions)} diverse colorings ===")
    distributions = []
    per_color_agg = {c: [] for c in range(k)}
    escape_found = False
    escape_witness = None
    for fp, sol in all_solutions:
        row = {}
        for c in range(k):
            n_mono, _ = count_mono_for_color(target, c, T_target, sol)
            row[c] = n_mono
            per_color_agg[c].append(n_mono)
            if n_mono == 0:
                escape_found = True
                escape_witness = (fp, c, dict(sol))
        distributions.append((fp, row))

    # Show distribution stats
    for c in range(k):
        vals = per_color_agg[c]
        vmin = min(vals) if vals else -1
        vmax = max(vals) if vals else -1
        vavg = sum(vals) / len(vals) if vals else 0
        zeros = sum(1 for v in vals if v == 0)
        print(f"  color {c}: min={vmin} max={vmax} avg={vavg:.2f} zeros={zeros}/{len(vals)}")

    # Per-coloring "tight color" (color with min count)
    tight_shifts = {}
    for fp, row in distributions:
        tight_c = min(row, key=lambda c: row[c])
        tight_shifts[tight_c] = tight_shifts.get(tight_c, 0) + 1
    print(f"\n  tight-color counter: {tight_shifts}")

    # Which partner-pairs catch the tight color per coloring?
    # For each coloring: find the tight color, list the triples in T_target
    # that go mono at that color. Sorted-partner-pair as key.
    tight_pair_hits = {}  # sorted_pair (r_a, r_b) -> count of colorings hit
    tight_witness_details = []  # (fp, tight_c, list of partner-pairs)
    for fp, sol in all_solutions:
        # find tight color for this coloring
        best_c, best_n = None, None
        for c in range(k):
            n_mono, _ = count_mono_for_color(target, c, T_target, sol)
            if best_n is None or n_mono < best_n:
                best_c, best_n = c, n_mono
        # collect the partner-pairs at that tight color
        _, conflict = count_mono_for_color(target, best_c, T_target, sol)
        pairs_here = []
        for tri in conflict:
            rest = tuple(sorted(r for r in tri if r != target))
            pairs_here.append(rest)
            tight_pair_hits[rest] = tight_pair_hits.get(rest, 0) + 1
        tight_witness_details.append((fp, best_c, best_n, pairs_here))
    print(f"\n  distinct tight-catching partner-pairs: {len(tight_pair_hits)}")
    top_pairs = sorted(tight_pair_hits.items(), key=lambda x: -x[1])[:10]
    print(f"  top-10 partner-pairs by tight-catch frequency:")
    for pair, n in top_pairs:
        print(f"    {pair} caught {n}/{len(all_solutions)} colorings")

    # HYPOTHESIS CHECK: if partner-pair (r_a, r_b) catches tight in 100%,
    # does color(r_a) == color(r_b) in EVERY coloring?
    if top_pairs and top_pairs[0][1] == len(all_solutions):
        pair = top_pairs[0][0]
        r_a, r_b = pair
        same_color = 0
        diff_color = 0
        for fp, sol in all_solutions:
            if sol.get(r_a) == sol.get(r_b):
                same_color += 1
            else:
                diff_color += 1
        print(f"\n  FORCED-PAIR CHECK for {pair}: "
              f"color({r_a})=color({r_b}) in {same_color}/{len(all_solutions)}, "
              f"diff in {diff_color}/{len(all_solutions)}")
        if same_color == len(all_solutions):
            print(f"    → hypothesis LIVE: pair {pair} forced-same-color under T_44.")
        elif diff_color > 0:
            print(f"    → pair NOT forced-same; tight-catch means both hit target=45's color regardless.")

    # H_no_escape sanity
    if escape_found:
        print(f"\n  ⚠️ ESCAPE FOUND: fp={escape_witness[0]} color={escape_witness[1]}")
        print(f"     This CONTRADICTS N=90 k=5 UNSAT. LOGIC BUG somewhere.")
    else:
        print(f"\n  no escape (H_no_escape confirmed — sanity OK, matches UNSAT).")

    elapsed = time.time() - t0
    print(f"\n  total elapsed: {elapsed:.2f}s")

    if args.out:
        receipt = {
            "meta": {
                "method": "pigeonhole explore over diverse T_44 colorings",
                "N": N, "k": k, "target_root": target,
                "n_orderings_tried": args.n_orders,
                "max_per_order": args.max_per_order,
                "seed": args.seed,
                "elapsed_s_total": round(elapsed, 3),
                "tool": "explore_pigeonhole_45.py",
                "tool_version": "23-07-2026 wake 00:00",
                "chains": len(all_roots),
                "triples_total": len(triples),
                "triples_containing_target": len(T_target),
                "triples_without_target": len(T_other),
                "distinct_partner_pairs": len(target_partners_pair),
            },
            "result": {
                "n_diverse_colorings": len(all_solutions),
                "distribution_per_color": {
                    str(c): {
                        "min": min(per_color_agg[c]) if per_color_agg[c] else None,
                        "max": max(per_color_agg[c]) if per_color_agg[c] else None,
                        "avg": (sum(per_color_agg[c]) / len(per_color_agg[c])) if per_color_agg[c] else None,
                        "zeros": sum(1 for v in per_color_agg[c] if v == 0),
                    } for c in range(k)
                },
                "tight_color_counter": tight_shifts,
                "escape_found": escape_found,
                "sample_rows": distributions[:10],  # first 10
            },
        }
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2, ensure_ascii=False, default=str)
        print(f"  receipt -> {args.out}")


if __name__ == "__main__":
    _cli()
