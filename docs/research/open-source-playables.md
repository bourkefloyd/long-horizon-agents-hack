# Open-source playable ads for the Long Horizon Agents Hackathon

Scope (revised 25 Sep 2026): the target is a **playable ad**, not a full casual game. A local model reads the clickstream from plays of the ad and makes decisions that should raise engagement (difficulty, pacing, CTA timing, end card). Everything below was checked against GitHub on 25 Sep 2026 via the GitHub API, raw file fetches, and where noted an actual clone-and-build on this machine. No repo is listed that was not confirmed to exist.

## Recommendation

**Fork [smoudjs/playable-template-pixi](https://github.com/smoudjs/playable-template-pixi) (PixiJS 8 + `@smoud/playable-sdk` + `@smoud/playable-scripts`).**

Why: it is the only candidate that, in one `npm install && npm run build <network>`, produced a single self-contained HTML file for AppLovin, Unity Ads, ironSource and Meta and a ZIP for Google and Mintegral, all well under the 5 MB ceiling (607 KB HTML, 213 KB ZIP), in about 10 seconds on this machine. The SDK already emits a unified event stream (`pointerdown/move/up` with coordinates, `interaction` count, `start`, `finish`, `install`, `retry`, `pause`, `resume`) across MRAID, DAPI, `FbPlayableAd`, `ExitApi` and `window.install`, so the clickstream is mostly there and the decision hook is a small object in one file (`src/Game.ts`). The SDK and build tool are MIT and were pushed this month. The template repo itself carries no LICENSE file (see caveat below), but it is about 130 lines of glue you will rewrite anyway.

Runner-up: same stack with Phaser ([smoudjs/playable-template-phaser](https://github.com/smoudjs/playable-template-phaser), 1.27 MB output) if the team prefers Phaser scenes to raw Pixi.

## Size and delivery constraints (why most game engines drop out)

Network rules as summarized by the Defold playable-ads README and the smoud SDK references (re-check the network docs before submitting anything real):

- Meta: single HTML with assets inlined as data URIs, reported as 2 MB; ZIP up to 5 MB accepted since 2020. CTA through `FbPlayableAd.onCTAClick()`. No external requests.
- Google Ads: ZIP, max 5 MB, max 512 files, must call `ExitApi.exit()`.
- AppLovin and Unity Ads: single HTML, max 5 MB, MRAID.
- ironSource: single HTML, MRAID or DAPI.
- Mintegral: ZIP plus `window.install` and a retry callback; special viewport.

Consequence for the hack: a Godot 4 or Flutter web export ships an engine runtime that alone is far above 5 MB, and Unity WebGL is worse. Only plain web, PixiJS, Phaser, Defold (with the engine binary trimmed and embedded) and Cocos Creator fit. That is why the Godot and Flutter candidates from the earlier casual-game pass were dropped (details at the end).

Second consequence: most networks forbid outbound network calls from inside the ad. A 1.2B on-device model cannot live inside a 600 KB HTML file, and the ad cannot call `localhost:8080/v1/chat/completions` in production. For the hack demo, run the single-file ad inside a harness page on the laptop, forward events to the model with `window.parent.postMessage`, and send decisions back the same way. Inside the ad, keep a scripted fallback so the file is still a valid standalone playable. See "Where the decision hook goes".

## Ranked candidates

| Rank | Repo | License | Engine | Last push | Single file < 5 MB? | Verdict for a one-day hack |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | [smoudjs/playable-template-pixi](https://github.com/smoudjs/playable-template-pixi) + [smoudjs/playable-sdk](https://github.com/smoudjs/playable-sdk) + [smoudjs/playable-scripts](https://github.com/smoudjs/playable-scripts) | Template: **no LICENSE file** (GitHub template repo, `license: null`, no `license` field in `package.json`). SDK: MIT. Scripts: MIT. | PixiJS 8, TypeScript, webpack via `playable-scripts` | Template 2026-02-11; SDK 2026-09-04; scripts 2026-09-02 | **Yes, verified.** 607,019 B HTML (AppLovin), 606,194 B (Meta), 607,051 B (ironSource), 607,019 B (Unity); 213 KB ZIP (Google, Mintegral). `npm install` + build ~10 s. | **Pick this.** Unified event API, 25 networks, `--protocol mraid|dapi`, Google `ExitAPIInjectorPlugin`, dev server with hot reload. |
| 2 | [smoudjs/playable-template-phaser](https://github.com/smoudjs/playable-template-phaser) | Same as above (template unlicensed; SDK/scripts MIT) | Phaser 3, TypeScript | 2026-02-11 | **Yes, verified.** 1,269,371 B HTML (AppLovin). | Same hooks as #1, 2x the size because Phaser is bundled. Use if the team already knows Phaser scenes. |
| 3 | [indiesoftby/defold-playable-ads](https://github.com/indiesoftby/defold-playable-ads) | MIT (GitHub API) | Defold 1.11.1, Lua, Gulp build | 2026-08-05 | Yes per README: example build "less than 1 megabyte", engine Zstd-compressed and Base64-embedded. Not built here (needs Defold's remote extender, README says 1–2 min per build). | Solid, actively maintained, supports Google, Meta, Mintegral, Unity, AppLovin. Costs a Lua/Defold ramp-up and a remote build step; network detection lives in `engine_template.html` (`window.Playable.gameLoaded/gameEnd/install/retry`). Second choice if someone on the team already uses Defold. |
| 4 | [Qugurun/phaser-to-playable-ad-html5](https://github.com/Qugurun/phaser-to-playable-ad-html5) | MIT (GitHub API) | Phaser 4.0.0-rc.4, Vite 6, Spine 4.2 | 2025-09-14 | Yes per README: `tools/inline-bundle.js` merges bundle into `index.html`, `tools/packer.js` compresses it with embedded pako inflate; assets auto-converted to base64. Not built here. | Good single-file pipeline but no network abstraction (README targets Meta), Phaser 4 is still a release candidate, and a pako-inflate wrapper makes some validators nervous. Use only as a reference for the inliner. |
| 5 | [ppgee/cocos-pnp](https://github.com/ppgee/cocos-pnp) | MIT (GitHub API) | Cocos Creator 2.4.x / 3.8.x plugin | 2024-06-07 | Yes per README (multi-channel single-file export). Not built here. | 385 stars, 11 networks (AppLovin, Facebook, Google, ironSource, Liftoff, Mintegral, Moloco, Pangle, Rubeex, TikTok, Unity). Requires installing the Cocos Creator editor and learning its build UI; too much setup for a one-day hack unless someone already has Cocos installed. |

### Tooling worth knowing, not a template

- [mraid/webtester](https://github.com/mraid/webtester), BSD-2-Clause, last push 2023-07-31, marked "unattended" in its README. A local web MRAID v2 container that renders your HTML tag and logs every MRAID call. Useful as the laptop harness for the demo: it shows `mraid.open`, viewability and state changes in a console.
- [songhuixiang/playable-demo](https://github.com/songhuixiang/playable-demo) ("Bingo"), MIT, last push 2026-09-13. Desktop app that wraps a Cocos Creator web build for 20+ networks and generic MRAID, with WebP + Base122 asset packing. Chinese-first docs. Not a template and tied to Cocos; skip for the hack.
- Smaller MIT helpers seen in search, not evaluated: [reybits/playable-ads](https://github.com/reybits/playable-ads) (11 KB TypeScript playable engine, 2026-03-01), [rafalfaro18/facebook-playable-ad-demo](https://github.com/rafalfaro18/facebook-playable-ad-demo) (2020).
- No official template repos from AppLovin, Unity Ads, ironSource, Meta, Google or Mintegral turned up on GitHub. Those networks publish specs and preview tools, not forkable code. The smoud SDK README links the preview tools: AppLovin playable preview, Unity Ad Testing app, Meta Playable Preview, Google H5 validator, ironSource HTML upload, Mintegral Playturbo review, Moloco Creative Lab.

## Clickstream: what each candidate already emits

**smoud `@smoud/playable-sdk`** (verified in `src/interaction.ts`, `src/events.ts`, `src/tracking.ts`, `src/core.ts`, 897 lines total):

- `pointerdown (x, y, event)`, `pointermove (x, y, event)`, `pointerup (x, y, event)`: unified mouse/touch, no duplicates; `pointermove` and `pointerup` only fire while pressed; move listeners are attached lazily on first `sdk.on('pointermove')`.
- `interaction (count)`: incremented on every `pointerdown`; `sdk.interactions` holds the total.
- Lifecycle: `init`, `boot`, `ready`, `start`, `pause`, `resume`, `volume(level)`, `resize(w,h)`, `retry`, `finish`, `install`, `error(message, action)`.
- Network-side tracking is automatic for some networks (`tracking.ts`): Bigabid engagement on first interaction and "complete" after 3 interactions; inMobi `First_Engagement`; Remerge engagement. Be aware that the SDK treats the 4th tap as "complete" on those networks regardless of your game state.
- Not emitted; add in game code: swipe direction (derive from `pointerdown` + `pointerup` deltas), dwell / idle (a timer reset on `pointerdown`), level fail / level clear, CTA shown, end-card shown, end-card variant. These are ~30 lines in `src/Game.ts`.

**indiesoftby/defold-playable-ads**: lifecycle only (`gameLoaded`, `gameEnd`, `install`, `retry`) via `window.Playable`; pointer events come from Defold's `on_input` in Lua. Everything else is yours to add.

**Qugurun / cocos-pnp**: no event layer at all; they are packagers.

## Where the decision hook goes (smoud Pixi template)

Files: `src/index.ts` (SDK init and event wiring, 20 lines) and `src/Game.ts` (Pixi app, install button, `sdk.on('interaction')` that calls `sdk.finish()` at 10 taps, 120 lines). Replace the button demo with a 20–30 second mini-loop (tap-timing, swipe-to-match, one-lane runner) and add:

1. **Event log.** A `ClickstreamLog` that appends `{t, type, x, y, ...}` on `pointerdown/up`, derived `swipe`, `idle` (no `pointerdown` for N ms), `level_fail`, `level_clear`, `cta_shown`, `cta_tap` (wrap the existing `sdk.install()` call), `endcard_shown`. Keep it under a few hundred entries; the "explicit mutable state" theme of the hackathon maps directly onto summarizing this log into a small state snapshot before each decision.
2. **Decision beats.** Call `director.decide(snapshot)` at fixed beats, not every frame: on `start`, after each `level_fail` or `level_clear`, after K seconds idle, and just before `finish`. The snapshot is the compact state (taps so far, fails, mean reaction time, time since last input, orientation, current difficulty, CTA already shown?).
3. **Decision surface.** `decide` returns `{difficulty: 1..5, pacing: spawnIntervalMs, ctaAt: 'now' | 'afterNextClear' | 'atFinish', endCard: 'win' | 'almost' | 'retry'}`. The game reads these values; nothing else changes.
4. **Two directors behind one interface.** `ScriptedDirector` (rules, ships inside the HTML so the ad stays valid on every network) and `ModelDirector` (posts the snapshot with `window.parent.postMessage` and waits up to a deadline for a reply; on timeout falls back to scripted). The harness page on the laptop hosts the ad in an iframe, calls `llama-server` on localhost with the snapshot, and posts the decision back. This keeps the production file network-free and still demos the on-device model live.
5. **Network gotchas.** Call `sdk.finish()` only when the end card is actually shown; the SDK exposes `sdk.isFinished` and the template's default fires it at 10 taps, which you will remove. Keep `sdk.install()` as the only CTA action. Test with `npm run dev` (port 3000 by default, `--port` to change), then `npm run build applovin` and drop the HTML into the AppLovin web preview, or run it in `mraid/webtester` locally.

For Defold the equivalent hook is a Lua `director.script` called from the game's `on_message` at the same beats, with `html5.run` bridging to `window.parent.postMessage`.

## Casual-game candidates from the first pass

Kept only if they can be cut down to a sub-5 MB single-file playable:

- **[gabrielecirulli/2048](https://github.com/gabrielecirulli/2048)**: MIT (`LICENSE.txt` confirmed), plain JS, last push 2024-10-24, 13.4k stars. `js/*.js + style/main.css + index.html` total **48 KB**; touch swipe is built in (`keyboard_input_manager.js`). Cuts to a playable in an hour: inline the scripts and CSS into `index.html`, cap it at ~20 moves or 60 seconds, add an install button wired to `sdk.install()`. Decision hook: the tile-spawn position and value are already a per-move random choice in `game_manager.js` (`addRandomTile`), so the director can steer difficulty per move, and the CTA/end card can trigger on a stall. Best fallback if the team wants a recognizable game loop inside the smoud template.
- Dropped: [luiz734/match3_game](https://github.com/luiz734/match3_game) (MIT, Godot 4, 2024-12-11) and [guladam/deck_builder_tutorial](https://github.com/guladam/deck_builder_tutorial) (MIT, Godot 4, 2024-10-16, 453 stars): Godot 4 web export runtime far exceeds 5 MB. [flutter/games](https://github.com/flutter/games) (BSD-3, 2026-09-14): Flutter web runtime too large for a single file. [P1X-in/tanks-of-freedom-ii](https://github.com/P1X-in/tanks-of-freedom-ii) (MIT, Godot 4, 2025-10-02): 3D, desktop-only per its design doc. [oskarrough/slaytheweb](https://github.com/oskarrough/slaytheweb) (2026-05-29): AGPL-3.0, not permissive. [Hextris/hextris](https://github.com/Hextris/hextris) (2023-05-13): GPL-3.0.

## Verification log

- GitHub API `GET /repos/...` for every repo above: `license.spdx_id`, `pushed_at`, `default_branch`, `is_template`, `archived`.
- LICENSE text fetched and read for smoud `playable-sdk` (MIT, "Copyright (c) 2025-present Smoud"), 2048 (`LICENSE.txt`, MIT), flutter/games (BSD-3 style, Chromium Authors), Hextris (`LICENSE.md`, GPL-3), Tanks of Freedom I and II (`LICENSE.md`, MIT).
- Clone and build on this machine (Node 22.14, npm 10.9): `smoudjs/playable-template-pixi` at commit `40fa379` built for `applovin`, `facebook`, `unity`, `ironsource`, `google`, `mintegral`; output files and byte sizes listed in the table. Built HTML inspected with ripgrep: MRAID builds contain `mraid.addEventListener/getState/getMaxSize/getAudioVolume/isViewable/open`; Meta build contains `FbPlayableAd.onCTAClick`. `smoudjs/playable-template-phaser` built for `applovin`: 1,269,371 B.
- `smoudjs/playable-sdk` cloned; `src/` is 897 lines across `index.ts`, `interaction.ts`, `protocols.ts`, `events.ts`, `tracking.ts`, `core.ts`.
- Defold, Qugurun, cocos-pnp, mraid/webtester, Bingo: README read, not built.
