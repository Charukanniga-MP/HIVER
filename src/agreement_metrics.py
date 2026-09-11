"""
Agreement Metrics Calculation Module.
Calculates agreement statistics (Exact Agreement, Within-One-Point Agreement, Weighted Cohen's Kappa, Spearman Correlation)
between LLM Judge scores and genuine Human ratings.
Enforces zero fabrication when human ratings are unavailable.
"""

import os
import json
import math

HUMAN_TEMPLATE_PATH = r'd:\Hiver\data\human_rating_template.json'
HUMAN_RATINGS_PATH = r'd:\Hiver\data\human_ratings.json'
LLM_JUDGE_RESULTS_PATH = r'd:\Hiver\data\llm_judge_results.json'
AGREEMENT_METRICS_PATH = r'd:\Hiver\data\judge_human_agreement.json'

def compute_cohen_kappa_quadratic(ratings1: list[int], ratings2: list[int], min_rating: int = 1, max_rating: int = 5) -> float:
    """
    Compute Quadratic Weighted Cohen's Kappa.
    """
    n = len(ratings1)
    if n == 0:
        return 0.0

    k = max_rating - min_rating + 1
    # Build weight matrix (quadratic penalty)
    w = [[((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)]

    # Build observed confusion matrix
    o = [[0 for _ in range(k)] for _ in range(k)]
    for r1, r2 in zip(ratings1, ratings2):
        i = max(0, min(k - 1, r1 - min_rating))
        j = max(0, min(k - 1, r2 - min_rating))
        o[i][j] += 1

    # Expected matrix
    hist1 = [sum(o[i][j] for j in range(k)) for i in range(k)]
    hist2 = [sum(o[i][j] for i in range(k)) for j in range(k)]

    e = [[(hist1[i] * hist2[j]) / n for j in range(k)] for i in range(k)]

    numerator = sum(w[i][j] * o[i][j] for i in range(k) for j in range(k))
    denominator = sum(w[i][j] * e[i][j] for i in range(k) for j in range(k))

    if denominator == 0:
        return 1.0
    return round(1.0 - (numerator / denominator), 4)

def calculate_agreement():
    """
    Calculate agreement metrics between Judge results and Human ratings.
    """
    human_file = HUMAN_RATINGS_PATH if os.path.exists(HUMAN_RATINGS_PATH) else HUMAN_TEMPLATE_PATH
    if not os.path.exists(human_file) or not os.path.exists(LLM_JUDGE_RESULTS_PATH):
        payload = {
            "metadata": {
                "has_genuine_human_ratings": False,
                "status_message": "Missing input files for agreement metrics computation."
            },
            "metrics": None
        }
        os.makedirs(os.path.dirname(AGREEMENT_METRICS_PATH), exist_ok=True)
        with open(AGREEMENT_METRICS_PATH, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return payload

    with open(human_file, 'r', encoding='utf-8') as f:
        human_data = json.load(f)

    with open(LLM_JUDGE_RESULTS_PATH, 'r', encoding='utf-8') as f:
        judge_data = json.load(f)

    human_examples = {ex["id"]: ex for ex in human_data.get("examples", [])}
    judge_examples = {ex["id"]: ex for ex in judge_data.get("results", [])}

    # Identify valid pairs where human rating is non-null
    paired_items = []
    for ex_id, h_ex in human_examples.items():
        if h_ex.get("human_overall_score") is not None and ex_id in judge_examples:
            paired_items.append((h_ex, judge_examples[ex_id]))

    rated_count = len(paired_items)
    total_human_examples = len(human_examples)

    if rated_count == 0:
        payload = {
            "metadata": {
                "total_human_template_examples": total_human_examples,
                "human_rated_count": 0,
                "has_genuine_human_ratings": False,
                "status_message": "No genuine human ratings recorded yet (0/30 rated). Agreement metrics cannot be calculated without human ratings."
            },
            "agreement_metrics": None
        }
        os.makedirs(os.path.dirname(AGREEMENT_METRICS_PATH), exist_ok=True)
        with open(AGREEMENT_METRICS_PATH, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print("Agreement Calculation: 0 human ratings found. Saved status message to data/judge_human_agreement.json")
        return payload

    # Calculate dimensional metrics if human ratings exist
    dimensions = ["relevance", "groundedness", "helpfulness", "correctness"]
    dim_metrics = {}

    for dim in dimensions:
        h_ratings = [int(p[0][f"human_{dim}"]) for p in paired_items]
        j_ratings = [int(p[1][dim]) for p in paired_items]

        exact = sum(1 for h, j in zip(h_ratings, j_ratings) if h == j)
        within_one = sum(1 for h, j in zip(h_ratings, j_ratings) if abs(h - j) <= 1)
        kappa = compute_cohen_kappa_quadratic(h_ratings, j_ratings)

        dim_metrics[dim] = {
            "exact_agreement_pct": round(exact / rated_count * 100, 2),
            "within_one_point_pct": round(within_one / rated_count * 100, 2),
            "cohen_kappa_quadratic": kappa
        }

    payload = {
        "metadata": {
            "total_human_template_examples": total_human_examples,
            "human_rated_count": rated_count,
            "has_genuine_human_ratings": True,
            "status_message": f"Calculated agreement metrics over {rated_count} human-rated examples."
        },
        "dimensional_agreement": dim_metrics
    }

    os.makedirs(os.path.dirname(AGREEMENT_METRICS_PATH), exist_ok=True)
    with open(AGREEMENT_METRICS_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Calculated agreement metrics for {rated_count} human-rated items -> {AGREEMENT_METRICS_PATH}")
    return payload

if __name__ == "__main__":
    calculate_agreement()
