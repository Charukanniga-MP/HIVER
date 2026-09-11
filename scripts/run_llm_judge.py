"""
LLM Judge Runner Script.
Evaluates the 40-example sample in data/judge_sample.json using the LLM judge interface.
Saves data/llm_judge_results.json.
Enforces honest reporting when live LLM API keys are unconfigured or rate-limited.
"""

import os
import json
from src.llm_judge import judge_response, get_judge

JUDGE_SAMPLE_PATH = r'd:\Hiver\data\judge_sample.json'
LLM_JUDGE_RESULTS_PATH = r'd:\Hiver\data\llm_judge_results.json'

def run_llm_judge():
    print("=" * 70)
    print("RUNNING RESPONSE QUALITY JUDGE")
    print("=" * 70)

    if not os.path.exists(JUDGE_SAMPLE_PATH):
        print("Judge sample dataset not found. Running sampler first...")
        from scripts.sample_judge_set import create_judge_sample
        create_judge_sample()

    with open(JUDGE_SAMPLE_PATH, 'r', encoding='utf-8') as f:
        sample_payload = json.load(f)

    examples = sample_payload.get("examples", [])
    active_judge = get_judge()
    evaluator_type = getattr(active_judge, "__class__").__name__

    key = os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    use_api = os.getenv("USE_REAL_LLM_JUDGE", "false").lower() == "true"
    real_llm_executed = bool(key and use_api and evaluator_type != "NonLLMFallbackJudge")

    if not real_llm_executed:
        print("[NOTICE]: Real LLM judge could not be executed because working LLM API credentials/quota are unavailable.")
        print("[NOTICE]: Generating non-LLM fallback ratings for infrastructure verification only.")

    judged_results = []
    for ex in examples:
        c_text = ex["customer_text"]
        reply = ex["generated_reply"]
        evidence_ids = ex.get("evidence_ids", [])
        intent = ex["predicted_intent"]
        esc_decision = ex["predicted_escalation"]

        # Reconstruct evidence list format for judge input
        evidence_list = [{"evidence_id": eid, "similarity_score": ex.get("retrieval_best_similarity", 0.0)} for eid in evidence_ids]

        res = judge_response(c_text, reply, evidence_list, intent, esc_decision)

        judged_results.append({
            "id": ex["id"],
            "customer_text": c_text,
            "generated_reply": reply,
            "evidence_ids": evidence_ids,
            "predicted_intent": intent,
            "predicted_escalation": esc_decision,
            "relevance": res["relevance"],
            "groundedness": res["groundedness"],
            "helpfulness": res["helpfulness"],
            "correctness": res["correctness"],
            "overall_score": res["overall_score"],
            "reasoning": res["reasoning"],
            "evidence_supported": res.get("evidence_supported", True),
            "evaluator_type": res.get("evaluator_type", "non-LLM fallback")
        })

    payload = {
        "metadata": {
            "sample_size": len(judged_results),
            "real_llm_executed": real_llm_executed,
            "status_message": "Real LLM judge executed successfully." if real_llm_executed else "Real LLM judge could not be executed because working LLM provider/API credentials are unconfigured or rate-limited.",
            "evaluator": evaluator_type
        },
        "results": judged_results
    }

    os.makedirs(os.path.dirname(LLM_JUDGE_RESULTS_PATH), exist_ok=True)
    with open(LLM_JUDGE_RESULTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Exported judge results to {LLM_JUDGE_RESULTS_PATH} ({len(judged_results)} examples)")

if __name__ == "__main__":
    run_llm_judge()
