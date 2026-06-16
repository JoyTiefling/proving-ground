# proving-ground

An open lab notebook of attempts at unsolved problems — mostly combinatorics, number theory, extremal constructions.

This is **not** a collection of results. It is a record of *attempts*, including the ones that hit a wall. The walls are kept on purpose: "here is exactly where the search stalls" is itself data.

## The one rule

**No claim without a runnable gate.**

Every claimed improvement ships with a verifier in [`verifiers/`](verifiers/) that anyone can run to confirm it independently. A construction is only "real" once an external checker accepts it — never because the prose around it sounds convincing. If you see a claimed record here, run the verifier yourself; it takes seconds.

This rule exists because the author's intuition about whether a derivation is *correct* is unreliable. The verifier is the trust anchor, not the argument.

## Method — a ladder

1. Pick a problem with a **cheap, automatic** check (progress = a concrete construction, number, or counterexample — not a proof a human must referee).
2. Write the verifier **first**, and validate it against **known exact values** before trusting it on anything new.
3. Start small, reproduce what is known, then push the frontier one step at a time until it stalls.

## Layout

- [`verifiers/`](verifiers/) — the gates. Each is standalone and self-validating against known values.
- [`log/`](log/) — the notebook. One file per problem: target, current best, dead-ends, tools, dated journal.
- `search/` — attack code (search heuristics, constructions).

## Current work

- **Weak Schur numbers** `WS(k)` — pushing lower bounds. Verifier validated against `WS(1..3)`. See [`log/weak-schur.md`](log/weak-schur.md).

## License

Code (verifiers, search scripts) is under the [MIT License](LICENSE).
Mathematical findings — constructions, bounds, counterexamples — are facts and belong to everyone; use them freely, no attribution required (though a link back is kind).
