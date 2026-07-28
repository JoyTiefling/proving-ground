"""
Probe F -- verify the difference-coloring SEAM for weak Schur.

Classic Schur upper bound: a sum-free k-colouring f of {1..N} induces a
difference-edge-colouring of K_{N+1} on vertices {0..N} (edge {a,b}, a<b -> f(b-a))
that is TRIANGLE-FREE. A mono triangle {a<b<c} gives x=b-a, y=c-b, z=c-a=x+y all
one colour -> a Schur triple.

CLAIM (the seam, to verify): for a WEAKLY sum-free colouring the induced colouring
is triangle-free EXCEPT on arithmetic progressions -- every mono triangle has
x=y (i.e. b-a=c-b), corresponding to an ALLOWED doubling f(d)=f(2d). Non-AP mono
triangles = genuine weak violations = must be ZERO for a valid colouring.

If verified: WS(k)'s factor-k slack over S(k) IS exactly the price of tolerating
these AP-triangles. We measure how many doublings f(d)=f(2d) a real boundary
colouring uses.
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
    ok, reason = verify_weak_schur([sorted(p) for p in parts], N)
    color = {}
    for c, p in enumerate(parts):
        for v in p:
            color[v] = c
    print(f"\n=== {os.path.basename(path)} N={N} valid={ok} {('' if ok else reason)}")

    # enumerate mono triangles in difference-coloring on vertices {0..N}
    # edge {a,b} colour = color[b-a].  triangle {a<b<c}: color[b-a]==color[c-b]==color[c-a]
    mono_ap = 0
    mono_nonap = []
    for a in range(0, N + 1):
        for b in range(a + 1, N + 1):
            x = b - a
            cx = color[x]
            for c in range(b + 1, N + 1):
                y = c - b
                z = c - a
                if color[y] == cx and color[z] == cx:
                    if x == y:
                        mono_ap += 1
                    else:
                        mono_nonap.append((a, b, c, x, y, z, cx))
    # doublings f(d)=f(2d)
    doublings = [d for d in range(1, N // 2 + 1) if color[d] == color[2 * d]]
    print(f"    mono triangles: AP(x=y)={mono_ap}  non-AP={len(mono_nonap)}  "
          f"-> {'SEAM HOLDS (all mono triangles are APs)' if not mono_nonap else 'SEAM BROKEN!'}")
    if mono_nonap:
        print(f"    non-AP examples (would be weak violations): {mono_nonap[:5]}")
    print(f"    doublings f(d)=f(2d): {len(doublings)} of {N//2}  "
          f"(d<=20: {[d for d in doublings if d <= 20]})")
    # per-colour doubling counts
    by_c = {}
    for d in doublings:
        by_c[color[d]] = by_c.get(color[d], 0) + 1
    print(f"    doublings per colour: {dict(sorted(by_c.items()))}")


if __name__ == "__main__":
    for t in sys.argv[1:] or ["out/ws4_N66.txt", "out/eject_ws5_N195.txt"]:
        analyze(t)
