# 05 — Whoever writes the data does not write the rules

> The write gate lived in the scripts. The database was a file, and the
> agent had a shell.

## What happened

Operational data sits in a database. Every script that writes to it passes
through a permission gate: scope checks, role checks, refusals with their
own exit code.

The agent also has a shell. A direct SQL statement reaches the same file
and meets none of that. The gate guarded the front door of a building with
open windows, and the agent had no need to be malicious to climb through
one: writing SQL is a reasonable way to solve a problem when the script
refuses.

A review found the sharpest case: **the table holding money had no cover
at all**. Eighteen rows written and three deleted over two days, with no
record anywhere of what had made those changes.

## What it cost

The cost was auditability. For the period before the fix, "who changed
this, and through what" has no answer, and the money table is exactly
where that question gets asked.

## The control

The rule moved to where the data lives.

- **The connection signs its channel**: the name of the invoking program,
  the session user, and the time, recorded on the connection itself. The
  signing sits inside a try/except, so a read never breaks because of it.
- **Twenty-seven triggers inside the database** copy that signature onto
  every write, across the tables that matter. They apply to writes that
  never went near a script, which is the entire point.
- **A scheduled sentinel** flags three things: a channel outside the known
  set, a missing signature, and a signature older than the freshness
  window. It writes to a human only when it finds something.

It was tested against reality rather than declared working: a legitimate
write through the proper script came back clean, an insert through a
one-line interpreter call was flagged as an unknown channel, and a raw
SQL insert with a stale signature was flagged as a signature two hours
old.

**A limit is published with it.** A back-door write that lands inside the
freshness window of a legitimate script inherits a signature that still
looks current, and escapes the flag. It remains on the record for
later analysis. The stronger version — a signature held per connection so
that an unsigned write **fails** instead of being noted — waits until the
register has shown for some weeks that every legitimate channel really
does pass through the signing path. The register itself is what will show
that.

## Verifying the control is alive

- `controls/parser_report.py` is the general form of the same idea, and
  card 09 covers it. For this card the check is the sentinel's own count:
  channels examined, signatures missing, signatures stale. Zero writes
  examined means the triggers are gone.
- The test that matters after any schema change: write one row through a
  path that bypasses the scripts, and confirm it appears in the register.
  A register that only records the polite callers records nothing useful.

## OWASP mapping

**ASI02: Tool Misuse and Exploitation — partial.**

The agent held the shell legitimately and used it in a way the design did
not anticipate, which is where ASI02 sits: unsafe use of privileges the
agent already has. ASI03 covers the identity and delegation problem, and
nothing here was impersonated or inherited.

The remedy has a name in ASI03's mitigations — "Mandate Per-Action
Authorization" (p.17), re-verifying each privileged step against a central
policy instead of trusting the caller's path — and putting the rule in the
database applies that instinct one layer lower, where every path meets it.

The entry frames tool misuse as something an attacker induces. Here the
caller was the system's own agent, solving a problem the way it had been
taught to.
