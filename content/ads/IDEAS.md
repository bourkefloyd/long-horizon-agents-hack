# SF video ad ideas, Nimble upstream

Spec (unofficial) ads for real San Francisco brands. The brands are not affiliated with this project.

## Pipeline

```
Nimble pulls  ->  facts.json (one fact per row, with source and expiry)  ->  script generator  ->  scripts.json variants  ->  render.py  ->  FLUX 3 video
```

Only rows in `facts.json` may appear in voiceover, the call to action, or hero shots. That rule keeps the ads from inventing prices, offers or hours. Each row expires, and the generator skips expired rows. That is the long-horizon part: the brand record is small, gets edited, and drops what has gone stale. It never grows into a scrape log.

### facts.json row

```json
{
  "brand": "bi_rite_creamery",
  "kind": "event | seasonal_item | hours | signature_item | history | review_theme | weather | local_event",
  "fact": "20th anniversary: three months of special flavors and events",
  "source": "https://www.prnewswire.com/news-releases/bi-rite-creamery-celebrates-20-years-of-creating-community-one-scoop-at-a-time-302843747.html",
  "retrieved_at": "2026-09-25",
  "expires_at": "2026-11-30"
}
```

`review_theme` rows are paraphrased themes ("line is long but moves", "sells out early"). Never quote a reviewer's words.

## Ideas

Each idea lists the Nimble signal that triggers it, the brand and the persona. Ideas marked ✓ already have a variant in `scripts.json`.

| # | Idea | Hook (first 1–2 s) | Nimble signal | Brand × persona |
|---|---|---|---|---|
| 1 | **Karl the Fog** | Fog "speaks" in voiceover: "You're welcome for the sourdough." | Fog forecast by neighborhood, plus Boudin's own story that SF's fog is part of the bread's secret | Boudin × new_transplant ✓ (variant) |
| 2 | **Sold out by 10** | POV of racing up Guerrero at 7:25 AM | Review theme "morning buns sell out" + hours (opens 7:30) | Tartine × ocean_beach_surfer ✓ |
| 3 | **The line is the ad** | Time-lapse of the line on 18th St, then a single cone | Review theme "long line, worth it" + hours (12–9) | Bi-Rite × dolores_park_crew ✓ |
| 4 | **Anniversary drop** | "Twenty years. One scoop." | Bi-Rite 20th-anniversary events (Aug 2026, three months) | Bi-Rite × mission_family_es ✓ |
| 5 | **Microclimate roulette** | Same person, three neighborhoods, three weathers in 10 s | Weather per neighborhood | Sunset fog → Sightglass; Mission sun → Bi-Rite |
| 6 | **Demo day fuel** | "Four minutes to make it count." | SF tech events calendar (demo days, launches) | Sightglass × soma_founder ✓ ; Dandelion × soma_founder ✓ (celebration) |
| 7 | **What's new this week** | Macro close-up of the new item | Seasonal items on brand pages | Dandelion (for example, their June 2026 aperitivo bonbons, which should expire now: demo of drop-stale) |
| 8 | **Tourist vs local** | Split screen: Wharf vs Mission | Brand locations | Boudin vs Tartine |
| 9 | **Open right now** | "It's 8:40. You have 20 minutes." | Hours; the call to action changes near closing time and the ad is never shown for a closed shop | Dandelion (Fri until 10) × dolores_park_crew |
| 10 | **Game-day / event tie-in** | Crowd noise, then a quiet ASMR bite | SF events this week (Giants games, street fairs, Fleet Week in October) | Boudin or Bi-Rite × whichever persona the event draws |

## Pick order for today

1. Render 1, 2 and 4 as drafts. They need no new Nimble data and each tests something different: a narrated character voice (1), fast POV pacing (2), and Spanish dialogue (4).
2. Wire idea 7 as the long-horizon demo. Nimble finds an item and the generator writes a variant. After the item's expiry date passes, the fact drops out and the variant retires.
3. Everything else waits until the drafts show FLUX 3 follows the music and voiceover directions.
