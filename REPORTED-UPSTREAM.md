# Reported upstream

Some of the failures described here are defects in software other
people maintain. Those go to the maintainers first, and appear in this
repository with a link to the report.

## A health check that looks from the wrong place

**Status: open, reproduction accepted.** Reported 19 August 2026,
[hermes-agent#90047](https://github.com/NousResearch/hermes-agent/issues/90047).
A self-contained reproduction was added on 20 August — two runs of the same
transient unit, differing by one property that hides the hook directory —
and the `needs-repro` label came off.

The runtime ships a diagnostic that checks configured hooks: the script
exists and is executable, it is on the allowlist, it has not changed since
approval, it answers a synthetic payload. It is a good tool and card 04
would be poorer without it.

It runs from the shell you type it in. The gateway, running as a hardened
service, sees a different filesystem — so a hook command in a directory
that was never mapped into the service's view is present for the diagnostic
and absent for the process that needs it. The check reports green, and the
hook never fires.

Reported before this repository was published, which is the order these
things belong in: the maintainers knew what card 04 says on the same day
the card became public.

**What the thread added, and what it took away.** A contributor confirmed
the second finding — the diagnostic exits 0 even while printing issues, so
nothing can gate on it — and offered a patch. One suggestion in the
original report had to be withdrawn: `fail_closed: true` already ships, and
asking for it was asking for something that exists. What survived the
correction is the divergence itself, which the setting does not touch: set
`fail_closed` on that hook and the diagnostic still reports healthy from
the host for a command the service cannot reach.

Then someone arrived from another direction. [hermes-agent#100942](https://github.com/NousResearch/hermes-agent/issues/100942),
opened 2 September 2026, reaches the same end state through a missing
approval file rather than a hidden path, and carries the observation that
sharpened card 04: `fail_closed` is read inside a registered hook's
callback, so a hook that was never registered fails open regardless of what
its configuration says.

Two independent triggers, one gap. That is worth more than either report
alone, and it is the reason this file exists.

## Sessions that never expire

**Status: open, triaged.** Reported 17 July 2026.

A gateway that recovers a session from its database after a restart skips
the reset policy and stamps the row as freshly updated, which clears the
idle clock. Sessions that should have expired stay alive indefinitely,
carrying their whole history.

The consequence is subtler than the wasted context. Instructions loaded
once as a tool result stay frozen in that history: you correct a rule,
deploy it, and it never takes effect, with no error and nothing in the
logs. The agent keeps following the version that was current on the day
the session started.

From the report: one session alive **3 days / 71 messages / ~291k tokens**
on a profile configured to reset after an hour of idleness. The first
cleanup closed **260 sessions**, the oldest of which had been immortal for
**37 days**.

The maintainers triaged it as a bug, medium priority, against the session
and gateway components.

Two of the principles in this repository were written down in that thread
before this repository existed:

> The source of truth must not be a field that the recovery path itself
> rewrites.

> Recovery had become a second path to the same decision, with the checks
> only on one of them. Any time two branches decide the same thing and only
> one carries the guard, the unguarded one eventually becomes the common
> case.

The second is [principle 08](principles/08-a-permission-holds-for-one-caller-only.md),
in the words it had on the day it was understood.

**The report:** [NousResearch/hermes-agent#66255](https://github.com/NousResearch/hermes-agent/issues/66255)

**The workaround**, if it is useful to anyone: an hourly job closes
sessions idle beyond a threshold by writing an end timestamp equal to the
**last real activity** rather than to now, and the same end reason the
runtime writes itself. The session finder stops adopting them, and the
next message opens a fresh session. No patch to the core, so it survives
updates.

## Still to report

One defect described in [principle 04](principles/04-a-control-is-verified-from-outside-itself.md)
concerns a hook mechanism that fails open: when the hook command cannot be
seen from inside the service namespace, the runtime logs a warning and the
write proceeds. That behaviour has not been reported upstream yet, and the
card here describes the class of failure without the detail needed to
exploit it. This page will carry the link once the report exists.
