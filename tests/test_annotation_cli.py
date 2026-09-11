"""
Unit Tests for Annotation CLI & Quality Control Validation Rules.
"""

import unittest
from scripts.annotate_golden_set import validate_golden_dataset

class TestAnnotationCLI(unittest.TestCase):
    def test_validation_incomplete_todo(self):
        draft = [
            {
                "id": "GOLDEN-001",
                "customer_tweet_id": "119239",
                "customer_text": "sample text",
                "true_intent": "TODO",
                "true_escalation": "TODO",
                "difficulty": "TODO"
            }
        ]
        is_valid, summary, errors = validate_golden_dataset(draft)
        self.assertFalse(is_valid)
        self.assertEqual(summary["todo_count"], 1)
        self.assertEqual(summary["completed_count"], 0)

    def test_validation_complete_valid_item(self):
        valid_set = [
            {
                "id": "GOLDEN-001",
                "customer_tweet_id": "119239",
                "customer_text": "sample text",
                "true_intent": "playback_audio_issue",
                "true_escalation": "AUTO-HANDLE",
                "difficulty": "Easy",
                "is_out_of_scope": False,
                "annotation_notes": ""
            }
        ]
        is_valid, summary, errors = validate_golden_dataset(valid_set)
        self.assertTrue(is_valid)
        self.assertEqual(summary["completed_count"], 1)
        self.assertEqual(summary["intent_counts"]["playback_audio_issue"], 1)
        self.assertEqual(summary["escalation_counts"]["AUTO-HANDLE"], 1)

    def test_validation_invalid_intent_value(self):
        invalid_set = [
            {
                "id": "GOLDEN-001",
                "customer_tweet_id": "119239",
                "customer_text": "sample text",
                "true_intent": "invalid_intent_category",
                "true_escalation": "AUTO-HANDLE",
                "difficulty": "Easy"
            }
        ]
        is_valid, summary, errors = validate_golden_dataset(invalid_set)
        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid intent" in err for err in errors))

if __name__ == "__main__":
    unittest.main()
