# `get_proof()` silently returns a truncated proof on Windows (unflushed C `FILE*` buffer)

**Environment:** Windows 10 (10.0.19045), CPython 3.13.5, python-sat 1.9.dev5 and 1.9.dev15 (wheels from PyPI). Not yet tested on Linux/macOS.

**Summary.** With `with_proof=True`, `get_proof()` returns a proof whose tail is missing. The cut happens at a stdio buffer boundary — sometimes mid-line — and the final empty clause `0` is never present. Nothing is raised, so the result looks like a normal proof. Any external checker will (correctly) reject it; a user who doesn't check gets a "certificate" that certifies nothing.

Affected (all solvers with proof support that I could test): Glucose3, Glucose4, Glucose42, Cadical153, Lingeling.

**Repro** (pigeonhole, UNSAT): see attached `pysat_truncated_proof_repro.py`. Output on 1.9.dev15:

```
PHP(5) Glucose4    solve=False lines=   199 last='d 27'               ends_with_empty_clause=False
PHP(7) Glucose3    solve=False lines= 11512 last='-39'                ends_with_empty_clause=False
PHP(7) Glucose4    solve=False lines= 11839 last='-14 27 26 25 19 16' ends_with_empty_clause=False
PHP(7) Glucose42   solve=False lines= 14130 last='55 15 54 10 53'     ends_with_empty_clause=False
PHP(7) Cadical153  solve=False lines= 13112 last='d 18 17 ... -54 0'  (no final empty clause)
PHP(7) Lingeling   solve=False lines= 31101 last='18'
```

(Separately: `Cadical153` on PHP(5) raises `IndexError: list index out of range` inside `get_proof()` — probably the same cause: the proof file is still empty when it is read.)

**Cause (as far as I can tell).** The solver writes the proof through a C `FILE*` obtained from the Python temp file; `get_proof()` reads the file from the Python side while the C-side buffer has not been flushed.

**Evidence.** Forcing a flush of all C streams before reading fixes it for Glucose:

```python
s = Glucose4(bootstrap_with=php(7), with_proof=True); s.solve()
ctypes.cdll.ucrtbase._flushall()      # <- workaround
p = s.get_proof()                     # 11918 lines (was 11839), last line '0'
```

Glucose4, PHP(7): 552 960 bytes without flush (= 135 × 4096 exactly) vs 554 080 with.

**Possibly related: #139** (open since 2023) — "Cadical103 and Cadical153 return an empty proof", cause unknown. An unflushed buffer would explain it: on a small formula the whole proof still sits in the C-side buffer when the file is read, so the file is empty. If that report was made on Linux, the problem is not Windows-only.

**Suggested fix.** `fflush()` the proof `FILE*` on the C side at the end of `solve()` / before `get_proof()` reads the file. A cheap sanity check in `get_proof()` (refutation of an UNSAT call must end with the empty clause) would turn a silent truncation into an error.
