"""
Unit Tests for SpotifyCares AI Customer Support Agent.
Tests Preprocessing, Intent Classification, Historical Retrieval, Escalation Rules, and Edge Cases.
"""

import unittest
from src.data_pipeline import clean_tweet_text
from src.intent_taxonomy import classify_intent_rule_based
from src.retriever import HistoricalRetriever
from src.escalation import evaluate_escalation
from src.generator import generate_support_reply

class TestSpotifyCaresPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = HistoricalRetriever()

    def test_preprocessing_clean_text(self):
        raw = "@SpotifyCares my &amp; playback keeps pausing @115887 https://t.co/xyz"
        clean = clean_tweet_text(raw)
        self.assertEqual(clean, "my & playback keeps pausing")

    def test_intent_classification(self):
        intent, conf = classify_intent_rule_based("my shuffle and repeat button are stuck on iphone")
        self.assertEqual(intent, "playback_audio_issue")
        self.assertGreaterEqual(conf, 0.70)

    def test_retrieval_and_leakage_prevention(self):
        query = "shuffle button not working"
        results = self.retriever.retrieve(query, exclude_tweet_id=119237, top_k=3)
        self.assertEqual(len(results), 3)
        # Verify no result matches excluded tweet_id
        for r in results:
            self.assertNotEqual(r['customer_tweet_id'], 119237)
            self.assertLessEqual(r['similarity_score'], 0.98)

    def test_escalation_security_hacked(self):
        intent, conf = "account_access_security", 0.90
        evidence = [{"similarity_score": 0.80}]
        decision, reason, _ = evaluate_escalation(intent, conf, "my account was hacked", evidence)
        self.assertEqual(decision, "ESCALATE TO HUMAN")
        self.assertIn("security", reason.lower())

    def test_escalation_billing_dispute(self):
        intent, conf = "billing_subscription_dispute", 0.85
        evidence = [{"similarity_score": 0.40}]  # Low retrieval evidence
        decision, reason, _ = evaluate_escalation(intent, conf, "refund me $15", evidence)
        self.assertEqual(decision, "ESCALATE TO HUMAN")

    def test_escalation_auto_handle(self):
        intent, conf = "playback_audio_issue", 0.90
        evidence = [{"similarity_score": 0.75}]
        decision, _, _ = evaluate_escalation(intent, conf, "shuffle pauses on repeat", evidence)
        self.assertEqual(decision, "AUTO-HANDLE")

    def test_edge_case_empty_message(self):
        intent, conf = classify_intent_rule_based("")
        self.assertEqual(intent, "general_feedback_inquiry")
        self.assertLess(conf, 0.50)

    def test_edge_case_out_of_scope(self):
        query = "order pizza"
        intent, conf = classify_intent_rule_based(query)
        evidence = self.retriever.retrieve(query, top_k=1)
        decision, _, _ = evaluate_escalation(intent, conf, query, evidence)
        self.assertEqual(decision, "ESCALATE TO HUMAN")

if __name__ == "__main__":
    unittest.main()
