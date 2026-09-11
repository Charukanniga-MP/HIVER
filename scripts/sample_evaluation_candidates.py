"""
Candidate Sampler for SpotifyCares Golden Evaluation Set.
Samples 200 real SpotifyCares customer conversations using a prevalence-guided,
stratified diversity strategy with ZERO automated label assignment (all set to 'TODO').
"""

import os
import json
import random

CONVERSATIONS_PATH = r'd:\Hiver\data\processed\spotify_conversations.json'
DRAFT_OUTPUT_PATH = r'd:\Hiver\data\golden_annotation_draft.json'

KEYWORDS_MAP = {
    'playback_audio_issue': ['shuffle', 'repeat', 'pause', 'pausing', 'stop', 'playing', 'sound', 'volume', 'stutter', 'lag', 'crash', 'freeze', 'freezing', 'skip', 'skipping', 'song stops'],
    'offline_sync_issue': ['offline', 'download', 'downloading', 'downloads', 'sync', 'storage', 'sd card', 'downloaded'],
    'billing_subscription_dispute': ['billing', 'charge', 'charged', 'refund', 'payment', 'subscription', 'premium', 'student', 'discount', 'receipt', 'card', 'money', 'overcharged'],
    'account_access_security': ['account', 'login', 'log in', 'password', 'hacked', 'hacker', 'stolen', 'breach', 'security', 'email', 'reset password'],
    'playlist_library_management': ['playlist', 'playlists', 'library', 'saved', 'liked songs', 'daily mix', 'wrapped', 'queue', 'local files'],
    'general_feedback_inquiry': ['feature', 'request', 'update', 'lyrics', 'ui', 'interface', 'podcast', 'suggestion', 'feedback', 'love spotify', 'hate update']
}

TARGET_ALLOCATION = {
    'billing_subscription_dispute': 35,
    'account_access_security': 30,
    'playback_audio_issue': 30,
    'general_feedback_inquiry': 25,
    'playlist_library_management': 25,
    'offline_sync_issue': 25,
    'difficult_ambiguous_edge': 30
}

def sample_candidates():
    print("=" * 70)
    print("SAMPLING 200 GOLDEN EVALUATION SET CANDIDATES")
    print("=" * 70)

    with open(CONVERSATIONS_PATH, 'r', encoding='utf-8') as f:
        conversations = json.load(f)

    print(f"Total available SpotifyCares conversations: {len(conversations):,}")
    random.seed(42)  # Deterministic seed for reproducible sampling

    # Bucket conversations into keyword categories & unmatched pool
    buckets = {cat: [] for cat in KEYWORDS_MAP}
    unmatched_pool = []

    for item in conversations:
        text_lower = item['clean_customer_text'].lower()
        matched = False
        for cat, kws in KEYWORDS_MAP.items():
            if any(kw in text_lower for kw in kws):
                buckets[cat].append(item)
                matched = True
                break
        if not matched:
            unmatched_pool.append(item)

    print("\nDataset Candidate Buckets (Taxonomy-Keyword Coverage):")
    for cat, items in buckets.items():
        print(f"  - {cat}: {len(items):,} items (Target: {TARGET_ALLOCATION[cat]})")
    print(f"  - Unmatched / Low-Keyword Pool: {len(unmatched_pool):,} items (Target: {TARGET_ALLOCATION['difficult_ambiguous_edge']})")

    sampled_raw_items = []
    seen_ids = set()

    # 1. Sample from each specific keyword category bucket
    for cat, target_count in TARGET_ALLOCATION.items():
        if cat == 'difficult_ambiguous_edge':
            continue
        available = buckets[cat]
        pool = [x for x in available if x['id'] not in seen_ids]
        sampled = random.sample(pool, min(target_count, len(pool)))
        for item in sampled:
            seen_ids.add(item['id'])
            sampled_raw_items.append((cat, item))

    # 2. Sample 30 items from unmatched / low-keyword / short pool for edge cases
    unmatched_clean = [x for x in unmatched_pool if x['id'] not in seen_ids]
    sampled_edge = random.sample(unmatched_clean, TARGET_ALLOCATION['difficult_ambiguous_edge'])
    for item in sampled_edge:
        seen_ids.add(item['id'])
        sampled_raw_items.append(('difficult_ambiguous_edge', item))

    # Shuffle to interleave categories naturally
    random.shuffle(sampled_raw_items)

    draft_candidates = []
    for idx, (strata_cat, item) in enumerate(sampled_raw_items, start=1):
        draft_candidates.append({
            "id": f"GOLDEN-{idx:03d}",
            "source_conversation_id": item['id'],
            "customer_tweet_id": str(item['customer_tweet_id']),
            "customer_text": item['clean_customer_text'],
            "raw_brand_reply": item['clean_brand_text'],
            "true_intent": "TODO",
            "true_escalation": "TODO",
            "is_out_of_scope": False,
            "difficulty": "TODO",
            "escalation_reason": "TODO",
            "annotation_notes": f"Sampled via strata: {strata_cat}",
            "annotator": "human"
        })

    os.makedirs(os.path.dirname(DRAFT_OUTPUT_PATH), exist_ok=True)
    with open(DRAFT_OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(draft_candidates, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"SUCCESS: Exported {len(draft_candidates)} unannotated candidates to:")
    print(f"  -> {DRAFT_OUTPUT_PATH}")
    print("All true_intent, true_escalation, and difficulty fields are set to 'TODO'.")
    print("=" * 70)
    return draft_candidates

if __name__ == "__main__":
    sample_candidates()
