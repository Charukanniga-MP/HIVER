# Golden Evaluation Set Methodology & Honest Disclosure

> [!IMPORTANT]
> **Honest Evaluation Disclosure**:
> Because manual human annotation of all 200 items was not feasible within project execution constraints, the labels in `data/golden_set_v2.json` were produced using **AI-assisted automatic annotation**.
>
> These labels are **NOT** equivalent to independently human-verified ground truth. Evaluation results reported against `golden_set_v2.json` represent an AI-assisted benchmark rather than a gold-standard human evaluation.

---

## 1. Candidate Sampling Methodology

We sampled **200 real SpotifyCares customer support conversations** from the 42,678 clean conversation pool in `data/processed/spotify_conversations.json`.

Sampling was guided by taxonomy-keyword coverage estimates across 7 strata:
1. `billing_subscription_dispute` (35 candidates)
2. `account_access_security` (30 candidates)
3. `playback_audio_issue` (30 candidates)
4. `general_feedback_inquiry` (25 candidates)
5. `playlist_library_management` (25 candidates)
6. `offline_sync_issue` (25 candidates)
7. `difficult_ambiguous_edge` (30 candidates from low-keyword pool)

---

## 2. AI-Assisted Annotation Rules

For each of the 200 candidate examples:
- **`true_intent`**: Classified into strictly one of the 6 core intents based on customer text semantics and brand response context.
- **`true_escalation`**: Assigned `ESCALATE TO HUMAN` for high-risk security threats, monetary refund disputes, ultra-short/ambiguous queries, or out-of-scope requests. Assigned `AUTO-HANDLE` for routine technical troubleshooting backed by self-serve precedents.
- **`is_out_of_scope`**: Flagged `true` for non-Spotify service queries (*"order pizza"*).
- **`difficulty`**: Assigned `Easy` (explicit keywords), `Medium` (indirect phrasing), or `Hard` (ultra-short / ambiguous / out-of-scope).
- **`annotator`**: Set explicitly to `"AI-assisted annotation"`.

---

## 3. Data Leakage & Evaluation Isolation

To preserve evaluation integrity:
1. **Zero Model Training Leakage**: `data/golden_set_v2.json` is **NEVER** used to train classifiers, fit TF-IDF vectorizers, or populate historical retrieval indices.
2. **Retrieval Exclusion**: All 200 Golden Set customer tweet IDs and exact customer text entries are explicitly excluded from the retrieval fitting matrix when `src/retriever.py` initializes.

---

## 4. Dataset Metadata Schema

The generated dataset `data/golden_set_v2.json` includes top-level metadata:

```json
{
  "metadata": {
    "total_examples": 200,
    "annotation_method": "AI-assisted automatic annotation",
    "human_annotation": false,
    "source": "SpotifyCares historical customer-support conversations",
    "intents": [
      "playback_audio_issue",
      "offline_sync_issue",
      "billing_subscription_dispute",
      "account_access_security",
      "playlist_library_management",
      "general_feedback_inquiry"
    ],
    "out_of_scope_supported": true,
    "labels_are_ground_truth": false,
    "note": "This evaluation set was produced via AI-assisted annotation and is NOT equivalent to a manually hand-labelled golden set."
  },
  "examples": [...]
}
```

---

## 5. Explicit Limitations & Methodological Disclosures

1. **AI-Assisted Reference Labels**: The 200 evaluation labels were generated using AI-assisted annotation rules and are not equivalent to independently human-verified ground truth.
2. **Reference Benchmark Interpretation**: Evaluation metrics measure classification agreement against this AI-assisted reference set rather than proven real-world accuracy.
3. **Weak Supervision in ML Baseline**: The 42,440 historical training conversations were labeled via weak keyword-taxonomy supervision (`src/intent_taxonomy.py`).
4. **Shared Taxonomy Assumptions**: The weakly supervised Logistic Regression baseline and the proposed Rule Classifier share rule/keyword logic, so comparison between them reflects shared taxonomy assumptions rather than an independent benchmark.
5. **Small Escalation Positive Class**: The evaluation set contains only 33 true positive escalation cases (out of 200 total examples).
6. **Escalation Precision & Workload**: Escalation precision is currently low (19.51%, 132 false positives out of 200), prioritizing safety and recall (96.97%) at the cost of creating human-agent review workload for routine tickets.
7. **Near-Duplicate Filtering Threshold**: Near-duplicate retrieval corpus filtering uses a TF-IDF cosine similarity threshold ($>0.95$), which removes near-identical messages but may retain distantly related queries.

