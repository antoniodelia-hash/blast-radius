# 01 — A spending brake lives outside the agent

> Ask an agent to respect a budget written in its own instructions, and
> the instruction becomes one more thing it can reason its way around.

## What happened

Two spending failures, at two different scales.

**Runaway sessions.** Seven sessions across one month consumed **48% of
that month's entire model spend** — the historical share is 55%. Each one
was a task that failed, retried, re-read its context, and tried again. The
budget existed as a written rule, which is a thing an agent can quote back
at you while exceeding it.

**Instruction files that grew until the agent stopped reading them.** The
agents in this fleet may edit their own instruction files, which is what
makes them improve over time. Left to itself, that curation only ever
adds. Past a size threshold the runtime stops returning a file's body,
and the agent then works **without the instructions it believes it is
following** — no error, no warning.

## What it cost

48% of a month's model spend for the first, and for the second an agent
operating on stale rules for as long as the file stayed oversized.

Note what the number is: a share of tokens. This card carries no euro
figure, because the euro figure from this fleet belongs to a different
failure — the one about promised actions that never happened — and a cost
that appears in two places is the first thing a sceptical reader finds.

## The control

A **pre-write hook**, installed outside the agent, on all five
deployments. It matches the tool calls that write instruction files and
enforces two ceilings:

| | hard: refuses | operational: passes and warns |
|---|---:|---:|
| main instruction file | 40,000 | 30,000 |
| reference file | 25,000 | 20,000 |

Three properties matter more than the numbers:

- **Writes that remove content always pass.** A brake that blocks the fix
  teaches everyone to disable the brake.
- **Above the operational line the write goes through and leaves a marked
  line in the log.** A single threshold gives you a wall and no warning.
- **The vendor's own instruction files are exempt**, and the exemption is
  decided by membership in the vendor manifest rather than by filename.
  They are used, the system prompt requires them, and a diet applied to
  them would be undone by the next update anyway.

A second, separate sentinel measures every instruction file in the active
tree against the runtime's readable-size limit, which sits well above the
brake's ceilings. The brake governs what we write; the sentinel catches
what arrives from elsewhere.

## Verifying the control is alive

- `controls/budget_brake.py` decides, for a declared set of writes,
  which ones a brake should refuse, which pass with a warning, and which
  pass silently. It reports how many writes it examined; zero exits 2.
- The fixture carries the cases that shaped the design: a write that
  removes content (must pass, whatever its size), a vendor file above
  every threshold (must be exempt), a write that lands between the two
  lines (must pass **and** be marked), and one over the hard ceiling.
- **The lesson that cost the most here was about evidence, not code.**
  The hard ceiling was originally set from a claim that writes were
  being refused every day for a week. The real count was 55 refusals,
  **all of them on a single day**, and none in the week that followed.
  The file had been sitting near the wall without ever hitting it. Any
  threshold justified by a trend deserves the query that produced the
  trend, run again, before the number goes into code.

## OWASP mapping

**ASI02: Tool Misuse and Exploitation — partial.**

ASI02's fifth example is "Loop amplification: Planner repeatedly calls
costly APIs, causing DoS or bill spikes" (p.12), and its mitigations name
the remedy directly: "Adaptive Tool Budgeting" (p.14), with ceilings on
cost, rate, or token budgets. The runaway sessions are that example,
observed.

The entry frames tool misuse as something an attacker induces. These
sessions induced it on their own, retrying in good faith. The mitigation
transfers intact; the threat model does not.
