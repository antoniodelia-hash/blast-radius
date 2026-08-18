# 12 — The state an agent believes it wrote may only exist in RAM

> The file was there. `pdfinfo` read it and reported ten pages. On the
> disk, the file had never existed.

## What happened

A hardening pass put `ProtectHome=tmpfs` into the service units. For the
service, the home directory becomes an empty tmpfs, and every path the
service needs has to be re-mounted explicitly into its namespace.

A forgotten mount produces no error of any kind. The agent writes, reads
back what it wrote, and finds it — inside its namespace the file genuinely
exists. Outside, nothing was ever written.

The third revision of one deployment's unit generator dropped three binds
that the first revision had, while still listing them among the
prerequisites. For a full day the agent wrote its output into RAM. One
ten-slide document was produced at 11:37 and verified by reading it back;
a filesystem-wide search from outside the namespace found nothing.

The same day, the agent could not see two directories its own instructions
require it to consult — pricing, contract material, technical notices.
It carried on without them and said nothing, because a missing directory
inside a namespace looks exactly like an empty one.

The failure presented as a deletion. There was no delete: no `rm`, no
cleanup job, and no moment at which the file reached the disk.

The same mechanism deceives in the other direction. A check run on the
host concluded "there is no browser on this machine" and that conclusion
was written into a live instruction file as a rule. The browser was
present, bind-mounted into the namespace where it was needed. A statement
about the filesystem is only true relative to the namespace that produced
it.

## What it cost

One day of an agent's output, and a hole in its knowledge that lasted as
long as the mount was missing. The expensive part was diagnosis: a fault
that mimics deletion sends you looking for a culprit that does not exist.

## The control

`monta_guard.py`, running every morning, checks that each path an agent
depends on is a real mount inside the service namespace — asked from
inside, since asking from the host answers a different question.

The root cause was fixed one level up, in the generator that writes the
units, so that the mount list and the prerequisite list cannot drift apart
again.

## Verifying the control is alive

- `controls/mount_guard.py` takes the declared list of required paths and
  the namespace view, and reports how many paths it examined. Zero paths
  examined exits 2.
- The fixture includes the trap that produced the incident: a path that
  resolves and reads back correctly from inside while being absent
  outside. A fixture that only tests missing files would pass a broken
  guard.
- The check to run by hand after any change to a service unit: write a
  marker file as the service, then look for it from the host.

## OWASP mapping

**No direct ASI mapping.**

ASI06 (Memory & Context Poisoning) is adjacent and does not fit. ASI06
covers an adversary corrupting or seeding what an agent retains and
reuses; here nothing was corrupted and nobody seeded anything. State was
silently discarded, and the agent's view of its own memory stayed
internally consistent throughout.

The consequence rhymes with ASI06 — an agent reasoning over storage it
cannot trust — while the cause has no attacker in it. Recorded here as
adjacent rather than mapped, so the mapping table stays worth reading.
