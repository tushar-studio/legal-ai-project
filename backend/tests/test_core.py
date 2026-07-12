"""Core checks for the local Legal AI workflow (no network or API key required)."""
import unittest

from app.analysis import analyze_paragraph, split_paragraphs
from app.database import initialize_database
from app.main import dynamic_similar_cases, heritage_tree, search_cases


class LegalAiCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_search_returns_related_topics(self):
        result = search_cases("press freedom")
        self.assertGreater(result["count"], 0)
        self.assertIn("Press Freedom", result["related_topics"])

    def test_similar_cases_are_dynamic(self):
        results = dynamic_similar_cases("romesh-thappar")
        self.assertGreater(len(results), 0)
        self.assertIn("similarity_score", results[0])
        self.assertIn("reason", results[0])

    def test_heritage_tree_has_current_case(self):
        tree = heritage_tree("romesh-thappar")
        self.assertTrue(tree["root"]["topics"])
        self.assertTrue(any(node["is_current"] for node in tree["nodes"]))

    def test_paragraph_processing_extracts_metadata(self):
        text = "The petitioner submitted that Article 19(1)(a) protects freedom of speech under the Constitution of India."
        result = analyze_paragraph(text)
        self.assertEqual(result["classification"], "Arguments")
        self.assertIn("Article 19(1)(a)", result["referenced_articles"])
        self.assertEqual(split_paragraphs("short\n\n" + text), [text])


if __name__ == "__main__":
    unittest.main()
