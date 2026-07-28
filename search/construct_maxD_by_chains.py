"""
CONSTRUCTIVE lower bound on max |D| for valid WSF k-colorings of [1..N].

Complements sat_maxD.py: while SAT climbs D>=D_min from below and stalls
at N=100 (>55h CPU on D>=45 as of 20-07-2026 wake 18:00), this tool tries
to hit the trivial ceiling |D| = floor(N/2) directly.

Structural observation (wake 18:00 20-07, mine): doubling chains
    chain(m) = {m, 2m, 4m, 8m, ...} intersect [1..N]     (m odd)
are FREE of internal weak-Schur triples. Proof: a strict WSF triple
inside a chain would need 2^i * m + 2^j * m = 2^k * m with i<j (strict).
That forces 2^i + 2^j = 2^k, which has no strict-i-j solution — only
i=j gives 2^{i+1}, and weak-Schur requires a<b (strict). So every
chain can be monochromatic without violating WSF ON ITS OWN.

If EVERY chain is monochromatic, |D| = floor(N/2) automatically:
   |D| = sum over chains (chain_length - 1)
       = (total elements) - (number of chains)
       = N - ceil(N/2) = floor(N/2).

What remains: k-color the odd-rooted chains so no cross-chain WSF triple
becomes monochromatic. That is: color the ~ceil(N/2) chain roots so no
triple (chain(a_root), chain(b_root), chain(z_root)) with a+b=z picks
one color three times. This is a hypergraph k-coloring on chains — much
smaller than raw WSF on [1..N], and typically feasible.

Method: enumerate all forbidden monochromatic chain-triples, greedy
DPLL backtracking on chain colors (chains ordered by degree in the
triple-graph, dense first). If SAT → dump partition as receipt.

If constructive succeeds for N=100 (SAT couldn't), it proves
max|D| = floor(N/2) is achievable at N=100 — the third data point
after N=50 (25/25) and N=80 (40/40) confirming max|D| = floor(N/2)
holds and the Ramsey reduction "tolerating C AP-families" is
degenerate on WS(5).
"""
import sys, os, time, json, argparse, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa


def odd_root(v: int) -> int:
    """The odd number m such that v = 2^i * m for some i >= 0."""
    while v % 2 == 0:
        v //= 2
    return v


def chains_up_to_N(N: int):
    """Return list of chains (each chain is sorted list) and root->chain_id map.
    Chains are indexed by their odd root; chain_id is the odd root itself."""
    chain_by_root = {}
    for v in range(1, N + 1):
        r = odd_root(v)
        chain_by_root.setdefault(r, []).append(v)
    # sort each chain
    for r in chain_by_root:
        chain_by_root[r].sort()
    return chain_by_root


def forbidden_triples(N: int):
    """All triples (r_a, r_b, r_z) of chain roots such that some a+b=z with
    a<b<z, all in [1..N], and a is in chain(r_a), b in chain(r_b), z in chain(r_z).
    Returned as a set of sorted-3-tuples (deduplicated).

    A monochromatic assignment on chain roots must AVOID any such triple
    being 3-monochromatic (all three roots getting the same color).
    Note: a triple (r,r,r) means the constraint reduces to "chain r must
    NOT be monochromatic" — but chain-monochromatic is our design. If any
    such all-same-root triple exists, the constructive method FAILS
    structurally (means the chain itself has an internal WSF triple).
    We proved above no such internal triple exists for doubling chains
    under STRICT weak-Schur (a<b), so this set should be empty.
    """
    triples = set()
    self_triples = []
    for a in range(1, N + 1):
        for b in range(a + 1, N + 1):
            z = a + b
            if z > N:
                break
            r_a, r_b, r_z = odd_root(a), odd_root(b), odd_root(z)
            key = tuple(sorted([r_a, r_b, r_z]))
            if r_a == r_b == r_z:
                self_triples.append((a, b, z))
                # would forbid the chain being monochromatic — shouldn't happen
            triples.add(key)
    return triples, self_triples


def color_chains(chain_roots, triples, k):
    """DPLL-ish greedy on chain roots. Try to assign each root a color in
    [0..k-1] such that no forbidden triple is 3-monochromatic.

    Order roots by degree in the triple hypergraph (dense first). Uses
    symmetry break: root #0 gets color 0; root #1 gets color in [0..min(1,k-1)].
    """
    # Build root -> incident triples index
    inc = {r: [] for r in chain_roots}
    for tri in triples:
        for r in set(tri):
            inc[r].append(tri)

    # Order roots by degree desc
    ordered = sorted(chain_roots, key=lambda r: -len(inc[r]))

    color = {}
    # Symmetry break
    order_idx = {r: i for i, r in enumerate(ordered)}

    def is_bad(new_root, new_color, color_map):
        """Check if assigning new_root=new_color creates any monochromatic
        forbidden triple among ALREADY-assigned roots (plus new_root)."""
        for tri in inc[new_root]:
            # Collect colors of the three roots (with duplicates)
            colors = []
            for r in tri:
                if r == new_root:
                    colors.append(new_color)
                elif r in color_map:
                    colors.append(color_map[r])
                else:
                    colors.append(None)
            # Bad iff all three are the same and non-None
            if all(c == new_color for c in colors):
                return True
        return False

    def try_assign(i):
        if i == len(ordered):
            return True
        r = ordered[i]
        # Symmetry break: first root always color 0. Second root: color <= 1.
        max_c = k - 1
        if i == 0:
            candidates = [0]
        elif i == 1:
            candidates = list(range(min(2, k)))
        else:
            candidates = list(range(k))
        for c in candidates:
            if is_bad(r, c, color):
                continue
            color[r] = c
            if try_assign(i + 1):
                return True
            del color[r]
        return False

    ok = try_assign(0)
    return (color if ok else None), ordered


def build_partition_from_chain_colors(N: int, chain_by_root, color_by_root, k):
    """Expand chain colors to a full [1..N] partition (list of k lists)."""
    parts = [[] for _ in range(k)]
    for r, chain in chain_by_root.items():
        c = color_by_root[r]
        for v in chain:
            parts[c].append(v)
    for p in parts:
        p.sort()
    return parts


def _cli():
    ap = argparse.ArgumentParser(
        description="Constructive max-|D| via monochromatic doubling chains.")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--N", type=int, default=100)
    ap.add_argument("--out", type=str, default=None,
                    help="If given, dump JSON receipt on success.")
    args = ap.parse_args()
    k, N = args.k, args.N

    t0 = time.time()
    chain_by_root = chains_up_to_N(N)
    chain_roots = sorted(chain_by_root.keys())
    triples, self_triples = forbidden_triples(N)

    print(f"CONSTRUCT max-|D|: N={N} k={k}")
    print(f"  chains: {len(chain_roots)}  (roots = odd numbers in [1..{N}])")
    print(f"  forbidden chain-triples (deduped): {len(triples)}")
    if self_triples:
        print(f"  self-triples in same chain (BAD, shouldn't exist): "
              f"{len(self_triples)}; first: {self_triples[:3]}")
        # The method fails structurally.
        return

    color_by_root, order = color_chains(chain_roots, triples, k)
    elapsed = time.time() - t0

    if color_by_root is None:
        print(f"  FAIL: no valid k-coloring of chain hypergraph found "
              f"({elapsed:.2f}s). |D| < floor(N/2) at k={k}.")
        return

    parts = build_partition_from_chain_colors(N, chain_by_root, color_by_root, k)
    ok, reason = verify_weak_schur(parts, N)
    if not ok:
        print(f"  GATE FAIL: {reason}")
        return

    # Recount D-set from partition (independent of construction claim)
    color_of = {}
    for c, p in enumerate(parts):
        for v in p:
            color_of[v] = c
    D_set = [d for d in range(1, N // 2 + 1)
             if color_of.get(d) is not None
             and color_of.get(d) == color_of.get(2 * d)]
    trivial_ceiling = N // 2

    print(f"  best |D| = {len(D_set)}  (trivial ceiling = floor(N/2) = "
          f"{trivial_ceiling})")
    print(f"  ratio |D| / (N/2) = {len(D_set) / trivial_ceiling:.3f}")
    print(f"  WSF gate: PASS")
    print(f"  D_set (first 20): {D_set[:20]}")
    print(f"  elapsed: {elapsed:.2f}s")

    if args.out:
        receipt = {
            "meta": {
                "method": "constructive (monochromatic doubling chains + "
                          "hypergraph k-coloring on chain roots)",
                "N": N, "k": k,
                "chains": len(chain_roots),
                "forbidden_chain_triples": len(triples),
                "elapsed_s_total": round(elapsed, 3),
                "wake": datetime.datetime.now(datetime.timezone.utc)
                    .isoformat(timespec="seconds").replace("+00:00", "Z"),
                "tool": "construct_maxD_by_chains.py",
                "tool_version": "20-07-2026 wake 18:00",
                "trivial_ceiling_N_over_2": trivial_ceiling,
            },
            "result": {
                "best_D": len(D_set),
                "gate": "PASS",
                "D_set": D_set,
                "partition": parts,
                "chain_colors": {str(r): c for r, c in color_by_root.items()},
            },
        }
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2, ensure_ascii=False)
        print(f"  receipt -> {args.out}")


if __name__ == "__main__":
    _cli()
