"""
Live Inference API Server for SpotifyCares AI Support System.
Runs a lightweight Flask HTTP server that executes the real Python AI support pipeline:
src.intent_taxonomy -> src.retriever -> src.escalation -> src.generator.
"""

import os
import json
from flask import Flask, request, jsonify

from src.intent_taxonomy import classify_intent
from src.retriever import HistoricalRetriever, CLEAN_CORPUS_PATH
from src.escalation import decide_escalation
from src.generator import generate_grounded_response

app = Flask(__name__)

# Initialize Retriever once at server startup (indexes 42,440 cases in memory)
print("[SERVER]: Loading HistoricalRetriever index...")
retriever = HistoricalRetriever(CLEAN_CORPUS_PATH)
print("[SERVER]: HistoricalRetriever index ready.")

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "SpotifyCares AI Support Inference API",
        "corpus_size": len(retriever.conversations)
    })

@app.route("/api/predict", methods=["POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(silent=True) or {}
    customer_text = data.get("customer_text", "").strip()

    if not customer_text:
        return jsonify({"error": "Customer text cannot be empty"}), 400

    # 1. Intent Classification
    intent_res = classify_intent(customer_text)
    pred_intent = intent_res["intent"]
    confidence = intent_res["confidence"]
    intent_reason = intent_res["reason"]

    # 2. Evidence Retrieval
    retrieval_res = retriever.retrieve_with_quality(customer_text, top_k=3)
    best_sim = retrieval_res["best_similarity"]
    evidence_quality = retrieval_res["evidence_quality"]
    evidence_list = retrieval_res["evidence"]

    # 3. Escalation Decision
    esc_res = decide_escalation(pred_intent, confidence, best_sim, customer_text, evidence_list)
    pred_esc = esc_res["decision"]
    esc_reason = esc_res["reason"]
    risk_level = esc_res["risk_level"]

    # 4. Grounded Reply Generation
    gen_res = generate_grounded_response(customer_text, pred_intent, retrieval_res, esc_res)
    reply = gen_res["reply"]
    evidence_ids = gen_res["evidence_ids"]
    grounding_reason = gen_res["grounding_reason"]

    top_evidence = evidence_list[0] if evidence_list else {}
    top_ev_id = top_evidence.get("evidence_id", "SPOT-00000")
    hist_cust = top_evidence.get("clean_customer_text", "No matching historical customer text.")
    hist_brand = top_evidence.get("clean_brand_text", "No matching historical resolution response.")

    return jsonify({
        "id": f"LIVE-{hash(customer_text) % 10000:04d}",
        "customer_handle": "@live_user",
        "timestamp": "JUST NOW",
        "customer_text": customer_text,
        "true_intent": pred_intent,
        "confidence": confidence,
        "intent_reason": intent_reason,
        "evidence_id": top_ev_id,
        "similarity_score": best_sim,
        "evidence_quality": evidence_quality,
        "evidence_list": [
            {
                "evidence_id": e.get("evidence_id"),
                "similarity_score": e.get("similarity_score"),
                "clean_customer_text": e.get("clean_customer_text"),
                "clean_brand_text": e.get("clean_brand_text")
            } for e in evidence_list
        ],
        "historical_customer": hist_cust,
        "historical_brand": hist_brand,
        "grounded": best_sim >= 0.50,
        "draft_reply": reply,
        "escalation": pred_esc,
        "why": esc_reason,
        "risk_level": risk_level,
        "grounding_reason": grounding_reason,
        "is_live_inference": True
    })

if __name__ == "__main__":
    print("[SERVER]: Starting SpotifyCares AI Support Inference API Server on http://localhost:5000...")
    app.run(host="0.0.0.0", port=5000, debug=False)
