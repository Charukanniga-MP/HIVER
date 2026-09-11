# SpotifyCares AI Support Agent — Human Annotation Guide

This document provides official guidelines for hand-labeling the 200-example Golden Evaluation Set (`data/golden_set_v2.json`).

---

## 1. Intent Taxonomy Definitions & Boundaries

Select strictly ONE of the 6 core intents for each candidate conversation:

### 1. `playback_audio_issue`
* **Definition**: Technical bugs impairing real-time audio playback, app controls, volume, or playback stability across iOS, Android, or Desktop.
* **Positive Examples**:
  - *"My shuffle button is stuck on repeat and won't turn off on iOS 11."*
  - *"Music keeps randomly pausing every 30 seconds on my Android."*
  - *"Volume drops to zero automatically whenever a song starts."*
* **Negative Examples**: *"My downloaded songs won't play in airplane mode."* (Use `offline_sync_issue`).
* **Borderline Examples**: *"App crashes as soon as I open my Liked Songs playlist."* (Use `playback_audio_issue` if crash occurs during playback attempt).

### 2. `offline_sync_issue`
* **Definition**: Errors related to downloading tracks, offline mode playback, local device storage, or SD card synchronization.
* **Positive Examples**:
  - *"Downloaded tracks are greyed out when I turn on Airplane Mode."*
  - *"Spotify won't let me change download storage location to my SD card."*
* **Negative Examples**: *"Song stutters when streaming on 4G."* (Use `playback_audio_issue`).
* **Borderline Examples**: *"My downloaded playlist disappeared from my phone."* (Use `offline_sync_issue` if download storage failed).

### 3. `billing_subscription_dispute`
* **Definition**: Financial inquiries, double billing complaints, student discount verification failures, payment declines, or plan cancellations.
* **Positive Examples**:
  - *"I was charged $14.99 twice on my bank statement this morning."*
  - *"My SheerID student discount verification failed, please help."*
* **Negative Examples**: *"Can't log into my Premium account."* (Use `account_access_security`).
* **Borderline Examples**: *"I cancelled Premium last week but my account still says Premium."* (Use `billing_subscription_dispute`).

### 4. `account_access_security`
* **Definition**: Authentication failures, credential recovery, email modifications, unauthorized access, or account breaches.
* **Positive Examples**:
  - *"Someone changed my account email to a Russian address without my permission!"*
  - *"Password reset link is not arriving in my inbox."*
* **Negative Examples**: *"Can't log in because app keeps crashing."* (Use `playback_audio_issue`).
* **Borderline Examples**: *"I can't see my Premium status after changing my email."* (Use `account_access_security`).

### 5. `playlist_library_management`
* **Definition**: Issues managing saved tracks, missing playlists, local audio file importing, Daily Mix, or Spotify Wrapped.
* **Positive Examples**:
  - *"All my saved playlists from the last 3 years suddenly disappeared!"*
  - *"Local files won't sync from my desktop app to my iPhone."*
* **Negative Examples**: *"Downloaded playlist won't play offline."* (Use `offline_sync_issue`).
* **Borderline Examples**: *"Daily Mix 1 is playing songs I thumbs-downed."* (Use `playlist_library_management`).

### 6. `general_feedback_inquiry`
* **Definition**: Non-bug queries, feature requests, UI redesign feedback, lyrics availability questions, or general brand interactions.
* **Positive Examples**:
  - *"When are you guys going to add live lyrics for desktop in Canada?"*
  - *"I really dislike the new UI update layout."*
* **Negative Examples**: *"The new update made my app freeze on startup."* (Use `playback_audio_issue`).
* **Borderline Examples**: *"Can you order me a pepperoni pizza?"* (Use `general_feedback_inquiry` and set `is_out_of_scope: true`).

---

## 2. Escalation Guidelines & Product Rationales

### Assign `ESCALATE TO HUMAN` when:
1. **Account Takeover / Security Threat**: Account hacks, stolen credentials, email changed without consent.
   * *Rationale*: An AI agent cannot verify user identity, perform multi-factor authentication, or safely execute sensitive credential changes.
2. **Financial Dispute & Refund Request**: Double-billing, overcharges, credit card disputes requiring ledger verification.
   * *Rationale*: Financial adjustments require private payment system access and compliance audit trails unavailable to an AI agent.
3. **Query Ambiguity & Ultra-Short Signal**: Messages lacking context (*"help pls"*, *"why"*).
   * *Rationale*: Intent uncertainty makes automated troubleshooting unreliable, risking incorrect advice.
4. **Insufficient Historical Grounding**: Rare devices, out-of-scope queries, or edge cases where no grounded precedent exists.
   * *Rationale*: Prevents AI hallucination or fabricated policies when grounded evidence is unavailable.

### Assign `AUTO-HANDLE` when:
- Technical playback bugs or offline download issues with clear, self-serve troubleshooting (restarting app, clearing cache, updating iOS/Android).
- Public non-sensitive plan inquiries (e.g. *"How much is Premium for family?"*).

---

## 3. Difficulty Classification

- **`Easy`**: Clear keywords and explicit phrasing (*"My shuffle button is stuck on iOS 11"*).
- **`Medium`**: Conversational, indirect phrasing, or mild ambiguity (*"Why is my playlist not updating?"*).
- **`Hard`**: Ultra-short queries (*"help pls"*), sarcastic phrasing (*"Great job breaking playback again"*), multi-intent messages, or out-of-scope questions.

---

## 4. Out-of-Scope Field

Set `is_out_of_scope: true` for non-Spotify service queries (*"order pizza"*), random chatter, or completely unsupported non-music requests.
