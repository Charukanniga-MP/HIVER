# SpotifyCares AI Support Agent — Architecture & Safety Specification

This document details the multi-stage, grounded architecture of the **SpotifyCares AI Support Agent** (System v3).

---

## 1. System Pipeline Overview

```
Customer Message
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│ 1. Intent Classification & Confidence Scoring           │
│    (src/intent_taxonomy.py)                             │
│    • 6 Core Taxonomy Intents                            │
│    • High-Priority Security / Takeover Overrides        │
│    • Calibrated Confidence Score & Reasoning            │
└──────────────────────────┬──────────────────────────────┘
                           │ {intent, confidence, reason}
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Historical Evidence Retrieval                        │
│    (src/retriever.py)                                   │
│    • Top-k Cosine Similarity over Clean 42.4k Corpus    │
│    • Strict Zero-Golden-Leakage Filtering               │
│    • Evidence Quality (strong | medium | weak)          │
└──────────────────────────┬──────────────────────────────┘
                           │ {evidence, best_similarity, evidence_quality}
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Explicit Escalation Policy Engine                    │
│    (src/escalation.py)                                  │
│    • Risk Signal Detection (Account Takeover, Refunds)  │
│    • Ambiguity & Retrieval Evidence Evaluation          │
│    • Risk Level Assignment (LOW | MEDIUM | HIGH)        │
└──────────────────────────┬──────────────────────────────┘
                           │ {decision, reason, risk_level}
                           ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Grounded Response Generation                         │
│    (src/generator.py)                                   │
│    • Brand-Aligned Grounded Resolution                  │
│    • Evidence Tracking (evidence_ids)                   │
│    • Strict Refusal to Hallucinate Account / Policy Actions│
└──────────────────────────┬──────────────────────────────┘
                           │
                           ▼
             Final Response & Audit Metadata
```

---

## 2. Component Design & Rationale

### A. Intent Classification (`src/intent_taxonomy.py`)
* **Purpose**: Classify raw customer text into one of 6 operational support intents.
* **Security Override Mechanism**: If a customer message contains explicit compromised-account phrases (*"hacked my account"*, *"someone logged in and changed my email"*), the classifier immediately assigns `account_access_security` with high confidence (0.95), overriding secondary vocabulary matches (such as playlist or album mentions).
* **Output Interface**:
  ```json
  {
    "intent": "account_access_security",
    "confidence": 0.95,
    "reason": "Explicit account security / takeover keyword detected ('hacked')."
  }
  ```

### B. Historical Evidence Retrieval (`src/retriever.py`)
* **Purpose**: Retrieve top-$k$ historically resolved brand responses from the clean non-golden corpus (42,440 items).
* **Leakage Prevention**: Excludes exact customer tweet IDs, exact golden customer texts, and near-duplicate messages ($>0.95$ TF-IDF similarity).
* **Quality Grading**:
  * **Strong**: Cosine similarity $\ge 0.70$
  * **Medium**: $0.50 \le \text{similarity} < 0.70$
  * **Weak**: Cosine similarity $< 0.50$
* **Output Interface**:
  ```json
  {
    "evidence": [...],
    "best_similarity": 0.7723,
    "evidence_quality": "strong"
  }
  ```

### C. Escalation Policy Engine (`src/escalation.py`)
* **Purpose**: Determine whether a ticket should be automatically handled (`AUTO-HANDLE`) or routed to a human specialist (`ESCALATE TO HUMAN`).
* **Decision Factors**:
  1. **Security Risk**: Account takeover / hacked account keywords $\rightarrow$ `HIGH` risk $\rightarrow$ `ESCALATE TO HUMAN`.
  2. **Monetary Risk**: Double charges, refund disputes, credit card fraud $\rightarrow$ `HIGH` risk $\rightarrow$ `ESCALATE TO HUMAN`.
  3. **Evidence Quality**: Routine issues with similarity score $\ge 0.40$ and clear intent $\rightarrow$ `AUTO-HANDLE`.
  4. **Brevity & Ambiguity**: Ultra-short queries without risk signals or retrieval evidence are escalated to prevent automated guessing.

### D. Grounded Response Generation (`src/generator.py`)
* **Purpose**: Produce brand-aligned responses grounded exclusively in retrieved historical evidence.
* **Hallucination Control**:
  * The generator does **NOT** invent unsupported policies, promise monetary refunds, or claim to have accessed the customer's private account.
  * If escalation is triggered, the system returns a safe handoff notice explaining that a human specialist will complete account verification.
  * Every generated reply includes `evidence_ids` and a `grounding_reason`.

## 4. Response Quality Evaluation Architecture

### Overview
The response quality evaluation framework measures the quality of generated support replies across four dimensions:
1. **Relevance** (30% weight)
2. **Groundedness** (30% weight)
3. **Helpfulness** (20% weight)
4. **Correctness & Safety** (20% weight)

### Evaluation Flow
1. **Stratified Sampling (`scripts/sample_judge_set.py`)**: Generates a reproducible stratified sample of 40 examples across error modes, retrieval quality levels, and escalation decisions saved to `data/judge_sample.json`.
2. **LLM Judge Interface (`src/llm_judge.py`)**: Abstracts provider calls (OpenAI/Gemini) and returns structured JSON scores. Includes an explicit `NonLLMFallbackJudge` used when API credentials or quotas are unavailable.
3. **Human Rating CLI (`scripts/rate_judge_sample.py`)**: Provides an interactive terminal CLI for human annotators to record genuine 1–5 ratings saved to `data/human_rating_template.json`.
4. **Agreement Metrics (`src/agreement_metrics.py`)**: Computes Quadratic Weighted Cohen's Kappa, Exact Agreement, and Within-One-Point Agreement between LLM Judge ratings and Human ratings saved to `data/judge_human_agreement.json`.

---

## 5. Methodological Limitations & Explicit Disclosures

1. **Golden Set Labeling Limitation**: Initial intent and escalation labels in the 200-example golden set (`data/golden_set_v2.json`) were created using AI-assisted annotation and rule validation. These labels were not independently double-blind human-labelled ground truth. This is a limitation of the evaluation.
2. **LLM-as-Judge Limitation**: The LLM judge interface and rubric are implemented, but the external LLM API was unavailable during the final evaluation run. A deterministic NonLLMFallbackJudge was used only for infrastructure verification. Its scores are not presented as LLM-judge results or LLM-human agreement.
3. **Response-Quality Ratings**: Response-quality results reported here are from 30 human-reviewed, AI-assisted ratings.
4. **Weak Supervision in Baseline**: The 42,440 historical training conversations were labeled via weak keyword-taxonomy supervision.
5. **Shared Taxonomy Assumptions**: The ML baseline and rule classifier share taxonomy assumptions, making baseline comparison non-independent.

