# Hyper-personalized SF video ads (FLUX 3 video)

These are spec (unofficial) scripts for short video ads with sound, for real San Francisco brands: Sightglass, Tartine, Bi-Rite Creamery, Dandelion Chocolate and Boudin. They are for a public hackathon experiment and are not affiliated with or endorsed by those brands. Each ad pairs a **product** with an SF **persona**, and FLUX 3 video renders it with music, sound effects and voiceover in a single call. Every brand fact cites a source in `scripts.json`, and no offers or prices are invented. Ideas and the Nimble hand-off format are in [IDEAS.md](IDEAS.md).

## Files

- `scripts.json` has three parts:
  - `products`: look, hero shot, signature sound effects, sonic logo, call to action and sources.
  - `personas`: who the viewer is, where and when the ad happens, narrator voice, language and music taste.
  - `variants`: one product × persona pairing with a three-beat story (tension → turn → payoff) and two voiceover lines.
- `render.py` compiles each variant into one FLUX 3 prompt, prints it, and with `--submit` renders it.

## How personalization works

The product decides the look, the hero shot, the sound effects and the sonic logo. The persona decides the setting, the time of day, the narrator voice, the language and the music genre. The variant writes the story beats and the spoken lines for that person. Sightglass gets a tense minimal beat for a founder on demo day and lo-fi for a commuter who missed the N-Judah. The Mission family persona gets Spanish voiceover.

A persona is a small, editable record. It is not a history. An agent can rewrite a field when it learns something new, for example `music` or `when`, and the next render picks up the change.

## Prompt shape

Each variant compiles to three shots, SHOT ONE / HARD CUT / SHOT TWO / HARD CUT / SHOT THREE, followed by an `AUDIO:` block. The BFL video docs say:

- Audio is on by default (`generate_audio: true`).
- Audio has no separate parameters. You steer it only through the prompt.
- Text in double quotes is spoken as dialogue, with lip sync.

The prompt asks for no on-screen text. Add the call-to-action text in post, so the model never has to render lettering.

## Run

```bash
python3 content/ads/render.py                               # dry run: print prompts and estimated cost
python3 content/ads/render.py --only boudin__new_transplant  # one variant
python3 content/ads/render.py --submit --draft --only boudin__new_transplant   # cheap test render
python3 content/ads/render.py --submit                      # all 8 variants
```

- The key is read from `BLACK_FOREST`, with `BFL_API_KEY` as a fallback. Never commit it.
- Renders go to `content/ads/out/`, which is gitignored. Download happens immediately because BFL result URLs expire.
- Cost: 10 s at `hd` is about $1.70 per clip, going by BFL's published $0.17/s. Drafts cost about a third of that. All 8 variants at hd come to about $13.60.

## Add a product or persona

Add an entry under `products` or `personas`. Then add a `variants` entry that references both by id and gives `tension`, `turn`, `payoff`, and two `lines`. Keep the spoken lines short, about 15–20 words in total for a 10 s clip, so the voiceover fits.
