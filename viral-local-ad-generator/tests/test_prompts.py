from __future__ import annotations

import unittest

from viral_local_ad_generator.models import NewsStory
from viral_local_ad_generator.prompts import (
    ANGLES,
    generate_video_concepts,
    make_campaign_info,
    order_angles,
    split_campaign_and_cta,
)

TAQUERIA_BRIEF = (
    "Late-night al pastor tacos carved fresh off the trompo until 2 AM, two blocks from the 24th St Mission BART. "
    "Order ahead on the link and skip the line after the show. CTA: Order ahead and skip the line."
)


class MakeCampaignInfoTests(unittest.TestCase):
    def test_taco_brief_gets_a_trompo_product_shot(self) -> None:
        campaign = make_campaign_info(TAQUERIA_BRIEF)

        self.assertEqual(campaign["product"], "fresh al pastor tacos")
        self.assertIn("trompo", campaign["product_shot"])
        self.assertEqual(campaign["product_energy"], "Late-night taco energy")
        self.assertEqual(campaign["craving"], "late-night taco craving")
        # The explicit CTA marker still wins over the taco default.
        self.assertEqual(campaign["cta"], "Order ahead and skip the line")

    def test_taco_brief_without_al_pastor_or_late_night_uses_generic_taco_copy(self) -> None:
        campaign = make_campaign_info("Neighborhood taqueria lunch special")

        self.assertEqual(campaign["product"], "fresh street tacos")
        self.assertEqual(campaign["product_energy"], "Fresh taco energy")
        self.assertEqual(campaign["craving"], "taco craving")
        self.assertEqual(campaign["cta"], "Grab your tacos today.")

    def test_taco_brief_with_a_link_gets_an_order_ahead_cta(self) -> None:
        campaign = make_campaign_info("Street tacos, order on the link")

        self.assertEqual(campaign["cta"], "Order ahead on the link and skip the line.")

    def test_long_brief_keeps_its_explicit_cta_after_truncation(self) -> None:
        padding = "Fresh tacos every night " * 12  # ~290 chars, longer than the phrase cap
        campaign = make_campaign_info(f"{padding.strip()}. CTA: Order ahead tonight.")

        self.assertEqual(campaign["cta"], "Order ahead tonight")
        self.assertLessEqual(len(campaign["phrase"]), 220)
        self.assertNotIn("CTA", campaign["phrase"])


    def test_imperative_brief_is_reused_as_the_cta(self) -> None:
        campaign = make_campaign_info("Come try our famous kouign Amann")

        self.assertEqual(campaign["cta"], "Come try our famous kouign Amann.")
        self.assertNotIn("Try Come", campaign["cta"])

    def test_pastry_brief_gets_a_bakery_product_shot(self) -> None:
        campaign = make_campaign_info("Come try our famous kouign Amann")

        self.assertIn("pastry", campaign["product"])
        self.assertIn("bakery", campaign["product_shot"])
        self.assertIn("pastry", campaign["craving"])

    def test_descriptive_brief_keeps_the_try_today_cta(self) -> None:
        campaign = make_campaign_info("Fresh coffee for the morning commute")

        self.assertEqual(campaign["cta"], "Try Fresh coffee for the morning commute today.")
        self.assertEqual(campaign["product"], "fresh coffee")

    def test_explicit_cta_marker_wins_over_imperative_detection(self) -> None:
        campaign = make_campaign_info("Come try our croissants. CTA: Order ahead for pickup")

        self.assertEqual(campaign["phrase"], "Come try our croissants")
        self.assertEqual(campaign["cta"], "Order ahead for pickup")

    def test_sandwich_brief_gets_a_food_product_shot_and_order_cta(self) -> None:
        campaign = make_campaign_info("Casual sandwich lovers buy now link")

        self.assertEqual(campaign["product"], "a fresh made-to-order sandwich")
        self.assertIn("sandwich", campaign["product_shot"])
        self.assertEqual(campaign["cta"], "Tap the link and order your sandwich now.")
        self.assertEqual(campaign["craving"], "lunch craving")
        self.assertNotIn("buy now link", campaign["cta"].lower())

    def test_sandwich_brief_tolerates_the_sandwitch_misspelling(self) -> None:
        campaign = make_campaign_info("Casual sandwitch lovers buy now link")

        self.assertEqual(campaign["product"], "a fresh made-to-order sandwich")
        self.assertEqual(campaign["cta"], "Tap the link and order your sandwich now.")

    def test_sandwich_brief_without_a_link_uses_a_visit_cta(self) -> None:
        campaign = make_campaign_info("Neighborhood sandwich shop grand opening")

        self.assertEqual(campaign["product"], "a fresh made-to-order sandwich")
        self.assertEqual(campaign["cta"], "Grab your sandwich today.")

    def test_explicit_cta_marker_wins_over_the_sandwich_default(self) -> None:
        campaign = make_campaign_info("Sandwich shop launch. CTA: Order ahead for lunch.")

        self.assertEqual(campaign["phrase"], "Sandwich shop launch")
        # split_campaign_and_cta strips the trailing period from explicit CTAs.
        self.assertEqual(campaign["cta"], "Order ahead for lunch")

    def test_game_branch_is_unchanged(self) -> None:
        campaign = make_campaign_info("Casual mobile game cross-promo for SF coffee lovers")

        self.assertEqual(campaign["product"], "a new casual mobile game")
        self.assertEqual(campaign["cta"], "Download the game and play on your next break.")

    def test_coffee_and_frappe_branches_are_unchanged(self) -> None:
        self.assertEqual(make_campaign_info("Fresh coffee for commuters")["product"], "fresh coffee")
        self.assertEqual(make_campaign_info("New Frappe launch")["product"], "a new Frappe")

    def test_unknown_brief_falls_back_to_featured_offer(self) -> None:
        campaign = make_campaign_info("Something nobody has a template for")

        self.assertEqual(campaign["product"], "featured offer")
        self.assertEqual(campaign["cta"], "Try Something nobody has a template for today.")

    def test_empty_brief_uses_placeholder_phrase(self) -> None:
        self.assertEqual(make_campaign_info("   ")["phrase"], "the featured offer")


class OrderAnglesTests(unittest.TestCase):
    def test_brief_without_time_of_day_keeps_the_canonical_order(self) -> None:
        for brief in (
            "Casual mobile game cross-promo for SF coffee lovers",
            "Casual sandwitch lovers buy now link",
            "Come try our famous kouign Amann",
            "Fred's Coffee new Frappe",
        ):
            self.assertEqual(order_angles(brief), list(ANGLES), brief)

    def test_late_night_brief_promotes_the_late_night_angle_into_the_first_three(self) -> None:
        angles = order_angles(TAQUERIA_BRIEF)

        self.assertEqual(angles[0], "local moment hook")
        self.assertEqual(angles[:3], ["local moment hook", "commuter craving", "late-night payoff"])
        self.assertEqual(sorted(angles), sorted(ANGLES))

    def test_lunch_brief_promotes_the_lunch_angle(self) -> None:
        angles = order_angles("Weekday lunch special for office workers")

        self.assertEqual(angles[:2], ["local moment hook", "quick lunch rescue"])
        self.assertEqual(sorted(angles), sorted(ANGLES))

    def test_concept_variant_numbering_follows_the_ordered_angles(self) -> None:
        story = NewsStory(title="San Francisco celebrates culture of lowriding", url="https://example.com/lowriding")
        concepts = generate_video_concepts(TAQUERIA_BRIEF, "San Francisco Mission District", story)

        self.assertEqual([concept.variant_index for concept in concepts], [1, 2, 3, 4, 5])
        self.assertEqual(concepts[2].angle, "late-night payoff")
        self.assertIn("al pastor", concepts[2].video_script)
        self.assertIn("Order ahead and skip the line", concepts[2].video_script)


class SplitCampaignAndCtaTests(unittest.TestCase):
    def test_splits_on_cta_marker(self) -> None:
        self.assertEqual(split_campaign_and_cta("Launch. cta: Buy now."), ("Launch", "Buy now"))

    def test_returns_empty_cta_when_no_marker(self) -> None:
        self.assertEqual(split_campaign_and_cta("Launch"), ("Launch", ""))


if __name__ == "__main__":
    unittest.main()
