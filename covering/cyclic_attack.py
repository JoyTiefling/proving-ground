"""
Cyclic structural attack on C(v,k,3) — search for covering of form
m * Z_v: union of orbits of m base blocks under the cyclic shift group Z_v.

For C(15,6,3) target=30: m=2, so we seek two base blocks B1, B2 ⊂ Z_15
of size 6 whose 15 cyclic shifts together cover all C(15,3) triples.

Strategy:
1. Enumerate all B in C(15,6) (5005 blocks).
2. For each B, compute the bitset of triple-orbits it intersects.
3. Pair-search: find (B1, B2) with bitset_or == ALL_ORBITS.
4. Verify each candidate with the gate (verify_covering on the 30 blocks).

Orbits of triples under Z_15: 31 total (30 of size 15, 1 of size 5 — the
arithmetic progressions {a, a+5, a+10}). Index them by canonical form
(rotate so the smallest element is 0).
"""
from itertools import combinations
from verify import verify_covering, schonheim

V = 15
K = 6
T = 3
M = 2  # 2 * Z_15 = 30 blocks

# ----- orbit indexing -----

def canon_triple(triple):
    """Canonical representative of a triple under Z_v shift.
    Rotate so min element is 0, return sorted tuple."""
    best = None
    s = sorted(triple)
    for shift in range(V):
        cand = tuple(sorted((x - shift) % V for x in s))
        if best is None or cand < best:
            best = cand
    return best

# enumerate orbits
all_triples = list(combinations(range(V), T))
orbit_id = {}
canonicals = []
for tri in all_triples:
    c = canon_triple(tri)
    if c not in orbit_id:
        orbit_id[c] = len(canonicals)
        canonicals.append(c)
N_ORBITS = len(canonicals)
ALL_MASK = (1 << N_ORBITS) - 1

print(f"orbits of C({V},{T}) under Z_{V}: {N_ORBITS}")
assert N_ORBITS == 31, f"expected 31, got {N_ORBITS}"

# orbit bitset for each block
def block_orbit_mask(B):
    m = 0
    for tri in combinations(sorted(B), T):
        m |= 1 << orbit_id[canon_triple(tri)]
    return m

# stabilizer size (to detect blocks whose orbit < V)
def stabilizer_size(B):
    s = frozenset(B)
    cnt = 0
    for g in range(V):
        if frozenset((x + g) % V for x in s) == s:
            cnt += 1
    return cnt

# canonical block (smallest representative under Z_V) — dedup B and B+g
def canon_block(B):
    s = sorted(B)
    best = None
    for shift in range(V):
        cand = tuple(sorted((x - shift) % V for x in s))
        if best is None or cand < best:
            best = cand
    return best

# ----- enumerate base block candidates -----

print(f"enumerating C({V},{K}) blocks...")
all_blocks = list(combinations(range(V), K))
print(f"  total = {len(all_blocks)}")

# dedup by canonical form, keep only blocks with FULL orbit (stab=1) for clean 30-block construction
# we still allow blocks with smaller orbit but track them separately
canon_blocks = {}
for B in all_blocks:
    c = canon_block(B)
    if c not in canon_blocks:
        canon_blocks[c] = (B, stabilizer_size(B))

full_orbit = [B for (B, stab) in canon_blocks.values() if stab == 1]
small_orbit = [(B, stab) for (B, stab) in canon_blocks.values() if stab > 1]
print(f"  canonical (orbit reps): {len(canon_blocks)}")
print(f"  full-orbit (stab=1):    {len(full_orbit)}")
print(f"  small-orbit:            {len(small_orbit)}  (sizes: {sorted(set(s for _, s in small_orbit))})")

# ----- precompute orbit masks -----

print("computing orbit-bitset per block...")
masks_full = [(B, block_orbit_mask(B)) for B in full_orbit]
print(f"  done ({len(masks_full)} masks)")

# ----- pair search -----

print(f"\nsearching {len(masks_full)} x {len(masks_full)} pairs (full-orbit only, B1<=B2)...")
found = []
checked = 0
for i, (B1, m1) in enumerate(masks_full):
    for j in range(i, len(masks_full)):
        B2, m2 = masks_full[j]
        if (m1 | m2) == ALL_MASK:
            # candidate — verify
            blocks = set()
            for g in range(V):
                blocks.add(tuple(sorted((x + g) % V for x in B1)))
                blocks.add(tuple(sorted((x + g) % V for x in B2)))
            if len(blocks) != 2 * V:
                continue  # shouldn't happen for stab=1 distinct orbits, but be safe
            ok, miss, ex = verify_covering(blocks, V, T)
            if ok:
                found.append((B1, B2, sorted(blocks)))
                print(f"  HIT  B1={B1}  B2={B2}  blocks={len(blocks)}")
                if len(found) >= 5:
                    break
        checked += 1
    if len(found) >= 5:
        break

print(f"\nchecked {checked} pairs, found {len(found)} valid 30-block coverings")

# ----- also try base+small_orbit (covers via < 30 cyclic blocks, padded with extra) -----
# skip for now: pure 2*Z_15 is the cleanest claim. if not found, escalate.

# ----- write result -----

if found:
    out_path = "out/cyclic_C_15_6_3_target_30.txt"
    with open(out_path, "w") as f:
        f.write(f"# C({V},{K},{T}) — cyclic covering of size {M}*{V}={M*V} (Schönheim L={schonheim(V,K,T)})\n")
        f.write(f"# best_known on LJCR: 31; this attempt: {M*V}\n")
        f.write(f"# found {len(found)} valid solutions; showing all\n\n")
        for k, (B1, B2, blocks) in enumerate(found):
            f.write(f"## Solution {k+1}\n")
            f.write(f"base_block_1 = {list(B1)}\n")
            f.write(f"base_block_2 = {list(B2)}\n")
            f.write(f"construction: orbits of B1 and B2 under Z_{V} shift\n")
            f.write(f"blocks ({len(blocks)}):\n")
            for b in blocks:
                f.write(f"  {list(b)}\n")
            f.write("\n")
    print(f"\nWROTE: {out_path}")
else:
    print("\nNO 2*Z_15 covering exists. Need to escalate: try 2-base with one small-orbit, or 3*Z_15-padded, or non-cyclic structure.")
