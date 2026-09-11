"""
Escalation Policy Engine for SpotifyCares AI Support System.
Evaluates intent, confidence, financial/security risk signals, retrieval evidence quality, and ambiguity
to decide between AUTO-HANDLE and ESCALATE TO HUMAN.
"""

import re

# High-risk security takeover signals
SECURITY_RISK_TERMS = [
    "hacked", "hacker", "stolen account", "account hacked", "unauthorized access",
    "someone changed my", "someone logged into", "compromised", "takeover", "breach"
]

# High-risk financial dispute signals
BILLING_RISK_TERMS = [
    "refund", "double bill", "charged twice", "getting charged twice", "overcharged",
    "unauthorized charge", "stolen card", "fraud", "cancel my card", "money"
]

def decide_escalation(
    intent: str,
    confidence: float,
    retrieval_score: float,
    message: str,
    evidence: list[dict] = None
) -> dict:
    """
    Explicit escalation policy function.
    Returns:
    {
      "decision": "AUTO-HANDLE|ESCALATE TO HUMAN",
      "reason": str,
      "risk_level": "LOW|MEDIUM|HIGH"
    }
    """
    msg_clean = message.strip()
    msg_lower = msg_clean.lower()
    evidence = evidence or []
    best_sim = retrieval_score if retrieval_score is not None else (evidence[0]['similarity_score'] if evidence else 0.0)

    # 1. Mandatory Security & Credential Protection Rule
    # Account access, password reset, login failures, and takeover attempts require private identity verification
    if intent == "account_access_security" or any(kw in msg_lower for kw in SECURITY_RISK_TERMS) or any(term in msg_lower for term in ["login", "log in", "password", "email", "sign in"]):
        if any(kw in msg_lower for kw in SECURITY_RISK_TERMS):
            reason = "High-risk account security / takeover attempt requiring identity verification by human safety team."
            risk_level = "HIGH"
        else:
            reason = "Account access & security credential request requiring private account verification."
            risk_level = "MEDIUM"
        return {
            "decision": "ESCALATE TO HUMAN",
            "reason": reason,
            "risk_level": risk_level
        }

    # 2. Financial & Billing Dispute Safeguard Rule
    # Payment disputes, refunds, and unrecognized charges require financial ledger access
    if any(kw in msg_lower for kw in BILLING_RISK_TERMS) or (intent == "billing_subscription_dispute" and best_sim < 0.45):
        if any(kw in msg_lower for kw in BILLING_RISK_TERMS):
            reason = "Monetary transaction dispute or refund request requiring billing specialist authorization."
            risk_level = "HIGH"
        else:
            reason = "Billing inquiry with insufficient grounded evidence; escalating for payment verification."
            risk_level = "MEDIUM"
        return {
            "decision": "ESCALATE TO HUMAN",
            "reason": reason,
            "risk_level": risk_level
        }


    # 3. Low-Information & High-Ambiguity Rule
    words = msg_clean.split()
    if len(words) <= 2 and confidence < 0.50 and best_sim < 0.40:
        return {
            "decision": "ESCALATE TO HUMAN",
            "reason": "Ultra-short ambiguous query with weak retrieval evidence; routing to human agent.",
            "risk_level": "MEDIUM"
        }

    # 4. Out-of-Scope & Low Confidence Safeguard
    OUT_OF_SCOPE_TERMS = ["pizza", "order food", "weather", "taxi", "flight", "uber", "delivery"]
    if any(kw in msg_lower for kw in OUT_OF_SCOPE_TERMS) or (intent == "general_feedback_inquiry" and confidence <= 0.50 and best_sim < 0.60):
        return {
            "decision": "ESCALATE TO HUMAN",
            "reason": "Out-of-scope or low-confidence inquiry without specific Spotify support precedent; routing to human agent.",
            "risk_level": "LOW"
        }






    # 5. Safe Routine Technical & General Auto-Handling
    # Routine playback bugs, offline sync issues, playlist management, and general inquiries
    if best_sim >= 0.50:
        evidence_status = f"grounded historical evidence (similarity {best_sim:.2f})"
    elif intent == "general_feedback_inquiry":
        evidence_status = f"no sufficiently grounded historical evidence (similarity {best_sim:.2f}); safe feedback acknowledgment provided"
    else:
        evidence_status = f"standard troubleshooting fallback (insufficient historical evidence similarity {best_sim:.2f})"

    return {
        "decision": "AUTO-HANDLE",
        "reason": f"Routine issue ({intent}) with acceptable confidence ({confidence:.2f}) and {evidence_status}.",
        "risk_level": "LOW"
    }

def evaluate_escalation(
    intent: str,
    confidence: float,
    query_text: str,
    retrieved_evidence: list[dict]
) -> tuple[str, str, str]:
    """
    Backwards-compatible wrapper returning (decision, reason, grounding_status).
    """
    best_sim = retrieved_evidence[0]['similarity_score'] if retrieved_evidence else 0.0
    res = decide_escalation(intent, confidence, best_sim, query_text, retrieved_evidence)
    grounding = "SUPPORTED" if best_sim >= 0.40 else "UNSUPPORTED"
    return res["decision"], res["reason"], grounding
