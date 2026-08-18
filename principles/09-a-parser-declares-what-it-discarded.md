# 09 — A parser declares what it discarded

> It read 187 of 199 messages and looked perfect. The 12 it dropped were
> all, and only, the ones the whole measurement was about.

## What happened

A scorecard script parsed the agent's message log to measure the quality of
its answers. Every number it produced was plausible, no check failed, and
nothing in its output suggested a gap.

It matched 187 lines out of 199. The 12 it missed shared one property:
the logger switches its quoting style when the message text contains an
apostrophe. In Italian, apostrophes cluster in a specific kind of
sentence — corrections. *"That's wrong, a delivery note is missing."*
*"You must just register it."*

The parser was blind precisely where the signal it existed to measure was
concentrated.

**A 6% error spread at random is noise. A 6% error that lands on one
category is a wrong answer wearing the clothes of a right one.**

## What it cost

One evening of conclusions drawn from a measurement that had removed the
evidence against them. Cheap here, and the same shape decides purchases,
staffing, and whether an agent is judged to be working.

## The control

Every parser counts **two** numbers: the lines that *should* have been of
interest, and the lines it failed to attach. Above a declared threshold —
1% for that scorecard — it stops with an error instead of answering.

Getting the first number is the part people skip. Count the lines
containing the keyword **before** applying the pattern, then compare with
how many the pattern caught. And then look at the rejects by eye: they are
a species, rarely an accident.

The same rule covers the period a source spans. A source that does not
reach the requested month is declared as such, because zero rows from
absent data and zero rows from absent work are opposite findings.

## Verifying the control is alive

- `controls/parser_report.py` parses a declared input and reports
  `examined`, `matched`, and `discarded`, refusing to answer when the
  discard rate crosses the threshold. Zero candidate lines exits 2.
- The fixture contains the trap that produced the incident: a log where
  the interesting lines use a **different quoting style** from the
  ordinary ones. A fixture of uniformly formatted lines would pass a
  parser that only handles uniform lines, which is exactly the failure.
- The rejects go on screen, not into a counter. A count tells you that
  something was dropped; the text tells you that everything dropped was a
  correction.

## OWASP mapping

**No direct ASI mapping.**

Nothing in the Agentic Top 10 addresses a measurement that quietly
excludes its own subject. The nearest ground is the leaders' letter, which
states that with agentic systems "observability becomes non-negotiable"
(p.7).

This card is the observability failure that survives good intentions: the
dashboard exists, the numbers are there, and the instrument has removed
the category it was pointed at.
