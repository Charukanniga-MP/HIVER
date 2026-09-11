"""
Judge Evaluation Sampling Script.
Generates a reproducible stratified sample of 40 examples from data/evaluation_v3.json.
Ensures diverse representation across intent correctness, escalation decisions, retrieval quality, message length, and difficulty.
Saves output to data/judge_sample.json.
"""

import os
import json
import random

EVALUATION_V3_PATH = r'd:\Hiver\data\evaluation_v3.json'
JUDGE_SAMPLE_PATH = r'd:\Hiver\data\judge_sample.json'

def create_judge_sample(sample_size: int = 40, seed: int = 42) -> dict:
    """
    Build reproducible stratified sample for response quality evaluation.
    """
    random.seed(seed)

    with open(EVALUATION_V3_PATH, 'r', encoding='utf-8') as f:
        eval_items = json.load(f)

    # Bucketing examples into strata
    strata = {
        "intent_correct": [],
        "intent_incorrect": [],
        "escalated": [],
        "auto_handled": [],
        "strong_retrieval": [],
        "medium_retrieval": [],
        "weak_retrieval": [],
        "short_messages": [],
        "hard_difficulty": []
    }

    for item in eval_items:
        if item.get("intent_correct", True):
            strata["intent_correct"].append(item)
        else:
            strata["intent_incorrect"].append(item)

        if item.get("predicted_escalation") == "ESCALATE TO HUMAN":
            strata["escalated"].append(item)
        else:
            strata["auto_handled"].append(item)

        sim = item.get("retrieval_best_similarity", 0.0)
        if sim >= 0.70:
            strata["strong_retrieval"].append(item)
        elif sim >= 0.50:
            strata["medium_retrieval"].append(item)
        else:
            strata["weak_retrieval"].append(item)

        if len(item.get("customer_text", "").split()) <= 4:
            strata["short_messages"].append(item)

        if item.get("difficulty") == "Hard":
            strata["hard_difficulty"].append(item)

    selected_ids = set()
    sampled_items = []

    def sample_from_list(lst, count):
        available = [x for x in lst if x["id"] not in selected_ids]
        num_to_take = min(count, len(available))
        picked = random.sample(available, num_to_take)
        for p in picked:
            selected_ids.add(p["id"])
            sampled_items.append(p)

    # Sample from each stratum
    sample_from_list(strata["intent_incorrect"], 8)
    sample_from_list(strata["escalated"], 8)
    sample_from_list(strata["weak_retrieval"], 6)
    sample_from_list(strata["short_messages"], 4)
    sample_from_list(strata["hard_difficulty"], 4)
    sample_from_list(strata["strong_retrieval"], 5)
    sample_from_list(strata["medium_retrieval"], 5)

    # Fill remaining up to 40
    remaining = [x for x in eval_items if x["id"] not in selected_ids]
    if len(sampled_items) < sample_size and remaining:
        fill_count = sample_size - len(sampled_items)
        picked = random.sample(remaining, min(fill_count, len(remaining)))
        for p in picked:
            selected_ids.add(p["id"])
            sampled_items.append(p)

    # Sort sampled items by ID
    sampled_items.sort(key=lambda x: x["id"])

    payload = {
        "metadata": {
            "sample_size": len(sampled_items),
            "seed": seed,
            "source": EVALUATION_V3_PATH,
            "strata_summary": {
                "total_items": len(eval_items),
                "sampled_items": len(sampled_items)
            }
        },
        "examples": sampled_items
    }

    os.makedirs(os.path.dirname(JUDGE_SAMPLE_PATH), exist_ok=True)
    with open(JUDGE_SAMPLE_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Created judge sample dataset: {len(sampled_items)} items saved to {JUDGE_SAMPLE_PATH}")
    return payload

if __name__ == "__main__":
    create_judge_sample()
