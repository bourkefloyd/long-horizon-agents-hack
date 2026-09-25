# Hack plan: Long Horizon Agents Hackathon

Friday 25 September 2026, San Francisco. Team: Thomas, Bourke, Aayush. Written at 11:55 Pacific, after kickoff. Research behind every claim here is in [docs/research/](docs/research/).

## Goal

A playable ad whose clickstream drives engagement decisions. The ad emits taps, swipes, dwell, fails, and drop-off; a decision agent turns that stream into calls that should raise engagement: difficulty, pacing, when the call-to-action appears, whether to hint, which end card to show, when to ask for the install. The long-horizon angle is the state, not the model. A play session and a campaign both accumulate events for as long as they run. The agent keeps one compact mutable state (counts, current policy, last decision, cohort row), edits it on every beat, and drops stale events (raw coordinates once counted, events from closed sessions, the previous completion) instead of carrying the whole log into the next decision. The on-screen panel of what was kept versus what was dropped is the product.

## Architecture

The demo is one laptop, no venue Wi-Fi on the critical path.

```
+------------------------------------------------------------------+
| harness page (localhost, plain browser)                          |
|                                                                  |
|  +------------------------------+    +------------------------+  |
|  | <iframe> smoud Pixi playable |    | Decision agent (TS)    |  |
|  |  - mini loop, 20-30 s        | -> |  - StateReducer        |  |
|  |  - ClickstreamLog            |    |    keep / drop rules   |  |
|  |  - ScriptedDirector (baked)  | <- |  - ModelDirector       |  |
|  |  - ModelDirector (postMsg)   |    |    POST localhost      |  |
|  +------------------------------+    |  - deadline + fallback |  |
|                                      +-----------+------------+  |
|  Panel: decision taken, who took it,             |               |
|         kept state, dropped events               v               |
|                                      llama-server (localhost)    |
|                                      LFM2.5 230M or 350M Q4      |
+------------------------------------------------------------------+
```

- **Playable.** Fork of [smoudjs/playable-template-pixi](https://github.com/smoudjs/playable-template-pixi) (PixiJS 8, `@smoud/playable-sdk`, `@smoud/playable-scripts`). Verified on this machine: `npm install && npm run build applovin` gives one 607 KB HTML in about 10 seconds, plus Meta, Unity, ironSource single files and Google and Mintegral ZIPs. The SDK already emits `pointerdown/move/up`, `interaction`, `start`, `finish`, `install`, `retry`. We add swipe, idle, `level_fail`, `level_clear`, `cta_shown`, `cta_tap`, `endcard_shown` in `src/Game.ts`. The template's default `sdk.finish()` at 10 taps is removed.
- **Decision beats, not frames.** `director.decide(snapshot)` runs on `start`, after each fail or clear, after K seconds idle, and just before `finish`. It returns `{difficulty: 1..5, pacing: spawnIntervalMs, ctaAt: 'now' | 'afterNextClear' | 'atFinish', hint: boolean, endCard: 'win' | 'almost' | 'retry'}`. The game reads those values and nothing else changes.
- **Two directors, one interface.** `ScriptedDirector` is rules and a small bandit, baked into the HTML, so the file is a valid standalone playable on every network. `ModelDirector` posts the snapshot to the parent with `window.parent.postMessage`, waits up to a deadline (a few hundred ms, tuned on the demo machine), and falls back to scripted on timeout or an illegal answer. The panel says which one answered and why.
- **Harness and model.** The harness hosts the ad in an iframe, reduces the event stream into the compact state, POSTs it to `llama-server` (OpenAI-compatible, `LFM2.5-230M` or `LFM2.5-350M` Q4_0 GGUF, 149 MB / 219 MB, already on disk, `n_ctx` small, `max_tokens` capped, temperature 0.1) and posts the decision back. Constrained output (JSON schema or GBNF) if unconstrained JSON is flaky; code rejects anything outside the legal action set either way.
- **State reducer.** Keep per session: taps, swipes, dwell bucket, fails, current difficulty, hint or CTA already showing, last decision, session open. Keep per cohort: arm shown (difficulty, end card, CTA timing) and reward (reached end card, tapped install, dropped). Drop raw positions after counting, events from closed sessions, and any arm no longer in the test. A toggle appends the raw log so judges can watch the stuffed version get slower and worse. No lift is claimed that was not measured.
- **Why the model is beside the ad, not in it.** Every network that publishes a rule bans it. AppLovin: "External network calls are prohibited." Meta: "No external network calls are permitted. For example, XMLHttpRequest is not allowed." Unity: "Should not need any network requests." Google App campaigns: no external references outside their font and library allowlist. Mintegral's Playturbo guide: "no dynamical request." Caps are 5 MB (2 MB single HTML on Meta's developer table); the smallest LFM2.5 GGUF is 149 MB, so weights cannot ship inside either. Table with sources: [on-device-game-decisions.md, "Can a playable make network requests?"](docs/research/on-device-game-decisions.md#can-a-playable-make-network-requests).
- **How it maps to a real network later.** Delete the `postMessage` path and ship the `ScriptedDirector` alone; the model stays on our machine and edits the next build's rules and bandit priors from the cohort state between plays. For cross-promo inside an app we own, keep the same page in a WebView and replace `localhost` with a JS bridge to llama.cpp in the host app. The HTML never calls out in either case.

## Team and ownership

Three owners, one hand-off interface each. Files named here are the contract; the repo layout is Bourke's.

### Thomas: marketing schema, Nimble process, scripts

- **Deliverables.** `schema/marketing.schema.json`: the vocabulary the whole system shares (campaign, creative variant, decision arms, reward definition, cohort). A Nimble process that pulls web data on the target category (store listing copy, competitor playable CTAs, genre norms) and turns it into `scripts/*.json`: the rules and copy the `ScriptedDirector` ships with (difficulty ladder, hint text, CTA copy, end-card text per variant, default arm priors). A one-paragraph "why these defaults" note per script.
- **Later, maybe.** Campaign generation with Facebook (Meta): turn a cohort result plus the schema into a campaign brief or creative set. Not in scope before 16:30.
- **Hand-off to Bourke.** Schema v0 by 12:45 so the reducer and directors type against it. First `scripts/default.json` by 14:30. Changes after 15:30 are copy only, no shape changes.
- **Hand-off to Aayush.** Variant names and end-card copy (`win`, `almost`, `retry`) by 13:00 so images and text match.

### Bourke: infrastructure for Long Horizon in GitHub: web, agents, RSI

- **Deliverables.** This repo: fork of the smoud Pixi template under `playable/`, harness under `web/`, decision agent under `agents/` (StateReducer, ScriptedDirector, ModelDirector, llama-server client, deadline and fallback), the kept-versus-dropped panel, build scripts, README with run steps. `llama-server` running LFM2.5 230M or 350M on the demo laptop. **RSI: to define.**
- **Hand-off interface.** Consumes `schema/marketing.schema.json` and `scripts/*.json` from Thomas; consumes `assets/endcards/{win,almost,retry}.png` from Aayush and inlines them at build. Exposes the `Decision` type and the `snapshot` shape in `agents/types.ts`; anything Thomas or Aayush needs from the runtime is read from there, not from `Game.ts`.

### Aayush: content generation

- **Deliverables.** End cards and creatives generated before the demo with the Black Forest Labs image API (`api.bfl.ai`, `x-key` header, `POST /v1/flux-2-pro` or a cheaper route; 1 credit = $0.01). Three end-card variants matching Thomas's copy, plus a background or hero for the mini loop if time allows. A `content/README.md` with prompts, routes, and sizes so they are reproducible. Optional: a short FLUX 3 video clip for the demo intro, generated well before 16:00 because result URLs expire in about two hours.
- **Constraints.** Live choice is which card, not a new generation; BFL is never called on a tap. Each PNG under 200 KB after compression so the inlined HTML stays far below 2 MB (Meta's stricter single-file cap). Sizes: 320x480 portrait for the card, 512x512 for anything square.
- **Hand-off to Bourke.** `assets/endcards/{win,almost,retry}.png` at the agreed sizes by 14:30; a placeholder set (solid colour plus text) by 12:30 so the build never waits on generation.

## Timeline (Pacific, against today's agenda)

| Time | Agenda | Team |
| --- | --- | --- |
| 11:00 | Kickoff and hack | Done. Research landed; this plan committed at ~12:00. |
| 12:00–13:30 | | Bourke: fork template, `npm run dev`, iframe harness, `postMessage` round trip with `ScriptedDirector`, confirm GGUF is on disk and `llama-server` answers. Thomas: schema v0 (12:45), start Nimble pull. Aayush: BFL key check, placeholder end cards (12:30), first real variants. |
| 13:30 | Lunch | Eat. Duration is not published; assume 30–45 min. |
| 14:15–15:30 | | Bourke: `StateReducer`, `ModelDirector` with deadline and fallback, kept/dropped panel, raw-log toggle, cohort replay button. Thomas: `scripts/default.json` (14:30), copy review. Aayush: final end cards (14:30), hero art, prompts README. |
| 15:30–16:15 | | Freeze features. Everyone: rehearse the 60-second demo twice on the demo laptop, fix what breaks, README run steps, `npm run build applovin` to prove the standalone file still works with the scripted director. |
| 16:15–16:30 | | Submit. Commit, push, tag `v0.1-submission`. |
| 16:30 | Project submission | Format is not published; have the repo URL, a one-paragraph description, and the laptop ready. |
| 17:00 | Finalist demos and judging | Demo from the laptop. Someone else plays. |
| 19:00 | Awards and closing | |

**What fits by 16:30.** The playable in the harness, scripted director baked in, model director with fallback on localhost, the kept-versus-dropped panel, one cohort replay, three pre-generated end cards, and a standalone network build that still runs. That is about 4.5 hours of hacking minus lunch.

**What does not fit, and is not promised.** Nimble-to-Meta campaign generation, Jev integration (no key in hand; label it a cloud call if one appears), a Tinybird sink, an AppLovin or Meta upload, any fine-tune, FLUX 3 Action, a phone embed, a defined RSI, measured engagement lift. If the model director is still flaky at 15:30, the demo ships scripted-only with the panel and the model as a visible "advisor" whose answers are shown but not applied.

## Demo script (60 seconds)

1. **0–10 s.** "This is a playable ad. Every network bans it from calling out during play, and the smallest useful model is 149 MB, so the model cannot live in the file. It lives beside it." Point at the harness: iframe on the left, panel on the right, `llama-server` log in a terminal.
2. **10–30 s.** Judge plays. They tap, miss twice. Panel shows `level_fail` x2 arriving, the reducer folding them into `fails: 2, dwell: short`, then the raw coordinates greying out as dropped. A beat fires. Panel: "decision: difficulty 3 -> 2, hint: on. By: LFM2.5-350M, 180 ms." Game eases.
3. **30–40 s.** Judge clears a level. Beat fires, CTA appears `afterNextClear`. End card shows the `almost` variant. Panel shows which arm and why.
4. **40–50 s.** Flip the "append raw log" toggle, replay the same session. Panel shows the prompt growing, latency climbing, and the fallback firing on a missed deadline: "By: ScriptedDirector (model late)." That is the failure mode the hackathon is about.
5. **50–60 s.** Press "next cohort." Three finished sessions collapse into one cohort row, the end-card prior shifts, the previous sessions' events are gone. "Ship the file without the localhost call and it is a valid AppLovin creative. The model stays here and edits the next build."

## Risks and fallbacks

| Risk | Fallback |
| --- | --- |
| GGUF not on the demo laptop; venue Wi-Fi too slow to fetch 149–219 MB | Check at 12:00. If missing, download over a phone hotspot immediately or use any LFM2.5 GGUF already on any team machine. Demo ships scripted-only if none arrives by 15:00. |
| Small model returns malformed or illegal JSON | GBNF grammar or JSON schema on `llama-server`; code rejects illegal actions; scripted director answers; panel shows the rejection. |
| Model latency too high for a beat | Deadline in `ModelDirector` is tuned on the machine at 12:30; late answers are dropped, not applied late. Cohort decisions (between plays) never have a player waiting. |
| Template has no LICENSE file | The template is ~130 lines of glue we rewrite; SDK and build scripts are MIT. Note it in the README. |
| BFL key or credits missing | Aayush's 12:30 placeholder set is already in the build. Demo is unchanged; end cards are plain. |
| Nimble access or schema slips | Bourke types against a hand-written schema v0 at 12:45 and Thomas's later changes are copy-only. |
| Submission format is unknown | Repo URL, one paragraph, and a laptop. Tag the commit. |
| Someone claims a lift | Nobody does. The panel shows decisions, kept state, and dropped events. Engagement lift is future work. |
| Scope creep toward a network upload, Jev, Tinybird, a phone | Not before 17:00. Anything not in "What fits by 16:30" waits. |

## Source docs

- [docs/research/project-context.md](docs/research/project-context.md): event brief, product target, workstreams.
- [docs/research/on-device-game-decisions.md](docs/research/on-device-game-decisions.md): Liquid LFM2.5, Jev, Black Forest Labs, network rules, architecture, smallest build.
- [docs/research/open-source-playables.md](docs/research/open-source-playables.md): smoud Pixi template recommendation, clickstream hooks, decision-hook placement.
