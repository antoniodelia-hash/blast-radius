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

`cron_guard.py`, read-only, across every profile. It reports:
malformed script field, missing script file, last-status error, vanished
profile, unreadable job list.

Three design choices carry the weight:

- **It declares what it examined.** Profiles and jobs, counted, on every
  run. Zero jobs examined exits 2 and calls itself invalid.
- **It exits 0 even when it finds anomalies**, and puts them on stdout.
  A scheduled check that fails loudly starts reporting on itself.
- **It reads the artifact, not the summary.** The status field is the
  thing that lied, so the sentinel goes to the output file.

## Verifying the control is alive

- `controls/job_guard.py --fixture` seeds a job whose status says ok and
  whose output holds a script error, a job that has not produced output
  in weeks, and a healthy job that must stay silent. It exits non-zero on
  purpose.
- The test battery runs nine cases in the real shape — absolute paths,
  traversal attempts, a non-string script field — because a fixture built
  from tidy data proves the parser handles tidy data.
- In production the sentinel reported 11 jobs across 5 profiles and 12
  anomalies. The number to watch is the first one: if jobs examined ever
  reads 0, the check has stopped being a check.

## OWASP mapping

**No direct ASI mapping.**

The 2026 Agentic list is organised around adversaries: hijacked goals,
misused tools, poisoned memory, rogue agents. A monitoring surface that
cannot express failure has no attacker in it, so none of the ten entries
fits without stretching.

ASI08 (Cascading Failures) comes closest in spirit, since it argues for
"resilient logging and non-repudiation mechanisms that prevent silent
propagation" — but ASI08 is explicitly about a fault spreading across
agents, and this fault did the opposite: it sat still, in one place, for
two months.

Stating the gap is part of the point. Production failures do not arrive
pre-sorted into a threat taxonomy, and a repository that forces every
scar into a code would be less useful than one that admits where the map
runs out.
