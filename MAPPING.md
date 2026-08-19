# Mapping to the OWASP Agentic Top 10 (2026)

Twelve principles from **18 incidents and 1 near miss**, none of them
involving an adversary. The ledger that produces those numbers is in
[INCIDENTS.md](INCIDENTS.md).

Every principle in this repository comes from a system running in
production between June and August 2026. Each one is mapped onto the
[OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
where the mechanism matches, and marked as unmapped where it does not.
A threat taxonomy and a production incident log answer two different
questions, and an operator needs both.

Every quotation below was checked against the published PDF, with the
page it sits on. `tools/citation_check.py` re-runs that check.

    principles examined = 12    adversary present = 0
    full = 0    partial = 7 (one of them weak)    none = 5
    distinct ASI codes mapped = 4    ASI codes with no card = 6

## Where our incidents land

Card files are named after these numbers. All twelve are written.

| # | Principle | ASI | Verdict | Adversary | Quotation holding the verdict |
|---|---|---|---|---|---|
| 01 | A spending brake lives outside the agent | ASI02 | partial | no | "Loop amplification: Planner repeatedly calls costly APIs, causing DoS or bill spikes" (p.12); "Adaptive Tool Budgeting" (p.14) |
| 02 | An announced action and a performed action are different events | ASI09 | partial | no | "Adversaries or misaligned designs may exploit this trust" (p.33); "approving actions without independent validation" (p.33) |
| 03 | A green light that cannot turn red is not a status | — | none | no | ASI08 applies "only when that defect spreads across agents" (p.30); this one stayed still for two months |
| 04 | A control is verified from outside itself | — | none | no | ASI02 prescribes policy enforcement middleware (p.14) and no entry covers a guardrail that reports as installed and is silently discarded |
| 05 | Whoever writes the data does not write the rules | ASI02 | partial | no | unsafe use of privileges the agent already holds; the remedy is named in ASI03's "Mandate Per-Action Authorization" (p.17) |
| 06 | The permission wall lives in code, with its own exit code | ASI03 | partial | no | broken identity boundaries make "enforcing true least privilege impossible" (p.15) |
| 07 | Identity is resolved on every message, by id | — | none | no | the attribution gap in ASI03 (p.15) concerns the *agent's* identity; here the *human* identity was resolved by name instead of id |
| 08 | A permission holds for one caller only | ASI03 | partial | no | "Un-scoped Privilege Inheritance" (p.15) |
| 09 | A parser declares what it discarded | — | none | no | no entry; the leaders' letter gives the ground: "observability becomes non-negotiable" (p.7) |
| 10 | An update is an actor: check what it installs and what it drops | ASI04 | partial | no | "or update channels" among the components at risk (p.18); "agentic ecosystems often compose capabilities at runtime" (p.18) |
| 11 | A discrepancy is dug to the cent, then escalated | ASI09 | partial (weak) | no | "Fake Explainability" (p.34) |
| 12 | The state an agent believes it wrote may only exist in RAM | — | none | no | ASI06 covers adversaries who "corrupt or seed this context" (p.24); nothing here was corrupted or seeded |

### Held back

"One fact, one engine" — two engines answering the same question and
disagreeing — is documented and kept out of the twelve for now. Its
sharpest numbers come from a synthetic dataset, and a cost figure that
did not happen has no place next to fifteen that did. It returns once
re-anchored on its production twin.

## Where the taxonomy goes and we do not follow

Four distinct codes carry cards: ASI02, ASI03, ASI04, ASI09. **Six of the
ten** have no counterpart here, and saying why is part of the map.

| ASI | Title | Why no card |
|---|---|---|
| ASI01 | Agent Goal Hijack | Requires an attacker redirecting the agent's goals. Nothing in three months of logs matches. |
| ASI05 | Unexpected Code Execution (RCE) | These agents execute code by design, inside declared boundaries. No unexpected execution was recorded. |
| ASI06 | Memory & Context Poisoning | Nothing corrupted or seeded the stores. The adjacent card is 12, where state was discarded rather than poisoned. |
| ASI07 | Insecure Inter-Agent Communication | The deployments do not talk to each other. Untested here, so unclaimed. |
| ASI08 | Cascading Failures | Requires a fault that spreads "across agents, sessions, or workflows, causing measurable fan-out" (p.30). Every failure here stayed where it started, sometimes for months. |
| ASI10 | Rogue Agents | Describes an agent that drifts out of its mandate (p.36). The drift in cards 01 and 02 stays inside the mandate; what misreported was the surface around the agent. |

## On the empty column

The adversary column holds twelve `no` values. That is a fact about the
eighteen incidents in [INCIDENTS.md](INCIDENTS.md), stated as measured,
and it carries no claim about how often attacks occur elsewhere.

The Agentic Top 10 does account for failures with nobody behind them.
ASI10 is described as "autonomous misalignment that emerges without active
attacker control" (p.9), ASI09 opens its fourth scenario with "Regardless
of root cause (hijack, poisoning, or hallucination)" (p.34), and ASI02
covers unsafe use of privileges an agent already holds. So the claim here
is narrow and checkable: **in these eighteen incidents no adversary was
present**, and nothing more.

Two cards do show an agent behaving in ways its designers did not intend —
01, where sessions retried until they had spent half a month's budget, and
02, where a sentence stood in for an act. What is missing in every case is
somebody hostile, and in most cases what failed was the reporting surface
around a working agent.

The NIST AI Risk Management Framework 1.0 names the axis this collection
sits on, separating *Secure and Resilient* from *Valid and Reliable*. NIST
treats those characteristics as interdependent rather than exclusive, and
the same is true here: an unreliable system is easier to attack, and these
incidents simply had nobody attacking.

## About the name

The practice this repository documents carries the name OWASP itself uses
for it. ASI08, mitigation 7, p.32:

> Implement blast-radius guardrails such as quotas, progress caps,
> circuit breakers between planner and executor.

## Method

The mapping was made from the published PDF, read in full. The OWASP
landing page does not list the ASI codes, so secondary summaries were not
used. Where a quotation is split across lines by PDF extraction, the
checker flattens whitespace before comparing — a check that missed two
genuine quotations before that was fixed, which is the kind of failure
this repository is about.
