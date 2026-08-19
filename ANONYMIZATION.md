# Anonymization policy

Every incident in this repository happened on a real system, at a real
company, to real people. The failures are published; the company is not.

This page states the rules, so that a reader can hold the repository to
them — and so that the next person writing a card has something firmer to
follow than their own judgement at midnight.

## What never appears

- **The client's name**, in any form: legal name, brand, domain, mail
  domain, invoice header.
- **Geography**: town, province, region, site address. Not even as
  "somewhere near X".
- **People**: names, initials, roles narrow enough to identify one person.
  "The site foreman" is one person; "the field crews" is not.
- **Third parties**: suppliers, subcontractors, end customers, carriers.
  A supplier list is a fingerprint.
- **Identifiers**: job numbers, invoice numbers, plate numbers, chat ids,
  IP addresses, file paths that carry a profile name.

## What is said openly

- **Size**: around 50 employees, plus external crews.
- **Sector**: manufacturing SME.
- **Window**: the systems have been running since June 2026. Three months,
  said plainly. A stretched date is the first thing a reader checks.
- **Numbers**: 62 days, 2,312 messages, 12 discarded rows out of 199, 195
  files examined and 0 kept, 48% of a month's spend. Numbers carry the
  flavour and identify nobody.

## Trade vocabulary is an identifier

Sector plus vocabulary plus region reconstructs a company faster than the
name does. A reader who knows the industry needs only three specific nouns.
The rule is to raise each term one level of abstraction: far enough to
break the fingerprint, close enough that the mechanism still makes sense.
Named processes become *an outsourced step*. Quantities in trade units
become *units of material*. Reference numbers become *a job, referred to
by its position in the story*. Departments, suppliers and end customers
lose their names and keep their roles.

**The original terms are not listed here.** An earlier version of this
page carried a two-column table with the real vocabulary on the left, and
an adversarial reviewer used that column as its main evidence for
reconstructing the sector. A translation table publishes the thing it
translates.

Do not over-abstract. "A number came out wrong" says nothing; "a revenue
figure reached leadership understated by a third" says the mechanism
without naming the trade.

## Five systems, one story

The material comes from five agent deployments. Some sit at the same
client, some are still in trial. Two consequences, both binding:

- **No card says which system an incident came from**, and no count of
  incidents per system appears anywhere. Mixing the systems together is
  not enough on its own: most of the strong material comes from one place,
  so the attribution itself is the leak.
- **Incidents from systems still in trial are labelled as such** wherever
  that changes how the failure should be read.

## How the policy is enforced

- `tools/secret_scan.py` runs on every commit through a pre-commit hook.
  It carries a denylist of the real strings, which lives **outside** this
  repository — a denylist committed to a public repo publishes precisely
  what it protects. `tools/denylist.example.txt` ships the shape.
- Exceptions are marked inline with `scan:allow` and **counted out loud**
  on every run. An exception nobody sees again is how a denylist rots.
- Before release, an adversarial pass: an agent receives only the public
  text and is asked to name the company, to count how many clients are
  behind the material, and to use the text to attack a similar system.
  What it finds gets rewritten.

## If you recognise yourself here

Open an issue, or write to the address in the repository profile, and the
card comes down while we talk. That offer is part of the policy, not a
courtesy.
