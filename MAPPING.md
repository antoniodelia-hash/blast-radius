# Mapping to the OWASP Agentic Top 10 (2026)

Twelve principles, sixteen dated incidents, **zero attackers**.

Every principle in this repository comes from a system running in
production between June and August 2026. Each one is mapped onto the
[OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
where the mechanism matches, and marked as unmapped where it does not.
A threat taxonomy and a production incident log answer two different
questions, and an operator needs both.

Every quotation below was checked against the published PDF, with the
page it sits on. `tools/citation_check.py` re-runs that check.

    principles examined = 12    adversary present = 0
    full = 1    partial = 6    none = 5

## Where our incidents land

Principle numbering is provisional until all twelve cards are written.

| Principle | ASI | Verdict | Adversary | Quotation holding the verdict |
|---|---|---|---|---|
| A spending brake lives outside the agent | ASI02 | partial | no | "Loop amplification: Planner repeatedly calls costly APIs, causing DoS or bill spikes" (p.12); "Adaptive Tool Budgeting" (p.14) |
| An announced action and a performed action are different events | ASI09 | partial | no | "Adversaries or misaligned designs may exploit this trust" (p.33); "approving actions without independent validation" (p.33) |
| A green light that cannot turn red is not a status | — | none | no | ASI08 applies "only when that defect spreads across agents" (p.30); this one stayed still for two months |
| A control is verified from outside itself | — | none | no | ASI02 prescribes policy enforcement middleware (p.14) and no entry covers a guardrail that reports as installed and is silently discarded |
| Whoever writes the data does not write the rules | ASI03 | partial | no | "Mandate Per-Action Authorization" (p.17) |
| The permission wall lives in code, with its own exit code | ASI03 | partial | no | broken identity boundaries make "enforcing true least privilege impossible" (p.15) |
| Identity is resolved on every message, by id | — | none | no | the attribution gap in ASI03 (p.15) concerns the *agent's* identity; here the *human* identity was resolved by name instead of id |
| A permission holds for one caller only | ASI03 | partial | no | "Un-scoped Privilege Inheritance" (p.15) |
| A parser declares what it discarded | — | none | no | no entry; the leaders' letter gives the ground: "observability becomes non-negotiable" (p.7) |
| One fact, one engine | ASI08 | partial | no | fault propagation across views of the same figure (p.30) |
| A discrepancy is dug to the cent, then escalated | ASI09 | partial (weak) | no | "Fake Explainability" (p.34) |
| The state an agent believes it wrote may only exist in RAM | — | none | no | ASI06 covers adversaries who "corrupt or seed this context" (p.24); nothing here was corrupted or seeded |
| An update is an actor: check what it installs and what it drops | ASI04 | full | no | "or update channels" among the components at risk (p.18); "agentic ecosystems often compose capabilities at runtime" (p.18) |

## Where the taxonomy goes and we do not follow

Seven of the ten entries have no counterpart here. Saying why is part of
the map.

| ASI | Title | Why no card |
|---|---|---|
| ASI01 | Agent Goal Hijack | Requires an attacker redirecting the agent's goals. Nothing in three months of logs matches. |
| ASI05 | Unexpected Code Execution (RCE) | Our agents execute code by design, inside declared boundaries. No unexpected execution was recorded. |
| ASI06 | Memory & Context Poisoning | Nothing corrupted or seeded our stores. The adjacent card is the one about state that exists only in RAM. |
| ASI07 | Insecure Inter-Agent Communication | The deployments do not talk to each other. Untested here, so unclaimed. |
| ASI10 | Rogue Agents | Describes an agent that drifts out of its mandate (p.36). Our agents did their job; the surfaces around them reported something untrue. |
| ASI01/ASI04 overlap | tampered artefacts | Our supply-chain card sits on the update channel, with no malice in it. |
| ASI03 (identity of the agent) | — | Covered partially; the *human*-identity half has no entry. |

## On the empty column

The adversary column holds twelve `no` values. That is a fact about these
sixteen incidents, stated as measured, and it carries no claim about how
often attacks occur elsewhere.

The Agentic Top 10 does account for failures with nobody behind them —
ASI10 is defined as "autonomous misalignment that emerges without active
attacker control" (p.9), and ASI09 opens its fourth scenario with
"Regardless of root cause (hijack, poisoning, or hallucination)" (p.34).
What it follows in each case is an agent that deviates, or a trust that
gets exploited. The failures collected here have neither: correct agents,
and reporting surfaces that stated something untrue while every monitor
stayed green.

For the axis this repository sits on, the NIST AI Risk Management
Framework 1.0 draws the line by name, separating the characteristic
*Secure and Resilient* from *Valid and Reliable*. The incidents below all
belong to the second one.

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
