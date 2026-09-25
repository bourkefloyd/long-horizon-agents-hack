from __future__ import annotations

import unittest

from viral_local_ad_generator.models import NewsStory
from viral_local_ad_generator.prompts import make_hook
from viral_local_ad_generator.sanitizer import sanitize_story_for_ad


def story(title: str, snippet: str = "") -> NewsStory:
    return NewsStory(title=title, url="https://example.com/story", source="Example", snippet=snippet)


class GenericTitleSanitizationTests(unittest.TestCase):
    def test_generic_title_is_quoted_as_a_headline(self) -> None:
        clean = sanitize_story_for_ad("San Francisco", story("San Francisco celebrates culture of lowriding"))

        self.assertEqual(clean.sanitized_reference, 'the headline "San Francisco celebrates culture of lowriding"')
        self.assertEqual(
            clean.sanitized_frame,
            'a San Francisco local moment behind the headline "San Francisco celebrates culture of lowriding"',
        )
        self.assertIn("publisher_suffix_removed", clean.sanitization_notes)

    def test_publisher_suffix_and_trailing_punctuation_are_dropped(self) -> None:
        clean = sanitize_story_for_ad("San Francisco", story("Local bakery collab sells out in minutes. | SFGate"))

        self.assertEqual(clean.sanitized_reference, 'the headline "Local bakery collab sells out in minutes"')

    def test_hook_reads_as_one_sentence(self) -> None:
        clean = sanitize_story_for_ad("San Francisco", story("San Francisco celebrates culture of lowriding"))
        hook = make_hook("San Francisco", clean.sanitized_reference, {"craving": "pastry craving"}, "local moment hook")

        self.assertEqual(
            hook,
            'San Francisco is already talking about this: the headline "San Francisco celebrates culture of lowriding"',
        )
        self.assertNotIn("local story about", hook)
        self.assertNotIn("local moment about", hook)

    def test_sensitive_title_keeps_the_generalized_note(self) -> None:
        clean = sanitize_story_for_ad("San Francisco", story("Neighbors file lawsuit over new bike lane"))

        self.assertIn("sensitive_terms_generalized", clean.sanitization_notes)
        self.assertEqual(clean.sanitized_reference, 'the headline "Neighbors file lawsuit over new bike lane"')

    def test_famous_brand_in_title_falls_back_to_a_neutral_frame(self) -> None:
        clean = sanitize_story_for_ad("San Francisco", story("New Starbucks opens downtown"))

        self.assertEqual(clean.sanitized_reference, "San Francisco's local culture-and-community moment")
        self.assertTrue(any(note.startswith("fallback_removed_famous_brand_terms") for note in clean.sanitization_notes))


if __name__ == "__main__":
    unittest.main()
