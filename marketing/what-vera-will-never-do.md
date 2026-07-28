# What Vera Will Never Do

**A published commitment from VetAgent — pattern ② of the platform "what-wins" brief.**
Audience: practice owners, medical directors, and their staff. Status: client-facing;
every line below is enforced in the product, not asserted in marketing.

---

Most software tells you everything it *can* do. The faster way to know whether you can
trust an assistant with your practice is to read what it will refuse to do — and to
know that the refusals are built into the system rather than promised in a brochure.

## Clinical judgment

**Vera will never diagnose, prescribe, or alter a treatment plan.** Clinical decisions
belong to your veterinarians. Vera drafts, summarizes, and organizes; a licensed
professional reviews and signs everything clinical before it becomes part of a record.

**Vera will never give a client medical advice over the phone.** When someone calls
describing symptoms, Vera routes — to your on-call protocol, your emergency
instructions, or a human — using the triage rules *your* practice approved. Routing is
not diagnosis, and the line is enforced in the software, not left to judgment in the
moment.

**Vera will never sign a medical record.** Ever. If a note exists in your system with a
doctor's name on it, that doctor put it there.

## Your clients' information

**Vera will never reveal one client's information to another.** Household and clinic
scoping is enforced at the database layer with default-deny: if Vera cannot prove a
caller is entitled to a fact, the fact is withheld — even when that makes the
conversation less helpful. Every reveal and every withholding is logged with its reason.

**Vera will never guess who it is talking to.** Identification requires verification
appropriate to what is being asked. An unverified caller can book a routine appointment;
they cannot hear a diagnosis.

**Vera will never pretend to be a person.** Callers are told they are speaking with an
assistant, at the start, every time.

## Your practice's data

**Vera will never hold your data hostage.** Your records are yours. The copies Vera works
from are stored in a vault you own, exportable on request, and delivered back to you if
we ever part ways.

**Vera will never train a public model on your clients' records.** Your data is used to
serve your practice. Extraction subprocessors operate under no-retention terms.

**Vera will never state a fact it cannot source.** Every claim Vera makes — a figure in
your morning briefing, a line in a draft note, a total in a reconciliation report — is
traceable in one step to the record it came from. If Vera cannot show you the source, it
does not make the claim.

## Your staff

**Vera will never make your staff learn new software to keep their jobs.** Vera arrives
through the channels your team already uses. There is no login for anyone who does not
want one, no training day, no migration weekend.

**Vera will never take an action your team can't see or undo.** Actions are logged,
attributable, and reversible. Nothing consequential happens silently.

**Vera will never replace your front desk.** Vera answers when no one can — after hours,
during a rush, on the fourth simultaneous call. The goal is that your team goes home on
time, not that there are fewer of them.

---

*Why we publish this: a system you can check is worth more than a system that asks to be
trusted. Every commitment above corresponds to an enforced control — a database rule, a
signature requirement, a disclosure step, or an audit record — and we would rather be
held to a short list we keep than a long list we don't.*
