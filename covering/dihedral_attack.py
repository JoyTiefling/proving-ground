"""
Dihedral structural attack on C(15,6,3) target=30.

After 2*Z_15 ruled out (cyclic_attack.py), try D_15 = <r, s | r^15=s^2=e, srs=r^-1>
acting on Z_15 by r: x->x+1 and s: x->-x (mod 15). |D_15| = 30.

A single base block B with trivial D_15-stabilizer has orbit of exactly 30 blocks
under D_15 — precisely the target size. Cleanest possible structural attack.

Strategy:
1. Enumerate all 5005 base blocks B in C(15,6).
2. Filter by D_15-stabilizer = trivial (orbit size 30).
3. For each, generate the 30 D_15-orbit blocks and run verify_covering.
4. Report first hit (or none) and write to file.
"""
from itertools import combinations
from verify import verify_covering

V = 15
K = 6
T = 3

def d15_orbit_blocks(B):
    """Return set of all D_15 translates of B (rotations and reflections)."""
    out = set()
    s = sorted(B)
    for g in range(V):
        # rotation
        out.add(tuple(sorted((x + g) % V for x in s)))
        # rotation + reflection
        out.add(tuple(sorted((-x + g) % V for x in s)))
    return out

def d15_stabilizer_size(B):
    bs = frozenset(B)
    cnt = 0
    for g in range(V):
        if frozenset((x + g) % V for x in bs) == bs:
            cnt += 1
        if frozenset((-x + g) % V for x in bs) == bs:
            cnt += 1
    return cnt

def canon_block_d15(B):
    """Smallest representative under D_15."""
    best = None
    s = sorted(B)
    for g in range(V):
        cand = tuple(sorted((x + g) % V for x in s))
        if best is None or cand < best:
            best = cand
        cand = tuple(sorted((-x + g) % V for x in s))
        if cand < best:
            best = cand
    return best

print(f"enumerating C({V},{K})...")
all_blocks = list(combinations(range(V), K))
print(f"  total = {len(all_blocks)}")

# dedup by D_15 canonical
canon = {}
for B in all_blocks:
    c = canon_block_d15(B)
    if c not in canon:
        canon[c] = (B, d15_stabilizer_size(B))
print(f"  D_15 canonical reps: {len(canon)}")

# keep only stab=1 → orbit size 30
candidates = [B for (B, stab) in canon.values() if stab == 1]
small = [(B, stab) for (B, stab) in canon.values() if stab > 1]
print(f"  full D_15 orbit (stab=1): {len(candidates)}")
print(f"  smaller orbits:           {len(small)}  (sizes: {sorted(set(s for _, s in small))})")

# attack
print(f"\nsearching {len(candidates)} candidates with full D_15 orbit...")
found = []
for i, B in enumerate(candidates):
    blocks = d15_orbit_blocks(B)
    if len(blocks) != 30:
        continue  # safety
    ok, miss, ex = verify_covering(blocks, V, T)
    if ok:
        found.append((B, sorted(blocks)))
        print(f"  HIT  base={B}  -> 30 blocks COVERING")
        if len(found) >= 3:
            break

print(f"\nfound {len(found)} valid D_15 coverings of size 30")

if found:
    import os
    os.makedirs("out", exist_ok=True)
    out_path = "out/dihedral_C_15_6_3_target_30.txt"
    with open(out_path, "w") as f:
        f.write(f"# C({V},{K},{T}) — DIHEDRAL covering of size 30 (Schönheim L=30, prev best_known=31)\n")
        f.write(f"# construction: orbit of single base block under D_{V} = <rot,refl>\n")
        f.write(f"# found {len(found)} solutions\n\n")
        for k, (B, blocks) in enumerate(found):
            f.write(f"## Solution {k+1}\n")
            f.write(f"base_block = {list(B)}\n")
            f.write(f"D_{V} orbit, |orbit| = {len(blocks)}\n")
            f.write(f"blocks:\n")
            for b in blocks:
                f.write(f"  {list(b)}\n")
            f.write("\n")
    print(f"WROTE: {out_path}")
else:
    print("NO single-base D_15 covering of size 30 exists.")
    print("Next: mixed (1 cyclic + supplements), or 2-base D_15 with smaller stab, or non-structural.")
