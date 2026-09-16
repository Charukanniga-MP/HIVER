"""
Script to compute agreement metrics between LLM Judge ratings and Human ratings.
Exports metrics to data/judge_human_agreement.json.
Does NOT fabricate LLM scores or substitute fallback heuristics as LLM scores.
"""

import os
import sys
import json
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from src.agreement_metrics import calculate_agreement, compute_cohen_kappa_quadratic

HUMAN_RATINGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'human_ratings.json')
LLM_JUDGE_RESULTS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'llm_judge_results.json')
AGREEMENT_METRICS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'judge_human_agreement.json')

def run_compute_agreement():
    print("=" * 70)
    print(" COMPUTING GEMINI LLM-JUDGE vs HUMAN AGREEMENT METRICS")
    print("=" * 70)

    if not os.path.exists(HUMAN_RATINGS_PATH):
        print(f"Error: Human ratings file missing at {HUMAN_RATINGS_PATH}")
        sys.exit(1)

    with open(HUMAN_RATINGS_PATH, 'r', encoding='utf-8') as f:
        human_payload = json.load(f)

    human_examples = {ex["id"]: ex for ex in human_payload.get("examples", []) if ex.get("human_overall_score") is not None}
    human_count = len(human_examples)

    if not os.path.exists(LLM_JUDGE_RESULTS_PATH):
        print(f"Error: LLM judge results file missing at {LLM_JUDGE_RESULTS_PATH}")
        payload = {
            "metadata": {
                "judge_provider": "Gemini",
                "evaluator_model": os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
                "real_llm_executed": False,
                "human_rating_count": human_count,
                "error_message": "LLM Judge results file missing. Run scripts/run_real_llm_judge.py first."
            },
            "summary": {
                "overall_exact_agreement_pct": None,
                "overall_within_one_point_pct": None,
                "sample_size": 0
            }
        }
        with open(AGREEMENT_METRICS_PATH, 'w', encoding='utf-8') as f_out:
            json.dump(payload, f_out, indent=2)
        sys.exit(1)

    with open(LLM_JUDGE_RESULTS_PATH, 'r', encoding='utf-8') as f:
        judge_payload = json.load(f)

    judge_meta = judge_payload.get("metadata", {})
    is_real_llm = judge_meta.get("real_llm_executed", False)
    judge_model = judge_meta.get("evaluator_model", os.getenv("GEMINI_MODEL", "gemini-3.6-flash"))
    judge_provider = judge_meta.get("judge_provider", "Gemini")

    if not is_real_llm:
        err_msg = judge_meta.get("status_message", judge_meta.get("error_details", "Real Gemini LLM Judge failed to execute."))
        print(f"\n[NOTICE] Real Gemini LLM Judge execution was not completed:")
        print(f"   Details: {err_msg}")
        print("Agreement calculation halted to prevent presenting fallback scores as real LLM scores.")

        payload = {
            "metadata": {
                "judge_provider": judge_provider,
                "evaluator_model": judge_model,
                "real_llm_executed": False,
                "human_rating_count": human_count,
                "status_message": err_msg,
                "note": "Real Gemini LLM Judge execution failed. No heuristic or fallback scores were substituted as LLM scores."
            },
            "summary": {
                "overall_exact_agreement_pct": None,
                "overall_within_one_point_pct": None,
                "sample_size": human_count
            }
        }
        os.makedirs(os.path.dirname(AGREEMENT_METRICS_PATH), exist_ok=True)
        with open(AGREEMENT_METRICS_PATH, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"Exported status to: {AGREEMENT_METRICS_PATH}")
        return payload

    judge_results = {ex["id"]: ex for ex in judge_payload.get("results", [])}

    paired_items = []
    for ex_id, h_ex in human_examples.items():
        if ex_id in judge_results:
            paired_items.append((h_ex, judge_results[ex_id]))

    rated_count = len(paired_items)
    print(f"Matched {rated_count} paired ratings between Human ratings and Gemini Judge results.")
    print(f"Judge Provider: {judge_provider} ({judge_model})")

    dimensions = ["relevance", "groundedness", "helpfulness", "correctness", "overall"]
    dim_metrics = {}

    for dim in dimensions:
        h_scores = []
        for p in paired_items:
            h_val = p[0].get(f"human_{dim}")
            if h_val is None and dim == "overall":
                h_val = p[0].get("human_overall_score")
            if h_val is not None:
                h_scores.append(int(round(float(h_val))))

        j_scores = [int(p[1][dim]) for p in paired_items if dim in p[1] and p[1][dim] is not None]

        if len(h_scores) > 0 and len(h_scores) == len(j_scores):
            exact = sum(1 for h, j in zip(h_scores, j_scores) if h == j)
            within_one = sum(1 for h, j in zip(h_scores, j_scores) if abs(h - j) <= 1)
            kappa = compute_cohen_kappa_quadratic(h_scores, j_scores)

            dim_metrics[dim] = {
                "sample_size": len(h_scores),
                "human_mean": round(float(sum(h_scores) / len(h_scores)), 2),
                "gemini_mean": round(float(sum(j_scores) / len(j_scores)), 2),
                "exact_agreement_pct": round(exact / len(h_scores) * 100, 2),
                "within_one_point_pct": round(within_one / len(h_scores) * 100, 2),
                "cohen_kappa_quadratic": kappa
            }

    if dim_metrics:
        overall_exact = sum(dim_metrics[d]["exact_agreement_pct"] for d in dim_metrics) / len(dim_metrics)
        overall_within_one = sum(dim_metrics[d]["within_one_point_pct"] for d in dim_metrics) / len(dim_metrics)
    else:
        overall_exact = None
        overall_within_one = None

    payload = {
        "metadata": {
            "judge_provider": judge_provider,
            "evaluator_model": judge_model,
            "human_rating_count": rated_count,
            "real_llm_executed": True,
            "note": "Reported scores are computed from empirical matched human ratings and real Gemini judge predictions."
        },
        "summary": {
            "overall_exact_agreement_pct": round(overall_exact, 2) if overall_exact is not None else None,
            "overall_within_one_point_pct": round(overall_within_one, 2) if overall_within_one is not None else None,
            "sample_size": rated_count
        },
        "dimensional_agreement": dim_metrics
    }

    os.makedirs(os.path.dirname(AGREEMENT_METRICS_PATH), exist_ok=True)
    with open(AGREEMENT_METRICS_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"\nAgreement metrics exported to: {AGREEMENT_METRICS_PATH}")
    return payload

if __name__ == "__main__":
    run_compute_agreement()
