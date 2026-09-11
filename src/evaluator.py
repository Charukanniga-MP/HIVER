"""
Evaluation Harness v2 for SpotifyCares AI Support System.
Evaluates Proposed System and Baselines on independent data/golden_set_v2.json.
Enforces zero train/test contamination and exports data/evaluation_v2.json and data/evaluation_summary_v2.json.
"""

import os
import json
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from src.intent_taxonomy import classify_intent_rule_based
from src.retriever import HistoricalRetriever, CLEAN_CORPUS_PATH, GOLDEN_SET_V2_PATH
from src.escalation import evaluate_escalation
from src.generator import generate_support_reply
from src.baselines import MajorityClassBaseline, LogisticRegressionBaseline

EVALUATION_V2_PATH = r'd:\Hiver\data\evaluation_v2.json'
EVALUATION_SUMMARY_V2_PATH = r'd:\Hiver\data\evaluation_summary_v2.json'

def run_evaluation_v2():
    print("=" * 70)
    print("STARTING EVALUATION V2 (Independent Golden Set Benchmark)")
    print("=" * 70)

    # 1. Load Golden Evaluation Set v2
    with open(GOLDEN_SET_V2_PATH, 'r', encoding='utf-8') as f:
        golden_payload = json.load(f)

    golden_metadata = golden_payload.get('metadata', {})
    golden_examples = golden_payload.get('examples', [])
    print(f"Loaded Golden Set v2 ({len(golden_examples)} items)")
    print(f"Annotation Method: {golden_metadata.get('annotation_method')}")

    # 2. Load Clean Retrieval Corpus for Baseline Training
    retriever = HistoricalRetriever(CLEAN_CORPUS_PATH)
    clean_corpus = retriever.conversations
    print(f"Clean Non-Golden Corpus Size: {len(clean_corpus):,} items")

    # 3. Train Baselines on Weakly Supervised Corpus Labels (Isolated from Golden Set)
    print("\n[PHASE 2]: Training Baselines on Weakly Supervised Corpus...")
    X_train_corpus = [c['clean_customer_text'] for c in clean_corpus]
    y_train_weak = [classify_intent_rule_based(t)[0] for t in X_train_corpus]

    majority_base = MajorityClassBaseline()
    majority_base.fit(X_train_corpus, y_train_weak)

    logreg_base = LogisticRegressionBaseline()
    logreg_base.fit(X_train_corpus, y_train_weak)

    # 4. Prepare Evaluation Data (Independent N=200 Golden Set)
    X_eval = [ex['customer_text'] for ex in golden_examples]
    y_intent_true = [ex['true_intent'] for ex in golden_examples]
    y_esc_true = [ex['true_escalation'] for ex in golden_examples]

    # 5. Evaluate Proposed System (Consumes ONLY customer_text & tweet_id for leakage filter)
    print("\n[PHASE 3]: Evaluating Proposed System on Independent Golden Set...")
    proposed_intent_preds = []
    proposed_esc_preds = []
    per_example_results = []

    for ex in golden_examples:
        c_text = ex['customer_text']
        tweet_id = ex.get('customer_tweet_id')

        # Proposed System Inference Pipeline (Model NEVER receives true_intent or true_escalation)
        pred_intent, conf = classify_intent_rule_based(c_text)
        evidence = retriever.retrieve(c_text, exclude_tweet_id=tweet_id, top_k=3)
        esc_decision, reason, grounding = evaluate_escalation(pred_intent, conf, c_text, evidence)
        reply = generate_support_reply(c_text, pred_intent, evidence, esc_decision)

        proposed_intent_preds.append(pred_intent)
        proposed_esc_preds.append(esc_decision)

        intent_correct = (pred_intent == ex['true_intent'])
        esc_correct = (esc_decision == ex['true_escalation'])

        per_example_results.append({
            "id": ex['id'],
            "customer_text": c_text,
            "true_intent": ex['true_intent'],
            "predicted_intent": pred_intent,
            "intent_correct": intent_correct,
            "confidence": conf,
            "retrieval_evidence": [e['evidence_id'] for e in evidence],
            "retrieval_score": evidence[0]['similarity_score'] if evidence else 0.0,
            "generated_reply": reply,
            "true_escalation": ex['true_escalation'],
            "predicted_escalation": esc_decision,
            "escalation_correct": esc_correct,
            "escalation_reason": reason,
            "is_out_of_scope": ex.get('is_out_of_scope', False),
            "difficulty": ex.get('difficulty', 'Medium')
        })

    # 6. Evaluate Baselines on Independent Golden Set
    maj_preds = majority_base.predict(X_eval)
    logreg_preds = logreg_base.predict(X_eval)

    # 7. Calculate Intent Classification Metrics
    intent_labels = list(sorted(set(y_intent_true)))
    
    # Majority Baseline
    acc_maj = accuracy_score(y_intent_true, maj_preds)
    _, _, f1_macro_maj, _ = precision_recall_fscore_support(y_intent_true, maj_preds, average='macro', zero_division=0)
    _, _, f1_weighted_maj, _ = precision_recall_fscore_support(y_intent_true, maj_preds, average='weighted', zero_division=0)

    # LogReg Baseline
    acc_logreg = accuracy_score(y_intent_true, logreg_preds)
    _, _, f1_macro_logreg, _ = precision_recall_fscore_support(y_intent_true, logreg_preds, average='macro', zero_division=0)
    _, _, f1_weighted_logreg, _ = precision_recall_fscore_support(y_intent_true, logreg_preds, average='weighted', zero_division=0)

    # Proposed System
    acc_proposed = accuracy_score(y_intent_true, proposed_intent_preds)
    _, _, f1_macro_proposed, _ = precision_recall_fscore_support(y_intent_true, proposed_intent_preds, average='macro', zero_division=0)
    _, _, f1_weighted_proposed, _ = precision_recall_fscore_support(y_intent_true, proposed_intent_preds, average='weighted', zero_division=0)

    # Per-Intent Metrics for Proposed System
    p_intent, r_intent, f1_intent, supp_intent = precision_recall_fscore_support(
        y_intent_true, proposed_intent_preds, labels=intent_labels, zero_division=0
    )

    per_intent_metrics = {}
    for idx, intent_name in enumerate(intent_labels):
        per_intent_metrics[intent_name] = {
            "precision": round(float(p_intent[idx]), 4),
            "recall": round(float(r_intent[idx]), 4),
            "f1": round(float(f1_intent[idx]), 4),
            "support": int(supp_intent[idx])
        }

    # Confusion Matrix for Proposed System
    cm = confusion_matrix(y_intent_true, proposed_intent_preds, labels=intent_labels).tolist()

    # 8. Calculate Escalation Metrics
    acc_esc = accuracy_score(y_esc_true, proposed_esc_preds)
    p_esc, r_esc, f1_esc, _ = precision_recall_fscore_support(
        y_esc_true, proposed_esc_preds, pos_label='ESCALATE TO HUMAN', average='binary', zero_division=0
    )

    # 9. Save Evaluation v2 Per-Example Artifacts
    os.makedirs(os.path.dirname(EVALUATION_V2_PATH), exist_ok=True)
    with open(EVALUATION_V2_PATH, 'w', encoding='utf-8') as f:
        json.dump(per_example_results, f, indent=2, ensure_ascii=False)

    # 10. Save Evaluation Summary v2 Artifacts
    summary_v2 = {
        "metadata": {
            "golden_set_size": len(golden_examples),
            "clean_retrieval_corpus_size": len(clean_corpus),
            "annotation_method": golden_metadata.get('annotation_method', 'AI-assisted automatic annotation'),
            "baseline_training_method": "Weakly supervised training on non-golden historical corpus"
        },
        "trivial_baseline_metrics": {
            "name": "Majority Class Baseline",
            "majority_intent": majority_base.majority_class,
            "accuracy": round(acc_maj, 4),
            "macro_f1": round(f1_macro_maj, 4),
            "weighted_f1": round(f1_weighted_maj, 4)
        },
        "weakly_supervised_ml_baseline_metrics": {
            "name": "TF-IDF + Logistic Regression",
            "accuracy": round(acc_logreg, 4),
            "macro_f1": round(f1_macro_logreg, 4),
            "weighted_f1": round(f1_weighted_logreg, 4)
        },
        "proposed_system_metrics": {
            "name": "Proposed AI Support Agent System",
            "accuracy": round(acc_proposed, 4),
            "macro_f1": round(f1_macro_proposed, 4),
            "weighted_f1": round(f1_weighted_proposed, 4)
        },
        "escalation_metrics": {
            "accuracy": round(acc_esc, 4),
            "precision": round(p_esc, 4),
            "recall": round(r_esc, 4),
            "f1": round(f1_esc, 4)
        },
        "per_intent_metrics": per_intent_metrics,
        "confusion_matrix": {
            "labels": intent_labels,
            "matrix": cm
        }
    }

    with open(EVALUATION_SUMMARY_V2_PATH, 'w', encoding='utf-8') as f:
        json.dump(summary_v2, f, indent=2, ensure_ascii=False)

    print("\n--- ACTUAL BENCHMARK EVALUATION RESULTS (N=200 Independent Golden Set) ---")
    print(f"1. Trivial Baseline (Majority Class: '{majority_base.majority_class}') -> Accuracy: {acc_maj*100:.2f}% | Macro F1: {f1_macro_maj:.4f}")
    print(f"2. Weakly Supervised ML (LogReg 42k train)                       -> Accuracy: {acc_logreg*100:.2f}% | Macro F1: {f1_macro_logreg:.4f}")
    print(f"3. Proposed AI System (Rule Classifier + Retrieval)             -> Accuracy: {acc_proposed*100:.2f}% | Macro F1: {f1_macro_proposed:.4f}")
    print("-" * 70)
    print(f"Escalation Decision Accuracy -> {acc_esc*100:.2f}%")
    print(f"Escalation Precision         -> {p_esc*100:.2f}%")
    print(f"Escalation Recall            -> {r_esc*100:.2f}%")
    print(f"Escalation F1 Score          -> {f1_esc:.4f}")
    print("=" * 70)
    print(f"Per-example evaluation artifacts saved to: {EVALUATION_V2_PATH}")
    print(f"Summary metrics exported to          : {EVALUATION_SUMMARY_V2_PATH}")
    print("=" * 70)

    return summary_v2

if __name__ == "__main__":
    run_evaluation_v2()
