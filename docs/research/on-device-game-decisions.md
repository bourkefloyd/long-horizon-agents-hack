# On-device decisions inside a playable

Reference for the [Long Horizon Agents Hackathon](https://luma.com/horizonagentshack). Checked against public docs on 25 September 2026.

The hackathon problem: agents get worse as a session runs because they keep every observation, action, and stale note. The architecture they want is explicit mutable state, an agent that edits its working context, and a split between what persists and what is thrown away.

The first cut of this note was a playable where a **local** model makes decisions during play. The target below replaces that: decisions on a playable **ad**, driven by the clickstream. Two names were attached to the original idea. They are not the same product.

- **Liquid AI** ships weights you can run on a laptop, in a browser, or inside an iOS/Android app.
- **Jev** (TypeSafe) is a hosted decision API. Official docs describe no on-device runtime.

Nothing below is a measurement from this hack. Vendor latency and price figures are quoted only where the vendor published them, and they are labeled as such.

## Target: clickstream-driven playable ad decisions

The model has to react to how people play a playable ad. Events are taps, swipes, dwell, drop-off, and the rest of a session. Decisions should change engagement: difficulty, pacing, when the call-to-action appears, whether to hint, which end card to show, when to ask for the install. Two clocks are allowed. **Per play**, while the session is open. **Per cohort**, after sessions end, before the next ones start.

A session and a campaign both get longer. The agent keeps a compact mutable state and drops stale events. Appending the raw clickstream is the failure mode.

Whether the creative can call out depends on the network. The check is below. On the networks that publish a rule, the ad file cannot ask a model server during play. A local model fits on a laptop beside the page, or inside an app you own. It does not fit in the creative.

### Liquid LFM2.5

The weights cannot live in the ad. Smallest confirmed GGUF is 149 MB (230M Q4_0). The ad is also forbidden from calling out, so a compliant AppLovin file cannot ask a Liquid server for the next beat either.

Places a Liquid model can still sit:

| Where | What it sees | Latency, as far as the docs go |
| --- | --- | --- |
| Advertiser server (`llama-server` / Ollama on a machine you control) | A compact state POSTed by **your** page, not by an AppLovin creative | One network round trip plus generation. Liquid publishes no milliseconds for a short action. Their hardware recipe is 256–1024 input tokens and 100 output tokens. A clickstream decision is a smaller prompt and a few tokens out, and that timing was not measured. Fine between plays. During a play it misses a 16.7 ms frame. It can still land on a beat (after a fail, before the end card) only if you time it on that machine. |
| SDK host app | The host already has the GGUF (Liquid’s mobile guide downloads it into app-private storage, 149–696 MB). The host reads events from the creative and applies the decision. | No cloud round trip after the weights are local. Decode time is still unpublished for this prompt. Whether a given ad SDK lets the host write difficulty or a CTA back into the HTML was **not** verified. |
| Offline, between plays | A cohort table: counts, last policy, reward (completed, dropped, tapped install) | No player is waiting. This is the comfortable Liquid fit. 230M or 350M is enough. Instruct only if the 696 MB file is already on disk. |

Do not send the event log. Count taps, swipes, and dwell in code. Put the counts, the current policy, and the open question in the prompt. Drop coordinates once they have been counted, drop events from finished sessions, drop the previous completion.

### Jev (TypeSafe)

Closer to this job than a generative checkpoint. Docs: one `state` (string, JSON object, or array of text) and several typed questions, answered in parallel. A clickstream summary is a JSON object. The questions are the decisions.

| Decision | Question type in their docs |
| --- | --- |
| Show the install prompt now? | Noul (probability of yes) |
| Which end card? | Choice, up to 255 options |
| How stuck does this session look? | Score, 2–10 ordered levels |

Code applies thresholds. Their jaggedness note says counting and arithmetic belong in code, and that extra unrelated state causes context rot. So the request is the compact state, not the tap log. Raw coordinates and old sessions are stale context.

Vendor figures, not measured here. [Models page](https://docs.typesafe.ai/models): **$0.042 per million input tokens**, output free; context **64k** for the request and **32k** for state plus the longest question; rate limits they publish (250,000 tokens/s and 1,200 requests/min) can change without notice. Launch post, 15 September 2026: end-to-end **70–500 ms**, from their laptops on the US West Coast to the service they were hosting. That is a network number. It is not a phone, and it is not a guarantee on venue Wi-Fi. Early access and an API key. No on-device weights in the docs.

Per play, inside an AppLovin file: **no**. The call is an external request. Per play, on your own page or from a host that is allowed to call out: possible on a beat, if 70–500 ms is acceptable and the key exists, with a rules fallback when it is late. Per cohort, between plays: the better fit. Batch the compact states. No one is tapping during the round trip.

### Black Forest Labs

Not the decision. From [their introduction](https://docs.bfl.ai/quick_start/introduction) and the pages it opens, the API returns images, video, and audio. FLUX 3 Action emits robot or fine-tuned game controls from **frames**, not from a clickstream, and it is not on `api.bfl.ai`. Use BFL to **prepare** end-card or background variants before the demo. A rule, a bandit, Jev, or Liquid picks which variant to show. Do not generate a creative on the tap.

### Baseline: rules or a small bandit

This is the path that can actually run inside the 5 MB file. No weights, no network. The hackathon story still applies, because the policy is only as good as the state it is allowed to see.

Keep, per session: taps, swipes, dwell bucket, fails, current difficulty, whether a hint or CTA is already showing, last decision, and whether the session is still open. Keep, per cohort: which arm (difficulty, end card, CTA timing) was shown, and the reward you defined (reached the end card, tapped install, dropped). Drop: raw positions after the count, events from closed sessions, and any arm that is no longer in the test. A stuck rule can lower difficulty after N fails. A bandit can shift the end card between plays. Both edit a small state instead of replaying the log.

### Can a playable make network requests?

Checked 25 September 2026 against the page named on each row. If a cell says “not published,” that page does not say. WebAssembly is not named on any of them. A `.wasm` file is also absent from Google’s published HTML5 type list, which is the only place a file-type rule exists.

| Network | Package and cap | Outbound during play | What they allow instead | Script |
| --- | --- | --- | --- | --- |
| [AppLovin](https://support.applovin.com/en/growth/promoting-your-apps/welcome-to-applovin/creative-specs-and-guidelines) | One HTML file, 5 MB or smaller. Resources in base64 or base122. | No. “External network calls are prohibited.” That covers fetch, XHR, and WebSocket. | `mraid.open()` for the click-through. No store redirect on the first tap, and no auto-redirect. MRAID 2.0. Their [analytics page](https://support.applovin.com/en/growth/promoting-your-apps/welcome-to-applovin/playable-analytics-integration) is an SDK object, `ALPlayableAnalytics`, not an HTTP call from the file. A tracking pixel is an external call. | The script is inside the one HTML file. WASM not published. |
| [Unity Ads](https://docs.unity.com/en-us/grow/acquire/creatives/playable/specifications) | One `index.html`, inlined and minified, under 5 MB. MRAID 3.0. | “Should not need any network requests (XHR).” Analytics “may be permitted” if they have no personal data and follow the law. WebSocket is not named. | `mraid.open` straight to the store. No automatic store redirect. Wait for `viewableChange` before play starts. | Assets inlined in the HTML. WASM not published. |
| [ironSource Exchange](https://docs.unity.com/en-us/grow/programmatic/ironsource-exchange/mraid-specifications-guidelines) | Not a playable-upload spec. MRAID 2.0 tag: a snippet, not a full document. “All assets + code downloaded to the device must be up to 4MB max.” | External assets must be absolute `https://` URLs. Outbound HTTPS for those assets is the published design. “No 3rd party real time blocking pixels.” WebSocket not named. A Unity LevelPlay page that restates a playable size cap or an XHR ban was **not found**. | `mraid.open(URL)` on click. The host draws the timer and the close button. | Raw HTML or JS. Inline script not forbidden by name. WASM not published. |
| Meta, including Audience Network placements. [Help Center](https://www.facebook.com/business/help/412951382532338) and [developer upload errors](https://developers.facebook.com/docs/app-ads/formats/playable-ad/) | Help Center: one HTML file, or a zip with `index.html` at the root, at most 100 files, archive 5 MB. The developer error table rejects a single HTML or an `index.html` over **2 MB**, and a zip over 5 MB. Both pages are official. The single-file cap disagrees. | Help Center: “No external network calls are permitted. For example, XMLHttpRequest is not allowed.” Also no dynamic loading from an external network. WebSocket is not named. The network-call ban is the rule that covers it. | `FbPlayableAd.onCTAClick()` for the store. JavaScript redirects are not allowed. Must work without `mraid.js`. | Single file: JS, CSS, images, and audio as data URIs. Zip: other assets by relative path. Those HTML and JS files still follow the no-network rule. WASM not published. |
| [Google Ads App campaigns](https://support.google.com/google-ads/answer/9981650?hl=en) | ZIP, maximum 5 MB, no more than 512 files. The [fix-issues page](https://support.google.com/google-ads/answer/12771973?hl=en) also says 320×480 and 480×320 assets can be up to 5.2 MB. | “No external references” except Google Fonts and Google-hosted jQuery, Greensock, and CreateJS. A fourth-party call can be disapproved. fetch, XHR, and WebSocket are not named. | Include `exitapi.js` and call `ExitApi.exit()`, or they add an Install button. Sound only after a user action. | Published types: `.CSS`, `.GIF`, `.HTML`, `.JPEG`, `.JS`, `.PNG`, `.SVG`. A `.wasm` file is not on that list. Inline script is not forbidden by name. Local storage cannot be used. |
| [AdMob HTML5 campaigns](https://support.google.com/admob/answer/6185487?hl=en) | ZIP, **150 KB** or smaller. Google Web Designer only. This is a campaign HTML5 ad, not the App-campaign playable above. | Images must be local, not referenced. fetch, XHR, and WebSocket are not named. | The destination URL is a campaign field. It is not a call the file makes. | Same file types as the row above, plus `.JPG`. WASM not listed. |
| [Ad Manager](https://support.google.com/admanager/answer/7046902?hl=en) | ZIP or a standalone HTML. The bundle, or the extracted files, cannot exceed 1 MB. The [API error](https://developers.google.com/ad-manager/api/reference/v202505/CreativeService.HtmlBundleProcessorError.Reason) says 1000 KB and at most 50 files. Served in SafeFrame. [Build guidelines](https://support.google.com/admanager/answer/7046799?hl=en). | Essential assets stay in the zip. External hosting only if Ad Manager has allowlisted it. fetch, XHR, and WebSocket are not named. | Click tags and exit events. Hard-coded click URLs are rejected. Impression tracking URLs are a setting on the creative, not a request the HTML invents mid-play. | Scripts live in the bundle. WASM not published. |
| Mintegral. [Asset specs](https://helpcenter.mintegral.com/en/docs/asset-specs), [creative guide](https://helpcenter.mintegral.com/en/docs/creative-management-guide), [Playturbo test guide](https://www.playturbo.com/review/doc) (linked from their [playable guide](https://helpcenter.mintegral.com/en/docs/playable-ad-guide)) | Asset table: HTML, single file, no more than 5 MB. Creative guide: playable upload is a URL or a ZIP. Playturbo: ZIP no larger than 5 MB, HTML openable locally, file names limited to letters, numbers, and underscores. The single-file line and the ZIP line are both published. | Playturbo: put dependent resources in the folder and make sure there is “no dynamical request” for them. WebSocket is not named. | `window.install()` for the store. The playable must not redirect itself. No auto-redirect. Close and loading chrome are theirs. Optional `window.HttpAPI.sendPoint` for up to five buried points. That is their function, not your URL. | JS and HTML may be files. Other files are base64. WASM not published. |
| Liftoff, formerly Vungle. [Interactive integration](https://docs.liftoff.io/liftoff_creatives/liftoff_creatives/interactive_api_integration) and [creative API](https://docs.liftoff.io/creative_integration_api) | One HTML file, or a zip of one folder, which they host on their CDN. Interactive page: HTML up to 5 MB. Creative API: they recommend under 700 KB, 1 MB at most, without video, and under 5 MB with video. A separate Vungle-branded playable spec was **not found**. | The creative loads its own assets by relative URL from their CDN, so those requests happen. Do not use absolute `http://` or `https://` URLs for assets. They do not publish a yes or no for fetch, XHR, or WebSocket to your server. Their CDN sends no CORS header for JS, and the blob workaround “does not allow importing external scripts from other origins.” | `mraid.open` or `window.open` after a deliberate tap. Not `window.location`. No iframes. | JS files in the zip are the normal path. Inline script is not forbidden by name. WASM not published. |
| [MRAID 3.0](https://iabtechlab.com/wp-content/uploads/2018/06/MRAID_3.0_FINAL_June_2018.pdf) (IAB Tech Lab, June 2018) | Not a package. No size cap. | The spec does not forbid fetch, XHR, or WebSocket. Section 2.4 says an offline ad needs store-and-forward metrics, and that how those metrics are reported is out of scope. | `open(url)` is the click-through. The host opens it with the device’s normal URL behavior. Hyperlinks must not be used. There is no separate store API. | HTML, JavaScript, and CSS are the assumed languages. The host injects `mraid.js`. WASM is not in the spec. |

### Where a local model can sit

A person meets the playable in one of three ways.

1. **An ad SDK inside someone else’s app.** The publisher integrated AppLovin, Unity, ironSource, and the rest. That SDK downloads the creative and runs it in its webview. You do not ship that app, so you cannot put llama.cpp in it. None of the pages above publish a JS bridge to a model.
2. **Cross-promo inside an app you own.** Your process owns the webview. Liquid’s mobile guide is this shape: llama.cpp in the app, GGUF downloaded into app storage, not sealed into the creative. The deprecated LEAP SDK is the other embed path. The playable talks to that process through a JS bridge you write (`WKScriptMessageHandler`, `JavascriptInterface`). That bridge is ordinary app code. It is not in any ad-network spec.
3. **A plain web link.** A browser, no ad SDK. The page may call `localhost` or a server. That request is normal web traffic. It is not a playable creative, and the caps above do not apply.

Against the preference for a local model:

- **Inside the ad file.** The smallest confirmed LFM2.5 GGUF is **149 MB** (230M Q4_0). 350M Q4_0 is 219 MB. 1.2B Q4_0 is 696 MB. The largest cap in the table is Google’s 5.2 MB interstitial note. No LFM weight fits. No sub-megabyte decision model showed up in these docs. What fits is a rule or a bandit, kilobytes of script, baked into the file. It can change difficulty during the play. On the networks that ban calls, it cannot fetch a new policy.
- **In the host, only when you own the host.** Cross-promo, or a shell you ship. Weights stay in app storage. The playable sends the compact state over the bridge and gets a decision back. Decode time for this prompt is still unpublished. It is not a 16.7 ms frame. This path does not exist while the playable is running in a publisher’s SDK.
- **On a server.** Jev, or Liquid behind `llama-server`. During a play, that call is an external request. AppLovin, Unity’s XHR line, Meta, Google App campaigns outside their library allowlist, and Mintegral’s Playturbo guide do not allow it from the creative. Between plays, the server updates the next file, or the numbers baked into the next bandit, and the SDK downloads that later. If you own the app, the native side can call Jev or a Liquid server and push the answer into the webview. The HTML still does not call out.

**Smallest demo that keeps the model local.** One page on the laptop. LFM2.5 230M or 350M Q4 already on disk, served by `llama-server`. The page POSTs the compact clickstream state to `localhost` and shows what was kept and what was dropped. That call is the stand-in for the JS bridge. The same request would be rejected inside the ad networks that ban external calls.

**How that maps later.** For a network creative, delete the call and ship the bandit, or bake the last cohort’s choice into the file. The model stays on your machine and only edits the next build. For an app you own, keep the same page in a WebView and replace `localhost` with the bridge to llama.cpp. Do not put the GGUF in the HTML.

## Hackathon frame

In-person, San Francisco. Doors 9:30, kickoff 11:00, submission 16:30, finalist demos 17:00. Team size at most four. Liquid AI is a partner. Viviana Márquez (Developer Relations) and Tianshu Yu (ML engineer) are speakers and judges.

A demo has to be playable by someone else in the room that afternoon. Store review, fine-tuning, and a from-scratch mobile engine do not fit that window.

## 1. Liquid AI

Source of truth: [docs.liquid.ai](https://docs.liquid.ai/lfm/models/complete-library), model cards on Hugging Face under `LiquidAI`, and the [LFM Open License](https://www.liquid.ai/lfm-license).

Liquid Foundation Models (LFM) are hybrid models (short convolutions plus grouped-query attention) aimed at fast inference and on-device deployment. Current generation is **LFM2.5**. LFM2 checkpoints are still listed; the docs say to prefer LFM2.5 when both exist.

### What can run locally today

Text models that matter for an in-game decision. “Local” here means the weights run in llama.cpp, Ollama, MLX, ONNX, the LEAP SDK, or Transformers on a machine you control.

| Model | Params | Context (as published) | Role |
| --- | --- | --- | --- |
| LFM2.5-230M | 230M | 32,768 tokens ([card](https://huggingface.co/LiquidAI/LFM2.5-230M)) | Smallest LFM2.5. Docs describe it for extraction and lightweight on-device agents. |
| LFM2.5-350M | 350M | 32,768 tokens ([card](https://huggingface.co/LiquidAI/LFM2.5-350M)) | Liquid’s recommended bring-up model for hardware profiling. |
| LFM2.5-1.2B-Instruct | 1.17B on the card; marketed as 1.2B | 32,768 tokens | Docs’ default for chat, instruction following, and tool calling. Details below. |
| LFM2.5-1.2B-Thinking | 1.17B on the card | 32,768 tokens | Reasoning variant. Poor fit for a short in-game beat. |
| LFM2.5-1.2B-JP | Docs say 1.2B; the card fetch did not restate 1.17B | 32K on the docs page; the card fetch did not restate it | Older Japanese chat. The hub also has JP-202606. |
| LFM2.5-1.2B-JP-202606 | 1.17B on the card | 32,768 tokens | Newer Japanese chat. English and Japanese only. |
| LFM2.5-1.2B-Base | 1.17B on the card | 32,768 tokens | Pretrained checkpoint. Not instruction-tuned. |
| LFM2.5-2.6B | 2.6B dense | **128K** on its [model page](https://docs.liquid.ai/lfm/models/lfm25-2.6b) | Agentic workloads, native tool calling. Page says it runs on a laptop or phone. That is their claim, not a measurement here. |
| LFM2.5-8B-A1B | 8B total, about 1.5B active (MoE) | 128K | Highest text tier in the current family. Laptop / single-GPU class, not a phone game. |
| LFM2-700M | 700M | Covered by the “most models are 32K” line | Previous generation. Android cookbook examples still use it. |
| LFM2-24B-A2B | 24B total, about 2B active | Not re-checked beyond the library | Largest listed. Laptop or one GPU. Skip for this hack. |

**Docs disagree on the 2.6B window.** The library overview and the FAQ say most LFMs are 32K and only LFM2.5-8B-A1B is 128K. The dedicated 2.6B page says 128K. Trust the model page for 2.6B, and do not plan a game around either number. A decision should see a small projection of state, not tens of thousands of tokens.

Also published, and the wrong tool if the game can pass structured state:

- Vision: LFM2.5-VL-450M, VL-1.6B, VL-3B. Extra `mmproj` file for llama.cpp.
- Audio: LFM2.5-Audio-1.5B. Liquid’s [Hand & Voice Racer](https://docs.liquid.ai/examples/web/hand-voice-racer) loads about **900 MB** at Q4.
- Nanos: extract, embed, translate, transcript. Narrow tasks, not a general action picker.

### File sizes that were actually on the Hugging Face file pages

| File | Size shown |
| --- | --- |
| `LiquidAI/LFM2.5-230M-GGUF` Q4_0 | 149 MB |
| same repo, Q4_K_M | 149 MB |
| Q5_K_M / Q6_K / Q8_0 | 172 / 191 / 247 MB |
| BF16 and F16 | 462 MB each |
| `LFM2.5-350M-Q4_0.gguf` | 219 MB |
| `LFM2.5-1.2B-Instruct-Q4_0.gguf` | 696 MB on the file page; 695,751,488 bytes in the tree API |

The full 1.2B quant ladder is in the next section. QAD Q4_0 checkpoints (quantization-aware distillation, distinct from the plain Q4_0 files) are published for at least the 230M, 350M, and 1.2B-Instruct GGUF repos. Liquid’s blog reports their own quality and throughput numbers for those. Those runs are not an in-game decision, and this note does not repeat the scores.

2.6B and 8B-A1B byte sizes were not copied here.

### License

[LFM Open License v1.0](https://docs.liquid.ai/lfm/help/model-license), based on Apache 2.0 with one commercial condition: free commercial use while annual revenue is under $10M. At or above that, the free commercial grant ends and you need a paid license (`sales@liquid.ai`). Research, education, and nonprofit use stay free with no revenue cap. Modifications can stay private. Weights are open-weight, not a full open-source training release. Hugging Face tags the license `lfm1.0`.

A hackathon demo is inside the free grant. Shipping a commercial game later is a license question only if the company crosses the threshold.

### How you call them

Documented runtimes:

- **llama.cpp.** `llama-cli` and `llama-server` (OpenAI-compatible). GGUF from `LiquidAI/<model>-GGUF`. Their laptop examples often pass `-c 4096`. Sampling published for LFM2.5-1.2B-Instruct and LFM2.5-230M: temperature 0.1, top_k 50, repetition penalty 1.05.
- **Ollama, LM Studio, Atomic Chat.** Local apps over the same GGUF idea.
- **MLX** on Apple Silicon. Docs recommend 8-bit there; 4-bit exists.
- **ONNX Runtime**, including browser examples (ONNX Runtime Web / WebGPU).
- **LEAP SDK.** The [deprecations page](https://docs.liquid.ai/lfm/help/deprecations) now says the LEAP SDK (iOS, Android, JVM, Kotlin/Native) and the LEAP bundling service are deprecated. The replacement they name is llama.cpp, used directly. A quick-start page for SDK `v0.10.7` was still online when this note was first drafted (iOS 17+, Android `minSdk` 31, 3 GB+ RAM). Do not start a new LEAP app for the hack. The 1.2B GGUF repos still contain a `leap/` directory; those files were not inventoried.
- **Embed llama.cpp yourself.** The current [iOS & Android guide](https://docs.liquid.ai/deployment/on-device/llama-cpp/mobile) says no wrapper SDK is required. Prebuilt `llama.xcframework` targets iOS 16.4+. Android path is the upstream `examples/llama.android` NDK sample or your own JNI. Download the GGUF on first launch into app-private storage. llama.cpp memory-maps the file, so it must be a real file, not a compressed asset. Their phone default quant is **Q4_0** (Arm kernels); Q4_K_M if you want quality over size. On Apple, `n_gpu_layers = 99` (Metal). On Android, CPU is the safe default.
- **Transformers, vLLM, SGLang.** Fine for a GPU laptop server. vLLM/SGLang are not the on-device path.

Chat template is ChatML-like (`<|im_start|>` …). Tool calls use `<|tool_call_start|>` … `<|tool_call_end|>`. The mobile guide also points at constrained decoding (JSON schema or a GBNF grammar). That page was not re-read line by line; use it if the action must be machine-readable. The game code should still reject anything outside the legal action set.

### Latency and context, for a decision during play

Liquid’s [hardware guide](https://docs.liquid.ai/guides/hardware-evaluation) tells you to measure on the target device: time to first token, decode tokens/sec, p50/p95 after one warmup, at 256/512/1024 input tokens and 100 output tokens, plus peak memory at context 256 through 4096. No tok/s figure from that guide is repeated here, because a game decision is a different workload: a few hundred tokens of state in, a few tokens of action out.

What the docs do say that changes the design:

- KV cache grows linearly with `n_ctx`. Keep the context at the size of the state projection, not at 32K or 128K.
- Weights can be mmap’d, which phones treat more gently than anonymous RAM. The cache cannot.
- More threads than big cores usually slows decode. Their starting point is `activeProcessorCount - 2`.
- The simulator is much slower than a device. LEAP says test on hardware; their SDK may crash loading bundles in an Android emulator.
- A Thinking checkpoint spends tokens on a trace. That is the opposite of a tight action. Use Instruct, 350M, or 230M, and cap `max_new_tokens`.

There is no published “milliseconds per in-game decision” number in the pages used here. Budget a decision **off** the frame loop until you have timed it on the demo machine.

### Poor fit for a one-day hack

- Fine-tuning (LEAP Finetune, TRL, Unsloth). The base Instruct/350M/230M models already take a state blob and a closed action list.
- LFM2.5-8B-A1B, LFM2-24B-A2B, and vision/audio checkpoints. Download size, RAM, and a second encoder.
- Embedding llama.cpp or LEAP into a store-ready mobile game the same day. Do the game on a laptop, or on a phone that already has the GGUF sideloaded.
- Filling the 32K window “because it fits.” That is the failure mode the hackathon is about.
- Per-frame calls. Decode will not share a 16 ms frame with rendering. Unmeasured, but the hardware guide’s own recipe is 100 generated tokens, which is already many frames.

### LFM2.5 1.2B

Checked 25 September 2026 against the docs pages for Instruct, Thinking, JP, and Base, the [migration guide](https://docs.liquid.ai/guides/migration-guide), the [ONNX](https://docs.liquid.ai/deployment/on-device/onnx) and [Ollama](https://docs.liquid.ai/deployment/on-device/ollama) pages, and the Hugging Face cards and GGUF trees named below. Docs market the class as 1.2B. Cards that state a count say **1.17B**. Context on those cards is **32,768** tokens, the same window as 230M and 350M. A 1.2B checkpoint does not give the game a longer memory.

License for the family is the [LFM Open License v1.0](https://docs.liquid.ai/lfm/help/model-license) (Hugging Face tag `license: other`; the Instruct GGUF readme names it `lfm1.0`). Each 1.2B GGUF repo listed here includes a `LICENSE` file. The JP-202606 file is 10,574 bytes and the others are 10,596. The text was not diffed.

Shared shape, where a card states it: 16 layers (10 convolution blocks + 6 grouped-query attention), vocab 65,536, knowledge cutoff mid-2024. Instruct’s card says “double-gated convolution.” Base and JP-202606 say “double-gated LIV convolution.” This note does not resolve that wording.

#### Checkpoints the cards actually separate

| Checkpoint | What it is | Params / context | Sampling on the card | Runtimes the card or docs name |
| --- | --- | --- | --- | --- |
| [Instruct](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct) | Chat, instruction following, tool calls. Docs’ default in this size. Card also says agentic tasks, extraction, and RAG, and not knowledge-heavy tasks or programming. | 1.17B / 32,768. Train budget 28T. Eight languages: EN, AR, ZH, FR, DE, JA, KO, ES. | temperature 0.1, top_k 50, repetition penalty 1.05 | Transformers, vLLM, SGLang, llama.cpp, MLX, LM Studio. ONNX and Ollama are in the deploy docs. |
| [Thinking](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Thinking) | Same family, trained for reasoning. Docs page: math, logic, multi-step problems, chain-of-thought, step-by-step decomposition. | 1.17B / 32,768. Train budget 28T. Same eight languages. | temperature **0.05**, top_k 50, repetition penalty 1.05 | Transformers, vLLM, llama.cpp, MLX, LM Studio. ONNX repo exists. No SGLang row on this card. |
| [JP](https://huggingface.co/LiquidAI/LFM2.5-1.2B-JP) | Japanese chat. Docs: generation, translation, conversation. | Docs page: 1.2B / 32K. The card text fetched here did **not** restate 1.17B or 32,768. | temperature 0.3, min_p 0.15, repetition penalty 1.05 | Card’s inference table: Transformers, vLLM, llama.cpp. Docs page also marks GGUF, MLX, and ONNX, and those repos exist. |
| [JP-202606](https://huggingface.co/LiquidAI/LFM2.5-1.2B-JP-202606) | Newer Japanese chat. The card says it improves on LFM2.5-1.2B-JP. Not in the docs text-model list fetched for this note. | 1.17B / 32,768. Train budget **31.5T**. Languages: **English and Japanese only.** | temperature 0.1, top_k 50, repetition penalty 1.05 | Transformers, vLLM, llama.cpp, MLX, LM Studio, plus a GGUF and an ONNX repo. |
| [Base](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Base) | Pretrain used to make the others. Docs: not instruction-tuned; use Instruct for chat. Card: only for heavy fine-tuning. | 1.17B / 32,768. Train budget 28T. Same eight languages. | None published on the card. | Transformers, vLLM, llama.cpp. GGUF and ONNX repos exist. Card does **not** list MLX. A docs library table marks MLX absent. |

The prompting guide says to take sampling from each model page. The copy fetched here does not reprint 1.2B numbers, so the card values above are the ones to use. No `<think>` delimiter was in the Thinking card text. Do not invent a parser for a hidden trace.

**Not 1.2B players:**

- **LFM2.5-1.2B-Instruct-DSpark** is a **296M** speculative-decoding drafter, not a second 1.2B. The Instruct card (vendor claim, not measured here) says about 2.1× faster decode in SGLang and about 2.5× on Apple silicon via Metal, with the same outputs. A GGUF repo exists. Sizes were not copied. Skip it for a one-day demo: it is a second model and a different runtime path.
- Deprecated LFM2 checkpoints, still downloadable, replacement **LFM2.5-1.2B-Instruct** on the [deprecations page](https://docs.liquid.ai/lfm/help/deprecations): `LFM2-1.2B`, `LFM2-1.2B-Extract`, `LFM2-1.2B-RAG`, `LFM2-1.2B-Tool`. The Ollama page’s curl samples still name `LiquidAI/LFM2-1.2B-GGUF`. Use the LFM2.5 Instruct repo instead.

#### GGUF file sizes

From the Hugging Face tree API (`/api/models/<repo>/tree/main`) on 25 September 2026. Figures are decimal megabytes (bytes / 1,000,000), rounded to 0.1. They are file sizes, not runtime RAM. Across Instruct, Thinking, JP, JP-202606, and Base, each quant rounds to the same 0.1 MB. Exact `Q4_0` byte counts differ by at most 640 bytes.

| Quant | Decimal MB | Exact `Q4_0` bytes |
| --- | --- | --- |
| Q4_0 | 695.8 | Instruct 695,751,488 · Thinking 695,751,680 · JP 695,751,616 · JP-202606 695,750,944 · Base 695,750,848 |
| Q4_K_M | 730.9 | |
| Q5_K_M | 843.4 | |
| Q6_K | 962.8 | |
| Q8_0 | 1,246.3 | |
| F16 | 2,343.3 | |
| BF16 | 2,343.3 | Present for Instruct, Thinking, and Base. **No BF16 file** in the JP or JP-202606 trees. |
| QAD Q4_0 | 695.8 (695,755,488 bytes) | **Instruct only**, among these five trees. |

The Instruct file page rounds Q4_0 to **696 MB**. That matches 695,751,488 bytes. MLX and ONNX byte sizes were **not** copied. Official MLX repos exist per bit width (4, 5, 6, 8, bf16) for Instruct, Thinking, JP, and JP-202606. Base’s card does not list an MLX export.

Compared with the sizes already in this note: 230M Q4_0 is 149 MB, 350M Q4_0 is 219 MB, 1.2B Q4_0 is 695.8 MB. That is about 4.7× the 230M file and about 3.2× the 350M file. Arithmetic on those file sizes, not a speed benchmark.

#### How you run a 1.2B locally

- **llama.cpp.** GGUF repos above. Same `llama-cli` / `llama-server` path as the smaller models. Phone guide’s example file is `LFM2.5-1.2B-Instruct-Q4_0.gguf`.
- **Ollama.** Docs’ worked example is `ollama run hf.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF`, then an OpenAI-compatible server on port 11434. They say any published GGUF repo can be loaded the same way. The MoE install warning on that page does not apply to these dense 1.2B models.
- **MLX.** Official `LiquidAI/LFM2.5-1.2B-*-MLX-*` repos for the chat variants. Liquid’s general MLX note recommends 8-bit and says 4-bit exists. Per-repo file sizes were not re-read.
- **LEAP.** Deprecated. See the runtime list above. Do not build the demo on it.
- **Browser.** The ONNX guide’s WebGPU sample loads `LiquidAI/LFM2.5-1.2B-Instruct-ONNX` in Transformers.js (`device: "webgpu"`, `dtype: "q4"` or `"fp16"`). Q8 is server-only. Their setup still tells you to enable a Chrome/Edge WebGPU flag. ONNX file sizes are a gap. Thinking, JP, JP-202606, and Base have ONNX repos. The browser snippet itself names Instruct.
- **Not the on-device path:** Transformers and vLLM on every card; SGLang on the Instruct card; partner NPU builds (NexaML, FastFlowLM) mentioned only as vendor deployment notes.

#### Vendor speed and memory

These are Liquid’s figures, from the cards, for **1,000 prefill tokens and 100 decode tokens**. They are not an in-game decision, and this note has no matching table for 230M or 350M, so they are not a comparison.

Instruct card headline: 239 tok/s decode on an AMD CPU, 82 tok/s on a mobile NPU, “under 1GB of memory.” One row: Samsung Galaxy S25 Ultra, llama.cpp Q4_0, CPU, prefill 335 tok/s, decode 70 tok/s, memory 719 MB.

Thinking card repeats the same headline, then a different table. Rows include AMD Ryzen AI 9 HX 370, llama.cpp Q4_0, CPU, prefill 2975 tok/s, decode 116 tok/s, memory 856 MB; and the same S25 Ultra CPU row at 335 / 70 tok/s and 719 MB. They also say FastFlowLM on AMD Ryzen NPUs holds about 52 tok/s at 16K context and about 46 tok/s at 32K. The card says Thinking uses fewer output tokens than Qwen3-1.7B in thinking mode, without stating the token count. The [migration guide](https://docs.liquid.ai/guides/migration-guide) says to pick Thinking only when reasoning quality is worth the **added latency**. No millisecond figure is attached.

#### Fit against 230M and 350M

Liquid’s own mapping puts classification, extraction, routing, and tight memory on **230M or 350M**. It puts the 1B–4B band on **Instruct or Thinking**. An in-game action, chosen from a list the code already computed, is closer to routing than to a math trace.

What does **not** change: context is still 32,768. You still send a fresh projection and drop the transcript. You still keep the call off the frame loop. You still cap new tokens and reject illegal actions.

What does change: the Q4_0 file is 696 MB instead of 149 or 219 MB. Venue Wi-Fi is the wrong time to download it. Vendor phone memory for Q4_0 is about 719 MB on the S25 Ultra row, which is the whole game plus the model, not a measured headroom number.

| Use this | For the hack |
| --- | --- |
| 230M or 350M Q4 | Still the demo default. Smaller download, and the documented class for a closed choice. |
| Instruct Q4_0 or Q4_K_M | The only 1.2B worth swapping in, and only if that file is **already on the laptop**. Same loop. Do not block the demo on the download. |
| Thinking | Poor fit. Extra reasoning work, and Liquid says it adds latency. A short action does not need a chain of thought. |
| JP or JP-202606 | Only if the playable is Japanese. If so, the newer card is JP-202606. Same file size, same context, not a smaller model. |
| Base, DSpark, LFM2-1.2B and its Extract/RAG/Tool checkpoints | Do not load these for the demo. |

The smallest-build recommendation stays 230M or 350M. Instruct is an optional local upgrade, not a new plan.

## Black Forest Labs

Primary page: [The frontier of visual intelligence](https://docs.bfl.ai/quick_start/introduction), read 25 September 2026. Its own line is that FLUX models generate and edit images and video, render synchronized audio, and drive robotics, “through one API.” The page then splits that into cards. The model and API pages below are the ones those cards link to.

The “Start with FLUX 3” grid is four modalities, all on FLUX 3:

| Card on the introduction | What the card says | Page it opens |
| --- | --- | --- |
| Text-to-Video | Text → Video. Motion from a prompt, synchronized audio included. | [Video](https://docs.bfl.ai/flux_3/flux3_video) |
| Image-to-Video | Image → Video. Animate a still or pin keyframes. | Same video page |
| Audio | Video with sound. Speech, effects, ambience with the frames. | [Video, audio anchor](https://docs.bfl.ai/flux_3/flux3_video#audio) |
| Action | Frames → Actions. “Open weights that predict the next 32 actions for a robot or a game.” | [FLUX 3 Action](https://docs.bfl.ai/flux_3/flux3_action_overview) |

So yes: BFL publishes an action model, and the introduction names it. It is **FLUX 3 Action**, not a mode of the video API.

### FLUX 3 Action

Cited from the page the introduction’s Action card opens, [FLUX 3 Action](https://docs.bfl.ai/flux_3/flux3_action_overview), and from the [FLUX 3 overview](https://docs.bfl.ai/flux_3/flux3_overview) (the introduction’s “API Reference” card points here). Both call it a **7B open-weights world action model**. Camera images, current state, and an instruction go in. A chunk of actions comes out (32 for DROID and games, 42 for SO-101), together with future video latents. DROID and game plans are about two seconds at 15 Hz. The overview’s shorter line: predict a chunk of actions and about two seconds of future video; run it on a robot arm through LeRobot, or fine-tune it for a robot, simulator, or game.

The [inference guide](https://docs.bfl.ai/flux_3/flux3_action_inference) linked from that overview says the current call returns **actions only**. It does not decode the latents into frames.

| Embodiment | Ready checkpoint? | What you send | What you get |
| --- | --- | --- | --- |
| DROID (Franka) | Yes | 3 cameras, 8-D joint state | 32 actions, 8-D, 15 Hz |
| SO-101 | Yes | 2 cameras, 6 joint positions | 6-D commands; released profile executes 32 of 42 at 30 Hz |
| Video game | No. Fine-tune | 1 frame on a 512×512 canvas, last action | 3 or 4 values in [-1, 1] |
| Drone (Isaac Sim) | No. Fine-tune | 1 onboard frame, last action | `[forward, lateral, up, yaw]` |

The base card (`flux-3-action-base`, linked from the overview as the weights collection) adds a frozen video VAE and an unmodified Qwen3-VL-4B-Instruct (Apache 2.0). It says the base is not a complete policy and that a new embodiment needs its own action heads. The “7B” line does not include that 4B encoder. File sizes were not copied.

**Not an API call.** The introduction’s [Get started](https://docs.bfl.ai/quick_start/get_started) page makes the first request `POST https://api.bfl.ai/v1/flux-3-video` with `"mode": "t2v"`. The [video page](https://docs.bfl.ai/flux_3/flux3_video) allows `t2v`, `i2v`, `v2v`, and `draft_enhance`. None of those return controls. The [image guide](https://docs.bfl.ai/quick_start/generating_images) the introduction links as “make your first API call” lists image routes only (`/flux-2-max`, `/flux-2-pro`, `/flux-2-flex`, `/flux-2-klein-4b`, `/flux-2-klein-9b`, Kontext, FLUX1.1 [pro], `/flux-dev`, and their preview twins). No action route is on that list.

Action runs from the [inference guide](https://docs.bfl.ai/flux_3/flux3_action_inference): Linux, Python 3.12, NVIDIA GPU, PyTorch 2.10, CUDA 12.8, repo `black-forest-labs/flux-action`. `FluxActionPolicy.from_pretrained`, then `predict_action_chunk` or `select_action`. They report BF16 inference around **32 GB** of GPU memory, and **79 ms** for one game plan on an H200 (76–79 ms in a separate BF16 512×512 note). Those are their figures. `select_action` is synchronous. They say to measure it, and to drop a command whose control step has already passed.

**License,** from the Kommunity text linked on the Action overview: non-commercial and non-production use, plus commercial use of Outputs for a Qualifying User under **US$5,000,000** gross annualized revenue (you plus affiliates), with filtering and any required AI disclosure. Outputs include action predictions. Anything else needs a separate license. Not legal advice. The code repo has its own license.

**Games are a fine-tune, not a shipped player.** The overview’s game example, [FLUX 3 Action plays video games](https://docs.bfl.ai/flux_3/flux3_action_games), trains on scripted bots: GRUNT (shooter, four controls) and VECTOR (racer, three controls). 800 episodes of 16 seconds at 15 Hz per game. Their reported run is about 7 H200s and 2,000–3,000 updates. The 60-second tables are one seed per game, and the simulator, bots, recorder, and player are not in the release. Each plan sees the current frame, the last executed action, and a fixed caption. Their shooter playback executes 2 of the 32 actions (about 133 ms at 15 Hz) and then looks again.

### What the same introduction offers besides Action

Still only pages the introduction links:

- **Hosted video.** [FLUX 3 overview](https://docs.bfl.ai/flux_3/flux3_overview) and [video](https://docs.bfl.ai/flux_3/flux3_video). Async: POST, then poll `polling_url` until `Ready`. Up to 20 seconds, 24 fps, audio on by default. Their price table: text-to-video and image-to-video $0.17/s at `hd` up to $0.80/s at `uhd`; continuation is higher; draft is about a third. Result URLs expire about 2 hours after the video job (the image guide says image URLs last 10 minutes). 24 active tasks, then HTTP 429.
- **Hosted images.** [Image generation](https://docs.bfl.ai/quick_start/generating_images). Same `api.bfl.ai` / `api.eu.bfl.ai` / `api.us.bfl.ai`, header `x-key`. First example is `POST /v1/flux-2-pro-preview`. [Get started](https://docs.bfl.ai/quick_start/get_started) says 1 credit = $0.01.
- **Tools.** The introduction’s tools card says outpainting, erase, deblur, and virtual try-on, and opens [outpainting](https://docs.bfl.ai/flux_tools/flux_outpainting). Video edit is a separate route the FLUX 3 overview documents: `POST /v1/flux-tools/video-edit-v1`.
- **Local image weights, not Action.** The introduction’s self-host card names FLUX.2 [klein] (Apache 2.0 / FLUX Non-Commercial), FLUX.1 [dev], FLUX.1 Tools [dev], and FLUX.1 Kontext [dev], and sends you to [bfl.ai/licensing](https://bfl.ai/licensing). It does not say those run on a phone. It does not give VRAM numbers. The “Run open weights” card goes to the [Black Forest Labs Hugging Face org](https://huggingface.co/black-forest-labs).

### Fit for this playable

FLUX 3 Action does emit in-game controls, on the pages above. It is still the wrong engine for this hack’s casual playable.

The API a game can call today, from the introduction’s own getting-started path, returns pixels and audio, not a decision. Action weights are local, NVIDIA, and on their figure about 32 GB at BF16. Ready policies are robot arms. A new game means new heads and a demonstration set. Their 79 ms number is an H200, not a phone frame.

The part that does match the hackathon: the documented game loop keeps a caption and the last action, then throws away a plan that missed its tick. It does not grow a frame history. That is mutable state and discarded context, on a GPU workstation, after a fine-tune you will not finish in an afternoon.

Use the introduction’s API for an end card or a clip before the demo. The live choice of which card to show belongs to the bandit, or to Jev or LFM on the compact clickstream state. Not to Action.

## 2. Jev

**Not Liquid.** Public pages describe a decision model from TypeSafe AI, launched 15 September 2026 by Diogo Almeida (founder; he says he previously worked on instruction-following at OpenAI). Named after William Stanley Jevons. “System One” is their name for fast judgments, after Kahneman, as opposed to slow generated reasoning.

Primary sources: [launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev), [docs.typesafe.ai](https://docs.typesafe.ai/introduction), model page, state page, and the [jev-1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13) note (reviewed 17 September 2026).

### What it is

Jev does not generate strings. You send `state` plus typed questions. It returns probabilities in one parallel pass. Three question types:

| Type | You define | You get back |
| --- | --- | --- |
| Choice | Up to 255 named options | Winning option, a distribution, confidence |
| Score | 2–10 ordered levels (docs: up to 10) | A score, per-level probabilities, confidence |
| Noul | A yes/no question | Probability the answer is yes (no separate confidence field) |

Questions in one request see the same state and are scored independently. Code is supposed to combine them (thresholds, weights). The model is not a calculator: counting, dates, and arithmetic belong in code. It does not emit prose; chaining Choices to fake generation is something they tell you not to do.

Current id on the docs model page: **`jev-1.13.0`**. Aliases `jev-latest` and `jev-preview` both pointed at it. Pin the versioned id if you tune thresholds. Endpoint: `POST https://api.typesafe.ai/v1/systemone` with a bearer key from the console. Official clients: `typesafe-sdk` (Python) and `@typesafe-ai/sdk` (JavaScript). Early access: waitlist, then a key. Not fine-tunable per customer. They say customer requests are not used for training.

Published limits (docs, and they say rate limits can change without notice):

- Context: **64k** tokens for state plus all questions; **32k** for state plus the single longest question.
- Input: text only. String, JSON object, or array of text. No image, audio, or video.
- Price they publish: **$0.042 per million input tokens**, output free.
- Rate limit they publish: 250,000 tokens/sec and 1,200 requests/min, else 429.

### Is it on-device?

**No, on the evidence used here.** The docs are an API (`api.typesafe.ai`), an API key, and hosted weights shared across accounts. No GGUF, no Core ML, no local runtime. A Swift or Rust client in search results is still a client of that API.

Vendor speed, from the 15 September launch post, not from a test here: end-to-end **70–500 ms**, measured from their laptops on the US West Coast, where they say the service was hosted. They note that the short demo inputs favor them, and that a more complex workflow eval is where “about 194× faster / 445× cheaper” comes from. Those multipliers are their comparison against LLM wrappers on their own workflows. Do not treat them as phone latency, and do not treat 70 ms as guaranteed on conference Wi-Fi.

Their launch post does show games: a **Doom** bot (structured text state, not pixels; they mention worrying about 10 queries/sec and a vendor cost around $7/hour) and **Wikiracing** (high-cardinality link choice, with a two-stage fallback above 255 options). Secondary writeups name Mario, Pokémon, and drone loops. Those repos were not opened for this note.

### Other things named Jev

| Candidate | What the page actually is | Plausible for on-device in-game decisions? |
| --- | --- | --- |
| TypeSafe Jev | Hosted System One model, decision-shaped, with official game demos in the launch post | Plausible **decision layer**. Not on-device. |
| [openjev.sh](https://openjev.sh/docs) | Separate site. `POST https://api.openjev.sh/v1/systemone`, model id `openjev`, same three primitives. Sample response is labeled illustrative. | Not established as TypeSafe, as downloadable weights, or as on-device. Ignore for the local-model build unless someone confirms the relationship. |
| learnjev.com, jevapi.dev, `jev-sdk` / `jevrs` | Tutorials and clients aimed at the TypeSafe HTTP API | Same cloud product, not a second model. |
| William Stanley Jevons | Economist. TypeSafe says the model is named after him | Not a product. |

No paper, weight file, or on-device SDK under the name Jev was found. If “JEV” meant something else in the room, it is not identified here.

### Why it still matters next to Liquid

Jev’s own docs are the hackathon thesis in API form: state is a record you would hand an expert; questions are separate from state; extra unrelated context causes **context rot** and lower accuracy (jaggedness item 5). The game owns the mutable state. The model sees a filtered snapshot and returns a typed judgment. It cannot be the offline on-device half of the idea.

## 3. Playables, and what changes the design

“Playable” is three different artifacts. Only one of them can carry a local model.

1. **A game a person plays.** Casual mobile is the interesting end state. For this hack, a short session on a laptop or a phone you already set up is the same idea.
2. **A hackathon demo.** Someone else finishes a run between 17:00 and judging, on hardware you brought.
3. **A user-acquisition playable ad.** The current target. The HTML file cannot carry model weights. Rules or a bandit can still run inside it. LFM or Jev, if used, sit beside it. See the target section.

### Casual mobile

The loop is still right: the player taps, the simulation moves, and sometimes a local model picks an NPC action, a shop offer, or a story branch from **current** state. The phone is a bad place to discover that on hack day.

Constraints that change the design:

- **Download size.** Confirmed GGUF weights start at 149 MB (230M Q4_0) and 219 MB (350M Q4_0). The 1.2B Q4_0 file is 696 MB. Liquid’s mobile guide downloads the GGUF at first launch instead of sealing it inside the binary. A demo device needs that download finished before doors open. A larger checkpoint means a larger mmap and a longer first load, so the working set you send the model should stay small even though the file is already big.
- **Memory.** mmap’d weights are file-backed. The KV cache is not, and it scales with context length. Persisting “the whole match” inside the prompt is how you blow memory and slow the next decision. Persist the match in your own state object; send a projection.
- **Heat.** Sustained decode shares the CPU/GPU with the game. Liquid tells you to use big cores only and to prefer Metal on Apple, CPU on Android until Vulkan/OpenCL is tested on that device. Call the model on a beat (a turn, a dialogue choice, an NPC tick every few seconds), then stop. Do not leave a generate loop running while the player walks around.
- **Frame time.** At 60 Hz a frame is about 16.7 ms. That number is arithmetic, not a benchmark. Liquid never published an in-game latency, and their own eval recipe generates 100 tokens. Assume one decision spans many frames. The game loop interpolates, animates, and accepts input while the decision is in flight. When the action returns, code checks it against the **current** legal set. If the world moved, drop the stale action instead of applying it.
- **Offline.** After the weights are on disk, Liquid inference needs no network. That is the point. First install, Hugging Face, and a LEAP manifest download do need a network. Jev needs a network on every decision.
- **Session length.** A casual session is short. The hackathon cares about reliability as history grows toward hours. A three-minute demo does not show that unless the game **fast-forwards** a long horizon: a day counter, a log of fifty past beats, and a visible working-memory panel. The panel is the product. Appending every beat to the prompt is the bug you are demoing against.
- **Input latency.** Taps and movement resolve in the simulation immediately. The model is not on the input path. It is on decision points. If a call is late, the game uses a scripted fallback so play never blocks on tokens.
- **Store packaging.** Current App Store and Play size caps were **not** re-checked, so no store limit is stated here. It does not matter for the hack: you will not pass review before 16:30. Sideload, TestFlight only if the build already exists, or skip the phone. Liquid’s embed guide is real, and it is a multi-hour native project (XCFramework or NDK, background download, sampler, grammar) before any game exists.

### Formats that fit one day better

**Desktop / laptop, local server.** Best demo. `llama-server` or Ollama with LFM2.5-350M or 230M Q4, game in a browser or a small desktop window talking to `localhost`. No store. Weights pre-downloaded. Judges stand at your machine. Context stays tiny because you choose `n_ctx`.

**Web playable on a laptop.** Liquid already ships browser games and WebGPU demos. Hand & Voice Racer is fully in-tab (Chrome or Edge 113+, WASM fallback) but the model transcribes keywords; it does not pick actions, and the audio weights are ~900 MB, cached in IndexedDB after the first fetch. A text model in-browser is plausible and still a first-load risk. Pre-cache. Do not depend on venue Wi-Fi for the weights. WebGPU availability on a random phone is an extra unknown; demo on your laptop.

**Short session with a long horizon baked in.** A turn-based village, shop, or route, ten decisions long, with a scrubber that replays “day 30” from a pruned state versus a stuffed transcript. This shows the hackathon thesis without a real hour of play.

**Phone as a stretch.** Only if llama.cpp or LEAP is already building on a device in your pocket and the GGUF is already local. The game design stays the laptop design.

### User-acquisition playable ads

The network table in the target section is the check. Caps run from AdMob’s 150 KB HTML5 zip to the 5 MB playable files, and several of those pages forbid an external call during play. A 149 MB model cannot live in any of those files. The ad file can run a rule or a bandit. LFM or Jev sits on the laptop, on a server between plays, or inside an app you own. Do not spend the afternoon on an ad-network upload.

### What “playable” means at this event

A judge can start a run in under a minute, play a few beats, and see three things on screen:

- the decision just taken (difficulty, hint, CTA, or end card) and who took it
- the compact clickstream state that was kept
- the raw events that were dropped before the call

If the model is slow or returns garbage, the game continues on a fallback and the panel says why. A video of a prompt is not a playable. A store listing is not a playable.

## 4. Smallest build that could be demoed today

Uncertainty is marked. This replaces the earlier traveler-and-NPC loop. The target is a playable ad and its clickstream.

**Loop.** One HTML page on the laptop. A tiny game: tap to jump, or swipe to clear a piece. It records taps, swipes, dwell, a fail, and a drop-off if the player stops. After a fail or a short timer it asks for one decision: ease the next beat, show a hint, or hold the install button. At the end it picks an end card. A second control, “next cohort,” replays a few finished sessions and updates which end card is favored.

**Keep.** Session counts, current difficulty, whether hint and CTA are already on, last decision, and a cohort row (arm shown, reward). **Drop** raw points once counted, events from sessions that have closed, and the previous model completion. A toggle appends the raw log so judges can see the stuffed version get worse. Do not claim a lift you have not measured.

**Who decides.** LFM2.5-350M or 230M, Q4, already on disk, via `llama-server` on localhost. The page sends the compact state and asks for one action. If the call is late or the string is illegal, the bandit answers and the panel says so. That localhost call is the local model. It is also the request a network creative is not allowed to make. The bandit is what you would ship inside the 5 MB file. Jev is a third button only if a key is already in hand, and it is labeled as a cloud call. Do not download weights at the venue.

**BFL.** If an end-card image is needed, generate it before the demo. The live choice is which card, not a new generation.

**Do not build.** An AppLovin upload, a fine-tune, FLUX 3 Action, an 8B harness, or a phone embed. The panel of kept state versus dropped events is the demo.

## Sources

- Hackathon: https://luma.com/horizonagentshack
- Liquid library, FAQ, license, hardware guide, text models, 2.6B page, migration guide, ONNX guide, Ollama guide, deprecations, llama.cpp mobile guide, LEAP SDK quick start (v0.10.7, now listed as deprecated), Hand & Voice Racer
- Hugging Face cards and GGUF trees for LFM2.5-1.2B Instruct, Thinking, JP, JP-202606, and Base, plus the 230M and 350M file pages
- Black Forest Labs, starting at https://docs.bfl.ai/quick_start/introduction and the pages that page links: FLUX 3 video, FLUX 3 overview, FLUX 3 Action overview, Action inference, Action games example, get started, image generation, Kommunity license on the Action weights
- TypeSafe launch post (15 Sep 2026), models, state, choice, jev-1.13 jaggedness
- Playable network specs, each page linked in the table: AppLovin creative specs and HTML analytics, Unity Ads playable specifications, ironSource Exchange MRAID guidelines, Meta Help Center playable specs, Meta playable upload errors, Google Ads App campaign HTML5, Google Ads HTML5 fix-issues, AdMob HTML5, Ad Manager HTML5 trafficking and build guidelines, Ad Manager HTML bundle errors, Mintegral asset specs, creative guide, and playable guide, Playturbo review doc, Liftoff interactive integration and creative API, MRAID 3.0 (IAB Tech Lab, June 2018 PDF)
- OpenJEV docs, only to record that a second hosted API exists: https://openjev.sh/docs

## Uncertainty

- No tok/s, thermal, or frame-time measurement was made. Do not quote one.
- Library/FAQ context text conflicts with the 2.6B model page (32K vs 128K).
- LEAP SDK and “embed llama.cpp, no wrapper” are both live docs. Either can run a model. Neither is required for a laptop demo.
- Jev 70–500 ms, the Doom cost aside, and the workflow speedups are TypeSafe’s figures.
- OpenJEV’s relationship to TypeSafe was not established. No local Jev weights were found.
- App Store / Play size rules were not verified. Playable caps in the network table were, and two official Meta pages disagree on the single-HTML cap (Help Center 5 MB, developer error table 2 MB). Google’s App-campaign pages say 5 MB and, for two interstitial sizes, 5.2 MB. Mintegral’s asset table says a single HTML file; their creative guide and Playturbo say a ZIP. A Unity LevelPlay playable-upload spec, and a Vungle-branded spec separate from Liftoff’s, were not found. WebAssembly is not named on these pages.
- Small-model JSON reliability without a grammar is untested. Instruct was not tested either.
- 1.2B MLX and ONNX byte sizes were not copied. The `leap/` directories inside the GGUF repos were not listed.
- The original JP card, as fetched, did not restate 1.17B or 32,768. Those figures for JP come from the docs page.
- Thinking’s card does not document a reasoning-token delimiter. Vendor tok/s on the 1.2B cards are not comparable here to 230M or 350M.
- JP-202606’s `LICENSE` file is a different size from the others. The license text was not diffed.
- FLUX 3 Action weight-file sizes were not copied. The 79 ms plan time and the GRUNT/VECTOR scores are Black Forest Labs’ figures, on their hardware and one seed per game. The game simulator is not in the release.
- A BFL product page still describes Action as a partner rollout and the FLUX 3 Dev backbone as unreleased. The Action docs and Hub repos describe downloadable weights. Both were live the same day.
- No `api.bfl.ai` Action route showed up in the docs index. That is not a proof that no private endpoint exists.
