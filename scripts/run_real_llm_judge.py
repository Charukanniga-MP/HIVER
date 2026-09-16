#!/usr/bin/env python3
"""
CLI Script to execute Real LLM Judge using OpenRouter or Gemini API over the 30 response-quality sample items.
Requires OPENROUTER_API_KEY or GEMINI_API_KEY in .env file or environment variables.
Exports results to data/llm_judge_results.json.
"""

import os
import sys
import json
import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from src.llm_judge import OpenRouterJudge, GeminiJudge
from src.retriever import HistoricalRetriever, CLEAN_CORPUS_PATH

HUMAN_RATINGS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'human_ratings.json')
LLM_JUDGE_RESULTS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'llm_judge_results.json')

def execute_real_llm_judge_run():
    print("=" * 70)
    print(" EXECUTING REAL LLM-AS-A-JUDGE EVALUATION RUN")
    print("=" * 70)

    or_key = os.getenv("OPENROUTER_API_KEY")
    gem_key = os.getenv("GEMINI_API_KEY")

    if or_key:
        provider = "OpenRouter"
        model_name = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        print(f"Provider: OpenRouter ({model_name})")
        judge_instance = OpenRouterJudge(api_key=or_key, model_name=model_name)
    elif gem_key:
        provider = "Gemini"
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        print(f"Provider: Google Gemini ({model_name})")
        judge_instance = GeminiJudge(api_key=gem_key, model_name=model_name)
    else:
        print("\n[ERROR] Neither OPENROUTER_API_KEY nor GEMINI_API_KEY environment variable is set.")
        print("Please set your API key in the root .env file.")
        sys.exit(1)

    if not os.path.exists(HUMAN_RATINGS_PATH):
        print(f"Error: Human ratings sample missing at {HUMAN_RATINGS_PATH}")
        sys.exit(1)

    with open(HUMAN_RATINGS_PATH, 'r', encoding='utf-8') as f:
        human_payload = json.load(f)

    examples = human_payload.get("examples", [])
    print(f"Evaluating {len(examples)} response-quality sample items using {provider} ({model_name})...")

    retriever = HistoricalRetriever(CLEAN_CORPUS_PATH)
    results = []

    for idx, ex in enumerate(examples, 1):
        item_id = ex["id"]
        c_text = ex.get("customer_message") or ex.get("customer_text", "")
        generated_reply = ex.get("generated_reply", "")
        intent = ex.get("ai_assisted_intent", "general_feedback_inquiry")
        esc_decision = ex.get("ai_assisted_escalation", "AUTO-HANDLE")

        # Retrieve evidence
        retrieval_res = retriever.retrieve_with_quality(c_text, exclude_tweet_id=ex.get("customer_tweet_id"), top_k=2)
        evidence = retrieval_res.get("evidence", [])

        print(f"[{idx}/{len(examples)}] Judging item {item_id} via {provider} ({model_name})...")
        try:
            # Execute LLM Judge (NOTE: Human scores are strictly excluded from prompt)
            judge_res = judge_instance.judge(c_text, generated_reply, evidence, intent, esc_decision)
        except Exception as e:
            print(f"\n[ERROR] during Real LLM Judge execution on item {item_id}:")
            print(f"   {e}")
            print("\nLLM Evaluation Halted. NonLLMFallbackJudge will NOT be used to fabricate scores.")
            
            # Record explicit error payload to avoid fake data
            error_payload = {
                "metadata": {
                    "sample_size": len(examples),
                    "real_llm_executed": False,
                    "judge_provider": provider,
                    "evaluator_model": model_name,
                    "status_message": f"Real LLM Judge failed: {e}",
                    "error_details": str(e),
                    "timestamp": datetime.datetime.now().isoformat()
                },
                "results": results
            }
            os.makedirs(os.path.dirname(LLM_JUDGE_RESULTS_PATH), exist_ok=True)
            with open(LLM_JUDGE_RESULTS_PATH, 'w', encoding='utf-8') as f_err:
                json.dump(error_payload, f_err, indent=2, ensure_ascii=False)
            sys.exit(1)

        results.append({
            "id": item_id,
            "judge_provider": provider,
            "evaluator_model": model_name,
            "timestamp": judge_res.get("timestamp", datetime.datetime.now().isoformat()),
            "customer_text": c_text,
            "generated_reply": generated_reply,
            "relevance": judge_res["relevance"],
            "groundedness": judge_res["groundedness"],
            "helpfulness": judge_res["helpfulness"],
            "correctness": judge_res["correctness"],
            "overall": judge_res["overall"],
            "overall_score": judge_res["overall_score"],
            "reasoning": judge_res.get("reasoning", judge_res.get("reason", "")),
            "evaluator_type": judge_res.get("evaluator_type", f"{provider} {model_name} LLM Judge")
        })

    payload = {
        "metadata": {
            "total_evaluated": len(results),
            "real_llm_executed": True,
            "judge_provider": provider,
            "evaluator_model": model_name,
            "timestamp": datetime.datetime.now().isoformat()
        },
        "results": results
    }

    os.makedirs(os.path.dirname(LLM_JUDGE_RESULTS_PATH), exist_ok=True)
    with open(LLM_JUDGE_RESULTS_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Real LLM Judge run complete! Exported {len(results)} results to {LLM_JUDGE_RESULTS_PATH}")
    return payload

if __name__ == "__main__":
    execute_real_llm_judge_run()
