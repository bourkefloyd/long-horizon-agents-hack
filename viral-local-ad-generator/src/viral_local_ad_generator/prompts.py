from __future__ import annotations

from .models import NewsStory, SanitizedStory, VideoAdConcept
from .sanitizer import sanitize_story_for_ad


ANGLES = [
    "local moment hook",
    "commuter craving",
    "fan celebration",
    "quick lunch rescue",
    "late-night payoff",
]


def generate_video_concepts(
    campaign_script: str,
    market: str,
    story: NewsStory,
    sanitized_story: SanitizedStory | None = None,
) -> list[VideoAdConcept]:
    concepts: list[VideoAdConcept] = []
    clean_story = sanitized_story or sanitize_story_for_ad(market, story)
    story_frame = clean_story.sanitized_frame
    story_reference = clean_story.sanitized_reference
    campaign = make_campaign_info(campaign_script)
    for index, angle in enumerate(ANGLES, start=1):
        hook = make_hook(market, story_reference, campaign, angle)
        script = make_short_script(campaign, hook, angle)
        video_script = make_10_second_video_script(
            campaign=campaign,
            market=market,
            story_frame=story_frame,
            story_reference=story_reference,
            hook=hook,
        )
        script = edit_ad_script_for_event_language(script)
        video_script = edit_ad_script_for_event_language(video_script)
        visual_prompt = make_visual_prompt(market, story_frame, angle, video_script)
        visual_prompt = edit_ad_script_for_event_language(visual_prompt)
        audio_prompt = make_audio_prompt(angle)
        negative_prompt = (
            "No publisher logos, no real public figures, no implying endorsement by people connected to the "
            "local moment, no tragedy, no crime scene, no politics, no medical emergency, no gore, "
            "no copyrighted characters, no distorted text, no famous brand references or logos."
        )
        payload = {
            "mode": "t2v",
            "prompt": f"{visual_prompt} Audio direction: {audio_prompt} Avoid: {negative_prompt}",
            "duration": 10,
            "aspect_ratio": "9:16",
            "resolution": "hd",
            "generate_audio": True,
            "safety_tolerance": 1,
            "draft": False,
        }
        concepts.append(
            VideoAdConcept(
                story_title=story_reference,
                story_url=story.url,
                variant_index=index,
                angle=angle,
                hook=hook,
                script=script,
                video_script=video_script,
                visual_prompt=visual_prompt,
                audio_prompt=audio_prompt,
                negative_prompt=negative_prompt,
                bfl_payload=payload,
            )
        )
    return concepts


def make_ad_safe_story_frame(market: str, story: NewsStory) -> str:
    return sanitize_story_for_ad(market, story).sanitized_frame


def make_script_story_reference(market: str, story: NewsStory) -> str:
    return sanitize_story_for_ad(market, story).sanitized_reference


IMPERATIVE_OPENERS = (
    "book",
    "bring",
    "come",
    "discover",
    "download",
    "get",
    "grab",
    "join",
    "order",
    "stop by",
    "swing by",
    "taste",
    "try",
    "visit",
)

PASTRY_TERMS = ("kouign", "pastry", "pastries", "patisserie", "patiserie", "croissant", "bakery", "baked")


def make_campaign_info(campaign_script: str) -> dict[str, str]:
    raw_phrase = " ".join(campaign_script.split())[:220] or "the featured offer"
    phrase, requested_cta = split_campaign_and_cta(raw_phrase)
    lower = phrase.lower()
    cta = make_default_cta(phrase)
    if "game" in lower:
        product = "a new casual mobile game"
        product_shot = (
            "phone-screen game reveal: a bright casual game on a handheld phone, one thumb tap, "
            "a satisfying level-clear burst, and a coffee cup resting beside it on a cafe table"
        )
        product_energy = "Quick-play energy"
        craving = "quick-play craving"
        cta = "Download the game and play on your next break."
    elif "sandwi" in lower:
        # Matches "sandwich" and the common "sandwitch" misspelling seen in website briefs.
        product = "a fresh made-to-order sandwich"
        product_shot = (
            "sandwich reveal: crusty bread sliced clean, layered fillings, crisp greens, a melty pull, "
            "wrapped in paper on a bright deli counter"
        )
        product_energy = "Fresh sandwich energy"
        craving = "lunch craving"
        cta = "Tap the link and order your sandwich now." if "link" in lower else "Grab your sandwich today."
    elif "frappe" in lower:
        product = "a new Frappe"
        product_shot = (
            "cold frappe reveal: clear cup, creamy blended coffee, whipped top, "
            "condensation, straw, and a clean cafe-counter close-up"
        )
        product_energy = "New Frappe energy"
        craving = "cool cafe craving"
    elif "coffee" in lower:
        product = "fresh coffee"
        product_shot = "fresh coffee reveal: warm cup, rich pour, gentle steam, and a clean cafe-counter close-up"
        product_energy = "Fresh coffee energy"
        craving = "coffee craving"
    elif any(term in lower for term in PASTRY_TERMS):
        product = "a fresh, flaky pastry"
        product_shot = (
            "bakery pastry reveal: caramelized, layered pastry on a marble bakery counter, buttery sheen, "
            "a light dusting of sugar, and an espresso cup resting beside it"
        )
        product_energy = "Fresh-from-the-oven energy"
        craving = "buttery pastry craving"
    elif any(term in lower for term in ("pottery", "ceramic", "clay")):
        product = "a date night pottery class"
        product_shot = (
            "hands shaping clay on a pottery wheel, warm studio lights, glazed mugs on a shelf, "
            "aprons, soft laughter, and a cozy class table"
        )
        product_energy = "Date night, shaped by hand"
        craving = "creative date-night plan"
    else:
        product = "featured offer"
        product_shot = "clean product reveal with appetizing lighting and a simple hero close-up"
        product_energy = "Fresh local energy"
        craving = "new craving"
    return {
        "phrase": phrase,
        "product": product,
        "product_shot": product_shot,
        "product_energy": product_energy,
        "craving": craving,
    "cta": requested_cta or cta,
    }


def make_default_cta(phrase: str) -> str:
    """Briefs written as an invitation ("Come try ...") are already a CTA; do not wrap them in "Try ... today"."""
    lower = phrase.lower()
    if any(lower == opener or lower.startswith(f"{opener} ") for opener in IMPERATIVE_OPENERS):
        return f"{phrase.rstrip(' .!')}."
    return f"Try {phrase} today."


def split_campaign_and_cta(phrase: str) -> tuple[str, str]:
    markers = ("call to action:", "cta:")
    lower = phrase.lower()
    for marker in markers:
        if marker in lower:
            index = lower.index(marker)
            campaign_phrase = phrase[:index].strip(" .")
            cta = phrase[index + len(marker) :].strip(" .")
            return campaign_phrase or phrase, cta
    return phrase, ""


def make_hook(market: str, story_reference: str, campaign: dict[str, str], angle: str) -> str:
    if angle == "local moment hook":
        return f"{market} is already talking about this: {story_reference}"
    if angle == "commuter craving":
        return f"On the way across {market}, the local buzz meets a {campaign['craving']}."
    if angle == "fan celebration":
        return f"When {market} has something to talk about, make the break memorable."
    if angle == "quick lunch rescue":
        return f"Everyone is following the local buzz. You can still plan something memorable."
    return f"The local feed is moving fast. End the moment with something refreshing."


def make_short_script(campaign: dict[str, str], hook: str, angle: str) -> str:
    return (
        f"Open with a local-current-events setup: {hook}. "
        f"Transition quickly into the advertiser message: {campaign['phrase']}. "
        "Keep it playful and avoid naming private individuals or implying anyone connected to the moment endorses the product. "
        f"Creative angle: {angle}. "
        f"End with a clear CTA: {campaign['cta']}"
    )


def make_10_second_video_script(
    campaign: dict[str, str],
    market: str,
    story_frame: str,
    story_reference: str,
    hook: str,
) -> str:
    return "\n".join(
        [
            "10-second vertical video commercial script",
            f"Market: {market}",
            f"Local event inspiration: {story_frame}",
            f"Local event reference to use in the ad: {story_reference}",
            f"Campaign message: {campaign['phrase']}",
            "",
            f"0.0-2.0s | Shot: Fast social-feed style montage of recognizable {market} street energy, phones lighting up, and abstract local-update card visuals tied to the event topic. | On-screen text: {market} is talking. | Voiceover: \"{market} is talking about {story_reference}.\"",
            f"2.0-4.0s | Shot: Quick abstract local-update cards slide by with no publisher logos, no real faces, and no private names; one card references: {story_reference}. | On-screen text: Local moment. Fresh twist. | Voiceover: \"When a local moment has everyone paying attention...\"",
            f"4.0-7.0s | Shot: Smash cut to an inviting {campaign['product_shot']}. | On-screen text: {campaign['product_energy']}. | Voiceover: \"...make your next twist {campaign['product']}.\"",
            f"7.0-10.0s | Shot: Hero product shot against a bright {market}-inspired backdrop, then quick end-card with a simple CTA. | On-screen text: {campaign['cta']} | Voiceover: \"{campaign['cta']}\"",
            "",
            "Brand-safety rules: reference the local event topic and city clearly, but do not show real private people, do not recreate sensitive events, do not show publisher logos, do not use famous brand references, and do not imply endorsement by anyone connected to the event.",
            f"Strategy note: {hook}",
        ]
    )


def make_visual_prompt(market: str, story_frame: str, angle: str, video_script: str) -> str:
    return (
        "Vertical mobile video ad, 9:16, polished social ad style, bright realistic lighting, "
        "fast readable visual pacing, no on-screen publisher logos. Create the video from this script. "
        f"Market: {market}. Local inspiration: {story_frame}. "
        f"Ad angle: {angle}. "
        "Scene: energetic local street-life montage, quick product close-up, happy everyday people, "
        "clear product payoff, tasteful local flavor without showing real private individuals or implying anyone "
        "connected to the local moment endorses the product. "
        f"Script: {video_script}"
    )


def make_audio_prompt(angle: str) -> str:
    if angle in {"fan celebration", "late-night payoff"}:
        return "Upbeat percussion, crowd energy, satisfying product reveal sound, warm friendly voiceover."
    if angle == "commuter craving":
        return "City ambience, light rhythmic music, transit whoosh, friendly concise voiceover."
    return "Bright playful music, subtle social feed notification sounds, crisp friendly voiceover."


def edit_ad_script_for_event_language(text: str) -> str:
    replacements = {
        "Local news inspiration": "Local event inspiration",
        "Story content reference": "Local event reference",
        "news story": "local event",
        "news subject": "person connected to the local moment",
        "local-news": "local-update",
        "local news": "local updates",
        "Local story": "Local moment",
        "local story": "local moment",
        "the story": "the local moment",
        "storytelling": "visual pacing",
        "story topic": "event topic",
        "story endorses": "event endorses",
        "from the story": "connected to the local moment",
    }
    edited = text
    for old, new in replacements.items():
        edited = edited.replace(old, new)
    return edited
