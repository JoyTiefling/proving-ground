#!/usr/bin/env python3
"""rss_probe.py — discriminator for candidate C-001.

Claim under test: minisat22 at a 5M-conflict step budget dies from memory growth
on learnt clauses, NOT from the size of N.

The two hypotheses make different traces:
  memory  -> RSS climbs monotonically through the hard step and the process dies
             near its peak; the N at which it dies is incidental.
  N       -> RSS stays flat/bounded and the death is pinned to a specific N.

So: run the climb in a child process, sample the child's RSS while it runs, and
line the RSS trace up against the ladder progress the child writes to its
.live.json. Then look at where the death sits on each axis.

Usage:
  python rss_probe.py --solver minisat22 --step-budget 5000000 --lo 138
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

import psutil

HERE = pathlib.Path(__file__).resolve().parent


def last_n(live_path: pathlib.Path) -> int | None:
    """Last N the child has recorded. The child rewrites this file each step, so
    a partial read is normal -- treat it as 'no news', not as an error."""
    try:
        data = json.loads(live_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    ladder = data.get("ladder") or []
    return ladder[-1].get("N") if ladder else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solver", default="minisat22")
    ap.add_argument("--step-budget", type=int, default=5_000_000)
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--lo", type=int, default=138)
    ap.add_argument("--hi", type=int, default=160)
    ap.add_argument("--interval", type=float, default=0.25)
    ap.add_argument("--tag", default="rss")
    args = ap.parse_args()

    out = HERE / "out" / f"chain_lift_k{args.k}_{args.solver}_{args.tag}.json"
    trace_path = HERE / "out" / f"rss_trace_k{args.k}_{args.solver}_{args.tag}.jsonl"

    cmd = [
        sys.executable, str(HERE / "chain_lift.py"),
        "--k", str(args.k), "--solver", args.solver,
        "--step-budget", str(args.step_budget),
        "--lo", str(args.lo), "--hi", str(args.hi),
        "--skip-controls", "--out", str(out),
    ]
    print("launching:", " ".join(cmd), flush=True)

    live = out.with_suffix(".live.json")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    ps = psutil.Process(proc.pid)
    t0 = time.time()
    peak = 0.0
    samples = 0

    with trace_path.open("w", encoding="utf-8") as fh:
        while proc.poll() is None:
            try:
                rss = ps.memory_info().rss / 2**20  # MiB
            except psutil.Error:
                break
            peak = max(peak, rss)
            samples += 1
            fh.write(json.dumps({
                "t": round(time.time() - t0, 2),
                "rss_mib": round(rss, 1),
                "N": last_n(live),
            }) + "\n")
            fh.flush()
            time.sleep(args.interval)

        _, err = proc.communicate()

    elapsed = time.time() - t0
    print(f"\nexit={proc.returncode}  elapsed={elapsed:.1f}s  "
          f"samples={samples}  peak_rss={peak:.1f} MiB")
    if err:
        print("stderr tail:", err.decode("utf-8", "replace")[-400:])
    print(f"last N recorded by child: {last_n(live)}")
    print(f"trace: {trace_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
