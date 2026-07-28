"""
Search heuristics for min percolating set in Q_d under r-neighbor bootstrap.

Verifier contract: whenever a "new best" is claimed, `verify.percolates` must
say True. No exceptions.

Heuristics implemented:
  A. Greedy seed builder — start empty, add the vertex maximizing final-infected
     after percolation until we percolate.
  B. Random + repair — random size-k set; if it doesn't percolate, greedily
     add vertices until it does; use as upper bound for m.
  C. Destruction-reconstruction LS — from a known percolating set S of size m,
     drop k random vertices and try to re-percolate with fewer additions.
     If final size < m, we improved.

Not implemented here: brute force. That lives in `verify.py`'s sanity funcs
and is only viable up to d≈5 for k≤7 or so.

Persistence: `best_known.json` — {"d=5,r=4": {"size": ..., "witness": [...]}}
Every improvement is recorded (append-only via write-verify-log dance).
"""

from __future__ import annotations

import json
import os
import random
from itertools import combinations
from pathlib import Path
from typing import Iterable

from verify import neighbors, percolates

BEST_FILE = Path(__file__).parent / "best_known.json"


# ---------- percolation shell (reused from verify) ----------

def infected_after_percolation(seed: Iterable[int], d: int, r: int) -> set[int]:
    """Return the full infected set after percolation stabilizes (may be < V)."""
    infected = set(seed)
    N = 1 << d
    while True:
        new = set()
        for v in range(N):
            if v in infected:
                continue
            cnt = sum(1 for u in neighbors(v, d) if u in infected)
            if cnt >= r:
                new.add(v)
        if not new:
            return infected
        infected |= new


# ---------- A. Greedy seed builder ----------

def greedy_seed(d: int, r: int, rng: random.Random | None = None) -> set[int]:
    """Build a percolating set greedily.

    At each step, pick the vertex v (not yet in seed) whose addition maximizes
    the size of the final infected set after percolation. Ties broken randomly
    (so different rng seeds explore different local optima).
    """
    if rng is None:
        rng = random.Random()
    N = 1 << d
    seed: set[int] = set()

    while True:
        # If current seed already percolates, done.
        cur_inf = infected_after_percolation(seed, d, r)
        if len(cur_inf) == N:
            return seed

        # Score each candidate by "how much of Q_d does it infect if added?"
        best_score = -1
        best_choices: list[int] = []
        for v in range(N):
            if v in seed:
                continue
            inf = infected_after_percolation(seed | {v}, d, r)
            s = len(inf)
            if s > best_score:
                best_score = s
                best_choices = [v]
            elif s == best_score:
                best_choices.append(v)
        # tie-break random for exploration
        pick = rng.choice(best_choices)
        seed.add(pick)


# ---------- B. Random + repair ----------

def repair_to_percolating(base: set[int], d: int, r: int,
                          rng: random.Random | None = None) -> set[int]:
    """Greedily extend `base` until it percolates. Returns superset that does.

    Additions minimize the same objective as greedy_seed.
    """
    if rng is None:
        rng = random.Random()
    N = 1 << d
    seed = set(base)
    while True:
        cur_inf = infected_after_percolation(seed, d, r)
        if len(cur_inf) == N:
            return seed
        best_score = -1
        best_choices: list[int] = []
        for v in range(N):
            if v in seed:
                continue
            inf = infected_after_percolation(seed | {v}, d, r)
            s = len(inf)
            if s > best_score:
                best_score = s
                best_choices = [v]
            elif s == best_score:
                best_choices.append(v)
        seed.add(rng.choice(best_choices))


def random_plus_repair(d: int, r: int, k: int, trials: int,
                       rng: random.Random | None = None) -> set[int] | None:
    """Sample `trials` random size-k sets; repair each; return best (smallest).

    Random start with small k is a NON-percolating seed almost always; repair
    then closes it. This is greedy-with-random-warmup, useful for escaping the
    all-empty local optimum.
    """
    if rng is None:
        rng = random.Random()
    N = 1 << d
    best: set[int] | None = None
    for _ in range(trials):
        start = set(rng.sample(range(N), k))
        repaired = repair_to_percolating(start, d, r, rng)
        if best is None or len(repaired) < len(best):
            best = repaired
    return best


# ---------- C. Destruction-reconstruction LS ----------

def destruction_reconstruction(S: set[int], d: int, r: int, k_drop: int,
                               attempts: int,
                               rng: random.Random | None = None) -> set[int]:
    """Given percolating S, try to find a smaller percolating S'.

    For each of `attempts` iterations:
      pick a random subset of size k_drop from S → remove →
      repair back to percolating.
      If result is smaller than current best, keep.
    """
    if rng is None:
        rng = random.Random()
    assert percolates(frozenset(S), d, r), "starting S must percolate"
    best = set(S)
    for _ in range(attempts):
        if len(best) <= k_drop + 1:
            # Nothing to drop and expect improvement.
            break
        drop = set(rng.sample(list(best), k_drop))
        residual = best - drop
        repaired = repair_to_percolating(residual, d, r, rng)
        if len(repaired) < len(best):
            # Sanity: verify (defensive — should always be true by construction).
            assert percolates(frozenset(repaired), d, r)
            best = repaired
    return best


# ---------- verifier contract + persistence ----------

def load_best() -> dict:
    if BEST_FILE.exists():
        return json.loads(BEST_FILE.read_text(encoding="utf-8"))
    return {}


def save_best(data: dict) -> None:
    BEST_FILE.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def record_if_better(d: int, r: int, S: set[int]) -> tuple[bool, dict]:
    """Store S as new best for (d, r) if smaller than existing.

    Verifies via `percolates` before storing. Returns (was_improvement, entry).
    """
    assert percolates(frozenset(S), d, r), \
        f"REFUSED: claimed percolating set of size {len(S)} does not percolate"
    key = f"d={d},r={r}"
    data = load_best()
    cur = data.get(key)
    if cur is not None and cur["size"] <= len(S):
        return False, cur
    entry = {"size": len(S), "witness": sorted(S)}
    data[key] = entry
    save_best(data)
    return True, entry


# ---------- driver for d=5, r=4 ----------

def search_d5_r4(seconds_budget: float = 25.0, seed: int = 0) -> dict:
    """Run all three heuristics against d=5 r=4 and record the best.

    seconds_budget is soft; we use it to size the number of random restarts.
    seed makes runs reproducible.
    """
    import time
    rng = random.Random(seed)
    d, r = 5, 4

    log = []

    # A. one greedy pass
    t0 = time.perf_counter()
    S_greedy = greedy_seed(d, r, rng)
    t_greedy = time.perf_counter() - t0
    log.append({"stage": "greedy", "size": len(S_greedy), "time_s": round(t_greedy, 3)})
    improved, entry = record_if_better(d, r, S_greedy)
    log.append({"stage": "record_greedy", "improved": improved, "current_best": entry["size"]})

    # B. random + repair — sample around greedy's size
    k_start = max(1, len(S_greedy) // 2)
    t0 = time.perf_counter()
    trials_budget = 40  # cheap in Q_5
    S_rr = random_plus_repair(d, r, k_start, trials_budget, rng)
    t_rr = time.perf_counter() - t0
    log.append({"stage": "random_repair", "k_start": k_start,
                "trials": trials_budget, "best_size": len(S_rr) if S_rr else None,
                "time_s": round(t_rr, 3)})
    if S_rr:
        improved, entry = record_if_better(d, r, S_rr)
        log.append({"stage": "record_random_repair", "improved": improved,
                    "current_best": entry["size"]})

    # C. destruction-reconstruction on current best
    data = load_best()
    cur_best = set(data[f"d={d},r={r}"]["witness"])
    t0 = time.perf_counter()
    S_ls = destruction_reconstruction(cur_best, d, r, k_drop=2, attempts=200, rng=rng)
    t_ls = time.perf_counter() - t0
    log.append({"stage": "ls_kdrop2", "attempts": 200,
                "result_size": len(S_ls), "time_s": round(t_ls, 3)})
    improved, entry = record_if_better(d, r, S_ls)
    log.append({"stage": "record_ls", "improved": improved,
                "current_best": entry["size"]})

    # LS second pass with bigger k_drop
    cur_best = set(load_best()[f"d={d},r={r}"]["witness"])
    t0 = time.perf_counter()
    S_ls2 = destruction_reconstruction(cur_best, d, r, k_drop=3, attempts=200, rng=rng)
    t_ls2 = time.perf_counter() - t0
    log.append({"stage": "ls_kdrop3", "attempts": 200,
                "result_size": len(S_ls2), "time_s": round(t_ls2, 3)})
    improved, entry = record_if_better(d, r, S_ls2)
    log.append({"stage": "record_ls2", "improved": improved,
                "current_best": entry["size"]})

    return {"log": log, "best": load_best()[f"d={d},r={r}"]}


def search_general(d: int, r: int, seeds: int = 6,
                   rr_trials: int = 30, ls_attempts: int = 150) -> dict:
    """d-general heuristic upper bound: greedy + random-repair + LS over `seeds`.

    Returns best-known entry after recording. Scales to any d (cost grows with
    N=2^d because each percolation is O(N·d) and greedy does N candidates/step).
    """
    import time
    d_r = (d, r)
    log = []
    t_start = time.perf_counter()
    for sd in range(seeds):
        rng = random.Random(sd)
        # A. greedy
        S = greedy_seed(d, r, rng)
        record_if_better(d, r, S)
        # B. random+repair around half the greedy size
        k_start = max(1, len(S) // 2)
        S_rr = random_plus_repair(d, r, k_start, rr_trials, rng)
        if S_rr:
            record_if_better(d, r, S_rr)
        # C. LS on current best, two k_drop levels
        cur = set(load_best()[f"d={d},r={r}"]["witness"])
        for k_drop in (2, 3):
            S_ls = destruction_reconstruction(cur, d, r, k_drop, ls_attempts, rng)
            record_if_better(d, r, S_ls)
            cur = set(load_best()[f"d={d},r={r}"]["witness"])
        log.append({"seed": sd, "best_so_far": len(cur),
                    "elapsed_s": round(time.perf_counter() - t_start, 1)})
    return {"log": log, "best": load_best()[f"d={d},r={r}"]}


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        d, r = int(sys.argv[1]), int(sys.argv[2])
        seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 6
        result = search_general(d, r, seeds=seeds)
    else:
        result = search_d5_r4()
    print(json.dumps(result, indent=2))
