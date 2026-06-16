"""
Oblique angle: structured seed + tail-only search (compute-light).

Instead of searching a 196-element coloring blind, fix the bulk by structure
and search only the tail:
  [1..66]   = a known WS(4) 4-coloring (colors 0..3)
  [67..134] = new color 4 as one block (interval (66,134] is weakly sum-free)
  [135..N]  = extend, reusing all 5 colors.

The tail is ~60 elements, not 196 — small enough for a weak CPU. We try both a
greedy tail and a bounded backtracking tail, and report the largest valid N.
Everything is checked by the gate.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa


def load_saved(path):
    parts = []
    with open(path) as f:
        for line in f:
            if ":" in line:
                parts.append([int(x) for x in line.split(":", 1)[1].split()])
    return parts


def build_seed(ws4_parts, block_hi=134):
    """color[n] for 1..block_hi: ws4 colors on 1..66, color 4 on 67..block_hi."""
    color = {}
    for c, part in enumerate(ws4_parts):
        for n in part:
            color[n] = c
    for n in range(67, block_hi + 1):
        color[n] = 4
    return color


def can_place(color, n, c):
    """n joins color c iff no pair (a, n-a), a<n-a, both already in c."""
    a = 1
    while 2 * a < n:
        if color.get(a) == c and color.get(n - a) == c:
            return False
        a += 1
    return True


def greedy_tail(color, k, start, Nmax):
    color = dict(color)
    for n in range(start, Nmax + 1):
        placed = False
        for c in range(k):
            if can_place(color, n, c):
                color[n] = c; placed = True; break
        if not placed:
            return n - 1, color
    return Nmax, color


def backtrack_tail(color, k, start, Nmax, deadline):
    """DFS maximizing reach; returns best N and coloring. Bounded by deadline."""
    color = dict(color)
    best = [start - 1, dict(color)]

    def dfs(n):
        if time.time() > deadline:
            return
        if n > Nmax:
            best[0] = Nmax; best[1] = dict(color); return
        cand = [c for c in range(k) if can_place(color, n, c)]
        if not cand:
            if n - 1 > best[0]:
                best[0] = n - 1; best[1] = dict(color)
            return
        for c in cand:
            color[n] = c
            dfs(n + 1)
            del color[n]
            if best[0] == Nmax or time.time() > deadline:
                return
    dfs(start)
    return best[0], best[1]


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    ws4 = load_saved(os.path.join(here, "out", "ws4_N66.txt"))
    for block_hi in (134, 130, 132, 133):
        seed = build_seed(ws4, block_hi)
        ok, reason = verify_weak_schur(
            [[n for n in seed if seed[n] == c] for c in range(5)], block_hi)
        gN, _ = greedy_tail(seed, 5, block_hi + 1, 260)
        t = time.time()
        bN, bcol = backtrack_tail(seed, 5, block_hi + 1, 260, time.time() + 20)
        print(f"block_hi={block_hi}: seed valid={ok}  greedy_tail->{gN}  "
              f"backtrack_tail->{bN}  ({time.time()-t:.1f}s)")
        if bN >= 196:
            parts = [[n for n in bcol if bcol[n] == c] for c in range(5)]
            okk, rr = verify_weak_schur(parts, bN)
            print(f"   reached N={bN} >=196, gate={'PASS' if okk else 'FAIL ' + str(rr)}")
            if okk and bN > 196:
                outdir = os.path.join(here, "out"); os.makedirs(outdir, exist_ok=True)
                with open(os.path.join(outdir, f"seed_ws5_N{bN}.txt"), "w") as f:
                    for i, p in enumerate(parts):
                        f.write(f"part {i}: {' '.join(map(str, sorted(p)))}\n")
                print(f"   *** N={bN} > 196 CANDIDATE — adversarial re-verify required ***")
