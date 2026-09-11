"""
Grounded Response Generation Module for SpotifyCares AI Support System.
Generates concise, brand-aligned support responses grounded in retrieved historical evidence.
Controls hallucination by refusing to make unsupported policy promises or claim private account access.
"""

def generate_grounded_response(
    query_text: str,
    intent: str,
    retrieval_result: dict,
    escalation_result: dict
) -> dict:
    """
    Generate grounded support reply with evidence IDs and grounding rationale.
    Returns:
    {
      "reply": str,
      "evidence_ids": list[str],
      "grounding_reason": str
    }
    """
    decision = escalation_result.get("decision", "AUTO-HANDLE")
    evidence_list = retrieval_result.get("evidence", [])
    evidence_quality = retrieval_result.get("evidence_quality", "weak")
    best_sim = retrieval_result.get("best_similarity", 0.0)
    evidence_ids = [e.get("evidence_id") for e in evidence_list]

    # ESCALATION CASE: Safe handoff without hallucinating actions or account access
    if decision == "ESCALATE TO HUMAN":
        if intent == "billing_subscription_dispute":
            reply = (
                "I apologize for the trouble with your billing. Because payment adjustments require "
                "secure account verification, I've escalated your ticket to our Billing Specialists to review your account safely."
            )
            reason = "Escalated billing dispute to human specialist due to account financial verification requirement."
        elif intent == "account_access_security":
            reply = (
                "We take account security very seriously. I've immediately flagged your request for our "
                "Account Security Team to help you regain secure access safely."
            )
            reason = "Escalated security issue to human safety team to prevent unauthorized access."
        else:
            reply = (
                "Thank you for reaching out! To make sure this gets resolved accurately, I've escalated your request "
                "to a human support agent who will follow up with you directly."
            )
            reason = f"Escalated {intent} query to human agent (Escalation Reason: {escalation_result.get('reason', 'High risk / ambiguous')})."

        return {
            "reply": reply,
            "evidence_ids": evidence_ids,
            "grounding_reason": reason
        }

    # AUTO-HANDLE CASE: Grounded on top historical resolution evidence
    if evidence_list and evidence_quality in ["strong", "medium"]:
        top_match = evidence_list[0]['historical_brand_response']
        # Clean brand response prefix if present
        clean_reply = top_match
        reply = f"Hey! {clean_reply}"
        reason = f"Reply grounded on historical resolution (Evidence ID: {evidence_ids[0]}, Similarity: {best_sim:.2f}, Quality: {evidence_quality})."
    else:
        # Fallback if quality is weak: differ between general feedback and technical issues
        if intent == "general_feedback_inquiry":
            reply = (
                "Thanks for reaching out and sharing your feedback with us! "
                "We really appreciate the suggestion and will pass it along to our product team."
            )
            reason = f"No sufficiently grounded historical evidence (best similarity {best_sim:.2f}); provided safe product feedback acknowledgment."
        else:
            reply = (
                "Hi there! Can you try restarting your app and checking for the latest Spotify update? "
                "If the issue persists, let us know and we will get a human specialist to take a closer look!"
            )
            reason = f"Generic troubleshooting fallback used because retrieval evidence quality was {evidence_quality} (best similarity {best_sim:.2f})."

    return {
        "reply": reply,
        "evidence_ids": evidence_ids,
        "grounding_reason": reason
    }

def generate_support_reply(
    query_text: str,
    intent: str,
    retrieved_evidence: list[dict],
    escalation_decision: str
) -> str:
    """
    Backwards-compatible string reply generator.
    """
    retrieval_result = {
        "evidence": retrieved_evidence,
        "best_similarity": retrieved_evidence[0]['similarity_score'] if retrieved_evidence else 0.0,
        "evidence_quality": "strong" if (retrieved_evidence and retrieved_evidence[0]['similarity_score'] >= 0.65) else "weak"
    }
    escalation_result = {
        "decision": escalation_decision,
        "reason": "Legacy call"
    }
    return generate_grounded_response(query_text, intent, retrieval_result, escalation_result)["reply"]
