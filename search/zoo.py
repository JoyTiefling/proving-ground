"""
"Until ideas run out, even absurd" — a zoo of exotic deterministic coloring
rules. Each maps n -> color in 0..4 by some structural feature; we measure the
weakly-sum-free reach via the gate. Most will be terrible; the point is to
exhaust the space and SEE if any raw exotic structure surprises (reach >100).
Substitution-aperiodic (Thue-Morse/Rudin-Shapiro) is genuinely different from
Beatty/Sturmian aperiodicity, so it is the most interesting bet here.
"""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa

PHI = (1 + math.sqrt(5)) / 2


def popcount(n):
    return bin(n).count("1")


def zeck_len(n):
    fibs = [1, 2]
    while fibs[-1] < n:
        fibs.append(fibs[-1] + fibs[-2])
    cnt = 0
    for f in reversed(fibs):
        if f <= n:
            n -= f
            cnt += 1
    return cnt


def rudin_shapiro(n):
    # parity of number of "11" pairs in binary
    b = bin(n)[2:]
    return sum(1 for i in range(len(b) - 1) if b[i] == "1" and b[i + 1] == "1") % 2


RULES = {
    "popcount%5": lambda n: popcount(n) % 5,
    "zeck_len%5": lambda n: zeck_len(n) % 5,
    "fib_band%5": lambda n: int(math.log(n) / math.log(PHI)) % 5,
    "log2_band%5": lambda n: n.bit_length() % 5,
    "thue_morse+pc": lambda n: (popcount(n) % 2) * 2 + (rudin_shapiro(n)) + (n % 1),
    "rudin_shapiro_mix": lambda n: (rudin_shapiro(n) * 3 + popcount(n)) % 5,
    "digitsum5%5": lambda n: sum(int(d) for d in str(n)) % 5,
    "mult_mod11": lambda n: (pow(n % 11, 1, 11)) % 5,
    "n2_mod5": lambda n: (n * n) % 5,
    "trailing_zeros%5": lambda n: ((n & -n).bit_length() - 1) % 5,
    "floor_sqrt%5": lambda n: int(math.isqrt(n)) % 5,
}


def reach_rule(rule, k=5, Nmax=300):
    parts = [set() for _ in range(k)]
    for n in range(1, Nmax + 1):
        c = rule(n) % k
        a = 1
        ok = True
        while 2 * a < n:
            if a in parts[c] and (n - a) in parts[c]:
                ok = False
                break
            a += 1
        if not ok:
            return n - 1
        parts[c].add(n)
    return Nmax


def greedy_topdown(k=5, Nmax=200):
    """Color from N down to 1, first-fit. Different basin than bottom-up."""
    for N in range(Nmax, 0, -1):
        parts = [set() for _ in range(k)]
        ok_all = True
        for n in range(N, 0, -1):
            placed = False
            for c in range(k):
                bad = False
                a = 1
                while 2 * a < n:
                    if a in parts[c] and (n - a) in parts[c]:
                        bad = True
                        break
                    a += 1
                # also n as addend: n+x in part and x in part
                if not bad:
                    for x in parts[c]:
                        if (n + x) in parts[c]:
                            bad = True
                            break
                if not bad:
                    parts[c].add(n)
                    placed = True
                    break
            if not placed:
                ok_all = False
                break
        if ok_all:
            return N
    return 0


if __name__ == "__main__":
    print("Exotic coloring zoo (record 196, irregular-search best 195):\n")
    results = []
    for name, rule in RULES.items():
        try:
            r = reach_rule(rule)
        except Exception as e:
            r = -1
        results.append((r, name))
        flag = "  <<< SURPRISE" if r > 100 else ""
        print(f"  {name:22s}: reach {r}{flag}")
    print(f"\n  best exotic rule: {max(results)}")
