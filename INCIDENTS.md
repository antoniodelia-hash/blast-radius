# The incident ledger

The headline number comes from this table. It is here because an earlier
draft claimed "sixteen incidents" and no list in the repository produced
that figure: grouping events one way gave fewer, another way gave more.
A number that cannot be recomputed from a list is an assertion.

## How an incident is counted

- **One incident is one distinct event**, datable to a month, that
  produced a cost or a remedy.
- **Repeated occurrences of the same mechanism in the same period count
  once**, with the occurrence count in its own column. Three empty
  promises across two weeks are one incident that happened three times.
- **A near miss is listed and counted separately.** Something caught at
  design time did not happen, and putting it in the same total would
  inflate the claim.
- **No row says which deployment it came from.** Five deployments sit
  behind this table, some at the same client; attributing incidents to
  systems is what would make the client identifiable. See
  [ANONYMIZATION.md](ANONYMIZATION.md).

## The ledger

| # | Month | Card | What happened | Times | Adversary |
|---|---|---|---|---|---|
| 01 | Aug 2026 | 01 | Retrying sessions consumed 48% of a month's model spend | 7 | no |
| 02 | Aug 2026 | 01 | Self-edited instruction files grew past the readable limit | 1 | no |
| 03 | Jul–Aug 2026 | 02 | An announced action was never performed | 3 | no |
| 04 | Jun–Aug 2026 | 03 | Scheduled jobs reported success over a failed script | 6 | no |
| 05 | Aug 2026 | 03 | Notification failures exited zero and reached nobody | 1 | no |
| 06 | Aug 2026 | 04 | A guardrail was declared, never registered, and failed open | 3 | no |
| 07 | Jul 2026 | 05 | The database was reachable outside the write gate | 1 | no |
| 08 | Jul 2026 | 05 | The table holding money had no audit trail at all | 1 | no |
| 09 | Jul 2026 | 06 | Internal cost figures headed for a job-scope recipient | 1 | no |
| 10 | Aug 2026 | 07 | Outcomes addressed to a display name reached nobody | 2 | no |
| 11 | Jun–Aug 2026 | 07 | Deliveries failed silently and were found only in a log | 6 | no |
| 12 | Aug 2026 | 09 | A parser dropped exactly the category it was measuring | 1 | no |
| 13 | Aug 2026 | 10 | An update installed unrequested vendor components | 2 | no |
| 14 | Aug 2026 | 10 | A local patch was reported restored and applied to nothing | 1 | no |
| 15 | Jul 2026 | 11 | Invoices attached to the wrong job passed the aggregate check | 2 | no |
| 16 | Jul 2026 | 11 | Invoices worth roughly EUR 120,000 belonged to no job | 1 | no |
| 17 | Aug 2026 | 12 | Written state existed only inside a namespace, never on disk | 1 | no |
| 18 | Aug 2026 | 12 | A conclusion about the filesystem was drawn from the wrong view | 1 | no |

**Incidents: 18.** Occurrences behind them: 41.

Both numbers are recomputed from the table above, and the second one is
why this file exists: the first draft of this page declared 40 while the
column summed to 41.

## Near misses

| # | Month | Card | What was caught | Adversary |
|---|---|---|---|---|
| N1 | Aug 2026 | 08 | A guard that stepped aside for callers without an identity, found while designing a second entry point | no |

**Near misses: 1**, counted apart from the eighteen.

## The empty column

Eighteen incidents and one near miss, and the adversary column holds `no`
in every row. That is a statement about these events and carries no claim
about how often attacks happen elsewhere. Cards 01, 02 and 06 involve an
agent behaving in ways its designers did not intend, which is a failure
mode the OWASP taxonomy covers; none of them involves anyone hostile.

Two cards carry no ledger row. Card 08 is the near miss above. The
principle held back from the twelve — two engines answering the same
question — comes from a synthetic dataset, and belongs in neither table
until it is re-anchored to its production twin.
