"""
Human Rating Interactive CLI for Response Quality Benchmark.
Allows human annotators to review generated support replies and assign genuine 1-5 ratings across 4 rubric dimensions.
Supports save/resume, skip, status, and custom notes.
"""

import os
import json
import sys

JUDGE_SAMPLE_PATH = r'd:\Hiver\data\judge_sample.json'
HUMAN_TEMPLATE_PATH = r'd:\Hiver\data\human_rating_template.json'

def init_human_rating_template(sample_count: int = 30) -> dict:
    """
    Initialize human rating template with exactly sample_count items and null ratings.
    """
    if not os.path.exists(JUDGE_SAMPLE_PATH):
        from scripts.sample_judge_set import create_judge_sample
        create_judge_sample()

    with open(JUDGE_SAMPLE_PATH, 'r', encoding='utf-8') as f:
        sample_payload = json.load(f)

    sampled_examples = sample_payload.get("examples", [])[:sample_count]

    template_examples = []
    for ex in sampled_examples:
        template_examples.append({
            "id": ex["id"],
            "customer_message": ex["customer_text"],
            "generated_reply": ex["generated_reply"],
            "retrieved_evidence": ex.get("evidence_ids", []),
            "human_relevance": None,
            "human_groundedness": None,
            "human_helpfulness": None,
            "human_correctness": None,
            "human_overall_score": None,
            "human_notes": None
        })

    payload = {
        "metadata": {
            "total_examples": len(template_examples),
            "completed_count": 0,
            "has_genuine_human_ratings": False,
            "instructions": "Use 'python -m scripts.rate_judge_sample' to enter genuine human ratings (1-5 scale) for each response."
        },
        "examples": template_examples
    }

    os.makedirs(os.path.dirname(HUMAN_TEMPLATE_PATH), exist_ok=True)
    with open(HUMAN_TEMPLATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Initialized unfilled human rating template with {len(template_examples)} items at {HUMAN_TEMPLATE_PATH}")
    return payload

def run_rating_cli():
    if not os.path.exists(HUMAN_TEMPLATE_PATH):
        init_human_rating_template()

    with open(HUMAN_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    examples = data["examples"]
    total = len(examples)

    print("=" * 70)
    print("SPOTIFYCARES SUPPORT AGENT — HUMAN RATING CLI")
    print("=" * 70)
    print(f"Loaded {total} examples for human evaluation.")
    print("Instructions: Rate each dimension from 1 to 5. Type 's' to skip, 'q' to quit & save.\n")

    completed = sum(1 for ex in examples if ex["human_overall_score"] is not None)
    print(f"Current Progress: {completed} / {total} completed.")

    # Non-interactive / headless environment check
    if not sys.stdin.isatty():
        print("[NOTICE]: Headless execution detected. CLI ready for interactive terminal use.")
        print(f"Template status: {completed}/{total} items rated.")
        return

    for idx, ex in enumerate(examples):
        if ex["human_overall_score"] is not None:
            continue

        print(f"\n--- Item [{idx + 1}/{total}] (ID: {ex['id']}) ---")
        print(f"Customer Message: \"{ex['customer_message']}\"")
        print(f"Generated Reply : \"{ex['generated_reply']}\"")
        print(f"Evidence IDs    : {ex['retrieved_evidence']}")

        try:
            rel_inp = input("Relevance (1-5) [s/q]: ").strip().lower()
            if rel_inp == 'q':
                break
            if rel_inp == 's':
                continue

            rel = int(rel_inp)
            grd = int(input("Groundedness (1-5): ").strip())
            hlp = int(input("Helpfulness (1-5): ").strip())
            cor = int(input("Correctness (1-5): ").strip())
            notes = input("Notes (optional): ").strip()

            overall = round(0.30 * rel + 0.30 * grd + 0.20 * hlp + 0.20 * cor, 2)

            ex["human_relevance"] = rel
            ex["human_groundedness"] = grd
            ex["human_helpfulness"] = hlp
            ex["human_correctness"] = cor
            ex["human_overall_score"] = overall
            ex["human_notes"] = notes or "Human rated via CLI."

            # Save progress immediately
            completed_now = sum(1 for item in examples if item["human_overall_score"] is not None)
            data["metadata"]["completed_count"] = completed_now
            data["metadata"]["has_genuine_human_ratings"] = (completed_now > 0)

            with open(HUMAN_TEMPLATE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"Saved rating for {ex['id']} (Overall: {overall}).")

        except (ValueError, KeyboardInterrupt):
            print("\nRating session paused. Progress saved.")
            break

    print(f"\nRating session finished. Progress: {data['metadata']['completed_count']}/{total} completed.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        init_human_rating_template()
    else:
        run_rating_cli()
