"""
Evaluation Harness v3 for SpotifyCares AI Support System.
Evaluates Improved Proposed Support Agent on data/golden_set_v2.json.
Generates data/evaluation_v3.json, data/evaluation_summary_v3.json, and data/failure_analysis_v3.json.
"""

import os
import json
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

from src.intent_taxonomy import classify_intent, classify_intent_rule_based
from src.retriever import HistoricalRetriever, CLEAN_CORPUS_PATH, GOLDEN_SET_V2_PATH
from src.escalation import decide_escalation
from src.generator import generate_grounded_response
from src.baselines import MajorityClassBaseline, LogisticRegressionBaseline

EVALUATION_V3_PATH = r'd:\Hiver\data\evaluation_v3.json'
EVALUATION_SUMMARY_V3_PATH = r'd:\Hiver\data\evaluation_summary_v3.json'
FAILURE_ANALYSIS_V3_PATH = r'd:\Hiver\data\failure_analysis_v3.json'

def run_evaluation_v3():
    print("=" * 70)
    print("STARTING EVALUATION V3 (Improved Proposed Agent Benchmark)")
    print("=" * 70)

    # 1. Load Golden Evaluation Set
    with open(GOLDEN_SET_V2_PATH, 'r', encoding='utf-8') as f:
        golden_payload = json.load(f)

    golden_metadata = golden_payload.get('metadata', {})
    golden_examples = golden_payload.get('examples', [])
    total_examples = len(golden_examples)
    print(f"Loaded Golden Set v2 ({total_examples} items)")

    # 2. Initialize Retriever
    retriever = HistoricalRetriever(CLEAN_CORPUS_PATH)
    clean_corpus = retriever.conversations
    print(f"Clean Non-Golden Corpus Size: {len(clean_corpus):,} items")

    # 3. Train Baselines on Weakly Supervised Historical Corpus
    X_train_corpus = [c['clean_customer_text'] for c in clean_corpus]
    y_train_weak = [classify_intent_rule_based(t)[0] for t in X_train_corpus]

    majority_base = MajorityClassBaseline()
    majority_base.fit(X_train_corpus, y_train_weak)

    logreg_base = LogisticRegressionBaseline()
    logreg_base.fit(X_train_corpus, y_train_weak)

    # 4. Prepare Evaluation Target Data
    X_eval = [ex['customer_text'] for ex in golden_examples]
    y_intent_true = [ex['true_intent'] for ex in golden_examples]
    y_esc_true = [ex['true_escalation'] for ex in golden_examples]

    # Baseline Predictions
    maj_preds = majority_base.predict(X_eval)
    logreg_preds = logreg_base.predict(X_eval)

    # 5. Evaluate Improved Proposed System v3
    v3_per_example_results = []
    v3_intent_preds = []
    v3_esc_preds = []

    for ex in golden_examples:
        c_text = ex['customer_text']
        tweet_id = ex.get('customer_tweet_id')

        # Phase 1: Intent classification
        intent_res = classify_intent(c_text)
        pred_intent = intent_res["intent"]
        confidence = intent_res["confidence"]
        intent_reason = intent_res["reason"]

        # Phase 2: Evidence retrieval
        retrieval_res = retriever.retrieve_with_quality(c_text, exclude_tweet_id=tweet_id, top_k=3)
        best_sim = retrieval_res["best_similarity"]
        evidence_quality = retrieval_res["evidence_quality"]
        evidence_list = retrieval_res["evidence"]

        # Phase 4: Escalation decision
        esc_res = decide_escalation(pred_intent, confidence, best_sim, c_text, evidence_list)
        pred_esc = esc_res["decision"]
        esc_reason = esc_res["reason"]
        risk_level = esc_res["risk_level"]

        # Phase 3: Grounded response generation
        gen_res = generate_grounded_response(c_text, pred_intent, retrieval_res, esc_res)
        reply = gen_res["reply"]
        evidence_ids = gen_res["evidence_ids"]
        grounding_reason = gen_res["grounding_reason"]

        v3_intent_preds.append(pred_intent)
        v3_esc_preds.append(pred_esc)

        intent_correct = (pred_intent == ex['true_intent'])
        esc_correct = (pred_esc == ex['true_escalation'])

        v3_per_example_results.append({
            "id": ex['id'],
            "customer_text": c_text,
            "true_intent": ex['true_intent'],
            "predicted_intent": pred_intent,
            "intent_confidence": confidence,
            "intent_reason": intent_reason,
            "intent_correct": intent_correct,
            "retrieval_best_similarity": best_sim,
            "evidence_quality": evidence_quality,
            "evidence_ids": evidence_ids,
            "true_escalation": ex['true_escalation'],
            "predicted_escalation": pred_esc,
            "escalation_reason": esc_reason,
            "risk_level": risk_level,
            "escalation_correct": esc_correct,
            "generated_reply": reply,
            "grounding_reason": grounding_reason,
            "is_out_of_scope": ex.get('is_out_of_scope', False),
            "difficulty": ex.get('difficulty', 'Medium')
        })

    # Save v3 per-example results
    os.makedirs(os.path.dirname(EVALUATION_V3_PATH), exist_ok=True)
    with open(EVALUATION_V3_PATH, 'w', encoding='utf-8') as f:
        json.dump(v3_per_example_results, f, indent=2, ensure_ascii=False)

    # 6. Metrics Computation
    intent_labels = list(sorted(set(y_intent_true)))

    # Baselines
    acc_maj = accuracy_score(y_intent_true, maj_preds)
    _, _, f1_macro_maj, _ = precision_recall_fscore_support(y_intent_true, maj_preds, average='macro', zero_division=0)
    _, _, f1_weighted_maj, _ = precision_recall_fscore_support(y_intent_true, maj_preds, average='weighted', zero_division=0)

    acc_logreg = accuracy_score(y_intent_true, logreg_preds)
    _, _, f1_macro_logreg, _ = precision_recall_fscore_support(y_intent_true, logreg_preds, average='macro', zero_division=0)
    _, _, f1_weighted_logreg, _ = precision_recall_fscore_support(y_intent_true, logreg_preds, average='weighted', zero_division=0)

    # Proposed v3 System Intent Metrics
    acc_v3_intent = accuracy_score(y_intent_true, v3_intent_preds)
    _, _, f1_macro_v3_intent, _ = precision_recall_fscore_support(y_intent_true, v3_intent_preds, average='macro', zero_division=0)
    _, _, f1_weighted_v3_intent, _ = precision_recall_fscore_support(y_intent_true, v3_intent_preds, average='weighted', zero_division=0)

    p_intent_v3, r_intent_v3, f1_intent_v3, supp_intent_v3 = precision_recall_fscore_support(
        y_intent_true, v3_intent_preds, labels=intent_labels, zero_division=0
    )

    per_intent_metrics_v3 = {}
    for idx, intent_name in enumerate(intent_labels):
        per_intent_metrics_v3[intent_name] = {
            "precision": round(float(p_intent_v3[idx]), 4),
            "recall": round(float(r_intent_v3[idx]), 4),
            "f1": round(float(f1_intent_v3[idx]), 4),
            "support": int(supp_intent_v3[idx])
        }

    cm_v3_intent = confusion_matrix(y_intent_true, v3_intent_preds, labels=intent_labels).tolist()

    # Escalation Metrics
    tp = sum(1 for yt, yp in zip(y_esc_true, v3_esc_preds) if yt == 'ESCALATE TO HUMAN' and yp == 'ESCALATE TO HUMAN')
    tn = sum(1 for yt, yp in zip(y_esc_true, v3_esc_preds) if yt == 'AUTO-HANDLE' and yp == 'AUTO-HANDLE')
    fp = sum(1 for yt, yp in zip(y_esc_true, v3_esc_preds) if yt == 'AUTO-HANDLE' and yp == 'ESCALATE TO HUMAN')
    fn = sum(1 for yt, yp in zip(y_esc_true, v3_esc_preds) if yt == 'ESCALATE TO HUMAN' and yp == 'AUTO-HANDLE')

    acc_v3_esc = accuracy_score(y_esc_true, v3_esc_preds)
    p_v3_esc, r_v3_esc, f1_v3_esc, _ = precision_recall_fscore_support(
        y_esc_true, v3_esc_preds, pos_label='ESCALATE TO HUMAN', average='binary', zero_division=0
    )

    # Operational Rates
    auto_handle_count = sum(1 for p in v3_esc_preds if p == 'AUTO-HANDLE')
    automation_rate = round(auto_handle_count / total_examples, 4)
    over_escalation_rate = round(fp / total_examples, 4)
    missed_escalation_rate = round(fn / total_examples, 4)

    # Old System metrics for side-by-side comparison
    # Old proposed: Intent Acc 90.50%, Macro F1 0.8935, Escalation Acc 33.50%, P 19.51%, R 96.97%, F1 0.3249 (FP=132, FN=1, TP=32, TN=35)
    summary_v3 = {
        "metadata": {
            "golden_set_size": total_examples,
            "clean_retrieval_corpus_size": len(clean_corpus),
            "annotation_methodology": golden_metadata.get('annotation_method', 'AI-assisted automatic annotation')
        },
        "comparison": {
            "trivial_baseline": {
                "name": "Majority Class Baseline",
                "accuracy": round(acc_maj, 4),
                "macro_f1": round(f1_macro_maj, 4),
                "weighted_f1": round(f1_weighted_maj, 4)
            },
            "weakly_supervised_ml_baseline": {
                "name": "TF-IDF + Logistic Regression",
                "accuracy": round(acc_logreg, 4),
                "macro_f1": round(f1_macro_logreg, 4),
                "weighted_f1": round(f1_weighted_logreg, 4)
            },
            "old_proposed_system": {
                "name": "Old Proposed Rule System",
                "intent_accuracy": 0.9050,
                "intent_macro_f1": 0.8935,
                "escalation_accuracy": 0.3350,
                "escalation_precision": 0.1951,
                "escalation_recall": 0.9697,
                "escalation_f1": 0.3249,
                "escalation_tp": 32,
                "escalation_tn": 35,
                "escalation_fp": 132,
                "escalation_fn": 1,
                "automation_rate": 0.1800
            },
            "improved_proposed_system_v3": {
                "name": "Improved Proposed System v3",
                "intent_accuracy": round(acc_v3_intent, 4),
                "intent_macro_f1": round(f1_macro_v3_intent, 4),
                "intent_weighted_f1": round(f1_weighted_v3_intent, 4),
                "escalation_accuracy": round(acc_v3_esc, 4),
                "escalation_precision": round(p_v3_esc, 4),
                "escalation_recall": round(r_v3_esc, 4),
                "escalation_f1": round(f1_v3_esc, 4),
                "escalation_tp": tp,
                "escalation_tn": tn,
                "escalation_fp": fp,
                "escalation_fn": fn,
                "automation_rate": automation_rate,
                "over_escalation_rate": over_escalation_rate,
                "missed_escalation_rate": missed_escalation_rate
            }
        },
        "per_intent_metrics_v3": per_intent_metrics_v3,
        "confusion_matrix_v3": {
            "labels": intent_labels,
            "matrix": cm_v3_intent
        }
    }

    with open(EVALUATION_SUMMARY_V3_PATH, 'w', encoding='utf-8') as f:
        json.dump(summary_v3, f, indent=2, ensure_ascii=False)

    print("\n--- EVALUATION V3 SUMMARY RESULTS ---")
    print(f"Old System Escalation Accuracy -> 33.50% | Precision: 19.51% | Recall: 96.97% (FP=132)")
    print(f"New System Escalation Accuracy -> {acc_v3_esc*100:.2f}% | Precision: {p_v3_esc*100:.2f}% | Recall: {r_v3_esc*100:.2f}% (FP={fp}, FN={fn})")
    print(f"Automation Rate                -> {automation_rate*100:.2f}%")
    print(f"Over-Escalation Rate           -> {over_escalation_rate*100:.2f}%")
    print(f"Missed-Escalation Rate         -> {missed_escalation_rate*100:.2f}%")
    print(f"New System Intent Accuracy     -> {acc_v3_intent*100:.2f}% | Macro F1: {f1_macro_v3_intent:.4f}")

    # 7. Generate Dynamic Failure Analysis v3
    generate_failure_analysis_v3(v3_per_example_results)

    return summary_v3

def generate_failure_analysis_v3(results: list[dict]):
    """
    Generate dynamic failure analysis from actual v3 prediction errors.
    Identifies top failure modes without hardcoding.
    """
    total = len(results)
    failures = []

    for item in results:
        intent_err = not item["intent_correct"]
        esc_err = not item["escalation_correct"]

        if intent_err or esc_err:
            fail_type = "BOTH_MISMATCH" if (intent_err and esc_err) else ("INTENT_MISMATCH" if intent_err else "ESCALATION_MISMATCH")
            failures.append({
                "item": item,
                "fail_type": fail_type
            })

    # Group into failure mode categories dynamically
    categories = {}
    for f in failures:
        it = f["item"]
        if f["fail_type"] == "INTENT_MISMATCH":
            cat = f"Intent Misclassification: True '{it['true_intent']}' vs Pred '{it['predicted_intent']}'"
        elif f["fail_type"] == "ESCALATION_MISMATCH":
            if it["true_escalation"] == "AUTO-HANDLE" and it["predicted_escalation"] == "ESCALATE TO HUMAN":
                cat = "Escalation Over-Protection (False Positive Escalation)"
            else:
                cat = "Escalation Under-Protection (False Negative Escalation)"
        else:
            cat = f"Compound Error: Intent and Escalation Misclassified ({it['true_intent']})"

        if cat not in categories:
            categories[cat] = []
        categories[cat].append(it)

    # Sort failure modes by count descending
    sorted_cats = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)
    top_5 = sorted_cats[:5]

    top_failure_modes = []
    for cat_name, items in top_5:
        rep = items[0]
        cnt = len(items)
        pct = round(cnt / total * 100, 2)

        if "Over-Protection" in cat_name:
            cause = "Conservative safety threshold or low retrieval similarity (<0.38) triggering auto-escalation on routine ticket."
            fix = "Improve retrieval index density for rare phrasing and tune minimum retrieval threshold."
        elif "Under-Protection" in cat_name:
            cause = "High intent confidence and retrieval similarity masking an implicit refund/dispute risk signal."
            fix = "Expand implicit monetary dispute risk patterns to capture nuanced phrasing."
        elif "Intent" in cat_name:
            cause = f"Overlapping vocabulary between '{rep['true_intent']}' and '{rep['predicted_intent']}'."
            fix = f"Add distinctive term weights and exclusion rules for {rep['predicted_intent']}."
        else:
            cause = "Multiple ambiguity factors in short customer query."
            fix = "Prompt customer for mandatory category clarification before agent routing."

        top_failure_modes.append({
            "category": cat_name,
            "count": cnt,
            "percentage": pct,
            "representative_example": {
                "id": rep["id"],
                "customer_text": rep["customer_text"],
                "predicted_intent": rep["predicted_intent"],
                "expected_intent": rep["true_intent"],
                "predicted_escalation": rep["predicted_escalation"],
                "expected_escalation": rep["true_escalation"],
                "retrieval_similarity": rep["retrieval_best_similarity"]
            },
            "likely_cause": cause,
            "proposed_fix": fix
        })

    analysis_payload = {
        "metadata": {
            "total_examples": total,
            "total_failures": len(failures),
            "failure_rate": round(len(failures) / total * 100, 2)
        },
        "top_failure_modes": top_failure_modes
    }

    os.makedirs(os.path.dirname(FAILURE_ANALYSIS_V3_PATH), exist_ok=True)
    with open(FAILURE_ANALYSIS_V3_PATH, 'w', encoding='utf-8') as f:
        json.dump(analysis_payload, f, indent=2, ensure_ascii=False)

    print(f"Dynamic Failure Analysis v3 saved to {FAILURE_ANALYSIS_V3_PATH} ({len(top_failure_modes)} failure categories)")

if __name__ == "__main__":
    run_evaluation_v3()
