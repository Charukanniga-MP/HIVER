# SpotifyCares AI Support System & Dark Cyber-SaaS Command Center

An explainable, reliable, and auditable AI customer support system built for **SpotifyCares** using the Kaggle *Customer Support on Twitter* dataset. Designed as an internship submission for **Hiver**.

---

## 1. Project Overview

This repository implements an end-to-end, production-grade AI support pipeline designed to process incoming customer support requests with safety, auditability, and historical grounding.

* **Target Brand**: `SpotifyCares` (Spotify's official customer support channel)
* **Core Problem**: Social support agents face high ticket volumes with mixed technical, billing, and high-risk account takeover inquiries. Automated systems must safely handle routine issues while strictly escalating high-risk queries without hallucinating promises or private actions.
* **Core Agent Capabilities**:
  1. **Intent Classification**: Multi-layered heuristic and keyword signal matching across 6 support intents.
  2. **Historical Evidence Retrieval**: TF-IDF cosine similarity retrieval over clean historical support resolutions with strict data leakage prevention.
  3. **Grounded Response Generation**: Draft reply generation grounded in retrieved evidence or safe acknowledgment templates.
  4. **Risk-Calibrated Escalation**: Rule-based policy engine determining `AUTO-HANDLE` vs. `ESCALATE TO HUMAN` with auditable reasoning.

---

## 2. Architecture

```
Customer Message
       │
       ▼
Intent Classification  ──►  Predicts 1 of 6 Intents + Confidence Score
       │
       ▼
Historical Retrieval   ──►  TF-IDF Cosine Match (Leakage-Free Corpus)
       │
       ▼
Response Generation    ──►  Grounded Draft Reply + Evidence Attribution
       │
       ▼
Escalation Decision    ──►  AUTO-HANDLE vs. ESCALATE TO HUMAN + Audit Reason
       │
       ▼
Live Command Center & Helpdesk UI
```

* **Backend Inference API**: Lightweight Flask HTTP server (`server.py` on `http://localhost:5000`) executing real-time Python inference via `/api/predict`.
* **Frontend Command Center**: Modern Dark Cyber-SaaS React application built with Vite (`web/` on `http://localhost:3000`).

---

## 3. Data Processing & Corpus Construction

* **Source Dataset**: Kaggle `thoughtvector/customer-support-on-twitter` v10 (2,811,774 tweets across 108 brand handles from 2017-era data).
* **Brand Filtering & Reconstruction**: Filtered for `@SpotifyCares` interactions and reconstructed multi-turn conversation threads linking customer tweets to official brand responses.
* **Original Clean Pair Set**: 42,678 original clean conversation pairs.
* **Clean Retrieval Corpus**: **42,440 clean historical cases** after excluding all golden set evaluation items and near-duplicates (>0.95 similarity) to prevent data leakage.
* **Support Intent Taxonomy**:
  1. `playback_audio_issue`: Song playback stopping/pausing midway, stuttering audio, shuffle/repeat button glitches.
  2. `offline_sync_issue`: Offline downloads failing, tracks unplayable offline, SD card storage errors.
  3. `billing_subscription_dispute`: Unrecognized charges, double billing, Student discount verification, cancellation.
  4. `account_access_security`: Forgotten password, account hacked/breached, email address changes, unauthorized login attempts.
  5. `playlist_library_management`: Missing saved tracks, deleted playlists, local audio file import failure.
  6. `general_feedback_inquiry`: Feature requests, lyrics inquiries, app redesign feedback, general questions.

---

## 4. Golden Evaluation Set

* **Dataset Size**: 200 curated evaluation examples (`data/golden_set_v2.json`).
* **Sampling Strategy**: Stratified sampling across all 6 support intents, combined with a dedicated sampling dimension for difficult/ambiguous edge cases (ultra-short queries, multi-intent overlaps, Spanish/multilingual text).
* **Methodology Disclosure**: **200-example golden evaluation set with human review of every example. AI-assisted labels were used only as initial suggestions; the project author explicitly confirmed or corrected every intent and escalation label.**
* **Evaluation Integrity**: Golden set labels were **not** used to train the proposed system or rule engine. The golden set remained 100% frozen during evaluation.

---

## 5. Baseline Comparisons

We evaluate our **Proposed System v3** against two standard reference baselines over the 200-example golden benchmark:

1. **Trivial Majority Baseline**: Always predicts the majority intent class (`general_feedback_inquiry`) and default routing.
2. **Weakly Supervised ML Baseline**: A TF-IDF + Logistic Regression model trained on 42,440 weakly-labeled historical corpus tweets. *(Note: The ML baseline uses taxonomy-derived weak labels and therefore shares some assumptions with the proposed system).*
3. **Proposed System v3**: Multi-layered signal pipeline combining pre-compiled regexes, leak-free retrieval, and risk-calibrated escalation rules.

---

## 6. Final Evaluation Results (Current Source of Truth Snapshot)

### Intent Classification Benchmark Performance ($N=200$)

| Model / System | Intent Accuracy | Macro F1 | Weighted F1 |
| :--- | :---: | :---: | :---: |
| **Trivial Majority Baseline** | 29.00% | 0.0749 | 0.1304 |
| **Weakly Supervised LogReg Baseline** | 84.00% | 0.8168 | 0.8375 |
| **Proposed System v3** | **88.00%** | **0.8625** | **0.8789** |

### Escalation Engine Performance ($N=200$)

| Metric | Value | Definition / Calculation |
| :--- | :---: | :--- |
| **Escalation Recall** | **96.97%** | True Escalates Captured / Total Expected Escalates (32 / 33) |
| **Escalation Precision** | **40.51%** | True Escalates Captured / Total Predicted Escalates (32 / 79) |
| **Escalation F1** | **0.5714** | Harmonic Mean of Precision and Recall |
| **Escalation Accuracy** | **76.00%** | Correct Escalation Decisions / Total Golden Set (151 / 200) |
| **Missed Escalations** | **1 / 200** | Count of expected human escalations incorrectly auto-handled |
| **Full-Set Missed Escalation Rate** | **0.50%** | Percentage of overall golden set with missed escalations (1 / 200) |
| **Over-Escalation Rate** | **23.50%** | Percentage of routine items escalated as safety precautions (47 / 200) |
| **Predicted Auto-Handled** | **60.50%** | Total tickets routed to auto-handling (121 / 200 = 120 TN + 1 FN) |
| **Correctly Auto-Handled Routine Cases (TN)** | **60.00%** | Truly routine cases correctly auto-handled (120 / 200) |

### Response Quality Evaluation ($N=30$)

Methodology Disclosure: **Response-quality evaluation uses $N=30$ human-reviewed examples (`data/human_ratings.json`) evaluated against an LLM-as-a-Judge API (`openai/gpt-4o-mini` via OpenRouter). Below are the empirical ratings and exact LLM-vs-human agreement metrics.**

| Dimension | Human Mean (1–5) | LLM Judge Mean (1–5) | Exact Agreement % | Within-1 Point % | Quadratic Weighted Kappa |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Relevance** | **3.47 / 5.0** | **3.53 / 5.0** | **53.33%** | **93.33%** | **0.7804** (Strong Alignment) |
| **Groundedness** | **2.80 / 5.0** | **2.63 / 5.0** | **20.00%** | **76.67%** | **0.4639** (Moderate Alignment) |
| **Helpfulness** | **3.17 / 5.0** | **2.97 / 5.0** | **23.33%** | **70.00%** | **0.4465** (Moderate Alignment) |
| **Correctness** | **3.77 / 5.0** | **5.00 / 5.0** | **43.33%** | **60.00%** | **0.0000** (Generous LLM Bias) |
| **Overall** | **3.40 / 5.0** | **3.20 / 5.0** | **23.33%** | **93.33%** | **0.6009** (Substantial Alignment) |
| **Summary Average** | **3.32 / 5.0** | **3.47 / 5.0** | **32.66%** | **78.67%** | **0.4583** |

---

## 7. Failure Analysis

Based on `data/final_failure_analysis.json`, the top 5 failure modes on the 200-example golden set are:

1. **False Positive Over-Escalation (Conservative Safety Override)** (*39 cases / 19.5% of eval set*):
   * *Cause*: Risk-calibrated escalation policy requires both high confidence ($\ge 0.70$) AND high retrieval similarity ($\ge 0.55$). Moderate similarity ($0.45–0.54$) forces conservative routing to human agents.
2. **Compound Cascade Error: Intent and Escalation Misclassified (`playback_audio_issue`)** (*6 cases / 3.0%*):
   * *Cause*: Short or multilingual queries contain insufficient English keyword signal for single-turn intent classification.
3. **Intent Misclassification: Expected 'account_access_security' vs Predicted 'general_feedback_inquiry'** (*4 cases / 2.0%*):
   * *Cause*: Overlapping vocabulary (e.g., requesting monthly receipts via email) where general feedback rule weights outweighed account security rules.
4. **Intent Misclassification: Expected 'general_feedback_inquiry' vs Predicted 'offline_sync_issue'** (*3 cases / 1.5%*):
   * *Cause*: Keyword overlap ("sync my tunes to phone/desktop") causing query to be misrouted to offline sync troubleshooting.
5. **Intent Misclassification: Expected 'billing_subscription_dispute' vs Predicted 'offline_sync_issue'** (*2 cases / 1.0%*):
   * *Cause*: Query mentioning song storage space on SD card vs internal memory misclassified as offline sync instead of billing/account options.

---

## 8. What is Misleading About Headline Numbers? (Limitations & Tradeoffs)

> **Important Disclosure**: 88.00% intent accuracy should **NOT** be interpreted as production readiness.

1. **Human-Reviewed Golden Set**: Every example in the 200-example golden set (`data/golden_set_human_reviewed.json`) was explicitly human-reviewed by the project author (confirming or correcting initial AI-assisted suggestions).
2. **LLM-as-a-Judge Evaluation**: Real LLM-as-a-Judge evaluation was executed over $N=30$ items (`data/llm_judge_results.json`), achieving **78.67% within-1-point agreement** and **32.66% exact agreement** against genuine human ratings.
3. **Weak Supervision in Baselines**: The ML baseline uses taxonomy-derived weak labels and therefore shares some assumptions with the proposed system.
4. **Small Evaluation Sample Sizes**: Benchmark metrics rely on $N=200$ golden examples, while human quality evaluations cover $N=30$ human-reviewed ratings.
5. **Over-Escalation Tradeoff**: Achieving 96.97% escalation recall required accepting a **23.50% over-escalation rate** (47 routine cases routed to humans).
6. **Historical Data Currency**: Historical Twitter support data from 2017-era data reflects historical Spotify policies and links.
7. **Retrieval Boundary Limits**: TF-IDF retrieval struggles with semantic similarity, slang, typos, and multilingual queries.

---

## 9. Live Demo Setup

To launch the system locally and perform live inference:

### Step 1: Start Backend API Server (Terminal 1)
```bash
python server.py
```
*Loads the 42,440 case retrieval index and starts the Flask API on `http://localhost:5000`.*

### Step 2: Start Frontend Application (Terminal 2)
```bash
cd web
npm install
npm run dev
```
*Launches the Dark Cyber-SaaS Command Center on `http://localhost:3000`.*

### Live Inference Flow
When a user enters a customer message in the **Live Command Center**:
1. Frontend sends HTTP POST request to `POST http://localhost:5000/api/predict` with `{"customer_text": "..."}`.
2. Backend executes `classify_intent()` $\rightarrow$ `retrieve_with_quality()` $\rightarrow$ `decide_escalation()` $\rightarrow$ `generate_grounded_response()`.
3. Backend returns complete audit JSON containing predicted intent, evidence ID, similarity score, draft reply, escalation decision, risk level, and rationale.

---

## 10. Reproducibility & Commands

Every pipeline step can be verified using standard repository commands:

```bash
# 1. Environment Installation
pip install -r requirements.txt
cd web && npm install && cd ..

# 2. Run All Unit Tests (52/52 Passing)
python -m unittest discover tests

# 3. Execute Full Final Evaluation & Audit Pipeline
python -m evaluation.run

# 4. Import Human Ratings & Compute Agreement (30/30)
python -m scripts.import_human_ratings --input data/human_ratings.json

# 5. Export UI Data Bundle
python scripts/export_app_data.py

# 6. Build Production Frontend Bundle
cd web && npm run build && cd ..
```

---

## 11. Testing & QA Status

* **Python Unit Test Suite**: **52 / 52 tests passing** (`python -m unittest discover tests`)
* **Frontend Production Build**: **Passing** (`cd web && npm run build` succeeds without errors)

---

## 12. Project Structure

```
d:/Hiver/
├── data/
│   ├── processed/
│   │   └── clean_retrieval_corpus.json  # 42,440 clean retrieval cases
│   ├── golden_set_v2.json               # 200 frozen golden evaluation examples
│   ├── final_evaluation.json            # Itemized 200-example predictions
│   ├── final_evaluation_summary.json    # Summary metrics & baseline comparisons
│   ├── final_failure_analysis.json      # Top 5 failure mode taxonomy
│   ├── human_ratings.json               # 30 explicitly approved human ratings
│   └── response_quality_summary.json    # Human response quality score breakdown
├── src/
│   ├── intent_taxonomy.py               # Intent categories, regexes & classifier
│   ├── retriever.py                     # Leak-free historical retriever
│   ├── escalation.py                    # Risk-calibrated escalation engine
│   ├── generator.py                     # Grounded draft reply generator
│   ├── baselines.py                     # Baseline models (Trivial & LogReg)
│   └── evaluator.py                     # Pipeline evaluation harness
├── evaluation/
│   └── run.py                           # CLI evaluation runner
├── scripts/
│   ├── export_app_data.py               # Bundles artifacts for frontend
│   └── import_human_ratings.py          # Validates & imports human rating data
├── tests/
│   ├── test_pipeline.py                 # Core pipeline unit tests
│   └── test_proposed_agent_v3.py        # System v3 unit tests
├── web/
│   ├── src/                             # React SPA Dark Cyber-SaaS UI
│   ├── package.json
│   └── vite.config.js
├── server.py                            # Flask Live Inference API (port 5000)
├── decision_log.md                      # Engineering decisions & architectural rationale
├── README.md                            # Primary project documentation
└── requirements.txt                     # Python dependencies
```

---

## 13. Decision Log Reference

For detailed explanations of architectural design choices (such as choosing rule-based signal intent taxonomy over unconstrained ML classifiers, choosing conservative escalation thresholds, and implementing strict retrieval data leakage filters), consult [`decision_log.md`](file:///d:/Hiver/decision_log.md).

---

## 14. What Was Not Built (Scope Boundaries)

To maintain realistic scope boundaries for an internship take-home assignment, the following were intentionally excluded:

1. **No Production Cloud Deployment**: The application runs on local dev servers (`server.py` on Flask dev server, `npm run dev` on Vite) rather than cloud containerized infrastructure (Kubernetes / AWS ECS).
2. **No Real Customer Account Integration**: The system does not connect to live Spotify backend databases or OAuth authentication flows to modify user accounts.
3. **No Private Financial Ledger Access**: Billing disputes are safely escalated to human specialists rather than executing automated bank refunds or payment card modifications.
4. **LLM-as-a-Judge Evaluation**: Real LLM evaluation rubric executed over $N=30$ items (`data/llm_judge_results.json`) using `openai/gpt-4o-mini` via OpenRouter API, establishing **78.67% within-1-point agreement** against genuine human supervisor ratings.
5. **No Autonomous Financial or Account Actions**: The agent strictly generates draft replies and escalation decisions; it does not take autonomous actions on user subscriptions.
