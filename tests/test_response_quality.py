"""
Unit Tests for Response Quality Evaluation Suite.
Tests LLM Judge output formatting, score bounds, unfilled human template integrity,
agreement calculation edge cases, reproducible sampling, and API key leakage prevention.
"""

import unittest
import os
import json

from src.llm_judge import judge_response, NonLLMFallbackJudge
from src.agreement_metrics import calculate_agreement, compute_cohen_kappa_quadratic
from scripts.sample_judge_set import create_judge_sample, JUDGE_SAMPLE_PATH
from scripts.rate_judge_sample import HUMAN_TEMPLATE_PATH

class TestResponseQualitySuite(unittest.TestCase):
    def test_1_structured_judge_output_and_bounds(self):
        res = judge_response(
            customer_message="shuffle keeps pausing on my iPhone",
            generated_reply="Hey! Try restarting your device and updating Spotify.",
            retrieved_evidence=[{"similarity_score": 0.65}],
            intent="playback_audio_issue",
            escalation_decision="AUTO-HANDLE"
        )
        self.assertIn("relevance", res)
        self.assertIn("groundedness", res)
        self.assertIn("helpfulness", res)
        self.assertIn("correctness", res)
        self.assertIn("overall_score", res)
        self.assertIn("reasoning", res)
        self.assertIn("evaluator_type", res)

        for dim in ["relevance", "groundedness", "helpfulness", "correctness"]:
            self.assertGreaterEqual(res[dim], 1)
            self.assertLessEqual(res[dim], 5)

        self.assertGreaterEqual(res["overall_score"], 1.0)
        self.assertLessEqual(res["overall_score"], 5.0)

    def test_2_unfilled_human_template_integrity(self):
        self.assertTrue(os.path.exists(HUMAN_TEMPLATE_PATH))
        with open(HUMAN_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            template = json.load(f)

        examples = template.get("examples", [])
        self.assertEqual(len(examples), 30)

        # Verify ZERO human scores are pre-filled (must be null)
        for ex in examples:
            self.assertIsNone(ex["human_relevance"])
            self.assertIsNone(ex["human_groundedness"])
            self.assertIsNone(ex["human_helpfulness"])
            self.assertIsNone(ex["human_correctness"])
            self.assertIsNone(ex["human_overall_score"])

        self.assertFalse(template["metadata"]["has_genuine_human_ratings"])

    def test_3_agreement_metrics_empty_human_ratings(self):
        agreement_payload = calculate_agreement()
        self.assertIn("metadata", agreement_payload)
        self.assertFalse(agreement_payload["metadata"]["has_genuine_human_ratings"])
        self.assertIn("No genuine human ratings recorded yet", agreement_payload["metadata"]["status_message"])

    def test_4_cohen_kappa_calculation(self):
        r1 = [5, 4, 3, 2, 1]
        r2 = [5, 4, 3, 2, 1]
        kappa_perfect = compute_cohen_kappa_quadratic(r1, r2)
        self.assertEqual(kappa_perfect, 1.0)

        r3 = [1, 2, 3, 4, 5]
        kappa_imperfect = compute_cohen_kappa_quadratic(r1, r3)
        self.assertLess(kappa_imperfect, 0.5)

    def test_5_reproducible_sampling(self):
        sample1 = create_judge_sample(sample_size=20, seed=123)
        sample2 = create_judge_sample(sample_size=20, seed=123)

        ids1 = [x["id"] for x in sample1["examples"]]
        ids2 = [x["id"] for x in sample2["examples"]]
        self.assertEqual(ids1, ids2)

    def test_6_zero_api_key_leakage(self):
        target_files = [
            r'd:\Hiver\data\judge_sample.json',
            r'd:\Hiver\data\llm_judge_results.json',
            r'd:\Hiver\data\human_rating_template.json',
            r'd:\Hiver\data\judge_human_agreement.json',
            r'd:\Hiver\data\response_quality_summary.json'
        ]
        for fpath in target_files:
            if os.path.exists(fpath):
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.assertNotIn("sk-proj-", content)
                self.assertNotIn("Bearer sk-", content)

if __name__ == "__main__":
    unittest.main()
