# CLAUDE.md

Guidance for an agent working in this repository. Facts are from the published Long Horizon Agents Hackathon brief (Luma event page, retrieved 25 September 2026). Where the page is silent, this file stays silent.

## Status

The hack is over. The team took 1st place, Best use of Nimble, on 25 September 2026 (winners slide name: Local Ad Platform). The shutdown dated 26 September 2026 is in [README.md](README.md): Actions disabled, secrets removed, Cloud Run deleted. Do not run generate-content, publish, or deploy workflows, and do not spend Black Forest Labs credits.

## This repo

- **Local folder:** `/Users/bourkefloydiv/projects/long-horizon-agents-hack`
- **GitHub:** https://github.com/bourkefloyd/long-horizon-agents-hack
- **Event page:** https://luma.com/horizonagentshack
- **Team:** Thomas Barrios (marketing schema, Nimble, campaign generation), Aayush Srivastava (content generation: BFL FLUX, Liquid), Bourke Floyd (long-horizon infrastructure: GitHub Actions agents, web, Cloud Run, CDN). Plan and hand-offs are in [HACK_PLAN.md](HACK_PLAN.md); the closeout record is in [README.md](README.md); research is in `docs/research/`.

The build for the hackathon below was finished on site on 25 September 2026. Do not invent a required stack, tracks, a street address, or a submission template. The Luma page did not publish those.

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

No other sessions are listed. The Luma page does not give prize amounts, prize categories, or judging criteria. The result recorded by the team is in [README.md](README.md): 1st place, Best use of Nimble. Submission format, demo rules, and any deadline detail beyond the 4:30 PM "Project Submission" line are not published.

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

## Goals the hack asked for

These were the build goals. They are not open work.

1. An agent architecture whose working state is explicit and mutable.
2. The agent can edit that working context, including removing what is no longer needed.
3. A durable split: persist what later steps still need; drop what has gone stale.
4. Reliability as a task runs longer than a single short context window — toward hours, days, or longer — without relying on an ever-growing history.
5. Stay inside published constraints. If a fact is missing from the event page (venue street address, tracks, required stack, submission template, judging criteria), leave it unspecified. The placement and prize are team-reported in [README.md](README.md), not copied from the Luma page.
