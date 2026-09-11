"""
Unit Tests for Improved Proposed Support Agent v3.
Tests Intent Classification, Confidence, Retrieval Evidence Quality, Grounding, Escalation Policy,
High-Risk Overrides, Routine Auto-Handling, Ambiguous Query Handling, and Leakage Control.
"""

import unittest
import os
import json

from src.intent_taxonomy import classify_intent, classify_intent_rule_based
from src.retriever import HistoricalRetriever, CLEAN_CORPUS_PATH, GOLDEN_SET_V2_PATH
from src.escalation import decide_escalation, evaluate_escalation
from src.generator import generate_grounded_response, generate_support_reply

class TestProposedAgentV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = HistoricalRetriever(CLEAN_CORPUS_PATH)
        with open(GOLDEN_SET_V2_PATH, 'r', encoding='utf-8') as f:
            cls.golden_data = json.load(f)
        cls.golden_examples = cls.golden_data['examples']

    def test_1_intent_classification_and_confidence(self):
        # Clear technical query
        res = classify_intent("my shuffle button is stuck on playback")
        self.assertEqual(res["intent"], "playback_audio_issue")
        self.assertGreaterEqual(res["confidence"], 0.70)
        self.assertIn("Matched key terms", res["reason"])

    def test_2_security_takeover_override(self):
        # Query mentioning albums but clearly describing account hack
        res = classify_intent("someone hacked my account and deleted my playlists and albums!")
        self.assertEqual(res["intent"], "account_access_security")
        self.assertGreaterEqual(res["confidence"], 0.90)
        self.assertIn("takeover", res["reason"].lower())

    def test_3_retrieval_evidence_and_quality(self):
        ret_res = self.retriever.retrieve_with_quality("how to download offline music", top_k=3)
        self.assertIn("evidence", ret_res)
        self.assertIn("evidence_quality", ret_res)
        self.assertIn(ret_res["evidence_quality"], ["strong", "medium", "weak"])
        self.assertGreater(len(ret_res["evidence"]), 0)

    def test_4_no_golden_leakage_in_retrieval(self):
        golden_ids = set(str(ex['customer_tweet_id']) for ex in self.golden_examples)
        ret_res = self.retriever.retrieve_with_quality("cancel subscription refund money", top_k=3)
        for ev in ret_res["evidence"]:
            self.assertNotIn(str(ev["customer_tweet_id"]), golden_ids)
            self.assertLessEqual(ev["similarity_score"], 0.95)

    def test_5_response_grounding_structure(self):
        c_text = "how do I turn off shuffle on desktop"
        intent_res = classify_intent(c_text)
        ret_res = self.retriever.retrieve_with_quality(c_text, top_k=3)
        esc_res = decide_escalation(intent_res["intent"], intent_res["confidence"], ret_res["best_similarity"], c_text, ret_res["evidence"])
        gen_res = generate_grounded_response(c_text, intent_res["intent"], ret_res, esc_res)

        self.assertIn("reply", gen_res)
        self.assertIn("evidence_ids", gen_res)
        self.assertIn("grounding_reason", gen_res)
        self.assertGreater(len(gen_res["reply"]), 10)

    def test_6_escalation_high_risk_security(self):
        esc = decide_escalation("account_access_security", 0.95, 0.80, "someone hacked my account", [])
        self.assertEqual(esc["decision"], "ESCALATE TO HUMAN")
        self.assertEqual(esc["risk_level"], "HIGH")

    def test_7_escalation_high_risk_billing_dispute(self):
        esc = decide_escalation("billing_subscription_dispute", 0.85, 0.70, "I was charged twice on my credit card refund me", [])
        self.assertEqual(esc["decision"], "ESCALATE TO HUMAN")
        self.assertEqual(esc["risk_level"], "HIGH")

    def test_8_escalation_routine_auto_handle(self):
        # Routine playback issue with good evidence
        evidence = [{"similarity_score": 0.65}]
        esc = decide_escalation("playback_audio_issue", 0.85, 0.65, "shuffle button is pausing", evidence)
        self.assertEqual(esc["decision"], "AUTO-HANDLE")
        self.assertEqual(esc["risk_level"], "LOW")

    def test_9_escalation_ambiguous_short_message(self):
        # Short non-specific query with low score
        esc = decide_escalation("general_feedback_inquiry", 0.35, 0.20, "help", [])
        self.assertEqual(esc["decision"], "ESCALATE TO HUMAN")
        self.assertIn("ambiguous", esc["reason"].lower())

    def test_10_billing_cases_distinction(self):
        # Generic billing FAQ vs double charge dispute
        faq_esc = decide_escalation("billing_subscription_dispute", 0.80, 0.60, "how much is student discount", [{"similarity_score": 0.60}])
        self.assertEqual(faq_esc["decision"], "AUTO-HANDLE")

        dispute_esc = decide_escalation("billing_subscription_dispute", 0.80, 0.60, "refund double charge", [{"similarity_score": 0.60}])
        self.assertEqual(dispute_esc["decision"], "ESCALATE TO HUMAN")

    def test_11_playback_stopping_intent(self):
        c_text = "My Spotify songs keep stopping after a few seconds and I cannot listen to anything."
        res = classify_intent(c_text)
        self.assertEqual(res["intent"], "playback_audio_issue")
        self.assertGreaterEqual(res["confidence"], 0.70)

    def test_12_general_feedback_weak_evidence_reply(self):
        c_text = "I really love Spotify. It would be great if you added more customization options."
        intent_res = classify_intent(c_text)
        ret_res = self.retriever.retrieve_with_quality(c_text, top_k=3)
        esc_res = decide_escalation(intent_res["intent"], intent_res["confidence"], ret_res["best_similarity"], c_text, ret_res["evidence"])
        gen_res = generate_grounded_response(c_text, intent_res["intent"], ret_res, esc_res)

        self.assertEqual(intent_res["intent"], "general_feedback_inquiry")
        self.assertIn("feedback", gen_res["reply"].lower())
        self.assertNotIn("restarting your app", gen_res["reply"].lower())
        self.assertIn("No sufficiently grounded historical evidence", gen_res["grounding_reason"])

    def test_13_escalation_reason_ungrounded_evidence(self):
        esc = decide_escalation("general_feedback_inquiry", 0.85, 0.48, "I really love Spotify.", [{"similarity_score": 0.48}])
        self.assertEqual(esc["decision"], "AUTO-HANDLE")
        self.assertNotIn("and grounded historical evidence", esc["reason"])
        self.assertIn("no sufficiently grounded historical evidence", esc["reason"])

if __name__ == "__main__":
    unittest.main()
