"""Parse the WS(5)=196 partition transcribed from Bouzy 2015 PDF p21 (K=5 block),
expand ranges, and VERIFY with the gate. Trust the gate, not the transcription.
'1' was dropped from class A in extraction (K=4 analogue starts '1 2 4 8 ...'); added.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verifiers"))
from weak_schur import verify_weak_schur  # noqa

RAW = {
    0: "1 2 4 8 11 16 22 25 31 45 50 60 63 69 106 135 140 150 155 178 183 196",
    1: "3 5-7 19 21 23 35 51-53 64-66 77-79 137-139 151-153 180-182 193-195",
    2: "9 10 12-15 17 18 20 54-59 61 62 99-105 141-149 184-192",
    3: "24 26-30 32-34 36-44 46-49 98 154 156-177 179",
    4: "67 68 70-76 80-97 107-134 136",
}


def expand(s):
    out = []
    for tok in s.split():
        if "-" in tok:
            a, b = tok.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(tok))
    return out


parts = [sorted(expand(RAW[c])) for c in range(5)]
N = 196
allv = sorted(v for p in parts for v in p)
print("sizes:", [len(p) for p in parts], "total:", len(allv))
print("covers 1..196:", allv == list(range(1, 197)))
# duplicates / gaps
from collections import Counter
cnt = Counter(v for p in parts for v in p)
dups = [v for v, c in cnt.items() if c > 1]
missing = [v for v in range(1, 197) if v not in cnt]
print("dups:", dups, "missing:", missing)

ok, reason = verify_weak_schur(parts, N)
print("GATE:", "PASS" if ok else f"FAIL {reason}")
if ok and allv == list(range(1, 197)):
    with open("out/eliahou_ws5_N196.txt", "w") as f:
        for c, p in enumerate(parts):
            f.write(f"part {c}: " + " ".join(map(str, p)) + "\n")
    print("*** VALID WS(5)=196 — saved out/eliahou_ws5_N196.txt ***")
