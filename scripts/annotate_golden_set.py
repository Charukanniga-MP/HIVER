"""
Interactive Human Annotation CLI & Quality Control Validator.
Allows the human reviewer to manually hand-label candidates step-by-step with progress saving,
resume capability, strict field validation rules, and summary reporting.
"""

import os
import sys
import json

DRAFT_PATH = r'd:\Hiver\data\golden_annotation_draft.json'
FINAL_OUTPUT_PATH = r'd:\Hiver\data\golden_set_v2.json'

VALID_INTENTS = {
    "1": "playback_audio_issue",
    "2": "offline_sync_issue",
    "3": "billing_subscription_dispute",
    "4": "account_access_security",
    "5": "playlist_library_management",
    "6": "general_feedback_inquiry"
}

VALID_ESCALATIONS = {
    "A": "AUTO-HANDLE",
    "E": "ESCALATE TO HUMAN"
}

VALID_DIFFICULTIES = {
    "1": "Easy",
    "2": "Medium",
    "3": "Hard"
}

def load_annotation_state():
    """Load from draft or final if progress exists."""
    target_path = FINAL_OUTPUT_PATH if os.path.exists(FINAL_OUTPUT_PATH) else DRAFT_PATH
    if not os.path.exists(target_path):
        print(f"ERROR: Candidate file not found at {target_path}. Run sampler first!")
        sys.exit(1)

    with open(target_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data, target_path

def save_annotation_state(data, path=FINAL_OUTPUT_PATH):
    """Save current state to file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def validate_golden_dataset(data):
    """
    Validate quality control rules across dataset.
    Returns (is_valid, summary_stats, errors).
    """
    errors = []
    seen_ids = set()
    intent_counts = {v: 0 for v in VALID_INTENTS.values()}
    esc_counts = {"AUTO-HANDLE": 0, "ESCALATE TO HUMAN": 0}
    diff_counts = {"Easy": 0, "Medium": 0, "Hard": 0}
    out_of_scope_count = 0
    needs_review_count = 0
    completed_count = 0

    for idx, item in enumerate(data):
        item_id = item.get("id")
        if not item_id:
            errors.append(f"Item #{idx} missing 'id'")
        elif item_id in seen_ids:
            errors.append(f"Duplicate ID found: {item_id}")
        else:
            seen_ids.add(item_id)

        intent = item.get("true_intent")
        esc = item.get("true_escalation")
        diff = item.get("difficulty")
        notes = item.get("annotation_notes", "")

        if "NEEDS_REVIEW" in str(notes):
            needs_review_count += 1

        if item.get("is_out_of_scope"):
            out_of_scope_count += 1

        # Check if fully labelled
        if intent != "TODO" and esc != "TODO" and diff != "TODO":
            completed_count += 1
            if intent in intent_counts:
                intent_counts[intent] += 1
            else:
                errors.append(f"{item_id}: Invalid intent '{intent}'")

            if esc in esc_counts:
                esc_counts[esc] += 1
            else:
                errors.append(f"{item_id}: Invalid escalation '{esc}'")

            if diff in diff_counts:
                diff_counts[diff] += 1
            else:
                errors.append(f"{item_id}: Invalid difficulty '{diff}'")

    summary = {
        "total_items": len(data),
        "completed_count": completed_count,
        "todo_count": len(data) - completed_count,
        "intent_counts": intent_counts,
        "escalation_counts": esc_counts,
        "difficulty_counts": diff_counts,
        "out_of_scope_count": out_of_scope_count,
        "needs_review_count": needs_review_count
    }

    is_valid = (len(errors) == 0 and completed_count == len(data))
    return is_valid, summary, errors

def print_summary_report(summary, errors):
    """Print human-readable quality summary report."""
    print("=" * 60)
    print("GOLDEN EVALUATION SET QUALITY CONTROL SUMMARY")
    print("=" * 60)
    print(f"Total Candidates: {summary['total_items']}")
    print(f"Hand-Labelled   : {summary['completed_count']} / {summary['total_items']}")
    print(f"Remaining TODO  : {summary['todo_count']}")
    print("-" * 60)
    print("Intent Distribution:")
    for k, v in summary['intent_counts'].items():
        print(f"  - {k}: {v}")
    print("-" * 60)
    print("Escalation Decisions:")
    for k, v in summary['escalation_counts'].items():
        print(f"  - {k}: {v}")
    print("-" * 60)
    print("Difficulty Breakdown:")
    for k, v in summary['difficulty_counts'].items():
        print(f"  - {k}: {v}")
    print("-" * 60)
    print(f"Out-of-Scope Items  : {summary['out_of_scope_count']}")
    print(f"NEEDS_REVIEW Flagged: {summary['needs_review_count']}")
    print("=" * 60)

    if errors:
        print("\n[VALIDATION WARNINGS / ERRORS]:")
        for err in errors[:10]:
            print(f"  - {err}")
        print("=" * 60)

def run_interactive_annotation():
    """Main interactive annotation CLI loop."""
    data, file_path = load_annotation_state()

    print("=" * 70)
    print("INTERACTIVE HUMAN ANNOTATION CLI — SpotifyCares Golden Set")
    print("=" * 70)
    print(f"Loaded candidates from: {file_path}")
    print("Instructions: Enter integer [1-6] for intent, [A/E] for escalation, [1-3] for difficulty.")
    print("Type 'q' anytime to save and quit, or 's' to skip to next item.\n")

    for idx, item in enumerate(data):
        # Skip items already labelled
        if item.get("true_intent") != "TODO" and item.get("true_escalation") != "TODO" and item.get("difficulty") != "TODO":
            continue

        print(f"\n[{idx+1} / {len(data)}] ITEM {item['id']} (Source: {item['source_conversation_id']})")
        print("-" * 60)
        print(f"CUSTOMER TEXT: \"{item['customer_text']}\"")
        print(f"BRAND REPLY  : \"{item['raw_brand_reply']}\"")
        print("-" * 60)

        # 1. Intent Selection
        print("Select True Intent:")
        for k, v in VALID_INTENTS.items():
            print(f"  [{k}] {v}")
        
        intent_choice = input("Choice (1-6, q=quit, s=skip): ").strip()
        if intent_choice.lower() == 'q':
            save_annotation_state(data)
            print("Progress saved. Exiting CLI.")
            return
        if intent_choice.lower() == 's':
            continue

        while intent_choice not in VALID_INTENTS:
            intent_choice = input("Invalid choice. Select (1-6): ").strip()
        selected_intent = VALID_INTENTS[intent_choice]

        # 2. Escalation Selection
        print("\nSelect True Escalation:")
        print("  [A] AUTO-HANDLE")
        print("  [E] ESCALATE TO HUMAN")
        esc_choice = input("Choice (A/E): ").strip().upper()
        while esc_choice not in VALID_ESCALATIONS:
            esc_choice = input("Invalid choice. Select A or E: ").strip().upper()
        selected_esc = VALID_ESCALATIONS[esc_choice]

        # 3. Out-of-Scope Flag
        oos_choice = input("\nIs Out-of-Scope / Non-Support? (y/N): ").strip().lower()
        is_oos = (oos_choice == 'y')

        # 4. Difficulty Selection
        print("\nSelect Difficulty:")
        print("  [1] Easy")
        print("  [2] Medium")
        print("  [3] Hard")
        diff_choice = input("Choice (1-3): ").strip()
        while diff_choice not in VALID_DIFFICULTIES:
            diff_choice = input("Invalid choice. Select 1, 2, or 3: ").strip()
        selected_diff = VALID_DIFFICULTIES[diff_choice]

        # 5. Escalation Reason & Notes
        reason = input("\nEscalation Reason (press Enter for default): ").strip()
        notes = input("Annotation Notes / Flag NEEDS_REVIEW (press Enter to skip): ").strip()

        # Update item
        item["true_intent"] = selected_intent
        item["true_escalation"] = selected_esc
        item["is_out_of_scope"] = is_oos
        item["difficulty"] = selected_diff
        item["escalation_reason"] = reason if reason else ("High-risk or low evidence threshold" if selected_esc == "ESCALATE TO HUMAN" else "Standard technical self-serve resolution")
        item["annotation_notes"] = notes if notes else item.get("annotation_notes", "")
        item["annotator"] = "human"

        # Save incremental progress
        save_annotation_state(data, FINAL_OUTPUT_PATH)
        print(f"SAVED item {item['id']}.")

    # End of loop validation report
    is_valid, summary, errors = validate_golden_dataset(data)
    print_summary_report(summary, errors)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        data, path = load_annotation_state()
        _, summary, errors = validate_golden_dataset(data)
        print_summary_report(summary, errors)
    else:
        run_interactive_annotation()
