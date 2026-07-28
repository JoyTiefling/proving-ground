"""
Probe: |D| у Eliahou-196 restriction к [1..N] для N ∈ {80, 100, 120, 130, 140, 150, 160, 180}.

Зачем: element-priority greedy строит partial |D|=65 при cover 101/150,
но valid full не даёт; SAT нижняя max|D|(valid) ≥ 36. Шов — valid-cover
constraint стоит ~29 пар. Вопрос: сколько пар БЫВАЕТ в РЕАЛЬНОЙ valid
coloring? Eliahou-196 — единственная известная construct. Ограничение
к [1..N] должно оставаться valid (WSF sum-free monotonically).

Мерим: (a) partition valid? (b) |D_N| = |{d ∈ [1..N/2]: f(d)=f(2d)}|.

Curves для N ∈ {80..180} показывают: linear? log? saturates?
Против SAT lower ≥36 при N=150, и нашего greedy partial=65.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).parent
ELIAHOU_FILE = ROOT / "out" / "eliahou_ws5_N196.txt"


def load_partition(path: Path) -> list[set[int]]:
    parts: list[set[int]] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or not line.startswith("part"):
            continue
        _, rhs = line.split(":", 1)
        nums = [int(x) for x in rhs.split()]
        parts.append(set(nums))
    return parts


def color_of(x: int, parts: list[set[int]]) -> int:
    for i, s in enumerate(parts):
        if x in s:
            return i
    return -1


def restrict(parts: list[set[int]], N: int) -> list[set[int]]:
    return [{x for x in s if 1 <= x <= N} for s in parts]


def is_wsf(parts: list[set[int]], N: int) -> tuple[bool, str]:
    """WSF (weak Schur-free): no monochromatic x+y=z with x<y (x=y allowed → doubling not forbidden)."""
    # Weak Schur: within one color, no x+y=z with x<y in same color.
    # (Strong Schur forbids x=y case too; weak allows x+x=2x.)
    seen_color: dict[int, int] = {}
    for i, s in enumerate(parts):
        for x in s:
            if not (1 <= x <= N):
                return False, f"num {x} out of [1..{N}] in part {i}"
            if x in seen_color:
                return False, f"num {x} in parts {seen_color[x]} and {i}"
            seen_color[x] = i
    covered = sorted(seen_color)
    # Every integer 1..N must be covered
    missing = [n for n in range(1, N + 1) if n not in seen_color]
    if missing:
        return False, f"missing: {missing[:20]}{'...' if len(missing) > 20 else ''}"
    # Check weak Schur inside each color
    for i, s in enumerate(parts):
        arr = sorted(s)
        arr_set = s
        for a_i, x in enumerate(arr):
            for y in arr[a_i + 1:]:  # x < y strict
                z = x + y
                if z in arr_set:
                    return False, f"monochromatic weak Schur triple x={x}<y={y}, z={z} in color {i}"
        # NOTE: x=y (i.e., 2x = z) НЕ считается запретом в weak-Schur.
    return True, "valid"


def count_D(parts: list[set[int]], N: int) -> tuple[int, list[int]]:
    """|D_N| = |{d ∈ [1..N/2]: f(d) = f(2d)}|, где f — цвет."""
    D = []
    for d in range(1, N // 2 + 1):
        two_d = 2 * d
        if two_d > N:
            break
        cd = color_of(d, parts)
        c2d = color_of(two_d, parts)
        if cd == -1 or c2d == -1:
            continue
        if cd == c2d:
            D.append(d)
    return len(D), D


def per_color_D(parts: list[set[int]], N: int) -> list[int]:
    """|D| разложение по цветам — какой цвет несёт удвоения."""
    counts = [0] * len(parts)
    for d in range(1, N // 2 + 1):
        two_d = 2 * d
        if two_d > N:
            break
        cd = color_of(d, parts)
        c2d = color_of(two_d, parts)
        if cd == c2d and cd != -1:
            counts[cd] += 1
    return counts


def main():
    parts_full = load_partition(ELIAHOU_FILE)
    print(f"Loaded {len(parts_full)} parts, sizes: {[len(s) for s in parts_full]}, total={sum(len(s) for s in parts_full)}")
    ok, msg = is_wsf(parts_full, 196)
    print(f"Full [1..196] WSF-valid: {ok} ({msg})")
    D_full, _ = count_D(parts_full, 196)
    print(f"|D_196| = {D_full}   (expected ~13 per state)")
    print()
    print(f"{'N':>4} {'valid':>6} {'|D|':>5}  per-color-D")
    print("-" * 60)
    for N in [80, 100, 120, 130, 140, 150, 160, 180, 190, 196]:
        pr = restrict(parts_full, N)
        ok, msg = is_wsf(pr, N)
        D, _ = count_D(pr, N)
        pc = per_color_D(pr, N)
        flag = "OK" if ok else "BAD"
        print(f"{N:>4} {flag:>6} {D:>5}  {pc}   {'' if ok else msg}")


if __name__ == "__main__":
    main()
