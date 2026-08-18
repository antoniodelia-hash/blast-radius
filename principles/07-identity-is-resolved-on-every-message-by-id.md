# 07 — Identity is resolved on every message, by id

> The outcome of a governance decision was sent to a person's name. The
> platform needs a numeric id. Nobody received anything, and nothing
> reported a failure.

## What happened

Two governance outcomes were dispatched with the recipient field set to a
**human name** where the platform expects an account id. The send
returned without complaint. The two people who had proposed those changes
never learned what had been decided.

That was the visible instance. The systemic version sits in the data: in
the table of proposed changes, the proposer field held **4 valid ids, 3
names, and 22 empty values out of 29 rows**. Whoever proposes a change
almost never finds out how it ended.

The same review found **six missed deliveries over two months**, every
one of them recorded in a log and seen by nobody: a digest refused
because a recipient had blocked the sender, a Monday report that reached
none of its three intended readers because it exceeded a length limit, and
the two name-instead-of-id cases above.

## What it cost

The mechanism the whole system exists for — a person asks, the system
decides, the person is told — was broken for 22 of 29 requests, silently.
No money moved. What eroded was the reason anyone would keep using it.

## The control

- **Identity is resolved at the moment of use, from the id**, on every
  message. A name is a display value and never a destination.
- **The proposer field is populated at creation** from the session, and a
  row without a valid id is refused rather than stored. An empty
  identifier is a delivery that will fail in a week, when the context that
  could have repaired it is gone.
- **Delivery is verified rather than assumed.** The house send helper
  reports success even when the platform rejected the message, so
  notifications that matter go through a wrapper that checks the platform's
  own answer.

## Verifying the control is alive

- `controls/promise_audit.py` covers the general shape: what the system
  said it did, checked against what the records show. For this card the
  specific query is the one that found it — count identifier fields by
  kind: valid ids, names, empties. A table where names outnumber ids has a
  resolution problem, whatever the code looks like.
- Zero empty identifiers is the target; the number to watch is the ratio,
  and it should be checked after any change to how sessions are read.
- The failure was found by reading a log nobody had read. Any log that no
  check consumes will hold a failure like this one right now.

## OWASP mapping

**No direct ASI mapping.**

ASI03 describes an attribution gap, and its subject is the identity of the
**agent** — service accounts, delegated tokens, un-scoped inheritance
(p.15). The failure here is in resolving the identity of the **human** on
whose behalf the agent acts, in a system where that resolution is what
makes an outcome reach anyone.

The taxonomy treats human identity as an input the system has. In practice
it is a lookup that can silently return the wrong kind of value.
