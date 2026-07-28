"""
Patterns BETWEEN rows (scales), not within -- operationalising the multiplicative
symmetry on our 4 valid 196 colourings (Eliahou + 3 new).

(1) Doubling transfer matrix T2[c][c'] = #{x: f(x)=c, f(2x)=c'}. If each row is
    concentrated on ONE c' -> f(2x)=sigma(f(x)) for a fixed permutation sigma ->
    the colouring PROPAGATES up scales by a rule (formula in multiplicative coords!).
(2) Same for c=3 dilation (pure odd-multiplicative direction).
(3) Cross-colouring forced skeleton: which elements share colour across all 4
    (after canonical relabel)? Is that skeleton CLOSED under x->2x / x->3x
    (a multiplicative substructure)?
"""
import sys, os


def load(path):
    parts = []
    with open(path) as f:
        for line in f:
            if ":" in line:
                parts.append([int(x) for x in line.split(":", 1)[1].split()])
    N = max(max(p) for p in parts if p)
    col = {}
    for c, p in enumerate(parts):
        for v in p:
            col[v] = c
    # canonical first-occurrence relabel
    remap, nxt = {}, 0
    canon = {}
    for v in range(1, N + 1):
        if col[v] not in remap:
            remap[col[v]] = nxt; nxt += 1
        canon[v] = remap[col[v]]
    return canon, N


def transfer(col, N, k, mult):
    T = [[0] * k for _ in range(k)]
    for x in range(1, N + 1):
        if mult * x <= N:
            T[col[x]][col[mult * x]] += 1
    return T


def report_T(T, k, label):
    print(f"    {label} transfer matrix (row c -> col c'):")
    permlike = True
    for c in range(k):
        tot = sum(T[c]) or 1
        mx = max(T[c])
        frac = mx / tot
        dom = T[c].index(mx)
        if frac < 0.9:
            permlike = False
        print(f"      c={c}: {T[c]}  dominant -> {dom} ({frac:.0%})")
    print(f"    => {'PERMUTATION-LIKE: f(mx)=sigma(f(x)) RULE!' if permlike else 'spread: no clean rule'}")


if __name__ == "__main__":
    files = ["out/eliahou_ws5_N196.txt", "out/new_ws5_196_1.txt",
             "out/new_ws5_196_2.txt", "out/new_ws5_196_3.txt"]
    cols = []
    for f in files:
        if os.path.exists(f):
            c, N = load(f)
            cols.append((os.path.basename(f), c, N))
    k = 5
    for name, col, N in cols:
        print(f"\n=== {name} ===")
        report_T(transfer(col, N, k, 2), k, "DOUBLING (x2)")
        report_T(transfer(col, N, k, 3), k, "TRIPLING (x3)")

    # cross-colouring forced skeleton
    if len(cols) >= 2:
        N = cols[0][2]
        forced = [v for v in range(1, N + 1)
                  if len(set(c[v] for _, c, _ in cols)) == 1]
        print(f"\n=== cross-colouring ({len(cols)} colourings) ===")
        print(f"    forced (same colour across all): {len(forced)}/{N}")
        closed2 = sum(1 for v in forced if 2 * v <= N and 2 * v in forced)
        cand2 = sum(1 for v in forced if 2 * v <= N)
        closed3 = sum(1 for v in forced if 3 * v <= N and 3 * v in forced)
        cand3 = sum(1 for v in forced if 3 * v <= N)
        print(f"    forced closed under x2: {closed2}/{cand2}   under x3: {closed3}/{cand3}")
        print(f"    forced skeleton (first 40): {sorted(forced)[:40]}")
