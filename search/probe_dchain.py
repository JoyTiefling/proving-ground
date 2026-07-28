"""
2b groundwork: are a colour's doublings confined to FEW 2-adic chains?

Doubling d (f(d)=f(2d)=c) is an edge inside the chain of odd-part(d). Chains are
short (<=log2 N). So  |D| <= (#chains carrying doublings) * log2 N.  For |D| bounded
we need: per colour, doublings live on O(1) chains. Measure s_c = #distinct chains
carrying colour c's doublings. If small -> lemma supported -> a real |D| bound
(prunes route-B cube space). If large -> chain route to 2b is dead.
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
    return color, N, len(parts)


def oddpart(v):
    while v % 2 == 0:
        v //= 2
    return v


def analyze(path):
    color, N, k = load(path)
    D = [d for d in range(1, N // 2 + 1) if color[d] == color[2 * d]]
    print(f"\n=== {os.path.basename(path)} N={N} |D|={len(D)} log2N={N.bit_length()-1}")
    by_color = {}
    for d in D:
        c = color[d]
        by_color.setdefault(c, []).append(d)
    total_chains = set()
    for c in sorted(by_color):
        ds = sorted(by_color[c])
        chains = sorted(set(oddpart(d) for d in ds))
        total_chains.update(chains)
        print(f"    colour {c}: {len(ds)} doublings on {len(chains)} chains (odd parts {chains}); d={ds}")
    s_sum = sum(len(set(oddpart(d) for d in by_color[c])) for c in by_color)
    print(f"    SUM s_c (chains-with-doublings, counted per colour) = {s_sum}")
    print(f"    distinct chains carrying ANY doubling = {len(total_chains)}: {sorted(total_chains)}")
    print(f"    => |D|={len(D)} vs bound (chains x log2N) = {len(total_chains)}x{N.bit_length()-1}={len(total_chains)*(N.bit_length()-1)}")


if __name__ == "__main__":
    for t in sys.argv[1:] or ["out/eliahou_ws5_N196.txt", "out/eject_ws5_N195.txt",
                              "out/sattail_ws5_N160.txt", "out/ws4_N66.txt"]:
        analyze(t)
