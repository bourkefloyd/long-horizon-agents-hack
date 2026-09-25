from __future__ import annotations

import unittest

from viral_local_ad_generator.prompts import make_campaign_info, split_campaign_and_cta


class MakeCampaignInfoTests(unittest.TestCase):
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


class SplitCampaignAndCtaTests(unittest.TestCase):
    def test_splits_on_cta_marker(self) -> None:
        self.assertEqual(split_campaign_and_cta("Launch. cta: Buy now."), ("Launch", "Buy now"))

    def test_returns_empty_cta_when_no_marker(self) -> None:
        self.assertEqual(split_campaign_and_cta("Launch"), ("Launch", ""))


if __name__ == "__main__":
    unittest.main()
