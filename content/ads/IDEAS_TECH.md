# Tech-news ad ideas (Nimble → Opus 5.5 → FLUX 3)

Stories are from a Nimble news search on 25 Sep 2026. Brand-safety calls and scripts are by Claude Opus 5.5. Each story row expires, so an idea drops out of rotation once its story is stale.

Rules for all ideas:
- **Riff on the story, never the company.** No company names, logos or real people on screen or in voiceover; a feed card shows the general topic only.
- **Longer format.** 15–20 s. FLUX 3 text-to-video allows up to 20 s. At HD that's $2.55–$3.40 per ad; drafts are about a third.
- **Every ad ends in the brand's playable** (Stack for Sutro Stack, Pour for Sightglass), then the feed's Order and Next buttons.

Stories left out as not brand-safe: rogue AI agent chaos, AI agents colluding at blackjack, banks warning about AI shopping-bot scams, and an AI café startup's executive dating-post backlash.

---

## 1. "Post-smartphone lunch" · Sutro Stack · 20 s

**Story:** Meta launches AI gadget Charm as the race for post-smartphone hardware heats up. [Reuters](https://www.reuters.com/business/meta-expected-unveil-smart-glasses-without-camera-privacy)
**Nimble query:** `new AI gadget launch this week`, expires in 7 days.

| Time | Shot | Voiceover |
|---|---|---|
| 0–3 s | SoMa sidewalk, lunch rush. Three people tap tiny wearable pins and glasses, looking lost. | "Everyone's got a new AI gadget." |
| 3–7 s | One of them sniffs the air, turns toward a sizzling flat-top through a shop window. | "None of them can taste." |
| 7–13 s | Macro: two patties smashed, cheddar melts, sourdough bun lands on top. Slow motion. | |
| 13–18 s | They put their gadgets in their pockets and bite in, eyes closed. Friends laugh. | "Some upgrades are analog." |
| 18–20 s | The burger held up to camera, sunlit. | "Sutro Stack. Built the way you like it." |

**Why it works:** the first two seconds ride a story people are already scrolling past, and the payoff is a sensory thing a device can't give. **Action:** the Stack game, then Order your build.

## 2. "My agent ordered this" · Sightglass · 15 s

**Story:** a *New York Times* reporter handed their life to an AI agent for a week and was impressed. [NYT](https://www.nytimes.com/2026/09/22/technology/meta-muse-ai-agent.html)
**Nimble query:** `AI agents news this week`, expires in 7 days.

| Time | Shot | Voiceover |
|---|---|---|
| 0–3 s | POV: a phone notification slides in on a foggy N-Judah platform. | "I let an AI agent run my week." |
| 3–7 s | Barista slides a hot oat latte across the counter the moment the commuter walks in, already made. | "Day one, it ordered this." |
| 7–12 s | Commuter sips by the fogged window, surprised and smiling. | "Honestly? Good call." |
| 12–15 s | Close-up: the cup, steam, window light. | "Sightglass. Order ahead, your way." |

**Why it works:** it turns a tech anxiety into a small delight, and it sets up the feed's **Order** button, which renders the viewer's exact drink. That makes this the strongest idea for the demo.

## 3. "Put AI in space" · Sightglass · 20 s

**Story:** Google Research's Project Suncatcher, a moonshot to run AI in space on solar power. [Google blog](https://blog.google/innovation-and-ai/models-and-research/google-research/google-project-s)
**Nimble query:** `AI launch announced this week`, expires in 10 days.

| Time | Shot | Voiceover |
|---|---|---|
| 0–4 s | Night sky over SoMa, slow push-in on a single satellite glint. | "Big tech wants to put AI in space." |
| 4–8 s | Match cut from the satellite to a sunbeam through tall roastery windows. | "We'll settle for sunlight on 7th Street." |
| 8–15 s | Beans pour out of the roaster in slow motion, then a latte-art pour. | |
| 15–20 s | Two coworkers carry cups out into bright sun, squinting and grinning. | "Sightglass. Roasted right here." |

**Why it works:** a big cinematic hook resolved by a small human scale. The satellite-to-sunbeam match cut is the shot people remember. **Action:** the Pour game.

## 4. "No grades, no tests" · Sutro Stack · 15 s

**Story:** Andreessen Horowitz is launching an SF academy for "builders" with no grades, tests or degree. [SF Standard](https://sfstandard.com/2026/09/22/grades-tests-degree-andreessen-horowitz-launching-sf-aca)
**Nimble query:** `San Francisco tech startup news this week`, expires in 14 days.

| Time | Shot | Voiceover |
|---|---|---|
| 0–3 s | Young builders in hoodies around a whiteboard covered in sketches, SoMa loft. | "No grades. No tests. Just builders." |
| 3–8 s | Whiteboard flips to reveal a hand-drawn burger with labeled layers. | "Here's what they're building." |
| 8–12 s | Real burger assembled layer by layer to match the drawing. | |
| 12–15 s | The team toasts with burgers on the loft roof, Bay Bridge behind. | "Sutro Stack. Stack yours." |

**Why it works:** the drawn-to-real layers mirror the Stack playable, so the ad leads straight into the game. **Action:** Stack it, then compare your score with the Liquid agent's on the leaderboard.

## 5. "AI got cheaper" · Sutro Stack or any new brand · 15 s

**Story:** two AI labs released cheaper models this week. [CNBC](https://www.cnbc.com/2026/09/22/anthropic-openai-cheaper-ai-models.html)
**Nimble query:** `biggest tech news this week`, expires in 5 days.

| Time | Shot | Voiceover |
|---|---|---|
| 0–3 s | A laptop screen of blurred code; a hand drums impatiently. | "AI just got cheaper this week." |
| 3–8 s | The developer glances at a paper bag slid onto the desk. | "Lunch didn't have to." |
| 8–15 s | They unwrap a burger, bite, and lean back as the code finally compiles. | "Sutro Stack. Worth every bite." |

**Why it works:** it's the most generic of the five, so it works for any new brand created in Create mode. The voiceover must not name either lab. **Action:** Order.

---

## How these run

1. Create → set **News topic: Tech** → Generate.
2. Nimble runs the matching query, and the stories are saved with a source and an expiry.
3. Opus 5.5 checks brand safety, picks one story, and writes the timed script above.
4. FLUX 3 renders it.
5. Liquid LFM2-VL checks the frames for readable text or logos, since FLUX sometimes draws them anyway.

Every step is recorded in that video's sponsor ledger in the State panel.
