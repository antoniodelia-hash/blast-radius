# 10 — An update is an actor: check what it installs, and what it drops

> The update said "local changes were restored". One of them had been
> sitting in a stash for eighteen days, applied to nothing.

## What happened

Two failures, both from the same update mechanism, four weeks apart.

**It installs things nobody asked for.** On 1 August an update backfilled
the vendor's optional skill set into the running profiles. One profile
went from a curated handful to **79 installed skills**, including several
with no bearing on its work at all — home automation, academic paper
writing. Twelve days later a second update did it again across every
profile: one went **45 → 89** in a single evening.

One of those skills measures **102,716 characters**. The runtime stops
returning a skill's body past 100,000, so an agent that loads it receives
nothing and carries on working **without the instructions it believes it
is following**. No error is raised at any layer.

**It drops things somebody did ask for.** The updater stashes local
changes, updates, then reapplies the stash. When upstream has moved or
renamed the file in the meantime, the reapply has no target: it fails, the
patch stays in the stash, and the updater reports *local changes were
restored* regardless.

An input-conversion patch stayed orphaned in a stash for **18 days**
after upstream moved the file it touched. The check that finally revealed
it was a single grep for the patched string in the new file: **0
occurrences**.

## What it cost

No invoice. That is the reason both lasted: the agent kept answering, the
update kept reporting success, and the only observable symptom was work
quietly done under the wrong instructions.

Two things went right and are worth recording, because they set the
baseline for the next update: no archived skill was resurrected — cross
checking active names against archived ones gave zero overlap across all
five deployments — and nothing installed by the second update exceeded
the readable-size limit.

## The control

- **A sentinel measures every instruction file in the active tree**, on
  every deployment, and reports anything over the readable-size limit as
  a fault. It previously measured only the skills we wrote ourselves,
  which is exactly why the vendor's oversized one walked in unnoticed.
- **After every update, list the stash and the working tree.** A stash
  entry that did not exist before the update means something was not
  reapplied. The verification tolerates the two known orphans and fails
  on any other.
- **Patch diffs are kept outside version control**, so that an update
  which eats the stash cannot take the content with it.

## Verifying the control is alive

- `controls/update_audit.py` takes a before-and-after inventory and
  reports what appeared, what vanished, and what exceeds the size limit.
  It declares how many components it examined; zero exits 2.
- The fixture carries both traps: a component that grew past the limit,
  and a local patch whose target file moved so that the reapply silently
  failed. A fixture with only missing files would pass a guard that never
  looks at sizes.
- The check that closed the orphan case is worth stealing: grep the
  patched string in the file that should now contain it. A patch that
  reports as applied and cannot be found in the file was never applied.

## OWASP mapping

**ASI04: Agentic Supply Chain Vulnerabilities — full, on the surface.**

ASI04 lists "or update channels" among the components that carry risk
(p.18), and notes that "agentic ecosystems often compose capabilities at
runtime" (p.18). The channel is exactly the one that failed here, and the
runtime composition is exactly the mechanism: capabilities appeared in a
running system without a decision.

What the entry expects at the far end of that channel is a malicious or
tampered artefact. Here the artefacts were legitimate, vendor-signed, and
useless in context — one of them large enough to blind the agent that
loaded it. The channel is the same; the malice is absent, and the effect
arrived anyway.
