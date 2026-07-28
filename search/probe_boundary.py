"""
Probe E -- boundary mapping / rigidity of a known maximal colouring.

Take a valid k-colouring of {1..N} at (or near) the boundary and feel out the
walls of the solution: which elements are FORCED (no valid recolouring) vs free,
how tight each class is, and -- crucially -- the colour distribution of the
top matching M_{N+1} = {(a, N+1-a)}.

Reduction we test:  {1..N} extends to N+1  <=>  some colour avoids EVERY pair of
M_{N+1}.  So a maximal colouring must have ALL k colours "pair-hit". Verified on
the KNOWN boundary WS(4)=66 first (CL-01), then applied to the 195 frontier.

forced backbone = the invariant Sanya asked for; #free elements gauges how lonely
the boundary solutions are (-> whether enumerating ALL of them, hence a focused
exhaustive proof, is on the table).
"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa


def load(path):
    parts = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            nums = line.split(":", 1)[1].split()
            parts.append([int(x) for x in nums])
    N = max(max(p) for p in parts if p)
    return parts, N


def wsf_ok_add(cls, v):
    """Does adding v to weakly-sum-free set cls keep it weakly sum-free?"""
    for a in cls:
        if a != v:
            if a < v and (v - a) in cls and (v - a) != a:   # a + (v-a) = v
                return False
            if (v + a) in cls:                               # v + a present
                return False
    return True


def analyze(path, verbose=True):
    parts, N = load(path)
    k = len(parts)
    color = {}
    for c, p in enumerate(parts):
        for v in p:
            color[v] = c
    sets = [set(p) for p in parts]

    ok, reason = verify_weak_schur([sorted(s) for s in sets], N)
    print(f"\n=== {os.path.basename(path)}  N={N} k={k}  valid={ok} {('' if ok else reason)}", flush=True)
    print(f"    class sizes: {[len(s) for s in sets]}", flush=True)
    if not ok:
        return

    # --- rigidity (degree 0): alternative colours per element ---
    forced, free = [], []
    alt_hist = [0] * (k + 1)
    for v in range(1, N + 1):
        c0 = color[v]
        alts = 0
        for c in range(k):
            if c == c0:
                continue
            if wsf_ok_add(sets[c], v):
                alts += 1
        alt_hist[alts] += 1
        (forced if alts == 0 else free).append(v)
    print(f"    rigidity(deg0): forced={len(forced)} free={len(free)}  "
          f"alt-count hist[0..k]={alt_hist}", flush=True)

    # --- top matching M_{N+1}: which colours are pair-hit ---
    target = N + 1
    pair_hit = [False] * k
    mono_pairs = []
    for a in range(1, target // 2 + 1):
        b = target - a
        if a < b and b <= N:
            if color[a] == color[b]:
                pair_hit[color[a]] = True
                mono_pairs.append((a, b, color[a]))
    free_colors = [c for c in range(k) if not pair_hit[c]]
    print(f"    M_{target}: pair_hit per colour={pair_hit}  "
          f"-> {'ALL hit => does NOT extend (maximal)' if not free_colors else f'colours {free_colors} pair-FREE => MIGHT extend!'}",
          flush=True)
    if verbose:
        print(f"    mono pairs summing to {target}: {len(mono_pairs)} "
              f"(e.g. {mono_pairs[:6]})", flush=True)

    # --- can N+1 actually be placed in some colour (degree-0 extension)? ---
    extendable = [c for c in range(k) if wsf_ok_add(sets[c], target)]
    print(f"    place {target} directly: colours that accept it = {extendable} "
          f"-> {'EXTENDS (!!) ' if extendable else 'no direct extension'}", flush=True)

    # --- forced backbone preview ---
    if forced:
        bb = sorted(forced)[:25]
        print(f"    forced backbone (first 25): {bb}", flush=True)


if __name__ == "__main__":
    targets = sys.argv[1:] or ["out/ws4_N66.txt", "out/eject_ws5_N195.txt"]
    for t in targets:
        analyze(t)
