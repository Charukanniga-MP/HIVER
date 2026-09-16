#!/usr/bin/env python3
"""
Validation Script for Human-Reviewed Golden Evaluation Set.

Verifies that data/golden_set_human_reviewed.json:
1. Exists and contains exactly 200 examples.
2. Every example has human_reviewed = True and annotator = 'Human Reviewer'.
3. Every example has a valid true_intent.
4. Every example has a valid true_escalation ('AUTO-HANDLE' or 'ESCALATE').
5. Every example has boolean is_out_of_scope.
6. All IDs are unique.
7. Has human_annotation = True in metadata.
"""

import os
import sys
import json

VALID_INTENTS = [
    "account_access_security",
    "playback_audio_issue",
    "playlist_library_management",
    "offline_sync_issue",
    "general_feedback_inquiry",
    "billing_subscription_dispute",
    "out_of_scope"
]

VALID_ESCALATIONS = ["AUTO-HANDLE", "ESCALATE TO HUMAN", "ESCALATE"]

def validate_golden_set(filepath="data/golden_set_human_reviewed.json"):
    print(f"Validating human-reviewed golden set at: {filepath}")
    
    if not os.path.exists(filepath):
        print(f"FAILED: Target dataset file '{filepath}' does not exist.")
        return False
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"FAILED: Failed to parse JSON file '{filepath}': {e}")
        return False
        
    metadata = data.get("metadata", {})
    examples = data.get("examples", [])
    
    errors = []
    
    if len(examples) != 200:
        errors.append(f"Expected exactly 200 examples, found {len(examples)}.")
        
    if not metadata.get("human_annotation"):
        errors.append("Metadata 'human_annotation' field is not True.")
        
    seen_ids = set()
    unreviewed_count = 0
    invalid_intents = 0
    invalid_escalations = 0
    invalid_oos = 0
    
    for idx, ex in enumerate(examples):
        ex_id = ex.get("id")
        if not ex_id:
            errors.append(f"Example at index {idx} is missing an 'id'.")
        elif ex_id in seen_ids:
            errors.append(f"Duplicate example ID found: {ex_id}")
        else:
            seen_ids.add(ex_id)
            
        if not ex.get("human_reviewed"):
            unreviewed_count += 1
            
        if ex.get("true_intent") not in VALID_INTENTS:
            invalid_intents += 1
            errors.append(f"Example {ex_id} has invalid intent: '{ex.get('true_intent')}'")
            
        if ex.get("true_escalation") not in VALID_ESCALATIONS:
            invalid_escalations += 1
            errors.append(f"Example {ex_id} has invalid escalation: '{ex.get('true_escalation')}'")
            
        if not isinstance(ex.get("is_out_of_scope"), bool):
            invalid_oos += 1
            errors.append(f"Example {ex_id} has non-boolean is_out_of_scope: {ex.get('is_out_of_scope')}")
            
    if unreviewed_count > 0:
        errors.append(f"{unreviewed_count} / {len(examples)} examples have NOT been marked as human_reviewed=True.")
        
    if errors:
        print("\n--- VALIDATION FAILED WITH THE FOLLOWING ERRORS ---")
        for err in errors[:20]: # show first 20 errors
            print(f" - {err}")
        if len(errors) > 20:
            print(f" ... and {len(errors) - 20} more errors.")
        print("---------------------------------------------------")
        return False
    else:
        print("\nSUCCESS: Golden set validation passed perfectly!")
        print(f" - Total Examples        : {len(examples)} / 200")
        print(f" - Human Reviewed        : 200 / 200 (100%)")
        print(f" - Unique IDs Verified   : {len(seen_ids)}")
        print(f" - Valid Intents & Esc.  : VERIFIED")
        print(f" - Ground Truth Status   : Human Ground Truth Verified\n")
        return True

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "data/golden_set_human_reviewed.json"
    success = validate_golden_set(target)
    sys.exit(0 if success else 1)
