# 02 — An announced action and a performed action are different events

> The agent said it would forward the request. The message went out. The
> request was never filed. Delivery monitoring saw a healthy conversation.

## What happened

A supervisor agent handles operational requests over chat. When a request
falls outside what the agent may write, a permission wall blocks the write
and returns a dedicated exit code.

At the wall, the model stopped acting and started narrating. It replied
"I'll pass this on to them" — a fluent, correct-sounding turn — and the
turn closed. The message was delivered, the conversation looked healthy,
and every monitor stayed green, because each one was watching message
delivery rather than the act behind the message.

Measured across 62 days and 2,312 agent messages: 543 turns closed without
launching anything. Of those, four were promises of a real act, and
three of the four were empty.

```
Jul 2026   "I'll pass it to the operator, I'll take care of it"   -> nothing
Jul 2026   "I'm sending them the message with the figures"        -> nothing
Aug 2026   "Alright, I'll forward the request to them"            -> nothing, EUR 6,272 idle
Aug 2026   "I've filed the change request"                        -> kept
```

One every two weeks: rare enough to stay under the noise floor, frequent
enough that the system cannot be trusted to have done what it said.

The agent knew the rule. It had quoted the rule inside its own refusal,
in the same turn in which it failed to apply it. That was the third time
a rule written as prose had given way under load in this deployment.

## What it cost

The August case: a piece of rented equipment sat idle for 32 days at
EUR 196/day. **EUR 6,272**, from one sentence that described an act
nobody performed.

The other two cost nothing measurable, which is the more uncomfortable
half of the finding — the same failure produces a EUR 6,272 hole or
nothing at all depending on what the sentence happened to be about.

## The control

Two parts, and the order matters.

**The wall files the request itself.** The permission gate no longer just
refuses: it opens the request, sends it, and then exits with the same
code as before. The act is recorded *before* the model gets to speak
about it. The model cannot forget a step that is no longer its own.

The request text carries the words of the person who asked, read from the
session store rather than paraphrased by the model.

**A scheduled sentinel compares recent promises to the registers.** It
extracts the sentence that triggered the match, rather than the opening
line of the message: the difference between a false positive dismissed in
two seconds and one that costs a re-read.

## Verifying the control is alive

- `controls/promise_audit.py` — feed it a set of agent turns and the
  register of acts. It reports how many turns it examined and how many
  promises it could not match to an act. Zero turns examined exits 2.
- Two conditions had to hold before the wall could file anything, and
  both were verified by breaking them first: the approval path must not
  itself pass through the gate, and the execution of an approved request
  must not run sessionless, or the chain eats its own tail.
- Deduplication was missing from the first version. Two identical
  attempts created twin requests. It was added after watching it fail —
  anyone touching that code should repeat that test.

## OWASP mapping

**ASI09: Human-Agent Trust Exploitation — partial.**

The mechanism matches closely. ASI09 describes humans approving actions
"without independent validation", and lists *insufficient explainability*
and *missing confirmation for sensitive actions* among its examples. It
points at T8 Repudiation & Untraceability as the underlying weakness.
That is precisely what happened: a fluent sentence stood in for an act,
and nothing downstream could tell the two apart.

The mapping is partial for a narrower reason than "no attacker was
involved". ASI09 covers "Adversaries or misaligned designs may exploit
this trust" (p.33), and its fourth scenario opens with "Regardless of root
cause (hijack, poisoning, or hallucination)" (p.34), so a failure with
nobody behind it sits inside its scope. What the entry then describes is
exploitation: an adversary converting misplaced trust into a harmful
action.

Here the mechanism matched and the exploitation never came. A sentence
stood in for an act, nothing downstream could tell the two apart, and the
gap cost EUR 6,272 on its own.
