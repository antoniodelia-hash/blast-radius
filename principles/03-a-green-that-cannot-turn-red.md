# 03 — A green light that cannot turn red is not a status

> The scheduler wrote *completed successfully*. The script had failed.
> Both statements were true, and only one of them mattered.

## What happened

Scheduled jobs in this runtime can run in two shapes: as a bare script,
or as a script whose output is handed to the agent for a follow-up turn.

In the second shape, a script failure never marks the job. The error text
arrives in the agent's prompt as `## Script Error`, the agent reads it,
writes a sensible summary about it, and the turn closes cleanly. The
scheduler records the turn, and the turn succeeded. `last_status: ok`.

The truth survived in exactly one place: the last file under the job's
output directory. Nothing read that file.

A second failure sat one floor up, in the same shape. Notification calls
were wrapped so that a failure printed to the log and execution continued
with exit 0. With delivery configured as local and stdout redirected into
a log file, a broken messaging token produced a job marked ok, a report
that reached nobody, and a sentinel that stayed quiet because the sentinel
was reading `last_status`.

## What it cost

Six scheduled jobs ran mute for roughly two months before anyone noticed.
No money moved, and that is the reason it lasted: a failure with no
invoice attached has nothing to make it visible except a status field,
and the status field said ok.

## The control

A read-only sentinel across every deployment, shipped here as
`controls/job_guard.py`. It reports:
malformed script field, missing script file, last-status error, vanished
profile, unreadable job list.

Three design choices carry the weight:

- **It declares what it examined.** Profiles and jobs, counted, on every
  run. Zero jobs examined exits 2 and calls itself invalid.
- **The scheduled sentinel exits 0 even when it finds anomalies**, and puts
  them on stdout: a cron job that exits non-zero starts reporting on
  itself, and the report is the point. The control shipped here does the
  opposite and exits 1 on findings, because you run it by hand or from CI
  and there the exit code is the answer. Same logic, two callers, two
  conventions — stated because the mismatch would otherwise read as a bug.
- **It reads the artifact, not the summary.** The status field is the
  thing that lied, so the sentinel goes to the output file.

## Verifying the control is alive

**Two layers, and this repository ships one of them.** The production
sentinel reads a live runtime: it resolves job definitions, validates the
script field against a whitelist, checks that the file exists, and notices
a profile that has vanished. Those checks need the runtime to exist, so
they belong to a collector that has no meaning on your machine.

`controls/job_guard.py` is the other layer: pure verdict logic over a
declared observation. It decides six things — a status contradicted by its
own output, a status with no output to check it against, a run that
reached nobody, a job that stopped running, a status outside the set it
understands, and a status the collector never brought back — and it
decides them from a JSON file you can write by hand.

The last two were added on 2026-09-11, after an outside review found this
control doing the thing this card is about. It read three words: ok, error,
failed. A job reporting timeout, crashed or skipped, or reporting nothing
at all, came out of it clean — a green that could not turn red, inside the
check written against greens that cannot turn red. The set it understands
is now declared at the top of the file, and a word outside it is reported.

- `job_guard.py --fixture` seeds all six, plus two healthy jobs that must
  stay silent, one of which prints alerts for a living. It exits 86, the
  code that means the fixture found the fault it planted.
- The clock comes from the observation file rather than the wall clock, so
  a verdict is reproducible a year later.
- In production the sentinel reported 11 jobs across 5 deployments and 12
  anomalies. The number to watch is the first one: if jobs examined ever
  reads 0, the check has stopped being a check.

## OWASP mapping

**No direct ASI mapping.**

The 2026 Agentic list is a threat taxonomy: hijacked goals, misused
tools, poisoned memory, rogue agents. It does account for failures with
nobody behind them — ASI10 is described as "autonomous misalignment that
emerges without active attacker control" (p.9) — and that entry tracks an
*agent* that drifts out of its mandate. Here the agent did its job
correctly, and the status field around it reported something untrue.
None of the ten entries fits that without stretching.

ASI08 (Cascading Failures) comes closest in spirit, since it argues for
"resilient logging and non-repudiation mechanisms that prevent silent
propagation" (p.30). ASI08 applies to a fault that spreads across agents;
this one sat still, in one place, for two months.

Stating the gap is part of the point. Production failures do not arrive
pre-sorted into a threat taxonomy, and a repository that forces every
scar into a code would be less useful than one that admits where the map
runs out.
