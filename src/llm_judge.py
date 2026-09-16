"""
LLM Judge Module for SpotifyCares AI Support System.
Evaluates generated responses against customer queries and retrieved evidence using a structured rubric.
Supports Google Gemini (google-genai), OpenRouter API (OpenAI-compatible), and OpenAI API.
Includes an explicit Non-LLM Fallback Judge for infrastructure testing.
"""

import os
import json
import datetime
import urllib.request
from dotenv import load_dotenv

# Load .env file from project root if present
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class NonLLMFallbackJudge:
    """
    Deterministic rule-based fallback evaluator.
    EXPLICIT DISCLOSURE: This is a non-LLM fallback judge used when no working LLM API key/quota is available.
    It is NOT an LLM judge and MUST NOT be represented as one.
    """
    def judge(self, customer_message: str, generated_reply: str, retrieved_evidence: list[dict], intent: str, escalation_decision: str) -> dict:
        evidence = retrieved_evidence or []
        best_sim = evidence[0]['similarity_score'] if (evidence and isinstance(evidence[0], dict) and 'similarity_score' in evidence[0]) else 0.0

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
            "overall": int(round(overall)),
            "reasoning": f"[Non-LLM Fallback Notice: Rule-based evaluation due to unconfigured/rate-limited LLM API] Best similarity: {best_sim:.2f}, Escalation: {escalation_decision}.",
            "reason": f"[Non-LLM Fallback Notice: Rule-based evaluation] Best similarity: {best_sim:.2f}.",
            "evidence_supported": bool(best_sim >= 0.40),
            "evaluator_type": "non-LLM fallback"
        }

class OpenRouterJudge:
    """
    Real LLM Judge using OpenRouter API (OpenAI-compatible endpoint).
    Requires OPENROUTER_API_KEY in environment or .env file.
    """
    def __init__(self, api_key: str = None, model_name: str = None):
        load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY environment variable is missing. "
                "Set OPENROUTER_API_KEY in your .env file or environment."
            )
        self.model_name = model_name or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    def judge(self, customer_message: str, generated_reply: str, retrieved_evidence: list[dict], intent: str, escalation_decision: str) -> dict:
        prompt = f"""
You are an expert evaluator for Spotify customer support responses.
Evaluate the generated support response based strictly on the customer message and retrieved historical evidence.

Customer Message: "{customer_message}"
Predicted Intent: "{intent}"
Escalation Decision: "{escalation_decision}"
Top Retrieved Evidence: {json.dumps(retrieved_evidence[:2] if retrieved_evidence else [], indent=2)}

Generated Reply to Evaluate: "{generated_reply}"

Rate the Generated Reply from 1 to 5 on each of these 5 dimensions:
1. relevance (integer 1-5): Does the reply address the customer's actual issue?
2. groundedness (integer 1-5): Is the reply supported by retrieved historical evidence?
3. helpfulness (integer 1-5): Does it provide a clear next step or clean handoff?
4. correctness (integer 1-5): Does it avoid false promises of refunds or fake claims of private account access?
5. overall (integer 1-5): Overall synthesis rating from 1 to 5.

Return ONLY valid JSON matching this exact structure:
{{
  "relevance": <integer 1-5>,
  "groundedness": <integer 1-5>,
  "helpfulness": <integer 1-5>,
  "correctness": <integer 1-5>,
  "overall": <integer 1-5>,
  "reason": "<short explanation>"
}}
"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Hiver Support Agent Evaluation",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a JSON-only evaluation judge."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"}
        }

        max_attempts = 3
        last_err = None
        for attempt in range(max_attempts):
            try:
                req = urllib.request.Request(
                    "https://openrouter.ai/api/v1/chat/completions",
                    data=json.dumps(payload).encode('utf-8'),
                    headers=headers
                )
                with urllib.request.urlopen(req, timeout=25) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    content = res_data['choices'][0]['message']['content']
                    parsed = json.loads(content)

                    # Validate required keys and integer bounds (1-5)
                    req_keys = ["relevance", "groundedness", "helpfulness", "correctness", "overall"]
                    for k in req_keys:
                        if k not in parsed:
                            raise ValueError(f"Missing required key '{k}' in OpenRouter output JSON: {parsed}")
                        val = int(parsed[k])
                        if not (1 <= val <= 5):
                            raise ValueError(f"Value for '{k}' out of bounds 1-5: {val}")
                        parsed[k] = val

                    parsed["overall_score"] = float(parsed["overall"])
                    parsed["reasoning"] = str(parsed.get("reason", parsed.get("reasoning", f"Evaluated by OpenRouter {self.model_name}")))
                    parsed["judge_provider"] = "OpenRouter"
                    parsed["evaluator_model"] = self.model_name
                    parsed["evaluator_type"] = f"Real LLM Judge (OpenRouter {self.model_name})"
                    parsed["is_real_llm"] = True
                    parsed["timestamp"] = datetime.datetime.now().isoformat()
                    return parsed
            except Exception as e:
                last_err = e

        raise RuntimeError(f"Real OpenRouter LLM Judge execution failed after {max_attempts} attempts: {last_err}")

class GeminiJudge:
    """
    Real LLM Judge using Google Gemini API (via official google-genai SDK).
    Requires GEMINI_API_KEY in environment or .env file.
    """
    def __init__(self, api_key: str = None, model_name: str = None):
        load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is missing. "
                "Set GEMINI_API_KEY in your .env file or environment to run the real Gemini LLM judge."
            )
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        
        # Initialize Google GenAI client
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        except ImportError:
            raise RuntimeError("The 'google-genai' package is not installed. Install it via 'pip install google-genai'.")

    def judge(self, customer_message: str, generated_reply: str, retrieved_evidence: list[dict], intent: str, escalation_decision: str) -> dict:
        from google.genai import types

        prompt = f"""
You are an expert evaluator for Spotify customer support responses.
Evaluate the generated support response based strictly on the customer message and retrieved historical evidence.

Customer Message: "{customer_message}"
Predicted Intent: "{intent}"
Escalation Decision: "{escalation_decision}"
Top Retrieved Evidence: {json.dumps(retrieved_evidence[:2] if retrieved_evidence else [], indent=2)}

Generated Reply to Evaluate: "{generated_reply}"

Rate the Generated Reply from 1 to 5 on each of these 5 dimensions:
1. relevance (integer 1-5): Does the reply address the customer's actual issue?
2. groundedness (integer 1-5): Is the reply supported by retrieved historical evidence?
3. helpfulness (integer 1-5): Does it provide a clear next step or clean handoff?
4. correctness (integer 1-5): Does it avoid false promises of refunds or fake claims of private account access?
5. overall (integer 1-5): Overall synthesis rating from 1 to 5.

Return ONLY valid JSON matching this exact structure:
{{
  "relevance": <integer 1-5>,
  "groundedness": <integer 1-5>,
  "helpfulness": <integer 1-5>,
  "correctness": <integer 1-5>,
  "overall": <integer 1-5>,
  "reason": "<short explanation>"
}}
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            parsed = json.loads(response.text)

            # Validate required keys and integer bounds (1-5)
            req_keys = ["relevance", "groundedness", "helpfulness", "correctness", "overall"]
            for k in req_keys:
                if k not in parsed:
                    raise ValueError(f"Missing required key '{k}' in Gemini output JSON: {parsed}")
                val = int(parsed[k])
                if not (1 <= val <= 5):
                    raise ValueError(f"Value for '{k}' out of bounds 1-5: {val}")
                parsed[k] = val

            parsed["overall_score"] = float(parsed["overall"])
            parsed["reasoning"] = str(parsed.get("reason", parsed.get("reasoning", "Evaluated by Google Gemini LLM Judge")))
            parsed["judge_provider"] = "Gemini"
            parsed["evaluator_model"] = self.model_name
            parsed["evaluator_type"] = f"Real LLM Judge (Gemini {self.model_name})"
            parsed["is_real_llm"] = True
            parsed["timestamp"] = datetime.datetime.now().isoformat()
            return parsed
        except Exception as e:
            # Clear error reporting without swallowing exceptions or silent fallback
            raise RuntimeError(f"Real Gemini LLM Judge execution failed on model '{self.model_name}': {e}")

def get_judge():
    """
    Instantiate active judge provider.
    Prefers OpenRouterJudge if OPENROUTER_API_KEY is present, or GeminiJudge if GEMINI_API_KEY is present AND USE_REAL_LLM_JUDGE is 'true'.
    Otherwise falls back to NonLLMFallbackJudge for local unit tests and infrastructure testing.
    """
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    use_api = os.getenv("USE_REAL_LLM_JUDGE", "false").lower() == "true"
    or_key = os.getenv("OPENROUTER_API_KEY")
    gem_key = os.getenv("GEMINI_API_KEY")

    if or_key and use_api:
        try:
            return OpenRouterJudge(api_key=or_key)
        except Exception:
            pass
    if gem_key and use_api:
        try:
            return GeminiJudge(api_key=gem_key)
        except Exception:
            pass
    return NonLLMFallbackJudge()

def run_real_llm_judge(customer_message: str, generated_reply: str, retrieved_evidence: list[dict], intent: str, escalation_decision: str) -> dict:
    """
    Executes Real LLM Judge strictly using OpenRouter or Gemini. Fails clearly if API key is missing or call fails.
    Does NOT silently fall back to NonLLMFallbackJudge.
    """
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    or_key = os.getenv("OPENROUTER_API_KEY")
    gem_key = os.getenv("GEMINI_API_KEY")

    if or_key:
        judge_instance = OpenRouterJudge(api_key=or_key)
        return judge_instance.judge(customer_message, generated_reply, retrieved_evidence, intent, escalation_decision)
    elif gem_key:
        judge_instance = GeminiJudge(api_key=gem_key)
        return judge_instance.judge(customer_message, generated_reply, retrieved_evidence, intent, escalation_decision)
    else:
        raise ValueError(
            "Neither OPENROUTER_API_KEY nor GEMINI_API_KEY environment variable is missing. "
            "Set OPENROUTER_API_KEY in your .env file to run the real LLM judge."
        )

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
