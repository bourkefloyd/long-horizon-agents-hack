# Hyper-personalized video ads (FLUX 3 video)

These are sample scripts for short video ads with sound. Each ad pairs a **product** with a **persona**, and FLUX 3 video renders it with music, sound effects and voiceover in a single call. All products and brands here are fictional.

## Files

- `scripts.json` has three parts:
  - `products`: look, hero shot, signature sound effects, sonic logo and call to action.
  - `personas`: who the viewer is, where and when the ad happens, narrator voice, language and music taste.
  - `variants`: one product × persona pairing with a three-beat story (tension → turn → payoff) and two voiceover lines.
- `render.py` compiles each variant into one FLUX 3 prompt, prints it, and with `--submit` renders it.

## How personalization works

The product decides the look, the hero shot, the sound effects and the sonic logo. The persona decides the setting, the time of day, the narrator voice, the language and the music genre. The variant writes the story beats and the spoken lines for that person. The same cold brew sounds like lo-fi piano for a nurse coming off a night shift and like synthwave for a developer at 2 AM. The Spanish-language personas get Spanish voiceover.

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
python3 content/ads/render.py --only hush__indie_dev        # one variant
python3 content/ads/render.py --submit --draft --only hush__indie_dev   # cheap test render
python3 content/ads/render.py --submit                      # all 8 variants
```

- The key is read from `BLACK_FOREST`, with `BFL_API_KEY` as a fallback. Never commit it.
- Renders go to `content/ads/out/`, which is gitignored. Download happens immediately because BFL result URLs expire.
- Cost: 10 s at `hd` is about $1.70 per clip, going by BFL's published $0.17/s. Drafts cost about a third of that. All 8 variants at hd come to about $13.60.

## Add a product or persona

Add an entry under `products` or `personas`. Then add a `variants` entry that references both by id and gives `tension`, `turn`, `payoff`, and two `lines`. Keep the spoken lines short, about 15–20 words in total for a 10 s clip, so the voiceover fits.
