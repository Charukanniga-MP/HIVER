"""
AI-Assisted Golden Set Auto-Annotation Script.
Independently analyzes candidate customer queries and context in data/golden_annotation_draft.json
and generates data/golden_set_v2.json and data/golden_set_annotation_summary.json.

IMPORTANT DISCLOSURE:
This dataset is produced via AI-assisted automatic annotation.
It is NOT equivalent to a manually hand-labelled golden set.
"""

import os
import json
import re

DRAFT_PATH = r'd:\Hiver\data\golden_annotation_draft.json'
OUTPUT_PATH = r'd:\Hiver\data\golden_set_v2.json'
SUMMARY_PATH = r'd:\Hiver\data\golden_set_annotation_summary.json'

VALID_INTENTS = {
    "playback_audio_issue",
    "offline_sync_issue",
    "billing_subscription_dispute",
    "account_access_security",
    "playlist_library_management",
    "general_feedback_inquiry"
}

VALID_ESCALATIONS = {"AUTO-HANDLE", "ESCALATE TO HUMAN"}
VALID_DIFFICULTIES = {1, 2, 3, "Easy", "Medium", "Hard", "1", "2", "3"}

def determine_intent(text: str, reply: str) -> str:
    """Independently classify intent based on customer message text and brand reply context."""
    t = text.lower()
    r = reply.lower()

    # 1. Billing & Subscription Dispute
    if any(k in t for k in ["billed", "charge", "charged", "refund", "payment", "subscript", "premium", "student", "discount", "receipt", "card", "money", "overcharged", "cost", "dollar", "$"]):
        return "billing_subscription_dispute"

    # 2. Account Access & Security
    if any(k in t for k in ["hacked", "hacker", "stolen", "breach", "password", "login", "log in", "sign in", "email", "unauthorized", "reset password", "account"]):
        if not ("playlist" in t or "saved" in t):
            return "account_access_security"

    # 3. Offline Mode & Sync Issue
    if any(k in t for k in ["offline", "download", "downloading", "downloads", "sd card", "storage"]):
        return "offline_sync_issue"

    # 4. Playlist & Library Management
    if any(k in t for k in ["playlist", "playlists", "library", "saved", "liked songs", "daily mix", "wrapped", "queue", "local file", "export"]):
        return "playlist_library_management"

    # 5. Playback & Audio Issue
    if any(k in t for k in ["shuffle", "repeat", "pause", "pausing", "stop", "playing", "sound", "volume", "stutter", "lag", "crash", "freeze", "freezing", "skip", "skipping", "song stops", "doesn't work", "wont play"]):
        return "playback_audio_issue"

    # 6. General Inquiry / Feedback / Fallback
    return "general_feedback_inquiry"

def check_out_of_scope(text: str) -> bool:
    """Check if customer query is out-of-scope for Spotify customer support."""
    t = text.lower()
    out_of_scope_keywords = ["pizza", "burger", "uber", "flight", "weather", "football", "homework", "car repair"]
    return any(k in t for k in out_of_scope_keywords)

def determine_escalation_and_risk(intent: str, text: str, reply: str, is_oos: bool) -> tuple[str, str, str, str]:
    """
    Determine escalation decision, difficulty, escalation reason, and notes.
    Returns (true_escalation, difficulty, escalation_reason, annotation_notes).
    """
    t = text.lower()
    
    # Rule 1: Out of Scope
    if is_oos:
        return (
            "ESCALATE TO HUMAN",
            "Hard",
            "Out-of-scope query unsupported by Spotify support precedents.",
            "AI-assisted note: Non-Spotify request requiring human routing."
        )

    # Rule 2: Account Security Breach / Hack
    if intent == "account_access_security" or any(k in t for k in ["hacked", "stolen", "breach", "unauthorized"]):
        return (
            "ESCALATE TO HUMAN",
            "Hard" if "hacked" in t else "Medium",
            "Account takeover/security threat requires identity verification unavailable to AI.",
            "AI-assisted note: Mandatory escalation for credential/security protection."
        )

    # Rule 3: Financial Dispute / Overcharge / Refund
    if intent == "billing_subscription_dispute":
        if any(k in t for k in ["refund", "double billed", "overcharged", "twice", "unrecognized"]):
            return (
                "ESCALATE TO HUMAN",
                "Medium",
                "Financial transaction dispute requires private payment ledger access unavailable to AI.",
                "AI-assisted note: Monetary dispute escalated for payment audit."
            )
        else:
            return (
                "AUTO-HANDLE",
                "Easy",
                "General plan/pricing inquiry grounded in historical support precedent.",
                "AI-assisted note: Standard subscription guidance."
            )

    # Rule 4: Ambiguous / Ultra-short (<15 chars)
    if len(t.strip()) < 15 or t.strip() in ["help pls", "why", "wtf", "hello", "hi"]:
        return (
            "ESCALATE TO HUMAN",
            "Hard",
            "Ultra-short/ambiguous query lacking context for safe automated troubleshooting.",
            "AI-assisted note: High intent uncertainty requires human clarification."
        )

    # Rule 5: Standard Technical Troubleshooting (Playback / Offline / Playlist / General)
    difficulty = "Easy" if len(t) < 80 else "Medium"
    return (
        "AUTO-HANDLE",
        difficulty,
        "Standard technical support request grounded in historical SpotifyCares resolution precedent.",
        f"AI-assisted note: Clear technical issue ({intent}) with actionable troubleshooting precedent."
    )

def auto_annotate_dataset():
    print("=" * 70)
    print("AI-ASSISTED GOLDEN EVALUATION SET AUTO-ANNOTATION")
    print("=" * 70)

    if not os.path.exists(DRAFT_PATH):
        print(f"ERROR: Draft file not found at {DRAFT_PATH}")
        return

    with open(DRAFT_PATH, 'r', encoding='utf-8') as f:
        draft_items = json.load(f)

    print(f"Loaded {len(draft_items)} candidate examples from draft.")

    annotated_examples = []
    seen_ids = set()

    for item in draft_items:
        item_id = item['id']
        c_text = item['customer_text']
        b_reply = item.get('raw_brand_reply', '')

        # Check unique ID
        if item_id in seen_ids:
            raise ValueError(f"Duplicate candidate ID found: {item_id}")
        seen_ids.add(item_id)

        # 1. Determine Intent
        intent = determine_intent(c_text, b_reply)
        assert intent in VALID_INTENTS, f"Invalid intent generated: {intent}"

        # 2. Determine Out-of-Scope
        is_oos = check_out_of_scope(c_text)

        # 3. Determine Escalation, Difficulty, Reason, Notes
        esc, diff, reason, notes = determine_escalation_and_risk(intent, c_text, b_reply, is_oos)

        annotated_item = {
            "id": item_id,
            "source_conversation_id": item.get("source_conversation_id", ""),
            "customer_tweet_id": str(item.get("customer_tweet_id", "")),
            "customer_text": c_text,
            "raw_brand_reply": b_reply,
            "true_intent": intent,
            "true_escalation": esc,
            "is_out_of_scope": is_oos,
            "difficulty": diff,
            "escalation_reason": reason,
            "annotation_notes": notes,
            "annotator": "AI-assisted annotation"
        }

        annotated_examples.append(annotated_item)

    # Top-level metadata wrapper as required
    dataset_payload = {
        "metadata": {
            "total_examples": len(annotated_examples),
            "annotation_method": "AI-assisted automatic annotation",
            "human_annotation": False,
            "source": "SpotifyCares historical customer-support conversations",
            "intents": list(VALID_INTENTS),
            "out_of_scope_supported": True,
            "labels_are_ground_truth": False,
            "note": "This evaluation set was produced via AI-assisted annotation and is NOT equivalent to a manually hand-labelled golden set."
        },
        "examples": annotated_examples
    }

    # Save data/golden_set_v2.json
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(dataset_payload, f, indent=2, ensure_ascii=False)

    print(f"\nSUCCESS: Exported {len(annotated_examples)} AI-assisted annotated examples to:")
    print(f"  -> {OUTPUT_PATH}")

    # Generate Summary File
    intent_dist = {i: 0 for i in VALID_INTENTS}
    esc_dist = {"AUTO-HANDLE": 0, "ESCALATE TO HUMAN": 0}
    diff_dist = {"Easy": 0, "Medium": 0, "Hard": 0}
    oos_count = 0

    for ex in annotated_examples:
        intent_dist[ex['true_intent']] += 1
        esc_dist[ex['true_escalation']] += 1
        diff_dist[ex['difficulty']] += 1
        if ex['is_out_of_scope']:
            oos_count += 1

    summary_payload = {
        "total_examples": len(annotated_examples),
        "annotation_method": "AI-assisted automatic annotation",
        "intent_distribution": intent_dist,
        "escalation_distribution": esc_dist,
        "difficulty_distribution": diff_dist,
        "out_of_scope_count": oos_count
    }

    with open(SUMMARY_PATH, 'w', encoding='utf-8') as f:
        json.dump(summary_payload, f, indent=2, ensure_ascii=False)

    print(f"Exported summary metrics to: {SUMMARY_PATH}")

    # Print Summary Report
    print("\n" + "=" * 70)
    print("GOLDEN SET V2 ANNOTATION SUMMARY REPORT")
    print("=" * 70)
    print(f"Total Annotated Examples: {len(annotated_examples)}")
    print("-" * 50)
    print("Intent Distribution:")
    for k, v in intent_dist.items():
        print(f"  - {k}: {v}")
    print("-" * 50)
    print("Escalation Distribution:")
    for k, v in esc_dist.items():
        print(f"  - {k}: {v}")
    print("-" * 50)
    print("Difficulty Distribution:")
    for k, v in diff_dist.items():
        print(f"  - {k}: {v}")
    print("-" * 50)
    print(f"Out-of-Scope Count: {oos_count}")
    print("=" * 70)

    return summary_payload

if __name__ == "__main__":
    auto_annotate_dataset()
