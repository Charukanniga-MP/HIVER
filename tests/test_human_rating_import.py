"""
Unit Tests for Human Rating Import Workflow and Agreement Metrics.
Covers:
1. Valid import
2. Invalid score (out of 1-5 range, non-integer, missing dimension)
3. Duplicate ID in input
4. Unknown ID in input
5. Missing rating / empty input array
6. Accidental overwrite protection (raises without --overwrite)
7. Agreement calculation with valid ratings
8. No-human-rating agreement fallback case
9. No-real-LLM evaluation state handling
"""

import unittest
import os
import json
import tempfile

from scripts.import_human_ratings import validate_and_import_ratings, HUMAN_RATINGS_PATH, HUMAN_TEMPLATE_PATH
from src.agreement_metrics import calculate_agreement

class TestHumanRatingImportWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_input_path = os.path.join(self.temp_dir.name, "test_ratings.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_input(self, data):
        with open(self.test_input_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_1_valid_import(self):
        valid_input = [
            {"id": "GOLDEN-002", "relevance": 5, "groundedness": 5, "helpfulness": 4, "correctness": 5},
            {"id": "GOLDEN-006", "relevance": 3, "groundedness": 4, "helpfulness": 4, "correctness": 3}
        ]
        self._write_input(valid_input)
        
        # Test valid import logic
        res = validate_and_import_ratings(self.test_input_path, overwrite=True)
        self.assertIn("metadata", res)
        self.assertTrue(res["metadata"]["has_genuine_human_ratings"])
        
        # Verify overall score calculation: 0.30*5 + 0.30*5 + 0.20*4 + 0.20*5 = 1.5 + 1.5 + 0.8 + 1.0 = 4.8
        ex1 = next(x for x in res["examples"] if x["id"] == "GOLDEN-002")
        self.assertEqual(ex1["human_overall_score"], 4.8)

    def test_2_invalid_score_out_of_range(self):
        invalid_input = [
            {"id": "GOLDEN-002", "relevance": 6, "groundedness": 5, "helpfulness": 4, "correctness": 5}
        ]
        self._write_input(invalid_input)
        with self.assertRaises(ValueError) as ctx:
            validate_and_import_ratings(self.test_input_path, overwrite=True)
        self.assertIn("Rating must be an integer between 1 and 5", str(ctx.exception))

    def test_2b_invalid_score_non_integer(self):
        invalid_input = [
            {"id": "GOLDEN-002", "relevance": 4.5, "groundedness": 5, "helpfulness": 4, "correctness": 5}
        ]
        self._write_input(invalid_input)
        with self.assertRaises(ValueError) as ctx:
            validate_and_import_ratings(self.test_input_path, overwrite=True)
        self.assertIn("Rating must be an integer between 1 and 5", str(ctx.exception))

    def test_3_duplicate_id_in_input(self):
        duplicate_input = [
            {"id": "GOLDEN-002", "relevance": 5, "groundedness": 5, "helpfulness": 4, "correctness": 5},
            {"id": "GOLDEN-002", "relevance": 4, "groundedness": 4, "helpfulness": 3, "correctness": 4}
        ]
        self._write_input(duplicate_input)
        with self.assertRaises(ValueError) as ctx:
            validate_and_import_ratings(self.test_input_path, overwrite=True)
        self.assertIn("Duplicate rating found in input file for ID: 'GOLDEN-002'", str(ctx.exception))

    def test_4_unknown_id_in_input(self):
        unknown_input = [
            {"id": "NON-EXISTENT-999", "relevance": 5, "groundedness": 5, "helpfulness": 4, "correctness": 5}
        ]
        self._write_input(unknown_input)
        with self.assertRaises(ValueError) as ctx:
            validate_and_import_ratings(self.test_input_path, overwrite=True)
        self.assertIn("Unknown ID 'NON-EXISTENT-999'", str(ctx.exception))

    def test_5_missing_rating_dimension(self):
        missing_dim_input = [
            {"id": "GOLDEN-002", "relevance": 5, "groundedness": 5, "helpfulness": 4}  # missing correctness
        ]
        self._write_input(missing_dim_input)
        with self.assertRaises(ValueError) as ctx:
            validate_and_import_ratings(self.test_input_path, overwrite=True)
        self.assertIn("Missing mandatory rating dimension 'correctness'", str(ctx.exception))

    def test_6_accidental_overwrite_protection(self):
        valid_input = [
            {"id": "GOLDEN-002", "relevance": 5, "groundedness": 5, "helpfulness": 4, "correctness": 5}
        ]
        self._write_input(valid_input)
        validate_and_import_ratings(self.test_input_path, overwrite=True)

        # Attempt to import again without overwrite flag
        with self.assertRaises(ValueError) as ctx:
            validate_and_import_ratings(self.test_input_path, overwrite=False)
        self.assertIn("already exists", str(ctx.exception))
        self.assertIn("overwrite", str(ctx.exception))

    def test_7_agreement_calculation_with_ratings(self):
        # Prepare valid human rating for an ID present in llm_judge_results.json (e.g. GOLDEN-008)
        valid_input = [
            {"id": "GOLDEN-008", "relevance": 5, "groundedness": 5, "helpfulness": 5, "correctness": 5}
        ]
        self._write_input(valid_input)
        validate_and_import_ratings(self.test_input_path, overwrite=True)

        # Run calculate_agreement
        agreement = calculate_agreement()
        self.assertIn("metadata", agreement)
        self.assertTrue(agreement["metadata"]["has_genuine_human_ratings"])
        self.assertIn("dimensional_agreement", agreement)

    def test_8_no_human_rating_agreement_case(self):
        # Reset ratings to unfilled template
        from scripts.rate_judge_sample import init_human_rating_template
        template_payload = init_human_rating_template()

        if os.path.exists(HUMAN_RATINGS_PATH):
            with open(HUMAN_RATINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(template_payload, f)

        agreement = calculate_agreement()
        self.assertFalse(agreement["metadata"]["has_genuine_human_ratings"])
        self.assertIsNone(agreement.get("agreement_metrics"))

    def test_9_no_real_llm_case_handling(self):
        # Verify LLM judge output file contains real_llm_executed status
        judge_path = r'd:\Hiver\data\llm_judge_results.json'
        self.assertTrue(os.path.exists(judge_path))
        with open(judge_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        meta = data.get("metadata", {})
        self.assertIn("real_llm_executed", meta)
        # Should cleanly state fallback status if real LLM API was not run
        if not meta["real_llm_executed"]:
            self.assertEqual(meta["evaluator"], "NonLLMFallbackJudge")
            self.assertIn("unconfigured or rate-limited", meta["status_message"])

if __name__ == "__main__":
    unittest.main()
