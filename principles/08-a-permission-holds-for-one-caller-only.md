# 08 — A permission holds for one caller only

> Every guard in the stack carried the same line: with no identity, do not
> block. One door had always supplied an identity. Then a second door was
> built.

## What happened

Identity resolution returns nothing when it does not recognise the caller.
Every guard above it — write permission, department scope, company-level
scope, job-data-only — handled that case the same way: **absent identity,
allow**.

That branch was written deliberately, and it was right. Maintenance over
SSH, scheduled jobs, and recovery work all arrive without a session, and
they need to run. It stayed harmless for as long as there was exactly one
door for humans, because the chat gateway always attaches a user id.

Then a web dashboard was designed, with a chat inside it. That door would
have entered the same branch and run **with maintenance powers** — which
are broader than those of anyone in the company.

Recognising nobody, the guard stepped aside. That behaviour is a different
thing from refusing, and the difference is invisible in the code, because
both are the same `if` with no `else`.

## What it cost

Nothing: this one was caught at design time — the only card here that
was. It is included because the cost of missing it would have been the
largest, and because the shape is general enough to find elsewhere.

## The control

- **The rule moved into identity resolution itself**, rather than into
  each guard. Every guard passes through that one function, and a
  checkpoint belongs in one place.
- **Each door declares itself.** Callers set a channel marker; from the
  web and the API an identity is mandatory, and its absence blocks with a
  dedicated exit code. Maintenance keeps the permissive branch, now
  explicitly and by name.
- **The positive corollary was verified, not assumed:** with the real
  identity propagated, the guards that already existed took effect.
  A user opening the dashboard sees the job list **without** the accrued,
  invoiced, and margin columns, and nobody wrote a line of web-specific
  permission code to make that happen.

The question worth asking before opening any new channel to tools that
already exist: **what happens in here when the caller has no name?**

## Verifying the control is alive

- `controls/install_check.py` covers the general case: a guardrail that is
  declared and does not engage. For this shape specifically, the test is
  to call the tool through the new door with the identity deliberately
  stripped, and require a non-zero exit.
- The fixture must include the permissive branch working as intended for
  maintenance. A test that only proves the new door blocks would pass a
  version that has broken every scheduled job.

## OWASP mapping

**ASI03: Identity and Privilege Abuse — partial.**

ASI03 names "Un-scoped Privilege Inheritance" (p.15) — a component
passing its full access context onward — and this is that, arriving from
an unexpected direction: the inheritance came from the absence of a
context rather than from passing one along.

The entry's actor is an attacker escalating privilege. Here the escalation
would have been granted by a convenience written for a different caller,
who was never consulted about sharing it.
