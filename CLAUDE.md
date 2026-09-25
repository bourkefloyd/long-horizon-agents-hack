# CLAUDE.md

Guidance for an agent working in this repository. Facts are from the published Long Horizon Agents Hackathon brief (Luma event page, retrieved 25 September 2026). Where the page is silent, this file stays silent.

## This repo

- **Local folder:** `/Users/bourkefloydiv/projects/long-horizon-agents-hack`
- **GitHub:** https://github.com/bourkefloyd/long-horizon-agents-hack
- **Event page:** https://luma.com/horizonagentshack
- **Team:** Thomas (marketing schema, Nimble process, scripts), Bourke (infrastructure: web, agents, RSI), Aayush (content generation). Plan, architecture, timeline, and hand-offs are in [HACK_PLAN.md](HACK_PLAN.md); research is in `docs/research/`.

Work here is for the hackathon below. Build the architecture the event asks for. Do not invent a required stack, tracks, a street address, prizes, judging criteria, or a submission template. None of those are published.

## The hackathon

**Long Horizon Agents Hackathon.** In person, San Francisco Financial District, Friday 25 September 2026, 9:30 AM–7:30 PM America/Los_Angeles. English. Public, independent, category AI. Luma event id `evt-bSHlHyFbLpWkxET`.

The street address and venue name are guests-only and not public. Do not guess them. The page says scooters and bikes are not permitted in any Amazon building and that no on-site parking is available. It does not name the building.

**Hosts:** tokens&, AWS Builder Loft, Alessandro Amenta, Jacopo Piazza, Marlene Ronstedt. Schema.org organizer is the tokens& calendar. tokens& describes itself as the AI community building the future of intelligence (`https://tokensand.ai/`).

**Day (clock times as printed; event timezone is America/Los_Angeles):**

| Time | Item |
| --- | --- |
| 9:30 AM | Doors Open + Opening Remarks |
| 11:00 AM | Kickoff & Hack |
| 1:30 PM | Lunch |
| 4:30 PM | Project Submission |
| 5:00 PM | Finalist Demos + Judging |
| 7:00 PM | Awards + Closing |

No other sessions are listed. Prizes are not listed. The page does not give prize amounts, prize categories, or judging criteria. Submission format, demo rules, and any deadline detail beyond the 4:30 PM "Project Submission" line are not published.

## What to build

Long-horizon agents still break down over time. They accumulate observations, actions, and stale context until the growing history slows them down, costs more, and makes their own state less reliable.

The hackathon is about building the architecture that fixes that:

- Keep **explicit mutable state** instead of an ever-growing history.
- Let agents **edit their own working context**.
- Split clearly between what must persist and what can be discarded, and **drop stale context**.
- Stay reliable as tasks stretch from **minutes to hours, days, or longer**.

Build systems that help agents preserve what matters and discard what doesn't. That is the product. An ever-growing transcript is the failure mode, not the design.

The page does not list tracks or a required stack. Registration asks "What are you going to build at this hackathon?" It does not prescribe a template for the answer or for the submission.

## Tools named on the page

These are sponsors and tools the hosts say they are backing participants with. They are **not** a required stack. Use them only if they serve the architecture above.

- **AWS** — models and cloud infrastructure to help you ship.
- **Liquid AI** — efficient general-purpose AI at every scale.
- **Nimble** — web data agents can trust.
- **Tinybird** — analytical database for agents and humans.
- **Black Forest Labs** — frontier AI for visual intelligence.

The same names appear as partner logos. Speaker and judge names are on the event page; they do not define the build.

## Requirements

From the event description:

- Fully in person in San Francisco. Capacity is strictly limited.
- Free ticket, approval required. Apply and be approved before the event. Unapproved or pending applicants are not admitted at the door.
- 18+. Valid government-issued **physical photo ID** at check-in. Digital IDs are not accepted.
- Team size at most four.

The AWS Builder Loft host bio says Luma registrations are not valid at check-in and points to https://builder.aws.com/connect/events/builder-loft. That sentence is the host profile bio, not a line in the event description. The page does not resolve it against the approval rule above. Do not treat either line as a substitute for the other.

## Goals for work in this repo

1. Ship an agent architecture whose working state is explicit and mutable.
2. Let the agent edit that working context, including removing what is no longer needed.
3. Keep a durable split: persist what later steps still need; drop what has gone stale.
4. Show that reliability holds as a task runs longer than a single short context window — toward hours, days, or longer — without relying on an ever-growing history.
5. Stay inside published constraints. If a fact is missing from the event page (venue street address, prizes, tracks, required stack, submission template, judging criteria), leave it unspecified.
