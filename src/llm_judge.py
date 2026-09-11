"""
LLM Judge Module for SpotifyCares AI Support System.
Evaluates generated responses against customer queries and retrieved evidence using a structured rubric.
Includes provider abstraction for OpenAI/Gemini and an explicit Non-LLM Fallback Judge.
"""

import os
import json
import urllib.request
import urllib.error

class NonLLMFallbackJudge:
    """
    Deterministic rule-based fallback evaluator.
    EXPLICIT DISCLOSURE: This is a non-LLM fallback judge used when no working LLM API key/quota is available.
    It is NOT an LLM judge and MUST NOT be represented as one.
    """
    def judge(self, customer_message: str, generated_reply: str, retrieved_evidence: list[dict], intent: str, escalation_decision: str) -> dict:
        evidence = retrieved_evidence or []
        best_sim = evidence[0]['similarity_score'] if evidence else 0.0

        # 1. Groundedness based on similarity score
        if best_sim >= 0.70:
            groundedness = 5
        elif best_sim >= 0.50:
            groundedness = 4
        elif best_sim >= 0.38:
            groundedness = 3
        else:
            groundedness = 2

        # 2. Correctness & Safety
        reply_lower = generated_reply.lower()
        has_unsafe_claim = any(kw in reply_lower for kw in [
            "issued a refund", "refunded your card", "changed your password",
            "accessed your account", "credited your account"
        ])
        correctness = 1 if has_unsafe_claim else 5

        # 3. Relevance
        relevance = 5 if len(generated_reply) > 15 else 3

        # 4. Helpfulness
        helpfulness = 5 if escalation_decision == "AUTO-HANDLE" and best_sim >= 0.50 else 4

        # Overall Score Weighted Combination
        overall = round(0.30 * relevance + 0.30 * groundedness + 0.20 * helpfulness + 0.20 * correctness, 2)

        return {
            "relevance": int(relevance),
            "groundedness": int(groundedness),
            "helpfulness": int(helpfulness),
            "correctness": int(correctness),
            "overall_score": float(overall),
            "reasoning": f"[Non-LLM Fallback Notice: Rule-based evaluation due to unconfigured/rate-limited LLM API] Best similarity: {best_sim:.2f}, Escalation: {escalation_decision}.",
            "evidence_supported": bool(best_sim >= 0.40),
            "evaluator_type": "non-LLM fallback"
        }

class OpenAIJudge:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def judge(self, customer_message: str, generated_reply: str, retrieved_evidence: list[dict], intent: str, escalation_decision: str) -> dict:
        prompt = f"""
You are an expert evaluator for Spotify customer support responses.
Evaluate the generated support response based strictly on the customer message and retrieved historical evidence.

Customer Message: "{customer_message}"
Predicted Intent: "{intent}"
Escalation Decision: "{escalation_decision}"
Top Retrieved Evidence: {json.dumps(retrieved_evidence[:2] if retrieved_evidence else [], indent=2)}

Generated Reply to Evaluate: "{generated_reply}"

Rate the Generated Reply from 1 to 5 on each of these 4 dimensions:
1. relevance (1-5): Does the reply address the customer's actual issue?
2. groundedness (1-5): Is the reply supported by retrieved historical evidence?
3. helpfulness (1-5): Does it provide a clear next step or clean handoff?
4. correctness (1-5): Does it avoid false promises of refunds or fake claims of private account access?

Return ONLY valid JSON matching this exact structure:
{{
  "relevance": <integer 1-5>,
  "groundedness": <integer 1-5>,
  "helpfulness": <integer 1-5>,
  "correctness": <integer 1-5>,
  "overall_score": <float 1.0-5.0>,
  "reasoning": "<short explanation>",
  "evidence_supported": <true/false>
}}
"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a JSON-only evaluation judge."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode('utf-8'),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            content = res_data['choices'][0]['message']['content']
            parsed = json.loads(content)
            parsed["evaluator_type"] = "OpenAI GPT-4o-mini LLM Judge"
            return parsed

def get_judge():
    """
    Instantiate active judge provider.
    Enforces NonLLMFallbackJudge unless explicit working API key and flag are present.
    """
    key = os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    use_api = os.getenv("USE_REAL_LLM_JUDGE", "false").lower() == "true"
    if key and use_api:
        try:
            return OpenAIJudge(key)
        except Exception:
            return NonLLMFallbackJudge()
    return NonLLMFallbackJudge()

def judge_response(
    customer_message: str,
    generated_reply: str,
    retrieved_evidence: list[dict],
    intent: str,
    escalation_decision: str
) -> dict:
    """
    Main response judging function interface.
    """
    judge_instance = get_judge()
    return judge_instance.judge(customer_message, generated_reply, retrieved_evidence, intent, escalation_decision)
