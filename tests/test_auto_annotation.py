"""
Unit Tests for AI-Assisted Auto-Annotation Script & Data Validation.
"""

import unittest
import os
import json
from scripts.auto_annotate_golden_set import (
    determine_intent,
    check_out_of_scope,
    determine_escalation_and_risk,
    VALID_INTENTS,
    VALID_ESCALATIONS,
    OUTPUT_PATH,
    SUMMARY_PATH
)

class TestAutoAnnotation(unittest.TestCase):
    def test_intent_rules(self):
        self.assertEqual(determine_intent("charged twice on credit card", ""), "billing_subscription_dispute")
        self.assertEqual(determine_intent("password reset email hacked", ""), "account_access_security")
        self.assertEqual(determine_intent("offline tracks greyed out airplane mode", ""), "offline_sync_issue")
        self.assertEqual(determine_intent("shuffle button stuck on repeat", ""), "playback_audio_issue")
        self.assertEqual(determine_intent("saved playlist deleted", ""), "playlist_library_management")

    def test_out_of_scope(self):
        self.assertTrue(check_out_of_scope("Can you order me a pizza?"))
        self.assertFalse(check_out_of_scope("My songs keep pausing on Android."))

    def test_escalation_rules(self):
        esc_hack, diff_hack, _, _ = determine_escalation_and_risk("account_access_security", "hacked account", "", False)
        self.assertEqual(esc_hack, "ESCALATE TO HUMAN")
        self.assertEqual(diff_hack, "Hard")

        esc_tech, diff_tech, _, _ = determine_escalation_and_risk("playback_audio_issue", "shuffle button stuck on ios 11", "", False)
        self.assertEqual(esc_tech, "AUTO-HANDLE")

        esc_short, diff_short, _, _ = determine_escalation_and_risk("general_feedback_inquiry", "help pls", "", False)
        self.assertEqual(esc_short, "ESCALATE TO HUMAN")

    def test_output_file_validation(self):
        if os.path.exists(OUTPUT_PATH):
            with open(OUTPUT_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)

            meta = data.get("metadata", {})
            examples = data.get("examples", [])

            self.assertEqual(meta.get("total_examples"), 200)
            self.assertFalse(meta.get("human_annotation"))
            self.assertEqual(len(examples), 200)

            seen_ids = set()
            for ex in examples:
                self.assertIn(ex["true_intent"], VALID_INTENTS)
                self.assertIn(ex["true_escalation"], VALID_ESCALATIONS)
                self.assertNotIn(ex["id"], seen_ids)
                seen_ids.add(ex["id"])
                self.assertEqual(ex["annotator"], "AI-assisted annotation")

if __name__ == "__main__":
    unittest.main()
