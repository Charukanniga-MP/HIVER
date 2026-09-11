"""
Human Ratings Import Script for SpotifyCares AI Support System.
Safely imports genuine human ratings from a structured JSON input file into data/human_ratings.json.
Validates score bounds (1-5), ID existence, duplicate prevention, and accidental overwrite protection.
"""

import os
import json
import sys
import argparse

HUMAN_TEMPLATE_PATH = r'd:\Hiver\data\human_rating_template.json'
HUMAN_RATINGS_PATH = r'd:\Hiver\data\human_ratings.json'
JUDGE_SAMPLE_PATH = r'd:\Hiver\data\judge_sample.json'

def validate_and_import_ratings(input_path: str, overwrite: bool = False) -> dict:
    """
    Import human ratings from input_path, validate schema, and update data/human_ratings.json.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input ratings file not found: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        try:
            raw_input = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in {input_path}: {e}")

    if not isinstance(raw_input, list):
        raise ValueError("Input file must contain a JSON array of rating objects.")

    # Load valid IDs from template or judge sample
    if os.path.exists(HUMAN_TEMPLATE_PATH):
        with open(HUMAN_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
            template_payload = json.load(f)
        valid_examples = {ex["id"]: ex for ex in template_payload.get("examples", [])}
    else:
        with open(JUDGE_SAMPLE_PATH, 'r', encoding='utf-8') as f:
            sample_payload = json.load(f)
        valid_examples = {ex["id"]: ex for ex in sample_payload.get("examples", [])}

    # Load existing human_ratings.json if present
    existing_ratings = {}
    if os.path.exists(HUMAN_RATINGS_PATH):
        with open(HUMAN_RATINGS_PATH, 'r', encoding='utf-8') as f:
            existing_payload = json.load(f)
            for ex in existing_payload.get("examples", []):
                if ex.get("human_overall_score") is not None:
                    existing_ratings[ex["id"]] = ex

    seen_input_ids = set()
    validated_ratings = {}

    for idx, item in enumerate(raw_input):
        if not isinstance(item, dict):
            raise ValueError(f"Item at index {idx} is not a valid object.")

        item_id = item.get("id")
        if not item_id:
            raise ValueError(f"Item at index {idx} is missing mandatory 'id' field.")

        if item_id in seen_input_ids:
            raise ValueError(f"Duplicate rating found in input file for ID: '{item_id}'.")
        seen_input_ids.add(item_id)

        if item_id not in valid_examples:
            raise ValueError(f"Unknown ID '{item_id}' not found in the 30-example evaluation sample.")

        # Overwrite protection check
        if item_id in existing_ratings and not overwrite:
            raise ValueError(
                f"Rating for ID '{item_id}' already exists in data/human_ratings.json. "
                f"Use --overwrite flag to explicitly allow overwriting existing human ratings."
            )

        # Validate numeric dimensions (1-5 integers)
        for dim in ["relevance", "groundedness", "helpfulness", "correctness"]:
            val = item.get(dim)
            if val is None:
                raise ValueError(f"Missing mandatory rating dimension '{dim}' for ID '{item_id}'.")
            if not isinstance(val, int) or isinstance(val, bool) or val < 1 or val > 5:
                raise ValueError(
                    f"Invalid rating value '{val}' for dimension '{dim}' on ID '{item_id}'. "
                    f"Rating must be an integer between 1 and 5."
                )

        rel = item["relevance"]
        grd = item["groundedness"]
        hlp = item["helpfulness"]
        cor = item["correctness"]
        overall = round(0.30 * rel + 0.30 * grd + 0.20 * hlp + 0.20 * cor, 2)
        notes = item.get("notes") or "Imported via scripts/import_human_ratings.py"

        base_example = valid_examples[item_id]
        validated_ratings[item_id] = {
            "id": item_id,
            "customer_message": base_example.get("customer_message") or base_example.get("customer_text"),
            "generated_reply": base_example.get("generated_reply"),
            "retrieved_evidence": base_example.get("retrieved_evidence") or base_example.get("evidence_ids", []),
            "human_relevance": rel,
            "human_groundedness": grd,
            "human_helpfulness": hlp,
            "human_correctness": cor,
            "human_overall_score": overall,
            "human_notes": notes,
            "evaluation_source": "HUMAN_RATINGS"
        }

    # Merge with existing ratings
    merged_ratings = existing_ratings.copy()
    merged_ratings.update(validated_ratings)

    # Build template alignment order (30 items)
    final_examples_list = []
    for ex_id, base_ex in valid_examples.items():
        if ex_id in merged_ratings:
            final_examples_list.append(merged_ratings[ex_id])
        else:
            final_examples_list.append({
                "id": ex_id,
                "customer_message": base_ex.get("customer_message") or base_ex.get("customer_text"),
                "generated_reply": base_ex.get("generated_reply"),
                "retrieved_evidence": base_ex.get("retrieved_evidence") or base_ex.get("evidence_ids", []),
                "human_relevance": None,
                "human_groundedness": None,
                "human_helpfulness": None,
                "human_correctness": None,
                "human_overall_score": None,
                "human_notes": None,
                "evaluation_source": "HUMAN_RATINGS"
            })

    completed_count = sum(1 for ex in final_examples_list if ex["human_overall_score"] is not None)
    has_ratings = completed_count > 0

    export_payload = {
        "metadata": {
            "total_examples": len(final_examples_list),
            "completed_count": completed_count,
            "has_genuine_human_ratings": has_ratings,
            "evaluation_source": "HUMAN_RATINGS",
            "import_status": f"Imported {len(validated_ratings)} ratings. {completed_count}/{len(final_examples_list)} total completed."
        },
        "examples": final_examples_list
    }

    # Save to data/human_ratings.json
    os.makedirs(os.path.dirname(HUMAN_RATINGS_PATH), exist_ok=True)
    with open(HUMAN_RATINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(export_payload, f, indent=2, ensure_ascii=False)

    # Synchronize data/human_rating_template.json
    with open(HUMAN_TEMPLATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(export_payload, f, indent=2, ensure_ascii=False)

    print(f"Successfully imported {len(validated_ratings)} ratings!")
    print(f"Total Completed: {completed_count}/{len(final_examples_list)} items in {HUMAN_RATINGS_PATH}")

    return export_payload

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import human ratings from JSON input file.")
    parser.add_argument("--input", "-i", type=str, default=r"d:\Hiver\data\human_ratings_input.json", help="Path to input JSON file with human ratings")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting existing ratings for matching IDs")

    args = parser.parse_args()
    try:
        validate_and_import_ratings(args.input, args.overwrite)
    except Exception as e:
        print(f"[ERROR]: {e}", file=sys.stderr)
        sys.exit(1)
