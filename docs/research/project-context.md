# Long Horizon Agents Hackathon

## Project outline

Reference outline of the event facts in the sections below.

### Goal

Long-horizon agents still break down over time: they accumulate observations, actions, and stale context until the growing history slows them down, costs more, and makes their own state less reliable. This hackathon is about building an architecture that stays reliable as tasks stretch from minutes to hours, days, or longer.

### What to build

- Explicit mutable state instead of ever-growing histories
- Agents that edit their own working context
- A clear split between what needs to persist and what can be discarded
- Systems that preserve what matters and discard what doesn't

The page does not list tracks, a required stack, or a submission template. Registration requires an answer to "What are you going to build at this hackathon?"

### Requirements

- Fully in person in San Francisco, Friday 25 September 2026, 9:30 AM–7:30 PM Pacific (`America/Los_Angeles`)
- Apply and be approved before the event. Capacity is strictly limited. Unapproved or pending applicants are not admitted at the door.
- Age 18 or older, with a valid government-issued physical photo ID at check-in. Digital IDs will not be accepted.
- Maximum team size is four
- Agenda: 9:30 AM doors and opening remarks; 11:00 AM kickoff and hack; 1:30 PM lunch; 4:30 PM project submission; 5:00 PM finalist demos and judging; 7:00 PM awards and closing

### Constraints

- Published place is San Francisco, CA, United States, Financial District. The exact street address and venue name are not public. Page coordinates are latitude 37.789798774682275, longitude −122.40101172037976.
- Scooters and bikes are not permitted in any Amazon building. No on-site parking is available. The description does not name the building.
- Prizes are not specified. The page does not list prize amounts, prize categories, or judging criteria. The agenda includes awards and closing at 7:00 PM.
- Submission format, deadline details beyond the 4:30 PM project-submission line, and demo rules are not on the page.
- Backing tools named on the page: AWS (models and cloud infrastructure), Liquid AI (efficient general-purpose AI), Nimble (web data), Tinybird (analytical database), Black Forest Labs (visual intelligence).
- The AWS Builder Loft host bio says Luma registrations are not valid at check-in and points to https://builder.aws.com/connect/events/builder-loft. That sentence is the host profile bio, not a line in the event description.

### Local paths

- Local agent file: `/Users/bourkefloydiv/projects/long-horizon-agents-hack/CLAUDE.md`
- Local repo: `/Users/bourkefloydiv/projects/long-horizon-agents-hack`
- GitHub: https://github.com/bourkefloyd/long-horizon-agents-hack

### Product target

The model must react to clickstreams from playable ad plays (taps, swipes, dwell, drop-off) and make decisions that improve ad engagement: difficulty, pacing, CTA timing, hints, end card, install prompt.

Long-horizon angle: a play session or campaign accumulates events over time. The agent keeps compact mutable state and drops stale events instead of carrying the full event history.

### Workstreams

1. **Repo scaffold** — done. GitHub https://github.com/bourkefloyd/long-horizon-agents-hack, local `/Users/bourkefloydiv/projects/long-horizon-agents-hack`, `CLAUDE.md` and `.gitignore` on `main` at commit `ab2f397`.
2. **Model research for clickstream-driven decisions** — in progress. Liquid AI LFM2.5 (230M, 350M, 1.2B being added), Jev (TypeSafe, hosted), Black Forest Labs action model being added. Doc: [on-device-game-decisions.md](on-device-game-decisions.md)
3. **Playable-ad research** — in progress. Open-source playable-ad templates and clickstream hooks (taps, swipes, dwell, drop-off). Constraints for casual mobile playables are in the same doc as workstream 2. Doc: [open-source-playables.md](open-source-playables.md)
4. **Prototype** — not started. A playable ad that emits clickstream events to a decision agent, which keeps compact mutable state and returns engagement decisions (difficulty, pacing, CTA timing, hints, end card, install prompt).

Facts below are taken from the Luma event page (embedded event data, schema.org markup, and the partners image). Source URL: https://luma.com/horizonagentshack?tk=w2kKwY. Canonical URL: https://luma.com/horizonagentshack. Retrieved 25 September 2026. Nothing below is inferred beyond what that page publishes.

## Event

- **Name:** Long Horizon Agents Hackathon
- **Luma event id:** `evt-bSHlHyFbLpWkxET`
- **Status:** Scheduled (`EventScheduled`), public, independent event
- **Category:** AI
- **Format:** In person. Schema.org attendance mode is offline. The description says the event is fully in-person in San Francisco.
- **Locale:** English

## Dates and times

- **Timezone:** `America/Los_Angeles` (offset −07:00 on the published start and end)
- **Start:** Friday, 25 September 2026, 9:30 AM Pacific (`2026-09-25T09:30:00.000-07:00`, `2026-09-25T16:30:00.000Z`)
- **End:** Friday, 25 September 2026, 7:30 PM Pacific (`2026-09-25T19:30:00.000-07:00`, `2026-09-26T02:30:00.000Z`)

Agenda lines below are printed on the page as clock times only. They are not individually labeled with a timezone. The event timezone is `America/Los_Angeles`.

## Location

- **Published place:** San Francisco, CA, United States
- **Neighborhood:** Financial District
- **Exact street address:** not public. Address mode is obfuscated and visibility is guests-only. The page does not name a venue or street.
- **Coordinates on the page:** latitude 37.789798774682275, longitude −122.40101172037976

The description says scooters and bikes are not permitted in any Amazon building and that no on-site parking is available. It does not name the building.

## Hosts

Schema.org organizer is the tokens& calendar, plus the five hosts below.

| Host | Profile facts published on the event | Links |
| --- | --- | --- |
| tokens& | Calendar name tokens&. Short description: "The AI community building the future of intelligence." X handle `tokensandai`. LinkedIn handle `/company/tokensand`. Not verified. | https://tokensand.ai/ · https://luma.com/tokensand · https://luma.com/user/tokensand |
| AWS Builder Loft | Profile bio: "Welcome! Please note: Luma registrations are not valid at Check-in. Register here: https://builder.aws.com/connect/events/builder-loft" | https://builder.aws.com/connect/events/builder-loft · https://luma.com/user/awsbuilderloft |
| Alessandro Amenta | LinkedIn `/in/alessandro-amenta`. X `ale_amenta`. | https://www.linkedin.com/in/alessandro-amenta · https://luma.com/user/usr-qSsdgMpbRnNqoVG |
| Jacopo Piazza | LinkedIn handle on the profile is `/in/None`. No website or X handle. | https://luma.com/user/usr-Jk6OAeS5XqwgoR3 |
| Marlene Ronstedt | Bio: "GTM & Events via Play by Ear \| Med Spa intern @ fountain.clinic". LinkedIn `/in/ronstedt`. X `inaccisland`. Luma username `ronstedt`. | https://www.linkedin.com/in/ronstedt · https://luma.com/user/ronstedt |

The share token on the fetched URL (`tk=w2kKwY`) is a referral attributed to Bourke Floyd (referral id `w2kKwY`). His profile bio on the page: "VP Engineering, Platform @ PeopleFun | Built the AI, Data, Tech Platform Org now powering many games with millions of DAU on petabyte-scale". LinkedIn `/in/bourkefloyd`. X `bourkefloyd`. He is not listed as a host.

## Description

Long-horizon agents still break down over time: they accumulate observations, actions, and stale context until the growing history slows them down, costs more, and makes their own state less reliable.

Fixing that means rethinking the architecture — explicit mutable state instead of ever-growing histories, agents that edit their own working context, and a clear split between what needs to persist and what can be discarded. This hackathon is about building that architecture.

Build systems that help agents preserve what matters and discard what doesn't, staying reliable as tasks stretch from minutes to hours, days, or longer.

## What participants build

The page asks participants to build that architecture: systems that help agents preserve what matters and discard what doesn't, staying reliable as tasks stretch from minutes to hours, days, or longer. It does not list tracks, required stack, or a submission template.

Registration asks, required: "What are you going to build at this hackathon?"

## Tools named in the description

Under "We're backing you with some of the best tools":

- **AWS:** The models and cloud infrastructure to help you actually ship.
- **Liquid AI:** Efficient general-purpose AI at every scale.
- **Nimble:** Web data your agents can trust.
- **Tinybird:** Analytical database for agents and humans.
- **Black Forest Labs:** Frontier AI for visual intelligence.

## Speakers

- [Viviana Márquez](https://www.linkedin.com/in/vivianamarquez/) — Developer Relations @ Liquid AI
- [Tianshu Yu](https://www.linkedin.com/in/tianshu-yu-b5683b18b/) — Member of Technical Staff, ML Engineer @ Liquid AI
- [Frederic Boesel](https://www.linkedin.com/in/frederic-boesel/) — Founding Member @ Black Forest Labs
- [Yaniv Markovski](https://www.linkedin.com/in/yanivmarkovski/) — Head of Ecosystem Engineering @ Nimble
- [Enzo Kajiya](https://www.linkedin.com/in/enzokajiya/) — Enterprise Account Executive @ Tinybird

The speakers section then links the word "Loading..." to https://i.gifer.com/ZKZg.gif?utm_source=luma. No further speaker name is given there.

## Judges

- [Saptarshi Banerjee](https://www.linkedin.com/in/saptarshi-banerjee-83472679/) — Applied AI Specialist Architect @ OpenAI
- [Viviana Márquez](https://www.linkedin.com/in/vivianamarquez/) — Developer Relations @ Liquid AI
- [Tianshu Yu](https://www.linkedin.com/in/tianshu-yu-b5683b18b/) — Member of Technical Staff, ML Engineer @ Liquid AI
- [Yaniv Markovski](https://www.linkedin.com/in/yanivmarkovski/) — Head of Ecosystem Engineering @ Nimble
- [Frederic Boesel](https://www.linkedin.com/in/frederic-boesel/) — Founding Member @ Black Forest Labs
- [Mogana Kumaran S.](https://www.linkedin.com/in/mogana-kumaran-s-8ab02026/?utm_source=luma) — Senior Staff Data Engineer @ Gap INC
- [Amit Panda](https://www.linkedin.com/in/pandaamit91/) — Staff Software Engineer @ LinkedIn
- [Tulika Manek](https://www.linkedin.com/in/tulika-manek/) — Tech Lead @ Razorpay
- [Pedro S. Lopez](https://www.linkedin.com/in/pedroslopez/) — Software Engineering @ Airbyte
- [Enzo Kajiya](https://www.linkedin.com/in/enzokajiya/) — Enterprise Account Executive @ Tinybird
- [Brian Neville-O'Neill](https://www.linkedin.com/in/bnevilleoneill/) — Head of Marketing @ Tinybird
- [David Li](https://www.linkedin.com/in/davidy-li/) — Co-founder @ Induction Labs
- [Frederic Boesel](https://www.linkedin.com/in/frederic-boesel/) — Founding Member @ Black Forest Labs (listed a second time)

The judges section then links "Loading..." to the same gif: https://i.gifer.com/ZKZg.gif?utm_source=luma.

## Agenda

- 9:30 AM — Doors Open + Opening Remarks
- 11:00 AM — Kickoff & Hack
- 1:30 PM — Lunch
- 4:30 PM — Project Submission
- 5:00 PM — Finalist Demos + Judging
- 7:00 PM — Awards + Closing

No other sessions are listed. The sessions array on the event is empty.

## Partners

A section titled "Thank you to our Partners!" contains one image and no caption or alt text.

- Image: https://images.lumacdn.com/uploads/1z/f1461f5d-1710-4ee5-b360-1a3efbcdd320.png
- Logos visible in that image: AWS, Liquid AI, Nimble, Tinybird, Black Forest Labs

## Prizes

Not specified. The agenda includes "Awards + Closing" at 7:00 PM. The page does not list prize amounts, prize categories, or judging criteria.

## Rules and attendance notes

Quoted from the event description:

- This event is fully in-person in San Francisco. Capacity is strictly limited. All attendees must apply and be approved prior to the event. Unapproved or pending applicants will not be admitted at the door.
- All guests must be 18+ and present a valid government-issued physical photo ID at check-in (digital IDs will not be accepted). Scooters and bikes are not permitted in any Amazon building with no on-site parking available.
- Maximum team size is four.

There is no separate rules document and no FAQ (FAQs are empty).

The AWS Builder Loft host bio, quoted above, says Luma registrations are not valid at check-in and points to https://builder.aws.com/connect/events/builder-loft. That sentence is the host profile bio, not a line in the event description.

## Registration

- **Availability:** open. Not sold out. Waitlist is enabled. Guest list is hidden.
- **Ticket in the event data:** name "Standard", type free, price empty, approval required. Not hidden, not disabled. No per-guest maximum and no capacity field on the ticket type.
- **Schema.org offer:** name "General Admission", price 0 USD, availability InStock, url https://luma.com/horizonagentshack.
- **Counts on the page data:** Standard ticket `num_tickets_registered` 622 and `num_guests` 622. Ticket info `spots_remaining` 1378. Top-level `guest_count` and `ticket_count` are 0.
- **Name requirement:** full name. Phone number is not required.

Registration questions:

| Question | Type | Required | Options |
| --- | --- | --- | --- |
| Which describes you best? | select | yes | Engineer / Developer / Researcher; Founder; Designer / Product; Investor (VC / Angel); Student; Other |
| What company / org are you with? | company | yes | |
| What's your current title / role? | text | yes | |
| What’s your work email? | text | yes | |
| What city are you based in? | text | yes | |
| What's your LinkedIn profile? | linkedin | yes | |
| What's your GitHub? | github | yes | |
| What's your X/Twitter? | twitter | no | |
| Link to the coolest thing you made? (website, repo, product, paper etc.) | url | yes | |
| What are you going to build at this hackathon? | text | yes | |
| Are you looking for a new role? | select | yes | Not looking; Open to the right thing; Actively looking |
| Are you currently fundraising? | select | yes | Not a founder; Not raising; Raising right now; Recently raised |
| By checking this box, you consent to providing your contact information to third-party event sponsors.* | agree-check | yes | |

## Links

- Event: https://luma.com/horizonagentshack
- Event with the fetched token: https://luma.com/horizonagentshack?tk=w2kKwY
- App link from the page: `luma://event/evt-bSHlHyFbLpWkxET?tk=w2kKwY`
- Cover image: https://images.lumacdn.com/uploads/mi/dcffc691-0c28-41e2-a9a9-bee2c14785fb.png
- Social image: https://images.lumacdn.com/event-social/f2/2c75c8c8-d8e5-46c4-8575-a55afabbfb52.png
- Partners image: https://images.lumacdn.com/uploads/1z/f1461f5d-1710-4ee5-b360-1a3efbcdd320.png
- tokens& site: https://tokensand.ai/
- tokens& calendar: https://luma.com/tokensand
- tokens& on X: https://x.com/tokensandai
- tokens& on LinkedIn: https://www.linkedin.com/company/tokensand
- tokens& newsletter: https://tokensandai.beehiiv.com/
- Embedded video, title "tokens& Agentic Engineering Summit": https://www.youtube.com/watch?v=WiEPPfNpV-0
- AWS Builder Loft registration URL from the host bio: https://builder.aws.com/connect/events/builder-loft
- Speaker and judge LinkedIn URLs are in the lists above.
- "Loading..." placeholders: https://i.gifer.com/ZKZg.gif?utm_source=luma

Closing line on the page: "See what’s possible." Then "Follow us on X · LinkedIn · Newsletter" using the tokens& links above.

## Missing from the page

- Street address and venue name
- Prize amounts, prize categories, and judging criteria
- Submission format, deadline details beyond the 4:30 PM "Project Submission" agenda line, and demo rules
- A capacity number stated as such (only the ticket counts above)
- FAQ, workshop list, or sessions beyond the agenda
- Further names after the "Loading..." gif in both the speakers and judges sections
- Alt text on the partners image
- A resolution of the host-bio line that Luma registrations are not valid at AWS Builder Loft check-in versus the event note that attendees must apply and be approved
