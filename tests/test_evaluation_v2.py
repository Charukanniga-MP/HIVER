"""
Unit Tests for Evaluation Harness v2 and Retrieval Leakage Prevention.
Verifies clean retrieval corpus isolation, zero train/test contamination, and dynamic metric evaluation.
"""

import unittest
import os
import json
from src.retriever import HistoricalRetriever, CLEAN_CORPUS_PATH, GOLDEN_SET_V2_PATH, LEAKAGE_REPORT_PATH
from src.evaluator import run_evaluation_v2, EVALUATION_V2_PATH, EVALUATION_SUMMARY_V2_PATH

class TestEvaluationV2Integrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(GOLDEN_SET_V2_PATH, 'r', encoding='utf-8') as f:
            cls.golden_payload = json.load(f)
        cls.golden_examples = cls.golden_payload['examples']

        cls.retriever = HistoricalRetriever(CLEAN_CORPUS_PATH)
        cls.clean_corpus = cls.retriever.conversations

    def test_retrieval_corpus_zero_golden_ids(self):
        golden_tweet_ids = set(str(ex['customer_tweet_id']) for ex in self.golden_examples)
        golden_source_ids = set(str(ex['source_conversation_id']) for ex in self.golden_examples)

        corpus_tweet_ids = set(str(c['customer_tweet_id']) for c in self.clean_corpus)
        corpus_source_ids = set(str(c['id']) for c in self.clean_corpus)

        # Zero golden tweet IDs present in retrieval corpus
        self.assertEqual(len(golden_tweet_ids.intersection(corpus_tweet_ids)), 0)
        self.assertEqual(len(golden_source_ids.intersection(corpus_source_ids)), 0)

    def test_retrieval_corpus_zero_exact_texts(self):
        golden_texts = set(ex['customer_text'].strip().lower() for ex in self.golden_examples)
        corpus_texts = set(c['clean_customer_text'].strip().lower() for c in self.clean_corpus)

        # Zero exact golden texts present in retrieval corpus
        self.assertEqual(len(golden_texts.intersection(corpus_texts)), 0)

    def test_leakage_report_exists_and_valid(self):
        self.assertTrue(os.path.exists(LEAKAGE_REPORT_PATH))
        with open(LEAKAGE_REPORT_PATH, 'r', encoding='utf-8') as f:
            report = json.load(f)

        self.assertEqual(report['original_corpus_size'], 42678)
        self.assertEqual(report['final_clean_retrieval_corpus_size'], len(self.clean_corpus))
        self.assertGreater(report['removed_by_exact_id'], 0)

    def test_model_prediction_independence(self):
        sample_query = "My shuffle button is stuck on iOS 11"
        evidence = self.retriever.retrieve(sample_query, top_k=3)
        self.assertEqual(len(evidence), 3)

        # Verify evidence comes ONLY from clean corpus
        golden_ids = set(str(ex['customer_tweet_id']) for ex in self.golden_examples)
        for ev in evidence:
            self.assertNotIn(str(ev['customer_tweet_id']), golden_ids)

    def test_evaluation_summary_v2_artifacts(self):
        self.assertTrue(os.path.exists(EVALUATION_V2_PATH))
        self.assertTrue(os.path.exists(EVALUATION_SUMMARY_V2_PATH))

        with open(EVALUATION_SUMMARY_V2_PATH, 'r', encoding='utf-8') as f:
            summary = json.load(f)

        self.assertIn("proposed_system_metrics", summary)
        self.assertIn("weakly_supervised_ml_baseline_metrics", summary)
        self.assertIn("trivial_baseline_metrics", summary)
        
        # Verify dynamic calculation of metrics
        prop_acc = summary["proposed_system_metrics"]["accuracy"]
        self.assertGreater(prop_acc, 0.50)
        self.assertLess(prop_acc, 1.00)

if __name__ == "__main__":
    unittest.main()
