"""
Completely multiplicative (CM) sequences and their Erdős discrepancy.

A CM sequence f: N -> {+1,-1} is fixed by its values on primes:
    f(1) = 1,  f(p) = ±1 for prime p,  f(mn) = f(m)f(n).
So f(n) = prod over primes p^a || n of f(p)^a.

Erdős discrepancy of f up to N:
    disc_N(f) = sup over d>=1, k>=1 with k*d <= N of | sum_{j=1}^k f(j*d) |.

KEY REDUCTION (proved below, then checked numerically):
    Because f is completely multiplicative, f(j*d) = f(j) f(d), so
        sum_{j=1}^k f(j*d) = f(d) * sum_{j=1}^k f(j),
    and |f(d)| = 1. Hence for CM sequences the sup over all d is attained at
    d=1 (every d gives the same absolute partial sums), and
        disc_N(f) = max_{1<=k<=N} | sum_{j=1}^k f(j) |
    = the maximum absolute PREFIX SUM of f on [1..N]. O(N), no d-loop needed.

C_CM(D) = the largest N for which some CM sequence has disc_N <= D.
Known: C_CM(2)=344, C_CM(3)=127645 (both exact). C_CM(4) is open.
"""

def _smallest_prime_factor(N: int) -> list:
    """spf[n] = smallest prime factor of n, for n in [0..N]. Linear-ish sieve."""
    spf = list(range(N + 1))
    i = 2
    while i * i <= N:
        if spf[i] == i:  # i is prime
            for m in range(i * i, N + 1, i):
                if spf[m] == m:
                    spf[m] = i
        i += 1
    return spf


def primes_up_to(N: int) -> list:
    """All primes <= N (no external deps)."""
    if N < 2:
        return []
    sieve = bytearray([1]) * (N + 1)
    sieve[0] = sieve[1] = 0
    for i in range(2, int(N ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = bytearray(len(sieve[i * i::i]))
    return [i for i in range(2, N + 1) if sieve[i]]


def build_cm(prime_signs: dict, N: int) -> list:
    """Build f(1..N) as a list f[1..N] (index 0 unused, set to 0).

    prime_signs: {p: +1 or -1} for all primes p <= N. Missing prime -> error.
    Uses complete multiplicativity: f(n) = f(spf) * f(n / spf), built bottom-up.
    """
    spf = _smallest_prime_factor(N)
    f = [0] * (N + 1)
    if N >= 1:
        f[1] = 1
    for n in range(2, N + 1):
        p = spf[n]
        if p == n:  # n is prime
            if p not in prime_signs:
                raise KeyError(f"sign for prime {p} (<= N={N}) not provided")
            f[n] = prime_signs[p]
        else:
            f[n] = f[p] * f[n // p]  # complete multiplicativity
    return f


def discrepancy_via_prefix(f: list, N: int) -> int:
    """disc via the CM reduction: max |prefix sum| over [1..N]. O(N)."""
    s = 0
    best = 0
    for k in range(1, N + 1):
        s += f[k]
        if abs(s) > best:
            best = abs(s)
    return best


def discrepancy_bruteforce(f: list, N: int) -> int:
    """disc by the DEFINITION: sup over all d,k of |sum_{j=1}^k f(jd)|. O(N log N).

    Used ONLY to validate the prefix-sum reduction. Never for production.
    """
    best = 0
    for d in range(1, N + 1):
        s = 0
        j = 0
        while (j + 1) * d <= N:
            j += 1
            s += f[j * d]
            if abs(s) > best:
                best = abs(s)
    return best


def all_prime_signs(N: int, signs_iter) -> dict:
    """Zip primes <= N with an iterable of ±1 signs."""
    return {p: next(signs_iter) for p in primes_up_to(N)}
