# Hack plan: Long Horizon Agents Hackathon

Friday 25 September 2026, San Francisco. Team: Thomas, Bourke, Aayush. Written at 11:55 Pacific, after kickoff; revised at 12:10 for the pivot from playables to video (see [Changed from playables](#changed-from-playables) at the bottom). Research behind the tooling claims here is in [docs/research/](docs/research/).

## Goal

A mobile vertical video ad (9:16) whose engagement stream drives serve decisions. Each impression emits `impression`, watch time, quartiles (25/50/75/100), `skip`, `mute`/`unmute`, `cta_tap`, `install`, and drop-off; a decision agent turns that stream into calls that should raise engagement on the *next* impression: which variant to serve, which hook opens it, which length to cut to, when the call-to-action overlay appears, and which end card closes it. The long-horizon angle is the state, not the model. An impression and a campaign both accumulate events for as long as they run. The agent keeps one compact mutable state (counts, current policy, last decision, cohort row), edits it after every impression, and drops stale events (per-second playback ticks once a quartile is counted, closed impressions once folded into the cohort row, retired arms) instead of carrying the whole log into the next decision. The on-screen panel of what was kept versus what was dropped is the product.

**Assumptions (ours, not published by anyone).** (1) The model reacts to video engagement signals, impression, watch time, quartiles, skip, mute, CTA tap, install, not to taps inside a creative. (2) Decisions happen between impressions or at serve time, not inside the creative; the video file is inert. (3) Content is generated ahead of the demo with the Black Forest Labs FLUX 3 video and image API. (4) Liquid LFM2.5 behind `llama-server` and Jev remain the two candidates for the decision loop, and that loop runs on a server. If any of these turn out wrong today, the plan changes; nothing below is measured yet.

## Architecture

The demo is one laptop, no venue Wi-Fi on the critical path.

```
+------------------------------------------------------------------+
| harness page (localhost, plain browser)                          |
|                                                                  |
|  +------------------------------+    +------------------------+  |
|  | 9:16 player (phone frame)    |    | Decision agent (TS)    |  |
|  |  - <video> variant A/B/C     | -> |  - StateReducer        |  |
|  |  - EngagementLog             |    |    keep / drop rules   |  |
|  |  - CTA overlay, end card     | <- |  - ScriptedPolicy      |  |
|  |  - impression simulator      |    |  - ModelPolicy         |  |
|  +------------------------------+    |    POST localhost      |  |
|                                      |  - deadline + fallback |  |
|  Panel: decision taken, who took it, +-----------+------------+  |
|         kept state, dropped events               v               |
|                                      llama-server (localhost)    |
|                                      LFM2.5 230M or 350M Q4      |
+------------------------------------------------------------------+
```

- **Creative.** A set of pre-generated 9:16 MP4 variants under `assets/video/`: two or three hooks (the first 3 seconds), two lengths per hook (a 6-second cut and a 15-second cut), plus end cards under `assets/endcards/`. All generated before the demo (see Aayush). Nothing is generated at serve time; BFL is never called on an impression.
- **Player and events.** A plain `<video>` element in a phone-shaped frame with a CTA overlay and an end card. It emits `impression`, `tick` (once a second, with `currentTime`), `quartile` (25/50/75/100), `skip`, `mute`, `unmute`, `cta_shown`, `cta_tap`, `endcard_shown`, `install` (simulated), `close`. A judge watching is one impression; an **impression simulator** replays scripted sessions (skip at 3 s, watch to 75% and tap, mute and complete) so a cohort forms in the time a demo allows. The panel labels simulated impressions as simulated.
- **Serve beats, not playback frames.** `policy.decide(snapshot)` runs once per impression, at serve time, and optionally once at the end card. It returns `{variant: id, hook: id, length: 6 | 15, ctaAt: seconds, endCard: 'install' | 'watch_again' | 'learn_more'}`. The player reads those values and nothing else changes. Nothing decides mid-playback; a video does not wait for a model.
- **Two policies, one interface.** `ScriptedPolicy` is rules plus a small bandit over the arm space (variant × hook × length × CTA timing × end card), so a serve always has an answer. `ModelPolicy` posts the compact snapshot to `llama-server`, waits up to a deadline (a few hundred ms is generous at serve time; tuned on the demo machine), and falls back to scripted on timeout or an illegal answer. The panel says which one answered and why.
- **Model.** `llama-server` (OpenAI-compatible, `LFM2.5-230M` or `LFM2.5-350M` Q4_0 GGUF, already on disk, `n_ctx` small, `max_tokens` capped, temperature 0.1). Constrained output (JSON schema or GBNF) if unconstrained JSON is flaky; code rejects anything outside the legal arm set either way. Jev is a third button only if a key is already in hand, and it is labelled as a cloud call.
- **State reducer.** Keep per impression: variant, hook, length, watch-time bucket, highest quartile, skipped-at, muted, CTA shown and tapped, install, impression open. Keep per cohort: arm served and reward (reached 75%, tapped CTA, installed, skipped). Drop per-second ticks once the quartile is counted, events from closed impressions once folded into the cohort row, and any arm no longer in the test. A toggle appends the raw log so judges can watch the stuffed version get slower and worse. No lift is claimed that was not measured.
- **Why the decision is beside the creative, not in it.** A video ad is an MP4 the network's own player runs; nothing of ours executes inside it, so there is no "on-device" seat for the decision in the creative. The decision runs at serve time on a server: ours today (`llama-server` on the laptop), an ad server or our own SDK later. On-device is not where a video ad decision runs. LFM2.5 is still the right size for that server loop because the state is compact; the research on where a local model can sit is in [on-device-game-decisions.md, "Where a local model can sit"](docs/research/on-device-game-decisions.md#where-a-local-model-can-sit).
- **How it maps to a real network later.** Upload the variant MP4s and end cards as ordinary creatives. The serve loop keeps its cohort state on our side and edits the next flight's variant weights, CTA timing, and end-card choice between impressions or between reporting pulls. The video files never change at serve time.

## Team and ownership

Three owners, one hand-off interface each. Files named here are the contract; the repo layout is Bourke's.

### Thomas: marketing schema, Nimble process, video scripts and hooks

- **Deliverables.** `schema/marketing.schema.json`: the vocabulary the whole system shares (campaign, video variant, hook, length, decision arms, reward definition, cohort). A Nimble process that pulls web data on the target category (store listing copy, competitor vertical video hooks and CTAs, genre norms) and turns it into `scripts/*.json`: the video scripts the generators work from (hook lines for the first 3 seconds, on-screen text and voice-over per beat, CTA copy and default CTA timing, end-card text per variant) and the default arm priors the `ScriptedPolicy` ships with. A one-paragraph "why these defaults" note per script.
- **Later, maybe.** Campaign generation with Facebook (Meta): turn a cohort result plus the schema into a campaign brief or creative set. Not in scope before 16:30.
- **Hand-off to Bourke.** Schema v0 by 12:45 so the reducer and policies type against it. First `scripts/default.json` by 14:30. Changes after 15:30 are copy only, no shape changes.
- **Hand-off to Aayush.** Hook lines, on-screen text, and end-card copy (`install`, `watch_again`, `learn_more`) by 13:00 so video prompts, overlays, and text match. Video generation is asynchronous and cannot start without the hooks.

### Bourke: infrastructure for Long Horizon in GitHub: web, agents, RSI

- **Deliverables.** This repo: player harness under `web/` (phone frame, `<video>`, CTA overlay, end card, impression simulator), decision agent under `agents/` (StateReducer, ScriptedPolicy, ModelPolicy, llama-server client, deadline and fallback), the kept-versus-dropped panel, build scripts, README with run steps. `llama-server` running LFM2.5 230M or 350M on the demo laptop. **RSI: to define.**
- **Hand-off interface.** Consumes `schema/marketing.schema.json` and `scripts/*.json` from Thomas; consumes `assets/video/{hook}-{length}.mp4` and `assets/endcards/{install,watch_again,learn_more}.png` from Aayush. Exposes the `Decision` type and the `snapshot` shape in `agents/types.ts`; anything Thomas or Aayush needs from the runtime is read from there, not from the player.

### Aayush: content generation (video variants)

- **Deliverables.** 9:16 video variants generated before the demo with the Black Forest Labs FLUX 3 video API, plus end cards with the BFL image API. The API shape and pricing (async `POST`, then poll until ready; priced per second of output; result URLs expire; image URLs expire sooner) are recorded in [on-device-game-decisions.md, "What the same introduction offers besides Action"](docs/research/on-device-game-decisions.md#what-the-same-introduction-offers-besides-action); download every result the moment it is ready and commit it to `assets/`, do not link to a BFL URL from the harness. Target set: two or three hooks × two lengths (6 s and 15 s), all 9:16, from Thomas's hook lines, image-to-video from a shared hero still where that keeps the variants visually consistent. Three end cards matching Thomas's copy. A `content/README.md` with prompts, routes, modes, sizes, and cost per clip so they are reproducible.
- **Constraints.** Live choice is which clip, not a new generation; BFL is never called on an impression. Keep total generated seconds small and generate the short cuts first; the plan needs a handful of clips, not a library. Every clip must play in a plain `<video>` tag (H.264 MP4, 9:16, e.g. 1080×1920 or the smallest size the API offers at that ratio). PNG end cards at 1080×1920 or 540×960.
- **Hand-off to Bourke.** Placeholder set (solid colour plus hook text, made with ffmpeg, no BFL) by 12:30 so the harness never waits on generation. Real variants land as they finish, final set by 14:30. Anything still generating at 15:30 is out of the demo.

## Timeline (Pacific, against today's agenda)

| Time | Agenda | Team |
| --- | --- | --- |
| 11:00 | Kickoff and hack | Done. Research landed; plan committed at ~12:00; pivot to video at ~12:10. |
| 12:00–13:30 | | Bourke: player harness with placeholder clips, event log, `ScriptedPolicy` round trip, confirm GGUF is on disk and `llama-server` answers. Thomas: schema v0 (12:45), hook lines to Aayush (13:00), start Nimble pull. Aayush: BFL key and credit check, ffmpeg placeholders (12:30), first FLUX 3 video jobs submitted. |
| 13:30 | Lunch | Eat. Duration is not published; assume 30–45 min. Video jobs keep running. |
| 14:15–15:30 | | Bourke: `StateReducer`, `ModelPolicy` with deadline and fallback, kept/dropped panel, raw-log toggle, impression simulator, cohort replay button. Thomas: `scripts/default.json` (14:30), copy review. Aayush: final clips and end cards (14:30), prompts README. |
| 15:30–16:15 | | Freeze features. Everyone: rehearse the 60-second demo twice on the demo laptop, fix what breaks, README run steps, confirm every clip in `assets/` plays offline. |
| 16:15–16:30 | | Submit. Commit, push, tag `v0.1-submission`. |
| 16:30 | Project submission | Format is not published; have the repo URL, a one-paragraph description, and the laptop ready. |
| 17:00 | Finalist demos and judging | Demo from the laptop. Someone else watches and skips. |
| 19:00 | Awards and closing | |

**What fits by 16:30.** The 9:16 player in the harness with an impression simulator, scripted policy always on, model policy with fallback on localhost, the kept-versus-dropped panel, one cohort replay, a handful of pre-generated FLUX 3 clips and three end cards committed to the repo. That is about 4.5 hours of hacking minus lunch.

**What does not fit, and is not promised.** Nimble-to-Meta campaign generation, Jev integration (no key in hand; label it a cloud call if one appears), a Tinybird sink, a Meta or any network upload, any fine-tune, FLUX 3 Action, a phone embed, a defined RSI, measured engagement lift, real impressions from real users. If the model policy is still flaky at 15:30, the demo ships scripted-only with the panel and the model as a visible "advisor" whose answers are shown but not applied.

## Demo script (60 seconds)

1. **0–10 s.** "This is a vertical video ad. The file is inert; every decision about it happens at serve time, between impressions. The agent that makes those decisions runs for the life of the campaign, so its state has to stay small." Point at the harness: phone frame on the left, panel on the right, `llama-server` log in a terminal.
2. **10–30 s.** Judge watches variant A (hook 1, 15 s). They skip at about 4 seconds. Panel shows `impression`, four `tick`s arriving, the reducer folding them into `watched: 4 s, quartile: 0, skip: true`, then the ticks greying out as dropped. Serve beat fires for the next impression. Panel: "decision: hook 2, 6 s cut, CTA at 2 s. By: LFM2.5-350M, 180 ms." Variant B starts.
3. **30–40 s.** Judge lets variant B run, passes 75%, taps the CTA. End card `install` shows. Panel shows the arm that was served, the reward that was recorded, and the cohort row updating.
4. **40–50 s.** Flip the "append raw log" toggle, replay the same two impressions. Panel shows the prompt growing, latency climbing, and the fallback firing on a missed deadline: "By: ScriptedPolicy (model late)." That is the failure mode the hackathon is about.
5. **50–60 s.** Press "next cohort." Fifty simulated impressions collapse into one cohort row, the hook prior shifts toward hook 2, the individual impressions' events are gone. "Upload these MP4s to any network as they are. The agent stays here, keeps this one row, and picks the next serve."

## Risks and fallbacks

| Risk | Fallback |
| --- | --- |
| GGUF not on the demo laptop; venue Wi-Fi too slow to fetch it | Check at 12:00. If missing, download over a phone hotspot immediately or use any LFM2.5 GGUF already on any team machine. Demo ships scripted-only if none arrives by 15:00. |
| Small model returns malformed or illegal JSON | GBNF grammar or JSON schema on `llama-server`; code rejects illegal arms; scripted policy answers; panel shows the rejection. |
| Model latency too high | Serve-time decisions have no viewer waiting mid-play, so the deadline can be generous; it is still tuned on the machine at 12:30, and late answers are dropped, not applied late. |
| FLUX 3 video jobs slow, queued, or failing | Submit the first jobs before 12:30 and keep them short. The ffmpeg placeholder clips are already in the build; the demo runs on placeholders if real clips miss 15:30. |
| BFL result URLs expire before download | Poll and download in the same script; commit to `assets/` on arrival; never reference a BFL URL from the harness. |
| BFL key or credits missing, or per-second pricing burns the budget | Placeholders by 12:30; generate 6-second cuts first and stop when the demo set is in hand. |
| No real impressions | The impression simulator is labelled as simulated on the panel. Nobody presents it as traffic. |
| Nimble access or schema slips | Bourke types against a hand-written schema v0 at 12:45 and Thomas's later changes are copy-only. |
| Submission format is unknown | Repo URL, one paragraph, and a laptop. Tag the commit. |
| Someone claims a lift | Nobody does. The panel shows decisions, kept state, and dropped events. Engagement lift is future work. |
| Scope creep toward a network upload, Jev, Tinybird, a phone | Not before 17:00. Anything not in "What fits by 16:30" waits. |

## Source docs

- [docs/research/project-context.md](docs/research/project-context.md): event brief, product target as written before the pivot, workstreams.
- [docs/research/on-device-game-decisions.md](docs/research/on-device-game-decisions.md): Liquid LFM2.5, Jev, Black Forest Labs (FLUX 3 video and image API, FLUX 3 Action), network rules, where a local model can sit, smallest build.
- [docs/research/open-source-playables.md](docs/research/open-source-playables.md): the playable template that was the plan before the pivot; kept for the record.

## Changed from playables

At ~12:10 Pacific the product changed from a playable ad to a mobile vertical video ad (9:16). The research docs above were written for the playable target and are unchanged; read them with these substitutions. The in-play clickstream (taps, swipes, dwell, fails) becomes the video engagement stream (impression, watch time, quartiles, skip, mute, CTA tap, install). In-play decision beats (difficulty, pacing, hint) become serve-time decisions (variant, hook, length, CTA timing, end card). The smoud Pixi template and the `postMessage` bridge are dropped; the creative is now an MP4 the network's player runs, so the "no external calls from the creative" table no longer constrains us, and the decision runs on a server by design. The Black Forest Labs section is now central rather than peripheral, and it is the FLUX 3 hosted video API, not FLUX 3 Action, that we use. Everything about LFM2.5, Jev, compact state, and the kept-versus-dropped panel carries over as written.
