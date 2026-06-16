"""
Compute-light creativity: mine the STRUCTURE of the small known records to
reverse-engineer the gluing operator T such that record(k) ~ T(record(k-1)).

We have exact optimal constructions for k=2,3,4 (all tiny, fully computable).
Decompose each part into maximal intervals and lay them side by side. If a
transformation (scale + insert a new color band + shift/repair) maps the
(k-1)-record into the k-record, that operator — not blind search — is the road
to k=5 on a weak CPU.

No heavy compute: find_partition is only used for small k (2,3); k=4 is read
from a previously saved construction.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import find_partition, verify_weak_schur  # noqa


def to_intervals(xs):
    xs = sorted(xs)
    out, s, p = [], xs[0], xs[0]
    for x in xs[1:]:
        if x == p + 1:
            p = x
        else:
            out.append((s, p)); s = p = x
    out.append((s, p))
    return out


def load_saved(path):
    parts = []
    with open(path) as f:
        for line in f:
            if ":" in line:
                nums = line.split(":", 1)[1].split()
                parts.append([int(x) for x in nums])
    return parts


def show(k, N, parts):
    ok, reason = verify_weak_schur(parts, N)
    print(f"WS({k}) = {N}   gate={'PASS' if ok else 'FAIL ' + str(reason)}")
    parts = sorted(parts, key=lambda q: min(q))
    for i, p in enumerate(parts):
        iv = to_intervals(p)
        # compact interval print
        s = ", ".join(f"{a}-{b}" if a != b else f"{a}" for a, b in iv)
        print(f"  c{i} (|{len(p)}|, {len(iv)} intervals): {s}")
    # color sequence as run-lengths (structure fingerprint)
    color = {}
    for i, p in enumerate(parts):
        for x in p:
            color[x] = i
    runs = []
    cur, ln = color[1], 1
    for n in range(2, N + 1):
        if color[n] == cur:
            ln += 1
        else:
            runs.append((cur, ln)); cur, ln = color[n], 1
    runs.append((cur, ln))
    print(f"  run pattern ({len(runs)} runs): " +
          " ".join(f"{c}^{l}" for c, l in runs))
    print()


if __name__ == "__main__":
    show(2, 8, find_partition(2, 8))
    show(3, 23, find_partition(3, 23))
    here = os.path.dirname(__file__)
    for cand in ["out/ws4_N66.txt", "out/structured_ws4_N66_runs22.txt"]:
        path = os.path.join(here, cand)
        if os.path.exists(path):
            print(f"[k=4 from {cand}]")
            show(4, 66, load_saved(path))
            break
