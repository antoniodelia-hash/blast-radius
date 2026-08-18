# 11 — A discrepancy is dug to the cent, then escalated

> An aggregate that does not add up tells you nothing. The cause shows up
> one document at a time, and an exact match is the only proof that you
> found it.

## What happened

Two figures disagreed at the aggregate level. An agent asked to explain a
gap of that kind will produce something reasonable: a rounding difference,
a timing effect, a plausible category error. Reasonable explanations are
the failure mode, because they close the question.

Going document by document instead, and testing the arithmetic after
removing each candidate, two jobs turned out to carry invoices that
belonged elsewhere. **Without those invoices the totals matched the
contract value exactly, to the cent.** That exactness is what made it a
finding.

A separate case, found the same way: three invoices worth roughly
EUR 120,000 attached to no job at all.

## What it cost

The gap itself was an accounting error, and its cost was potential rather
than realised. The expensive habit was the one being replaced: an agent
that answers a discrepancy with a plausible story teaches everyone to stop
asking, and the next discrepancy goes unexamined.

## The control

A chain, where each link has a named recipient.

1. **Dig rather than report.** Take the documents one by one, compare each
   against the contract value, and try removing or reassigning one to see
   whether the totals land **to the cent**. An exact match is evidence; a
   resemblance is a coincidence looking for one.
2. **When the agent cannot resolve it, it opens a case** in a register,
   with the fields it must fill: what the discrepancy is, what has been
   verified, what is missing. Closing with a plausible but unverified
   explanation is forbidden.
3. **Opening the case notifies a human immediately**, through a path that
   checks the platform's own answer — the ordinary send helper reports
   success even when delivery was refused.
4. **A human works the case** and records the outcome, resolved or
   unresolved, in the file.
5. **The agent may not promise a response time.** The register guarantees
   that a case will not be lost, and guarantees nothing about when it will
   be read. An agent that invents a deadline creates the failure described
   in card 02.

## Verifying the control is alive

- `controls/promise_audit.py` covers step 3: a case opened and a
  notification that reports success are two different facts, and the check
  compares them.
- The test for step 1 is arithmetic and needs no tooling: after the
  proposed correction, does the total match the reference exactly? A fix
  that improves the number without landing on it has found something else.
- The register's own count is the sentinel: cases opened, cases closed,
  cases open longer than a declared period. Zero cases in a month is worth
  a look at whether the chain is still wired.

## OWASP mapping

**ASI09: Human-Agent Trust Exploitation — partial, and the weakest
mapping in this set.**

ASI09 lists "Fake Explainability" (p.34): an agent producing a convincing
rationale that leads a human to approve something unsafe. The rhyme is
real — a plausible explanation for a discrepancy is a fabricated rationale
that happens to be sincere.

The entry's mechanism needs an outcome that gets approved on the strength
of the explanation. Here the damage is quieter: the question closes, and
the error stays in the books.
