"""Контроли силы drup_check: он обязан ОТВЕРГАТЬ, а не только принимать."""
import itertools
from pysat.solvers import Glucose4
from drup_check import check, full_proof

def php(n):  # n+1 голубей, n нор — UNSAT
    v = lambda p, h: p * n + h + 1
    f = [[v(p, h) for h in range(n)] for p in range(n + 1)]
    for h in range(n):
        for a, b in itertools.combinations(range(n + 1), 2):
            f.append([-v(a, h), -v(b, h)])
    return f, (n + 1) * n

def proof_of(f):
    return full_proof(f)

def test_accepts_valid():
    f, nv = php(5); ok, info = check(f, proof_of(f), nv); assert ok, info

def test_rejects_weakened_formula():
    f, nv = php(5); p = proof_of(f)
    for drop in range(len(f)):          # любая клауза PHP несущая ⇒ любой выброс ломает
        ok, _ = check(f[:drop] + f[drop + 1:], p, nv); assert not ok, drop

def test_rejects_gutted_proof():
    f, nv = php(5); p = [l for l in proof_of(f) if not l.startswith("d")]
    ok, _ = check(f, p[-1:], nv); assert not ok   # только финальная лемма

def test_rejects_sat_formula():
    ok, _ = check([[1, 2], [-1, 2]], ["0"], 2); assert not ok

if __name__ == "__main__":
    for t in [test_accepts_valid, test_rejects_weakened_formula, test_rejects_gutted_proof, test_rejects_sat_formula]:
        t(); print("ok", t.__name__)
