"""
Probe I -- test the self-similar recursion behind the upper bound (gap 2 groundwork).

Difference-colouring is translation-invariant, so the Schur step on vertex 0 gives:
largest colour class U has |U| >= N/k, and within U the induced difference-colouring
{a,b}->f(b-a) uses the OTHER k-1 colours (f(b-a) != colour(U) for a<b in U, b!=2a),
and is again "triangle-free except AP". The recursion feeds on itself.

We verify on real colourings:
  (1) recursion inequality N <= k*|U_max| (measure slack)
  (2) within each class U: differences b-a (b!=2a) AVOID U's own colour  [validity => 0 viol]
  (3) induced difference-colouring on U is triangle-free except AP (non-AP mono tri = 0)
  (4) doublings realised as in-U differences -- governed by the SAME global D? (per-level C)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa


def load(path):
    parts = []
    with open(path) as f:
        for line in f:
            if ":" in line:
                parts.append([int(x) for x in line.split(":", 1)[1].split()])
    N = max(max(p) for p in parts if p)
    return parts, N


def analyze(path):
    parts, N = load(path)
    k = len(parts)
    color = {}
    for c, p in enumerate(parts):
        for v in p:
            color[v] = c
    ok, _ = verify_weak_schur([sorted(p) for p in parts], N)
    sizes = [len(p) for p in parts]
    cstar = sizes.index(max(sizes))
    U = sorted(parts[cstar])
    print(f"\n=== {os.path.basename(path)} N={N} k={k} valid={ok}")
    print(f"    sizes={sizes}  largest class c*={cstar} |U|={len(U)}")
    print(f"    (1) recursion N <= k*|U_max|:  {N} <= {k*len(U)}  {'OK' if N<=k*len(U) else 'FAIL'}  (N/k={N/k:.1f})")

    # (2) within-U differences avoid own colour (except doublings b=2a)
    viol_own = 0
    diff_colors = [0] * k
    Uset = set(U)
    for i in range(len(U)):
        for j in range(i + 1, len(U)):
            a, b = U[i], U[j]
            d = b - a
            cc = color[d]
            diff_colors[cc] += 1
            if cc == cstar and b != 2 * a:
                viol_own += 1
    print(f"    (2) within-U diffs (b!=2a) using own colour c*: {viol_own}  (expect 0)")
    print(f"        within-U difference colour histogram: {diff_colors}  (c*={cstar} should be ~0)")

    # (3) induced difference-colouring on U: mono triangles AP vs non-AP
    ap = nonap = 0
    for ia in range(len(U)):
        for ib in range(ia + 1, len(U)):
            a, b = U[ia], U[ib]
            x = b - a
            cx = color[x]
            for ic in range(ib + 1, len(U)):
                cc = U[ic]
                y = cc - b
                z = cc - a
                if color[y] == cx and color[z] == cx:
                    if x == y:
                        ap += 1
                    else:
                        nonap += 1
    print(f"    (3) induced diff-colouring on U: mono-triangles AP={ap} non-AP={nonap}  "
          f"-> {'self-similar (AP only)' if nonap == 0 else 'BROKEN'}")

    # (4) global doublings vs those realised as in-U differences
    Dglob = [d for d in range(1, N // 2 + 1) if color.get(2 * d) == color.get(d)]
    diffs_in_U = set(U[j] - U[i] for i in range(len(U)) for j in range(i + 1, len(U)))
    D_in_U = [d for d in Dglob if d in diffs_in_U]
    print(f"    (4) |D_global|={len(Dglob)}  |D realised as in-U diff|={len(D_in_U)}  "
          f"(per-level correction <= global C)")


if __name__ == "__main__":
    for t in sys.argv[1:] or ["out/eliahou_ws5_N196.txt", "out/eject_ws5_N195.txt"]:
        analyze(t)
