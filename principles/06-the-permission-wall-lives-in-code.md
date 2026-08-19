# 06 — The permission wall lives in code, with its own exit code

> A recipient with narrow permissions was one line away from receiving
> internal cost figures. What stopped it was the messaging platform's
> length limit.

## What happened

A recurring reminder asks a recipient with **job-level scope** for a
couple of operational dates. The instructions for that job say plainly
which categories of data must never appear in it: rates, standstill
costs, company totals.

The script built its message by pasting a notes field in full. Over the
preceding days that field had accumulated internal annotations, written
by the agent itself — rate corrections, cross-references to purchasing
documents, reconciliation notes.

On the day it broke, the platform refused the message: too long, 4,803
characters against a 4,096 limit. The failure sat in a log file for a day.

**The length was the symptom.** What the length was hiding was a
scope-violating payload heading for a recipient who was never meant to see
it, and the thing that stopped it was an unrelated platform limit. Had the
notes been three lines shorter, it would have gone out.

## What it cost

The cost was the discovery itself: scope, in that path, was enforced by a
coincidence. The payload stayed inside, and it stayed inside because a
message length limit happened to sit in the way.

## The control

Two defences, in series, each covering what the other misses.

- **The payload filter.** Only the first line of the notes field is shown,
  cut to 300 characters, and any item whose first line contains a monetary
  amount drops out of the list entirely. The message went from 4,803 to
  2,771 characters, zero amounts, both useful questions preserved.
- **The scope guard.** The finished text is re-read immediately before
  sending. A monetary amount anywhere in it stops the send with a
  **dedicated exit code**, and a human receives the offending line. This
  covers the routes the filter cannot see — an amount arriving through an
  equipment name, or through a job-phase label.

Both were tested against a copy of the database rather than the live one.

A side effect became a rule for the humans and the agent that write those
notes: **the first line is the only line the field will ever read**. The
operational fact goes first, corrections go underneath.

The same fix exposed a second defect one layer down. The message splitter
broke text only on blank lines, so a block without any — a table, a list —
stayed whole and got refused. It now falls back to lines, and then to a
hard cut.

## Verifying the control is alive

- `controls/promise_audit.py` and this card's guard share a shape: the
  check reads the artefact that is about to leave, rather than the code
  that composed it.
- The test to keep: run the reminder in print-only mode against a database
  copy seeded with a notes field that carries an amount **in a place the
  filter does not cover**, and confirm the guard exits non-zero. A guard
  proven only against the case the filter already handles proves nothing.
- Watch the exit code, not the log line. The original failure lived in a
  log for a day.

## OWASP mapping

**ASI03: Identity and Privilege Abuse — partial.**

ASI03 describes how broken identity boundaries make "enforcing true least
privilege impossible" (p.15) across an agent fleet. The recipient's scope
was defined correctly in the instructions; the enforcement lived in prose,
and prose does not run.

The entry expects a privilege boundary crossed by an attacker. Here the
system crossed its own boundary while doing exactly what it was asked, and
a message-length limit on an unrelated platform was the only thing in the
way.
