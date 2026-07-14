import os
import unittest
from unittest.mock import patch

from app.analysis import analyze_paragraph, split_paragraphs
from app.indian_kanoon import IndianKanoonError, authority_items, case_metadata_defaults, html_paragraphs
from app.insights import deterministic_insights, paragraph_takeaway


class LiveResearchTests(unittest.TestCase):
    def test_paragraph_analysis_extracts_nested_article(self):
        result = analyze_paragraph("The petitioner submitted that Article 19(1)(a) protects freedom of speech.")
        self.assertIn("Article 19(1)(a)", result["referenced_articles"])

    def test_live_html_preserves_source_paragraphs(self):
        html = '<p id="p12">12. The petitioner submitted that Article 19(1)(a) protects freedom of speech and expression.</p>'
        paragraph = html_paragraphs("123", html)[0]
        self.assertEqual(paragraph["paragraph_number"], "12")
        self.assertIn("/doc/123/#p12", paragraph["source_url"])
        self.assertGreaterEqual(len(paragraph["ai_analysis"]["bullets"]), 2)

    def test_split_paragraphs_discards_short_fragments(self):
        text = "Short\n\nThis is a sufficiently detailed legal paragraph that provides enough source material for the analysis pipeline to process correctly."
        self.assertEqual(len(split_paragraphs(text)), 1)

    def test_missing_token_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            from app.indian_kanoon import api_request
            with self.assertRaises(IndianKanoonError) as context:
                api_request("/search/")
        self.assertEqual(context.exception.status_code, 503)

    def test_concise_fallback_populates_all_dashboard_sections(self):
        paragraphs = [
            {"classification": "Facts", "original_text": "In 2019 the petitioner challenged the order issued by the respondent authority."},
            {"classification": "Arguments", "original_text": "Learned counsel submitted that the restriction violated Article 19(1)(a)."},
            {"classification": "Holding", "original_text": "The Court held that the restriction was not justified under the statute."},
        ]
        insights = deterministic_insights(paragraphs, " ".join(item["original_text"] for item in paragraphs))
        self.assertIn("Key Dates", insights["overview"])
        self.assertTrue(all(insights[key] for key in ("facts", "arguments", "judgment", "ratio_decidendi", "obiter_dicta", "final_decision")))
        keys = ("overview", "facts", "issues", "arguments", "judgment", "ratio_decidendi", "obiter_dicta", "final_decision")
        self.assertEqual(len({insights[key].lower() for key in keys}), len(keys))

    def test_statute_metadata_uses_jurisdiction_defaults(self):
        court, bench, year = case_metadata_defaults("Article 19 of the Constitution", "The Constitution was enacted in 1950.", {}, {})
        self.assertIn("Supreme Court", court)
        self.assertIn("Constitutional Interpretation", bench)
        self.assertEqual(year, "1950")

    def test_authority_parser_uses_citation_and_citedby_lists(self):
        items = authority_items({"citeList": [{"tid": 11, "title": "A v. B"}], "citedbyList": [{"tid": 12, "title": "C v. D"}]}, "10")
        self.assertEqual({item["reason"] for item in items}, {"Cited authority", "Cited by"})

    def test_paragraph_takeaway_is_short_and_source_grounded(self):
        takeaway = paragraph_takeaway("The Court held that Article 19 protects speech.", {"classification": "Holding", "referenced_articles": ["Article 19"], "referenced_acts": []})
        self.assertLessEqual(len(takeaway["bullets"]), 3)
        self.assertIn("Legal focus", takeaway["bullets"][0])


if __name__ == "__main__":
    unittest.main()
