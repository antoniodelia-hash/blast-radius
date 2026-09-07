# 04 — A control is verified from outside itself

> The brake appeared in the configuration file. The process had never
> registered it. Every write went through, and the log said so in a line
> nobody reads.

## What happened

A pre-write hook — the control described in card 01 — exists only when
**three conditions hold together**. One of them is the configuration
entry. Installing that alone produces a brake that is visible in the
config and lets everything past.

1. The line in the configuration file, whose matcher must exactly equal
   the tool name.
2. A shell-hooks allowlist **inside the profile**. Without it the runtime
   discards the hook at registration: it tries to ask for confirmation on
   a terminal, and under the service manager there is no terminal, so the
   prompt returns false and the hook is dropped.
3. The hook command **visible inside the service's namespace**. The
   hardening described in card 12 hides the directory it lives in, and the
   hook **fails open**: when the file cannot be seen, the runtime logs a
   warning and the write proceeds.

And a fourth, which is the one that catches people who did everything
right: **hooks are registered only when the gateway starts**. Nothing in
the codebase reloads them, so an edit to the configuration is inert while
the process lives.

At the time of discovery, three of the five deployments had an empty hook
section, no allowlist, and no size sentinel watching their instruction
files. The protection was believed to be fleet-wide.

**The setting that should close the gate lives inside the gate.** The
runtime does offer `fail_closed: true`, which turns a spawn error or a
timeout into a refusal. It is read inside the hook's callback, and the
callback only exists once the hook is registered. So a hook that never got
wired up — because its command was invisible, or because the allowlist
entry was missing — fails open while its configuration declares the
opposite, and the option that was supposed to protect you is unreachable
code.

That correction came from someone else. A reader of the upstream report
reproduced the same end state from a different trigger and made the point
sharper than we had: enforcement of "fail closed" belongs at registration
time, not only at fire time, or it keeps missing the cases where the hook
never got wired up at all. Their report is
[hermes-agent#100942](https://github.com/NousResearch/hermes-agent/issues/100942);
across 13 profiles sharing one identical hooks block, 8 had no approval
file, and those 8 were exactly the ones emitting the warning.

**The runtime's own diagnostic reports this hook as healthy.** It checks
that the script exists and is executable, and it does so from the shell it
was typed in — where the file is genuinely there. The gateway looks from
inside its own view of the filesystem, where it is not. Green on one side,
absent on the other, and the write goes through.

That part is reported upstream:
[hermes-agent#90047](https://github.com/NousResearch/hermes-agent/issues/90047),
19 August 2026. The maintainers know what this card says.

## What it cost

Nothing yet, which is the whole problem. This is the failure class that
removes attention without adding protection: the brake is on the list of
things that are handled, so nobody looks again.

## The control

`install_check.py`, which answers one question: **is this guardrail
active in the live process?**

The decisive part is where it looks. Reading the configuration, or asking
the service manager what the unit file says, answers "was it declared".
The check instead resolves the running process and looks at the hook
command **through that process's own root**, so that "drop-in updated but
service not restarted" reads differently from "installed and active".

## Verifying the control is alive

- `controls/install_check.py` takes a declared set of guardrails and the
  observed state of the live process, and reports which ones are declared
  yet unreachable. It reports how many guardrails it examined; zero exits 2.
- The fixture carries all four failure shapes: declared but not
  registered, registered but invisible inside the namespace, present on
  disk while the process predates it, and one fully working guardrail that
  must come back clean.
- The manual version takes ten seconds and is worth doing after every
  change: write a marker through the tool the hook is supposed to guard,
  and see whether the hook's log grew. A hook whose log never grows was
  never installed.

## OWASP mapping

**No direct ASI mapping.**

ASI02 prescribes policy enforcement middleware as a mitigation (p.14),
and the taxonomy has no entry for the middleware that reports as
installed while standing aside. Every entry in the list assumes the
control either exists or does not; this failure lives in the gap where a
control exists in every document and in no process.

The absence is worth stating, because a fail-open guardrail is the one
thing that makes every other card in this repository unreliable.
