"""
Unit tests for src.final_evaluator module.
Verifies evaluation computations, data integrity, response quality statistics, and artifact output.
"""

import os
import json
import unittest

from src.final_evaluator import (
    compute_response_quality_metrics,
    extract_dynamic_failure_analysis,
    run_final_evaluation,
    HUMAN_RATINGS_PATH,
    FINAL_EVALUATION_PATH,
    FINAL_SUMMARY_PATH,
    FINAL_FAILURE_ANALYSIS_PATH
)

class TestFinalEvaluator(unittest.TestCase):

    def setUp(self):
        input_file = r'd:\Hiver\data\human_ratings_input.json'
        if os.path.exists(input_file):
            from scripts.import_human_ratings import validate_and_import_ratings
            validate_and_import_ratings(input_file, overwrite=True)

    def test_compute_response_quality_metrics_structure(self):
        result = compute_response_quality_metrics()
        self.assertIn("metadata", result)
        self.assertIn("metrics", result)
        self.assertEqual(result["metadata"]["total_rated"], 30)
        self.assertTrue(result["metadata"]["has_genuine_human_ratings"])
        
        metrics = result["metrics"]
        self.assertIn("mean_relevance", metrics)
        self.assertIn("mean_groundedness", metrics)
        self.assertIn("mean_helpfulness", metrics)
        self.assertIn("mean_correctness", metrics)
        self.assertIn("mean_overall_score", metrics)
        self.assertGreaterEqual(metrics["mean_overall_score"], 1.0)
        self.assertLessEqual(metrics["mean_overall_score"], 5.0)

    def test_extract_dynamic_failure_analysis(self):
        sample_results = [
            {
                "id": "GOLDEN-001",
                "customer_text": "Sample test message",
                "true_intent": "billing_subscription_dispute",
                "predicted_intent": "billing_subscription_dispute",
                "intent_correct": True,
                "intent_confidence": 0.90,
                "intent_reason": "Rule match",
                "retrieval_best_similarity": 0.80,
                "evidence_quality": "strong",
                "evidence_ids": ["SPOT-001"],
                "true_escalation": "AUTO-HANDLE",
                "predicted_escalation": "ESCALATE TO HUMAN",
                "escalation_correct": False,
                "escalation_reason": "Low confidence test",
                "risk_level": "LOW",
                "generated_reply": "Sample reply",
                "grounding_reason": "Grounding ok"
            }
        ]
        payload = extract_dynamic_failure_analysis(sample_results)
        self.assertEqual(payload["metadata"]["total_examples"], 1)
        self.assertEqual(payload["metadata"]["total_failures"], 1)
        self.assertGreater(len(payload["top_failure_modes"]), 0)
        mode = payload["top_failure_modes"][0]
        self.assertIn("failure_mode_name", mode)
        self.assertIn("customer_message", mode)
        self.assertIn("fix_hypothesis", mode)

    def test_run_final_evaluation_exports_artifacts(self):
        summary = run_final_evaluation()
        self.assertTrue(os.path.exists(FINAL_EVALUATION_PATH))
        self.assertTrue(os.path.exists(FINAL_SUMMARY_PATH))
        self.assertTrue(os.path.exists(FINAL_FAILURE_ANALYSIS_PATH))

        with open(FINAL_SUMMARY_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.assertIn("baseline_comparison", data)
        self.assertIn("trivial_baseline", data["baseline_comparison"])
        self.assertIn("weakly_supervised_ml_baseline", data["baseline_comparison"])
        self.assertIn("proposed_system", data["baseline_comparison"])
        self.assertEqual(data["metadata"]["golden_set_size"], 200)

if __name__ == "__main__":
    unittest.main()
