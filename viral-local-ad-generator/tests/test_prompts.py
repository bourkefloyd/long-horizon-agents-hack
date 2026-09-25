from __future__ import annotations

import unittest

from viral_local_ad_generator.prompts import make_campaign_info


class MakeCampaignInfoTests(unittest.TestCase):
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

    def test_game_brief_still_uses_the_game_branch(self) -> None:
        campaign = make_campaign_info("Casual mobile game cross-promo for SF coffee lovers")

        self.assertEqual(campaign["product"], "a new casual mobile game")
        self.assertEqual(campaign["cta"], "Download the game and play on your next break.")


if __name__ == "__main__":
    unittest.main()
