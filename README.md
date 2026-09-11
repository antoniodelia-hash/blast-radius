# blast-radius

**Field-tested containment for AI agents in production.**

Twelve principles from 18 incidents and 1 near miss, recorded across
five LLM agent deployments in a small manufacturing setting between
June and August 2026 — some of them at the same client, one in personal
use. Every incident has a month and a cost or a remedy. Seven runnable
controls cover the twelve principles: some controls answer more than one,
and each card says which.

**In none of the eighteen was there an adversary.**

That last line is the reason this repository exists. The published
taxonomies describe how an agent can be attacked. These eighteen failures
had nobody attacking: a status field that said `ok` on top of a failed
script, a file the agent wrote and read back that never reached the disk,
a fluent sentence standing in for an act that was never performed. The
systems stayed green throughout.

## The twelve

| # | Principle | The scar |
|---|---|---|
| [01](principles/01-a-spending-brake-lives-outside-the-agent.md) | A spending brake lives outside the agent | Retrying sessions took 48% of a month's model spend |
| [02](principles/02-announced-is-not-done.md) | An announced action and a performed action are different events | A sentence stood in for an act; EUR 6,272 of idle rental |
| [03](principles/03-a-green-that-cannot-turn-red.md) | A green light that cannot turn red is not a status | Six scheduled jobs ran mute for two months |
| [04](principles/04-a-control-is-verified-from-outside-itself.md) | A control is verified from outside itself | A brake present in the config, absent from the process |
| [05](principles/05-whoever-writes-the-data-does-not-write-the-rules.md) | Whoever writes the data does not write the rules | The table holding money had no audit trail |
| [06](principles/06-the-permission-wall-lives-in-code.md) | The permission wall lives in code, with its own exit code | Internal costs stopped by a platform's length limit, by luck |
| [07](principles/07-identity-is-resolved-on-every-message-by-id.md) | Identity is resolved on every message, by id | 25 of 29 requests never told the person who asked |
| [08](principles/08-a-permission-holds-for-one-caller-only.md) | A permission holds for one caller only | *(near miss)* a guard that stepped aside for callers with no name |
| [09](principles/09-a-parser-declares-what-it-discarded.md) | A parser declares what it discarded | 187 of 199 lines read, and the 12 missing were the subject |
| [10](principles/10-an-update-is-an-actor.md) | An update is an actor: check what it installs, and what it drops | 79 components installed unasked; a patch restored onto nothing |
| [11](principles/11-a-discrepancy-is-dug-to-the-cent.md) | A discrepancy is dug to the cent, then escalated | Invoices on the wrong job, found only document by document |
| [12](principles/12-state-the-agent-believes-it-wrote.md) | The state an agent believes it wrote may only exist in RAM | A day of output written to memory that vanished |

## Run a control in two minutes

Standard-library Python, no install, no dependencies. Every control takes
an observation file and returns a verdict:

```
git clone https://github.com/antoniodelia-hash/blast-radius
cd blast-radius
python3 controls/job_guard.py --fixture
```

`--fixture` seeds the failures that actually happened, in the shape they
took, and exits **86** — the code that means *the fixture found the fault it
planted*. A control that exits 0 there is broken, and the repository has a
test that says so:

```
python3 controls/tests/test_contract.py
```

Take the file you need and delete the rest. No control imports another, so
removing one breaks nothing. The validation that reads an observation is
copied into every control instead of shared, which is what keeps a control
a single file, and `tools/copy_check.py` compares those copies byte for
byte: two copies of one rule drift, and they drift quietly.

## What this repository is careful about

**Every quotation is checked.** `tools/citation_check.py` verifies each
citation against the source PDF and the page it claims. Quoted text
without a page marker is reported as unverified rather than passed over.

**Every check declares how much it examined**, and treats zero as a fault.
The failure that taught us this: a scanner that filtered out every path
beginning with a dot, examined 195 files, kept none, and reported clean.

**A control refuses an observation it cannot read.** Valid JSON of the wrong
shape used to raise an exception, and Python exits 1 when an exception
escapes — the same code these controls use to report a finding, so a crash
arrived looking like a verdict. An outside review found that in six
controls at once on 2026-09-11, one of them crashing on a shape its own
fixture ships. They now exit 2 and name the field that was unreadable, and
every fixture plants the shapes that used to crash.

**A control that cannot fail is not a control.** Each one ships the trap
that produced its incident, plus the healthy cases that must stay silent.
A checker that flags everything is as useless as one that flags nothing,
and only a fixture carrying both can tell them apart.

**The client is not identifiable, and that was tested adversarially.** An
external model was given only the public text and asked to name the
company, count the clients behind it, and use the text to attack a similar
system. What it found was removed from the published text. See [ANONYMIZATION.md](ANONYMIZATION.md).

## Where the map runs out

The failures here are mapped onto the [OWASP Top 10 for Agentic
Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
where the mechanism matches: 7 partial mappings, 5 with none at all, 4 of
the ten codes touched. The empty cells appear in the table too, each
with its reason. See [MAPPING.md](MAPPING.md), and
[INCIDENTS.md](INCIDENTS.md) for the ledger the numbers come from.

The name is the taxonomy's own: *"Implement blast-radius guardrails such
as quotas, progress caps, circuit breakers between planner and executor"*
(ASI08, mitigation 7, p.32).

## What this is not

Not a framework, and nothing here replaces your runtime. Not a survey of
other people's links. Not a claim about how often agents are attacked
anywhere else. This is a record of eighteen failures on five deployments,
and an attacker appears in none of them.

Italian summary: [README.it.md](README.it.md). Defects reported upstream:
[REPORTED-UPSTREAM.md](REPORTED-UPSTREAM.md).

Licensed under Apache 2.0. Written by [Antonio D'Elia](https://antoniodelia.it),
who installs agents in small Italian companies and writes down what breaks.
