"""
Response Quality Summary Computation Script.
Calculates aggregate statistics over judged responses in data/llm_judge_results.json.
Exports data/response_quality_summary.json.
"""

import os
import json
import numpy as np

LLM_JUDGE_RESULTS_PATH = r'd:\Hiver\data\llm_judge_results.json'
RESPONSE_QUALITY_SUMMARY_PATH = r'd:\Hiver\data\response_quality_summary.json'

def compute_response_quality_summary():
    """
    Compute aggregate metrics over judged responses.
    """
    if not os.path.exists(LLM_JUDGE_RESULTS_PATH):
        from scripts.run_llm_judge import run_llm_judge
        run_llm_judge()

    with open(LLM_JUDGE_RESULTS_PATH, 'r', encoding='utf-8') as f:
        payload = json.load(f)

    results = payload.get("results", [])
    meta = payload.get("metadata", {})
    total = len(results)

    if total == 0:
        print("No judged results found to aggregate.")
        return

    rel_list = [r["relevance"] for r in results]
    grd_list = [r["groundedness"] for r in results]
    hlp_list = [r["helpfulness"] for r in results]
    cor_list = [r["correctness"] for r in results]
    ovr_list = [r["overall_score"] for r in results]

    mean_rel = round(float(np.mean(rel_list)), 4)
    mean_grd = round(float(np.mean(grd_list)), 4)
    mean_hlp = round(float(np.mean(hlp_list)), 4)
    mean_cor = round(float(np.mean(cor_list)), 4)
    mean_ovr = round(float(np.mean(ovr_list)), 4)

    pct_grd_ge_4 = round(sum(1 for g in grd_list if g >= 4) / total * 100, 2)
    pct_cor_ge_4 = round(sum(1 for c in cor_list if c >= 4) / total * 100, 2)

    summary_payload = {
        "metadata": {
            "total_judged_examples": total,
            "evaluator_type": meta.get("evaluator", "non-LLM fallback"),
            "real_llm_executed": meta.get("real_llm_executed", False),
            "status_message": meta.get("status_message", "")
        },
        "response_quality_metrics": {
            "mean_relevance": mean_rel,
            "mean_groundedness": mean_grd,
            "mean_helpfulness": mean_hlp,
            "mean_correctness": mean_cor,
            "mean_overall_score": mean_ovr,
            "pct_groundedness_ge_4": pct_grd_ge_4,
            "pct_correctness_ge_4": pct_cor_ge_4
        }
    }

    os.makedirs(os.path.dirname(RESPONSE_QUALITY_SUMMARY_PATH), exist_ok=True)
    with open(RESPONSE_QUALITY_SUMMARY_PATH, 'w', encoding='utf-8') as f:
        json.dump(summary_payload, f, indent=2, ensure_ascii=False)

    print(f"Exported response quality summary to {RESPONSE_QUALITY_SUMMARY_PATH}")
    print(f"Mean Overall Score: {mean_ovr:.2f} | Groundedness >= 4: {pct_grd_ge_4:.1f}% | Correctness >= 4: {pct_cor_ge_4:.1f}%")
    return summary_payload

if __name__ == "__main__":
    compute_response_quality_summary()
