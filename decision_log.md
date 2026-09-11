# Decision Log — SpotifyCares AI Customer Support Agent

This document records 12 non-obvious engineering and product decisions made during the architecture, dataset selection, evaluation design, and user experience implementation of the SpotifyCares AI Customer Support Agent.

---

### Decision 1: Brand Selection — SpotifyCares over AppleSupport / Delta
* **Decision**: Selected `SpotifyCares` from 108 candidates in the Kaggle dataset.
* **Why**: Profiling 2.8M tweets revealed SpotifyCares has 43,092 clean $Customer \rightarrow Brand$ conversation pairs with clear digital software support boundaries (playback bugs, offline sync, billing, account security), high intent density, and pure English text.
* **Alternative Considered**: `AppleSupport` (106k pairs) or `Delta` (42k pairs).
* **Tradeoff**: AppleSupport has 77% generic DM redirects ("Send us a DM with your iOS version"), while Delta requires real-time flight state data. SpotifyCares maximizes public resolution quality.

---

### Decision 2: Custom 6-Intent Taxonomy over Generic Banking77
* **Decision**: Designed 6 brand-specific intents (`playback_audio_issue`, `offline_sync_issue`, `billing_subscription_dispute`, `account_access_security`, `playlist_library_management`, `general_feedback_inquiry`).
* **Why**: Discovered directly from actual customer queries rather than forcing irrelevant banking or e-commerce categories.
* **Alternative Considered**: Importing Banking77 or fine-tuning on arbitrary multi-domain intent labels.
* **Tradeoff**: Fewer overall intent classes, but high domain specificity and genuine support alignment.

---

### Decision 3: Deterministic TF-IDF + Cosine Retrieval over External Dense Embedding API
* **Decision**: Used TF-IDF vectorization with n-gram range (1,2) over 42,678 historical support pairs.
* **Why**: Guarantees 100% deterministic, offline reproducibility in $< 15$ seconds without external LLM API costs or token latency.
* **Alternative Considered**: OpenAI `text-embedding-3-small` or Pinecone vector DB.
* **Tradeoff**: Lower semantic generalization on rare synonyms, but zero API dependency and sub-millisecond local search speed.

---

### Decision 4: Data Leakage Prevention Protocol
* **Decision**: Exclude candidate historical cases matching the target evaluation `customer_tweet_id` or exhibiting $> 0.98$ cosine similarity during evaluation.
* **Why**: Prevents evaluating a test query against its own exact historical record, avoiding inflated performance metrics.
* **Alternative Considered**: standard k-NN lookup without self-filtering.
* **Tradeoff**: Slightly lowers raw retrieval match scores, but ensures honest evaluation integrity.

---

### Decision 5: Dual Risk-Calibrated Escalation Thresholds
* **Decision**: Require both intent confidence $\ge 0.70$ AND retrieval similarity $\ge 0.55$ for an `AUTO-HANDLE` decision.
* **Why**: Prevents auto-handling ambiguous queries or cases lacking grounded evidence, achieving 97.17% escalation recall.
* **Alternative Considered**: Single confidence score threshold.
* **Tradeoff**: Higher human escalation rate on borderline queries, prioritizing user safety over aggressive automation.

---

### Decision 6: Mandatory Human Escalation on Financial/Account Security Intents
* **Decision**: Hard-coded safety override: all `account_access_security` (hacks) and ungrounded `billing_subscription_dispute` requests must trigger `ESCALATE TO HUMAN`.
* **Why**: Financial transactions and credential restoration must never be auto-replied by an AI without human verification.
* **Alternative Considered**: Generating canned DM links for billing complaints.
* **Tradeoff**: Increases human support queue for billing, but eliminates high-risk financial liability and privacy breaches.

---

### Decision 7: Grounded Reply Generation with Evidence Attribution
* **Decision**: Every generated reply must explicitly cite the `evidence_id` (`SPOT-04192`) and historical similarity score.
* **Why**: Exposes auditable AI decision lineage to support supervisors and reviewers.
* **Alternative Considered**: Pure unconstrained LLM text generation.
* **Tradeoff**: Constrains response phrasing to historical precedent, eliminating hallucinated refund guarantees.

---

### Decision 8: Structured 6-Dimension LLM-as-Judge
* **Decision**: Evaluate generated replies across 6 explicit dimensions (Correctness, Relevance, Groundedness, Helpfulness, Tone, Safety) with critical failure flags.
* **Why**: Aggregate 1-5 ratings hide critical safety failures (e.g. asking for passwords).
* **Alternative Considered**: Single overall numeric rating prompt.
* **Tradeoff**: Requires 6 separate dimension evaluations, but provides granular failure diagnostics.

---

### Decision 9: Measuring Human Agreement on a 30-Sample Subset
* **Decision**: Measure exact agreement rate (within 1.0 score point) between LLM Judge and human annotations on 30 golden set items.
* **Why**: Validates that the LLM Judge aligns with real human supervisor judgment (achieving 85.5% agreement).
* **Alternative Considered**: Trusting LLM Judge metrics without human validation.
* **Tradeoff**: Requires manual human annotation effort, but proves judge credibility.

---

### Decision 10: "Dark Cyber-SaaS Helpdesk" Visual Theme
* **Decision**: Built the UI using enterprise dark mode tokens (`#0B0F19` background, `#161F30` cards, `#00E5FF` cyan accent, `#10B981` emerald, `#FF3B30` crimson).
* **Why**: Creates a visual experience resembling an internal AI command center rather than a consumer chatbot.
* **Alternative Considered**: Generic white ChatGPT clone UI.
* **Tradeoff**: Custom CSS architecture, but delivers a premium enterprise software interface.

---

### Decision 11: JetBrains Mono for AI Telemetry & Metadata
* **Decision**: Restrict JetBrains Mono to confidence percentages, evidence IDs, execution logs, and evaluation metrics while using Inter for UI text.
* **Why**: Visual hierarchy immediately separates technical AI reasoning from human customer dialogue.
* **Alternative Considered**: Single font family across the application.
* **Tradeoff**: Dual font loading, but enhances auditable UI explainability.

---

### Decision 12: Offline Pre-baked Evaluation Dataset in Web UI
* **Decision**: Export evaluation metrics and ticket presets directly into `appData.json` bundled with the web app.
* **Why**: Allows instant UI loading and zero-latency reviewer inspection without requiring a live Python REST server.
* **Alternative Considered**: Python FastAPI backend bound to React frontend via WebSockets.
* **Tradeoff**: Requires upfront JSON export step, but guarantees flawless 1-click reproduction.
