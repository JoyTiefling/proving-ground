"""
Brainstorm probe #3 -- re-coordinatize by 2-adic chains.

Linear order {1,2,3,...} makes the weak-Schur record APERIODIC (no formula). But the
trouble (doublings) lives on chains m, 2m, 4m, 8m... Re-index every number as
(odd part m, exponent e), number = m * 2^e. Look at colour as a function of (m,e).

Bet: structure aperiodic in linear order may be PERIODIC/simple in chain coords.
  - per chain (fixed odd m): the colour sequence along e=0,1,2,...  How many chains
    are monochromatic ("pure doubling chains") vs how many change colour?
  - is colour mostly a function of the odd part m?  of m mod something?
  - compare strong S(5)=160 vs weak 196 in these coords.
"""
import sys, os


def load(path):
    parts = []
    with open(path) as f:
        for line in f:
            if ":" in line:
                parts.append([int(x) for x in line.split(":", 1)[1].split()])
    N = max(max(p) for p in parts if p)
    color = {}
    for c, p in enumerate(parts):
        for v in p:
            color[v] = c
    return color, N


def oddpart(v):
    e = 0
    while v % 2 == 0:
        v //= 2; e += 1
    return v, e


def analyze(path):
    color, N = load(path)
    print(f"\n=== {os.path.basename(path)}  N={N}")
    # group by odd part
    chains = {}
    for v in range(1, N + 1):
        m, e = oddpart(v)
        chains.setdefault(m, {})[e] = (v, color[v])
    pure = 0
    changing = 0
    for m in sorted(chains):
        seq = [chains[m][e][1] for e in sorted(chains[m])]
        if len(set(seq)) == 1:
            pure += 1
        else:
            changing += 1
    print(f"    chains: {len(chains)} total, pure(mono)={pure}, changing={changing}")
    # show colour sequence for small odd parts
    print("    odd m -> colour along chain (e=0,1,2,...):")
    for m in sorted(chains)[:24]:
        seq = "".join(str(chains[m][e][1]) for e in sorted(chains[m]))
        print(f"      m={m:3d}: {seq}")
    # is colour a function of odd part alone? (colour of e=0 element vs whole chain)
    func_of_m = sum(1 for m in chains if len(set(chains[m][e][1] for e in chains[m])) == 1)
    print(f"    chains where colour depends ONLY on odd part: {func_of_m}/{len(chains)}")
    # colour of the odd numbers themselves (e=0) vs m mod small moduli
    for mod in (3, 4, 5, 7, 8):
        groups = {}
        for m in chains:
            if 0 in chains[m]:
                groups.setdefault(m % mod, set()).add(chains[m][0][1])
        det = sum(1 for r in groups if len(groups[r]) == 1)
        print(f"    odd-part colour(e=0) vs m mod {mod}: {det}/{len(groups)} residues map to a single colour")


if __name__ == "__main__":
    for t in sys.argv[1:] or ["out/eliahou_ws5_N196.txt", "out/sattail_ws5_N160.txt"]:
        analyze(t)
