import os
import unittest
from unittest.mock import patch

from app.analysis import analyze_paragraph, split_paragraphs
from app.indian_kanoon import IndianKanoonError, html_paragraphs


class LiveResearchTests(unittest.TestCase):
    def test_paragraph_analysis_extracts_nested_article(self):
        result = analyze_paragraph("The petitioner submitted that Article 19(1)(a) protects freedom of speech.")
        self.assertIn("Article 19(1)(a)", result["referenced_articles"])

    def test_live_html_preserves_source_paragraphs(self):
        html = '<p id="p12">12. The petitioner submitted that Article 19(1)(a) protects freedom of speech and expression.</p>'
        paragraph = html_paragraphs("123", html)[0]
        self.assertEqual(paragraph["paragraph_number"], "12")
        self.assertIn("/doc/123/#p12", paragraph["source_url"])

    def test_split_paragraphs_discards_short_fragments(self):
        text = "Short\n\nThis is a sufficiently detailed legal paragraph that provides enough source material for the analysis pipeline to process correctly."
        self.assertEqual(len(split_paragraphs(text)), 1)

    def test_missing_token_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            from app.indian_kanoon import api_request
            with self.assertRaises(IndianKanoonError) as context:
                api_request("/search/")
        self.assertEqual(context.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
