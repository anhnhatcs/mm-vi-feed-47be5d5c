"""Pin the article extractor against real saved pages.

If MM changes its markup these fail loudly, instead of the feed quietly filling with
teasers or with related-article link noise.

Run: python3 -m unittest discover -s tests -v      (from the project root)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from article import extract_body, is_gated, slice_container  # noqa: E402

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return fh.read()


class FreeArticle(unittest.TestCase):
    def setUp(self):
        self.html = load("free_article.html")

    def test_container_is_found(self):
        self.assertIsNotNone(slice_container(self.html))

    def test_body_is_substantial(self):
        self.assertGreater(len(extract_body(self.html)), 1000)

    def test_body_starts_with_the_dateline(self):
        self.assertTrue(extract_body(self.html).startswith("Berlin."))

    def test_no_related_article_link_noise(self):
        # The related-articles list leaks "_arid,NNN.html" strings into the body
        # when the extractor falls back to sweeping every <p> on the page.
        self.assertNotIn("_arid,", extract_body(self.html))

    def test_dpa_credit_is_stripped(self):
        self.assertNotIn("dpa-infocom", extract_body(self.html))

    def test_not_reported_as_gated(self):
        self.assertFalse(is_gated(self.html))


class GatedArticle(unittest.TestCase):
    def setUp(self):
        self.html = load("gated_article.html")

    def test_container_is_absent(self):
        self.assertIsNone(slice_container(self.html))

    def test_body_is_empty(self):
        self.assertEqual(extract_body(self.html), "")

    def test_is_detected_as_gated(self):
        self.assertTrue(is_gated(self.html))


class GateHeuristic(unittest.TestCase):
    def test_share_widget_is_not_a_gate_signal(self):
        # "Artikel freischalten" appears on every page including free ones;
        # treating it as the paywall marker reports 100% gated.
        self.assertIn("Artikel freischalten", load("free_article.html"))
        self.assertFalse(is_gated(load("free_article.html")))


if __name__ == "__main__":
    unittest.main()
